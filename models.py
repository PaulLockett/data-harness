"""data-harness models — per-primitive resolve tables keyed by regime.

Capability-aware foundation-model resolution. Every primitive that
needs a model (`vlm`, `llm`, `embed`, `rerank`, `ocr`, `transcribe`,
`vad`, `nli`, `pii`) calls `models.resolve(kind, caps)` instead of
hard-coding a provider. The resolve table maps each primitive ×
hardware regime to an ordered chain of model identifiers (hosted-API
endpoints + local Hugging Face fallbacks), so the same skill code
runs on a TINY laptop, a SERVER-MULTI cluster, or a HOSTED-ONLY box
without a single regime check inside the skill itself.

Discipline: hard-fail on unfittable, WARN on non-primary pick, never
silently swap kinds (asking for `vlm` and getting an `llm` would be
a contract break).

The current snapshot ships RESOLVE TABLES + a stub `resolve()` that
raises NotImplementedError until the cassette layer wires its first
real client. The cassette machinery in `check_skill.py` replays
predicate-relevant calls without ever invoking `resolve()` for the
v0 green path, so this module is forward-compatible scaffolding.
The first skill that actually needs a model (likely an embedder for
a quantify-family case like `uncertainty` or `calibrate`) will land
the real client lookups.
"""
from __future__ import annotations

import os
import sys
from typing import Callable

import capabilities as _caps_mod


class CapabilityError(RuntimeError):
    """Raised when no model in the resolve chain fits current capabilities."""
    def __init__(self, primitive: str, regime: str, suggested_downgrade: str):
        super().__init__(
            f"No model fits regime={regime} for primitive={primitive}. "
            f"Suggested downgrade: {suggested_downgrade}"
        )
        self.primitive = primitive
        self.regime = regime
        self.suggested_downgrade = suggested_downgrade


# Per-primitive resolve table: regime → ordered chain of model identifiers.
# Production deployments should pin to revision SHAs (e.g.
# `hf:Qwen/Qwen2.5-VL-3B-Q4_K_M@<sha>`) so the same physical bytes
# resolve every time. The current snapshot uses logical names for
# readability; revision-pinning lands when the first model-using
# skill records its cassette.
RESOLVE_TABLE = {
    "vlm": {
        "TINY":         ["hosted:gemini-2.5-flash"],
        "LAPTOP-CPU":   ["hf:Qwen/Qwen2.5-VL-3B-Q4_K_M", "hosted:gemini-2.5-flash"],
        "LAPTOP-GPU":   ["hf:Qwen/Qwen2.5-VL-7B-Instruct-AWQ-INT4", "hosted:gemini-2.5-flash"],
        "WORKSTATION":  ["hf:Qwen/Qwen3-VL-8B-Instruct-BF16", "hosted:gemini-2.5-pro"],
        "SERVER-1GPU":  ["hf:Qwen/Qwen3-VL-32B-BF16"],
        "SERVER-MULTI": ["hf:Qwen/Qwen3-VL-235B-A22B-FP8"],
        "HOSTED-ONLY":  ["hosted:gemini-2.5-pro", "hosted:claude-sonnet-4-6", "hosted:gpt-5"],
    },
    "llm": {
        "TINY":         ["hf:Qwen/Qwen2.5-1.5B-Q4_K_M"],
        "LAPTOP-CPU":   ["hf:Qwen/Qwen3.5-4B-Q4_K_M", "hosted:claude-haiku-4-5"],
        "LAPTOP-GPU":   ["hf:Qwen/Qwen3.5-9B-Q4_K_M", "hosted:claude-sonnet-4-6"],
        "WORKSTATION":  ["hf:Qwen/Qwen3-32B-Instruct-AWQ-INT4", "hosted:claude-sonnet-4-6"],
        "SERVER-1GPU":  ["hf:Qwen/Qwen3.6-35B-A3B-BF16"],
        "SERVER-MULTI": ["hf:Qwen/Qwen3.5-397B-A17B-FP8"],
        "HOSTED-ONLY":  ["hosted:claude-sonnet-4-6", "hosted:gpt-5", "hosted:gemini-2.5-flash"],
    },
    "embed": {
        "TINY":         ["hf:sentence-transformers/all-MiniLM-L6-v2"],
        "LAPTOP-CPU":   ["hf:BAAI/bge-small-en-v1.5", "hosted:voyage-4-large"],
        "LAPTOP-GPU":   ["hf:BAAI/bge-m3-FP16", "hosted:voyage-4-large"],
        "WORKSTATION":  ["hf:Qwen/Qwen3-Embedding-4B-BF16"],
        "SERVER-1GPU":  ["hf:Qwen/Qwen3-Embedding-8B"],
        "SERVER-MULTI": ["hf:Qwen/Qwen3-Embedding-8B"],
        "HOSTED-ONLY":  ["hosted:gemini-embedding-001", "hosted:text-embedding-3-small", "hosted:voyage-4-large"],
    },
    "embed_late": {
        "TINY":         ["fallback:dense+rerank"],
        "LAPTOP-CPU":   ["hf:colbert-ir/colbertv2.0"],
        "LAPTOP-GPU":   ["hf:vidore/colqwen2-v1.0"],
        "WORKSTATION":  ["hf:vidore/colqwen2.5-v0.2"],
        "SERVER-1GPU":  ["hf:vidore/colqwen3-v1.0"],
        "SERVER-MULTI": ["hf:vidore/colqwen3-v1.0"],
        "HOSTED-ONLY":  ["fallback:dense+cohere-rerank"],
    },
    "sam": {
        "TINY":         ["cv2:GrabCut"],
        "LAPTOP-CPU":   ["onnx:MobileSAM"],
        "LAPTOP-GPU":   ["hf:facebook/sam2.1-hiera-tiny-FP16"],
        "WORKSTATION":  ["hf:facebook/sam2.1-hiera-base-plus-FP16"],
        "SERVER-1GPU":  ["hf:facebook/sam2.1-hiera-large-BF16"],
        "SERVER-MULTI": ["hf:facebook/sam2.1-hiera-large-BF16"],
        "HOSTED-ONLY":  ["hosted:replicate-sam2"],
    },
    "ocr": {
        "TINY":         ["tesseract:5"],
        "LAPTOP-CPU":   ["paddle:PP-OCRv4"],
        "LAPTOP-GPU":   ["hf:vikp/surya"],
        "WORKSTATION":  ["hf:allenai/olmocr-2-7B"],
        "SERVER-1GPU":  ["hf:allenai/olmocr-2-7B-1025"],
        "SERVER-MULTI": ["hf:allenai/olmocr-2-7B-1025"],
        "HOSTED-ONLY":  ["hosted:mistral-ocr"],
    },
    "asr": {
        "TINY":         ["faster-whisper:tiny-INT8"],
        "LAPTOP-CPU":   ["faster-whisper:large-v3-turbo-INT8"],
        "LAPTOP-GPU":   ["faster-whisper:large-v3-turbo-FP16"],
        "WORKSTATION":  ["nvidia:Parakeet-TDT-0.6B-v3"],
        "SERVER-1GPU":  ["nvidia:Parakeet-TDT-1.1B"],
        "SERVER-MULTI": ["nvidia:Parakeet-TDT-1.1B"],
        "HOSTED-ONLY":  ["hosted:deepgram-nova-3"],
    },
    "pii": {
        "TINY":         ["regex+spacy:en_core_web_sm"],
        "LAPTOP-CPU":   ["presidio+gliner_multi_pii-v1"],
        "LAPTOP-GPU":   ["hf:urchade/gliner-pii-base-v1.0"],
        "WORKSTATION":  ["hf:nvidia/gliner-pii"],
        "SERVER-1GPU":  ["hf:nvidia/gliner-pii"],
        "SERVER-MULTI": ["hf:nvidia/gliner-pii"],
        "HOSTED-ONLY":  ["hosted:aws-comprehend-pii"],
    },
    "rerank": {
        "TINY":         ["hf:cross-encoder/ms-marco-MiniLM-L-6-v2-INT8"],
        "LAPTOP-CPU":   ["hf:BAAI/bge-reranker-base-INT8"],
        "LAPTOP-GPU":   ["hf:BAAI/bge-reranker-v2-m3-FP16"],
        "WORKSTATION":  ["hf:jinaai/jina-reranker-v3"],
        "SERVER-1GPU":  ["hf:nvidia/nemotron-rerank-1B"],
        "SERVER-MULTI": ["hf:Qwen/Qwen3-Reranker-8B"],
        "HOSTED-ONLY":  ["hosted:cohere-rerank-3.5"],
    },
}


def _override_model(primitive: str) -> str | None:
    return os.environ.get(f"DH_{primitive.upper()}_MODEL")


def resolve(primitive: str, c: "_caps_mod.Capabilities") -> Callable:
    """Return a callable that takes (input, **opts) for `primitive` on caps `c`.

    Resolution order:
    - Explicit override via `DH_<KIND>_MODEL` env var (e.g. `DH_VLM_MODEL=hosted:gpt-5`).
    - Hosted API if the corresponding key is present + provider has
      headroom (rate-limit + monthly-budget room), unless `DH_FORCE_LOCAL=1`.
    - Else the regime-default local fallback. HF downloads happen on
      first use and are gated by `should_download(model_size_gb, caps,
      deadline)` so a 6-hour pull against a 4-hour deadline routes to
      hosted instead.
    - Walks the chain in order; WARNs the caller when the picked model
      is not the primary; raises `CapabilityError` if nothing in the
      chain fits the current capabilities.
    """
    if primitive not in RESOLVE_TABLE:
        raise CapabilityError(primitive, c.regime, suggested_downgrade="(unknown primitive)")
    table = RESOLVE_TABLE[primitive].get(c.regime, [])
    override = _override_model(primitive)
    if override:
        return _make_client(override, primitive, c, primary=True)
    force_local = os.environ.get("DH_FORCE_LOCAL") == "1"
    for i, model_id in enumerate(table):
        is_hosted = model_id.startswith("hosted:")
        if is_hosted and force_local:
            continue
        if i > 0:
            print(
                f"[data-harness] WARN: resolve({primitive}) downgraded "
                f"from {table[0]} to {model_id} (regime={c.regime})",
                file=sys.stderr,
            )
        return _make_client(model_id, primitive, c, primary=(i == 0))
    raise CapabilityError(primitive, c.regime, suggested_downgrade=f"add an entry for {c.regime}")


def _make_client(model_id: str, primitive: str, c, *, primary: bool) -> Callable:
    """Return a callable that invokes `model_id` for `primitive`.

    Stub until the first model-using skill records its cassette and
    wires the real client. The `embedding_cosine_to` predicate type
    is the only model-using predicate currently in the contract; it
    is skipped with a stderr note when no resolved client is available,
    so the green path stays foundation-model-free.
    """
    def _stub(*args, **kwargs):
        raise NotImplementedError(
            f"resolve({primitive}) → {model_id}: real client not yet wired. "
            f"For check-skill predicates, `embedding_cosine_to` is the only "
            f"model-using predicate type and is currently skipped with a "
            f"stderr note."
        )
    _stub.__name__ = f"{primitive}_via_{model_id}"
    return _stub


def dry_run_resolve(plan_paths: list[str]) -> list[dict]:
    """Pre-flight: for each skill plan, list (primitive, picked, fits, reason)."""
    c = _caps_mod.current()
    out = []
    for path in plan_paths:
        # naive plan parse: assume `plan` is a list of primitive names; v0 doesn't read SKILL.md yet.
        for prim in ("vlm", "llm", "embed", "embed_late", "sam", "ocr", "asr", "pii", "rerank"):
            chain = RESOLVE_TABLE.get(prim, {}).get(c.regime, [])
            picked = chain[0] if chain else None
            out.append({
                "skill": path, "primitive": prim, "regime": c.regime,
                "picked": picked, "fits": picked is not None,
                "reason": "primary" if picked else "no chain entry",
            })
    return out
