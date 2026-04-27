"""Generates case_001/inputs/sample.parquet — a 5-row Polars DataFrame.

Run once to materialize the fixture file (parquet binary is committed; this
script lives alongside it as the recipe for re-creation).
"""
import polars as pl
from pathlib import Path

HERE = Path(__file__).resolve().parent

df = pl.DataFrame({
    "x":     [1.0, 2.5, 3.7, 4.2, 5.1],
    "y":     [10, 20, 30, 40, 50],
    "label": ["alpha", "beta", "gamma", "delta", "epsilon"],
})
df.write_parquet(HERE / "sample.parquet")
print(f"wrote {HERE / 'sample.parquet'}: shape={df.shape}")
