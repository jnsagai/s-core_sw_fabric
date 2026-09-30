# Feature Specification: Deterministic workflow compiler

**Feature Branch**: `003-deterministic-workflow-compiler`

**Created**: 2026-09-27

**Status**: Specified for planning; implementation and owner review pending.

**Input**: Continue from the 002 handoff. Specify and plan the deterministic compiler required
by brief §20.6 and FAB-012–FAB-015. Transform a complete sealed work-product plan plus reviewed
execution mappings into a reproducible, validator-accepted Fabro package without registering or
running it.

## User Scenarios & Testing

### User Story 1 — Compile obligations into an executable package (Priority: P1)

A fabric maintainer supplies a complete, sealed work-product plan and reviewed execution
configuration. The compiler produces one closed workflow package in which every planned
obligation has explicit work, review, evidence, or external-boundary handling and every generated
element can be traced to its origin.

**Why this priority**: The package is the first usable bridge from planned native obligations to
later Fabro execution. Missing or implicit obligations would make every later run untrustworthy.

**Independent Test**: A small complete draft plan with two dependent work-product instances,
separate review purposes, and one shared gate produces the exact expected nodes, edges, package
files, source-map entries, and content identity; the selected Fabro validator accepts it.

**Acceptance Scenarios**:

1. **Given** a valid complete plan and a reviewed mapping for every required instance, **when**
   compilation runs, **then** each instance has explicit generated actions, inputs, outputs,
   actor/permission bindings, evidence expectations, and terminal handling. (AC003-01)
2. **Given** several instances that require the same scope-bound review, **when** compilation
   runs, **then** the review gate is represented once only when its subject, purpose, authority
   requirement, and bindings agree; distinct review purposes remain distinct. (AC003-02)
3. **Given** dependencies and shared parent obligations, **when** compilation runs, **then**
   ordering edges come only from reviewed execution mappings, preserve every prerequisite, and
   do not reinterpret native semantic links as schedule edges. (AC003-03)
4. **Given** a generated package, **when** a reviewer follows any node, edge, gate, or packaged
   support file through the source map, **then** the exact plan instance, rule/policy origin,
   source reference, and compiler decision are identifiable. (AC003-04)

---

### User Story 2 — Reject bypasses and unsafe control flow (Priority: P1)

A reviewer can rely on compilation to fail before package publication when a graph omits a
mandatory gate, bypasses review on a success or failure route, contains an unbounded feedback
cycle, refers to an absent dependency, or weakens a fail-closed outcome.

**Why this priority**: A syntactically valid graph can still violate engineering process. Semantic
validation is the safety boundary for the derived execution representation.

**Independent Test**: Mutating one valid source mapping at a time to remove a gate, add a bypass,
drop a failure route, create an unbounded cycle, or reference a missing node causes a stable,
actionable compilation failure and leaves any previous valid package unchanged.

**Acceptance Scenarios**:

1. **Given** a required human review, **when** any route reaches success without that gate or an
   explicit authorized exclusion, **then** compilation fails with the bypass path and affected
   obligation identified. (AC003-05)
2. **Given** a deterministic check or action that can fail, block, time out, or produce an unknown
   result, **when** its mapping lacks explicit non-success handling, **then** compilation fails
   rather than defaulting to success. (AC003-06)
3. **Given** a feedback or retry route, **when** no finite attempt/visit bound and terminal
   exhausted route are declared, **then** compilation fails; a bounded loop retains its limit and
   exhaustion destination in the package and source map. (AC003-07)
4. **Given** blocked, incomplete, tampered, drifted, or semantically unsupported input, **when**
   compilation is requested, **then** no new package replaces a prior valid output. (AC003-08)

---

### User Story 3 — Review workflow meaning and drift (Priority: P2)

A process owner can review what changed between two generated packages without reading raw graph
syntax. The report separates obligation changes, execution-policy changes, permissions, gates,
control flow, packaged files, and compiler/validator baseline changes.

**Why this priority**: Generated output must remain derived and reviewable. Manual edits or hidden
policy changes cannot become a parallel source of engineering process.

**Independent Test**: Recompiling unchanged sources reports no semantic change; modifying one
reviewed source changes only the expected semantic category; editing generated output directly is
reported as drift and cannot be accepted as the new source.

**Acceptance Scenarios**:

1. **Given** equivalent normalized inputs in different directories or set-like orders, **when**
   compiled independently, **then** package semantic identity, source map, and report are
   identical. (AC003-09)
2. **Given** one changed obligation, gate, permission, loop bound, or packaged support file,
   **when** packages are compared, **then** the semantic diff reports the exact category, source,
   and affected nodes/instances. (AC003-10)
3. **Given** a hand-edited generated file, **when** drift verification runs against its declared
   sources, **then** the changed path and expected/actual content identities are reported and the
   package is unusable until regenerated or the source mapping is reviewed. (AC003-11)
4. **Given** a source change that produces the same visible graph text but changes a semantic
   binding, **when** compilation runs, **then** the package identity still changes and the source
   map records the new binding. (AC003-12)

---

### User Story 4 — Validate a closed, portable package (Priority: P2)

A maintainer receives a self-contained package whose manifest lists every graph, prompt,
configuration, policy, and support file needed by the selected validator. Validation can run
offline against the declared profile, without registering a workflow or creating a run.

**Why this priority**: Later runtime registration must receive an immutable, reviewable closure.
Compiler success cannot depend on undeclared files or host-specific paths.

**Independent Test**: The package validates in a relocated directory; deleting, adding,
renaming, escaping, or changing a referenced file fails closure or integrity validation. No run,
model call, target edit, approval, or readiness transition occurs.

**Acceptance Scenarios**:

1. **Given** a generated package, **when** the selected native validator examines it, **then** its
   graph and manifest are accepted under the exact declared validation profile. (AC003-13)
2. **Given** a referenced prompt/configuration/script, **when** it is absent, outside the package,
   ambiguously cased, duplicated, or content-mismatched, **then** package validation fails with the
   referencing node and path identified. (AC003-14)
3. **Given** any generated human-interaction node, **when** its configuration permits automatic
   approval, replayed approval, or a success-producing timeout default, **then** semantic
   validation rejects the package. (AC003-15)
4. **Given** a successful compile and validation, **when** the report is reviewed, **then** it
   states that registration, execution, evidence trust, engineering acceptance, and release
   readiness remain unevaluated and outside increment 003. (AC003-16)

### Edge Cases

- Two rules request one logical gate but disagree on its subject, independence, permissions, or
  failure route.
- An instance is present but effectively unresolved, externally owed, or bound to a blocked
  finding despite a misleading top-level status.
- A graph is acyclic except for a retry edge whose bound is zero, negative, missing, or larger
  than the selected profile permits.
- A conditional has overlapping, contradictory, unreachable, or incomplete outcomes.
- An agent action omits its allowed paths, data destinations, model-capability binding, or a
  finite execution budget, or requests a capability/budget above the selected profile.
- A fan-out has no complete fan-in, or a merge allows partial child success where all results are
  required.
- A failure route loops into a success path without re-evaluating the failed predicate.
- A generated identifier collides after escaping or case normalization.
- A prompt/support file is referenced by content under two paths or by one path with two hashes.
- A package contains an undeclared file, symlink, hardlink alias, absolute path, traversal, or
  host-specific path.
- The compiler or validator profile changes while plan and mapping inputs stay constant.
- The native validator accepts syntax that the fabric semantic validator must still reject.
- A prior package is valid but the next request is malformed, unsupported, or exceeds a bound.

## Requirements

### Functional Requirements

- **003-R01 / FAB-013**: Compilation MUST accept only exact supported versions of a sealed 002
  plan, execution mapping, compiler profile, and validator profile. It MUST verify every
  self-digest, selected semantic binding, and declared file hash before deriving output.
  (AC003-08,09,13,14)
- **003-R02 / FAB-012**: Every generated node, edge, gate, packaged file, retry/failure route, and
  scheduling choice MUST identify its origin as upstream process, reviewed project
  configuration, or an authorized human decision with an exact source reference. Missing or
  unverified authority MUST NOT become executable policy. (AC003-01,03,04,12)
- **003-R03 / FAB-012**: The compiler MUST require an explicit reviewed execution mapping for every
  compilable plan instance and MUST preserve its native work-product identity, scope, purpose,
  applicability, disposition, templates, reviews, dependencies, and source bindings.
  (AC003-01–04)
- **003-R04 / FAB-014**: A blocked plan, incomplete closure, unresolved effective disposition,
  unknown mandatory applicability, unresolved external obligation, dangling instance, or
  unsupported plan finding MUST prevent executable package generation. (AC003-05,08)
- **003-R05 / FAB-014**: Human, deterministic-check, agent, command, conditional, fan-out, fan-in,
  and terminal actions MUST have explicit typed semantics. Shape, title, filename, prose, or
  native semantic relations MUST NOT implicitly select execution behavior. (AC003-01,03,05,06)
- **003-R06 / FAB-014**: Every mandatory human review MUST dominate all successful terminal paths
  for its bound subject unless an exact authorized exclusion is supplied. The compiler MUST
  report a concrete bypass path when this invariant fails. (AC003-05)
- **003-R07 / FAB-014**: Every fallible action and predicate MUST define explicit success and
  non-success routing. Missing, unknown, stale, timeout, malformed, infrastructure, and exhausted
  outcomes MUST NOT reach success through a default or omitted edge. (AC003-06)
- **003-R08 / FAB-014**: Every cycle, retry, feedback, correction, or re-review route MUST declare a
  positive finite bound within the selected profile and an explicit exhausted destination.
  Bounded cycles MUST remain distinguishable from ordinary dependency edges. (AC003-07)
- **003-R09 / FAB-014**: Fan-out/fan-in mappings MUST state whether all or a reviewed subset of
  child outcomes is required. Mandatory obligations MUST use complete fan-in and MUST NOT pass
  vacuously on an empty or partial child set. (AC003-03,05,06)
- **003-R10 / FAB-012**: Each executable action MUST bind its role, allowed inputs, expected
  outputs, allowed paths, data destinations, write scope, tool/permission profile, model-capability
  profile or explicit non-model binding, positive finite execution budgets within the selected
  compiler profile, completion predicate, evidence expectation, failure behavior, and prohibited
  authority. Missing, unlimited, unknown, or above-profile bindings MUST block compilation.
  (AC003-01,04,06)
- **003-R11 / FAB-013**: Equivalent normalized sources MUST produce byte-identical semantic
  manifests, source maps, compile reports, and generated files across relocation and independent
  input ordering. Absolute operational paths, timestamps, random values, and host state MUST NOT
  affect semantic identity. (AC003-09)
- **003-R12 / FAB-013**: The package manifest MUST close over every referenced graph, prompt,
  configuration, schema, policy, and support file using relative logical paths and content
  digests. Undeclared files and unsafe path aliases MUST be rejected. (AC003-13,14)
- **003-R13 / FAB-012/FAB-013**: The source map MUST cover every generated semantic element and
  retain plan instance IDs, execution-rule IDs, source references, decision references,
  transformation rationale, and output locations. Unmapped generated semantics MUST fail
  validation. (AC003-04,10,12)
- **003-R14 / FAB-015**: The compiler MUST emit a structured semantic diff between selected
  package identities and a drift result that distinguishes reviewed source changes from direct
  generated-output edits. A generated edit MUST be resolved through source change and
  regeneration, never adopted as authority by itself. (AC003-10,11)
- **003-R15 / FAB-014**: Generated human interactions MUST prohibit automatic approval, replayed
  approval, success-producing timeout defaults, and any configuration that treats workflow
  traversal as an authenticated engineering decision. (AC003-05,15)
- **003-R16 / FAB-013/FAB-014**: Compiler semantic validation MUST remain stricter than native
  syntax validation where fabric invariants require it. A successful native validator result
  MUST NOT override a semantic failure. (AC003-05–08,13,15)
- **003-R17 / FAB-013**: The compiler MUST bind its own version, normalized source digests, selected
  validator profile and validator identity into package identity. Relevant changes MUST alter the
  semantic digest while stable logical node identities remain unchanged where their source
  identity is unchanged. (AC003-09,10,12,13)
- **003-R18 / FAB-014/FAB-015**: Output MUST be bounded, validated, and atomically replaced only
  after all compiler and validator checks pass. Invalid requests MUST preserve prior valid
  packages and every input/reference source. (AC003-07,08,14)
- **003-R19**: Compilation and validation MUST NOT register or execute a workflow, call a model,
  modify target/native artifacts, authenticate approvals, collect trusted evidence, or change
  engineering/release readiness. (AC003-16)

### Key Entities

- **Execution mapping**: Reviewed rules that map planned obligations to explicit action and
  control-flow semantics with origins.
- **Compiler profile**: Supported limits, identifier rules, output contract, and semantic
  invariant versions.
- **Validator profile**: Exact native validator baseline, accepted package/graph subset, and
  validation invocation contract.
- **Execution node**: Stable logical action identity plus role, inputs, outputs, permissions,
  evidence expectations, and failure semantics.
- **Execution edge**: Typed prerequisite, outcome, branch, merge, retry, or feedback relation with
  a declared origin.
- **Gate**: A deterministic or human review boundary bound to exact subjects and explicit
  success/non-success routing.
- **Workflow package**: Closed generated file set plus semantic manifest and content identity.
- **Source-map entry**: Mapping from generated elements and file locations to plan, rule, source,
  decision, and transformation rationale.
- **Compile report**: Validation outcomes, retained limitations, package identity, and actionable
  diagnostics.
- **Semantic diff/drift result**: Structured changes between source/package identities and direct
  generated-output divergence.

## Success Criteria

### Measurable Outcomes

- **SC003-01**: Every compilable plan instance and every generated node, edge, gate, and support
  file has exactly one or more explicit source-map origins; unmapped generated semantics count is
  zero.
- **SC003-02**: All required-gate bypass, missing failure route, missing or excessive action
  capability/budget, dangling dependency, incomplete
  fan-in, unbounded cycle, automatic/replayed approval, and unsafe file-closure fixtures are
  rejected before output replacement.
- **SC003-03**: At least three representative packages—linear obligations, shared parallel review,
  and bounded correction feedback—are accepted by the selected native validator and the stricter
  semantic validator.
- **SC003-04**: Independent relocation and set-order permutations produce identical semantic
  manifests, source maps, reports, generated bytes, and package digest in 100% of acceptance
  cases.
- **SC003-05**: Each single-source semantic mutation in the acceptance suite produces a diff in the
  expected category with no unrelated category changes; each direct generated edit produces a
  drift failure.
- **SC003-06**: Invalid or unsupported requests replace zero prior valid package files and modify
  zero declared input/reference files.
- **SC003-07**: Every successful report states that runtime registration/execution, trusted
  evidence, human acceptance, engineering readiness, release, and deployment remain
  unevaluated.
- **SC003-08**: Representative maximum-bound compilation completes deterministically within the
  declared limits; exceeding any node, edge, file, byte, or cycle bound fails with a stable
  diagnostic and no partial package publication.

## Assumptions

- Increment 002's sealed plan format is the only planning input boundary. 003 does not reinterpret
  the native catalogue or repair blocked plans.
- Execution mapping is reviewed project configuration with explicit sources; mapping review
  status is not engineering approval and cannot satisfy a human gate.
- The compiler targets a declared Fabro validator profile. The inspected nightly source pin is a
  conformance candidate, not a selected production runtime; native validator evidence is required
  before 003 completion.
- A conservative, explicit graph subset is preferable to using every available runtime feature.
  Registration, run lifecycle, events, checkpoints, resume, and cancellation belong to 006.
- Protected evidence and authenticated decision verification belong to 005. A generated human
  node represents a stop/interaction point only.
- Native process relationships inform provenance and obligation planning but do not define
  execution ordering without a reviewed 003 mapping.
