# meta-skills

Skills about how the agent works with the user — not how it works with data.

Where `interaction-skills/` covers data primitives (`glance`, `distribution`, `grain`, ...) and `domain-skills/` covers per-source extractions, this directory holds skills that govern the agent ↔ user relationship: bootstrapping the user profile, refining it over time, eventually reflecting on sessions.

## Skills

- **`interview/`** — first-run interview that bootstraps `~/.data-harness/USER.md` (the user's persistent profile). Run once when the harness is first set up; subsequent sessions read USER.md and update it as they learn more about how the user works.

## Why a separate family

Data verbs (`glance`, `validate`, `quantify`, `refute`) describe what the substrate does to bytes. Domain skills describe a specific source. Meta-skills describe the *relationship* the agent maintains with the user across sessions — they don't validate fixtures, they shape every other call by anchoring SOUL.md (the agent's constitution) and USER.md (the user's profile) into the substrate's working memory.

Keeping them distinct from `interaction-skills/` preserves the family's semantic discipline: an agent searching `interaction-skills/` for a data primitive shouldn't have to filter past the interview.
