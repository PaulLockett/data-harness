# ztf — Zwicky Transient Facility alert sample

## What it does

Reads a sample of ZTF (Zwicky Transient Facility) public Avro alert files
captured from one observation night and emits a canonical Alert-Sample
record. Each alert's `schemavsn`, `publisher`, `programid`, and `objectId`
are validated against the ZTF Avro alert schema invariants documented in
the public `ztf-avro-alert` repository, and each `candidate` subrecord is
validated against the ZTF survey conventions in Bellm et al. 2019
(PASP 131, 018002): filter ID is one of {1=g, 2=r, 3=i}, RA in [0, 360]°,
Dec in [-90, 90]°, and PSF magnitude in the survey's typical detection
range. Predicates assert these survey invariants directly so the case
fails when captured alerts don't pertain to the public ZTF stream.

## Capture flow

1. **Pick a night.** ZTF publishes one tar of Avro alerts per UTC night at
   `https://ztf.uw.edu/alerts/public/ztf_public_<YYYYMMDD>.tar.gz`. Tarball
   sizes range from a few MB to ~1 GB depending on observing conditions
   and survey footprint coverage.
2. **Pick a small one** (resource-budget discipline). Probe the index
   listing for K- or M-suffix sizes; values like 7-12 MB are typical for
   a quiet night and yield ~200 alerts.
3. **Download** the `.tar.gz` to scratch (NOT under `inputs/`).
4. **Stream-extract** a representative sample (5-10 alerts) via
   `tarfile.extractfile`; save under `inputs/alerts/<candid>.avro`.
5. **Discard the tarball** and the unextracted alerts; persisted footprint
   is ~50-67 KB per alert × 5 alerts = ~300 KB.

## Inputs

`fixtures/case_<NNN>/inputs/`:
- `_provenance.json` — declares `target_archive_url`,
  `target_observation_night_utc` (YYYYMMDD), `target_schemavsn`,
  `target_publisher`, `target_programid` (1 for public archive),
  capture method.
- `alerts/<candid>.avro` — one or more ZTF alert Avro files, one record
  per file.

## Output (skill.py contract)

`run(inputs_dir: Path) -> dict` returns:

```python
{
    "target": {
        "schemavsn":             str,    # e.g. "3.3"
        "publisher":             str,    # canonical "ZTF (www.ztf.caltech.edu)"
        "programid":             int,    # always 1 for public archive
        "observation_night_utc": str,    # YYYYMMDD
    },
    "alerts": [
        {
            "filename":                  str,    # <candid>.avro
            "file_path":                 "alerts/...",
            "size_bytes":                int,
            "sha256_prefix":             str,    # 16 hex
            "schema_name":               "ztf.alert",
            "schemavsn":                 str,
            "publisher":                 str,
            "objectId":                  str,    # ZTF<YY><7-letters>
            "object_id_matches_pattern": bool,
            "object_id_year_2digit":     str,
            "candid":                    int,    # 18-20 digit alert ID
            "candidate": {
                "jd":        float,    # Julian Date
                "fid":       int,      # 1=g, 2=r, 3=i
                "pid":       int,
                "ra":        float,    # degrees J2000
                "dec":       float,    # degrees J2000
                "magpsf":    float,    # PSF magnitude
                "sigmapsf":  float,    # magnitude error
                "isdiffpos": str,      # "t" or "f"
                "programid": int,      # always 1 for public
                "field":     int,      # ZTF survey field ID
                "ssdistnr":  float,    # nearest solar-system object distance (-999 = none)
                "candid":    int,
            },
            "n_top_fields":              int,
            "missing_top_fields":        [str, ...],
            "missing_candidate_fields":  [str, ...],
        }, ...
    ],
    "files":          [{"file_path", "size_bytes", "sha256_prefix",
                        "format": "avro"}, ...],
    "captured_from":   str,
    "captured_at_utc": str,
    "capture_method":  str,
    "validation": {
        "all_validated":                          bool,
        "publishers_match_target":                bool,
        "schemavsns_match_target":                bool,
        "programids_match_target":                bool,
        "object_ids_match_pattern":               bool,
        "fids_in_ztf_filter_system":              bool,
        "isdiffpos_valid":                        bool,
        "all_required_top_fields_present":        bool,
        "all_required_candidate_fields_present":  bool,
        "n_alerts":                               int,
        "n_files":                                int,
        "target_identifiers":                     [str, ...],
    },
}
```

## Predicates (case_001)

43 predicates total. Provenance per group:

| Group | Predicate(s) | Source |
|---|---|---|
| **Identity** (5) | `target.schemavsn in_set ["3.3"]`, `target.publisher in_set ["ZTF (www.ztf.caltech.edu)"]`, `target.programid in_set [1]`, `target.observation_night_utc` regex, `target` keyset | **External (`_provenance.json` + ZTF Avro alert spec)** — schemavsn 3.3 has been current since 2020; publisher string is the canonical Avro `publisher` per the schema; programid=1 is the public-archive contract. |
| **Per-alert shape** (15, all for_all) | file_path/size_bytes/sha256_prefix/schema_name/schemavsn/publisher/objectId regex; `object_id_matches_pattern in_set [true]`; n_top_fields in_range [9, 12] | **External (ZTF Avro schema repo)** — `ztf-avro-alert/schema/alert.avsc` defines exactly 9 top-level fields for schemavsn 3.3; the schema_name is `ztf.alert`; the publisher and schemavsn values are constants in the Avro stream. |
| **Per-alert candidate physics** (8, all for_all) | `fid in {1,2,3}`, `programid in {1}`, `ra in [0,360]`, `dec in [-90,90]`, `jd in [2458000,2470000]`, `magpsf in [10,25]`, `sigmapsf in [0,5]`, `isdiffpos in {t,f,1,0,true,false}`, `field in [1,2000]` | **External (Bellm et al. 2019 PASP 131, 018002 + ZTF survey website)** — filter system documented in §3.2 of the survey paper; ra/dec are J2000 celestial coordinates; ZTF survey began 2018-03 (JD 2458180), giving a lower bound on captured `jd`; ZTF detection saturates at magpsf~12.5 and faintens to ~21.5 at 30s exposure, so [10, 25] is a generous physical envelope; `isdiffpos` is the difference-image polarity flag with documented enum values; field IDs are 245-1895 in the survey grid. |
| **Per-file shape** (5 for_all) | files min/max_size, file_path regex, sha256_prefix 16 hex, size_bytes range, format `in_set ["avro"]` | **External (Avro file format)** + **structural** |
| **Validation rollup** (10 booleans + 1 list) | `all_validated`, 8 sub-flags, `n_alerts`, `target_identifiers min_size 3` | **Captured-data-only / belt-and-suspenders** — these mirror skill flags but the strong external predicates above would catch failures even with these removed. |
| **Capture URL + root keyset** (2) | captured_from regex `^https://ztf\.uw\.edu/alerts/public/`; root key_set_includes | **External** — locks data to the ZTF public archive URL. |

The strong **external** predicates (~33 of 43) would catch a wrong capture
even if the skill's validation flags were broken; the **captured-data-only**
predicates (~10) are belt-and-suspenders.

## Future cases

- **case_002**: a different night (different YYYYMMDD), perhaps one with
  a known transient. The schemavsn / publisher / programid invariants
  carry over unchanged; only `target.observation_night_utc` retightens.
- **case_003**: filter rather than sampling — pick alerts where the
  candidate has `ssdistnr > 0` (a nearby solar-system object) and validate
  the SSO catalog cross-match. Adds asteroid-detection content predicates.
- **case_004**: cutout-image rendering. The Avro records carry FITS
  cutoutScience/cutoutTemplate/cutoutDifference; case_004 wires the
  `pdf_render` / `fits_open` Tier-3 helpers and predicates the cutout
  shape (pixel scale, WCS pointing within `ra ± epsilon`).
- **case_005**: cross-domain composition with the `distribution`
  interaction-skill — magnitude-distribution KS test against a known
  reference catalog.
