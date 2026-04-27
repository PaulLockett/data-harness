# split — train/test split leakage check

## What it does

Given a train and test partition, detect whether they overlap. Any overlap
between train and test is a leakage source — the model will appear to
generalize when it's actually memorizing.

## Inputs

- `inputs/train.parquet`, `inputs/test.parquet`
- `inputs/key.txt` — column to compare on (else: all columns hashed)

## Output

```python
{
    "kind":             "random" | "temporal" | "group",   # static "random" in v0
    "train_rows":       int,
    "test_rows":        int,
    "overlap_count":    int,    # rows present in both
    "leak_score":       float,  # overlap_count / min(train, test)
    "group_collisions": [...],  # specific overlapping keys
}
```

## Predicates

`expected.json` asserts the planted overlap is detected (`overlap_count >= 1`,
`leak_score > 0`).
