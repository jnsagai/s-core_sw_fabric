# Native CodeQL command construction (010)

This internal adapter component constructs bounded argument vectors from already selected,
frozen inputs. It executes no process and makes no eligibility or engineering decision.
The public prerequisite mode remains unchanged until the full execution gate is implemented.
T011/T012/T078/T079 remain open; this component supplies their verified native command recipes.

## Inputs and bounds

`commands` accepts the declared CodeQL executable, GCC toolchain, compiled pack root, native
suite, disposable source/database/work paths, explicit units/includes/defines, frozen scan
configuration, copied native reporting-source root, nullable reporting toolchain, per-phase
timeout and resource selections. Toolchains use the existing exact schemas; construction is
pure and does not probe their host paths. Live callers must verify identities and permissions,
copy exact selected bytes and inspect hooks before execution, then refreeze all inputs.

Paths are absolute lexical paths without traversal, control characters or option-shaped
components. Units/includes are unique safe relative paths, units are `.cpp`/`.cc`/`.cxx`;
at most 500 units, 32 include directories and 64 identifier/integer defines. The suite is an
explicit `codeql-suites/*.qls` filename. Timeout is integer 1–3600; threads integer 1–32 and
query memory integer 1024–8192 MiB. No shell string, build command, arbitrary query, retry or
automatic download is accepted. GCC compile arguments are owned by the adapter.

## Derived commands

Every item contains exactly `name`, `argv`, `timeout_seconds`, `state`, `reason_codes`.
State is `planned` with an argument list, or `unavailable` with null argv and a named missing
reporting prerequisite. These are command construction states, never execution outcomes.

Commands retain separate version, database-init, configuration conversion, XML indexing,
per-unit traced compilation, database-finalize, query execution, SARIF interpretation,
CSV interpretation and native-report phases. Configuration conversion uses the original
processor's `--skip-indexing --save-temps`; indexing runs separately so its failure cannot
be swallowed by that processor. The original scan configuration is selected at initialization.
Native suite and scan filters/exclusions remain explicit in the selected controls.

The full compiled pack/version/suite selector is
`codeql/misra-cpp-coding-standards@2.61.0:<selected suite>` with its explicit search path.
Reporting uses the copied `scripts/reports/analysis_report.py` and the source's stated Python
3.9 toolchain. Missing reporting leaves both Python phases unavailable. Construction never
substitutes another interpreter or marks native reports complete.

CLI syntax is verified against the installed 2.21.4 help, the pinned `time` wrapper and
real approved software-demonstration version/init/trace/finalize/query/SARIF commands.
All phases still require the caller's eligibility, source/pack/runtime/reporting checks.
No generated command is a scheduled job, accepted artifact or automatic approval.

## Reproduction program with installed reporting dependencies

The separate software-demonstration program may select an explicit `--reporting-profile`.
It validates the existing reporting-toolchain schema, freezes its bytes and selected assets,
and independently probes Python 3.9, PyYAML 5.4 and pytest 7.2.0 before native work. A regular
copy of the interpreter in its virtual environment avoids selecting symlink paths; original
installation bytes remain intact. Selected assets are an observed subset, not a qualified
runtime closure. The primary prerequisite configuration remains unchanged.

With that selection, the program copies reviewed Git-blob-verified configuration/report/shared
scripts, report queries, supported-version configuration and original LICENSE to the disposable
tree before execution. It creates a labelled demonstration configuration containing only
`report-deviated-alerts: true`; no deviations, permits, recategorizations or approvals are added.
Generated YAML/XML bytes are retained, and XML indexing runs as a separate native phase.
The original reporting script executes after independent extraction checks; every existing
native Markdown report is captured before a failing reporting status is propagated. Such a
failure cannot become a complete or clean report. Earlier evidence is never overwritten.

An explicit reproduction-only `--apply-report-patch` option requires the reporting profile.
It copies the already selected, hash-frozen `time` report patch into disposable work. Separate
plain `git apply --check`, `git apply --recount --check` and `git apply --recount` phases retain
the original malformed-hunk refusal and explicit recount transformation. Only copied
`scripts/reports/utils.py` may change; original and transformed hashes and bytes are retained.
All other copied source identities and the original reference source are checked again.
This is a local transformed demonstration variant, not native Bazel patch compatibility,
publisher authentication, runtime qualification or a changed reviewed upstream baseline.

## Independent extraction entities

`extracted_units` consumes the original two-column string/URL CSV from the pinned
`SuccessfullyExtractedFiles.ql`. Native file strings are absolute, rather than assumed relative.
Both the native path and file URL must identify the same selected file in the disposable
source root. Each URL retains its four native position fields. At most 500 unique rows are
accepted; malformed URLs, outside/unselected paths, duplicates and contradictory entities
refuse. Only observed expected translation units are returned; headers remain in the raw
original rows. This projection alone confers no adequacy or engineering acceptance.
