# Tasks: Component safety feedback

**Input**: [spec](spec.md), [plan](plan.md), [research](research.md),
[data model](data-model.md), [safety contract](contracts/safety.md), [quickstart](quickstart.md).

**Prerequisites**: 004 RST scanner, 005 assessment replay (fixture domain only; T009 open), 007
role validation. No model call, native write or human decision is authorized.

**Format**: `[ID] [P?] [Story] Description`.

## Phase 1: Setup

- [X] T001 Record pinned native safety sources, catalogues, field rules and checklist in `specs/008-component-safety-feedback/research.md`; keep reference checkouts unchanged (008-R01).
- [X] T002 Create `src/score_sw_fabric/safety/__init__.py` and synthetic telemetry-guard fixtures under `tests/fixtures/safety/` (DEMO-02, DEMO-03).
- [X] T003 [P] Add version-1 schemas `schemas/safety-*.schema.json` for the profile, requests, report, packet and gate evaluation (008-R11).

## Phase 2: Foundational

- [X] T004 Implement `profiles/s-core-safety-analysis-v1.yaml` and its validator/extractor in `src/score_sw_fabric/safety/profile.py` (008-R01).
- [X] T005 Implement native need and list-table parsing in `src/score_sw_fabric/safety/native.py` using the 004 scanner (008-R02/R03).
- [X] T006 [P] Add `tests/contract/test_safety_profile.py` covering the profile, list-table parsing and native reading (008-R01–R03).

## Phase 3: User Story 1 — Coverage and item rules (P1) 🎯 MVP

- [X] T007 [US1] Implement coverage, item rules and mitigation states in `src/score_sw_fabric/safety/analysis.py` (008-R02/R03).
- [X] T008 [P] [US1] Add coverage/rule tests in `tests/contract/test_safety_analysis.py` (AC008-01–04).

## Phase 4: User Story 2 — Feedback and re-analysis (P1)

- [X] T009 [US2] Add feedback proposals, loop budget, AoU flag and baseline re-analysis to `analysis.py` (008-R04–R06).
- [X] T010 [P] [US2] Add DEMO-02 v1→v2 loop, re-analysis and escalation tests (AC008-05–08).

## Phase 5: User Story 3 — Promotion control and roles (P1)

- [X] T011 [US3] Add promotion classification with 007 agent checks and FMEA/DFA role separation checks; add `profiles/agent-role-{fmea,dfa}-analyst-draft-v1.yaml` (008-R07/R08).
- [X] T012 [P] [US3] Add promotion and role tests (AC008-09–11).

## Phase 6: User Story 4 — Packet and gates (P1)

- [X] T013 [US4] Implement the review packet in `src/score_sw_fabric/safety/packet.py` (008-R09).
- [X] T014 [US4] Implement gate evaluation with 005 replay binding in `src/score_sw_fabric/safety/gates.py` (008-R10).
- [X] T015 [P] [US4] Add packet and gate tests in `tests/contract/test_safety_gates.py`, including DEMO-03 and the evaluator positive path (AC008-12–15).
- [X] T016 Add `score-fabric safety check|packet|gate` and `tests/contract/test_safety_cli.py` (008-R11).

## Phase 7: Polish and evidence

- [X] T017 Add env-gated `tests/integration/test_safety_native.py` re-deriving catalogues from pinned checkouts and run it.
- [X] T018 Run all repository checks; record results and limitations in `specs/008-component-safety-feedback/acceptance.md`.
- [X] T019 Update `README.md`, `schemas/README.md`, `docs/backlog/requirements-index.md`, `docs/backlog/roadmap.md`, and write `docs/handoff/008-to-009.md`.
- [ ] T020 Owner review of the safety profile, the platform-allocation policy and FMEA/DFA role profiles (human-owned).

## Dependencies

T001–T003 → T004–T006 → US1 → US2 → US3 → US4 → T016 → T017–T019. T020 is outside agent authority.
