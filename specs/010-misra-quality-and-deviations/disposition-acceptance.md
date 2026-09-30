# Draft/correction validation — bounded 010 US3 slice

2026-09-30. Implements scoped T049–T052, under [the exact contract](contracts/dispositions.md).
The user's `go` followed the proposed disposition draft and correction freshness step.
T020/T022 decision replay, CodeQL execution, coverage and human T032 remain pending.

## Behavior and retained observations

`quality disposition` binds a sealed draft to its exact original finding/native record,
frozen file, component and expected units. It retains rationale, impact, alternatives,
compensating references, expiry, review triggers, category declarations and native metadata.
Names/dates/statuses are unauthenticated. Deviation/false-positive/suppression proposals
stay pending or stale; unknown category policy and unreplayed decisions remain explicit.

A correction requires changed tracked source and unchanged component/file membership,
scope, profile, toolchain and configuration. The command runs the existing bounded local
adapter again, retaining all raw output. It independently checks the fresh baseline,
scope, phases, truncation, capability/check selection, extraction and original check absence
across the whole component. Imported output cannot establish a correction in this slice.
The conservative whole-file comparison does not infer AST correspondence.

History verifies every transport/self digest, subject and consecutive revision to the
root, retaining immutable links. All ancestor paths are protected against overwrite.
Changed current baseline stales previous corrected observations. Historical labels and
local clock timestamps never authenticate execution or engineering decisions.

Fresh local runs on synthetic defect/fix sources are retained below. These are genuine
tool executions with `local_unprotected_execution` origin, not CodeQL/decision fixtures.
Sources remain unchanged; adapter builds execute only in disposable copies.

| Adapter | Original run | Fresh corrected review |
| --- | --- | --- |
| Clang-Tidy 19.1.7 | [native run](evidence/disposition-clang-tidy-origin-run.json) | [review and native run](evidence/disposition-clang-tidy-corrected-review.json) |
| Cppcheck 2.7 | [native run](evidence/disposition-cppcheck-origin-run.json) | [review and native run](evidence/disposition-cppcheck-corrected-review.json) |
| GCC 11.4 ASan | [native run](evidence/disposition-asan-origin-run.json) | [review and native run](evidence/disposition-asan-corrected-review.json) |
| GCC 11.4 UBSan | [native run](evidence/disposition-ubsan-origin-run.json) | [review and native run](evidence/disposition-ubsan-corrected-review.json) |

Clang-Tidy additionally retains the linked [open draft](evidence/disposition-clang-tidy-pending-review.json)
and [stale observation](evidence/disposition-clang-tidy-stale-review.json). Each corrected
review contains the complete fresh execution, adequate extraction and zero native findings.
All four remain `not_eligible` with `engineering_readiness: not_evaluated`.

## Repository gates

Tests were written before implementation; the initial run failed collection because the
disposition module did not yet exist. An additional boundary test exposed expiry during
analysis; the validator now checks expiry again after execution and preserves a stale result.

- `uv sync --frozen`: passed, 18 packages checked.
- `uv run --frozen pytest --ignore=tests/integration/test_workflow_compiler_native.py`:
  **1233 passed, 11 skipped, 100.43 s**. Three existing 003 native Fabro compiler tests
  are excluded because the exact pinned runtime is not selected; their pins were preserved.
  The 11 existing external/native skips remain unmet proof, not readiness evidence.
- After the expiry fix, `uv run --frozen pytest tests/contract/test_quality_dispositions.py tests/integration/test_quality_dispositions.py -q`:
  **45 passed, 33.19 s** (40 contract and 5 integration cases).
- `uv run --frozen ruff check .`, `uv run --frozen ruff format --check .`,
  `uv run --frozen mypy`: passed; 100 source files type checked.
- `uv run --frozen python scripts/check_foundation.py`: passed, 64 unchanged FAB
  requirements and 19 dependency rows. The initial run found the pending validation
  document link; the document was added and the final link check passed.
- `uv build`: source distribution and wheel built successfully.
- Offline full Draft 2020-12 validation: all quality schemas valid; **32 examples and
  new evidence records** validated with resolved local schema references and formats.
- Both documented Clang-Tidy CLI examples executed: draft exits 1, fresh correction
  exits 0. Invalid inputs preserve prior output. Every native reference remains clean.

The 45 new tests include native imported contributors, nonexecuting drafts, unknown
category policy, names/dates, unreplayed decisions, expiry before/during analysis,
unchanged source, current policy/filter/scope drift, incomplete phases/extraction,
truncation, moved findings, malformed retained bytes, linked history and ancestor overwrite.
These gates validate implementation behavior, not engineering acceptance.

## Remaining engineering obligations

No 005 assessment was accepted or upgraded. The next implementation slice is independent
005 replay and exact disposition/category/scope/validity binding (T020/T022). The default
profile's category/mapping policy remains unknown; no allowable deviation set is invented.
005 T009 protected authority, 009 T018 profile review, CodeQL eligibility and source/build/
reporting prerequisites, guideline denominator, manual review and 010 T032 remain open.
No native status/source/suppression was changed and no reference repository was built in.
All four pinned reference repositories were read only and clean at their original commits.
No continuation to broader 010 or 011 is authorized by this validation record.
