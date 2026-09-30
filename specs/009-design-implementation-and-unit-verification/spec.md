# Feature Specification: Detailed design, implementation and unit verification

**Feature Branch**: `009-design-implementation-and-unit-verification`

**Created**: 2026-09-30

**Status**: Draft for implementation. No design acceptance exists for the demo mitigation (008
stops at `awaiting_decision`), no protected evidence collector exists (005 T009), and no live model
call is authorized. Owner review of the verification and toolchain profiles is pending.

**Input**: Continue from the [008 handoff](../../docs/handoff/008-to-009.md). Specify brief §12.1,
§12.2 and §20.12 and FAB-036–FAB-038: the C++17 telemetry freshness guard, native detailed
design, a build/test adapter, requirement-to-test mapping with deterministic time inputs,
structural-coverage import, code-inspection packets, retained failure evidence with a correction
loop, and a milestone report listing what remains pending.

## User Scenarios & Testing

### User Story 1 — Check detailed design and source traceability (Priority: P1)

A developer submits the component's native requirements, detailed design and sources. The fabric
checks that the detailed design follows the pinned template, that every source unit carries
native requirement tags resolving to real component requirements or AoUs, and that every
in-scope requirement is implemented by at least one unit.

**Why this priority**: Code without traceable design and requirement links cannot be verified or
reviewed against intent.

**Independent Test**: Check the demo, then remove one tag, point one tag at an unknown ID and drop
one template section.

**Acceptance Scenarios**:

1. **Given** the demo design and sources, **when** checked, **then** each unit, its digest, its
   requirement tags and each requirement's implementing units are reported. (AC009-01)
2. **Given** a missing template section, placeholder, untagged unit, unknown or wrongly typed tag,
   or unimplemented requirement, **when** checked, **then** the fault is named. (AC009-02)

---

### User Story 2 — Build and test the actual code on a recorded baseline (Priority: P1)

The fabric compiles the C++17 sources and tests with a recorded local toolchain and the pinned
S-CORE warning policy, runs the tests, and records every result with the exact source, test,
compiler, flag and library identities. Test metadata follows the native verification rules, and
requirement coverage and structural coverage are reported without an invented threshold.

**Why this priority**: The demo must actually compile and exercise positive, boundary and failure
behaviour, and results must bind to what was tested.

**Independent Test**: Run the demo suite; change one source byte and confirm the baseline changes;
swap the compiler identity and confirm the run is refused.

**Acceptance Scenarios**:

1. **Given** the demo, **when** run, **then** it compiles under the selected warning policy and its
   positive, boundary and failure tests run, each result bound to source/test/tool digests.
   (AC009-03)
2. **Given** tests missing `TestType`, `DerivationTechnique`, `Description` or a verified
   requirement link, or using unknown values or IDs, **when** run, **then** the native metadata
   rule is named and the run is not a pass. (AC009-04)
3. **Given** a compiler, library or policy that differs from the profile, or policy flags the
   compiler cannot honour, **when** run, **then** the run is refused or the gap is explicit.
   (AC009-05)
4. **Given** coverage instrumentation, **when** run, **then** per-unit line and branch counts are
   reported with no pass/fail threshold. (AC009-06)

---

### User Story 3 — Retain failures and loop to the owning artifact (Priority: P1)

When a build or test fails, the full diagnostics are retained and the milestone report routes each
failure to the artifacts it concerns (verified requirement, implementing units, test) as review
questions, bounded by an attempt budget. A later pass counts only on a different source baseline;
a pass on the same baseline after a failure is a nondeterminism finding.

**Why this priority**: A failing test must produce retained evidence and a correction loop.

**Independent Test**: Run the seeded off-by-one variant, then the corrected source, then rerun the
failing baseline.

**Acceptance Scenarios**:

1. **Given** a failing test, **when** the milestone report is built, **then** the failure, its
   retained output and its route are listed, and the requirement is not verified. (AC009-07)
2. **Given** a later passing run on a changed source baseline, **when** reported, **then** the
   failure is resolved on that baseline and the history is kept. (AC009-08)
3. **Given** the same baseline failing then passing, **when** reported, **then** the result is
   nondeterministic and blocks. (AC009-09)
4. **Given** the attempt budget is exhausted, **when** reported, **then** it escalates to a human.
   (AC009-10)

---

### User Story 4 — Milestone report and code-inspection packet (Priority: P1)

The milestone report summarizes design, build and test status on the current baseline, the
requirement-to-test matrix, candidate evidence for 008 mitigating requirements, the native
implementation-inspection checklist with answers left to the reviewer, and every obligation still
pending (MISRA/static analysis, integration, security, release, protected evidence, design
acceptance).

**Why this priority**: The milestone must say what is not done.

**Independent Test**: Build the report for the passing demo with the 008 v2 report.

**Acceptance Scenarios**:

1. **Given** a passing run, **when** reported, **then** the verification results are labelled local
   unprotected execution, not eligible 005 evidence, and the 008 mitigation remains without
   closure evidence. (AC009-11)
2. **Given** any report, **when** built, **then** MISRA, static analysis, integration, security,
   release, protected evidence, design acceptance and code inspection are listed as pending with
   their owning increment or authority. (AC009-12)
3. **Given** the inspection packet, **when** built, **then** each unit digest and the native
   checklist items are present with `pending_human` answers. (AC009-13)

### Edge Cases

- A test binary crashes or times out before writing its XML report.
- A test reports `<error>` (native parser treats it as failed) or is skipped.
- A tag appears in a comment inside a string literal.
- Coverage files are missing because instrumentation failed.
- A source file is added that the design does not mention.

## Requirements

### Functional Requirements

- **009-R01 / FAB-036**: Detailed design MUST be checked against the pinned template sections and
  work product; units are the component's source files; each unit MUST carry native `req-Id` tags
  resolving to component requirements or AoUs; each in-scope requirement MUST be implemented.
  (AC009-01/02)
- **009-R02 / FAB-037**: Builds and tests MUST run only with a toolchain matching the recorded
  profile (compiler, library and policy digests) in a disposable build directory, with the
  selected pinned warning flags and an explicit record of unavailable policy levels. (AC009-03/05)
- **009-R03 / FAB-037**: Each result MUST bind to the source, test, toolchain and flag digests and
  the native result classes (`passed`, `failed`, `skipped`; `error` is failed). (AC009-03)
- **009-R04 / FAB-037**: Test metadata MUST follow `gd_req__verification_link_tests`,
  `gd_req__verification_checks` and `gd_req__verification_checks_extended`. (AC009-04)
- **009-R05 / FAB-037**: Requirement coverage MUST distinguish fully/partially verified,
  failing and unverified; structural coverage MUST be reported without a threshold. (AC009-06)
- **009-R06 / FAB-038**: Failures MUST retain bounded raw diagnostics and route to the owning
  requirement, units and test with a bounded attempt loop and human escalation. (AC009-07/10)
- **009-R07 / FAB-038**: Pass/fail history MUST be kept; resolution requires a changed source
  baseline; same-baseline disagreement is nondeterminism. (AC009-08/09)
- **009-R08 / FAB-037**: Results MUST be labelled local unprotected execution and never become 005
  evidence, design acceptance or closure. (AC009-11)
- **009-R09**: The milestone report MUST list pending obligations and a code-inspection packet with
  the native checklist unanswered. (AC009-12/13)
- **009-R10**: Commands MUST give stable 0/1/2 outcomes, preserve prior outputs on error, and never
  write sources, native files or reference repositories.

### Key Entities

- **Verification profile**: Pinned native verification rules, metadata values, tags, template
  sections, inspection checklist, loop budget, pending-obligation catalogue.
- **Toolchain profile**: Compiler, test library, coverage tool, digests and selected policy flags.
- **Design report**: Units, tags, requirement implementation map, findings.
- **Verification run**: Baseline, build steps, test results, metadata findings, coverage.
- **Milestone report**: History, routes, requirement matrix, inspection packet, pending list.

## Success Criteria

### Measurable Outcomes

- **SC009-01**: The demo compiles with zero warnings under the selected policy and runs at least one
  positive, one boundary and one failure test per requirement. (AC009-03)
- **SC009-02**: Every result carries source, test and toolchain digests; changing one byte changes
  the baseline digest. (AC009-03)
- **SC009-03**: The seeded defect yields one failing run with retained output and a route; the fix
  yields a pass on a new baseline with both runs in history. (AC009-07/08)
- **SC009-04**: Every metadata and design fault case is named. (AC009-02/04)
- **SC009-05**: The report lists all pending obligation classes and zero items claim acceptance.
  (AC009-11–13)

## Assumptions

- Native pins: `process_description` `98d1d5f`, `module_template` `c4d4ad0`, `docs-as-code`
  `d5f3de6`, `score_cpp_policies` `9bcfe82`.
- S-CORE builds with Bazel; Bazel and the S-CORE toolchain are not available offline here, so a
  recorded local GCC 11.4 + GoogleTest 1.11 toolchain is used as a candidate and labelled as such.
- 008 did not accept the stale-data design; implementing it here is exploratory work that cannot
  satisfy a design gate or closure.
- The demo code and tests are written by the implementer, not a model call.
