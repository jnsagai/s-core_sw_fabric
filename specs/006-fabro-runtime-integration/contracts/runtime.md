# Proposed runtime contract v1

**Status:** Proposed public commands; the `score-fabric runtime` commands below do not yet exist.
The pinned candidate was exercised on a disposable loopback server for registration, command
execution, status/events/timeline/questions, waiting human input and pre-start cancellation;
see [acceptance](../acceptance.md). No production runtime is selected. Checkpoint continuation,
complete export and production authentication/capability evidence remain open.

## Proposed public commands

```text
score-fabric runtime register --request REQUEST.yaml --out BINDING.json [--json]
score-fabric runtime run --request REQUEST.yaml --out BINDING.json [--json]
score-fabric runtime status --binding BINDING.json --out SNAPSHOT.json [--json]
score-fabric runtime resume --request REQUEST.yaml --out BINDING.json [--json]
score-fabric runtime cancel --request REQUEST.yaml --out SNAPSHOT.json [--json]
score-fabric runtime export --binding BINDING.json --out EXPORT.json [--json]
score-fabric runtime verify --export EXPORT.json [--json]
```

`register` is version-only; `run` creates and starts only after the version binding is durable.
`status` is a native observation, not an independent run state. `resume` is same-run checkpoint
continuation, never a new-run retry. `cancel` requests native cancellation and reports confirmed
terminal state only when observed. `export` builds a historical package; `verify` is offline.
There is no public answer, approve, sign, schedule, deploy or publish command in this increment.

### Exit semantics

| Exit | Meaning | Publication |
| --- | --- | --- |
| 0 | Requested operation completed and its exact result was observed, status faithfully retrieved, or offline export faithfully reproduced | New complete output may replace prior output atomically |
| 1 | An effectful operation reached native waiting/non-success, blocked drift, or reconciliation-required outcome | A complete, explicit non-success observation may be published; no new unsafe native action |
| 2 | Malformed, corrupt, unsupported, unsafe, unavailable or infrastructure input prevents reliable operation | Previous complete output remains byte-identical; bounded diagnostic only |

Exit 0 for `status` means faithful status retrieval, not runtime success or engineering pass.
Exit 0 for `verify` means historical record reproduction, even if the run waited or failed.
All console JSON has bounded fields and exact reason codes; secrets and raw credentials are not
echoed. An interrupted local output replacement leaves the prior complete file unchanged.

## Input and output boundary

Each request selects exact version-1 records: sealed 003 package path plus transport and semantic
digests; selected runtime profile and demonstrated capability record; operator intent ID and
start arguments; source/process/policy/tool/005 subject/evidence baseline; protected input and
output roots; finite timeout/page/byte/attempt limits. Unknown fields, versions or enum values
are errors. Paths are request-relative only where explicitly declared, normalized and confined;
symlinks, aliases, traversal, direct output/input overlap and undeclared files fail before write.
The current candidate client accepts a temporary dev token from an injected protected-file
provider for a disposable loopback server. No credential is stored in a package, request,
runtime profile, export or agent-readable command line. Production credential provisioning is
outside the current client.

The version-1 binding records original 003 package digest, projected Fabro wire digest, native
version ID, native run ID when known, operator intent digest, exact baseline, native observation
identity, and `creation_state`. A `reconciliation_required` binding has no asserted run ID or
safe automatic retry. Binding bytes are not an authenticated 005 receipt.

## Native lifecycle mapping to validate on the selected runtime

The inspected candidate exposes `POST /api/v1/workflow-versions`, `POST /api/v1/runs`,
`POST /api/v1/runs/{id}/start`, `GET /api/v1/runs/{id}`, event/timeline/question reads,
`POST /api/v1/runs/{id}/cancel`, and native checkpoint resume through start with `resume=true`.
These routes are source-derived candidate interfaces, not verified installation commands. The
adapter uses a capability probe and refuses operations absent on the selected runtime. The
disposable probe confirmed that version registration returns HTTP 201 with
`workflow_version_id`, run creation returns HTTP 201 with `id`, start returns HTTP 200, and
summary uses nested `lifecycle.status.kind`/`reason`. The summary omits the version ID; the
first `run.created` platform event contains it. Events use numeric `stream_seq` and exclusive
`after` cursor, with `meta.has_more`; timeline returns `entries`; questions return `data` and
`meta`. Command output uses `{node_id}@{visit}` stage IDs, `bytes_base64`, offsets and `eof`.
The `run_resume` route remains unproven for a live checkpoint; a completed run accepted
`resume=true` with HTTP 200 and added a resume start request plus runnable event while its
summary remained completed. The adapter must refuse terminal-source resume before calling this
route; a 200 response alone cannot prove continuation or effect deduplication. Pre-start
cancellation returned `failed` with reason `cancelled`. A human question
had a 60-second timeout; the unattended run subsequently became `failed/workflow_error`.

The projected native version uses graph `entrypoint`, exact files and explicit
`workflow_dependencies`. The original 003 package is retained. For current single-graph
fixtures, graph entrypoint is `workflow.fabro`, while 003 package entrypoint is
`workflow.toml`; both identities are recorded. The adapter validates the distinct native wire
limits and server acceptance before returning a version binding.

### Ambiguous run creation

Before create, the adapter durably marks the local intent `create_in_flight`. It sends native
create once. If the response provides a run ID, it persists that ID before start. If the response
is lost or malformed after send, it marks `reconciliation_required` and never automatically sends
another create. A paginated native label search may supply candidates for human reconciliation,
but a label is neither a uniqueness constraint nor authorization to resume. A selected native
API with a proven server-side idempotency key could support a stronger future contract.

Native start with a known run ID is inspected before retry; an already requested/running conflict
does not authorize a second run. Native `/retry` creates another run and is outside same-run
resume. Attempts, side-effect IDs and partial outputs are reconciled before an effectful retry.

## Human waiting and resume admission

A required 003 human gate must have no auto-approve setting or success-producing timeout
default. The native pending question must map uniquely through the sealed 003 source map to the
exact 005 subject and review purpose. Fabro's optional `review_target` or answer text alone is
insufficient. The adapter exposes the pending question and stops. Answer submission requires a
separate authorized human channel and independently authenticated 005 decision; neither is
implemented as an agent operation here.

Resume compares exact registered version, source/process/tool/policy, gate subject and relevant
005 evidence/decision identities with the checkpoint baseline. It also checks 005 freshness and
portable replay where evidence is selected. Missing production trust root/time still blocks
production acceptance even when native resume is operational. Unknown or changed bindings yield
`block_unknown` or `block_drift` with sorted changed IDs. No historical event or assessment is
rewritten.

## Status, cancellation and portable export

Status reads native summary plus ordered event pages, checkpoint timeline and pending questions.
Overlapping pages deduplicate by native ID and sequence; a gap, missing page, unknown status or
truncated output is reported incomplete. Native cancellation may be merely requested; do not
label it terminal until the native failure/cancellation reason is observed. The adapter never
invents a top-level `cancelled` state if the native state is `failed` with cancellation reason.

Export retains the sealed 003 package, wire projection, native IDs, events, checkpoint/question
records, raw outputs and blob bytes with any immutable references bound to included bytes, source/origin labels and explicit
completeness. It does not use an unstable native `/state` projection or latest-artifact ZIP as
the sole history. Offline verification recomputes all digests, closure and ordered event identity
without contacting Fabro. A partial export can be kept for diagnosis only with an explicit
`incomplete` marker and cannot reproduce as complete. Fabro output is `runtime_observation`;
only separately eligible 005 receipts/decisions can establish assurance eligibility.

## Stable reason families

`PACKAGE_CLOSURE_MISSING`, `PACKAGE_DRIFT`, `WIRE_LIMIT_EXCEEDED`,
`RUNTIME_CAPABILITY_UNAVAILABLE`, `RUNTIME_IDENTITY_MISMATCH`, `RUN_CREATE_UNCERTAIN`,
`RUN_ID_UNKNOWN`, `NATIVE_STATE_UNKNOWN`, `EVENT_GAP`, `QUESTION_SUBJECT_UNKNOWN`,
`HUMAN_GATE_WAITING`, `RESUME_BASELINE_STALE`, `EFFECT_RECONCILIATION_REQUIRED`,
`CHECKPOINT_MISSING`, `CANCEL_PENDING`, `EXPORT_INCOMPLETE`, `EXPORT_CLOSURE_MISMATCH`,
and `PRODUCTION_AUTHORITY_UNAVAILABLE` are proposed bounded codes. The implementation may
refine the enum only by updating schema, contract, tests and acceptance evidence together.
