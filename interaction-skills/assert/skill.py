"""assert — evaluates a list of predicates against a record (the contract layer)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
if str(_HERE.parent.parent.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent.parent.parent))


def run(inputs_dir: Path) -> dict:
    inputs_dir = Path(inputs_dir)
    record = json.loads((inputs_dir / "record.json").read_text())
    predicates = json.loads((inputs_dir / "predicates.json").read_text())
    if isinstance(predicates, dict) and "predicates" in predicates:
        predicates = predicates["predicates"]

    # Reuse check_skill's predicate machinery.
    from check_skill import _check_predicate, _jsonpath
    results = []
    for p in predicates:
        path = p.get("path", "$")
        values = _jsonpath(record, path)
        ok, why = _check_predicate(values, p)
        results.append({"path": path, "ok": bool(ok), "why": why})
    n_passed = sum(1 for r in results if r["ok"])
    n_failed = len(results) - n_passed
    return {
        "n_predicates": len(predicates),
        "n_passed":     n_passed,
        "n_failed":     n_failed,
        "results":      results,
        "all_passed":   n_failed == 0,
    }
