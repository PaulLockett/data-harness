# dhs — Demographic and Health Surveys indicator records

## What it does

Reads captured DHS Program API responses (no-auth, public) for one
country + one indicator and validates against externally-citable facts:
ISO country codes, the DHS Standard Indicator List, the country's
documented survey history, and historically-known fertility-rate values.

## Capture flow

1. Pick a country (`DHS_CountryCode` 2-letter) + indicator (`IndicatorId`
   from DHS Standard Indicator List).
2. GET 4 endpoints from `api.dhsprogram.com/rest/dhs/`:
   - `/data?indicatorIds=<X>&countryIds=<C>` — values across surveys
   - `/countries?countryIds=<C>` — ISO codes + region/subregion
   - `/surveys?countryIds=<C>` — survey history with implementing-org
   - `/indicators?indicatorIds=<X>` — indicator metadata + definition

## Output (skill.py contract)

Returns target / country / indicator / surveys_summary / first_survey_tfr
/ validation rollup with 12 sub-flags + per-file metadata.

## Predicates (case_001) — 46 total

| Group | Source |
|---|---|
| **Identity** (9): DHS code "KE", ISO2 "KE", ISO3 "KEN", country "Kenya", indicator "FE_FRTR_W_TFR", first survey 1989, TFR ~6.7 | **External**: ISO 3166-1 country codes; DHS Standard Indicator List; UN/World Bank historical fertility data (Kenya 1989 TFR 6.7) |
| **Country from data** (6): DHS code, ISO2 regex `^[A-Z]{2}$`, ISO3 regex `^[A-Z]{3}$`, country name, region in_set (DHS regional grouping), subregion in_set | **External**: ISO 3166 + DHS regional taxonomy |
| **Indicator from data** (4): indicator_id, label "Total fertility rate 15-49", measurement_type in_set (Rate/Pct/Number/Mean/Median/Ratio), definition min_length | **External**: DHS Standard Indicator List + DHS measurement-type enum |
| **Surveys summary** (4): n_surveys range, first_survey_id, year=1989, org regex matches NCPD | **External**: DHS Kenya country page lists 9 DHS rounds since 1989 with NCPD as 1989 implementing org |
| **First-survey TFR** (2): survey_id, value in [6.5, 7.0] | **External**: 1989 Kenya DHS reported TFR=6.7 (widely cited fertility-transition benchmark) |
| **Per-file shape** (5 for_all + 1) | Structural |
| **Validation rollup** (13) | Captured-data-only |
| **Capture URL + root keyset** (2) | **External** |

## Future cases

- **case_002**: a different country + indicator (e.g. Senegal under-5
  mortality CM_ECMR_C_U5M).
- **case_003**: a regional aggregate via the `/data` API's `breakdown`
  parameter.
- **case_004**: time-series of a single indicator across multiple DHS
  countries — exercises join + distribution interaction-skills.
