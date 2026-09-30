# Increment 006 runtime research

**Source baseline:** Read-only inspection of pinned Fabro commit
`1b4fb15281ebb724426f9e480dce48d0100ff79b` in `/home/jefferson/fabro` and the
repository's [003 acceptance](../003-deterministic-workflow-compiler/acceptance.md) and
[005 handoff](../../docs/handoff/005-to-006.md). The pinned executable has been used for
`version` and `validate`; no registration, run, paid model call or human answer is claimed here.
Fabro remains `runtime_candidate_not_selected` in `upstream.lock.yaml`; `toolchain.lock.yaml`
still marks the runtime unresolved. Source behavior below is a design input, not a live capability
claim. Exact source files are named so an implementer can recheck a selected release.
This paragraph records the phase-0 research state; later disposable registration and run probes
are recorded separately in [acceptance](acceptance.md).

## Decision 1 — Project the 003 package into Fabro's version wire form

**Decision:** Preserve the sealed 003 package intact. Verify its closure, then derive and record a
separate Fabro wire object `{entrypoint, files, workflow_dependencies}`. For the current single
graph package, the wire `entrypoint` is `workflow.fabro`, `files` retains the exact 003 native
file map including adjacent `workflow.toml`, and `workflow_dependencies` is empty. Bind the wire
digest and Fabro's returned version ID to the original 003 package identity. Refuse unknown child
workflow or dynamic file dependencies until explicitly supported and closed.

**Rationale:** The 003 package's `entrypoint` is `workflow.toml`; pinned Fabro's
`WorkflowVersion` calls `entrypoint` the graph path. Reusing the 003 value would be the wrong
wire contract. Pinned Fabro bounds 512 files, 512 KiB per file and 2 MiB canonical version bytes;
the 003 package has its own different bounds, so both must be checked. Fabro revalidates graph,
configuration, template and child-workflow closure at registration. Registration is content
addressed and returns the same ID for identical canonical content.

The 003 `validate_package` path checks file records and source-map digests but does not compare
its recorded native `source_set_digest` to the current file map. The 006 projection checks that
binding and validator source identity independently. A resealed changed file with updated file
records/source map but the old native receipt is rejected before registration.
The fabric's canonical JSON helper appends a newline, whereas Fabro's
`serde_json::to_vec(WorkflowVersion)` does not. The 006 wire byte limit and digest omit that
newline; registration still must compare the returned native version ID in a live probe.

**Evidence:** `src/score_sw_fabric/compiler/package.py:139-140,230,244-406`;
`src/score_sw_fabric/compiler/render.py:81-84`; pinned Fabro
`lib/foundation/fabro-types/src/workflow_version.rs:14-17,47-121`,
`lib/components/fabro-workflow-version/src/lib.rs:93-99,163-213,255-353`, and
`docs/public/api-reference/fabro-api.yaml:1091-1153`.

**Alternatives considered:** Change the sealed 003 package entrypoint in place (breaks 003
history); submit only a graph path (drops declared support files); infer child dependencies from
filenames (cannot prove closure).

## Decision 2 — Use native HTTP lifecycle calls with a fail-closed submission ledger

**Decision:** Keep a durable, narrowly scoped operator-intent ledger for correlation only; Fabro
remains authoritative for run state. Use native version registration, run creation and start as
separate operations. Record the returned native run ID before starting. If run creation's response
is lost before its ID is durably known, mark the intent `reconciliation_required` and do not
automatically create another run. Native labels may help a human locate candidates but do not
prove uniqueness. A known run ID can be inspected before retrying start.

**Rationale:** Pinned `POST /workflow-versions` is content addressed. Pinned `POST /runs` has no
caller idempotency key or supplied run ID and allocates a fresh ID server-side. `GET /runs` is
paginated and has no atomic label/intent uniqueness check; client-side label search is advisory.
Therefore exactly-once creation after a lost response cannot be guaranteed on this pin. Native
`start` by a known ID reports conflict for an already requested/running run, allowing status
reconciliation. MCP `fabro_run_create` defaults to start, increasing the ambiguity window.

**Evidence:** Pinned Fabro `docs/public/api-reference/fabro-api.yaml:1091-1214,2163-2199`,
`lib/foundation/fabro-types/src/run_intent.rs:11-43`,
`lib/apps/fabro-server/src/server/handler/runs.rs:501-539,636-703`,
`lib/apps/fabro-server/src/server/handler/lifecycle.rs:50-119`, and
`lib/components/fabro-tool/src/create.rs:33-70,136-145`.

**Alternatives considered:** Retry `POST /runs` on timeout (may duplicate execution); treat an
intent-digest label as a server uniqueness constraint (it is only searchable metadata); use MCP
create for atomicity (it does not provide it). A future selected Fabro version with server-enforced
idempotency or client-chosen run ID could remove this blocker after actual validation.

## Decision 3 — Inspect native events and questions; never infer a 005 decision

**Decision:** Read run summary, ordered event stream, checkpoint timeline and pending questions
from native interfaces. Retain native event IDs and sequence; deduplicate overlapping pages and
report gaps as incomplete. Keep unknown, waiting, failed and cancelled states explicit. Bind a
pending question to an exact 005 review subject through the immutable 003 gate source map; reject
missing or ambiguous binding. Do not submit answers through an agent-held approval credential.

**Rationale:** The pinned API exposes `GET /runs/{id}`, `/events?after=`, `/timeline`, and
`/questions`. The question includes optional `review_target` but no 005 subject digest. Native
Fabro question answers and auto-approve paths have no 005 authenticated reviewer authority. A
cancel request may return immediate or accepted status; the run is terminal only after native
confirmation. Native cancelled is represented as failed with cancellation reason.

**Evidence:** Pinned Fabro API YAML `:2546-2563,3020-3078,3460-3525`; pinned
`lib/apps/fabro-server/src/server/handler/events.rs:127-172`,
`lib/apps/fabro-server/src/server/handler/runs.rs:1326-1365`,
`lib/components/fabro-petri/src/interview.rs:400`, and
`src/score_sw_fabric/compiler/ir.py:168-180`.

**Alternatives considered:** Parse a success string or answer text as approval (untrusted);
reimplement a scheduler from event observations (violates one-runtime principle); treat a 202
cancel response as terminal (native transition not yet confirmed).

## Decision 4 — Resume only after exact baseline and effect reconciliation

**Decision:** Use Fabro's native checkpoint/resume operation on the same run only after comparing
version, source/process/policy/tool identities, exact gate subject and 005 evidence identities.
Treat an absent checkpoint, unknown status, changed binding, or partial external effect as a
stopping condition. A native `/retry` is a new run and cannot be substituted for same-run resume.
Finite attempt limits and effect IDs are explicit in the derived ledger; they do not become a
second run-state authority.

**Rationale:** `start` with `resume=true` requires a checkpoint, but that alone does not prove
external effects were not repeated. The 005 freshness and independent replay checks are needed
for evidence reuse; production eligibility remains blocked by T009 and related owner services.

**Evidence:** Pinned Fabro API YAML `:2163-2199,2383-2394`; pinned lifecycle handler
`:103-119`; [005 assurance contract](../005-trusted-evidence-and-human-gates/contracts/assurance.md)
and [acceptance](../005-trusted-evidence-and-human-gates/acceptance.md).

**Alternatives considered:** Assume native checkpoint alone authenticates evidence; restart with
`/retry` while reporting the same run; replay an old 005 fixture receipt into production.

**Implementation observation (2026-09-30):** On the disposable candidate, explicit
`start` with `resume=true` returned 200 for terminated, cancelled and succeeded runs but did not
continue them (terminated: worker `run already finished already — nothing to resume`). Native
startup continuation after a server crash did continue the same run but re-executed the in-flight
command, and an orphaned worker race produced contradictory terminal records. `run_resume`
therefore stays undemonstrated; see [acceptance](acceptance.md).

## Decision 5 — Export a closed portable run package

**Decision:** Retain the sealed 003 package and the exact projected wire version independently
of Fabro. Export native run summary, ordered event pages, checkpoint timeline, pending questions,
raw output/blob bytes, native IDs, source and origin labels, completeness marker, and hashes into
a bounded package. Offline verification checks every included byte, sequence and closure. A Fabro
command result remains runtime context unless a separate eligible 005 receipt exists.

**Rationale:** The pinned API has no `GET` workflow-version route. Native dump can export a run's
state/events/logs/blobs, but does not include the complete original version package; artifact ZIP
provides latest paths, not a complete historical record. Native `/state` is explicitly unstable,
so a versioned fabric export must not treat that projection as its sole lasting contract.

**Evidence:** Pinned API YAML `:2672-2677,3020-3145,3613-3625`; pinned
`lib/apps/fabro-cli/src/commands/dump.rs:20-113`,
`lib/components/fabro-dump/src/lib.rs:58-65,147-171`; [005 contract](../005-trusted-evidence-and-human-gates/contracts/assurance.md).

**Alternatives considered:** Store only a Fabro URL (not portable); use latest-artifact ZIP as
complete event history (omits revisions and version closure); mark missing blobs as empty success.

## Capability and authority boundary for implementation

The selected runtime is still unresolved in `toolchain.lock.yaml`. Before an executable adapter
or quickstart claim, implementation must choose and verify a compatible Fabro version, API
authentication, file-size limits, version registration, run creation/start, event pagination,
question waiting, checkpoint/resume, cancellation and export in a disposable environment.
Management endpoints require native user/worker credentials; those credentials must not grant
005 collector signing or human approval authority. A command-only disposable run can exercise
runtime behavior without a paid model call. A production pass remains unavailable until the
005 independent trust root and owner-controlled services are established.
