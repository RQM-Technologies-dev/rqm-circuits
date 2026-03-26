"""Tests for JSON / dict serialization of Circuit, Instruction, Gate, and Parameter."""

from __future__ import annotations

import json

import pytest

from rqm_circuits import (
    SCHEMA_VERSION,
    Circuit,
    Parameter,
    SerializationError,
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
        # cx: control=0, target=1 (new canonical format)
        c.add(make_instruction("cx", targets=[1], controls=[0]))
        return c

    def test_to_dict_has_schema_version(self):
        c = Circuit(num_qubits=1)
        d = c.to_dict()
        assert d["schema_version"] == SCHEMA_VERSION

    def test_schema_version_is_0_2(self):
        assert SCHEMA_VERSION == "0.2"

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
        # Use canonical param name "angle" for rx
        instr = make_instruction("rx", [0], params=[Parameter("angle", value=1.5)])
        d = instr.to_dict()
        assert d["params"][0]["name"] == "angle"
        assert d["params"][0]["value"] == pytest.approx(1.5)

    def test_instruction_with_symbolic_param(self):
        # Use canonical param name "angle" for ry
        instr = make_instruction("ry", [0], params=[Parameter("angle")])
        d = instr.to_dict()
        assert d["params"][0]["name"] == "angle"
        assert "value" not in d["params"][0]

    def test_instruction_with_controls(self):
        from rqm_circuits.gates import get_gate
        from rqm_circuits.instructions import Instruction
        from rqm_circuits.registers import QubitRef

        gate = get_gate("x")
        instr = Instruction(
            gate=gate,
            targets=(QubitRef(1),),
            controls=(QubitRef(0),),
        )
        d = instr.to_dict()
        assert d["controls"][0]["index"] == 0
        assert d["targets"][0]["index"] == 1

    def test_cx_serializes_with_controls_field(self):
        """cx instruction must serialize with targets=[tgt] and controls=[ctrl]."""
        instr = make_instruction("cx", targets=[1], controls=[0])
        d = instr.to_dict()
        assert d["targets"] == [{"index": 1, "type": "qubit"}]
        assert d["controls"] == [{"index": 0, "type": "qubit"}]

    def test_instruction_round_trip(self):
        from rqm_circuits.instructions import Instruction
        # cx: control=0, target=1
        instr = make_instruction("cx", targets=[1], controls=[0])
        d = instr.to_dict()
        restored = Instruction.from_dict(d)
        assert restored.gate.name == "cx"
        assert len(restored.targets) == 1
        assert len(restored.controls) == 1

    def test_instruction_with_label(self):
        instr = make_instruction("h", [0], label="hadamard_on_q0")
        d = instr.to_dict()
        assert d["label"] == "hadamard_on_q0"

    def test_legacy_cx_format_normalized_on_deserialization(self):
        """Legacy schema 0.1 cx format (arity=2, 2 targets, no controls) is normalized."""
        from rqm_circuits.instructions import Instruction

        legacy_dict = {
            "gate": {"name": "cx", "arity": 2, "num_params": 0, "categories": []},
            "targets": [{"index": 0, "type": "qubit"}, {"index": 1, "type": "qubit"}],
        }
        instr = Instruction.from_dict(legacy_dict)
        assert instr.gate.name == "cx"
        assert len(instr.targets) == 1
        assert len(instr.controls) == 1
        assert instr.controls[0].index == 0
        assert instr.targets[0].index == 1


# --------------------------------------------------------------------------- #
# Parameter serialization
# --------------------------------------------------------------------------- #

class TestParameterSerialization:
    def test_concrete_to_dict(self):
        p = Parameter("angle", value=3.14)
        d = p.to_dict()
        assert d == {"name": "angle", "value": 3.14}

    def test_symbolic_to_dict(self):
        p = Parameter("angle")
        d = p.to_dict()
        assert d == {"name": "angle"}
        assert "value" not in d

    def test_round_trip_concrete(self):
        p = Parameter("angle", value=1.5707963267948966)
        d = p.to_dict()
        restored = Parameter.from_dict(d)
        assert restored == p

    def test_round_trip_symbolic(self):
        p = Parameter("angle")
        d = p.to_dict()
        restored = Parameter.from_dict(d)
        assert restored == p
        assert not restored.is_bound

    def test_from_dict_missing_name_raises(self):
        with pytest.raises(SerializationError):
            Parameter.from_dict({"value": 1.0})

    def test_from_dict_invalid_value_raises(self):
        with pytest.raises(SerializationError):
            Parameter.from_dict({"name": "angle", "value": "not_a_number"})


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

    def test_from_json_accepts_schema_0_1_legacy(self):
        """Schema 0.1 payloads are accepted (legacy compatibility)."""
        payload = json.dumps({
            "schema_version": "0.1",
            "num_qubits": 1,
            "instructions": [],
        })
        data = from_json(payload)
        assert data["num_qubits"] == 1

    def test_from_json_accepts_schema_0_2(self):
        payload = json.dumps({
            "schema_version": "0.2",
            "num_qubits": 1,
            "instructions": [],
        })
        data = from_json(payload)
        assert data["schema_version"] == "0.2"


# --------------------------------------------------------------------------- #
# Determinism tests
# --------------------------------------------------------------------------- #

class TestDeterministicSerialization:
    """Verify that to_json() produces identical output across repeated calls."""

    def _make_bell(self) -> Circuit:
        c = Circuit(num_qubits=2, name="bell")
        c.add(make_instruction("h", [0]))
        c.add(make_instruction("cx", targets=[1], controls=[0]))
        return c

    def test_to_json_identical_on_repeated_calls(self):
        c = self._make_bell()
        assert c.to_json() == c.to_json()

    def test_to_json_keys_sorted(self):
        c = self._make_bell()
        data = json.loads(c.to_json())
        top_level_keys = list(data.keys())
        assert top_level_keys == sorted(top_level_keys)

    def test_to_json_gate_keys_sorted(self):
        c = self._make_bell()
        data = json.loads(c.to_json())
        for instr in data["instructions"]:
            gate_keys = list(instr["gate"].keys())
            assert gate_keys == sorted(gate_keys)

    def test_two_identical_circuits_produce_identical_json(self):
        c1 = self._make_bell()
        c2 = self._make_bell()
        assert c1.to_json() == c2.to_json()

    def test_parametric_circuit_deterministic(self):
        c = Circuit(num_qubits=1, name="rotation")
        c.add(make_instruction("rx", [0], params=[Parameter("angle", value=1.5707963267948966)]))
        assert c.to_json() == c.to_json()

    def test_complex_circuit_round_trip_deterministic(self):
        c = Circuit(num_qubits=3, name="complex", num_clbits=2,
                    metadata={"author": "rqm", "version": 1})
        c.add(make_instruction("h", [0]))
        c.add(make_instruction("cx", targets=[1], controls=[0]))
        c.add(make_instruction("ry", [2], params=[Parameter("angle", value=0.5)]))
        c.add(make_instruction("measure", [0], clbits=[0]))
        c.add(make_instruction("measure", [1], clbits=[1]))
        raw = c.to_json()
        restored = Circuit.from_json(raw)
        assert restored == c
        # Round-trip JSON must also be identical.
        assert restored.to_json() == raw
