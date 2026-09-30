# Tasks: Fabro runtime integration

**Input**: [spec](spec.md), [plan](plan.md), [research](research.md),
[data model](data-model.md), [runtime contract](contracts/runtime.md), [quickstart](quickstart.md).

**Prerequisites**: Sealed 003 package and 005 fixture-domain assurance contract. The pinned
Fabro candidate has validator evidence only. Production trust-root and owner-controlled
collector/decision services remain open under 005 T009; no task here grants those authorities.

**Tests**: Story-specific contract and disposable native integration tests are required by
AC006-01–13. Native tests must use a command-only disposable environment with no paid model call.

**Format**: `[ID] [P?] [Story] Description`. Every checklist item below starts unchecked.

## Phase 1: Setup

**Purpose**: Establish an exact candidate capability record without modifying reference sources.

- [X] T001 Inspect pinned Fabro commit and API in `upstream.lock.yaml`, build or reuse a disposable copy, and record the candidate source/executable identity plus source-derived register/run/events/questions/checkpoint/cancel/export routes in `specs/006-fabro-runtime-integration/acceptance.md`; mark live capabilities unverified (006-R12).
- [X] T002 Create `src/score_sw_fabric/runtime/__init__.py` and fixture layout under `tests/fixtures/runtime/`, preserving the 003 package and 005 fixture source bytes (006-R01/R02).
- [X] T003 [P] Add version-1 JSON schemas for exact intent, binding and export envelopes in `schemas/runtime-intent.schema.json`, `schemas/runtime-binding.schema.json`, and `schemas/runtime-export.schema.json`, including bounded strings/arrays/bytes and explicit unknown-state enums (006-R03/R04/R09/R11).

**Checkpoint**: Candidate capability and data-envelope boundaries are inspectable; no production runtime authority is implied.

---

## Phase 2: Foundational contracts

**Purpose**: Shared guarded inputs and native transport before any effectful story.

- [X] T004 Add strict version-1 models, canonical digests, exact field validation, bounded diagnostics and guarded atomic publication in `src/score_sw_fabric/runtime/models.py`; reject unknown versions/fields and prior-output overlap (006-R11).
- [X] T005 [P] Add a typed selected-runtime profile and bounded native HTTP client in `src/score_sw_fabric/runtime/client.py`; verify selected commit/executable/API/auth capability, constrain URL/credentials/timeouts/pages/bytes, and expose only demonstrated lifecycle operations (006-R01/R12).
- [X] T006 [P] Add contract tests in `tests/contract/test_runtime_models.py` for every required field, unknown version/enum, limits, path/alias safety, secret redaction and interrupted output replacement (006-R11).
- [ ] T007 Verify the selected candidate profile and all source-file identities against a disposable server, probe actual register/run/events/questions/checkpoint/cancel/export operations without a paid model call, record exact native response shapes in `specs/006-fabro-runtime-integration/acceptance.md`, and revise `specs/006-fabro-runtime-integration/contracts/runtime.md` where live behavior differs; do not claim owner production selection (006-R12).

**Checkpoint**: Malformed inputs and unsupported runtime operations fail before registration or run creation.

---

## Phase 3: User Story 1 — Register and start a closed workflow (Priority: P1) 🎯 MVP

**Goal**: Project one sealed 003 package into an exact native version and start at most one run per safely known intent.

**Independent Test**: A disposable command-only package registers/starts; a changed file is refused; a lost create response yields no automatic duplicate.

### Tests for User Story 1

- [ ] T008 [P] [US1] Add projection and native-wire limit tests in `tests/contract/test_runtime_projection.py` for 003 `workflow.toml` versus Fabro `workflow.fabro`, exact file map, empty child map, 512-file/512-KiB-per-file/2-MiB-wire maxima, symlinks, extra/missing refs and original 003 bytes (AC006-01/03).
- [ ] T009 [P] [US1] Add intent ambiguity, repeat, concurrent caller, known-run start-conflict and atomic-output tests in `tests/contract/test_runtime_intents.py`; a label match must not be treated as server uniqueness (AC006-02/03).
- [X] T010 [US1] Add disposable native registration/create/start integration test in `tests/integration/test_runtime_fabro.py` with exact version/run IDs and zero paid model calls; skip only with a documented absent selected capability (AC006-01/02).

### Implementation for User Story 1

- [X] T011 [US1] Implement `src/score_sw_fabric/runtime/projection.py` to revalidate 003 closure, retain the sealed package, derive `{entrypoint: workflow.fabro, files, workflow_dependencies: {}}`, enforce both 003 and native wire limits, and bind source/wire digests (006-R02/R03).
- [X] T012 [US1] Implement `src/score_sw_fabric/runtime/ledger.py` with durable `prepared|create_in_flight|run_known|reconciliation_required` intent states and per-intent serialization; never resend an uncertain create or infer uniqueness from labels (006-R04).
- [X] T013 [US1] Implement register/create/start transport in `src/score_sw_fabric/runtime/client.py`, persisting native version and run IDs before the next effect; inspect known-run status before start retry (006-R01/R03/R04).
- [ ] T014 [US1] Route proposed `runtime register` and `runtime run` commands through `src/score_sw_fabric/cli.py`, returning stable 0/1/2 exits, bounded JSON and guarded binding publication (006-R11).
- [ ] T015 [US1] Complete public relocation, file-drift, lost-response, duplicate-intent and unchanged-003-history cases in `tests/integration/test_runtime_fabro.py`; record the exact native candidate limits and ambiguity in 006 acceptance (AC006-01–03).

**Checkpoint**: The MVP registers and starts only a closed package. An uncertain native create is a visible stop, not an automatic retry.

---

## Phase 4: User Story 2 — Inspect and stop at a human gate (Priority: P1)

**Goal**: Expose native events/questions faithfully and leave required human review waiting.

**Independent Test**: A disposable command-plus-human-gate run reports ordered events, one question and zero automatic answers.

### Tests for User Story 2

- [ ] T016 [P] [US2] Add event pagination, overlap/gap, checkpoint, unknown status, pending cancellation and exact gate-subject tests in `tests/contract/test_runtime_inspection.py` (AC006-04/05).
- [X] T017 [P] [US2] Add required-gate auto-approve/default-timeout refusal and Fabro-answer-is-not-005-decision cases in `tests/contract/test_runtime_human_gate.py` (AC006-06).
- [X] T018 [US2] Add a disposable native command-plus-human-gate waiting journey in `tests/integration/test_runtime_fabro.py`; if an authorized external human channel is absent, stop at the question and record that limit (AC006-04/06).

### Implementation for User Story 2

- [X] T019 [US2] Implement `src/score_sw_fabric/runtime/inspect.py` to read native summary/events/timeline/questions with event ID/sequence closure and explicit unknown/incomplete states; never use unstable `/state` as the sole contract (006-R05).
- [X] T020 [US2] Bind pending native question to one exact 003 gate/source-map entry and 005 subject in `src/score_sw_fabric/runtime/inspect.py`; block ambiguous mapping and required-gate auto-approve or success timeout (006-R06).
- [ ] T021 [US2] Route `runtime status` in `src/score_sw_fabric/cli.py` with bounded JSON, native status/reason, waiting handoff and separate `engineering_readiness: not_evaluated` (006-R05/R06/R10).
- [X] T022 [US2] Record native event/question IDs, zero automatic answers and distinct failure/cancel/wait statuses in `specs/006-fabro-runtime-integration/acceptance.md` (AC006-04–06).

**Checkpoint**: Waiting is visible and cannot be mistaken for approval or engineering completion.

---

## Phase 5: User Story 3 — Resume without duplicated effects (Priority: P1)

**Goal**: Admit only same-run compatible checkpoint continuation after exact baseline and effect reconciliation.

**Independent Test**: Resume an unchanged disposable checkpoint once; one-binding drift, partial effect and cancellation remain blocked or pending.

### Tests for User Story 3

- [ ] T023 [P] [US3] Add one-binding source/process/tool/policy/subject/005-evidence drift, missing checkpoint, terminal-source resume, unknown effect, finite attempt and native `/retry` refusal tests in `tests/contract/test_runtime_resume.py` (AC006-07–09).
- [ ] T024 [P] [US3] Add cancellation accepted-versus-terminal and known-ID resume/start conflict tests in `tests/contract/test_runtime_cancellation.py` (AC006-10).
- [ ] T025 [US3] Add disposable native checkpoint/resume and cancellation integration to `tests/integration/test_runtime_fabro.py`, counting completed command effects and preserving historical events (AC006-07/10).

### Implementation for User Story 3

- [ ] T026 [US3] Implement `src/score_sw_fabric/runtime/resume.py` admission using native checkpoint, exact 003/005 baseline vector, 005 freshness/replay, effect IDs and finite attempts; refuse terminal-source resume before native call; emit sorted drift IDs and `admit|block_drift|block_unknown|reconciliation_required` (006-R07/R08).
- [ ] T027 [US3] Implement same-run native resume and cancellation in `src/score_sw_fabric/runtime/client.py`; never substitute native new-run `/retry`, and wait for confirmed native cancellation reason (006-R08).
- [ ] T028 [US3] Route `runtime resume` and `runtime cancel` in `src/score_sw_fabric/cli.py` with 0/1/2 exits, guarded output and no implicit approval or evidence rewrite (006-R08/R11).
- [ ] T029 [US3] Record exact unchanged and drifted native run/effect IDs, retry bounds, prior hashes and unresolved production trust conditions in `specs/006-fabro-runtime-integration/acceptance.md` (AC006-07–10).

**Checkpoint**: Native Fabro owns continued execution; uncertainty and changed acceptance bindings stop automatic work.

---

## Phase 6: User Story 4 — Export an independently readable run record (Priority: P2)

**Goal**: Retain complete historical execution without requiring Fabro during review.

**Independent Test**: Relocate completed and waiting exports, verify offline, then remove one event/output/version byte and fail closed.

### Tests for User Story 4

- [ ] T030 [P] [US4] Add source/wire/native-ID/event/blob/checkpoint/question closure and single-byte mutation cases in `tests/contract/test_runtime_export.py` (AC006-11/13).
- [ ] T031 [P] [US4] Add runtime-observation versus authenticated 005 origin and fixture-to-production refusal cases in `tests/contract/test_runtime_export_origins.py` (AC006-12).
- [ ] T032 [US4] Add disposable native completed and waiting export, relocation, offline verification and missing-raw tests in `tests/integration/test_runtime_fabro.py` (AC006-11–13).

### Implementation for User Story 4

- [ ] T033 [US4] Implement bounded `src/score_sw_fabric/runtime/export.py` packaging of sealed 003 source, wire projection, native IDs, ordered events, output/blob bytes, checkpoints/questions, origin labels, limits and explicit completeness (006-R09/R10).
- [ ] T034 [US4] Implement offline `src/score_sw_fabric/runtime/export.py` verification of version-1 digest, byte/ref/event closure, sequence and recorded limitations with zero Fabro access (006-R09).
- [ ] T035 [US4] Route `runtime export` and `runtime verify` in `src/score_sw_fabric/cli.py`, preserving a prior complete export on interruption or incomplete input (006-R09/R11).
- [ ] T036 [US4] Record relocated export identities, byte hashes, missing-byte refusals and non-promotion of Fabro output/answers in `specs/006-fabro-runtime-integration/acceptance.md` (AC006-11–13).

**Checkpoint**: Historical execution is portable; current 005 acceptance remains separately determined.

---

## Phase 7: Polish and cross-cutting acceptance

- [ ] T037 [P] Reconcile 006-R01–R12, AC006-01–13, SC006-01–06 and FAB-024–FAB-026 with actual evidence and open boundaries in `specs/006-fabro-runtime-integration/acceptance.md` and `docs/backlog/requirements-index.md`.
- [ ] T038 [P] Update `README.md`, `schemas/README.md` and `docs/backlog/roadmap.md` with only executed runtime commands, version/exit contracts, 005 production-authority blocker and 007/014+ boundaries.
- [ ] T039 Run every applicable command in `specs/006-fabro-runtime-integration/quickstart.md`, frozen Ruff/format/mypy/pytest, foundation checker and offline build; record counts, elapsed time, native IDs, hashes, skips and unsupported capabilities in `specs/006-fabro-runtime-integration/acceptance.md`.
- [ ] T040 Create `docs/handoff/006-to-007.md` with exact run/version/export identities, preserved 003/005 artifacts, native capability limits, pending human/production authority, and narrow 007 context boundary; claim no deployment or engineering readiness.

## Dependencies and execution order

- **Setup (T001–T003)**: T001 is source/capability inspection; T002 and T003 can proceed independently. Live use waits for a selected compatible runtime and actual probe.
- **Foundation (T004–T007)**: Depends on setup. Models, transport and tests can use read-only/stub capability evidence before any native action. T007 resolves observed API differences.
- **US1 (T008–T015)**: Depends on foundation. It is the MVP and owns version/run creation.
- **US2 (T016–T022)**: Depends on the shared client and a run binding; human waiting can be tested from a native fixture even while US1 integration is pending.
- **US3 (T023–T029)**: Depends on native run/checkpoint identities and 005 closure; same-run resume must wait for US1/US2 integration.
- **US4 (T030–T036)**: Contract work can begin from sealed fixtures after foundation; final native export waits for the prior journeys.
- **Polish (T037–T040)**: Follows actual checks and native capability evidence. No human-owned production acceptance task is checked by an agent.

### Parallel opportunities

- T002 fixture setup and T003 schemas touch independent paths.
- T008 projection tests and T009 intent tests touch separate files.
- T016 inspection and T017 human-gate tests touch separate files.
- T023 resume and T024 cancellation tests touch separate files.
- T030 closure and T031 origin tests touch separate files.
- T037 evidence reconciliation and T038 documentation touch distinct files, after story evidence stabilizes.

## Implementation strategy

First prove package closure and native version registration, then run creation with a durable
known ID. Treat an ambiguous create response as a stopping condition. Add faithful native
inspection and a waiting human gate before resume. Admit resume only after exact baseline and
effect reconciliation. Export complete historical records last and verify them without Fabro.
Record all observed native limitations; a fixture or native success never grants 005 production
authority or 014+ readiness.
