# serialization.py
"""JSON serialization helpers for rqm-circuits.

This module provides standalone :func:`to_json` / :func:`from_json` utilities
that operate over the circuit dictionary schema.  The primary serialization
interface lives on the :class:`~rqm_circuits.circuit.Circuit` object itself
(``circuit.to_json()`` / ``Circuit.from_json(...)``); this module handles the
lower-level JSON encoding/decoding and schema versioning.

Schema version
--------------
The JSON output always includes a ``"schema_version"`` field set to
:data:`SCHEMA_VERSION`.  Deserializers must check this version before
attempting to parse a payload.

The table below summarises the schema history:

+----------+--------------------------------------------------------------+
| Version  | Changes                                                      |
+==========+==============================================================+
| ``0.1``  | Initial release.  Controlled gates (cx/cy/cz) encoded with   |
|          | arity=2 and both control+target in the ``targets`` list.     |
+----------+--------------------------------------------------------------+
| ``0.2``  | Controlled gates use ``arity=1, num_controls=1`` with an     |
|          | explicit ``controls`` list.  New gates: ``phaseshift``,      |
|          | ``u1q``.  Rotation gates use canonical ``"angle"``           |
|          | parameter name.                                              |
+----------+--------------------------------------------------------------+

``from_json`` accepts both ``"0.1"`` (legacy) and ``"0.2"`` payloads.
Legacy ``"0.1"`` payloads are transparently normalized during instruction
deserialization (see :meth:`~rqm_circuits.instructions.Instruction.from_dict`).

Design note
-----------
All JSON output is deterministic: dictionaries are written with sorted keys
(where order does not carry semantic meaning) so that the output can be used
as a stable payload format for a future hosted API and for snapshot testing.
"""

from __future__ import annotations

import json
from typing import Any

from rqm_circuits.errors import SerializationError

#: Current stable schema version.
SCHEMA_VERSION: str = "0.2"

#: All schema versions accepted by this release's deserializer.
SUPPORTED_SCHEMA_VERSIONS: frozenset[str] = frozenset({"0.1", "0.2"})


def to_json(data: dict[str, Any], *, indent: int = 2) -> str:
    """Serialize a circuit dictionary to a JSON string.

    Args:
        data: Dictionary produced by ``Circuit.to_dict()``.
        indent: JSON indentation level (default 2 for readability).

    Returns:
        A deterministic JSON string.

    Raises:
        SerializationError: When the data cannot be serialized.
    """
    try:
        return json.dumps(data, indent=indent, sort_keys=True, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise SerializationError(f"Failed to serialize circuit to JSON: {exc}") from exc


def from_json(raw: str) -> dict[str, Any]:
    """Deserialize a JSON string to a circuit dictionary.

    Accepts payloads produced by any supported schema version.  Legacy
    ``"0.1"`` payloads are returned as-is; normalization of the controlled-gate
    encoding happens inside
    :meth:`~rqm_circuits.instructions.Instruction.from_dict`.

    Args:
        raw: A JSON string previously produced by :func:`to_json`.

    Returns:
        A dictionary suitable for passing to ``Circuit.from_dict()``.

    Raises:
        SerializationError: When the string is not valid JSON, is missing the
            ``"schema_version"`` field, or carries an unsupported version.
    """
    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SerializationError(f"Invalid JSON payload: {exc}") from exc

    if not isinstance(data, dict):
        raise SerializationError(
            f"Expected a JSON object at the top level, got {type(data).__name__!r}."
        )

    version = data.get("schema_version")
    if version is None:
        raise SerializationError(
            "JSON payload is missing required field 'schema_version'.  "
            "This payload may have been produced by an incompatible version."
        )
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise SerializationError(
            f"Unsupported schema version {version!r}; "
            f"this release supports versions {sorted(SUPPORTED_SCHEMA_VERSIONS)}."
        )
    return data
