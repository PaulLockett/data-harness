"""Linear y = 1.5*x1 - 2.0*x2 + 0.5; no noise — must fit exactly."""
import polars as pl, numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent
rng = np.random.default_rng(42)
x1 = rng.uniform(-3, 3, size=30)
x2 = rng.uniform(-3, 3, size=30)
y = 1.5 * x1 - 2.0 * x2 + 0.5
df = pl.DataFrame({"x1": x1.tolist(), "x2": x2.tolist(), "y": y.tolist()})
df.write_parquet(HERE / "data.parquet")
(HERE / "target.txt").write_text("y\n")
print("wrote data.parquet n=30; y = 1.5*x1 - 2.0*x2 + 0.5; expected mse ~ 0")
