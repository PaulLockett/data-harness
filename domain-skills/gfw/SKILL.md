# gfw — vessel-tracking AIS data (fishing-effort domain)

## What it does

Reads a Polars-filtered Parquet of AIS (Automatic Identification System)
messages for one vessel on one UTC day and emits a canonical
Vessel-Tracks record. The skill validates that every persisted message
belongs to the target MMSI, that the captured vessel-identity fields
match the search target, and that LAT/LON/SOG/COG/Heading/VesselType all
conform to the ITU-R M.1371 AIS standard's documented value ranges.

## Data source

Global Fishing Watch (GFW) is the named domain in the spec, but their
gateway API requires authentication that's outside v0 scope. case_001
uses NOAA Marine Cadastre's public AIS feed (the same upstream raw data
GFW + every fishing-effort study processes). Predicates anchored to
ITU-R M.1371 apply unchanged regardless of which agency hosts the data.
case_002 may wire the GFW gateway when an auth token is added.

## Capture flow

1. **Pick a day.** NOAA Marine Cadastre publishes one ZIP of AIS for the
   contiguous US per UTC day at
   `https://coast.noaa.gov/htdata/CMSP/AISDataHandler/<YYYY>/AIS_<YYYY>_<MM>_<DD>.zip`.
   Daily ZIPs are 200-400 MB compressed; uncompressed CSVs are 700 MB to
   2 GB.
2. **Stream-filter.** Use `polars.scan_csv` with `infer_schema_length=10000`
   (handles the mixed-blank-vs-numeric columns) to lazy-filter to one
   `VesselType` (e.g. 30 = Fishing per ITU-R M.1371 Table 18) and one
   MMSI. A moderate-activity vessel with 100-500 messages exercises the
   schema without being noisy.
3. **Persist as Parquet.** Write the filtered rows to
   `inputs/vessel_tracks.parquet` with zstd compression (~10-20 KB per
   vessel-day). Delete the daily ZIP and uncompressed CSV scratch.

## Inputs

`fixtures/case_<NNN>/inputs/`:
- `_provenance.json` — declares `target_mmsi`, `target_vessel_name`,
  `target_call_sign`, `target_vessel_type` (ITU code), `target_country_mid`
  (first 3 digits of MMSI per ITU MID table), `target_observation_date_utc`,
  capture URL and method.
- `vessel_tracks.parquet` — Polars-filtered AIS messages.

## Output (skill.py contract)

`run(inputs_dir: Path) -> dict` returns:

```python
{
    "target":          {"mmsi", "vessel_name", "call_sign",
                        "vessel_type", "country_mid", "observation_date"},
    "vessel": {                                      # extracted from data
        "mmsi": int, "vessel_name": str, "call_sign": str,
        "vessel_type": int, "imo": str,
        "transceiver_class": "A" | "B",
    },
    "tracks_summary": {
        "n_messages": int,
        "lat_min/max": float, "lon_min/max": float,
        "sog_min/max": float, "cog_min/max": float,
        "time_min": str, "time_max": str,
        "captured_dates": [str, ...],
    },
    "schema": {"columns": [str, ...], "n_columns": int},
    "files":  [{"file_path", "size_bytes", "sha256_prefix",
                "format": "parquet", "n_rows": int}],
    "captured_from":   str,
    "captured_at_utc": str,
    "capture_method":  str,
    "validation": {
        "all_validated":               bool,
        "all_mmsi_match_target":       bool,
        "mmsi_starts_with_target_mid": bool,
        "vessel_name_matches_target":  bool,
        "call_sign_matches_target":    bool,
        "target_vessel_type_present":  bool,
        "vessel_types_in_itu_table":   bool,
        "sog_in_ais_range":            bool,
        "cog_in_ais_range":            bool,
        "heading_in_ais_range":        bool,
        "lat_in_global_range":         bool,
        "lon_in_global_range":         bool,
        "all_dates_match_target":      bool,
        "n_messages":                  int,
        "n_files":                     int,
        "target_identifiers":          [str, ...],
    },
}
```

## Predicates (case_001) — 54 total

| Group | Source |
|---|---|
| **Identity** (7): target.mmsi `in_set [303324000]`, vessel_name, call_sign, vessel_type=30, country_mid="303", observation_date=2024-01-01, target keyset | **External** — search inputs declared in `_provenance.json` |
| **Vessel from data** (6): vessel.mmsi `in_set`, vessel_name, call_sign regex `^[WK][A-Z0-9]{3,7}$`, vessel_type=30, imo regex `^IMO[0-9]{7}$`, transceiver_class `in_set ["A","B"]` | **External**: ITU-R M.1371 (vessel type, transceiver class), FCC ship-station call-sign format (US W/K prefix), IMO numbering convention (7 digits) |
| **Tracks summary** (15): n_messages range, lat global + tight Pacific NW window [44, 47], lon global + tight Pacific NW window [-126, -122], SOG `in [0, 102.3]`, COG `in [0, 360]`, time regex starts with target date, captured_dates `in_set [target_date]` for_all | **External**: ITU-R M.1371 (SOG/COG ranges per Table 14, NaN value 102.3), equatorial coordinate definition, vessel's known fishing grounds (Pacific NW US continental shelf) |
| **Schema** (2): n_columns=17, columns `in_set` of NOAA Marine Cadastre's exact 17 column names, for_all | **External**: NOAA Marine Cadastre AIS schema (https://marinecadastre.gov/AIS/) |
| **Per-file shape** (5 for_all + 1): files min/max_size, file_path regex, sha256, size_bytes range, format=parquet, n_rows range | **External (Parquet format)** + structural |
| **Validation rollup** (13 booleans + 1 list + 2 counts) | Captured-data-only / belt-and-suspenders |
| **Capture URL + root keyset** (2) | **External** — locks data to NOAA Marine Cadastre URL |

The strong **external** predicates (~38 of 54) would catch a wrong
capture even with the validation booleans removed.

## Future cases

- **case_002**: a different vessel type (cargo=70, tanker=80) on a
  different day. Re-tightens identity but keeps the AIS-standard
  invariants.
- **case_003**: a multi-vessel slice for a small bbox-day. Tests
  joins/grain interaction-skills; introduces vessel-density predicates.
- **case_004**: actual GFW gateway data once auth is wired. The
  vessel-identity + AIS-range predicates carry over; add GFW-specific
  fields like `inferred_fishing_score` and `fishing_event_id`.
