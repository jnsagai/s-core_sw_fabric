# Increment 010: Cppcheck and sanitizer slice validation

2026-09-30. The user's `go` authorized the bounded Cppcheck/ASan/UBSan adapter slice.
T039–T043 record this work, following [Clang-Tidy validation](acceptance.md).
Full increment 010 and engineering acceptance remain incomplete; human-owned T032 is unchecked.

## Implemented scope

`quality capabilities|run --adapter cppcheck|asan|ubsan` selects strict version 1 requests,
hash-bound profiles and configuration. The default Clang-Tidy interface is preserved.
[Exact contract](contracts/complementary-tools.md), [examples](../../examples/quality/),
and [quickstart](quickstart.md) describe the implemented interface.

Cppcheck 2.7 executes selected translation units independently, retaining original XML v2,
native IDs, severity, CWE, primary/related locations and artifact/result references.
The local C++17 configuration enables warning, style, performance, portability, information
and missingInclude categories. Missing includes/configurations and malformed/incomplete
reports block adequate clean evidence. This configuration is a complementary candidate.

GCC 11.4 builds each declared translation unit, links one component binary and executes it
in a disposable tree. ASan and UBSan are separate selections. Capability probes actually
compile, link and execute a clean synthetic program. Native policy bytes are copied from
`score_cpp_policies` commit `9bcfe8296038569a0ff7627fb8ce7a189018a7b3`; source IDs,
hashes, statuses and Apache-2.0 LICENSE/NOTICE remain in the candidate profile/assets.
The adapter derives `-g1`, compile/link `-fsanitize=address` or `-fsanitize=undefined`
from native `cc_args`. UBSan selects native `ubsan_gcc`; no Clang runtime flag is invented.
Native ASAN_OPTIONS/UBSAN_OPTIONS templates are rendered with isolated suppression paths.
Both selected suppression files contain comments only; active rules block execution.
No blanket LSan/GoogleTest/Rust suppression inheritance occurs.

Requests use the existing bounded capture, timeout, frozen source and guarded output foundation.
Probe phases/artifacts have distinct names; probe/component effective configurations are independent
snapshots. Raw outputs, full-stream and retained-prefix hashes, rendered runtime options,
compiler/link arguments and generated binary size/hash are retained. Source/build hooks are
not executed. Existing reference repositories are read only.

## Actual CLI evidence

These are genuine local tool executions on synthetic sources, produced through the public CLI
handler with guarded `--out` publication. Fixtures supply source content, not fabricated reports.
Capability and corrected runs exit 0; every seeded run exits 1 with one native finding.

| Adapter | Capability | Seeded native finding | Fresh corrected run |
| --- | --- | --- | --- |
| Cppcheck | [Available](evidence/cppcheck-capabilities.json) | [nullPointer](evidence/cppcheck-seeded-run.json), analyzer exit 2 | [Zero findings](evidence/cppcheck-corrected-run.json) |
| ASan | [Actual clean runtime](evidence/asan-capabilities.json) | [heap-buffer-overflow](evidence/asan-seeded-run.json), runtime exit 55 | [Runtime 0, zero findings](evidence/asan-corrected-run.json) |
| UBSan | [Actual clean runtime](evidence/ubsan-capabilities.json) | [signed integer overflow](evidence/ubsan-seeded-run.json), runtime exit 55 | [Runtime 0, zero findings](evidence/ubsan-corrected-run.json) |

The corrected sources have fresh matching source baselines and adequate declared selected-unit
processing. Seeded reports remain immutable. Each sanitizer finding retains a native source
location and original diagnostic text. All records remain `local_unprotected_execution`,
`not_eligible`, readiness `not_evaluated`; local clean execution accepts no engineering decision.

## Verification and limits

Tests preceded adapter implementation and initially failed collection because the new modules
were absent. The focused suite has **44 passing tests**, including the 25 existing Clang-Tidy
tests. New cases exercise actual probes, defects/fixes, CLI publication, strict mode/config
identity, all XML locations/CWE, entity rejection, unknown source scope, missing includes,
build failure, unavailable selected assets, active suppression rejection, truncated runtime
output, unexpected runtime exit and independent probe/component identities.

Final repository checks are recorded below. The full selected pytest suite has
**1146 passed, 11 skipped**, 68.53 seconds. The three existing
`tests/integration/test_workflow_compiler_native.py` scenarios were excluded: their pinned
Fabro runtime is not selected by this slice. Skipped/excluded integrations remain unmet native proof.

Completed checks:

- `uv sync --frozen`: passed.
- `uv run --frozen pytest tests/contract/test_quality* tests/integration/test_quality* -q`:
  44 passed. After the final XML encoding guard, both complementary test files passed again:
  19 passed. Entity declarations in UTF-16 cannot bypass the XML byte guard.
- `uv run --frozen pytest --ignore=tests/integration/test_workflow_compiler_native.py`:
  1146 passed, 11 skipped, as described above.
- `uv run --frozen ruff check .` and `ruff format --check .`: passed, 381 files formatted.
- `uv run --frozen mypy`: passed, 94 source files.
- `uv run --frozen python scripts/check_foundation.py`: passed; 64 unchanged FAB requirements,
  19 dependency rows, locks and local documentation links.
- `uv build`: passed; source distribution and wheel generated.
- Draft 2020-12 validation using local JSON Schema references passed for all quality schemas,
  workstation examples/profiles and historical/new execution records.
- All eight documented capability/run console examples executed; capabilities exited 0,
  seeded runs exited 1 and published findings. Clang-Tidy examples now select the updated
  candidate profile hash; earlier historical evidence remains unchanged.
- Copied native quality asset bytes/hashes match pinned `score_cpp_policies` sources.
  `score`, `score_cpp_policies`, `time` and `codeql-coding-standards` checkouts remain clean
  at their recorded commits. Original brief and license notices are preserved.
- `git diff --check`: passed. No Spec Kit extension hooks are registered; the spec-quality
  checklist remains 16/16, unchanged by implementation.

Remaining work and limits:

- CodeQL eligible use, compiled-pack/source reconciliation and native reporting prerequisites
  remain unresolved. No CodeQL analysis is claimed.
- Native CSV/rule mapping, applicability denominator, manual review, tool confidence and
  protected production authority remain unknown/pending even for clean local runs.
- Native-output import/SARIF normalization, cross-tool deduplication, disposition decisions,
  guideline coverage and compliance packet/assessment are not implemented in this slice.
- Compiler helpers and sanitizer runtime assets are pinned; system headers, host ABI,
  startup objects and complete linker/library closure are unqualified. Fixed local compiler
  invocations do not reproduce a native Bazel target build.
- Sanitizer execution covers only this selected binary and its executed paths. Arbitrary
  flags, target build hooks, external headers, runtime arguments and combined selectors
  are unsupported. Separate ASan/UBSan selection does not assert native incompatibility.
- Fatal runtime signals or other diagnostics without a recognized sanitizer finding are
  incomplete evidence. No hidden retry or compiler flag workaround is applied.
- 009 T018, 005 T009 and 010 T032 remain human/external prerequisites. No publishing,
  merging, deployment, automatic acceptance or continuation to 011 is authorized.
