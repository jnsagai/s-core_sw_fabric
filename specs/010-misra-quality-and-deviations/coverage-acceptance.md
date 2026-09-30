# Guideline coverage validation — bounded 010 US4 slice

2026-09-30. The user's `go` followed the guideline coverage matrix. Implements T023/T025
and T057–T060 under [the exact contract](contracts/coverage.md), including read-only
`quality coverage`. Packet/compliance work and engineering acceptance remain pending.
The Spec Kit requirements checklist is complete (16/16); no reviewer marker changed.

## Measured behavior

Current source/component/files/expected units and declared tool/config/pack/suite identities
use the existing native-import baseline reader, factored into a shared freeze function.
Existing import behavior remains unchanged. The supplied manifest retains source refs,
category, applicability/rationale, expected IDs, mechanisms/automation/limitations and raw/manual
evidence expectations. Source JSON contains IDs/license/notices/status only. Selected bytes and
linked IDs are verified; semantic adoption remains explicitly unverified.

Unknown denominator stays null even with clean tools. Every declared ID generates a cell;
missing rows remain unknown. Manual/audit/partial mechanisms and manual evidence stay pending.
Unsupported/default-disabled checks and unreviewed exclusions remain visible, retaining the
denominator. Matching findings, including suppressed and historical contributors, stay open.
Native suppression/status/names cannot erase obligations or authenticate decisions.

Selected imports reproduce exactly from originals and independent extraction checks. Different
source/profile/component/files/units/tool/config/pack/suite identities cannot support current
clean use. Structural automatic coverage needs exact check selection in a matching adequate
retained local run; Clang-Tidy declarations must match original probe bytes. Every required raw
artifact must be present and untruncated. Primary MISRA execution, manual review, tool confidence
and protected authority remain unresolved regardless of that observation.

The matrix retains original guideline-source records, profiles/notices, full reproduced imports,
all current cells/counts/reasons and the prior manifest with changed applicability/mappings/
scope/source selections. Publication protects all inputs/source roots and rechecks controls,
native originals and current frozen bytes. Bounds cover controls/sources, rows/mechanisms/findings
and aggregate records; no silent truncation is used. Invalid input preserves prior output.

No analyzer, model or signer runs during measurement. Covered rows are structural observations;
all matrices keep zero accepted claims, ineligible origin and unevaluated engineering readiness.
The default profile remains unmapped and pending owner review. Target source hashes are retained;
full portable target source bytes and independent packet/compliance replay belong to the next
slice. No native content or suppression is changed.

## Evidence and command

- [Unknown native denominator](evidence/coverage-unknown.json): no invented guideline IDs/count.
- [Local measurement](evidence/coverage-local.json): genuine Clang-Tidy clean/probe output with
  synthetic guideline associations and separate pending manual review. The
  [fixture explanation](../../tests/fixtures/quality/coverage/README.md) distinguishes supplied
  declarations from native measurements; neither establishes adopted MISRA applicability.

```bash
uv run --frozen score-fabric quality coverage --request examples/quality/coverage-unknown.yaml --out /tmp/quality-010-coverage.json --json
```

The example was executed and exits 1 with an incomplete matrix and unknown denominator.
Primary execution, mapping, manual, confidence and authority gaps remain explicit.

## Repository gates

Tests preceded implementation; initial collection failed because the coverage module did not
exist. Final review added missing-required-artifact and historical-source overwrite regressions
after the broad suite.
- `uv sync --frozen`: passed; 18 packages checked, no dependency changes.
- `uv run --frozen pytest --ignore=tests/integration/test_workflow_compiler_native.py -q`:
  **1324 passed, 11 skipped, 164.42 s**. This broad run includes the shared baseline
  reader refactor and 37 coverage cases. Three existing 003 native Fabro compiler tests
  remain excluded because their exact pinned runtime is not selected; pins were preserved.
  The 11 existing external/native skips remain unmet proof, not readiness evidence.
- After the final required-artifact and historical-source guards, `uv run --frozen pytest tests/contract/test_quality_coverage.py tests/integration/test_quality_coverage.py -q`:
  **39 passed, 3.59 s** (36 contract and 3 integration cases). This delta verifies missing
  required original artifacts cannot be covered and historical sources cannot be overwritten,
  while genuine automatic observations remain.
- `uv run --frozen ruff check .`, `uv run --frozen ruff format --check .` and
  `uv run --frozen mypy`: passed; 104 source files type checked.
- `uv run --frozen python scripts/check_foundation.py`: passed; 64 unchanged FAB
  requirements, 19 dependency rows, locks/skills and local links checked.
- `uv build`: source distribution and wheel built successfully.
- Offline Draft 2020-12 validation: all quality schemas valid; **67 example/evidence/fixture
  records** validated with local schema references and format checks.
- The documented unknown-denominator CLI example exits 1. Tests check deterministic bytes,
  required observations, source/suite/config drift, suppressed findings, missing mapping,
  unknown/excluded applicability, partial/manual/default-disabled audit mechanisms, filters,
  original-input drift and exit-2 prior-output preservation.
- All four native reference repositories remain clean at their original commits: S-CORE
  `e2373d822fc2f6e9a3f8a0538904f3faa39309ea`, C++ policies
  `9bcfe8296038569a0ff7627fb8ce7a189018a7b3`, time
  `3723ce687e4abc7d6cb4c0efdbbd30455ed7c303`, Coding Standards
  `06dc6bc32b05152fbe94dbf341a3e854574c9df5`.

Task accounting: 60 total; 37 complete (28 scoped, 5 US2, 2 US3 and 2 US4),
23 original tasks open. Human-owned T032 remains unchecked.

## Remaining scope

T024/T026 packet and T027/T028 compliance evaluation remain open, with broader T019/T021
and CodeQL source/build/reporting/eligible-use prerequisites. Human T032, 009 T018 and 005 T009
are not checked off. No mapping, category or exclusion was adopted. This validation proposes
the next step without authorizing another slice or 011.
