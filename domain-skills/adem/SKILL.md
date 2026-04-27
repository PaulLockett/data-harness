# adem — Alabama Department of Environmental Management

## What it does

Extracts canonical Facility records from ADEM's public eFile portal. Given a
facility identifier (Master ID, name, or permit number), produce a normalized
object with the facility's identity, location, permits, and downloaded +
validated recent documents. Predicates assert both **schema shape** AND
**content provenance** — every PDF in the record must be locally on disk,
parseable, and contain the target identifier (in the filename or extracted
text), so downstream analysis trusts that the documents are what they claim.

## Capture flow

1. Search eFile (`https://app.adem.alabama.gov/eFile/Default.aspx`) by
   permit number, facility name, or Master ID. ADEM's DB is slow — plan
   on 60s to 5+ minute UpdatePanel postbacks.
2. Filter the result grid to rows matching the target facility (e.g.
   `master_id == "6298" AND county == "DALLAS"` for Riverdale Mill).
3. For each row, fetch the binary PDF from
   `https://lf.adem.alabama.gov/WebLink/ElectronicFile.aspx?docid=<id>&dbid=0&repo=ADEM&pdfView=true`
   using the cloud browser's session cookies (via `js fetch(..., {credentials: 'include'})`).
   The `DocView.aspx` URL on the row is the *viewer page* and returns HTML;
   `ElectronicFile.aspx` is the binary endpoint.
4. Save each PDF under `inputs/documents/<safe_filename>.pdf`.
5. Parse each PDF with pypdf; extract first 10 pages of text.
6. **Validate every document**: text contains a target identifier
   (`INTERNATIONAL PAPER`, the Master ID, county name, facility nickname,
   or permit number) OR the filename contains one. Image-scanned PDFs that
   fail text extraction still pass via filename match — ADEM's filename
   convention starts with `<master_id> <permit> ...`.

## Inputs

`fixtures/case_<NNN>/inputs/`:
- `record.json` — the canonical Facility object (output of the capture flow)
- `documents/*.pdf` — every PDF referenced by `record.recent_documents[*].file_path`
- `raw_rows_page1.json`, `_riverdale_rows_raw.json` — auxiliary scout artifacts (filtered + raw)
- `page.html` — full HTML snapshot of the eFile results page (debugging)

## Output (skill.py contract)

The skill is currently identity-with-validation — `record.json` is the
canonical shape directly. Future cases may add an actual transform layer
when the input shape evolves (e.g., raw HTML → canonical shape).

Canonical Facility shape:

```python
{
    "facility": {
        "name": str,
        "adem_master_id": str,         # numeric string, 4-5 digits
        "location": {"county": str, "state": "AL"},
        "operator": str,
        "primary_media": "Air" | "Water" | "Land" | "Multi",
    },
    "permits": [{"permit_number": str, "media_type_code": str}, ...],
    "recent_documents": [
        {
            "date":             "YYYY-MM-DD",
            "type":             str,            # ADEM doc-type code (DMR, STR, MACT, ...)
            "permit_number":    str,
            "laserfiche_docid": str,            # 8-12 digit Laserfiche ID
            "file_name":        str,            # ADEM-assigned filename
            "file_path":        "documents/...",  # local relative path
            "size_bytes":       int,
            "n_pages":          int,            # pypdf page count
            "sha256_prefix":    str,            # first 16 hex chars
            "url":              str,            # original DocView.aspx URL
            "text_excerpt":     str,            # first 300 chars of extracted text
            "text_matches":     [str, ...],     # target identifiers found in text
            "filename_matches": [str, ...],     # target identifiers found in filename
            "validated":        bool,           # text or filename match
        }, ...
    ],
    "captured_from":  "https://app.adem.alabama.gov/eFile/Default.aspx",
    "captured_at_utc": str,
    "capture_method": str,
    "validation": {
        "all_validated":      bool,
        "n_text_matches":     int,
        "n_filename_matches": int,
        "n_documents":        int,
        "target_identifiers": [str, ...],
    },
}
```

## Predicates (case_001)

23 predicates enforce:
- facility shape (county is one of the literal 67 Alabama counties; state="AL"; primary_media enum)
- permits non-empty with non-trivial permit numbers
- **every document exists on disk** (`file_path` regex `^documents/.*\.pdf$`)
- **every document is a real PDF** (`size_bytes > 10 KB`, `n_pages >= 1`, `sha256_prefix` 16 hex chars)
- **every document is validated** (`validated == true` for_all)
- `laserfiche_docid` is 8-12 digit numeric
- `validation.all_validated == true` rolls up the per-document checks

## Future cases

- case_002: a different facility (e.g. 3M Decatur, Plant Barry) — verifies
  predicates generalize.
- case_003: the same facility, captured by name search rather than permit
  number — verifies the capture flow is search-shape-agnostic.
- case_004: a facility with active enforcement docs (Enforcement category) —
  introduces a richer document-type distribution.
- case_005: AEPACS profile pull (auth-walled; deferred).
