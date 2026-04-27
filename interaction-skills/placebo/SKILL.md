# placebo — refutation by random shuffle

## What it does

Tests whether a measured "effect" survives randomization. Compute the
treatment-vs-control mean difference on the real labels, then on randomly
shuffled labels (the placebo). A real effect persists; an artifact mostly
vanishes. Returns the ratio so a downstream caller can decide whether the
real effect dominates the placebo distribution.

## Inputs

- `inputs/data.parquet` — at minimum two columns: `treatment` (0/1 int) and `outcome` (numeric)

## Output

```python
{
    "n":                       int,
    "true_effect":             float,    # mean(outcome | treated) - mean(outcome | control)
    "placebo_effect":          float,    # same metric on shuffled treatment
    "placebo_ratio":           float,    # |placebo_effect| / |true_effect|
    "placebo_passes":          bool,     # placebo_ratio < 0.5
    "n_placebo_resamples":     int,
}
```

## Predicates

`expected.json` asserts `placebo_passes` is true on the planted-real-effect
fixture, and the dict has the right shape.
