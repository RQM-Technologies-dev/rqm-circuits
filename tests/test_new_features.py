"""Tests for new features: controlled-gate semantics, phaseshift/u1q gates,
parameter validation, measure clbit enforcement, and backward-compatible
deserialization of the legacy controlled-gate encoding."""

from __future__ import annotations

import json
import math

import pytest

from rqm_circuits import (
    Circuit,
    CircuitValidationError,
    InstructionError,
    Parameter,
    make_instruction,
)
from rqm_circuits.gates import get_gate
from rqm_circuits.instructions import Instruction
from rqm_circuits.registers import ClassicalBitRef, QubitRef

# --------------------------------------------------------------------------- #
# Bell circuit – new canonical controls+targets format
# --------------------------------------------------------------------------- #

class TestBellCircuitNewFormat:
    def _make_bell(self) -> Circuit:
        c = Circuit(num_qubits=2, name="bell")
        c.add(make_instruction("h", [0]))
        # cx: control=q0, target=q1
        c.add(make_instruction("cx", targets=[1], controls=[0]))
        return c

    def test_bell_circuit_construction(self):
        c = self._make_bell()
        assert len(c) == 2
        assert c.instructions[1].gate.name == "cx"

    def test_cx_instruction_has_one_control_one_target(self):
        c = self._make_bell()
        cx_instr = c.instructions[1]
        assert len(cx_instr.targets) == 1
        assert len(cx_instr.controls) == 1
        assert cx_instr.targets[0].index == 1
        assert cx_instr.controls[0].index == 0

    def test_bell_circuit_serializes_with_controls_field(self):
        c = self._make_bell()
        d = c.to_dict()
        cx_dict = d["instructions"][1]
        assert "controls" in cx_dict
        assert cx_dict["controls"][0]["index"] == 0
        assert cx_dict["targets"][0]["index"] == 1

    def test_bell_circuit_round_trip(self):
        c = self._make_bell()
        raw = c.to_json()
        restored = Circuit.from_json(raw)
        assert restored == c

    def test_bell_circuit_cx_gate_arity_is_one(self):
        c = self._make_bell()
        cx_instr = c.instructions[1]
        assert cx_instr.gate.arity == 1
        assert cx_instr.gate.num_controls == 1


# --------------------------------------------------------------------------- #
# GHZ circuit – new canonical controls+targets format
# --------------------------------------------------------------------------- #

class TestGHZCircuit:
    def _make_ghz(self, n: int = 3) -> Circuit:
        c = Circuit(num_qubits=n, name="ghz")
        c.add(make_instruction("h", [0]))
        for i in range(1, n):
            c.add(make_instruction("cx", targets=[i], controls=[0]))
        return c

    def test_ghz_circuit_construction(self):
        c = self._make_ghz(3)
        assert len(c) == 3  # 1 H + 2 CX

    def test_ghz_circuit_all_cx_have_correct_format(self):
        c = self._make_ghz(4)
        for instr in c.instructions[1:]:
            assert instr.gate.name == "cx"
            assert len(instr.controls) == 1
            assert len(instr.targets) == 1
            assert instr.controls[0].index == 0

    def test_ghz_circuit_round_trip(self):
        c = self._make_ghz(3)
        raw = c.to_json()
        restored = Circuit.from_json(raw)
        assert restored == c


# --------------------------------------------------------------------------- #
# Phaseshift gate
# --------------------------------------------------------------------------- #

class TestPhaseshiftGate:
    def test_phaseshift_in_standard_gates(self):
        gate = get_gate("phaseshift")
        assert gate.arity == 1
        assert gate.num_params == 1
        assert gate.param_names == ("angle",)

    def test_phaseshift_instruction_with_angle(self):
        instr = make_instruction("phaseshift", [0], params=[Parameter("angle", value=math.pi / 4)])
        assert instr.gate.name == "phaseshift"
        assert instr.params[0].name == "angle"
        assert instr.params[0].value == pytest.approx(math.pi / 4)

    def test_phaseshift_legacy_theta_normalized(self):
        instr = make_instruction("phaseshift", [0], params=[Parameter("theta", value=0.5)])
        assert instr.params[0].name == "angle"

    def test_phaseshift_legacy_phi_normalized(self):
        instr = make_instruction("phaseshift", [0], params=[Parameter("phi", value=0.5)])
        assert instr.params[0].name == "angle"

    def test_phaseshift_symbolic_angle(self):
        instr = make_instruction("phaseshift", [0], params=[Parameter("angle")])
        assert not instr.params[0].is_bound

    def test_phaseshift_wrong_param_name_raises(self):
        with pytest.raises(InstructionError, match="parameter"):
            make_instruction("phaseshift", [0], params=[Parameter("omega", value=1.0)])

    def test_phaseshift_round_trip(self):
        c = Circuit(num_qubits=1)
        c.add(make_instruction("phaseshift", [0], params=[Parameter("angle", value=0.7854)]))
        raw = c.to_json()
        restored = Circuit.from_json(raw)
        assert restored == c


# --------------------------------------------------------------------------- #
# u1q gate
# --------------------------------------------------------------------------- #

class TestU1QGate:
    def _make_u1q_instr(self) -> Instruction:
        norm = 1.0 / math.sqrt(2)
        return make_instruction(
            "u1q", [0],
            params=[
                Parameter("w", value=norm),
                Parameter("x", value=norm),
                Parameter("y", value=0.0),
                Parameter("z", value=0.0),
            ],
        )

    def test_u1q_in_standard_gates(self):
        gate = get_gate("u1q")
        assert gate.arity == 1
        assert gate.num_params == 4
        assert gate.param_names == ("w", "x", "y", "z")

    def test_u1q_instruction_construction(self):
        instr = self._make_u1q_instr()
        assert instr.gate.name == "u1q"
        assert len(instr.params) == 4

    def test_u1q_param_names_correct(self):
        instr = self._make_u1q_instr()
        assert [p.name for p in instr.params] == ["w", "x", "y", "z"]

    def test_u1q_wrong_param_name_raises(self):
        with pytest.raises(InstructionError, match="parameter"):
            make_instruction(
                "u1q", [0],
                params=[
                    Parameter("a", value=1.0),  # "a" not in ("w","x","y","z")
                    Parameter("x", value=0.0),
                    Parameter("y", value=0.0),
                    Parameter("z", value=0.0),
                ],
            )

    def test_u1q_round_trip_serialization(self):
        c = Circuit(num_qubits=1, name="u1q_circuit")
        c.add(self._make_u1q_instr())
        raw = c.to_json()
        restored = Circuit.from_json(raw)
        assert restored == c
        assert restored.instructions[0].gate.name == "u1q"
        assert [p.name for p in restored.instructions[0].params] == ["w", "x", "y", "z"]

    def test_u1q_gate_serialization_includes_param_names(self):
        instr = self._make_u1q_instr()
        d = instr.to_dict()
        assert d["gate"]["param_names"] == ["w", "x", "y", "z"]

    def test_u1q_missing_params_raises(self):
        with pytest.raises(InstructionError, match="parameter"):
            make_instruction("u1q", [0])  # needs 4 params


# --------------------------------------------------------------------------- #
# rx / ry / rz parameter name validation
# --------------------------------------------------------------------------- #

class TestRotationParamValidation:
    @pytest.mark.parametrize("gate_name", ["rx", "ry", "rz"])
    def test_canonical_angle_name_accepted(self, gate_name: str):
        instr = make_instruction(gate_name, [0], params=[Parameter("angle", value=1.0)])
        assert instr.params[0].name == "angle"

    @pytest.mark.parametrize("gate_name", ["rx", "ry", "rz"])
    def test_legacy_theta_normalized(self, gate_name: str):
        instr = make_instruction(gate_name, [0], params=[Parameter("theta", value=1.0)])
        assert instr.params[0].name == "angle"

    @pytest.mark.parametrize("gate_name", ["rx", "ry", "rz"])
    def test_legacy_phi_normalized(self, gate_name: str):
        instr = make_instruction(gate_name, [0], params=[Parameter("phi", value=0.5)])
        assert instr.params[0].name == "angle"

    @pytest.mark.parametrize("gate_name", ["rx", "ry", "rz"])
    def test_symbolic_angle_accepted(self, gate_name: str):
        instr = make_instruction(gate_name, [0], params=[Parameter("angle")])
        assert not instr.params[0].is_bound

    @pytest.mark.parametrize("gate_name", ["rx", "ry", "rz"])
    def test_wrong_name_raises(self, gate_name: str):
        with pytest.raises(InstructionError, match="parameter"):
            make_instruction(gate_name, [0], params=[Parameter("omega", value=1.0)])

    def test_normalized_legacy_param_round_trips_as_canonical(self):
        """After normalization, round-tripped circuits use the canonical 'angle' name."""
        c = Circuit(num_qubits=1)
        # Construct with legacy "theta" – gets normalized to "angle"
        c.add(make_instruction("rx", [0], params=[Parameter("theta", value=1.0)]))
        raw = c.to_json()
        data = json.loads(raw)
        param_name = data["instructions"][0]["params"][0]["name"]
        assert param_name == "angle"


# --------------------------------------------------------------------------- #
# Measure instruction clbit enforcement
# --------------------------------------------------------------------------- #

class TestMeasureClbitEnforcement:
    def test_measure_with_clbit_accepted(self):
        c = Circuit(num_qubits=1, num_clbits=1)
        c.add(make_instruction("measure", [0], clbits=[0]))
        assert len(c) == 1

    def test_measure_without_clbit_raises(self):
        c = Circuit(num_qubits=1, num_clbits=1)
        with pytest.raises(CircuitValidationError, match="classical bit"):
            c.add(make_instruction("measure", [0]))

    def test_measure_with_multiple_clbits_raises(self):
        """measure must have exactly one classical bit target."""
        c = Circuit(num_qubits=1, num_clbits=2)
        gate = get_gate("measure")
        instr = Instruction(
            gate=gate,
            targets=(QubitRef(0),),
            clbits=(ClassicalBitRef(0), ClassicalBitRef(1)),
        )
        with pytest.raises(CircuitValidationError, match="classical bit"):
            c.add(instr)

    def test_non_measure_gate_with_clbit_raises(self):
        c = Circuit(num_qubits=1, num_clbits=1)
        gate = get_gate("h")
        instr = Instruction(
            gate=gate,
            targets=(QubitRef(0),),
            clbits=(ClassicalBitRef(0),),
        )
        with pytest.raises(CircuitValidationError, match="classical bit"):
            c.add(instr)

    def test_full_measure_circuit_round_trip(self):
        c = Circuit(num_qubits=2, num_clbits=2, name="full_measure")
        c.add(make_instruction("h", [0]))
        c.add(make_instruction("cx", targets=[1], controls=[0]))
        c.add(make_instruction("measure", [0], clbits=[0]))
        c.add(make_instruction("measure", [1], clbits=[1]))
        raw = c.to_json()
        restored = Circuit.from_json(raw)
        assert restored == c


# --------------------------------------------------------------------------- #
# Backward-compatible deserialization of legacy controlled-gate format
# --------------------------------------------------------------------------- #

class TestLegacyControlledGateDeserialization:
    """Verify that schema-0.1 payloads with cx/cy/cz as arity=2 gates
    deserialize correctly into the new arity=1+controls format."""

    def _make_legacy_cx_payload(self, ctrl: int = 0, tgt: int = 1) -> dict:
        return {
            "schema_version": "0.1",
            "num_qubits": 2,
            "instructions": [
                {
                    "gate": {
                        "name": "cx",
                        "arity": 2,
                        "num_params": 0,
                        "categories": ["clifford", "two_qubit"],
                    },
                    "targets": [
                        {"index": ctrl, "type": "qubit"},
                        {"index": tgt, "type": "qubit"},
                    ],
                }
            ],
        }

    def test_legacy_cx_payload_deserializes(self):
        payload = self._make_legacy_cx_payload()
        c = Circuit.from_dict(payload)
        assert len(c.instructions) == 1
        instr = c.instructions[0]
        assert instr.gate.name == "cx"

    def test_legacy_cx_control_extracted_correctly(self):
        payload = self._make_legacy_cx_payload(ctrl=0, tgt=1)
        c = Circuit.from_dict(payload)
        instr = c.instructions[0]
        assert len(instr.controls) == 1
        assert len(instr.targets) == 1
        assert instr.controls[0].index == 0
        assert instr.targets[0].index == 1

    def test_legacy_cx_reversed_control_target(self):
        payload = self._make_legacy_cx_payload(ctrl=1, tgt=0)
        c = Circuit.from_dict(payload)
        instr = c.instructions[0]
        assert instr.controls[0].index == 1
        assert instr.targets[0].index == 0

    def test_legacy_cy_payload_deserializes(self):
        payload = {
            "schema_version": "0.1",
            "num_qubits": 2,
            "instructions": [
                {
                    "gate": {"name": "cy", "arity": 2, "num_params": 0, "categories": []},
                    "targets": [{"index": 0, "type": "qubit"}, {"index": 1, "type": "qubit"}],
                }
            ],
        }
        c = Circuit.from_dict(payload)
        instr = c.instructions[0]
        assert instr.gate.name == "cy"
        assert instr.controls[0].index == 0
        assert instr.targets[0].index == 1

    def test_legacy_from_json_round_trip(self):
        """Full round-trip: parse legacy JSON → new Circuit → serialize to 0.2 JSON."""
        payload = json.dumps(self._make_legacy_cx_payload())
        c = Circuit.from_json(payload)
        new_json = c.to_json()
        new_data = json.loads(new_json)
        # Re-serialized payload must use schema 0.2
        assert new_data["schema_version"] == "0.2"
        cx_instr = new_data["instructions"][0]
        # New format: controls field present
        assert "controls" in cx_instr
        assert cx_instr["controls"][0]["index"] == 0
        assert cx_instr["targets"][0]["index"] == 1
