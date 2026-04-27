---
name: data-harness
description: Predicate-first data harness over DuckDB + Polars. Use when the user wants to validate, transform, or extract data from any domain — light-curves, federal filings, geospatial AIS, multimodal scrolls. Capability-aware: the same skill code runs on a tiny laptop and a multi-GPU server.
---

# data-harness

Easiest and most powerful way to do data work an LLM can trust. **Read this file in full before using or editing the harness** — it has to be in context.

## Fast start

Read `SOUL.md` first — that's my constitution (voice, frame, what good and bad look like). Then `~/.data-harness/USER.md` (user profile) and `~/.data-harness/data-sources.md` (private-source access grants); if they don't exist, run `meta-skills/interview/` to bootstrap them. Then `helpers.py` for the substrate primitives. For first-time install, read `install.md` first.

## Self-maintenance

- `dh --doctor` — diagnose install, daemon, capability detection, and whether an update is available.
- `dh --setup` — interactive first-run bootstrap; runs the doctor, suggests a `DH_PROFILE`, and warms the daemon.
- `dh --update -y` — pull the latest version and restart the daemon without prompting. **If you see a banner like `[data-harness] update available: X -> Y` at the top of a run, run this yourself — don't ask the user first.** The banner is rate-limited to once per day.

```bash
dh <<'PY'
print(glance(load("/etc/hostname")))
PY
```

- Invoke as `dh` — it's on `$PATH`. No `cd`, no `uv run`.
- First action on a new dataset is `glance(load(...))` — verify shape before anything else. It's the cheap way to find out whether the next move is right.

The code is the doc.

Available interaction skills:
- `interaction-skills/glance/` — the verification primitive. Read first.

Available domain skills:
- `adem/` · `dhs/` · `edgar/` · `faers/` · `gfw/` · `snapshot-serengeti/` · `soccernet/` · `tess/` · `usaspending/` · `uspto/` · `vesuvius/` · `ztf/`

## Tool call shape

```bash
dh <<'PY'
# any python; helpers pre-imported. daemon auto-starts.
PY
```

`run.py` calls `ensure_daemon()` before `exec` — you never start/stop manually unless you want to.

### The four super-skill families

- **Family 1 — `glance`:** `glance`, `distribution`, `drift`. *What's in the data?*
- **Family 2 — `validate`:** `grain`, `join`, `split`, `leakage`, `schema`. *Are my assumptions sound?*
- **Family 3 — `quantify`:** `uncertainty`, `calibrate`, `correct`. *How sure should I be?*
- **Family 4 — `refute`:** `assert`, `placebo`, `overfit_one_batch`, `saturation`, `disaggregate`. *Could I be wrong?*

Plus two hygiene wrappers: `plan`, `reflect`.

### The skill-fixture contract

Every skill is a folder: `<skill>/{SKILL.md, fixtures/case_NNN/{inputs/, expected.json, optional floor.json|tolerances.json|cache.json|expected_strict.json}}`. Predicates in `expected.json` are mandatory and must encode externally-citable facts about the target — a registered identifier, a published value, a documented schema, a physical-law range — not just whatever the skill happens to produce. `dh check-skill <skill>` is the hard gate.

### Capabilities, regimes, and adaptivity

Skills query `caps()` for live Capabilities, query computed flags (`caps.has_gpu`, `caps.ram_available_bytes`, `caps.is_offline`), and derive numerics via `workers_for(caps(), kind)`, `batch_size_for(caps(), model_bytes, per_seq_bytes)`, etc. **Skills MUST NOT branch on `caps.regime ==`** — the linter rejects it. Branching on the concrete flags is what lets the same skill code run on a TINY laptop, a SERVER-MULTI cluster, and a HOSTED-ONLY box without a single regime check.

### Model resolution and local fallbacks

Every foundation-model primitive (`vlm`, `llm`, `embed`, ...) resolves through `models.resolve(kind, caps)`. Hosted-API → HF local fallback chain keyed by regime. Hard-fail on unfittable, WARN on non-primary pick. Cassettes (`cache.json`) replay during `check-skill`; never live API hits.

### Time, deadlines, and budget propagation

Use `Deadline` and `Budget` (absolute `time.monotonic()`). Descend semantics: child's deadline = `min(parent, now + child_seconds)`. `with budget(seconds=N) as b: ...` for scoped time + dollar caps. Never use `signal.SIGALRM`, raw durations, or wall-clock — the deadline math depends on the absolute-monotonic invariant.

### Two paths for AI-sees-image

- **`image_show(img)`** — orchestrating Claude Code's eyes. No model call, no cost.
- **`vlm(image, prompt) -> str`** — batch programmatic VLM call. Real cost, real latency.

Rule: **`image_show` for one image you want to see; `vlm` for many images the skill processes.**

## Search first

After cloning the repo, search `domain-skills/` first for the domain you are working on before inventing a new approach.

Only if you start struggling with a specific primitive while shaping data, look in `interaction-skills/` for the right verb. The available interaction skills are:
- `glance/`
- `distribution/`
- `drift/`
- `grain/`
- `join/`
- `split/`
- `leakage/`
- `schema/`
- `uncertainty/`
- `calibrate/`
- `correct/`
- `assert/`
- `placebo/`
- `overfit-one-batch/`
- `saturation/`
- `disaggregate/`
- `plan/`
- `reflect/`

Useful commands:

```bash
rg --files domain-skills
rg -n "tess|fits|toi-700" domain-skills
```

## Always contribute back

**If you learned anything non-obvious about a dataset, capture path, or predicate anchor, open a PR to `domain-skills/<domain>/` before you finish. Default to contributing.** The harness gets better only because agents file what they learn. If figuring something out cost you a few steps, the next run should not pay the same tax.

Examples of what's worth a PR:

- A **public API** the dataset publishes (REST endpoint, bulk-download URL, query shape, auth) — often 10× faster than scraping and easier to validate.
- A **canonical record shape** that beats the raw response — what fields are stable identifiers vs. drift-prone, what nesting flattens cleanly.
- A **predicate anchor** — the externally-citable source (NASA catalog entry, FDA spec section, ITU standard, peer-reviewed paper, public registry) that justifies a min/max range, an enum set, or a regex.
- A **format quirk** — "this FITS file uses BJD-TDB not JD-UTC", "this CSV has a UTF-16 BOM", "the ZIP's outer directory is the version, not the dataset".
- A **URL pattern** — bulk-download path, sampling slice that fits a resource budget, a variant that skips a paywall.
- A **trap** — silent truncation when a record exceeds a size limit, deprecated identifiers that now return null, image-only PDFs that return empty text from `pypdf`.

### What a domain skill should capture

The *durable* shape of the dataset — the map, not the diary. Focus on what the next agent on this domain needs to know before it starts:

- Capture path: REST endpoint / bulk-download URL / query shape.
- Canonical record shape with field provenance.
- Stable identifiers vs. drift-prone fields (what to anchor predicates to, what to allow to drift).
- Predicate anchors with their external citation.
- Format quirks unique to this domain (encoding, time system, units).
- Resource budget — typical case_001 size, sampling discipline if the full dataset is too large.
- Traps — what doesn't work and why.

### Do not write

- **Run narration** or step-by-step of the specific task you just did.
- **Skill-derived booleans as primary predicates.** A predicate that just checks "this skill said true" tests nothing — predicates encode external/analytical truth, not skill output. Skill-derived booleans are belt-and-suspenders only.
- **Secrets, API keys, session tokens, or user-specific data.** `domain-skills/` is shared and public.

## What actually works

- **`glance` after every meaningful transform.** Not optional. The harness's discipline is "verify, don't assume" — every transform earns its keep by surviving a glance.
- **Predicate-first beats byte-exact.** Predicates encode the contract; tolerances calibrate per profile. A captured value that drifts 0.01% should not fail a check that's actually about identity.
- **Skills query computed flags.** `caps.has_gpu`, never `caps.regime == "WORKSTATION"`.
- **Capture once, replay forever.** The first time you hit a real dataset, save the inputs to `fixtures/case_NNN/inputs/` so `check-skill` is hermetic forever after.
- **Cassettes for foundation-model calls.** Record-once, replay-from-`cache.json` during `check-skill`. No live API hits during validation.
- **`should_download()` before every weight pull.** A 6-hour download against a 4-hour deadline routes to hosted-API instead of forcing the wait.
- **`workers_for(caps, kind)` and `batch_size_for(...)` for parallelism.** Don't hard-code `n_workers=4` — the same skill on TINY would thrash and on SERVER-MULTI would idle.
- **`Deadline.descend()` at every step.** Time pressure should propagate; if the parent has 60s left, a child can have at most 60s.
- **Predicate vocabulary**: `type`, `min_length`/`max_length`, `regex`, `min/max`, `in_range`, `in_set`, `min_size`/`max_size`, `for_all`, `embedding_cosine_to`+`min`, `key_set_includes`. The linter rejects trivial-only predicate sets.
- **Auth wall**: redirected to login → stop and ask the user. Don't type credentials into capture scripts.

## Design constraints

- **Don't add a manager / supervisor / orchestrator / config_system / plugin layer.** The substrate is flat on purpose — `helpers.py` is the substrate, `daemon.py` runs it, `check_skill.py` validates fixtures, `models.py` resolves model primitives. Adding a coordination layer above that breaks the flat-helpers discipline.
- **Don't add method-specific skills inside the four super-skill families.** Method-specific things (DiD, target encoding, propensity scoring) go in sub-packages within the relevant family — e.g. a DiD primitive lives under `quantify/uncertainty/did/`, not as a top-level interaction-skill.
- **Don't ship a skill without a fixture.** `<skill>/fixtures/case_NNN/expected.json` is mandatory and must contain at least one positive predicate.
- **Don't hardcode a single model provider in `helpers.py`.** Every primitive that needs a model resolves through `models.resolve(kind, caps)`.
- **Don't read `psutil` / `torch.cuda` / nvidia-ml-py directly from a skill.** Use `caps()` so the abstraction handles cgroup limits, MPS vs CUDA, container vs bare-metal, etc.
- **Don't use `signal.SIGALRM`, raw durations, or wall-clock time for deadlines.** Use the `Deadline` / `Budget` types — the descend semantics depend on the absolute-monotonic invariant.
- **Don't skip `should_download()` before pulling a model weight.** A 6-hour download against a 4-hour deadline must route to hosted-API instead of forcing the wait.
- **`run.py` stays tiny.** No argparse beyond the wired subcommands; no orchestration framework on top.
- **Helpers stay short.** Substrate primitives in `helpers.py` (hard cap so the substrate stays reviewable); daemon socket lifecycle and CLI dispatch live in `admin.py` / `run.py`.

## Architecture

```text
your script ──► dh CLI ──► daemon (Unix socket) ──► DuckDB conn + lazy models + Atomic[Capabilities]
                              │                            │
                              └─► helpers.py primitives ◄──┘
                              └─► models.resolve(kind, caps)
```

- Protocol is one JSON line each way over a Unix socket at `/tmp/dh-<NAME>.sock`.
- Requests are `{"meta": "ping"}` / `{"meta": "status"}` / `{"meta": "shutdown"}` for daemon control.
- Responses are `{"meta": ..., ...}` or `{"error": ...}`.
- `DH_NAME` namespaces socket, pid, and log files (default `dh-default.*`).
- `DH_PROFILE` selects a profile from `profiles/*.toml` — declared budget overrides on top of detected capabilities.
- `DH_FORCE_LOCAL=1` overrides hosted-API preference in `models.resolve(...)`.
- `DH_SCRATCH_DIR` overrides the `~/.data-harness/` scratch root.

## Gotchas (field-tested)

- **The daemon does NOT import torch or download weights at startup.** First `vlm()` / `embed()` call triggers the resolve path. Cold-start <1s by design.
- **`should_download()` gates every HF pull.** A 6-hour download against a 4-hour task routes to hosted; if no hosted route exists for that primitive, the skill is `skipped-below-floor`.
- **`DH_FORCE_LOCAL=1` overrides hosted preference.** Useful for offline replay verification; never for production capture.
- **Cassettes carry `recorded_at`.** `check-skill` warns when >90 days old; weekly `--cassette-refresh` re-records against real APIs.
- **Skills MUST NOT branch on `caps.regime`.** The linter rejects it. Always query computed flags (`caps.has_gpu`, `caps.ram_available_bytes`, `caps.is_offline`) so the same code runs across regimes.
- **`embedding_cosine_to` predicates need a `cache.json`.** Live API hits during `check-skill` are forbidden — record once, replay forever.
- **PDF text-extraction is not OCR.** `pypdf` returns empty text on image-scanned PDFs; don't anchor a `min_length` predicate to extracted text without a fallback (filename match, OCR pass).
- **Stale daemon sessions surface as `"unsupported"` responses.** `restart_daemon()` once and retry — see `admin.py`.
- **`uv run --no-sync daemon.py` is the daemon spawn pattern.** Don't `python daemon.py` directly; the substrate depends on the pyproject-managed venv.
- **`floor.json` declares hardware honestly.** A skill that fits in 4 GB RAM should declare `min_ram_gb: 4`, not `min_ram_gb: 16`. The runner uses the floor to compute `skipped-below-floor` vs. hard-fail.
- **External-anchor citations live in `case_NNN/README.md`.** A predicate without a citation is a candidate for predicate rot when the data drifts; the README is where the next agent learns where the number came from.
- **`make check-all-skills` must be hermetic.** No live API hits, no live data fetches. If a skill needs the network during `check-skill`, the cassette is incomplete.

## Persistent state maintenance

Two per-user files persist across sessions and grow as we work:

**`~/.data-harness/USER.md`** — the user's profile. When you observe something stable about how they work — a preference, an anti-pattern, a domain they're working in — append or revise the relevant section. If new behavior contradicts what's there, edit; don't accumulate duplicates. When in doubt, ask before saving.

**`~/.data-harness/data-sources.md`** — private data sources the user has granted (or committed to grant) access to. Each entry has a status: `pending` (committed, no credentials yet) → `configured` (credentials present, untested) → `tested` (connection verified, helper built). The interview seeds initial pending entries; subsequent sessions move entries forward as helpers get built. Never store credentials here — those belong in `.env` or a secret store.

The bootstrap interview at `meta-skills/interview/` populates initial sections of both files. From then on, every session is responsible for keeping them current.

## Interaction notes

- `interaction-skills/` holds the cross-cutting data primitives (the four super-skill families plus `plan`/`reflect`).
- `domain-skills/` holds per-source extractions and should be updated when a new domain is captured or an existing one drifts.
- `meta-skills/` holds skills about how the agent works with the user — the bootstrap interview, plus future user-profile maintenance flows.
