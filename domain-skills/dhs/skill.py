"""dhs — read captured DHS Program API JSONs, build validated record.

Contract: run(inputs_dir: Path) -> dict.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


def _file_meta(p: Path) -> dict:
    raw = p.read_bytes()
    return {
        "file_path":     p.name,
        "size_bytes":    len(raw),
        "sha256_prefix": hashlib.sha256(raw).hexdigest()[:16],
        "format":        "json",
    }


def run(inputs_dir: Path) -> dict:
    inputs_dir = Path(inputs_dir)
    prov = json.loads((inputs_dir / "_provenance.json").read_text())

    target_dhs_cc = str(prov["target_dhs_country_code"])
    target_iso2 = str(prov["target_iso2_country_code"])
    target_iso3 = str(prov["target_iso3_country_code"])
    target_name = str(prov["target_country_name"])
    target_indicator = str(prov["target_indicator_id"])
    target_ind_substr = str(prov["target_indicator_name_substring"])
    target_first_survey_id = str(prov["target_first_survey_id"])
    target_first_year = int(prov["target_first_survey_year"])
    target_first_tfr = float(prov["target_first_survey_tfr"])
    target_org = str(prov.get("target_implementing_org", ""))
    target_min_n_surveys = int(prov.get("target_min_n_surveys", 1))

    indicator_data = json.loads((inputs_dir / "indicator_data.json").read_text())
    country = json.loads((inputs_dir / "country.json").read_text())
    surveys = json.loads((inputs_dir / "surveys.json").read_text())
    indicator_meta = json.loads((inputs_dir / "indicator_meta.json").read_text())

    data_records = indicator_data.get("Data", [])
    country_records = country.get("Data", [])
    survey_records = surveys.get("Data", [])
    indicator_records = indicator_meta.get("Data", [])

    # Country identity
    country_rec = country_records[0] if country_records else {}
    captured_dhs_cc = country_rec.get("DHS_CountryCode", "")
    captured_iso2 = country_rec.get("ISO2_CountryCode", "")
    captured_iso3 = country_rec.get("ISO3_CountryCode", "")
    captured_name = country_rec.get("CountryName", "")

    # Indicator identity
    indicator_rec = indicator_records[0] if indicator_records else {}
    captured_indicator_id = indicator_rec.get("IndicatorId", "")
    captured_indicator_label = indicator_rec.get("Label", "")
    captured_indicator_definition = indicator_rec.get("Definition", "")
    captured_measurement_type = indicator_rec.get("MeasurementType", "")

    # Surveys — find the first Kenya DHS
    first_survey_id = ""
    first_survey_year = None
    first_survey_org = ""
    for s in survey_records:
        sid = s.get("SurveyId", "")
        if sid == target_first_survey_id:
            first_survey_id = sid
            first_survey_year = int(s.get("SurveyYear", 0)) if s.get("SurveyYear") else None
            first_survey_org = s.get("ImplementingOrg", "")
            break

    # First-survey TFR — find indicator-data record where SurveyId matches target
    first_survey_tfr_value = None
    for d in data_records:
        if d.get("SurveyId") == target_first_survey_id and d.get("CharacteristicCategory") == "Total":
            first_survey_tfr_value = float(d.get("Value")) if d.get("Value") is not None else None
            break

    # External validation flags
    dhs_cc_matches = captured_dhs_cc == target_dhs_cc
    iso2_matches = captured_iso2 == target_iso2
    iso3_matches = captured_iso3 == target_iso3
    name_matches = captured_name == target_name
    indicator_id_matches = captured_indicator_id == target_indicator
    indicator_label_contains_target = (
        target_ind_substr.lower() in (captured_indicator_label or "").lower()
    )
    n_surveys = len(survey_records)
    n_surveys_meets_min = n_surveys >= target_min_n_surveys
    first_survey_present = first_survey_id == target_first_survey_id
    first_survey_year_matches = first_survey_year == target_first_year
    first_survey_org_matches = (
        target_org == "" or target_org in (first_survey_org or "")
    )
    first_survey_tfr_matches = (
        first_survey_tfr_value is not None
        and abs(first_survey_tfr_value - target_first_tfr) < 0.05
    )

    all_validated = bool(
        dhs_cc_matches and iso2_matches and iso3_matches and name_matches
        and indicator_id_matches and indicator_label_contains_target
        and n_surveys_meets_min and first_survey_present
        and first_survey_year_matches and first_survey_org_matches
        and first_survey_tfr_matches
    )

    files = [_file_meta(inputs_dir / f) for f in
             ("indicator_data.json", "country.json", "surveys.json", "indicator_meta.json")]

    return {
        "target": {
            "dhs_country_code":     target_dhs_cc,
            "iso2_country_code":    target_iso2,
            "iso3_country_code":    target_iso3,
            "country_name":         target_name,
            "indicator_id":         target_indicator,
            "first_survey_id":      target_first_survey_id,
            "first_survey_year":    target_first_year,
            "first_survey_tfr":     target_first_tfr,
        },
        "country": {
            "dhs_country_code":     captured_dhs_cc,
            "iso2_country_code":    captured_iso2,
            "iso3_country_code":    captured_iso3,
            "country_name":         captured_name,
            "subregion":            country_rec.get("SubregionName", ""),
            "region":               country_rec.get("RegionName", ""),
        },
        "indicator": {
            "indicator_id":      captured_indicator_id,
            "label":             captured_indicator_label,
            "measurement_type":  captured_measurement_type,
            "definition":        (captured_indicator_definition or "")[:300],
        },
        "surveys_summary": {
            "n_surveys":            n_surveys,
            "first_survey_id":      first_survey_id,
            "first_survey_year":    first_survey_year,
            "first_survey_org":     first_survey_org,
        },
        "first_survey_tfr": {
            "survey_id":  target_first_survey_id,
            "value":      first_survey_tfr_value,
        },
        "files":       files,
        "captured_from":   prov.get("captured_from", ""),
        "captured_at_utc": prov.get("captured_at_utc", ""),
        "capture_method":  prov.get("capture_method", ""),
        "validation": {
            "all_validated":                  all_validated,
            "dhs_cc_matches":                 dhs_cc_matches,
            "iso2_matches":                   iso2_matches,
            "iso3_matches":                   iso3_matches,
            "name_matches":                   name_matches,
            "indicator_id_matches":           indicator_id_matches,
            "indicator_label_contains_target": indicator_label_contains_target,
            "n_surveys_meets_min":            n_surveys_meets_min,
            "first_survey_present":           first_survey_present,
            "first_survey_year_matches":      first_survey_year_matches,
            "first_survey_org_matches":       first_survey_org_matches,
            "first_survey_tfr_matches":       first_survey_tfr_matches,
            "n_files":                        len(files),
            "target_identifiers": [
                target_dhs_cc, target_iso3, target_name, target_indicator,
                target_first_survey_id, str(target_first_year),
            ],
        },
    }
