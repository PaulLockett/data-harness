# case_001 — SoccerNet action-spotting schema (sn-spotting v2/v3)

Schema-only fixture. The SoccerNet video corpus + per-game annotations
are auth-gated; case_001 captures only the public schema files from the
sn-spotting GitHub repo.

## Provenance

Captured 2026-04-27 from raw.githubusercontent.com/SoccerNet/sn-spotting
(3 config text files) and /SoccerNet/SoccerNet (utils.py). Total ~6.4 KB
across 4 files.

## What the captured schema contains (verified at capture-time)

- `classes.txt` — 18 lines: the 17 documented action classes (Penalty,
  Kick-off, Goal, Substitution, Offside, Shots on target, Shots off
  target, Clearance, Ball out of play, Throw-in, Foul, Indirect free-
  kick, Direct free-kick, Corner, Yellow card, Red card,
  Yellow->red card) plus "I don't know" placeholder.
- `second_classes.txt` — 3 lines: not applicable / home / away (team
  affiliation per action).
- `third_classes.txt` — 3 lines: not applicable / visible / not shown
  (visibility flag per action).
- `utils.py` — contains `getListGames(split, task, dataset)` which
  enumerates "train" / "valid" / "test" / "challenge" splits + the
  v1 → train+valid+test expansion documented in the SoccerNet API.

## External-source citations (predicate provenance)

| Predicate | Source |
|---|---|
| 17 action classes (Penalty, Kick-off, Goal, ...) | **Giancola et al. CVPR 2018** — "SoccerNet: A Scalable Dataset for Action Spotting in Soccer Videos" (the original taxonomy) |
| Team affiliation enum {not applicable, home, away} | **sn-spotting Annotation/config/second_classes.txt** + **Cioppa et al. CVPR 2022** "SoccerNet-v2" expansion |
| Visibility enum {not applicable, visible, not shown} | **sn-spotting Annotation/config/third_classes.txt** + **SoccerNet survey paper** §3.2 (visibility flag rationale) |
| Splits enum {train, valid, test, challenge} | **SoccerNet/utils.py getListGames** + **soccer-net.org dataset documentation** |
| Tasks enum {action-spotting, replay-grounding, tracking, jersey-recognition} | **soccer-net.org/tasks** task pages |

## Spoof matrix

| Mutation | Predicate that fails |
|---|---|
| `_provenance.json` `target_n_primary_classes` → 99 | `target.n_primary_classes in_set [17]` fails first |
| `_provenance.json` `target_team_classes` → ["red", "blue", "green"] | `target.team_classes[*] in_set` fails for_all |
| Truncate `classes.txt` to 5 lines | `schema.n_primary_actions in_set [17]` fails |
| Replace `utils.py` with empty file | `schema.utils_has_getListGames in_set [true]` fails |
