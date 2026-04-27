"""usaspending — read a captured award-detail JSON, build validated record.

Contract: run(inputs_dir: Path) -> dict.

Inputs (capture-time):
    inputs_dir/_provenance.json   target spec + capture metadata
    inputs_dir/award.json          full award-detail JSON from
                                   api.usaspending.gov/api/v2/awards/<id>/

Output: a canonical Award record with target identity, captured award fields,
recipient + awarding-agency identity, and a validation rollup that asserts
the captured generated_unique_award_id, piid, recipient name + UEI, and
awarding agency all match externally-known values.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


def _native(x):
    if x is None or isinstance(x, (str, int, float, bool)):
        return x
    return str(x)


def _read_json(path: Path) -> tuple[dict, int, str]:
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8")), len(raw), hashlib.sha256(raw).hexdigest()[:16]


def run(inputs_dir: Path) -> dict:
    inputs_dir = Path(inputs_dir)
    prov = json.loads((inputs_dir / "_provenance.json").read_text())

    target_award_id = prov["target_generated_unique_award_id"]
    target_piid = prov.get("target_piid", "")
    target_recipient_search = prov.get("target_recipient_search", "")
    target_recipient_name = prov.get("target_recipient_name", "")
    target_recipient_uei = prov.get("target_recipient_uei", "")
    target_aliases = list({a for a in prov.get("target_aliases", []) + [target_recipient_name] if a})

    award_path = inputs_dir / "award.json"
    award, size_bytes, sha = _read_json(award_path)

    awarding = award.get("awarding_agency") or {}
    toptier = (awarding.get("toptier_agency") or {})
    subtier = (awarding.get("subtier_agency") or {})
    recipient = award.get("recipient") or {}
    pop = award.get("place_of_performance") or {}
    period = award.get("period_of_performance") or {}

    captured_award_id = _native(award.get("generated_unique_award_id"))
    captured_piid = _native(award.get("piid", ""))
    captured_recipient_name = _native(recipient.get("recipient_name", ""))
    captured_recipient_uei = _native(recipient.get("recipient_uei", ""))
    captured_toptier_name = _native(toptier.get("name", ""))
    captured_subtier_name = _native(subtier.get("name", ""))
    description = _native(award.get("description", "")) or ""

    award_id_match = captured_award_id == target_award_id
    piid_match = (target_piid == "") or (captured_piid == target_piid)
    recipient_name_contains_target = bool(
        target_recipient_search
        and target_recipient_search.upper() in (captured_recipient_name or "").upper()
    )
    recipient_uei_match = (
        (target_recipient_uei == "") or (captured_recipient_uei == target_recipient_uei)
    )
    # Externally-documented invariant: NASA's toptier agency name in
    # USAspending is "National Aeronautics and Space Administration" (per
    # USAspending's agency reference table). For non-NASA targets this
    # check would naturally be re-tightened in case_002+.
    awarding_toptier_is_nasa = "Aeronautics and Space" in (captured_toptier_name or "")

    # Externally-documented invariant: HLS contract scope publicly described
    # as "Human Landing System" / "HLS" / "Integrated Lander" in NASA's
    # 2021-04-16 announcement and in subsequent GAO reports. Description
    # field on USAspending mirrors the contract PWS scope statement.
    desc_upper = description.upper()
    description_mentions_hls = any(
        term in desc_upper for term in ("HUMAN LANDING SYSTEM", "HLS", "LANDER")
    )

    # USAspending data-dictionary invariant: top-level award-detail keys
    # always include id, generated_unique_award_id, type, recipient,
    # awarding_agency, period_of_performance, total_obligation, etc.
    REQUIRED_TOP_KEYS = {
        "id", "generated_unique_award_id", "category", "type",
        "type_description", "total_obligation", "date_signed",
        "period_of_performance", "recipient", "awarding_agency",
        "place_of_performance", "description",
    }
    captured_top_keys = set(award.keys())
    missing_top_keys = sorted(REQUIRED_TOP_KEYS - captured_top_keys)
    top_keys_match_api_spec = not missing_top_keys

    all_validated = bool(
        award_id_match and piid_match
        and recipient_name_contains_target and recipient_uei_match
        and awarding_toptier_is_nasa and description_mentions_hls
        and top_keys_match_api_spec
    )

    return {
        "target": {
            "generated_unique_award_id": target_award_id,
            "piid":                       target_piid,
            "recipient_search":           target_recipient_search,
            "recipient_uei":              target_recipient_uei,
        },
        "award": {
            "id":                          _native(award.get("id")),
            "generated_unique_award_id":   captured_award_id,
            "piid":                        captured_piid,
            "category":                    _native(award.get("category", "")),
            "type":                        _native(award.get("type", "")),
            "type_description":            _native(award.get("type_description", "")),
            "total_obligation":            _native(award.get("total_obligation")),
            "total_outlay":                _native(award.get("total_outlay")),
            "base_and_all_options_value":  _native(award.get("base_and_all_options_value")),
            "date_signed":                 _native(award.get("date_signed", "")),
            "subaward_count":              _native(award.get("subaward_count")),
            "total_subaward_amount":       _native(award.get("total_subaward_amount")),
            "description":                 description,
            "period_of_performance": {
                "start_date":              _native(period.get("start_date", "")),
                "end_date":                _native(period.get("end_date", "")),
                "potential_end_date":      _native(period.get("potential_end_date", "")),
                "last_modified_date":      _native(period.get("last_modified_date", "")),
            },
        },
        "recipient": {
            "recipient_name":         captured_recipient_name,
            "recipient_uei":          captured_recipient_uei,
            "recipient_unique_id":    _native(recipient.get("recipient_unique_id", "")),
            "parent_recipient_name":  _native(recipient.get("parent_recipient_name", "")),
            "parent_recipient_uei":   _native(recipient.get("parent_recipient_uei", "")),
        },
        "awarding_agency": {
            "toptier_name": captured_toptier_name,
            "subtier_name": captured_subtier_name,
        },
        "place_of_performance": {
            "city":       _native(pop.get("city_name", "")),
            "state_code": _native(pop.get("state_code", "")),
            "state_name": _native(pop.get("state_name", "")),
            "country_code": _native(pop.get("country_code", "")),
        },
        "files": [{
            "file_path":     "award.json",
            "size_bytes":    size_bytes,
            "sha256_prefix": sha,
            "format":        "json",
        }],
        "captured_from":   prov.get("captured_from", ""),
        "captured_at_utc": prov.get("captured_at_utc", ""),
        "capture_method":  prov.get("capture_method", ""),
        "validation": {
            "all_validated":                  all_validated,
            "award_id_match":                 award_id_match,
            "piid_match":                     piid_match,
            "recipient_name_contains_target": recipient_name_contains_target,
            "recipient_uei_match":            recipient_uei_match,
            "awarding_toptier_is_nasa":       awarding_toptier_is_nasa,
            "description_mentions_hls":       description_mentions_hls,
            "top_keys_match_api_spec":        top_keys_match_api_spec,
            "missing_top_keys":               missing_top_keys,
            "n_files":                        1,
            "target_identifiers": sorted(
                set(target_aliases + [target_award_id, target_piid, target_recipient_uei])
                - {""}
            ),
        },
    }
