---
name: data-harness-install
description: Install and bootstrap data-harness into the current agent on macOS or Linux, then verify that capability detection and at least one domain fixture are green.
---

# data-harness install

Use this file only for first-time install or a fresh checkout. For day-to-day data work, read `SKILL.md`. Always read `helpers.py` after cloning; that is where the substrate primitives live.

Tested on macOS arm64 (Apple Silicon) and Linux x86_64 with Python 3.11+ and `uv`.

## Install prompt contract

After install, run `dh --doctor` and `dh caps` and show the user the output. Capability detection drives every downstream skill — a wrong regime or a missing GPU detection means every skill resolves the wrong model and either fails or silently degrades. If detection looks off (no GPU on a known-GPU box, regime classified as TINY on a workstation, RAM way under the real total), stop and surface that to the user before running any real skill.

## Best everyday setup

Clone the repo once into a durable location, then install it as an editable tool so `dh` works from any directory:

```bash
git clone https://github.com/PaulLockett/data-harness
cd data-harness
uv tool install -e .
command -v dh
```

That keeps the command global while still pointing at the real repo checkout, so when the agent edits `helpers.py` the next `dh` call uses the new code immediately. Prefer a stable path like `~/Developer/data-harness`, not `/tmp`.

The default install routes every model primitive through hosted APIs and is enough for every domain skill in this repo (cassettes mean `dh check-skill` never hits a real API anyway). For offline-capable installs, swap the last command for `uv tool install -e ".[local-models]"` — adds `transformers`, `sentence-transformers`, `faster-whisper`, `paddleocr`, `presidio-analyzer`, `gliner`, `huggingface_hub`, `torch`. The `gpu` PyPI extra is intentionally empty; install GPU FAISS via conda (`conda install -c pytorch -c nvidia faiss-gpu`).

## Make it global for the current agent

After the repo is installed, register this repo's `SKILL.md` with the agent you are using:

- **Codex**: add this file as a global skill at `$CODEX_HOME/skills/data-harness/SKILL.md` (often `~/.codex/skills/data-harness/SKILL.md`). A symlink to this repo's `SKILL.md` is fine.
- **Claude Code**: add an import to `~/.claude/CLAUDE.md` that points at this repo's `SKILL.md`, for example `@~/Developer/data-harness/SKILL.md`.

Codex command:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills/data-harness" && ln -sf "$PWD/SKILL.md" "${CODEX_HOME:-$HOME/.codex}/skills/data-harness/SKILL.md"
```

That makes new Codex or Claude Code sessions in other folders load the runtime data-harness instructions automatically. An empty `~/.codex/skills/data-harness/` directory is fine; the symlink command above populates it.

## Verify the install

Set environment:

```bash
cp .env.example .env              # then fill in any API keys you want to use
export DH_PROFILE=laptop-cpu      # or laptop-gpu, workstation, hosted-api-only, etc.
```

If no API keys are set and `[local-models]` isn't installed, the affected skills are reported as `skipped-below-floor` rather than failing.

Then run the verification ladder:

```bash
dh --doctor                              # python + capabilities + deadlines + daemon
dh caps                                  # detected hardware snapshot
dh check-skill domain-skills/_template   # one fixture green
make check-all-skills                    # every fixture green
```

`make smoke` is the canonical one-liner: `glance(load("/etc/hostname"))`. Reuse a healthy daemon if `dh --doctor` reports it alive — for parallel agents, set distinct `DH_NAME`s so they don't fight over the same default daemon.

## Keeping the harness current

For an editable clone:

```bash
cd ~/Developer/data-harness
git pull --ff-only
uv tool install -e . --force            # picks up new dependencies
dh --doctor
```

The daemon picks up new `helpers.py` code automatically on the next `dh` call (it `exec`s the file each time). Restart it explicitly only if you've changed `daemon.py`, `admin.py`, or any module the daemon imports at startup:

```bash
dh <<'PY'
from admin import restart_daemon; restart_daemon()
PY
```

If the editable clone has uncommitted changes, sort the dirty worktree before pulling — don't let `git pull` discard work.

## Resource budget

The substrate aims for a tight resting-state footprint — code + curated local model weights + interaction-skill fixtures + domain-skill fixtures + cassettes — with everything else (runtime scratch, raw captures that were filtered down to a persisted subset, abandoned model downloads) cleaned up rather than left to accumulate.

`make models` is opt-in only. Cassettes (`cache.json` per fixture) are the primary mechanism for replay during `check-skill`, so a green `check-skill` run never depends on local model weights. Model weights that are required for offline replay live in `~/.data-harness/models/` and are declared in `profiles/retained-weights.toml` — anything else under `~/.cache/huggingface/hub/` is fair game to prune.

## Cold-start reminders

- Run `dh --doctor` before assuming anything else is broken — it surfaces missing `capabilities.py` / `deadlines.py` modules, missing profile files, and dead daemons in one report.
- The daemon auto-starts on the first `dh <<'PY'` call. If it doesn't come up in 30s, check `/tmp/dh-default.log` for the start-up exception.
- Cold-start <1s by design; the daemon does NOT import `torch` or download weights at startup. First `vlm()` / `embed()` triggers `models.resolve(...)`.
- `DH_NAME=alt dh ...` lets parallel agents use independent daemons. The default name is `default`; files live under `/tmp/dh-<name>.{sock,pid,log}`.
- If skills hang while the daemon is responsive, check `dh caps` — `caps.is_offline=True` from a transient network blip will route every model call to local fallbacks, which may not be installed.
- A "stale daemon" symptom (sockets exist, calls return `"unsupported"` or hang) clears with one `restart_daemon()` — don't reach for `pkill` first.
