# Feature Specification: Applicability and work-product planning

**Feature Branch**: `002-applicability-and-work-product-plan`

**Created**: 2026-09-27

**Status**: Implemented and validated as a bounded draft planner; owner/profile review and source-conflict resolution pending.

**Input**: Continue from the 001 handoff. Implement brief §§8, 9.6 and 20.5,
FAB-008–FAB-011, and ADR0003/0004. The implementation delivers the bounded draft planner, schemas, source-cited review-draft
configuration and acceptance evidence; it does not accept target engineering decisions.

## User Scenarios & Testing

### User Story 1 — See the obligations for a change (Priority: P1)

A project engineer supplies the target scope, baseline and change context and receives
a work-product plan. The plan explains which feature, component, module and platform
instances the change requires, including shared upstream obligations and external owners.

**Why this priority**: A missing document must be visible as work to do; an inventory
of existing files cannot establish the required work-product set.

**Independent Test**: A feature with two affected components and declared module/platform
context produces distinct component analyses, shared parent obligations, and separately
identified formal reviews. Removing an existing document changes its disposition to
create without removing the expected instance.

**Acceptance Scenarios**:

1. **Given** a new component and a source-backed scope mapping, **when** planning,
   **then** every expected instance has its native work-product reference, scope,
   purpose, rationale, owner and relevant template/review references. (AC002-01)
2. **Given** two components and several reviews of one module, **when** planning,
   **then** identities remain distinct by target, scope and purpose; a shared platform
   plan is represented once with all requesting scopes recorded. (AC002-02)
3. **Given** an expected artifact is absent or deleted from the inventory, **when**
   replanning, **then** the obligation remains and the missing artifact is explicit.
   Missing inventory knowledge remains unresolved, rather than proving absence. (AC002-03)
4. **Given** a required dependency belongs outside the selected scope, **when** planning,
   **then** its named owner, interface, evidence owed and boundary are recorded; an
   unknown owner or missing parent context blocks the affected plan. (AC002-04)

### User Story 2 — Keep unknown or conflicting applicability visible (Priority: P1)

A reviewer sees why each candidate obligation was selected, excluded from this scope,
or left unresolved. Unsupported profiles and conflicting native sources are actionable
findings; they do not disappear through defaults.

**Why this priority**: Uncertainty about applicability cannot justify reducing obligations.

**Independent Test**: Removing classification, changing to an unsupported profile,
adding an unmapped native work product, or introducing a source conflict retains an
explicit unresolved obligation or coverage finding and blocks the affected assessment.

**Acceptance Scenarios**:

1. **Given** unknown safety/security relevance or an unsupported language/reliability
   combination, **when** planning, **then** affected candidates remain visible with
   blockers and required next actions; the planner never lowers classification. (AC002-05)
2. **Given** a security-relevant feature interacting with a nominally non-security
   component, **when** planning, **then** interaction obligations are considered and
   independent dependency/license/SBOM/vulnerability obligations cannot be suppressed
   by a local security label. (AC002-06)
3. **Given** an unmapped native work product or conflicting process/template references,
   **when** planning, **then** coverage is incomplete and the exact missing/conflicting
   source is reported. No silent ID substitution or blanket default exclusion occurs.
   This includes the pinned safety/security formal-review ID mismatch. (AC002-07)
4. **Given** a source states that an audit is currently tailored out but discussion is
   pending, **when** planning for a target, **then** the source statement is preserved
   and does not become an accepted target tailoring decision. (AC002-08)

### User Story 3 — Propose reuse and tailoring with their evidence (Priority: P2)

An engineer supplies existing artifact bindings, component classification and tailoring
references. The reviewer can distinguish a reuse or exclusion proposal from an effective,
authorized disposition and can see exactly what remains to be resolved.

**Why this priority**: Reuse and tailoring are useful only when their evidence and scope
are explicit; treating every reused component as new is also incorrect.

**Independent Test**: New, reused and modified-reused component scenarios produce different
proposals. Missing authority, stale bindings or prohibited classification retain the
required obligations and prevent effective reuse/exclusion.

**Acceptance Scenarios**:

1. **Given** a reused component, **when** planning, **then** its exact version, classification
   record, Safety Manager classification approval, accepted containing change request
   and selected native route are required as distinct references. The planner
   does not infer classification from raw complexity measurements or an OSS flag. New
   development alone does not trigger the reused-component classification route. (AC002-09)
2. **Given** a reuse proposal, **when** the accepted artifact revision, applicability
   justification or dependency freshness is absent or unverified, **then** proposed reuse
   remains visible but the effective disposition is unresolved. (AC002-10)
3. **Given** a tailoring proposal, **when** upstream permission, bound impact analysis, scope-specific rationale,
   authorized decision or replacement obligation is missing or unverified, **then** the
   original obligation remains. Native tailoring work products and human decisions have
   distinct identities. (AC002-11)
4. **Given** a component without subcomponents proposes coverage by feature analysis,
   **when** planning, **then** explicit coverage rationale and exact bindings are required;
   feature/component analysis and the associated reviews remain distinguishable. (AC002-12)

### User Story 4 — Review and reproduce the plan (Priority: P2)

A reviewer can reproduce a plan from the same inputs and compare a changed baseline
without losing the logical identity of work-product instances.

**Why this priority**: Planning must be reviewable before a workflow or acceptance check
uses the result.

**Independent Test**: Reordering sets or relocating input files preserves the plan;
changing the bound source, mapping or target baseline changes its content identity.
Malformed inputs cannot replace a previous valid plan or alter reference sources.

**Acceptance Scenarios**:

1. **Given** equivalent inputs in another location or order, **when** planning,
   **then** the same instances and deterministic plan result are produced. (AC002-13)
2. **Given** a new native revision or target baseline for the same logical obligation,
   **when** planning, **then** logical instance identity remains stable while its bindings
   and plan content identity change; namespace/purpose changes remain distinct. If both
   native revisions are available at once, an exact selection is required and an ambiguous
   choice blocks planning rather than selecting a latest revision. (AC002-14)
3. **Given** tampered catalogue data, ambiguous identities, malformed inputs or unsafe
   output paths, **when** planning, **then** generation fails with actionable diagnostics
   and preserves prior outputs and all reference inputs. A dangling declared mapping
   reference is invalid input; missing declared scope context instead produces a blocked
   draft with the affected obligation retained. (AC002-15)
4. **Given** any generated plan, including a complete draft or a blocked proposal,
   **when** reviewed, **then** source authority, declared evidence and unresolved decisions
   are distinguishable. No output asserts engineering acceptance or release readiness.
   Self-declared approval flags cannot remove an obligation. (AC002-16)

### Edge Cases

- A process work product exists in multiple namespaces or revisions; a bare ID is ambiguous.
- One formal-review type has several purposes, or one purpose reviews multiple subjects.
- A feature crosses module boundaries; the same parent obligation is requested by two children.
- Unknown classification makes both sides of an applicability choice possible.
- A mapping rule is missing, contradictory, obsolete or references the wrong native type.
- A dependency cycle reaches a fixed set; an expansion limit is exceeded before closure.
- A complete inventory reports absence versus an incomplete inventory has no matching entry.
- An artifact is modified or untracked relative to its claimed revision; its reuse binding is stale.
- A target decision is forged, expired, for another scope or an older baseline.
- Output aliases an input or falls inside a declared reference tree, including through symlinks.

## Requirements

### Functional Requirements

- **002-R01 / FAB-008**: Intake MUST identify target repositories/baselines, intended change,
  scope/context, constraints, allowed paths, language/toolchain/environment, relevance,
  classification, development/reuse origin, assessment intent, roles/independence and
  referenced plans. Missing information MUST be explicit. Execution budgets/configuration
  may be retained as context but MUST NOT authorize execution. (AC002-01,05,15)
- **002-R02 / FAB-008**: Profile support MUST be checked against the exact selected process
  and tool context; unknown or unsupported combinations MUST block affected planning.
  Example classifications MUST NOT become supported engineering profiles. (AC002-05)
- **002-R03 / FAB-009**: Expected obligations MUST derive from a versioned, source-backed
  applicability mapping over the selected native catalogue and declared scope, independently
  of the inventory of existing artifacts. (AC002-01,03,07)
- **002-R04 / FAB-009**: Every candidate work-product/scope pair MUST have a coverage result:
  selected, outside scope with source-backed reason, or unresolved. A mapping gap MUST NOT
  count as non-applicability. All additional mapping-defined review purposes and dependencies
  MUST be covered. (AC002-02,04,07)
- **002-R05 / FAB-009**: Instance identity MUST distinguish target namespace, source-qualified
  native work product, scope kind/identifier and purpose. Versions and baseline hashes MUST
  be bindings separate from that stable identity. (AC002-02,14)
- **002-R06 / FAB-009**: Each instance MUST carry create/update/reuse/tailored_out/
  external_obligation/unresolved disposition, rationale, origin, baseline and relevant
  template, verification and review references. Proposed and effective dispositions MUST
  remain distinct when evidence or authority is pending. (AC002-01,04,10,11,16)
- **002-R07 / FAB-009**: Dependency closure MUST reach a reproducible finite set with explicit
  cross-scope owners; unknown targets or bounded-expansion failure MUST prevent a complete
  plan. Native semantic links alone MUST NOT become scheduling or applicability rules.
  (AC002-02,04,07,13)
- **002-R08 / FAB-010**: Unknown or unverified relevance/classification MUST NOT suppress
  potential mandatory obligations. Conflicting sources MUST retain both facts and identify
  the required resolution. (AC002-05,06,07,08)
- **002-R09 / FAB-010**: Effective tailoring MUST require upstream permission and an authorized,
  current decision and element-level impact analysis bound to scope, subject and baseline.
  A proposal or native status alone
  MUST NOT remove an obligation. (AC002-08,11,16)
- **002-R10 / FAB-011**: Reused/OSS components MUST follow their explicit classification route;
  modified reuse MUST retain reassessment obligations. Classification approval and accepted
  change-request references MUST remain distinct from artifact acceptance. New components MUST NOT be assigned
  a reused-component classification solely because a template contains one. (AC002-09)
- **002-R11 / FAB-011**: Effective reuse MUST require an exact accepted artifact revision,
  applicability rationale and current dependency bindings. Cross-scope analysis coverage
  MUST be explicit and MUST NOT collapse distinct identities. (AC002-10,12,14)
- **002-R12 / FAB-008–FAB-011**: The result MUST preserve every unresolved input/decision and
  identify the affected instances, scope and required action; external obligations MUST
  remain evidence owed, never automatically satisfied. (AC002-04,05,10,11,16)
- **002-R13 / FAB-009**: Equivalent normalized inputs MUST yield identical plan content;
  relevant input, source, mapping, profile or baseline changes MUST alter its content identity.
  (AC002-13,14)
- **002-R14 / FAB-008–FAB-011**: Inputs and outputs MUST be bounded, validated and isolated from
  reference sources; malformed or unsafe requests MUST preserve inputs and prior valid output.
  (AC002-15)
- **002-R15 / FAB-010**: Planning MUST NOT authenticate decisions through self-declared fields
  or convert fixtures into accepted target evidence. Until protected verification is available,
  authority-dependent reuse/tailoring remains proposed with an unresolved effective result.
  Every result MUST leave engineering readiness unevaluated. (AC002-10,11,16)

### Key Entities

- **Intake**: Target context, scope, declared facts, baselines, assessment intent and authority references.
- **Scope**: A feature, component, module or platform with explicit ownership and membership relationships.
- **Planning profile and mapping**: Versioned support bounds and source-backed rules for candidate obligations.
- **Coverage entry**: Why a native work product is selected, outside a scope, or unresolved.
- **Work-product instance**: Stable identity, mutable baseline bindings, disposition and required evidence/reviews.
- **Artifact binding**: Existing native document identity, exact revision/content and declared applicability/freshness.
- **Decision reference**: Claimed human decision and exact subject/scope binding, with separate verification state.
- **Plan result**: Expected instances, closure, coverage, blockers, provenance and deterministic content identity.

## Success Criteria

### Measurable Outcomes

- **SC002-01**: All 16 acceptance scenarios have explicit expected outcomes and actual results
  by implementation closure; new, reused and security-relevant scenarios have explainable differences.
- **SC002-02**: Every native work-product/scope candidate has a coverage entry; every generated
  instance and exclusion has an origin, and missing mappings always produce blockers.
- **SC002-03**: Deleting an existing document removes zero expected obligations; distinct scope
  or formal-review purposes produce zero logical identity collisions in the acceptance set.
- **SC002-04**: All unknown-classification, unapproved-tailoring, stale-reuse and source-conflict
  cases retain affected obligations and report the required resolution.
- **SC002-05**: Equivalent inputs produce identical plans in relocation/order tests; relevant
  baseline or source changes alter plan identity while retaining stable logical instances.
- **SC002-06**: No acceptance scenario writes to reference sources or produces an engineering
  acceptance/readiness claim, including fixture scenarios and complete planning drafts.

## Assumptions

- 001's pinned minimal-consumer catalogue is the starting process baseline; broader target
  documentation build compatibility is not established by 002 planning.
- The initial C++17/MISRA C++:2023 policy comes from the brief. No supported target safety
  profile, accepted ASIL or authorized tailoring is assumed from the example templates.
- Source-backed mappings are explicit project configuration with their own review status;
  they cannot silently replace native authority or expand beyond their declared coverage.
- 002 produces a draft plan and references to decisions. Protected authority verification
  belongs to 005; the initial implementation must expose the resulting authority blockers.
  Fabric acceptance may exercise expected blocked plans without claiming target acceptance.
- Compiler/scheduling, target artifact editing, protected evidence/approval collection,
  runtime/model calls, general change-impact analysis and release readiness are out of scope.
- The user's continuation authorizes this design work; it does not check off human-owned
  001 review items or ratify target engineering decisions.
