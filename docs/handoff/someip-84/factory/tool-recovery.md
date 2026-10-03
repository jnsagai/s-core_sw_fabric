# SOME/IP tool installation and queue restart

User authority, 2026-10-03: install all missing tools from the failed SOME/IP queue,
then run the queue again to address verification issues. This is bounded operational
work within increment 010. Engineering review and acceptance remain pending.

Run **`01M3ZRSDK2XQAF1H48VWTPKQNZ`** is running with DeepSeek Flash/high, no fallback,
one complete all-obligations pass and no clock cutoff. The native worker, fresh
supervisor heartbeat and pinned network-disconnected Docker container were measured.
See [startup observation](runs/score-someip84-factory-oicrb03_/restart-status.json).
The queue has 38 draft tasks and 54 measurement tasks. Final verification is pending.

## Installed tools and storage

| Tool | Installed version |
| --- | --- |
| Bazel | 8.6.0, matching the target `.bazelversion` |
| Valgrind | 3.18.1, Ubuntu Jammy package `1:3.18.1-1ubuntu2` |
| pre-commit | 4.6.2 |
| REUSE | 6.2.0, matching the repository hook |
| clang-format | 19.1.7, complementary local installation |
| Gitleaks | 8.30.1 |

All six version probes and a real Valgrind runtime smoke passed. Bazel and Gitleaks
release binaries and the Valgrind package were checked against published checksums.
Python packages were installed in a dedicated Python 3.12.14 virtual environment;
all resolved versions, package license files and native package notices remain in
the installation. Native Bazel formatting/toolchains retain the target's own pins;
the local formatter does not replace its LLVM 22.1.7 configuration.

`score-fabric storage` measured and selected the registered kernel ext4 image on
the external Lexar SSD. Tools live in
`/media/jefferson/11c42dee-73a3-4c2b-ab42-a0440011d9e0/.s-core-build/runs/score-someip84-tools-0ptca_j_`.
The new queue lives beside it in `score-someip84-factory-oicrb03_`. Each has its own
bound storage selection. Credentials and private Fabro state remain internal.
Global tool storage and reference repositories were not changed.

The internal pointer `~/.config/s-core/someip84-tools.json` is consumed only when
preparing new queues. Each successor freezes its manifest in `queue-tools.json`
and seals it in the operational dependency overlay. Admission and every collector
command validate the tool volume and 823 measured identities, including Python
package source, formatter binary and Valgrind runtime files. Missing, changed,
escaping or disconnected tools stop execution. Historical frozen scripts remain
unchanged. The legacy paths remain only for unfrozen historical/test imports.

[Download records](runs/score-someip84-factory-oicrb03_/tool-downloads.json),
[installation smoke](runs/score-someip84-factory-oicrb03_/installation-smoke.json),
[frozen tool identities](runs/score-someip84-factory-oicrb03_/queue-tools.json) and
[recovery lineage](runs/score-someip84-factory-oicrb03_/tool-recovery-provenance.json)
retain the measurements.

## Verification and preserved work

The previous run `01M3YRJEGXNY6CB81T7TKW774B` is natively
`failed/workflow_error`, with no live worker. Its exact stopped container was copied
without runtime Git metadata; the six candidate files match the preserved hashes.
All 38 current reports were copied into the successor's prior reports. The earlier
12 reports and all original failure evidence remain in the predecessor workspace.
The source correction stays with Fabro's bounded target agents; no human question
was answered and no engineering decision was accepted.

The focused diagnostic harness now compiles GoogleTest objects separately, keeping
dependency warnings in their original logs. `-Werror` remains on production and
regression translation units. This resolves the measured Clang/libstdc++ dependency
deprecation failure without changing the target or suppressing its diagnostics.
Fresh GCC 12.3 and Clang 19 runs each pass **87 tests, zero failures**.
[Compiler commands](runs/score-someip84-factory-oicrb03_/compiler-preflight.json) and
[Clang test results](runs/score-someip84-factory-oicrb03_/clang-tests.json) retain scope.
Fresh [focused Memcheck](runs/score-someip84-factory-oicrb03_/memcheck-preflight.json)
also passes. These are local measurements, not protected acceptance evidence.

The native Bazel preflight now builds and tests the actual BUILD target
`//score/socom/test/unit:socom_test` successfully with the target's pinned LLVM
toolchain: **685 test cases, zero failures/errors, 0 skipped**.
See [native result](runs/score-someip84-factory-oicrb03_/native-preflight-result.json)
and [original JUnit](runs/score-someip84-factory-oicrb03_/native-unit-test.xml).
The first attempt used an undeclared test label and failed; original and corrected
commands/output are preserved in the run evidence. The full repository
build/test/sanitizer/coverage/integration results still require the queue's
collection and correction stages. This preflight binds the preserved predecessor
candidate, before the successor's agents make further changes.

Ruff, strict mypy (122 source files), 96 affected contracts with one intentional
skip, foundation consistency and package build passed. After the diagnostic
harness change, 19 directly affected contracts with one skip, Ruff and foundation
consistency passed again. Negative tool tests cover changed bytes, missing
identity, symlink escape, disconnected storage and frozen registration isolation.

Existing analyzer findings, native Clang-Tidy configuration incompatibility,
TSan runtime failure, MISRA applicability and human reviews remain obligations
for the new run. Coverity and QNX cannot be supplied by installing an unlicensed
or unconfigured SDK; their entitlement/adoption blockers remain explicit.
