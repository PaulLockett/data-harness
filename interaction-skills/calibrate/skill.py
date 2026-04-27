"""calibrate — Brier + reliability bins + ECE."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
if str(_HERE.parent.parent.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent.parent.parent))


def run(inputs_dir: Path, n_bins: int = 10) -> dict:
    inputs_dir = Path(inputs_dir)
    import polars as pl
    import numpy as np

    df = pl.read_parquet(inputs_dir / "preds.parquet")
    p = df["prob"].to_numpy().astype(float)
    y = df["actual"].to_numpy().astype(float)
    if p.shape != y.shape:
        raise ValueError("prob and actual must have same length")
    n = len(p)

    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins = []
    ece = 0.0
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        mask = (p >= lo) & (p < hi if i < n_bins - 1 else p <= hi)
        cnt = int(mask.sum())
        if cnt == 0:
            mean_pred = 0.0
            frac_pos = 0.0
        else:
            mean_pred = float(p[mask].mean())
            frac_pos = float(y[mask].mean())
            ece += (cnt / n) * abs(mean_pred - frac_pos)
        bins.append({
            "bin":       i,
            "lo":        float(lo),
            "hi":        float(hi),
            "n":         cnt,
            "mean_pred": mean_pred,
            "frac_pos":  frac_pos,
        })
    return {
        "n":                int(n),
        "brier_score":      float(np.mean((p - y) ** 2)),
        "ece":              float(ece),
        "reliability_bins": bins,
    }
