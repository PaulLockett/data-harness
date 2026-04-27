"""Saturating learning curve: y = 0.8*x + N(0, 1), n=400."""
import polars as pl, numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent
rng = np.random.default_rng(42)
x = rng.uniform(-3, 3, size=400)
y = 0.8 * x + rng.normal(0, 1, size=400)
df = pl.DataFrame({"x": x.tolist(), "y": y.tolist()})
df.write_parquet(HERE / "data.parquet")
(HERE / "target.txt").write_text("y\n")
print(f"wrote data.parquet n=400; y = 0.8*x + N(0,1); expected R² saturates ~0.4")
