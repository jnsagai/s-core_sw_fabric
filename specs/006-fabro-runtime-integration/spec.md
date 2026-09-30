# Feature Specification: Fabro runtime integration

**Feature Branch**: `006-fabro-runtime-integration`

**Created**: 2026-09-30

**Status**: Implementation in progress (39/40 tasks). Disposable candidate execution of the
public runtime commands is recorded in acceptance. Same-run native checkpoint continuation is not
demonstrated on the candidate (T025 open); production runtime selection, 005 production authority
and engineering acceptance remain pending.

**Input**: Continue from the 005 handoff. Specify brief §20.9 and FAB-024–FAB-026:
register a complete 003 workflow version, run and inspect it through Fabro, handle a human
waiting point, resume safely, and export portable run evidence without promoting runtime
success to engineering acceptance.

## User Scenarios & Testing

### User Story 1 — Register and start a closed workflow (Priority: P1)

An operator selects a validated, sealed 003 workflow package. The integration checks every
referenced local file, registers an immutable workflow version, starts a run through Fabro, and
returns Fabro's version and run IDs. A repeated submission cannot create a duplicate merely
because the first response was lost; unresolved native identity stops automatic retries.

**Why this priority**: Missing support files or duplicate submissions make subsequent execution
and evidence ambiguous.

**Independent Test**: Register and start a small command-only workflow in a disposable Fabro
environment; repeat the request, then change or remove one referenced file.

**Acceptance Scenarios**:

1. **Given** a sealed package with complete file closure, **when** submitted, **then** the
   registered version identifies the exact package and the run resolves to that version. (AC006-01)
2. **Given** the same package and submission intent, **when** retried after an uncertain response,
   **then** the original run is reused if its native ID can be established; otherwise submission
   remains unresolved and no second run starts automatically. (AC006-02)
3. **Given** a missing, changed, unsafe, or undeclared dependency, **when** registration is
   requested, **then** no run starts and existing records remain unchanged. (AC006-03)

---

### User Story 2 — Inspect a run and stop at a human gate (Priority: P1)

An operator reads Fabro's status, events, pending questions and checkpoints through one stable
view. A completed command followed by required human review leaves the run waiting with its exact
subject visible. The integration does not answer on the person's behalf.

**Why this priority**: Waiting is an intentional state, distinct from success, failure and
cancellation.

**Independent Test**: Run a graph with a command and required human gate; inspect the native
events and question and confirm zero automatic answers.

**Acceptance Scenarios**:

1. **Given** a pending gate, **when** status is requested, **then** the native waiting state,
   version/run IDs, event position, question, exact review subject and next action are shown.
   (AC006-04)
2. **Given** failure, timeout, cancellation or uncertain native status, **when** inspected,
   **then** each stays distinct from completion with its event history. (AC006-05)
3. **Given** a waiting gate, **when** unattended work ends, **then** it stops and exposes a
   handoff without fabricating a 005 human decision. (AC006-06)

---

### User Story 3 — Resume without duplicated effects (Priority: P1)

After interruption or an authorized human response, an operator resumes the same Fabro run.
Before continuation, the integration checks the registered version, source and policy baseline,
gate subject, and evidence. Compatible work resumes from the native checkpoint; drifted or
uncertain work stops for review. Retries are finite and reconcile partial effects.

**Why this priority**: Filename matches and prior success text cannot prove current eligibility
or prevent duplicate effects.

**Independent Test**: Interrupt a disposable run after one recorded effect, resume unchanged,
then change one binding and attempt resume again; inspect effect counts and historical bytes.

**Acceptance Scenarios**:

1. **Given** an unchanged checkpoint and bindings, **when** resumed, **then** the same run
   continues and each completed effect occurs once. (AC006-07)
2. **Given** changed workflow, source, policy, subject, tool or 005 evidence identity, **when**
   resume is requested, **then** affected continuation is blocked and history is retained.
   (AC006-08)
3. **Given** an uncertain response after an effect, **when** retried, **then** native state and
   effect identity are reconciled before another attempt under a finite limit. (AC006-09)
4. **Given** a confirmed cancellation, **when** status or export is requested, **then** it
   remains cancelled until a separately authorized new action. (AC006-10)

---

### User Story 4 — Export an independently readable run record (Priority: P2)

A reviewer exports run/version linkage, package files, events, checkpoints, command observations
and unresolved questions. Every item identifies its Fabro origin and whether any separate 005
authenticated origin exists. Historical execution remains understandable without Fabro.

**Why this priority**: Fabro owns run state, while S-CORE artifacts and acceptance must be
independently understandable.

**Independent Test**: Export completed and waiting runs, disconnect Fabro, inspect both packages,
then remove or change a required byte.

**Acceptance Scenarios**:

1. **Given** a run with events and raw output, **when** exported, **then** each item retains its
   native identity, exact bytes or immutable reference, digest, origin and completeness. (AC006-11)
2. **Given** only Fabro output or a claimed reviewer answer, **when** exported, **then** it is
   runtime context until an independently eligible 005 receipt or decision exists. (AC006-12)
3. **Given** a copied export, **when** reviewed without Fabro, **then** complete historical data
   is reproducible and missing or changed required bytes fail closed. (AC006-13)

### Edge Cases

- A registration or start response is lost after Fabro accepted the request.
- A package path is a symlink, changes between validation and submission, or escapes its root.
- Status is unknown; event pages overlap or arrive out of order; a checkpoint is missing.
- A human question lacks an exact subject or was already answered by another actor.
- A step partially writes output before crashing; a retry encounters that effect.
- Source, policy, gate subject, receipt or time binding changes while waiting.
- Fabro is unavailable during export, or the selected release lacks a needed lifecycle operation.

## Requirements

### Functional Requirements

- **006-R01 / FAB-024**: Fabro MUST remain the sole authority for registration, execution,
  scheduling, events, checkpoints, questions, cancellation and run state. The fabric MAY keep
  derived reconciliation data but MUST NOT create a competing scheduler or status authority.
  (AC006-01/04/05/07/10)
- **006-R02 / FAB-025**: Before registration, the integration MUST verify the sealed 003 package,
  selected validator/runtime compatibility, all local references, exact bytes and digests, and
  closure of prompts, scripts and configuration. Unknown or unsafe references MUST be refused.
  (AC006-01/03)
- **006-R03 / FAB-025**: A registered version MUST identify the complete package immutably and
  retain Fabro's version ID separately from the package digest. (AC006-01/02/11)
- **006-R04 / FAB-024/FAB-026**: Submission MUST bind stable operator intent and reconcile
  uncertain native responses before retry. If the original native run cannot be identified,
  automatic retry MUST stop rather than risk a duplicate run or effect. (AC006-02/09)
- **006-R05 / FAB-024**: Inspection MUST show native status, event and checkpoint identity,
  pending question, and explicit unknown or incomplete states. Waiting, failure, cancellation
  and successful runtime termination MUST remain distinct. (AC006-04/05/06)
- **006-R06 / FAB-024**: A required human gate MUST stop unattended work, retain its exact
  review subject, and route a question to an authorized external channel. A Fabro answer or
  agent text MUST NOT become a 005 approval. (AC006-04/06/12)
- **006-R07 / FAB-026**: Resume MUST compare registered version, source/process/policy/tool
  baseline, gate subject and 005 evidence identities with the checkpoint. Missing or changed
  mandatory bindings MUST block affected continuation without editing history. (AC006-07/08)
- **006-R08 / FAB-026**: Retry and resume MUST use native checkpoints, finite attempt limits,
  and reconciliation of partial outputs and external effect IDs. Confirmed cancellation MUST
  stay terminal until separately authorized. (AC006-07/09/10)
- **006-R09 / FAB-024/FAB-026**: Export MUST retain immutable version/run linkage, native
  events/checkpoints, raw output bytes or immutable references whose bytes are included in the
  portable closure, pending gates, origin, completeness and limitations. Missing required data
  MUST not appear complete. (AC006-11/13)
- **006-R10 / FAB-024**: Fabro success MUST remain separate from 005 evidence eligibility,
  human decisions and scoped engineering readiness in status and export. (AC006-04/06/12)
- **006-R11 / FAB-024/FAB-026**: Operations MUST have bounded diagnostics and stable outcomes
  for success, waiting/non-success and malformed/unavailable requests; errors or interruption
  MUST preserve prior complete local outputs. (AC006-03/05/09/13)
- **006-R12 / FAB-024**: The selected compatible Fabro version and supported lifecycle
  operations MUST be demonstrated before live use. An unproven operation remains unavailable.
  (AC006-01/07)

### Key Entities

- **Runtime package closure**: Sealed 003 workflow and every referenced file, digest, source
  map, validator baseline and runtime compatibility identity.
- **Registered workflow version**: Fabro's immutable version ID bound to one package.
- **Run binding**: Native run ID, version, submission intent, source/policy baseline and
  reconciliation status.
- **Native event/checkpoint**: Fabro execution record and restart point with native identity.
- **Pending human gate**: Native question linked to an exact 005 subject and external decision
  requirement, without an agent-held approval credential.
- **Portable run export**: Historical version/run links, events, outputs, questions, origins and
  limitations readable without Fabro.

## Success Criteria

### Measurable Outcomes

- **SC006-01**: One validated small workflow registers and starts in a compatible disposable
  Fabro environment; all support files and both native IDs are recoverable. (AC006-01)
- **SC006-02**: Repeating a submission after a simulated lost response yields no duplicate
  version or run: the original ID is recovered where possible, and ambiguous creation stays
  pending. Changing or removing any declared file yields zero new runs. (AC006-02/03)
- **SC006-03**: A real command-plus-human-gate run reaches a visible waiting state with one
  pending question and zero automatically submitted approvals. (AC006-04/06)
- **SC006-04**: A compatible interrupted run resumes with each effect counted once; each
  one-binding drift case blocks continuation and preserves earlier events. (AC006-07–09)
- **SC006-05**: Completed, waiting, failed and cancelled runs export distinct outcomes. A
  complete copied export remains readable without Fabro; missing required bytes are detected.
  (AC006-10–13)
- **SC006-06**: No runtime success, Fabro answer or fixture-only 005 receipt is labelled a
  production engineering pass. (AC006-06/12)

## Assumptions

- Increment 003 supplies a sealed, validated package. Increment 005 supplies a fixture-domain
  assurance contract and portable verifier; T009 production trust root and owner-controlled
  identity, collector, roles, policy and time remain open.
- A compatible Fabro lifecycle interface must be demonstrated against the selected pin.
  Validation-only compatibility does not prove registration or resume support.
- Initial live testing uses a disposable local runtime and a command-only graph with no paid
  model call, publishing, deployment or external effect. A genuine human-gate flow requires an
  authorized response channel; an agent-created approval cannot substitute for it.
- Native S-CORE artifacts and 005 assurance history remain authoritative outside Fabro.
  Module/platform readiness and release decisions belong to later increments.
