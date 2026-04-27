# schema — type/shape/key validation against a declared schema

## What it does

Given a record (or table) and a declared schema, return a structured report
of missing required keys, extra keys, and per-field type mismatches. The
validator catches drift between what an upstream producer claims and what the
record actually contains.

## Inputs

- `inputs/record.json` — the record to validate (object with arbitrary keys)
- `inputs/schema.json` — the schema. Shape:
  ```json
  {
      "required": [{"name": "id", "type": "string"}, ...],
      "optional": [{"name": "extra", "type": "int"}, ...]
  }
  ```

## Output

```python
{
    "valid":              bool,
    "missing_required":   [...],   # required keys not in record
    "extra_keys":         [...],   # record keys not declared in schema
    "type_mismatches":    [{"key": str, "declared": str, "got": str}, ...],
}
```

## Predicates

`expected.json` asserts the planted mismatch is detected.
