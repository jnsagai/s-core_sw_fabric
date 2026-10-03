# SOME/IP repair orchestration and external validation

Authority: the user's 2026-10-03 instruction moves human validation outside the
workflow, makes it mandatory for task closure, requires orchestrators and loopbacks
to repair errors inside the same run, and makes integration tests mandatory.
This supersedes the operational SOME/IP human stop, not human engineering authority.

Fabro remains the sole runtime. New SOME/IP recovery graphs contain deterministic
orchestration, measured checks, scoped repairs and native loopback edges. A tool
failure, missing result, unavailable collection, timeout or unexecuted required
integration test cannot route to successful completion. Collection success alone
is insufficient. Each error routes to diagnosis, a repair, and a fresh measurement
inside the same native run. Three repair attempts per affected check bound execution;
exhaustion retains a failed run and an explicit unresolved blocker, never acceptance.
An external observer must not replace a failed repair workflow with another run.

Only the previously failing formatting, profiling and integration checks are selected.
Formatting changes are restricted to the existing six candidate paths. Fresh focused
regression and affected native unit tests are required after source changes. Prior
passes stay retained with their original source hashes; they are not reattributed to
the corrected source. Mandatory integration must report all six real native tests
executed and passed; absent, skipped, cached-only or zero-test output is insufficient.

Deterministic orchestrators read actual tool diagnostics and retain classifications,
repair actions, source/tool identities and every prior attempt. They do not accept
engineering decisions. Trusted host repair handlers may expose verified installed
tools to Bazel, apply exact-version formatting inside the owned disposable container,
and provide a run-scoped perf execution environment. They cannot change machine-wide
perf policy, source locks, reference repositories or global tool storage.

Repair selection must follow the measured diagnostic. A repair that leaves the same
failure cannot be selected unchanged again. Unknown failures remain explicit blockers.
The scoped capture tool variant builds pinned tcpdump 4.99.1 with a recorded patch:
it preserves an already selected identity only inside a single-user namespace where
supplementary-group changes are denied; the host launcher must be non-root. Real packet capture,
setgid/setuid failures and test assertions remain active. Native test sources and
the system tcpdump remain unchanged; tool qualification needs external validation.

Passing formatting and affected regressions may be reused only with identical fresh
candidate hashes and checksum-bound original results. A blocked terminal packet must
reject its blocking native hook; an explicit failure edge to the exit node must never
be mistaken for successful verification.

Original failed diagnostics may trigger the initial repair without repeating the
failed command when their result/log checksums and candidate hashes match. This
reuse is diagnosis only. Integration still requires a fresh execution of all six
tests after the repair. Native build outputs may be reused from a stopped disposable
queue with no live worker, bound storage and matching candidate hashes; running
queues are never migrated. Profiling selects only the two failed end-to-end targets
and rejects skipped tests. A later targeted follow-up can retain the original
six-test integration pass only under identical fresh candidate hashes and original
result/log checksums; it executes only checks still missing. PID namespace resolution and the storage owner's explicit
context bind the scoped perf helper to the actual workload and mounted volume.

The terminal output is a portable review packet with technical completion separate
from `task_closure: pending_external_human_validation`. Human validation is recorded
outside Fabro against the exact candidate and evidence hashes using the existing
review process; no local receipt, agent report or Fabro success fabricates authority.
Human-owned review tasks remain unchecked until that validation actually occurs.

Required tests: failed tools despite successful collection route to repair; missing
and skipped integration block success; graph has no human node, contains sourced
bounded loops and orchestrators; exhaustion cannot succeed; source changes invalidate
old evidence; native failures do not spawn successor runs. Actual native execution
and integration results are required separately from fixture contract tests.

Profiling helpers use explicit per-container capabilities and perf's native control
interface; successful collection, signal termination or an empty/skipped test cannot
satisfy profiling. Actual workload and perf failures remain failures. Decoding accepts
only a successful scoped recording receipt and matching dataset checksum. The portable
packet retains raw datasets, flamegraphs, tool/source/patch/package/license provenance
and original diagnostics. Tool qualification and evidence limitations remain subject
to mandatory external human validation.

## Agent-review repair run: R1–R3

The user's targeted repair instruction authorizes the three reproduced findings,
not the complete upstream identifier/discovery redesign. The repair run reuses
formatting, compiler and native unit results only after verifying their original
raw bytes against the previously archived portable packet. Legacy imports must
retain that archive's checksum and original manifest provenance; calculating new
hashes of mutable old logs cannot substitute for the original checksum anchor.
New collectors bind stdout, stderr, command records and exported native artifacts
at measurement completion. Reuse and packet creation verify every bound file.
Changed or unbound passing evidence blocks reuse.

Mandatory fresh integration reruns all six native Linux QEMU targets and retains
each target's native pytest XML and log. The predicate requires the exact 14 case
identities: 13 execute and pass; only the QNX split-process gateway case is excluded
on Linux, using its exact native skip reason and the pinned applicability source
hash. Missing-capability skips, unexpected exclusions, missing/duplicate cases,
failures and unknown platform/source applicability block completion.

The profiler wrapper propagates positive workload failures and signal exits
(SIGSEGV becomes 139; SIGKILL becomes 137). A profiler exit of zero reports only
successful recording. Receipts also retain workload/wrapper exit codes. Native
daemon cleanup deliberately kills gatewayd/someipd/echo_server and ignores the wrapper return;
only that recorded SIGKILL cleanup may decode daemon data. Foreground crashes
remain failures and their datasets cannot decode as successful workload evidence.
An actual scoped crash/normal-workload qualification check runs inside the native
workflow separately from the two fresh native profiling targets. Synthetic tool
regressions cannot replace native integration or performance evidence.

Recorded original failures and the real agent-review crash reproducer can trigger
scoped repairs without repeating known failed commands. Every diagnosis must state
its original measurement and scope; candidate hashes on a tool regression bind the
repair scope, not a claim that the synthetic workload tested the candidate. The
native run builds/provisions its repaired tools and executes fresh verification
through its bounded loopbacks. External human validation remains mandatory for
closure and is never a workflow node or an agent-owned task.
