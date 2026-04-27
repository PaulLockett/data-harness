# faers — FDA Adverse Event Reporting System

## What it does

Reads filtered subsets of the FDA's quarterly FAERS data dumps and emits a
canonical AE-report record. Given a target drug + primaryid (FAERS report
key), the skill verifies that the drug appears in the report's DRUG table
with `role_cod = PS` (primary suspect), every persisted row across the seven
FAERS tables shares that primaryid, and the report has the expected
DEMO + DRUG + REAC + OUTC structure. Predicates assert both **schema shape**
AND **content provenance** — `validated == true` only when the report is
demonstrably about the declared target drug.

## FAERS schema (the seven $-delimited ASCII tables)

Every quarterly dump contains exactly these seven tables, each prefixed by
the quarter (e.g. `DEMO25Q3.txt`, `DRUG25Q3.txt`):

| Table | Grain | Contents |
|---|---|---|
| `DEMO` | one row per `primaryid` | report metadata: caseid, caseversion, FDA dates, age, sex, weight, country, manufacturer (`mfr_sndr`), reporter occupation |
| `DRUG` | one row per (primaryid, drug_seq) | every drug taken: `drugname`, `prod_ai`, `role_cod` (PS/SS/C/I), route, dose |
| `REAC` | one row per (primaryid, reaction) | `pt` = MedDRA Preferred Term for the adverse event |
| `OUTC` | one row per (primaryid, outc_cod) | `outc_cod` ∈ {DE death, LT life-threatening, HO hospitalized, DS disability, CA congenital anomaly, RI required intervention, OT other} |
| `RPSR` | one row per (primaryid, source) | report source codes |
| `THER` | one row per (primaryid, drug_seq) | therapy timeline: start_dt, end_dt, dur, dur_cod |
| `INDI` | one row per (primaryid, indi_drug_seq) | drug indication (why the drug was taken), MedDRA-coded |

Field separator is `$` (not comma — many fields contain commas, e.g. dose
narratives). No quoting. The first line is the header.

## Capture flow

1. **Pick a quarter** and verify the URL exists at
   `https://fis.fda.gov/content/Exports/faers_ascii_<YYYYqQ>.zip`. The FDA
   Qlik server responds 200 to HEAD with `Content-Length: 0` (a server
   quirk) but honors range GETs and the magic bytes confirm a real ZIP.
2. **Download to scratch.** ZIPs are 50–200 MB each (~73 MB for 2025Q3).
   Use `httpx` or `curl` directly to `/tmp`, NOT under `inputs/`.
3. **Extract the seven `*.txt` ASCII tables** to a scratch directory.
   Uncompressed total is ~430 MB (DRUG dominates at ~210 MB).
4. **Pick a target drug** with a documented serious AE profile and a known
   `role_cod = PS` presence in the data. Examples: clozapine
   (agranulocytosis, myocarditis), warfarin (bleeding), acetaminophen
   (hepatotoxicity).
5. **Filter via Polars `scan_csv` (separator='$', infer_schema_length=0)**:
   join DRUG to OUTC, find primaryids where the drug is PS and the
   outcome is serious, pick one with the richest reactions table for
   maximum predicate coverage.
6. **Persist filtered subsets only.** For each of the seven tables, write
   only the rows where `primaryid == target_primaryid` to
   `inputs/extracted/<table>.txt` (each is a few hundred bytes to a few KB).
7. **Delete scratch.** The 73 MB ZIP and 430 MB extracted tables are gone;
   `inputs/` adds <10 KB to the repo.

## Inputs

`fixtures/case_<NNN>/inputs/`:
- `_provenance.json` — declares `target_drug` (uppercase string),
  `target_primaryid`, `target_caseid`, `target_aliases` (lowercase + brand
  names), the FAERS quarterly URL, capture method, and a `table_files` map
  pointing at the seven persisted subsets.
- `extracted/{demo,drug,reac,outc,rpsr,ther,indi}.txt` — Polars-filtered
  $-delimited text files, all keyed by the same primaryid. Some may have
  zero data rows (e.g. RPSR or THER) but always include the header line.

## Output (skill.py contract)

`run(inputs_dir: Path) -> dict` returns:

```python
{
    "target":         {"drug_name", "primaryid", "caseid", "case_version"},
    "report":         {
        "primaryid": str, "caseid": str, "case_version": str,
        "patient":     {"age", "age_cod", "age_grp", "sex",
                        "weight", "weight_cod", "country"},
        "report_meta": {"rept_cod", "init_fda_dt", "fda_dt", "mfr_sndr",
                        "auth_num", "mfr_num", "occp_cod",
                        "reporter_country"},
    },
    "drugs":          [{"drug_seq", "role_cod", "drugname", "prod_ai",
                        "route", "dose_vbm", "dose_amt", "dose_unit",
                        "dose_form", "dose_freq", "dechal", "rechal",
                        "nda_num"}, ...],
    "reactions":      [{"pt", "drug_rec_act"}, ...],
    "outcomes":       [{"outc_cod"}, ...],
    "indications":    [{"drug_seq", "indi_pt"}, ...],
    "therapy":        [{"drug_seq", "start_dt", "end_dt",
                        "dur", "dur_cod"}, ...],
    "report_sources": [{"rpsr_cod"}, ...],
    "files":          [{"table", "file_path", "size_bytes",
                        "sha256_prefix", "n_rows", "n_columns",
                        "header"}, ...],
    "captured_from":   str,
    "captured_at_utc": str,
    "capture_method":  str,
    "validation": {
        "all_validated":                       bool,
        "target_drug_in_drug_table":           bool,
        "target_drug_role_is_primary_suspect": bool,
        "all_files_keyed_by_target_primaryid": bool,
        "n_files":                             int,
        "n_drugs":                             int,
        "n_reactions":                         int,
        "n_outcomes":                          int,
        "target_identifiers":                  [str, ...],
    },
}
```

## Predicates (case_001)

46 predicates total. Provenance per predicate group:

| Group | Predicate(s) | Source — how this could fail |
|---|---|---|
| **Identity** (5) | `target.drug_name in_set ["CLOZAPINE"]`, `target.primaryid in_set ["215586863"]`, `target.caseid in_set ["21558686"]`, `case_version` regex, `target` keyset | **External** — these are the search inputs. A different drug or report would fail; a corrupted target spec also fails. |
| **Patient/report shape** (8) | age regex, age_cod / sex / rept_cod in_set, country regex, FDA dates regex, mfr_sndr min_length | **External (FAERS schema)** — code enums come from FDA's ASC_NTS spec; date regex from spec; country regex from ISO. Captured-data values must conform to schema-mandated formats. |
| **Drug / Reaction / Outcome content** (7) | `drugs[*].role_cod in {PS,SS,C,I}`, `drugs[*].drug_seq` regex, `drugs[*].drugname min_length 1`, `reactions[*].pt min_length 2`, `outcomes[*].outc_cod in {DE,LT,HO,DS,CA,RI,OT}` | **External (FAERS schema)** — every value enum is FDA-published. A row-shuffled or broken-encoding capture fails. |
| **Per-file shape** (5, all for_all) | `files min/max_size 7`, `files[*].table` in the seven-table set, `file_path` regex, `sha256_prefix` 16 hex, `n_rows in [0, 5000]`, `n_columns in [2, 50]` | **External (FAERS schema)** + **captured-data structural** — quarter must produce exactly seven $-delimited tables. |
| **FDA-spec header conformance** (5) | `validation.all_headers_match_fda_spec in_set [true]`, plus per-table booleans for DEMO/DRUG/REAC/OUTC | **External (FDA ASC_NTS.pdf)** — every quarter's tables MUST have these exact column names. Schema drift at FDA OR a wrong-table extraction fails. |
| **Documented-drug-AE intersection** (3) | `n_documented_drug_aes_present in_range [1,60]`, `documented_drug_aes_present min_size 1`, every entry `in_set` of FDA Clozaril label MedDRA PTs | **External (FDA Clozaril prescribing information, sections 6.1/6.2)** — the captured report's reactions must include at least one term from clozapine's labeled AE list. A wrong-target capture (e.g. an aspirin report) would have no overlap. |
| **Validation rollup** (4 booleans + 4 counts) | `all_validated`, `target_drug_in_drug_table`, `target_drug_role_is_primary_suspect`, `all_files_keyed_by_target_primaryid` ∈ `{true}`; `n_files==7`; `target_identifiers min_size 2` | **Captured-data-only / belt-and-suspenders** — these mirror the skill's own validation flags. They're redundant with the strong external predicates above but make the failure message clearer when the data's wrong. |
| **Capture URL + root keyset** (2) | `captured_from` regex `^https://fis\.fda\.gov/content/Exports/faers_ascii_`; root key_set_includes | **External** — locks the data to FDA's published URL pattern. |

The strong **external** predicates (~28 of 46) would catch a wrong capture
even if the skill's own validation flags were broken; the **captured-data-only**
predicates (~12) are belt-and-suspenders. The case still passes if any
non-load-bearing predicate is removed; it fails on any of the external ones.

## Future cases

- **case_002**: a different drug + different quarter (e.g. warfarin in
  2024Q4). Re-tightens `target.drug_name` and `target.primaryid`; verifies
  the predicate template generalizes off clozapine specifics.
- **case_003**: a death-outcome (DE) report. Adds `outcomes[*].outc_cod
  in_set ["DE", ...]` for_all and an explicit assertion that one of the
  outcomes is DE — exercises the most serious code path.
- **case_004**: a multi-quarter join across the same caseid (FAERS reports
  are versioned; `caseversion` increments on follow-up). Exercises the
  longitudinal nature of FAERS.
- **case_005**: cross-domain composition with the `disaggregate`
  interaction-skill — break reaction rates by age_grp / sex.
