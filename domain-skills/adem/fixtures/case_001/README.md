# case_001 — International Paper – Riverdale Mill (Selma, Dallas County, AL)

## What it captures

Master ID **6298** = INTERNATIONAL PAPER COMPANY. Air permit **104-0003** —
10 most-recent documents (Feb–Apr 2026 dates) covering RATA tests, MACT
periodic-condition reports, T5 annual compliance certifications,
CEMS reports, and inventory/correspondence.

Document type distribution:
- `STR` (stack test report): 2
- `MACT` (max achievable control technology): 2
- `T5ACC` (Title V annual compliance cert): 2
- `CORS` (corrective response): 1
- `CORR` (correspondence): 1
- `MONR` (monitoring report): 1
- `CEMS` (continuous emissions monitoring): 1

Sizes range 394 KB – 5.85 MB; total ~11 MB.

## Provenance — capture method

Captured 2026-04-27 via cloud-isolated browser-harness:

1. eFile search by **Permit Number = "104-0003"** (narrower than facility-name
   search; resolved in 56s where name search timed out at 5+ minutes).
2. All 11 result rows on page 1 returned. Filtered to
   `master_id == "6298" AND county == "DALLAS"` → 10 Riverdale docs.
3. For each row, fetched the actual PDF binary from
   `https://lf.adem.alabama.gov/WebLink/ElectronicFile.aspx?docid=<id>&dbid=0&repo=ADEM&pdfView=true`
   using the browser's session cookies. (The row's `DocView.aspx?id=...` URL
   returns the WebLink viewer HTML, NOT the PDF — discovered during the
   capture; documented in `Browserstuff/browser-harness/domain-skills/adem/efile-search.md`.)
4. Each PDF parsed with pypdf, first 10 pages of text extracted, validated
   against target identifiers `["INTERNATIONAL PAPER", "6298", "DALLAS",
   "Selma", "Riverdale", "104-0003"]`.

Validation results:
- 5/10 PDFs match a target identifier in extracted text (text-extractable PDFs)
- 10/10 PDFs match in their ADEM-assigned filename (`6298 104-0003 ...`)
- All 10 marked `validated = true` via the OR criterion

The 5 PDFs without text matches are image-scanned (CEMS data exports, RATA
test report scans, T5 large compliance certifications) — pypdf returns empty
text. Their filename match is authoritative since ADEM's server assigns
filenames based on the canonical Master ID + permit number at upload time.

## Predicates exercised (23 total)

- 5 on `facility` shape (name length, master_id regex, county in 67-set, state="AL", primary_media enum)
- 1 on `facility` key set
- 2 on `permits` (size, for_all permit_number length)
- 1 on `recent_documents` size
- 8 `for_all` on `recent_documents[*]` (laserfiche_docid 8-12 digits, file_path regex, size_bytes > 10 KB,
  n_pages ≥ 1, sha256_prefix 16 hex chars, ISO date, eFile URL pattern, validated == true)
- 4 on `validation` rollup (all_validated == true, n_documents in_range, target_identifiers list, key set)
- 1 on `captured_from` URL pattern
- 1 on top-level key set

## Spoof verification

Flipping `recent_documents[0].validated` to `false` makes check-skill fail
with `for_all violated: value False not in set of 1`. Restoring → 23 ok.

Other spoofs that must fail (matrix for case_002+ regression):
- `county = "COOK"` → not in 67-county set
- `master_id = "abc"` → fails `^[0-9]{4,8}$` regex
- `recent_documents[0].size_bytes = 500` → fails `in_range [10000, ...]` (catches
  the 1.9 KB Laserfiche-error-HTML disguised as a PDF)
- `recent_documents[0].file_path = "documents/missing.pdf"` (file doesn't actually
  exist on disk) — current predicates don't enforce file existence at validation time;
  add to case_002.

## What this case does NOT exercise

- Water permit (Riverdale's water permit `24-06` was on page 1 of the name-search
  in Phase 1 but isn't returned by the permit-number search for `104-0003`)
- AEPACS profile pull (auth-walled)
- e-Maps GIS / spatial
- Enforcement / Inspection categories (none on page 1 for this permit)
- PDF body content extraction beyond the first 10 pages

## When to file case_002

A different facility — to verify the predicates generalize off Riverdale's
Master ID and the validator catches a wrong-facility download.

## Re-capture procedure

If `record.json` is lost:

```bash
# from data-harness/
BU_NAME=harnessmaker browser-harness <<'PY'
start_remote_daemon("harnessmaker")
PY

# Run the capture script (from the eFile recipe in browser-harness/domain-skills/adem/):
#   1. eFile search by permit number 104-0003 (~60s wait)
#   2. http_get-via-browser-fetch on lf.adem.alabama.gov ElectronicFile.aspx for each row
#   3. pypdf parse + validate
#   4. write record.json

cd Browserstuff/browser-harness && uv run python -c "
import sys; sys.path.insert(0, '.')
from admin import stop_remote_daemon
stop_remote_daemon('harnessmaker')
"
```
