# Feature Specification: APM agent context and profiles

**Feature Branch**: `007-apm-agent-context-and-profiles`

**Created**: 2026-09-30

**Status**: Implemented for disposable use (21/22 tasks; T022 owner review open). Real pinned MCP
discovery, setup, context and change checks and catalogue-based admission are recorded in
[acceptance](acceptance.md). Owner review of the lock and of role, model and budget profiles is
pending; no live model call, provider credential or production role assignment is authorized.

**Input**: Continue from the [006 handoff](../../docs/handoff/006-to-007.md). Specify brief §15
and §20.10 and FAB-027–FAB-030: pinned S-CORE APM/MCP capability discovery, explicit setup,
bounded role context, MCP permissions, provider/model profiles, budget checks and structured
output validation, keeping deterministic checks outside LLM judgment.

## User Scenarios & Testing

### User Story 1 — Discover pinned context capabilities and set them up explicitly (Priority: P1)

An operator selects the reviewed S-CORE context packages. The fabric confirms the exact source
revision and manifests, starts each context server from a disposable copy of that revision,
records what the server actually offers, and invokes one supported read tool. Setup that changes
a workspace is a separate, explicit operator action on a named disposable workspace, and running
it again changes nothing further.

**Why this priority**: Agents cannot be bounded by tools nobody has identified. The upstream
manifests launch unpinned sources and the runtime silently skips a server that fails to start.

**Independent Test**: Discover the pinned packages against a disposable workspace, invoke a
read tool, then change one manifest byte or advertised tool and repeat.

**Acceptance Scenarios**:

1. **Given** the reviewed package lock and a disposable copy at the pinned revision, **when**
   discovery runs, **then** each server's identity, protocol version and exact tool list are
   recorded and a supported read tool returns a real result. (AC007-01)
2. **Given** a changed manifest, an unlisted or changed tool, an unpinned launch reference or a
   failed handshake of a required server, **when** discovery runs, **then** dependent roles are
   blocked and the difference is named; nothing is silently skipped. (AC007-02)
3. **Given** an explicit setup request for a disposable workspace, **when** it runs twice,
   **then** the first run records every workspace change, the second records none, and setup is
   refused for reference repositories and never offered to an engineering role. (AC007-03)
4. **Given** a capability whose dependency or compatibility is unproven, **when** discovered,
   **then** it remains explicitly unsupported or unverified instead of assumed. (AC007-04)

---

### User Story 2 — Assemble a bounded, baseline-bound role context (Priority: P1)

An operator requests context for one role and one task. The context names the repository
baseline, each native source with its revision and digest, the role's allowed tools and paths,
its expected output, prohibited decisions and unresolved assumptions. Local working-memory
observations appear only as labelled hints, marked stale or uncertain when they cannot be tied to
the current baseline.

**Why this priority**: Context without a baseline is not reproducible, and a recalled
observation can masquerade as engineering evidence.

**Independent Test**: Build context for a role in a disposable workspace with one current and
one older recorded observation; change a native source after binding and rebuild.

**Acceptance Scenarios**:

1. **Given** a role and selected native sources, **when** context is built, **then** it
   identifies the repository commit and dirty state and every native source path, revision and
   digest; a missing or changed source blocks the context. (AC007-05)
2. **Given** local observations, **when** included, **then** each is a hint with its origin and
   baseline binding, and any observation not bound to the current baseline is stale or
   uncertain; no observation counts as evidence or a decision. (AC007-06)
3. **Given** private local data or credential-like values, **when** context is built, **then**
   they are excluded unless explicitly selected, and the bundle states what was omitted.
   (AC007-07)

---

### User Story 3 — Constrain what a role may write and which tools it may use (Priority: P1)

A reviewer checks a role profile before use and the role's reported result after use. A profile
that grants approval, collector, answer, run-control, setup or credential capability is refused.
After the role acts, every workspace change must fall inside its write scope and match what it
reported.

**Why this priority**: The runtime's own workflow agents default to broad auto-approval; the
fabric must supply the boundary.

**Independent Test**: Validate a correct role and one with each forbidden grant; after a
disposable role action, change one file outside scope and one undeclared file.

**Acceptance Scenarios**:

1. **Given** a role profile granting any approval, collector, human-answer, run-control, resume,
   setup or credential capability, **when** validated, **then** it is refused with the named
   grant. (AC007-08)
2. **Given** a completed role action, **when** its result is checked, **then** any change
   outside the write scope, any undeclared change, or any declared change that did not happen
   stops the result. (AC007-09)
3. **Given** a valid role, **when** its runtime agent configuration is derived, **then** it
   lists only allowlisted context servers with pinned launch commands, disables run-management
   tools, and is labelled a candidate that has not executed a model. (AC007-10)

---

### User Story 4 — Admit a model call only within capability and budget (Priority: P1)

Before any model call, the fabric compares the role's provider/model profile with the runtime's
captured model catalogue and the remaining budget, and after the call it validates the returned
structured result. Missing capability, disallowed fallback, exhausted budget or malformed output
stops predictably.

**Why this priority**: Aliases, documentation prices and unreported usage are not reliable
bases for spending or for trusting output.

**Independent Test**: Admit a correct profile, then one field at a time use an alias, unknown
model, unsupported reasoning option, oversized output, unallowlisted fallback, exhausted budget
and unknown prior usage; validate one well-formed and several malformed results.

**Acceptance Scenarios**:

1. **Given** a profile naming a provider and model, **when** admission runs, **then** the exact
   offering must exist in the captured catalogue with tool support, the requested reasoning
   option and limits within the offering; otherwise admission stops with the missing
   capability. (AC007-11)
2. **Given** a fallback, **when** requested, **then** it is admitted only when explicitly
   allowlisted with compatible capabilities, the same data destination and a price within the
   remaining budget; nothing switches silently. (AC007-12)
3. **Given** recorded usage and limits, **when** admission runs, **then** a call whose
   conservative estimate exceeds any remaining limit, or whose prior usage is unknown for a
   limited dimension, is refused; unknown usage never counts as zero. (AC007-13)
4. **Given** a role result, **when** validated, **then** a malformed or incomplete result stops
   the role, and any self-reported check result stays an agent assertion. (AC007-14)

### Edge Cases

- A server writes local files on startup before any tool call.
- A server answers with an older protocol version than the runtime's client requests.
- A tool's advertised schema differs from its package manifest.
- The code-graph dependency is absent, so graph queries return a setup hint instead of data.
- A write-scope pattern or a reported path uses `..`, an absolute path or a symbolic link.
- A catalogue row lists reasoning as supported but exposes no selectable reasoning levels.
- Documentation and the live catalogue disagree on model IDs or prices.
- Usage is partly known (tokens known, cost unknown).

## Requirements

### Functional Requirements

- **007-R01 / FAB-027**: Context packages MUST be selected by a reviewed lock naming the source
  revision, license, manifest digests, launch module, expected server identity and protocol,
  and each tool's exact advertised schema digest and classification. (AC007-01/02)
- **007-R02 / FAB-027**: Discovery MUST start servers only from a disposable copy verified
  against the lock, record observed identity/protocol/tools, and invoke only tools classified
  as read-only context. Any drift or failed required handshake MUST block dependent roles.
  (AC007-01/02/04)
- **007-R03 / FAB-027**: Setup MUST be a separate explicit operation on a named disposable
  workspace, MUST refuse reference and protected roots, MUST record before/after workspace
  state, and MUST be idempotent. Setup tools MUST NOT be granted to engineering roles. (AC007-03)
- **007-R04 / FAB-028**: A role context MUST identify the repository baseline, native sources
  with revision and digest, allowed tools, write scope, expected output, prohibited decisions
  and unresolved assumptions. Missing or drifted sources MUST block it. (AC007-05)
- **007-R05 / FAB-028**: Local observations MUST be labelled hints with origin and baseline
  binding; unbound or mismatched observations MUST be stale or uncertain and MUST NOT become
  evidence, decisions or native records. (AC007-06)
- **007-R06 / FAB-028**: Private local data and credential-like values MUST be excluded from a
  context unless explicitly selected, and omissions MUST be listed. (AC007-07)
- **007-R07 / FAB-028**: Role profiles MUST refuse approval, collector, human-answer,
  run-management, resume, setup and credential grants and MUST name explicit tools, paths, data
  destinations, budgets and retry limits. (AC007-08/10)
- **007-R08 / FAB-028**: Role results MUST be checked against the write scope and the actual
  workspace change set; out-of-scope, undeclared or missing changes MUST stop the result.
  (AC007-09)
- **007-R09 / FAB-029**: Model profiles MUST name an exact provider and canonical model ID, the
  reasoning option, output, context, time and cost limits, and MUST be validated against a
  catalogue captured from the selected runtime rather than documentation. (AC007-11)
- **007-R10 / FAB-030**: Fallback MUST require an explicit allowlist entry with compatible
  capabilities, the same data destination and a budget that still admits the call. (AC007-12)
- **007-R11 / FAB-029**: Admission MUST enforce conservative pre-call limits for cost, tokens,
  wall time, retries and correction visits; unknown usage MUST remain unknown and MUST block a
  limited dimension. (AC007-13)
- **007-R12 / FAB-028**: Role results MUST follow a versioned structure (changed paths, native
  IDs, evidence references, unresolved assumptions, proposed next action); malformed results MUST
  stop, and self-reported checks MUST remain agent assertions. (AC007-14)
- **007-R13 / FAB-027–FAB-030**: Commands MUST give stable outcomes for success, explicit
  stop and malformed/unavailable input; errors MUST preserve prior outputs. No command may make
  a model call, grant credentials or record an approval. (AC007-02/08/11/13/14)

### Key Entities

- **Context package lock**: Reviewed revision, manifests, launch modules, expected servers,
  protocol and classified tool schemas.
- **Capability inventory**: What a disposable launch actually exposed and one real read-tool
  result, with drift and unsupported items.
- **Setup record**: Explicit workspace, before/after state and idempotence outcome.
- **Role profile**: Purpose, inputs, output structure, write scope, tools, data destinations,
  prohibited decisions, retry/visit limits, model profile and budget references.
- **Role context bundle**: Baseline, native sources, role instructions, hints and omissions.
- **Model profile and catalogue snapshot**: Exact offering and limits compared with the
  runtime's captured catalogue.
- **Budget ledger and admission**: Prior usage (known or unknown) and the pre-call decision.
- **Role result and check**: Structured agent output compared with the real change set.

## Success Criteria

### Measurable Outcomes

- **SC007-01**: Against the pinned packages, discovery records every advertised tool of each
  selected server and one real read-tool invocation succeeds; each of the drift cases stops
  discovery. (AC007-01/02/04)
- **SC007-02**: A second setup of the same workspace reports zero further changes; setup on a
  protected root makes zero changes. (AC007-03)
- **SC007-03**: A built context names 100% of selected native sources with digest and revision
  and marks every unbound observation stale or uncertain. (AC007-05–07)
- **SC007-04**: Every forbidden grant class is refused, and every out-of-scope, undeclared or
  missing change is detected in disposable checks. (AC007-08–10)
- **SC007-05**: Every capability, fallback, budget and output fault case stops with a named
  reason, and zero model calls or credentials are used. (AC007-11–14)

## Assumptions

- 006 supplies only its demonstrated capability list, runtime schemas and labelled runtime
  observations; no dev token, answer route or resume capability passes to agents.
- The pinned S-CORE packages are inspected at `29aeaa8251bd006d7ed3b0ea64229ea8589ce826`.
  The code-graph dependency is not installed; installing it needs network access and a separate
  decision.
- The model catalogue comes from the pinned disposable runtime with no provider credentials.
  Live model tests would send prompts and are excluded without cost authority.
- Role, model and budget profiles are draft examples for review, not approved production
  assignments. Domain roles such as FMEA/DFA belong to 008 and later increments.
