# join — characterize join cardinality + fanout

## What it does

Given two tables and a shared key, classify the join as 1:1 / 1:N / N:1 / N:M
and surface fanout. Joining on a non-unique key without realizing it inflates
metrics; this is one of the most common silent corruptions in data work.

## Inputs

- `inputs/left.parquet`, `inputs/right.parquet`
- `inputs/key.txt` — single line, the column name to join on (else: first shared column)

## Output

```python
{
    "key":            str,
    "cardinality":    "1:1" | "1:N" | "N:1" | "N:M",
    "left_rows":      int,
    "right_rows":     int,
    "joined_rows":    int,    # inner join count
    "fanout_max":     int,    # max repeats per left key after join
    "missing_left":   int,    # left rows with no match in right
    "missing_right":  int,    # right rows with no match in left
}
```

## Predicates

`expected.json` asserts the planted cardinality, fanout, and orphan counts.
