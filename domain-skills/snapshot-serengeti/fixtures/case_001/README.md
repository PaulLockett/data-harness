# case_001 — Snapshot Serengeti species list + train/val splits

Metadata-only fixture. The full ~3.2M annotated camera-trap images +
per-season annotation JSONs are deliberately not captured in v0
(hundreds of GB of images; per-season JSON is 19 MB+). case_001 captures
the species taxonomy (61 classes) and the train/val site splits.

## Provenance

Captured 2026-04-27 from Lila BC's Azure Blob + Google Cloud Storage
mirrors:
- `species_list.csv` (894 bytes) — 61 species + image counts S01-S11
- `splits.json` (4.7 KB) — train (179 sites) / val (46 sites) keyed by
  Serengeti grid camera-trap site IDs (B03, C02, ..., V13)

## What the captured data contains (verified at capture-time)

| Field | Value |
|---|---|
| n_species_classes | 61 (60 wildlife + "empty" placeholder) |
| Top 5 by image count | empty (5,445,842), wildebeest (533,478), zebra (352,892), gazellethomsons (323,326), buffalo (61,283) |
| Most-photographed wildlife species | wildebeest (533,478 images) |
| Camera-trap site count | 225 sites (179 train + 46 val) for seasons 1-6 |
| Site ID pattern | `^[A-Z][0-9]{2}$` |
| Splits version | "1.0" |
| Splits coverage | seasons 1-6 |

## External-source citations

- **Swanson et al. 2015** "Snapshot Serengeti, high-frequency annotated
  camera trap images of 40 mammalian species in an African savanna"
  (Scientific Data 2:150026) — original taxonomy (40 species; expanded
  to 60+empty in Lila BC v2.1)
- **Lila BC dataset page** (https://lila.science/datasets/snapshot-serengeti)
  — 11 seasons (S01-S11), 2010-2014 deployment, ~3.2M images
- **Serengeti National Park ecology** — wildebeest (~1.5M individuals)
  is the largest population of any African herbivore; predicate
  `non_empty_top == "wildebeest"` reflects this fact
- **Camera-trap site grid convention** — Snapshot Serengeti deployed a
  grid of ~225 cameras using letter+2-digit IDs documented in the
  Swanson 2015 supplement

## Spoof matrix

| Mutation | Predicate that fails |
|---|---|
| `_provenance.json` `target_n_species_classes` → 99 | `target.n_species_classes in_set [61]` fails first |
| Replace `species_list.csv` with empty | `species.n_classes in_set [61]` fails; `has_wildebeest`, `has_empty_class` fail |
| Reorder `species_list.csv` so wildebeest isn't top non-empty | `species.non_empty_top in_set ["wildebeest"]` fails |
| Replace `splits.json` site IDs with non-pattern values | `splits.train_sample[*] regex ^[A-Z][0-9]{2}$` fails for_all |
