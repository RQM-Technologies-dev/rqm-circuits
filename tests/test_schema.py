"""Tests for the Circuit JSON schema (Task 5 – FastAPI endpoint readiness)."""

from __future__ import annotations

import json

import pytest

from rqm_circuits import (
    CIRCUIT_JSON_SCHEMA,
    Circuit,
    CircuitPayload,
    Parameter,
    make_instruction,
)

# --------------------------------------------------------------------------- #
# Schema structure tests
# --------------------------------------------------------------------------- #

class TestCircuitJsonSchema:
    def test_schema_is_dict(self):
        assert isinstance(CIRCUIT_JSON_SCHEMA, dict)

    def test_schema_has_draft07(self):
        assert "$schema" in CIRCUIT_JSON_SCHEMA

    def test_schema_title(self):
        assert CIRCUIT_JSON_SCHEMA["title"] == "Circuit"

    def test_schema_required_fields(self):
        required = CIRCUIT_JSON_SCHEMA["required"]
        assert "schema_version" in required
        assert "num_qubits" in required
        assert "instructions" in required

    def test_schema_defines_instruction(self):
        assert "Instruction" in CIRCUIT_JSON_SCHEMA["$defs"]

    def test_schema_defines_gate(self):
        assert "Gate" in CIRCUIT_JSON_SCHEMA["$defs"]

    def test_schema_defines_qubit_ref(self):
        assert "QubitRef" in CIRCUIT_JSON_SCHEMA["$defs"]

    def test_schema_defines_classical_bit_ref(self):
        assert "ClassicalBitRef" in CIRCUIT_JSON_SCHEMA["$defs"]

    def test_schema_defines_parameter(self):
        assert "Parameter" in CIRCUIT_JSON_SCHEMA["$defs"]

    def test_schema_version_enum(self):
        """schema_version must be an enum containing at least "0.1"."""
        prop = CIRCUIT_JSON_SCHEMA["properties"]["schema_version"]
        assert "0.1" in prop["enum"]

    def test_num_qubits_minimum_zero(self):
        prop = CIRCUIT_JSON_SCHEMA["properties"]["num_qubits"]
        assert prop["minimum"] == 0

    def test_gate_categories_enum_values(self):
        cat_items = CIRCUIT_JSON_SCHEMA["$defs"]["Gate"]["properties"]["categories"]["items"]
        enum = cat_items["enum"]
        for expected in ("clifford", "rotation", "single_qubit", "two_qubit",
                         "measurement", "directive", "non_clifford"):
            assert expected in enum

    def test_schema_is_json_serializable(self):
        """The schema dict must itself be JSON-serialisable."""
        raw = json.dumps(CIRCUIT_JSON_SCHEMA, sort_keys=True)
        restored = json.loads(raw)
        assert restored["title"] == "Circuit"


# --------------------------------------------------------------------------- #
# Schema validates real circuit payloads
# --------------------------------------------------------------------------- #

class TestSchemaValidatesPayloads:
    """Use jsonschema (if available) to validate real circuit payloads.

    These tests are skipped gracefully if jsonschema is not installed,
    since it is an optional dev dependency.  They serve as integration
    tests for the schema definition itself.
    """

    @pytest.fixture(autouse=True)
    def skip_if_no_jsonschema(self):
        pytest.importorskip("jsonschema", reason="jsonschema not installed")

    def _validate(self, payload: dict) -> None:
        import jsonschema
        jsonschema.validate(instance=payload, schema=CIRCUIT_JSON_SCHEMA)

    def test_bell_circuit_validates(self):
        c = Circuit(num_qubits=2, name="bell")
        c.add(make_instruction("h", [0]))
        c.add(make_instruction("cx", [0, 1]))
        self._validate(c.to_dict())

    def test_empty_circuit_validates(self):
        c = Circuit(num_qubits=0)
        self._validate(c.to_dict())

    def test_parametric_circuit_validates(self):
        c = Circuit(num_qubits=1)
        c.add(make_instruction("rx", [0], params=[Parameter("theta", value=1.5)]))
        self._validate(c.to_dict())

    def test_symbolic_parameter_validates(self):
        c = Circuit(num_qubits=1)
        c.add(make_instruction("rz", [0], params=[Parameter("phi")]))
        self._validate(c.to_dict())

    def test_measurement_circuit_validates(self):
        c = Circuit(num_qubits=1, num_clbits=1)
        c.add(make_instruction("x", [0]))
        c.add(make_instruction("measure", [0], clbits=[0]))
        self._validate(c.to_dict())

    def test_metadata_circuit_validates(self):
        c = Circuit(num_qubits=2, name="meta", metadata={"author": "rqm"})
        c.add(make_instruction("h", [0]))
        self._validate(c.to_dict())

    def test_missing_schema_version_fails(self):
        import jsonschema
        payload = {
            "num_qubits": 1,
            "instructions": [],
        }
        with pytest.raises(jsonschema.ValidationError):
            self._validate(payload)

    def test_negative_num_qubits_fails(self):
        import jsonschema
        payload = {
            "schema_version": "0.1",
            "num_qubits": -1,
            "instructions": [],
        }
        with pytest.raises(jsonschema.ValidationError):
            self._validate(payload)

    def test_unknown_top_level_field_fails(self):
        import jsonschema
        payload = {
            "schema_version": "0.1",
            "num_qubits": 1,
            "instructions": [],
            "unknown_field": "value",
        }
        with pytest.raises(jsonschema.ValidationError):
            self._validate(payload)


# --------------------------------------------------------------------------- #
# TypedDict structural tests
# --------------------------------------------------------------------------- #

class TestCircuitPayloadTypedDict:
    def test_circuit_payload_is_typed_dict(self):
        from typing import get_type_hints
        hints = get_type_hints(CircuitPayload)
        assert "schema_version" in hints
        assert "num_qubits" in hints
        assert "instructions" in hints

    def test_circuit_payload_optional_name(self):
        from typing import get_type_hints
        hints = get_type_hints(CircuitPayload)
        assert "name" in hints

    def test_circuit_payload_optional_num_clbits(self):
        from typing import get_type_hints
        hints = get_type_hints(CircuitPayload)
        assert "num_clbits" in hints
