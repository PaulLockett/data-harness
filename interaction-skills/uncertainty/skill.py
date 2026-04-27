"""uncertainty — bootstrap CI on a statistic."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
if str(_HERE.parent.parent.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent.parent.parent))


def run(inputs_dir: Path, n_resamples: int = 1000, level: float = 0.95) -> dict:
    inputs_dir = Path(inputs_dir)
    import polars as pl
    import numpy as np

    df = pl.read_parquet(inputs_dir / "data.parquet")
    tgt_file = inputs_dir / "target.txt"
    target = (tgt_file.read_text().strip() if tgt_file.exists()
              else next(c for c, t in zip(df.columns, df.dtypes)
                        if str(t).startswith(("Int", "Float", "UInt"))))
    x = df[target].drop_nulls().to_numpy().astype(float)
    rng = np.random.default_rng(42)
    sample_means = np.array([
        np.mean(rng.choice(x, size=len(x), replace=True))
        for _ in range(n_resamples)
    ])
    alpha = (1 - level) / 2
    return {
        "kind":        "bootstrap",
        "stat":        "mean",
        "target":      target,
        "point":       float(np.mean(x)),
        "ci_low":      float(np.quantile(sample_means, alpha)),
        "ci_high":     float(np.quantile(sample_means, 1 - alpha)),
        "level":       float(level),
        "n_resamples": int(n_resamples),
    }
