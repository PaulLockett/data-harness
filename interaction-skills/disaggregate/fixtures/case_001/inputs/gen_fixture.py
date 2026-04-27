"""3 groups (A, B, C) with mean 5, 10, 15 (σ=1.5 within)."""
import polars as pl, numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent
rng = np.random.default_rng(42)
group_means = {"A": 5.0, "B": 10.0, "C": 15.0}
groups = []
outcomes = []
for g, m in group_means.items():
    groups.extend([g] * 100)
    outcomes.extend(rng.normal(m, 1.5, size=100).tolist())
df = pl.DataFrame({"group": groups, "outcome": outcomes})
df.write_parquet(HERE / "data.parquet")
print(f"wrote data.parquet n=300; group means {group_means}")
