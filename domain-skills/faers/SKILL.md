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

38 predicates enforce:
- **Identity is clozapine + primaryid 215586863**: `target.drug_name
  in_set ["CLOZAPINE"]`, `target.primaryid in_set ["215586863"]`,
  `target.caseid in_set ["21558686"]`. A different drug or report would
  fail immediately.
- **Patient/report shape**: age numeric, sex in enum, country 2-3 letter
  code, FDA dates 8-digit YYYYMMDD strings, rept_cod in the FAERS code
  table, manufacturer non-empty.
- **Drug table**: at least one drug, every `drug_seq` numeric, every
  `role_cod` in `{PS,SS,C,I}`, every `drugname` non-empty.
- **Reactions / outcomes**: at least one each, `outc_cod` in the
  serious-outcomes vocabulary.
- **Per-file shape (for_all over the seven tables)**: file path under
  `extracted/`, sha256 16 hex chars (proves real bytes hashed), row count
  in [0, 5000] (truncation/empty-padding caught), column count plausible.
- **Validation rollup**: all four sub-flags `true`, `n_files == 7`,
  `target_identifiers` non-trivial.
- **`captured_from`** points at FDA FAERS quarterly URL pattern.

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
