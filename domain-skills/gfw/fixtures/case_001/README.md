# case_001 — TAASINGE (MMSI 303324000), 2024-01-01 UTC

## What this case demonstrates

A real US-flagged fishing vessel's AIS-tracks for one day (409 messages,
00:01:58 to 23:44:34 UTC), captured from NOAA Marine Cadastre's public
no-auth feed. Pure tabular path: download → polars filter → persist as
zstd Parquet. Every load-bearing predicate cites the ITU-R M.1371 AIS
standard, the ITU MID country-code table, the IMO numbering convention,
or the NOAA Marine Cadastre AIS schema.

## Provenance

Captured 2026-04-27 from
`https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2024/AIS_2024_01_01.zip`
(277 MB compressed; 770 MB uncompressed CSV). Filtered to
VesselType=30 (Fishing per ITU-R M.1371 Table 18) → 1,095 unique
fishing-vessel MMSIs in the day → picked MMSI 303324000 (TAASINGE)
from the 100-500-track-count bucket sorted ascending. Persisted 409
rows as 14.7 KB zstd Parquet.

## What the captured tracks contain (verified at capture-time)

| Field | Value | Predicate |
|---|---|---|
| `MMSI` | 303324000 | `in_set [303324000]` (identity) |
| `country_mid` | "303" | `in_set ["303"]` — ITU MID 303 = Alaska/USA |
| `VesselName` | TAASINGE | `in_set ["TAASINGE"]` (identity) |
| `CallSign` | WDI7004 | `regex ^[WK][A-Z0-9]{3,7}$` (FCC US ship-station) |
| `IMO` | IMO7398315 | `regex ^IMO[0-9]{7}$` (IMO 7-digit numbering) |
| `VesselType` | 30 | `in_set [30]` — Fishing per ITU-R M.1371 Table 18 |
| `TransceiverClass` | B | `in_set ["A", "B"]` — ITU AIS transmitter class |
| `n_messages` | 409 | `in_range [10, 10000]` |
| `LAT` range | [45.36, 45.73] | `in_range [44, 47]` — Pacific NW continental shelf |
| `LON` range | [-124.06, -123.98] | `in_range [-126, -122]` — Oregon coast |
| `SOG` range | [0.1, 9.6] knots | `in_range [0, 102.3]` (102.3 = "not available") |
| `COG` range | [0.1, 359.5] degrees | `in_range [0, 360]` |
| `BaseDateTime` range | 2024-01-01T00:01:58 to T23:44:34 | `regex ^2024-01-01T` |
| `captured_dates` | ["2024-01-01"] | `in_set ["2024-01-01"]` for_all |
| schema columns | 17 NOAA Marine Cadastre fields | `in_set` of exact column list, for_all |

## External-source citations (predicate provenance)

| Predicate group | Source |
|---|---|
| MMSI 9-digit format + country MID first 3 digits | **ITU-R M.585** — Maritime Mobile Service Identity assignments |
| MID 303 = Alaska/United States | **ITU MID table** — Maritime Identification Digit assignments |
| VesselType 30 = Fishing | **ITU-R M.1371-5 Table 18** — Ship and cargo type codes (0-99) |
| SOG 0-102.2 knots, 102.3=NaN | **ITU-R M.1371-5 Table 14** — Speed Over Ground value range |
| COG 0-360 degrees | **ITU-R M.1371-5 Table 14** — Course Over Ground |
| Heading 0-359 or 511 (NaN) | **ITU-R M.1371-5** — true heading field spec |
| TransceiverClass A vs B | **ITU-R M.1371-5** — Class A (SOLAS-mandated) vs Class B (recreational) |
| IMO regex `^IMO[0-9]{7}$` | **IMO Resolution A.600(15)** — 7-digit IMO ship identification number |
| US call sign W/K prefix | **FCC Part 80 / ITU Radio Regulations Article 19** — international call-sign letter assignments to USA |
| Lat/Lon equatorial ranges | **WGS-84 datum** for AIS position reports |
| Pacific NW geographic window | **NOAA fishing grounds documentation** for Oregon coast (Astoria/Newport area) |
| 17 NOAA AIS columns | **NOAA Marine Cadastre AIS data dictionary** at marinecadastre.gov/AIS/ |
| Capture URL prefix | NOAA Marine Cadastre standard archive path |

## Spoof matrix

| Mutation | Predicate that fails |
|---|---|
| `_provenance.json` `target_mmsi` → 999999999 | `target.mmsi in_set [303324000]` fails first |
| `_provenance.json` `target_vessel_type` → 99 | `target.vessel_type in_set [30]` fails |
| Replace `vessel_tracks.parquet` rows with a different MMSI's tracks | `validation.all_mmsi_match_target in_set [true]` fails; vessel_name and call_sign would also drift |
| Mix in a row with `LAT=200` (invalid) | `validation.lat_in_global_range in_set [true]` fails |
| Drop the `IMO` column | `vessel.imo regex` fails (empty doesn't match) |
| Replace the day's data with rows from a different date | `validation.all_dates_match_target` fails; `tracks_summary.captured_dates[*] in_set` fails for_all |

## Why TAASINGE / 2024-01-01

- **US-flagged with full identity fields populated** — MMSI, IMO, FCC
  call sign all present, allowing strong identity predicates.
- **Moderate activity** — 409 tracks is enough to exercise the schema
  without being noisy. A vessel with 1,300+ tracks would have similar
  predicate behavior but a larger persisted parquet.
- **Stable geography** — fishing in Oregon-coast waters; the lat/lon
  predicate windows (44-47°N, -126 to -122°W) are tight enough to
  reject a mis-attributed vessel.
- **NOAA's data-of-record** — the underlying U.S. Coast Guard Nationwide
  Automatic Identification System (NAIS) feed; same data GFW uses to
  build their fishing-effort grids.
