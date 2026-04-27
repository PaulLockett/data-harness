# case_001 — known-true predicate set

A simple record (name, count, tags) plus three predicates known to hold by
construction. `all_passed` must be true; `n_failed` zero.

Future: case_002 = known-failing predicates (verifies the inverse — that the
runner correctly reports failures, not silent pass).
