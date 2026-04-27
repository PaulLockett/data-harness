# glance — verification primitive

## What it does

Type-aware deep inspection of a tabular / array / image / graph artifact.
Returns enough structure that an agent (or `dh check-skill`) can verify whether
a downstream transform produced what it intended.

Use `glance` after every meaningful transform. The harness's discipline is
"verify, don't assume." Skipping `glance` is how silent corruption ships.

## Inputs

A single artifact, typically loaded via `helpers.load(uri)`. Supported types:
Polars / Pandas DataFrame, NumPy ndarray, PIL Image, GeoDataFrame, NetworkX
graph, Astropy HDUList, Zarr Array, dict, list, bytes, Path, str.

## Output (skill.py contract)

```python
{
    "kind":        "DataFrame" | "ndarray" | "Series" | ...,
    "n_rows":      int,
    "n_cols":      int,
    "columns":     [str, ...],
    "schema":      {col: dtype_str, ...},
    "nulls":       {col: int_count, ...},
    "summary_str": str   # multi-line human-readable
}
```

## Predicates

`expected.json` asserts shape, schema key set, null counts in range, and
structural completeness via `key_set_includes`. Different fixtures capture
different artifact kinds; the v0 fixture exercises a 5-row Polars DataFrame.

## When to file a new case

Whenever a new artifact type is encountered (e.g., HDUList during the TESS
domain build, GeoDataFrame for GFW), add `case_NNN/` with that artifact in
`inputs/` and predicates that exercise the new code path.
