# Tasks: Deterministic workflow compiler

**Input**: Design documents from `specs/003-deterministic-workflow-compiler/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/compiler.md`, `quickstart.md`

**Tests**: Required by AC003-01–16 and SC003-01–08. Contract tests precede implementation
within each story. Actual matching Fabro validator evidence is required before 003 completion.

**Organization**: Tasks are grouped by user story. The compiler remains offline and may validate
a disposable native package, but no task registers or executes a workflow, calls a model, edits a
target artifact, authenticates an approval, or changes engineering readiness.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can proceed in parallel after stated phase prerequisites because it changes different files.
- **[Story]**: User story from `spec.md`; setup, foundation, and cross-cutting tasks have no story label.
- Every task names exact paths and relevant acceptance or requirement coverage.

## Phase 1: Setup and versioned contract surfaces

**Purpose**: Establish the compiler package, strict schemas, pinned profiles, source-cited mapping,
and licensed fixtures without adding a runtime dependency.

- [X] T001 Create `src/score_sw_fabric/compiler/__init__.py` and confirm generated compiler/validator temporary paths are covered in `.gitignore` without ignoring canonical fixtures or acceptance evidence.
- [X] T002 [P] Publish strict version-1 envelopes in `schemas/compiler-request.schema.json`, `schemas/execution-mapping.schema.json`, `schemas/compiler-profile.schema.json`, `schemas/validator-profile.schema.json`, `schemas/workflow-package.schema.json`, `schemas/workflow-source-map.schema.json`, `schemas/compile-report.schema.json`, and `schemas/workflow-diff.schema.json`; require allowed paths/data destinations, explicit model-capability-or-none bindings, finite action budgets, reject unknown normative fields, boolean-as-integer versions/limits, and undeclared success defaults (003-R01/R05/R07/R10/R12–R14/R17).
- [X] T003 [P] Add `profiles/deterministic-compiler-v1.yaml`, `profiles/fabro-conformance-1b4fb152-v1.yaml`, and `policies/s_core_execution_mapping_v1.yaml` with exact source commit/hashes, MIT notice, explicit native subset, deterministic selection, `on_failure=route`, mandatory `allow_partial=false`, all declared structural/action-budget ceilings and model-capability profile IDs, and a visible pending owner-review state rather than fabricated approval (003-R02/R05/R08–R10/R15–R17).
- [X] T004 [P] Create licensed fixture-origin scenarios under `tests/fixtures/compiler/linear/`, `tests/fixtures/compiler/shared-parallel-review/`, `tests/fixtures/compiler/bounded-correction/`, and `tests/fixtures/compiler/invalid/`; include exact expected logical tuples/origins and synthetic fixture review records, never production `approved`/`trusted` switches (AC003-01–16).
- [X] T005 [P] Add deterministic fixture builders and a side-effect-recording validator stub in `tests/compiler_support.py`; distinguish simulated test acceptance from real Fabro evidence and provide byte-preserving sentinel helpers for failed publication tests.

---

## Phase 2: Foundational validated inputs and native-validator boundary

**Purpose**: Prevent every story from consuming unbounded, ambiguous, tampered, unreviewed, or
environment-dependent inputs.

**Critical**: Complete this phase before user-story behavior.

- [X] T006 [P] Add failing request/profile/plan/path contract cases in `tests/contract/test_compiler_inputs.py` for duplicate keys, exact integer/schema checks, unknown normative fields, transport/self/semantic digest mismatch, blocked or incomplete 002 plans, unresolved dispositions/external debt, profile incompatibility, exact-maximum and one-over 64 MiB input, 10,000 plan-instance, 100,000 plan-dependency, and 50,000 mapping-rule limits, traversal, case collision, symlink parents, hardlink aliases, protected-root output, and prior-output preservation (AC003-08/09/14; 003-R01/R04/R18; SC003-08).
- [X] T007 Implement strict immutable shapes in `src/score_sw_fabric/compiler/models.py` for CompilationRequest, InputReference, profiles/limits, ExecutionMapping/Rule, ActionTemplate, ModelCapabilityBinding, ActionBudget, ExecutionGraph/Node/Edge, GateObligation, FanGroup, CycleComponent, Origin, PackageFile/Manifest, SourceMapEntry, CompileReport, validation receipts, SemanticChange/Diff, and DriftResult; preserve null/missing/unknown/blocked/failed/successful states and exact enumerations from `data-model.md` (003-R05/R07/R10/R14).
- [X] T008 Implement bounded JSON/YAML parsing, exact plan/profile compatibility, semantic normalization/digests, protected path and file-identity checks in `src/score_sw_fabric/compiler/reader.py`; enforce 64 MiB per input, 10,000 plan instances, 100,000 plan dependencies, and 50,000 mapping rules before expansion while excluding only operational paths from identity (003-R01/R04/R11/R17/R18).
- [X] T009 [P] Add failing validator-adapter cases in `tests/contract/test_compiler_validator.py` for executable/source identity mismatch, host-settings leakage, malformed/oversized JSON output, timeout/nonzero/signal/missing executable, undeclared file access, disposable-tree cleanup, and attempts to select any command other than validation (AC003-13/16; 003-R16/R18/R19).
- [X] T010 Implement isolated native validation in `src/score_sw_fabric/compiler/validator.py`; verify the exact profiled binary/build identity, materialize only declared UTF-8 files into a fresh bounded tree, use isolated configuration/environment, invoke only `fabro validate` with structured output, capture a path-independent bounded receipt, and clean up on every result (003-R12/R16–R19).

**Checkpoint**: Invalid inputs and validator environments fail before IR derivation or publication;
the adapter cannot register, run, resume, cancel, or invoke providers/models.

---

## Phase 3: User Story 1 — Compile obligations into an executable package (Priority: P1) — MVP

**Goal**: Turn a complete sealed plan and reviewed mapping into a deterministic, closed,
source-mapped Fabro package accepted by the selected validator.

**Independent Test**: Two dependent instances with distinct review purposes and one exactly shared
gate compile to the expected typed IR, native files, source map, package identity, and validator
receipt; every semantic element traces to its plan/rule/source origin.

### Tests for User Story 1

- [X] T011 [P] [US1] Add failing mapping/IR cases in `tests/contract/test_compiler_ir.py` for every supported action type; deterministic-check identity; explicit role/input/output/allowed-path/data-destination/write-scope/tool-permission/model-capability-or-none/wall-time/attempt/tool-call/token/cost/predicate/evidence/failure/prohibited-authority bindings; missing, unlimited, zero-invalid, unknown, and above-profile policy; ordering only from reviewed rules; stable logical tuple hashes; complete gate-tuple deduplication; mapping gaps/conflicts; and ID/case-normalization collisions (AC003-01–04/06/12; 003-R02/R03/R05/R10/R13/R17; SC003-02).
- [X] T012 [P] [US1] Add failing canonical renderer cases in `tests/contract/test_compiler_rendering.py` for explicit native `type`, deterministic-check-to-command rendering with non-model binding and retained typed outcomes, one start/exit, exact DOT escaping and sorted statements, `_version = 1`, relative `workflow.fabro`, deterministic support files, graph `on_failure=route`, and rejection of implicit type/random selection/success-on-failure/partial mandatory merge/unbounded visits (AC003-01–04/09; 003-R05/R08/R09/R11/R16).
- [X] T013 [P] [US1] Add failing package/compile CLI cases in `tests/contract/test_compiler_package.py` and `tests/contract/test_compiler_cli.py` for complete source-map coverage, canonical self-digest, compiler/input/profile/validator bindings, successful exit 0, semantic/native rejection exit 1, malformed/infrastructure exit 2, atomic replacement, and the required `not_evaluated` report boundary (AC003-04/08/13/16; 003-R11–R13/R16–R19).

### Implementation for User Story 1

- [X] T014 [US1] Implement finite reviewed-rule selection, exact plan-instance coverage, action/gate/order/branch/merge/loop projection, allowed-path/data-destination/tool/model-capability/action-budget binding, agreeing-origin union, and complete gate-tuple deduplication in `src/score_sw_fabric/compiler/mapping.py`; require explicit non-model capability for non-model actions and never infer scheduling from native semantic links or apply last-rule-wins (003-R02/R03/R05/R10).
- [X] T015 [US1] Implement sorted typed graph derivation and canonical logical-key IDs in `src/score_sw_fabric/compiler/ir.py`; use plan instance set, rule ID, action purpose/role for nodes and endpoint/type/outcome/loop tuple for edges, retain full keys, keep mutable baselines as bindings, and reject collisions or dangling selectors (003-R03/R05/R11/R17).
- [X] T016 [US1] Implement canonical DOT, TOML, prompt/schema/script/policy rendering in `src/score_sw_fabric/compiler/render.py`; emit only the profiled explicit native node subset, always render internal deterministic-check as native `command`, retain its non-model/tool/budget bindings and typed outcomes in package semantics, use deterministic escaping/order and relative logical paths, and include no host-derived content (003-R05/R07–R12/R15/R16).
- [X] T017 [US1] Implement generated-file closure, the registry-compatible `entrypoint`/`files` map, per-file records, canonical package identity, and self-integrity validation in `src/score_sw_fabric/compiler/package.py`; enforce at most 512 files, 512 KiB per file, 2 MiB native text, and 64 MiB package with normalized unique relative paths (003-R11/R12/R17/R18).
- [X] T018 [US1] Complete source-map and compile-report construction in `src/score_sw_fabric/compiler/package.py`; cover every node, edge, gate, loop, fan group, file, and material renderer decision with sorted plan/rule/source/decision origins and state all registration/execution/evidence/acceptance/readiness/release capabilities as `not_evaluated` (AC003-04/16; 003-R02/R13/R19).
- [X] T019 [US1] Implement the guarded in-memory compile pipeline plus `score-fabric workflow compile --request REQUEST.yaml --out PACKAGE.json [--json]` in `src/score_sw_fabric/compiler/package.py` and `src/score_sw_fabric/cli.py`; validate inputs, IR, rendered closure, and native receipt before protected atomic replacement and preserve prior output for every exit 1/2 path (003-R16/R18/R19).
- [X] T020 [US1] Add the independently asserted linear/shared-review journey to `tests/integration/test_workflow_compiler.py`, proving exact obligation/action/edge/gate/file sets, distinct review purposes, agreeing shared-gate deduplication, total provenance, deterministic bytes, and zero target/source mutation (SC003-01/04/06/07).
- [X] T021 [US1] Add the linear real-validator case to `tests/integration/test_workflow_compiler_native.py`; require `SCORE_FABRO_BIN`, verify it against `profiles/fabro-conformance-1b4fb152-v1.yaml`, assert native acceptance and no registration/run/model/target effect, and make a skipped result ineligible for final 003 acceptance (AC003-13/16; SC003-03).

**Checkpoint**: US1 produces a closed, traceable package through the public compile command and
proves one real native conformance case without claiming runtime adoption.

---

## Phase 4: User Story 2 — Reject bypasses and unsafe control flow (Priority: P1)

**Goal**: Fail before publication when control flow can bypass required review, omit non-success
routing, loop without a finite exhaustion path, merge incompletely, or exceed authority.

**Independent Test**: Mutate one valid mapping at a time; each unsafe graph yields its stable
finding and concrete affected path/component while an existing package remains byte-identical.

### Tests for User Story 2

- [X] T022 [P] [US2] Add failing semantic graph cases in `tests/contract/test_compiler_graph_semantics.py` for duplicate/missing start or success exit, dangling/unreachable elements, required-gate bypass with expected shortest path, missing/overlapping outcomes, unknown-to-success fallthrough, missing/unknown/unlimited/above-profile action policy, unbounded/zero/negative/excess cycles, missing exhaustion, mismatched/empty/partial mandatory fan-in, and unmapped generated semantics (AC003-05–08; 003-R05–R10/R13/R16/R18; SC003-02).
- [X] T023 [P] [US2] Add failing authority/publication cases in `tests/contract/test_compiler_cli.py` for automatic approval, replayed approval, approval/evidence-collector credentials, success-producing timeout, allowed paths/data destinations/write scope outside the mapped boundary, disallowed model capabilities, excessive wall-time/attempt/tool-call/token/cost budgets, syntactically native-valid but fabric-invalid graphs, deterministic diagnostics, and unchanged sentinel output (AC003-05/06/08/15; 003-R10/R15/R16/R18/R19).

### Implementation for User Story 2

- [X] T024 [US2] Implement deterministic endpoint, uniqueness, start/exit, sorted reachability, unreachable-element, outcome-partition, and source-map-coverage validation in `src/score_sw_fabric/compiler/graph_validation.py`; non-success states must never use an omitted/default success edge (003-R05/R07/R13/R16).
- [X] T025 [US2] Implement mandatory-gate dominance/bypass-path analysis in `src/score_sw_fabric/compiler/graph_validation.py`; bind exact subject/purpose/authority and report a deterministic concrete start-to-success path for every violation, preserving exact authorized exclusions as visible semantics (003-R06/R15).
- [X] T026 [US2] Implement sorted Tarjan cyclic-component checks, positive profile-bounded loop policies with explicit exhausted destinations, exact fan-out/fan-in branch-set validation, and allowed-path/data-destination/tool/model-capability/action-budget plus agent/command/human authority prohibitions in `src/score_sw_fabric/compiler/graph_validation.py` (003-R08–R10/R15).
- [X] T027 [US2] Extend `tests/integration/test_workflow_compiler.py` with all single-mutation unsafe-control-flow scenarios plus exact-maximum and one-over 50,000-node, 200,000-edge, and 10,000-cyclic-component cases; assert stable finding codes/paths/components, validator non-invocation after semantic failure, no partial files, and preservation of prior valid output/input bytes (SC003-02/06/08).

**Checkpoint**: US2 proves that native syntax acceptance cannot override stricter fabric semantics.

---

## Phase 5: User Story 3 — Review workflow meaning and drift (Priority: P2)

**Goal**: Compare packages by semantic category and distinguish reviewed source change from direct
generated-output drift without adopting edited output as authority.

**Independent Test**: Relocation and set-order recompilation are equivalent; each isolated source
mutation changes only its expected category; a direct file-map edit reports exact drift.

### Tests for User Story 3

- [X] T028 [US3] Add failing semantic comparison cases in `tests/contract/test_compiler_diff_drift.py` for obligation, node/action, edge/control-flow, gate, permission, loop-bound, fan-group, generated-file, compiler-baseline, and validator-baseline additions/removals/modifications with exact stable subjects/origins and no unrelated category noise (AC003-09/10/12; 003-R11/R14/R17).
- [X] T029 [US3] Add failing drift cases in `tests/contract/test_compiler_diff_drift.py` for self-digest damage, changed/missing/undeclared file entries, source/profile/validator divergence, same visible DOT with changed semantic binding, unavailable recompilation input, and proof that the selected package is never resealed or replaced (AC003-11/12; 003-R14/R18).

### Implementation for User Story 3

- [X] T030 [P] [US3] Implement validated package comparison and ordered `SemanticChange`/`SemanticDiff` categories in `src/score_sw_fabric/compiler/diff.py`; verify both package identities first and compare typed bindings rather than raw formatting (003-R14/R17).
- [X] T031 [P] [US3] Implement read-only integrity and in-memory source-regeneration comparison in `src/score_sw_fabric/compiler/drift.py`; report expected/actual identities and classify direct edits separately from reviewed source/profile changes without writing either package (003-R14/R18).
- [X] T032 [US3] Add `score-fabric workflow diff` and `score-fabric workflow drift` routing, JSON receipts, and exact 0/1/2 exit semantics in `src/score_sw_fabric/cli.py` (003-R14/R18/R19).
- [X] T033 [US3] Extend `tests/integration/test_workflow_compiler.py` with independent relocation/permutation recompilation, one-change-per-category comparisons, stable logical IDs across revision rebinding, hidden semantic-binding changes, and direct generated-file edits (SC003-04/05).

**Checkpoint**: US3 makes generated changes reviewable and keeps source configuration authoritative.

---

## Phase 6: User Story 4 — Validate a closed, portable package (Priority: P2)

**Goal**: Revalidate a relocated self-contained package against its exact profile without
registration, execution, model calls, target writes, approval authentication, or readiness change.

**Independent Test**: A relocated valid package passes; deleting, adding, renaming, escaping,
case-colliding, oversizing, or changing any referenced file fails with its node/path identified.

### Tests for User Story 4

- [X] T034 [P] [US4] Add failing package-reader/closure cases in `tests/contract/test_compiler_package.py` for unknown fields, canonical/self/per-file digest mismatch, absent/extra/renamed/absolute/traversing/case-colliding paths, entrypoint absence, ambiguous aliases, UTF-8 failure, references to undeclared content, and exact 512-file/512-KiB/2-MiB/64-MiB boundaries (AC003-13/14; 003-R11/R12/R18).
- [X] T035 [P] [US4] Add failing public validation cases in `tests/contract/test_compiler_cli.py` for matching/mismatched/unavailable validator profiles, native rejection versus infrastructure exits, relocation, read-only behavior, bounded receipts, and explicit unevaluated capabilities (AC003-13–16; 003-R15/R16/R19).

### Implementation for User Story 4

- [X] T036 [US4] Complete strict existing-package parsing, integrity, closure, source-map consistency, profile compatibility, and reference-to-node diagnostics in `src/score_sw_fabric/compiler/package.py`; validate all limits before native materialization and reject undeclared logical content (003-R11–R13/R17/R18).
- [X] T037 [US4] Implement `score-fabric workflow validate --package PACKAGE.json --validator PROFILE.yaml [--json]` in `src/score_sw_fabric/cli.py` using `src/score_sw_fabric/compiler/validator.py`; preserve exact 0/1/2 semantics and perform no package/source/target mutation (003-R16/R18/R19).
- [X] T038 [US4] Add relocated-package and side-effect integration coverage to `tests/integration/test_workflow_compiler.py`, including closure attacks and human-node auto/replay/timeout prohibitions with referencing node/path diagnostics (SC003-02/04/06/07).
- [X] T039 [US4] Complete `tests/integration/test_workflow_compiler_native.py` with linear, shared-parallel-review, and bounded-correction packages plus maximum/one-over native closure limits; require all three to pass the matching real validator and record that no runtime registration/execution occurred (SC003-03/08).

**Checkpoint**: All four stories work through public commands, and three representative packages
have real native conformance evidence while every later-runtime capability remains unevaluated.

---

## Phase 7: Cross-cutting validation and handoff

**Purpose**: Reconcile actual results, public documentation, requirement traceability, and the next
increment boundary without starting native artifact mutation or runtime work.

- [X] T040 Update `schemas/README.md`, `README.md`, `docs/backlog/roadmap.md`, `docs/backlog/requirements-index.md`, and `specs/003-deterministic-workflow-compiler/quickstart.md` with only implemented commands, tested bounds, pinned validator identity, fixture-versus-production review distinction, and explicit registration/execution/readiness exclusions.
- [X] T041 After T040, run AC003-01–16 and SC003-01–08 plus frozen Ruff lint/format, strict mypy, full pytest, foundation checker, public CLI examples, offline package build, non-skipped matching-validator integration, and exact-maximum/one-over cases for 64 MiB inputs/package, 10,000 plan instances, 100,000 plan dependencies, 50,000 mapping rules/nodes, 200,000 edges, 10,000 cyclic components, 512 native files, 512 KiB per native file, 2 MiB native text, and each action-budget ceiling; record stable diagnostics, elapsed time/peak size, commands, results, hashes, validator identity, limitations, and FAB-012–FAB-015 mapping in `specs/003-deterministic-workflow-compiler/acceptance.md`.
- [X] T042 Reconcile every task marker with actual files/evidence and create `docs/handoff/003-to-004.md` covering implemented contracts, package/validator identities, pending owner review or runtime selection, retained trust boundaries, native-artifact prerequisites, and the recommended model for increment 004; stop before FAB-016–FAB-018 implementation.

---

## Dependencies and execution order

- Phase 1 starts immediately. After T001, T002–T005 affect independent schema, profile/policy,
  fixture, and test-support paths and can proceed in parallel.
- Phase 2 depends on the schemas/profiles/fixtures. T006 and T009 can be written in parallel;
  T007–T008 satisfy input cases, while T010 satisfies validator-adapter cases. Phase 2 blocks all stories.
- US1 depends on Phase 2 and is the MVP. T011–T013 can be authored in parallel; implementation
  then proceeds mapping → IR → rendering → package/report → CLI → integration/native evidence.
- US2 depends on the US1 IR and guarded compile pipeline. T022–T023 are parallel failing-test tasks;
  T024–T026 complete semantic checks before T027 integration.
- US3 depends on valid US1 packages and can proceed alongside US2 after package semantics stabilize.
  T028 and T029 are sequential because they share one test file; T030 and T031 can then implement
  diff and drift in parallel before shared CLI and integration work.
- US4 depends on package and validator foundations plus US1 publication. Its closure tests can be
  authored while US2/US3 proceed, but T036–T039 require stable package semantics.
- Phase 7 depends on all desired stories and real validation results. T041 must not pass while the
  matching native integration is skipped; T041 depends on T040, and T042 records unresolved owner/runtime decisions honestly.

## Parallel execution examples

### User Story 1

```text
T011: mapping and IR contract tests in tests/contract/test_compiler_ir.py
T012: renderer contract tests in tests/contract/test_compiler_rendering.py
T013: package and CLI contract tests in test_compiler_package.py/test_compiler_cli.py
```

### User Story 2

```text
T022: graph-semantic mutation tests in test_compiler_graph_semantics.py
T023: authority and publication tests in test_compiler_cli.py
```

### User Story 3

```text
T028 then T029: sequential test additions in test_compiler_diff_drift.py
T030: semantic comparison implementation in compiler/diff.py
T031: drift implementation in compiler/drift.py
```

### User Story 4

```text
T034: strict package/closure cases in test_compiler_package.py
T035: public validation/validator-profile cases in test_compiler_cli.py
```

Tasks sharing a file are coordinated sequentially even when their test-case design can be discussed
in parallel. `[P]` marks only file-safe implementation opportunities after prerequisites.

## Implementation strategy

### MVP first

1. Complete setup and foundational input/validator boundaries.
2. Implement US1 through canonical package publication and one real native-validator case.
3. Stop and verify provenance coverage, deterministic bytes, prior-output protection, and no side effects.

### Incremental delivery

1. Add US2 semantic rejection before expanding supported mappings.
2. Add US3 semantic review and drift detection over validated packages.
3. Add US4 standalone portable validation and complete all three native conformance cases.
4. Run cross-cutting acceptance, update only evidence-backed status, and hand off to 004.

No task adopts the pinned nightly Fabro source as the production runtime. That selection and all
registration/run-state behavior remain increment 006; trusted evidence and human decision
authentication remain increment 005.

## Requirement coverage index

| Requirement | Primary tasks |
| --- | --- |
| 003-R01 | T002, T006, T008 |
| 003-R02 | T003, T011, T014, T018 |
| 003-R03 | T011, T014, T015 |
| 003-R04 | T006, T008 |
| 003-R05 | T002, T003, T011, T012, T014–T016, T022, T024 |
| 003-R06 | T022, T025, T027 |
| 003-R07 | T002, T012, T016, T022, T024 |
| 003-R08 | T003, T012, T016, T022, T026 |
| 003-R09 | T003, T012, T014, T016, T022, T026 |
| 003-R10 | T003, T011, T014, T023, T026 |
| 003-R11 | T008, T012, T016, T017, T028, T033, T034, T036 |
| 003-R12 | T002, T010, T016–T018, T034, T036 |
| 003-R13 | T002, T011, T018, T022, T024, T036 |
| 003-R14 | T002, T028–T032 |
| 003-R15 | T003, T023, T025, T026, T038 |
| 003-R16 | T003, T009, T010, T012, T013, T019, T023, T024, T035, T037 |
| 003-R17 | T002, T008, T011, T013, T015, T017, T028, T030, T034, T036 |
| 003-R18 | T002, T006, T008–T010, T013, T017, T019, T022, T023, T027, T029, T031, T032, T034–T037 |
| 003-R19 | T009, T010, T013, T018, T019, T021, T023, T032, T035, T037–T039 |
