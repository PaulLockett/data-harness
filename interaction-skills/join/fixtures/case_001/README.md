# case_001 — planted 1:N fanout

`left` has 5 unique users; `right` has 15 rows (3 per user_id) representing
multiple sessions per user. Joining inflates the row count 3× — exactly the
silent inflation `join` exists to surface.

Predicates assert cardinality is "1:N" and fanout_max is 3.

Future: case_002 = clean 1:1; case_003 = N:M with adversarial fanout > 100.
