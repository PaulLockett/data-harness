# case_001 — planted near-perfect leak

500 rows. `y = 2x + ε` with `ε ~ N(0, 0.05)` (very small noise). Three features:

- `x` — independent (correlated with y by construction, ~0.999)
- `noise` — pure noise (correlation ~0)
- `leaked` — `2*x + tiny_noise` (correlation ~0.999, the planted leak)

The skill must surface `leaked` (and `x`, but x's high correlation is by
design — both end up in suspect_features given the threshold of 0.95).
This case demonstrates the validator catches near-deterministic features.

Future: case_002 = no-leak baseline; case_003 = subtle leak (corr ~0.92,
just under threshold — should NOT alarm).
