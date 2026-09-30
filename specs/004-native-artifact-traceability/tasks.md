---

description: "Dependency-ordered implementation tasks for native artifact traceability"
---

# Tasks: Native artifact traceability

**Input**: Design documents from `/specs/004-native-artifact-traceability/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/artifacts.md`,
and `quickstart.md`

**Tests**: The specification requires independent contract, integration, native-build,
determinism, negative, and exact-boundary evidence. Test tasks precede implementation tasks in
each story and must fail for the intended reason before implementation.

**Organization**: Tasks are grouped by user story. Native target/source checkouts remain read-only;
all builds use disposable copies. A checked task proves only its described result.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel after its stated prerequisites because it changes independent files.
- **[Story]**: Maps the task to one of the four user stories in `spec.md`.
- Every task names its concrete file path and requirement/acceptance boundary.

## Phase 1: Setup and versioned contracts

**Purpose**: Establish the version-1 schema/profile/fixture surface without claiming production
policy approval or implementing behavior.

- [X] T001 Create the `src/score_sw_fabric/artifacts/__init__.py` package boundary and add the planned artifact command namespace skeleton to `src/score_sw_fabric/cli.py`; expose no successful operation until strict readers and validators exist (004-R21).
- [X] T002 [P] Add strict draft-2020-12 schemas `schemas/target-snapshot.schema.json`, `schemas/artifact-request.schema.json`, `schemas/native-artifact-profile.schema.json`, `schemas/trace-profile.schema.json`, `schemas/native-artifact-index.schema.json`, `schemas/artifact-candidate.schema.json`, `schemas/artifact-report.schema.json`, and `schemas/artifact-diff.schema.json`; use exact integer `schema_version: 1`, reject unknown normative fields, require SHA-256 digests, encode request operations exactly as `index|candidate|trace`, obligation states exactly as `expected|satisfied|partial|excluded|unresolved|mismatched`, and fix all six later capabilities to `not_evaluated` (004-R01/R19–R21).
- [X] T003 [P] Add `profiles/s_core_native_artifacts_v1.yaml`, `profiles/s_core_native_build_v1.yaml`, `policies/s_core_artifact_mapping_v1.yaml`, and `policies/s_core_trace_profile_v1.yaml` with exact source/metamodel/template/tool hashes, allowed native types/statuses/options/relations, output classifications, trace/impact rules, visible pending production-review state, fixture-only reviewed records, and exact limits of 64 MiB per control/package and declared target, 10,000 files, 2 MiB per text file, 100,000 native entities, 100,000 expected obligations, 500,000 relations, 10,000 edits, 20,000 findings, 8 MiB native output, and 1,800 seconds (004-R01/R03/R04/R09/R10/R14/R16/R19).
- [X] T004 [P] Add licensed feature/component/analysis/native-consumer fixtures under `tests/fixtures/artifacts/` from the exact pinned module-template/docs-as-code sources, with `LICENSE`, `README.md`, file/source hashes, Bazel 8.7.0 lock/configuration, expected live-versus-literal directive counts, complete and missing-obligation variants, and fixture-only plan/package/profile bindings; never build or edit a protected checkout (AC004-01–15; SC004-01–07).
- [X] T005 [P] Add deterministic fixture/request/package builders and mutation helpers in `tests/artifact_support.py` covering exact identities, native exports, edit preimages, expected obligations, trace paths, impact rules, canonical digests, protected sentinel outputs, and maximum/one-over inputs without granting fixture records production authority (SC004-03–08).

---

## Phase 2: Foundational input, model, native-build, and publication boundaries

**Purpose**: Implement shared strict records and fail-closed boundaries that block every user story.

**Critical**: No story implementation begins until these tasks pass.

- [X] T006 [P] Add failing request/snapshot/profile/schema cases in `tests/contract/test_artifact_inputs.py` for duplicate JSON/YAML keys, booleans-as-integers, unknown fields/enums, malformed/self/transport digest, plan/package/source mismatch, pending production policy, missing operation-conditional inputs, unsafe paths, symlink/hardlink/case aliases, non-UTF-8 managed RST, exact file/byte/entity/relation/obligation/edit/finding limits, and input/output/source-root aliasing (004-R01/R04/R05/R19/R21; SC004-03).
- [X] T007 Implement frozen/typed request, snapshot, profile, source, directive, wrapper, need, relation, index, edit, candidate, obligation, trace, coverage, impact, receipt, report, diff, and finding records in `src/score_sw_fabric/artifacts/models.py`; preserve the exact identity/state/enumeration/required-field constraints from `data-model.md` and never derive native identity from a title, path, list position, or workflow node ID (004-R01–R03/R08–R12/R16–R21).
- [X] T008 Implement bounded duplicate-key-safe loading and cross-input validation in `src/score_sw_fabric/artifacts/reader.py`; verify every transport/self/nested digest, complete plan and validated package binding, source lock/commit/metamodel/template/profile identities, full regular-file snapshot closure, inode/path protections, operation-conditional inputs, finite counts/bytes, and read-only protected roots before scanning or building (004-R01/R02/R04/R05/R19/R21).
- [X] T009 [P] Implement isolated locked native validation in `src/score_sw_fabric/artifacts/native.py`; verify the exact profiled Bazel/Bazelisk/dependency identities, copy only declared base+overlay closure into a fresh tree, isolate HOME/cache, invoke fixed argv without a shell for `needs_json` and `docs_check`, cap 1,800 seconds and 8 MiB output, hash fresh export/logs, return a host-path-free receipt, and clean up on every result without fetching links or executing imported content (004-R01/R05/R07/R19/R21).
- [X] T010 Implement canonical JSON/digest helpers, nested integrity, normalized path/file closure, changed-file overlay materialization, guarded sibling-temp publication, and prior-output preservation in `src/score_sw_fabric/artifacts/package.py`; exclude only self-digest and operational local paths from identity and reject undeclared files or unmapped semantics (004-R02/R05/R06/R18/R19/R21).
- [X] T011 Complete shared `score-fabric artifact` exception-to-exit routing and bounded JSON/text diagnostics in `src/score_sw_fabric/cli.py`; reserve exit 0 for success, exit 1 for semantic/native/coverage/drift failure or detected change, and exit 2 for malformed/unsupported/unsafe/unavailable input, with no model, approval, evidence, readiness, runtime, or production-target capability (004-R19/R21).
- [X] T012 [P] Add failing native-boundary and protected-publication cases in `tests/contract/test_artifact_native.py` for tool/profile mismatch, unavailable executable, timeout/output cap, native rejection, missing/stale export, source/export mismatch, cache/path independence, cleanup, command-injection-shaped content, locked dependency drift, and unchanged sentinel output for every exit-1/2 path (004-R01/R05/R07/R19/R21; SC004-03/06/08).

**Checkpoint**: Inputs, profiles, native invocations, digests, limits, and outputs fail closed before
any target candidate can be treated as usable.

---

## Phase 3: User Story 1 — Inspect native artifacts without losing their meaning (Priority: P1) — MVP

**Goal**: Produce a portable, source-qualified index in which native source spans and a fresh
Sphinx-Needs export agree for wrappers, contained needs, statuses, classifications, relations,
locations, and revisions.

**Independent Test**: Index representative feature, component, and analysis snapshots through the
public command and real locked native stack; every live native value/source agrees, literal example
directives stay opaque, invalid wrapper/child/relation/status cases fail, and sources remain unchanged.

### Tests for User Story 1

- [X] T013 [P] [US1] Add failing lossless-source cases in `tests/contract/test_artifact_rst.py` for UTF-8/newline preservation, directive/option/content byte and line spans, indentation/nesting, duplicate options, malformed boundaries, literal `::`, `code-block`, and `parsed-literal` opacity, live need versus example distinction, stable preimage digests, and exact unchanged rescans (AC004-01/04; 004-R03/R07–R09; SC004-01/03).
- [X] T014 [P] [US1] Add failing index/reconciliation cases in `tests/contract/test_artifact_index.py` for source-qualified duplicate IDs, case collisions, namespace/revision ambiguity, source-only/export-only records, exact document `draft|valid|invalid` versus child `valid|invalid` statuses, required options, wrapper cardinality/containment, raw version selectors, link direction/target type, imported external policy, and wrapper-valid/child-invalid separation (AC004-01–04; 004-R02/R03/R08/R09; SC004-01/03).
- [X] T015 [P] [US1] Add failing public index cases in `tests/contract/test_artifact_cli.py` for exact `artifact index` 0/1/2 exits, validated-only atomic output, bounded diagnostics, relocation/set-order equivalence, malformed/native rejection, no source/build-cache leakage, no target mutation, and fixed unevaluated capabilities (AC004-01–04/08/16; 004-R01–R03/R08/R09/R19/R21).
- [X] T016 [US1] Add feature/component/analysis real-native index cases to `tests/integration/test_artifact_native.py`; require a matching `SCORE_BAZEL_BIN`, fresh locked `needs_json` and `docs_check`, exact template/metamodel/export identity, live/literal counts, source/export reconciliation, wrapper/child results, and zero protected-source changes, and make a skip ineligible for final 004 acceptance (SC004-01/03/08).

### Implementation for User Story 1

- [X] T017 [US1] Implement the bounded lossless RST scanner in `src/score_sw_fabric/artifacts/rst.py`; record exact source/option/content/literal spans without reflow, skip need-looking text in literal-producing contexts, reject overlapping/ambiguous spans and duplicate options, and execute no include/substitution/template content (004-R02/R03/R07–R09).
- [X] T018 [US1] Implement source/native-export reconciliation and stable index construction in `src/score_sw_fabric/artifacts/index.py`; match exact source-qualified ID/version/type/title/content/status/options/relations/path/location, retain raw selectors and imported identity, derive wrapper containment by profiled file policy, and reject source-only/export-only/ambiguous records (004-R02/R03/R08/R09).
- [X] T019 [US1] Implement metamodel/profile validation in `src/score_sw_fabric/artifacts/index.py`; enforce type-specific ID/status/required-option/required-link rules, exact relation names/directions/target types/version selectors, wrapper and child independence, duplicate/case collision, external-reference policy, and deterministic findings while allowing unsupported records as opaque only when normative completeness is unchanged (004-R03/R08/R09).
- [X] T020 [US1] Implement canonical `NativeArtifactIndex` sealing and `score-fabric artifact index --request ... --out ...` in `src/score_sw_fabric/artifacts/package.py` and `src/score_sw_fabric/cli.py`; require scan, native build/export, reconciliation, source-map coverage, fixed limits, canonical digest, atomic publication, and all six capabilities `not_evaluated` (AC004-01–04/08/16; 004-R01–R03/R08/R09/R19/R21).
- [X] T021 [US1] Add independently asserted feature/component/analysis index journeys to `tests/integration/test_artifact_index.py`, covering exact identities/locations/relations, namespace ambiguity, invalid child under valid wrapper, literal examples, deterministic relocation/permutation bytes, stable findings, prior-output preservation, and no target/model/runtime/readiness side effect (SC004-01/03/06/08).

**Checkpoint**: The MVP indexes and validates native sources through their actual build/export stack
without editing them or turning the derived index into authority.

---

## Phase 4: User Story 2 — Create or update an isolated native candidate safely (Priority: P1)

**Goal**: Realize explicit template-based creates and preimage-bound scoped edits into one sealed
candidate overlay while preserving every unrelated byte and source.

**Independent Test**: Create and update representative native documents; exact intended spans change,
unrelated prose/comments/IDs/decisions/links survive, fresh native build and re-index pass, repeated
relocated generation is identical, and every invalid edit preserves prior output and sources.

### Tests for User Story 2

- [X] T022 [P] [US2] Add failing edit-operation cases in `tests/contract/test_artifact_edits.py` for exact `create_document|set_option|set_content|add_link|remove_link|insert_need`, complete explicit values, template/source/plan/rule origins, subject/anchor uniqueness, stale preimage, unsupported type/field/status/relation, ID collision, unresolved placeholder, deletion/rename/arbitrary patch prohibition, literal-example protection, and byte-exact unchanged complement (AC004-05–07; 004-R03–R07/R09; SC004-02/03).
- [X] T023 [P] [US2] Add failing overlay/package/publication cases in `tests/contract/test_artifact_package.py` and `tests/contract/test_artifact_cli.py` for complete base bindings, all new/changed UTF-8 bytes, per-edit/source-map coverage, materialized base+overlay closure, nested/self-digests, successful candidate exit 0, semantic/native exit 1, input/infrastructure exit 2, atomic replacement, and no partial package/tree (AC004-05–08/16; 004-R05–R07/R18/R19/R21).
- [X] T024 [P] [US2] Add create/update journey cases in `tests/integration/test_artifact_candidate.py` for representative feature/component/analysis templates, exact placeholder/directive realization, one allowed existing-field/link/content change, source/export re-index agreement, zero unrelated changes, deterministic relocation/permutation output, and no source/production mutation (SC004-02/06/08).
- [X] T025 [P] [US2] Add exact-maximum and one-over candidate cases in `tests/contract/test_artifact_limits.py` for 64 MiB inputs/package/declared target, 10,000 files, 2 MiB text file, 100,000 native entities, 100,000 expected obligations, 500,000 relations, 10,000 edits, 20,000 findings, 8 MiB native output, and 1,800-second configured timeout; assert stable early diagnostics and unchanged sentinel output (004-R19; SC004-03/06).

### Implementation for User Story 2

- [X] T026 [US2] Implement exact template realization and preimage-bound span transformations in `src/score_sw_fabric/artifacts/edit.py`; accept only the six version-1 operations, source every value, detect conflicts before mutation, apply in deterministic dependency order, prove the unchanged byte complement, reject unresolved placeholders/unintended changes, and return complete edit/source-map results without calling a model (004-R03–R07/R09/R19/R21).
- [X] T027 [US2] Implement candidate overlay construction, disposable materialization, post-edit native build/export/re-index/round-trip validation, complete base/overlay/source-map/report closure, canonical identity, explicit `trace_validation: not_requested`, and guarded sealing in `src/score_sw_fabric/artifacts/package.py`; no failed operation may replace prior output or modify inputs/history (004-R05–R07/R17–R21).
- [X] T028 [US2] Implement `score-fabric artifact candidate --request ... --out ...` and independent `artifact validate --candidate ... --profile ...` routing in `src/score_sw_fabric/cli.py`; validate embedded flags rather than trusting them, preserve explicit no-trace-claim handling, preserve exact 0/1/2 semantics, and expose no apply/approve/accept/run option (AC004-05–08/16; 004-R18–R21).
- [X] T029 [US2] Extend `tests/integration/test_artifact_native.py` with non-skipped real-native create/update cases for feature/component/analysis documents; require exact pinned templates, valid wrapper/contained-need statuses, preserved unrelated bytes, fresh export agreement, matching candidate receipt, and zero reference/production/model/runtime changes (SC004-02/06/08).

**Checkpoint**: Reviewable native candidate overlays can be created and updated through public
commands, but no production target is written and no structural pass becomes engineering acceptance.

---

## Phase 5: User Story 3 — Measure expected trace obligations and expose gaps (Priority: P1)

**Goal**: Freeze a complete source-cited expected set from the sealed plan and validated package,
then measure exact native allocation/verification paths without allowing deletion to improve coverage.

**Independent Test**: A closed fixture passes; removing an entire expected artifact, allocation, or
verification link retains the same denominator, lowers the correct numerator, produces the stable
gap/mismatch, publishes a blocked trace report, and returns exit 1.

### Tests for User Story 3

- [X] T030 [P] [US3] Add failing expected-set cases in `tests/contract/test_artifact_obligations.py` for every applicable plan instance, purpose/scope/disposition, exact artifact rule, every package `expected_output` and data destination classified as `native_artifact|non_native_record|external_boundary`, package source-map binding, shared/multi-artifact cardinality, missing/conflicting mapping, unresolved applicability/disposition, external authority/rationale, and proof that output declarations are not observed artifacts or acceptance (AC004-09/10/12/16; 004-R01/R02/R06/R10/R20/R21).
- [X] T031 [P] [US3] Add failing trace/coverage cases in `tests/contract/test_artifact_trace.py` for exact native hop field/direction/source/target type/version/scope, allocation, full versus explicitly partial verification, absent artifact/link, wrong-type/direction/target/external relation, wrapper/child paths, literal numerator/denominator/exclusion/unresolved/mismatched lists, exclusion authority, and deletion-invariant denominators (AC004-03/09–12; 004-R09–R15/R20; SC004-04/05).
- [X] T032 [P] [US3] Add public trace/report cases in `tests/contract/test_artifact_cli.py` for `artifact trace` success exit 0, mandatory-gap exit 1 with atomically published bounded blocked report, malformed/infrastructure exit 2 with prior report preserved, exact source citations, human-readable/machine-checkable agreement, relocation determinism, and explicit structural-only limitations/unevaluated capabilities (AC004-09–12/16; 004-R11–R15/R19–R21).

### Implementation for User Story 3

- [X] T033 [US3] Implement exact plan/package/rule joining and canonical expected-obligation derivation in `src/score_sw_fabric/artifacts/obligations.py`; freeze the set before target inspection, cover every plan instance/output/destination exactly once, preserve origin/scope/purpose/cardinality/completeness, and block missing/conflicting/unclassified authority without inferring from filenames, prose, or workflow topology (004-R01/R02/R06/R10/R20).
- [X] T034 [US3] Implement typed path matching and coverage evaluation in `src/score_sw_fabric/artifacts/trace.py`; follow only profiled native fields/directions/types/versions, distinguish full/partial/excluded/unresolved/mismatched states, retain absent items in denominators, fail every unresolved/mismatched mandatory obligation, and never interpret a relation as adequacy/evidence/approval (004-R11–R15/R20/R21).
- [X] T035 [US3] Implement canonical readable and machine-checkable `ArtifactReport` construction in `src/score_sw_fabric/artifacts/package.py`; list every obligation/path/hop/revision/source/exclusion/gap plus exact count sets, limitations, profile/input identities, and all six `not_evaluated` capability fields (004-R12/R15/R19–R21).
- [X] T036 [US3] Implement `score-fabric artifact trace --request ... --out ...` in `src/score_sw_fabric/cli.py`; publish complete blocked reports for well-formed coverage failures while preventing candidate/index replacement, preserve stable 0/1/2 semantics, and print bounded actionable summaries (004-R11–R15/R19–R21).
- [X] T037 [US3] Add closed, missing-artifact, missing/wrong allocation, missing/partial/wrong verification, allowed exclusion, external obligation, and unclassified-output journeys to `tests/integration/test_artifact_trace.py`; assert fixed denominators, exact source paths, deterministic bytes, blocked status where required, and no evidence/approval/readiness claim (SC004-04/05/06/08).

**Checkpoint**: Coverage is expected-set-first and fail-closed; removing native content can only
expose or worsen a gap, never improve the metric.

---

## Phase 6: User Story 4 — Review artifact changes and downstream impact (Priority: P2)

**Goal**: Report semantic changes, direct drift, and conservative downstream impact across native
revisions without rewriting historical acceptance or requiring Fabro.

**Independent Test**: Single requirement/interface/allocation/assumption/analysis/baseline mutations
produce exact impact sets; new unlinked/unknown dependencies expand or block; direct generated edits
are distinct from reviewed source/profile changes and cannot be adopted.

### Tests for User Story 4

- [X] T038 [P] [US4] Add failing impact cases in `tests/contract/test_artifact_impact.py` for identity/fingerprint additions/removals/modifications, stable reverse native traversal, shared-resource/allocation/interface/assumption/analysis/template/metamodel/baseline expansion rules, transitive cycles, new unlinked subjects, unknown/external dependencies, affected scopes/plan instances/reviews, deterministic shortest paths, and immutable prior accepted facts (AC004-13/14; 004-R16/R17; SC004-07).
- [X] T039 [P] [US4] Add semantic diff and drift cases in `tests/contract/test_artifact_diff_drift.py` for every baseline/wrapper/need/option-status-classification/content/relation/containment/obligation/coverage/impact/template-profile/native-validator/file-bytes category, relocation/set-order equivalence, nested/self/file/source-map damage, reviewed-source/profile rederivation, direct generated edit, and no reseal/adopt/repair behavior (AC004-08/13–15; 004-R17–R19; SC004-06–08).
- [X] T040 [P] [US4] Add public validate/diff/drift cases in `tests/contract/test_artifact_cli.py` for exact candidate/profile compatibility, readable offline report, matching/mismatched/unavailable native receipt, 0 on equivalent/clean, 1 on semantic change/drift, 2 on malformed/infrastructure failure, bounded diagnostics, read-only behavior, and six unevaluated capabilities (AC004-13–16; 004-R18/R19/R21).

### Implementation for User Story 4

- [X] T041 [US4] Implement stable index comparison, reverse-dependency traversal, and conservative rule expansion in `src/score_sw_fabric/artifacts/impact.py`; include direct/transitive/rule-expanded/newly-unlinked/unknown subjects, affected scopes/instances/reviews/blockers, terminate cycles deterministically, and record candidate staleness without editing old statuses or decisions (004-R16/R17).
- [X] T042 [P] [US4] Implement validated categorized semantic comparison and canonical `ArtifactDiff` in `src/score_sw_fabric/artifacts/diff.py`; compare typed index/candidate/report/profile/validator bindings rather than presentation formatting and emit only affected categories with exact subjects/origins (004-R17–R19).
- [X] T043 [P] [US4] Implement read-only nested-integrity and optional exact-request rederivation checks in `src/score_sw_fabric/artifacts/drift.py`; classify direct file/package edits separately from reviewed snapshot/request/template/metamodel/artifact-profile/trace-profile changes and provide no accept/repair/write path (004-R18/R19/R21).
- [X] T044 [US4] Complete `artifact validate`, `artifact diff`, and `artifact drift` public routing and stable receipts in `src/score_sw_fabric/cli.py`, integrate impact into candidate/trace reports through `src/score_sw_fabric/artifacts/package.py`, and preserve exact 0/1/2 semantics plus offline readability (AC004-13–16; 004-R15–R21).
- [X] T045 [US4] Add one-mutation-per-category impact/diff/drift journeys to `tests/integration/test_artifact_review.py`; assert expected conservative impact only, new-unlinked/unknown blocking, immutable history, exact semantic category isolation, direct-drift detection, deterministic relocation, and no target/evidence/approval/readiness/runtime effect (SC004-06–08).

**Checkpoint**: All four stories operate through public commands; native records remain independently
understandable and direct generated edits never become engineering authority.

---

## Phase 7: Cross-cutting acceptance and handoff

**Purpose**: Reconcile actual implementation, public documentation, native evidence, limits, FAB
traceability, and the boundary to increment 005.

- [X] T046 Update `schemas/README.md`, `README.md`, `docs/backlog/roadmap.md`, `docs/backlog/requirements-index.md`, and `specs/004-native-artifact-traceability/quickstart.md` with only implemented commands, exact tested limits/pins, fixture-versus-production review states, native-build prerequisites, stable exit semantics, and explicit approval/evidence/readiness/runtime/production-mutation exclusions.
- [X] T047 After T046, run AC004-01–16 and SC004-01–08 plus frozen Ruff lint/format, strict mypy, full pytest, foundation checker, public quickstart commands, offline wheel/sdist build, non-skipped locked native feature/component/analysis index and create/update builds, relocation/permutation checks, single-mutation trace/impact/diff/drift cases, and exact-maximum/one-over 64 MiB control/package/target, 10,000 files, 2 MiB file, 100,000 native entities, 100,000 expected obligations, 500,000 relations, 10,000 edits, 20,000 findings, 8 MiB native output, and 1,800-second timeout configuration; record commands/results/hashes/elapsed time/peak size/tool identities/logs/limitations and FAB-016–FAB-018 mapping in `specs/004-native-artifact-traceability/acceptance.md`.
- [X] T048 Reconcile every marker in `specs/004-native-artifact-traceability/tasks.md` with actual files/evidence and create `docs/handoff/004-to-005.md` covering implemented native/index/candidate/trace/impact contracts, exact source/profile/package identities, pending production profile/owner decisions, fixture/native evidence distinction, retained trust boundaries, evidence/gate prerequisites, and the recommended model for increment 005; stop before FAB-019–FAB-023 implementation.

---

## Dependencies and execution order

### Phase dependencies

- Phase 1 starts immediately. After T001, T002–T005 touch independent schema, profile/policy,
  fixture, and support paths and may proceed in parallel.
- Phase 2 depends on Phase 1. T006 and T012 are parallel failing-test surfaces; T007 precedes T008
  and T010, while T009 can proceed independently after profiles/fixtures exist. Phase 2 blocks stories.
- US1 depends on Phase 2 and is the MVP. T013–T015 can be authored in parallel; T016 follows fixture
  readiness. Implementation proceeds scanner → reconciliation → validation → package/CLI → integration.
- US2 depends on US1's stable scanner/index. T022–T025 are file-safe parallel test tasks; candidate
  implementation proceeds edits → package/native/re-index → CLI → real-native evidence.
- US3 depends on US1 index and foundational 002/003 readers, but its contract tests may proceed beside
  US2. T033 precedes T034–T036; T037 needs the public trace path. Candidate-integrated trace uses US2.
- US4 depends on stable indexes and trace/report shapes. T038–T040 can be authored in parallel;
  T042 and T043 can implement diff/drift in parallel after tests while T041 implements impact.
- Phase 7 depends on all desired stories. T047 must not pass if any real native case is skipped;
  T048 follows the final acceptance record and must preserve unresolved decisions honestly.

### User story dependency graph

```text
Setup -> Foundation -> US1 inspection (MVP)
                         |-> US2 candidate edits -----|
                         |-> US3 expected trace ------|-> US4 impact/diff/drift
```

US1 is independently demonstrable. US2 and US3 each deliver a separately testable public journey
over the stable index. US4 consumes their stable records but remains independently testable with
sealed fixture candidates/indexes.

## Parallel execution examples

### User Story 1

```text
T013: lossless RST scanner cases in tests/contract/test_artifact_rst.py
T014: native index/reconciliation cases in tests/contract/test_artifact_index.py
T015: public index cases in tests/contract/test_artifact_cli.py
```

### User Story 2

```text
T022: typed edit cases in tests/contract/test_artifact_edits.py
T023: overlay/publication cases in test_artifact_package.py and test_artifact_cli.py
T024: create/update journeys in tests/integration/test_artifact_candidate.py
T025: exact boundary cases in tests/contract/test_artifact_limits.py
```

### User Story 3

```text
T030: expected-set cases in tests/contract/test_artifact_obligations.py
T031: trace and coverage cases in tests/contract/test_artifact_trace.py
T032: public blocked-report cases in tests/contract/test_artifact_cli.py
```

### User Story 4

```text
T038: conservative impact cases in tests/contract/test_artifact_impact.py
T039: semantic diff/drift cases in tests/contract/test_artifact_diff_drift.py
T040: public validate/diff/drift cases in tests/contract/test_artifact_cli.py
T042: semantic comparison in src/score_sw_fabric/artifacts/diff.py
T043: drift verification in src/score_sw_fabric/artifacts/drift.py
```

Tasks sharing `src/score_sw_fabric/cli.py`, `package.py`, or `test_artifact_cli.py` are coordinated
sequentially despite parallelizable case design. `[P]` marks only safe file ownership after prerequisites.

## Implementation strategy

### MVP first

1. Complete setup and foundational validation boundaries.
2. Implement US1 through real native feature/component/analysis indexing.
3. Stop and verify source/export agreement, wrapper/child separation, deterministic bytes, prior-output
   preservation, and zero source/model/runtime/readiness side effects.

### Incremental delivery

1. Add US2 scoped candidate edits and real-native round trips.
2. Add US3 expected-set trace coverage and blocked gap reports.
3. Add US4 conservative impact, semantic diff, and direct drift.
4. Run cross-cutting native/limit acceptance and hand off only evidence/gate work to 005.

Production target mutation, artifact approval, evidence trust, engineering acceptance, readiness,
workflow registration/execution, release, and deployment remain outside every task.

## Requirement coverage index

| Requirement | Primary tasks |
| --- | --- |
| 004-R01 | T002, T003, T006–T009, T020, T030, T033 |
| 004-R02 | T007, T017–T020, T030, T033 |
| 004-R03 | T002, T003, T007, T013, T014, T017–T019, T022, T026 |
| 004-R04 | T003, T004, T006, T008, T022, T026, T029 |
| 004-R05 | T006, T008–T010, T022, T023, T026, T027 |
| 004-R06 | T005, T007, T010, T022, T023, T026, T027, T030, T033 |
| 004-R07 | T009, T013, T017, T022–T029 |
| 004-R08 | T002, T007, T014, T018–T021, T029 |
| 004-R09 | T003, T007, T014, T018, T019, T022, T026, T031 |
| 004-R10 | T003, T007, T030, T033 |
| 004-R11 | T030–T037 |
| 004-R12 | T030–T037 |
| 004-R13 | T003, T030, T031, T033, T034, T037 |
| 004-R14 | T003, T007, T031, T034, T037 |
| 004-R15 | T002, T007, T031, T032, T034–T037, T040, T044 |
| 004-R16 | T003, T007, T038, T041, T045 |
| 004-R17 | T007, T027, T038, T039, T041–T045 |
| 004-R18 | T007, T010, T023, T027, T028, T039, T040, T042–T045 |
| 004-R19 | T002, T003, T005–T012, T015, T020, T023–T028, T032, T035, T036, T039, T040, T042–T044 |
| 004-R20 | T002, T030–T037 |
| 004-R21 | T001–T003, T006–T012, T015, T016, T020, T021, T023–T029, T030, T032–T037, T039, T040, T043–T048 |
