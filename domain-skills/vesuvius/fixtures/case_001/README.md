# case_001 — PHercParis2Fr47, level 5 of 54keV/3.24μm Zarr volume

## What this case demonstrates

A real 3D micro-CT crop of one of the carbonized Herculaneum papyrus
fragments published by the Vesuvius Challenge. The case exercises:

- **OME-NGFF multiscale Zarr capture** at strict resource budget — the
  full fragment is 100s of MB; only the most-downsampled pyramid level
  (~3.4 MB compressed) is persisted. Levels 0-4 are intentionally not
  downloaded.
- **Zarr v2 format conformance** — the `.zattrs` (multiscales metadata),
  per-level `.zarray` (shape/dtype/chunks/compressor), and the
  `dimension_separator='/'` chunk path layout all match the Zarr v2
  storage spec.
- **Voxel-level sanity** — sampling a 50×30×50 corner verifies that real
  X-ray attenuation data is on disk (75,000/75,000 sampled voxels
  non-zero; uint16 values 20983-32657, consistent with carbonized
  papyrus organic-material density on the µCT scale).

## Provenance

Captured 2026-04-27 from the Vesuvius Challenge data hosting at
`https://dl.ash2txt.org/fragments/Frag1/PHercParis2Fr47.volpkg/volumes_zarr/54keV_3.24um_.zarr/`.
The fragment is "PHercParis2Fr47", part of the
P.Herc.Paris.2 scroll held at the Bibliothèque Nationale de France
(unrolled and scanned for the Vesuvius Challenge first letters prize).
Scan energy 54 keV; voxel size 3.24 μm.

## What's in `inputs/`

| File | Bytes | Notes |
|---|---|---|
| `_provenance.json` | ~2 KB | target spec + capture metadata |
| `fragment.zarr/.zattrs` | 3,018 | OME-NGFF root multiscales metadata |
| `fragment.zarr/.zgroup` | 24 | Zarr group marker `{"zarr_format": 2}` |
| `fragment.zarr/5/.zarray` | 397 | Level 5 array spec |
| `fragment.zarr/5/0/0/0` | 1,095,826 | chunk z=0,y=0,x=0 (blosc/zstd) |
| `fragment.zarr/5/0/0/1` | 815,422 | chunk z=0,y=0,x=1 |
| `fragment.zarr/5/1/0/0` | 824,895 | chunk z=1,y=0,x=0 |
| `fragment.zarr/5/1/0/1` | 648,920 | chunk z=1,y=0,x=1 |

Total persisted: ~3.4 MB.

## What the volume contains (verified at capture-time)

| Field | Value | Predicate |
|---|---|---|
| `volume.shape` | [226, 44, 225] (z, y, x) | `shape[*] in_range [1, 100000]` for_all |
| `volume.dtype` | uint16 | `in_set ["uint8", "uint16"]` |
| `volume.chunks` | [128, 128, 128] | `chunks[*] in_range [1, 2048]` for_all |
| `volume.zarr_format` | 2 | `in_set [2, 3]` |
| `volume.dimension_separator` | "/" | `in_set ["/", "."]` |
| `volume.fill_value` | 0 | `in_range [0, 65535]` |
| `volume.compressor_id` | blosc | `in_set [...]` |
| `volume.compressor_cname` | zstd | `in_set [...]` |
| `volume.compressor_clevel` | 3 | (no predicate) |
| `ome_ngff.axes` | z/y/x all type=space | `axes[*].type in_set ["space","channel","time"]` |
| `ome_ngff.n_pyramid_levels` | 6 | `in_range [2, 12]` |
| `ome_ngff.pyramid_paths` | ["0","1","2","3","4","5"] | `pyramid_paths[*]` regex `^[0-9]+$` |
| `sample.shape` | [50, 30, 50] | (no predicate; informational) |
| `sample.n_total` | 75,000 | `in_range [1, 1M]` |
| `sample.n_nonzero` | 75,000 | `in_range [0, 1M]` |
| `sample.min` | 20,983 | `in_range [0, 65535]` |
| `sample.max` | 32,657 | `in_range [0, 65535]` |
| `sample.mean` | 23,368.2 | `in_range [0, 65535]` |
| `sample.nonzero_ratio` | 1.0 | `in_range [0.5, 1.0]` |

## External-source citations (predicate provenance)

| Predicate group | Source |
|---|---|
| OME-NGFF multiscales structure (axes, datasets, coordinate transformations) | **OME Next-Generation File Format spec** (ngff.openmicroscopy.org), §4 multiscale-image rules |
| Zarr v2 `.zarray` field layout (zarr_format / shape / chunks / dtype / compressor / dimension_separator / fill_value) | **Zarr v2 storage specification** (zarr.readthedocs.io/en/stable/spec/v2.html) |
| Numcodecs compressor IDs (`blosc` / `zlib` / `lz4` / `zstd` / `gzip`) | **Numcodecs registry** (numcodecs.readthedocs.io) |
| Vesuvius Challenge fragment naming (PHercParis2Fr47, PHerc0009B, etc.) and scan energies (54, 70, 88 keV) | **scrollprize.org/data** documentation pages and dl.ash2txt.org autoindex listings |
| 3D axes order z/y/x | **Vesuvius Challenge data spec** (z is depth-into-volume, y/x are scan plane) |
| uint16 voxel range [0, 65535] | **µCT physics** — typical 16-bit detector ADC output |
| Capture URL prefix `^https://dl\.ash2txt\.org/` | **Vesuvius Challenge data hosting URL** |

## Spoof matrix

| Mutation | Predicate that fails |
|---|---|
| `_provenance.json` `target_fragment_id` → "WRONGFRAG" | `target.fragment_id in_set ["PHercParis2Fr47"]` fails first |
| `_provenance.json` `target_dtype` → "float64" | `target.dtype in_set ["uint8","uint16"]` fails |
| Truncate one chunk file to 0 bytes | `files[*].size_bytes in_range [10, ...]` fails for_all OR zarr.open raises before predicates run |
| Replace `.zattrs` with empty `{}` | skill raises `RuntimeError("missing 'multiscales'")` |
| Corrupt one chunk's blosc bytes | `arr[0:50, 0:30, 0:50]` decode raises; case fails to produce output |

## Why PHercParis2Fr47

- **Smallest persisted footprint** — fragment Zarrs are MB-scale at level
  5; full scrolls (PHerc0009B etc.) are GB-scale even at level 5. Stays
  comfortably inside the 20 GB total cap with 18+ GB headroom.
- **OME-NGFF compliant** — Vesuvius Challenge migrated to OME-NGFF in
  2024; predicates against the metadata structure are stable across
  fragments.
- **Public, no-auth** — dl.ash2txt.org serves nginx autoindex; no
  authentication required for fragment data (full-scroll TB-scale data
  is gated; we deliberately avoid that branch).
- **Real scientific value** — this fragment was used as competition data
  for the first-letters prize; predicates anchored to its known scan
  parameters (54 keV, 3.24 μm) are independently citable from the
  Vesuvius Challenge announcements.
