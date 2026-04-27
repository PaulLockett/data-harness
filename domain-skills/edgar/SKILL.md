# edgar — SEC EDGAR filing records

## What it does

Reads captured SEC EDGAR submissions JSON + filing-index JSON for one
public company's specific filing, emits a canonical EDGAR-Filing record,
validates company identity (CIK / EIN / SIC / ticker / exchange / state)
and filing metadata (accession number format, filing form, filing date,
primary document) against externally-citable SEC and IRS public records.

## Capture flow

1. **Pick a company by CIK.** SEC assigns each filer a 10-digit CIK
   (Central Index Key). For Apple, CIK 0000320193. CIKs are stable
   forever.
2. **GET company submissions.**
   `https://data.sec.gov/submissions/CIK<10digit>.json` returns 100-200 KB
   of company metadata + the 1000 most recent filings (form, date,
   accession, primary document).
3. **Pick a target filing.** Walk `filings.recent.form` to find the
   accession number for the desired form (10-K, 10-Q, 8-K, S-1, etc.).
4. **GET filing index.**
   `https://www.sec.gov/Archives/edgar/data/<CIK_int>/<accession_no_dashes>/index.json`
   returns a directory listing of all documents in the filing (XBRL ZIP,
   primary HTML, exhibits).
5. **Persist both JSONs verbatim** as `inputs/submissions.json` and
   `inputs/filing_index.json`. SEC requires a real User-Agent header per
   www.sec.gov/os/accessing-edgar-data.

## Inputs

- `_provenance.json` — declares CIK, name, ticker, exchange, SIC, state,
  EIN, target filing form/accession/date/primary_document
- `submissions.json` — data.sec.gov submissions response
- `filing_index.json` — sec.gov/Archives/.../index.json directory listing

## Output (skill.py contract)

`run(inputs_dir: Path) -> dict` returns target / company / filings_summary
/ target_filing / files / validation rollup with 14 sub-flags.

## Predicates (case_001) — 56 total

| Group | Source |
|---|---|
| **Identity** (10): CIK, name, ticker, exchange, SIC, state, EIN, form, accession, date in_set | **External** — all are publicly-citable: SEC CIK 0000320193 = Apple Inc. (stable forever); IRS EIN 942404110 (Apple's tax ID, public per FOIA + 10-K filings); SIC 3571 = Electronic Computers (BLS classification); state CA (Apple incorporated in California per California SOS records) |
| **Company from data** (12): CIK regex `^[0-9]{10}$`, EIN regex `^[0-9]{9}$`, ticker_in_tickers, exchange_in_exchanges (NASDAQ/NYSE/OTC/CBOE), SIC + description, state, entity_type enum, fiscal_year_end regex MMDD | **External**: SEC EDGAR submissions schema; SIC 1987 BLS classification; SEC fiscal-year-end MMDD format |
| **Filings summary** (4): n_recent in_range, n_recent_10k/10q/8k ranges | **External**: SEC public-filing thresholds (10-K = annual, 10-Q = quarterly, 8-K = current report) |
| **Target filing** (6): accession regex `^[0-9]{10}-[0-9]{2}-[0-9]{6}$`, accession in_set, form, date, primary doc regex | **External**: SEC EDGAR accession-number format + Apple's primary-document naming convention `aapl-YYYYMMDD.htm` |
| **Per-file shape** (5 for_all + 1) | Structural |
| **Validation rollup** (15) | Captured-data-only / belt-and-suspenders |
| **Capture URL + root keyset** (2) | **External** — data.sec.gov URL pattern |

The strong **external** predicates (~32 of 56) catch a wrong capture
even with the validation booleans removed.

## Future cases

- **case_002**: a different company (e.g. MSFT CIK 0000789019, GOOGL
  CIK 0001652044) with a different filing form (10-Q instead of 10-K).
- **case_003**: a different filing type (S-1, 8-K, DEF 14A) for the same
  company. Tests form-specific predicate adjustments.
- **case_004**: an XBRL-financial-data slice (data.sec.gov/api/xbrl/
  companyconcept/CIK<...>/us-gaap/Revenues.json). Adds numeric
  predicates over financial values.
- **case_005**: cross-domain composition with `disaggregate` —
  break revenues by reporting segment.
