# distribution — univariate distribution summary

## What it does

Given a column of numeric values, return a structured summary: count, mean,
std, min/max, median, p95, and a 10-bin histogram. Use this BEFORE comparing
two snapshots (`drift`) or modeling a target — you should know the marginal
shape first.

## Inputs

A parquet with at least one numeric column. The skill auto-picks the first
numeric column it finds; specify `target_column` to override (future v).

## Output (skill.py contract)

```python
{
    "column":    str,
    "n":         int,
    "mean":      float,
    "std":       float,
    "min":       float,
    "max":       float,
    "p50":       float,
    "p95":       float,
    "histogram": [int, ...]   # exactly 10 bin counts
}
```

## Predicates

`expected.json` asserts the column name is one of a known set, n is in a
reasonable range, std is non-negative, and the histogram has exactly 10 bins
each of which is a non-negative int.

## Future cases

Categorical columns (Shannon entropy + value counts), multimodal distributions
(KDE peaks), heavy-tailed (powerlaw fit) — file as case_002+ when needed.
