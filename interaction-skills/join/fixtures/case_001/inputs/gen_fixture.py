"""Plant a 1:N join (5 users × 3 sessions each)."""
import polars as pl
from pathlib import Path

HERE = Path(__file__).resolve().parent

left = pl.DataFrame({
    "user_id": [1, 2, 3, 4, 5],
    "name":    ["A", "B", "C", "D", "E"],
})
right = pl.DataFrame({
    "user_id":    sorted([1, 2, 3, 4, 5] * 3),
    "session_id": list(range(15)),
    "score":     [0.1 * i for i in range(15)],
})
left.write_parquet(HERE / "left.parquet")
right.write_parquet(HERE / "right.parquet")
(HERE / "key.txt").write_text("user_id\n")
print(f"wrote left ({left.height}) + right ({right.height}) — 1:N expected, fanout=3")
