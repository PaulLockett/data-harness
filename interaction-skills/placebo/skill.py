"""placebo — randomization refutation."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
if str(_HERE.parent.parent.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent.parent.parent))


def run(inputs_dir: Path, n_resamples: int = 200) -> dict:
    inputs_dir = Path(inputs_dir)
    import polars as pl
    import numpy as np

    df = pl.read_parquet(inputs_dir / "data.parquet")
    t = df["treatment"].to_numpy().astype(int)
    y = df["outcome"].to_numpy().astype(float)

    true_effect = float(y[t == 1].mean() - y[t == 0].mean())

    rng = np.random.default_rng(42)
    placebo_effects = []
    for _ in range(n_resamples):
        shuffled = rng.permutation(t)
        if shuffled.sum() == 0 or shuffled.sum() == len(shuffled):
            continue
        placebo_effects.append(float(y[shuffled == 1].mean() - y[shuffled == 0].mean()))
    placebo_mean_abs = float(np.mean(np.abs(placebo_effects))) if placebo_effects else 0.0
    placebo_ratio = float(placebo_mean_abs / abs(true_effect)) if true_effect != 0 else 0.0
    return {
        "n":                    int(len(y)),
        "true_effect":          true_effect,
        "placebo_effect":       placebo_mean_abs,
        "placebo_ratio":        placebo_ratio,
        "placebo_passes":       bool(placebo_ratio < 0.5),
        "n_placebo_resamples":  int(len(placebo_effects)),
    }
