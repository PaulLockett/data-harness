# case_001 — SpaceX HLS Option A contract (NASA, 80MSFC20C0034)

## What this case demonstrates

A real $3.02B Federal contract: NASA's Human Landing System (HLS) Option A
award to SpaceX, captured from `api.usaspending.gov` on 2026-04-27. The
case exercises:

- **JSON-API capture** without browser-harness, ZIPs, or scraping — pure
  REST.
- **External-fact-anchored predicates** — every load-bearing predicate
  is sourced from a citable, externally-published fact about the HLS
  contract (NASA records, SAM.gov UEI registry, USAspending data
  dictionary, SpaceX corporate address) so the case fails when the
  captured data drifts off the target, not just when the skill is broken.

## Provenance

Captured 2026-04-27 from
`https://api.usaspending.gov/api/v2/awards/CONT_AWD_80MSFC20C0034_8000_-NONE-_-NONE-/`.
The award was discovered by POSTing
`/api/v2/search/spending_by_award/` with
`recipient_search_text=["SPACE EXPLORATION TECHNOLOGIES"] +
agencies.NASA + award_type_codes=A/B/C/D + sort=Award Amount desc`.

## What's in `inputs/`

| File | Bytes | Notes |
|---|---|---|
| `_provenance.json` | ~2 KB | target spec + capture metadata |
| `award.json` | 8,549 | full USAspending award-detail JSON |

## What the award contains (verified at capture-time)

| Field | Value |
|---|---|
| `id` (USAspending internal) | 291816084 |
| `generated_unique_award_id` | `CONT_AWD_80MSFC20C0034_8000_-NONE-_-NONE-` |
| `piid` | 80MSFC20C0034 |
| `category` | contract |
| `type` | D (definitive contract) |
| `type_description` | DEFINITIVE CONTRACT |
| `total_obligation` | $3,018,254,542.85 |
| `date_signed` | 2020-05-13 |
| `period_of_performance.start_date` | 2020-05-13 |
| `period_of_performance.potential_end_date` | 2027-12-06 |
| `period_of_performance.last_modified_date` | 2026-04-09 |
| `recipient.recipient_name` | SPACE EXPLORATION TECHNOLOGIES CORP. |
| `recipient.recipient_uei` | C6M7C2FLKER5 |
| `awarding_agency.toptier_agency.name` | National Aeronautics and Space Administration |
| `place_of_performance.city` | HAWTHORNE |
| `place_of_performance.state_code` | CA |
| `description` (first 200 chars) | "WORK REQUIRED FOR THE DESIGN, DEVELOPMENT, MANUFACTURE, TEST, LAUNCH, DEMONSTRATION, AND ENGINEERING SUPPORT OF THE HUMAN LANDING SYSTEM (HLS) INTEGRATED LANDER." |

## External-source citations (predicate provenance)

| Predicate group | Source |
|---|---|
| Award `type` and `type_description` enums | **USAspending API data dictionary** (github.com/fedspendingtransparency/usaspending-api/wiki) — contract type codes A–G |
| `category` enum (`contract` / `grant` / `loan` / `direct payment` / `idv`) | **USAspending API data dictionary** — top-level award category enum |
| Required top-level keys (`id`, `generated_unique_award_id`, `category`, `type`, `total_obligation`, etc.) | **USAspending API award-detail schema** |
| PIID format `^80MSFC[0-9]{2}[A-Z][0-9]{4}$` | **NASA Procurement Information Circular** — Marshall Space Flight Center contracting-office prefix `80MSFC` followed by `<YY><CW><NNNN>` |
| `date_signed = 2020-05-13` and `period_of_performance.start_date = 2020-05-13` | **NASA HLS award notice** (the contract was signed May 13, 2020 under NextSTEP-2 BAA Appendix H; the SpaceX-only award was announced publicly 2021-04-16 after the Blue Origin protest period closed) |
| `total_obligation in [$2B, $5B]` | **NASA OIG report IG-22-007** (HLS funding analysis) — Option A initial value $2.89B; Option B added $1.15B; modifications since 2024 have brought obligated total above $3B |
| `recipient_name` regex `^SPACE EXPLORATION TECHNOLOGIES` | **SAM.gov entity registration** for Space Exploration Technologies Corp., the SpaceX legal entity |
| `recipient_uei in_set ["C6M7C2FLKER5"]` | **SAM.gov UEI registry** — public 12-character SpaceX UEI |
| `recipient_uei` regex `^[A-Z0-9]{12}$` | **SAM.gov UEI specification** — 12-character alphanumeric, replacing DUNS as of 2022 |
| `awarding_agency.toptier_name = "National Aeronautics and Space Administration"` | **USAspending agency reference table** — authoritative NASA toptier name |
| `place_of_performance.city in {HAWTHORNE, Hawthorne}`, `state_code = "CA"` | **SpaceX corporate address**: 1 Rocket Road, Hawthorne, CA 90250 (publicly published) |
| `description` mentions HUMAN LANDING SYSTEM / HLS / LANDER | **NASA HLS contract scope** — public PWS published with the award notice |
| Capture URL prefix `^https://api\.usaspending\.gov/api/v2/awards/` | **USAspending API URL pattern** (the documented public endpoint) |
| Identity values (target_award_id, target_piid, target_recipient_uei) | **Search inputs** declared in `_provenance.json` |

## Spoof matrix

| Mutation | Predicate that fails |
|---|---|
| `award.json` `recipient.recipient_uei` → "WRONGUEI12345" | `recipient.recipient_uei in_set ["C6M7C2FLKER5"]` fails first |
| `award.json` `date_signed` → "2099-01-01" | `award.date_signed in_set ["2020-05-13"]` fails |
| `award.json` `recipient.recipient_name` → "ACME DEFENSE INC." | `recipient.recipient_name` regex `^SPACE EXPLORATION TECHNOLOGIES` fails |
| `award.json` `awarding_agency.toptier_agency.name` → "Department of Defense" | `awarding_agency.toptier_name in_set [NASA]` fails; `validation.awarding_toptier_is_nasa` becomes false |
| `award.json` `total_obligation` → 50000 | `award.total_obligation in_range [2e9, 5e9]` fails |
| Truncate `award.json` to `{}` | top-key conformance + identity predicates fail; `validation.missing_top_keys max_size 0` fails |
| `_provenance.json` `target_recipient_uei` → "OTHER12345" | `target.recipient_uei in_set ["C6M7C2FLKER5"]` fails; `recipient_uei_match` becomes false |

## Why HLS / 80MSFC20C0034

- **Public, citable**: NASA's HLS competition outcome is one of the
  most-reported government contracts of the decade. Every external fact
  used as a predicate has a publicly-published source.
- **Stable identity**: `generated_unique_award_id` and `piid` are
  stable across USAspending refreshes (only `total_obligation`,
  `total_outlay`, and `last_modified_date` move with subsequent
  modifications).
- **Distinctive description**: "HUMAN LANDING SYSTEM" is unambiguous —
  no other public Federal contract uses this exact phrase as primary
  scope.
- **Single-recipient definitive contract**: no IDV/parent-child
  complexity to thread through the schema; case_002+ can introduce
  IDV-style awards as a separate exercise.

## Why USAspending

- **No auth, no scraping, no ZIPs.** Pure JSON REST API; the simplest
  capture path of any Phase 4 domain.
- **Data dictionary is publicly maintained.** Predicates anchored to
  enums and required-keys-lists from the USAspending API wiki are
  externally checkable without dependence on the captured response.
- **High-stakes data.** Federal-spending records are widely audited;
  a wrong capture fails public-facing fact checks.
