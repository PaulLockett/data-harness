"""schema — declared-schema validator for a JSON record."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
if str(_HERE.parent.parent.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent.parent.parent))


_TYPE_CHECK = {
    "string": lambda v: isinstance(v, str),
    "int":    lambda v: isinstance(v, int) and not isinstance(v, bool),
    "float":  lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "bool":   lambda v: isinstance(v, bool),
    "list":   lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
}


def _got_type(v) -> str:
    if isinstance(v, bool):  return "bool"
    if isinstance(v, int):   return "int"
    if isinstance(v, float): return "float"
    if isinstance(v, str):   return "string"
    if isinstance(v, list):  return "list"
    if isinstance(v, dict):  return "object"
    if v is None:            return "null"
    return type(v).__name__


def run(inputs_dir: Path) -> dict:
    inputs_dir = Path(inputs_dir)
    record = json.loads((inputs_dir / "record.json").read_text())
    schema = json.loads((inputs_dir / "schema.json").read_text())
    required = {f["name"]: f["type"] for f in schema.get("required", [])}
    optional = {f["name"]: f["type"] for f in schema.get("optional", [])}
    declared = {**required, **optional}

    missing = [k for k in required if k not in record]
    extra = [k for k in record if k not in declared]
    mismatches = []
    for k, v in record.items():
        if k in declared:
            chk = _TYPE_CHECK.get(declared[k])
            if chk and not chk(v):
                mismatches.append({"key": k, "declared": declared[k], "got": _got_type(v)})
    return {
        "valid":            not (missing or mismatches),
        "missing_required": missing,
        "extra_keys":       extra,
        "type_mismatches":  mismatches,
    }
