# Install

Tested on macOS arm64 (Apple Silicon) and Linux x86_64 with Python 3.11+ and `uv`.

## 1. Clone and resolve

```bash
git clone https://github.com/PaulLockett/data-harness
cd data-harness
uv lock                  # ~5s, no installs
```

## 2. Choose your install depth

- **Smoke-test only (no API keys, no model weights):** `uv venv && uv pip install psutil py-cpuinfo duckdb polars` — enough for `dh caps` + `dh check-skill <template>` + `glance(load("..."))`.
- **Baseline (everything but local model weights):** `uv sync` — pulls all `dependencies` from `pyproject.toml` (~5–10 GB; includes torch via marker-pdf transitive).
- **Full (with local model fallbacks):** `uv sync --extra local-models` — adds transformers, sentence-transformers, faster-whisper, etc.

## 3. Set environment

```bash
cp .env.example .env     # then fill in any API keys you want to use
export DH_PROFILE=laptop-cpu      # or laptop-gpu, workstation, etc.
```

If no API keys are set, the harness falls back to local models. If neither is available, the relevant skills are `skipped-below-floor`.

## 4. Verify

```bash
uv run dh --doctor
uv run dh caps
uv run dh check-skill domain-skills/_template
```

`make smoke` is the canonical one-liner: `glance(load("/etc/hostname"))`.

## Resource budget

The substrate aims for a tight resting-state footprint — code + curated
local model weights + interaction-skill fixtures + domain-skill fixtures
+ cassettes — with everything else (runtime scratch, raw captures that
were filtered down to a persisted subset, abandoned model downloads)
cleaned up rather than left to accumulate.

`make models` is opt-in only. Cassettes (`cache.json` per fixture) are
the primary mechanism for replay during `check-skill`, so a green
`check-skill` run never depends on local model weights. Model weights
that are required for offline replay live in `~/.data-harness/models/`
and are declared in `profiles/retained-weights.toml` — anything else
under `~/.cache/huggingface/hub/` is fair game to prune.
