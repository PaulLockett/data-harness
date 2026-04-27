# case_001 — Apple Inc. FY2025 10-K (CIK 0000320193, accession 0000320193-25-000079)

## What this case demonstrates

Apple Inc.'s annual 10-K filing for fiscal year 2025 (ending 2025-09-27,
filed 2025-10-31), captured from SEC EDGAR's no-auth public APIs. Pure
JSON path. Every load-bearing predicate cites a public SEC, IRS, or BLS
record.

## Provenance

Captured 2026-04-27 from
`https://data.sec.gov/submissions/CIK0000320193.json` (165 KB) and
`https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/index.json`
(9 KB). SEC's accessing-edgar-data policy requires a real User-Agent
identifying the requester; both endpoints are otherwise public no-auth.

## What the captured data contains (verified at capture-time)

| Field | Value |
|---|---|
| CIK | 0000320193 (10-digit, Apple's permanent SEC identifier) |
| Name | Apple Inc. |
| Tickers | ["AAPL"] |
| Exchanges | ["Nasdaq"] |
| SIC | 3571 — Electronic Computers (BLS 1987 classification) |
| EIN | 942404110 (IRS tax ID; SEC stores without dash) |
| State of incorporation | CA (California) |
| Entity type | "operating" |
| Fiscal year end | "0926" (Sept 26, calendar) |
| LEI | (null in current SEC data; Apple's actual LEI is HWUPKR0MPOU8FGXBT394 per gleif.org) |
| n_recent_filings | 1000 |
| n_recent_10k | 11 (Apple has 11 annual reports in the last 1000 filings) |
| n_recent_10q | 33 (quarterly reports) |
| n_recent_8k | 106 (current-event reports) |
| Target accession | 0000320193-25-000079 |
| Target form | 10-K |
| Target filing date | 2025-10-31 |
| Target primary document | aapl-20250927.htm |
| Target filing directory items | 93 (the 10-K's full document set: HTML, XBRL ZIP, exhibits) |

## External-source citations (predicate provenance)

| Predicate group | Source |
|---|---|
| CIK 0000320193 = Apple Inc. | **SEC EDGAR public record** — CIKs are permanent and queryable at https://www.sec.gov/cgi-bin/browse-edgar |
| EIN 94-2404110 | **IRS public record + Apple's own 10-K filings** (cover page) |
| Ticker AAPL on Nasdaq | **Nasdaq market data + Apple's 10-K cover page** |
| SIC 3571 = Electronic Computers | **BLS Standard Industrial Classification 1987** |
| State of incorporation CA | **California Secretary of State** + Apple's 10-K cover page |
| Accession number format `^[0-9]{10}-[0-9]{2}-[0-9]{6}$` | **SEC EDGAR accession-number specification** |
| Filing form types (10-K, 10-Q, 8-K, S-1, DEF 14A) | **SEC Forms list at sec.gov/forms** |
| Fiscal year end MMDD format | **SEC EDGAR submissions schema** |
| Primary document naming `aapl-YYYYMMDD.htm` | **Apple's filing-document naming convention** (consistent across the last 10+ years of filings) |
| Filing date 2025-10-31 + accession 0000320193-25-000079 | **SEC EDGAR public filing record** |

## Spoof matrix

| Mutation | Predicate that fails |
|---|---|
| `_provenance.json` `target_cik` → "9999999999" | `target.cik in_set ["0000320193"]` fails first |
| `_provenance.json` `target_ein` → "000000000" | `target.ein in_set ["942404110"]` fails |
| `_provenance.json` `target_filing_accession` → "1111-22-333333" | `target.filing_accession in_set` fails; `accession_format_ok` fails (wrong format) |
| Replace `submissions.json` with another company's | `cik_matches_target` cascade fails; `name_matches_target`, `ticker_in_tickers`, etc. all fail |
| Truncate `filing_index.json` to `{}` | `target_filing.n_directory_items in_range [10, 200]` fails (n=0) |
