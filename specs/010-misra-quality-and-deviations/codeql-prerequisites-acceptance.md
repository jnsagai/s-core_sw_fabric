# CodeQL prerequisite implementation evidence

2026-10-01, Lisbon. [Exact contract](contracts/codeql-prerequisites.md).
The existing seven-hour authorization covers this inspection and continuing 010 work.
It does not adopt eligibility/report configuration, authorize engineering decisions or start 011.

## Implemented behavior

`quality capabilities/run --adapter codeql` inspect explicit frozen selections, source Git objects,
installed pack files, dependency metadata, suite filters and original reporting/configuration
controls. They never execute CodeQL, a build, a query, a report script or an interpreter.
Supporting eligibility bytes cannot unlock execution. T011/T012 remain unmet for genuine analysis.

Only bounded host Git inspection commands execute after output guards. Optional locks, fsmonitor,
hooks and inherited global/system Git configuration are disabled. Reference indexes stay unchanged.
Source bytes compare directly with their Git blobs, including when index flags hide modifications.
Source/build Git trees, exact suite imports, native query files, pack manifests and embedded library
names/versions are checked. Missing objects/libraries remain named; drifted identities refuse.

Every selected control/source/pack/tool identity, Git state and original component file is refrozen
before guarded publication. Native roots and the Git inspector are protected. An accidental call
through the complementary handler rejects CodeQL before any CLI execution.

Inspection and run output both exit 1 with unavailable execution, unknown extraction where
requested, zero accepted claims, not_eligible and readiness not_evaluated. Exit 2 preserves a
previous output for malformed/unsafe/drifting selections. No exit-0 execution path exists here.
Declared versions and installed bytes do not qualify the runtime or reporting environment.

## Actual selected installation

[Request](../../examples/quality/codeql-prerequisites.yaml),
[toolchain](../../profiles/codeql2214-local-v1.yaml),
[native input selections](../../profiles/codeql261-prerequisites-local-v1.yaml),
[retained unavailable inventory](evidence/codeql-prerequisites.json).

```bash
uv run --frozen score-fabric quality capabilities --adapter codeql --request examples/quality/codeql-prerequisites.yaml --out /tmp/quality-010-codeql-prerequisites.json --json
```

The actual record measures 240 selected native files (233 MISRA queries/libraries/suites),
2,068 installed pack files and 13 embedded library identities. Reviewed/declared-build Git
trees are equal. Fourteen named gaps remain: eligibility, primary execution, runtime closure,
compiled/library source provenance, reporting interpreter/compatibility, owner configuration/tool
confidence, mapping/manual/production authority and native audit/default-disabled suite exclusions.
This is installation/source inspection; no query or report acceptance is claimed.

Native query text and compiled artifacts are not redistributed. Original metadata/configuration,
patch, source license and requirements bytes remain supporting records. Installed CLI terms/notices
remain at their selected paths. Proprietary guideline text and native statuses are untouched.

## Verification

- Initial negative contract cases failed on the absent implementation; subsequent adversarial
  cases verify direct Git-blob matching, native fsmonitor/index protection, missing/drifted library
  identities, bounded/cyclic controls, source/control races and unsafe publication.
- Focused contract and real selected installation integration: **29 passed**, 3.61 seconds.
  Real installation checks are prerequisite inspections; they cannot substitute for T012.
- Actual request, both candidate profiles and retained output validate against Draft 2020-12
  schemas with local references and format checking. No dependency was added.
- Ruff check/format and mypy (109 source files) pass for the implementation.
- Combined CodeQL contract/selected-installation and complementary contract checkpoint: **42 passed**, 3.90 seconds, including four new LeakSanitizer fatal-error cases.
- `UV_CACHE_DIR=/tmp/s-core-quality-uv-cache uv sync --frozen`: 18 installed packages checked; no dependency change.
- Full Ruff check/format: pass, 450 files formatted; mypy: pass, 109 source files.
- Foundation consistency: pass, 64 unchanged requirements and 19 dependency rows.
- `uv build` initially failed because the new writable cache lacked the pinned backend and PyPI DNS was unavailable. A copy of cached Hatchling 1.32.4 and its dependencies was byte-verified (178 files), with the original cache unchanged. `UV_CACHE_DIR=/tmp/s-core-quality-uv-cache uv build --offline` then built both sdist and wheel successfully.
- Full regression: **1,413 passed, 11 skipped, three ASan failures**, 197.20 seconds. Native stderr identifies LeakSanitizer fatal thread attachment failure in the restricted sandbox. [Retained diagnosis and correction](sanitizer-environment.md) preserve the failed integration gate. Full T030 remains unmet; no skip or runtime override was introduced.

Exact full regression command:

```bash
SCORE_SOURCE=/home/jefferson/score \
SCORE_CPP_POLICIES_SOURCE=/tmp/s-core-foundation/references/score_cpp_policies \
SCORE_TIME_SOURCE=/tmp/s-core-foundation/references/time \
CODEQL_CODING_STANDARDS_SOURCE=/tmp/s-core-foundation/references/codeql-coding-standards \
CODEQL_RECONCILIATION_SOURCE=/tmp/quality-010-codeql-reconcile \
CODEQL_MISRA_COMPILED_PACK=/home/jefferson/.local/share/s-core-tools/codeql-coding-standards-2.61.0 \
CODEQL_CODING_STANDARDS_ARCHIVE=/home/jefferson/.local/share/s-core-tools/downloads/codeql-coding-standards-2.61.0/coding-standards-codeql-packs.zip \
SCORE_CODEQL_PREREQUISITE_REQUEST="$PWD/examples/quality/codeql-prerequisites.yaml" \
UV_CACHE_DIR=/tmp/s-core-quality-uv-cache \
uv run --frozen pytest --ignore=tests/integration/test_workflow_compiler_native.py -q --tb=short
```

Three native Fabro compiler tests are excluded because that runtime is not selected; the
11 existing skipped external/native checks do not establish readiness. The broad run preceded
the four new sanitizer contract cases; their focused checkpoint is recorded separately.

The environment changed during the window: `.git` is now read-only and approval unavailable.
This slice remains a reviewable worktree change; no commit is attempted under that restriction.

Bounds: controls 1 MiB; source identity selection 500 files/64 MiB; pack 5,000 regular files,
64 MiB total/16 MiB each and 10,000 directory entries; 32 dependency libraries; suite import
depth eight/16 files; depth 64/200,000 nodes; retained raw outputs 64 MiB; final record 96 MiB.
Measured process durations can differ; semantic observations and exit classifications remain stable.

Human T032, 009 T018 and protected production authority 005 T009 remain open. No publishing,
merge, release, deployment, paid model call or competing scheduler occurred.

## Current original-library capture checkpoint

[Current installed inventory](evidence/codeql-prerequisites-current.json) adds all thirteen
original library metadata byte captures, enabling immutable historical packet replay. The earlier
inventory is preserved. Current digest: `eab0d57b850891fdcb75331e8846ea72e261cf8e1d959cdb9751baf87804cf9f`.
The actual CLI still exits 1, analysis_executed false, zero accepted claims and the same fourteen
gaps. Source/pack/library counts, native source trees and installed tools are unchanged.
No CodeQL/native reporting execution or eligible-use decision is established.
