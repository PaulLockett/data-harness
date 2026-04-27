# reflect — post-hoc retrospective

## What it does

Given a trace of steps + outcomes (pass/fail), return a structured critique:
which steps worked, which didn't, surfaced patterns, and suggested next
actions. v0 is rule-based (counts + simple heuristics); production should
route through `llm()` for narrative reasoning.

## Inputs

- `inputs/trace.json` — list of step records:
  ```json
  [{"step": "load data", "outcome": "pass", "duration_s": 0.4},
   {"step": "validate schema", "outcome": "fail", "duration_s": 0.1, "error": "missing column"}]
  ```

## Output

```python
{
    "n_steps":         int,
    "n_passed":        int,
    "n_failed":        int,
    "pass_rate":       float,
    "what_worked":     [str, ...],
    "what_failed":     [str, ...],
    "common_errors":   [str, ...],
    "next_actions":    [str, ...],
    "kind":            "rule_based" | "llm",
}
```

## Predicates

`expected.json` asserts the structural shape — counts add up, lists exist,
pass_rate ∈ [0, 1].
