# Increment 006 data model

All fabric records below are proposed version-1 envelopes. Exact fields and limits are part of
the [runtime contract](contracts/runtime.md). Native Fabro IDs and states remain native; the
fabric does not substitute its own execution status for them.

## Package projection

| Field | Meaning |
| --- | --- |
| `source_package_digest` | Self-digest of the validated, sealed 003 package |
| `source_package_sha256` | Exact transport bytes used for this request |
| `source_entrypoint` | 003 package entrypoint (`workflow.toml` in current fixtures) |
| `wire_entrypoint` | Fabro graph entrypoint, derived from validated package file map |
| `files` | Exact UTF-8 native file map, closed under all native references |
| `workflow_dependencies` | Explicit complete child-version map; empty in the initial single-graph scope |
| `wire_digest` | Canonical digest of the exact Fabro registration object |
| `validator` | Selected 003 validator identity and native acceptance result |
| `runtime` | Selected Fabro release/source/executable/API identity and demonstrated capabilities |

The source package is immutable. Projection changes require a new wire digest and fresh native
validation. `source_entrypoint` and `wire_entrypoint` intentionally differ; neither may be
silently substituted. The registration object obeys both 003 and Fabro byte/file ceilings.

## Operator intent and native run binding

| Field | Meaning |
| --- | --- |
| `intent_id` | Stable operator-supplied identity within the selected local ledger |
| `intent_digest` | Digest of package/version, selected target, start arguments and baseline |
| `version_id` | Fabro's returned immutable workflow-version ID |
| `run_id` | Fabro's returned run ID, absent until durably known |
| `creation_state` | `prepared`, `create_in_flight`, `run_known`, or `reconciliation_required` |
| `start_state` | `not_requested`, `start_in_flight`, `started`, or `reconciliation_required` |
| `baseline` | Exact source, process, policy, tool, subject and selected 005 evidence identities |
| `native_observation` | Last native response identity/time for reconciliation, never the status authority |

The ledger serializes a local intent so two local callers cannot submit it concurrently. It is
not a global uniqueness service: the inspected Fabro API has no run-create idempotency key.
After an uncertain create response, `run_id` remains unknown and the state becomes
`reconciliation_required`. A matching label in Fabro's list is a candidate for human review,
not proof that the create was unique. No automatic second create is permitted. Once `run_id` is
known, the adapter inspects Fabro before retrying start or resume.

## Native inspection view

- **Run summary**: exact native run/version IDs, native status/reason, labels and observed time.
- **Event cursor**: native event ID and monotonic stream sequence; overlapping pages deduplicate
  by native identity, while missing sequence values make the view incomplete.
- **Checkpoint**: native checkpoint ID and event position, plus a digest of the baseline vector
  against which continuation is admitted.
- **Pending question**: native question ID, stage, prompt/type/options and optional review target,
  plus an independently derived exact 005 subject and gate source-map identity. A missing or
  ambiguous binding blocks automatic answer handling.
- **Completeness**: `complete`, `incomplete`, or `unknown`, with exact missing IDs/pages/bytes.

The native run may be submitted, running, waiting, completed, or failed; cancellation is a native
failure reason rather than a fabricated top-level state. A cancel request accepted but not yet
terminal is still pending. The raw `/state` projection, if inspected, is version-specific
diagnostic context and not the sole basis of a portable record.

## Resume admission and effects

| Field | Meaning |
| --- | --- |
| `run_id` / `checkpoint_id` | Exact same native run and restart point |
| `registered_version_id` | Native version retained at original start |
| `baseline_before` / `baseline_now` | Exact source, process, tool, policy, subject and 005 evidence vectors |
| `changed_bindings` | Deterministically sorted changed or missing identities |
| `effect_ids` | Exact external effect identities and reconciliation outcomes |
| `attempts` / `attempt_limit` | Finite bounded retry count; unknown native attempt count is not zero |
| `decision` | `admit`, `block_drift`, `block_unknown`, or `reconciliation_required` |

Only `admit` may call Fabro's resume operation. A checkpoint alone cannot establish that an
external command's partial side effect was safe to repeat. An unknown effect requires explicit
reconciliation. A native retry that creates a new run is a separate operation and cannot be
reported as resume of the old one.

## Portable run export

The export contains the sealed 003 package bytes, exact wire projection, registered version and
run IDs, selected runtime identity, ordered native events, checkpoint timeline, pending or
answered question metadata, raw command output/blob bytes and any immutable references bound to
those included bytes, origin labels, independent 005 evidence/decision references when present, and a completeness
manifest. Each byte entry records length and SHA-256; the envelope has a canonical digest. An
offline verifier checks closure, identities, event sequence, raw byte hashes and stated limits
without Fabro. It reproduces historical execution facts, not current engineering readiness.

If Fabro is unavailable, an export may be created only as visibly incomplete; it cannot claim
that missing events, blobs or version files were empty. A 005 fixture receipt remains fixture-only,
and a Fabro answer or auto-approval remains runtime context.
