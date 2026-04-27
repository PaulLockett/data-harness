"""edgar — read captured SEC EDGAR submissions + filing-index JSON, build validated record.

Contract: run(inputs_dir: Path) -> dict.

Inputs (capture-time):
    inputs_dir/_provenance.json   target spec + capture metadata
    inputs_dir/submissions.json    data.sec.gov/submissions/CIK<N>.json
    inputs_dir/filing_index.json   sec.gov/Archives/edgar/data/<CIK>/<accession-no-dashes>/index.json

Output: a canonical EDGAR-Filing record with company identity, recent
filings rollup, target filing's metadata + document list. Validates
CIK / EIN / SIC / ticker / exchange / accession-number format / filing
type against externally-citable SEC and IRS public records.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


def _file_meta(path: Path) -> dict:
    raw = path.read_bytes()
    return {
        "file_path":     path.name,
        "size_bytes":    len(raw),
        "sha256_prefix": hashlib.sha256(raw).hexdigest()[:16],
        "format":        "json",
    }


def run(inputs_dir: Path) -> dict:
    inputs_dir = Path(inputs_dir)
    prov = json.loads((inputs_dir / "_provenance.json").read_text())

    target_cik = str(prov["target_cik"])
    target_name = str(prov.get("target_company_name", ""))
    target_ticker = str(prov.get("target_ticker", ""))
    target_exchange = str(prov.get("target_exchange", ""))
    target_sic = str(prov.get("target_sic", ""))
    target_state = str(prov.get("target_state_of_incorporation", ""))
    target_ein = str(prov.get("target_ein", ""))
    target_form = str(prov.get("target_filing_form", ""))
    target_accession = str(prov.get("target_filing_accession", ""))
    target_date = str(prov.get("target_filing_date", ""))
    target_doc = str(prov.get("target_primary_document", ""))

    submissions = json.loads((inputs_dir / "submissions.json").read_text())
    filing_index = json.loads((inputs_dir / "filing_index.json").read_text())

    # SEC submissions schema-derived fields
    cik = str(submissions.get("cik", "")).zfill(10)
    name = submissions.get("name", "")
    tickers = list(submissions.get("tickers", []))
    exchanges = list(submissions.get("exchanges", []))
    sic = str(submissions.get("sic", ""))
    sic_description = submissions.get("sicDescription", "")
    ein = submissions.get("ein", "")
    state = submissions.get("stateOfIncorporation", "")
    state_full = submissions.get("stateOfIncorporationDescription", "")
    entity_type = submissions.get("entityType", "")
    fiscal_year_end = submissions.get("fiscalYearEnd", "")
    lei = submissions.get("lei", "")
    description = submissions.get("description", "")

    # Filings rollup: find target accession in recent filings
    recent = (submissions.get("filings") or {}).get("recent", {}) or {}
    accessions = list(recent.get("accessionNumber", []))
    forms = list(recent.get("form", []))
    dates = list(recent.get("filingDate", []))
    primary_docs = list(recent.get("primaryDocument", []))

    n_recent = len(accessions)
    n_recent_10k = sum(1 for f in forms if f == "10-K")
    n_recent_10q = sum(1 for f in forms if f == "10-Q")
    n_recent_8k = sum(1 for f in forms if f == "8-K")

    target_filing_idx = None
    for i, a in enumerate(accessions):
        if a == target_accession:
            target_filing_idx = i
            break

    if target_filing_idx is not None:
        captured_form = forms[target_filing_idx]
        captured_date = dates[target_filing_idx]
        captured_primary = primary_docs[target_filing_idx]
    else:
        captured_form = ""
        captured_date = ""
        captured_primary = ""

    # Filing-index directory
    directory = (filing_index.get("directory") or {})
    items = list(directory.get("item", []))
    item_names = [it.get("name", "") for it in items]
    n_items = len(items)
    primary_in_directory = target_doc in item_names

    # External validation flags
    cik_matches_target = cik == target_cik
    name_matches_target = target_name == "" or name == target_name
    ticker_in_tickers = target_ticker == "" or target_ticker in tickers
    exchange_in_exchanges = target_exchange == "" or target_exchange in exchanges
    sic_matches_target = target_sic == "" or sic == target_sic
    state_matches_target = target_state == "" or state == target_state
    ein_matches_target = target_ein == "" or ein == target_ein
    target_filing_present = target_filing_idx is not None
    target_form_matches = target_form == "" or captured_form == target_form
    target_date_matches = target_date == "" or captured_date == target_date
    target_primary_matches = target_doc == "" or captured_primary == target_doc

    # Accession format check: 10-digit CIK + - + 2-digit year + - + 6-digit seq
    accession_format_ok = bool(re.match(r"^\d{10}-\d{2}-\d{6}$", target_accession))

    all_validated = bool(
        cik_matches_target and name_matches_target
        and ticker_in_tickers and exchange_in_exchanges
        and sic_matches_target and state_matches_target
        and ein_matches_target and target_filing_present
        and target_form_matches and target_date_matches
        and target_primary_matches and accession_format_ok
        and primary_in_directory
    )

    files = [_file_meta(inputs_dir / f) for f in ("submissions.json", "filing_index.json")]

    return {
        "target": {
            "cik":                    target_cik,
            "company_name":           target_name,
            "ticker":                 target_ticker,
            "exchange":               target_exchange,
            "sic":                    target_sic,
            "state_of_incorporation": target_state,
            "ein":                    target_ein,
            "filing_form":            target_form,
            "filing_accession":       target_accession,
            "filing_date":            target_date,
            "primary_document":       target_doc,
        },
        "company": {
            "cik":                                cik,
            "name":                               name,
            "tickers":                            tickers,
            "exchanges":                          exchanges,
            "sic":                                sic,
            "sic_description":                    sic_description,
            "ein":                                ein,
            "state_of_incorporation":             state,
            "state_of_incorporation_description": state_full,
            "entity_type":                        entity_type,
            "fiscal_year_end":                    fiscal_year_end,
            "lei":                                lei,
        },
        "filings_summary": {
            "n_recent":      n_recent,
            "n_recent_10k":  n_recent_10k,
            "n_recent_10q":  n_recent_10q,
            "n_recent_8k":   n_recent_8k,
        },
        "target_filing": {
            "accession":         target_accession,
            "form":              captured_form,
            "date":              captured_date,
            "primary_document":  captured_primary,
            "n_directory_items": n_items,
        },
        "files": files,
        "captured_from":   prov.get("captured_from", ""),
        "captured_at_utc": prov.get("captured_at_utc", ""),
        "capture_method":  prov.get("capture_method", ""),
        "validation": {
            "all_validated":           all_validated,
            "cik_matches_target":      cik_matches_target,
            "name_matches_target":     name_matches_target,
            "ticker_in_tickers":       ticker_in_tickers,
            "exchange_in_exchanges":   exchange_in_exchanges,
            "sic_matches_target":      sic_matches_target,
            "state_matches_target":    state_matches_target,
            "ein_matches_target":      ein_matches_target,
            "target_filing_present":   target_filing_present,
            "target_form_matches":     target_form_matches,
            "target_date_matches":     target_date_matches,
            "target_primary_matches":  target_primary_matches,
            "accession_format_ok":     accession_format_ok,
            "primary_in_directory":    primary_in_directory,
            "n_files":                 len(files),
            "target_identifiers": [
                target_cik, target_name, target_ticker, target_exchange,
                target_sic, target_ein, target_accession, target_form,
            ],
        },
    }
