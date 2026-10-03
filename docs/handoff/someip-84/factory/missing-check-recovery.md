# Selected missing-check recovery, 2026-10-03

Latest observation: the selected collectors have finished. Native run
`01M4082KVKZ7DE1D4KSBEEJE0C` stopped at an unanswered human-gate timeout at
08:25 Lisbon; no worker remains. Docs, traceability, native Clang-Tidy and benchmarks
have exit code zero. C++ formatting has substantive violations; profiling fails
because perf events are denied (`perf_event_paranoid=4`); integration still cannot
resolve cloud-localds inside Bazel's build environment, despite its installed entrypoint
and passing standalone seed-image smoke. Integration executed zero of six tests.
[Latest terminal evidence](runs/score-someip84-recheck-blfnwq7c/terminal-status.json)
and [command outcomes](runs/score-someip84-recheck-blfnwq7c/verification-outcomes.json)
retain these measured results.

The infrastructure observer replaced the initial selected run once, repeating the
same selected set, including its passing commands. It did not execute the full queue.
The next observer refused another repair after native events confirmed a human-gate
timeout with no default. Engineering acceptance remains pending. The original scoped
startup and intermediate observations below remain historical evidence.

The user authorized cloud-localds installation and disposable Git metadata repair,
then narrowed execution: "be sure to not run everything again, just want is missing".
Native run **`01M405PNQN7DWH4H7VNNZSDC8G`** was observed running at 07:05 Lisbon,
with a live worker, ready supervisor and pinned network-disconnected container.
[Startup evidence](runs/score-someip84-recheck-fpsmfu3g/restart-status.json) binds
the selected commands, actual native run, container and prepared root.

The selected docs command and traceability gate have since completed with exit
code zero. [Docs evidence](runs/score-someip84-recheck-fpsmfu3g/native_docs-result.json)
and [traceability evidence](runs/score-someip84-recheck-fpsmfu3g/native_traceability-result.json)
retain the actual Git identities, command results and remaining review limitations.
The other selected measurements are still pending.

| Selected measurement | Previous obstruction | New command bound |
| --- | --- | --- |
| Native docs | No Git remote in collector copy | 1,800 seconds |
| Traceability gate | Docs/metrics unavailable or stale | 300 seconds |
| Formatting | Command timeout | 1,800 seconds |
| Native Clang-Tidy | Command timeout during nested Bazel work | 1,800 seconds |
| Benchmarks and profiling | Command timeouts | 1,800 seconds each |
| QEMU integration | Missing cloud-localds; guest build/boot timeout | 3,600 seconds |

Only these commands and a result-report stage are in the deterministic workflow.
There are no implementation-agent stages or model smoke calls. The shared native
workspace and public archive cache are reused within the new run; command-specific
build prerequisites can still execute. Passed native/focused tests, build,
sanitizers, coverage, cross-compilation and Ruff are not explicitly rerun.
Pre-commit, REUSE, module tidy and lockfile commands are omitted from the formatting
group. Traceability omits its previously passing unit/component tests. CodeQL,
Cppcheck, Gitleaks and focused TSan findings remain preserved without re-execution.

Cloud-image-utils `0.32-22-g45fe84a5-0ubuntu1` and genisoimage
`9:1.1.11-3.2ubuntu1` were extracted from checksum-verified Ubuntu packages on the
bound SSD Linux filesystem. Package downloads and license notices remain in that
installation. A real cloud-localds smoke created a 374,784-byte seed image with exit
code zero. [The frozen queue tool manifest](runs/score-someip84-recheck-fpsmfu3g/queue-tools.json)
retains original and supplementary identities/storage bindings; older installations
and previous queue manifests were not changed. Credentials and private server state
remain on internal storage.

The new disposable Git bundle comes from public history for the locked
`eclipse-score/inc_someip_gateway` commit
`f8a196c3b16d5172d898394ab99b0ed81346d63d`, tree
`826a77c2f3ec0838f37230319f9397e442cef407`. Collector Git initialization, fetch,
mixed reset and remote restoration completed successfully; measured HEAD/tree
match that real baseline. Hooks are disabled and candidate worktree changes remain
uncommitted against the actual baseline. Reference checkouts and source locks are
unchanged. No fabricated engineering commit is introduced.

Supervisor admission initially encountered a stale server PID: an earlier observer
had restored a listener while the dedicated persistent service retried its occupied
port. Both preceding queues were verified terminal with no workers. Their observers
were stopped, the exact owned idle listener was replaced by the existing dedicated
persistent service, and the already submitted native run was started once.
[Reconciliation evidence](runs/score-someip84-recheck-fpsmfu3g/server-reconciliation.json)
records the preserved run identity; no duplicate run was submitted.

The preceding full run `01M3ZRSDK2XQAF1H48VWTPKQNZ` reached human review and timed
out without an answer. Its [native terminal observation](runs/score-someip84-factory-oicrb03_/terminal-status.json),
[measured report](runs/score-someip84-factory-oicrb03_/verification-report-result.json)
and [command outcomes](runs/score-someip84-factory-oicrb03_/verification-outcomes.json)
remain retained. Existing agent reports are drafts; deterministic tool outputs govern
measurement claims. Remaining licensed/platform limitations and substantive findings
are not cleared by installing tools or collecting new results.

Validation: 70 relevant contract tests passed, one native-environment test skipped;
Ruff, mypy (122 source files), foundation consistency and package build passed.
Selective-command tests verify passing commands stay omitted, timeout bounds reject
before launch, real Git metadata preserves dirty candidate source, and supplementary
tool-volume disconnection refuses execution. This is operational verification, not
engineering acceptance. T100's selected collection is complete; all human reviews
and the remaining verification failures remain open.
