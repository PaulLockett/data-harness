# drift — distributional shift between two snapshots

## What it does

Given two snapshots of the same schema, return a per-column drift score and an
overall alarm. Use BEFORE retraining a model on a new vintage of data —
silent drift is how stale models start producing wrong answers.

## Inputs

Two parquets under `inputs/`: `a.parquet` (reference) and `b.parquet` (new).
Same schema. Numeric columns get a quantile-shift score; categorical columns
get a value-counts total-variation distance (placeholder in v0).

## Output (skill.py contract)

```python
{
    "metric":    "quantile_shift",
    "score":     float,                # max over columns
    "alarm":     bool,                 # score > 0.5
    "by_column": {col: float, ...}
}
```

## Predicates

`expected.json` asserts the metric is from a known set, the score is
non-negative, the alarm is a bool, and `by_column` includes the columns
we expect.

## Future cases

case_002 = no-drift baseline (alarm=False); case_003 = adversarial drift
(label noise injected); case_004 = mixed numeric+categorical shift.
