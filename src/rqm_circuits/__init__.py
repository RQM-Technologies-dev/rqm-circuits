# __init__.py
"""rqm-circuits – canonical circuit-definition layer for the RQM stack.

This package defines the native circuit object model that sits between
low-level quaternion/math libraries (``rqm-core``) and higher-level compiler
and backend adapter layers.

Stack position
--------------
- ``rqm-core``       – quaternion/math foundation
- **``rqm-circuits``** – canonical circuit language / IR  ← you are here
- ``rqm-compiler``   – optimization and rewriting engine
- backend repos      – translation/execution bridges
- future hosted API  – circuit ingestion, analysis, optimization, export

Quick start
-----------
>>> from rqm_circuits import Circuit, make_instruction
>>> c = Circuit(num_qubits=2, name="bell")
>>> c.add(make_instruction("h", [0]))
>>> c.add(make_instruction("cx", [0, 1]))
>>> print(c.summary())

Public API
----------
All stable public symbols are re-exported from this top-level module.
"""

from __future__ import annotations

from rqm_circuits.circuit import Circuit
from rqm_circuits.errors import (
    CircuitValidationError,
    GateDefinitionError,
    InstructionError,
    RQMCircuitsError,
    SerializationError,
)
from rqm_circuits.gates import STANDARD_GATES, Gate, get_gate
from rqm_circuits.instructions import Instruction, make_instruction
from rqm_circuits.ir import (
    circuit_depth,
    filter_by_category,
    gate_counts,
    has_measurements,
    is_parametric,
    qubit_usage,
)
from rqm_circuits.params import Parameter
from rqm_circuits.registers import ClassicalBitRef, QubitRef
from rqm_circuits.schema import CIRCUIT_JSON_SCHEMA, CircuitPayload
from rqm_circuits.serialization import SCHEMA_VERSION
from rqm_circuits.types import GateCategory
from rqm_circuits.validators import validate_circuit, validate_instruction

__version__ = "0.1.0"

__all__ = [
    # Circuit
    "Circuit",
    # Instructions
    "Instruction",
    "make_instruction",
    # Gates
    "Gate",
    "get_gate",
    "STANDARD_GATES",
    # Parameters
    "Parameter",
    # Registers
    "QubitRef",
    "ClassicalBitRef",
    # Errors
    "RQMCircuitsError",
    "CircuitValidationError",
    "GateDefinitionError",
    "InstructionError",
    "SerializationError",
    # Validators
    "validate_circuit",
    "validate_instruction",
    # IR helpers
    "circuit_depth",
    "filter_by_category",
    "gate_counts",
    "has_measurements",
    "is_parametric",
    "qubit_usage",
    # Types
    "GateCategory",
    # Serialization
    "SCHEMA_VERSION",
    # Schema
    "CIRCUIT_JSON_SCHEMA",
    "CircuitPayload",
    # Version
    "__version__",
]
