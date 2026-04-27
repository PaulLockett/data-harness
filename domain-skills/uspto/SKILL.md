# uspto — US patent records

## What it does

Reads a captured Google Patents HTML mirror of a USPTO patent record and
emits a canonical Patent record. Validates extracted fields against
externally-known facts (filing/grant dates, inventor, assignee,
application number, patent-number format) sourced from public USPTO
records.

## Data source

USPTO's `api.uspto.gov` requires an authentication token outside v0
scope (returns 403 "Missing Authentication Token" without registration).
case_001 uses **Google Patents** as a stable no-auth public mirror —
Google indexes the full USPTO data corpus and exposes structured
metadata via `<meta name="DC.*">` and `<meta name="citation_*">` tags.
Predicates anchored to USPTO patent-numbering conventions and the
inventor/assignee facts apply unchanged regardless of the host. case_002
may wire the api.uspto.gov path when an API key is added.

## Capture flow

1. **Pick a target patent.** Use a well-documented patent whose inventor,
   assignee, and dates are independently verifiable from non-USPTO
   sources (a published patent expiry notice, a corporate press release,
   a Wikipedia citation, etc.).
2. **Fetch the Google Patents page** at
   `https://patents.google.com/patent/<COUNTRY><NUMBER>/en` (e.g.
   `US6285999/en` for the PageRank patent). Response is ~1-3 MB HTML
   per patent; no auth.
3. **Save verbatim** as `inputs/patent.html`. Keep the full HTML so the
   capture is reproducible from the file alone.

## Inputs

- `_provenance.json` — declares `target_patent_number`, `target_country_code`,
  `target_application_number`, `target_filing_date`, `target_grant_date`,
  `target_inventor`, `target_assignee`, `target_title_keywords`, capture
  URL and method.
- `patent.html` — full Google Patents page.

## Output (skill.py contract)

`run(inputs_dir: Path) -> dict` returns:

```python
{
    "target":  {patent_number, country_code, application_number,
                filing_date, grant_date, inventor, assignee,
                title_keywords},
    "patent":  {
        "patent_number":       str,
        "country_code":        "US" | "EP" | ...,
        "raw_citation":        "US:6285999",
        "application_number":  "09/004,827",
        "application_country": "US",
        "filing_date":         "YYYY-MM-DD",
        "grant_date":          "YYYY-MM-DD",
        "title":               str,
        "abstract":            str,
        "pdf_url":             str,
        "n_contributors":      int,
        "contributors":        [str, ...],   # combined inventors + assignees
        "n_relations":         int,           # related patents (DC.relation)
        "n_references":        int,           # academic literature refs
        "n_citing":            int,
    },
    "files":   [{"file_path", "size_bytes", "sha256_prefix",
                 "format": "html"}],
    "captured_from", "captured_at_utc", "capture_method": str,
    "validation": {
        "all_validated", "patent_number_matches_target",
        "country_code_matches_target",
        "application_number_matches_target",
        "filing_date_matches_target", "grant_date_matches_target",
        "target_inventor_in_contributors",
        "target_assignee_in_contributors",
        "title_contains_keywords": bool,
        "n_files": int, "target_identifiers": [str, ...],
    },
}
```

## Predicates (case_001) — 43 total

| Group | Source |
|---|---|
| **Identity** (8): patent_number, country, application_number, filing_date, grant_date, inventor, assignee in_set | **External** — search inputs (each a public fact) |
| **Patent extracted** (16): patent_number `in_set ["6285999"]`, country=US, application_number regex `^[0-9]{2}/[0-9]{3},[0-9]{3}$`, filing+grant dates `in_set [exact dates]`, title min_length, abstract min_length, pdf_url regex (Google's patentimages bucket), contributor count, n_relations, n_references | **External**: USPTO patent-numbering convention + application-number format + Google Patents PDF URL pattern + public PageRank patent facts (Page, Stanford, 1998-01-09 filed, 2001-09-04 granted) |
| **Per-file shape** (5 for_all + 1) | Structural |
| **Validation rollup** (10) | Captured-data-only / belt-and-suspenders |
| **Capture URL + root keyset** (2) | **External** — Google Patents URL pattern |

The strong **external** predicates (~26 of 43) would catch a wrong
capture even with the validation booleans removed.

## Future cases

- **case_002**: a different patent (e.g. iPhone touch-screen patent
  US7479949 = Steve Jobs et al; HTTP/3 patent US10911549 = Apple).
  Re-tightens identity values; verifies the predicate template
  generalizes off PageRank specifics.
- **case_003**: the api.uspto.gov direct path once an API key is
  wired. Captures `inputs/patent.json` instead of HTML; predicates
  carry over with field-name remapping.
- **case_004**: an EP (European Patent) record from EPO Open Patent
  Services or Google Patents — exercises non-US country code
  predicates.
- **case_005**: cross-domain composition with the substrate's text
  helpers — embed the abstract via models.embed and run a similarity
  predicate.
