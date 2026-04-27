# tess — TESS light-curve records

## What it does

Reads TESS (Transiting Exoplanet Survey Satellite) light-curve FITS files from
the SPOC (Science Processing Operations Center) pipeline and emits a canonical
record that combines the target's stellar identity with per-file light-curve
statistics and a validation rollup. Predicates assert both **schema shape**
AND **content provenance** — every FITS file's primary-header `TICID` must
match the declared search target, so downstream analysis trusts that the
photometry pertains to the star it claims.

## Capture flow

1. Pick a target by **TIC (TESS Input Catalog) ID**. For case_001 this is
   TIC 150428135 (TOI-700, an M-dwarf ~100 ly away that hosts the first
   Earth-sized habitable-zone planet found by TESS).
2. Identify which sectors observed the target. MAST publishes per-sector
   bulk-download manifests at
   `https://archive.stsci.edu/missions/tess/download_scripts/sector/tesscurl_sector_<NN>_lc.sh`.
   Grep the manifest for `s<NNNN>-<TIC_padded_to_16_digits>-` to pull the
   FITS URL for that sector + target.
3. Download the FITS via the MAST API URL
   (`https://mast.stsci.edu/api/v0.1/Download/file/?uri=mast:TESS/product/<filename>`).
   The MAST API issues a 302 to S3 (`stpubdata.s3.us-east-1.amazonaws.com`),
   so the HTTP client must follow redirects (`httpx` with
   `follow_redirects=True`). Save under `inputs/lightcurves/<filename>.fits`.
4. Parse with `astropy.io.fits`. The **primary HDU** carries target metadata
   (`TICID`, `OBJECT`, `TESSMAG`, `TEFF`, `RADIUS`, `RA_OBJ`, `DEC_OBJ`,
   `SECTOR`, `CAMERA`, `CCD`); **extension 1** carries the light-curve table
   with columns `TIME`, `SAP_FLUX`, `PDCSAP_FLUX`, `QUALITY`, etc. Prefer
   `PDCSAP_FLUX` (Pre-search Data Conditioning) over `SAP_FLUX` (Simple
   Aperture Photometry) when both are present.
5. **Validate every file pertains to the target**: `header['TICID']` matches
   the declared `target_tic`; `header['OBJECT']` contains one of
   `target_aliases`; light-curve table has `> 100` cadences. The skill marks
   each file `validated=true` only when all three hold.

## Inputs

`fixtures/case_<NNN>/inputs/`:
- `_provenance.json` — declares `target_tic` (numeric), `target_aliases`
  (list of names that should appear in `OBJECT`), `captured_from`,
  `captured_at_utc`, `capture_method`, and a `lightcurve_urls` map keyed by
  filename.
- `lightcurves/*.fits` — every FITS referenced by `lightcurve_urls`.

## Output (skill.py contract)

`run(inputs_dir: Path) -> dict` returns:

```python
{
    "target": {
        "tic_id":      str,    # decimal string, no leading zeros (matches TICID)
        "object_name": str,    # e.g. "TIC 150428135"
        "tess_mag":    float,  # apparent TESS magnitude
        "teff":        float,  # effective temperature (K)
        "radius":      float,  # stellar radius (R_sun)
        "ra_deg":      float,  # J2000 RA in degrees
        "dec_deg":     float,  # J2000 Dec in degrees
        "camera":      int,    # 1..4
        "ccd":         int,    # 1..4
    },
    "lightcurves": [
        {
            "filename":          str,
            "file_path":         "lightcurves/...",
            "size_bytes":        int,
            "sha256_prefix":     str,    # first 16 hex chars of SHA-256
            "sector":            int,
            "camera":            int,
            "ccd":               int,
            "n_cadences":        int,    # rows in extension-1 table
            "n_finite_flux":     int,    # finite values in PDCSAP_FLUX/SAP_FLUX
            "time_min_bjd":      float,  # min TIME in BJD - 2457000 (TJD)
            "time_max_bjd":      float,
            "flux_column":       "PDCSAP_FLUX" | "SAP_FLUX",
            "pdcsap_flux_median": float,
            "pdcsap_flux_min":    float,
            "pdcsap_flux_max":    float,
            "tic_id_in_header":  str,    # TICID from FITS, as string
            "object_in_header":  str,    # OBJECT from FITS
            "url":               str,    # MAST API URL it was fetched from
            "tic_id_match":      bool,   # tic_id_in_header == target_tic
            "object_name_match": bool,   # any alias appears in OBJECT
            "validated":         bool,   # all three checks passed
        }, ...
    ],
    "captured_from":   str,
    "captured_at_utc": str,
    "capture_method":  str,
    "validation": {
        "all_validated":      bool,         # for_all over lightcurves[*].validated
        "n_lightcurves":      int,
        "target_identifiers": [str, ...],   # the alias list used in matching
    },
}
```

## Predicates (case_001)

28 predicates enforce:
- **target identity is TOI-700**: `tic_id in_set ["150428135"]`; `ra_deg in
  [95, 100]` and `dec_deg in [-70, -60]` (a tight window around TOI-700's
  known sky position 97.10°, -65.58°)
- **target shape**: TESS magnitude in [0, 25], Teff in [2000, 12000] K,
  radius in [0.05, 100] R_sun (physical stellar ranges)
- **every file is on disk**: `file_path` regex `^lightcurves/.*\.fits$`
- **every file is real bytes**: `size_bytes` in [100 KB, 100 MB],
  `sha256_prefix` 16 hex chars
- **every light curve is plausible TESS data**: `n_cadences ≥ 100`,
  `time_min_bjd ≥ 1300` (Sector 1 begins ~TJD 1325), `flux_column` is one of
  the SPOC pipeline outputs
- **every file pertains to the target**: `tic_id_match == true`,
  `object_name_match == true`, `validated == true` for_all
- **captured_from points at MAST** (`^https://mast\.stsci\.edu/`)
- **rollup checks** on `validation.{all_validated, n_lightcurves,
  target_identifiers}`

## Future cases

- **case_002**: a different sector for TOI-700 (e.g. Sector 4 or 13) — same
  target, different observation epoch; should pass the same predicate set
  and prove the predicates aren't tied to one timestamp.
- **case_003**: a different target entirely (e.g. TIC 25155310 = TOI-100, a
  hot Jupiter host; or HD 21749 = TIC 279741379). Re-tightens the RA/Dec
  in_range to the new target — proves the predicate template generalizes.
- **case_004**: TESS Full-Frame Image (FFI) cutout via `tica` (different file
  layout, no pre-extracted light curve) — exercises FFI-vs-LC code path.
- **case_005**: a target with a known transiting planet — adds predicates on
  detected transit depth or BLS periodogram peak (introduces interaction-skill
  composition with `distribution`/`drift`).
