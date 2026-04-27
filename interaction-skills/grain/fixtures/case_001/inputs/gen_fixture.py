"""Plant a duplicate id and write data.parquet + key.txt."""
import polars as pl
from pathlib import Path

HERE = Path(__file__).resolve().parent

df = pl.DataFrame({
    "id":    [1, 2, 3, 3, 4, 5],   # 3 appears twice
    "value": [10, 20, 30, 31, 40, 50],
})
df.write_parquet(HERE / "data.parquet")
(HERE / "key.txt").write_text("id\n")
print(f"wrote data.parquet (planted duplicate id=3); key=id")
