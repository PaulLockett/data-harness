---
description: First-run interview that bootstraps ~/.data-harness/USER.md — a deep model of who the user is, how they work, and what they're building. Run once at install time; later sessions read USER.md instead of asking again, and update it when they learn something new.
user-invocable: true
---

# data-harness interview

A short, focused interview that creates `~/.data-harness/USER.md` — the user's persistent profile across data-harness sessions. Run this once when the harness is first set up.

## Why USER.md

The data-harness substrate is capable across many domains and many hardware regimes. The same skill code runs differently for an astronomer on a workstation than for a policy analyst on a laptop. USER.md captures the parts of who the user is that should shape every future session — communication style, technical depth, domains they work in, what they care about — so I don't re-orient myself every time.

USER.md is **per-user, per-machine, never in the repo.** It lives at `~/.data-harness/USER.md` and only that user sees it. SOUL.md is the agent's constitution and ships with the project; USER.md is the user's profile and stays on their machine.

## Pre-interview context (required)

Before asking any questions:

1. Read `SOUL.md` from the repo root. Its voice and frame govern how I talk during the interview — calm rigor, no throat-clearing, real questions, specifics over generalities, praise effort and strategy not innate ability. The interview is one of the highest-stakes places to get the voice right.
2. Read `~/.data-harness/USER.md` if it exists. Skim what's already known.
3. If USER.md exists, print a short summary back to the user: "Here's what I already know about you. I'd like to fill in [gaps] / confirm [uncertain bits]." Then tailor the interview to skip what's covered.
4. If USER.md doesn't exist, create it with this header:

```markdown
# USER.md

*Bootstrapped via the data-harness interview on YYYY-MM-DD. This file grows during normal sessions as I learn more about how you work.*
```

## Guardrails

- Focus on stable, cross-session traits and preferences — not project-specific details that will change next month.
- Avoid sensitive data: API keys, real credentials, personal addresses, anyone else's information.
- Ask one question at a time. Wait for the answer before asking the next.
- Take the answer at face value if it has any actionable signal. Only follow up when an answer is too abstract to write a validatable section from — and even then, ask one concrete question ("what was the most recent example?") to extract a pattern. Don't educate the user on what good answers look like.
- If the user declines to answer, skip and move on.
- Never re-ask what USER.md already covers; refine instead.
- No throat-clearing. No "Great question." Start where it matters.

## Interview flow

Ask in order. The first three questions gate setup actions — once they're answered, **kick off background work and keep the conversation going** so downloads finish during the interview rather than after it. Skip any question the existing USER.md already answers; deepen any that look thin.

### About your environment and what the agent can reach

1. **Hardware regime and runtime ceiling** — What does your machine look like? (You can also defer to `dh caps`.) How much of it can the harness use at a time while running? (Default: 40%, with 20% reserved for you.)
2. **Storage budget** — How much disk can the harness keep at rest for fixtures, model weights, and cassettes? (Default: 20 GB.) If you want a tighter or looser cap, say so now.
3. **Data sources you'll grant access to** — Public APIs are open by default. What private sources will you let the agent reach? Your own databases, internal record stores, OAuth services, file dumps the agent doesn't have without you. Name each one — we'll record each as a pending entry the user can fulfill on their own schedule.

### Kick off setup in parallel (after Q1–Q3)

Once the environment answers are in, start the work the storage budget and hardware regime have unblocked. Don't wait for the rest of the interview. The remaining eight questions should fill the time the downloads need; by wrap-up, setup should be complete or near-complete.

Concrete actions to spawn (each in a backgrounded shell):

- `mkdir -p ~/.data-harness/` — ensure the scratch directory exists.
- `dh caps` — refresh the daemon's capabilities snapshot against the user's stated ceiling.
- `dh models pull` — local model weights sized to the storage budget. Skip if the user is hosted-API-only.
- `make smoke` — substrate sanity check.

While they run, ask Q4–Q11. Check progress in the natural pauses between user answers — not mid-question. If a download finishes mid-conversation, you can briefly note it ("model weights done, proceeding") without breaking stride. If something's still running at wrap-up, name it.

### About what you're building

4. **Domains** — What kinds of data are you working with? (Public datasets, internal records, multimodal scrolls, peer-reviewed archives, regulator portals, ...)
5. **Done** — When you finish a piece of work, how do you know it's actually done? What's the test in your head?
6. **Failure response** — When something doesn't work the way you wanted, what's the right next move? Retry, escalate to you, find an alternative path, pause and ask.

### About you and how you work

7. **Role and background** — What do you do day-to-day? What discipline did you come from?
8. **Communication style** — Concise answers, narrative explanations, or step-by-step? Bullet-friendly or prose?
9. **Technical depth** — What level should I assume? Domain expert / comfortable generalist / learning-as-we-go.
10. **Collaboration style** — Should I make changes directly, propose options first, or ask before edits?
11. **Triggers** — Is there a way of working — common in agents — that you specifically don't want me doing? (Examples: throat-clearing, asking permission for trivial edits, lecturing about mindset, soft-pedaling hard truths, hand-waving when uncertain.)

## Saving conclusions

After each answer, append a section to USER.md immediately. Don't batch.

Format: a heading + one tight paragraph. Specific over vague. Each section should be **operational** — not just "what is true about the user" but "how I should act on it."

```markdown
## Communication style

Prefers narrative explanations over bullet lists; sees narrative as a verification mechanism — early misalignment surfaces faster in prose than in lists. Apply: when explaining something non-trivial, lead with prose. Use bullets only for lists of discrete items where the order or count matters.
```

The "Apply:" half is what makes the conclusion useful in future sessions. A bare fact ("prefers narrative") doesn't tell future-me what to do with it. A conclusion paired with an application rule does.

## Saving pending data-source entries

Q11 may produce one or more private data sources the user is willing to grant access to. For each, append a section to `~/.data-harness/data-sources.md` immediately — don't batch, and don't collect credentials during the interview.

If `~/.data-harness/data-sources.md` doesn't exist when the first private source comes up, create it with this header:

```markdown
# data-sources.md

*Tracks private data sources the user has granted (or committed to grant) access to. Lifecycle: `pending` (committed, no credentials yet) → `configured` (credentials present, untested) → `tested` (connection verified, helper built). Credentials live in `.env` or a secret store — never here.*
```

Each source becomes a section:

```markdown
## <name the user gave>

- **Type**: postgres / rest API / file dump / OAuth service / unclear
- **Provides**: <what the user said it has>
- **Status**: pending
- **Needs**: <connection string / API key / OAuth flow / file path — whatever the user said would be required>
- **Use case**: <which of the user's tasks this serves, if mentioned>
```

Pending entries are a written commitment, not a credential request. After the interview, a follow-up session reads the pending entries and builds a helper for each — usually a thin function added to `helpers.py`, sometimes a new domain skill if the source is rich enough to warrant one. Credentials go in `.env` or the user's own secret store; data-sources.md only ever contains the metadata.

## Wrap-up

When the interview is done:

1. Print the new USER.md sections back to the user.
2. If any pending data-source entries were created, print those too — the user should see exactly what they committed to providing.
3. **Confirm setup status.** Background pulls finished? Daemon warm? Capabilities snapshot fresh? Tell the user where things stand. If something's still running, name it and roughly how much longer — don't end the interview pretending setup is done when it isn't.
4. Ask: "Anything wrong or missing?"
5. Make at most one round of corrections; save them.
6. Tell the user: "USER.md will keep growing during normal sessions — when I notice something stable about how you work that isn't already there, I'll add it; when behavior contradicts what's there, I'll edit rather than append. data-sources.md only changes when you grant new access or I move a pending entry forward as we get a source connected and tested."

## Updating these files after the interview

This skill bootstraps both files. Future sessions are responsible for keeping them current.

**USER.md** — append when you learn something new and stable about how the user works (a one-off correction during one task is noise; a pattern repeating across tasks is signal). Edit when behavior contradicts what's there; don't let stale duplicates accumulate. **Compress when sections sprawl** — once a section grows past a tight paragraph (six or seven sentences), summarize it back to one; preserve the rule, drop the redundant examples. When in doubt, ask: "I noticed you do X consistently — should I add that to USER.md?"

**data-sources.md** — entries move forward (`pending` → `configured` → `tested`) as the user provides credentials and helpers get built. Append a new pending entry when the user grants access to a private source mid-session, the same way the interview does. Never store credentials here.
