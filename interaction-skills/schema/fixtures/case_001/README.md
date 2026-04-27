# case_001 — planted schema violations

A record with three deliberate violations of the declared schema:

1. **Missing required key** `id` (declared in schema.required, absent from record)
2. **Type mismatch** `count` (declared `int`, record has `"twelve"` string)
3. **Extra key** `__debug__` (not declared anywhere)

Predicates assert: `valid == false`, missing/mismatches non-empty.

Future: case_002 = perfect match (`valid == true`, all lists empty).
