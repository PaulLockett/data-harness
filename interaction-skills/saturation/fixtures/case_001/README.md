# case_001 — saturating learning curve

400 rows of `y = 0.8*x + N(0, 1)`. With this much noise relative to signal,
R² should saturate around ~0.4 well before n=400. The 100%-vs-75% delta
should be small (< 0.01) → `saturation_reached` true.

Future: case_002 = high-noise undersampled regime where saturation isn't yet
reached at 100%; case_003 = noiseless data where saturation is reached at 25%.
