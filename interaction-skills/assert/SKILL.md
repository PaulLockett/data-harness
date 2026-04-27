# assert — predicate contract layer

## What it does

Evaluates a list of predicates against a record. Same predicate vocabulary as
`expected.json` (`type`, `min_length`, `regex`, `in_set`, `in_range`,
`min_size`, `key_set_includes`, ...). Use this when you want to declare a
contract on an intermediate value mid-pipeline — the assertion either passes
silently or fails loudly with the predicate path that broke.

## Inputs

- `inputs/record.json` — any JSON value to assert against
- `inputs/predicates.json` — list of predicate dicts (same shape as `expected.json` predicates)

## Output

```python
{
    "n_predicates":   int,
    "n_passed":       int,
    "n_failed":       int,
    "results":        [{"path": str, "ok": bool, "why": str}, ...],
    "all_passed":     bool,
}
```

## Predicates

`expected.json` validates the validator: a known-true predicate set on a known
record yields `all_passed = true` and `n_failed = 0`.
