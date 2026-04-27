# case_001 — bootstrap CI on a Gaussian mean

200 rows of `x ~ N(10, 2)`. Bootstrap 1000 resamples; expected CI to bracket
~10 with width ~0.55 (≈ 2 × 1.96 × σ/√n).

Predicates assert kind/stat are recognized values, level = 0.95, n_resamples
in a sensible range, and the dict has the expected shape. The point-and-CI
ordering (ci_low < point < ci_high) is a structural property the skill
guarantees by construction.

Future cases: case_002 = bootstrap of median; case_003 = conformal; case_004
= small sample (n = 20) where CI widens dramatically.
