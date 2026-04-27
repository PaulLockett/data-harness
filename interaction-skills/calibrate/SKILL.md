# calibrate — predicted-probability calibration check

## What it does

Given probabilistic predictions vs binary outcomes, return Brier score,
reliability-diagram bins (10 equal-width bins), and Expected Calibration
Error (ECE). Use BEFORE trusting predicted probabilities for decisions —
miscalibrated probabilities hide their quality from a thresholded accuracy
metric.

## Inputs

- `inputs/preds.parquet` — at least two columns, `prob` (float ∈ [0, 1])
  and `actual` (bool / 0-1 int).

## Output

```python
{
    "n":                  int,
    "brier_score":        float,         # 0 perfect, 1 worst
    "ece":                float,         # 0 perfectly calibrated
    "reliability_bins":   [{
        "bin":      int,
        "lo":       float, "hi": float,
        "n":        int,
        "mean_pred":float,
        "frac_pos": float,
    }, ...],   # 10 bins
}
```

## Predicates

`expected.json` asserts brier ∈ [0, 1], ece ∈ [0, 1], 10 bins, dict shape.
