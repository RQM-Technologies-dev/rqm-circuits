# circuit.py
"""Core circuit object for rqm-circuits.

The :class:`Circuit` class is the primary data structure of this package.  It
represents a quantum program as an ordered list of
:class:`~rqm_circuits.instructions.Instruction` objects applied to a fixed
number of qubits and optional classical bits.

Architecture position
---------------------
``rqm-circuits`` is the *canonical IR* layer of the RQM stack:

- ``rqm-core`` – quaternion/math foundation
- **``rqm-circuits``** – canonical circuit language / IR  ← you are here
- ``rqm-compiler`` – optimization and rewriting engine
- backend repos (``rqm-qiskit``, ``rqm-braket``, …) – translation/execution
- future hosted API – circuit ingestion, analysis, optimization, export

The :class:`Circuit` is designed to be easy to accept from REST requests,
validate, analyze, and pass downstream without hidden state or magic behaviour.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from rqm_circuits.errors import CircuitValidationError, SerializationError
from rqm_circuits.instructions import Instruction
from rqm_circuits.serialization import SCHEMA_VERSION, from_json, to_json
from rqm_circuits.types import Metadata
from rqm_circuits.validators import validate_circuit


@dataclass
class Circuit:
    """A quantum circuit: a named, validated, ordered sequence of instructions.

    Attributes:
        num_qubits: Total number of qubits in the circuit.  Must be ≥ 0.
        name: Optional human-readable name.
        num_clbits: Optional number of classical bits.  Defaults to ``None``
            (no classical register).
        instructions: Ordered list of :class:`~rqm_circuits.instructions.Instruction`
            objects.
        metadata: Optional free-form metadata mapping.

    Examples:
        >>> from rqm_circuits.circuit import Circuit
        >>> from rqm_circuits.instructions import make_instruction
        >>> c = Circuit(num_qubits=2, name="bell")
        >>> c.add(make_instruction("h", [0]))
        >>> c.add(make_instruction("cx", [0, 1]))
        >>> print(c.summary())
        Circuit 'bell': 2 qubits, 0 clbits, 2 instructions
          [0] h  q[0]
          [1] cx q[0], q[1]
    """

    num_qubits: int
    name: str = ""
    num_clbits: int | None = None
    instructions: list[Instruction] = field(default_factory=list)
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.num_qubits < 0:
            raise CircuitValidationError(
                f"num_qubits must be ≥ 0, got {self.num_qubits}."
            )
        if self.num_clbits is not None and self.num_clbits < 0:
            raise CircuitValidationError(
                f"num_clbits must be ≥ 0, got {self.num_clbits}."
            )

    # ------------------------------------------------------------------ #
    # Mutation helpers
    # ------------------------------------------------------------------ #

    def add(self, instruction: Instruction) -> Circuit:
        """Append a single instruction and validate it against the circuit.

        Args:
            instruction: The instruction to append.

        Returns:
            ``self`` (for method chaining).

        Raises:
            CircuitValidationError: When the instruction references qubit or
                classical bit indices outside the circuit's registered counts.

        Examples:
            >>> c = Circuit(num_qubits=1)
            >>> c.add(make_instruction("x", [0]))
            Circuit(num_qubits=1, ...)
        """
        from rqm_circuits.validators import validate_instruction

        validate_instruction(
            instruction,
            self.num_qubits,
            self.num_clbits or 0,
        )
        self.instructions.append(instruction)
        return self

    def append(self, instruction: Instruction) -> Circuit:
        """Alias for :meth:`add`.

        Provided for API symmetry with other quantum frameworks.
        """
        return self.add(instruction)

    def extend(self, instructions: list[Instruction]) -> Circuit:
        """Append multiple instructions in order.

        Args:
            instructions: Iterable of instructions to append.

        Returns:
            ``self`` (for method chaining).
        """
        for instr in instructions:
            self.add(instr)
        return self

    # ------------------------------------------------------------------ #
    # Copy
    # ------------------------------------------------------------------ #

    def copy(self) -> Circuit:
        """Return a deep copy of this circuit.

        Returns:
            A new :class:`Circuit` instance with independent instruction list.
        """
        return copy.deepcopy(self)

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    def validate(self) -> None:
        """Run full structural validation over the circuit.

        Raises:
            CircuitValidationError: On the first violation found.
        """
        validate_circuit(self)

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a deterministic, JSON-compatible dictionary.

        The schema includes a ``"schema_version"`` field for forward-compat
        checking on deserialization.

        Returns:
            A JSON-serializable dictionary.
        """
        d: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "num_qubits": self.num_qubits,
            "instructions": [instr.to_dict() for instr in self.instructions],
        }
        if self.name:
            d["name"] = self.name
        if self.num_clbits is not None:
            d["num_clbits"] = self.num_clbits
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Circuit:
        """Deserialize from a dictionary produced by :meth:`to_dict`.

        Args:
            data: Dictionary representation of a circuit.

        Returns:
            A :class:`Circuit` instance.

        Raises:
            SerializationError: When required fields are missing or malformed.
        """
        for key in ("num_qubits",):
            if key not in data:
                raise SerializationError(
                    f"Circuit dict is missing required field {key!r}: {data!r}"
                )
        try:
            instructions = [
                Instruction.from_dict(i) for i in data.get("instructions", [])
            ]
        except Exception as exc:
            raise SerializationError(
                f"Failed to deserialize circuit instructions: {exc}"
            ) from exc

        num_clbits = data.get("num_clbits")
        return cls(
            num_qubits=int(data["num_qubits"]),
            name=str(data.get("name", "")),
            num_clbits=int(num_clbits) if num_clbits is not None else None,
            instructions=instructions,
            metadata=dict(data.get("metadata") or {}),
        )

    def to_json(self, *, indent: int = 2) -> str:
        """Serialize to a JSON string.

        Args:
            indent: Indentation level for human readability.

        Returns:
            A deterministic JSON string.
        """
        return to_json(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, raw: str) -> Circuit:
        """Deserialize from a JSON string produced by :meth:`to_json`.

        Args:
            raw: JSON string.

        Returns:
            A :class:`Circuit` instance.

        Raises:
            SerializationError: When the JSON is invalid or schema version
                is unsupported.
        """
        data = from_json(raw)
        return cls.from_dict(data)

    # ------------------------------------------------------------------ #
    # Inspection
    # ------------------------------------------------------------------ #

    def summary(self) -> str:
        """Return a concise human-readable summary of the circuit.

        Returns:
            A multi-line string describing the circuit structure.
        """
        num_clbits = self.num_clbits if self.num_clbits is not None else 0
        header = (
            f"Circuit {self.name!r}: {self.num_qubits} qubit(s), "
            f"{num_clbits} clbit(s), "
            f"{len(self.instructions)} instruction(s)"
        )
        lines = [header]
        for idx, instr in enumerate(self.instructions):
            targets_str = ", ".join(f"q[{q.index}]" for q in instr.targets)
            controls_str = (
                " ctrl:" + ",".join(f"q[{q.index}]" for q in instr.controls)
                if instr.controls
                else ""
            )
            params_str = (
                "(" + ", ".join(
                    str(p.value) if p.is_bound else p.name
                    for p in instr.params
                ) + ")"
                if instr.params
                else ""
            )
            label_str = f" [{instr.label}]" if instr.label else ""
            lines.append(
                f"  [{idx:3d}] {instr.gate.name}{params_str}{controls_str}"
                f"  {targets_str}{label_str}"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Dunder helpers
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self.instructions)

    def __repr__(self) -> str:
        return (
            f"Circuit(name={self.name!r}, num_qubits={self.num_qubits}, "
            f"num_clbits={self.num_clbits!r}, "
            f"num_instructions={len(self.instructions)})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Circuit):
            return NotImplemented
        return (
            self.num_qubits == other.num_qubits
            and self.name == other.name
            and self.num_clbits == other.num_clbits
            and self.instructions == other.instructions
            and self.metadata == other.metadata
        )
