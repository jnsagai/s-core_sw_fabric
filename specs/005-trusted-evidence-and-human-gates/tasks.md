---

description: "Dependency-ordered implementation tasks for trusted evidence and authenticated human gates"
---

# Tasks: Trusted evidence and authenticated human gates

**Input**: Design documents from `/specs/005-trusted-evidence-and-human-gates/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/assurance.md`, and `quickstart.md`.

**Tests**: The specification requires independently testable evidence, human-decision, gate, and
freshness journeys plus exact negative and portable verification outcomes. Test tasks precede the
behavior they assert and must fail for the intended reason first.

**Organization**: Four user-story phases follow a shared bounded verifier foundation. A checked
task proves only its described behavior. Fixture-domain success cannot become production authority.
All tasks are unchecked; no implementation or owner approval is claimed by this list.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable after stated prerequisites because it changes independent files.
- **[Story]**: Maps to one of the four user stories in `spec.md`.
- Every task names concrete files and its requirement or acceptance boundary.

## Phase 1: Setup and versioned contracts

**Purpose**: Establish exact version-1 records and fixture-only trust inputs before behavior exists.

- [X] T001 Pin a Python 3.12-compatible `cryptography` Ed25519 verifier release and license in `pyproject.toml` and `uv.lock`; verify frozen offline wheel resolution and record the selected release in `specs/005-trusted-evidence-and-human-gates/research.md`, with no signing or production key dependency (005-R02/R06/R20).
- [X] T002 [P] Add strict draft-2020-12 version-1 schemas `schemas/assurance-subject.schema.json`, `schemas/assurance-trust-profile.schema.json`, `schemas/assurance-receipt.schema.json`, `schemas/assurance-evidence.schema.json`, `schemas/assurance-decision.schema.json`, `schemas/assurance-gate-policy.schema.json`, and `schemas/assurance-assessment.schema.json`; require exact integer `schema_version: 1`, explicit domain, finite arrays, SHA-256 fields, six gate outcomes, four evidence classes, and reject unknown normative fields/enums (005-R01–R03/R07/R10/R18/R19).
- [X] T003 [P] Add a clearly labelled test-only `profiles/assurance-fixture-v1.yaml` and licensed `tests/fixtures/assurance/fixture-trust/` public-key/test-vector material with `assurance_domain: fixture_contract`, issuer kind/scope/role/validity rules, `README.md`, and no production private key or implied owner approval (005-R03/R05–R08/R20; SC005-02/03).
- [X] T004 Add sealed 002-plan/004-candidate/report fixture references, complete/blocked expected sets, test-domain receipts, exact identity mutations, and deterministic builders in `tests/assurance_support.py` plus `tests/fixtures/assurance/passing-scope/`, `blocked-scope/`, and `mutations/`; preserve native source bytes and label all test keys as fixture-only (AC005-01–16; SC005-01–08).

---

## Phase 2: Foundational strict input and origin boundary

**Purpose**: Make version, closure, trust-domain, signature, path, and output checks available to all
four stories. No story begins before this phase passes.

- [X] T005 [P] Add failing strict-envelope, duplicate-key, boolean-version, unknown enum/field, transport/self/nested digest, symlink/hardlink/case/path alias, exact-maximum/one-over, input/output alias, absent-root, and fixture-to-production promotion cases in `tests/contract/test_assurance_inputs.py` (005-R01/R05/R17–R19; SC005-02/08).
- [X] T006 [P] Add failing domain-separated Ed25519 receipt test vectors in `tests/contract/test_assurance_origins.py` for wrong payload/kind/domain/key/signature, malformed base64/key, revoked/expired key, replayed sequence, unsupported algorithm, unapproved issuer, and altered trust profile; hash equality alone must never authenticate origin (005-R02–R06/R08; SC005-01/02).
- [X] T007 Implement strict typed record definitions, exact allowed fields/enums, stable IDs, version-1 limits of 64 MiB per control/package, 100,000 predicates/evidence, 10,000 decisions/references, 20,000 findings and 32 reference levels, plus deterministic reason structures in `src/score_sw_fabric/assurance/models.py` and `src/score_sw_fabric/assurance/__init__.py` (005-R01/R03/R07/R10/R18/R19).
- [X] T008 Implement duplicate-safe bounded JSON/YAML loading, exact schema/version checks, transport/self/nested digest and reference-closure validation, logical path normalization, protected-root and inode/alias checks, strict output-root policy, and no network fetching in `src/score_sw_fabric/assurance/reader.py` (005-R01/R17–R19).
- [ ] T009 Implement canonical domain-separated Ed25519 public-key receipt verification in `src/score_sw_fabric/assurance/origins.py`; pin trusted keys outside agent-writable request authority, verify signature/payload digest/issuer/kind/scope/domain/validity/revocation/sequence, and reject a fixture root in production even if the signature is valid (005-R02–R06/R08/R18).
- [X] T010 Add the `score-fabric assurance` command namespace, bounded diagnostics, stable 0/1/2 exits, and no sign/approve/run operation to `src/score_sw_fabric/cli.py`; wire guarded sibling-temp publication in `src/score_sw_fabric/assurance/package.py` so malformed/interrupted work never replaces an existing complete output (005-R17–R20).

**Checkpoint**: A valid-looking local file or digest cannot authenticate origin, and every operation
can fail safely before using incomplete or unsafe inputs.

---

## Phase 3: User Story 1 - Establish trusted verification evidence (Priority: P1) - MVP

**Goal**: Produce a sealed subject and classify an exact verification result without promoting a
fixture, agent assertion, or unapproved import into trusted production evidence.

**Independent Test**: Use the public `assurance subject` and `assurance evidence` commands with a
sealed 002/004 fixture and one test-signed result, then substitute wrong input/tool/policy/process,
import issuer, fixture class, and agent-authored lookalike; only exact test-domain eligibility holds.

### Tests for User Story 1

- [X] T011 [P] [US1] Add failing subject-closure cases in `tests/contract/test_assurance_subjects.py` for exact 002 plan and 004 candidate/report/source/tool/profile/metamodel/template/validator/obligation bindings, report `not_evaluated` boundary, missing trace limitation, circular-approval exclusion, altered nested bytes, and relocation/order identity (AC005-01/04/16; 005-R01/R02/R18; SC005-01/08).
- [X] T012 [P] [US1] Add failing observed/import/fixture/agent eligibility cases in `tests/contract/test_assurance_evidence.py` for full result and raw-output hashes, collector origin, tool executable/version, process/policy/profile, exact scope/obligations, signed issuer, import chain, timeout/crash/truncation/missing extraction, and production-domain refusal (AC005-01–04; 005-R02–R06; SC005-01/02).
- [X] T013 [P] [US1] Add failing public subject/evidence exit, bounded JSON, atomic sentinel, and 002/004 integration cases in `tests/integration/test_assurance_from_artifacts.py`; a fixture-domain eligible result must remain explicitly fixture-only (AC005-01–04; 005-R01–R06/R17/R19; SC005-01/02).

### Implementation for User Story 1

- [X] T014 [US1] Implement `SubjectManifest` construction in `src/score_sw_fabric/assurance/subjects.py`; revalidate sealed 002/004 closure, include the complete expected obligation set before observations, bind exact source/process/tool/profile/report identities, exclude evidence/decision/self digests from the subject digest, and retain missing-trace limitations (005-R01/R02/R14/R18).
- [X] T015 [US1] Implement protected-observed, imported-verified, fixture-replay, and agent-assertion classification in `src/score_sw_fabric/assurance/evidence.py`; preserve original issuer/subject/result/transformation, require raw bytes and authenticated collector where eligible, apply exact import policy, and treat timeout/crash/missing measurement as unknown rather than zero or clean (005-R02–R06/R12).
- [X] T016 [US1] Implement independent `assurance subject` and `assurance evidence` request/output routing in `src/score_sw_fabric/assurance/package.py` and `src/score_sw_fabric/cli.py`; return exact subject and per-record eligibility/reasons without editing 002/004 records or claiming approval/readiness (AC005-01–04; 005-R01–R06/R17/R19/R20).
- [X] T017 [US1] Complete the sealed-plan/native-candidate and evidence journeys in `tests/integration/test_assurance_from_artifacts.py`; assert exact bound identities, fixture-only positive result, agent/fixture/import substitution rejection, source immutability, deterministic relocation, and unchanged prior output on malformed/incomplete input (SC005-01/02/08).

**Checkpoint**: The MVP provides independently inspectable subject and evidence eligibility but no
human approval or aggregate gate result.

---

## Phase 4: User Story 2 - Record an accountable human decision (Priority: P1)

**Goal**: Verify a human decision's authenticated origin, actor, role, authority, independence,
exact subject/scope, conditions, and lifecycle without relying on a claimed actor string.

**Independent Test**: Validate a test-domain decision for one sealed subject; wrong subject, wider
scope, disallowed role, failed independence, withdrawal, expiry, conflict, replay, and an agent file
must all be ineligible while the historical decision bytes stay unchanged.

### Tests for User Story 2

- [X] T018 [P] [US2] Add failing decision contract cases in `tests/contract/test_assurance_decisions.py` for all mandatory actor/role/authority/independence/subject/scope/outcome/rationale/condition/policy/time/origin fields, signed issuer versus 002 `claimed_actor`, Fabro interview/replay, wrong scope/policy/role, expired/revoked authority, conflicting decisions, and immutable withdrawal/supersession (AC005-05–08; 005-R07–R09; SC005-02/03).
- [X] T019 [P] [US2] Add failing public decision command and guarded-output cases in `tests/contract/test_assurance_cli.py` for `assurance decision` 0/1/2 exits, bounded reasons, exact domain labels, no private-key or approval-submission argument, and unchanged prior result on malformed receipt (AC005-05–08; 005-R07–R09/R17/R19/R20).

### Implementation for User Story 2

- [X] T020 [US2] Implement authenticated `HumanDecision` eligibility in `src/score_sw_fabric/assurance/decisions.py`; require trusted issuer attestation of actor authentication, corroborated role assignment and independence, exact subject/scope/gate/obligation/policy, valid time/conditions, and reject unverified 002/Fabro/agent claims (005-R07/R08/R20).
- [X] T021 [US2] Implement immutable decision events in `src/score_sw_fabric/assurance/decisions.py`; represent rejection, request changes, conditional approval, withdrawal, expiry, supersession and conflicts as separate current-use eligibility outcomes without rewriting original records (005-R07–R09/R15).
- [X] T022 [US2] Route `assurance decision` through `src/score_sw_fabric/assurance/package.py` and `src/score_sw_fabric/cli.py`; emit the exact actor/role/authority/independence/scope/condition checks and safe non-pass reasons but no decision signer, approval credential, or production authority from a fixture (AC005-05–08; 005-R07–R09/R17/R19/R20).
- [X] T023 [US2] Complete public decision integration assertions in `tests/integration/test_assurance_from_artifacts.py` using a sealed subject fixture and altered decision receipts; prove fixture-domain positive, all wrong-authority/scope/conflict negatives, independent 002/Fabro-claim refusal, and zero historical byte changes (SC005-02/03/05).

**Checkpoint**: A reviewer can inspect which exact authenticated decision is eligible or ineligible
for one subject; no gate assumes a decision from an interview or agent-written file.

---

## Phase 5: User Story 3 - Evaluate scoped gates fail-closed (Priority: P1)

**Goal**: Derive complete expected predicates first, then emit one of six exact gate outcomes with
stable reasons and routes for the selected subject, scope, and assurance domain.

**Independent Test**: With fixture-domain signed evidence and decisions, a complete non-empty gate
passes; one measured failure fails; each missing/unknown/untrusted/timeout/empty case blocks;
exact tailoring remains visible; mixed failure plus missing input blocks with both findings.

### Tests for User Story 3

- [X] T024 [P] [US3] Add failing expected-set and applicability cases in `tests/contract/test_assurance_gates.py` for 002 instances, 004 obligations, reviewed policy origin, deterministic/trusted/human predicate classes, duplicate/missing/unclassified obligations, stable denominator, and exact authenticated tailoring that does not erase an obligation (AC005-09/12; 005-R10/R11/R13/R16; SC005-04/06).
- [X] T025 [US3] Add failing six-state and precedence cases in `tests/contract/test_assurance_gates.py` for complete pass, measured fail, blocked missing/unknown/timeout/untrusted/over-limit, never-started `not_evaluated`, prior-baseline `stale`, authorized whole-gate `not_applicable`, mixed fail+missing blocked with both predicate results, stable reason/action/route and no vacuous pass (AC005-09–12; 005-R10–R13/R16; SC005-04/06).
- [X] T026 [P] [US3] Add failing policy-limit and public gate cases in `tests/contract/test_assurance_limits.py` for exact maxima and one-over records, bytes, predicates, evidence, decisions, refs, findings, nesting, duration, bounded diagnostics, 0/1/2 exits, and unchanged prior assessment on interruption (AC005-04/09–12; 005-R18/R19; SC005-04/08).

### Implementation for User Story 3

- [X] T027 [US3] Implement complete `ExpectedPredicate` derivation in `src/score_sw_fabric/assurance/predicates.py`; freeze non-empty obligation IDs from 002/004 plus exact reviewed gate rules before observed records, preserve tailored/external denominator entries, and reject duplicate/conflicting/missing authority (005-R01/R11/R13/R16).
- [X] T028 [US3] Implement per-predicate deterministic, trusted-evidence and human-decision eligibility checks in `src/score_sw_fabric/assurance/predicates.py`; compare exact subject/scope/policy/issuer/role/independence/conditions/time and keep signature authenticity distinct from adequacy (005-R02–R13/R16).
- [X] T029 [US3] Implement gate result calculation in `src/score_sw_fabric/assurance/gates.py`; use exact `pass|fail|blocked|not_evaluated|not_applicable|stale`, block incomplete inputs even with an independent measured failure, require whole-gate tailoring authority for whole-gate N/A, bind all reasons/refs/routes, and prevent a broader readiness or release claim (005-R10–R13/R16).
- [X] T030 [US3] Implement `assurance gate --request ... --out ...` in `src/score_sw_fabric/assurance/package.py` and `src/score_sw_fabric/cli.py`; validate domain, trusted time basis for current production use, complete predicate matrix, canonical assessment, guarded publication, and exact 0/1/2 behavior (AC005-09–12; 005-R10–R13/R17–R20).
- [X] T031 [US3] Complete fixture-domain positive and adversarial public gate cases in `tests/integration/test_assurance_from_artifacts.py`; prove all six outcomes, mixed-state precedence, missing-review block, tailored denominator visibility, fixture-to-production refusal, zero 004 capability changes, and no module/platform/release claim (SC005-02/04/06).

**Checkpoint**: A gate result is exact, non-vacuous, fail-closed and scoped. A fixture-domain pass
proves only the algorithm and never production acceptance.

---

## Phase 6: User Story 4 - Detect staleness and audit independently (Priority: P2)

**Goal**: Re-evaluate current applicability after any bound identity changes and reproduce a
portable historical assessment without Fabro while preserving all prior facts.

**Independent Test**: Mutate one subject/source/process/tool/profile/policy/trust/evidence/decision/
time binding at a time; affected current use becomes stale or blocked, original bytes stay intact,
and a relocated offline verifier reproduces the historical result from complete inputs.

### Tests for User Story 4

- [X] T032 [P] [US4] Add failing one-change-at-a-time freshness cases in `tests/contract/test_assurance_freshness.py` for candidate/report/source/process/template/metamodel/validator/tool/profile/policy/trust root/obligation/evidence/decision/condition/validity, changed role or revocation, unknown/new unlinked dependency, and exact old/new scoped no-impact decision (AC005-07/13/14; 005-R14/R15; SC005-05).
- [X] T033 [P] [US4] Add failing portable verifier cases in `tests/contract/test_assurance_portability.py` for complete closed refs, signed receipt/raw-output/root absence, wrong historical/current time basis, independent root selection, unknown versions, canonical relocation/order, result recomputation, original blocked assessment reproduction, and zero Fabro access (AC005-15/16; 005-R17–R19; SC005-07/08).

### Implementation for User Story 4

- [X] T034 [US4] Implement immutable current-use freshness and conservative impact in `src/score_sw_fabric/assurance/freshness.py`; compare every bound identity, retain 004 impact paths, widen unknown/new unlinked dependencies, verify any old/new no-impact decision's exact scope/authority, and never mutate historical evidence, decisions or gates (005-R14/R15/R18).
- [X] T035 [US4] Implement portable assessment closure and independent `verify` in `src/score_sw_fabric/assurance/package.py`; reread source/raw/receipt bytes by immutable digest, verify externally anchored trust context, recompute eligibility/predicate/gate outcome, separate historical replay from current applicability, and fail closed on absent bytes (005-R01/R14/R15/R17–R19).
- [X] T036 [US4] Add `assurance verify --assessment ... --trust-context ...` routing in `src/score_sw_fabric/cli.py`; return 0 only for faithful record reproduction regardless of historical gate pass/fail, 1 for semantic mismatch and 2 for malformed/unsafe/unavailable verification input, with a bounded readable/JSON result and no Fabro client (AC005-15/16; 005-R17–R20).
- [X] T037 [US4] Complete relocated offline and current-use mutation journeys in `tests/integration/test_assurance_from_artifacts.py`; prove byte-identical semantic identities/results under path/order permutations, exact affected stale set, unchanged historical files, missing-ref non-pass, and protected-time requirement for current production pass (SC005-05/07/08).

**Checkpoint**: Earlier facts remain immutable, while current applicability and portable replay are
independently checkable without runtime access.

---

## Phase 7: Polish and cross-cutting acceptance

**Purpose**: Verify all four journeys together, document actual limits and keep owner authority
pending where no protected production services exist.

- [X] T038 [P] Run the full one-field/one-binding adversarial matrix and exact-max/one-over cases in `tests/contract/test_assurance_inputs.py`, `test_assurance_origins.py`, `test_assurance_evidence.py`, `test_assurance_decisions.py`, `test_assurance_gates.py`, `test_assurance_freshness.py`, `test_assurance_portability.py`, and `test_assurance_limits.py`; record deterministic reasons, output preservation and FAB-019–FAB-023 coverage in `specs/005-trusted-evidence-and-human-gates/acceptance.md` (SC005-01–08).
- [X] T039 [P] Update `schemas/README.md` and `README.md` with exact assurance record versions, CLI exits, fixture/production domain boundary, external protected-root/time prerequisites, portable verifier use, and explicit 006/runtime and 014+/readiness boundaries (005-R16/R17/R20).
- [X] T040 Execute all commands in `specs/005-trusted-evidence-and-human-gates/quickstart.md` against checked-in fixture outputs and run `uv run --frozen ruff check .`, `ruff format --check .`, `mypy`, `pytest -q`, `python scripts/check_foundation.py`, and `uv build --offline`; write actual commands, counts, hashes, time, package size, skipped tests and limitations in `specs/005-trusted-evidence-and-human-gates/acceptance.md` (SC005-01–08).
- [X] T041 Reconcile every 005 requirement and acceptance scenario with concrete evidence in `specs/005-trusted-evidence-and-human-gates/acceptance.md`, update `docs/backlog/requirements-index.md` and `docs/backlog/roadmap.md`, and leave all human-owned production identity/collector/role/trust/gate-policy review items pending until actually performed (005-R01–R20; AC005-01–16).
- [X] T042 Create `docs/handoff/005-to-006.md` with exact assessment/fixture identities, known production blockers, verified offline commands, unchanged 004/002 history, and the narrow Fabro runtime integration boundary for Increment 006; claim no production approval, registration, release or deployment (005-R15–R20).

**Checkpoint**: Increment 005 may be marked implemented for its fixture-domain contract and
portable verifier only after all actual checks pass. Real production acceptance remains blocked
until protected owner-controlled infrastructure and decisions exist.

---

## Dependencies and execution order

- **Phase 1 (T001–T004)**: Setup. T002 and T003 may run in parallel; T004 depends on T003 test-key material.
  T001 must finish before the frozen implementation checks.
- **Phase 2 (T005–T010)**: Depends on Phase 1. T005 and T006 are independent failing-test files;
  T007–T010 implement shared records, readers, origin verification and safe CLI/publication.
- **US1 (T011–T017)**: Depends on Phase 2. Tests T011–T013 can be written independently. The
  subject and evidence commands then form the MVP and can be tested without a gate.
- **US2 (T018–T023)**: Depends on Phase 2. It uses a sealed subject fixture, so decision
  eligibility can be tested independently of US1 command completion; end-to-end reuse of the
  newly built US1 subject is checked in T023.
- **US3 (T024–T031)**: Depends on Phase 2 and the US1/US2 eligibility interfaces. Its predicate
  matrix can be built against sealed fixture records before their public commands are complete;
  final gate integration waits for T017 and T023.
- **US4 (T032–T037)**: Depends on Phase 2 and the US3 result format for final portable replay.
  Freshness and verifier contracts can be tested with sealed fixture assessments first; final
  integration waits for T031.
- **Polish (T038–T042)**: Depends on all four story checkpoints. Documentation T039 can start once
  the public contract stabilizes. T041 and T042 follow actual acceptance evidence in T040.

### Parallel execution examples

- After T004 and foundational validation, `T011` subject tests, `T012` evidence tests, and `T018`
  decision tests can be authored in separate files; each uses the same sealed fixture identities.
- After T010, `T014` subject construction and `T020` decision eligibility touch distinct modules;
  their public CLI routing remains sequential to avoid editing `cli.py` concurrently.
- `T032` freshness tests and `T033` portable verifier tests use different files and a fixed
  assessment fixture; the implementation converges in T034–T037.
- In the final phase, `T038` adversarial cases and `T039` documentation touch independent files;
  acceptance reconciliation waits for their outputs.

## Requirement and outcome coverage

This table identifies primary implementation and verification tasks. Range references in the task
text are supplemental; every key below has at least one concrete task.

| Key | Primary task IDs |
| --- | --- |
| 005-R01 | T002, T008, T011, T014 |
| 005-R02 | T006, T009, T011, T012, T014, T015 |
| 005-R03 | T002, T003, T007, T015 |
| 005-R04 | T012, T015 |
| 005-R05 | T003, T006, T009, T012, T015 |
| 005-R06 | T001, T003, T006, T009, T012, T015 |
| 005-R07 | T002, T007, T018, T020 |
| 005-R08 | T006, T009, T018, T020 |
| 005-R09 | T018, T021 |
| 005-R10 | T002, T007, T024, T025, T029 |
| 005-R11 | T024, T027 |
| 005-R12 | T012, T015, T025, T029 |
| 005-R13 | T024, T027, T029 |
| 005-R14 | T032, T034 |
| 005-R15 | T021, T032, T034, T035 |
| 005-R16 | T024, T027, T028, T029, T031, T039 |
| 005-R17 | T008, T010, T013, T016, T019, T022, T030, T035, T036 |
| 005-R18 | T002, T007, T008, T009, T011, T014, T026, T034 |
| 005-R19 | T002, T007, T008, T010, T013, T016, T019, T022, T026, T030, T035, T036 |
| 005-R20 | T001, T003, T010, T016, T019, T022, T030, T036, T039, T041, T042 |
| SC005-01 | T004, T012, T013, T017, T038, T040 |
| SC005-02 | T003, T005, T006, T012, T013, T017, T018, T023, T031, T038, T040 |
| SC005-03 | T003, T018, T023, T038, T040 |
| SC005-04 | T024, T025, T026, T031, T038, T040 |
| SC005-05 | T023, T032, T037, T038, T040 |
| SC005-06 | T024, T025, T031, T038, T040 |
| SC005-07 | T033, T037, T038, T040 |
| SC005-08 | T004, T005, T011, T017, T026, T033, T037, T038, T040 |

## Implementation strategy

1. Deliver T001–T010, then prove the trust-domain/signature boundary fails correctly before
   recording any accepted evidence or decision.
2. Deliver US1 as the MVP: a portable exact subject and evidence eligibility report. Validate it
   independently with a sealed 002/004 fixture and negative substitutions.
3. Deliver US2 and prove actor/role/independence/lifecycle checks with a sealed subject fixture.
4. Deliver US3 only after eligibility interfaces are stable; freeze expected obligations before
   observations and check every six-state branch plus mixed incomplete/failure behavior.
5. Deliver US4 and verify historical replay, current-use staleness and relocation without Fabro.
6. Run the complete quickstart and repository gates, record real evidence, and leave owner-controlled
   production trust and approval inputs visibly pending.

No step uses a model/provider, mutates a production target or protected reference checkout,
registers/executes Fabro, or creates a release/deployment decision. The current Git branch and
untracked baseline remain untouched by this task-generation step.
