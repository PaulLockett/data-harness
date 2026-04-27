"""drift — distributional shift between two snapshots."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
if str(_HERE.parent.parent.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent.parent.parent))


def run(inputs_dir: Path) -> dict:
    inputs_dir = Path(inputs_dir)
    a_path = inputs_dir / "a.parquet"
    b_path = inputs_dir / "b.parquet"
    if not (a_path.exists() and b_path.exists()):
        raise FileNotFoundError(f"need a.parquet and b.parquet under {inputs_dir}")
    import polars as pl
    import numpy as np

    a = pl.read_parquet(a_path)
    b = pl.read_parquet(b_path)
    common = [c for c in a.columns if c in b.columns]
    by_column: dict[str, float] = {}
    for col in common:
        ta, tb = str(a[col].dtype), str(b[col].dtype)
        if ta.startswith(("Int", "Float", "UInt")) and tb.startswith(("Int", "Float", "UInt")):
            xa = a[col].drop_nulls().to_numpy().astype(float)
            xb = b[col].drop_nulls().to_numpy().astype(float)
            if len(xa) == 0 or len(xb) == 0:
                by_column[col] = 0.0
                continue
            qa = np.quantile(xa, [0.1, 0.5, 0.9])
            qb = np.quantile(xb, [0.1, 0.5, 0.9])
            denom = float(np.std(np.concatenate([xa, xb]))) + 1e-9
            by_column[col] = float(np.mean(np.abs(qa - qb)) / denom)
        else:
            # categorical placeholder: total variation distance over value counts
            va = dict(a[col].value_counts().rows())
            vb = dict(b[col].value_counts().rows())
            keys = set(va) | set(vb)
            na = sum(va.values()) or 1
            nb = sum(vb.values()) or 1
            tvd = 0.5 * sum(abs(va.get(k, 0) / na - vb.get(k, 0) / nb) for k in keys)
            by_column[col] = float(tvd)
    overall = float(max(by_column.values())) if by_column else 0.0
    return {
        "metric":    "quantile_shift",
        "score":     overall,
        "alarm":     bool(overall > 0.5),
        "by_column": by_column,
    }
