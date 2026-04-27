# case_001 — clozapine FAERS report 215586863 (2025Q3)

## What this case demonstrates

A real FDA Adverse Event Reporting System report for **clozapine**
(antipsychotic with a black-box warning for agranulocytosis, myocarditis,
and seizures), captured from the FDA's published 2025Q3 quarterly bulk
ZIP. The case exercises:

- **Bulk-download capture** without browser-harness — direct HTTP to the
  FDA Qlik server's `Exports/` path; no auth, no JavaScript.
- **Volume-aware filtering** — the raw quarter is 73 MB compressed /
  430 MB extracted across seven `$`-delimited tables. The skill's runtime
  consumes only the few-KB filtered subset; the bulk capture footprint is
  reclaimed before the case is committed.
- **Multi-table content validation** — the canonical AE-report ties seven
  tables together by `primaryid` (FAERS's report key), and the skill
  asserts every persisted row shares that key plus the target drug
  appears in DRUG with `role_cod = 'PS'` (primary suspect).

## Provenance

Captured 2026-04-27 from
`https://fis.fda.gov/content/Exports/faers_ascii_2025q3.zip`. ZIP:
`Last-Modified: Thu, 30 Oct 2025 19:14:16 GMT`, 76,715,577 bytes (73 MB),
20 entries (7 ASCII tables + Deleted/DELETE25Q3.txt + 11 docs).

## What's in `inputs/`

| File | Bytes | n_rows | Notes |
|---|---|---|---|
| `_provenance.json` | ~1.5 KB | — | target spec + capture metadata + table-file map |
| `extracted/demo.txt` | 583 | 1 | report metadata |
| `extracted/drug.txt` | 1,165 | 10 | 1 PS clozapine + 1 SS clozapine + 8 SS co-medications |
| `extracted/reac.txt` | 648 | 16 | MedDRA preferred terms |
| `extracted/outc.txt` | 70 | 2 | OT (other), HO (hospitalized) |
| `extracted/indi.txt` | 330 | 7 | drug indications |
| `extracted/ther.txt` | 58 | 0 | header only — no therapy timeline rows for this primaryid |
| `extracted/rpsr.txt` | 26 | 0 | header only — no source rows for this primaryid |

Total: ~3 KB on disk.

## What the report contains (verified at capture-time)

| Field | Value | Predicate |
|---|---|---|
| `primaryid` | 215586863 | `in_set ["215586863"]` |
| `caseid` | 21558686 | `in_set ["21558686"]` |
| `caseversion` | 3 | `regex ^[0-9]+$` |
| Patient | 30-year-old male, EU | `age regex ^[0-9]{1,3}$`; `sex in ["M",...]`; `country regex ^[A-Z]{2,3}$` |
| `init_fda_dt` | 20221107 (2022-11-07) | `regex ^[0-9]{8}$` |
| `fda_dt` | 20250805 (2025-08-05) | `regex ^[0-9]{8}$` |
| `rept_cod` | EXP | `in_set ["EXP",...]` |
| `mfr_sndr` | AUROBINDO | `min_length 1` |
| `mfr_num` | EU-AUROBINDO-AUR-APL-2022-045536 | (no predicate) |
| `occp_cod` | MD (medical doctor) | (no predicate) |
| Reporter country | EU | `regex ^[A-Z]{2,3}$` |
| Drug 1 (PS) | CLOZAPINE 125 mg/QD | `role_cod in ["PS",...]`, `drugname min_length 1`, `target_drug_in_drug_table` true |
| Drug 2 (SS) | CLOZAPINE 50 mg/QD | (concomitant clozapine variant) |
| Drug 3 (SS) | AMISULPRIDE 600 mg/QD | (antipsychotic) |
| Drug 4 (SS) | SUBOXONE | (opioid use disorder treatment) |
| Drug 5 (SS) | CHLORPROMAZINE 150 mg/QD | (antipsychotic) |
| Drug 6 (SS) | ZUCLOPENTHIXOL | (antipsychotic) |
| Drug 7 (SS) | HALOPERIDOL 6 mg/QD | (antipsychotic) |
| Drug 8-10 (SS) | CLOTHIAPINE | (antipsychotic) |
| Reactions | Priapism, Drug withdrawal syndrome, Tremor, Self-destructive behaviour, Psychotic symptom, Borderline personality disorder, Alcoholism, Suicide attempt, Influenza like illness, Food craving, ... (16 total) | `pt min_length 2` for_all |
| Outcomes | OT (other), HO (hospitalized) | `outc_cod in_set [DE,LT,HO,...]` for_all |

## External-source citations (predicate provenance)

| Predicate group | Source |
|---|---|
| 7-table `files` shape, `$`-delimited format, header-column lists | **FDA FAERS ASCII NTS specification** (`ASC_NTS.pdf`, included in every quarterly ZIP) |
| FAERS code enums (`role_cod ∈ {PS,SS,C,I}`, `outc_cod ∈ {DE,LT,HO,DS,CA,RI,OT}`, `rept_cod ∈ {EXP,DIR,...}`, `age_cod ∈ {YR,MO,DY,...}`) | **FDA FAERS data dictionary** (in the `Readme.pdf` accompanying each release) |
| Documented clozapine AE MedDRA Preferred Terms (`KNOWN_CLOZAPINE_AES` set in `skill.py`) | **FDA Clozaril prescribing information**, sections 6.1 (Adverse Reactions in Clinical Trials) and 6.2 (Postmarketing Experience), 2024 revision |
| Country-code regex `^[A-Z]{2,3}$` | **ISO 3166-1 alpha-2 / -3** standard |
| FDA date regex `^[0-9]{8}$` (YYYYMMDD) | **FAERS schema spec** |
| Quarterly URL pattern `^https://fis\.fda\.gov/content/Exports/faers_ascii_` | **FDA Open Government — FAERS Quarterly Data Files** index page |
| Identity values (drug name, primaryid, caseid) | **Search inputs** declared in `_provenance.json` |

## Spoof matrix

| Mutation | Predicate that fails |
|---|---|
| `_provenance.json` `target_drug` → "ASPIRIN" | `target.drug_name in_set ["CLOZAPINE"]` fails first; even if that passed, `documented_drug_aes_present` would be empty after intersecting against the aspirin-AE label (different MedDRA terms), failing `min_size 1` |
| `_provenance.json` `target_primaryid` → "999999999" | `target.primaryid in_set ["215586863"]` fails; also `validation.all_files_keyed_by_target_primaryid` becomes false |
| Truncate `drug.txt` to header only | `drugs min_size 1` fails (no PS row found); `validation.target_drug_in_drug_table` would be false |
| Replace `drug.txt` with rows where every `role_cod = 'C'` | `validation.target_drug_role_is_primary_suspect in_set [true]` fails |
| Add a row with `primaryid = 'OTHER'` to `reac.txt` | `validation.all_files_keyed_by_target_primaryid in_set [true]` fails |
| Rename a header column in any table (e.g. `pt → ptt` in REAC) | `reactions[*].pt min_length 2` fails on empty values; `validation.headers_match_fda_spec.REAC in_set [true]` would also fail |
| Replace REAC body with non-clozapine PTs (e.g. only "Influenza like illness", "Food craving") | `validation.documented_drug_aes_present min_size 1` fails — captures the case where the data still has FAERS shape but doesn't pertain to clozapine |

## Why clozapine

- **Black-box warning** — clozapine has documented serious AEs in the
  literature, so a non-trivial AE-report is plausibly findable in any
  recent quarter.
- **Distinctive drugname** — "CLOZAPINE" is one canonical spelling in the
  FAERS DRUG table (no ambiguous brand vs. generic split — Clozaril
  appears separately under prod_ai when listed).
- **Public, reproducible** — FAERS quarterlies are no-auth, citable URLs.

## Why 2025Q3

- Most recent quarter at capture-time (released 2025-10-29 per
  `Last-Modified`).
- Recent enough that the report's `init_fda_dt` (2022) + `fda_dt` (2025)
  span shows the FAERS report-versioning lifecycle (caseversion=3 means
  two follow-up updates after the initial submission).
