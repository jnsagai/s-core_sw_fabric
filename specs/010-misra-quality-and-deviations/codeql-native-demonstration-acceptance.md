# Increment 010: genuine CodeQL software demonstrations

2026-10-01, after the user's [resumption instruction](../../docs/handoff/010-resumed-approval.md).
Full increment acceptance remains pending. These measurements exercise the installed tools
using fixed synthetic C++, under the publisher's software-demonstration permission. They do
not establish target-project eligibility, tool qualification or authenticated engineering decisions.

**Later checkpoint:** the user installed Python 3.9.25 and the pinned packages.
[Installed reporting validation](codeql-python39-reporting-acceptance.md) supersedes the missing
interpreter status below, while retaining the original failures and demonstration outputs.

## Implemented component and actual measurements

The [internal phase contract](contracts/codeql-native-phases.md) precedes the pure
`quality/codeql_native_phases.py` implementation. It constructs bounded native argument lists
and validates independent extracted-file string/URL pairs against selected disposable sources.
It performs no execution or host reads. The public `--adapter codeql` interface remains a
prerequisite inspector; full execution integration T011/T012/T078/T079 remains open.

The retained [measurement program](evidence/measurement-scripts/native_codeql_demonstration.py)
executes the installed CodeQL 2.21.4 CLI, GCC 11.4 and compiled MISRA 2.61.0 default suite.
Each demonstration creates a fresh disposable database and isolated HOME/cache, runs version,
initialization with selected scan configuration, traced compilation, finalization, queries and
separate original SARIF/CSV interpretation. All seven core phases exit 0. Original diagnostic
queries independently measure extraction; query source hashes, raw BQRS decode output, raw
SARIF/CSV, exact source bytes and pre/post identity checks are retained. No project hooks run.

| Measurement | Native findings | Independent extraction |
| --- | --- | --- |
| [Seeded unused variable](evidence/codeql-native-demonstration-seeded.json) | 3 | `check.cpp`, no extraction errors |
| [Fresh corrected source](evidence/codeql-native-demonstration-corrected.json) | 0 | `check.cpp`, no extraction errors |

The seeded rule IDs are `cpp/misra/avoid-standard-integer-type-names`,
`cpp/misra/unused-limited-visibility-variable` and `cpp/misra/unnecessary-write-to-local-object`.
Record digests are respectively
`d6df4c1e123dd94a67de2713e27a808935093ac242dd3398694370305dca7638` and
`8576f8761eab6f2e439c381a55b11cfefd9f1d41d9754e0047d6d4451f382a17`.
The [earlier projection failure](evidence/codeql-native-demonstration-extraction-failure.json)
preserves successful native phases and raw output: our initial relative-path assertion was
wrong. Native CodeQL emits absolute paths. The corrected projection checks those paths and
their independent URL/position fields against the disposable source root and selected files.

These sealed measurement records are reproduction artifacts, not public quality request/run
schemas or accepted evidence. Their embedded prerequisite inventories retain all fourteen
gaps. No finding is marked accepted or corrected in an engineering disposition.

## Native reporting and runtime limits

Both demonstrations explicitly omit `configuration:convert`, `configuration:index` and
`native:report`. Initialization retains selected scan filters, but the publisher's Python/XML
configuration path and Python report pipeline have not executed. A clean SARIF does not prove
complete reporting, audit/default-disabled coverage, applicability or MISRA compliance.

The user explicitly authorized Python 3.9 installation. `uv python install 3.9` selected
CPython 3.9.25; the workspace-local attempt failed with exit 1 because GitHub DNS could not
resolve. The [original failure log](evidence/python39-install-after-user-approval.txt) is retained.
The destination was ignored `.tools/python`, cache `/tmp/s-core-quality-uv-cache`, with
`UV_HTTP_RETRIES=0`, `--no-config --no-progress`. No Python 3.9 interpreter was installed.
The enforced network restriction cannot be changed by a conversation approval. An accessible
local installation archive or compatible connected execution environment is needed.

A fresh [ASan capability probe](evidence/asan-after-user-approval.json) still fails its runtime
with exit 55 and fatal LeakSanitizer thread-attachment errors. Version/compile/link phases
succeed. Original native flags and suppressions remain unchanged; the full ASan gate stays failed.

## Verification

Negative tests preceded the phase builder and extracted-unit projection. The new module has
35 passing contract cases covering bounded pure construction, unsafe paths/arguments, missing
or incompatible reporting, and malformed/contradictory extraction identities.

```bash
UV_CACHE_DIR=/tmp/s-core-quality-uv-cache uv run --frozen pytest tests/contract/test_quality_codeql.py tests/contract/test_quality_codeql_record_types.py tests/contract/test_quality_codeql_native_phases.py tests/contract/test_quality_installed_context.py -q --tb=short
```

Initial result: **214 passed, 3.48 seconds**; final repeated focused verification: **214 passed,
4.12 seconds**. Ruff/check/format (480 files), mypy (114 source files), foundation consistency
and offline sdist/wheel build pass. Retained record seals and original artifact hashes were
independently verified after copying to repository evidence. The historical full gate remains **1,682 passed,
11 skipped, three ASan failures**; focused checks do not replace it. Task count remains
**70/84 complete, 14 open**. Human T032/T082, 009 T018 and protected 005 T009 remain unchecked.
