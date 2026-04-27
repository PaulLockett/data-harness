"""uspto — read a captured Google Patents HTML, build validated record.

Contract: run(inputs_dir: Path) -> dict.

Inputs (capture-time):
    inputs_dir/_provenance.json   target spec + capture metadata
    inputs_dir/patent.html         full Google Patents HTML mirror of the
                                    USPTO patent record

Output: a canonical Patent record extracted from the HTML's structured
<meta> tags, validated against externally-known facts about the target
patent.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


# Citation meta-tag names exposed by Google Patents (consistent across
# the corpus per Google Patents documentation)
CITATION_FIELDS = [
    "citation_patent_number", "citation_publication_date",
    "citation_filing_date", "citation_application_number",
    "citation_pdf_url", "citation_inventor", "citation_assignee",
    "citation_title", "citation_abstract", "citation_classifications",
]


def _meta_all(html: str, name: str) -> list[str]:
    """Find all <meta name='<name>' content='...'> values."""
    pat = re.compile(
        rf'<meta\s+(?:[^>]*\s)?name="{re.escape(name)}"\s+content="([^"]*)"',
        re.IGNORECASE,
    )
    return [m.group(1) for m in pat.finditer(html)]


def _meta_one(html: str, name: str) -> str:
    vs = _meta_all(html, name)
    return vs[0] if vs else ""


def _decode_html_entities(s: str) -> str:
    import html as _h
    return _h.unescape(s)


def run(inputs_dir: Path) -> dict:
    inputs_dir = Path(inputs_dir)
    prov = json.loads((inputs_dir / "_provenance.json").read_text())

    target_pn = str(prov["target_patent_number"])
    target_cc = str(prov.get("target_country_code", "US"))
    target_app = str(prov.get("target_application_number", ""))
    target_filing = str(prov.get("target_filing_date", ""))
    target_grant = str(prov.get("target_grant_date", ""))
    target_inventor = str(prov.get("target_inventor", ""))
    target_assignee = str(prov.get("target_assignee", ""))
    target_title_keywords = list(prov.get("target_title_keywords", []))

    html_path = inputs_dir / "patent.html"
    raw = html_path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()[:16]
    text = raw.decode("utf-8", errors="replace")

    # Extract structured metadata. Google Patents tag conventions:
    # - citation_patent_number = "<COUNTRY>:<NUMBER>" (e.g. "US:6285999")
    # - citation_patent_application_number = same format
    # - citation_pdf_url = link to PDF on patentimages.storage.googleapis.com
    # - DC.title = patent title
    # - description = patent abstract
    # - DC.contributor (multi) = inventors + assignees combined (no separation
    #   in the raw HTML; the page's renderer reads further structured data
    #   from JS context). For predicate purposes, the union list is what we
    #   validate against — both `target_inventor` AND `target_assignee` must
    #   appear in `contributors`.
    # - DC.date appears TWICE: first = filing_date, second = publication/grant_date
    # - DC.relation (multi) = patents that cite or are cited by this one
    # - citation_reference (multi) = academic literature references
    citation_pn_raw = _meta_one(text, "citation_patent_number")  # "US:6285999"
    app_no_raw = _meta_one(text, "citation_patent_application_number")
    pdf_url = _meta_one(text, "citation_pdf_url")
    title = _decode_html_entities(_meta_one(text, "DC.title"))
    abstract = _decode_html_entities(_meta_one(text, "description"))
    contributors = [_decode_html_entities(v) for v in _meta_all(text, "DC.contributor")]
    dc_dates = _meta_all(text, "DC.date")
    filing_date = dc_dates[0] if len(dc_dates) >= 1 else ""
    pub_date = dc_dates[1] if len(dc_dates) >= 2 else dc_dates[0] if dc_dates else ""
    relations = _meta_all(text, "DC.relation")          # related patent numbers
    references = _meta_all(text, "citation_reference")  # academic references
    citing = _meta_all(text, "citation_cites")

    # Parse citation_patent_number "US:6285999" → country + number
    country_code = ""
    patent_number = ""
    if ":" in citation_pn_raw:
        country_code, patent_number = citation_pn_raw.split(":", 1)
    else:
        patent_number = citation_pn_raw

    # Parse citation_application_number "US:09/004,827"
    app_country = ""
    app_number = ""
    if ":" in app_no_raw:
        app_country, app_number = app_no_raw.split(":", 1)
    else:
        app_number = app_no_raw

    # External-fact validation
    patent_number_matches_target = patent_number == target_pn
    country_code_matches_target = country_code == target_cc
    application_number_matches_target = (
        target_app == "" or app_number == target_app
    )
    filing_date_matches_target = (
        target_filing == "" or filing_date == target_filing
    )
    grant_date_matches_target = (
        target_grant == "" or pub_date == target_grant
    )
    target_inventor_in_contributors = (
        target_inventor == "" or
        any(target_inventor.lower() in (c or "").lower() for c in contributors)
    )
    target_assignee_in_contributors = (
        target_assignee == "" or
        any(target_assignee.lower() in (c or "").lower() for c in contributors)
    )
    title_contains_keywords = (
        not target_title_keywords or
        all(kw.lower() in (title or "").lower() for kw in target_title_keywords)
    )

    all_validated = bool(
        patent_number_matches_target and country_code_matches_target
        and application_number_matches_target
        and filing_date_matches_target and grant_date_matches_target
        and target_inventor_in_contributors and target_assignee_in_contributors
        and title_contains_keywords
    )

    return {
        "target": {
            "patent_number":      target_pn,
            "country_code":       target_cc,
            "application_number": target_app,
            "filing_date":        target_filing,
            "grant_date":         target_grant,
            "inventor":           target_inventor,
            "assignee":           target_assignee,
            "title_keywords":     target_title_keywords,
        },
        "patent": {
            "patent_number":       patent_number,
            "country_code":        country_code,
            "raw_citation":        citation_pn_raw,
            "application_number":  app_number,
            "application_country": app_country,
            "filing_date":         filing_date,
            "grant_date":          pub_date,
            "title":               title,
            "abstract":            abstract,
            "pdf_url":             pdf_url,
            "n_contributors":      len(contributors),
            "contributors":        contributors,
            "n_relations":         len(relations),
            "n_references":        len(references),
            "n_citing":            len(citing),
        },
        "files": [{
            "file_path":     "patent.html",
            "size_bytes":    len(raw),
            "sha256_prefix": sha,
            "format":        "html",
        }],
        "captured_from":   prov.get("captured_from", ""),
        "captured_at_utc": prov.get("captured_at_utc", ""),
        "capture_method":  prov.get("capture_method", ""),
        "validation": {
            "all_validated":                     all_validated,
            "patent_number_matches_target":      patent_number_matches_target,
            "country_code_matches_target":       country_code_matches_target,
            "application_number_matches_target": application_number_matches_target,
            "filing_date_matches_target":        filing_date_matches_target,
            "grant_date_matches_target":         grant_date_matches_target,
            "target_inventor_in_contributors":   target_inventor_in_contributors,
            "target_assignee_in_contributors":   target_assignee_in_contributors,
            "title_contains_keywords":           title_contains_keywords,
            "n_files":                           1,
            "target_identifiers": [
                f"US:{target_pn}", target_inventor, target_assignee,
                target_app, target_filing, target_grant,
            ],
        },
    }
