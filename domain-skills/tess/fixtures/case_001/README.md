# case_001 — TOI-700 (TIC 150428135), Sector 1

## What this case demonstrates

The first end-to-end TESS fixture: a real Sector 1 SPOC light curve for
**TOI-700**, an M-dwarf 100 light-years away that hosts the first
Earth-sized planet found in a star's habitable zone by NASA's TESS mission.

It exercises the full data-harness contract for an astronomy domain:
- **Bulk-download capture** (no browser-harness): grep MAST's published
  per-sector manifest for the target's TIC, fetch the FITS via the MAST API
  with redirect-following.
- **Astropy-based parsing**: read the primary HDU header for stellar
  identity + the extension-1 binary table for the light-curve photometry.
- **Content-vs-target validation**: every file's `TICID` and `OBJECT`
  header keywords must match the declared search target before the case
  predicates can pass.

## Provenance

Captured 2026-04-27. Source URL recorded in `inputs/_provenance.json`.

```
https://mast.stsci.edu/api/v0.1/Download/file/?uri=mast:TESS/product/tess2018206045859-s0001-0000000150428135-0120-s_lc.fits
```

The MAST API 302-redirects to the actual S3 location at
`stpubdata.s3.us-east-1.amazonaws.com/tess/public/tid/s0001/0000/0001/5042/8135/...`.
The skill records both the API URL (stable, citable) and the S3 mirror is
treated as an implementation detail.

## What's in `inputs/`

| File | Bytes | Notes |
|---|---|---|
| `_provenance.json` | ~1 KB | target spec, capture metadata, URL map |
| `lightcurves/tess2018206045859-s0001-0000000150428135-0120-s_lc.fits` | 2,039,040 | real SPOC light-curve FITS |

Total: ~2 MB on disk.

## What the FITS contains (verified at capture-time)

| Field | Value | Predicate window |
|---|---|---|
| `TICID` | 150428135 | `in_set ["150428135"]` |
| `OBJECT` | "TIC 150428135" | `regex ^TIC\s+[0-9]+$` |
| `TESSMAG` | 10.91 | `in_range [0, 25]` |
| `TEFF` | 3494 K | `in_range [2000, 12000]` |
| `RADIUS` | 0.42 R_sun | `in_range [0.05, 100]` |
| `RA_OBJ` | 97.097° | `in_range [95, 100]` |
| `DEC_OBJ` | -65.579° | `in_range [-70, -60]` |
| `SECTOR` | 1 | `in_range [1, 100]` |
| `CAMERA` | 4 | `in_range [1, 4]` |
| `CCD` | 3 | `in_range [1, 4]` |
| `n_cadences` | 20,076 | `in_range [100, 1000000]` |
| `n_finite_flux` | 18,279 | `in_range [50, 1000000]` |
| `time_min_bjd` (TJD) | 1325.294 | `in_range [1300, 100000]` |
| `time_max_bjd` (TJD) | 1353.176 | (covered by min check) |
| `PDCSAP_FLUX` median | 6,572.4 e-/s | (no predicate; physical for V=10.9) |
| `sha256_prefix` | `4b2aa5d5584b4cc3` | `regex ^[0-9a-f]{16}$` |

The RA/Dec window is narrow on purpose — it locks this case specifically to
TOI-700, not just any TIC. case_002 (different target) re-tightens this to
the new target's coordinates.

## Spoof matrix

| Mutation | Predicate that fails |
|---|---|
| corrupt `_provenance.json` `target_tic` to `1234` | `tic_id_match` becomes false → `lightcurves[*].validated in_set [true]` (for_all) fails |
| flip `target.tic_id` in skill output to `"999"` | `target.tic_id in_set ["150428135"]` fails |
| swap in a FITS for a different star | `tic_id_match=false` cascades to `validated=false`, predicate fails |
| truncate FITS to <100 KB | `size_bytes in_range [100000, ...]` fails |
| replace bytes with HTML error page | astropy raises `OSError("Empty or corrupt FITS file")` → skill exits non-zero before predicates run |

## Why TOI-700

- **Public**: MAST is a no-auth archive; predicates can be reproduced anywhere.
- **Small**: One Sector 1 light curve is ~2 MB. Stays well inside the 20 GB
  total footprint cap.
- **Memorable**: TOI-700 d is the first Earth-sized habitable-zone planet
  TESS found; the system is well-characterized in the literature so the
  predicate windows are easy to defend.
- **Geographically friendly**: TESS observed it in 9 sectors (1, 3, 4, 6,
  8, 10, 11, 12, 13); future cases can use the same target across epochs.
