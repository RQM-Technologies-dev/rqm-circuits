# ir.py
"""Intermediate representation (IR) utilities for rqm-circuits.

This module provides helpers that operate on :class:`~rqm_circuits.circuit.Circuit`
objects at the IR level: inspection, analysis, and lightweight transformation
helpers that do **not** require a backend or compiler.

These utilities are intentionally minimal.  Deeper optimization (quaternion
fusion, gate cancellation, basis translation) belongs in ``rqm-compiler``.

Architecture note
-----------------
``rqm-circuits`` is the *IR boundary* of the RQM stack.  This module exposes
functions that help downstream layers (compiler, API, visualizer) answer
structural questions about a circuit without needing direct access to its
internal fields.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rqm_circuits.types import GateCategory

if TYPE_CHECKING:
    from rqm_circuits.circuit import Circuit
    from rqm_circuits.instructions import Instruction


def gate_counts(circuit: "Circuit") -> dict[str, int]:
    """Count instructions per gate name.

    Args:
        circuit: The circuit to analyse.

    Returns:
        A dictionary mapping gate names to their occurrence counts, sorted
        alphabetically for deterministic output.

    Examples:
        >>> from rqm_circuits.circuit import Circuit
        >>> from rqm_circuits.instructions import make_instruction
        >>> c = Circuit(num_qubits=2)
        >>> c.add(make_instruction("h", [0]))
        >>> c.add(make_instruction("cx", [0, 1]))
        >>> gate_counts(c)
        {'cx': 1, 'h': 1}
    """
    counts: dict[str, int] = {}
    for instr in circuit.instructions:
        counts[instr.gate.name] = counts.get(instr.gate.name, 0) + 1
    return dict(sorted(counts.items()))


def circuit_depth(circuit: "Circuit") -> int:
    """Compute the critical-path depth of a circuit.

    The depth is defined as the maximum number of instructions that must be
    executed sequentially on any single qubit wire, taking into account that
    two-qubit gates advance multiple wires simultaneously.

    Args:
        circuit: The circuit to analyse.

    Returns:
        Circuit depth (integer ≥ 0).

    Examples:
        >>> c = Circuit(num_qubits=2)
        >>> c.add(make_instruction("h", [0]))
        >>> c.add(make_instruction("cx", [0, 1]))
        >>> circuit_depth(c)
        2
    """
    if not circuit.instructions:
        return 0

    # Track the current depth on each qubit wire.
    wire_depth: dict[int, int] = {i: 0 for i in range(circuit.num_qubits)}

    for instr in circuit.instructions:
        qubits = sorted(instr.all_qubits)
        if not qubits:
            continue
        # The instruction starts after the deepest involved wire finishes.
        start = max(wire_depth.get(q, 0) for q in qubits)
        new_depth = start + 1
        for q in qubits:
            wire_depth[q] = new_depth

    return max(wire_depth.values(), default=0)


def qubit_usage(circuit: "Circuit") -> dict[int, list[int]]:
    """Return, for each qubit, the (0-based) indices of instructions that touch it.

    Args:
        circuit: The circuit to analyse.

    Returns:
        A dictionary mapping qubit index to a list of instruction positions.

    Examples:
        >>> usage = qubit_usage(c)
        >>> usage[0]
        [0, 1]
    """
    usage: dict[int, list[int]] = {i: [] for i in range(circuit.num_qubits)}
    for instr_idx, instr in enumerate(circuit.instructions):
        for q in instr.all_qubits:
            usage.setdefault(q, []).append(instr_idx)
    return usage


def has_measurements(circuit: "Circuit") -> bool:
    """Return ``True`` if the circuit contains at least one measure instruction.

    Args:
        circuit: The circuit to inspect.

    Returns:
        Boolean.
    """
    return any(instr.gate.name == "measure" for instr in circuit.instructions)


def is_parametric(circuit: "Circuit") -> bool:
    """Return ``True`` if the circuit contains any unbound (symbolic) parameters.

    Args:
        circuit: The circuit to inspect.

    Returns:
        Boolean.
    """
    return any(
        not param.is_bound
        for instr in circuit.instructions
        for param in instr.params
    )


def filter_by_category(
    circuit: "Circuit",
    category: GateCategory,
) -> list["Instruction"]:
    """Return all instructions whose gate belongs to ``category``.

    Args:
        circuit: The circuit to search.
        category: A :class:`~rqm_circuits.types.GateCategory` value.

    Returns:
        List of matching :class:`~rqm_circuits.instructions.Instruction` objects
        (in circuit order).
    """
    return [
        instr
        for instr in circuit.instructions
        if category in instr.gate.categories
    ]
