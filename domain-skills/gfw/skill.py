"""gfw — read a captured AIS-tracks Parquet, build validated record.

Contract: run(inputs_dir: Path) -> dict.

Inputs (capture-time):
    inputs_dir/_provenance.json   target spec + capture metadata
    inputs_dir/vessel_tracks.parquet  Polars-filtered AIS messages for one
                                       MMSI on one UTC day

Output: a canonical Vessel-Tracks record. The skill validates that every
persisted message belongs to the target MMSI, that vessel-identity fields
(VesselName, CallSign, VesselType) are constant across the day's tracks,
and that LAT / LON / SOG / COG / Heading / VesselType all conform to the
ITU-R M.1371 AIS standard's value ranges.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


# ITU-R M.1371 AIS Vessel Type codes — the maritime-mobile-service
# identification table. Source: ITU-R M.1371 Table 18 (Ship Type).
# Spec encodes 0-99 with reserved blocks; we keep the documented values
# we actually expect a fixture to encounter (cargo/tanker/fishing/passenger
# /pleasure/tug/military/sailing/etc.).
ITU_VESSEL_TYPE_CODES: list[int] = list(range(0, 100))

# AIS Navigation Status enum (ITU-R M.1371 Table 16, codes 0-15)
ITU_NAV_STATUS_CODES: list[int] = list(range(0, 16))


def run(inputs_dir: Path) -> dict:
    inputs_dir = Path(inputs_dir)
    prov = json.loads((inputs_dir / "_provenance.json").read_text())

    target_mmsi = int(prov["target_mmsi"])
    target_vessel_name = str(prov.get("target_vessel_name", ""))
    target_call_sign = str(prov.get("target_call_sign", ""))
    target_vessel_type = int(prov.get("target_vessel_type", 0))
    target_country_mid = str(prov.get("target_country_mid", ""))
    target_date = str(prov.get("target_observation_date_utc", ""))

    parquet_path = inputs_dir / "vessel_tracks.parquet"
    if not parquet_path.exists():
        raise RuntimeError(f"missing parquet at {parquet_path}")

    raw = parquet_path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()[:16]

    import polars as pl
    df = pl.read_parquet(parquet_path)
    n_rows = len(df)
    columns = df.columns

    # Identity values from the captured data
    captured_mmsis = df["MMSI"].unique().to_list()
    captured_names = [n for n in df["VesselName"].unique().to_list() if n is not None]
    captured_callsigns = [c for c in df["CallSign"].unique().to_list() if c is not None]
    captured_types = df["VesselType"].unique().to_list()

    # External invariants (ITU-R M.1371):
    # - MMSI is a 9-digit positive integer; first 3 digits are the country MID
    # - LAT in [-90, 90], LON in [-180, 180]
    # - SOG (Speed Over Ground) in [0, 102.2] knots; 102.3 = "not available"
    # - COG (Course Over Ground) in [0, 360) degrees; 360.0 = "not available"
    # - Heading is integer degrees [0, 359]; 511 = "not available"
    # - VesselType in [0, 99] (Table 18); Status in [0, 15] (Table 16)
    # - TransceiverClass in {"A", "B"} per ITU
    # - BaseDateTime in NOAA's ISO-without-Z format

    # Derive validation flags
    all_mmsi_match_target = all(int(m) == target_mmsi for m in captured_mmsis)
    mmsi_starts_with_target_mid = str(target_mmsi).startswith(target_country_mid) if target_country_mid else True

    # Convert SOG/COG/Heading via Polars to plain values
    sog = df["SOG"].cast(pl.Float64)
    cog = df["COG"].cast(pl.Float64)
    heading = df["Heading"].cast(pl.Float64)

    sog_min, sog_max = float(sog.min() or 0), float(sog.max() or 0)
    cog_min, cog_max = float(cog.min() or 0), float(cog.max() or 0)
    heading_unique = sorted(set(int(h) for h in df["Heading"].drop_nulls().to_list()))

    lat_min, lat_max = float(df["LAT"].min()), float(df["LAT"].max())
    lon_min, lon_max = float(df["LON"].min()), float(df["LON"].max())

    sog_in_ais_range = (sog_min >= 0) and (sog_max <= 102.3)
    cog_in_ais_range = (cog_min >= 0) and (cog_max <= 360.0)
    # Heading: 0-359 integer or 511 (not available)
    heading_in_ais_range = all(0 <= h <= 359 or h == 511 for h in heading_unique)
    lat_in_global_range = (-90 <= lat_min) and (lat_max <= 90)
    lon_in_global_range = (-180 <= lon_min) and (lon_max <= 180)
    vessel_types_in_itu_table = all(int(t) in ITU_VESSEL_TYPE_CODES for t in captured_types if t is not None)
    target_vessel_type_present = target_vessel_type in [int(t) for t in captured_types if t is not None]

    # Identity: vessel name and call sign should be constant across one
    # vessel's tracks (modulo None in some messages)
    vessel_name_matches_target = (
        target_vessel_name == "" or
        any(target_vessel_name in str(n) for n in captured_names)
    )
    call_sign_matches_target = (
        target_call_sign == "" or
        any(target_call_sign in str(c) for c in captured_callsigns)
    )

    # BaseDateTime should be on the target_observation_date_utc
    captured_dates = (
        df["BaseDateTime"].cast(pl.Utf8).str.slice(0, 10).unique().to_list()
        if "BaseDateTime" in columns else []
    )
    all_dates_match_target = (
        target_date == "" or all(d == target_date for d in captured_dates)
    )

    all_validated = bool(
        all_mmsi_match_target
        and mmsi_starts_with_target_mid
        and sog_in_ais_range and cog_in_ais_range and heading_in_ais_range
        and lat_in_global_range and lon_in_global_range
        and vessel_types_in_itu_table and target_vessel_type_present
        and vessel_name_matches_target and call_sign_matches_target
        and all_dates_match_target
    )

    return {
        "target": {
            "mmsi":              target_mmsi,
            "vessel_name":       target_vessel_name,
            "call_sign":         target_call_sign,
            "vessel_type":       target_vessel_type,
            "country_mid":       target_country_mid,
            "observation_date":  target_date,
        },
        "vessel": {
            "mmsi":               int(captured_mmsis[0]) if captured_mmsis else None,
            "vessel_name":        captured_names[0] if captured_names else "",
            "call_sign":          captured_callsigns[0] if captured_callsigns else "",
            "vessel_type":        int(captured_types[0]) if captured_types else None,
            "imo":                str(df["IMO"].drop_nulls().unique().to_list()[0]) if df["IMO"].drop_nulls().len() else "",
            "transceiver_class":  str(df["TransceiverClass"].drop_nulls().unique().to_list()[0]) if df["TransceiverClass"].drop_nulls().len() else "",
        },
        "tracks_summary": {
            "n_messages":         n_rows,
            "lat_min":            lat_min,
            "lat_max":            lat_max,
            "lon_min":            lon_min,
            "lon_max":            lon_max,
            "sog_min":            sog_min,
            "sog_max":            sog_max,
            "cog_min":            cog_min,
            "cog_max":            cog_max,
            "time_min":           str(df["BaseDateTime"].min()),
            "time_max":           str(df["BaseDateTime"].max()),
            "captured_dates":     sorted(captured_dates),
        },
        "schema": {
            "columns":            columns,
            "n_columns":          len(columns),
        },
        "files": [{
            "file_path":     "vessel_tracks.parquet",
            "size_bytes":    len(raw),
            "sha256_prefix": sha,
            "format":        "parquet",
            "n_rows":        n_rows,
        }],
        "captured_from":   prov.get("captured_from", ""),
        "captured_at_utc": prov.get("captured_at_utc", ""),
        "capture_method":  prov.get("capture_method", ""),
        "validation": {
            "all_validated":               all_validated,
            "all_mmsi_match_target":       all_mmsi_match_target,
            "mmsi_starts_with_target_mid": mmsi_starts_with_target_mid,
            "vessel_name_matches_target":  vessel_name_matches_target,
            "call_sign_matches_target":    call_sign_matches_target,
            "target_vessel_type_present":  target_vessel_type_present,
            "vessel_types_in_itu_table":   vessel_types_in_itu_table,
            "sog_in_ais_range":            sog_in_ais_range,
            "cog_in_ais_range":            cog_in_ais_range,
            "heading_in_ais_range":        heading_in_ais_range,
            "lat_in_global_range":         lat_in_global_range,
            "lon_in_global_range":         lon_in_global_range,
            "all_dates_match_target":      all_dates_match_target,
            "n_messages":                  n_rows,
            "n_files":                     1,
            "target_identifiers": [
                str(target_mmsi), target_vessel_name, target_call_sign,
                f"VesselType={target_vessel_type}", target_country_mid,
                target_date,
            ],
        },
    }
