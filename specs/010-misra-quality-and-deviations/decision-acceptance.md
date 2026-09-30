# Independent disposition replay validation — bounded 010 US3 slice

2026-09-30. The user's `go` followed independent 005 replay for disposition drafts.
Implements T020/T022 and scoped T053–T056 under [the exact contract](contracts/decisions.md).
This is an implementation validation record; authorized engineering acceptance is pending.

## Implemented behavior

`quality decision-subject` prepares a deterministic sealed binding from a validated draft,
original native finding/provenance, every frozen source file, current tool/config/profile/
assets and an explicitly supplied category policy. It refuses correction execution requests;
preparation runs no analyzer. Category permission requires exact native check/tool/category,
kind, component, complete translation-unit set and single tracked file. Null/missing/unknown
category policy, prohibited categories and broader suppressions block. The default candidate
profile and its unknown mapping/adoption state are unchanged.

`quality decision` independently reproduces selected 005 assessments from originals and an
independently selected fixture trust context. A selected subject must contain exact canonical
binding bytes, every selected source hash and policy-source bytes in its verified file closure.
The dedicated gate, exact scope/obligations and required human predicates must match. A gate
pass without an eligible signed fixture decision cannot accept a proposal.

The command reevaluates the complete 005 gate at current declared fixture as-of, including
shorter evidence lifetimes, then reclassifies signed decisions for role, actor, authority,
independence, conditions, key/role validity, revocation and decision expiry/maximum age.
It reconciles withdrawals, conflicts and supersession and rejects cross-payload receipt reuse.
Inputs are refrozen after replay; guarded atomic publication protects selected controls,
source/config files and all linked review ancestors. Malformed/unsafe input preserves prior
output. Controls/policy, individual/aggregate records and signed-history counts are bounded.

Existing draft/correction version 1 records are preserved. `accepted_fixture` is a separate
decision result; no native status or suppression is changed. Production always blocks while
005 T009 protected authority is unavailable. Every result remains `not_eligible` with
`engineering_readiness: not_evaluated`; no signer, model call or automatic approval is added.

## Retained examples and fixture proof

The [checked-in positive fixture](../../tests/fixtures/quality/dispositions/decision-replay/README.md)
retains binding, independently reproducible 005 assessment and current result. It extends
existing synthetic 004/005 source closure and uses the existing public test key and synthetic
actor/authority IDs. The invented `fixture_allowed` category and December 2026 times are test
data, not adopted MISRA policy or real human acceptance. Original fixture IDs/statuses and
native provenance are preserved. Replay is portable after local source paths disappear.

Actual blocked examples select the existing local Clang-Tidy source/run plus a new deviation
proposal with unknown category and no adopted policy. Both commands exit 1 as intended:

```bash
uv run --frozen score-fabric quality decision-subject --request examples/quality/decision-subject.yaml --out /tmp/quality-010-decision-binding.json --json
uv run --frozen score-fabric quality decision --request examples/quality/decision-production.yaml --out /tmp/quality-010-decision-production.json --json
```

Fixture positive CLI, expiry, production refusal, overwritten-input refusal and source deletion
journeys are automated. Names/dates, self-author decisions, wrong roles/authority, conditions,
reject/request-changes/withdraw, historical pass with revoked authority, changed binding/source/
config/tool/suite, incomplete closure and overly broad scope remain unresolved.

## Repository gates

Tests preceded implementation: the first run failed collection because the decision module
did not yet exist. Focused tests then exposed policy blocker precedence; category blockers
now retain `blocked` even when the old assessment also belongs to a changed subject.
Final review added regressions for trust-context drift during replay and preservation
of each context's validity findings when the same signed decision is selected twice.

- `uv sync --frozen`: passed; 18 packages checked, no dependency changes.
- `uv run --frozen pytest --ignore=tests/integration/test_workflow_compiler_native.py -q`:
  **1287 passed, 11 skipped, 160.76 s**. The final 53 new decision cases comprise 51 contract
  and 2 integration cases. Three existing 003 native Fabro compiler tests remain excluded
  because the exact pinned runtime is not selected; their pins were preserved. The 11
  external/native skips remain unmet proof, never readiness evidence.
- After the final publication/context checks, `uv run --frozen pytest tests/contract/test_quality_decisions.py tests/integration/test_quality_decisions.py -q`: **53 passed, 60.16 s**.
- `uv run --frozen ruff check .`, `uv run --frozen ruff format --check .` and
  `uv run --frozen mypy`: passed; 102 source files type checked.
- `uv run --frozen python scripts/check_foundation.py`: passed; 64 unchanged FAB
  requirements, 19 dependency rows, locks/skills and local links checked.
- `uv build`: source distribution and wheel built successfully.
- Offline Draft 2020-12 checks: all quality schemas valid; **61 example/evidence/fixture
  records** validated with local reference resolution and format checks.
- Both documented blocked CLI examples executed with exit 1. Fixture CLI exit 0,
  subsequent expiry/production exit 1, malformed/unsafe exit 2 and portable independent
  005 replay are tested. Input overwrite refusals preserve original bytes.
- All four native reference repositories remain clean at their original commits:
  S-CORE `e2373d822fc2f6e9a3f8a0538904f3faa39309ea`, C++ policies
  `9bcfe8296038569a0ff7627fb8ce7a189018a7b3`, time
  `3723ce687e4abc7d6cb4c0efdbbd30455ed7c303`, Coding Standards
  `06dc6bc32b05152fbe94dbf341a3e854574c9df5`.

Completed task accounting: 56 total; 31 complete (24 scoped, 5 US2 and T020/T022),
25 original tasks open. Human-owned T032 remains unchecked.

## Remaining obligations

The next useful bounded implementation is guideline coverage (T023/T025), with an explicit
unknown denominator and source-bound applicability/mechanisms/manual obligations. Packet and
compliance evaluation (T024/T026–T028), broader T019/T021, CodeQL execution and source/build/
reporting reconciliation remain open. 005 T009, 009 T018 and human 010 T032 require authority;
agents cannot check them off. Reference repositories remain read only and are never built in.
This validation does not authorize another slice, 011, publishing, merging or deployment.
