# Proposed runtime contract v1

**Status:** Proposed public commands, implemented for a `candidate_only` runtime profile and
executed against a disposable loopback server built from the pinned candidate; see
[acceptance](../acceptance.md). No production runtime is selected. Explicit same-run checkpoint
resume is not a demonstrated capability of the candidate. Production authentication, 005 trust
authority and engineering acceptance remain unavailable.

## Public commands

```text
score-fabric runtime register --request REQUEST.yaml --out BINDING.json [--json]
score-fabric runtime run      --request REQUEST.yaml --out BINDING.json [--json]
score-fabric runtime status   --request REQUEST.yaml --out SNAPSHOT.json [--json]
score-fabric runtime resume   --request REQUEST.yaml --out DECISION.json [--json]
score-fabric runtime cancel   --request REQUEST.yaml --out CANCEL.json [--json]
score-fabric runtime export   --request REQUEST.yaml --out EXPORT.json [--json]
score-fabric runtime verify   --export EXPORT.json [--json]
```

`register` is version-only and prepares the durable intent binding. `run` registers, creates
once and starts once after each preceding identity is durable. `status` is a native observation,
not an independent run state. `resume` computes a sealed admission and is same-run checkpoint
continuation only, never a new-run retry. `cancel` requests native cancellation and reports
confirmed terminal state only when observed. `export` builds a historical package; `verify` is
offline. There is no public answer, approve, sign, schedule, deploy or publish command.

**Revision from the planning draft:** `status` and `export` take `--request` rather than
`--binding`: a binding alone cannot select the runtime profile, candidate bytes, credential file,
sealed source bytes or ledger, and must not carry them. The binding is read from the ledger named
by the request. `resume` publishes a resume decision rather than a binding.

### Exit semantics

| Exit | Meaning | Publication |
| --- | --- | --- |
| 0 | Requested operation completed and its exact result was observed, status faithfully and completely retrieved (including a waiting gate bound to its exact subject), cancellation confirmed, export complete, or offline export reproduced as complete | New complete output replaces prior output atomically |
| 1 | Reconciliation required, incomplete/conflicting/unknown native view, unbound waiting question, non-admitted or capability-blocked resume, pending or unconfirmed cancellation, incomplete export, or a non-reproduced/incomplete verification | A complete, explicit non-success record is published; no unsafe native action |
| 2 | Malformed, corrupt, unsupported, unsafe, unavailable or infrastructure input prevents reliable operation | Previous output remains byte-identical; bounded diagnostic `{code, pointer, message}` only |

Exit 0 for `status` means faithful status retrieval, not runtime success or engineering pass.
Exit 0 for `verify` means complete historical reproduction, even if the run waited or failed.
All console JSON has bounded fields and exact reason codes; secrets and raw credentials are not
echoed. An interrupted local output replacement leaves the prior complete file unchanged.

## Input and output boundary

A version-1 `runtime_request` (YAML) names exact local files with SHA-256: the runtime intent,
sealed 003 package, compiler profile and candidate runtime profile. The intent must bind the
package transport/semantic digests and the runtime profile transport/self digests. It also names
the candidate executable and API file (rehashed against the profile before any request), an
owner-only regular credential file, a ledger root, a disposable target (`environment_id` must equal
the intent `target_id`), the current baseline vector, selected 005 assessment/trust-context
pairs, effect reconciliation records, an optional exact 005 subject, and protected roots.
Relative paths resolve from the request directory. Symlinked paths are refused; read-only inputs
are digest-bound, so matching hard links are accepted. Outputs cannot alias an input or land
inside a protected root or the ledger root. Unknown fields, versions or enum values are errors.

The credential is read at request time from a file that must be regular, owner-only (`0600`),
owned by the caller and singly linked. No credential is stored in a package, request, runtime
profile, binding, snapshot, decision or export, nor passed on a fabric command line.

The version-1 binding records original 003 package digest, projected Fabro wire digest, native
version ID, native run ID when known, operator intent digest, exact baseline digest, last native
observation identity, finite `resume_attempts`, `creation_state` and `start_state`. A
`reconciliation_required` binding has no asserted run ID or safe automatic retry. Binding bytes
are not an authenticated 005 receipt.

## Native lifecycle mapping observed on the disposable candidate

Candidate source commit `1b4fb15281ebb724426f9e480dce48d0100ff79b`, API file SHA-256
`b760ef95cb3a7e3b50ea4a8336d7241716533fcb7b4ff6f8a7155b0684df21ed`, disposable executable
SHA-256 `09d338fbbe107d6c2e41fe9f3b33531c72b54782a2e17dac7c720b89898a68cf`. The client allowlists exact
routes per capability and refuses any capability absent from `demonstrated_capabilities`
(`…` abbreviates `/api/v1/runs/{id}`):

| Capability | Route | Observed behavior |
| --- | --- | --- |
| `workflow_register` | `POST /api/v1/workflow-versions` | 201 `{workflow_version_id}` equal to SHA-256 of the newline-free canonical wire; repeat and relocated bytes return the same ID |
| `run_create` | `POST /api/v1/runs` | 201 `{id}`; no idempotency key; a lost response leaves one native run the fabric cannot identify |
| `run_start` | `POST /api/v1/runs/{id}/start` | 200 from `submitted`; 409 otherwise |
| `run_inspect` | `GET /api/v1/runs/{id}` | `lifecycle.status.{kind,reason,blocked_reason}`, `pending_control`; summary omits version ID |
| `event_read` | `GET …/events?after=N&limit=L` | numeric `stream_seq` cursor, `meta.has_more`, `event_contract_version` |
| `timeline_read` | `GET …/timeline` | checkpoint `entries` with `stage`, `checkpoint_seq`, `run_commit_sha` |
| `question_read` | `GET …/questions` | `data`, `meta`; a question may remain listed on a terminated run |
| `stage_list` | `GET …/stages` | `data[{id, status}]`, `meta.has_more`; an interrupted in-flight stage stays `running` |
| `output_read` | `GET …/stages/{node}@{n}/logs/output?offset&limit` | `bytes_base64`, `offset`, `next_offset`, `total_bytes`, `eof`, `cas_ref` |
| `blob_read` | `GET …/blobs/{sha256}` | raw bytes whose SHA-256 equals the reference |
| `run_cancel` | `POST …/cancel` | 202 lifecycle body with `pending_control: cancel`; terminal `failed/cancelled` observed later; 409 `Run is not cancellable.` for terminal runs |
| `run_resume` | `POST …/start {"resume": true}` | **Declared, not demonstrated.** Returned 200 and appended `start_requested(resume)`/`runnable` records for terminated, cancelled and succeeded runs; the summary kept its prior terminal status. For terminated runs the worker log recorded `run already finished already — nothing to resume`; a repeat on the same server returned 409 |

Native `/retry`, answer, approve, run listing and `/state` routes are not fabric capabilities.
An unintended probe request confirmed that `/retry` creates a new fork run that repeats effects.
Native `fabro dump` exports events, `graph.fabro`, checkpoints and stage logs but omits the
complete version file map, the definition/spec/graph blobs and any digest manifest; it is not the
fabric's portable record.

Native restart behavior is outside fabric control: a graceful server stop records
`failed/terminated` while a running command process may continue and complete its external effect;
a server crash triggers automatic native continuation of the same run at startup, re-executing the
in-flight step (while the stage list and timeline still show only `@1`). An orphaned worker racing
the continuation produced two `failed/workflow_error` records followed by `succeeded` while the
summary stayed `failed`. These are recorded candidate hazards, not supported recovery paths.

### Package projection

The projected native version uses graph `entrypoint`, exact files and explicit empty
`workflow_dependencies`. The original 003 package is retained. For current single-graph
fixtures, graph entrypoint is `workflow.fabro`, while 003 package entrypoint is
`workflow.toml`; both identities are recorded. 003 validation (declared file records, source map,
IR integrity, native receipt source set) and the distinct native 512-file, 512-KiB/file and 2-MiB
wire limits run before registration, and the returned version ID must equal the wire digest.

### Ambiguous run creation

Before create, the adapter durably marks the local intent `create_in_flight` and sends native
create once. A returned run ID is persisted before start. A lost or malformed response, or a
`create_in_flight` record left by an interrupted process, becomes `reconciliation_required`; no
second create is ever sent automatically. Label searches are not a capability and cannot clear
ambiguity. Start inspects the known run and sends one start only from `submitted`.

## Human waiting and resume admission

A required 003 human gate must have no auto-approve setting or success-producing timeout
default. The native pending question must map uniquely through the sealed 003 source map to the
exact 005 subject and review purpose, on a complete `blocked/human_input_required` view. The
adapter exposes the question and stops with `next_action:
external_authorized_human_decision_required`. A question on a non-waiting run is not bound.

Resume admission returns a sealed `runtime_resume_decision` with `decision` in:

| Decision | Cause |
| --- | --- |
| `refuse_terminal` | `succeeded`, `dead`, `failed/cancelled`, or any failure reason other than `terminated`/`transient_infra` |
| `block_unknown` | unknown or conflicting native view, active source, missing checkpoint, unknown run, attempts exhausted, or admitted but `run_resume` not demonstrated (`RUNTIME_CAPABILITY_UNAVAILABLE`) |
| `block_drift` | changed intent/baseline seal, registered version, source/process/policy/tool/subject digest, or 005 evidence set; a selected 005 assessment that does not replay or is not `pass` |
| `reconciliation_required` | an in-flight stage whose effects are not all `confirmed_absent`, any `unknown` effect, stage state unavailable, or an uncertain prior resume |
| `admit` | none of the above |

Priority is `refuse_terminal`, `block_unknown`, `block_drift`, `reconciliation_required`.
Changed bindings are sorted (`baseline:<field>`, `evidence:<digest>`, `intent`, `baseline`,
`workflow_version`). Only `admit` may reach the native route: the attempt is counted durably first,
and a lost response records `RESUME_UNCERTAIN`. `production_authority` is always `unavailable`.
No historical event or assessment is rewritten.

## Status, cancellation and portable export

Status reads native summary plus ordered event pages, checkpoint timeline, stage list and pending
questions. Overlapping pages deduplicate by native ID and sequence; a gap, stalled page, malformed
stage list or timeline, unknown status, or disagreement between a terminal summary and the last
status-bearing lifecycle record (`NATIVE_STATE_CONFLICT`) is incomplete. Native waiting has no
lifecycle record and is not a conflict. Cancellation is `confirmed` only when `failed/cancelled`
is observed; `pending` and `terminal_other` are non-success.

Export retains the sealed 003 package and compiler profile bytes (`fabric_source`), wire
projection, runtime identity, binding, native summary and status, all events, checkpoints,
stages, questions, every native `blob`/`*_blob` reference's bytes and every stage output
(`runtime_observation`), 005 references and explicit completeness. Offline verification
reprojects the 003 bytes, checks version/run linkage, contiguous event sequence and exact blob
closure (no missing or extra identities), origin labels, runtime commit, and recomputes
completeness; any byte change without reseal fails at the envelope digest. Native answers are
counted as runtime observations; `assurance_decisions` is always 0.

## Stable reason families

`PACKAGE_CLOSURE`, `PACKAGE_DIGEST`, `PACKAGE_FILE_DIGEST`, `PACKAGE_DRIFT`,
`NATIVE_RECEIPT_STALE`, `WIRE_LIMIT_EXCEEDED`, `RUNTIME_CAPABILITY_UNAVAILABLE`,
`RUNTIME_IDENTITY_MISMATCH`, `RUNTIME_AUTH_UNAVAILABLE`, `RUNTIME_RESPONSE`, `RUN_CREATE_UNCERTAIN`,
`RUN_START_UNCERTAIN`, `RUN_ID_UNKNOWN`, `NATIVE_STATE_UNKNOWN`, `NATIVE_STATE_CONFLICT`,
`EVENT_GAP`, `CHECKPOINT_INCOMPLETE`, `QUESTION_INCOMPLETE`, `STAGE_INCOMPLETE`,
`QUESTION_SUBJECT_UNKNOWN`, `HUMAN_GATE_WAITING`, `RESUME_BASELINE_STALE`,
`EVIDENCE_NOT_ELIGIBLE`, `RESUME_SOURCE_TERMINAL`, `RESUME_SOURCE_ACTIVE`, `CANCELLED_TERMINAL`,
`RESUME_ATTEMPTS_EXHAUSTED`, `RESUME_UNCERTAIN`, `RESUME_NOT_ADMITTED`,
`EFFECT_RECONCILIATION_REQUIRED`, `CHECKPOINT_MISSING`, `CANCEL_PENDING`, `CANCEL_NOT_CONFIRMED`,
`BLOB_MISSING`, `STAGE_OUTPUT_LIMIT`, `STAGE_OUTPUT_MALFORMED`, `STAGE_OUTPUT_STALLED`,
`STAGE_OUTPUT_CAS_REF_UNSUPPORTED`, `EXPORT_INCOMPLETE`, `EXPORT_CLOSURE_MISMATCH`, and
`PRODUCTION_AUTHORITY_UNAVAILABLE`. Refinement requires updating schema, contract, tests and
acceptance evidence together.
