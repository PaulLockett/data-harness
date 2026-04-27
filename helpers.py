"""data-harness — substrate primitives across 10 tiers + capability-derived helpers.

Self-imposed cap: keep this file ≤900 lines so the substrate stays
reviewable end-to-end. Heavy deps (torch, transformers, astropy, zarr)
are imported lazily inside primitives so import cost stays cheap and
the daemon cold-starts in <1s without loading torch.

Tier 1   compute / IO
Tier 2   tabular spine (DuckDB + Polars)
Tier 3   decoders (PDF, images, video, audio, FITS, Zarr) — many stubbed for v0
Tier 4   foundation models (one-liner wrappers around models.resolve)
Tier 5   math / optimization (re-exports + a few helpers)
Tier 6   orchestration (cache_by_hash, checkpoint, budget(), provenance_log, diff_artifact)
Tier 7   geospatial — stubbed for v0
Tier 8   graph — stubbed for v0
Tier 9   vector — partially stubbed for v0
Tier 10  streaming — stubbed for v0
Plus glance() (verification primitive) and capability-derived helpers.
"""
from __future__ import annotations

import json
import os
import pickle
import sys
import time as time_module
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from hashlib import blake2b
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Optional

import capabilities as _caps_mod
from deadlines import (
    Budget,
    BudgetExceeded,
    Deadline,
    current_deadline,
    push_deadline,
)


# ─── Cap entry point ─────────────────────────────────────────────────────────

def caps() -> "_caps_mod.Capabilities":
    """Snapshot of current Capabilities. Read each primitive call entry; never cache long."""
    return _caps_mod.current()


# ─── Capability-derived helpers (mandatory; called by skills) ───────────────

def workers_for(c: "_caps_mod.Capabilities", kind: str) -> int:
    """Worker count derived from CPU count + load + tenancy + battery."""
    headroom = 1.0
    if c.cpu_load_1m and c.cpu_logical:
        headroom = max(0.1, 1.0 - (c.cpu_load_1m / c.cpu_logical))
    if c.is_shared:
        headroom *= 0.5
    if c.on_battery:
        headroom *= 0.6
    cores = c.cpu_logical or 1
    if kind == "io":
        return max(4, min(64, int(cores * 8 * headroom)))
    if kind == "cpu_gil":
        return max(1, int(cores * headroom))
    if kind == "cpu_mp":
        return max(1, int((cores - 1) * headroom))
    return 1


def batch_size_for(c: "_caps_mod.Capabilities", model_bytes: int, per_seq_bytes: int) -> int:
    """Batch size from model footprint + per-sequence activation budget."""
    if c.has_gpu:
        gpu = next((g for g in c.gpus if g.free_vram_bytes > model_bytes + (1 << 30)), None)
        if gpu:
            free = gpu.free_vram_bytes - model_bytes - (1 << 30)
            return max(1, free // max(per_seq_bytes, 1))
    if model_bytes > c.ram_available_bytes // 4:
        return 1
    return 8


def chunk_size_for(c: "_caps_mod.Capabilities", embed_max: int, llm_ctx: int) -> int:
    """Chunk size capped by regime + embed/LLM ctx limits."""
    regime_caps = {
        "TINY": 256, "LAPTOP-CPU": 384, "LAPTOP-GPU": 512,
        "WORKSTATION": 1024, "SERVER-1GPU": 1536, "SERVER-MULTI": 2048,
        "HOSTED-ONLY": 1024,
    }
    cap = regime_caps.get(c.regime, 512)
    return min(embed_max, llm_ctx // 4, cap)


def duckdb_pragmas(c: "_caps_mod.Capabilities") -> dict:
    """DuckDB pragmas tuned to the current host."""
    mem = max(c.ram_available_bytes // 2, 1 << 28)
    threads = max(1, (c.cpu_logical or 2) - 1)
    scratch = (Path(os.environ.get("DH_SCRATCH_DIR", "~/.data-harness")).expanduser() / "duckdb_scratch")
    scratch.mkdir(parents=True, exist_ok=True)
    return {
        "memory_limit": f"{mem // (1 << 20)}MiB",
        "threads": str(threads),
        "temp_directory": str(scratch),
        "max_temp_directory_size": "20GiB",
    }


def vector_index_kind(n: int, dim: int, c: "_caps_mod.Capabilities") -> str:
    """Pick vector index family by corpus size + VRAM."""
    if n < 10_000:
        return "Flat"
    fits_ram = (n * dim * 4) < (c.ram_available_bytes // 4)
    if n < 2_000_000 and fits_ram:
        return "HNSW"
    if n < 20_000_000:
        return "HNSW,SQ8"
    if n < 200_000_000:
        return "IVF65536_HNSW32,PQ32"
    return "IVF_GPU"


def should_download(model_size_gb: float, c: "_caps_mod.Capabilities",
                    deadline: Optional[Deadline] = None,
                    threshold: float = 0.5) -> str:
    """Gate before HF model download. Returns 'DOWNLOAD' or 'USE_HOSTED'."""
    storage_budget_gb = (c.declared.get("storage", {}) or {}).get("budget_gb", 20)
    used_gb = (c.hf_cache_size_bytes or 0) / (1 << 30)
    if used_gb + model_size_gb > storage_budget_gb:
        return "USE_HOSTED"
    if c.on_battery and model_size_gb > 2:
        return "USE_HOSTED"
    bw_MBps = (c.network.measured_bandwidth_MBps if (c.network and c.network.measured_bandwidth_MBps) else 6.25)
    # bandwidth in MB/s; size in GB; eta in seconds
    eta_seconds = (model_size_gb * 1024) / max(bw_MBps, 0.5)
    if deadline and eta_seconds > deadline.remaining() * threshold:
        return "USE_HOSTED"
    if bw_MBps < 3.0 and eta_seconds > 600:
        return "USE_HOSTED"
    return "DOWNLOAD"


# ─── Tier 1: compute and IO ──────────────────────────────────────────────────

def read_text(path) -> str:
    return Path(path).read_text()


def read_bytes(path) -> bytes:
    return Path(path).read_bytes()


def read_json(path) -> Any:
    return json.loads(Path(path).read_text())


def write_text(path, s: str) -> None:
    Path(path).write_text(s)


def write_json(path, obj, *, indent: int = 2) -> None:
    Path(path).write_text(json.dumps(obj, indent=indent, default=str))


def http_get(url: str, **kw) -> bytes:
    import httpx
    return httpx.get(url, **kw).content


def http_post(url: str, *, json=None, data=None, **kw) -> bytes:
    import httpx
    return httpx.post(url, json=json, data=data, **kw).content


def ls(path: str = ".", *, recursive: bool = False, glob: Optional[str] = None) -> list:
    p = Path(path)
    if recursive:
        return sorted(p.rglob(glob or "*"))
    if glob:
        return sorted(p.glob(glob))
    return sorted(p.iterdir())


def bulk(fn: Callable, items: Iterable, workers: Optional[int] = None) -> list:
    """Parallel apply. Defaults workers via workers_for(caps(), 'io')."""
    workers = workers or workers_for(caps(), "io")
    items = list(items)
    if not items:
        return []
    if len(items) == 1 or workers == 1:
        return [fn(x) for x in items]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(fn, items))


# ─── Tier 2: tabular spine (DuckDB + Polars) ─────────────────────────────────

_DUCK = None


def _duckdb():
    """Get-or-create DuckDB connection, configured via duckdb_pragmas(caps())."""
    global _DUCK
    if _DUCK is not None:
        return _DUCK
    import duckdb
    _DUCK = duckdb.connect(":memory:")
    for k, v in duckdb_pragmas(caps()).items():
        try:
            _DUCK.execute(f"SET {k} = '{v}'")
        except Exception:
            pass
    _DUCK.execute("CREATE SCHEMA IF NOT EXISTS scratch")
    return _DUCK


def load(uri, **opts):
    """Load any URI/path into a Polars DataFrame, raw bytes, or text.

    .csv/.tsv/.parquet/.json/.jsonl/.xlsx → pl.DataFrame
    .txt or no extension that's plaintext → str
    bytes-like binary → bytes
    s3:// or postgres:// → DuckDB query

    Polars is imported lazily only on tabular branches so plaintext
    loads work without polars installed (matters for the smoke-test
    install depth where the user only pip-installed psutil/cpuinfo/
    duckdb/polars).
    """
    p = str(uri)
    low = p.lower()
    if low.endswith((".csv", ".tsv")):
        import polars as pl
        sep = "\t" if low.endswith(".tsv") else ","
        return pl.read_csv(p, separator=sep, **opts)
    if low.endswith(".parquet"):
        import polars as pl
        return pl.read_parquet(p, **opts)
    if low.endswith((".jsonl", ".ndjson")):
        import polars as pl
        return pl.read_ndjson(p, **opts)
    if low.endswith(".json"):
        import polars as pl
        return pl.read_json(p, **opts)
    if low.endswith((".xlsx", ".xls")):
        import polars as pl
        return pl.read_excel(p, **opts)
    if low.startswith(("s3://", "postgres://")):
        return query(f"SELECT * FROM '{p}'")
    # plaintext or no extension — return text content; bytes if undecodable
    try:
        return Path(p).read_text()
    except UnicodeDecodeError:
        return Path(p).read_bytes()


def query(sql: str, **named_dfs):
    """DuckDB query. **named_dfs registers Polars/Pandas DataFrames as views."""
    import polars as pl
    con = _duckdb()
    for name, df in named_dfs.items():
        if hasattr(df, "to_arrow"):
            con.register(name, df.to_arrow())
        else:
            con.register(name, df)
    res = con.execute(sql).pl()
    for name in named_dfs:
        try:
            con.unregister(name)
        except Exception:
            pass
    return res


def query_spatial(sql: str, **named_dfs):
    con = _duckdb()
    try:
        con.execute("INSTALL spatial; LOAD spatial;")
    except Exception:
        pass
    return query(sql, **named_dfs)


def query_fts(sql: str, **named_dfs):
    con = _duckdb()
    try:
        con.execute("INSTALL fts; LOAD fts;")
    except Exception:
        pass
    return query(sql, **named_dfs)


def materialize(name: str, df) -> None:
    """Persist a DataFrame as scratch.<name> in DuckDB."""
    con = _duckdb()
    if hasattr(df, "to_arrow"):
        con.register("_tmp", df.to_arrow())
    else:
        con.register("_tmp", df)
    con.execute(f"CREATE OR REPLACE TABLE scratch.{name} AS SELECT * FROM _tmp")
    con.unregister("_tmp")


def tables() -> list:
    """List materialized tables in the scratch schema."""
    con = _duckdb()
    rs = con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='scratch'"
    ).fetchall()
    return [r[0] for r in rs]


def peek(obj, n: int = 5) -> str:
    """Quick type-aware preview. For deeper inspection use glance()."""
    try:
        import polars as pl
    except Exception:
        pl = None
    try:
        import pandas as pd
    except Exception:
        pd = None
    if pl and isinstance(obj, pl.DataFrame):
        return f"pl.DataFrame[{obj.height} rows × {obj.width} cols]\n{str(obj.head(n))}"
    if pd and isinstance(obj, pd.DataFrame):
        return f"pd.DataFrame[{len(obj)} rows × {len(obj.columns)} cols]\n{obj.head(n)}"
    if isinstance(obj, dict):
        keys = list(obj.keys())
        return f"dict[{len(keys)} keys] keys={keys[:8]}{'…' if len(keys) > 8 else ''}"
    if isinstance(obj, (list, tuple)):
        sample = obj[:n]
        return f"{type(obj).__name__}[{len(obj)}] {sample}"
    if isinstance(obj, (bytes, bytearray)):
        return f"bytes[{len(obj)}] head={obj[:64]!r}"
    if isinstance(obj, str):
        return f"str[{len(obj)} chars] {obj[:200]!r}"
    if isinstance(obj, Path):
        try:
            stat = obj.stat()
            return f"Path({obj}) size={stat.st_size} mtime={time_module.ctime(stat.st_mtime)}"
        except Exception:
            return f"Path({obj}) [missing]"
    return f"{type(obj).__name__}: {str(obj)[:200]}"


# ─── Verification primitive: glance() ────────────────────────────────────────

def glance(obj, n: int = 5) -> str:
    """Deep type-aware verification. Returns a multi-line summary fit for inspection.

    Must handle every artifact a skill produces: Polars df, pandas df,
    dict, list, PIL Image, bytes, Path, np.ndarray, GeoDataFrame, Graph,
    HDUList, Zarr Array. The agent calls glance() after every meaningful
    transform so it verifies what it just produced before assuming.
    """
    # tabular
    try:
        import polars as pl
        if isinstance(obj, pl.DataFrame):
            schema = {c: str(t) for c, t in zip(obj.columns, obj.dtypes)}
            nulls = {c: int(obj[c].null_count()) for c in obj.columns}
            return (
                f"pl.DataFrame[{obj.height} rows × {obj.width} cols]\n"
                f"  schema:   {schema}\n"
                f"  nulls:    {nulls}\n"
                f"  head({n}):\n{obj.head(n)}"
            )
    except Exception:
        pass
    try:
        import pandas as pd
        if isinstance(obj, pd.DataFrame):
            return (
                f"pd.DataFrame[{len(obj)} rows × {len(obj.columns)} cols]\n"
                f"  dtypes:   {dict(obj.dtypes.astype(str))}\n"
                f"  nulls:    {obj.isna().sum().to_dict()}\n"
                f"  head({n}):\n{obj.head(n)}"
            )
    except Exception:
        pass
    # numpy
    try:
        import numpy as np
        if isinstance(obj, np.ndarray):
            return f"np.ndarray shape={obj.shape} dtype={obj.dtype} first={obj.flatten()[:8].tolist()}"
    except Exception:
        pass
    # PIL
    try:
        from PIL import Image
        if isinstance(obj, Image.Image):
            return f"PIL.Image mode={obj.mode} size={obj.size}"
    except Exception:
        pass
    # geopandas
    try:
        import geopandas as gpd
        if isinstance(obj, gpd.GeoDataFrame):
            return (
                f"gpd.GeoDataFrame[{len(obj)} rows × {len(obj.columns)} cols]\n"
                f"  crs={obj.crs}\n  geometry_type={obj.geometry.geom_type.value_counts().to_dict()}"
            )
    except Exception:
        pass
    # networkx graph
    try:
        import networkx as nx
        if isinstance(obj, (nx.Graph, nx.DiGraph, nx.MultiGraph, nx.MultiDiGraph)):
            return f"{type(obj).__name__} nodes={obj.number_of_nodes()} edges={obj.number_of_edges()}"
    except Exception:
        pass
    # astropy HDUList
    try:
        from astropy.io.fits import HDUList
        if isinstance(obj, HDUList):
            return f"astropy.HDUList n={len(obj)} ext_names={[h.name for h in obj]}"
    except Exception:
        pass
    # zarr Array
    try:
        import zarr
        if isinstance(obj, zarr.Array):
            return f"zarr.Array shape={obj.shape} dtype={obj.dtype} chunks={obj.chunks}"
    except Exception:
        pass
    # dict / list / bytes / Path / str
    return peek(obj, n=n)


def assert_(cond, msg: str = "assertion failed"):
    """The 'assert' refute-family primitive — exposes predicate machinery as callable.

    Refute family (assert / placebo / overfit_one_batch / saturation /
    disaggregate) answers "could I be wrong?" by attacking your own
    result. assert_ is the primitive contract: skills compose it to
    encode invariants the answer must satisfy.
    """
    if not cond:
        raise AssertionError(msg)
    return True


def image_show(img):
    """Render an image to the orchestrator's eyes (Claude Code). Print path."""
    # In Claude Code, the orchestrator can read image paths via the Read tool.
    # We just save the image to a temp path and print it; the orchestrator reads it.
    import tempfile
    try:
        from PIL import Image
        if isinstance(img, Image.Image):
            f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            img.save(f.name)
            print(f"[image_show] {f.name}")
            return f.name
    except Exception:
        pass
    if isinstance(img, (str, Path)):
        print(f"[image_show] {img}")
        return str(img)
    raise TypeError(f"image_show: unsupported {type(img)}")


# ─── Tier 3: decoders (mostly stubbed for v0) ───────────────────────────────

def pdf_pages(path):
    import pypdf
    return pypdf.PdfReader(str(path)).pages


def pdf_render(path, *, dpi: int = 150):
    raise NotImplementedError("pdf_render: implement when the first PDF-rendering skill lands")


def pdf_layout(path):
    raise NotImplementedError("pdf_layout: implement when the first layout-aware PDF skill lands")


def docx_open(path):
    import docx
    return docx.Document(str(path))


def pptx_open(path):
    from pptx import Presentation
    return Presentation(str(path))


def xlsx_sheets(path):
    import openpyxl
    return openpyxl.load_workbook(str(path), data_only=True).sheetnames


def image_open(path):
    from PIL import Image
    return Image.open(str(path))


def video_frames(path, *, fps: float = 1.0):
    raise NotImplementedError("video_frames: implement for SoccerNet")


def audio_load(path):
    import soundfile as sf
    return sf.read(str(path))


def fits_open(path):
    from astropy.io import fits
    return fits.open(str(path))


def zarr_open(path):
    import zarr
    return zarr.open(str(path))


# ─── Tier 4: foundation models (one-liners around models.resolve) ───────────

def vlm(image, prompt: str, **opts):
    from models import resolve
    return resolve("vlm", caps())(image, prompt, **opts)


def llm(prompt: str, *, system: Optional[str] = None, **opts):
    from models import resolve
    return resolve("llm", caps())(prompt, system=system, **opts)


def embed(items, **opts):
    from models import resolve
    return resolve("embed", caps())(items, **opts)


def embed_late(docs, **opts):
    from models import resolve
    return resolve("embed_late", caps())(docs, **opts)


def sam(image, *, points=None, boxes=None):
    from models import resolve
    return resolve("sam", caps())(image, points=points, boxes=boxes)


def ocr(image):
    from models import resolve
    return resolve("ocr", caps())(image)


def asr(audio):
    from models import resolve
    return resolve("asr", caps())(audio)


def pii_detect(text_or_df):
    from models import resolve
    return resolve("pii", caps())(text_or_df)


def rerank(query_str: str, docs, **opts):
    from models import resolve
    return resolve("rerank", caps())(query_str, docs, **opts)


# ─── Tier 5: math / optimization (re-exports + helpers) ─────────────────────

def conformal(scores, alpha: float = 0.1):
    raise NotImplementedError("conformal: implement when first quantify skill needs it")


# ─── Tier 6: orchestration ──────────────────────────────────────────────────

_CACHE_DIR = Path(os.environ.get("DH_SCRATCH_DIR", "~/.data-harness")).expanduser() / "cache"


def cache_by_hash(fn: Callable) -> Callable:
    """Decorator: cache fn(*args, **kwargs) → result on disk by content-hash."""
    @wraps(fn)
    def wrapped(*args, **kwargs):
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        key = blake2b(
            (fn.__module__ + ":" + fn.__name__).encode() +
            pickle.dumps((args, sorted(kwargs.items()))),
            digest_size=16,
        ).hexdigest()
        path = _CACHE_DIR / f"{key}.pkl"
        if path.exists():
            return pickle.loads(path.read_bytes())
        result = fn(*args, **kwargs)
        path.write_bytes(pickle.dumps(result))
        return result
    return wrapped


def checkpoint(name: str, fn: Callable):
    """Memoize fn() in the DuckDB scratch schema under `name`."""
    if name in tables():
        return query(f"SELECT * FROM scratch.{name}")
    df = fn()
    materialize(name, df)
    return df


@contextmanager
def budget(*, seconds: Optional[float] = None,
           dollars: Optional[float] = None,
           deadline: Optional[Deadline] = None) -> Iterator[Budget]:
    """Scope a deadline + dollar cap. Inner code reads `current_deadline()`."""
    parent = deadline or current_deadline()
    if seconds is not None:
        dl = parent.descend(seconds)
    else:
        dl = parent
    b = Budget(deadline=dl, max_dollars=dollars, spent_dollars=0.0)
    with push_deadline(dl):
        yield b


_PROVENANCE_PATH = (
    Path(os.environ.get("DH_SCRATCH_DIR", "~/.data-harness")).expanduser() / "provenance.jsonl"
)


def provenance_log(action: str, *, inputs=None, outputs=None) -> None:
    """Append-only JSONL log of meaningful actions (with hashed inputs/outputs)."""
    _PROVENANCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    def _hash(o):
        try:
            return blake2b(pickle.dumps(o), digest_size=8).hexdigest()
        except Exception:
            return f"<{type(o).__name__}>"
    entry = {
        "ts": time_module.time(),
        "action": action,
        "inputs": _hash(inputs) if inputs is not None else None,
        "outputs": _hash(outputs) if outputs is not None else None,
    }
    with _PROVENANCE_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def diff_artifact(old, new) -> dict:
    """Diff two DataFrames by row/col delta. Stub for non-tabular types."""
    try:
        import polars as pl
        if isinstance(old, pl.DataFrame) and isinstance(new, pl.DataFrame):
            return {
                "rows_added":   max(0, new.height - old.height),
                "rows_removed": max(0, old.height - new.height),
                "cols_added":   sorted(set(new.columns) - set(old.columns)),
                "cols_removed": sorted(set(old.columns) - set(new.columns)),
            }
    except Exception:
        pass
    raise NotImplementedError(f"diff_artifact: unsupported types ({type(old)}, {type(new)})")


# ─── Tier 7: geospatial — stubbed for v0 ────────────────────────────────────

def geo_load(path):
    import geopandas as gpd
    return gpd.read_file(str(path))


def crs_align(*args, **kw):
    raise NotImplementedError("crs_align: implement for GFW domain")


# ─── Tier 8: graph — stubbed for v0 ─────────────────────────────────────────

def graph_build(edges):
    import networkx as nx
    g = nx.Graph()
    g.add_edges_from(edges)
    return g


def centrality(g, kind: str = "degree"):
    raise NotImplementedError("centrality: implement for USAspending domain")


# ─── Tier 9: vector ─────────────────────────────────────────────────────────

def vector_index(vectors, *, kind: Optional[str] = None):
    if kind is None:
        c = caps()
        n = len(vectors) if hasattr(vectors, "__len__") else 0
        dim = len(vectors[0]) if n else 0
        kind = vector_index_kind(n, dim, c)
    raise NotImplementedError(
        f"vector_index({kind=}): implement when first retrieval skill needs it"
    )


# ─── Tier 10: streaming — stubbed for v0 ────────────────────────────────────

def stream_iter(source, **opts):
    raise NotImplementedError("stream_iter: implement for ZTF Avro stream")


# ─── End of helpers.py — keep ≤900 lines so the substrate stays reviewable ──
