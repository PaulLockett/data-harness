# usaspending — federal award detail records

## What it does

Reads a single Federal award detail JSON captured from
`api.usaspending.gov/api/v2/awards/<id>/` and emits a canonical Award
record that combines target identity, recipient identity, awarding-agency
identity, period of performance, total obligation, and a validation
rollup. Predicates assert the captured award matches externally-known
facts about a public-record contract — the recipient's SAM.gov UEI, the
agency's authoritative name, the publicly-documented signing date, the
contract type code, and place of performance — so the case fails if the
captured JSON drifts off the target.

## Capture flow

1. **Pick a target award.** Search `api.usaspending.gov/api/v2/search/spending_by_award/`
   with a recipient filter to find a stable `generated_unique_award_id`.
   For case_001 this is the Human Landing System (HLS) Option A contract
   awarded to SpaceX by NASA, search-discoverable via
   `recipient_search_text=["SPACE EXPLORATION TECHNOLOGIES"] +
   awarding_agency=NASA`.
2. **Fetch the full award detail** with
   `GET https://api.usaspending.gov/api/v2/awards/<generated_unique_award_id>/`.
   Response is application/json; ~5–15 KB per award; no auth.
3. **Save the response** to `inputs/award.json` verbatim (no
   transformation at capture time). Provenance + target spec go to
   `inputs/_provenance.json`.

## Inputs

`fixtures/case_<NNN>/inputs/`:
- `_provenance.json` — declares `target_generated_unique_award_id`,
  `target_piid`, `target_recipient_search`, `target_recipient_name`,
  `target_recipient_uei`, capture URL, capture method, file list.
- `award.json` — full USAspending award-detail JSON.

## Output (skill.py contract)

`run(inputs_dir: Path) -> dict` returns:

```python
{
    "target":         {"generated_unique_award_id", "piid",
                       "recipient_search", "recipient_uei"},
    "award":          {
        "id":                          int,
        "generated_unique_award_id":   str,
        "piid":                        str,
        "category":                    str,    # "contract" | "grant" | ...
        "type":                        str,    # contract type code A/B/C/D
        "type_description":            str,
        "total_obligation":            float,
        "total_outlay":                float | None,
        "base_and_all_options_value":  float | None,
        "date_signed":                 "YYYY-MM-DD",
        "subaward_count":              int,
        "total_subaward_amount":       float | None,
        "description":                 str,
        "period_of_performance": {
            "start_date", "end_date", "potential_end_date",
            "last_modified_date",
        },
    },
    "recipient":      {
        "recipient_name", "recipient_uei", "recipient_unique_id",
        "parent_recipient_name", "parent_recipient_uei",
    },
    "awarding_agency": {"toptier_name", "subtier_name"},
    "place_of_performance": {
        "city", "state_code", "state_name", "country_code",
    },
    "files":          [{"file_path": "award.json", "size_bytes",
                        "sha256_prefix", "format": "json"}],
    "captured_from":   str,
    "captured_at_utc": str,
    "capture_method":  str,
    "validation": {
        "all_validated":                  bool,
        "award_id_match":                 bool,
        "piid_match":                     bool,
        "recipient_name_contains_target": bool,
        "recipient_uei_match":            bool,
        "awarding_toptier_is_nasa":       bool,    # case_001 specific
        "description_mentions_hls":       bool,    # case_001 specific
        "top_keys_match_api_spec":        bool,
        "missing_top_keys":               [str, ...],
        "n_files":                        int,
        "target_identifiers":             [str, ...],
    },
}
```

case_002+ for non-NASA, non-HLS targets re-tightens
`awarding_toptier_is_nasa` and `description_mentions_hls` to whatever
agency / scope is appropriate for the new target.

## Predicates (case_001)

43 predicates total. Provenance per group:

| Group | Predicate(s) | Source |
|---|---|---|
| **Identity** (4) | `target.generated_unique_award_id`, `target.piid`, `target.recipient_uei` `in_set`; `target` keyset | **Search input** declared in `_provenance.json` |
| **Award shape** (10) | `award.generated_unique_award_id` regex + `in_set`, `award.piid` regex `^80MSFC[0-9]{2}[A-Z][0-9]{4}$`, category/type/type_description in_set, total_obligation in_range, date_signed `in_set ["2020-05-13"]`, period start_date `in_set ["2020-05-13"]`, last_modified_date regex, description min_length | **External**: NASA contract numbering convention (PIID prefix `80MSFC` is Marshall Space Flight Center per NASA Procurement website); USAspending data dictionary award-type codes; HLS Option A signing date 2020-05-13 documented in NASA SBIR records and FedBizOpps award notice; HLS contract value range from NASA OIG and GAO public reports ($2.89B Option A + $1.15B Option B + mods). |
| **Recipient identity** (4) | `recipient_name` regex `^SPACE EXPLORATION TECHNOLOGIES`, `recipient_uei in_set ["C6M7C2FLKER5"]`, UEI regex `^[A-Z0-9]{12}$`, recipient keyset | **External**: SpaceX legal entity name and UEI registered on SAM.gov (UEI format is SAM.gov's 12-char alphanumeric standard, replacing DUNS as of 2022). |
| **Awarding agency** (2) | toptier_name `in_set ["National Aeronautics and Space Administration"]`, subtier_name regex | **External**: USAspending agency reference table — NASA's authoritative toptier name. |
| **Place of performance** (3) | city `in_set ["HAWTHORNE", "Hawthorne"]`, state_code `in_set ["CA"]`, state_name | **External**: SpaceX HQ at 1 Rocket Road, Hawthorne, CA — public corporate address. |
| **Per-file shape** (4 for_all + 1 size) | files min/max_size, file_path regex, sha256_prefix 16 hex, size_bytes range, format `in_set ["json"]` | **External (USAspending API contract)** + **captured-data structural** |
| **API top-key conformance** (2) | `validation.top_keys_match_api_spec in_set [true]`, `validation.missing_top_keys max_size 0` | **External**: USAspending data dictionary documents the required top-level keys for award-detail responses. |
| **Validation rollup** (8 booleans + 1 list) | `all_validated` and 7 sub-flags `in_set [true]`; `target_identifiers min_size 3` | **Captured-data-only / belt-and-suspenders** — these mirror skill flags but the strong external predicates above would catch failures even with these removed. |
| **Capture URL + root keyset** (2) | captured_from regex `^https://api\.usaspending\.gov/api/v2/awards/`; root key_set_includes | **External** — locks data to USAspending's API URL pattern |

The strong **external** predicates (~30 of 43) would catch a wrong capture
even if the skill's validation flags were broken; the **captured-data-only**
predicates (~13) are belt-and-suspenders.

## Future cases

- **case_002**: a different prime award by a different agency (e.g.
  Lockheed Martin / DOD F-35 sustainment, or Pfizer / DOD Operation
  Warp Speed). Re-tightens `awarding_toptier_is_nasa` and
  `description_mentions_hls` to the new target's authoritative
  toptier / scope. Verifies the external-fact predicate template
  generalizes off the SpaceX-specific identity.
- **case_003**: a grant rather than a contract (`category="grant"`,
  `type` in different code set, no PIID — uses `fain` instead).
  Exercises the categories the API serves beyond contracts.
- **case_004**: a sub-awarded contract (`subaward_count > 0`). The
  award detail then has `total_subaward_amount` populated; case adds
  predicates on the sub-award rollup.
- **case_005**: cross-domain composition with `disaggregate` /
  `distribution` — break agency obligations by recipient state to
  see whether USAspending data joins cleanly to the geographic
  helpers in the substrate.
