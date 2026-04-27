# adem — Alabama Department of Environmental Management

## What it does

Extracts canonical Facility records from ADEM's public eFile portal. Given a
facility identifier (Master ID or name), produce a normalized object with the
facility's identity, location, permits, and recent documents — validated by
predicate-first fixtures so downstream analysis can trust the schema.

## Inputs

`fixtures/case_<NNN>/inputs/record.json` — the captured Facility record
(extracted via the eFile search recipe documented in the capture-recipe doc).
The capture itself happens via the browser-harness eFile recipe; this skill
operates on the resulting JSON.

## Output (skill.py contract)

The skill is identity-with-validation in v0 — the captured `record.json`
already has the canonical shape. Phase 4+ may add an actual transform layer
when the input shape evolves (e.g., raw HTML → canonical shape).

Canonical Facility shape:

```python
{
    "facility": {
        "name":           str,
        "adem_master_id": str,         # numeric string, 4-5 digits
        "location":       {"county": str, "state": "AL", ...},
        "operator":       str,
        "primary_media":  "Air" | "Water" | "Land" | "Multi"
    },
    "permits": [
        {"permit_number": str, "media_type_code": str, ...}
    ],
    "recent_documents": [
        {"date": "YYYY-MM-DD", "type": str, "permit_number": str,
         "url": "http://lf.adem.alabama.gov/weblink/DocView.aspx?id=...&dbid=0",
         "file_name": str}
    ],
    "captured_from":  "https://app.adem.alabama.gov/eFile/Default.aspx",
    "captured_at_utc": str        # ISO-8601
}
```

## Predicates

`fixtures/case_001/expected.json` enforces:

- `name`, `adem_master_id`, `county` shapes (county must be one of the 67
  Alabama counties — tight predicate that catches a wrong-state extraction)
- `primary_media` is one of `{Air, Water, Land, Multi}`
- `permits` and `recent_documents` are non-empty lists with bounded sizes
- Each `recent_documents[*].url` matches the Laserfiche WebLink pattern
- Each date is ISO-8601
- The `facility` dict has the full key set
- `embedding_cosine_to` predicate ties the captured `name` to a reference
  description — currently skipped in v0 (the embedder is wired in Phase 2d)
  but preserved as the future-proof contract

## Capture provenance

case_001's `record.json` was extracted from a real `INTERNATIONAL PAPER` name
search on eFile (Phase 1 scout), filtered client-side to `master_id == "6298"
AND county == "DALLAS"` (Riverdale Mill in Selma). The Phase 3 fresh-recapture
attempt was blocked by ADEM-server slowness (postback >3 minutes) — Phase 1's
real captured rows are reused since the facts (Master ID, county, permits,
type codes, date format) are independently verifiable.

## Future cases

- case_002 = different facility (e.g. 3M Decatur, Master ID TBD) — verifies
  the predicate set generalizes off Riverdale's specific embedding-cosine
  reference.
- case_003 = same facility with PDF download (exercises Laserfiche WebLink
  fetch + later PDF/OCR pipeline).
- case_004 = facility with active enforcement record (introduces a richer
  document-type distribution including Enforcement category).
- case_005 = AEPACS profile pull (auth-walled; deferred until profile-sync).
