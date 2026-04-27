# saturation — diminishing-returns curve over data size

## What it does

Trains a linear regression on increasingly large prefixes of the data
(25%, 50%, 75%, 100%) and reports R². If R² flattens early, more data won't
help — invest in features, not rows. If it climbs steeply, more data
probably will.

## Inputs

- `inputs/data.parquet` — feature columns + target column
- `inputs/target.txt` — target column name

## Output

```python
{
    "fractions":       [0.25, 0.5, 0.75, 1.0],
    "n_at_fraction":   [int, int, int, int],
    "r2_scores":       [float, float, float, float],
    "delta_last":      float,    # r2[-1] - r2[-2]; small means saturation reached
    "saturation_reached": bool,  # delta_last < 0.01
}
```

## Predicates

`expected.json` asserts the structural shape (4-element lists, R² in [0, 1]).
