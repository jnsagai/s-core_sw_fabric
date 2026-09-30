# Feature Specification: C++ quality, MISRA, and deviations

**Feature Branch**: `010-misra-quality-and-deviations`

**Created**: 2026-09-30

**Status**: Clang-Tidy, Cppcheck and separate GCC ASan/UBSan capability/run adapters implemented
for local complementary use; native-output import/extraction validation is implemented for
unverified/fixture inputs. Disposition drafts and fresh local correction/history checks
are implemented; independent 005 fixture decision replay and the guideline coverage matrix
are implemented. Portable review packets and offline structural replay are implemented.
Compliance evaluation, CodeQL execution, full 010
implementation and engineering acceptance remain pending. The 009 verification/toolchain profiles still await owner
review (T018). Production authority remains unavailable (005 T009). No compliance acceptance
or eligible CodeQL execution is recorded.

**Input**: The [009 handoff](../../docs/handoff/009-to-010.md), brief §§12.2–12.8 and §20.13,
and FAB-039–FAB-042. Integrate selected native quality policies, actual complementary analysis,
original analyzer output, extraction integrity, rule/manual coverage, scoped disposition and
reviewed deviations. Keep unavailable MISRA capabilities visible.

## User Scenarios & Testing

### User Story 1 — Run available checks and expose capability gaps (Priority: P1)

An engineer selects the source baseline, native quality policy and analyzer identities. Available
checks run against a disposable copy, retain their original output and report which checks,
translation units and policy options ran. Unsupported tools/configurations remain named gaps.

**Independent Test**: Run a seeded quality defect with an available complementary analyzer;
fix it and rerun. Request an unavailable analyzer or unsupported policy check.

**Acceptance Scenarios**:

1. **Given** a seeded defect, **when** an available analyzer runs, **then** a real finding, native
   check ID, location, tool/source/policy digests and original output are retained. (AC010-01)
2. **Given** a fixed source, **when** analyzed afresh, **then** the later result binds the changed
   baseline and keeps the earlier finding in history. A changed source with only an old report
   remains stale. (AC010-02)
3. **Given** missing Clang-Tidy, missing CodeQL, unresolved CLI eligibility, unsupported checks or
   missing native mapping, **when** assessed, **then** the affected obligation is blocked and
   available complementary checks can still execute. (AC010-03)
4. **Given** supported sanitizer configurations, **when** selected, **then** execution and runtime
   diagnostics are retained; incompatible combinations and unavailable runtimes remain explicit.
   (AC010-04)

---

### User Story 2 — Import original outputs and check extraction (Priority: P1)

An engineer submits analyzer outputs and supporting extraction reports on a frozen baseline.
The fabric preserves original rule IDs, locations, fingerprints, suppression records and run
failures. It compares expected translation units with extracted units before considering a clean
result usable.

**Independent Test**: Import representative native output; remove an extracted translation unit,
submit an empty extraction, a failed query and a filtered/suppressed finding.

**Acceptance Scenarios**:

1. **Given** original analyzer output, **when** normalized, **then** findings retain their original
   identities and source references; deduplication preserves every contributing result. (AC010-05)
2. **Given** zero or partial extraction, an unknown expected set, failed query, incomplete run or
   unexplained exclusion, **when** checked, **then** zero findings cannot be reported as adequate
   clean evidence. (AC010-06)
3. **Given** suppressed findings or a broad exclusion, **when** imported, **then** they remain
   reviewable and cannot remove required obligations without an eligible scoped decision.
   (AC010-07)
4. **Given** a source, tool, query-pack, suite or policy mismatch, **when** outputs are assessed,
   **then** the report names the drift and refuses reuse as current evidence. (AC010-08)

---

### User Story 3 — Track dispositions and prepare deviation review (Priority: P1)

An engineer fixes a finding or drafts a false-positive/deviation rationale. The fabric retains
its link to the finding, rule, source construct and exact baseline, together with scope, impact,
compensating evidence and expiry/review triggers. Drafts stay pending until authenticated review
and adopted deviation policy are present.

**Independent Test**: Draft a deviation, provide a self-asserted approval, then change its source,
rule policy or validity conditions. Exercise eligible decisions only in an explicitly labelled
fixture assurance domain.

**Acceptance Scenarios**:

1. **Given** an AI-authored rationale or unverified approval field, **when** evaluated, **then** it
   remains `pending_review` and cannot dispose of the finding. (AC010-09)
2. **Given** an unknown or prohibited deviation category, **when** submitted, **then** it remains
   blocked; the fabric never assumes all guidelines are deviable. (AC010-10)
3. **Given** a replayed decision bound to another finding/baseline, an expired decision or changed
   validity conditions, **when** evaluated, **then** the disposition is stale or unresolved.
   (AC010-11)
4. **Given** a reported correction without fresh matching analysis, **when** assessed, **then**
   the finding remains open. Suspected false positives remain pending review. (AC010-12)

---

### User Story 4 — Report guideline coverage and compliance blockers (Priority: P1)

A reviewer sees the full applicable guideline denominator, each automation/manual mechanism,
its limitations, unresolved findings, disposition history and remaining required reviews. Where
the native mapping or applicability denominator is unavailable, that uncertainty is explicit.

**Independent Test**: Assess clean complementary results while the primary MISRA capability,
rule mapping or manual review is missing; inspect the resulting blockers and review packet.

**Acceptance Scenarios**:

1. **Given** missing mapping/applicability, primary capability, extraction evidence, manual review
   or authorized decisions, **when** assessed, **then** compliance is `blocked` or
   `not_evaluated`, with each gap named. (AC010-13)
2. **Given** a coverage matrix, **when** assessed, **then** every declared applicable guideline has
   an explicit mechanism/state; unknown rules and manual/audit obligations cannot disappear.
   (AC010-14)
3. **Given** a review packet, **when** built, **then** original outputs, source/tool/policy hashes,
   extraction, coverage and deviation references are portable; required human answers stay
   `pending_human`. Local execution and fixture imports remain ineligible production evidence.
   (AC010-15)

### Edge Cases

- A clean analyzer result has an empty translation-unit set or a failed supporting report.
- Tool exit is zero while output reports errors, failed queries or incomplete extraction.
- SARIF contains multiple runs, indirect locations, duplicate fingerprints or suppression entries.
- Analyzer output refers to a path outside the selected source baseline.
- Query filters and target exclusions hide checks needed by a declared guideline mechanism.
- A suppression covers a whole file or rule, while the decision covers one construct.
- A default query suite excludes audit/default-disabled checks needed by the coverage matrix.
- Native documentation names an unavailable CSV mapping or suite.

## Requirements

### Functional Requirements

- **010-R01 / FAB-039**: The quality profile MUST bind the C++17/MISRA C++:2023 target policy,
  native source pins, selected tool configuration and every unavailable capability. (AC010-03/04)
- **010-R02 / FAB-039**: Execution MUST use verified tool identities and disposable input copies,
  retaining original outputs and source/test/tool/policy baseline digests. It MUST leave target
  sources and reference repositories unchanged. (AC010-01/02/04)
- **010-R03 / FAB-040**: Extraction adequacy MUST compare a declared expected translation-unit
  set with actual extraction and retain all exclusions, warnings, failed queries and incomplete
  report generation. Empty, partial or unknown extraction MUST block clean evidence. (AC010-06)
- **010-R04 / FAB-041**: Finding normalization/deduplication MUST preserve native check/rule IDs,
  original fingerprints, all contributing locations, severity and suppression provenance.
  (AC010-05/07)
- **010-R05 / FAB-040**: Guideline coverage MUST use explicit applicability, mechanisms,
  automation classes, limitations and manual/audit obligations. A missing mapping/denominator
  MUST remain unknown and block the corresponding claim. (AC010-13/14)
- **010-R06 / FAB-041**: Corrections MUST require fresh matching analysis. Source, tool, query-pack,
  suite, policy and scope changes MUST make affected results/dispositions stale. (AC010-02/08/12)
- **010-R07 / FAB-041**: Deviation/false-positive drafts MUST remain review proposals. An eligible
  decision MUST bind finding, guideline, construct, baseline, permitted category, scope, authority,
  impact, evidence and validity conditions through the 005 boundary. (AC010-09–12)
- **010-R08 / FAB-041**: Inline suppressions, SARIF suppressions and exclusions MUST remain
  visible and require exact scoped authority where the adopted policy requires it. (AC010-07/11)
- **010-R09 / FAB-042**: Missing licensed capability, unknown eligibility, incomplete extraction,
  missing coverage or required decisions MUST block compliance regardless of complementary
  tool success. (AC010-03/06/13)
- **010-R10**: Reports MUST distinguish local execution, unverified imports, fixtures and separately
  verified 005 evidence, and retain portable review packets with pending human answers.
  (AC010-15)
- **010-R11**: Commands MUST expose stable 0/1/2 outcomes, preserve previous output on rejected
  input and retain source IDs/license notices. Proprietary MISRA text MUST remain external.
  (AC010-01/05/15)

### Key Entities

- **Quality profile**: Native policy, target language/edition, tool identities, required capabilities.
- **Analysis baseline/run**: Frozen files, translation-unit expectation, configurations and raw output.
- **Finding**: Native check/rule identity, locations, fingerprint, source result references.
- **Extraction assessment**: Expected/extracted units, exclusions, warnings, query/report failures.
- **Guideline matrix**: Applicability denominator, mechanisms, limitations, manual/audit obligations.
- **Disposition/deviation proposal**: Finding/construct/baseline scope, rationale, impact and validity.
- **Review packet/compliance assessment**: Portable evidence references, human questions and blockers.

## Success Criteria

### Measurable Outcomes

- **SC010-01**: At least one seeded defect yields a real finding; correction requires a later
  matching analysis and preserves the old result. (AC010-01/02)
- **SC010-02**: Every imported finding retains a source result reference and native identity;
  every deduplicated finding retains all contributing results. (AC010-05)
- **SC010-03**: Empty, partial and unknown extraction cases each fail adequacy even with zero
  findings; unsupported or filtered required checks are named. (AC010-03/06/07)
- **SC010-04**: Every declared applicable guideline has an explicit state; missing denominator,
  manual review or primary capability yields zero accepted compliance claims. (AC010-13/14)
- **SC010-05**: Self-approved, expired, wrong-baseline and prohibited-category deviations each
  leave the affected finding unresolved. (AC010-09–12)

## Assumptions

- The 009 telemetry guard is synthetic exploratory content; owner review remains pending.
- The pinned S-CORE MISRA mapping is a draft with no data rows. No complete guideline set can be
  inferred. A reviewed external mapping can contain IDs/references, with licensed text external.
- Clang-Tidy 19.1.7 and CodeQL 2.21.4 are installed locally, with compiled MISRA pack 2.61.0.
  Installation probes establish availability only. Cppcheck is complementary only. CodeQL
  project-use eligibility, compiled-pack/source reconciliation and compatible report execution
  remain unresolved prerequisites.
- All development checks are fabric evidence. Required engineering acceptance stays human-owned.
- Contract tests and real complementary analyzer integration tests are required for implementation;
  synthetic native-output tests are labelled fixtures and cannot replace a genuine licensed run.
