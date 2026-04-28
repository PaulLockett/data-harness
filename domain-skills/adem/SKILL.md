---
name: adem
description: Longitudinal analysis of Alabama Department of Environmental Management NPDES Construction General Permit (ALR100000) coverages, inspections, BMP findings, and enforcement actions. Produces canonical year-over-year and per-company rollups from raw eFile metadata + parsed inspection text.
---

# adem — NPDES Construction Stormwater Longitudinal Analysis

## What it does

Given a corpus of ADEM eFile metadata rows and ADEM CSW inspection report
text, produce a canonical multi-year analysis of construction-stormwater
permit activity, regulatory inspection coverage, BMP-category findings,
and enforcement gaps. The output is a single JSON object suitable for
loading into a dashboard, embedding in a report, or replaying as a
fixture for downstream skills.

**Scope boundary.** This skill is about the **data work**: parsing,
categorizing, joining, rolling up. It does **not** include eFile portal
scraping, Laserfiche document downloading, or any HTTP/browser
interaction with the ADEM web systems — those concerns belong in
`browser-harness/domain-skills/adem/`. This skill consumes whatever
those upstream systems produce.

## Pipeline shape

```
                browser-harness (separate concern)
  ─────────────────────────────────────────────────────────
                          ↓
  raw_rows_YYYY.jsonl   (eFile metadata: docid, permit, name,
                         county, date, type, fname per document)
  inspection_corpus/    (raw INSPR documents — PDF, .pptx,
                         .docx, .xlsx, legacy .doc)
                          ↓
                  data-harness/adem (this skill)
  ─────────────────────────────────────────────────────────
   1. Multi-format text extraction
        - PDF → liteparse OCR (capped pages)
        - .pptx/.docx/.xlsx → python-pptx/python-docx/openpyxl
        - legacy .doc/.xls/.ppt → soffice → liteparse
   2. Per-inspection BMP categorization
        - silt_fence, inlet_protection, gravel_entrance,
          vegetation, general_bmp
        - cited vs problem (negative-context window)
   3. Per-permit aggregation
        - "site started" = year of first NOI on that permit
        - any inspection cited problem → site flagged
        - any ENOV/EWL/EAO → site flagged enforced
   4. Rollups
        - yearly_trend: started / inspected / cited_problem / enforced per year
        - top_builders_by_sites
        - top_builders_by_unenforced_violations  ← key accountability metric
        - bmp_category_counts
        - regional: per-watershed (e.g. Mobile Bay = Mobile + Baldwin)
                          ↓
                    record.json (canonical output)
```

## Canonical output shape

```python
{
  "analysis": str,                   # human-readable description
  "scope": {
    "permit_prefix": "ALR10",        # ADEM CGP individual coverages
    "media_area":   "Water",
    "date_start":   "YYYY-MM-DD",
    "date_end":     "YYYY-MM-DD",
    "years_covered": int,
  },
  "totals": {
    "sites_started":                  int,
    "sites_inspected":                int,
    "sites_with_cited_problem":       int,
    "sites_enforced":                 int,
    "sites_unenforced_gap":           int,    # cited problem AND no enforcement
    "inspections_processed":          int,
    "inspections_with_cited_problem": int,
  },
  "yearly_trend": [
    {"year": int, "sites_started": int, "sites_inspected": int,
     "sites_cited_problem": int, "sites_enforced": int,
     "pct_inspected": float, "pct_enforced": float}, ...
  ],
  "top_builders_by_sites": [
    {"company": str, "sites": int, "inspected": int,
     "cited_problem": int, "enforced": int, "unenforced_gap": int}, ...
  ],
  "top_builders_by_unenforced_violations": [...],   # same shape, sorted by gap
  "bmp_category_counts": {
    "silt_fence":         int,
    "inlet_protection":   int,
    "gravel_entrance":    int,
    "vegetation":         int,
    "general_bmp":        int,
  },
  "regional": {
    "<region_name>": {
      "counties": [str, ...],
      "sites_started": int,
      "sites_inspected": int,
      "sites_with_cited_problem": int,
      "sites_enforced": int,
      "sites_unenforced_gap": int,
      "top_builders_by_sites":         [...],
      "top_builders_by_unenforced":    [...],
    }, ...
  },
  "captured_from":   "https://app.adem.alabama.gov/eFile/",
  "document_archive":"https://lf.adem.alabama.gov/WebLink/",
  "captured_at_utc": "ISO8601",
  "capture_method":  str,             # one-line description of pipeline
  "documents_processed": {
    "total_eFile_documents":         int,
    "inspr_documents_extracted":     int,
    "inspr_documents_unreachable":   int,
  },
}
```

## Inputs

`fixtures/case_<NNN>/inputs/`:
- `record.json` — the canonical analysis (identity-with-validation case).
  Future cases may add an actual transform layer (`skill.py`) operating
  on raw `rows.jsonl` + `inspections/*.txt`.

## Predicates (case_001)

The contract: **shape and plausibility** for each top-level field, plus
`for_all` checks on every yearly trend entry and every builder row, so
the predicate set fails on any drift in either the captured numbers or
the canonical shape.

Specifically:
- `scope` has the expected keys with valid values
- `totals` includes all 7 metrics, each non-negative integers in plausible ranges
- `yearly_trend` is non-empty; every entry has year in [2009, 2030],
  rates in [0, 100], counts non-negative
- `top_builders_*` entries each have a non-empty company name and integer
  site/inspected/cited/enforced/gap fields
- `bmp_category_counts` has all 5 known categories
- `regional` has at least one watershed rollup with the same per-region
  metrics shape as totals
- `captured_from` matches the eFile portal URL pattern
- `captured_at_utc` is ISO 8601

## Methodology notes

**"Site started" vs "NOI filed".** A single permit can have multiple
NOIs over its lifetime (initial filing, amendments, ownership transfers,
5-year cycle reissuances). This skill counts each unique permit's
**first** NOI as the site's start date. Counting all NOIs as starts
inflates totals 2-3× and produces phantom booms in re-filing years.

**BMP problem detection.** A category is flagged as "cited problem"
when the inspector text mentions both a category keyword (e.g. "silt
fence") AND a negative phrase (e.g. "not maintained", "absent",
"failing", "inadequate") within a ±200-character window. This is a
high-precision conservative classifier that under-counts rather than
over-counts. It does not capture violations the inspector failed to
cite — that is the domain of a future vision-verification pass over
inspection photos.

**Enforcement.** A site is enforced if any of three formal document
types appear on the permit: ENOV (Notice of Violation), EWL
(Enforcement Warning Letter), EAO (Enforcement Action Order). Routine
correspondence (CORR/CORS), engineering reports (ERPL), and complaints
(COMP) are not counted as enforcement.

**Multi-format handling.** ADEM's INSPR corpus spans nearly two
decades of document-format conventions. Pre-AEPACS (rough cutoff
~2018) heavily uses Microsoft PowerPoint and Word, both legacy CFB
and modern Open XML. The pipeline auto-detects format via magic bytes
and the zip directory layout (Open XML zips contain `ppt/`, `xl/`, or
`word/` subtrees that disambiguate the parser to call). Each format
gets its fastest correct path: native Python parsers for Open XML
(milliseconds), LiteParse for PDFs (seconds), and LibreOffice
round-trip only for legacy CFB binaries (~5s, with per-worker profile
directories required to allow parallel invocation without collisions).

## Future cases

- **case_002**: a different state agency with the same regulatory shape
  (e.g. Mississippi DEQ NPDES) — verifies the shape generalizes beyond
  Alabama-specific permit prefixes.
- **case_003**: a single-county slice for fast iteration during
  development of new BMP categories or rollup dimensions.
- **case_004**: an enriched-with-vision case — adds vision-model
  flags to the per-site rollup (`bmp_vision_problem` columns) so the
  analysis can identify inspector-missed violations alongside
  inspector-cited ones.
