# Tasks: Detailed design, implementation and unit verification

**Input**: [spec](spec.md), [plan](plan.md), [research](research.md), [data model](data-model.md),
[verification contract](contracts/verification.md), [quickstart](quickstart.md).

**Prerequisites**: 008 reports (no accepted design); no protected collector (005 T009); no model
call. Local candidate toolchain only.

## Phase 1: Setup

- [X] T001 Record native verification rules, tags, template, checklist and warning-policy findings in `research.md`; keep references unchanged.
- [X] T002 Create `src/score_sw_fabric/verification/__init__.py` and the C++17 demo fixture (requirements, detailed design, sources, defect variant, GoogleTest tests).
- [X] T003 [P] Add `schemas/verification-*.schema.json` for profiles, requests and outputs.

## Phase 2: Foundational

- [X] T004 Implement `profiles/s-core-verification-v1.yaml`, `profiles/cpp17-gcc11-gtest-local-v1.yaml` and their validators in `profile.py`/`toolchain.py`, including toolchain identity verification (009-R02).
- [X] T005 [P] Add `tests/contract/test_verification_profile.py`.

## Phase 3: User Story 1 — Design traceability (P1) 🎯 MVP

- [X] T006 [US1] Implement `design.py` (template sections, diagram, tags, requirement map) (009-R01).
- [X] T007 [P] [US1] Add `tests/contract/test_verification_design.py` (AC009-01/02).

## Phase 4: User Story 2 — Build and test (P1)

- [X] T008 [US2] Implement `runner.py`: toolchain check, disposable build, GoogleTest XML parsing, metadata rules, requirement matrix, gcov import (009-R02–R05).
- [X] T009 [P] [US2] Add `tests/contract/test_verification_run.py` with real demo runs and metadata/toolchain fault cases (AC009-03–06).

## Phase 5: User Story 3 — Failure loop (P1)

- [X] T010 [US3] Implement history, routes, nondeterminism and escalation in `report.py` (009-R06/R07).
- [X] T011 [P] [US3] Add seeded-defect, fix, nondeterminism and escalation tests (AC009-07–10).

## Phase 6: User Story 4 — Milestone report (P1)

- [X] T012 [US4] Add 008 mitigation candidates, inspection packet and pending obligations to `report.py` (009-R08/R09).
- [X] T013 [P] [US4] Add `tests/contract/test_verification_report.py` (AC009-11–13).
- [X] T014 Add `score-fabric verify design|run|report` and `tests/contract/test_verification_cli.py` (009-R10).

## Phase 7: Polish and evidence

- [X] T015 Add env-gated `tests/integration/test_verification_native.py` and run it.
- [X] T016 Run all checks; record results in `acceptance.md`.
- [X] T017 Update `README.md`, `schemas/README.md`, requirement index, roadmap; write `docs/handoff/009-to-010.md`.
- [ ] T018 Owner review of verification and toolchain profiles and of the toolchain substitution (human-owned).
