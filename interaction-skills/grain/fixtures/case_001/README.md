# case_001 — planted PK duplicate

A 6-row table with `id` declared as PK, but `id=3` appears twice.
Predicates assert: violation detected (`pk_violation_count >= 2`,
`duplicate_keys` non-empty, `is_valid_pk` is false).

Future: case_002 = clean grain (the inverse — `is_valid_pk` true).
