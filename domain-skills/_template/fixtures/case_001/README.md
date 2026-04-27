# case_001 — template baseline

A trivial-but-non-trivial fixture that exercises five predicate types
(string + length, string + in_set, list + min/max size, float + range,
object + key_set_includes). The `key_set_includes` predicate is the
positive assertion required by the trivial-predicate linter — a
fixture asserting only `type:any` would tautologically pass and is
rejected, so every case must include at least one positive predicate
(`regex` / `in_set` / `in_range` / `key_set_includes` /
`embedding_cosine_to`).

Used as the install smoke test: `dh check-skill domain-skills/_template`
must return 0 on a fresh install before any other case is authored.
