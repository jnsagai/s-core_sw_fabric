# Increment 010: Clang-Tidy slice validation

2026-09-30. Implemented for local complementary use. Full increment 010 is incomplete;
engineering acceptance remains pending and human-owned T032 is unchecked.

**Latest resumed checkpoint (2026-10-01):** [genuine CodeQL software demonstrations](codeql-native-demonstration-acceptance.md)
retain three seeded findings and zero on a fresh corrected database, independently verified
extraction and no extraction errors. The new internal phase component has 35 contract cases;
214 focused checks pass. The later [Python 3.9 checkpoint](codeql-python39-reporting-acceptance.md)
verifies installed pinned dependencies, native Python/XML phases and complete reports with an
explicit disposable patch variant. Original failures are retained. The failed full ASan gate,
full target CodeQL adapter and human reviews remain open. The
[public fixed demonstration slice](codeql-public-demonstration-acceptance.md) now executes
through a distinct bounded request; target-source inspection remains blocked.

This records the initial Clang-Tidy slice and its historical validation. The subsequent
[Cppcheck/ASan/UBSan slice](complementary-acceptance.md) implements those additional adapters;
its current profiles and validation supersede the earlier unimplemented capability status.
The current overnight full gate and task reconciliation are recorded below; historical passes
do not clear the current restricted ASan runtime failure or required engineering review.

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

## Current overnight validation (2026-10-01)

The seven-hour user authorization covers remaining increment 010 implementation and reviewable
handoff. It does not authorize 011, engineering acceptance, publishing, merging or deployment.
[Actual handoff](../../docs/handoff/010-to-011.md) and [task reconciliation](task-reconciliation.md)
record 84 tasks: 69 complete, 15 open. Human T032/T082, 009 T018 and protected 005 T009 remain open.

| Gate | Current measured result |
| --- | --- |
| `UV_CACHE_DIR=/tmp/s-core-quality-uv-cache uv sync --frozen` | Pass, 18 packages checked; lock unchanged |
| Ruff check/format | Pass; mypy/foundation details below |
| `uv run --frozen mypy` with writable cache | Pass, 111 source files |
| `uv run --frozen python scripts/check_foundation.py` with writable cache | Pass, 64 unchanged FAB requirements and 19 dependency rows; no engineering acceptance |
| `uv build --offline` with writable cache | Pass, sdist and wheel; cached pinned backend dependencies are byte-verified copies |
| Full selected pytest suite | **Failed: 1,509 passed, 11 skipped, three native ASan failures; 252.06 seconds** |
| Combined review/decision/packet checkpoint | 106 passed, 98.57 seconds |
| Final foundation/CodeQL/context/actual installation checkpoint | 94 passed, 15.95 seconds |
| Synthetic public CLI and local Draft 2020-12 checks | Review exit 1, 005 binding exit 1, packet exit 0; all four request/result schemas validate with format checking |

The exact full native selector command is retained in
[CodeQL validation](codeql-prerequisites-acceptance.md#verification), and the complete current
[pytest output](evidence/overnight-regression.txt) preserves the three failed ASan cases.
The native LeakSanitizer stderr/capability/run originals are in
[sandbox diagnosis](sanitizer-environment.md). They show fatal thread attachment failure; original
native flags/suppressions remain unchanged. Three existing native Fabro compiler tests were
excluded because that runtime is not selected; eleven external/native skips do not imply readiness.
T030/T081 remain open. No full green gate is claimed.

The full run preceded the final two shared tool-count and eleven malformed CodeQL phase/suite
cases. Their negative-first fixes pass the final 94-case checkpoint. A deterministic 60-case
malformed inspection probe then produced no unexpected exceptions. Static/foundation/build checks
were repeated after these bounded fixes. That checkpoint preserved the failed full result;
the later shared reader corrections have their own full result below. Historical
profiles/transport hashes remain unchanged.

[CodeQL disposition context](codeql-dispositions-acceptance.md) adds original unavailable
inspection, native identity comparison, immutable portable history and blocked 005 binding.
Installed-pack integration uses a synthetic finding and cannot satisfy genuine CodeQL evidence.
T011/T012/T078/T079 remain unimplemented and gated by reviewed eligible-use and native report/runtime
prerequisites. Source/build tree equality is measured; compiled provenance and confidence remain
unverified. Unknown applicability/mapping/manual/deviation/production authority gaps remain visible.

Current `.git`/agent/native-install permissions are read-only with approval unavailable. New
CodeQL/control/sanitizer/schema/docs changes remain a reviewable worktree; no commit was attempted
under that restriction. Earlier packet/assessment/source-reconciliation commits remain retained.
Tests, fixtures, analyzer cleanliness and Fabro results do not establish engineering acceptance.

Subsequent bounded metadata-history fixes pass 101 combined cases and the unchanged legacy packet
replay; original library metadata is now retained. The unavailable-native-Git guard fix passes
52 CodeQL/context/installed checks. These checkpoints preserve the earlier failed full-suite
record and do not establish licensed analysis or clear the ASan runtime gate.

## 03:23 UTC shared reader validation checkpoint

The later profile/retained CodeQL metadata corrections pass 130 new negative cases and 299
combined contract checks. Ruff/formatting (468 files), mypy (111 source files), foundation
consistency and offline sdist/wheel build pass. Exact changes and commands are in
[controls validation](controls-validation.md).

The full regression under the same documented native selectors finishes with **1,657 passed,
11 skipped, three ASan failures**, 258.45 seconds. [Original output](evidence/overnight-regression-types.txt)
retains the same three failing seed/fix, disposition and import cases. This full
checkpoint leaves T030/T081 open; later checkpoints below preserve this historical evidence.
Native CodeQL/reporting, applicability/tool confidence and human acceptance are still unresolved.

The 03:35 UTC source/build observation replay adds six contradiction refusals and two
partial-failure cases. **232 combined cases pass, 22.78 seconds**, including installed-context,
portable assessment/compliance and unchanged legacy replay. Ruff/formatting (469 files), mypy
(112 sources), foundation consistency and offline build pass. This focused checkpoint follows
the full run above and preserves its failed native ASan gate; it does not establish eligible
CodeQL execution or engineering acceptance.

## 04:28 UTC installed-context checkpoint

T001 consolidation and explicit original/current policy migration are implemented under the
[installed-context contract and validation](installed-context-acceptance.md). Both profiles
and four current CLI outputs pass local schemas; actual current packet replay forbids host
reads/probes. Fresh read-only CodeQL inspection preserves all fourteen gaps. Current task
count is **70/84 complete, 14 open**, with human and native execution gates open.

The first consolidation regression retained four failures (three ASan and one incorrect
same-policy test expectation). Explicit original policy selection plus a separate changed-policy
case fixed the test scope; production's stale response was correct. Final full gate under the
same native selectors: **1,682 passed, 11 skipped, three ASan failures**, 358.60 seconds.
[Original output](evidence/overnight-regression-installed-context.txt) retains all three native
failures. This supersedes earlier full checkpoints without deleting their evidence. No full
green gate is claimed; T030/T081 remain open. Frozen sync, Ruff/format (474 files), mypy (113
sources), foundation consistency and offline sdist/wheel build pass. The original flags,
suppressions, source locks and historical packet bytes remain intact.

## Public fixed demonstration integration checkpoint

[Scoped public validation](codeql-public-demonstration-acceptance.md) records the distinct
request/record schemas, initial parser/harness failures, strict guard tests and genuine public
seed/fresh-fix native integration: **2 passed, 316.02 seconds**, three/zero native findings,
adequate extraction and all four original reports. T085–T088 are complete; current count is
**74/88 complete, 14 open**. Full target execution, failed ASan validation and authenticated
engineering reviews remain open. No compliance or production readiness is accepted.

Final focused public/parser/extraction/packet/installed-source checks: **302 passed, 2 deselected,
24.18 seconds**. Frozen sync, Ruff, formatting, mypy, foundation, offline build and diff checks
pass. This supplements the two real native integration passes; it does not clear the earlier
full-suite ASan failure. Original failed logs and measurements remain unchanged.

## Compatible host full validation checkpoint

The [complete host validation](asan-host-validation.md) passes **1,773 tests, 13 documented
external/native skips, 361.00 seconds**, with zero failures/errors. Sync, Ruff, formatting, mypy,
foundation and offline build pass. Fresh ASan capability, native defect/fix and all three formerly
failing integration cases pass without changing native settings. Original failed logs remain
retained. T008/T030/T081 are complete; current count is **77/88 complete, 11 open**.

The agent sandbox still cannot complete LeakSanitizer thread attachment. The compatible host
result resolves the native validation need for that host context; neither the thirteen skips nor
the three explicitly excluded native Fabro compiler cases count as readiness. Eligible target
CodeQL, manual/mapping/profile/provenance review and protected human authority remain open.

## Shared source include selection follow-up

[The source include validation](source-include-validation.md) preserves the original 35 failing
cases and the corrected focused native/contract checks. Comments, continued lines and `%:` can
no longer hide literal external paths from shared input inspection. Native selected-header runs
still diagnose the original defect and retain unchanged protected source/header bytes. Complete
target/generated-input closure and human acceptance remain open; task count stays 77/88.
## Fabro SOME/IP execution correction (2026-10-01)

The user's continuation authorizes the bounded command-binding contract and real factory
measurement demonstrator. T089–T092/T094 are complete with
[retained evidence](../../docs/handoff/someip-84/factory/README.md); T093 remains incomplete.
This is local operational draft execution, not native engineering plan acceptance.

- Negative-first binding gate: six initial failures; separate resealed-IR binding substitution
  fails before its integrity correction. Final binding/host gate: 21 passed.
- Negative-first host handoff: three initial failures; native CLI auth parsing and incomplete
  phase preservation pass after correction. The original user host failure remains retained.
- Compiler/runtime regression: 258 passed; native compiler integration: four passed.
- Frozen sync, Ruff, format, mypy (117 source files), foundation and offline build pass.
  Initial Ruff/format failures are retained separately. Build uses the existing writable
  copy of pinned cached backend dependencies; no network dependency fetch is claimed.
- Actual pinned Fabro host run `01M3VZNAAQ1QXK5530X7E8HZ26` starts both bound commands;
  expected baseline exit 1 with seven failures out of 13, external-candidate exit 0 with
  zero failures out of 13. Both measurement stages succeed after checking the expectations.
- Complete native export reproduces offline: 63 events, three checkpoints, nine blobs,
  one unanswered question, zero human answers and no portable closure reason codes.
  Native status is `blocked`, reason `human_input_required`. The fabric snapshot explicitly
  retains `QUESTION_SUBJECT_UNKNOWN` for the operational configuration question.
- The user's DeepSeek Flash/spending selection does not alter old disabled draft profiles,
  authorize another provider, imply a successful live call, or create engineering acceptance.
  Credentials, native agent binding/enforcement and usage/admission remain pending.

The external candidate remains earlier direct Codex work. No collector receipt, engineering
approval, qualification, complete native test suite or issue completion is inferred.
