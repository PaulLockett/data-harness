# plan — task-decomposition prior

## What it does

Given a goal string, return a structured plan: a list of steps + estimated
prerequisites. v0 ships a deterministic, rule-based decomposition that
produces well-formed structure; production should route through `llm()`
(via cassette) for real reasoning. The fixture validates the structural
contract — predicates pass either way.

## Inputs

- `inputs/goal.txt` — single line, the goal/task description

## Output

```python
{
    "goal":         str,
    "n_steps":      int,
    "steps":        [{"id": int, "title": str, "depends_on": [int, ...]}, ...],
    "estimated_minutes": int,
    "kind":         "rule_based" | "llm",
}
```

## Predicates

`expected.json` asserts the structural shape — at least 1 step, dependencies
reference valid step ids, the goal echoes the input.
