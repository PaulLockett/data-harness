"""100 p-values: 90 null + 10 real-effect."""
import polars as pl, numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent
rng = np.random.default_rng(42)
nulls = rng.uniform(0, 1, size=90).tolist()
hits = rng.uniform(0.0001, 0.005, size=10).tolist()
df = pl.DataFrame({"p": nulls + hits})
df.write_parquet(HERE / "pvals.parquet")
(HERE / "method.txt").write_text("bh\n")
(HERE / "alpha.txt").write_text("0.05\n")
print(f"wrote pvals.parquet n=100 (90 null + 10 effect); method=bh; alpha=0.05")
