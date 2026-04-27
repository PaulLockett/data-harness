# case_001 — ZTF public alerts, night of 2023-02-20 UTC

## What this case demonstrates

A 5-alert sample from the Zwicky Transient Facility's public alert archive
for one observation night. The case exercises:

- **Avro-format capture** — first Phase 4 domain to use a binary
  serialization other than FITS / JSON / `$`-delimited ASCII.
- **Schema-version-locked predicates** — the ZTF Avro schema is
  versioned and publicly documented at
  `https://github.com/ZwickyTransientFacility/ztf-avro-alert`. Predicates
  assert the captured `schemavsn`, `publisher`, and top-level field set
  match the v3.3 contract.
- **Survey-paper-anchored physics predicates** — filter system, magnitude
  range, JD start, programid, and field-ID range all come from
  Bellm et al. 2019, the founding ZTF survey paper.

## Provenance

Captured 2026-04-27 from
`https://ztf.uw.edu/alerts/public/ztf_public_20230220.tar.gz` (9.5 MB
compressed; 213 alerts in the night). Extracted the first 5 alerts via
`tarfile.extractfile`, discarded the remaining 208 + tar bytes. Persisted
footprint: ~300 KB.

## What's in `inputs/`

| File | Bytes | Notes |
|---|---|---|
| `_provenance.json` | ~1.5 KB | target schemavsn / publisher / programid + capture metadata |
| `alerts/2241227440415015014.avro` | 55,679 | objectId ZTF19acgecqr |
| `alerts/2241227440415015020.avro` | 52,040 | objectId ZTF23aactfqe |
| `alerts/2241227440515010041.avro` | 67,329 | objectId ZTF18acpdnys |
| `alerts/2241227440515010047.avro` | 66,444 | objectId ZTF18acpupju |
| `alerts/2241227445915015042.avro` | 55,949 | objectId ZTF19aaljmem |

## What the alerts contain (verified at capture-time, all 5)

| Field | Value range | Predicate |
|---|---|---|
| `schemavsn` | "3.3" | `in_set ["3.3"]` for_all |
| `publisher` | "ZTF (www.ztf.caltech.edu)" | `in_set [...]` for_all |
| `objectId` | ZTF19acgecqr, ZTF23aactfqe, ZTF18acpdnys, ZTF18acpupju, ZTF19aaljmem | regex `^ZTF[0-9]{2}[a-z]+$` for_all |
| `candid` | 18-digit alert IDs (2241227440415015014, etc.) | derived from filename pattern |
| `candidate.fid` | 2 (r-band), all 5 alerts | `in_set [1, 2, 3]` for_all |
| `candidate.programid` | 1 (public archive) | `in_set [1]` for_all |
| `candidate.jd` | 2459995.7274 (≈ 2023-02-19 17:30 UTC, the start of the 02-20 UTC night) | `in_range [2458000, 2470000]` for_all |
| `candidate.ra` | 123.14, ... (degrees J2000) | `in_range [0, 360]` for_all |
| `candidate.dec` | -5.05, ... (degrees J2000) | `in_range [-90, 90]` for_all |
| `candidate.magpsf` | 15.89, ... | `in_range [10, 25]` for_all |
| `candidate.isdiffpos` | "t" (positive difference) | `in_set ["t","f",...]` for_all |
| `candidate.field` | 413, ... (ZTF field ID in survey grid) | `in_range [1, 2000]` for_all |

## External-source citations (predicate provenance)

| Predicate group | Source |
|---|---|
| schemavsn = "3.3", schema_name = "ztf.alert", 9-12 top-level fields | **`ztf-avro-alert/schema/alert.avsc`** at github.com/ZwickyTransientFacility/ztf-avro-alert |
| publisher = "ZTF (www.ztf.caltech.edu)" | **ZTF Avro alert spec** — constant on every published alert |
| programid = 1 for public archive | **`https://ztf.uw.edu/alerts/public/` documentation** — programid field codes 1=public, 2=collaboration, 3=Caltech |
| objectId regex `^ZTF[0-9]{2}[a-z]+$` | **Bellm et al. 2019** PASP 131, 018002, §4.4 (alert object naming convention) |
| filter system fid ∈ {1=g, 2=r, 3=i} | **Bellm et al. 2019** §3.2 (filter system table) |
| magpsf in [10, 25] | **Bellm et al. 2019** §6 (saturation ~12.5; 5σ depth ~21.5 at 30 s exposure) |
| jd ≥ 2458000 (ZTF survey start) | **Bellm et al. 2019** survey commencement March 2018 |
| field IDs in survey grid (245-1895; range [1, 2000] generous) | **Bellm et al. 2019** Table 1 (survey field grid layout) |
| isdiffpos enum values ("t", "f", or "1", "0") | **`ztf-avro-alert/schema/candidate.avsc`** — boolean polarity flag |
| Avro file format magic + reader contract | **Apache Avro specification** |
| ra in [0, 360], dec in [-90, 90] | **Equatorial coordinate definition** (J2000) |
| Capture URL prefix `^https://ztf\.uw\.edu/alerts/public/` | **ZTF public archive URL** |

## Spoof matrix

| Mutation | Predicate that fails |
|---|---|
| `_provenance.json` `target_schemavsn` → "9.9" | `target.schemavsn in_set ["3.3"]` fails first |
| `_provenance.json` `target_programid` → 99 | `target.programid in_set [1]` fails |
| Replace one alert's bytes with a non-ZTF Avro file | `alerts[*].schemavsn in_set ["3.3"]` fails for_all; `objectId` regex would also fail |
| Truncate one alert to a 0-byte file | astropy/fastavro raises before predicates evaluate; alternately, `size_bytes in_range` fails |
| Swap one alert with a `programid=2` (collaboration-tier) alert | `alerts[*].candidate.programid in_set [1]` fails for_all — **the strong external invariant for the public archive** |

## Why ZTF / 2023-02-20

- **Public no-auth archive.** Predicates can be reproduced by anyone.
- **Mature schema.** schemavsn 3.3 has been stable since 2020;
  predicate-version-locking is reliable.
- **Small night.** 9.5 MB compressed / 213 alerts; 5-alert sample fits
  easily under the 300 KB persistence target.
- **Documented invariants.** Bellm 2019 + GitHub schema repo provide
  strong externally-citable predicate sources.
