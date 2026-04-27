"""correct — multiple-comparison p-value correction (BH/FDR or Bonferroni)."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
if str(_HERE.parent.parent.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent.parent.parent))


def _bh(p):
    """Benjamini-Hochberg step-up FDR; returns q-values in original order."""
    import numpy as np
    p = np.asarray(p, dtype=float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order]
    q_sorted = ranked * n / (np.arange(1, n + 1))
    # enforce monotonicity from the top down
    q_sorted = np.minimum.accumulate(q_sorted[::-1])[::-1]
    q_sorted = np.minimum(q_sorted, 1.0)
    q = np.empty_like(q_sorted)
    q[order] = q_sorted
    return q


def run(inputs_dir: Path) -> dict:
    inputs_dir = Path(inputs_dir)
    import polars as pl
    import numpy as np

    df = pl.read_parquet(inputs_dir / "pvals.parquet")
    p = df["p"].to_numpy().astype(float)
    method_file = inputs_dir / "method.txt"
    method = (method_file.read_text().strip() if method_file.exists() else "bh")
    alpha_file = inputs_dir / "alpha.txt"
    alpha = float(alpha_file.read_text().strip() if alpha_file.exists() else "0.05")

    n = len(p)
    if method == "bh":
        q = _bh(p)
    elif method == "bonferroni":
        q = np.minimum(p * n, 1.0)
    else:
        raise ValueError(f"unknown method {method!r}")

    return {
        "method":                  method,
        "alpha":                   float(alpha),
        "n_total":                 int(n),
        "n_significant_at_alpha":  int((q < alpha).sum()),
        "q":                       [float(x) for x in q],
    }
