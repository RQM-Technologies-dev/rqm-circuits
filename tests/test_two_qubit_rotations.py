from __future__ import annotations

import json
import math

import pytest

from rqm_circuits import (
    CIRCUIT_JSON_SCHEMA,
    STANDARD_GATES,
    Circuit,
    GateCategory,
    Parameter,
    circuit_depth,
    gate_counts,
    make_instruction,
)
from rqm_circuits.instructions import Instruction


@pytest.mark.parametrize("name", ["rxx", "ryy", "rzz"])
def test_standard_gate_definition(name: str) -> None:
    gate = STANDARD_GATES[name]
    assert gate.arity == 2
    assert gate.num_controls == 0
    assert gate.num_params == 1
    assert gate.param_names == ("angle",)
    assert GateCategory.ROTATION in gate.categories
    assert GateCategory.TWO_QUBIT in gate.categories
    assert GateCategory.ENTANGLING in gate.categories


@pytest.mark.parametrize("name", ["rxx", "ryy", "rzz"])
def test_instruction_parameter_normalization_and_round_trip(name: str) -> None:
    instruction = make_instruction(
        name,
        [0, 1],
        params=[Parameter("theta", value=math.pi / 7)],
    )
    assert instruction.params[0].name == "angle"
    restored = Instruction.from_dict(json.loads(json.dumps(instruction.to_dict())))
    assert restored == instruction


def test_circuit_builder_helpers_counts_depth_and_deterministic_json() -> None:
    circuit = Circuit(num_qubits=3, name="pair-rotations")
    assert circuit.rxx(0.1, 0, 1) is circuit
    assert circuit.ryy(0.2, 1, 2) is circuit
    assert circuit.rzz(0.3, 0, 2) is circuit
    assert gate_counts(circuit) == {"rxx": 1, "ryy": 1, "rzz": 1}
    assert circuit_depth(circuit) == 3
    assert circuit.to_json() == circuit.to_json()
    assert Circuit.from_json(circuit.to_json()) == circuit


def test_schema_retains_backward_compatible_version_and_category() -> None:
    assert Circuit(num_qubits=0).to_dict()["schema_version"] == "0.2"
    categories = CIRCUIT_JSON_SCHEMA["$defs"]["Gate"]["properties"]["categories"][
        "items"
    ]["enum"]
    assert "entangling" in categories


def test_rzz_description_does_not_claim_universal_input_entanglement() -> None:
    assert "does not guarantee entanglement for every input state" in STANDARD_GATES[
        "rzz"
    ].description


@pytest.mark.parametrize("name", ["rxx", "ryy", "rzz"])
def test_two_distinct_targets_are_required(name: str) -> None:
    with pytest.raises(Exception, match="duplicate"):
        make_instruction(name, [0, 0], params=[Parameter("angle", value=0.5)])
