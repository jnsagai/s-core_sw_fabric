# SOME/IP queue: stopped at human review

Run `01M3YRJEGXNY6CB81T7TKW774B` completed 93 workflow stages, including the review
packet and verification report. The human gate timed out without an answer at
**19:56 Lisbon, 2026-10-02**. Native status is `failed/workflow_error`; the worker
has exited and no successor is running. Engineering acceptance remains pending.

**Verification did not all pass.** Final focused GCC/UBSan measurement passed
87 tests with no failures. Focused ASan/LSan passed. Focused production coverage
was 100% lines and 78.6% branches, with incomplete target scope. Full native
build/tests/integration could not run because Bazel still referenced a missing
`/tmp` installation. Clang compilation, native Clang-Tidy configuration, Cppcheck
and TSan failed; CodeQL retained findings and MISRA applicability blockers.
Other checks retained missing-tool and human-review blockers. Collection-stage
success records execution/result retention rather than passing verification.

[Terminal observation](runs/score-someip84-factory-2fekt_ew/terminal-status.json),
[measured verification report](runs/score-someip84-factory-2fekt_ew/verification-report-result.json),
[check outcomes](runs/score-someip84-factory-2fekt_ew/verification-outcomes.json) and
[final focused measurement](runs/score-someip84-factory-2fekt_ew/focused-final-measurement.json)
retain the current result. Original startup and failed-attempt records remain below.

## Supervisor recovery startup observation (historical)


Observed 2026-10-02T16:54:40.717042+00:00. Run `01M3YRJEGXNY6CB81T7TKW774B` is **running**,
using DeepSeek Flash/high, no fallback, all declared obligations, one complete pass
and no clock cutoff. Engineering review and acceptance remain pending.

The previous run `01M3YGTGYFEN406VDEVVTJTRWV` completed 40 workflow stages before
its supervisor's full-history read crossed the 4 MiB limit and triggered cancellation.
Recovery then blocked while the worker was still exiting. Native terminal state and
worker absence are now reconciled. The latest six candidate source files, 12 current
draft reports and 13 older reports remain preserved in the owned snapshot.

The supervisor now uses native compact status and pending-question endpoints,
retaining the read bound and human-gate checks. Cancellation recovery requires both
terminal native state and worker exit, allowing up to 120 seconds for settlement.
The actual oversized predecessor passed a corrected observer check without repair
dispatch. Ruff, mypy, 91 contracts (one skip), foundation and package build passed.

Prepared root: `/media/jefferson/11c42dee-73a3-4c2b-ab42-a0440011d9e0/.s-core-build/runs/score-someip84-factory-2fekt_ew`.
Current worker, pinned network-disconnected container, fresh observer receipt and
enabled/active server and observer services were verified. The predecessor's frozen
package, failed incident and blocked recovery records remain unchanged.

[Current restart evidence](runs/score-someip84-factory-2fekt_ew/restart-status.json),
[preserved work](runs/score-someip84-factory-2fekt_ew/preservation.json),
[frozen workflow](runs/score-someip84-factory-2fekt_ew/workflow.fabro) and
[repair validation](../../../../specs/010-misra-quality-and-deviations/runtime-recovery/acceptance-observer-reads.md).

## Reboot recovery observation (historical; subsequently cancelled)


Observed 2026-10-02T14:42:39.232655+00:00. Run `01M3YGTGYFEN406VDEVVTJTRWV` is **running**,
using DeepSeek Flash with high reasoning, no fallback, one complete pass and no
clock cutoff. Human engineering review and acceptance remain pending.

The reboot cleared the original server checkpoints and executable from `/tmp`.
This is a fresh supervised successor of `01M3XZAQ65TTE35XSGXC4JAMAH`, using its
preserved candidate source and 13 draft reports. Exact checkpoint continuation
was unavailable. The pinned runtime was rebuilt on bound SSD storage; its executable,
private server state and enabled user services now live on persistent internal storage.

Prepared root: `/media/jefferson/11c42dee-73a3-4c2b-ab42-a0440011d9e0/.s-core-build/runs/score-someip84-factory-mfwqxi3a`.
Native worker liveness, the exact pinned network-disconnected Docker container,
current supervisor receipt and both enabled/active services were verified.
The failed pre-agent startup `01M3YGBHTTM3NCGTMYAN76363M` is preserved; its missing
`/usr/sbin` server PATH was corrected and storage validated before this successor.

[Restart evidence](runs/score-someip84-factory-mfwqxi3a/restart-status.json),
[recovery lineage](runs/score-someip84-factory-mfwqxi3a/recovery-provenance.json),
[frozen workflow](runs/score-someip84-factory-mfwqxi3a/workflow.fabro) and
[recovery validation](../../../../specs/010-misra-quality-and-deviations/runtime-recovery/acceptance-reboot.md).

## Pre-crash startup observation (historical)


Observed 2026-10-02T09:38:10.341857+00:00. Run `01M3XZAQ65TTE35XSGXC4JAMAH` is **running**, using DeepSeek Flash
with high reasoning and no fallback. One complete pass covers all obligations,
correction/recollection and review drafts; no overall clock cutoff is set.
Human engineering review and acceptance remain pending.

Prepared root: `/media/jefferson/11c42dee-73a3-4c2b-ab42-a0440011d9e0/.s-core-build/runs/score-someip84-factory-b2_8i2fs`.

Native worker PID `785832` and owned network-disconnected container
`506777c061a6` are present. Latest native stage references: scope, start, invariants, callsites.
Prior implementation and draft reports are preserved. Build scratch uses the same
SSD ext4 image through its verified kernel mount. Private native state and credentials
remain internal. Other Fabro queues were not changed.

[Current workflow SVG](current-workflow.svg),
[expanded workflow SVG](current-workflow-expanded.svg),
[restart status](runs/score-someip84-factory-b2_8i2fs/restart-status.json) and
[frozen workflow](runs/score-someip84-factory-b2_8i2fs/workflow.fabro).

## Previous restart: failed before tool collection

Run `01M3XT7NQ04S4MTFRMTT2401XK` failed at 09:51 Lisbon. Docker workspace extraction failed
on read-only runtime Git objects; collectors could not execute their tools.
Source and reports were recovered. Subsequent coverage probes exposed repeated FUSE
write/connection failures. Offline filesystem checks found no structural inconsistencies.
The preserved image now uses a kernel ext4 mount; no SSD partition was formatted.

The corrected shared archive transfer and actual kernel-mounted collectors were
verified before restart. GCC compilation/tests passed; Clang compilation failed.
Focused production coverage is 77.8% line / 64.3% branch. Process applicability,
independent reviews and acceptance remain pending. Ruff, mypy, 46 relevant contracts,
foundation consistency and package build passed.

[Previous failure and preserved startup observation](runs/score-someip84-factory-eimdgfek/restart-status.json).

## Previous stalled run


## Morning status: stalled; container stopped

Observed 2026-10-02T07:52:16.042312+01:00. Fabro retains a stale `running` state; its last event
was at **02:07 Lisbon** and the launch worker is no longer present. Native cancellation
returned HTTP 409 (`Run is not cancellable`). Only the exact owned container was stopped;
its workspace remains at `/tmp/score-someip84-factory-81ibm9qq/cutoff-workspace`. No native database status was rewritten.

Focused GCC tests, ASan/LSan/UBSan and Memcheck passed. Latest focused production coverage
was **77.8% line / 64.3% branch**. Full native builds/tests did not pass: LLVM extraction
hit `No space left on device`. TSan had a runtime mapping failure; Clang/native analyzer
configuration and other checks have unresolved failures. Raw CodeQL output includes
dependency findings and requires triage. Final review/report stages were not reached.
Engineering acceptance remains pending.

[Morning evidence](runs/score-someip84-factory-81ibm9qq/morning-status.json).

## Previous startup observation


Status: **Fabro running**, observed at 00:34 Lisbon on 2026-10-02.
Run: `01M3WX09X84XFM5X08QY2944DF`. Cutoff: **07:00 Europe/Lisbon, 2026-10-02**.

Root: `/tmp/score-someip84-factory-81ibm9qq`.

The expanded workflow has **99 nodes**: 38 implementation/review/repair drafts,
four conditional correction agents, 54 deterministic collection/recollection/progress
nodes, start, human gate and exit. DeepSeek Flash uses high reasoning with no fallback.
No additional spending/rework cap is set; the native ceiling and deadline apply.

[Full obligations, work items and correction routes](runs/score-someip84-factory-81ibm9qq/QUEUE.md)
include coverage, MISRA, analyzers, native build/regression, sanitizers, integration,
performance, cross compilation, repository hygiene, security, traceability, tool
assurance, inspections and review/report drafts. Actual deterministic tool failures,
missing capabilities, unknown applicability and human decisions remain explicit.
Successful collection never implies successful verification or acceptance.

The original run was cancelled and its workspace retained. A startup attempt was
also cancelled before collectors ran to correct its traceability path. The current
run's Docker ownership, pinned image and disconnected networking are verified.
It can finish drafting or stop for human review before 7 AM; no review is answered
automatically.

[Live observation](runs/score-someip84-factory-81ibm9qq/live-observation.json) and
[workflow verification](runs/score-someip84-factory-81ibm9qq/verification.json) preserve the evidence.
Broad collector execution and live deadline expiry have not yet been observed.
Engineering acceptance remains pending.
