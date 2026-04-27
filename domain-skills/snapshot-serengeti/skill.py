"""snapshot-serengeti — read captured species list + train/val splits, build validated record."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from io import StringIO
from pathlib import Path


def _file_meta(p: Path) -> dict:
    raw = p.read_bytes()
    return {
        "file_path":     p.name,
        "size_bytes":    len(raw),
        "sha256_prefix": hashlib.sha256(raw).hexdigest()[:16],
    }


def run(inputs_dir: Path) -> dict:
    inputs_dir = Path(inputs_dir)
    prov = json.loads((inputs_dir / "_provenance.json").read_text())

    target_dataset = str(prov["target_dataset"])
    target_n_species = int(prov["target_n_species_classes"])
    target_top = list(prov["target_top_species_by_count"])
    target_well_known = list(prov["target_well_known_species"])
    target_n_seasons = int(prov["target_n_seasons"])
    target_site_pattern = str(prov["target_camera_site_pattern"])
    target_splits = list(prov["target_splits"])
    target_min_train_sites = int(prov.get("target_min_train_sites", 100))

    # Parse species_list.csv: rows of (species_name, count)
    species_text = (inputs_dir / "species_list.csv").read_text()
    species_rows = list(csv.reader(StringIO(species_text)))
    species_names = [r[0] for r in species_rows if r and r[0]]
    species_counts = {r[0]: int(r[1]) for r in species_rows if r and len(r) >= 2 and r[1].isdigit()}

    # Parse splits.json
    splits_data = json.loads((inputs_dir / "splits.json").read_text())
    splits_info = splits_data.get("info", {})
    splits = splits_data.get("splits", {})
    train_sites = list(splits.get("train", []))
    val_sites = list(splits.get("val", []))

    # External validation flags
    n_species_matches = len(species_names) == target_n_species
    top_species_present = all(s in species_names for s in target_top)
    well_known_species_present = all(s in species_names for s in target_well_known)
    has_empty_class = "empty" in species_names
    has_wildebeest = "wildebeest" in species_names
    splits_keys_match = set(splits.keys()) == set(target_splits)
    site_pattern = re.compile(target_site_pattern)
    train_sites_match_pattern = all(site_pattern.match(s) for s in train_sites)
    val_sites_match_pattern = all(site_pattern.match(s) for s in val_sites)
    n_train_sites_meets_min = len(train_sites) >= target_min_train_sites

    # Wildebeest count is the largest non-"empty" — the Serengeti
    # hosts the largest wildebeest population on earth (~1.5M)
    non_empty_top = max(((c, s) for s, c in species_counts.items() if s != "empty"),
                       default=(0, ""))
    wildebeest_is_top_non_empty = non_empty_top[1] == "wildebeest"

    all_validated = bool(
        n_species_matches and top_species_present
        and well_known_species_present and has_empty_class and has_wildebeest
        and splits_keys_match and train_sites_match_pattern
        and val_sites_match_pattern and n_train_sites_meets_min
        and wildebeest_is_top_non_empty
    )

    files = [_file_meta(inputs_dir / f) for f in ("species_list.csv", "splits.json")]

    return {
        "target": {
            "dataset":               target_dataset,
            "n_species_classes":     target_n_species,
            "top_species_by_count":  target_top,
            "well_known_species":    target_well_known,
            "n_seasons":             target_n_seasons,
            "splits":                target_splits,
        },
        "species": {
            "n_classes":           len(species_names),
            "names":               species_names,
            "counts":              species_counts,
            "top_5_by_count":      species_names[:5],
            "non_empty_top":       non_empty_top[1],
            "non_empty_top_count": non_empty_top[0],
        },
        "splits": {
            "info":           splits_info,
            "split_keys":     sorted(splits.keys()),
            "n_train_sites":  len(train_sites),
            "n_val_sites":    len(val_sites),
            "train_sample":   train_sites[:5],
            "val_sample":     val_sites[:5],
        },
        "files":          files,
        "captured_from":   prov.get("captured_from", ""),
        "captured_at_utc": prov.get("captured_at_utc", ""),
        "capture_method":  prov.get("capture_method", ""),
        "validation": {
            "all_validated":                  all_validated,
            "n_species_matches":              n_species_matches,
            "top_species_present":            top_species_present,
            "well_known_species_present":     well_known_species_present,
            "has_empty_class":                has_empty_class,
            "has_wildebeest":                 has_wildebeest,
            "splits_keys_match":              splits_keys_match,
            "train_sites_match_pattern":      train_sites_match_pattern,
            "val_sites_match_pattern":        val_sites_match_pattern,
            "n_train_sites_meets_min":        n_train_sites_meets_min,
            "wildebeest_is_top_non_empty":    wildebeest_is_top_non_empty,
            "n_files":                        len(files),
            "target_identifiers":             [target_dataset] + target_top + target_splits,
        },
    }
