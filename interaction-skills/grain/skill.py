"""grain — primary-key uniqueness check."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
if str(_HERE.parent.parent.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent.parent.parent))


def run(inputs_dir: Path) -> dict:
    inputs_dir = Path(inputs_dir)
    parquets = sorted(inputs_dir.glob("*.parquet"))
    if not parquets:
        raise FileNotFoundError(f"no .parquet under {inputs_dir}")
    import polars as pl

    df = pl.read_parquet(parquets[0])
    key_file = inputs_dir / "key.txt"
    key_col = key_file.read_text().strip() if key_file.exists() else df.columns[0]
    if key_col not in df.columns:
        raise ValueError(f"key_col {key_col!r} not in {df.columns}")
    counts = df.group_by(key_col).count().filter(pl.col("count") > 1)
    duplicates = [str(v) for v in counts[key_col].to_list()]
    return {
        "key_col":            key_col,
        "n_rows":             int(df.height),
        "n_unique_keys":      int(df[key_col].n_unique()),
        "duplicate_keys":     duplicates,
        "pk_violation_count": int(counts[key_col].sum() if counts.height else 0),
        "is_valid_pk":        len(duplicates) == 0,
    }
