# Increment 010: installed Python 3.9 and native reporting

2026-10-01. This extends the [earlier native demonstrations](codeql-native-demonstration-acceptance.md)
after the user installed the interpreter and pinned packages from the normal host terminal.
The earlier DNS failures remain historical evidence. Python installation is now verified.

## Interpreter and dependencies

Independent execution confirms Python 3.9.25, PyYAML 5.4 and pytest 7.2.0 in
`.tools/codeql-reporting-venv`. The [candidate profile](../../profiles/python39-codeql-reporting-local-v1.yaml)
selects a regular byte-identical interpreter copy inside that environment and 22 observed
runtime assets. Physical paths avoid symlink installation aliases. Original user-installed
files remain intact. These identities are measured selections, not publisher authentication,
complete runtime closure or tool qualification. The fabric still uses Python >=3.12 and its
unchanged frozen dependencies. The primary CodeQL prerequisite configuration remains unchanged.

The [reproduction program](evidence/measurement-scripts/native_codeql_demonstration.py) accepts
the explicit reporting profile under the [internal contract](contracts/codeql-native-phases.md).
It independently checks the three versions, freezes profile/runtime bytes and copies original
Git-blob-verified scripts, common/report query sources, supported-version configuration and
LICENSE into fresh disposable work. It executes no project hooks or reference-repository writes.

The synthetic `coding-standards.yml` contains only `report-deviated-alerts: true`. Original Python
conversion creates retained XML; independent XML indexing exits 0. No deviation, permit,
recategorization or approval is introduced. Native reporting runs after independently measured
successful `check.cpp` extraction and zero extraction errors. All generated Markdown files are
captured before a reporting failure is propagated.

## Original failures preserved

- [First copy omission](evidence/codeql-python39-missing-query-source.json): reporting creates
  the database integrity report, then fails because a required native common query was absent
  from our disposable copy. The program now copies the complete reviewed `cpp/common/src` tree.
- [Original source report failure](evidence/codeql-python39-original-report-failure.json): all
  configuration/index/compile/query/interpretation/extraction phases succeed. Native reporting
  runs for 111.98 seconds and exits 1 with `KeyError: 'misra'`. Integrity, deviation and
  recategorization reports are retained; the compliance summary contains only a partial header.
  This is failed reporting, regardless of those partial files or the successful outer queries.

The original failure record digest is
`32a3eb33d09a0b86d109601740b55107a2691e49cd4a212de49b3352ba4354e2`.
The inspected `time` example supplies a report-source patch adding the missing MISRA display
name. Its original SHA is
`c45662cdc8845c11fb9d71d153eee5c22d9f3421e245791b249392e7f8f3ea08`.
The original patch has malformed hunk counts: plain Git check refuses it. The explicit
reproduction-only recount option retains that refusal, then separate recount check/application
phases, original/transformed source hashes and exact bytes. Only disposable `utils.py` changes.
This transformation does not establish the native Bazel patch engine's compatibility.

## Measured local patch variant

The [seeded complete run](evidence/codeql-python39-patched-seeded.json) succeeds with the
explicit recount variant: configuration conversion, XML indexing, traced compilation, query
execution, SARIF/CSV interpretation, independent extraction and native reporting all exit 0.
The retained original plain-patch check exits 128; both recount phases exit 0. All four native
Markdown reports are present and untruncated. Three real native findings remain. Extraction
retains both `check.cpp` and `coding-standards.xml`; the expected C++ unit is confirmed and
extraction errors are empty. Native statuses and MISRA identifiers remain unchanged.

The [fresh corrected run](evidence/codeql-python39-patched-corrected.json) repeats the full
pipeline on a new source baseline and fresh database. It retains zero findings, successful
`check.cpp` and generated XML extraction, no extraction errors, and all four complete native
reports. Its digest is
`79841cab5cf073a5af6496e51c8c55a344600e8ad02b1f1f3dc3e59f9ee5341a`.
Both patched runs preserve every phase status, full original output hashes and source variant
identities. Their seals, streams and all four report artifacts were independently checked
after copying into repository evidence. The original failure outputs are retained alongside them.

Seeded record digest:
`fec2b7af170c3df8012222d4c71a88988942299f79c114aac4c913834942bc5f`.
Original `utils.py` SHA:
`3fea33a2f8bbfe33f5270d562864f0041f669d675d851dd91f3978022bf6917a`.
Transformed disposable `utils.py` SHA:
`202bffac54dbe1d84084a59a7f0730c9739d053905cfb783a5afb24c9556a1ef`.
All other copied native source hashes, original reference bytes, profile/runtime identities,
compiler and compiled-pack manifests are checked again before publication. The native summary
is supporting output: its individual `Compliant` labels do not prove applicability, omitted
audit/default-disabled checks, manual review or MISRA compliance.

## Verification boundary

The pure native component still passes all 35 contract cases. The combined focused suite passes
**214 cases, 3.63 seconds**. Mypy including the reproduction program passes **115 source files**.
Frozen synchronization checks 18 fabric packages; Ruff and formatting pass (481 files),
foundation consistency passes (64 unchanged FAB requirements, 19 dependency rows and local
links), and offline sdist/wheel build passes. Diff whitespace checks pass. The historical full gate
still has three ASan runtime failures; installing Python does not change that runtime.

Full public execution and T011/T012/T078/T079 remain incomplete. The software demonstrations
retain synthetic source origin, zero accepted claims and `engineering_readiness: not_evaluated`.
Target eligibility, native source/compiled confidence, applicability, audit/manual obligations
and authenticated engineering acceptance remain separate unresolved requirements.
Task count remains 70/84 complete, 14 open. Human-owned task markers remain unchanged.
