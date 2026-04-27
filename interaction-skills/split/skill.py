"""split — train/test leakage check."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
if str(_HERE.parent.parent.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent.parent.parent))


def run(inputs_dir: Path) -> dict:
    inputs_dir = Path(inputs_dir)
    import polars as pl

    train = pl.read_parquet(inputs_dir / "train.parquet")
    test = pl.read_parquet(inputs_dir / "test.parquet")
    key_file = inputs_dir / "key.txt"
    key = (key_file.read_text().strip() if key_file.exists() else train.columns[0])
    train_keys = set(train[key].to_list())
    test_keys = set(test[key].to_list())
    overlap = sorted(train_keys & test_keys)
    overlap_count = len(overlap)
    denom = max(1, min(train.height, test.height))
    return {
        "kind":             "random",
        "train_rows":       int(train.height),
        "test_rows":        int(test.height),
        "overlap_count":    int(overlap_count),
        "leak_score":       float(overlap_count / denom),
        "group_collisions": [str(v) for v in overlap[:20]],
    }
