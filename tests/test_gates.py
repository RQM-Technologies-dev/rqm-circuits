"""Tests for the Gate model and standard gate registry."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from rqm_circuits import (
    Gate,
    GateCategory,
    GateDefinitionError,
    STANDARD_GATES,
    get_gate,
)


# --------------------------------------------------------------------------- #
# Standard gate registry
# --------------------------------------------------------------------------- #

class TestStandardGates:
    EXPECTED_GATES = [
        "i", "x", "y", "z", "h", "s", "t",
        "rx", "ry", "rz",
        "cx", "cy", "cz", "swap", "iswap",
        "measure", "barrier",
    ]

    def test_all_expected_gates_present(self):
        for name in self.EXPECTED_GATES:
            assert name in STANDARD_GATES, f"Gate '{name}' missing from registry"

    def test_single_qubit_gates_arity(self):
        for name in ("i", "x", "y", "z", "h", "s", "t", "rx", "ry", "rz", "measure"):
            assert STANDARD_GATES[name].arity == 1, f"Gate '{name}' should have arity 1"

    def test_two_qubit_gates_arity(self):
        for name in ("cx", "cy", "cz", "swap", "iswap"):
            assert STANDARD_GATES[name].arity == 2, f"Gate '{name}' should have arity 2"

    def test_rotation_gates_have_one_param(self):
        for name in ("rx", "ry", "rz"):
            assert STANDARD_GATES[name].num_params == 1, (
                f"Gate '{name}' should have 1 parameter"
            )

    def test_clifford_gates_no_params(self):
        for name in ("x", "y", "z", "h", "s"):
            assert STANDARD_GATES[name].num_params == 0

    def test_t_gate_non_clifford(self):
        assert GateCategory.NON_CLIFFORD in STANDARD_GATES["t"].categories

    def test_h_gate_clifford(self):
        assert GateCategory.CLIFFORD in STANDARD_GATES["h"].categories

    def test_measure_gate_category(self):
        assert GateCategory.MEASUREMENT in STANDARD_GATES["measure"].categories

    def test_barrier_directive_category(self):
        assert GateCategory.DIRECTIVE in STANDARD_GATES["barrier"].categories

    def test_barrier_allows_barrier_flag(self):
        assert STANDARD_GATES["barrier"].allows_barrier is True

    def test_rotation_gates_category(self):
        for name in ("rx", "ry", "rz"):
            assert GateCategory.ROTATION in STANDARD_GATES[name].categories

    def test_quaternion_form_present_for_single_qubit(self):
        for name in ("x", "y", "z", "h", "s", "t", "rx", "ry", "rz", "i"):
            gate = STANDARD_GATES[name]
            assert gate.quaternion_form, (
                f"Gate '{name}' should have a quaternion_form annotation"
            )


# --------------------------------------------------------------------------- #
# get_gate
# --------------------------------------------------------------------------- #

class TestGetGate:
    def test_get_known_gate(self):
        gate = get_gate("h")
        assert gate.name == "h"

    def test_get_unknown_gate_raises(self):
        with pytest.raises(GateDefinitionError, match="Unknown gate"):
            get_gate("unknown_xyz")

    def test_get_gate_returns_correct_object(self):
        gate = get_gate("cx")
        assert gate.arity == 2
        assert gate.num_params == 0


# --------------------------------------------------------------------------- #
# Gate construction
# --------------------------------------------------------------------------- #

class TestGateConstruction:
    def test_valid_gate(self):
        g = Gate(name="custom", arity=1, num_params=0)
        assert g.name == "custom"

    def test_gate_negative_arity_raises(self):
        with pytest.raises(GateDefinitionError):
            Gate(name="bad", arity=-1)

    def test_gate_negative_params_raises(self):
        with pytest.raises(GateDefinitionError):
            Gate(name="bad", arity=1, num_params=-1)

    def test_gate_empty_name_raises(self):
        with pytest.raises(GateDefinitionError):
            Gate(name="", arity=1)

    def test_gate_immutable(self):
        g = Gate(name="h", arity=1)
        with pytest.raises(FrozenInstanceError):
            g.name = "x"  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# Gate serialization
# --------------------------------------------------------------------------- #

class TestGateSerialization:
    def test_to_dict_basic(self):
        gate = get_gate("h")
        d = gate.to_dict()
        assert d["name"] == "h"
        assert d["arity"] == 1
        assert d["num_params"] == 0
        assert isinstance(d["categories"], list)

    def test_round_trip(self):
        for name in ("h", "cx", "rx", "measure"):
            gate = get_gate(name)
            d = gate.to_dict()
            restored = Gate.from_dict(d)
            assert restored.name == gate.name
            assert restored.arity == gate.arity
            assert restored.num_params == gate.num_params

    def test_from_dict_missing_name_raises(self):
        from rqm_circuits import SerializationError
        with pytest.raises(SerializationError):
            Gate.from_dict({"arity": 1})

    def test_from_dict_missing_arity_raises(self):
        from rqm_circuits import SerializationError
        with pytest.raises(SerializationError):
            Gate.from_dict({"name": "h"})

    def test_categories_serialized_sorted(self):
        gate = get_gate("rx")
        d = gate.to_dict()
        assert d["categories"] == sorted(d["categories"])

    def test_repr_contains_name(self):
        gate = get_gate("h")
        assert "h" in repr(gate)
