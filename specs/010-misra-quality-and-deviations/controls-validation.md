# Live quality controls and native failure interpretation

2026-10-01, Lisbon. Convergence fixes T074–T077; original authority gates remain open.

## Changes

- Local capability/run readers retain the exact original request, profile, toolchain,
  configuration and sanitizer control bytes, then recheck them before returning results.
  Disposition observations also recheck origin/draft/history/evidence/current source selections.
  Changed controls refuse with exit 2; existing output remains intact.
- Shared bounded readers require regular files, at most 1 MiB per control before parsing,
  nesting depth 64 and 200,000 nodes. YAML must remain JSON-compatible with finite numbers.
  Native Clang-Tidy/effective-config YAML keeps the 16 MiB artifact bound. Live diagnostic
  IDs/levels and 1,000-location bound match retained-record readers.
- Missing tool/runtime assets do not stop validation of other selected identities. Changed
  dependencies still refuse even when the executable is absent. All selected runtime paths
  are checked for symlinks again.
- Execution and imports share native LeakSanitizer fatal-error interpretation. An exit 0,
  or an ASan finding with exit 55, cannot clear the fatal runtime failure. Original findings
  and stderr survive independent offline packet replay. No native flag/suppression changed.

## Verification

Tests preceded each implementation. The corrected control suite initially produced 45 failures
and two passes; the failures included all 38 late control/native-control cases. Four independent
late disposition cases also failed before implementation. Three live diagnostic field/location
cases and four native import cases failed before their corrections.

```bash
UV_CACHE_DIR=/tmp/s-core-quality-uv-cache uv run --frozen pytest tests/contract/test_quality_controls.py tests/contract/test_quality_contracts.py tests/contract/test_quality_dispositions.py tests/contract/test_quality_complementary.py tests/contract/test_quality_codeql.py -q --tb=short
```

Checkpoint: **149 passed**, 42.37 seconds. It preceded the final three diagnostic bound cases.

```bash
UV_CACHE_DIR=/tmp/s-core-quality-uv-cache uv run --frozen pytest tests/contract/test_quality_controls.py tests/contract/test_quality_sanitizer_import_failures.py -q --tb=short
```

Final control/import checkpoint: **54 passed**, 1.69 seconds. The four import tests also
verify offline packet replay with host reads/probes forbidden. Fixtures measure failure
interpretation and cannot replace real native analyzer acceptance.

```bash
UV_CACHE_DIR=/tmp/s-core-quality-uv-cache uv run --frozen pytest tests/integration/test_quality_tools.py tests/integration/test_quality_complementary.py tests/integration/test_quality_import.py tests/integration/test_quality_dispositions.py -q -k 'not asan' --tb=short
```

Affected genuine integration checkpoint: **20 passed, four deselected**, 12.70 seconds.
Clang-Tidy, Cppcheck and UBSan seeded/corrected executions, original imports and linked
correction history pass. Explicit ASan parameter cases were outside this focused checkpoint;
the prior full-run three ASan failures remain recorded in [runtime evidence](sanitizer-environment.md).
This focused selection does not clear T030/T081. Interrupted/truncated runtime behavior remains
fail-closed. Full validation will be recorded after the remaining bounded implementation.

Ruff check passes; mypy passes for 110 source files; foundation consistency passes. No
transport schema, dependency, native policy, source lock or historical evidence was rewritten
by these fixes. [Contract composition](contracts/quality.md) documents the unchanged version 1
profiles and the separate prerequisite-only CodeQL records. Current changes remain uncommitted
because `.git` is read-only in this environment.

## Retained CodeQL metadata refusal follow-up

At 03:20 UTC, a deeper deterministic inspection mutation probe covered 234 field paths and
1,404 malformed/type substitutions. It exposed six internal `TypeError` cases in shared profile
enum handling and 361 schema-invalid accepted substitutions in retained CodeQL metadata.
The meaningful negative checkpoint was **124 failed, 6 passed** before the fixes.

Shared profile enum guards now refuse unhashable values, the pinned CodeQL toolchain version
is checked during offline loading, and live configuration selection/offline replay share a pure
configuration shape validator. Retained source/reporting/prerequisite/inspector/pack/phase fields
now enforce the published types and bounds, including 32 phases and original raw formats.
Valid historical records retain their original bytes and digests; no host probe occurs in pure
inspection validation.

After correction, **130 new negative cases pass**, and the combined CodeQL/control/profile/
portable assessment checkpoint passes **299 cases, 19.00 seconds**. The same 1,404-case probe
has zero internal exceptions and zero schema-invalid accepted records. Schema-valid substitutions
remain unprotected declarations; structure never authenticates their truth or grants acceptance.
The unchanged legacy packet remains covered by offline replay tests.

```bash
UV_CACHE_DIR=/tmp/s-core-quality-uv-cache uv run --frozen pytest tests/contract/test_quality_codeql.py tests/contract/test_quality_codeql_dispositions.py tests/contract/test_quality_codeql_record_types.py tests/contract/test_quality_controls.py tests/contract/test_quality_contracts.py tests/contract/test_quality_assessment.py -q --tb=short
```

Ruff, formatting (468 files), mypy (111 source files), foundation consistency and an offline
sdist/wheel build pass. The broad regression after these shared reader changes completes with
**1,657 passed, 11 skipped, three failures**, 258.45 seconds. The same three native ASan seed/fix,
disposition and import cases fail. [Original output](evidence/overnight-regression-types.txt)
retains the failed gate. Existing native runtime evidence remains applicable; this checkpoint
does not clear T030/T081 or establish engineering acceptance.

## Original source/build observation replay

At 03:35 UTC, six semantic negative cases showed that schema-valid source/build summaries could
contradict the retained Git observations. All six failed before the fix and now pass. Pure
observation replay checks selected roots/read-only commands, required initial samples, subsequent
refreeze consistency, selected/query source closure, declared build commit and recomputed tree
relation. Two partial-failure cases preserve unknown source/build reconciliation and replay the
resulting packet without host reads. The unchanged legacy packet remains covered.

The initial record/context checkpoint passes **185 tests, 12.51 seconds**. The installed-context,
portable assessment/compliance and contradiction checkpoint passes **230 tests, 22.43 seconds**
before adding the two partial-failure cases; the final combined checkpoint passes **232 tests,
22.78 seconds**.
The same 1,404-case metadata probe has no internal exceptions. Ruff/formatting (469 files),
mypy (112 source files), foundation consistency and offline package build pass. These checks
preserve the latest full-suite ASan failures and do not establish genuine CodeQL analysis.

```bash
SCORE_CODEQL_PREREQUISITE_REQUEST="$PWD/examples/quality/codeql-prerequisites.yaml" UV_CACHE_DIR=/tmp/s-core-quality-uv-cache uv run --frozen pytest tests/integration/test_quality_codeql.py tests/contract/test_quality_assessment.py tests/contract/test_quality_compliance.py tests/contract/test_quality_codeql_record_types.py tests/contract/test_quality_codeql_dispositions.py -q --tb=short
```
