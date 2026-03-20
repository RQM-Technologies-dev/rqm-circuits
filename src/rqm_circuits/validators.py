# validators.py
"""Validation rules for rqm-circuits.

This module provides circuit-level and instruction-level validation logic.
Validation is separated from construction so that:

1. Objects can be constructed leniently during deserialization and then
   validated in a single explicit pass.
2. Validation errors are structured and carry enough context to be surfaced
   through a future REST API.

All public functions raise :class:`~rqm_circuits.errors.CircuitValidationError`
on failure.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rqm_circuits.errors import CircuitValidationError

if TYPE_CHECKING:
    from rqm_circuits.circuit import Circuit
    from rqm_circuits.instructions import Instruction


def validate_instruction(
    instruction: "Instruction",
    num_qubits: int,
    num_clbits: int = 0,
) -> None:
    """Validate a single instruction against a circuit's qubit/bit counts.

    Args:
        instruction: The instruction to validate.
        num_qubits: Total number of qubits in the circuit.
        num_clbits: Total number of classical bits in the circuit.

    Raises:
        CircuitValidationError: When any validation rule is violated.
    """
    gate = instruction.gate

    # 1. Qubit index bounds.
    for qubit in (*instruction.targets, *instruction.controls):
        if qubit.index >= num_qubits:
            raise CircuitValidationError(
                f"Instruction '{gate.name}' references qubit index "
                f"{qubit.index}, but the circuit only has {num_qubits} qubit(s) "
                f"(valid indices: 0–{num_qubits - 1})."
            )

    # 2. Classical bit index bounds.
    for clbit in instruction.clbits:
        if clbit.index >= num_clbits:
            raise CircuitValidationError(
                f"Instruction '{gate.name}' references classical bit index "
                f"{clbit.index}, but the circuit only has {num_clbits} classical "
                f"bit(s) (valid indices: 0–{max(0, num_clbits - 1)})."
            )

    # 3. Measure gate must have exactly one classical bit target.
    if gate.name == "measure" and len(instruction.clbits) != 1:
        raise CircuitValidationError(
            f"Measure instruction must have exactly 1 classical bit target, "
            f"got {len(instruction.clbits)}."
        )


def validate_circuit(circuit: "Circuit") -> None:
    """Run all validation rules over an entire circuit.

    Args:
        circuit: The circuit to validate.

    Raises:
        CircuitValidationError: On the first rule violation found.
    """
    if circuit.num_qubits < 0:
        raise CircuitValidationError(
            f"Circuit '{circuit.name}' has invalid qubit count {circuit.num_qubits}; "
            f"must be ≥ 0."
        )

    num_clbits = circuit.num_clbits or 0

    for idx, instr in enumerate(circuit.instructions):
        try:
            validate_instruction(instr, circuit.num_qubits, num_clbits)
        except CircuitValidationError as exc:
            raise CircuitValidationError(
                f"Instruction[{idx}] ({instr.gate.name}): {exc}"
            ) from exc
