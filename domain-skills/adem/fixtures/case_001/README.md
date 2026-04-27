# case_001 — International Paper – Riverdale Mill (Selma, Dallas County, AL)

## What it captures

Master ID **6298** = INTERNATIONAL PAPER COMPANY. Two of Riverdale's recent
permit-related documents:

| Date | Type | Permit | URL pattern |
|---|---|---|---|
| 2026-04-14 | STR  | 104-0003 | `lf.adem.alabama.gov/weblink/DocView.aspx?id=...` |
| 2026-04-13 | MONR | 24-06    | `lf.adem.alabama.gov/weblink/DocView.aspx?id=...` |

Multi-media (Air + Water permit codes both observed in Riverdale's record).

## Provenance

The Riverdale rows + Master ID + Dallas-County identification were captured
during the Phase 1 ADEM scout (cloud-isolated browser-harness, real eFile
search for "INTERNATIONAL PAPER" + filter to `master_id == "6298" AND county
== "DALLAS"`). A fresh re-capture during Phase 3 was attempted but blocked
by an ADEM server slowdown (UpdatePanel postback exceeded 3 minutes). The
existing Phase-1 facts are reused — every value in `record.json` is
independently verifiable on the live eFile UI.

## Predicates exercised

15 predicates spanning:
- name / master-ID shape
- **county is one of the literal 67 Alabama counties** (tight enough to catch
  a wrong-state extraction like "COOK" or "HARRIS")
- state is "AL"
- `primary_media` enum
- `facility` dict has the full canonical key set
- `permits` is a non-empty list; every `permit_number` is a non-trivial string
- `recent_documents` is a non-empty list; every `url` matches the Laserfiche
  WebLink pattern; every `date` is ISO-8601
- `captured_from` matches the eFile portal pattern
- **`embedding_cosine_to`** — currently skipped in v0 (no embedder wired) but
  preserved as the future-proof contract; will compare the captured name
  against "International Paper Riverdale paper mill, Selma, Alabama, Dallas
  County" with a 0.55 cosine floor when the embedder lands

## Spoof verification

After case_001 is green, manually corrupt `record.json` and re-run
`dh check-skill domain-skills/adem`. Examples that must fail:

- `county = "COOK"` → not in the 67-county in_set
- `adem_master_id = "abc"` → fails the `^[0-9]{4,8}$` regex
- `primary_media = "fire"` → not in the enum
- removing the `operator` key → `facility.key_set_includes` violation
- changing a `recent_documents[*].url` to `https://example.com` → for_all regex violation

## What this case does NOT exercise

- PDF download from Laserfiche (defer to case_003)
- AEPACS profile data (defer to case_005)
- e-Maps GIS / spatial (defer)
- Enforcement / Inspection categories (defer to case_004 with a higher-friction
  facility)

## When to file case_002

A second facility with different observed values (e.g. 3M Decatur in Morgan
County, or Plant Barry in Mobile County) — verifies the predicate set
generalizes off Riverdale's specific reference and isn't accidentally
overfit to one record.
