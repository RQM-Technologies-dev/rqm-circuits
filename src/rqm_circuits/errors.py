# errors.py
"""Custom exceptions for rqm-circuits.

All exceptions are designed to carry structured, human-readable information
suitable for surfacing through a future REST API.
"""

from __future__ import annotations


class RQMCircuitsError(Exception):
    """Base exception for all rqm-circuits errors."""


class CircuitValidationError(RQMCircuitsError):
    """Raised when a circuit fails structural or semantic validation.

    Examples:
        - Instruction targets qubit indices outside the circuit's qubit count.
        - Duplicate target qubits within a single instruction.
        - Control and target qubit conflict.
    """


class GateDefinitionError(RQMCircuitsError):
    """Raised when a gate definition is invalid or incomplete.

    Examples:
        - Gate with negative arity.
        - Required parameter schema is missing.
    """


class InstructionError(RQMCircuitsError):
    """Raised when an instruction is malformed or incompatible with its gate.

    Examples:
        - Wrong number of parameters supplied.
        - Targets list length does not match gate arity.
    """


class SerializationError(RQMCircuitsError):
    """Raised when serialization or deserialization fails.

    Examples:
        - JSON payload is missing required fields.
        - Round-trip produces a structurally different circuit.
    """
