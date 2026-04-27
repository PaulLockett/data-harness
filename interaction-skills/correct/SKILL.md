# correct — multiple-comparison p-value correction

## What it does

Given a vector of p-values, return Benjamini-Hochberg q-values (FDR control)
or Bonferroni-corrected p-values. Use whenever multiple hypotheses are tested
on the same data — uncorrected significance multiplies false positives
linearly with the number of tests.

## Inputs

- `inputs/pvals.parquet` — single column `p` of floats in [0, 1]
- `inputs/method.txt` — `"bh"` or `"bonferroni"` (else: `"bh"`)
- `inputs/alpha.txt` — significance threshold (else: 0.05)

## Output

```python
{
    "method":               "bh" | "bonferroni",
    "alpha":                float,
    "n_total":              int,
    "n_significant_at_alpha": int,
    "q":                    [float, ...],   # corrected values, same order as input
}
```

## Predicates

`expected.json` asserts the method is recognized, q is the same length as
input, and counts are non-negative integers.
