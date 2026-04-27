# grain — primary-key uniqueness check

## What it does

Given a table and a declared primary key (single column for v0), surface
duplicate rows. If more than one row shares a key value, the grain is wrong
and downstream joins / aggregations will silently produce inflated answers.

## Inputs

- `inputs/data.parquet` — the table to check
- `inputs/key.txt` — single line, the column name to treat as PK (else: first column)

## Output

```python
{
    "key_col":            str,
    "n_rows":             int,
    "n_unique_keys":      int,
    "duplicate_keys":     [str, ...],   # the offending values
    "pk_violation_count": int,
    "is_valid_pk":        bool,
}
```

## Predicates

`expected.json` asserts the violation is detected (planted-duplicate fixture).
A clean-grain fixture is the inverse case (`is_valid_pk` true, `duplicate_keys`
empty); file as case_002 when needed.
