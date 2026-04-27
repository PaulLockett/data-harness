"""Plant a 3-row id overlap between train and test."""
import polars as pl
from pathlib import Path

HERE = Path(__file__).resolve().parent

train = pl.DataFrame({"id": list(range(1, 11)), "y": [0.1 * i for i in range(10)]})
test = pl.DataFrame({"id": list(range(8, 16)), "y": [0.2 * i for i in range(8)]})
train.write_parquet(HERE / "train.parquet")
test.write_parquet(HERE / "test.parquet")
(HERE / "key.txt").write_text("id\n")
print(f"wrote train ({train.height}) + test ({test.height}) — 3-row planted overlap on id")
