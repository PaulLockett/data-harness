"""overfit-one-batch — sanity check via linear regression memorize."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
if str(_HERE.parent.parent.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent.parent.parent))


def run(inputs_dir: Path, threshold: float = 0.1) -> dict:
    inputs_dir = Path(inputs_dir)
    import polars as pl
    import numpy as np

    df = pl.read_parquet(inputs_dir / "data.parquet")
    target = (inputs_dir / "target.txt").read_text().strip()
    feature_cols = [c for c in df.columns if c != target]
    X = np.column_stack([df[c].to_numpy().astype(float) for c in feature_cols])
    y = df[target].to_numpy().astype(float)
    X_aug = np.column_stack([X, np.ones(len(y))])  # intercept

    coef, _resid, _rank, _sv = np.linalg.lstsq(X_aug, y, rcond=None)
    y_hat = X_aug @ coef
    mse = float(np.mean((y - y_hat) ** 2))
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2)) or 1.0
    r2 = 1.0 - ss_res / ss_tot
    return {
        "n":            int(len(y)),
        "n_features":   int(X.shape[1]),
        "train_mse":    mse,
        "r2":           r2,
        "can_memorize": bool(mse < threshold),
    }
