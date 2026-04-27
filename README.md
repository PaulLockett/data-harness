# data-harness

The simplest, thinnest, self-healing harness that gives an agent complete
freedom to do data work — exploration, transformation, multimodal analysis,
statistical inference, reportable output — across radically different domains
AND radically different hardware regimes.

One Python kernel + DuckDB + a small set of foundation-model clients (with local
fallbacks) + four primitive tiers + a typed Capabilities object that adapts
behavior to whatever resources are actually available.

## Quick start

```bash
cd data-harness
uv sync                    # install deps
uv run dh --doctor         # verify install
uv run dh caps             # print Capabilities snapshot
uv run dh <<'PY'
print(glance(load("/etc/hostname")))
PY
```

## Structure

```
data-harness/
├── run.py                       # ~60-line CLI; exec stdin + check-skill | caps | models
├── helpers.py                   # 10-tier substrate + glance() + capability-derived helpers
├── daemon.py                    # long-running process: DuckDB conn, lazy models, Atomic[Capabilities]
├── admin.py                     # daemon socket lifecycle (DH_NAME-namespaced)
├── check_skill.py               # predicate-first skill-fixture validator (§11)
├── models.py                    # per-primitive resolve tables keyed by regime (§13)
├── capabilities.py              # Capabilities introspection + adaptivity loop (§14)
├── deadlines.py                 # absolute-monotonic Deadline + Budget (§15)
├── profiles/                    # base.toml + 8 declared-profile presets
├── interaction-skills/          # 18 v0 skills (spec §6)
└── domain-skills/               # per-domain extraction fixtures (ADEM, TESS, FAERS, ...)
```

See `data-harness-build-spec-v5.md` (one level up) for the authoritative blueprint.

## Discipline

- Skills query computed flags (`caps.has_gpu`), never branch on `caps.regime ==`.
- Every skill is a folder with `SKILL.md` + `fixtures/case_*/`. Predicate-first.
- `dh check-skill <skill>` is the hard gate.
- Foundation-model calls go through `models.resolve(kind, caps)`. Hard-fail on unfittable; WARN on downgrade. Never silently swap kinds.
- Cassettes replay LLM/VLM/network calls during `check-skill`; never live API hits.
- Deadlines are absolute `time.monotonic()` with descend semantics.

## Setup prompt

See spec §17 for the full prompt to bootstrap data-harness from this README.
