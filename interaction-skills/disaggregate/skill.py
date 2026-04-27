"""disaggregate — by-group means + heterogeneity score."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
if str(_HERE.parent.parent.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent.parent.parent))


def run(inputs_dir: Path) -> dict:
    inputs_dir = Path(inputs_dir)
    import polars as pl
    import numpy as np

    df = pl.read_parquet(inputs_dir / "data.parquet")
    grand = float(df["outcome"].mean())
    grouped = df.group_by("group").agg([
        pl.col("outcome").count().alias("n"),
        pl.col("outcome").mean().alias("mean"),
        pl.col("outcome").std().fill_null(0.0).alias("std"),
    ]).sort("group")

    groups = []
    means = []
    ns = []
    for row in grouped.iter_rows(named=True):
        groups.append({
            "group": str(row["group"]),
            "n":     int(row["n"]),
            "mean":  float(row["mean"]),
            "std":   float(row["std"]),
        })
        means.append(float(row["mean"]))
        ns.append(int(row["n"]))

    means_arr = np.array(means)
    ns_arr = np.array(ns)
    between_var = float(np.average((means_arr - grand) ** 2, weights=ns_arr) if ns_arr.sum() > 0 else 0.0)
    total_var = float(df["outcome"].var() or 0.0)
    within_var = max(0.0, total_var - between_var)
    return {
        "n_groups":            len(groups),
        "groups":              groups,
        "between_var":         between_var,
        "within_var":          within_var,
        "total_var":           total_var,
        "heterogeneity_score": float(between_var / total_var) if total_var > 0 else 0.0,
        "max_min_ratio":       float(max(means) / min(means)) if min(means) > 0 else 0.0,
    }
