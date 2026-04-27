# soccernet — soccer-action-spotting schema metadata

## What it does

Reads the SoccerNet (Giancola et al. CVPR 2018; Cioppa et al. CVPR 2022)
action-spotting taxonomy as captured from the public sn-spotting GitHub
repo, and validates it against the published 17-class action vocabulary,
3-class team-affiliation, 3-class visibility, and 4-split list documented
in the survey paper + utils.py.

case_001 is a **schema-only fixture**: SoccerNet's video corpus + per-game
annotation JSONs are gated behind the soccer-net.org NDA-style download
flow with password authentication. v0 captures the public schema files
that anchor the predicate vocabulary; case_002+ may add real annotated
games when that auth path is wired.

## Capture flow

1. GET 4 files from raw.githubusercontent.com/SoccerNet/sn-spotting and
   /SoccerNet/SoccerNet:
   - `Annotation/config/classes.txt` — 17 action classes + "I don't know"
   - `Annotation/config/second_classes.txt` — 3 team-affiliation classes
   - `Annotation/config/third_classes.txt` — 3 visibility classes
   - `SoccerNet/utils.py` — canonical splits enum (train/valid/test/challenge)
2. Persist all 4 verbatim. Total ~6.4 KB.

## Output (skill.py contract)

`run(inputs_dir: Path) -> dict` returns target / schema (extracted from
the 4 files) / validation rollup with 6 sub-flags + per-file metadata.

## Predicates (case_001) — 33 total

| Group | Source |
|---|---|
| **Identity** (10): dataset SoccerNet-v2/v3, task in {action-spotting, replay-grounding, tracking, jersey-recognition}, n_primary_classes=17, team_classes=[na/home/away], visibility_classes=[na/visible/not_shown], splits=[train/valid/test/challenge], target keyset | **External**: SoccerNet survey paper Giancola et al. CVPR 2018 + sn-spotting README + Cioppa et al. CVPR 2022 |
| **Schema extracted** (8): primary_actions list (17 elements, each in_set of the documented 17 action types), team_classes for_all in_set, visibility_classes for_all in_set, n_team_classes=3, n_visibility_classes=3, utils_has_getListGames | **External**: SoccerNet/utils.py canonical Python module exposes getListGames + the 17-action enum is documented in the original CVPR 2018 paper (the "soccer events" taxonomy) |
| **Per-file shape** (4 for_all + 1) | Structural |
| **Validation rollup** (9) | Captured-data-only |
| **Capture URL + root keyset** (2) | **External** — raw.githubusercontent.com/SoccerNet/ URL pattern |

The strong **external** predicates (~22 of 33) catch a wrong capture even
with the validation booleans removed.

## Future cases

- **case_002**: a real game's annotation JSON once auth is wired
  (Labels-v2.json contains action-spot annotations).
- **case_003**: a tracking-task subset (sn-tracking) — different schema
  with player bounding boxes per frame.
- **case_004**: a video-clip thumbnail/frame for the substrate's image
  helpers — exercises `pdf_render` / `video_frames`.
