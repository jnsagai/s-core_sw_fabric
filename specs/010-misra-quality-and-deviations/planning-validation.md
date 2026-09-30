# Increment 010 planning validation

2026-09-30. Planning and tool installation only; no adapter implementation or engineering acceptance.

## Spec Kit workflow

Pinned Spec Kit 1.0.12 on PATH with explicit SPECIFY_FEATURE_DIRECTORY for 010.
Spec, research, plan, data model, proposed contract, quickstart, checklist and tasks are present.
No extension hooks are registered. Two research agents were used as required by the plan skill.
Specification quality checklist: 16/16 checks; no clarification markers. Unknown external
prerequisites have defined blocked outcomes, so no user clarification was required.

## Read-only consistency analysis

The analyze prerequisite script succeeded. Semantic review checked the spec/plan/tasks against
all twelve constitution principles and the native authority/evidence boundaries. A deterministic
check verified sequential task IDs, explicit file paths and requirement references.

| Requirement | Task IDs |
| --- | --- |
| 010-R01 | T001,T005,T007,T009,T029,T032 |
| 010-R02 | T003,T004,T007,T008,T010,T029 |
| 010-R03 | T010,T011,T012,T015,T017 |
| 010-R04 | T014,T016,T018 |
| 010-R05 | T005,T023,T025,T027,T032 |
| 010-R06 | T007,T008,T010,T018,T019,T021 |
| 010-R07 | T019,T020,T021,T022,T027,T032 |
| 010-R08 | T014,T016,T019,T020,T022 |
| 010-R09 | T001,T005,T007,T009,T011,T012,T015,T017,T022,T023,T024,T025,T027,T032 |
| 010-R10 | T004,T006,T018,T020,T022,T024,T026,T027,T031 |
| 010-R11 | T001,T002,T003,T004,T006,T010,T013,T014,T018,T024,T026,T028,T029,T030,T031 |
| SC010-01 | T008 |
| SC010-02 | T014 |
| SC010-03 | T015 |
| SC010-04 | T023 |
| SC010-05 | T020 |

16 buildable requirements/success criteria; 32 tasks; 100% mapped; no unmapped tasks,
constitutional conflicts, blocking ambiguity or duplication findings. These are planning
observations, not tool confidence or engineering acceptance. Request schemas are a proposed
interface; T002 settles exact fields before validator tests/implementation.

Story counts: US1 7, US2 5, US3 4, US4 6; setup/foundation 6; validation/handoff 4.
Independent test criteria and four pairs of parallel test tasks are in [tasks](tasks.md).
MVP: US1 actual seeded/fixed complementary analysis with visible capability gaps.
All 32 implementation/review tasks remain unchecked; T032 is human-owned.

## Measured installation

- Clang-Tidy 19.1.7: official LLVM signed-index/package verification; native config accepted;
  real seeded null dereference produced native YAML and exit 1.
- CodeQL 2.21.4: official bundle SHA-256 verified; version and C++ extractor probes succeeded.
- MISRA pack 2.61.0: official archive SHA-256 verified; additional-pack resolution succeeded.
  Build metadata commit differs from inspected source commit; reconciliation remains unresolved.

See [installation](evidence/tool-installation.json), [Clang-Tidy smoke](evidence/clang-tidy-install-smoke.json)
and [pack resolution](evidence/codeql-packs-resolved.json). No CodeQL analysis was performed.

## Open authority and prerequisites

009 T018 owner review and 005 T009 protected authority remain open. Native guideline CSV is absent;
project applicability/categories, CodeQL eligible use, source/build relationship, compatible
report execution and genuine extraction/report evidence remain required. Local tools, fixture
contracts and successful checks cannot satisfy these external decisions or compliance claims.

Next action: implement T001–T006 when authorized, then US1. No automatic 011 continuation.

## Repository validation

- `uv sync --frozen`: passed, 18 packages checked.
- `uv run --frozen ruff check .`: passed.
- `uv run --frozen ruff format --check .`: passed, 359 files already formatted.
- `uv run --frozen mypy`: passed, 84 source files.
- `uv run --frozen python scripts/check_foundation.py`: passed after preserving plain numeric
  increment cells in the FAB index; 64 unchanged requirements, 19 dependency rows, local links.
- `uv build`: passed, sdist and wheel generated.
- `uv run --frozen pytest --ignore=tests/integration/test_fabro_native.py`: 1102 passed,
  11 skipped, 3 failed in 55.08 seconds. The ignored path does not exist, so all 1116 current
  tests were collected. All three failures are the existing workflow compiler native scenarios:
  `SCORE_FABRO_BIN` was unset. This run does not satisfy pinned native Fabro acceptance;
  skips do not satisfy their native acceptance obligations. No Python implementation changed.
- All three installation evidence JSON files parse; selected reference repositories remain clean
  at the researched commits; `git diff --check` passed.

Validation above covers repository/tool installation checks only. All 010 implementation and
engineering acceptance tasks remain open.
