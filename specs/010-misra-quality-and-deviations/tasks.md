# Tasks: C++ quality, MISRA, and deviations

**Input**: [spec](spec.md), [plan](plan.md), [research](research.md),
[data model](data-model.md), [contract](contracts/quality.md), [quickstart](quickstart.md).

**Status**: Scoped adapter slices are implemented below. Original full-increment tasks remain
unchecked unless their entire stated scope is complete. Human acceptance remains pending.
Installation evidence is separate from adapter implementation and acceptance.
Tests are required by the spec. Write the relevant negative tests before implementation.
`[P]` identifies independent files within the stated phase, not authorization for agents.

## Phase 1: Setup

- [ ] T001 Record pinned native policies, license notices, installed tool identities and compiled-pack/source discrepancy in profiles/s-core-quality-v1.yaml; use unknown mapping/category defaults (010-R01/R09/R11).
- [ ] T002 Define exact version 1 field names, required/nullable fields and enums for all five requests and records in specs/010-misra-quality-and-deviations/contracts/quality.md and schemas/quality-*.schema.json before validator implementation (010-R11).

## Phase 2: Foundation

- [ ] T003 Add strict request/profile/digest/path/refusal tests in tests/contract/test_quality_contracts.py; reject duplicate/unknown/missing fields, unsafe roots, malformed selections and changed prior output (010-R02/R11).
- [ ] T004 Implement shared records and bounds in src/score_sw_fabric/quality/models.py: control request at most 1 MiB, 500 source files, 32 tools; native output at most 16 MiB per artifact and 64 MiB combined, with bounded prefix/full-stream digest on truncation; at most 10000 findings, 1000 guideline rows, 1000 dispositions, 20 decision references; timeout integer 1–3600 seconds; no retries; schema_version 1 and engineering_readiness not_evaluated (010-R02/R10/R11).
- [ ] T005 Implement strict sourced profile loading in src/score_sw_fabric/quality/profile.py and candidate profile profiles/cpp17-quality-local-v1.yaml; keep mapping_state unknown by default, decision_policy_ref null, primary/complementary roles, explicit C++17/MISRA edition, native statuses and suppression refs (010-R01/R05/R09).
- [ ] T006 Add shared sealed fixtures and source manifests in tests/quality_support.py and tests/fixtures/quality/; label fixtures and local origins distinctly, with no production authority or fabricated guideline text (010-R10/R11).

## Phase 3: US1 — Available checks and capability gaps (P1, MVP)

**Goal**: Run real selected checks and retain capability gaps.
**Independent test**: Seed a defect, collect native output, fix/rerun with changed baseline;
request missing/unsupported tools and incompatible sanitizer combinations (AC010-01–04).

- [ ] T007 [P] [US1] Add capability, drift, bounded output/timeout and disposable-copy tests in tests/contract/test_quality_execution.py, including unchanged protected inputs (010-R01/R02/R06/R09).
- [ ] T008 [P] [US1] Add seeded/corrected C++ sources and actual Clang-Tidy, optional Cppcheck and separate ASan/UBSan integration checks in tests/integration/test_quality_tools.py and tests/fixtures/quality/seeded/, corrected/ and sanitizers/; require real native findings and fresh correction, never a fixture substitute (SC010-01; 010-R02/R06).
- [ ] T009 [US1] Implement measured capability inventory in src/score_sw_fabric/quality/capabilities.py with available/unavailable/unsupported/unknown states, tool hashes/versions, expanded checks/effective config, pack/suite identities and eligibility/qualification gaps (010-R01/R09).
- [ ] T010 [US1] Implement frozen source/include/generated-input and expected-unit manifests, inspected hooks, disposable copies and bounded adapter-owned argument execution in src/score_sw_fabric/quality/runner.py; retain phases/outputs/configs/digests, compiler/runtime/suppression settings and completed/findings/incomplete/unavailable/failed outcomes (010-R02/R03/R06/R11).
- [ ] T011 [US1] Add gated CodeQL phase execution to src/score_sw_fabric/quality/runner.py only after exact CLI/library/pack/suite/config/patch identity and source/build reconciliation, eligible-use evidence and compatible reporting prerequisites; isolate user/cache, preserve every phase failure/filter/exclusion, and publish unknown prerequisites as blocked (010-R03/R09).
- [ ] T012 [US1] Add genuine environment-selected CodeQL/native-report integration in tests/integration/test_quality_codeql.py; record unmet prerequisites explicitly and retain original SARIF/reports when eligible; unavailable runs stay unmet acceptance rather than replaced fixtures (010-R03/R09).
- [ ] T013 [US1] Wire quality capabilities/run and stable 0/1/2 outcomes into src/score_sw_fabric/cli.py, preserving previous output on rejected selections (010-R11).

## Phase 4: US2 — Native output and extraction (P1)

**Goal**: Preserve native findings and refuse inadequate clean evidence.
**Independent test**: Import original bytes and compare expected/extracted units;
empty/partial/unknown extraction and failed report/query phases block adequacy (AC010-05–08).

- [x] T014 [P] [US2] Add native YAML/XML/SARIF tests in tests/contract/test_quality_native_outputs.py for multiple SARIF runs, all location kinds, duplicate fingerprints at different locations, deduplication contributors, suppression fields, bad external paths and malformed/truncated bytes (SC010-02; 010-R04/R08/R11).
- [x] T015 [P] [US2] Add extraction cases in tests/contract/test_quality_extraction.py and tests/fixtures/quality/extraction/ for empty/partial/unknown expected sets, unexplained exclusions, failed queries/reports and zero outer exit with inner failures (SC010-03; 010-R03/R09).
- [x] T016 [US2] Implement bounded original-format import/normalization in src/score_sw_fabric/quality/native_outputs.py; preserve native IDs, severities, all locations, fingerprints, raw suppression data and every contributing result; deduplicate only same tool/check/baseline/location/message (010-R04/R08).
- [x] T017 [US2] Implement expected/processed/extracted unit comparison in src/score_sw_fabric/quality/extraction.py with adequate/incomplete/unknown states; empty/partial/unknown scope, missing reports, truncation and failed mandatory phases block adequacy (010-R03/R09).
- [x] T018 [US2] Wire quality import into src/score_sw_fabric/cli.py; enforce original byte/tool/pack/suite/config/baseline identity and imported_unverified origin, expose source/result references and baseline drift without upgrading authority (010-R04/R06/R10/R11).

## Phase 5: US3 — Dispositions and review proposals (P1)

**Goal**: Keep drafts pending, corrections fresh and decisions exactly scoped.
**Independent test**: Exercise self-approved, wrong-subject, expired, stale and prohibited
records; only independently replayed exact fixture decisions can yield accepted_fixture (AC010-09–12).

- [ ] T019 [P] [US3] Add correction/staleness/history tests in tests/contract/test_quality_dispositions.py including old, filtered/incomplete and changed-policy results, tracked constructs and unverified names/dates (010-R06/R07/R08).
- [x] T020 [P] [US3] Add 005 replay/category/scope/validity tests in tests/contract/test_quality_decisions.py and tests/fixtures/quality/dispositions/; self-approval, cross-subject replay, unknown/prohibited categories and broad suppressions must remain unresolved; positive cases are fixture_contract only (SC010-05; 010-R07/R08/R10).
- [ ] T021 [US3] Implement draft disposition/history and fresh adequately analyzed correction in src/score_sw_fabric/quality/dispositions.py with open/pending_review/corrected/accepted_fixture/stale/blocked states; retain rationale, impact, alternatives, compensating evidence, scope, expiry and native provenance (010-R06/R07).
- [x] T022 [US3] Bridge independent 005 replay to exact disposition/finding/rule/construct/source/tool/policy closure in src/score_sw_fabric/quality/dispositions.py; enforce adopted category/scope/authority/validity policy and block production while 005 T009 remains unavailable (010-R07/R08/R09/R10).

## Phase 6: US4 — Coverage and compliance blockers (P1)

**Goal**: Show every declared obligation or an explicit unknown denominator.
**Independent test**: Clean complementary results plus missing mapping/primary capability/manual
review/authority yield blocked or not_evaluated, with a portable pending-human packet (AC010-13–15).

- [x] T023 [P] [US4] Add coverage tests in tests/contract/test_quality_coverage.py: unknown denominator, missing declared rows, unsupported/audit/manual/excluded mechanisms and changed applicability remain visible; zero accepted claims with required gaps (SC010-04; 010-R05/R09).
- [ ] T024 [P] [US4] Add portable packet/assessment tests in tests/contract/test_quality_assessment.py for raw-byte/source/license closure, all origins, pending_human answers, fixture/protected separation and positive local findings never implying production readiness (010-R09/R10/R11).
- [x] T025 [US4] Implement coverage matrix in src/score_sw_fabric/quality/coverage.py with unknown/declared scope and covered/findings_open/pending_manual/unsupported/excluded_pending_review/unknown states; bind categories/applicability/mechanisms/limitations to supplied source refs (010-R05/R09).
- [x] T026 [US4] Implement portable current/prior-run, baseline/output/extraction/matrix/disposition/license closure and pending_human review questions in src/score_sw_fabric/quality/packet.py; retain all unresolved history and import/local/fixture origins (010-R10/R11).
- [ ] T027 [US4] Implement independent compliance evaluation in src/score_sw_fabric/quality/assessment.py with fixture_contract/production domains and pass/fail/blocked/not_evaluated outcomes; required missing capabilities/extraction/coverage/decisions block claims (010-R05/R07/R09/R10).
- [ ] T028 [US4] Wire quality packet/assess into src/score_sw_fabric/cli.py with schema-checked atomic publication and deterministic 0/1/2 exits (010-R11).

## Phase 7: Cross-cutting validation and handoff

- [ ] T029 Verify pinned source/config hashes and read-only native repository status in tests/integration/test_quality_native_sources.py; record absent native CSV and unresolved compiled-pack/source relationship without inventing mappings (010-R01/R02/R11).
- [ ] T030 Run uv sync --frozen, Ruff, mypy, pytest, uv run --frozen python scripts/check_foundation.py and uv build; record exact commands/outcomes, actual tool runs and unmet native CodeQL/report prerequisites in specs/010-misra-quality-and-deviations/acceptance.md (all SC010 criteria; 010-R11).
- [ ] T031 Update README.md, docs/backlog/requirements-index.md, docs/backlog/roadmap.md and docs/handoff/010-to-011.md with actual implementation limits and owner-review questions; do not authorize 011 work (010-R10/R11).
- [ ] T032 Obtain authorized owner review of source/tool confidence, 009 T018, applicability denominator, allowed deviation/recategorization policy and CodeQL eligibility/report configuration; record authenticated decisions or remaining blockers in specs/010-misra-quality-and-deviations/acceptance.md. Human-owned: agents must not check off this task (010-R01/R05/R07/R09).

## Dependencies and parallel opportunities

Setup T001–T002 → foundation T003–T006 → US1 → US2 → US3 → US4 → validation.
Each story has a separate independent test checkpoint. US2 imports may be tested independently
with explicitly labelled native-output fixtures after foundation, before live runner integration.
US3 uses the US2 finding/extraction model; US4 needs all preceding records. Shared cli.py edits
and runner.py/dispositions.py extensions are sequential. T032 cannot be completed by agents.
CodeQL prerequisites block its real execution/acceptance, while complementary implementation proceeds.

Parallel examples within each story (tests first, then implementation):

- US1: T007 execution contract tests and T008 real-tool integration sources use separate files.
- US2: T014 parser cases and T015 extraction cases use separate files.
- US3: T019 correction cases and T020 decision cases use separate files.
- US4: T023 coverage cases and T024 packet/assessment cases use separate files.

## Implementation strategy

Deliver US1 first with actual Clang-Tidy defect/fix and explicit missing capabilities.
Validate native preservation/extraction before disposition or compliance logic. Extend through
US2, US3 and US4, rerunning each independent checkpoint. Record local/fixture evidence truthfully;
stop at human/external prerequisites for the affected acceptance. Planning does not authorize
publishing, merging, deployment or automatic continuation to 011.

Counts: 32 tasks; US1 7, US2 5, US3 4, US4 6; setup/foundation 6, validation/handoff 4.

## Authorized Clang-Tidy implementation slice (2026-09-30)

The user's `go` followed the concrete next step “implement 010's Clang-Tidy adapter”.
This authorizes this slice and its prerequisites. T001–T032 describe the larger increment;
their remaining multi-tool/import/disposition/coverage work is not claimed complete.
The six scoped tasks below record the implemented parts so follow-up work can reuse them.
They do not replace T032 or check off owner review.

- [x] T033 [US1] Define exact Clang-Tidy capability/run requests and output schemas in specs/010-misra-quality-and-deviations/contracts/clang-tidy.md and schemas/quality-*.schema.json (scoped parts of T002/T013).
- [x] T034 [US1] Implement candidate native/tool profiles, strict frozen selections and bounded capture in profiles/s-core-quality-v1.yaml, profiles/cpp17-quality-local-v1.yaml, profiles/native-quality/ and src/score_sw_fabric/quality/models.py and profile.py (scoped parts of T001/T003–T006).
- [x] T035 [US1] Measure Clang-Tidy version, configuration recognition, expanded checks and effective config in src/score_sw_fabric/quality/capabilities.py; report other capabilities as unimplemented and authority/mapping as unknown (scoped part of T009).
- [x] T036 [US1] Execute selected translation units on disposable copies, retain native YAML/text/diagnostic locations and extraction scope, and wire quality capabilities/run with guarded 0/1/2 publication in src/score_sw_fabric/quality/runner.py, native_outputs.py and src/score_sw_fabric/cli.py (scoped parts of T010/T013/T016/T017).
- [x] T037 [US1] Verify genuine defect/fix, selected header diagnostics, incomplete scope, compiler failure, suppression, tool/config drift, timeout/truncation and safe publication in tests/contract/test_quality_contracts.py, test_quality_execution.py and tests/integration/test_quality_tools.py (scoped parts of T003/T007/T008).
- [x] T038 [US1] Record actual CLI outputs and repository validation in specs/010-misra-quality-and-deviations/evidence/, acceptance.md and docs/handoff/010-clang-tidy-slice.md; update README.md and backlog status truthfully (scoped parts of T030/T031).

At the end of the Clang-Tidy slice: 38 tasks; 6 scoped tasks complete, all 32 full-increment tasks remain
unchecked because they include broader work or authority. The original 32-task story counts
above remain the plan for the complete increment. No automatic 011 work is authorized.

## Authorized complementary-tool slice (2026-09-30)

The user's next `go` authorizes Cppcheck and ASan/UBSan adapters and their prerequisites.
Broader import/decision/coverage work and human-owned T032 stay outside this slice.

- [x] T039 [US1] Define exact adapter selections/configuration/schema contracts in specs/010-misra-quality-and-deviations/contracts/complementary-tools.md and schemas/quality-*.schema.json, retaining the Clang-Tidy version 1 interface.
- [x] T040 [US1] Add pinned local Cppcheck/GCC/runtime and native feature/template/suppression selections in profiles/ and strict readers in src/score_sw_fabric/quality/configuration.py and models.py.
- [x] T041 [US1] Write meaningful contract/parser and real seeded/corrected integration tests in tests/contract/test_quality_complementary.py and tests/integration/test_quality_complementary.py before adapter implementation.
- [x] T042 [US1] Implement bounded Cppcheck XML capability/execution in src/score_sw_fabric/quality/cppcheck.py and separate actual GCC ASan/UBSan build/link/runtime probes/execution in src/score_sw_fabric/quality/sanitizers.py; wire --adapter in src/score_sw_fabric/cli.py.
- [x] T043 [US1] Record real seed/fix/capability outputs and repository validation in specs/010-misra-quality-and-deviations/evidence/ and complementary-acceptance.md; update quickstart, README.md and docs/handoff/010-complementary-tools.md with remaining blockers.

At the end of the complementary-tool slice: 43 tasks, 11 scoped tasks complete; original full-increment T001–T032 remain
unchecked. Human-owned T032 is pending. No automatic continuation to broader 010 or 011 work
is authorized by completing this slice.

## Authorized native import/extraction slice (2026-09-30)

The user's `go` follows “implement native-output import and extraction validation”. This
authorizes US2 and its shared prerequisites, without CodeQL execution, disposition or coverage.

- [x] T044 [US2] Reconcile the exact import/baseline/identity/artifact/extraction/output contract and schemas before readers in contracts/native-import.md and schemas/quality-*.schema.json.
- [x] T045 [US2] Add parser/deduplication and extraction refusal tests before implementation in tests/contract/test_quality_native_outputs.py and test_quality_extraction.py, with clearly labelled native-output fixtures.
- [x] T046 [US2] Implement bounded read-only imports, multi-run SARIF resolution and native contributor preservation in quality/imports.py, import_models.py, sarif.py and native_outputs.py; reuse existing native readers.
- [x] T047 [US2] Implement independent extraction/report/phase assessment in quality/extraction.py and wire guarded quality import publication in cli.py.
- [x] T048 [US2] Verify genuine complementary-output imports and labelled SARIF fixtures, frozen identity/drift/refusal/portable closure; record repository gates and remaining prerequisites in native-import-acceptance.md and docs/handoff/010-native-import.md.

Current total: 48 tasks; 16 scoped tasks and 5 original US2 tasks complete. The remaining
27 original tasks, including human-owned T032, remain unchecked. No automatic disposition,
coverage, CodeQL execution or 011 continuation is authorized.

## Authorized draft/correction slice (2026-09-30)

The user's next `go` follows the concrete disposition draft and correction freshness
step. This slice implements scoped T019/T021 behavior; T020/T022 decision acceptance,
coverage and CodeQL execution remain pending. Human T032 remains unchecked.

- [x] T049 Define strict draft/review requests, source/construct closure and linked history in contracts/dispositions.md and schemas/quality-disposition-*.schema.json before implementation.
- [x] T050 Write negative freshness/draft/history/publication tests in tests/contract/test_quality_dispositions.py before implementation, including policy/scope drift, names/dates and filtered/incomplete evidence.
- [x] T051 Implement quality/disposition_models.py and dispositions.py and guarded quality disposition CLI; fresh correction uses adapter-owned execution after exact scope checks and never grants decision authority.
- [x] T052 Verify genuine corrections with all four local adapters and preserve linked stale history in tests/integration/test_quality_dispositions.py; record gates, source preservation and remaining blockers in disposition-acceptance.md and docs/handoff/010-dispositions.md.

Current total: 52 tasks, 25 complete (20 scoped and 5 US2), 27 original tasks open.
T019/T021 retain broader unbuilt scope; T020/T022 decision replay and human T032 are
unchecked. Completion proposes the next step without authorizing broader 010 or 011 work.

## Authorized 005 decision bridge (2026-09-30)

The user's next `go` follows independent 005 replay for disposition drafts. This authorizes
T020/T022 and shared prerequisites, without CodeQL execution, coverage or owner decisions.

- [x] T053 Define exact subject/policy/decision requests, binding/result schemas and fixture/production boundaries in contracts/decisions.md and schemas/quality-disposition-*.schema.json before implementation.
- [x] T054 Add independent 005 positive/adversarial fixture tests before implementation in tests/contract/test_quality_decisions.py and tests/quality_decision_support.py.
- [x] T055 Implement deterministic binding preparation and independent current-use decision replay in quality/decisions.py with guarded quality decision-subject/decision CLI; preserve existing draft/correction version 1 records.
- [x] T056 Retain portable labelled 005 fixtures, execute CLI/refusal/history journeys, run repository gates and document remaining prerequisites in decision-acceptance.md and docs/handoff/010-decisions.md.

Current total: 56 tasks, 31 complete (24 scoped, 5 US2 and T020/T022), 25 original
tasks open. Broader T019/T021, coverage, CodeQL execution and human T032 remain unchecked.
Decision results use a separate module/record alongside unchanged version 1 reviews;
[validation](decision-acceptance.md) and [handoff](../../docs/handoff/010-decisions.md)
record fixture-only limits. No automatic continuation is authorized.

## Authorized guideline coverage slice (2026-09-30)

The user's next `go` follows the guideline coverage matrix. This authorizes T023/T025
and the necessary read-only CLI/schema/source binding; packet/assessment and CodeQL
execution remain separate work. Human T032 remains unchecked.

- [x] T057 Define coverage request/manifest/source/matrix contracts and schemas before implementation in contracts/coverage.md and schemas/quality-guideline-*.schema.json.
- [x] T058 Add missing/unknown denominator, source/scope/drift, mechanism/manual/exclusion, native finding and unsafe-publication tests before implementation in tests/contract/test_quality_coverage.py.
- [x] T059 Implement bounded source-backed coverage measurement and exact read-only import replay in quality/coverage.py and guarded quality coverage CLI; preserve all declared rows and zero accepted claims.
- [x] T060 Run native complementary/import coverage and portable/current-prior CLI journeys, repository gates and source preservation checks; record limits in coverage-acceptance.md and docs/handoff/010-coverage.md.

Current total: 60 tasks, 37 complete (28 scoped, 5 US2, 2 US3 and 2 US4),
23 original tasks open. T024/T026–T028 packet/compliance work, broader T019/T021,
CodeQL execution and human T032 remain unchecked. See [validation](coverage-acceptance.md)
and [handoff](../../docs/handoff/010-coverage.md). No automatic continuation is authorized.

## Authorized overnight packet and remaining 010 work (2026-09-30)

The user explicitly authorized seven hours of autonomous work, starting with the
portable quality packet and continuing through the remaining implementable 010 tasks.
See [window and boundaries](../../docs/handoff/010-overnight.md). Earlier slice-only
continuation limits no longer restrict this window's 010 implementation. T032 and
other human-owned decisions remain unchecked; 011 and prohibited external actions
remain outside this authorization.

- [x] T061 Define exact packet selections, archive/snapshot/notice closure and schemas in contracts/packet.md and schemas/quality-packet-request.schema.json and quality-review-packet.schema.json before implementation.
- [x] T062 Add portable/raw/source/history/notice/drift/refusal and genuine local/fixture decision tests in tests/contract/test_quality_assessment.py and tests/integration/test_quality_packet.py before implementation (packet portion of T024).
- [x] T063 Implement bounded portable packet/independent original-byte replay in quality/packet.py and packet_models.py; share native import/extraction/coverage/current fixture decision evaluators and wire quality packet CLI (T026 and packet portion of T028).
- [x] T064 Retain actual unknown-denominator packet, run repository gates and record scope/limitations in packet-acceptance.md and docs/handoff/010-packets.md; keep compliance, eligible CodeQL and human review pending.

After this packet slice: 64 tasks, 42 complete, 22 original tasks open. T024 and
T028 remain open until their assessment portions are implemented. Human T032 remains
open; structural packet completion never constitutes engineering acceptance.
