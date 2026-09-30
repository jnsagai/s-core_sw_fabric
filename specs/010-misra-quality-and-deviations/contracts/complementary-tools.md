# Cppcheck and GCC sanitizer adapter contract, version 1

This extends the local 010 slice with explicit `--adapter cppcheck|asan|ubsan` selections on
`quality capabilities` and `quality run`. Default `clang-tidy` keeps its original version 1
requests. No full import/packet/assessment or MISRA compliance interface is implemented here.

## Exact selections

Each adapter requires its own `quality_<adapter>_capability_request` or
`quality_<adapter>_run_request`, with the same exact control/source fields and bounds as the
[Clang-Tidy contract](clang-tidy.md). CLI adapter and request kind must match. Combined/unknown
selectors are rejected; ASan and UBSan are executed separately. This does not claim that their
combination is a native incompatibility. Native ASan/TSan and ASan/TySan exclusions remain source facts.

New toolchain kinds are `quality_cppcheck_toolchain_profile` and
`quality_sanitizer_toolchain_profile`, with `id`, `status`, `tool`, `dependencies`, `library_dirs`
and the same strict version 1 envelope. Dependencies include selected compiler helpers/runtime
assets, standard-library configuration and license notices, rather than only shared libraries.
Clang-Tidy's original library-dependency restriction remains unchanged.

Cppcheck configuration exact fields: `id`, `status`, `standard`, `language`, `enable`,
`platform`, `max_configs`, `error_exitcode`, `xml_version`, plus
`schema_version: 1`, `kind: quality_cppcheck_configuration`. This slice supports C++17/C++,
unix64, 1–12 preprocessor configurations, error exit 2, XML v2 and only the locally researched
warning/style/performance/portability/information/missingInclude categories. This is an explicit
local complementary configuration, not a native MISRA policy. No addon, clang parser, project
file, inline suppression, external library selection, arbitrary flags or commands are accepted.

Sanitizer configuration exact fields: `id`, `status`, `mode`, `feature`, `native_features`,
`native_runtime`, `native_suppressions`, with `schema_version: 1`,
`kind: quality_sanitizer_configuration`. The three native refs are `{path, sha256}` selections,
matching `sanitizer_features`, `<mode>_runtime` and `<mode>_suppressions` profile source hashes.
Mode is `asan` or `ubsan`; feature is respectively `asan` or `ubsan_gcc`. Compiler/link flags
are extracted from the native `cc_args` declarations; debug_symbols is selected through the
native feature implication. Native environment-template options are rendered with the isolated
suppression-file path. Every byte/hash and rendered environment/argument list is retained.
Noncomment suppressions remain pending scope/justification review and block execution in this
slice. No blanket LSan/GoogleTest/Rust suppression inheritance is used.

## Execution and results

Both modes reuse strict source freezing, bounded outputs, timeouts, guarded publication and
independent expected/processed-unit checks. Builds use only fixed compiler/assembler/linker
invocations; source/project hooks are not executed. Sanitizers build each declared translation
unit then link and execute one component binary without caller-supplied runtime arguments.
Capability probes build/link/execute a clean synthetic program; library presence alone is not
an available runtime. Build failure, timeout, unknown runtime exit, missing/incomplete report,
truncation or unresolved suppression makes the affected result unavailable/incomplete.
Native exit 55 plus a retained diagnostic is a sanitizer finding; runtime 0 without diagnostics
is a completed local run. Diagnostic text/native category, source locations where resolvable,
all raw logs and generated binary identity are retained. Fatal runtime signals without a useful
native report are incomplete runtime evidence, not a named source defect.

Cppcheck preserves XML v2, native error ID, severity, CWE and every primary/related location.
Missing includes, syntax/internal errors and insufficient configuration checking block adequate
clean evidence. Zero findings cannot override empty/partial/unknown source processing.

New output kinds are `quality_<adapter>_capability_inventory` and
`quality_<adapter>_analysis_run`. Exact outer fields match the earlier records, with configuration
`{path, sha256, adapter, effective}`. Run adds baseline, processed_units, extraction, diagnostics,
source_integrity. Artifacts preserve native format, total bytes, full-stream/prefix digests,
bounded base64 and truncation, together with artifact ID/translation-unit reference. Build
binaries are hashed; their artifact is labelled generated binary identity, not native SARIF.

Exits: 0 completed local capability/analysis; 1 findings/unavailable/incomplete; 2 rejected
input or identity drift with prior output preserved. All records remain
`local_unprotected_execution`, `not_eligible`, readiness `not_evaluated`. MISRA mapping,
CodeQL eligible execution, manual review and protected authority remain unresolved gaps.
