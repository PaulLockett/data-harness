# data-harness — day-to-day usage

Read this in full before using or editing the harness. The code is the doc; this
is the orientation layer.

## Fast start

Helpers are pre-imported by `run.py`; the daemon auto-starts on first call.

```bash
dh <<'PY'
print(glance(load("/etc/hostname")))
PY
```

## Tool call shape

```bash
dh <<'PY'
# any python; helpers pre-imported.
PY
```

## The four super-skill families

- **Family 1 — `glance`:** `glance`, `distribution`, `drift`. *What's in the data?*
- **Family 2 — `validate`:** `grain`, `join`, `split`, `leakage`, `schema`. *Are my assumptions sound?*
- **Family 3 — `quantify`:** `uncertainty`, `calibrate`, `correct`. *How sure should I be?*
- **Family 4 — `refute`:** `assert`, `placebo`, `overfit_one_batch`, `saturation`, `disaggregate`. *Could I be wrong?*

Plus two hygiene wrappers: `plan`, `reflect`.

## The skill-fixture contract

Every skill is a folder: `<skill>/{SKILL.md, fixtures/case_NNN/{inputs/, expected.json, optional floor.json|tolerances.json|cache.json|expected_strict.json}}`. Predicates in `expected.json` are mandatory and must encode externally-citable facts about the target — a registered identifier, a published value, a documented schema, a physical-law range — not just whatever the skill happens to produce. `dh check-skill <skill>` is the hard gate.

## Capabilities, regimes, and adaptivity

Skills query `caps()` for live Capabilities, query computed flags (`caps.has_gpu`, `caps.ram_available_bytes`, `caps.is_offline`), and derive numerics via the helper `workers_for(caps(), kind)`, `batch_size_for(caps(), model_bytes, per_seq_bytes)`, etc. **Skills MUST NOT branch on `caps.regime ==`** — that's a strong-constraint violation; the linter rejects it. Branching on the concrete flags is what lets the same skill code run on a TINY laptop, a SERVER-MULTI cluster, and a HOSTED-ONLY box without a single regime check.

## Model resolution and local fallbacks

Every foundation-model primitive (`vlm`, `llm`, `embed`, ...) resolves through `models.resolve(kind, caps)`. Hosted-API → HF local fallback chain keyed by regime. Hard-fail on unfittable, WARN on non-primary pick. Cassettes (`cache.json`) replay during `check-skill`; never live API hits.

## Time, deadlines, and budget propagation

Use `Deadline` and `Budget` (absolute `time.monotonic()`). Descend semantics: child's deadline = `min(parent, now + child_seconds)`. `with budget(seconds=N) as b: ...` for scoped time + dollar caps. Never use `signal.SIGALRM`, raw durations, or wall-clock — the deadline math depends on the absolute-monotonic invariant.

## Two paths for AI-sees-image

- **`image_show(img)`** — orchestrating Claude Code's eyes. No model call, no cost.
- **`vlm(image, prompt) -> str`** — batch programmatic VLM call. Real cost, real latency.

Rule: **`image_show` for one image you want to see; `vlm` for many images the skill processes.**

## Search first

When solving a new domain, search `domain-skills/` first before inventing a new approach.

## Always contribute back (and the check-skill workflow)

If you write working code that solves a real problem, file it as a skill. Extract → write SKILL.md → record `fixtures/case_001/inputs/` from the just-solved run → derive `expected.json` predicates → declare `floor.json` if needed → run `dh check-skill <path>`. Pass = live, fail = rejected.

## What actually works

- **`glance` after every meaningful transform.** Not optional. The harness's discipline is "verify, don't assume."
- **Predicate-first** beats byte-exact. Predicates encode the contract; tolerances calibrate per profile.
- **Skills query computed flags.** `caps.has_gpu`, never `caps.regime == "WORKSTATION"`.

## Design constraints

- Don't add a manager / supervisor / orchestrator / config_system / plugin layer. The substrate is flat on purpose — `helpers.py` is the substrate, `daemon.py` runs it, `check_skill.py` validates fixtures, `models.py` resolves model primitives. Adding a coordination layer above that breaks the flat-helpers discipline.
- Don't add method-specific skills (DiD, target encoding, propensity scoring, etc.) inside the four super-skill families. Those go in sub-packages within the relevant family — e.g. a DiD primitive lives under `quantify/uncertainty/did/`, not as a top-level interaction-skill.
- Don't ship a skill without a fixture. `<skill>/fixtures/case_NNN/expected.json` is mandatory and must contain at least one positive predicate.
- Don't hardcode a single model provider in `helpers.py`. Every primitive that needs a model resolves through `models.resolve(kind, caps)`.
- Don't read `psutil` / `torch.cuda` / nvidia-ml-py directly from a skill. Use `caps()` so the abstraction handles cgroup limits, MPS vs CUDA, container vs bare-metal, etc.
- Don't use `signal.SIGALRM`, raw durations, or wall-clock time for deadlines. Use the `Deadline` / `Budget` types — the descend semantics depend on the absolute-monotonic invariant.
- Don't skip `should_download()` before pulling a model weight. A 6-hour download against a 4-hour deadline must route to hosted-API instead of forcing the wait.

## Architecture

```
your script ──► dh CLI ──► daemon (Unix socket) ──► DuckDB conn + lazy models + Atomic[Capabilities]
                              │                            │
                              └─► helpers.py primitives ◄──┘
                              └─► models.resolve(kind, caps)
```

## Gotchas (field-tested, will grow)

- The daemon does NOT import torch or download weights at startup. First `vlm()` / `embed()` call triggers the resolve path.
- `should_download()` gates every HF pull. A 6-hour download against a 4-hour task routes to hosted.
- `DH_FORCE_LOCAL=1` overrides hosted preference.
- Cassettes carry `recorded_at`; CI warns when >90 days old. Weekly `--cassette-refresh` re-records against real APIs.

## Interaction notes

- `interaction-skills/` holds the 18 v0 cross-cutting primitives.
- `domain-skills/` holds per-source extractions and should be updated when a new domain is captured.
