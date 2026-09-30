# Tasks: Applicability and work-product planning

**Input**: Design documents from `specs/002-applicability-and-work-product-plan/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/planning.md`, `quickstart.md`

**Tests**: Required by AC002-01–16. Contract tests precede implementation in each phase.

**Organization**: Tasks are grouped by user story and preserve the production authority
boundary: local decision references can never promote reuse or tailoring to effective status.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel after its phase prerequisites because it affects different files.
- **[Story]**: User story from `spec.md`.
- Every task names its concrete file paths and acceptance/requirement coverage.

## Phase 1: Setup and contract surfaces

**Purpose**: Establish versioned planning schemas and source-cited fixtures without changing dependencies.

- [x] T001 Create `src/score_sw_fabric/planning/__init__.py` and extend `.gitignore` only if generated planning build paths are not already covered.
- [x] T002 [P] Publish strict version-1 input/output envelopes in `schemas/intake.schema.json`, `schemas/planning-profile.schema.json`, `schemas/applicability-mapping.schema.json`, `schemas/artifact-inventory.schema.json`, `schemas/decision-references.schema.json`, and `schemas/work-product-plan.schema.json`; reject unknown normative fields and require exact integer versions per 002-R01/R14.
- [x] T003 [P] Add the review-draft profile and source-cited 74-work-product coverage configuration in `profiles/cpp17-review-draft-v1.yaml` and `policies/s_core_applicability_v1.yaml`, preserving the `wp__fdr_reports_security` versus template `wp__fdr_reports` conflict as unresolved rather than normalizing it (AC002-05–08).
- [x] T004 [P] Create licensed, clearly fixture-origin planning scenarios and expected sets under `tests/fixtures/planning/` for new component, reused component, security feature, multi-scope/review purposes, and invalid inputs; no fixture may expose a trusted-authority flag (AC002-01–16).

---

## Phase 2: Foundational validated inputs and catalogue boundary

**Purpose**: Block every story from consuming unbounded, ambiguous, or unselected inputs.

**Critical**: Complete this phase before any user-story planning behavior.

- [x] T005 [P] Add failing catalogue-reader contract cases in `tests/contract/test_catalogue_reader.py` for duplicate JSON keys, transport/self/selected digest mismatch including resealed alteration, duplicate qualified identities, invalid source/type/relation endpoints, multiple revision ambiguity, and the 64 MiB bound (AC002-14/15).
- [x] T006 Implement the sealed catalogue loader/index in `src/score_sw_fabric/catalog/reader.py`, reusing bounded parsing and canonical bytes while verifying exact v1 shape, digest excluding only `digest`, caller-selected baseline digest, source-qualified identities and relation endpoints (002-R03/R05/R14).
- [x] T007 [P] Add failing planning input/path tests in `tests/contract/test_planning_inputs.py` for exact version/type checks, duplicate keys, cyclic/ambiguous scope ownership, unsafe paths, hardlink aliases, symlink parents, source-root outputs and prior-output preservation (AC002-04/15).
- [x] T008 Implement strict dataclass/TypedDict planning shapes in `src/score_sw_fabric/planning/models.py` for Intake, ScopeNode, profile/rules, CoverageEntry, ArtifactBinding, DecisionReference/Assessment, WorkProductInstance, Finding and PlanResult; preserve `selected/outside_scope/unresolved` coverage separately from `required/unresolved` instance applicability.
- [x] T009 Implement bounded YAML/JSON loading, semantic normalization/digests and path confinement in `src/score_sw_fabric/planning/reader.py`; enforce at most 1,000 scopes, 10,000 rules, 100,000 coverage rows, 10,000 instances and 100,000 edges, with transport hashes excluded from canonical plan semantics (002-R01/R13/R14).

**Checkpoint**: Corrupt or unsafe inputs fail before applicability logic and cannot replace a valid result.

---

## Phase 3: User Story 1 — See obligations for a change (Priority: P1) — MVP

**Goal**: Derive complete expected instances independently of existing documents, including scope fan-out, shared parents and distinct reviews.

**Independent Test**: New component plus two-component/module context produces exact scoped instances; deleting inventory changes disposition rather than expected membership.

- [x] T010 [P] [US1] Add failing coverage/closure tests in `tests/contract/test_planning_coverage.py` for new component, distinct formal-review purposes, shared parent deduplication, explicit external owners, partial inventory, cycles/fixed points and missing scope context (AC002-01–04; 002-R03–R07/R12).
- [x] T011 [US1] Implement finite whitelisted predicate evaluation and all-work-product/scope coverage in `src/score_sw_fabric/planning/mapping.py`; only `eq`/`in` conjunctions and named scope selectors are allowed, and unmatched pairs emit `MAPPING_COVERAGE_GAP` rather than exclusion.
- [x] T012 [US1] Implement stable structured instance identity and sorted fixed-point dependency expansion in `src/score_sw_fabric/planning/closure.py`; versions/baselines remain bindings, shared instances union agreeing origins/requesters, and size-limited drafts remain deterministically blocked.
- [x] T013 [US1] Implement create/update/external/unresolved inventory matching in `src/score_sw_fabric/planning/dispositions.py`; complete-inventory absence permits create, partial-inventory absence remains unresolved, and external obligations retain evidence owed (AC002-03/04).
- [x] T014 [US1] Add the independently asserted new-component/multi-scope integration journey to `tests/integration/test_work_product_plan.py`, proving exact expected set, purpose fan-out and deletion resistance (SC002-02/03).

**Checkpoint**: US1 yields an independently testable draft obligation plan without workflow compilation.

---

## Phase 4: User Story 2 — Keep unknown or conflicting applicability visible (Priority: P1)

**Goal**: Retain unsupported profiles, unknown facts, coverage gaps and conflicting native sources as actionable blockers.

**Independent Test**: Unknown classification, unmapped work product and security-FDR conflict each retain candidates and stable findings.

- [x] T015 [P] [US2] Add failing profile/conflict tests in `tests/contract/test_planning_coverage.py` for unknown/unsupported language, safety and security facts, security/non-security interactions, unmapped native additions, audit-tailoring prose, exact active-revision selection and simultaneous-revision ambiguity (AC002-05–08/14).
- [x] T016 [US2] Complete profile and revision selection in `src/score_sw_fabric/planning/mapping.py`; never choose latest implicitly, record non-selected revision coverage, and emit stable `PROFILE_UNSUPPORTED`, `PROFILE_REVISION_AMBIGUOUS`, `NATIVE_SOURCE_CONFLICT` and coverage findings.
- [x] T017 [US2] Extend `tests/integration/test_work_product_plan.py` with the source-backed security-feature scenario over all 74 native work products, proving the real FDR conflict and unresolved audit statement remain explicit (SC002-01/02/04).

**Checkpoint**: US2 cannot turn missing or conflicting source facts into non-applicability.

---

## Phase 5: User Story 3 — Propose reuse and tailoring with evidence (Priority: P2)

**Goal**: Explain reuse/tailoring proposals while keeping effective status unresolved until protected authority verification exists.

**Independent Test**: New, reused and modified-reused cases differ, while stale bindings, missing impact analysis and local approval claims retain obligations.

- [x] T018 [P] [US3] Add failing disposition tests in `tests/contract/test_planning_dispositions.py` for new/reused/modified-reused routes, Q/QR/NQ, separate Safety Manager classification approval/change-request/artifact subjects, stale reuse, tailoring permission and missing/stale impact analysis, forged local acceptance, and cross-scope analysis coverage (AC002-09–12/16).
- [x] T019 [US3] Complete reuse/tailoring checks in `src/score_sw_fabric/planning/dispositions.py`; requested/effective dispositions remain distinct, production authority is always unavailable in 002, and findings include `AUTHORITY_UNVERIFIED`, classification/change-request prerequisites, stale reuse and tailoring impact/permission codes.
- [x] T020 [US3] Add the reused-component integration scenario to `tests/integration/test_work_product_plan.py`, asserting retained logical identities, exact bindings and expected authority blockers without fixture trust switches (SC002-01/04/06).

**Checkpoint**: US3 produces reviewable proposals and never fabricates accepted decisions.

---

## Phase 6: User Story 4 — Review and reproduce the plan (Priority: P2)

**Goal**: Produce deterministic sealed draft plans with protected atomic output and stable diagnostics.

**Independent Test**: Relocation and independent input permutations preserve plan bytes; semantic changes and selected baselines change identity; malformed requests preserve prior output.

- [x] T021 [P] [US4] Add failing export/CLI tests in `tests/contract/test_planning_cli.py` for each auxiliary document permutation, relocation, semantic sensitivity, deterministic closure-limit findings, stable instance IDs across native revision changes, wrong/resealed selected catalogue, dangling rule exit 2 versus missing context exit 1, all aliases/source roots and forged decision flags (AC002-13–16).
- [x] T022 [US4] Implement canonical sealed plan export and protected atomic writer in `src/score_sw_fabric/planning/export.py`; bind normalized semantic digests, sort worklists/set-like data before evaluation, use identity-based sealed diagnostic locations and protect all inputs/hardlinks/reference roots.
- [x] T023 [US4] Implement `score-fabric plan --input INTAKE.yaml --out PLAN.json [--json]` in `src/score_sw_fabric/cli.py` with exits 0 complete draft, 1 blocked draft written, and 2 invalid/infrastructure with prior output preserved; always report `plan_kind:draft` and `engineering_readiness:not_evaluated`.
- [x] T024 [US4] Complete `tests/integration/test_work_product_plan.py` with full deterministic scenarios and assert no output can claim engineering acceptance, release readiness, workflow scheduling or satisfied external evidence (SC002-05/06).

**Checkpoint**: All four stories work through the public CLI with documented fail-closed semantics.

---

## Phase 7: Cross-cutting validation and handoff

**Purpose**: Reconcile real outcomes, documentation, traceability and package quality without starting increment 003.

- [x] T025 [P] Update `schemas/README.md`, `README.md`, `docs/backlog/roadmap.md`, `docs/backlog/requirements-index.md`, and `specs/002-applicability-and-work-product-plan/quickstart.md` with only tested commands, supported schema/profile limits and explicit expected blocked scenarios.
- [x] T026 Run every AC002-01–16 scenario plus frozen Ruff lint/format, strict mypy, default and source-backed pytest, foundation checker, CLI examples and offline wheel/sdist build; record exact outcomes/hashes in `specs/002-applicability-and-work-product-plan/acceptance.md`.
- [x] T027 Reconcile every task marker against actual files/results and create `docs/handoff/002-to-003.md` with implementation boundaries, unresolved target decisions, source conflict, next compiler prerequisites and a model recommendation; stop before 003.

---

## Dependencies and execution order

- Phase 1 has no code dependencies; T002–T004 can proceed in parallel after T001.
- Phase 2 depends on Phase 1 contracts/fixtures. T005 and T007 are parallel failing-test tasks; T006 then satisfies T005, while T008/T009 satisfy T007.
- US1 depends on all foundational tasks and supplies the minimum useful planner.
- US2 depends on the US1 coverage engine but remains independently verifiable with conflict/unknown scenarios.
- US3 depends on foundational models and inventory matching; it can proceed alongside US2 after US1 core identities exist.
- US4 depends on the story services and is the public integration/export layer.
- Phase 7 depends on all desired stories and actual validation results.

## Parallel examples

After T001, T002, T003 and T004 affect independent schema/config/fixture paths. After their
shared prerequisites, T005 and T007 create independent foundational contract tests. After US1,
US2 coverage tests/implementation and US3 disposition tests/implementation touch different
modules and may proceed in parallel before US4 integrates them.

## Implementation strategy

1. Complete Setup and Foundation, verifying failing contract tests before implementation.
2. Deliver US1 as the MVP: exact expected set and dispositions independent of inventory.
3. Add US2 conservative coverage/conflict behavior and US3 evidence-bound proposals.
4. Add US4 canonical output/CLI only after core results are stable.
5. Run complete acceptance, update only evidence-backed status, and stop before 003.

No task implements a scheduler, native artifact writer, protected decision service, model call,
engineering gate, release evaluation or automatic human approval.
