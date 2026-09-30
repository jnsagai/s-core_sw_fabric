# Increment 010: Clang-Tidy slice validation

2026-09-30. Implemented for local complementary use. Full increment 010 is incomplete;
engineering acceptance remains pending and human-owned T032 is unchecked.

## Implemented scope

`score-fabric quality capabilities` and `score-fabric quality run` support the installed
Clang-Tidy 19.1.7 candidate. The [exact contract](contracts/clang-tidy.md) and six scoped tasks
T033–T038 identify this user-authorized slice. Original T001–T032 retain the larger increment.
No full import/packet/assess interface, other analyzer/sanitizer runner, disposition evaluator,
CodeQL analysis, complete guideline mapping or engineering acceptance is implemented here.

The adapter binds exact tool/runtime-asset, native configuration and selected source hashes.
It measures version/config recognition/expanded checks/effective config, copies only selected
bytes to a disposable tree, supplies fixed C++17 arguments and a selected-tree header filter,
and preserves native YAML/stdout/stderr with full-stream digests and bounded base64 prefixes.
Per-phase timeouts kill the process group; aggregate retained bytes are capped. Source files
are checked after execution. Outputs refuse aliases/protected roots before running tools.
Native diagnostics retain rule IDs, levels, original messages/notes/fixes, byte offsets and
artifact/result references. These are Clang-Tidy indexes, not a complete cross-tool normalizer.

## Actual CLI evidence

| Evidence | CLI exit | Measured result |
| --- | --- | --- |
| [Capabilities](evidence/clang-tidy-capabilities.json) | 0 | Configuration recognized; expanded checks and native effective configuration retained |
| [Seeded run](evidence/clang-tidy-seeded-run.json) | 1 | Two native diagnostics: null dereference and required trailing-return style |
| [Corrected run](evidence/clang-tidy-corrected-run.json) | 0 | Fresh source baseline, adequate selected-unit processing, zero native diagnostics |

Source fixtures: [seeded](../../tests/fixtures/quality/seeded/check.cpp) and
[corrected](../../tests/fixtures/quality/corrected/check.cpp). The corrected fixture fixes the
null dereference and native trailing-return style warning. The earlier report is retained;
no suppression, check disabling or approved correction disposition is used.
These reports are genuine local runs on synthetic source content; origin is
`local_unprotected_execution`, assurance eligibility `not_eligible`, readiness `not_evaluated`.
The effective configuration's temporary paths and host defaults are retained as measured.

Malformed requests, duplicate keys, links, changed tool/config/source identities and output
aliases reject with exit 2 and preserve prior output. Missing tools return exit 1 with a named
gap. Partial/empty/unknown expected translation-unit sets, compiler errors, truncation, dynamic
or undeclared includes and NOLINT suppressions cannot count as adequate clean evidence.
Selected headers are copied and their actual native locations are retained.

## Remaining limits

- MISRA applicability denominator/mapping is unknown; the native CSV is absent. Compliance,
  manual review, tool confidence and protected production authority gaps remain visible even
  when complementary analysis is clean.
- Clang-Tidy uses the LLVM 19 candidate; native policy self-test uses LLVM 22.1.7. This slice
  measures actual configuration recognition, without claiming full-version qualification.
- System headers and host ABI are outside a qualified closure. Relative selected includes and
  integer defines are supported; arbitrary compiler flags, external headers, compilation DBs,
  generated build hooks and C++ language alternatives are not supported.
- The adapter executes no source/build hooks. It materializes only declared files in a fresh
  tree and invokes the selected analyzer directly with adapter-owned arguments, without --fix.
- Inline suppression detection is conservative; approved scoped suppression/deviation handling
  awaits the remaining 010 tasks. Native suppression/filter output stays in the raw streams.
- CodeQL eligible use, compiled-pack/source reconciliation, Python reporting compatibility and
  genuine extraction/report evidence remain external prerequisites. Cppcheck and sanitizers
  have explicit unimplemented adapter states.
- 009 T018, 005 T009 and 010 T032 remain open. Tests and successful CLI execution do not accept
  engineering decisions, native target artifacts or compliance.

## Validation commands

Tests were written first and initially failed collection because quality modules were absent.
`uv sync --frozen` succeeded. The quality contract/integration suite exercises actual installed
Clang-Tidy rather than substituting report fixtures. Final repository results are recorded below.

Final validation on this workstation:

- `uv run --frozen pytest tests/contract/test_quality_contracts.py tests/contract/test_quality_execution.py tests/integration/test_quality_tools.py -q`: 25 passed before the final corrected-fixture/style refinement; the final complete selected suite below includes all 25 tests and the final source.
- `uv run --frozen pytest --ignore=tests/integration/test_workflow_compiler_native.py`:
  **1127 passed, 11 skipped**, 61.95 seconds. The three existing 003 native Fabro scenarios
  were deliberately excluded: this slice neither selects their pinned runtime nor satisfies
  their native acceptance. The 11 skipped native/environment integrations remain unmet proof.
- `uv run --frozen ruff check .`: passed.
- `uv run --frozen ruff format --check .`: passed, 372 files already formatted.
- `uv run --frozen mypy`: passed, 90 source files.
- `uv run --frozen python scripts/check_foundation.py`: passed, all 64 FAB requirements unchanged,
  19 dependency rows and local documentation links checked.
- `uv build`: passed, source distribution and wheel generated.
- Both documented examples in [quickstart](quickstart.md) executed: capabilities exit 0,
  seeded run exit 1 with a published native finding record.
- Native config bytes exactly match the pinned upstream source. `score`, `score_cpp_policies`,
  `time` and Coding Standards reference checkouts remain clean at their recorded commits.
  License/NOTICE/config copies were read from the reference, without writing to it.
- `git diff --check`: passed. No extension hooks are registered; spec-quality checklist
  remains 16/16 and was not edited during implementation.

These checks validate the local adapter slice only. Full 010 requirements/owner acceptance
and CodeQL/sanitizer/compliance evidence remain open.
