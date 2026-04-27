# Data Harness ⚗

The simplest, thinnest, **self-healing** harness that gives an LLM **complete freedom** to do data work — across any domain, any hardware. Built directly on Python + DuckDB.

The agent writes what's missing, mid-task. No framework, no recipes, no rails. One Python kernel, ten substrate tiers, every fixture predicate-first.

```
  ● agent: wants to validate a TESS light-curve
  │
  ● domain-skills/tess/ → does not exist
  │
  ● agent captures from MAST + writes the fixture    domain-skills/tess/
  │                                                  new + 28 predicates
  │
  ✓ dh check-skill domain-skills/tess
```

**You will never wrangle a one-off data pipeline again.**

## Setup prompt

Paste into Claude Code or Codex:

```text
Set up https://github.com/PaulLockett/data-harness for me.

Read `install.md` first to install this repo and verify it works on my machine. Then read `SKILL.md` for day-to-day usage. Always read `helpers.py` because that is where the substrate primitives live. After install, run `dh caps` to print the Capabilities snapshot for this machine, then `make check-all-skills` to confirm all 31 fixtures are green. Show me which domain skills are ready out of the box, and ask if I want a worked example of `dh check-skill` on one of them.
```

See [domain-skills/](domain-skills/) for ready-built domains and [interaction-skills/](interaction-skills/) for the primitive verbs.

## Domains ready out of the box

12 public-data domains validated by externally-anchored predicates (NASA catalogs, FDA specs, ITU standards, peer-reviewed papers, public registries):

- **adem** — Alabama Department of Environmental Management facility records
- **dhs** — Demographic and Health Surveys (USAID-funded global health data)
- **edgar** — SEC EDGAR public filings
- **faers** — FDA Adverse Event Reporting System
- **gfw** — Global Fishing Watch / NOAA Marine Cadastre AIS tracks
- **snapshot-serengeti** — Camera-trap species classification
- **soccernet** — Soccer-action-spotting taxonomy
- **tess** — TESS exoplanet light-curves
- **usaspending** — Federal contract awards
- **uspto** — US patent records
- **vesuvius** — Vesuvius Challenge 3D micro-CT scrolls
- **ztf** — Zwicky Transient Facility alert streams

## How simple is it? (~2374 lines of Python)

- `install.md` — first-time install
- `SKILL.md` — day-to-day usage
- `run.py` (~56 lines) — runs plain Python with the substrate preloaded
- `helpers.py` (~689 lines) — ten-tier substrate primitives; the agent edits these
- `daemon.py` + `admin.py` (~364 lines) — long-running process plus daemon socket lifecycle
- `check_skill.py` (~220 lines) — predicate-first fixture validator
- `models.py` (~181 lines) — capability-aware foundation-model resolve table
- `capabilities.py` + `deadlines.py` (~864 lines) — typed Capabilities + absolute-monotonic deadlines

## Contributing

PRs and improvements welcome. The best way to help: **contribute a new domain skill** under [domain-skills/](domain-skills/) for a public dataset or domain you work with often (a regulator's filing portal, a research archive, an open-data API, etc.). Each skill teaches the agent the capture path, the canonical record shape, and the externally-anchored predicates it would otherwise have to rediscover.

- **Skills are written by the harness, not by you.** Just run your task with the agent — when it captures a real artifact and figures out the predicate set, it files the skill itself (see [SKILL.md](SKILL.md)). Please don't hand-author skill files; agent-generated ones reflect what actually validates against external sources.
- Open a PR with the generated `domain-skills/<domain>/` folder — small and focused is great.
- New interaction-skill primitives (under [interaction-skills/](interaction-skills/)), helper additions, and bug fixes are equally welcome.
- Browse existing skills (`tess/`, `edgar/`, `faers/`, ...) to see the shape.

If you're not sure where to start, open an issue and we'll point you somewhere useful.

---

[Predicate-first fixtures](SKILL.md) · [Capabilities + deadlines](capabilities.py)
