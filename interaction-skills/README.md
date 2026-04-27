# interaction-skills

The 18 cross-cutting analysis primitives, organized into four families
plus two hygiene wrappers. The four families answer the four questions
that distinguish a real analysis from a black-box prediction:

- **Family 1 — glance** (*what's in the data?*): `glance`, `distribution`, `drift`
- **Family 2 — validate** (*are my assumptions sound?*): `grain`, `join`, `split`, `leakage`, `schema`
- **Family 3 — quantify** (*how sure should I be?*): `uncertainty`, `calibrate`, `correct`
- **Family 4 — refute** (*could I be wrong?*): `assert`, `placebo`, `overfit_one_batch`, `saturation`, `disaggregate`
- **Hygiene wrappers:** `plan`, `reflect`

Each is a folder following the skill-fixture contract:
`<skill>/{SKILL.md, fixtures/case_001/{inputs/, expected.json, optional floor.json/tolerances.json/cache.json/README.md}}`.

Predicates in `expected.json` are mandatory and must include at least
one positive assertion (`regex` / `in_set` / `in_range` /
`key_set_includes` / `embedding_cosine_to`) — a fixture asserting only
`type:any` is rejected by the linter. `dh check-skill
interaction-skills/<name>` is the gate per skill.
