"""distribution — univariate numeric distribution summary."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
if str(_HERE.parent.parent.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent.parent.parent))


def run(inputs_dir: Path) -> dict:
    inputs_dir = Path(inputs_dir)
    parquets = sorted(inputs_dir.glob("*.parquet"))
    if not parquets:
        raise FileNotFoundError(f"no .parquet under {inputs_dir}")
    import polars as pl
    import numpy as np

    df = pl.read_parquet(parquets[0])
    numeric = [c for c, t in zip(df.columns, df.dtypes)
               if str(t).startswith(("Int", "Float", "UInt"))]
    if not numeric:
        raise ValueError(f"no numeric columns in {parquets[0]}")
    col = numeric[0]
    series = df[col].drop_nulls().to_numpy()
    if len(series) == 0:
        raise ValueError(f"all-null column {col!r}")
    return {
        "column":    col,
        "n":         int(len(series)),
        "mean":      float(np.mean(series)),
        "std":       float(np.std(series, ddof=1) if len(series) > 1 else 0.0),
        "min":       float(np.min(series)),
        "max":       float(np.max(series)),
        "p50":       float(np.median(series)),
        "p95":       float(np.percentile(series, 95)),
        "histogram": np.histogram(series, bins=10)[0].astype(int).tolist(),
    }
