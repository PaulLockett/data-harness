"""saturation — learning-curve over fractions of the dataset."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
if str(_HERE.parent.parent.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent.parent.parent))


def _r2(X, y):
    import numpy as np
    X_aug = np.column_stack([X, np.ones(len(y))])
    coef, *_ = np.linalg.lstsq(X_aug, y, rcond=None)
    y_hat = X_aug @ coef
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2)) or 1.0
    return 1.0 - ss_res / ss_tot


def run(inputs_dir: Path) -> dict:
    inputs_dir = Path(inputs_dir)
    import polars as pl
    import numpy as np

    df = pl.read_parquet(inputs_dir / "data.parquet")
    target = (inputs_dir / "target.txt").read_text().strip()
    feature_cols = [c for c in df.columns if c != target]
    X = np.column_stack([df[c].to_numpy().astype(float) for c in feature_cols])
    y = df[target].to_numpy().astype(float)
    n = len(y)

    fractions = [0.25, 0.5, 0.75, 1.0]
    n_at_fraction = []
    r2_scores = []
    for f in fractions:
        k = max(2, int(n * f))
        n_at_fraction.append(k)
        r2_scores.append(float(_r2(X[:k], y[:k])))
    delta_last = float(r2_scores[-1] - r2_scores[-2])
    return {
        "fractions":          fractions,
        "n_at_fraction":      n_at_fraction,
        "r2_scores":          r2_scores,
        "delta_last":         delta_last,
        "saturation_reached": bool(abs(delta_last) < 0.01),
    }
