# Tasks: C++ quality, MISRA, and deviations

**Input**: [spec](spec.md), [plan](plan.md), [research](research.md),
[data model](data-model.md), [contract](contracts/quality.md), [quickstart](quickstart.md).

**Status**: Scoped adapter slices are implemented below. Original full-increment tasks remain
unchecked unless their entire stated scope is complete. Human acceptance remains pending.
Installation evidence is separate from adapter implementation and acceptance.
Tests are required by the spec. Write the relevant negative tests before implementation.
`[P]` identifies independent files within the stated phase, not authorization for agents.

2026-10-01 resumed checkpoint: [internal native phase contract](contracts/codeql-native-phases.md),
35 negative-first contract cases and genuine synthetic CodeQL seed/fresh-fix demonstrations
are implemented. [Measured evidence](codeql-native-demonstration-acceptance.md) records partial
T002/T011/T012/T078/T079 progress. Public execution, native Python/XML/reporting and the full
acceptance scope remain incomplete; the corresponding original checkboxes stay open.
Task count at that checkpoint was 70/84 complete, 14 open; human reviews remained unchecked.

The later [Python 3.9 reporting checkpoint](codeql-python39-reporting-acceptance.md) verifies
installed dependencies, original configuration/XML phases and complete native reports using
an explicit disposable recount variant of the selected upstream patch. Original failed reports
remain preserved. Target-project execution and the original full acceptance tasks are still open; the later fixed
public demonstration slice is recorded below.

## Phase 1: Setup

- [x] T001 Record pinned native policies, license notices, installed tool identities and compiled-pack/source discrepancy in profiles/s-core-quality-v1.yaml; use unknown mapping/category defaults (010-R01/R09/R11).
- [ ] T002 Define exact version 1 field names, required/nullable fields and enums for all five requests and records in specs/010-misra-quality-and-deviations/contracts/quality.md and schemas/quality-*.schema.json before validator implementation (010-R11).

## Phase 2: Foundation

- [x] T003 Add strict request/profile/digest/path/refusal tests in tests/contract/test_quality_contracts.py; reject duplicate/unknown/missing fields, unsafe roots, malformed selections and changed prior output (010-R02/R11).
- [x] T004 Implement shared records and bounds in src/score_sw_fabric/quality/models.py: control request at most 1 MiB, 500 source files, 32 tools; native output at most 16 MiB per artifact and 64 MiB combined, with bounded prefix/full-stream digest on truncation; at most 10000 findings, 1000 guideline rows, 1000 dispositions, 20 decision references; timeout integer 1–3600 seconds; no retries; schema_version 1 and engineering_readiness not_evaluated (010-R02/R10/R11).
- [x] T005 Implement strict sourced profile loading in src/score_sw_fabric/quality/profile.py and candidate profile profiles/cpp17-quality-local-v1.yaml; keep mapping_state unknown by default, decision_policy_ref null, primary/complementary roles, explicit C++17/MISRA edition, native statuses and suppression refs (010-R01/R05/R09).
- [x] T006 Add shared sealed fixtures and source manifests in tests/quality_support.py and tests/fixtures/quality/; label fixtures and local origins distinctly, with no production authority or fabricated guideline text (010-R10/R11).

## Phase 3: US1 — Available checks and capability gaps (P1, MVP)

**Goal**: Run real selected checks and retain capability gaps.
**Independent test**: Seed a defect, collect native output, fix/rerun with changed baseline;
request missing/unsupported tools and incompatible sanitizer combinations (AC010-01–04).

- [ ] T007 [P] [US1] Add capability, drift, bounded output/timeout and disposable-copy tests in tests/contract/test_quality_execution.py, including unchanged protected inputs (010-R01/R02/R06/R09).
- [x] T008 [P] [US1] Add seeded/corrected C++ sources and actual Clang-Tidy, optional Cppcheck and separate ASan/UBSan integration checks in tests/integration/test_quality_tools.py and tests/fixtures/quality/seeded/, corrected/ and sanitizers/; require real native findings and fresh correction, never a fixture substitute (SC010-01; 010-R02/R06).
- [x] T009 [US1] Implement measured capability inventory in src/score_sw_fabric/quality/capabilities.py with available/unavailable/unsupported/unknown states, tool hashes/versions, expanded checks/effective config, pack/suite identities and eligibility/qualification gaps (010-R01/R09).
- [ ] T010 [US1] Implement frozen source/include/generated-input and expected-unit manifests, inspected hooks, disposable copies and bounded adapter-owned argument execution in src/score_sw_fabric/quality/runner.py; retain phases/outputs/configs/digests, compiler/runtime/suppression settings and completed/findings/incomplete/unavailable/failed outcomes (010-R02/R03/R06/R11).
- [ ] T011 [US1] Add gated CodeQL phase execution to src/score_sw_fabric/quality/runner.py only after exact CLI/library/pack/suite/config/patch identity and source/build reconciliation, eligible-use evidence and compatible reporting prerequisites; isolate user/cache, preserve every phase failure/filter/exclusion, and publish unknown prerequisites as blocked (010-R03/R09).
- [ ] T012 [US1] Add genuine environment-selected CodeQL/native-report integration in tests/integration/test_quality_codeql.py; record unmet prerequisites explicitly and retain original SARIF/reports when eligible; unavailable runs stay unmet acceptance rather than replaced fixtures (010-R03/R09).
- [x] T013 [US1] Wire quality capabilities/run and stable 0/1/2 outcomes into src/score_sw_fabric/cli.py, preserving previous output on rejected selections (010-R11).

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
- [x] T024 [P] [US4] Add portable packet/assessment tests in tests/contract/test_quality_assessment.py and test_quality_compliance.py for raw-byte/source/license closure, all origins, pending_human answers, fixture/protected separation and positive local findings never implying production readiness (010-R09/R10/R11).
- [x] T025 [US4] Implement coverage matrix in src/score_sw_fabric/quality/coverage.py with unknown/declared scope and covered/findings_open/pending_manual/unsupported/excluded_pending_review/unknown states; bind categories/applicability/mechanisms/limitations to supplied source refs (010-R05/R09).
- [x] T026 [US4] Implement portable current/prior-run, baseline/output/extraction/matrix/disposition/license closure and pending_human review questions in src/score_sw_fabric/quality/packet.py; retain all unresolved history and import/local/fixture origins (010-R10/R11).
- [x] T027 [US4] Implement independent compliance evaluation in src/score_sw_fabric/quality/assessment.py with fixture_contract/production domains and pass/fail/blocked/not_evaluated outcomes; required missing capabilities/extraction/coverage/decisions block claims (010-R05/R07/R09/R10).
- [x] T028 [US4] Wire quality packet/assess into src/score_sw_fabric/cli.py with schema-checked atomic publication and deterministic 0/1/2 exits (010-R11).

## Phase 7: Cross-cutting validation and handoff

- [x] T029 Verify pinned source/config hashes and read-only native repository status in tests/integration/test_quality_native_sources.py; record absent native CSV, measured identical source trees and unresolved compiled artifact provenance without inventing mappings (010-R01/R02/R11).
- [x] T030 Run uv sync --frozen, Ruff, mypy, pytest, uv run --frozen python scripts/check_foundation.py and uv build; record exact commands/outcomes, actual tool runs and unmet native CodeQL/report prerequisites in specs/010-misra-quality-and-deviations/acceptance.md (all SC010 criteria; 010-R11).
- [x] T031 Update README.md, docs/backlog/requirements-index.md, docs/backlog/roadmap.md and docs/handoff/010-to-011.md with actual implementation limits and owner-review questions; do not authorize 011 work (010-R10/R11).
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

## Autonomous independent assessment slice (2026-10-01, Lisbon)

The existing seven-hour authorization continues through independent assessment and CLI.
The supported profile remains unmapped; production and fixture overall compliance cannot
pass. Human-owned T032 and protected/eligible execution gates are still open.

- [x] T065 Define exact current/offline assessment controls, original transport/source closure, source/decision validity and schemas under contracts/assessment.md.
- [x] T066 Add independent source/origin/denominator/obligation/tampering/refusal and genuine complementary/fixture decision integration tests before implementation in tests/contract/test_quality_compliance.py and tests/integration/test_quality_compliance.py (assessment portion of T024).
- [x] T067 Implement independent current/offline evaluation and portable replay in quality/assessment.py; wire quality assess with guarded deterministic publication and 0/1/2 semantics (T027/T028; only blocked overall outcomes are possible with the current unmapped profile).
- [x] T068 Retain the actual blocked unknown-denominator assessment and record verification, remaining source/CodeQL/owner prerequisites in assessment-acceptance.md and docs/handoff/010-assessment.md.

After assessment: 68 tasks, 49 complete, 19 original tasks open. Detailed remaining work
is limited to 010; no 011 implementation or human review completion is authorized.

## Native source reconciliation checkpoint (2026-10-01, Lisbon)

T029 is complete with five environment-selected read-only tests and [measured evidence](source-reconciliation.md).
The source-tree discrepancy is resolved without changing reviewed locks. Native CSV absence,
compiled build provenance, reporting and use eligibility remain explicit. Current total: 68 tasks,
50 complete, 18 original tasks open including human T032. No new engineering acceptance is recorded.

## Autonomous CodeQL prerequisites and native runtime diagnosis

The existing seven-hour authorization covers this prerequisite inspection and fail-closed
runtime correction. These tasks record bounded implemented scope; they do not complete
T011/T012 or the failed full validation gate T030. No human-owned decision is checked off.

- [x] T069 Define exact CodeQL prerequisite requests, toolchain/configuration/inventory/run schemas in contracts/codeql-prerequisites.md and schemas/quality-codeql-*.schema.json before implementation (scoped T001/T002).
- [x] T070 Write Git object, source/pack/library/suite/control identity, bounded inspection, drift/race and protected-output refusal tests before implementation in tests/contract/test_quality_codeql.py; add environment-selected installed-source inspection tests in tests/integration/test_quality_codeql.py (scoped T003/T007/T012; inspection does not satisfy genuine T012 analysis).
- [x] T071 Implement bounded frozen prerequisite inspection in quality/codeql.py and codeql_models.py and guarded quality capabilities/run --adapter codeql routing, with unavailable execution, unverified eligibility and zero claims; protect native roots and reject accidental complementary execution (scoped T009/T013).
- [x] T072 Retain actual selected prerequisite inventory/profiles/request and exact pass/fail verification results in codeql-prerequisites-acceptance.md, schemas/README.md and docs/handoff/010-codeql-prerequisites.md (scoped T030/T031; broad ASan validation remains failed).
- [x] T073 Add failing contract cases before correcting LeakSanitizer fatal-error handling in quality/sanitizers.py: even exit 0 or exit 55 with an AddressSanitizer finding must keep scope incomplete; preserve original stderr/findings and precise runtime/ptrace gaps in sanitizer-environment.md (010-R02/R03/R09).

Current total: 73 tasks, 55 complete, 18 original tasks open. Full validation T030 is
failed in the restricted ASan runtime environment; CodeQL execution T011/T012 and human
T032 remain pending. The [overnight handoff](../../docs/handoff/010-overnight.md) records
the active window and current filesystem limits. No 011 continuation is authorized.


## Phase 8: Convergence

Current-code audit: 31 requirement/scenario/success items, seven plan decisions, twelve
constitution principles and all 73 existing tasks. Three missing and eight partial findings;
nine HIGH and two MEDIUM. No additional contradictory or unrequested behavior identified.
These tasks preserve the original task scope and external/human gates; completing a scoped
fix does not complete the full increment or authorize 011. F5/F6 require reviewed prerequisites;
F11 is human-owned and must remain unchecked by agents.

- [x] T074 Refreeze the original request, profile, toolchain, configuration and native sanitizer controls before returning local capability/run/disposition results in quality/models.py, capabilities.py, runner.py, complementary.py and dispositions.py; write control/source race and safe-publication tests before implementation per F1, 010-R02/R06/R11 and T007/T010/T019/T021 (partial, HIGH).
- [x] T075 Bound live YAML controls/effective configuration/Clang-Tidy native output by depth/nodes and regular-file/control bytes in quality/models.py, profile.py, configuration.py, capabilities.py and native_outputs.py; refuse cycles, non-JSON and nonfinite values with stable exit 2 and prior output intact per F2, 010-R02/R11 and T003/T004/T007 (partial, HIGH).
- [x] T076 Check every selected runtime asset even when another tool/dependency is unavailable in quality/models.py; missing capability cannot hide changed identities; write negative tests before implementation per F3, 010-R02/R09 and T007/T009 (partial, HIGH).
- [x] T077 Share LeakSanitizer fatal-error interpretation across execution, original native import and offline packet replay in quality/sanitizers.py and imports.py; preserve findings/stderr and incomplete extraction for misleading zero/finding exits; test original-byte import and portable replay per F4, 010-R03/R04/R09 and AC010-06 (partial, HIGH).
- [ ] T078 Implement isolated adapter-owned CodeQL/native-report phases and bounded original SARIF/supporting artifacts only after exact source/build/tool/library/pack/suite/config/patch/report compatibility and independently established eligible-use prerequisites in quality/codeql.py and runner.py per F5, 010-R03/R09 and T011 (missing, HIGH; external eligibility/configuration prerequisites remain pending).
- [ ] T079 Add environment-selected genuine eligible CodeQL extraction/query/native-report seeded/corrected integration with original outputs and explicitly unmet unavailable prerequisites in tests/integration/test_quality_codeql.py per F6, 010-R03/R09, SC010-01 and T012 (missing, HIGH; prerequisite inspections and fixtures cannot satisfy this task).
- [x] T080 Add CodeQL source/tool/pack/suite/policy context for imported disposition drafts and blocked corrections in quality/dispositions.py and disposition_models.py with compatible portable history/decision binding tests; prerequisite inspection must never count as fresh analysis per F7, 010-R06/R07/R10 and T019/T021 (partial, HIGH).
- [x] T081 Complete current full validation and exact pass/fail records in acceptance.md with frozen sync, Ruff, mypy, pytest, foundation and build; retain existing ASan sandbox failures until a compatible runtime permits the original checks per F9, 010-R11 and T030 (partial, HIGH at audit; compatible-host gate now passes, historical failure retained).
- [ ] T082 Obtain authenticated owner review of tool/source confidence, 009 profile review, applicability/mapping, deviation categories and CodeQL eligibility/report configuration; retain pending prerequisites in acceptance.md per F11, 010-R01/R05/R07/R09 and T032 (partial, HIGH; HUMAN-OWNED, agents must not check off).
- [x] T083 Reconcile the full version 1 contract with implemented profile/toolchain/configuration composition, installed/source identities, schemas and explicit unimplemented native phases in contracts/quality.md and profile documentation; preserve historical transport hashes and unknown mappings per F8, 010-R01/R11 and T001/T002 (partial, MEDIUM).
- [x] T084 Finish actual 010 implementation/verification/blocker handoff in docs/handoff/010-to-011.md and README/backlog indexes, preserving pending owner reviews and no authorization for 011 per F10, 010-R10/R11 and T031 (missing, MEDIUM).

After audit: 84 tasks, 55 complete, 29 open including 18 original tasks. The full
regression gate remains failed in the restricted ASan environment. Convergence appends
work only; no checkbox, code, profile or spec was changed by this audit.


Convergence implementation checkpoint: T074–T077 and T083 are complete with
[negative-first verification](controls-validation.md). Current total: 84 tasks, 60 complete,
24 open. T078/T079 native CodeQL, T080 CodeQL disposition context, T081 full validation,
T082 human review and T084 final handoff remain open. Current ASan validation is still unmet.

CodeQL context and handoff checkpoint: T080, T031 and T084 are complete with
[context verification](codeql-dispositions-acceptance.md) and [actual handoff](../../docs/handoff/010-to-011.md).
Current total: 84 tasks, 63 complete, 21 open (17 original tasks). Genuine CodeQL
execution/integration T011/T012/T078/T079, failed full validation T030/T081 and
human-owned T032/T082 remain open. No inspection or fixture establishes acceptance.

Full-task reconciliation closes T003/T004/T005/T006/T009/T013 against their complete
implemented scope and [measured evidence](task-reconciliation.md), including the corrected
combined 32-tool bound. Current total: 84 tasks, 69 complete, 15 open (eleven original).

04:22 UTC T001 follow-up: candidate installed context is now consolidated under its exact
[contract](contracts/installed-context.md), with complete original notices and explicit unknown
qualification/eligibility. Original profile bytes are retained for historical imports/packets;
current selections use the new SHA. Current total: **84 tasks, 70 complete, 14 open** (ten
original). Human gates and native CodeQL/full ASan validation remain open.
Unimplemented eligible CodeQL execution, the failed ASan gate and human-owned reviews remain open.


## Resumed public software demonstration slice (2026-10-01)

User resumption authorizes the bounded synthetic demonstration integration below. These tasks
implement parts of T002/T011/T012/T078/T079; they do not close target-project eligibility,
qualification, human reviews or full ASan validation. No increment 011 work is authorized.

- [x] T085 Define the distinct fixed demonstration request/result contract before validator implementation and publish matching strict schemas; prohibit target roots/files/build commands and bind original CLI terms, selected prerequisite/compiler/reporting controls and explicit patch mode (010-R02/R03/R09/R11).
- [x] T086 Add negative-first demonstration scope/hash/license/output/failure tests and native SARIF self-index/default-line/source-root regressions; preserve native records and refuse unresolved paths/content drift (010-R02/R04/R06/R11).
- [x] T087 Implement bounded public fixed CodeQL demonstration execution in quality/codeql_demonstration.py with shared capture bounds, isolated source/cache, complete native phases, independent extraction, original report failures and source/tool/control refreezing; retain inspection-only target requests and all qualification gates (010-R03/R09/R10).
- [x] T088 Execute environment-selected public seeded/fresh-corrected integration, preserve sealed original SARIF/configuration/XML/native reports and failures, validate exact schemas and foundation gates, then reconcile acceptance/handoff without checking human-owned tasks (010-R03/R04/R09/R11).

Completed [public demonstration slice](codeql-public-demonstration-acceptance.md): T085–T088
are complete. Current total: **88 tasks, 74 complete, 14 open** (ten original tasks).
Real public seeded/fresh-corrected integration passes with three/zero findings, adequate
extraction and all native reports. Full target execution, ASan validation and human reviews
remain open; no fixture, native status or test pass closes engineering acceptance.

## ASan normal-terminal validation continuation

The latest user resumption authorizes preparing/running the existing T030/T081 validation
gates in a compatible host context. `scripts/validate_asan_host.sh` retains original capability,
seed/fresh-fix records and the three affected integration checks, and can resume full gates in
a new output directory without overwriting earlier evidence. Negative-first retained-record
checks refuse changed phase exits, missing runtime, LeakSanitizer failures, changed native
configuration/origin/kind, truncation and raw-byte mismatch.

[Host ASan evidence](sanitizer-environment.md) now records genuine capability/defect/correction
and three passing integration checks. Original host Ruff failure and agent-sandbox runtime
failure remain preserved. T030/T081 stay open until the resumed full validation is complete.
Task count remains 74/88 complete, 14 open; human-owned T032/T082 stay unchecked.


## Completed host validation checkpoint

The user's normal-terminal continuation completes [the selected full validation](asan-host-validation.md):
1,773 passed, 13 explicitly documented external/native skips, 361.00 seconds; all static,
foundation/frozen/build gates pass. All four actual Clang-Tidy/Cppcheck/ASan/UBSan seed/fresh-fix
cases pass in the original full JUnit. T008's complete stated four-tool integration scope is
verified; T030/T081's exact validation/recording scope is complete. Earlier failed measurements
remain preserved; current agent-sandbox ASan failure does not invalidate the compatible host
measurement or become silently cleared in that sandbox.

Current total: **88 tasks, 77 complete, 11 open** (eight original tasks).
T002/T007/T010/T011/T012/T019/T021/T032 and T078/T079/T082 remain open. Human-owned T032/T082,
009 T018 and protected 005 T009 stay unchecked. No target CodeQL eligibility or engineering
acceptance is inferred from this gate.

## Shared source include validation follow-up

[The source include correction](source-include-validation.md) retains 35 negative-first failures
and a final passing focused gate, including five genuine Clang-Tidy selected-header spellings.
Literal external paths obscured by comments/continuations/directive spelling now refuse before
execution; unknown macro/import/include-next scope remains explicit. This is additional scoped
T007/T010 progress. Their full target/generated-input work remains open; count stays 77/88.

## Fabro SOME/IP execution correction (2026-10-01)

Authorized by the user's continuation after identifying direct implementation
outside the factory. Earlier provenance and all human gates remain intact.

- [x] T089 Define the optional packaged command binding and bounded SOME/IP factory execution contract before code, preserving historical prototype replay and explicit live-agent admission (contracts/fabro-command-binding.md; 010-R03/R09/R11).
- [x] T090 Write negative-first command binding/execution/exit/tampering tests in tests/contract/test_compiler_command_binding.py; fixtures cannot establish actual native execution (010-R03/R11).
- [x] T091 Implement and verify explicit support-file script projection in compiler/mapping.py, ir.py, models.py and render.py without introducing a scheduler or implicit shell filename execution (010-R03/R11).
- [x] T092 Compile a genuine bound SOME/IP measurement workflow with the pinned native validator and execute it through the existing fabric runtime; retain original Fabro events/checkpoints/outputs and all failures in docs/handoff/someip-84/factory/ (010-R03/R09/R11).
- [ ] T093 Admit and execute a live Fabro implementation agent only after provider, spending limit and boundary configuration are available; preserve the earlier external candidate and stop explicitly if admission is unavailable (010-R09/R11; pending configuration).
- [x] T094 Record actual command/native/static/foundation/build results and reconcile factory provenance/handoff without completing human reviews or claiming issue completion (010-R10/R11).

[Actual factory evidence](../../docs/handoff/someip-84/factory/README.md) completes the
bounded measurement/execution correction. Native run `01M3VZNAAQ1QXK5530X7E8HZ26`
reproduces the expected baseline 7/13 failures and external-candidate 13/13 passes;
complete portable export retains 63 events, three checkpoints and zero human answers.
The operational configuration gate remains unanswered and has no 005 engineering subject.
Earlier listener/authentication/interrupted-export failures stay preserved. The user's later
DeepSeek Flash/spending selection is recorded; credential availability, enforceable native
model/tool/path binding and runtime usage/admission remain required for T093. Selection and
measurement do not complete live implementation. Current total: **94 tasks, 82 complete,
12 open**, including all eleven previously open tasks. Human review markers remain unchanged.


## Authorized SOME/IP missing-tool recovery (2026-10-03)

The user requested installation of all missing tools from the failed SOME/IP queue
and a fresh queue run to address verification issues. Preserve predecessor evidence,
source locks, draft reports and unanswered human decisions. Use the shared storage
selector, bind tool storage and fresh queues to their measured volume, retain exact
tool versions/hashes, and freeze tool paths with each successor. Global tool storage
and reference repositories remain unchanged. Licensed Coverity/QNX capability and
engineering acceptance cannot be inferred from installation.

- [x] T095 Install and smoke-test missing Bazel 8.6.0, Valgrind, pre-commit, REUSE, clang-format and Gitleaks on selected storage; retain downloads, licenses and tool identities.
- [x] T096 Replace vanished temporary collector paths with frozen, storage-bound tool identities; verify tool drift/disconnection rejection and existing collector contracts.
- [x] T097 Preserve the latest failed run's candidate source/reports, prepare and start one supervised all-obligations successor with the existing Flash/high/no-fallback selection; retain measured startup and verification results without answering human reviews.


T095–T097 bounded installation, collector repair and fresh supervised startup are
verified in [tool recovery](../../docs/handoff/someip-84/factory/tool-recovery.md).
That full successor subsequently reached human review and timed out unanswered; these task completions do not assert all
verification checks passed or complete any human review.


## Authorized failed-check rerun (2026-10-03)

User "do it" authorizes the proposed cloud-localds installation, disposable Git
metadata repair and fresh failed-check execution. Preserve the earlier queue's
results and human stop. Collect fresh evidence through Fabro on the preserved
source with explicit longer bounds for previously timed-out measurements; never
turn installation or successful collection into engineering acceptance.

The user's correction, "be sure to not run everything again, just want is missing",
narrows the successor to docs, traceability, formatting, native Clang-Tidy,
benchmarks/profiling and QEMU integration. Previously passed checks and measured
findings are preserved without re-execution. There are no implementation-agent stages.

- [x] T098 Install cloud-image-utils and genisoimage with package checksums/licenses and real seed-image smoke; freeze additional storage bindings without changing older tool installations.
- [x] T099 Restore genuine pinned public Git metadata in collector-owned copies, with hooks disabled; verify remote and baseline identity and keep candidate source dirty against the real baseline.
- [x] T100 Prepare and execute a deterministic failed-check Fabro successor, retain original/new results and identify remaining findings, runtime/platform failures and required human decisions.

T098/T099 are verified in [selected-check recovery](../../docs/handoff/someip-84/factory/missing-check-recovery.md).
T100's earlier bounded collection is complete. That slice's final run `01M4082KVKZ7DE1D4KSBEEJE0C`
stopped at the unanswered human gate. Formatting violations, perf permissions and
Bazel cloud-localds visibility remain unresolved; this completion is not issue closure
or engineering acceptance. The observer repeated the selected set once, then refused
another human-gate timeout repair.

## User-authorized same-run orchestration and external validation

- [x] T101 Define same-run repair, mandatory executed integration and external mandatory human validation in contracts/someip-in-run-repair.md and spec/plan; preserve historical evidence and prior human authority.
- [x] T102 Add negative-first contracts for real failure routing, bounded loopbacks, orchestrators, mandatory integration execution, external human closure and refusal of automatic successor creation.
- [x] T103 Implement scoped deterministic orchestration and repair stages inside Fabro, including Bazel tool visibility, source formatting and affected regressions; remove operational human interviews from new SOME/IP workflows.
- [x] T104 Repair run-scoped perf/integration execution prerequisites and measure actual selected checks; keep global tool/kernel settings and reference repositories unchanged.
- [x] T105 Compile, validate and execute the corrected native workflow with same-run repair evidence, mandatory real integration and preserved failures; task remains open if any mandatory check fails.
- [x] T106 Reconcile portable review packet, workflow diagram and handoff with exact tests/tool/native results and explicit pending external human validation.
- [ ] T107 Obtain the required external human validation of the exact candidate/evidence to close this task (HUMAN-OWNED; agents must not check off).

The [current repair run](../../docs/handoff/someip-84/factory/repair-orchestration.md)
demonstrated real formatting, integration and profiling repair loopbacks. Final run
`01M40R4FYAZR2PGCH5AQF4DRMC` succeeded after its profiling failure → orchestrator
→ repair → passing check loop. All six native integration tests previously executed
and passed; the final run reused that checksum-bound evidence with identical fresh
candidate hashes and executed only the two outstanding profiling targets, both
passing. T104–T106 are technically complete; task closure still requires T107
outside Fabro. The portable review archive retains candidate, raw logs, 12 datasets,
12 flamegraphs, capture source/binary/patch/licenses and exact evidence hashes.
Validation after the final helper changes: 121 tests passed, one native CLI test
skipped; Ruff, mypy, foundation checks and package build passed. No engineering
acceptance, merge, publication or deployment is claimed.

## Subsequent agent review findings (2026-10-03)

The successful scoped native run and T104–T106 measurement/packet history remain
preserved. [The agent review](../../docs/handoff/someip-84/factory/runs/score-someip84-repair-bi5z3qb7/agent-review.json)
found defects that block current merge/closure readiness; no human review occurred.

- [x] T108 Propagate unexpected workload signal exits through the scoped profiler bridge; distinguish intentional daemon termination and add negative regression coverage (R1, P1).
- [x] T109 Bind original passing raw log/artifact identities and reject changed evidence before reuse or packet creation (R2, P2).
- [x] T110 Verify integration case-level outcomes and explicit native platform applicability; reject skipped applicable cases while retaining the QNX-only Linux exclusion (R3, P2).

T107 remains mandatory and human-owned. Upstream #84's broader identifier/discovery
scope must be implemented or explicitly narrowed by its maintainers before closure.

T108–T110 are verified by the [targeted repair evidence](../../docs/handoff/someip-84/factory/review-repair-run.md).
Run `01M40XMJ9K182CG0SWBNVPY7AB` passed fresh six-target integration (13 applicable
cases passed; one pinned QNX-only exclusion), then failed profiling because the
new cleanup guard omitted the native echo server. That failed run remains preserved.
The manually prepared profiling-only correction `01M40Y7RJF9NZJTE2N9Z3BAAXA`
succeeded through its own measured failure → orchestrator → repair → passing check
loop; the earlier fresh integration and unchanged formatting/compiler/unit checks
were reused after identity verification. The actual SIGSEGV regression returns 139
and rejects decoding; both native profiling targets pass. Validation: 147 local
tests passed, zero skipped; Ruff, mypy, foundation and package build passed. Offline
replay verified 1,046 portable files, 269 candidate hashes, integration XML, 12
datasets and 12 flamegraphs. T107 remains unchecked and mandatory outside Fabro;
no full upstream #84 implementation, acceptance, publication or issue closure is claimed.


## External user approval and local PR preparation (2026-10-03)

The user explicitly stated: “I agree and approve, prepare the PR closure scope but
dont create the PR now”. [The approval record](../../docs/handoff/someip-84/factory/runs/score-someip84-repair-b4ard87e/external-user-approval.json)
binds this external conversation decision to the final run and original evidence
archive. [The prepared closure scope](../../docs/handoff/someip-84/pr-preparation/closure-scope.md)
contains a native six-file patch matching the final tested candidate, a PR body,
and a Related-to-#84 reference that retains its broader design work. Clean patch
application and all six file hashes were verified in a disposable baseline copy;
no native queue reran and no PR was created. T107's checkbox stays human-owned;
this approval is recorded separately from signed assurance/maintainer decisions
and does not authorize publication, merge or upstream issue closure.
