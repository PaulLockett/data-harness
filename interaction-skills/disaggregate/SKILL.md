# disaggregate — group-wise heterogeneity surface

## What it does

Given a numeric outcome and a grouping column, return per-group statistics
and a heterogeneity score (between-group variance / total variance).
Aggregate metrics often hide subgroup-level catastrophes — disaggregate
catches them.

## Inputs

- `inputs/data.parquet` — `outcome` (numeric) and `group` (categorical)

## Output

```python
{
    "n_groups":             int,
    "groups":               [{"group": str, "n": int, "mean": float, "std": float}, ...],
    "between_var":          float,
    "within_var":           float,
    "total_var":            float,
    "heterogeneity_score":  float,    # between / total ∈ [0, 1]
    "max_min_ratio":        float,    # max(group_means) / min(group_means)
}
```

## Predicates

`expected.json` asserts heterogeneity_score is positive (planted disparity),
groups list non-empty, structural shape complete.
