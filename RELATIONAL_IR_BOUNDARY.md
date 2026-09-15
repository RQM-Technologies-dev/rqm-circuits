# Relational IR boundary

`rqm-circuits` remains the portable public circuit schema. It does **not** serialize `BellHinge`, `AxisHinge`, `CartanRelation`, or `QuaternionCartanBlock` as public wire objects.

The public standard-compatible primitives `rxx`, `ryy`, and `rzz` are the materialization boundary for one-axis and Cartan relational forms. `rqm-entanglement` owns the relational mathematics; `rqm-compiler` recognizes, promotes/demotes, and routes those forms internally; backend adapters consume the resulting standard gates or verified `su4q` fallback.

This preserves schema stability while allowing the compiler to use the smallest exact representation internally.
