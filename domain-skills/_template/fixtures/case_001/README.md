# case_001 — template baseline

A trivial-but-non-trivial fixture that exercises five predicate types
(string + length, string + in_set, list + min/max size, float + range,
object + key_set_includes). The `key_set_includes` predicate is the
positive assertion required by the §11 trivial-predicate linter.

Used by Phase 2a's smoke test: `dh check-skill domain-skills/_template`
must return 0.
