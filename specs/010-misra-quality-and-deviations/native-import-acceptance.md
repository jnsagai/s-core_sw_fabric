# Increment 010: native import and extraction validation

2026-09-30. The user's `go` authorized native-output import and extraction validation, following
the [complementary tools slice](complementary-acceptance.md). US2 T014–T018 and scoped
T044–T048 are implemented. Full increment 010 and engineering acceptance remain incomplete;
human-owned T032 stays unchecked.

## Implemented scope

`score-fabric quality import` reads hash-selected source, identity, native artifact and extraction
manifests without executing tools. The [exact contract](contracts/native-import.md) and strict
schemas describe the implemented interface. Source/profile/tool/config/pack/suite/library bindings
are explicit. Import does not require an executable to be installed and does not verify execution
eligibility. Selected-byte drift rejects; mismatched reported bindings remain incomplete gaps.

Clang YAML, Cppcheck XML, sanitizer text and a bounded SARIF 2.1.0 subset preserve original
formats/bytes separately from derived indexes. Clang notes, ranges and replacements are indexed.
SARIF resolves multiple runs, rule descriptors/components, direct/indexed artifacts, URI bases,
logical/related locations, code flows, stacks, fixes and attachment artifact locations. Unsupported
external properties, remote paths, malformed coordinates/references and unknown native versions
reject. Native rule/result records, severity, fingerprints and suppression/property data remain
available. Deduplication retains every contributor; distinct SARIF runs/components/kinds and
different locations remain separate. Fingerprints cannot hide observations at other locations.

The independent expected source set is compared against each tool's declared processed/extracted
sets. Phase and report status, truncation, extraction warnings/errors, failed queries, filters,
unexplained exclusions and missing observations remain blockers even when outer exit is zero.
CodeQL supporting report IDs are checked, and native database-integrity counts/listing must match
the declared extracted set. Native `Compliant` and `approved-by` strings accept no decision.
Bindings and phase declarations remain unauthenticated even when structural adequacy is adequate.

Controls are at most 1 MiB; frozen source is at most 500 files/64 MiB. Native retention is
16 MiB per artifact, 64 MiB total; at most 512 MiB original native input is streamed/hashed.
Oversize retained artifacts preserve full-stream/prefix hashes and are incomplete. Native
nesting/nodes and 10000 aggregate results are bounded. Output aliases/protected roots refuse
publication, and malformed inputs preserve previous output. Baseline snapshots carry their own
seal and retain the original input baseline digest separately.

## Actual evidence

Eight imports were produced through the public CLI handler from fresh genuine local analyzer
runs on synthetic sources. Each includes the original run as a raw log, original native bytes,
declared derivative bindings, baseline snapshot, findings and extraction assessment. Native
analysis origin remains in the original raw run; the import origin is always `imported_unverified`.

| Adapter | Seeded import | Corrected import |
| --- | --- | --- |
| Clang-Tidy | [Exit 1, two native findings](evidence/clang-tidy-seeded-import.json) | [Exit 0, zero findings](evidence/clang-tidy-corrected-import.json) |
| Cppcheck | [Exit 1, nullPointer](evidence/cppcheck-seeded-import.json) | [Exit 0, zero findings](evidence/cppcheck-corrected-import.json) |
| ASan | [Exit 1, heap-buffer-overflow](evidence/asan-seeded-import.json) | [Exit 0, runtime 0](evidence/asan-corrected-import.json) |
| UBSan | [Exit 1, signed integer overflow](evidence/ubsan-seeded-import.json) | [Exit 0, runtime 0](evidence/ubsan-corrected-import.json) |

The clean Clang-Tidy probe emits no fixes YAML. Its empty native stdout/stderr are retained as
`clang-tidy-text`, bound to the successful native phase. Nonempty text without a parsed report
stays incomplete; no fake clean YAML is generated. Seeded native finding exits 1/2/55 are retained
and distinguished from failed phases using parsed findings. Native reports remain unchanged.

The [SARIF fixture import](evidence/sarif-fixture-import.json) uses clearly labelled
[synthetic SARIF](../../tests/fixtures/quality/sarif/README.md) and
[extraction/report fixtures](../../tests/fixtures/quality/extraction/README.md).
It is `fixture`, not a genuine CodeQL run. It preserves the synthetic finding and leaves mapping,
manual review, eligibility, source/build reconciliation, tool confidence and authority unresolved.

All records remain `not_eligible`, readiness `not_evaluated`. Exit 0 describes complete declared
import processing, without accepting engineering content, CodeQL execution or MISRA compliance.

## Verification

Initial contract/extraction tests failed collection because import modules did not exist.
The completed quality suite has **87 passing tests**, including 43 new import/extraction cases.
Tests cover native contributor retention, multiple runs/components, repeated fingerprints at
different locations, logical/indexed/flow/fix locations, message IDs, suppressions, byte/baseline
drift, unsafe publication, native invocation failure, unknown/empty/partial source scope,
missing/failed reports, filtered checks, warnings/errors, exclusions, malformed phase types,
duplicate keys/YAML anchors/nonfinite values and streamed truncation. Genuine analyzer imports
also verify unchanged sources, fresh correction and no tool invocation during import.

Completed repository checks:

- `uv sync --frozen`: passed.
- `uv run --frozen pytest tests/contract/test_quality* tests/integration/test_quality* -q`:
  **87 passed**, 13.03 seconds.
- `uv run --frozen pytest --ignore=tests/integration/test_workflow_compiler_native.py`:
  **1189 passed, 11 skipped**, 68.32 seconds. The three existing Fabro native scenarios were
  excluded because their pinned runtime is not selected. These and skipped integrations remain
  unmet native proof, as in earlier slices.
- `uv run --frozen ruff check .` and `uv run --frozen ruff format --check .`: passed,
  398 files formatted. `uv run --frozen mypy`: passed, 98 source files.
- Quality schemas/examples/evidence and persistent fixture manifests pass Draft 2020-12
  validation with local references. The synthetic SARIF passes the full schema in the pinned
  Coding Standards source; runtime support is the narrower documented subset.
- Native report/query/schema/license sources were inspected read only and their exact hashes
  retained in [research evidence](evidence/native-import-research.json). Native source commits
  and notices remain unchanged; no reference build or reporting script was executed.
- After the native numeric-count guard refinement, the 43 import/extraction tests passed again
  in 3.31 seconds; an oversized native count also produced an incomplete report without an
  unhandled parser exception.
- `uv run --frozen python scripts/check_foundation.py`: passed, 64 unchanged FAB requirements,
  19 dependency rows, locks, skills and local links. `uv build`: source distribution/wheel passed.
- The documented console import example returned exit 1, published its labelled fixture finding
  and retained unverified authority. Native `score`, `score_cpp_policies`, `time` and
  `codeql-coding-standards` references remain clean at their recorded commits.
- `git diff --check`: passed. The original brief/license notices are untouched. No Spec Kit
  extension hooks are registered; spec-quality checklist remains 16/16 and unchanged.

## Remaining work

Disposition/correction/decision history, guideline coverage and portable packet/assessment
interfaces remain unimplemented. CodeQL execution needs eligible use, source/build reconciliation
and compatible native reporting prerequisites. Imported declarations, fixtures, self-digests,
suppression names and native compliance strings cannot satisfy those prerequisites or protected
005 authority. Full host build closure and native target qualification remain unvalidated.
009 T018, 005 T009 and 010 T032 remain human/external obligations. No publishing, merging,
release, deployment, automatic acceptance or continuation to 011 is authorized.
