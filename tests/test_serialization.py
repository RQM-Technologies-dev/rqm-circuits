"""Tests for JSON / dict serialization of Circuit, Instruction, Gate, and Parameter."""

from __future__ import annotations

import json

import pytest

from rqm_circuits import (
    Circuit,
    Parameter,
    SerializationError,
    SCHEMA_VERSION,
    make_instruction,
)
from rqm_circuits.serialization import from_json, to_json


# --------------------------------------------------------------------------- #
# Circuit round-trip
# --------------------------------------------------------------------------- #

class TestCircuitRoundTrip:
    def _make_bell(self) -> Circuit:
        c = Circuit(num_qubits=2, name="bell")
        c.add(make_instruction("h", [0]))
        c.add(make_instruction("cx", [0, 1]))
        return c

    def test_to_dict_has_schema_version(self):
        c = Circuit(num_qubits=1)
        d = c.to_dict()
        assert d["schema_version"] == SCHEMA_VERSION

    def test_to_dict_num_qubits(self):
        c = Circuit(num_qubits=3)
        d = c.to_dict()
        assert d["num_qubits"] == 3

    def test_to_dict_name(self):
        c = Circuit(num_qubits=1, name="my_circuit")
        d = c.to_dict()
        assert d["name"] == "my_circuit"

    def test_to_dict_omits_empty_name(self):
        c = Circuit(num_qubits=1)
        d = c.to_dict()
        assert "name" not in d

    def test_to_dict_num_clbits(self):
        c = Circuit(num_qubits=2, num_clbits=2)
        d = c.to_dict()
        assert d["num_clbits"] == 2

    def test_to_dict_omits_none_clbits(self):
        c = Circuit(num_qubits=1)
        d = c.to_dict()
        assert "num_clbits" not in d

    def test_to_dict_instructions_count(self):
        c = self._make_bell()
        d = c.to_dict()
        assert len(d["instructions"]) == 2

    def test_from_dict_round_trip_empty(self):
        c = Circuit(num_qubits=2, name="empty")
        d = c.to_dict()
        restored = Circuit.from_dict(d)
        assert restored == c

    def test_from_dict_round_trip_bell(self):
        c = self._make_bell()
        d = c.to_dict()
        restored = Circuit.from_dict(d)
        assert restored == c

    def test_from_dict_round_trip_with_clbits(self):
        c = Circuit(num_qubits=1, num_clbits=1)
        c.add(make_instruction("x", [0]))
        c.add(make_instruction("measure", [0], clbits=[0]))
        d = c.to_dict()
        restored = Circuit.from_dict(d)
        assert restored == c

    def test_from_dict_missing_num_qubits_raises(self):
        with pytest.raises(SerializationError):
            Circuit.from_dict({"schema_version": SCHEMA_VERSION})

    def test_to_json_valid_json(self):
        c = self._make_bell()
        raw = c.to_json()
        data = json.loads(raw)
        assert data["num_qubits"] == 2

    def test_from_json_round_trip(self):
        c = self._make_bell()
        raw = c.to_json()
        restored = Circuit.from_json(raw)
        assert restored == c

    def test_from_json_invalid_raises(self):
        with pytest.raises(SerializationError):
            Circuit.from_json("not json at all {{{")

    def test_from_json_missing_schema_version_raises(self):
        bad = json.dumps({"num_qubits": 1, "instructions": []})
        with pytest.raises(SerializationError, match="schema_version"):
            Circuit.from_json(bad)

    def test_from_json_wrong_schema_version_raises(self):
        bad = json.dumps({
            "schema_version": "99.0",
            "num_qubits": 1,
            "instructions": [],
        })
        with pytest.raises(SerializationError, match="Unsupported schema version"):
            Circuit.from_json(bad)

    def test_metadata_round_trip(self):
        c = Circuit(num_qubits=1, metadata={"author": "rqm", "tags": ["test"]})
        raw = c.to_json()
        restored = Circuit.from_json(raw)
        assert restored.metadata == {"author": "rqm", "tags": ["test"]}


# --------------------------------------------------------------------------- #
# Instruction serialization
# --------------------------------------------------------------------------- #

class TestInstructionSerialization:
    def test_basic_instruction_dict(self):
        instr = make_instruction("h", [0])
        d = instr.to_dict()
        assert d["gate"]["name"] == "h"
        assert d["targets"][0]["index"] == 0

    def test_instruction_with_params_dict(self):
        instr = make_instruction("rx", [0], params=[Parameter("theta", value=1.5)])
        d = instr.to_dict()
        assert d["params"][0]["name"] == "theta"
        assert d["params"][0]["value"] == pytest.approx(1.5)

    def test_instruction_with_symbolic_param(self):
        instr = make_instruction("ry", [0], params=[Parameter("phi")])
        d = instr.to_dict()
        assert d["params"][0]["name"] == "phi"
        assert "value" not in d["params"][0]

    def test_instruction_with_controls(self):
        from rqm_circuits.instructions import Instruction
        from rqm_circuits.registers import QubitRef
        from rqm_circuits.gates import get_gate

        gate = get_gate("x")
        instr = Instruction(
            gate=gate,
            targets=(QubitRef(1),),
            controls=(QubitRef(0),),
        )
        d = instr.to_dict()
        assert d["controls"][0]["index"] == 0
        assert d["targets"][0]["index"] == 1

    def test_instruction_round_trip(self):
        from rqm_circuits.instructions import Instruction
        instr = make_instruction("cx", [0, 1])
        d = instr.to_dict()
        restored = Instruction.from_dict(d)
        assert restored.gate.name == "cx"
        assert len(restored.targets) == 2

    def test_instruction_with_label(self):
        instr = make_instruction("h", [0], label="hadamard_on_q0")
        d = instr.to_dict()
        assert d["label"] == "hadamard_on_q0"


# --------------------------------------------------------------------------- #
# Parameter serialization
# --------------------------------------------------------------------------- #

class TestParameterSerialization:
    def test_concrete_to_dict(self):
        p = Parameter("theta", value=3.14)
        d = p.to_dict()
        assert d == {"name": "theta", "value": 3.14}

    def test_symbolic_to_dict(self):
        p = Parameter("phi")
        d = p.to_dict()
        assert d == {"name": "phi"}
        assert "value" not in d

    def test_round_trip_concrete(self):
        p = Parameter("theta", value=1.5707963267948966)
        d = p.to_dict()
        restored = Parameter.from_dict(d)
        assert restored == p

    def test_round_trip_symbolic(self):
        p = Parameter("phi")
        d = p.to_dict()
        restored = Parameter.from_dict(d)
        assert restored == p
        assert not restored.is_bound

    def test_from_dict_missing_name_raises(self):
        with pytest.raises(SerializationError):
            Parameter.from_dict({"value": 1.0})

    def test_from_dict_invalid_value_raises(self):
        with pytest.raises(SerializationError):
            Parameter.from_dict({"name": "theta", "value": "not_a_number"})


# --------------------------------------------------------------------------- #
# Serialization module
# --------------------------------------------------------------------------- #

class TestSerializationModule:
    def test_to_json_and_from_json(self):
        c = Circuit(num_qubits=1, name="test")
        raw = to_json(c.to_dict())
        data = from_json(raw)
        assert data["num_qubits"] == 1

    def test_from_json_wrong_type_raises(self):
        with pytest.raises(SerializationError):
            from_json(json.dumps([1, 2, 3]))

    def test_to_json_non_serializable_raises(self):
        with pytest.raises(SerializationError):
            to_json({"key": object()})  # type: ignore[arg-type]
