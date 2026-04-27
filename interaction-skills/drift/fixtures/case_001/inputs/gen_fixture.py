"""Generates a/b parquet pair with planted ~1.5σ mean shift in x."""
import polars as pl
import numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent

rng = np.random.default_rng(42)
a = pl.DataFrame({
    "x":     rng.normal(loc=10.0, scale=2.0, size=200).tolist(),
    "label": ["A", "B"] * 100,
})
b = pl.DataFrame({
    "x":     rng.normal(loc=13.0, scale=2.0, size=200).tolist(),
    "label": ["A", "B"] * 100,
})
a.write_parquet(HERE / "a.parquet")
b.write_parquet(HERE / "b.parquet")
print(f"a mean={float(a['x'].mean()):.3f}; b mean={float(b['x'].mean()):.3f}; expected drift > 0.5")
