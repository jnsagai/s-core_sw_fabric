# Tasks: Change impact, freshness and bounded AI context

Input: spec/plan/research/data-model/contracts. Negative-first tests required. Human-owned
reviews remain unchecked. Current implementation instruction authorizes development while
reviewer-owned requirements checklist remains pending; this is not engineering acceptance.

## Phase 1: Setup

- [x] T001 Preserve owner v3 brief and resolve Spec Kit templates in S_CORE_SW_FABRIC_TOKEN_OPTIMIZATION_SPEC_KIT_CODEX_BRIEF_v3_NO_JEV.md.
- [x] T002 Specify/plan/checklist/analyze 011 and constitution proposal in specs/011-change-impact-and-freshness/.

## Phase 2: Foundational contracts

- [x] T003 Add exact safe-path/digest/byte-estimate helpers in src/score_sw_fabric/optimization/common.py (FR-017).
- [x] T004 Define explicit opt-in policy and schemas in policies/optimization-v1.yaml and schemas/optimization-*-v1.schema.json (FR-002/010/017).

## Phase 3: US1 — Evidence containment

Independent test: 1 MiB one-line SARIF, traversal/drift and persistent stage exhaustion.

- [x] T005 [US1] Write negative-first evidence/firewall tests in tests/contract/test_optimization_evidence.py (FR-001/002/016).
- [x] T006 [US1] Implement bounded native findings/JSON queries in src/score_sw_fabric/optimization/evidence_query.py (FR-001).
- [x] T007 [US1] Retain full output and enforce persistent result/stage budgets in src/score_sw_fabric/optimization/tool_results.py (FR-002).
- [x] T008 [US1] Deny generic raw reads/broad search in src/score_sw_fabric/optimization/firewall.py and docs/handoff/someip-84/factory/guard_agent_tools.py (FR-016).
- [x] T009 [US1] Deliver summary-only feedback in docs/handoff/someip-84/factory/collect_obligations.py and overnight_hooks.py (FR-003).
- [x] T010 [US1] Execute bounded stdio service and pre-tool hook integration in src/score_sw_fabric/optimization/server.py and tests/integration/test_optimization_service.py (FR-016).

## Phase 4: US2 — Telemetry and baseline

Independent test: missing usage stays null and impossible cache splits refuse.

- [x] T011 [US2] Test and implement nullable per-call usage/aggregation in src/score_sw_fabric/optimization/telemetry.py and tests/contract/test_optimization_governor.py (FR-004).
- [x] T012 [US2] Retain five pre-budget context baselines in specs/011-change-impact-and-freshness/evidence/benchmark/baseline.json (FR-014).

## Phase 5: US3 — Transitive impact/freshness

Independent test: removed edges/cycles/unknown dependencies cannot narrow scope.

- [x] T013 [US3] Test both-baseline reachability/freshness in tests/contract/test_optimization_context.py (FR-005).
- [x] T014 [US3] Implement conservative old/new impact and baseline-vector invalidation in src/score_sw_fabric/optimization/impact.py and src/score_sw_fabric/artifacts/impact.py (FR-005).

## Phase 6: US4 — Classification

Independent test: S0–S4 cases, unresolved scope, safety/interface and fanout.

- [x] T015 [US4] Test and implement deterministic classifier in src/score_sw_fabric/optimization/task_classification.py and tests/contract/test_optimization_context.py (FR-006).

## Phase 7: US5 — Manifest/lazy context

Independent test: stale manifest blocks; required safety/L0 cannot trim; optional L2 omitted.

- [x] T016 [US5] Implement digest-bound manifest in src/score_sw_fabric/optimization/context_manifest.py (FR-007).
- [x] T017 [US5] Implement context accounting/retrieval/observations in src/score_sw_fabric/optimization/context_budget.py and src/score_sw_fabric/agents/context.py (FR-008).

## Phase 8: US6 — Lazy Skills

Independent test: modified/missing/unselected Skill refuses, reference loads only on demand.

- [x] T018 [US6] Create eight narrow Skills and registry in .agents/skills/score-*/SKILL.md and profiles/optimization-skills-v1.yaml (FR-009).
- [x] T019 [US6] Implement bounded selection and explicit runtime renderer in src/score_sw_fabric/optimization/skill_selection.py (FR-009).

## Phase 9: US7 — Governor/routing

Independent test: unknown usage, missing trigger, ceiling exhaustion and human gates refuse.

- [x] T020 [US7] Test and implement class governor in src/score_sw_fabric/optimization/token_governor.py and tests/contract/test_optimization_governor.py (FR-010).
- [x] T021 [US7] Route existing admitted catalogue profiles and conditional critic in src/score_sw_fabric/optimization/model_router.py and src/score_sw_fabric/agents/admission.py (FR-010/017).

## Phase 10: US8 — Structured stage/review output

Independent test: output schema rejects prose; required rationale stays intact; stable prefixes.

- [x] T022 [US8] Implement common prompt/result/review pack in src/score_sw_fabric/optimization/prompts.py and review_pack.py (FR-011).
- [x] T023 [US8] Apply silent common prompt contract in src/score_sw_fabric/agents/roles.py and docs/handoff/someip-84/factory/prepare_overnight_queue.py (FR-011).

## Phase 11: US9 — Progress/stops

Independent test: repeated failures/queries, unchanged correction and evidence-only refresh.

- [x] T024 [US9] Test and implement progress/stops in src/score_sw_fabric/optimization/progress.py and tests/contract/test_optimization_governor.py (FR-012).

## Phase 12: US10 — Derived modes

Independent test: five modes retain exact mandatory collectors/human gates.

- [x] T025 [US10] Implement derived mode projection in src/score_sw_fabric/optimization/workflow_modes.py and tests/contract/test_optimization_governor.py (FR-013).

## Phase 13: US11 — Benchmarks/audit

Independent test: B1–B5 deterministic outcomes/checks/IDs/evidence remain equal, estimates labelled.

- [x] T026 [US11] Implement five baseline/optimized benchmarks in src/score_sw_fabric/optimization/benchmark.py and evidence/benchmark/ (FR-014).
- [x] T027 [US11] Implement consistency audit/coverage map in src/score_sw_fabric/optimization/audit.py and specs/011-change-impact-and-freshness/coverage.yaml (FR-015).
- [x] T028 [US11] Add operator CLI in src/score_sw_fabric/optimization/cli.py and src/score_sw_fabric/cli.py (FR-017).

## Phase 14: Validation and reconciliation

- [x] T029 Execute native conformance and full regression with pinned tools; record logs in specs/011-change-impact-and-freshness/evidence/ (SC-002/004).
- [x] T030 Reconcile README, docs/backlog/roadmap.md, requirements-index.md, docs/architecture/0014-bounded-context-and-procedures.md and acceptance.md (FR-015).
- [x] T031 Run final analyze/converge and audit against all spec/plan/tasks in specs/011-change-impact-and-freshness/ (SC-004).
- [ ] T032 HUMAN: Review constitution proposal, optimization policy/Skill mapping and requirements checklist in .specify/memory/constitution.md and specs/011-change-impact-and-freshness/checklists/optimization.md.
- [ ] T033 HUMAN/EXTERNAL: Authorize and measure native guarded Fabro stage activation and B1–B5 live provider usage; verify 60–80% routine uncached reduction in specs/011-change-impact-and-freshness/acceptance.md (FR-014/016).

## Dependencies and implementation strategy

Setup → contracts → US1 → US2 baseline → US3 → US4 → US5 → US6 → US7 → US8 → US9 →
US10 → US11 → full validation. US1 is the independently testable emergency MVP. Tests precede
code or accompany interface updates. Independent read-only research runs in parallel; no concurrent
file edits. Converge after each major phase and append only new uncovered work. Human tasks do not
block local implementation or imply authority; default live execution remains disabled; US12 explicitly permits scoped qualification while T033 remains open.

## Phase 15: Convergence

- [x] T034 Bind bounded context/governor to reviewed compiler projections before IR generation in src/score_sw_fabric/compiler/optimization.py and tests/contract/test_optimization_governor.py per FR-013/016 (partial). Preserve every command/human node and native edge/loop; command-only modes reject supplied agent nodes instead of deleting obligations.

## Phase 16: Convergence

- [x] T035 Align generated collector/repair command and expected-output paths with actual summary-only feedback, enforce the complete serialized summary ceiling, and test host evidence retention versus copied agent feedback in docs/handoff/someip-84/factory/ and tests/contract/test_optimization_evidence.py per FR-003/016 (partial).

## Phase 17: Convergence

- [x] T036 Expose classifier thresholds and conservative precedence in policies/optimization-v1.yaml, bind them to the classification digest and self-audit, and test that broad sensitive work requires S4 scope authorization in src/score_sw_fabric/optimization/task_classification.py and tests/contract/test_optimization_context.py per FR-006/015 (partial).

## Phase 18: Scoped native qualification continuation

- [x] T037 Draft the T032 review subject and exact artifact bindings in specs/011-change-impact-and-freshness/review-draft.md; record owner continuation and Flash-only scope without accepting human items (FR-015/018).
- [x] T038 Test and implement host-private activation bindings and a DeepSeek-only bounded transport meter in src/score_sw_fabric/optimization/activation.py, provider_boundary.py and tests/contract/test_optimization_activation.py (FR-018).
- [x] T039 Measure real native stage guard/service behavior in a separate disposable Fabro server, initially without provider calls, and retain new evidence in specs/011-change-impact-and-freshness/evidence/qualification/ (FR-016/018).
- [x] T040 Run authorized Flash-only paired B1–B5 development measurements within ten requests and $0.10; stop on unmeasured required usage and retain raw native/provider records separately (FR-014/018).
- [x] T041 Reconcile source-derived price bounds, native activation limitations, tests, review draft, contracts, coverage, ADR/roadmap/acceptance and final analyze/converge without checking T032/T033 (FR-015/018).

## Phase 19: Measured overhead convergence

- [x] T042 Remove declarations for already-denied native tools before experimental provider transmission using a checksum-pinned bounded-tool selection; retain every message, allowed declaration and original/request digest, and enforce the pinned governor per task in src/score_sw_fabric/optimization/provider_boundary.py, activation.py and tests/contract/test_optimization_activation.py (FR-016/018). Replay real native requests without further paid calls; live requalification remains T033.
