# case_001 — Kenya total fertility rate (TFR), DHS surveys 1989-present

## What this case demonstrates

Kenya's DHS-measured total fertility rate (15-49) across all 9 Kenya DHS
surveys since 1989. Pure no-auth JSON path from api.dhsprogram.com.
Externally-anchored to ISO country codes, DHS Standard Indicator List,
and Kenya's documented fertility-transition history (1989 TFR=6.7 is a
widely cited benchmark).

## Provenance

Captured 2026-04-27 from api.dhsprogram.com (4 endpoints): /data,
/countries, /surveys, /indicators. ~14 KB total across 4 JSONs.

## What the captured data contains (verified at capture-time)

| Field | Value | Predicate |
|---|---|---|
| Country DHS code | KE | `in_set ["KE"]` |
| Country ISO2 | KE | regex `^[A-Z]{2}$` |
| Country ISO3 | KEN | regex `^[A-Z]{3}$` |
| Country name | Kenya | `in_set ["Kenya"]` |
| Region | Sub-Saharan Africa | `in_set` of DHS regional grouping |
| Subregion | Eastern Africa | `in_set` of DHS subregional grouping |
| Indicator ID | FE_FRTR_W_TFR | `in_set` |
| Indicator label | "Total fertility rate 15-49" | `in_set` |
| Measurement type | Rate | `in_set [Rate, Pct, Number, Mean, ...]` |
| n_surveys | 9 | `in_range [5, 50]` |
| First survey ID | KE1989DHS | `in_set ["KE1989DHS"]` |
| First survey year | 1989 | `in_set [1989]` |
| First survey implementing org | National Council for Population Development (NCPD) | regex match |
| 1989 TFR value | 6.7 | `in_range [6.5, 7.0]` |

## External-source citations

- **ISO 3166-1 alpha-2 + alpha-3** — country code regex patterns
- **DHS Standard Indicator List** at dhsprogram.com — `FE_FRTR_W_TFR`
  is the canonical TFR indicator
- **UN World Population Prospects + World Bank fertility data** —
  Kenya's 1989 TFR of 6.7 is widely cited in the demographic-transition
  literature
- **DHS Country Profile: Kenya** at dhsprogram.com/countries/Kenya — 9
  DHS rounds since 1989 listed with implementing organizations
- **NCPD (National Council for Population Development) historical
  records** — implementing org for the 1989 Kenya DHS

## Spoof matrix

| Mutation | Predicate that fails |
|---|---|
| `target_first_survey_year` → 1899 | `target.first_survey_year in_set [1989]` fails |
| `target_dhs_country_code` → "ZZ" | `target.dhs_country_code in_set ["KE"]` fails; cascade fails country-match flags |
| Replace `country.json` with another country's | `validation.dhs_cc_matches in_set [true]` fails |
| Truncate `surveys.json` to `{"Data": []}` | `validation.first_survey_present` fails (no KE1989DHS row) |
