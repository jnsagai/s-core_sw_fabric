# Same-run repair orchestration and external human validation

Latest repair: **`01M40Y7RJF9NZJTE2N9Z3BAAXA` succeeded**; R1–R3 corrected.
Fresh integration verified 13 applicable passing cases and one source-supported
QNX-only exclusion on Linux. Final execution reran only profiling: both targets
passed. Unchanged formatting, compiler, native unit and fresh integration evidence
were checksum-verified and reused. The user has approved this scoped work outside Fabro.
[PR preparation and closure scope](../pr-preparation/closure-scope.md) record the
approval and the exact verified patch; no PR was created.
See [targeted repair evidence](review-repair-run.md),
[terminal status](runs/score-someip84-repair-b4ard87e/terminal-status.json) and
[portable archive](runs/score-someip84-repair-b4ard87e/review-packet.tar.gz).

## Earlier review and run history

The user explicitly requires human validation outside Fabro, mandatory before task
closure; orchestrators and loopbacks must repair failures inside the run, and
integration tests are mandatory. [The scoped contract](../../../../specs/010-misra-quality-and-deviations/contracts/someip-in-run-repair.md)
records this authority. Older native runs and their human timeouts stay preserved.

Previously reviewed native run: **`01M40R4FYAZR2PGCH5AQF4DRMC`**, succeeded; worker exited.
[The terminal observation](runs/score-someip84-repair-bi5z3qb7/terminal-status.json)
and [native stage outcomes](runs/score-someip84-repair-bi5z3qb7/native-stage-outcomes.json)
record its actual failed profiling check → orchestrator → repair → passing check
loopback under that single run ID. Only the two outstanding profiling tests executed;
both passed with no skips. Formatting, compiler, native unit and the six-test
integration results were reused under identical fresh candidate hashes.
The scoped technical work is complete; task closure remains pending mandatory
external human validation. [The review packet](runs/score-someip84-repair-bi5z3qb7/review-packet.json)
and [complete portable archive](runs/score-someip84-repair-bi5z3qb7/review-packet.tar.gz)
retain source, original logs, 12 real datasets, 12 flamegraphs and tool/license provenance.
[The workflow diagram](current-workflow.svg) shows the actual graph: four deterministic
orchestrators, three measured checks with repair loopbacks, affected regressions,
and external-review/unresolved packets. Human validation is drawn outside the native
workflow. The graph has zero human nodes and zero implementation-agent stages.

Each check evaluates actual tool outcomes, rather than successful collection.
Failure routes to its deterministic orchestrator, a scoped repair handler, and the
same check in the same native run. Three repair attempts bound each loop. There are
no implicit command retries. A repeated ineffective repair is rejected, rather than
being selected unchanged. Exhaustion produces a blocked packet; its blocking terminal
hook exits nonzero and makes the native run fail. Explicit terminal failure edges
are insufficient by themselves because native `on_failure=exit` still permits an
explicit matching conditional edge. Contract tests cover the blocked native hook.
The earlier run exposed this error and is preserved with its incorrectly green
native status and blocked verification packet;
the observer and external recovery adapter cannot create replacement runs for this
workflow. Fabro owns execution, events, checkpoints and routing throughout.

Only the three remaining failed groups are selected: formatting, QEMU integration
and profiling. Source formatting touches only the original candidate paths.
Fresh GCC/Clang focused tests and the native `//score/socom/test/unit:socom_test`
target verify the changed source before integration. Earlier passing checks remain
retained under their original source hashes rather than being reattributed to new
source. Mandatory integration disables test-result caching and requires all six
real native tests to execute and pass. Zero, partial, skipped or cached-only output
cannot satisfy that predicate. Integration precedes profiling.

The run has already demonstrated a real loopback: formatting failed with native
exit code 3, the orchestrator classified the measured failure, and the repair handler
formatted the four changed C++ source/test files inside the owned disposable
workspace. Their before/after hashes and every attempt are retained on bound SSD
storage. No functional patch is retroactively attributed to this repair workflow.
The fresh formatting and GCC/Clang results passed, as did the affected native unit
target. The current follow-up reuses their original checksum-bound results only
after checking fresh candidate hashes. It executes only the two outstanding profiling targets.

The earlier in-run integration repair exposed the already installed, checksum-bound
tools in Bazel's strict action/test PATH. All six tests then executed, with three
passes and three packet-capture failures. [The terminal observation](runs/score-someip84-repair-che5hm2t/terminal-status.json)
records the failure and the native-status discrepancy. No worker remains for that run.

The current capture repair builds pinned tcpdump 4.99.1 inside its repair stage.
Its narrowly scoped patch preserves an already selected UID/GID only in a
single-user namespace, with matching current UID/GID and group changes denied.
The host collector refuses a root launcher. This accounts for ITF's nested user
namespace, whose UID mapping is presented relative to the reader. It still performs setgid/setuid and propagates failures. The unchanged
native tests use the private binary through a Bazel binary-directory mount; packet capture,
filtering and every test assertion remain real. The system binary and native test
sources stay unchanged. The private libpcap development prefix contains the original
checksum-verified Ubuntu archive and relocated package configuration; libraries,
licenses, source commit and the tool patch are retained. This tool variant requires
external human qualification.

The failure is explained by [pinned Bazel namespace setup](https://github.com/bazelbuild/bazel/blob/8.6.0/src/main/tools/linux-sandbox-pid1.cc)
and [pinned tcpdump identity handling](https://github.com/the-tcpdump-group/tcpdump/blob/5f552b5e6e9fe05f7ad9681d51d0303233daba6a/tcpdump.c). The profiling repair creates a dedicated helper
that attaches to the exact run-owned workload. Its perf binary and runtime libraries
retain measured identities. The helper has no network, binds the disposable run and
read-only installed tool files, and uses explicit PERFMON/DAC_OVERRIDE/SYS_PTRACE/CHOWN/IPC_LOCK
capabilities with per-container seccomp/AppArmor settings. It changes no global
sysctl, tool storage, credential state or reference repository. The first attachment
smoke failures (exit 255) were traced to Docker's default AppArmor denying process-map
access. The corrected real attachment smoke recorded 8,096 samples and 676,668 bytes,
exit zero. This synthetic smoke establishes capability only; mandatory native
profiling results remain separate.

The first submitted repair attempt `01M40GPKEGS92QBFM0E039N6ZE` failed before any
measurement because a frozen hook imported the preparation builder, which was not
packaged. [That startup failure](runs/score-someip84-repair-che5hm2t/startup-failure-preserved.json)
is retained. The dependency was removed, and admission now imports every frozen
repair hook before native submission. The current run passed that smoke.

The terminal portable packet binds exact candidate/evidence hashes and reports
`task_closure: pending_external_human_validation`. Required human validation must
occur through the existing external engineering review process against that subject;
an agent report, successful run or local record cannot stand in for it. Human-owned
T107 and the earlier engineering reviews remain unchecked. No task closure, release,
merge, publication or deployment is claimed.

Validation after the final helper changes: 121 relevant contracts passed, one
environment-dependent native CLI test
skipped. Ruff, strict mypy (122 source files), frozen synchronization, foundation
consistency and package build passed. Negative-first tests cover real failure despite
successful collection, incomplete integration, bounded loopbacks, source staleness,
external closure, no successor dispatch, and frozen import independence. The pinned
Fabro validator accepts both the compiled graph and the sealed native-source overlay
that sets implicit retries to zero and terminal failure policy to `exit`.

The corrected capture smoke executed inside Bazel's PID namespace and ITF's nested
user/network namespace. It captured a real ICMP request and response, exit zero.
The first scoped binary mount exposed its executable name in sandbox argv, which
native stale-process assertions matched; the corrected directory mount retains
those assertions. The preceding failed run and its raw diagnostics remain preserved.

Integration in run `01M40NRH62RND9E3HA8KQXM1AJ` executed all six native tests and
passed, with 1,513 cache hits and six actual test actions. The retained original
failure triggered its repair without repeating the failing command. Original
result and log checksums bind this diagnosis reuse; it cannot satisfy readiness.
Source formatting and the affected regressions were reused under identical fresh
candidate hashes. The stopped disposable native build workspace is reused with
its bound volume and verified absence of a worker; no queue was migrated.

The profiling helper resolves the namespace PID to the unique host PID using the
PID namespace inode and process start time. Its real PID-namespace smoke recorded
9,277 samples and 781,120 bytes, exit zero. Shared storage validation now accepts an
explicit owner context and distinguishes subdirectory binds from duplicate root
mounts. Disconnection, substituted images and duplicate filesystem-root mounts
remain failures. Native profiling selects only the two previously failed end-to-end
tests and rejects skipped execution. Both targets executed and passed, with no skipped tests.

The later scoped follow-ups preserve each native failure and every diagnostic:
[read-only invocation-directory failure](runs/score-someip84-repair-n9_a6foi/terminal-status.json),
[concurrent locked-memory and artifact-ownership failure](runs/score-someip84-repair-35ug26v0/terminal-status.json),
and [signal termination during finalization](runs/score-someip84-repair-4kav1jee/terminal-status.json).
Their workers have exited. No frozen controls or native statuses were rewritten;
corrected host-hook packages were submitted explicitly, with retained passing checks
and the original failed diagnostics. The observer never dispatched a replacement.
Within each submission, the diagnostic enters a native check → orchestrator → repair
→ check loop under that submission's single run ID.

The writable invocation directory is exposed through Bazel's verified
`--sandbox_writable_path`. CHOWN returns actual recording outputs to the measured
build user's UID/GID, allowing Bazel to materialize them. IPC_LOCK is scoped to each
profiler helper, rather than changing the machine's locked-memory setting; the
[Linux perf security documentation](https://cdn.kernel.org/doc/html/latest/admin-guide/perf-security.html)
explains concurrent profiler buffer limits. Three concurrent real PID-namespace
recordings passed with user-owned artifacts. Kernel-symbol restrictions remain
visible in diagnostics and are not an assertion of profiling qualification.

The helper uses the actual perf `stop` control command to flush attached recordings,
verified against [Linux 6.8's implementation](https://raw.githubusercontent.com/torvalds/linux/v6.8/tools/perf/builtin-record.c).
It retains genuine perf and workload failures. Decoding checks a successful recording
receipt and the dataset checksum before allowing the helper's different UID to read
it. Four negative contracts reject changed bytes, failed recordings, mismatched
owners and files outside the bound run. A real record/decode round trip produced
7,662 samples and 2,030,376 bytes of decoded stack data, exit zero; this capability
smoke is separate from native readiness.

The review packet retains actual native profiling outputs and raw logs, their
checksums, capture binary/source/package/patch/license provenance, candidate source
and repair history. Archived candidate snapshots preserve original bytes and paths;
extract them beside the portable packet to restore its candidate-directory reference.
External human review must assess tool qualification and evidence limitations in
addition to the candidate. Existing unresolved engineering findings remain explicit.

The terminal native measurement reported `Executed 2 out of 2 tests: 2 tests pass.`
The full test took 166.2 seconds, the focused test 17.7 seconds; 1,532 action-cache
hits reused build outputs, while both actual test actions executed. This final run
contains one measured obligation directory, for profiling only. All five required
selected results match the final candidate hashes. The stage record contains zero
provider calls and no pending interviews. Human validation stays outside Fabro;
T107 remains open. CPU scaling, ASLR, kernel-symbol visibility and local-tool
qualification limits remain part of the evidence, not engineering acceptance.

[Offline packet verification](runs/score-someip84-repair-bi5z3qb7/offline-packet-verification.json)
restored the archive on the selected bound SSD without Fabro, verified all 269
candidate source hashes and 112 portable evidence files, checked 12 perf-file headers
and recording receipts, parsed all 12 flamegraphs, and confirmed the original six-test
integration and two-test profiling pass logs. This is deterministic evidence replay;
it does not perform or replace the pending human validation.

## Subsequent agent review: changes required

The [agent technical review](runs/score-someip84-repair-bi5z3qb7/agent-review.json)
requests changes before merge or closure. A real synthetic workload terminated with
SIGSEGV (direct exit -11), but the scoped profiling wrapper returned zero: its
return-code guard propagates only positive exits. Passing reuse binds result JSON
without binding original raw log bytes. The integration predicate checks passing
Bazel targets without checking applicability and case-level skips. Its actual record
has six passing targets, 13 passing Python cases and one QNX-only case skipped on
Linux; that exclusion must be explicit rather than described as no skipped cases.

The archive integrity, passing run and actual repair-loop record remain intact. The
full benchmark JSON contains 43 entries and the focused benchmark one entry, with no
reported benchmark errors. These positives do not remove the failure-propagation
and evidence-validation defects. No historical native status or evidence was rewritten,
no queue was rerun and no implementation code was changed during this review.
Human-owned T107 remains unchecked. This is an agent review, not human validation.
The current implementation fixes registration-key duplication; upstream #84 also
discusses public identifier and discovery design. Closing that issue needs an agreed
scope or the remaining implementation, in addition to external human acceptance.
