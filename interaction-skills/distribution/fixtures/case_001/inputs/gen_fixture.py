"""Generates a 200-row parquet with x ~ N(10, 2) for the distribution skill."""
import polars as pl
import numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent

rng = np.random.default_rng(42)
df = pl.DataFrame({
    "x":     rng.normal(loc=10.0, scale=2.0, size=200).tolist(),
    "label": ["A", "B"] * 100,
})
df.write_parquet(HERE / "sample.parquet")
print(f"wrote {HERE / 'sample.parquet'}: shape={df.shape}; mean={float(df['x'].mean()):.3f}")
