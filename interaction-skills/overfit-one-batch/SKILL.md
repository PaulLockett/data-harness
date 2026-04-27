# overfit-one-batch — verify a model can memorize a tiny dataset

## What it does

Fits a linear regression to a small dataset; if the training MSE doesn't go
near zero, either the data has duplicate-x-with-different-y noise (degenerate
target) or the implementation is broken upstream. Use this as a smoke test
BEFORE training on the full dataset — it catches "I have a bug" early.

## Inputs

- `inputs/data.parquet` — feature columns + target column
- `inputs/target.txt` — target column name

## Output

```python
{
    "n":            int,
    "n_features":   int,
    "train_mse":    float,
    "r2":           float,
    "can_memorize": bool,    # train_mse < threshold (default 0.1)
}
```

## Predicates

`expected.json` asserts the linear fit memorizes a small generated dataset
(`can_memorize` true, `train_mse < 0.1`).
