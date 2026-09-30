# Feature Specification: Native artifact traceability

**Feature Branch**: `004-native-artifact-traceability`

**Created**: 2026-09-28

**Status**: Planned and tasked; implementation and owner review pending.

**Input**: Continue from the 003 handoff. Specify native target artifact indexing, safe scoped
generation and edits, wrapper and contained-need validation, relation and status validation,
expected-obligation coverage, allocation and verification traceability, impact reporting, and
portable inspection for FAB-016–FAB-018 without treating workflow output as native authority.

## User Scenarios & Testing

### User Story 1 — Inspect native artifacts without losing their meaning (Priority: P1)

A fabric maintainer indexes a bounded target candidate against a pinned S-CORE baseline and gets
a portable view of its native documents, contained needs, identities, statuses, classifications,
relationships, source locations, and revisions. The view preserves native meaning and points back
to the authoritative files rather than becoming a parallel requirements store.

**Why this priority**: Safe generation and trace checking depend on an exact, reviewable account
of what already exists. A lossy or ambiguous index would make later edits and coverage claims
untrustworthy.

**Independent Test**: Index representative feature, component, and analysis documents containing
wrappers, child needs, supported links, and external references; confirm every indexed value and
source location matches the pinned native artifacts and the native documentation build accepts
the unmodified candidate.

**Acceptance Scenarios**:

1. **Given** a complete candidate and pinned native configuration, **when** indexing runs, **then**
   each document wrapper and contained need retains its native ID, type, version, allowed status,
   classification fields, containment, relations, source revision, path, and location. (AC004-01)
2. **Given** the same native ID in different source namespaces or revisions, **when** the target is
   indexed, **then** identities remain source-qualified and no arbitrary entity is selected.
   (AC004-02)
3. **Given** a duplicate ID, unresolved link, unsupported relation, wrong target type, unexpected
   external reference, or invalid status for a native type, **when** validation runs, **then** it
   reports the exact source subject and fails the affected candidate. (AC004-03)
4. **Given** a wrapper with an invalid or unresolved contained need, **when** validation runs,
   **then** wrapper and child results remain distinct and the wrapper cannot mask the child
   failure. (AC004-04)

---

### User Story 2 — Create or update an isolated native candidate safely (Priority: P1)

A maintainer creates a missing artifact or applies an explicitly bounded update using the actual
template and conventions from the pinned S-CORE baseline. The result is an isolated candidate
whose changes are source-cited, deterministic, and limited to the authorized subjects; existing
content outside that scope remains byte-for-byte or semantically intact as appropriate.

**Why this priority**: Native artifacts are the engineering record. Automation is useful only
when it cannot silently rewrite identifiers, decisions, prose, relationships, or history.

**Independent Test**: Generate one representative artifact and change one allowed field in an
existing artifact. Build and re-index each candidate, then show that the expected native elements
changed while unrelated prose, comments, IDs, decisions, and links survived the round trip.

**Acceptance Scenarios**:

1. **Given** a `create` obligation with a resolvable pinned native template and reviewed identity
   policy, **when** generation runs, **then** the isolated candidate uses the exact native wrapper,
   directive types, allowed fields, status vocabulary, and source citations. (AC004-05)
2. **Given** an `update` obligation and a narrow authorized subject, **when** the edit is applied,
   **then** only the requested native elements change and unrelated prose, comments, IDs, manual
   decisions, containment, and trace links survive parsing and re-rendering. (AC004-06)
3. **Given** a missing template, ambiguous identity rule, unsupported field, scope escape, parse or
   round-trip loss, failed native build, or failed re-index, **when** publication is attempted,
   **then** no candidate replaces a prior valid output and every source remains unchanged.
   (AC004-07)
4. **Given** equivalent normalized inputs and an unchanged native baseline, **when** candidate
   generation is repeated in another location, **then** the native content, provenance index,
   report, and candidate identity are identical. (AC004-08)

---

### User Story 3 — Measure expected trace obligations and expose gaps (Priority: P1)

A process owner checks a target against the complete expected obligation set from the sealed plan
and its validated workflow package. The resulting report shows what is expected, what is linked,
what is missing or excluded, and whether allocation and verification paths have the right native
types and scope. Removing an obligation or link cannot make coverage look better.

**Why this priority**: Counting only relationships that happen to exist rewards deletion and hides
unrepresented work. Release decisions need a stable denominator and actionable missing items.

**Independent Test**: Start with a closed feature-to-component-to-verification fixture, then remove
one expected need, one allocation, and one verification link in separate cases. Each mutation keeps
the same expected denominator, lowers the appropriate coverage numerator, and names the missing
subject and required path.

**Acceptance Scenarios**:

1. **Given** a sealed plan and validated workflow package bound to the same sources, **when** trace
   checking runs, **then** expected artifacts and relations are derived before observed links and
   every expectation retains its plan instance, source, scope, purpose, and package obligation.
   (AC004-09)
2. **Given** an expected output or data destination in the workflow package, **when** no matching
   native artifact exists, **then** trace validation fails with an unsatisfied obligation rather
   than treating the declaration as proof of existence or acceptance. (AC004-10)
3. **Given** a present relation with the wrong native type, direction, revision, scope, allocation,
   or verification target, **when** coverage is calculated, **then** it does not satisfy the
   obligation and the mismatch is reported. (AC004-11)
4. **Given** an allowed exclusion or external obligation, **when** coverage is calculated, **then**
   the report includes its authority, rationale, source reference, denominator treatment, and
   unresolved work instead of silently dropping it. (AC004-12)

---

### User Story 4 — Review artifact changes and downstream impact (Priority: P2)

A reviewer can compare native candidate revisions and understand the changed subjects, their
origins, their expected downstream impact, and any gaps that require broader review. The report is
usable without Fabro and distinguishes a reviewed source/profile change from a direct edit to
derived output.

**Why this priority**: Native files can remain syntactically valid while their allocation,
verification, safety, or security context becomes stale. Conservative impact reporting keeps that
risk visible without making an acceptance decision.

**Independent Test**: Change one requirement, interface, allocation, assumption, or analysis input
at a time and verify that the report follows native dependencies plus declared conservative impact
rules. A new unlinked interface or unknown dependency expands review scope or blocks the result;
a direct edit to a generated candidate is reported as drift.

**Acceptance Scenarios**:

1. **Given** a changed native subject or baseline, **when** impact analysis runs, **then** the report
   identifies the revision fingerprints, affected native subjects, dependency paths, expected
   reviews, and unresolved impacts without rewriting prior accepted history. (AC004-13)
2. **Given** a new unlinked interface, shared resource, allocation change, assumption change, or
   unknown dependency, **when** impact analysis runs, **then** review scope expands conservatively
   or the candidate is blocked; absence of an old link never implies no impact. (AC004-14)
3. **Given** a direct edit to generated native output, **when** drift checking runs, **then** it is
   distinguished from an authorized source/profile change and cannot become authority without
   regeneration or an explicitly reviewed native update. (AC004-15)
4. **Given** any successful index, candidate, coverage, or impact report, **when** it is reviewed
   offline, **then** it remains understandable without Fabro and states that evidence trust,
   engineering acceptance, readiness, release, registration, and execution are unevaluated.
   (AC004-16)

### Edge Cases

- A document wrapper has an allowed status while one contained need has a forbidden, missing, or
  unresolved status.
- A contained need appears in more than one wrapper, has a missing parent, or points to a parent
  of the wrong native type.
- Two sources use the same native ID, or a new ID collides after namespace or case normalization.
- A native link resolves by text but uses the wrong relation field, direction, target type, scope,
  source revision, or version selector.
- An external link is syntactically resolvable but not permitted by the selected target profile.
- An expected artifact is wholly absent, so no discovered link exists from which to infer the gap.
- Removing a need, link, or source file would otherwise reduce both the coverage numerator and
  denominator and falsely preserve or improve the percentage.
- One artifact partially satisfies an obligation but lacks its allocation or verification path.
- Several plan instances legitimately point to one native artifact, or one plan instance requires
  several native artifacts for different purposes.
- A workflow node ID resembles a native need ID and would collide if used as artifact authority.
- An edit changes only line endings or directive formatting, while another edit changes native
  semantics without changing rendered prose.
- A parser round trip reorders fields, drops a comment, normalizes manual prose, or rewrites an
  unrelated link.
- A template or native metamodel changes while the plan and edit request remain unchanged.
- A previously accepted artifact is current for an old baseline but stale for the candidate
  baseline.
- A new interface, shared resource, assumption, or analysis subject has no existing incoming or
  outgoing trace links.
- A candidate exceeds a declared file, byte, entity, relation, expectation, or diagnostic limit.

## Requirements

### Functional Requirements

- **004-R01 / FAB-016**: Every operation MUST accept only exact supported versions of the source
  lock, native catalogue/metamodel, sealed plan, validated workflow package, artifact profile,
  request, and target snapshot that it consumes. It MUST verify their identities, digests,
  closure, mutual plan/source bindings, and declared files before using them. (AC004-01,05,09,16)
- **004-R02 / FAB-016**: Native target artifacts and the pinned S-CORE configuration MUST remain
  authoritative. Any machine-readable index MUST be derived from or resolve exactly to those
  artifacts, and workflow node IDs MUST NOT be used as native artifact IDs. (AC004-01,02,09,10)
- **004-R03 / FAB-016**: Indexing and candidate generation MUST preserve source-qualified native
  IDs, document IDs, need IDs, types, versions, type-specific status semantics, classification
  fields, containment, native relation names/directions, source revisions, and source locations.
  Unknown or lossy translations MUST fail. (AC004-01–05)
- **004-R04 / FAB-016**: Creation MUST use an actual native template and configuration selected
  from the pinned baseline. New identifiers and fields MUST follow explicit reviewed native or
  project policy; absence or ambiguity of that authority MUST block generation. (AC004-05,07)
- **004-R05 / FAB-016**: Automated creation and updates MUST occur only in an isolated candidate
  revision and within the declared target, path, subject, field, and relation scope. Source inputs
  and historical accepted revisions MUST remain unchanged. (AC004-05–07,13)
- **004-R06 / FAB-016**: Every generated or changed native semantic element MUST cite the exact
  plan instance, native definition/template, source revision, request/profile rule, and, where
  applicable, workflow-package obligation from which it was derived. Missing or mismatched
  authority MUST fail candidate validation. (AC004-05,06,08,09)
- **004-R07 / FAB-016**: Updates MUST use structure-aware or equivalently bounded edits followed
  by parse, re-index, native-build, and semantic round-trip checks. Unrelated prose, comments,
  identifiers, manual decisions, containment, ordering where meaningful, and existing trace links
  MUST survive the round trip. (AC004-06,07)
- **004-R08 / FAB-018**: Document wrappers and every contained need MUST be validated separately
  and together for required fields, native type, allowed status, containment, identifiers, and
  relations. A valid wrapper MUST NOT mask an invalid, missing, or unresolved child. (AC004-01,04)
- **004-R09 / FAB-016/FAB-018**: Validation MUST reject duplicate or colliding IDs, dangling or
  ambiguous references, unsupported relations, wrong relation direction or source/target type,
  forbidden external references, invalid version selectors, containment defects, and statuses not
  allowed for the exact native type. (AC004-02–04)
- **004-R10 / FAB-017**: The expected obligation set MUST be established independently of the
  links and artifacts discovered in the target. It MUST combine applicable sealed-plan instances
  with their package-declared expected outputs and boundaries while retaining native source,
  scope, purpose, disposition, and authority. (AC004-09,10,12)
- **004-R11 / FAB-017**: Trace validation MUST compare the complete expected obligation set with
  observed native artifacts and relations. An absent artifact or link, including one with no
  remaining representation in the target, MUST remain in the denominator and be reported as
  unresolved. Any unresolved or mismatched mandatory obligation MUST fail trace validation
  for the affected candidate. (AC004-09–12)
- **004-R12 / FAB-017**: Coverage results MUST report numerator, denominator, permitted exclusions,
  unresolved and mismatched items, and exact source references for each metric. Exclusions MUST
  retain their authority and rationale and MUST NOT silently improve coverage. (AC004-09–12)
- **004-R13 / FAB-017**: Relevant expected obligations MUST require correct native allocation and
  verification linkage for their declared scope and purpose. A present but wrongly typed,
  directed, scoped, versioned, or allocated link MUST NOT count as coverage. (AC004-10–12)
- **004-R14 / FAB-017**: Selected trace profiles MUST support the applicable native paths from
  context to feature requirements, feature requirements to architecture/component allocation,
  component requirements to design/implementation, requirements/design to verification cases and
  results, safety/security analysis to mitigations and verification, assumptions of use to their
  responsible boundary/manual, work-product instances to reviews/baselines, and aggregate reports
  to their included evidence/dependencies. Only native relation names discovered in the pinned
  configuration MAY represent these paths. (AC004-03,09–12)
- **004-R15 / FAB-017**: A readable trace report and its machine-checkable counterpart MUST show
  every expected path, observed hop, native subject and revision, coverage disposition, source
  citation, exclusion, and actionable gap. Trace existence MUST NOT be described as proof of
  requirement correctness, test adequacy, mitigation effectiveness, evidence trust, or approval.
  (AC004-09–12,16)
- **004-R16 / FAB-016/FAB-017**: Change and impact analysis MUST use native dependency links plus
  conservative declared rules for shared resources, allocation, assumptions, interfaces, analysis
  coverage, and baseline changes. New unlinked subjects and unknown dependencies MUST expand the
  review scope or block the result rather than imply no impact. (AC004-13,14)
- **004-R17 / FAB-016**: Revision fingerprints and reports MUST distinguish prior accepted history
  from the current candidate. Staleness or invalidation MUST be represented in the candidate
  assessment and MUST NOT rewrite the status or acceptance facts of an earlier baseline.
  (AC004-13,14)
- **004-R18 / FAB-016**: Direct changes to generated candidates MUST be detected and distinguished
  from reviewed request, source, template, metamodel, or profile changes. A direct output edit MUST
  NOT become authority merely because it parses or builds. (AC004-08,15)
- **004-R19 / FAB-016/FAB-017**: Equivalent normalized inputs MUST yield identical native candidate
  content, indexes, reports, provenance, and identities across relocation and independent input
  ordering. All operations MUST enforce declared finite limits and publish a complete candidate
  atomically only after every required check passes. (AC004-07,08)
- **004-R20**: Expected outputs, completion declarations, and data destinations MUST be treated as
  obligations and boundaries, never as proof that an artifact exists, is correct, has acceptable
  evidence, or was approved. (AC004-09,10,16)
- **004-R21**: Increment 004 MUST NOT call a model/provider, mutate a production target, register or
  execute a workflow, authenticate an approval, accept trusted evidence, or change engineering or
  release readiness. Reports MUST retain `registration`, `execution`, `evidence`, `acceptance`,
  `engineering_readiness`, and `release` as `not_evaluated`. (AC004-07,16)

### Key Entities

- **Native target snapshot**: Bounded immutable input revision containing authoritative native
  documents, configuration, source identity, and declared file closure.
- **Document wrapper**: Native document-level record with its own identity, type, status,
  metadata, source location, and containment of needs.
- **Contained need**: Native typed engineering item within a wrapper, with its own ID, fields,
  status, relations, provenance, and validation result.
- **Native artifact index**: Derived portable inventory that resolves each wrapper, need, field,
  relationship, and revision back to authoritative target content.
- **Artifact request/profile**: Bounded reviewed instruction and policy selecting target subjects,
  templates, identity rules, permitted edits, trace paths, external references, and finite limits.
- **Candidate revision**: Isolated generated or edited native artifact set that has not acquired
  engineering acceptance merely by passing structural checks.
- **Expected obligation**: Required artifact or relationship derived independently from the sealed
  plan and its package binding, including scope, purpose, disposition, source, and authority.
- **Observed trace**: Native relationship path found in the candidate and evaluated against an
  expected obligation and the selected relation/type rules.
- **Coverage result**: Numerator, denominator, exclusions, unresolved items, mismatches, and source
  references for one declared trace metric.
- **Impact result**: Conservative set of changed and potentially affected native subjects,
  baselines, required reviews, unknown dependencies, and blocking gaps.
- **Artifact report**: Portable human-readable and machine-checkable record of validation,
  provenance, coverage, drift, impact, candidate identity, and explicitly unevaluated boundaries.

## Success Criteria

### Measurable Outcomes

- **SC004-01**: Representative feature, component, and analysis documents preserve 100% of their
  indexed native IDs, types, allowed statuses, classifications, containment, relations, and source
  locations through an unmodified index/build cycle.
- **SC004-02**: One create case and one scoped-update case for each representative document class
  build successfully with the pinned native documentation baseline; unrelated content, comments,
  IDs, manual decisions, and trace links have zero unintended changes.
- **SC004-03**: All fixtures containing duplicate/colliding IDs, broken or ambiguous links, wrong
  relation types/directions/targets, forbidden external references, invalid wrapper/child status,
  missing child needs, scope escape, or lossy round trips are rejected before candidate
  publication.
- **SC004-04**: For every acceptance fixture, expected-obligation coverage reports exact numerator,
  denominator, exclusions, unresolved items, and source references; deleting an artifact or link
  never reduces its expected denominator.
- **SC004-05**: All missing or mismatched allocation and verification obligations in the
  representative feature/component/analysis fixtures are detected, including obligations with no
  observed artifact or link.
- **SC004-06**: Independent relocation and set-order permutations produce byte-identical native
  candidate content, index, trace/impact reports, provenance, and candidate identity in 100% of
  deterministic acceptance cases.
- **SC004-07**: Each single-subject requirement, interface, allocation, assumption, analysis, or
  baseline mutation produces the expected conservative impact set; every unknown dependency and
  new unlinked subject expands review scope or blocks the result.
- **SC004-08**: Every successful artifact report is usable without Fabro, maps all generated or
  changed semantics to exact sources, reports zero direct-output drift, and marks registration,
  execution, evidence, acceptance, engineering readiness, and release as `not_evaluated`.

## Assumptions

- Increment 001's source locks, exported native metamodel, source-qualified identities, and
  catalogue form the discovery authority for the selected native baseline.
- Increment 002 supplies a complete sealed plan. Increment 003 supplies a self-consistent,
  validated package bound to that plan, but its workflow nodes and traversal do not become native
  artifact authority.
- Contract development and acceptance use representative fixture targets and fixture workflow
  packages until production execution mappings and target-owner decisions are reviewed.
- Actual S-CORE templates and documentation configuration for the selected baseline are available
  through pinned, immutable source references. A missing or incompatible template blocks the
  affected create operation.
- Project-specific identifier allocation, permitted edit scope, external-reference policy, and
  trace profiles are reviewed configuration with exact sources; 004 does not invent them from
  names, prose, or workflow shape.
- Passing native build, structure, relation, coverage, drift, and impact checks establishes only a
  reviewable candidate. Evidence trust and human engineering acceptance begin in increment 005;
  runtime registration and execution begin in increment 006.
