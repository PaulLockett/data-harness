"""reflect — rule-based retrospective (LLM-via-cassette TBD)."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve()
if str(_HERE.parent.parent.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent.parent.parent))


def run(inputs_dir: Path) -> dict:
    inputs_dir = Path(inputs_dir)
    trace = json.loads((inputs_dir / "trace.json").read_text())

    passed = [t for t in trace if t.get("outcome") == "pass"]
    failed = [t for t in trace if t.get("outcome") == "fail"]
    error_counts = Counter(t.get("error", "(no detail)") for t in failed)
    common_errors = [err for err, _ in error_counts.most_common(3)]

    next_actions = []
    if failed:
        next_actions.append(f"Triage the {len(failed)} failed step(s) (most common: {common_errors[0]!r})")
    if passed:
        next_actions.append(f"Codify the {len(passed)} passing step(s) into reusable skills")
    if not failed and not passed:
        next_actions.append("Trace was empty — capture a real run before reflecting")
    return {
        "n_steps":       len(trace),
        "n_passed":      len(passed),
        "n_failed":      len(failed),
        "pass_rate":     float(len(passed) / len(trace)) if trace else 0.0,
        "what_worked":   [t["step"] for t in passed],
        "what_failed":   [t["step"] for t in failed],
        "common_errors": common_errors,
        "next_actions":  next_actions,
        "kind":          "rule_based",
    }
