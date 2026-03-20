# types.py
"""Shared type aliases and lightweight enumerations for rqm-circuits.

Keeping these in one place makes it easy to re-use them across the package
and to maintain a stable public contract for downstream tooling.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

# --------------------------------------------------------------------------- #
# Primitive aliases
# --------------------------------------------------------------------------- #

#: A qubit index within a circuit (0-based).
QubitIndex = int

#: A classical bit index within a circuit (0-based).
ClassicalBitIndex = int

#: Generic metadata container – any JSON-serializable mapping.
Metadata = dict[str, Any]


# --------------------------------------------------------------------------- #
# Enumerations
# --------------------------------------------------------------------------- #


class GateCategory(str, Enum):
    """Broad category tags used to classify gate types.

    These are informational and not enforced by the validation layer.
    They are included in the JSON representation to help downstream tools
    (compiler passes, visualizers) quickly filter gate sets.
    """

    SINGLE_QUBIT = "single_qubit"
    TWO_QUBIT = "two_qubit"
    ROTATION = "rotation"
    CLIFFORD = "clifford"
    NON_CLIFFORD = "non_clifford"
    MEASUREMENT = "measurement"
    DIRECTIVE = "directive"
