# params.py
"""Parameter model for rqm-circuits.

Supports both concrete numeric parameters and symbolic (named) parameters.
The design is intentionally minimal – we do not implement a full symbolic
algebra engine.  Parameters serialize cleanly to JSON and round-trip without
loss of information.

Architecture note
-----------------
``rqm-circuits`` acts as the IR boundary for the RQM stack.  Gate parameters
must remain expressible both as concrete floats (for simulation / immediate
execution) and as symbolic names (for later binding by a compiler pass or a
hosted API call).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from rqm_circuits.errors import SerializationError


@dataclass(frozen=True)
class Parameter:
    """A gate parameter that may be concrete or symbolic.

    Attributes:
        name: Human-readable parameter name (e.g. ``"theta"``).
              Required even for numeric parameters so that documentation and
              error messages remain informative.
        value: Concrete numeric value.  ``None`` indicates a free / symbolic
               parameter that has not yet been bound.

    Examples:
        >>> # Concrete parameter
        >>> p = Parameter(name="theta", value=1.5707963267948966)
        >>> p.is_bound
        True
        >>> p.as_float()
        1.5707963267948966

        >>> # Symbolic parameter
        >>> s = Parameter(name="phi")
        >>> s.is_bound
        False
    """

    name: str
    value: float | None = field(default=None)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Parameter name must be a non-empty string.")

    # ------------------------------------------------------------------ #
    # Convenience
    # ------------------------------------------------------------------ #

    @property
    def is_bound(self) -> bool:
        """Return ``True`` if this parameter has a concrete numeric value."""
        return self.value is not None

    def as_float(self) -> float:
        """Return the concrete value or raise ``ValueError`` if symbolic.

        Raises:
            ValueError: When the parameter has not been bound to a value.
        """
        if self.value is None:
            raise ValueError(f"Parameter '{self.name}' is symbolic and has no concrete value.")
        return self.value

    def bind(self, value: float) -> Parameter:
        """Return a new :class:`Parameter` with the given value bound.

        Args:
            value: The numeric value to assign.

        Returns:
            A new :class:`Parameter` instance with ``value`` set.
        """
        return Parameter(name=self.name, value=value)

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary.

        Returns:
            A dictionary with keys ``"name"`` and optionally ``"value"``.
        """
        d: dict[str, Any] = {"name": self.name}
        if self.value is not None:
            d["value"] = self.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Parameter:
        """Deserialize from a dictionary produced by :meth:`to_dict`.

        Args:
            data: Dictionary with at least a ``"name"`` key.

        Returns:
            A :class:`Parameter` instance.

        Raises:
            SerializationError: When required fields are missing or malformed.
        """
        try:
            name = data["name"]
        except KeyError as exc:
            raise SerializationError(
                f"Parameter dict is missing required field 'name': {data!r}"
            ) from exc
        if not isinstance(name, str):
            raise SerializationError(
                f"Parameter 'name' must be a string, got {type(name).__name__!r}."
            )
        value = data.get("value")
        if value is not None and not isinstance(value, (int, float)):
            raise SerializationError(
                f"Parameter 'value' must be numeric, got {type(value).__name__!r}."
            )
        return cls(name=name, value=float(value) if value is not None else None)

    # ------------------------------------------------------------------ #
    # Dunder helpers
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        if self.value is not None:
            return f"Parameter(name={self.name!r}, value={self.value!r})"
        return f"Parameter(name={self.name!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Parameter):
            return NotImplemented
        if self.name != other.name:
            return False
        # Compare float values with tolerance to handle floating-point drift.
        if self.value is None and other.value is None:
            return True
        if self.value is None or other.value is None:
            return False
        return math.isclose(self.value, other.value, rel_tol=1e-9, abs_tol=1e-12)

    def __hash__(self) -> int:
        return hash((self.name, self.value))
