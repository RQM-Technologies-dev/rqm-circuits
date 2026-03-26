# instructions.py
"""Instruction model for rqm-circuits.

An :class:`Instruction` is the atomic unit of a quantum circuit: it binds a
:class:`~rqm_circuits.gates.Gate` definition to concrete qubit targets,
optional control qubits, parameters, and metadata.

Instructions are immutable value objects (frozen dataclasses).  This makes
them safe to store in ordered lists, compare for equality, and serialize
deterministically.

Architecture note
-----------------
Instructions do *not* hold a reference to the parent circuit.  Validation
that target indices fall within the circuit's qubit count is delegated to
:mod:`~rqm_circuits.validators`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rqm_circuits.errors import InstructionError, SerializationError
from rqm_circuits.gates import Gate, get_gate
from rqm_circuits.params import Parameter
from rqm_circuits.registers import ClassicalBitRef, QubitRef
from rqm_circuits.types import Metadata

# Legacy parameter names that are normalized to the canonical name for
# single-parameter rotation gates (rx, ry, rz, phaseshift).
_LEGACY_ANGLE_NAMES: frozenset[str] = frozenset({"theta", "phi"})


def _normalize_params(
    params: tuple[Parameter, ...],
    gate: Gate,
) -> tuple[Parameter, ...]:
    """Normalize legacy parameter names to canonical names.

    For single-parameter rotation gates (where ``gate.param_names == ("angle",)``),
    the names ``"theta"`` and ``"phi"`` are accepted as legacy aliases and
    silently renamed to ``"angle"``.

    Args:
        params: The parameter tuple to normalize.
        gate: The gate definition providing canonical param_names.

    Returns:
        A (possibly new) tuple of parameters with normalized names.
    """
    if not gate.param_names:
        return params
    normalized: list[Parameter] = []
    changed = False
    for i, param in enumerate(params):
        if i < len(gate.param_names):
            canonical = gate.param_names[i]
            is_legacy = param.name in _LEGACY_ANGLE_NAMES and canonical == "angle"
            if param.name != canonical and is_legacy:
                normalized.append(Parameter(name=canonical, value=param.value))
                changed = True
                continue
        normalized.append(param)
    return tuple(normalized) if changed else params


@dataclass(frozen=True)
class Instruction:
    """A gate application within a quantum circuit.

    Attributes:
        gate: The :class:`~rqm_circuits.gates.Gate` definition being applied.
        targets: Ordered list of target :class:`~rqm_circuits.registers.QubitRef`
            objects.  Length must equal ``gate.arity`` unless the gate is a
            barrier directive.
        controls: Optional list of control
            :class:`~rqm_circuits.registers.QubitRef` objects.  Length must
            equal ``gate.num_controls`` for gates that declare a non-zero
            ``num_controls``.  Must not overlap with ``targets``.
        params: Ordered list of :class:`~rqm_circuits.params.Parameter` objects.
            Length must equal ``gate.num_params``.  Parameter names are
            validated against ``gate.param_names`` when the gate declares them;
            legacy names (``"theta"``, ``"phi"``) are normalized to ``"angle"``
            for single-parameter rotation gates.
        clbits: Optional list of classical bit references used for measurement
            results.  Required for ``measure`` instructions; forbidden for all
            other gate instructions.
        label: Optional human-readable label for the instruction.
        metadata: Optional metadata mapping.

    Examples:
        >>> from rqm_circuits.gates import get_gate
        >>> from rqm_circuits.registers import QubitRef
        >>> h = get_gate("h")
        >>> instr = Instruction(gate=h, targets=[QubitRef(0)])
        >>> instr.gate.name
        'h'
        >>> cx = get_gate("cx")
        >>> bell = Instruction(gate=cx, targets=[QubitRef(1)], controls=[QubitRef(0)])
        >>> bell.gate.name
        'cx'
    """

    gate: Gate
    targets: tuple[QubitRef, ...]
    controls: tuple[QubitRef, ...] = field(default_factory=tuple)
    params: tuple[Parameter, ...] = field(default_factory=tuple)
    clbits: tuple[ClassicalBitRef, ...] = field(default_factory=tuple)
    label: str | None = None
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Coerce mutable sequences to tuples for immutability.
        object.__setattr__(self, "targets", tuple(self.targets))
        object.__setattr__(self, "controls", tuple(self.controls))
        object.__setattr__(self, "params", tuple(self.params))
        object.__setattr__(self, "clbits", tuple(self.clbits))
        # Freeze metadata too.
        object.__setattr__(self, "metadata", dict(self.metadata))
        # Normalize legacy parameter names before validation.
        object.__setattr__(self, "params", _normalize_params(self.params, self.gate))
        self._validate()

    def _validate(self) -> None:
        """Run structural self-validation.

        This only checks the internal consistency of the instruction itself,
        not whether the qubit indices fall within a specific circuit's qubit
        count (that is done in :mod:`~rqm_circuits.validators`).
        """
        gate = self.gate

        # Barrier is a special directive with variable target count.
        if not gate.allows_barrier and len(self.targets) != gate.arity:
            raise InstructionError(
                f"Gate '{gate.name}' has arity {gate.arity} but "
                f"{len(self.targets)} target(s) were supplied."
            )

        # Validate control qubit count for controlled gates.
        if gate.num_controls > 0 and len(self.controls) != gate.num_controls:
            raise InstructionError(
                f"Gate '{gate.name}' requires {gate.num_controls} control qubit(s) but "
                f"{len(self.controls)} were supplied."
            )

        if len(self.params) != gate.num_params:
            raise InstructionError(
                f"Gate '{gate.name}' expects {gate.num_params} parameter(s) but "
                f"{len(self.params)} were supplied."
            )

        # Validate parameter names against canonical param_names when declared.
        if gate.param_names:
            for i, (param, expected_name) in enumerate(
                zip(self.params, gate.param_names, strict=True)
            ):
                if param.name != expected_name:
                    raise InstructionError(
                        f"Gate '{gate.name}' expects parameter {i} to be named "
                        f"'{expected_name}', got '{param.name}'."
                    )

        # Duplicate targets are not allowed.
        seen_targets = set(q.index for q in self.targets)
        if len(seen_targets) != len(self.targets):
            raise InstructionError(
                f"Instruction targets contain duplicate qubit indices: "
                f"{[q.index for q in self.targets]}"
            )

        # Control/target overlap is not allowed.
        control_indices = {q.index for q in self.controls}
        if control_indices & seen_targets:
            overlap = sorted(control_indices & seen_targets)
            raise InstructionError(
                f"Control qubits {overlap} overlap with target qubits."
            )

        # Duplicate controls are not allowed.
        if len(control_indices) != len(self.controls):
            raise InstructionError(
                f"Instruction controls contain duplicate qubit indices: "
                f"{[q.index for q in self.controls]}"
            )

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible, deterministic dictionary.

        Returns:
            A fully serializable representation of this instruction.
        """
        d: dict[str, Any] = {
            "gate": self.gate.to_dict(),
            "targets": [q.to_dict() for q in self.targets],
        }
        if self.controls:
            d["controls"] = [q.to_dict() for q in self.controls]
        if self.params:
            d["params"] = [p.to_dict() for p in self.params]
        if self.clbits:
            d["clbits"] = [c.to_dict() for c in self.clbits]
        if self.label is not None:
            d["label"] = self.label
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Instruction:
        """Deserialize from a dictionary produced by :meth:`to_dict`.

        Supports backward-compatible deserialization of the legacy
        controlled-gate encoding.  In the legacy (schema 0.1) format, ``cx``,
        ``cy``, and ``cz`` were encoded as arity-2 gates with both the control
        and target in the ``targets`` list (first element = control).  This
        method detects and normalizes that format automatically.

        Legacy parameter name aliases (``"theta"`` / ``"phi"`` → ``"angle"``)
        for single-parameter rotation gates are also normalized here before the
        :class:`Instruction` object is constructed.

        Args:
            data: Dictionary representation of an instruction.

        Returns:
            An :class:`Instruction` instance.

        Raises:
            SerializationError: When required fields are missing or malformed.
            InstructionError: When the resulting instruction is structurally invalid.
        """
        for key in ("gate", "targets"):
            if key not in data:
                raise SerializationError(
                    f"Instruction dict is missing required field {key!r}: {data!r}"
                )

        # Resolve gate – prefer looking it up in the standard registry so that
        # the round-tripped object is the canonical singleton-like value.
        gate_data: dict[str, Any] = data["gate"]
        gate_name = gate_data.get("name", "")
        try:
            gate = get_gate(gate_name)
        except Exception:
            # Fall back to reconstructing a custom gate from the dict.
            gate = Gate.from_dict(gate_data)

        try:
            targets = tuple(QubitRef.from_dict(q) for q in data["targets"])
            controls = tuple(
                QubitRef.from_dict(q) for q in data.get("controls", [])
            )
            params = tuple(
                Parameter.from_dict(p) for p in data.get("params", [])
            )
            clbits = tuple(
                ClassicalBitRef.from_dict(c) for c in data.get("clbits", [])
            )
        except (SerializationError, ValueError, KeyError, TypeError) as exc:
            raise SerializationError(
                f"Failed to deserialize instruction fields: {exc}"
            ) from exc

        # ----------------------------------------------------------------- #
        # Backward-compatible normalization for controlled gates (schema 0.1)
        # ----------------------------------------------------------------- #
        # Old encoding for cx/cy/cz: arity=2 gate with both control and target
        # in the targets list (targets[0]=control, targets[1]=target).
        # New encoding: arity=1, num_controls=1, controls=[ctrl], targets=[tgt].
        if (
            gate.num_controls > 0
            and not controls
            and len(targets) == gate.arity + gate.num_controls
        ):
            controls = targets[: gate.num_controls]
            targets = targets[gate.num_controls :]

        return cls(
            gate=gate,
            targets=targets,
            controls=controls,
            params=params,
            clbits=clbits,
            label=data.get("label"),
            metadata=dict(data.get("metadata") or {}),
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @property
    def all_qubits(self) -> frozenset[int]:
        """Return the union of all qubit indices touched by this instruction."""
        return frozenset(
            q.index for q in (*self.targets, *self.controls)
        )

    def __repr__(self) -> str:
        targets = [q.index for q in self.targets]
        return (
            f"Instruction(gate={self.gate.name!r}, targets={targets}, "
            f"params={[p.name for p in self.params]})"
        )


# --------------------------------------------------------------------------- #
# Factory helpers
# --------------------------------------------------------------------------- #

def make_instruction(
    gate_name: str,
    targets: list[int],
    controls: list[int] | None = None,
    params: list[Parameter] | None = None,
    clbits: list[int] | None = None,
    label: str | None = None,
    metadata: Metadata | None = None,
) -> Instruction:
    """Convenience factory for building an :class:`Instruction` from primitives.

    Args:
        gate_name: Name of a gate in the standard registry.
        targets: List of target qubit indices.
        controls: Optional list of control qubit indices.  For controlled gates
            (``cx``, ``cy``, ``cz``), supply exactly one control index here.
        params: Optional list of :class:`~rqm_circuits.params.Parameter` objects.
        clbits: Optional list of classical bit indices.
        label: Optional label.
        metadata: Optional metadata mapping.

    Returns:
        A validated :class:`Instruction`.

    Raises:
        GateDefinitionError: When ``gate_name`` is not in the registry.
        InstructionError: When the instruction is structurally invalid.

    Examples:
        >>> from rqm_circuits.instructions import make_instruction
        >>> instr = make_instruction("h", targets=[0])
        >>> instr.gate.name
        'h'
        >>> # For controlled gates, supply controls separately:
        >>> instr = make_instruction("cx", targets=[1], controls=[0])
        >>> instr.gate.name
        'cx'
    """
    gate = get_gate(gate_name)
    return Instruction(
        gate=gate,
        targets=tuple(QubitRef(i) for i in targets),
        controls=tuple(QubitRef(i) for i in (controls or [])),
        params=tuple(params or []),
        clbits=tuple(ClassicalBitRef(i) for i in (clbits or [])),
        label=label,
        metadata=dict(metadata or {}),
    )
