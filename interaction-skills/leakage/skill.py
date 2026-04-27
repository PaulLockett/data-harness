"""leakage — feature/target correlation scan."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
if str(_HERE.parent.parent.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent.parent.parent))


def run(inputs_dir: Path, threshold: float = 0.95) -> dict:
    inputs_dir = Path(inputs_dir)
    import polars as pl
    import numpy as np

    df = pl.read_parquet(inputs_dir / "features.parquet")
    tgt_file = inputs_dir / "target.txt"
    target_col = tgt_file.read_text().strip() if tgt_file.exists() else df.columns[-1]
    if target_col not in df.columns:
        raise ValueError(f"target_col {target_col!r} not in {df.columns}")
    y = df[target_col].drop_nulls().to_numpy().astype(float)

    correlations: list[tuple[str, float]] = []
    for col in df.columns:
        if col == target_col:
            continue
        if not str(df[col].dtype).startswith(("Int", "Float", "UInt")):
            continue
        x = df[col].drop_nulls().to_numpy().astype(float)
        n = min(len(x), len(y))
        if n < 2:
            continue
        x, yc = x[:n], y[:n]
        if np.std(x) == 0 or np.std(yc) == 0:
            corr = 0.0
        else:
            corr = float(np.corrcoef(x, yc)[0, 1])
        correlations.append((col, corr))
    correlations.sort(key=lambda kv: -abs(kv[1]))
    suspect = [col for col, c in correlations if abs(c) > threshold]
    max_abs = max((abs(c) for _, c in correlations), default=0.0)
    return {
        "target_col":       target_col,
        "max_correlation":  float(max_abs),
        "top_correlated":   [(col, round(c, 4)) for col, c in correlations[:5]],
        "suspect_features": suspect,
    }
