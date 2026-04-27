# case_001 — US Patent 6,285,999 (PageRank, Lawrence Page, Stanford)

## What this case demonstrates

The PageRank patent — the algorithmic foundation of Google's web search
engine. Filed by Lawrence Page (Larry Page, Google co-founder) while a
Stanford PhD student; granted to Stanford. Stanford licensed the patent
to Google in exchange for ~1.8 M Google shares. Captured from Google
Patents because USPTO's api.uspto.gov requires authentication outside
v0 scope; predicates anchored to publicly-known facts about the patent
remain valid regardless of host.

## Provenance

Captured 2026-04-27 from `https://patents.google.com/patent/US6285999/en`
(1.81 MB HTML). The page exposes ~38 structured `<meta>` tags including
`citation_patent_number`, `citation_patent_application_number`,
`citation_pdf_url`, `DC.title`, `DC.contributor` (multi),
`DC.date` (multi: filing then grant), `DC.relation` (citing patents),
and `citation_reference` (academic literature).

## What the captured patent contains (verified at capture-time)

| Field | Value | Predicate |
|---|---|---|
| Patent number | 6,285,999 | `in_set ["6285999"]` |
| Country | US | `in_set ["US"]` |
| Raw citation | US:6285999 | `in_set` (compound format) |
| Application number | 09/004,827 | `regex ^[0-9]{2}/[0-9]{3},[0-9]{3}$` |
| Filing date | 1998-01-09 | `in_set ["1998-01-09"]` |
| Grant date | 2001-09-04 | `in_set ["2001-09-04"]` |
| Title | "Method for node ranking in a linked database" | min_length 20, contains "node ranking" + "linked database" |
| Abstract | ~700 chars | `min_length 200` |
| PDF URL | https://patentimages.storage.googleapis.com/.../US6285999.pdf | regex Google's patentimages bucket |
| Contributors | ["Lawrence Page", "Leland Stanford Junior University"] | inventor + assignee in_contributors |
| n_relations (citing patents) | 7 | `in_range [1, 1000]` |
| n_references (academic) | 20 | `in_range [1, 1000]` |

## External-source citations (predicate provenance)

| Predicate group | Source |
|---|---|
| Patent number 6,285,999 | **USPTO Patent Full-Text Database** + widely cited in patent-search literature; the patent expired 2018 (publicly-listed expiry per Stanford's Office of Technology Licensing) |
| Application number 09/004,827 (filing 1998-01-09) | **USPTO USPTO standard application-number format**: `<series-code>/<sequence>` where `09` = 1995-1998 series, `004,827` = sequence within that series |
| Inventor Lawrence Page | **Public record**: Page is the named inventor on the patent's title page; widely documented in Google's S-1 filing (2004) and Stanford's PhD-thesis archives |
| Assignee Leland Stanford Junior University | **Stanford Office of Technology Licensing**: the patent was assigned to Stanford as an employee invention during Page's PhD; Stanford licensed it to Google |
| Filing 1998-01-09 / Grant 2001-09-04 | **USPTO public record** — dates have appeared in dozens of patent-law articles + Stanford OTL filings |
| Title "Method for node ranking in a linked database" | **USPTO official title** — exact title is in the patent's preamble |
| US application format `^[0-9]{2}/[0-9]{3},[0-9]{3}$` | **USPTO MPEP §503** — application serial number format |
| Google Patents PDF URL pattern (patentimages.storage.googleapis.com) | **Google Patents indexing convention** — public CDN URL for patent PDFs |

## Spoof matrix

| Mutation | Predicate that fails |
|---|---|
| `_provenance.json` `target_inventor` → "Bill Gates" | `target.inventor in_set ["Lawrence Page"]` fails first |
| `_provenance.json` `target_patent_number` → "1234567" | `target.patent_number in_set ["6285999"]` fails |
| `_provenance.json` `target_grant_date` → "1999-01-01" | `target.grant_date in_set ["2001-09-04"]` fails |
| Replace `patent.html` with a different patent's HTML | `patent.patent_number in_set ["6285999"]` fails for_all (data-driven check) |
| Truncate `patent.html` to 0 bytes | `files[*].size_bytes in_range [10000, ...]` fails; identity extractions return empty strings, all match-target booleans become false |

## Why PageRank / US 6,285,999

- **Most-documented patent in the public domain.** Hundreds of
  academic papers + textbooks cite Page's PageRank patent.
- **Stable identity.** Patent number is fixed; expired in 2018 so no
  ongoing modifications.
- **Distinctive title.** "Method for node ranking in a linked database"
  is unambiguous — no other public patent uses these exact words.
- **Single inventor / single assignee** — clean predicate template;
  case_002 with multiple inventors will introduce list-semantic
  predicates.
