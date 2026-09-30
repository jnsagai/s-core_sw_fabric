# Increment 010 validation guide

**Status:** Clang-Tidy, Cppcheck and separate GCC ASan/UBSan capability/run adapters implemented.
Read-only native import/extraction validation and draft/correction checks are implemented.
Independent fixture decision replay and guideline coverage are implemented; the remaining
CodeQL execution and packet/compliance workflow remain planned in [tasks](tasks.md).

## Installed tools

```bash
clang-tidy --version
codeql version --format=json
```

Commands resolve through `~/.local/bin/` into `~/.local/share/s-core-tools/`.
[Installation evidence](evidence/tool-installation.json) contains verified download/package hashes,
versions, local paths and the compiled 2.61.0 MISRA pack identity. Use the recorded pack path
explicitly; global CodeQL cache/configuration was not modified.

The [Clang-Tidy installation smoke](evidence/clang-tidy-install-smoke.json) retains a genuine
`clang-analyzer-core.NullDereference` finding with the pinned native config. It is an installation
probe and cannot satisfy a guideline compliance claim.

## Run the implemented Clang-Tidy slice

These examples bind the current workstation's exact candidate paths/hashes. Output is outside
all selected source/protected roots. On another host, rebind the reviewed tool/input refs.

```bash
uv run --frozen score-fabric quality capabilities --request examples/quality/clang-tidy-capabilities.yaml --out /tmp/quality-capabilities.json --json
uv run --frozen score-fabric quality run --request examples/quality/clang-tidy-run.yaml --out /tmp/quality-run.json --json
```

The seeded run returns 1 with native diagnostics. It writes no source fixes. See the
[exact contract](contracts/clang-tidy.md) and [actual seed/fix evidence](acceptance.md).
The corrected synthetic source has a fresh adequate selected-unit run with zero native
findings; mapping/authority/compliance gaps remain. Output 0 never means engineering acceptance.

## Run Cppcheck or a separate sanitizer mode

These workstation selections use Cppcheck 2.7 and GCC 11.4. Each capability request executes
a clean real probe; sanitizer probes compile, link and run with the pinned native policy assets.
The following commands use the implemented CLI:

```bash
uv run --frozen score-fabric quality capabilities --adapter cppcheck --request examples/quality/cppcheck-capabilities.yaml --out /tmp/cppcheck-capabilities.json --json
uv run --frozen score-fabric quality run --adapter cppcheck --request examples/quality/cppcheck-run.yaml --out /tmp/cppcheck-run.json --json
uv run --frozen score-fabric quality capabilities --adapter asan --request examples/quality/asan-capabilities.yaml --out /tmp/asan-capabilities.json --json
uv run --frozen score-fabric quality run --adapter asan --request examples/quality/asan-run.yaml --out /tmp/asan-run.json --json
uv run --frozen score-fabric quality capabilities --adapter ubsan --request examples/quality/ubsan-capabilities.yaml --out /tmp/ubsan-capabilities.json --json
uv run --frozen score-fabric quality run --adapter ubsan --request examples/quality/ubsan-run.yaml --out /tmp/ubsan-run.json --json
```

Seeded runs exit 1 and preserve native diagnostics. Corrections require fresh source hashes
and a new run. See [contract](contracts/complementary-tools.md) and
[actual capability/seed/fix records](complementary-acceptance.md). Active native suppressions,
incomplete source scope, truncated reports and unexpected runtime exits block clean evidence.

## Import native outputs without executing tools

The example below selects synthetic SARIF/report/source fixtures and remains `fixture`.
Tool/pack identities are explicitly synthetic; it is not a CodeQL execution example.

```bash
uv run --frozen score-fabric quality import --request examples/quality/native-import.yaml --out /tmp/quality-native-import.json --json
```

It exits 1 and publishes a synthetic native finding with complete declared structural scope.
Original bytes, contributor references and every authority/compliance gap remain visible.
For actual local analyzer output, select the frozen source baseline, declared identities,
original artifacts and independent phase/extraction manifest according to the
[exact contract](contracts/native-import.md). See [genuine complementary-output imports](native-import-acceptance.md).
Unknown/empty/partial extraction and inner failures remain incomplete. Imports invoke no tools.

## Draft and check a correction

These examples bind synthetic source files and genuine local analyzer output. Drafts
invoke no analyzer; an explicit correction check runs the selected tool again and
retains original native output. A prior clean report cannot substitute for that run.

```bash
uv run --frozen score-fabric quality disposition --request examples/quality/disposition-clang-tidy.yaml --out /tmp/quality-draft.json --json
uv run --frozen score-fabric quality disposition --request examples/quality/disposition-clang-tidy-correction.yaml --out /tmp/quality-correction.json --json
```

The first exits 1 with an open draft. The second exits 0 only for a fresh local
`corrected` observation, without engineering acceptance. Cppcheck, ASan and UBSan
selections use `examples/quality/disposition-{cppcheck,asan,ubsan}-correction.yaml`.
Scope/tool/policy drift, incomplete extraction, suppression and failed phases prevent
correction. False-positive/deviation/suppression proposals stay pending. See the
[exact contract](contracts/dispositions.md) and [retained observations](disposition-acceptance.md).

## Measure guideline coverage

The supplied native mapping is absent. This executed example preserves an unknown denominator
and returns 1; it invents no guideline ID or applicability decision:

```bash
uv run --frozen score-fabric quality coverage --request examples/quality/coverage-unknown.yaml --out /tmp/quality-010-coverage.json --json
```

Declared source-backed fixture IDs demonstrate structural coverage and pending manual/audit/
exclusion states only. Missing rows, required artifacts, filters, drift and suppressed findings
remain unresolved. See [contract](contracts/coverage.md) and [validation](coverage-acceptance.md).
No matrix grants compliance or changes the default profile's unknown mapping/authority state.

## Remaining increment validation sequence

1. Implement the strict profile/request/native-output contract tests and real local analyzer
   integration tests from `tasks.md`.
2. Copy 009 fixtures into a disposable working tree. Freeze file digests/configuration and explicit
   expected translation units. Run a seeded quality defect under native Clang-Tidy, preserve native
   YAML/text, correct it and run a changed baseline. Exercise optional Cppcheck similarly.
3. Execute supported GCC ASan/UBSan fixtures, including a seeded defect. Retain raw build/runtime
   output and prove incompatible/unavailable modes remain explicit.
4. Import labelled SARIF/native-report fixtures. Empty/partial/unknown extraction, failed query,
   suppressed finding and native `Compliant` with missing rules must remain blocked.
5. Build a draft deviation, exercise wrong/expired/self-asserted decisions and source drift. A
   fixture 005positive path remains fixture only; required human questions stay pending.
6. Run genuine CodeQL integration only with exact selected tools/packs, externally established
   eligible use and compatible reporting prerequisites. If absent, record the blocked real-run
   state; no fixture satisfies this acceptance.
7. Run Ruff, mypy, pytest, `uv run --frozen python scripts/check_foundation.py` and `uv build`.
   Record actual acceptance evidence and limitations before a 010-to-011 handoff.

## Expected review result

The local candidate may report a passing complementary analysis, findings or a correction history.
MISRA compliance remains blocked until the guideline denominator/mapping, licensed execution,
manual/audit obligations and required authorized decisions are present. Native report labels and
local analyzer success cannot clear those missing obligations.
