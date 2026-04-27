# uncertainty — bootstrap confidence interval on a statistic

## What it does

Given a numeric column and a statistic (mean by default), return a 95% CI via
percentile bootstrap (1000 resamples). Method auto-picks based on data shape;
v0 ships bootstrap only; conformal / Bayesian variants are kind switches
deferred until first skill that needs them.

## Inputs

- `inputs/data.parquet` — table with at least one numeric column
- `inputs/target.txt` — target column name (else first numeric)

## Output

```python
{
    "kind":         "bootstrap",
    "stat":         "mean" | "median" | "var",
    "point":        float,
    "ci_low":       float,
    "ci_high":      float,
    "level":        0.95,
    "n_resamples":  int,
}
```

## Predicates

`expected.json` asserts `ci_low < point < ci_high`, `level == 0.95`, and the
output dict shape is complete.
