# Increment 006 acceptance evidence

**Status:** Implementation in progress; 39/40 tasks complete. The public `score-fabric runtime`
commands were executed against a disposable server built from the pinned candidate: registration,
run creation/start, status, waiting human question, confirmed cancellation, resume admission,
portable export and offline verification. **Same-run checkpoint continuation is not
demonstrated:** the candidate's explicit resume was accepted but inert, so `run_resume` stays
undemonstrated and T025 remains open. Production runtime selection, 005 production authority
(005 T009) and engineering acceptance remain unestablished. No question was answered and no paid
model call was made. Sections below are chronological; the first two record the prior session.

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


## Continuation session — 2026-09-30 (from `7fa0ff4`)

### Disposable environment

A fresh server ran the digest-checked pinned executable
(`09d338fbbe107d6c2e41fe9f3b33531c72b54782a2e17dac7c720b89898a68cf`, link count 2, Git
`1b4fb15281ebb724426f9e480dce48d0100ff79b`) with
`server start --foreground --no-web --bind 127.0.0.1:43995 --storage-dir <root>/storage
--config <root>/settings.toml --max-concurrent-runs 1` in root
`/tmp/score-fabro-006-t007-jZMLPa`. `HOME` was isolated under the root; `settings.toml` enabled
only dev-token auth. The dev token and session secret were generated from `/dev/urandom` into
owner-only files and passed to the server by environment, never through a fabric command.
`/proc/<pid>/exe` resolved to the pinned executable and `/proc/<pid>/cwd` to the root (initial
pid 3466138; after the deliberate restarts below, pid 3504644). The user's unrelated server on
`127.0.0.1:32276` was not contacted. The reference checkout stayed clean at the pin.

### T007 — native capability probes

Probe-only graphs below are native capability probes, **not 003 packages**; their command steps
append to an absolute file outside Fabro's workspace so external effects can be counted.

| Probe (run ID) | Observation |
| --- | --- |
| Baseline command graph (`01M3RM0HCBPENSN7XX5D1TBM25`) | Commands execute in a Git-backed scratch workspace (`storage/scratch/<run>/petri/scopes/…/work`), not the target folder. 81 events; five checkpoint records, four with `patch_blob` (137–168 B, SHA-256 equal) |
| Graceful stop during a running command (`01M3RM2A5SJ4R74XY2VABGZKRN`) | Summary `failed/terminated` (seq 47); timeline `start@1`, `effect@1`; stage list `hold@1 running`. The orphaned command kept running and wrote `hold-end` after termination (external log `effect, hold-start, hold-end`). Explicit `start {"resume":true}` returned 200 twice (before and after a restart), appended `start_requested(resume)`/`runnable`, and the worker logged `run already finished already — nothing to resume`; summary stayed `failed/terminated`. A second resume on the same server returned 409 `an engine process is still running for this run — cannot resume` |
| Server SIGKILL, worker alive (`01M3RM48DKPAKG9HM2FAWXT7RW`) | Startup continuation of the same run (`resume` at seq 47). The orphaned worker lost its lease: `failed/workflow_error` at 77 and 84, then `succeeded` at 90, while the summary reported `failed/workflow_error`. External log: `effect` ×1, `hold-start` ×2, `hold-end` ×1, `after` ×1 |
| Server process-group SIGKILL (`01M3RM5BVGCM3DR6S1G71MCA6E`) | Worker runs in its own process group; identical race and effect counts |
| Server and worker SIGKILL (`01M3RM610XG2RZ352XS8FABE7W`) | Startup continuation reached `succeeded/completed` (86 events). Checkpointed `effect` ran once; in-flight `hold` re-executed (`hold-start` ×2) while timeline and stage list show only `hold@1 succeeded` |
| Cancel a running command (`01M3RM8QADTAZ00TZ6KNE2QGJ9`) | 202 with the lifecycle object `{status: running, pending_control: cancel}`; `failed/cancelled` within 0.2 s; `hold@1 cancelled`; external log then `effect, hold-start` (no `hold-end`). Resume then returned 200 but stayed `failed/cancelled`; start returned 409; cancel again returned 409 `Run is not cancellable.` (also for a succeeded run) |
| **Unintended native `/retry` (probe error)** | A later probe line meant only to note the `/retry` route sent `POST /api/v1/runs/01M3RM8QADTAZ00TZ6KNE2QGJ9/retry` once (a conditional suppressed only its print). Fabro returned 201 and created fork run `01M3RN491PF4KSCBH6AVFR40FH` seeded at firing 2, which re-executed `hold` and `after`, appending `hold-start, hold-end, after` to the same disposable log (final 44 B). No model, external system or 003/005 record was involved. It confirms that native `/retry` is a new run that repeats effects; no fabric code path sends it |
| Stage output and dump (`01M3RM7F0BF72B8S3MESBZD9B2`) | Output route returned 9 bytes `hello-006`, `eof=true`, `cas_ref=null`. Native `fabro dump` exported 12 files (77,774 B), 58 events equal to the API stream, but omitted `workflow.toml`, the definition/spec/graph blobs and any digest manifest. Dump over TCP needed `fabro auth login --dev-token` inside the isolated HOME; that probe passed the disposable token once on a local command line |
| Blob closure (`01M3RM610XG2RZ352XS8FABE7W`) | `definition_blob` 1,616 B, `spec_blob` 3,047 B and admission graph `blob` 8,116 B fetched; each SHA-256 equals its reference |
| Human gate lifecycle (`01M3RMCG2WMSS5NWT51H6EAWMR`) | `blocked/human_input_required` emits no lifecycle record (last is `running`, seq 6); stage list shows the gate `running`; cancel produced `cancel_requested` (147) and `failed/cancelled` (163) |

The external logs for the three crash probes (`kill`, `crash`, `host`) each end as `effect,
hold-start, hold-start, hold-end, after`.

Result: register, create, start, inspect, events, timeline, questions, stage list, output, blob
and cancel are demonstrated. `run_resume` is **declared but not demonstrated**: no explicit
same-run resume continued execution, and the only observed continuation (startup after a crash)
is automatic, outside fabric admission, and re-executes the in-flight step. The
[contract](contracts/runtime.md) was revised accordingly.

### Implementation evidence (T008–T036)

- **Projection/intents (T008, T009, T011–T013):** 26 projection cases pin the refusal code for
  undeclared, missing, redirected, case-colliding and shadowing files and an injected child
  reference (003 validation fires first: `PACKAGE_CLOSURE`, `PACKAGE_ENTRYPOINT`,
  `PACKAGE_CASE_COLLISION`, `IR_DIGEST`), plus relocation to the same wire digest. 12 intent
  cases add a lost create with a label-bearing native run that never clears
  `reconciliation_required` (no list/search capability) and an interrupted ledger replace that
  keeps prior bytes.
- **Inspection (T016, T019):** a terminal summary must equal the last status-bearing lifecycle
  record with no later lifecycle request; otherwise `NATIVE_STATE_CONFLICT` makes the view
  incomplete. Cases reproduce both observed conflicts; waiting and confirmed cancellation are
  consistent. Malformed stage lists or timelines are `STAGE_INCOMPLETE`/`CHECKPOINT_INCOMPLETE`.
- **Resume/cancel (T023, T024, T026, T027):** 25 resume and 5 cancellation cases cover every
  one-binding drift, 005 missing/stale/non-replaying evidence, version/intent change, missing
  checkpoint, five terminal sources, four active sources, conflict, in-flight effect states,
  finite attempts, uncertain prior resume, admission-gated route use, no `/retry` route, and
  accepted-but-inert resume becoming a visible conflict.
- **Export (T030, T031, T033, T034):** 17 closure and 4 origin cases cover complete and waiting
  exports, relocation with zero native calls, unavailable blobs, output limits, nine resealed
  mutations (event, blob, output, package bytes, version, extra blob, relabelled origin, runtime
  commit, readiness claim), unresealed single-byte corruption, and a recorded `incomplete` marker
  that verification never upgrades; answers remain runtime
  observations, fixture 005 references are never production-eligible, and a `production`
  reference is refused.
- **CLI (T014, T021, T028, T035):** 14 command cases cover the full simulated journey, lost
  create, interrupted `create_in_flight`, four malformed requests (exit 2, prior output
  byte-identical, bounded `{code, pointer, message}` without the token), protected/ledger output
  refusal, unbound waiting, resume refusal/drift/capability block, admitted resume with a durable
  attempt, confirmed cancellation, and incomplete/corrupt verification. A schema test keeps the
  runtime schemas' required fields equal to the readers.

Runtime contract totals: 206 passed across the eleven `test_runtime_*` files
(cancellation 5, client 15, CLI 14, export origins 4, export 17, human gate 11,
inspection 14, intents 12, models 55, projection 26, resume 25) plus 8 foundation CLI cases,
in 5.27 s.

### Native integration tests (T010, T015, T018, T025 partial, T032)

With the five `SCORE_FABRO_*` variables selecting the server above, the six native tests passed
(9.77 s standalone, before the last two intent cases were added). The final frozen run recorded:

| Case | Native identities and result |
| --- | --- |
| Relocation, drift, duplicate intent, lost response | Relocated and original bytes registered as `47cbdbad41371f725f650c461d926c65f58b22bcaffcdfe40daca4f6aef4f6ff`; unsealed drift `PACKAGE_DIGEST`, resealed drift `PACKAGE_FILE_DIGEST`, no request. Duplicate intent reused `01M3RNV4WS09S5JZD9527G6VGX` with one start. A create whose response was dropped after native acceptance created exactly one run (`01M3RNV52CM9AX8RCKNGVS08KY`, found only by a test-side raw list) and the ledger refused a second create. 003 package bytes unchanged |
| Resume admission and cancellation | Completed `01M3RNV5PAJRTKXYGM4DFKBJ8Z`: all stages `@1`, `refuse_terminal`, native route refused before transport, events unchanged. Waiting `01M3RNV6ET3G0N517NAQ48FG8R`: `block_unknown` (`EFFECT_RECONCILIATION_REQUIRED`, `RESUME_SOURCE_ACTIVE`); cancel 202 then confirmed; earlier events retained as an exact prefix; `refuse_terminal` (`CANCELLED_TERMINAL`); second cancel refused |
| Probe-graph external effect | `01M3RNV84861GQHAP607JKWQY5`: stages `start@1, effect@1, exit@1`; external effect exactly once, unchanged by inspection |
| Completed and waiting export | `01M3RNV98BSW00TCJHQYBBYYWD` (69 events, 9 blobs, 96,810 B, SHA-256 `f3f163d52beb7fa059d74975dae093a4c1b17ea2642fb78970c6eb1b8b407b35`) and `01M3RNV9YQ6WD0METE0J50AJPC` (146 events, 14 blobs, 232,070 B, SHA-256 `f0f4a1a095a1b65ecce30d36b6fd30d8b13fb66f91c19fe24ad0e2e1b691a436`) relocated and verified with a transport that fails on any call; removed blobs gave `BLOB_MISSING`, corrupted bytes were refused |

T025 is **not** complete: its checkpoint-resume journey cannot run because the candidate has no
operational same-run resume. The integration covers admission, cancellation, history
preservation and a single-effect count, not an unchanged resumed continuation (AC006-07).

### Public command journeys (T014, T021, T028, T035)

All outputs are under `/tmp/score-fabro-006-t007-jZMLPa/cli-out` (SHA-256 of published bytes).

| Command | Exit | Result |
| --- | --- | --- |
| `register` linear (`cli-linear-006`) | 0 | version `47cbdbad41371f725f650c461d926c65f58b22bcaffcdfe40daca4f6aef4f6ff` prepared; `60f421b20e2c1789c4aee5660926e83b3413f82078a1b346cead147419b49115` |
| `run` linear | 0 | run `01M3RN874CV0SSKHPX1F2Q75D2` started; `14d774bc3d148a041ae2952dbacbbcd309cb5b21f8d01a38c6e8437d08995833` |
| `status` linear | 0 | `succeeded/completed`, complete; `930601ab4ad2fda64d93f04a8fc9c5e8396196276caed4c757ac3677a4a43bac` |
| `resume` linear | 1 | `refuse_terminal` `RESUME_SOURCE_TERMINAL`, `not_sent`; `48da1091045aad21586736f12872dc3e664af0e8abe60369cba04ad945d8c5e5` |
| `export` linear, relocated `verify` | 0 / 0 | complete, 69 events, 9 blobs; `46507af840222b002e3dd53e5f7eef7276397bc90dabe1c17c0e240b0144d7fe` |
| `export` with 005 fixture evidence, `verify` | 0 / 0 | reference `e291defaa985c8f9394aa144c2230bfab9480c66c88539b3d41b24a473c67bb0` `authenticated_005_reference`, `fixture_contract`, `production_eligible: false`; `ecba6d78ddcafce8685d498ed2ccea0c30b3431faf381dfbb008a5f84cba5578` |
| `verify` flipped blob byte / dropped event (unresealed) | 2 / 2 | `SEMANTIC_DIGEST` |
| `run` human (`cli-human-006`) | 0 | run `01M3RN8QKJN6H0PQHFC9JJJWQN`; `5edec7bd9c0a895c97c9521bc611fd29e20cae736f7773b914f3a71517de0115` |
| `status` human | 0 | `blocked/human_input_required`, `HUMAN_GATE_WAITING`, question `node_b3a60d7744d0e9fc356f57e8#7` bound to gate `node_b3a60d7744d0e9fc356f57e8`, synthetic `fixture_contract` subject `cb26b4381fbd4b1764e8c0231efe809e2f2c0c67bcfa29ecefb5a3a4b45bae9c`, next action external human; `805068d569f9f1c755efd66f3d00c30071f69ef032d23bb1e7399afc8dab6496` |
| `resume` human | 1 | `block_unknown` (`EFFECT_RECONCILIATION_REQUIRED`, `RESUME_SOURCE_ACTIVE`); `9909304c2d42c2257367037009324a6cdb018044bbb2a9f3fa66c4f6eb106d06` |
| `export` waiting, `verify` | 0 / 0 | complete, 146 events, `native_answers_observed: 0`; `75800202f057e9abf65e1abc36d064074d1939bfc5f094e3f0b77977c0d9170b` |
| `cancel` human | 0 | confirmed `failed/cancelled`; `4371c2523ede78bdf509e3d4ded8a2ff587684daa77712d04fcc7c88274f3680` |
| `status` / `resume` after cancel | 0 / 1 | `failed/cancelled`; `refuse_terminal` `CANCELLED_TERMINAL`; `8a77977d8d62f2507053bfeca72ad271ad96d8f8fa49f41a297549fb9d8749cc`, `8b8261b3fe5b988570fc87d3120f215a32b5349bccc5a9a306828eb9bbdf654c` |
| `export` cancelled, `verify` | 0 / 0 | complete, 164 events; `e38ba913d138ccd7c28ef7138c7c3b8b63a66104af7b7d3121be7cb30cdcde09` |

**Interrupted sealed 003 run (`cli-interrupt-006`, run `01M3RN9PJ9CZ3ZDC8RQEPV5P0W`).** The
shared-human run waited at its gate (status exit 0), then the disposable server was stopped
gracefully and restarted. Status became `failed/terminated` with last checkpoint
`node_ac90e5e2fd0c0f7744473d18@1` and in-flight `node_b3a60d7744d0e9fc356f57e8@1`; Fabro still
listed the question, so status exited 1 with `QUESTION_SUBJECT_UNKNOWN` (not a waiting gate).
`resume` without effect records → `reconciliation_required` (exit 1); with the gate effect
`confirmed_absent` → admitted internally but published `block_unknown`
`RUNTIME_CAPABILITY_UNAVAILABLE`, `not_sent` (exit 1); with `policy_digest` changed →
`block_drift` `baseline:policy_digest` (exit 1). A raw capability probe of native resume on this
run returned 200, the worker again logged `run already finished already — nothing to resume`,
and the summary stayed `failed/terminated`; the fabric then reported `NATIVE_STATE_CONFLICT`
(status and resume exit 1) and exported the run as `incomplete` (exit 1), which `verify`
reproduced as incomplete. Output SHA-256: run `07386e2b5820a438dc7465280aa1985175b222ef4dcfef452314d4d1781ff997`,
waiting `09ebfd1134d1f828429396e4eb797a7933cce44db8996ddc924e6e978aba658a`, terminated
`de62ee3d82666a2b980d6bc515352c27299aaeb6d6d116835e775ebfb95aacc5`, resume variants
`6f644ca4d80e6844a0061b1b4bc62435a5e83ab7b808e75d5661bfd0fc1354ac`,
`8050ee806356af573ab908fc69af69a51629265c78d3453f34c0d049332e6892`,
`6d79db0a4bf219dde42c7b7434542f7d7df4d122a910f53a6d2838cbfb6f7648`, conflict status
`b00df7baa7fa073b135da5a32aecd32941ac26b68eeed7c73ac26ee592b67243`, export
`39c885318fe53d2fdf782c32167527eca3957058e956cd836947e85f83474093`.

### Requirement reconciliation (T037)

| Item | Evidence | State |
| --- | --- | --- |
| 006-R01 / FAB-024, AC006-04/05 | Native summary/events/timeline/questions/stages/cancel are read faithfully; conflicts and unknowns are explicit; ledger holds only correlation | Met on candidate |
| 006-R02, R03 / FAB-025, AC006-01/03, SC006-01/02 | Closure/limits/receipt checks before registration; relocated bytes → same content-addressed version; drift refused with zero requests | Met on candidate |
| 006-R04, AC006-02/09 | Lost create → one native run, `reconciliation_required`, no retry; `create_in_flight` after interruption also stops | Met; exactly-once creation impossible without native idempotency |
| 006-R05, R06, AC006-04/06, SC006-03 | One pending question bound to exact gate/subject; zero answers, zero model tokens; unbound or non-waiting questions refused | Met; authorized external human channel absent |
| 006-R07, AC006-08 | Every one-binding drift, 005 evidence drift, version change → `block_drift`, history unchanged | Met (admission level) |
| 006-R08, AC006-07/09/10, SC006-04 | Finite attempts, effect reconciliation, confirmed cancellation stays terminal | Admission met; **same-run continuation not demonstrated** (candidate resume inert; crash continuation re-executes in-flight steps) |
| 006-R09, AC006-11/13, SC006-05 | Completed, waiting, cancelled and conflicted exports; offline, relocated verification; missing/changed bytes fail closed | Met on candidate |
| 006-R10, AC006-12, SC006-06 | Fabro output/answers `runtime_observation`; fixture 005 never production-eligible; production reference refused | Met |
| 006-R11 | Stable 0/1/2 exits, bounded diagnostics, prior output preserved | Met |
| 006-R12 | Demonstrated-capability gating; `run_resume` unproven and unavailable | Met; runtime not selected |

### Frozen validation (T039)

With the pinned validator/executable and disposable server selected by `SCORE_FABRO_BIN`,
`SCORE_FABRO_RUNTIME_DISPOSABLE_ROOT`, `SCORE_FABRO_RUNTIME_URL`,
`SCORE_FABRO_RUNTIME_TOKEN_FILE` and `SCORE_FABRO_SOURCE_API`: `uv sync --frozen` checked 18
packages; `ruff check .` passed; `ruff format --check .` reported 273 files formatted; `mypy`
reported no issues in 64 source files; `pytest -q -rs` passed **893 tests, 2 skipped in 39.29 s**
(skips: fresh native export manifest and real Bazel module prerequisites, not provided for this
increment); `scripts/check_foundation.py` passed 64 unchanged FAB requirements, 19 dependency
rows, Spec Kit skills, locks and local links. `uv build --offline` produced wheel
`score_sw_fabric-0.0.0-py3-none-any.whl` (173,044 B, SHA-256
`5be7b0457de135c933fd3d636df40fd4dd3dd6004d78f069886ab67842923ba8`) and sdist
`score_sw_fabric-0.0.0.tar.gz` (1,460,875 B, SHA-256
`f098d42a39a3e701354f0ce57bb19e48ddbc513a879dd5e634bfc7c4edc0e927`). The sdist includes documentation; this record's final text edits
postdate that build, so a rebuild changes the sdist bytes. Without the selection
variables, the three 003 native-validator tests fail by design (`SCORE_FABRO_BIN is required`)
and the 006 native tests skip. Fixture bytes were unchanged (`git status` clean): 003 linear
package `9605abac81940cdde5e54e8b367ac47cff8a792a85a43e1fd2c361ccdf1ce95b`, shared-human package
`3dbb8a98b2377a9fa04c18097912fca6128dde21c63c065b4e4693f10504452e`, 005 passing assessment
`d133c516c2d6c5f29118391f6b0e09ed863706386cee5696781abbc958374ccf`.

After validation the disposable server was stopped, and its token, session secret and isolated CLI
`auth.json` were deleted. Non-secret storage, logs and exports remain under
`/tmp/score-fabro-006-t007-jZMLPa` for local inspection. Nothing was committed, pushed, merged,
published or deployed.

### Open boundaries

- T025 and AC006-07/SC006-04: a selected runtime with operational same-run resume (or an owner
  decision on another continuation mechanism) is required; native crash continuation must be
  treated as an unfenced effect hazard until then.
- Runtime selection: the candidate remains `candidate_only`; production authentication and
  deployment configuration are unassessed.
- 005 T009 and owner-controlled identity, collector, decision, role, policy and protected-time
  services remain pending; no production pass is possible.
- An authorized external human response channel is absent; no question was answered.
- No human-owned review item is checked by this record.
