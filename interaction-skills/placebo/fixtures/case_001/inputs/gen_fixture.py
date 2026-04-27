"""400 rows; outcome = 5 + 2*treatment + N(0, 0.5)."""
import polars as pl, numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent
rng = np.random.default_rng(42)
t = rng.integers(0, 2, size=400)
y = 5.0 + 2.0 * t + rng.normal(0, 0.5, size=400)
df = pl.DataFrame({"treatment": t.tolist(), "outcome": y.tolist()})
df.write_parquet(HERE / "data.parquet")
print(f"wrote data.parquet n=400; true_effect target=+2.0; observed={float(y[t==1].mean() - y[t==0].mean()):.3f}")
