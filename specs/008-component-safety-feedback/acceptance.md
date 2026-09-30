# Increment 008 acceptance evidence

**Status:** Implemented for fixture demonstrations: 19/20 tasks complete. T020 (owner review of
the safety-analysis profile, its platform-allocation policy and the FMEA/DFA analyst roles) is
human-owned and open. This is fabric development evidence only. No safety analysis was accepted,
no human decision was recorded, no model was called, and no native file was written. 005 T009
(production authority) and 006 T025 remain open; 007 T022 owner review remains open.

## Fixed identities

| Item | Identity |
| --- | --- |
| Safety profile | `profiles/s-core-safety-analysis-v1.yaml` `1ec1e5988d6e1825a31747c0530050bd10fe145217ea2b963536abceefd0feb4` |
| FMEA analyst role (draft) | `profiles/agent-role-fmea-analyst-draft-v1.yaml` `6fc73ea6046232ee53c9bca4055c8f17ee22b4c38430dd0d811a57cfcece8339` |
| DFA analyst role (draft) | `profiles/agent-role-dfa-analyst-draft-v1.yaml` `88ec7857f348a16142cc331b71b8279d2a2e12a013ec106ae6d7fd6b40542784` |
| `process_description` | `98d1d5f42dad412a09a888ea25e59c62fa6371ce`: fault models `c24713773b71ed0c46ad5074a0753522fbc71c3f79a4df9d80b584b109e6b18`, DFA initiators `74a39c6fdc66697c9c8508137ccd57dad5792da997bc3fe5cde3fda3cc47bfaa`, process requirements `6f7a7c050272cce7c416f2b5c00866b996568dcf93bfe72ab3d0aaac86ec1e87` |
| `module_template` | `c4d4ad090c6584e58279f0e5d0b6894f7fc4cf0d`: component FMEA/DFA templates and FDR checklist (digests equal `upstream.lock.yaml`) |
| `docs-as-code` | `d5f3de608cdfc034952c57d40979c78d8cd35957`: `metamodel.yaml` `fe6a3b6af5ea69271e53c57e3a1694dc69d6ff3df16bd1505dc7242db9976290` |
| 005 fixture assessment used for replay | `tests/fixtures/assurance/passing-scope/out/assessment.json` (gate `component-verification`, `fixture_contract`) |

The profile holds 15 FMEA fault models, 35 DFA initiators (`SR` and `SC` platform scope; `CO`,
`SI`, `UI` component scope), the metamodel field rules, three native attribute rules and six
checklist items. `tests/integration/test_safety_native.py` re-derived all of them from the
read-only checkouts in `/tmp/s-core-foundation/references`, which stayed clean at their pins.

## Demonstrations (synthetic telemetry freshness guard fixtures)

**DEMO-02 — missing FMEA mitigation.** v1: all 15 fault models accounted for; `MF_01_02` late
sample is applicable with no mitigation and no issue → `MITIGATION_UNRESOLVED`
(`gd_req__saf_attr_mitigation_issue`), design acceptance blocked, one
`requirement_or_aou_review` feedback proposal. At iteration 3 the same gap escalates to a human.
v2 against v1: new `comp_req__telemetry_guard__stale_detection`, changed `evaluate`, new
`timeout_check`; all three affected items re-analysed; the late-sample item links the new
requirement and an issue and stays `sufficient: no`/`status: invalid` → `ready_for_design_review`.
The packet is requestable for design acceptance only; closure lists three mitigations without
evidence. With no verified decision the gates are `awaiting_decision` / `blocked`.

**DEMO-03 — DFA shared dependency.** Guard and monitor share the time source and timeout
configuration (`SI_01_02`). Without a platform allocation, all `SR`/`SC` initiators are
`ALLOCATION_UNRESOLVED`. With `doc__platform_dfa_fixture` (realizes `wp__platform_dfa`) they are
`allocated`; the concern item is `proposed` (issue linked, no mitigation) and blocks design
acceptance; the packet lists it under `dependency_concerns` with `disposition: pending_review`.

## Acceptance criteria

| AC | Evidence (`tests/contract/…`) | Result |
| --- | --- | --- |
| AC008-01 | v1/v2 coverage; coverage fault cases (`test_safety_analysis.py`) | Met |
| AC008-02 | Item rule cases naming `gd_req__saf_attr_*`; DFA link type | Met |
| AC008-03 | `missing` and `proposed` states unresolved | Met |
| AC008-04 | Platform allocation resolved/unresolved/wrong type | Met (fabric policy pending review) |
| AC008-05 | v1 feedback proposal; design prerequisites blocked | Met |
| AC008-06 | Changed/new element re-analysis; unchanged item and unanalysed new element cases; design decision on other bytes is `stale` | Met |
| AC008-07 | Escalation at iteration 3 | Met |
| AC008-08 | `AOU_TRANSFER_REVIEW` on the EX_01_01 AoU-only mitigation | Met (non-blocking flag) |
| AC008-09 | Agent-changed promotion → `UNTRUSTED_PROMOTION`, blocked | Met |
| AC008-10 | Unreviewed promotion recorded; closure needs a closure decision on the exact bytes | Met |
| AC008-11 | Separate, confined FMEA/DFA roles; overlap, scope, same-role and credential cases | Met |
| AC008-12 | Packet sections and both approval scopes (`test_safety_gates.py`) | Met |
| AC008-13 | No decision, other subject, not reproduced, production, non-pass, wrong gate; real 005 replay binds another subject; tampered and resealed forgeries refused | Met |
| AC008-14 | Accepted design (evaluator seam) leaves closure `MITIGATION_EVIDENCE_MISSING` | Met at evaluator; no eligible real decision exists |
| AC008-15 | DEMO-03 packet dependency concern | Met |

## Repository checks (2026-09-30)

| Command | Result |
| --- | --- |
| `uv run --frozen ruff check .` / `ruff format --check .` | Passed / 325 files formatted |
| `uv run --frozen mypy` | No issues in 79 source files |
| `uv run --frozen pytest -q tests/contract/test_safety_*.py` | 68 passed (profile 16, analysis 33, gates 15, CLI 4) |
| `SCORE_*_SOURCE=… uv run --frozen pytest -q tests/integration/test_safety_native.py` | 1 passed |
| Full suite with `SCORE_FABRO_BIN`, `SCORE_MCP_SERVERS_SOURCE` and the three `SCORE_*_SOURCE` selections | 1098 passed, 8 skipped (006 runtime ×6, 004 artifact native, 001 native export) |
| Full suite without selections | 3 failed by design (003 native tests require `SCORE_FABRO_BIN`), 10 skipped |
| `uv run --frozen python scripts/check_foundation.py` | PASS |
| `uv build --offline` | Built (digests recorded in the 008-to-009 handoff) |

## Limitations and open authority

- The positive design-accepted path is exercised only at the pure evaluator with
  verified-decision summaries; no 005 assessment exists for these files, and production decisions
  are ineligible while 005 T009 is open.
- Checks are structural and native-rule checks. Analysis adequacy, independence arguments and
  mitigation effectiveness remain human review questions; checklist answers stay unanswered.
- Component scope only; feature/platform propagation and `feat_saf_*` checks are later work.
- The fixture RST files were not built with the native `needs_json`/`docs_check` path.
- No FMEA/DFA drafting by a model was run; it needs cost authority and an approved role profile.
