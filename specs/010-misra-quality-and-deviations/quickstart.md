# Increment 010 validation guide

**Status:** Clang-Tidy capability/run slice implemented. The full multi-tool, import, disposition
and compliance workflow remains planned in [tasks](tasks.md).

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

## Implementation validation sequence

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
