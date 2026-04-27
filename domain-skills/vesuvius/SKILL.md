# vesuvius — Vesuvius Challenge fragment Zarr crops

## What it does

Reads a small persisted slice of one of the Herculaneum-scroll micro-CT
volumes published by the Vesuvius Challenge and emits a canonical
Vesuvius-Crop record. The Zarr store on disk holds only the targeted
multiscale-pyramid level and its compressed chunks; the skill validates
the OME-NGFF metadata, the per-level array's dtype/shape/chunks/
compressor against the Vesuvius Challenge data spec + Zarr v2 spec, and
samples a small voxel block to confirm real data is on disk (not all
fill_value=0).

## Capture flow

1. **Pick a fragment.** scrollprize.org / dl.ash2txt.org publishes nine
   public Herculaneum scroll fragments and three full-scroll volumes.
   Fragments are smaller than full scrolls (MB to GB rather than TB) and
   are the right entry point for case_001. Authoritative listing is
   `https://dl.ash2txt.org/fragments/`.
2. **Locate the Zarr store.** Each fragment is a `.volpkg` containing a
   `volumes_zarr/` directory with one or more energy-tagged Zarr stores
   (e.g. `54keV_3.24um_.zarr/`).
3. **Pick the smallest pyramid level.** OME-NGFF multiscale Zarrs expose
   pyramid levels indexed `0` (full res) through N. Level 5 is typically
   the most-downsampled (~3.4 MB compressed for a fragment).
4. **Persist only the targeted level.** Walk the chunk directories
   (`<level>/<z>/<y>/<x>` per Zarr v2 with `dimension_separator="/"`)
   and write each chunk plus the `.zarray`. Also persist root `.zattrs`
   (multiscales metadata) and `.zgroup`.
5. **Validate.** Open the persisted store with `zarr.open(mode="r")`,
   read the targeted level array, sample a 50×30×50 voxel corner. Real
   scroll data has >50% non-zero ratio (carbonized organic material) and
   uint16 values in the X-ray attenuation range.

## Inputs

`fixtures/case_<NNN>/inputs/`:
- `_provenance.json` — declares `target_fragment_id`, `target_scroll_id`,
  `target_energy_keV`, `target_voxel_size_um`, `target_volume_level`,
  `target_axes`, `target_dtype`, `target_zarr_format`, capture URL and
  method.
- `fragment.zarr/` — the persisted Zarr store with only the targeted
  level's chunks. Always includes `.zattrs`, `.zgroup`, and
  `<level>/.zarray` plus the compressed chunk files.

## Output (skill.py contract)

`run(inputs_dir: Path) -> dict` returns:

```python
{
    "target":   {"fragment_id", "scroll_id", "energy_keV",
                 "voxel_size_um", "volume_level", "axes",
                 "dtype", "zarr_format"},
    "ome_ngff": {
        "axes":             [{"name", "type"}, ...],   # OME-NGFF spec
        "n_pyramid_levels": int,
        "pyramid_paths":    [str, ...],
    },
    "volume":   {
        "path":                str,    # the persisted level
        "shape":               [int, int, int],
        "dtype":               str,
        "chunks":              [int, int, int],
        "zarr_format":         int,    # 2 or 3
        "dimension_separator": str,    # "/" or "."
        "fill_value":          int,
        "compressor_id":       str,    # "blosc" / "zlib" / ...
        "compressor_cname":    str,    # "zstd" / "lz4" / ...
        "compressor_clevel":   int,
    },
    "sample":   {                                  # small voxel-block
        "shape":         [int, int, int],
        "n_total":       int,
        "n_nonzero":     int,
        "min":           int,
        "max":           int,
        "mean":          float,
        "std":           float,
        "nonzero_ratio": float,
    },
    "files":    [{"file_path", "size_bytes", "sha256_prefix"}, ...],
    "captured_from":   str,
    "captured_at_utc": str,
    "capture_method":  str,
    "validation": {
        "all_validated":              bool,
        "axes_names_match_target":    bool,
        "axes_types_all_space":       bool,
        "pyramid_paths_sequential":   bool,
        "n_pyramid_levels":           int,
        "array_dtype_matches_target": bool,
        "array_chunks_cubic":         bool,
        "zarr_format_matches_target": bool,
        "sample_has_real_data":       bool,
        "sample_in_uint16_range":     bool,
        "n_files":                    int,
        "target_identifiers":         [str, ...],
    },
}
```

## Predicates (case_001)

49 predicates total. Provenance per group:

| Group | Predicate(s) | Source |
|---|---|---|
| **Identity** (9) | `target.fragment_id in_set ["PHercParis2Fr47"]`, `scroll_id in_set ["PHerc.Paris.2"]`, `energy_keV in_set [54, 70, 88]` (the three published Herculaneum scan energies), `voxel_size_um in [1, 10]`, `volume_level in [0, 10]`, `axes[*] in_set ["z", "y", "x"]`, `dtype in_set ["uint8", "uint16"]`, `zarr_format in_set [2, 3]`, target keyset | **External**: Vesuvius Challenge data documentation (scrollprize.org/data) — fragment naming convention, scan energies, voxel pitches |
| **OME-NGFF metadata** (5) | `axes` has 3 elements; `axes[*].name` in {z,y,x,c,t}; `axes[*].type` in {space,channel,time}; `n_pyramid_levels in [2, 12]`; `pyramid_paths[*]` regex `^[0-9]+$` | **External**: OME Next-Generation File Format spec (ngff.openmicroscopy.org) §4 multiscale-image rules |
| **Zarr v2 spec** (10) | `volume.path` regex; `shape min/max_size 3` (3D volume); `shape[*] in [1, 100000]`; `dtype in_set` of valid Zarr v2 dtypes; `chunks min/max_size 3`; `chunks[*] in [1, 2048]`; `zarr_format in_set [2, 3]`; `dimension_separator in_set ["/", "."]`; `fill_value in [0, 65535]`; compressor id/cname enums | **External**: Zarr v2 storage specification (zarr.readthedocs.io); Numcodecs registry for compressor IDs |
| **Sample voxels** (6) | `n_total in [1, 1M]`, `n_nonzero in [0, 1M]`, `min in [0, 65535]`, `max in [0, 65535]`, `mean in [0, 65535]`, `nonzero_ratio in [0.5, 1.0]` | **External**: uint16 range from Zarr v2 spec; nonzero-ratio threshold encodes "real scroll material" — sparse/empty volumes would have ratio near 0 |
| **Files** (4 for_all + 1 size) | `files min/max_size 5-50`, `file_path regex ^fragment\.zarr/`, `sha256_prefix` 16 hex, `size_bytes in [10, 10MB]` | **External (Zarr v2 file format)** + **structural** |
| **Validation rollup** (10 booleans + 1 list) | `all_validated`, 8 sub-flags, `n_pyramid_levels`, `target_identifiers` | **Captured-data-only / belt-and-suspenders** |
| **Capture URL + root keyset** (2) | captured_from regex `^https://dl\.ash2txt\.org/`; root key_set_includes | **External** |

The strong **external** predicates (~37 of 49) would catch a wrong
capture even with the validation booleans removed; the **captured-data-only**
predicates (~12) are belt-and-suspenders.

## Future cases

- **case_002**: a different fragment (e.g. PHercParis2Fr48 or PHerc0500P2)
  at the same level. Re-tightens `target.fragment_id` to the new value;
  validates the predicate template generalizes off Frag1 specifics.
- **case_003**: a different pyramid level (e.g. level 3 instead of level
  5). Larger persisted footprint but same shape/dtype invariants.
- **case_004**: a synthetic crop from one of the full scrolls (PHerc0009B
  or PHerc0343P) at the highest downsample level. Exercises the
  full-scroll vs fragment data distinction.
- **case_005**: cross-domain composition — render a single Z-slice via
  the substrate's image helpers + run a `glance` distribution check on
  the voxel histogram; predicate that the histogram has the bimodal
  shape characteristic of carbonized scrolls (papyrus matrix vs.
  inscription ink).
