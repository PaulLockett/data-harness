# leakage — feature/target leakage detection

## What it does

Given features and a target column, surface features whose linear correlation
with the target is suspiciously high (default threshold 0.95). Such features
typically encode the target itself — a model "learns" them and produces
spectacular validation scores that fail in production.

## Inputs

- `inputs/features.parquet` — table with both features and the target column
- `inputs/target.txt` — single line, the target column name (else: last column)

## Output

```python
{
    "target_col":       str,
    "max_correlation":  float,
    "top_correlated":   [(col, corr), ...],   # sorted desc by |corr|
    "suspect_features": [col, ...],            # |corr| > 0.95
}
```

## Predicates

`expected.json` asserts the planted suspect feature is in the suspect_features
list and `max_correlation > 0.95`.
