"""Tests for the Circuit class."""

from __future__ import annotations

import pytest

from rqm_circuits import (
    Circuit,
    CircuitValidationError,
    Parameter,
    circuit_depth,
    gate_counts,
    has_measurements,
    is_parametric,
    make_instruction,
    qubit_usage,
)

# --------------------------------------------------------------------------- #
# Construction
# --------------------------------------------------------------------------- #

class TestCircuitConstruction:
    def test_minimal_circuit(self):
        c = Circuit(num_qubits=1)
        assert c.num_qubits == 1
        assert c.name == ""
        assert c.num_clbits is None
        assert c.instructions == []
        assert c.metadata == {}

    def test_named_circuit(self):
        c = Circuit(num_qubits=3, name="test")
        assert c.name == "test"

    def test_circuit_with_clbits(self):
        c = Circuit(num_qubits=2, num_clbits=2)
        assert c.num_clbits == 2

    def test_circuit_with_metadata(self):
        meta = {"author": "rqm", "version": 1}
        c = Circuit(num_qubits=1, metadata=meta)
        assert c.metadata == meta

    def test_empty_circuit_zero_qubits(self):
        c = Circuit(num_qubits=0)
        assert c.num_qubits == 0
        assert len(c) == 0

    def test_negative_qubits_raises(self):
        with pytest.raises(CircuitValidationError):
            Circuit(num_qubits=-1)

    def test_negative_clbits_raises(self):
        with pytest.raises(CircuitValidationError):
            Circuit(num_qubits=1, num_clbits=-1)


# --------------------------------------------------------------------------- #
# Instruction appending
# --------------------------------------------------------------------------- #

class TestCircuitAdd:
    def test_add_single_gate(self):
        c = Circuit(num_qubits=1)
        c.add(make_instruction("h", [0]))
        assert len(c) == 1

    def test_append_alias(self):
        c = Circuit(num_qubits=1)
        c.append(make_instruction("x", [0]))
        assert len(c) == 1

    def test_extend_multiple(self):
        c = Circuit(num_qubits=2)
        c.extend([
            make_instruction("h", [0]),
            make_instruction("cx", [0, 1]),
        ])
        assert len(c) == 2

    def test_add_returns_self_for_chaining(self):
        c = Circuit(num_qubits=1)
        result = c.add(make_instruction("x", [0]))
        assert result is c

    def test_add_invalid_qubit_raises(self):
        c = Circuit(num_qubits=1)
        with pytest.raises(CircuitValidationError):
            c.add(make_instruction("x", [1]))  # only qubit 0 exists

    def test_add_invalid_qubit_two_qubit_gate(self):
        c = Circuit(num_qubits=2)
        with pytest.raises(CircuitValidationError):
            c.add(make_instruction("cx", [0, 2]))  # qubit 2 does not exist

    def test_bell_circuit(self):
        c = Circuit(num_qubits=2, name="bell")
        c.add(make_instruction("h", [0]))
        c.add(make_instruction("cx", [0, 1]))
        assert len(c) == 2
        assert c.instructions[0].gate.name == "h"
        assert c.instructions[1].gate.name == "cx"

    def test_measure_instruction(self):
        c = Circuit(num_qubits=1, num_clbits=1)
        c.add(make_instruction("measure", [0], clbits=[0]))
        assert len(c) == 1

    def test_measure_without_clbit_raises(self):
        c = Circuit(num_qubits=1, num_clbits=1)
        with pytest.raises(CircuitValidationError):
            c.add(make_instruction("measure", [0]))  # no classical bit target

    def test_measure_invalid_clbit_raises(self):
        c = Circuit(num_qubits=1, num_clbits=1)
        with pytest.raises(CircuitValidationError):
            c.add(make_instruction("measure", [0], clbits=[2]))  # clbit 2 out of range


# --------------------------------------------------------------------------- #
# Copy
# --------------------------------------------------------------------------- #

class TestCircuitCopy:
    def test_copy_is_independent(self):
        c = Circuit(num_qubits=1, name="original")
        c.add(make_instruction("x", [0]))
        c2 = c.copy()
        c2.add(make_instruction("z", [0]))
        assert len(c) == 1
        assert len(c2) == 2

    def test_copy_equality(self):
        c = Circuit(num_qubits=2)
        c.add(make_instruction("h", [0]))
        c2 = c.copy()
        assert c == c2

    def test_copy_name_preserved(self):
        c = Circuit(num_qubits=1, name="mycirc")
        c2 = c.copy()
        assert c2.name == "mycirc"


# --------------------------------------------------------------------------- #
# Equality
# --------------------------------------------------------------------------- #

class TestCircuitEquality:
    def test_equal_empty_circuits(self):
        assert Circuit(num_qubits=2) == Circuit(num_qubits=2)

    def test_not_equal_different_qubits(self):
        assert Circuit(num_qubits=1) != Circuit(num_qubits=2)

    def test_not_equal_different_instructions(self):
        c1 = Circuit(num_qubits=1)
        c1.add(make_instruction("x", [0]))
        c2 = Circuit(num_qubits=1)
        c2.add(make_instruction("z", [0]))
        assert c1 != c2


# --------------------------------------------------------------------------- #
# Summary
# --------------------------------------------------------------------------- #

class TestCircuitSummary:
    def test_empty_summary(self):
        c = Circuit(num_qubits=2, name="empty")
        s = c.summary()
        assert "empty" in s
        assert "2 qubit" in s
        assert "0 instruction" in s

    def test_summary_contains_gate_names(self):
        c = Circuit(num_qubits=2, name="bell")
        c.add(make_instruction("h", [0]))
        c.add(make_instruction("cx", [0, 1]))
        s = c.summary()
        assert "h" in s
        assert "cx" in s

    def test_summary_with_params(self):
        c = Circuit(num_qubits=1)
        c.add(make_instruction("rx", [0], params=[Parameter("theta", value=1.5)]))
        s = c.summary()
        assert "rx" in s
        assert "1.5" in s

    def test_summary_with_symbolic_param(self):
        c = Circuit(num_qubits=1)
        c.add(make_instruction("rx", [0], params=[Parameter("phi")]))
        s = c.summary()
        assert "phi" in s

    def test_repr(self):
        c = Circuit(num_qubits=3, name="test")
        r = repr(c)
        assert "Circuit" in r
        assert "num_qubits=3" in r


# --------------------------------------------------------------------------- #
# IR helpers
# --------------------------------------------------------------------------- #

class TestIRHelpers:
    def test_gate_counts_empty(self):
        c = Circuit(num_qubits=1)
        assert gate_counts(c) == {}

    def test_gate_counts(self):
        c = Circuit(num_qubits=2)
        c.add(make_instruction("h", [0]))
        c.add(make_instruction("h", [1]))
        c.add(make_instruction("cx", [0, 1]))
        counts = gate_counts(c)
        assert counts["h"] == 2
        assert counts["cx"] == 1

    def test_circuit_depth_empty(self):
        c = Circuit(num_qubits=2)
        assert circuit_depth(c) == 0

    def test_circuit_depth_linear(self):
        c = Circuit(num_qubits=1)
        c.add(make_instruction("x", [0]))
        c.add(make_instruction("z", [0]))
        assert circuit_depth(c) == 2

    def test_circuit_depth_parallel(self):
        c = Circuit(num_qubits=2)
        c.add(make_instruction("h", [0]))
        c.add(make_instruction("h", [1]))
        assert circuit_depth(c) == 1

    def test_circuit_depth_bell(self):
        c = Circuit(num_qubits=2)
        c.add(make_instruction("h", [0]))
        c.add(make_instruction("cx", [0, 1]))
        assert circuit_depth(c) == 2

    def test_has_measurements_false(self):
        c = Circuit(num_qubits=1)
        c.add(make_instruction("x", [0]))
        assert not has_measurements(c)

    def test_has_measurements_true(self):
        c = Circuit(num_qubits=1, num_clbits=1)
        c.add(make_instruction("measure", [0], clbits=[0]))
        assert has_measurements(c)

    def test_is_parametric_false(self):
        c = Circuit(num_qubits=1)
        c.add(make_instruction("rx", [0], params=[Parameter("theta", value=1.0)]))
        assert not is_parametric(c)

    def test_is_parametric_true(self):
        c = Circuit(num_qubits=1)
        c.add(make_instruction("rx", [0], params=[Parameter("theta")]))
        assert is_parametric(c)

    def test_qubit_usage(self):
        c = Circuit(num_qubits=2)
        c.add(make_instruction("h", [0]))
        c.add(make_instruction("cx", [0, 1]))
        usage = qubit_usage(c)
        assert 0 in usage[0]
        assert 1 in usage[0]
        assert 1 in usage[1]
