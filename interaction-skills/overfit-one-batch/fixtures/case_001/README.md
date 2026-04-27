# case_001 — perfectly fittable linear data

30 rows. `y = 1.5*x1 + (-2.0)*x2 + 0.5` (no noise). A linear regression must
fit this exactly: `train_mse < 1e-10`, `r2 > 0.999`.

Future: case_002 = data with noise (mse > 0); case_003 = duplicate-x
adversarial (impossible to memorize).
