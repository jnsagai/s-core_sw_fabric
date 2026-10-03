# Increment 010 validation guide

**Status:** Clang-Tidy, Cppcheck and separate GCC ASan/UBSan capability/run adapters implemented.
Read-only native import/extraction validation and draft/correction checks are implemented.
Independent fixture decision replay and guideline coverage are implemented; the remaining
CodeQL execution and engineering reviews remain planned in [tasks](tasks.md).

## Installed tools

```bash
clang-tidy --version
codeql version --format=json
```

Commands resolve through `~/.local/bin/` into `~/.local/share/s-core-tools/`.
[Installation evidence](evidence/tool-installation.json) contains verified download/package hashes,
versions, local paths and the compiled 2.61.0 MISRA pack identity. Use the recorded pack path
explicitly; global CodeQL cache/configuration was not modified.

The current [primary profile](../../profiles/s-core-quality-v1.yaml) also retains four
candidate installation snapshots and complete original notices under the
[installed-context contract](contracts/installed-context.md). Qualification/eligibility remain
unknown. Current execution examples select its new SHA; the synthetic native-import example
selects the [byte-exact original profile](../../tests/fixtures/quality/profiles/s-core-quality-legacy-v1.yaml)
to preserve its old native artifact bindings. Historical outputs/packets remain unchanged.

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

## Emit a portable review packet

This executed example retains the current unknown-denominator matrix, explicit fixture
source bytes and original license/notice files. It invokes no analyzer.

```bash
uv run --frozen score-fabric quality packet --request examples/quality/packet-unknown.yaml --out /tmp/quality-010-packet.json --json
```

Exit 0 indicates portable closure. Mapping, manual reviews, CodeQL eligibility and protected
authority remain gaps; every human question stays pending. See [contract](contracts/packet.md)
and [verification](packet-acceptance.md). Selected earlier imports and full disposition history
can be included, with exact current/prior source snapshots and notice associations.

## Independently evaluate compliance blockers

This executed request replays the portable packet and selects current fixture source bytes.
It invokes no analyzer and exits 1 with blocked production-domain compliance.

```bash
uv run --frozen score-fabric quality assess --request examples/quality/assessment-unknown.yaml --out /tmp/quality-010-assessment.json --json
```

A null current baseline selects offline evaluation with unknown source freshness. Fixture
decisions are reevaluated at the explicit as-of and domain; source/config/validity drift
prevents reuse. Even an exact packet-bound supporting 005 pass does not adopt guideline
policy or discharge manual review. See [contract](contracts/assessment.md) and
[verification](assessment-acceptance.md). No current profile can produce a compliance pass.

## Remaining increment validation sequence

### Inspect CodeQL prerequisites

The explicit installed-source selection measures prerequisites without invoking CodeQL or
native reporting. It exits 1 with unavailable execution and named missing prerequisites:

```bash
UV_CACHE_DIR=/tmp/s-core-quality-uv-cache uv run --frozen score-fabric quality capabilities --adapter codeql --request examples/quality/codeql-prerequisites.yaml --out /tmp/quality-010-codeql-prerequisites.json --json
```

See [the contract](contracts/codeql-prerequisites.md) and
[the measured result](codeql-prerequisites-acceptance.md). Eligible-use bytes remain unverified;
neither a fixture nor an inspection unlocks analysis. The current sandbox also blocks native
ASan LeakSanitizer probing; [that failure](sanitizer-environment.md) remains unmet validation.

### Run the public fixed CodeQL software demonstrations

The [public contract](contracts/codeql-demonstration.md) selects fixed synthetic seeded/corrected
C++ programs, the installed compiler and Python 3.9.25 reporting environment. It executes native
configuration/XML, C++ extraction, default-suite queries, SARIF/CSV, independent extraction
queries and all four reports in disposable trees. The examples explicitly request the local
`git_recount` transformation of the selected upstream patch; native patch qualification stays
unknown. Each output must be new and outside protected roots.

```bash
UV_CACHE_DIR=/tmp/s-core-quality-uv-cache uv run --frozen score-fabric quality run --adapter codeql --request examples/quality/codeql-demonstration-seeded.yaml --out /tmp/quality-codeql-public-seeded-review.json --json
UV_CACHE_DIR=/tmp/s-core-quality-uv-cache uv run --frozen score-fabric quality run --adapter codeql --request examples/quality/codeql-demonstration-corrected.yaml --out /tmp/quality-codeql-public-corrected-review.json --json
```

Seeded findings produce exit 1; a complete zero-finding corrected demonstration produces exit 0.
Missing prerequisites, phase/report failure or inadequate extraction produce exit 1 with named
gaps. Rejected/drifting inputs produce exit 2 and preserve earlier output. These outcomes do not
grant engineering acceptance. Target-project run requests continue to inspect prerequisites only.

The [original internal measurements](codeql-native-demonstration-acceptance.md) and
[Python 3.9 reporting history](codeql-python39-reporting-acceptance.md) preserve the earlier
failures and reproducer. The user installed Python 3.9.25, PyYAML 5.4 and pytest 7.2.0 after
sandbox DNS failures. `unmodified` report mode retains the original seeded `KeyError: 'misra'`;
it does not silently apply the recount variant.

### Full increment gates

Imported CodeQL proposals can use the distinct request/review kinds in
[the context contract](contracts/codeql-dispositions.md) with `quality disposition` and
`quality decision-subject`. Context reviews exit 1 and cannot correct a finding; packets
may exit 0 for structural emission while execution/eligibility/manual blockers remain.
[Verification](codeql-dispositions-acceptance.md) includes synthetic and installed-pack checks.

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

## Validate ASan from the normal terminal

This workstation's agent sandbox cannot complete LeakSanitizer thread attachment. Run the
existing selected native settings from the normal terminal; no suppression or native flag is
changed. All outputs go to a fresh `/tmp/score-quality-asan-host.*` directory.

```bash
cd /home/jefferson/s-core_sw_fabric
bash scripts/validate_asan_host.sh --full
```

The script stops on failed capability, incomplete seed/fix records or failed native integration,
retaining original evidence. It checks native exits, bytes, scope, fresh source/configuration and
three targeted integration cases before running full static/regression/foundation/build gates.
The three native Fabro compiler tests remain explicitly excluded because that runtime is not
selected; environment-dependent skips remain reported and cannot establish readiness. The
new public CodeQL demonstrations retain their separately measured native gate.

To resume after a repository validation error, use the printed original evidence directory:

```bash
bash scripts/validate_asan_host.sh --resume /tmp/score-quality-asan-host.BVZPU8t8
```

Resume verifies the original ASan records and passing integration report, then creates a new
evidence directory for subsequent gates. This local verifier neither authenticates a protected
collector nor accepts engineering decisions. [Current native measurements](sanitizer-environment.md).
