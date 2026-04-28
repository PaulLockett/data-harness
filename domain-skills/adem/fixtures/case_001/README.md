# case_001 — Statewide NPDES Construction Stormwater Longitudinal Analysis (2009-2026)

## What it captures

The full canonical analysis output of every electronically-recorded ADEM
NPDES Construction General Permit (ALR100000) coverage from June 8,
2009 through April 27, 2026. **22,325 unique construction sites,
33,326 inspection reports, 123,424 total eFile documents** distilled
into a single JSON object.

The case is **identity-with-validation**: `inputs/record.json` is the
canonical analysis output and predicates assert its shape and
plausibility ranges. There is no `skill.py` transform — future cases
may add one operating on raw inputs.

## Key headline numbers (as of capture date)

- **22,325** sites started
- **12,654** with at least one ADEM inspection on file
- **8,519** with an inspector-cited BMP problem in writing
- **3,571** with formal enforcement action
- **6,230** sites with cited problems and **no enforcement filed** —
  the systemic ADEM enforcement gap

## Provenance — capture method

The upstream eFile scraping and Laserfiche document download is the
responsibility of `browser-harness/domain-skills/adem/`. This skill
consumes that output:

1. **Metadata phase** (browser-harness): year-by-year HTTP postback
   pagination of the eFile search portal filtered by Water + ALR10
   permit prefix + 1/1 to 12/31 date range, producing
   `rows_YYYY.jsonl` files. 18 years × ~5-10K rows/year = 123,424
   total document metadata records.
2. **Document download phase** (browser-harness): for each INSPR-type
   document on a permit with at least one NOI, fetch the binary from
   `https://lf.adem.alabama.gov/WebLink/ElectronicFile.aspx?docid=<id>&pdfView=true`
   using the cloud browser's session cookies.
3. **Text extraction phase** (this skill): multi-format dispatch —
   PDFs through LiteParse OCR (capped at 12 pages per doc for
   inspector-summary range), Open XML PowerPoint/Word/Excel through
   native Python parsers (python-pptx, python-docx, openpyxl), legacy
   CFB binaries through soffice → LiteParse with per-worker LibreOffice
   profile dirs to allow parallel invocation.
4. **BMP categorization** (this skill): regex against extracted text
   for five BMP categories (silt fence, inlet protection, gravel
   entrance, vegetation/slope, general BMP), with a ±200-character
   negative-context window check to distinguish a cited problem from
   a routine mention.
5. **Per-permit aggregation** (this skill): collapse per-inspection
   findings to per-site flags. "Site started" = year of first NOI.
6. **Rollups** (this skill): yearly trend, top builders by sites and
   by unenforced violations, BMP category counts, regional watershed
   slices.

Total compute time: ~24 hours for first run, ~12 hours steady state.

## Predicates exercised

61 predicates covering:
- **Top-level shape**: 13 expected keys
- **Scope**: permit_prefix in {ALR10}, media_area in {Air,Water,Land,Multi},
  ISO date format, years_covered range
- **Totals**: 7 metrics, all integer with plausible ranges
- **Yearly trend**: 5-30 entries, every entry has year in [2009,2030],
  rates in [0,100], counts non-negative (`for_all`)
- **Top builders**: 5-50 entries each in two ranked lists, every entry
  has non-empty company name and integer site/inspected/cited/enforced/gap
  fields (`for_all`)
- **BMP categories**: all 5 known categories must be present
- **Regional**: at least the Mobile Bay watershed entry, with proper
  Alabama county codes (`for_all` against the 67-county set)
- **Provenance**: captured_from regex matches eFile portal,
  document_archive regex matches Laserfiche, captured_at_utc is ISO 8601

## Spoof verification

The predicate set rejects:
- Single-year toy datasets (yearly_trend min_size=5)
- Empty top-builder lists
- Regional rollups missing required metrics
- Captures from unrelated systems (URL pattern enforcement)
- Counter-factual ranges (e.g. negative site counts, percentages > 100)

## Future cases

- **case_002**: a different state agency NPDES system to verify the
  shape generalizes
- **case_003**: a single-county or single-year slice for fast
  development iteration
- **case_004**: an enriched-with-vision case adding inspector-missed
  violation columns from a vision-model verification pass
