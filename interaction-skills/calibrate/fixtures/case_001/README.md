# case_001 — moderately well-calibrated predictions

500 rows. `prob` is a beta-distributed score, `actual` = Bernoulli(prob)
(so the predictions ARE the true probability, modulo sampling noise).
ECE should be small (~0.02-0.05); Brier well below 0.25 (the value of the
"always predict 0.5" baseline).

Predicates assert structural shape only (brier in [0,1], ece in [0,1], 10
bins) — exact values vary with the random seed; the bins/structure is the
durable contract.

Future: case_002 = systematically overconfident model; case_003 = perfectly
calibrated (brier and ece near 0).
