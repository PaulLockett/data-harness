# case_001 — real treatment effect of +2.0

400 rows. `treatment ∈ {0, 1}` randomly assigned; `outcome = 5 + 2*treatment + ε`
with `ε ~ N(0, 0.5)`. The true effect (~+2) should dominate any placebo
effect (which has mean 0 by construction). `placebo_passes` must be true.

Future: case_002 = no real effect (true_effect ≈ 0; placebo_passes false
because the ratio diverges); case_003 = small effect that fails the placebo.
