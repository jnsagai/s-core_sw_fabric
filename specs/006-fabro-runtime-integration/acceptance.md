# Increment 006 acceptance evidence

**Status:** Implementation in progress; 15/40 tasks complete. A matching disposable candidate
server has demonstrated registration, command execution, read routes, a waiting human question,
and pre-start cancellation. Checkpoint resume, complete portable export, production runtime
selection and engineering acceptance remain unestablished. No question was answered and no
paid model call was made.

## Candidate source and executable inspection — 2026-09-30

| Check | Observed result |
| --- | --- |
| `git -C /home/jefferson/fabro rev-parse HEAD` | `1b4fb15281ebb724426f9e480dce48d0100ff79b` |
| `git -C /home/jefferson/fabro status --short` | Empty; reference checkout unchanged |
| Pinned Fabro API file SHA-256 | `b760ef95cb3a7e3b50ea4a8336d7241716533fcb7b4ff6f8a7155b0684df21ed` |
| Disposable debug executable SHA-256 | `09d338fbbe107d6c2e41fe9f3b33531c72b54782a2e17dac7c720b89898a68cf` |
| Disposable executable `--json version` client | `0.362.0-nightly.0`, abbreviated Git SHA `1b4fb15`, Linux x86_64 debug build |
| `--json version` discovered local server | `http://127.0.0.1:32276`, Git SHA `a192bce`, release build: **different source identity**; no 006 operation was sent to it |

The candidate OpenAPI and source expose content-addressed workflow-version registration,
run create/start, summary/events/timeline/questions, checkpoint resume, cancellation and dump
interfaces as detailed in [research](research.md). Source inspection is not a live probe.
The local server observed by `version` is not the pinned client commit, so no 006 operation was
sent to it. A separate disposable server below used the pinned executable and API file. This
does not select a production runtime.

The new version-1 intent, binding and export schemas parse as JSON. The foundation checker
passes, Ruff passes for the new runtime package, and the sealed 003 package SHA-256 remains
`9605abac81940cdde5e54e8b367ac47cff8a792a85a43e1fd2c361ccdf1ce95b`.
The 005 passing assessment SHA-256 remains
`d133c516c2d6c5f29118391f6b0e09ed863706386cee5696781abbc958374ccf`.
The version-1 runtime model contract has 50 passing tests for required fields, bounded limits,
corrupt blob bytes, output aliases, secret-safe diagnostics and interrupted atomic replacement.
Ruff and mypy pass for the new source and tests. These are local record checks, not native
Fabro lifecycle evidence.
The sealed 003 package now projects to Fabro's graph entrypoint while retaining its original
`workflow.toml` entrypoint and file bytes. The projection checks 003 closure, the native 512-file,
512-KiB/file and 2-MiB canonical wire ceilings, and pinned native path limits. Combined runtime
model/projection contract tests passed 68 cases before the live probe below. An additional
regression reseals changed 003 graph bytes and updates file records/source-map hashes while
retaining the old native-validation receipt. The existing 003 package validator accepts that
self-consistent reseal, but the 006 projection rejects it as `NATIVE_RECEIPT_STALE`. This does
not authenticate the original package's author or replace live native validation at registration.
The local intent ledger records `create_in_flight` durably before a native create can be sent.
After an uncertain response it records `reconciliation_required` and refuses a second automatic
create. Same-intent repetition, changed-intent refusal, a known native run ID, and two concurrent
local callers are covered by contract tests. Combined runtime contracts pass 74 cases; no
native create request was sent.
The candidate-only HTTP client checks full source commit, local executable/API byte hashes,
loopback origin, sorted demonstrated capability names, exact operation routes, timeouts and byte
ceilings; it disables proxy use and redirects. Mock-transport tests show unproven operations and
wrong routes never send a request. Initial runtime contracts passed 86 cases. The capability
list remains candidate-only. The executable has link count 2; read-only identity verification
accepts matching hardlinked bytes and rejects symlinks. A contract regression covers both.

## Disposable native probe — 2026-09-30

The disposable server ran the pinned executable from `/tmp/score-fabro-build-kDgEvg` in
`/tmp/score-fabro-006-uHPItJ`, bound to `127.0.0.1:43991`, with separate storage and a
temporary dev token supplied by a protected file. `/proc/3349971/exe` resolved to the
digest-checked executable; the reference checkout was not written. The API file digest is the
one above. The candidate profile is `candidate_only` and permits only demonstrated loopback
routes. The real `FabroClient`, with an injected disposable credential, reproduced version
registration and summary/event/timeline/question reads. The native integration test, explicitly
selected by five `SCORE_FABRO_*` environment variables, passed in **1.18 s** and otherwise
skips because it has no selected disposable server. No production credential is in a request,
profile or export.

| Native operation | Observed response |
| --- | --- |
| `POST /api/v1/workflow-versions` on sealed 003 linear package | 201 `{"workflow_version_id":"47cbdbad41371f725f650c461d926c65f58b22bcaffcdfe40daca4f6aef4f6ff"}`; exactly the 956-byte projected wire SHA-256; repeat returned the same ID |
| `POST /api/v1/runs` with local target, `auto_approve:false`, no model | 201 run `01M3REB2YNGYFKYHA8NKGHNQ66`, initially `lifecycle.status.kind=submitted`; no create idempotency key was supplied or found |
| `POST /api/v1/runs/{id}/start` | 200 `runnable`; later GET reported `succeeded/completed`; repeat start was 409 |
| Summary, events, timeline, questions | GET 200; summary `lifecycle.status={kind:succeeded,reason:completed}`, `usage.tokens` all zero; 69 events with `stream_seq` 1–69; `events.meta.has_more=false`; four checkpoint timeline entries; zero questions |
| Event pagination | `after=0&limit=10` returned sequences 1–10; `after=10&limit=10` returned 11–20, both with `has_more=true` |
| Stage command output | GET for `node_7d7113bb6893c9053161eed9@1` returned 200 with `offset=next_offset=total_bytes=0`, `eof=true`, `bytes_base64=""`; native stage IDs include `@visit`. The actual bounded `FabroClient` output route repeated this response after file identity verification. |
| Native content-addressed blobs | The bounded `FabroClient` GET `/api/v1/runs/{id}/blobs/{sha256}` returned HTTP 200 `application/octet-stream`; `definition_blob` was 1,896 bytes and `spec_blob` was 3,284 bytes, each SHA-256 equal to its `run.created` reference. A route contract rejects uppercase, traversal and extra path components before transport. Complete blob-reference discovery/export remains open. |
| Submitted-run cancellation | Run `01M3REXBVAEK39PD62EJKD1617` returned 200 from cancel; subsequent GET reported `failed` with reason `cancelled`, not a distinct `cancelled` kind |
| Shared human-gate package | Sealed package `e3f24bb4d7f5b33fca7e6a297f0a4920449f546e869151358eec0c9b12b70759` registered as version `ac27a309ea123e4396d88cb9ecd87c62dfc43ac2b6429c23c3c4c49904fc84ef`; run `01M3RF4BKDZKTXPM2HTA7S1AE0` reached `blocked/human_input_required`, with one question `node_b3a60d7744d0e9fc356f57e8#7` at stage `node_b3a60d7744d0e9fc356f57e8@1`; no answer was sent and model tokens were zero |
| Human question timeout | Native question had `timeout_seconds=60.0`; it later disappeared and run became `failed/workflow_error` with 175 event sequences. The observed waiting handoff was transient; no answer or 005 decision is inferred. |
| `start` with `resume=true` on completed command run | 200 with the same completed summary; two new platform events at `stream_seq` 70–71 recorded `start_requested/source=resume` and `runnable/source=start_requested` after the original 69-event completion. No repeated command effect was measured. This is not evidence of safe checkpoint continuation or effect deduplication; the fabric must refuse terminal-source resume before calling it. |

The API's event cursor is numeric `stream_seq` (`after=0` for the first page). Stage output
uses `{node_id}@{visit}` and base64 bytes. The client route allowlist was corrected to those
observed forms. Native run summary does not include the workflow-version ID; the `run.created`
platform event does. Full source/version/event/output closure is still needed for an export.
T007 remains open because same-run checkpoint resume, blob closure and full export have not
been demonstrated. Public commands, resume admission and portable export remain scoped work
in [tasks](tasks.md).

The guarded client now checks the projected wire digest before registration and requires the
native content-addressed ID to match. The local ledger persists the returned version binding
before create, marks `create_in_flight` before sending create, and persists the native run ID
before start. A lost or malformed create response becomes `reconciliation_required`; a repeated
call sends no second POST. Start inspects the known run and sends one native start only from
`submitted`; conflicting or uncertain status stops. The disposable native integration test
exercised these guarded methods and passed again in **1.27 s**. Contract tests include a lost
response after a simulated accepted create, exact one-POST count, known-run inspection and
start conflict. These local correlation records do not replace Fabro run state.

The bounded native inspector reads summary, numeric event pages, timeline and questions without
using unstable `/state`. It records the exact native status and reason separately from
`engineering_readiness:not_evaluated`. Gaps, conflicting overlaps, stalled pages and unknown
native status produce explicit incomplete or unknown results. Seven contract cases pass, including
identical-page overlap and pending cancellation that remains nonterminal; the
disposable completed run also produced a complete 69-event inspection. Raw native questions
remain runtime observations and carry no 005 decision authority.

The question handoff now revalidates the 003 package and native-validation file digest, checks
that the graph is the compiler-rendered graph, and binds the pending `stage` to one gate and
source-map entry. It requires the exact selected 005 subject digest, the subject's workflow
package binding and coverage of the gate's obligation IDs. The `run.created` event must bind
the same native version and `approval:prompt`; auto approval, success-producing timeout defaults,
answered or ambiguous questions and changed version/subject IDs are refused. The handoff gives
an external human next action and `engineering_readiness:not_evaluated`, without an answer or
005 decision. Eleven contract cases cover these boundaries. The synthetic subject used by these
tests is `fixture_contract`; its self digest is an identity, not authenticated human authority.

The second disposable native integration test registered the sealed shared-human package,
created and started one run, inspected `blocked/human_input_required` with one question and zero
model tokens, produced the exact gate/subject handoff, and sent no answer. The test then requested
native cancellation and observed terminal `failed/cancelled`. Run
`01M3RH2SEE7JKSC9ZXVJMFVMR6` retained **164** consecutive events (IDs/`stream_seq` 1–164),
nine checkpoint timeline entries, zero `interview.answered` platform records and zero model
tokens. Its pending question vanished after cancellation; the earlier timeout run
`01M3RF4BKDZKTXPM2HTA7S1AE0` had question
`node_b3a60d7744d0e9fc356f57e8#7`, waiting `blocked/human_input_required`, then
`failed/workflow_error` at timeout. These are distinct from the completed command run's
`succeeded/completed`. Both selected native integration tests passed in **2.94 s**. An authorized
external human response channel was absent, so the journey stopped at the question.

## Frozen validation — 2026-09-30

`uv sync --frozen` checked 18 packages. `uv run --frozen ruff check .` passed;
`ruff format --check .` reported 262 files already formatted; `uv run --frozen mypy`
reported no issues in 60 source files. `uv run --frozen python scripts/check_foundation.py`
passed 64 unchanged FAB requirements, 19 dependency rows, Spec Kit skills, locks and local
links. With the pinned validator and matching disposable runtime explicitly selected,
`uv run --frozen pytest -q` passed **802 tests, 2 skipped in 27.99 s** on a fresh matching
disposable server after candidate-file symlink-race hardening, the blob-route contract test,
and a parent-path escape regression for run targets. A live two-blob probe also passed. The skips were the
fresh S-CORE native export manifest and real Bazel module/build prerequisites, neither provided
for this increment. The two 006 native integration tests ran; neither skipped.

`uv build --offline` passed. Wheel `score_sw_fabric-0.0.0-py3-none-any.whl` was 155,498 bytes,
SHA-256 `27b16d3e00cb2b63485ddae40bc45415bafb818121065617b7efdecfdd0abefd`;
sdist `score_sw_fabric-0.0.0.tar.gz` was 1,413,264 bytes, SHA-256
`454152f57145c3e6e0d9eed355fc3b66fc361ec41bb350c9e20ea543bfe724f0`.
The reference Fabro checkout remained clean. These are development checks; they do not
establish 005 production authority, an accepted runtime, a resumed effect or complete export.
The disposable server processes were terminated after validation, and their temporary dev-token
files were removed. Isolated nonsecret run storage remains under `/tmp/score-fabro-006-uHPItJ`
and `/tmp/score-fabro-006-final-20260930` for local inspection.

The 003 package entrypoint/wire-entrypoint mismatch and the candidate's absent native
run-create idempotency key are open implementation constraints. A lost create response must
stop automatic retry pending reconciliation. The independent 005 production trust-root pin
remains open under T009; Fabro success and fixture receipts cannot establish production
engineering readiness.

Pinned source `lib/apps/fabro-server/src/server/handler/lifecycle.rs:69-120` confirms that
`resume=true` checks for a checkpoint and excludes managed active states, but does not refuse
a persisted terminal `succeeded` or `failed` source before queueing. The fabric's future resume
admission must independently refuse terminal success, failure and confirmed cancellation unless
a distinct owner-authorized operation is specified. A 200 response alone cannot establish that
the same run continued or that effects were not repeated.

## Pending validation

- Remaining selected-candidate capability probes: same-run checkpoint resume, complete blob/output
  export and independently verifiable historical closure.
- Open items in [tasks](tasks.md), including public CLI, effect reconciliation, offline export and
  their adversarial integration tests.
- Owner-controlled 005 production identity, collector, human decision, trust-root, policy and
  protected time services; no human-owned review item is checked by this record.
