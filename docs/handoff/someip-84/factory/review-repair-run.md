# Targeted repair of agent-review findings R1–R3

Final native run **`01M40Y7RJF9NZJTE2N9Z3BAAXA` succeeded**, and its worker exited.
The three reported defects are corrected for the scoped candidate. The user has
now [approved the scoped work outside Fabro](runs/score-someip84-repair-b4ard87e/external-user-approval.json)
and requested [local PR preparation](../pr-preparation/closure-scope.md). Original
measurement records retain their earlier pending status; no upstream issue closure
or maintainer acceptance is claimed. [Terminal status](runs/score-someip84-repair-b4ard87e/terminal-status.json),
[native stage outcomes](runs/score-someip84-repair-b4ard87e/native-stage-outcomes.json)
and [agent review resolution](runs/score-someip84-repair-b4ard87e/review-resolution.json)
retain the observations separately.

| Finding | Correction | Measured verification |
|---|---|---|
| R1: profiler hides workload signal failures | Propagate signal exits; record workload and profiler status separately; decode only normal completion or known native daemon SIGKILL cleanup | Real SIGSEGV wrapper exit 139 and decoding rejected; normal workload exit zero and decoding succeeds; both native profiling targets pass |
| R2: reused passing logs lack identity binding | Hash new raw logs, command records and artifacts at measurement completion; verify identities before reuse/packet creation; import legacy hashes from the original archived packet | Changed stdout, stderr, command record and artifact rejected; unbound legacy pass rejected; archived originals verified before reuse |
| R3: six Bazel passes can hide skipped applicable cases | Export native pytest XML and require exact case identities and source-supported platform applicability | All six native targets executed; 13 applicable cases passed; only the exact QNX split-process gateway case excluded on Linux |

The first targeted run, `01M40XMJ9K182CG0SWBNVPY7AB`, built its capture repair
inside its native loop and passed fresh integration. Its corrected crash guard
passed the actual signal regression, but native profiling exposed an additional
intentional cleanup: the pinned harness kills `echo_server`, alongside gatewayd
and someipd. The incomplete cleanup classification rejected its dataset. The run
failed and stopped; its original results, stage outcomes and 48 retained failed
native artifact files remain preserved. It was not rewritten or automatically
replaced. [Failed terminal observation](runs/score-someip84-repair-0oa1nndu/initial-terminal-status.json).

The manually prepared correction run retained the fresh checksum-bound integration
pass and reused the unchanged formatting, GCC/Clang and native unit results. Only
profiling executed again. Its native stages show failed check →
`native_echo_server_cleanup` diagnosis → scoped helper provisioning → fresh passing
check, within the final run ID. All four deterministic orchestrators and three
bounded loops remain in the graph. There are no human interview nodes, model calls
or automatic replacement runs. [Current graph](current-workflow.svg).

Final profiling executed both actual native targets, with 1,532 build action-cache
hits and fresh test actions. It retained 12 perf datasets, 12 flamegraphs and
benchmark JSON with 43 full-suite entries and one focused entry, with no reported
benchmark errors. Its actual crash/normal-workload regression is tool qualification
evidence, separate from native candidate tests. No C++ candidate source changed
during this repair; all 269 candidate source hashes still match the original scope.
CPU scaling, ASLR, kernel-symbol visibility and local tool qualification remain
evidence limitations for external review.

Local validation: **147 tests passed, zero skipped**; Ruff, mypy (122 source files),
foundation consistency and package build passed. The previously skipped Fabro CLI
authentication test now selects the installed pinned binary instead of a deleted
temporary build path. The fixed handlers and their dependencies were frozen,
validated and imported successfully before the native run started.

The [portable archive](runs/score-someip84-repair-b4ard87e/review-packet.tar.gz)
contains the exact candidate, original checks, native integration XML, profiles,
flamegraphs, frozen collector/repair code, capture source/patch/license provenance,
the original legacy checksum anchor, actual tool regression and preserved failed-run
diagnostics. It is 36,969,655 bytes; SHA-256:
`2b8f5c40ae194ba06f8e6c95933c05727ec8f4bec563ef7c4fc10ef3e33fa6da`.
[Offline verification](runs/score-someip84-repair-b4ard87e/offline-packet-verification.json)
restored it on the bound SSD without Fabro, verified all 1,046 portable files and
269 candidate source hashes, re-evaluated native integration case outcomes, checked
all 12 datasets/receipts and parsed all 12 SVGs. Packaging is explicitly separate
from original measurement timestamps and hashes.

The result and user approval support the prepared scoped PR. Human-owned T107
stays under human control; its checkbox remains unchanged. Closing upstream #84 additionally requires maintainer agreement on the
registration-key patch's scope or implementation of the remaining public identifier
and discovery design. Agent review and successful native execution cannot supply
those engineering decisions.
