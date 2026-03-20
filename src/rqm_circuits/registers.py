# registers.py
"""Qubit and classical bit reference types for rqm-circuits.

These lightweight reference objects are used within
:class:`~rqm_circuits.instructions.Instruction` to address individual qubits
and classical bits in a circuit.

Design notes
------------
References are index-based and circuit-agnostic; validation that the referenced
index actually exists within a particular circuit is the responsibility of the
:mod:`~rqm_circuits.validators` module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rqm_circuits.errors import SerializationError
from rqm_circuits.types import ClassicalBitIndex, QubitIndex


@dataclass(frozen=True)
class QubitRef:
    """A reference to a single qubit by its 0-based index.

    Attributes:
        index: 0-based qubit index within the parent circuit.

    Examples:
        >>> q0 = QubitRef(0)
        >>> q1 = QubitRef(1)
        >>> q0 < q1
        True
    """

    index: QubitIndex

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError(
                f"QubitRef index must be ≥ 0, got {self.index}."
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {"index": self.index, "type": "qubit"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QubitRef:
        """Deserialize from a dictionary produced by :meth:`to_dict`.

        Args:
            data: Dictionary with an ``"index"`` key.

        Raises:
            SerializationError: When required fields are missing or invalid.
        """
        if "index" not in data:
            raise SerializationError(
                f"QubitRef dict is missing required field 'index': {data!r}"
            )
        idx = data["index"]
        if not isinstance(idx, int) or idx < 0:
            raise SerializationError(
                f"QubitRef 'index' must be a non-negative integer, got {idx!r}."
            )
        return cls(index=idx)

    def __lt__(self, other: QubitRef) -> bool:
        return self.index < other.index

    def __repr__(self) -> str:
        return f"QubitRef({self.index})"


@dataclass(frozen=True)
class ClassicalBitRef:
    """A reference to a single classical bit by its 0-based index.

    Attributes:
        index: 0-based classical bit index within the parent circuit.

    Examples:
        >>> c0 = ClassicalBitRef(0)
        >>> c0.index
        0
    """

    index: ClassicalBitIndex

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError(
                f"ClassicalBitRef index must be ≥ 0, got {self.index}."
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {"index": self.index, "type": "clbit"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClassicalBitRef:
        """Deserialize from a dictionary produced by :meth:`to_dict`.

        Args:
            data: Dictionary with an ``"index"`` key.

        Raises:
            SerializationError: When required fields are missing or invalid.
        """
        if "index" not in data:
            raise SerializationError(
                f"ClassicalBitRef dict is missing required field 'index': {data!r}"
            )
        idx = data["index"]
        if not isinstance(idx, int) or idx < 0:
            raise SerializationError(
                f"ClassicalBitRef 'index' must be a non-negative integer, got {idx!r}."
            )
        return cls(index=idx)

    def __lt__(self, other: ClassicalBitRef) -> bool:
        return self.index < other.index

    def __repr__(self) -> str:
        return f"ClassicalBitRef({self.index})"
