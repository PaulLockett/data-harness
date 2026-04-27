# interaction-skills

The 18 v0 cross-cutting analysis primitives, organized into four families
plus two hygiene wrappers (per spec §6):

- **Family 1 — glance:** `glance`, `distribution`, `drift`
- **Family 2 — validate:** `grain`, `join`, `split`, `leakage`, `schema`
- **Family 3 — quantify:** `uncertainty`, `calibrate`, `correct`
- **Family 4 — refute:** `assert`, `placebo`, `overfit_one_batch`, `saturation`, `disaggregate`
- **Hygiene:** `plan`, `reflect`

Each is a folder following the §11 contract:
`<skill>/{SKILL.md, fixtures/case_001/{inputs/, expected.json, optional floor.json/tolerances.json/cache.json/README.md}}`.

Phase 2a only scaffolds the structure. Phase 2b–f author real implementations
plus passing fixtures per family. `dh check-skill interaction-skills/<name>` is
the gate per skill.
