# case_001 — BH-corrected p-values from a mixed null/alternative

100 p-values: 90 drawn uniformly from [0, 1] (null), 10 small (~0.001)
representing real effects. Method = `bh`, alpha = 0.05.

Predicates assert structural shape: q-values list has 100 entries, all in
[0, 1], counts are sane.

Future: case_002 = bonferroni method (the conservative inverse, expected
fewer significant); case_003 = all-null (no real effects, q ≈ p).
