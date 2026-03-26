# rqm-circuits

**Canonical external circuit IR for the RQM Technologies quantum software stack.**

[![PyPI](https://img.shields.io/pypi/v/rqm-circuits)](https://pypi.org/project/rqm-circuits/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/RQM-Technologies-dev/rqm-circuits/actions/workflows/ci.yml/badge.svg)](https://github.com/RQM-Technologies-dev/rqm-circuits/actions/workflows/ci.yml)

---

## What is `rqm-circuits`?

`rqm-circuits` is the **single source-of-truth wire format** for API and Studio
traffic in the RQM Technologies quantum software stack.  It defines the canonical
circuit object model that sits between the quaternion math layer and the internal
optimization engine.

### Architecture

```
rqm-core       – quaternion/math foundation
rqm-circuits   – canonical external circuit IR   ← you are here
rqm-compiler   – internal optimization / canonicalization engine
rqm-qiskit     – Qiskit translation/execution bridge
rqm-braket     – Amazon Braket translation/execution bridge
rqm-api        – hosted API (accepts rqm-circuits JSON payloads)
Studio         – visual circuit editor (emits rqm-circuits JSON payloads)
```

Key roles:

- **`rqm-circuits` = canonical external circuit IR**.  API payloads and Studio
  traffic use `rqm-circuits` as the wire format.  The JSON representation is
  versioned and stable.
- **`rqm-compiler` = internal engine**.  Compiler descriptors are *internal*;
  they are not the public API payload.
- `rqm-circuits` is **lightweight and backend-neutral**: no dependency on
  Qiskit, Braket, or `rqm-compiler`.

### What it is NOT

- Not a backend adapter
- Not a transpiler to Qiskit / Braket / PennyLane
- Not a simulator
- Not a quaternion math library (`rqm-core` handles that)
- Not the compiler's internal IR (`rqm-compiler` has its own descriptor types)

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
Rx(angle) → q = cos(angle/2) + i·sin(angle/2)
Ry(angle) → q = cos(angle/2) + j·sin(angle/2)
Rz(angle) → q = cos(angle/2) + k·sin(angle/2)
H         → q = (i+k)/√2   (π-rotation about (x̂+ẑ)/√2)
X         → q = i           (π-rotation about x̂)
Y         → q = j           (π-rotation about ŷ)
Z         → q = k           (π-rotation about ẑ)
```

The universal single-qubit gate `u1q` is parameterised directly by the unit
quaternion components `(w, x, y, z)`:

```
u1q(w, x, y, z) → q = w + xi + yj + zk  (|q| = 1)
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

### Bell circuit

```python
from rqm_circuits import Circuit, make_instruction

# Create a 2-qubit Bell circuit
c = Circuit(num_qubits=2, name="bell")
c.add(make_instruction("h", targets=[0]))
# cx: supply the control qubit via controls=, the target via targets=
c.add(make_instruction("cx", targets=[1], controls=[0]))

print(c.summary())
# Circuit 'bell': 2 qubit(s), 0 clbit(s), 2 instruction(s)
#   [  0] h  q[0]
#   [  1] cx ctrl:q[0]  q[1]
```

### GHZ circuit

```python
from rqm_circuits import Circuit, make_instruction

n = 3
c = Circuit(num_qubits=n, name="ghz")
c.add(make_instruction("h", [0]))
for i in range(1, n):
    c.add(make_instruction("cx", targets=[i], controls=[0]))
```

### Rotation gate with a parameter

```python
import math
from rqm_circuits import Circuit, make_instruction, Parameter

c = Circuit(num_qubits=1, name="rotation")
# Canonical parameter name for all rotation gates is "angle"
c.add(make_instruction("rx", targets=[0], params=[Parameter("angle", value=math.pi / 2)]))
```

### Phase-shift gate

```python
from rqm_circuits import Circuit, make_instruction, Parameter

c = Circuit(num_qubits=1)
c.add(make_instruction("phaseshift", targets=[0], params=[Parameter("angle", value=0.5)]))
```

### Universal single-qubit gate (u1q)

```python
import math
from rqm_circuits import Circuit, make_instruction, Parameter

# Hadamard expressed as a unit quaternion
norm = 1.0 / math.sqrt(2)
c = Circuit(num_qubits=1)
c.add(make_instruction(
    "u1q", targets=[0],
    params=[
        Parameter("w", value=norm),
        Parameter("x", value=norm),
        Parameter("y", value=0.0),
        Parameter("z", value=0.0),
    ],
))
```

### Symbolic (unbound) parameter

```python
c = Circuit(num_qubits=1)
c.add(make_instruction("rz", targets=[0], params=[Parameter("angle")]))

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
to a clean, deterministic JSON payload (schema version `"0.2"`).

```python
from rqm_circuits import Circuit, make_instruction

c = Circuit(num_qubits=2, name="bell")
c.add(make_instruction("h", [0]))
c.add(make_instruction("cx", targets=[1], controls=[0]))

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
  "instructions": [
    {
      "gate": {
        "arity": 1,
        "categories": ["clifford", "single_qubit"],
        "description": "Hadamard gate.  π-rotation about the (x+z)/√2 axis.",
        "name": "h",
        "num_params": 0,
        "quaternion_form": "q = (i+k)/√2  (axis = (x̂+ẑ)/√2, angle = π)"
      },
      "targets": [{"index": 0, "type": "qubit"}]
    },
    {
      "controls": [{"index": 0, "type": "qubit"}],
      "gate": {
        "arity": 1,
        "categories": ["clifford", "two_qubit"],
        "description": "Controlled-X (CNOT) gate.  One control qubit, one target qubit.",
        "name": "cx",
        "num_controls": 1,
        "num_params": 0
      },
      "targets": [{"index": 1, "type": "qubit"}]
    }
  ],
  "name": "bell",
  "num_qubits": 2,
  "schema_version": "0.2"
}
```

### Schema versioning

| Version | Description |
|---------|-------------|
| `"0.1"` | Legacy.  Controlled gates encoded as arity-2 with both qubits in `targets`. |
| `"0.2"` | **Current**.  Controlled gates use `arity=1`, `num_controls=1`, explicit `controls` list.  New gates: `phaseshift`, `u1q`.  Canonical param name `"angle"`. |

Schema `"0.1"` payloads are accepted on ingestion and transparently normalized.

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

| Gate | Arity | Controls | Params | Param names | Category | Quaternion form |
|------|-------|----------|--------|-------------|----------|-----------------|
| `i` | 1 | 0 | 0 | — | Clifford | `q = 1` |
| `x` | 1 | 0 | 0 | — | Clifford | `q = i` |
| `y` | 1 | 0 | 0 | — | Clifford | `q = j` |
| `z` | 1 | 0 | 0 | — | Clifford | `q = k` |
| `h` | 1 | 0 | 0 | — | Clifford | `q = (i+k)/√2` |
| `s` | 1 | 0 | 0 | — | Clifford | `q = cos(π/4) + k·sin(π/4)` |
| `t` | 1 | 0 | 0 | — | Non-Clifford | `q = cos(π/8) + k·sin(π/8)` |
| `rx` | 1 | 0 | 1 | `angle` | Rotation | `q = cos(angle/2) + i·sin(angle/2)` |
| `ry` | 1 | 0 | 1 | `angle` | Rotation | `q = cos(angle/2) + j·sin(angle/2)` |
| `rz` | 1 | 0 | 1 | `angle` | Rotation | `q = cos(angle/2) + k·sin(angle/2)` |
| `phaseshift` | 1 | 0 | 1 | `angle` | Rotation | `q = cos(angle/2) + k·sin(angle/2)` |
| `u1q` | 1 | 0 | 4 | `w,x,y,z` | — | `q = w + xi + yj + zk` |
| `cx` | 1 | 1 | 0 | — | Clifford | — |
| `cy` | 1 | 1 | 0 | — | Clifford | — |
| `cz` | 1 | 1 | 0 | — | Clifford | — |
| `swap` | 2 | 0 | 0 | — | Clifford | — |
| `iswap` | 2 | 0 | 0 | — | — | — |
| `measure` | 1 | 0 | 0 | — | Measurement | — |
| `barrier` | * | 0 | 0 | — | Directive | — |

> **Controlled gates** (`cx`, `cy`, `cz`): supply the control qubit via
> `controls=[{"index": ctrl}]` and the target qubit via `targets=[{"index": tgt}]`.
> The legacy encoding (both qubits in `targets`, arity=2) is still accepted on
> ingestion for schema `"0.1"` backward compatibility.

> **Rotation gates** (`rx`, `ry`, `rz`, `phaseshift`): the canonical parameter
> name is `"angle"`.  Legacy names `"theta"` and `"phi"` are silently normalized
> to `"angle"` on ingestion.

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
    schema.py          JSON Schema + TypedDict definitions
tests/
    test_circuit.py
    test_gates.py
    test_serialization.py
    test_validation.py
    test_schema.py
    test_new_features.py
```

---

## Error handling

All errors are structured and human-readable:

| Exception | When raised |
|-----------|-------------|
| `CircuitValidationError` | Invalid qubit indices, circuit structure, wrong clbit usage |
| `InstructionError` | Wrong arity, parameter count/name, duplicate targets, missing controls |
| `GateDefinitionError` | Unknown gate, invalid gate definition |
| `SerializationError` | Missing fields, wrong schema version, bad JSON |

---

## Breaking changes (schema 0.1 → 0.2)

| Change | Schema 0.1 | Schema 0.2 |
|--------|-----------|-----------|
| `cx`/`cy`/`cz` arity | 2 (both qubits in `targets`) | 1 (target in `targets`, control in `controls`) |
| Rotation param name | `"theta"` or `"phi"` | `"angle"` (legacy normalized on ingestion) |
| New gates | — | `phaseshift`, `u1q` |
| `Gate` fields | `name`, `arity`, `num_params` | + `num_controls`, `param_names` |

Schema `"0.1"` payloads remain accepted on ingestion; they are transparently
normalized to the `"0.2"` internal representation.

---

## Development

```bash
pip install -e ".[dev]"
pytest
```

---

## License

MIT — see [LICENSE](LICENSE).
