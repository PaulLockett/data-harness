"""plan — deterministic rule-based plan decomposition (LLM-via-cassette TBD)."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
if str(_HERE.parent.parent.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent.parent.parent))


_TEMPLATE = [
    "Understand the goal and surface what's known vs unknown",
    "Identify the smallest verifiable subgoal",
    "Implement the subgoal end-to-end",
    "Verify with a predicate / spoof",
    "Generalize and document",
]


def run(inputs_dir: Path) -> dict:
    inputs_dir = Path(inputs_dir)
    goal = (inputs_dir / "goal.txt").read_text().strip()
    steps = []
    for i, title in enumerate(_TEMPLATE):
        steps.append({
            "id":         i,
            "title":      title,
            "depends_on": [i - 1] if i > 0 else [],
        })
    return {
        "goal":               goal,
        "n_steps":            len(steps),
        "steps":              steps,
        "estimated_minutes":  len(steps) * 15,
        "kind":               "rule_based",
    }
