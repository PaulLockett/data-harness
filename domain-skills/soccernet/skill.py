"""soccernet — read SoccerNet schema metadata files, build validated record.

Contract: run(inputs_dir: Path) -> dict.

Inputs (capture-time):
    inputs_dir/_provenance.json   target spec + capture metadata
    inputs_dir/classes.txt          17 action classes (+ "I don't know")
    inputs_dir/second_classes.txt   3 team-affiliation classes
    inputs_dir/third_classes.txt    3 visibility classes
    inputs_dir/utils.py             SoccerNet utils.py (contains canonical splits)

Output: a canonical SoccerNet-Schema record validated against the
documented action-spotting taxonomy.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


def _file_meta(p: Path) -> dict:
    raw = p.read_bytes()
    return {
        "file_path":     p.name,
        "size_bytes":    len(raw),
        "sha256_prefix": hashlib.sha256(raw).hexdigest()[:16],
    }


def _read_lines(p: Path) -> list[str]:
    return [ln.strip() for ln in p.read_text().splitlines() if ln.strip()]


def run(inputs_dir: Path) -> dict:
    inputs_dir = Path(inputs_dir)
    prov = json.loads((inputs_dir / "_provenance.json").read_text())

    target_dataset = str(prov.get("target_dataset", ""))
    target_task = str(prov.get("target_task", ""))
    target_n_primary = int(prov.get("target_n_primary_classes", 17))
    target_primary_subset = list(prov.get("target_primary_classes_subset", []))
    target_team_classes = list(prov.get("target_team_classes", []))
    target_visibility_classes = list(prov.get("target_visibility_classes", []))
    target_splits = list(prov.get("target_splits", []))

    primary = _read_lines(inputs_dir / "classes.txt")
    teams = _read_lines(inputs_dir / "second_classes.txt")
    visibility = _read_lines(inputs_dir / "third_classes.txt")

    utils_text = (inputs_dir / "utils.py").read_text()

    # External invariants from SoccerNet papers + utils.py:
    # - 17 action classes are documented in Giancola 2018 (CVPR Workshop)
    #   plus "I don't know" placeholder = 18 lines in classes.txt
    # - team affiliation: not applicable / home / away
    # - visibility: not applicable / visible / not shown
    # - canonical splits in utils.py: train / valid / test / challenge
    #   (with v1 expanding to train/valid/test)

    # Skill output: extract first 17 action classes (ignoring trailing
    # "I don't know" placeholder); the canonical 17-class action set.
    primary_actions = [c for c in primary if c != "I don't know"]

    # Validation
    n_action_classes_matches = len(primary_actions) == target_n_primary
    teams_match_target = teams == target_team_classes
    visibility_match_target = visibility == target_visibility_classes
    target_subset_in_actions = all(c in primary_actions for c in target_primary_subset)
    splits_in_utils = all(re.search(rf"['\"]?{re.escape(s)}['\"]?", utils_text) for s in target_splits)
    has_get_list_games = "getListGames" in utils_text

    all_validated = bool(
        n_action_classes_matches and teams_match_target
        and visibility_match_target and target_subset_in_actions
        and splits_in_utils and has_get_list_games
    )

    files = [_file_meta(inputs_dir / f) for f in
             ("classes.txt", "second_classes.txt", "third_classes.txt", "utils.py")]

    return {
        "target": {
            "dataset":              target_dataset,
            "task":                 target_task,
            "n_primary_classes":    target_n_primary,
            "team_classes":         target_team_classes,
            "visibility_classes":   target_visibility_classes,
            "splits":               target_splits,
        },
        "schema": {
            "primary_actions":         primary_actions,
            "n_primary_actions":       len(primary_actions),
            "all_primary_lines":       primary,
            "team_classes":            teams,
            "visibility_classes":      visibility,
            "n_team_classes":          len(teams),
            "n_visibility_classes":    len(visibility),
            "utils_has_getListGames":  has_get_list_games,
        },
        "files": files,
        "captured_from":   prov.get("captured_from", ""),
        "captured_at_utc": prov.get("captured_at_utc", ""),
        "capture_method":  prov.get("capture_method", ""),
        "validation": {
            "all_validated":              all_validated,
            "n_action_classes_matches":   n_action_classes_matches,
            "teams_match_target":         teams_match_target,
            "visibility_match_target":    visibility_match_target,
            "target_subset_in_actions":   target_subset_in_actions,
            "splits_in_utils":            splits_in_utils,
            "has_get_list_games":         has_get_list_games,
            "n_files":                    len(files),
            "target_identifiers":         [target_dataset, target_task] + target_splits,
        },
    }
