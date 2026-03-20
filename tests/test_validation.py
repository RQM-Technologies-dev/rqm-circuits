"""Tests for validation rules."""

from __future__ import annotations

import pytest

from rqm_circuits import (
    Circuit,
    CircuitValidationError,
    InstructionError,
    Parameter,
    make_instruction,
    validate_circuit,
)
from rqm_circuits.gates import get_gate
from rqm_circuits.instructions import Instruction
from rqm_circuits.registers import QubitRef

# --------------------------------------------------------------------------- #
# Qubit index validation
# --------------------------------------------------------------------------- #

class TestQubitIndexValidation:
    def test_valid_qubit_accepted(self):
        c = Circuit(num_qubits=3)
        c.add(make_instruction("x", [2]))  # qubit 2 is valid

    def test_out_of_range_qubit_rejected(self):
        c = Circuit(num_qubits=2)
        with pytest.raises(CircuitValidationError, match="qubit index"):
            c.add(make_instruction("x", [2]))  # only 0,1 valid

    def test_control_out_of_range_rejected(self):
        c = Circuit(num_qubits=2)
        gate = get_gate("x")
        instr = Instruction(
            gate=gate,
            targets=(QubitRef(1),),
            controls=(QubitRef(5),),  # 5 is out of range
        )
        with pytest.raises(CircuitValidationError, match="qubit index"):
            c.add(instr)

    def test_zero_qubit_circuit_rejects_any_instruction(self):
        c = Circuit(num_qubits=0)
        with pytest.raises(CircuitValidationError):
            c.add(make_instruction("x", [0]))


# --------------------------------------------------------------------------- #
# Duplicate target validation
# --------------------------------------------------------------------------- #

class TestDuplicateTargets:
    def test_duplicate_targets_rejected(self):
        """A gate with two target qubits should reject duplicate indices."""
        gate = get_gate("cx")
        with pytest.raises(InstructionError, match="duplicate"):
            Instruction(gate=gate, targets=(QubitRef(0), QubitRef(0)))


# --------------------------------------------------------------------------- #
# Control/target conflict
# --------------------------------------------------------------------------- #

class TestControlTargetConflict:
    def test_control_equals_target_rejected(self):
        gate = get_gate("x")
        with pytest.raises(InstructionError, match="overlap"):
            Instruction(
                gate=gate,
                targets=(QubitRef(0),),
                controls=(QubitRef(0),),
            )

    def test_distinct_control_and_target_accepted(self):
        gate = get_gate("x")
        instr = Instruction(
            gate=gate,
            targets=(QubitRef(1),),
            controls=(QubitRef(0),),
        )
        assert instr.gate.name == "x"


# --------------------------------------------------------------------------- #
# Duplicate controls
# --------------------------------------------------------------------------- #

class TestDuplicateControls:
    def test_duplicate_controls_rejected(self):
        gate = get_gate("x")
        with pytest.raises(InstructionError, match="duplicate"):
            Instruction(
                gate=gate,
                targets=(QubitRef(2),),
                controls=(QubitRef(0), QubitRef(0)),
            )


# --------------------------------------------------------------------------- #
# Parameter count validation
# --------------------------------------------------------------------------- #

class TestParameterCountValidation:
    def test_wrong_param_count_raises(self):
        with pytest.raises(InstructionError, match="parameter"):
            make_instruction(
                "h", [0],
                params=[Parameter("extra", value=1.0)],  # h takes 0 params
            )

    def test_rx_correct_param_count(self):
        instr = make_instruction("rx", [0], params=[Parameter("theta", value=1.0)])
        assert instr.gate.name == "rx"

    def test_rx_missing_param_raises(self):
        with pytest.raises(InstructionError, match="parameter"):
            make_instruction("rx", [0])  # rx requires 1 parameter

    def test_rx_too_many_params_raises(self):
        with pytest.raises(InstructionError, match="parameter"):
            make_instruction(
                "rx", [0],
                params=[Parameter("a", value=1.0), Parameter("b", value=2.0)],
            )


# --------------------------------------------------------------------------- #
# Gate arity validation
# --------------------------------------------------------------------------- #

class TestGateArityValidation:
    def test_wrong_arity_raises(self):
        with pytest.raises(InstructionError, match="arity"):
            make_instruction("h", [0, 1])  # h is single-qubit

    def test_cx_correct_arity(self):
        instr = make_instruction("cx", [0, 1])
        assert len(instr.targets) == 2

    def test_cx_wrong_arity_raises(self):
        with pytest.raises(InstructionError, match="arity"):
            make_instruction("cx", [0])  # cx needs 2 targets


# --------------------------------------------------------------------------- #
# validate_circuit
# --------------------------------------------------------------------------- #

class TestValidateCircuit:
    def test_valid_circuit_passes(self):
        c = Circuit(num_qubits=2)
        c.add(make_instruction("h", [0]))
        c.add(make_instruction("cx", [0, 1]))
        validate_circuit(c)  # should not raise

    def test_empty_circuit_passes(self):
        c = Circuit(num_qubits=0)
        validate_circuit(c)  # should not raise

    def test_circuit_with_measurement_passes(self):
        c = Circuit(num_qubits=1, num_clbits=1)
        c.add(make_instruction("measure", [0], clbits=[0]))
        validate_circuit(c)

    def test_negative_qubit_count_detected(self):
        # We have to bypass __post_init__ to test the validator directly.
        c = Circuit.__new__(Circuit)
        c.num_qubits = -1
        c.name = ""
        c.num_clbits = None
        c.instructions = []
        c.metadata = {}
        with pytest.raises(CircuitValidationError, match="qubit count"):
            validate_circuit(c)


# --------------------------------------------------------------------------- #
# Classical bit validation
# --------------------------------------------------------------------------- #

class TestClassicalBitValidation:
    def test_valid_clbit(self):
        c = Circuit(num_qubits=1, num_clbits=2)
        c.add(make_instruction("measure", [0], clbits=[1]))

    def test_clbit_out_of_range_raises(self):
        c = Circuit(num_qubits=1, num_clbits=1)
        with pytest.raises(CircuitValidationError):
            c.add(make_instruction("measure", [0], clbits=[5]))


# --------------------------------------------------------------------------- #
# Register construction validation
# --------------------------------------------------------------------------- #

class TestRegisterValidation:
    def test_qubit_ref_negative_raises(self):
        with pytest.raises(ValueError):
            QubitRef(-1)

    def test_qubit_ref_valid(self):
        q = QubitRef(0)
        assert q.index == 0

    def test_qubit_ref_ordering(self):
        assert QubitRef(0) < QubitRef(1)
        assert not (QubitRef(2) < QubitRef(1))

    def test_qubit_ref_round_trip(self):
        q = QubitRef(3)
        d = q.to_dict()
        restored = QubitRef.from_dict(d)
        assert restored.index == 3

    def test_classical_bit_ref_negative_raises(self):
        from rqm_circuits.registers import ClassicalBitRef
        with pytest.raises(ValueError):
            ClassicalBitRef(-1)


# --------------------------------------------------------------------------- #
# Parameter validation
# --------------------------------------------------------------------------- #

class TestParameterValidation:
    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            Parameter("")

    def test_whitespace_name_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            Parameter("   ")

    def test_bind(self):
        p = Parameter("theta")
        bound = p.bind(1.5)
        assert bound.is_bound
        assert bound.value == pytest.approx(1.5)

    def test_as_float_symbolic_raises(self):
        p = Parameter("phi")
        with pytest.raises(ValueError, match="symbolic"):
            p.as_float()

    def test_equality_numeric_close(self):
        p1 = Parameter("theta", value=1.5707963267948966)
        p2 = Parameter("theta", value=1.5707963267948966)
        assert p1 == p2

    def test_inequality_different_names(self):
        p1 = Parameter("theta", value=1.0)
        p2 = Parameter("phi", value=1.0)
        assert p1 != p2

    def test_inequality_different_values(self):
        p1 = Parameter("theta", value=1.0)
        p2 = Parameter("theta", value=2.0)
        assert p1 != p2
