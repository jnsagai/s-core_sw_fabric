# Feature Specification: Trusted evidence and authenticated human gates

**Feature Branch**: `005-trusted-evidence-and-human-gates`

**Created**: 2026-09-28

**Status**: Implementation in progress; fixture-domain paths verified, production authority pending.

**Input**: Specify trusted-evidence and authenticated human-decision contracts against the exact
candidate, report, source, tool, policy, profile, and process identities established through
Increment 004. Define fail-closed, scoped gate evaluation and staleness without implementing
workflow registration or execution.

## User Scenarios & Testing

### User Story 1 - Establish trusted verification evidence (Priority: P1)

An assurance reviewer receives a verification result that states exactly what was evaluated, which
inputs and process obligations applied, which tool and policy produced the result, and which
protected origin attested it. The reviewer can distinguish an observed trusted result from an
imported result, fixture replay, or agent assertion without relying on a filename, prose claim, or
workflow completion state.

**Why this priority**: No later approval or readiness decision is defensible unless the underlying
verification result is authentic, complete, and bound to the exact engineering subject.

**Independent Test**: Submit one protected observed result, one policy-authorized imported result,
one fixture result, and one agent assertion for the same subject. The first two retain their exact
identity and origin bindings; the latter two remain usable for development context but cannot
satisfy a trusted-evidence predicate.

**Acceptance Scenarios**:

1. **Given** a complete Increment 004 candidate and report closure, **when** a protected collector
   records a verification result, **then** the result binds the exact subject manifest, inputs,
   source and process baselines, tool identity, policy, profile, raw observations, collector origin,
   and collection time. (AC005-01)
2. **Given** imported evidence permitted by an explicit trust policy, **when** it is accepted for
   evaluation, **then** its issuer, authentication, original subject and result identities,
   transformation history, permitted scope, and freshness constraints remain visible. (AC005-02)
3. **Given** fixture, replay, simulated, or agent-authored evidence with valid-looking fields,
   **when** a trusted predicate is evaluated, **then** that evidence is classified accurately and
   cannot satisfy the predicate. (AC005-03)
4. **Given** a mismatched, incomplete, ambiguous, altered, unsupported, or unauthenticated evidence
   record, **when** validation runs, **then** the record is rejected or treated as untrusted with an
   exact reason and no prior valid record is replaced. (AC005-04)

---

### User Story 2 - Record an accountable human decision (Priority: P1)

An authorized reviewer approves, rejects, conditions, or withdraws a decision for a precisely
identified engineering subject and scope. The decision records who acted, under which role and
authority, whether required independence was met, why the decision was made, and how its origin was
authenticated. It cannot be replayed for a different subject or widened beyond its stated scope.

**Why this priority**: Human accountability cannot be inferred from a tool result, agent statement,
workflow interview, or display name. A gate needs an attributable decision with bounded authority.

**Independent Test**: Record an authenticated decision for one exact subject and scope, then try to
reuse it with a changed subject digest, a wider scope, a disallowed role, failed independence, and
an agent-authored lookalike. Only the original authorized use is eligible.

**Acceptance Scenarios**:

1. **Given** an authorized human acting through a trusted decision origin, **when** a decision is
   recorded, **then** it includes the actor identity, role, authority source, independence result,
   exact subject, scope, outcome, rationale, conditions, policy, time, and authentication basis.
   (AC005-05)
2. **Given** a decision whose subject, scope, policy, authority, role, independence, or validity
   interval does not match the gate, **when** the gate is evaluated, **then** the decision cannot
   satisfy that gate and the mismatch is reported. (AC005-06)
3. **Given** a superseded, expired, or withdrawn decision, **when** a current assessment is made,
   **then** its historical fact remains intact while its current applicability is rejected.
   (AC005-07)
4. **Given** an agent-authored file, replayed interview answer, success default, or unverified actor
   string that resembles an approval, **when** it is submitted, **then** it remains an untrusted
   assertion and cannot become a human decision. (AC005-08)

---

### User Story 3 - Evaluate scoped gates fail-closed (Priority: P1)

A process owner evaluates a named gate for an exact scope and complete expected obligation set. The
result distinguishes a measured failure from unavailable authority or evidence, no evaluation,
staleness, and a justified not-applicable disposition. A pass is possible only when every mandatory
predicate is satisfied by evidence and decisions eligible under the selected policy.

**Why this priority**: Converting missing, unknown, stale, timed-out, or empty results into success
would make every downstream assurance claim unsafe.

**Independent Test**: Evaluate the same gate with complete eligible inputs and then replace one
required input at a time with missing, unknown, stale, timeout, untrusted, failed, empty, or
not-applicable data. Only the complete eligible case passes, and each other case yields its defined
non-pass state and required action.

**Acceptance Scenarios**:

1. **Given** a non-empty expected obligation set whose mandatory evidence and human-decision
   predicates are all satisfied for the exact subject and scope, **when** the gate is evaluated,
   **then** the outcome is `pass` with references to every satisfied predicate. (AC005-09)
2. **Given** a measured unmet requirement and complete eligible inputs for all mandatory
   predicates, **when** evaluation runs, **then** the outcome is `fail` and identifies the unmet
   predicate, affected subject, and required action. If another mandatory input is missing, the
   aggregate is `blocked` and retains the measured failure in its predicate results. (AC005-10)
3. **Given** missing, unknown, unavailable, ambiguous, unsupported, unauthenticated, timed-out, or
   untrusted input, **when** evaluation runs, **then** the outcome is `blocked` or `not_evaluated`
   as defined by policy and can never be `pass`. (AC005-11)
4. **Given** a not-applicable claim, **when** no eligible scope-specific applicability or tailoring
   decision exists, **then** the mandatory predicate remains unresolved and the gate does not pass.
   (AC005-12)

---

### User Story 4 - Detect staleness and audit decisions independently (Priority: P2)

A reviewer changes or inspects any bound subject, source, process, tool, profile, policy, evidence,
or decision identity and can see exactly which evidence and gate results are stale for the new
assessment. Earlier evidence and decisions remain immutable historical facts. A portable record
allows an independent reviewer to reproduce the eligibility and gate outcome without Fabro.

**Why this priority**: A result that was valid for one baseline must not silently authorize a later
baseline, while preservation of the old fact is required for auditability.

**Independent Test**: Start from a passing assessment, mutate each bound identity independently,
and confirm the affected evidence or decision becomes ineligible and the gate becomes `stale` or
otherwise non-passing. Restore the exact inputs in another location and reproduce the original
outcome from the portable record without contacting Fabro.

**Acceptance Scenarios**:

1. **Given** a prior evidence or decision record and a changed bound identity, **when** current
   applicability is evaluated, **then** every affected record is marked stale for the new subject
   while the prior record and its original outcome remain unchanged. (AC005-13)
2. **Given** an unknown dependency or incomplete impact boundary, **when** freshness is evaluated,
   **then** review scope expands conservatively or the assessment is blocked rather than assuming
   no impact. (AC005-14)
3. **Given** a complete portable assessment, **when** an independent reviewer verifies it without
   Fabro access, **then** the reviewer can validate identities, origins, predicate eligibility,
   human authority, staleness, limitations, and the resulting scoped gate outcome. (AC005-15)
4. **Given** equivalent normalized inputs in another location or ordering, **when** assessment is
   repeated, **then** the subject identity, eligibility decisions, reasons, and gate outcome are
   identical. (AC005-16)

### Edge Cases

- A trusted result has the expected tool name but a different executable digest, version, policy,
  command profile, environment boundary, or process baseline.
- Evidence is authentic but covers only part of the subject or uses a broader, narrower, older, or
  differently classified scope.
- An imported result is authentic to its issuer but the selected policy does not trust that issuer,
  transformation, result type, or scope.
- A protected collector records a timeout, crash, truncated output, limit breach, or absent result.
- Raw observations pass while required provenance, expected-obligation coverage, or human review is
  incomplete.
- A fixture is copied into a production-shaped path or given the same display name as a trusted
  result.
- An agent drafts a syntactically complete evidence or approval record, copies a human name, or
  gains access to an unprotected output directory.
- One person has several roles, a role changes after the decision, or the selected policy requires
  independence from the author, executor, or collector.
- A valid decision is reused for another revision, sibling component, broader release scope, or a
  gate with a similar title.
- Two decisions conflict, one is withdrawn, or a later decision narrows conditions without erasing
  the earlier record.
- A not-applicable decision is authentic but refers to a different obligation, baseline, or scope.
- The expected obligation set is empty, incomplete, duplicated, or altered after evidence capture.
- A result arrives after the evaluation deadline or after a newer assessment has already started.
- A policy or trust root changes without any engineering artifact changing.
- A baseline change has no known dependency path, or a new unlinked subject lies outside the prior
  impact graph.
- A portable record is relocated, reordered, partially missing, or contains an unknown contract
  version, origin type, decision outcome, gate state, or reason code.
- Evidence, decisions, predicates, reasons, or referenced bytes exceed declared finite limits.

## Requirements

### Functional Requirements

- **005-R01 / FAB-019**: Every operation MUST accept only supported contract versions and MUST
  validate the complete identity and digest closure of the Increment 002 plan and the Increment 004
  candidate, artifact report, source locks, native snapshot, toolchain, templates, metamodel,
  profiles, policies, expected obligations, and requests that it consumes. Missing, conflicting,
  ambiguous, or altered bindings MUST block dependent evaluation. (AC005-01,04,09,13)
- **005-R02 / FAB-019**: A trusted verification result MUST bind a canonical subject manifest to
  the exact inputs, source and process baselines, expected obligations, tool identity and version,
  execution policy and profile, raw observations, outcome, collector identity, trusted origin,
  collection time, and integrity data. Display names, paths, workflow state, or content hashes
  without authenticated origin MUST NOT establish trust. (AC005-01,02,04)
- **005-R03 / FAB-019/FAB-020**: Evidence MUST be classified at least as protected observed,
  policy-authorized imported, fixture or replay, or agent assertion. The classification, original
  origin, transformations, trust-policy decision, eligible scope, and limitations MUST remain
  explicit in machine-checkable and human-readable records. (AC005-01–04,15)
- **005-R04 / FAB-019**: An imported result MAY satisfy a predicate only when an explicit policy
  trusts its authenticated issuer, evidence type, subject binding, transformation chain, freshness,
  and scope. Import MUST NOT silently promote or rewrite the original result. (AC005-02,04)
- **005-R05 / FAB-020**: Fixture, replay, simulated, model-generated, agent-authored, or otherwise
  untrusted evidence MUST NOT satisfy a real approval, acceptance, or readiness predicate,
  regardless of schema validity, content similarity, filename, path, or claimed outcome.
  (AC005-03,04,08,11)
- **005-R06 / FAB-023**: Only an independently protected collector or policy-authorized trusted
  importer MAY establish trusted evidence origin. Engineering-agent and target execution roles
  MUST lack trusted-result and approval authority; agent-writable records MUST remain drafts or
  untrusted assertions until independently verified through an eligible origin. (AC005-01–04,08)
- **005-R07 / FAB-021**: Every human decision MUST record a stable decision identity, authenticated
  actor identity, role, authority source, independence result where required, exact subject
  manifest identity, bounded scope, outcome, rationale, conditions, applicable policy, decision
  time, validity constraints, and trusted origin. Secrets and reusable credentials MUST NOT be
  embedded in the decision. (AC005-05–08)
- **005-R08 / FAB-021/FAB-023**: A human decision MUST apply only to its exact subject, scope,
  policy, authority, role, independence constraints, conditions, and validity interval. A display
  name, repository permission, signed-looking field, Fabro actor string, interview response,
  replay, success default, or agent assertion alone MUST NOT authenticate a decision. (AC005-05–08)
- **005-R09 / FAB-021**: Decision outcomes and lifecycle MUST distinguish approval, rejection,
  conditional approval, withdrawal, expiry, and supersession without erasing or mutating historical
  facts. Conflicts and unmet conditions MUST remain visible and MUST prevent an unqualified pass.
  (AC005-05-07)
- **005-R10 / FAB-022**: Gate evaluation MUST use the explicit outcomes `pass`, `fail`, `blocked`,
  `not_evaluated`, `not_applicable`, and `stale`. Each outcome MUST retain the exact gate, scope,
  subject manifest, evaluator and policy identity, reasons, evidence references, decision
  references, unmet obligations, limitations, evaluation time, and permitted next route.
  (AC005-09–15)
- **005-R11 / FAB-022**: `pass` MUST require a non-empty complete expected obligation set and every
  mandatory deterministic, trusted-evidence, and human-decision predicate defined by the selected
  policy to be satisfied for the exact subject and scope. Success of one predicate, workflow node,
  tool, native build, trace report, or human interview MUST NOT imply the aggregate result.
  (AC005-09–12)
- **005-R12 / FAB-022**: A measured unmet predicate MUST be recorded as `failed`; an aggregate
  with complete eligible mandatory inputs and at least one failed predicate MUST produce `fail`.
  Missing, unknown, unavailable, ambiguous, unsupported, unauthenticated, untrusted, malformed,
  timed-out, or over-limit mandatory input MUST produce `blocked` once evaluation begins, even if
  another predicate failed. `not_evaluated` means no evaluation began. None of these states may
  coerce to success; empty collections and absent responses MUST NOT pass by vacuity. (AC005-10,11)
- **005-R13 / FAB-021/FAB-022**: `not_applicable` MUST require an eligible authenticated
  applicability or tailoring decision bound to the exact obligation, subject, scope, authority,
  rationale, and policy. It MUST remain distinct from pass and MUST NOT silently remove an
  obligation from the expected set. (AC005-12)
- **005-R14 / FAB-019/FAB-022**: A record MUST be stale for a new assessment when any applicable
  subject, input, source, process, tool, profile, policy, trust root, expected obligation, evidence,
  decision, condition, or validity identity changes. Unknown dependencies and incomplete impact
  boundaries MUST expand review or block use. (AC005-13,14)
- **005-R15 / FAB-019/FAB-021**: Staleness, withdrawal, expiry, supersession, and later rejection
  MUST affect current applicability without rewriting the bytes, origin, outcome, or validity facts
  of earlier evidence, decisions, and gate evaluations. (AC005-07,13)
- **005-R16 / FAB-022**: Gate policy MUST distinguish deterministic technical checks, trusted
  evidence predicates, accountable human decisions, engineering acceptance, scoped readiness, and
  release authorization. A result MUST NOT claim a broader subject, lifecycle stage, or authority
  than the exact gate and scope evaluated. (AC005-09,12,15)
- **005-R17 / FAB-019–FAB-023**: Every assessment MUST produce a portable machine-checkable record
  and readable report that resolve all subjects, evidence, decisions, predicate outcomes, reasons,
  limitations, and prior-history references without Fabro access. External bytes MAY be referenced
  only by immutable, independently retrievable identity with absence handled fail-closed.
  (AC005-13–16)
- **005-R18 / FAB-019/FAB-022**: Equivalent normalized inputs MUST produce identical subject
  identities, evidence and decision eligibility, predicate results, reason ordering, and gate
  outcomes across relocation and independent input ordering. Unknown enum values, contract
  versions, or lossy translations MUST fail. (AC005-04,15,16)
- **005-R19 / FAB-019–FAB-023**: All operations MUST enforce declared finite limits for records,
  referenced bytes, subjects, obligations, evidence, decisions, predicates, reasons, nesting, and
  evaluation duration. A failed, interrupted, stale, or over-limit assessment MUST NOT replace a
  prior complete record or publish a partial success. (AC005-04,11,15)
- **005-R20**: Increment 005 MUST NOT register, schedule, execute, resume, or retry a Fabro workflow;
  call a model or provider; mutate a production target; qualify a tool; certify a process; or grant
  module, platform, release, publication, or deployment authorization. These contracts MAY consume
  exact prior identities and express scoped gate outcomes only. (AC005-08,09,15)

### Key Entities

- **Subject manifest**: Canonical, immutable description of the exact candidate, native artifacts,
  reports, sources, process baseline, tools, profiles, policies, expected obligations, scope, and
  referenced content to which evidence and decisions apply; it excludes self-referential approval
  data from its identity.
- **Evidence record**: Immutable verification observation and result with subject, input, tool,
  policy, process, raw-result, time, integrity, and origin bindings plus an explicit evidence class.
- **Trusted origin**: Independently verifiable collector, issuer, or decision channel identity that
  the selected trust policy authorizes for a specific record type and scope.
- **Trust policy**: Reviewed rules defining eligible origins, evidence types, transformations,
  freshness, authority, roles, independence, predicates, limits, and permitted gate transitions.
- **Human decision**: Authenticated, scoped, reasoned act by an identified person under explicit
  authority, with conditions and lifecycle that remain distinct from evidence and workflow state.
- **Expected predicate**: One mandatory or explicitly tailored condition derived independently from
  the applicable plan, obligations, policy, and gate definition before observed results are counted.
- **Gate evaluation**: Deterministic, scoped comparison of the complete expected predicate set with
  eligible evidence and decisions, producing one defined outcome and actionable reasons.
- **Freshness assessment**: Comparison between a record's bound identities and the current subject,
  policy, validity, and conservative impact boundary without changing historical facts.
- **Portable assessment record**: Self-describing machine-checkable and readable closure needed to
  reproduce eligibility and a scoped gate outcome independently of Fabro.

## Success Criteria

### Measurable Outcomes

- **SC005-01**: 100% of accepted protected or policy-authorized imported evidence records retain
  exact subject, input, source, process, obligation, tool, policy, profile, raw-result, time,
  integrity, and authenticated-origin bindings; omission or mutation of any mandatory binding is
  detected before gate use.
- **SC005-02**: Across all acceptance cases, fixture, replay, simulated, model-generated,
  agent-authored, unauthenticated, or merely schema-valid records satisfy zero real trusted-evidence
  or human-approval predicates.
- **SC005-03**: 100% of eligible human decisions expose actor, role, authority, required
  independence, exact subject, scope, outcome, rationale, conditions, policy, time, validity, and
  trusted origin; every wrong-subject, wrong-scope, unauthorized, dependent, expired, withdrawn, or
  replayed decision is rejected for current use.
- **SC005-04**: In a complete gate matrix, only the case with a non-empty complete expected set and
  all mandatory eligible predicates produces `pass`; a measured failure with otherwise complete
  mandatory inputs produces `fail`; and every missing, unknown, malformed, unsupported, untrusted,
  timed-out, empty, or unevaluated case remains non-passing with a stable reason and required action.
- **SC005-05**: Independently changing each bound subject, source, process, tool, profile, policy,
  trust-root, obligation, evidence, decision, condition, or validity identity makes every affected
  current use stale or otherwise ineligible while changing zero historical record facts.
- **SC005-06**: Every accepted not-applicable disposition has an eligible scope-specific decision
  and remains visible in the expected set; deleting or misbinding that decision causes the affected
  gate to become non-passing in 100% of cases.
- **SC005-07**: An independent reviewer can use each complete portable assessment without Fabro to
  reproduce all identity checks, eligibility decisions, predicate outcomes, limitations, and the
  exact scoped gate result; missing referenced content always yields a non-pass state.
- **SC005-08**: Relocation and independent input-order permutations produce byte-identical subject
  identity, eligibility results, reasons, and gate outcome in 100% of deterministic acceptance
  cases, while interrupted or over-limit evaluation publishes no partial success.

## Assumptions

- Increment 002 supplies the sealed applicable instance plan, explicit dispositions, authority
  references, and non-empty expected obligation set used by each gate.
- Increment 004 supplies exact candidate, native snapshot, report, source, toolchain, template,
  metamodel, profile, request, trace, impact, and drift identities. Increment 005 consumes these
  bindings and does not reconstruct them from names or paths.
- Production identity providers, protected collector topology, trusted import issuers, role
  assignments, independence rules, trust roots, retention, and target-specific gate policies remain
  owner-controlled inputs. Their absence blocks real acceptance; fixture policies may demonstrate
  contracts but cannot grant production authority.
- Actual tool qualification, process certification, engineering sufficiency, release criteria, and
  organizational sign-off remain external obligations unless an explicit future scope supplies
  their authoritative policies and eligible decisions.
- Fabro remains the sole future workflow runtime. Increment 006 will bind these portable contracts
  to registration, execution, inspection, resume, and export behavior without making Fabro state an
  evidence or approval authority.
- Increment 005 establishes evidence, decision, freshness, and gate-evaluation behavior only. The
  component safety loop begins in Increment 008, later engineering verification begins in 009-013,
  aggregate readiness begins in 014-017, and publication or deployment remains outside this scope.
