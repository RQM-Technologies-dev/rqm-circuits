# rqm-circuits

**Canonical circuit-definition layer for the RQM Technologies quantum software stack.**

[![PyPI](https://img.shields.io/pypi/v/rqm-circuits)](https://pypi.org/project/rqm-circuits/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/RQM-Technologies-dev/rqm-circuits/actions/workflows/ci.yml/badge.svg)](https://github.com/RQM-Technologies-dev/rqm-circuits/actions/workflows/ci.yml)

---

## What is `rqm-circuits`?

`rqm-circuits` defines the native circuit object model that sits between
low-level quaternion/math libraries and higher-level compiler and backend adapter layers.

It is the **source-of-truth circuit representation** and the **canonical IR boundary**
for the RQM Technologies quantum software stack.

### Where it fits in the RQM stack

```
rqm-core          – quaternion/math foundation
rqm-circuits      – canonical circuit language / IR   ← you are here
rqm-compiler      – optimization and rewriting engine
rqm-qiskit        – Qiskit translation/execution bridge
rqm-braket        – Amazon Braket translation/execution bridge
rqm-pennylane     – PennyLane translation/execution bridge
future hosted API – circuit ingestion, analysis, optimization, export
```

### What it is NOT

- Not a backend adapter
- Not a transpiler to Qiskit / Braket / PennyLane
- Not a simulator
- Not a quaternion math library (`rqm-core` handles that)

### What it IS

- The stable internal language for quantum programs
- A clean, typed, serializable circuit representation
- An IR layer that a future hosted API can accept, validate, analyse, and return

---

## Quaternion connection

Every single-qubit `SU(2)` gate can be represented exactly as a unit quaternion

```
q = cos(θ/2) + u·sin(θ/2)
```

where `u` is the unit pure-imaginary quaternion (rotation axis) and `θ` is the
physical Bloch-sphere rotation angle.  `rqm-circuits` annotates each standard
gate with its quaternion form (`gate.quaternion_form`) as an informational field.
The mathematical evaluation of those forms lives in `rqm-core`.

```
Rx(θ)  →  q = cos(θ/2) + i·sin(θ/2)
Ry(θ)  →  q = cos(θ/2) + j·sin(θ/2)
Rz(θ)  →  q = cos(θ/2) + k·sin(θ/2)
H      →  q = (i+k)/√2   (π-rotation about (x̂+ẑ)/√2)
X      →  q = i           (π-rotation about x̂)
Y      →  q = j           (π-rotation about ŷ)
Z      →  q = k           (π-rotation about ẑ)
```

---

## Install

```bash
pip install rqm-circuits
```

Or for development:

```bash
git clone https://github.com/RQM-Technologies-dev/rqm-circuits.git
cd rqm-circuits
pip install -e ".[dev]"
```

---

## Quick start

```python
from rqm_circuits import Circuit, make_instruction, Parameter

# Create a 2-qubit Bell circuit
c = Circuit(num_qubits=2, name="bell")
c.add(make_instruction("h", targets=[0]))
c.add(make_instruction("cx", targets=[0, 1]))

print(c.summary())
# Circuit 'bell': 2 qubit(s), 0 clbit(s), 2 instruction(s)
#   [  0] h  q[0]
#   [  1] cx q[0], q[1]
```

### Rotation gate with a parameter

```python
import math
from rqm_circuits import Circuit, make_instruction, Parameter

c = Circuit(num_qubits=1, name="rotation")
c.add(make_instruction("rx", targets=[0], params=[Parameter("theta", value=math.pi / 2)]))
```

### Symbolic (unbound) parameter

```python
c = Circuit(num_qubits=1)
c.add(make_instruction("rz", targets=[0], params=[Parameter("phi")]))

from rqm_circuits import is_parametric
print(is_parametric(c))  # True
```

### Measurement

```python
c = Circuit(num_qubits=1, num_clbits=1)
c.add(make_instruction("x", targets=[0]))
c.add(make_instruction("measure", targets=[0], clbits=[0]))
```

---

## JSON serialization

`rqm-circuits` is designed as an API-ready IR layer.  Every circuit serializes
to a clean, deterministic JSON payload.

```python
from rqm_circuits import Circuit, make_instruction

c = Circuit(num_qubits=2, name="bell")
c.add(make_instruction("h", [0]))
c.add(make_instruction("cx", [0, 1]))

# Serialize
json_str = c.to_json()
print(json_str)

# Deserialize
c2 = Circuit.from_json(json_str)
assert c == c2
```

Example JSON output:

```json
{
  "schema_version": "0.1",
  "num_qubits": 2,
  "name": "bell",
  "instructions": [
    {
      "gate": {
        "name": "h",
        "arity": 1,
        "num_params": 0,
        "categories": ["clifford", "single_qubit"],
        "description": "Hadamard gate.  π-rotation about the (x+z)/√2 axis.",
        "quaternion_form": "q = (i+k)/√2  (axis = (x̂+ẑ)/√2, angle = π)"
      },
      "targets": [{"index": 0, "type": "qubit"}]
    },
    {
      "gate": {
        "name": "cx",
        "arity": 2,
        "num_params": 0,
        "categories": ["clifford", "two_qubit"],
        "description": "Controlled-X (CNOT) gate.  First target is control, second is target."
      },
      "targets": [
        {"index": 0, "type": "qubit"},
        {"index": 1, "type": "qubit"}
      ]
    }
  ]
}
```

---

## IR analysis helpers

```python
from rqm_circuits import (
    circuit_depth,
    gate_counts,
    has_measurements,
    is_parametric,
    qubit_usage,
    filter_by_category,
    GateCategory,
)

print(circuit_depth(c))          # 2
print(gate_counts(c))            # {'cx': 1, 'h': 1}
print(has_measurements(c))       # False
print(is_parametric(c))          # False
print(qubit_usage(c))            # {0: [0, 1], 1: [1]}
```

---

## Standard gate set

| Gate | Arity | Params | Category | Quaternion form |
|------|-------|--------|----------|-----------------|
| `i` | 1 | 0 | Clifford | `q = 1` |
| `x` | 1 | 0 | Clifford | `q = i` |
| `y` | 1 | 0 | Clifford | `q = j` |
| `z` | 1 | 0 | Clifford | `q = k` |
| `h` | 1 | 0 | Clifford | `q = (i+k)/√2` |
| `s` | 1 | 0 | Clifford | `q = cos(π/4) + k·sin(π/4)` |
| `t` | 1 | 0 | Non-Clifford | `q = cos(π/8) + k·sin(π/8)` |
| `rx` | 1 | 1 (θ) | Rotation | `q = cos(θ/2) + i·sin(θ/2)` |
| `ry` | 1 | 1 (θ) | Rotation | `q = cos(θ/2) + j·sin(θ/2)` |
| `rz` | 1 | 1 (θ) | Rotation | `q = cos(θ/2) + k·sin(θ/2)` |
| `cx` | 2 | 0 | Clifford | — |
| `cy` | 2 | 0 | Clifford | — |
| `cz` | 2 | 0 | Clifford | — |
| `swap` | 2 | 0 | Clifford | — |
| `iswap` | 2 | 0 | — | — |
| `measure` | 1 | 0 | Measurement | — |
| `barrier` | * | 0 | Directive | — |

---

## Package layout

```
src/rqm_circuits/
    __init__.py        Public API surface
    circuit.py         Circuit class
    gates.py           Gate definitions + standard registry
    instructions.py    Instruction model + make_instruction()
    registers.py       QubitRef / ClassicalBitRef
    params.py          Parameter (concrete + symbolic)
    validators.py      Validation rules
    serialization.py   JSON helpers + schema versioning
    ir.py              IR analysis utilities
    errors.py          Custom exceptions
    types.py           Type aliases and enumerations
tests/
    test_circuit.py
    test_gates.py
    test_serialization.py
    test_validation.py
```

---

## Error handling

All errors are structured and human-readable:

| Exception | When raised |
|-----------|-------------|
| `CircuitValidationError` | Invalid qubit indices, circuit structure |
| `InstructionError` | Wrong arity, parameter count, duplicate targets |
| `GateDefinitionError` | Unknown gate, invalid gate definition |
| `SerializationError` | Missing fields, wrong schema version, bad JSON |

---

## Future use in `rqm-compiler` and hosted APIs

`rqm-circuits` is designed as the stable contract between circuit producers
(user code, API ingestion) and circuit consumers (compiler, backends):

- `rqm-compiler` will import `Circuit` / `Instruction` directly and run
  quaternion-based optimization passes (gate fusion, inverse cancellation, etc.)
  over the instruction list.
- A future hosted API will accept `Circuit.to_json()` payloads, validate them,
  run compiler passes, and return optimized circuits or backend-native programs.

The JSON schema is versioned (`schema_version`) and stable across patch releases.

---

## Development

```bash
pip install -e ".[dev]"
pytest
```

---

## License

MIT — see [LICENSE](LICENSE).
