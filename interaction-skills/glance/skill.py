"""glance interaction-skill — type-aware deep inspection.

skill.run(inputs_dir) loads the first artifact in inputs_dir, calls
helpers.glance() to produce the human-readable summary, and packages a
structured dict that downstream predicates can validate.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make the data-harness top-level modules (helpers, capabilities, ...) importable
# regardless of where check_skill invokes us from.
_HERE = Path(__file__).resolve()
_DATA_HARNESS = _HERE.parent.parent.parent
if str(_DATA_HARNESS) not in sys.path:
    sys.path.insert(0, str(_DATA_HARNESS))


def run(inputs_dir: Path) -> dict:
    inputs_dir = Path(inputs_dir)
    parquets = sorted(inputs_dir.glob("*.parquet"))
    if not parquets:
        raise FileNotFoundError(f"no .parquet under {inputs_dir}")
    import polars as pl
    from helpers import glance as helpers_glance

    df = pl.read_parquet(parquets[0])
    return {
        "kind":        "DataFrame",
        "n_rows":      int(df.height),
        "n_cols":      int(df.width),
        "columns":     list(df.columns),
        "schema":      {c: str(t) for c, t in zip(df.columns, df.dtypes)},
        "nulls":       {c: int(df[c].null_count()) for c in df.columns},
        "summary_str": helpers_glance(df),
    }
