# schema.py
"""Formal JSON schema for the rqm-circuits wire format.

This module defines the canonical JSON schema for the ``Circuit`` payload
as a machine-readable Python dictionary (JSON Schema draft-07 / OpenAPI 3.1
compatible) and as a set of :class:`typing.TypedDict` classes that can be
used directly as FastAPI / Pydantic model annotations.

Design intent
-------------
A future hosted REST API will accept ``Circuit.to_json()`` payloads, validate
them against this schema, and pass the parsed circuit to the compiler or
backend layer.  Keeping the schema co-located with the circuit definition
ensures it stays in sync with the serialisation code.

Usage
-----
::

    from rqm_circuits.schema import CIRCUIT_JSON_SCHEMA, CircuitPayload

    # FastAPI endpoint (requires ``pip install fastapi pydantic``)
    #
    # from fastapi import FastAPI
    # from pydantic import TypeAdapter
    #
    # app = FastAPI()
    #
    # @app.post("/circuits/validate")
    # def validate(payload: dict) -> dict:
    #     ta = TypeAdapter(CircuitPayload)
    #     circuit_data = ta.validate_python(payload)
    #     return circuit_data

    # Validate a dict payload using the JSON Schema directly:
    #
    # import jsonschema
    # jsonschema.validate(instance=payload, schema=CIRCUIT_JSON_SCHEMA)
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# TypedDict definitions (FastAPI / Pydantic compatible)
# --------------------------------------------------------------------------- #
# NOTE: TypedDicts are used instead of dataclasses here so that FastAPI can
#       reflect the schema automatically via Pydantic v2's TypeAdapter without
#       requiring rqm-circuits to declare a hard dependency on Pydantic.
from typing import Any, TypedDict


class QubitRefPayload(TypedDict, total=False):
    """JSON representation of a qubit register reference."""

    index: int  # required
    type: str   # "qubit" (optional, informational)


class ClassicalBitRefPayload(TypedDict, total=False):
    """JSON representation of a classical bit register reference."""

    index: int  # required
    type: str   # "clbit" (optional, informational)


class ParameterPayload(TypedDict, total=False):
    """JSON representation of a gate parameter."""

    name: str    # required – symbolic name
    value: float  # optional – omitted for unbound/symbolic parameters


class GatePayload(TypedDict, total=False):
    """JSON representation of a gate definition."""

    name: str        # required
    arity: int       # required
    num_params: int  # optional, default 0
    categories: list[str]   # optional
    description: str        # optional
    quaternion_form: str    # optional


class InstructionPayload(TypedDict, total=False):
    """JSON representation of a single circuit instruction."""

    gate: GatePayload       # required
    targets: list[QubitRefPayload]  # required
    controls: list[QubitRefPayload]  # optional
    params: list[ParameterPayload]   # optional
    clbits: list[ClassicalBitRefPayload]  # optional
    label: str    # optional
    metadata: dict[str, Any]  # optional


class CircuitPayload(TypedDict, total=False):
    """Top-level JSON payload for a circuit.

    Suitable for use as a FastAPI request body type or for ``jsonschema``
    validation.  All required fields are marked accordingly in
    :data:`CIRCUIT_JSON_SCHEMA`.
    """

    schema_version: str          # required – e.g. "0.1"
    num_qubits: int              # required
    instructions: list[InstructionPayload]  # required (may be empty)
    name: str                    # optional
    num_clbits: int              # optional
    metadata: dict[str, Any]     # optional


# --------------------------------------------------------------------------- #
# Machine-readable JSON Schema (draft-07 / OpenAPI 3.1 compatible)
# --------------------------------------------------------------------------- #

#: JSON Schema for the ``Circuit`` wire format.
#:
#: This schema is designed to be used as the ``requestBody`` schema for a
#: future FastAPI endpoint that accepts circuit payloads.
CIRCUIT_JSON_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Circuit",
    "description": (
        "Canonical rqm-circuits circuit payload.  "
        "Accepted by the RQM Technologies circuit ingestion API."
    ),
    "type": "object",
    "required": ["schema_version", "num_qubits", "instructions"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {
            "type": "string",
            "description": "Schema version string.  Must be '0.1' for this release.",
            "enum": ["0.1"],
            "examples": ["0.1"],
        },
        "num_qubits": {
            "type": "integer",
            "minimum": 0,
            "description": "Total number of qubits in the circuit.",
            "examples": [2],
        },
        "name": {
            "type": "string",
            "description": "Optional human-readable circuit name.",
            "examples": ["bell"],
        },
        "num_clbits": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of classical bits (omit if no measurement register).",
            "examples": [1],
        },
        "metadata": {
            "type": "object",
            "description": "Free-form JSON-serialisable metadata.",
            "additionalProperties": True,
        },
        "instructions": {
            "type": "array",
            "description": "Ordered list of gate instructions.",
            "items": {
                "$ref": "#/$defs/Instruction",
            },
        },
    },
    "$defs": {
        "QubitRef": {
            "title": "QubitRef",
            "description": "A reference to a single qubit by its 0-based index.",
            "type": "object",
            "required": ["index"],
            "additionalProperties": False,
            "properties": {
                "index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "0-based qubit index within the circuit.",
                    "examples": [0],
                },
                "type": {
                    "type": "string",
                    "const": "qubit",
                    "description": "Discriminator field; always 'qubit'.",
                },
            },
        },
        "ClassicalBitRef": {
            "title": "ClassicalBitRef",
            "description": "A reference to a single classical bit by its 0-based index.",
            "type": "object",
            "required": ["index"],
            "additionalProperties": False,
            "properties": {
                "index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "0-based classical bit index within the circuit.",
                    "examples": [0],
                },
                "type": {
                    "type": "string",
                    "const": "clbit",
                    "description": "Discriminator field; always 'clbit'.",
                },
            },
        },
        "Parameter": {
            "title": "Parameter",
            "description": (
                "A gate parameter.  May be concrete (value present) or "
                "symbolic (value absent, name used as a placeholder)."
            ),
            "type": "object",
            "required": ["name"],
            "additionalProperties": False,
            "properties": {
                "name": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Parameter name (e.g. 'theta', 'phi').",
                    "examples": ["theta"],
                },
                "value": {
                    "type": "number",
                    "description": "Concrete numeric value (radians for angle params).",
                    "examples": [1.5707963267948966],
                },
            },
        },
        "Gate": {
            "title": "Gate",
            "description": "A gate definition embedded in an instruction.",
            "type": "object",
            "required": ["name", "arity"],
            "additionalProperties": False,
            "properties": {
                "name": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Canonical gate name (e.g. 'h', 'cx', 'rx').",
                    "examples": ["h", "cx", "rx"],
                },
                "arity": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Number of target qubits.",
                    "examples": [1, 2],
                },
                "num_params": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                    "description": "Number of numeric/symbolic parameters.",
                    "examples": [0, 1],
                },
                "categories": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "clifford",
                            "directive",
                            "measurement",
                            "non_clifford",
                            "rotation",
                            "single_qubit",
                            "two_qubit",
                        ],
                    },
                    "description": "Category tags for downstream filtering.",
                    "examples": [["clifford", "single_qubit"]],
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable gate description.",
                },
                "quaternion_form": {
                    "type": "string",
                    "description": (
                        "Unit-quaternion representation of the gate "
                        "(informational; single-qubit gates only)."
                    ),
                    "examples": ["q = (i+k)/√2  (axis = (x̂+ẑ)/√2, angle = π)"],
                },
            },
        },
        "Instruction": {
            "title": "Instruction",
            "description": "A single gate application within a circuit.",
            "type": "object",
            "required": ["gate", "targets"],
            "additionalProperties": False,
            "properties": {
                "gate": {
                    "$ref": "#/$defs/Gate",
                    "description": "The gate being applied.",
                },
                "targets": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/QubitRef"},
                    "description": "Ordered list of target qubits.",
                    "examples": [[{"index": 0, "type": "qubit"}]],
                },
                "controls": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/QubitRef"},
                    "description": "Optional control qubits (must not overlap with targets).",
                    "default": [],
                },
                "params": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/Parameter"},
                    "description": (
                        "Gate parameters.  Length must equal gate.num_params."
                    ),
                    "default": [],
                },
                "clbits": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/ClassicalBitRef"},
                    "description": (
                        "Classical bit targets (required for measure instructions)."
                    ),
                    "default": [],
                },
                "label": {
                    "type": "string",
                    "description": "Optional human-readable label for this instruction.",
                },
                "metadata": {
                    "type": "object",
                    "description": "Free-form JSON-serialisable metadata.",
                    "additionalProperties": True,
                },
            },
        },
    },
}
