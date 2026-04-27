"""join — cardinality + fanout characterization."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
if str(_HERE.parent.parent.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent.parent.parent))


def run(inputs_dir: Path) -> dict:
    inputs_dir = Path(inputs_dir)
    import polars as pl

    left = pl.read_parquet(inputs_dir / "left.parquet")
    right = pl.read_parquet(inputs_dir / "right.parquet")
    key_file = inputs_dir / "key.txt"
    key = (key_file.read_text().strip() if key_file.exists()
           else next(c for c in left.columns if c in right.columns))

    left_unique = left[key].n_unique() == left.height
    right_unique = right[key].n_unique() == right.height
    cardinality = ("1:1" if left_unique and right_unique
                   else "1:N" if left_unique
                   else "N:1" if right_unique
                   else "N:M")

    joined = left.join(right, on=key, how="inner")
    fanout = (joined.group_by(key).count()["count"].max()
              if joined.height else 0)
    missing_left = left.height - left.join(right, on=key, how="inner").select(key).n_unique()
    missing_right = right.height - right.join(left, on=key, how="inner").select(key).n_unique()
    return {
        "key":           key,
        "cardinality":   cardinality,
        "left_rows":     int(left.height),
        "right_rows":    int(right.height),
        "joined_rows":   int(joined.height),
        "fanout_max":    int(fanout or 0),
        "missing_left":  int(missing_left),
        "missing_right": int(missing_right),
    }
