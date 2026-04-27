"""200 Gaussian samples for bootstrap CI of mean."""
import polars as pl, numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent
rng = np.random.default_rng(42)
df = pl.DataFrame({"x": rng.normal(10, 2, size=200).tolist()})
df.write_parquet(HERE / "data.parquet")
(HERE / "target.txt").write_text("x\n")
print(f"wrote data.parquet n=200; mean={float(df['x'].mean()):.3f} (target ~10)")
