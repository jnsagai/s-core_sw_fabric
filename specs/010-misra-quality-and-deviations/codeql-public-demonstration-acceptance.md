# Public fixed CodeQL demonstration validation

2026-10-01, resumed user-authorized 010 integration. Engineering acceptance remains pending.
The [exact contract](contracts/codeql-demonstration.md) was defined before the new validator;
T085–T088 trace this slice without closing full target execution or human tasks.

## Delivered scope

`quality run --adapter codeql` accepts a distinct `quality_codeql_demonstration_request` for
fixed labelled seeded/corrected C++ programs. Original capability/target-run requests retain
inspection-only behavior. Explicit prerequisite/compiler/reporting/license references, default
suite, disposable source/library cache, bounded native processes and shared raw capture precede
configuration/XML extraction, C++ extraction, queries, SARIF/CSV, independent extraction and
all four native reports. Selected source, pack, tool, runtime and controls are refrozen.

The examples select observed Python 3.9.25/PyYAML 5.4/pytest 7.2.0 and the explicit local recount
variant of the original upstream patch. Original plain check 128 is retained; recount check and
apply exit 0. Native patch/runtime/compiled provenance qualification remains unknown.

## Failures retained and corrected

The first public seeded execution reached native SARIF/CSV, then the importer incorrectly
classified a legitimate descriptor self-index as cyclic. The sealed
[evidence](evidence/codeql-public-initial-sarif-failure.json), digest
`1ea8f7a9b49f08cba72ffc5e0c9f2b36fbcbc4d9bd171001618a838699ef33c2`, retains original phases
and native artifacts with incomplete outcome; no native report execution is claimed for it.

Negative-first regressions cover descriptor self-indexes, embedded content/hash drift, omitted
end-line defaults, invalid columns and explicit source-root mapping. The native consumer maps
`%SRCROOT%` from the source root it passed to CodeQL, preserving original SARIF bytes. General
imports still refuse unresolved URI bases. These rules follow
[OASIS SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html),
§3.4.4–3.4.5 and §3.30.7.

The first two complete public native runs returned findings/3 and completed/0 respectively,
with adequate extraction and complete reports. The integration harness then failed because its
`verify_digest` calls omitted the required pointer argument. The
[original failed harness log](evidence/codeql-public-integration-initial.txt) is retained:
2 failed, 3 deselected, 317.18 seconds. Corrected assertions independently pass against both
retained results. The fresh corrected-harness native gate is recorded below.

## Fresh public execution evidence

The corrected integration harness genuinely invokes the public CLI against two new disposable
databases: [native gate](evidence/codeql-public-integration.txt), **2 passed, 3 deselected,
316.02 seconds**. Both sealed records and their nested inventories, all 91 raw captures per run,
full byte counts/hashes and original request/run schemas were independently verified.

| Case | Original sealed record | Native result | Extraction/reports |
| --- | --- | --- | --- |
| Seeded | [evidence](evidence/codeql-public-demonstration-seeded.json), `ea883293ab62e55593385ff3550eebf22391bef062818c6ce2df8853cbe3b0af` | `findings`, three original native results, CLI exit 1 | adequate, zero extraction errors, four complete reports |
| Fresh corrected | [evidence](evidence/codeql-public-demonstration-corrected.json), `f3123ac349e0092069b09b173b1a582cbc04dde2872776a9844019f3815471c2` | `completed`, zero native results, CLI exit 0 | adequate, zero extraction errors, four complete reports |

All required native execution phases exit 0; the original patch-check observation retains 128.
The native successfully-extracted set includes both `check.cpp` and `coding-standards.xml`;
expected C++ units are exactly `check.cpp`. Original result/rule identities, fingerprint/location
records, SARIF/CSV, configuration/XML, notices and Markdown status labels remain retained.
Inputs and original/disposable selected source/library bytes match their frozen identities
or the explicitly declared copied reporting-source transformation.

T085–T088 are complete for this scoped slice. Current total: **88 tasks, 74 complete, 14 open**.
T002/T011/T012/T078/T079 keep their full target scope open, together with the failed ASan/full
validation and human-owned reviews. No task was closed using fixtures or native clean labels.

## Verification and limits

[Final focused regression](evidence/codeql-public-regression-final.txt): **302 passed, 2 deselected,
24.18 seconds**, including genuine installed-source inspection. Request and run schemas resolve
locally; Ruff, formatting (485 files), mypy (115 source files), frozen sync (18 packages),
foundation (64 unchanged FAB IDs/19 dependency rows/local links) and offline source/wheel build
pass. The prior full suite's three native ASan failures remain preserved and unresolved.

No target sources, arbitrary commands, query selectors or engineering approvals are accepted
by this request. Fixture prerequisites never execute native analysis. Origin remains
`local_unprotected_execution`, assurance eligibility `not_eligible`, readiness `not_evaluated`
and accepted claims zero, including a completed zero-finding demonstration. Native report labels
never establish MISRA applicability, full coverage or compliance. Human reviews remain unchecked;
no scheduler, model call, merge, release, deployment or increment 011 work is introduced.

The final failure bookkeeping checks ensure that a phase prevented by budget exhaustion or
process-start failure is not labelled executed. A started report that fails, times out or truncates
its output retains its actual execution status and original failure. The focused public/SARIF
checkpoint after that fix passes **64 tests, 2.52 seconds**. Original metadata mismatches in native
SARIF/extraction are execution failures; actual selected-input drift still refuses publication.
