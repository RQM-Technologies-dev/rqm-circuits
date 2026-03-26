# gates.py
"""Gate definition model for rqm-circuits.

This module defines the lightweight :class:`Gate` dataclass and the canonical
gate registry.

Design notes
------------
Gates are **definitions**, not applications.  A :class:`Gate` says "what kind of
operation this is", while an :class:`~rqm_circuits.instructions.Instruction`
says "apply this gate to these specific qubits with these specific parameters".

The gate registry (:data:`STANDARD_GATES`) provides the minimal canonical set
needed for a universal gate language without tying the package to any particular
backend.

Quaternion relationship
-----------------------
In the RQM stack, every single-qubit gate has an exact quaternion representation
``q = cos(θ/2) + u·sin(θ/2)`` where ``u`` is the unit pure-imaginary quaternion
corresponding to the rotation axis.  The :attr:`Gate.quaternion_form` field
carries a human-readable description of this form; the mathematical evaluation
lives in the companion ``rqm-core`` library.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rqm_circuits.errors import GateDefinitionError
from rqm_circuits.types import GateCategory


@dataclass(frozen=True)
class Gate:
    """Lightweight, backend-neutral gate definition.

    Attributes:
        name: Canonical short name (e.g. ``"h"``, ``"cx"``, ``"rx"``).
        arity: Number of *target* qubits the gate acts on.  Must be ≥ 0.
        num_params: Number of numeric/symbolic parameters the gate expects.
        num_controls: Number of *control* qubits this gate requires.
            ``0`` for non-controlled gates; ``1`` for standard controlled
            gates like ``cx``, ``cy``, ``cz``.
        param_names: Canonical ordered tuple of parameter names.  When
            non-empty, ``len(param_names) == num_params`` is required and
            instruction parameters are validated against these names.
        categories: Broad category tags for downstream filtering.
        description: Human-readable description including quaternion form where
                     applicable.
        quaternion_form: Optional string expression of the unit-quaternion
                         representation (for single-qubit gates).  This is
                         informational; numeric evaluation lives in ``rqm-core``.
        allows_barrier: Internal flag – set to ``True`` only for the special
                         ``barrier`` directive which accepts a variable arity.

    Examples:
        >>> from rqm_circuits.gates import STANDARD_GATES
        >>> STANDARD_GATES["h"]
        Gate(name='h', arity=1, num_params=0, ...)
        >>> STANDARD_GATES["rx"]
        Gate(name='rx', arity=1, num_params=1, param_names=('angle',), ...)
        >>> STANDARD_GATES["cx"]
        Gate(name='cx', arity=1, num_controls=1, ...)
    """

    name: str
    arity: int
    num_params: int = 0
    num_controls: int = 0
    param_names: tuple[str, ...] = field(default_factory=tuple)
    categories: frozenset[GateCategory] = field(default_factory=frozenset)
    description: str = ""
    quaternion_form: str = ""
    allows_barrier: bool = False

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise GateDefinitionError("Gate name must be a non-empty string.")
        if self.arity < 0:
            raise GateDefinitionError(
                f"Gate '{self.name}' has invalid arity {self.arity}; must be ≥ 0."
            )
        if self.num_params < 0:
            raise GateDefinitionError(
                f"Gate '{self.name}' has invalid num_params {self.num_params}; must be ≥ 0."
            )
        if self.num_controls < 0:
            raise GateDefinitionError(
                f"Gate '{self.name}' has invalid num_controls {self.num_controls}; must be ≥ 0."
            )
        # Coerce param_names to a tuple for immutability and consistent typing.
        object.__setattr__(self, "param_names", tuple(self.param_names))
        if self.param_names and len(self.param_names) != self.num_params:
            raise GateDefinitionError(
                f"Gate '{self.name}' has {len(self.param_names)} param_names but "
                f"num_params={self.num_params}; they must be equal."
            )

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        d: dict[str, Any] = {
            "name": self.name,
            "arity": self.arity,
            "num_params": self.num_params,
            "categories": sorted(c.value for c in self.categories),
        }
        if self.num_controls:
            d["num_controls"] = self.num_controls
        if self.param_names:
            d["param_names"] = list(self.param_names)
        if self.description:
            d["description"] = self.description
        if self.quaternion_form:
            d["quaternion_form"] = self.quaternion_form
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Gate:
        """Deserialize from a dictionary produced by :meth:`to_dict`.

        Args:
            data: Dictionary representation of a gate.

        Returns:
            A :class:`Gate` instance.

        Raises:
            :class:`~rqm_circuits.errors.SerializationError`: When fields are
                missing or malformed.
            :class:`~rqm_circuits.errors.GateDefinitionError`: When the gate
                definition itself is invalid.
        """
        from rqm_circuits.errors import SerializationError

        for key in ("name", "arity"):
            if key not in data:
                raise SerializationError(
                    f"Gate dict is missing required field {key!r}: {data!r}"
                )
        categories: frozenset[GateCategory] = frozenset()
        raw_cats = data.get("categories", [])
        if raw_cats:
            try:
                categories = frozenset(GateCategory(c) for c in raw_cats)
            except ValueError as exc:
                raise SerializationError(f"Unknown gate category: {exc}") from exc
        raw_param_names = data.get("param_names", [])
        return cls(
            name=data["name"],
            arity=int(data["arity"]),
            num_params=int(data.get("num_params", 0)),
            num_controls=int(data.get("num_controls", 0)),
            param_names=tuple(str(n) for n in raw_param_names),
            categories=categories,
            description=str(data.get("description", "")),
            quaternion_form=str(data.get("quaternion_form", "")),
        )

    def __repr__(self) -> str:
        cats = ", ".join(sorted(c.value for c in self.categories))
        parts = [
            f"Gate(name={self.name!r}",
            f"arity={self.arity}",
            f"num_params={self.num_params}",
        ]
        if self.num_controls:
            parts.append(f"num_controls={self.num_controls}")
        if self.param_names:
            parts.append(f"param_names={self.param_names!r}")
        parts.append(f"categories=[{cats}])")
        return ", ".join(parts)


# --------------------------------------------------------------------------- #
# Canonical standard gate registry
# --------------------------------------------------------------------------- #

def _gate(
    name: str,
    arity: int,
    num_params: int = 0,
    num_controls: int = 0,
    param_names: tuple[str, ...] = (),
    cats: list[GateCategory] | None = None,
    desc: str = "",
    qf: str = "",
    barrier: bool = False,
) -> Gate:
    return Gate(
        name=name,
        arity=arity,
        num_params=num_params,
        num_controls=num_controls,
        param_names=param_names,
        categories=frozenset(cats or []),
        description=desc,
        quaternion_form=qf,
        allows_barrier=barrier,
    )


#: Canonical registry of standard gates.
#:
#: This is the minimal gate set required for a universal quantum circuit language.
#: All gates here are backend-neutral.  Backend-specific decompositions are
#: handled in the ``rqm-compiler`` and adapter layers.
#:
#: Controlled gates (cx, cy, cz) use arity=1 (one target qubit) and
#: num_controls=1 (one required control qubit).  Instructions for these gates
#: must supply exactly one qubit via ``controls=`` and one via ``targets=``.
STANDARD_GATES: dict[str, Gate] = {
    # ----- Single-qubit identity -----
    "i": _gate(
        "i", 1,
        cats=[GateCategory.SINGLE_QUBIT, GateCategory.CLIFFORD],
        desc="Identity gate – no-op.",
        qf="q = 1",
    ),
    # ----- Pauli gates -----
    "x": _gate(
        "x", 1,
        cats=[GateCategory.SINGLE_QUBIT, GateCategory.CLIFFORD],
        desc="Pauli-X gate.  π-rotation about the x-axis on the Bloch sphere.",
        qf="q = i  (cos(π/2) + i·sin(π/2), axis = x̂)",
    ),
    "y": _gate(
        "y", 1,
        cats=[GateCategory.SINGLE_QUBIT, GateCategory.CLIFFORD],
        desc="Pauli-Y gate.  π-rotation about the y-axis on the Bloch sphere.",
        qf="q = j  (cos(π/2) + j·sin(π/2), axis = ŷ)",
    ),
    "z": _gate(
        "z", 1,
        cats=[GateCategory.SINGLE_QUBIT, GateCategory.CLIFFORD],
        desc="Pauli-Z gate.  π-rotation about the z-axis on the Bloch sphere.",
        qf="q = k  (cos(π/2) + k·sin(π/2), axis = ẑ)",
    ),
    # ----- Hadamard -----
    "h": _gate(
        "h", 1,
        cats=[GateCategory.SINGLE_QUBIT, GateCategory.CLIFFORD],
        desc="Hadamard gate.  π-rotation about the (x+z)/√2 axis.",
        qf="q = (i+k)/√2  (axis = (x̂+ẑ)/√2, angle = π)",
    ),
    # ----- Phase gates -----
    "s": _gate(
        "s", 1,
        cats=[GateCategory.SINGLE_QUBIT, GateCategory.CLIFFORD],
        desc="S gate (phase gate).  π/2-rotation about the z-axis.",
        qf="q = cos(π/4) + k·sin(π/4)  (axis = ẑ, angle = π/2)",
    ),
    "t": _gate(
        "t", 1,
        cats=[GateCategory.SINGLE_QUBIT, GateCategory.NON_CLIFFORD],
        desc="T gate.  π/4-rotation about the z-axis.",
        qf="q = cos(π/8) + k·sin(π/8)  (axis = ẑ, angle = π/4)",
    ),
    # ----- Rotation gates -----
    "rx": _gate(
        "rx", 1, num_params=1, param_names=("angle",),
        cats=[GateCategory.SINGLE_QUBIT, GateCategory.ROTATION],
        desc="Rotation about x-axis by angle.",
        qf="q = cos(angle/2) + i·sin(angle/2)",
    ),
    "ry": _gate(
        "ry", 1, num_params=1, param_names=("angle",),
        cats=[GateCategory.SINGLE_QUBIT, GateCategory.ROTATION],
        desc="Rotation about y-axis by angle.",
        qf="q = cos(angle/2) + j·sin(angle/2)",
    ),
    "rz": _gate(
        "rz", 1, num_params=1, param_names=("angle",),
        cats=[GateCategory.SINGLE_QUBIT, GateCategory.ROTATION],
        desc="Rotation about z-axis by angle.",
        qf="q = cos(angle/2) + k·sin(angle/2)",
    ),
    # ----- Phase-shift gate (parity with rqm-compiler) -----
    "phaseshift": _gate(
        "phaseshift", 1, num_params=1, param_names=("angle",),
        cats=[GateCategory.SINGLE_QUBIT, GateCategory.ROTATION],
        desc="Phase-shift gate.  Applies a phase of e^(i·angle) to |1⟩.",
        qf="q = cos(angle/2) + k·sin(angle/2)  (diagonal phase gate)",
    ),
    # ----- Universal single-qubit gate (parity with rqm-compiler) -----
    "u1q": _gate(
        "u1q", 1, num_params=4, param_names=("w", "x", "y", "z"),
        cats=[GateCategory.SINGLE_QUBIT],
        desc=(
            "Universal single-qubit gate specified as a unit quaternion "
            "(w, x, y, z) where w + xi + yj + zk is the SU(2) element."
        ),
        qf="q = w + xi + yj + zk  (|q| = 1)",
    ),
    # ----- Two-qubit entangling gates (symmetric, no controls) -----
    "swap": _gate(
        "swap", 2,
        cats=[GateCategory.TWO_QUBIT, GateCategory.CLIFFORD],
        desc="SWAP gate.  Swaps the states of two qubits.",
    ),
    "iswap": _gate(
        "iswap", 2,
        cats=[GateCategory.TWO_QUBIT],
        desc="iSWAP gate.  SWAP with an additional i phase factor.",
    ),
    # ----- Controlled gates -----
    # arity=1 means one TARGET qubit; num_controls=1 means one CONTROL qubit.
    # Instructions for these gates supply controls=[{"index": ctrl}] and
    # targets=[{"index": tgt}].
    "cx": _gate(
        "cx", 1, num_controls=1,
        cats=[GateCategory.TWO_QUBIT, GateCategory.CLIFFORD],
        desc="Controlled-X (CNOT) gate.  One control qubit, one target qubit.",
    ),
    "cy": _gate(
        "cy", 1, num_controls=1,
        cats=[GateCategory.TWO_QUBIT, GateCategory.CLIFFORD],
        desc="Controlled-Y gate.  One control qubit, one target qubit.",
    ),
    "cz": _gate(
        "cz", 1, num_controls=1,
        cats=[GateCategory.TWO_QUBIT, GateCategory.CLIFFORD],
        desc="Controlled-Z gate.  One control qubit, one target qubit.",
    ),
    # ----- Measurement -----
    "measure": _gate(
        "measure", 1,
        cats=[GateCategory.MEASUREMENT],
        desc="Measure a qubit in the computational basis.",
    ),
    # ----- Directives -----
    "barrier": _gate(
        "barrier", 0,
        cats=[GateCategory.DIRECTIVE],
        desc="Barrier directive.  Prevents reordering across this point.",
        barrier=True,
    ),
}


def get_gate(name: str) -> Gate:
    """Retrieve a standard gate by name.

    Args:
        name: The canonical gate name (case-sensitive).

    Returns:
        The :class:`Gate` definition.

    Raises:
        :class:`~rqm_circuits.errors.GateDefinitionError`: If ``name`` is not
            in the standard registry.
    """
    try:
        return STANDARD_GATES[name]
    except KeyError as exc:
        raise GateDefinitionError(
            f"Unknown gate {name!r}.  "
            f"Available gates: {sorted(STANDARD_GATES)}"
        ) from exc
