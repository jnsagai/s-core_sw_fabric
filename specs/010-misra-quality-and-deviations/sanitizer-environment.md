# Native ASan runtime environment blocker

2026-10-01, Lisbon. Native settings and reference inputs remain unchanged.

## Latest normal-terminal checkpoint (2026-10-01)

The user ran [the host validation script](../../scripts/validate_asan_host.sh) outside the
restricted agent sandbox. Original ASan capability succeeds, the seeded source reports one
`heap-buffer-overflow` finding, and a fresh corrected source reports zero findings with adequate
scope. [Three native integration checks](evidence/asan-host-20261001/integration.log) pass in
**2.61 seconds**: seeded/fresh-fix, correction/history and original-output import.

Original host records and logs are preserved under [host evidence](evidence/asan-host-20261001/status.txt):

| Measurement | Sealed digest | Native outcome |
| --- | --- | --- |
| [Capability](evidence/asan-host-20261001/capabilities.json) | `1dcad258bc911218e0fcc9c8509b1ea8b8a08212bb4ea6820edec7307c078081` | completed; clean runtime exit 0 |
| [Seeded](evidence/asan-host-20261001/seeded.json) | `4714c083ba31447e1c29b35eabbb669dff912419bf9d212ceff36122025f8a18` | findings; requested runtime exit 55 |
| [Corrected](evidence/asan-host-20261001/corrected.json) | `0a175a5c62fc7247d2c1434ddc8f0074e1f0b9920cc89f07233dcf303832337a` | completed; requested runtime exit 0 |

Selected compiler/runtime/configuration identities and native flags/suppressions remain unchanged.
Original raw capture counts/hashes, all phase exits, native LeakSanitizer failure checks and fresh
source digests are independently checked by [the verifier](../../scripts/verify_asan_host_records.py).
This is local unprotected execution, with no engineering acceptance or qualification upgrade.

The host script then stopped on Ruff errors in the new helper/tests while they were being
completed. [Original failed Ruff log](evidence/asan-host-20261001/ruff.log) is retained. Formatting
and import sorting are corrected, and current Ruff checks pass. The resumed [full host validation](asan-host-validation.md) passes 1,773 tests with 13 documented
external/native skips and zero failures, plus all static/frozen/foundation/build gates.

A fresh agent-sandbox capability probe still fails at LeakSanitizer thread attachment, digest
`038b5b02f38a6ece9f8b285b23d23387891f315243d56ee5a57dce720e780e48`.
[Original sandbox measurement](evidence/asan-resumed-sandbox-capabilities.json) stays incomplete.
The successful host measurements supersede the earlier lack of an available native runtime;
they do not make the restricted agent sandbox compatible. Historical failed gates below remain
unaltered. T008/T030/T081 are complete after the full compatible-host gate; human tasks remain unchecked.

## Historical failed validation gate

The complete regression run after the sandbox permission change ended with **1,413 passed,
11 skipped and three failed**, 197.20 seconds. Failures are the existing ASan seeded/fresh-fix,
disposition correction/history and genuine native import tests. T030 remains unmet.
Prior complementary execution evidence remains historical; it does not establish capability
in the current environment. UBSan, Cppcheck and Clang-Tidy are separate selections.

A bounded diagnostic capability probe and requested run each retained original phases. Version,
compile and link exit 0; the clean runtime probe exits 55 and reports:

```text
Could not attach to thread (errno 1).
Failed suspending threads.
LeakSanitizer has encountered a fatal error.
HINT: LeakSanitizer does not work under ptrace (strace, gdb, etc)
```

This is native evidence of an interrupted LeakSanitizer runtime in the restricted sandbox;
the ptrace hint is preserved as a diagnostic, not a qualified platform determination.
The requested seed is never analyzed after the failed clean capability probe.
[Original capability/run records](evidence/asan-restricted-runtime.json) retain full stderr,
compile/link commands, selected runtime/compiler hashes and source baseline. SHA-256:
`c9d735453cd44892b8bd032790bbf78b8d3f68b0e08b72729a43b28787895240`.
Both commands exit 1 with incomplete outcome and unknown/incomplete scope as appropriate.
The diagnostic harness exited 0 because it successfully collected those failures; that exit
is not a passing analyzer result.

## Implementation correction

Four contract cases failed before implementation: a native LeakSanitizer fatal error could
otherwise be accepted when the process returned 0 without a finding or 55 with an ASan finding.
The adapter now retains `LEAK_SANITIZER_RUNTIME_FAILED` and `SANITIZER_RUNTIME_INCOMPLETE`
regardless of those exit/finding combinations, plus `LEAK_SANITIZER_PTRACE_UNSUPPORTED` when
that exact native hint is present. Findings and original stderr remain preserved; processed
units remain empty. All **13 complementary contract tests pass** after the correction.
One diagnostic collection confirms both actual incomplete records carry the new named gaps.
Fixtures verify failure interpretation only; they cannot satisfy native execution acceptance.

No runtime flag, suppression, native template or sandbox setting was altered. No retries are
added. The current environment does not permit requesting elevated execution. A compatible
native runtime environment is required to rerun the original ASan integration gate.

## Validation command and exclusions

The full command is recorded in [CodeQL slice verification](codeql-prerequisites-acceptance.md).
Three native Fabro compiler tests were excluded because that runtime is not selected. Eleven
existing external/native tests skipped. The three ASan failures were retained and not skipped.
Other foundation/build/static gates are recorded separately; none clears this failed runtime gate.
