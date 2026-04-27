# snapshot-serengeti — camera-trap species classification metadata

## What it does

Reads captured Snapshot Serengeti species list + train/val splits from
Lila BC, validates against the published 60+1-class taxonomy and the
expected camera-trap site-ID convention (Serengeti's grid uses
`<letter><2-digit>` sites, e.g. B03 / V13).

case_001 captures only the dataset metadata (~5.6 KB total) — the full
~3.2M annotated images live in 19 MB+ per-season annotation JSONs and
hundreds of GB of image data, both deliberately not included in v0.

## Capture flow

1. GET `https://lilawildlife.blob.core.windows.net/lila-wildlife/snapshotserengeti-v-2-0/SnapshotSerengeti_S1-11_v2.1.species_list.csv`
   — 60+1 species classes (the +1 is "empty" for camera-triggered-but-no-animal frames)
   plus their image counts across S01-S11.
2. GET `https://storage.googleapis.com/public-datasets-lila/snapshotserengeti-v-2-0/SnapshotSerengetiSplits_v0.json`
   — train/val site lists keyed by `<letter><2-digit>` site IDs for seasons 1-6.

Lila BC Azure Blob + Google Cloud Storage URLs are no-auth public.

## Output (skill.py contract)

`run(inputs_dir: Path) -> dict` returns target / species (n_classes,
names, counts, top_5, non_empty_top) / splits (info, split_keys,
n_train_sites, n_val_sites, samples) / files / validation rollup with
10 sub-flags.

## Predicates (case_001) — 39 total

| Group | Source |
|---|---|
| **Identity** (7): dataset, n_species=61, n_seasons=11, top_species_by_count, well_known_species, splits in {train, val, test}, target keyset | **External**: Lila BC Snapshot Serengeti dataset documentation + Swanson et al. 2015 species taxonomy + Serengeti National Park camera-trap deployment 2010-2014 |
| **Species** (7): n_classes=61, names list, top_5 in_set [empty, wildebeest, zebra, gazellethomsons, buffalo], non_empty_top=wildebeest, non_empty_top_count in [400K, 700K] | **External**: published image-count rankings from Lila BC; Serengeti National Park hosts ~1.5M wildebeest population (largest on earth) |
| **Splits** (6): split_keys=[train,val], n_train >= 100, site IDs match `^[A-Z][0-9]{2}$` for_all | **External**: SnapshotSerengetiSplits_v0.json info field documents seasons 1-6 split + Serengeti grid letter-number site convention |
| **Per-file shape** (4 for_all + 1) | Structural |
| **Validation rollup** (12) | Captured-data-only |
| **Capture URL + root keyset** (2) | **External** — Lila BC Azure Blob URL pattern |

## Future cases

- **case_002**: a single season's annotations (e.g. S01) — adds image
  metadata + bounding-box predicates.
- **case_003**: cross-domain composition — voxel-level species
  distribution analysis using the `distribution` interaction-skill
  on captured species counts.
