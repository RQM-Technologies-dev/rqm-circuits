import pytest

from rqm_circuits import Circuit, CircuitValidationError, validate_circuit, validate_public_circuit


def _custom_gate_circuit(name: str) -> Circuit:
    return Circuit.from_dict(
        {
            "schema_version": "0.2",
            "num_qubits": 2,
            "instructions": [
                {
                    "gate": {
                        "name": name,
                        "arity": 2,
                        "num_params": 0,
                        "categories": ["two_qubit"],
                    },
                    "targets": [
                        {"index": 0, "type": "qubit"},
                        {"index": 1, "type": "qubit"},
                    ],
                }
            ],
        }
    )


def test_public_boundary_rejects_internal_su4q() -> None:
    circuit = _custom_gate_circuit("su4q")
    validate_circuit(circuit)
    with pytest.raises(CircuitValidationError, match="internal compiler gate"):
        validate_public_circuit(circuit)


def test_public_boundary_preserves_other_custom_gates() -> None:
    validate_public_circuit(_custom_gate_circuit("custom_echo"))
