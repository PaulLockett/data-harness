"""faers — read filtered FAERS adverse-event-report tables, build validated record.

Contract: run(inputs_dir: Path) -> dict.

Inputs (capture-time):
    inputs_dir/_provenance.json   target spec + capture metadata
    inputs_dir/extracted/{demo,drug,reac,outc,rpsr,ther,indi}.txt
                                  Polars-filtered subsets of the FAERS quarterly
                                  $-delimited ASCII tables, all keyed to the
                                  target primaryid

Output: a canonical AE-report record. The skill asserts the target drug
appears in DRUG with role 'PS' (primary suspect), every persisted row's
primaryid equals the target, and every file is on disk. validated == true
iff all three hold.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _read_table(path: Path) -> tuple[list[dict], list[str], int, str]:
    """Read a $-delimited FAERS ASCII file into a list of dicts. Returns (rows, header, size_bytes, sha256_prefix)."""
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()[:16]
    text = raw.decode("utf-8", errors="replace")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return [], [], len(raw), sha
    header = lines[0].split("$")
    rows = []
    for ln in lines[1:]:
        parts = ln.split("$")
        # Pad short rows to header length so dict() doesn't drop fields
        if len(parts) < len(header):
            parts = parts + [""] * (len(header) - len(parts))
        rows.append(dict(zip(header, parts)))
    return rows, header, len(raw), sha


def run(inputs_dir: Path) -> dict:
    inputs_dir = Path(inputs_dir)
    prov = json.loads((inputs_dir / "_provenance.json").read_text())
    target_drug = prov["target_drug"]
    target_pid = str(prov["target_primaryid"])
    target_caseid = str(prov.get("target_caseid", ""))
    aliases = sorted({a for a in prov.get("target_aliases", []) + [target_drug] if a})

    table_files = prov["table_files"]
    parsed: dict[str, tuple[list[dict], list[str], int, str]] = {}
    for tname, rel in table_files.items():
        parsed[tname] = _read_table(inputs_dir / rel)

    files_meta = []
    for tname, (rows, header, size_bytes, sha) in parsed.items():
        files_meta.append({
            "table": tname,
            "file_path": table_files[tname],
            "size_bytes": size_bytes,
            "sha256_prefix": sha,
            "n_rows": len(rows),
            "n_columns": len(header),
            "header": header,
        })

    demo_rows, _, _, _ = parsed["DEMO"]
    drug_rows, _, _, _ = parsed["DRUG"]
    reac_rows, _, _, _ = parsed["REAC"]
    outc_rows, _, _, _ = parsed["OUTC"]
    indi_rows, _, _, _ = parsed["INDI"]
    ther_rows, _, _, _ = parsed["THER"]
    rpsr_rows, _, _, _ = parsed["RPSR"]

    if not demo_rows:
        raise RuntimeError(f"DEMO table is empty for target primaryid {target_pid}")
    demo = demo_rows[0]

    report = {
        "primaryid": demo.get("primaryid", ""),
        "caseid": demo.get("caseid", ""),
        "case_version": demo.get("caseversion", ""),
        "patient": {
            "age": demo.get("age", ""),
            "age_cod": demo.get("age_cod", ""),
            "age_grp": demo.get("age_grp", ""),
            "sex": demo.get("sex", ""),
            "weight": demo.get("wt", ""),
            "weight_cod": demo.get("wt_cod", ""),
            "country": demo.get("occr_country", ""),
        },
        "report_meta": {
            "rept_cod": demo.get("rept_cod", ""),
            "init_fda_dt": demo.get("init_fda_dt", ""),
            "fda_dt": demo.get("fda_dt", ""),
            "mfr_sndr": demo.get("mfr_sndr", ""),
            "auth_num": demo.get("auth_num", ""),
            "mfr_num": demo.get("mfr_num", ""),
            "occp_cod": demo.get("occp_cod", ""),
            "reporter_country": demo.get("reporter_country", ""),
        },
    }

    drugs = [{
        "drug_seq":   d.get("drug_seq", ""),
        "role_cod":   d.get("role_cod", ""),
        "drugname":   d.get("drugname", ""),
        "prod_ai":    d.get("prod_ai", ""),
        "route":      d.get("route", ""),
        "dose_vbm":   d.get("dose_vbm", ""),
        "dose_amt":   d.get("dose_amt", ""),
        "dose_unit":  d.get("dose_unit", ""),
        "dose_form":  d.get("dose_form", ""),
        "dose_freq":  d.get("dose_freq", ""),
        "dechal":     d.get("dechal", ""),
        "rechal":     d.get("rechal", ""),
        "nda_num":    d.get("nda_num", ""),
    } for d in drug_rows]

    reactions = [{
        "pt":            r.get("pt", ""),
        "drug_rec_act":  r.get("drug_rec_act", ""),
    } for r in reac_rows]

    outcomes = [{"outc_cod": o.get("outc_cod", "")} for o in outc_rows]

    indications = [{
        "drug_seq": i.get("indi_drug_seq", ""),
        "indi_pt":  i.get("indi_pt", ""),
    } for i in indi_rows]

    therapy = [{
        "drug_seq":  t.get("dsg_drug_seq", ""),
        "start_dt":  t.get("start_dt", ""),
        "end_dt":    t.get("end_dt", ""),
        "dur":       t.get("dur", ""),
        "dur_cod":   t.get("dur_cod", ""),
    } for t in ther_rows]

    report_sources = [{"rpsr_cod": s.get("rpsr_cod", "")} for s in rpsr_rows]

    target_drug_in_drug_table = any(target_drug.upper() in (d["drugname"] or "").upper() for d in drugs)
    target_drug_role_is_primary_suspect = any(
        d.get("role_cod") == "PS" and target_drug.upper() in (d.get("drugname") or "").upper()
        for d in drugs
    )

    all_keyed = True
    for tname, (rows, _, _, _) in parsed.items():
        for row in rows:
            if row.get("primaryid", "") != target_pid:
                all_keyed = False
                break
        if not all_keyed:
            break

    all_validated = bool(
        target_drug_in_drug_table
        and target_drug_role_is_primary_suspect
        and all_keyed
        and report["primaryid"] == target_pid
        and (target_caseid == "" or report["caseid"] == target_caseid)
    )

    return {
        "target": {
            "drug_name":    target_drug,
            "primaryid":    target_pid,
            "caseid":       target_caseid,
            "case_version": report["case_version"],
        },
        "report":         report,
        "drugs":          drugs,
        "reactions":      reactions,
        "outcomes":       outcomes,
        "indications":    indications,
        "therapy":        therapy,
        "report_sources": report_sources,
        "files":          files_meta,
        "captured_from":   prov.get("captured_from", ""),
        "captured_at_utc": prov.get("captured_at_utc", ""),
        "capture_method":  prov.get("capture_method", ""),
        "validation": {
            "all_validated":                       all_validated,
            "target_drug_in_drug_table":           target_drug_in_drug_table,
            "target_drug_role_is_primary_suspect": target_drug_role_is_primary_suspect,
            "all_files_keyed_by_target_primaryid": all_keyed,
            "n_files":                             len(files_meta),
            "n_drugs":                             len(drugs),
            "n_reactions":                         len(reactions),
            "n_outcomes":                          len(outcomes),
            "target_identifiers":                  aliases + [target_pid, target_caseid],
        },
    }
