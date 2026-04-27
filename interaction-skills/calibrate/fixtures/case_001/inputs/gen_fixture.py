"""500 well-calibrated probabilistic predictions."""
import polars as pl, numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent
rng = np.random.default_rng(42)
prob = rng.beta(2, 2, size=500)         # spread of probabilities
actual = (rng.random(size=500) < prob).astype(int)
df = pl.DataFrame({"prob": prob.tolist(), "actual": actual.tolist()})
df.write_parquet(HERE / "preds.parquet")
print(f"wrote preds.parquet n=500; brier ~ {float(np.mean((prob - actual) ** 2)):.3f}")
