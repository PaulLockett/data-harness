"""500 rows; y = 2x + tiny noise. 'leaked' = 2x + tinier noise (~0.999 corr)."""
import polars as pl
import numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent
rng = np.random.default_rng(42)

x = rng.normal(0, 1, size=500)
y = 2 * x + rng.normal(0, 0.05, size=500)
leaked = 2 * x + rng.normal(0, 0.005, size=500)
noise = rng.normal(0, 1, size=500)

df = pl.DataFrame({
    "x":      x.tolist(),
    "noise":  noise.tolist(),
    "leaked": leaked.tolist(),
    "y":      y.tolist(),
})
df.write_parquet(HERE / "features.parquet")
(HERE / "target.txt").write_text("y\n")
print("wrote features.parquet; planted: x and leaked both ~0.999 correlated with y")
