# Native source and CodeQL pack reconciliation

2026-10-01, Lisbon. This is measured source inspection for T029, without native analysis,
report generation or engineering acceptance. [Sealed observations](evidence/native-source-reconciliation.json)
supplement the earlier [installation record](evidence/tool-installation.json); its original
unverified state remains an accurate record of the installation checkpoint.

## Measured closure

- Four reference repositories remain at their reviewed commits, with clean status before
  and after inspection. Thirty-four selected policy, configuration, report, license and
  source-lock files match their recorded SHA-256 values.
- The copied Clang-Tidy configuration, sanitizer features/templates/suppressions and native
  LICENSE/NOTICE match the pinned `score_cpp_policies` bytes. S-CORE document identifiers,
  valid/draft statuses and version 1 remain intact.
- The referenced MISRA mapping CSV is absent. The native mapping document is draft;
  `mapping_state: unknown` and the null applicability denominator remain required.
- Reviewed Coding Standards commit `06dc6bc32b05152fbe94dbf341a3e854574c9df5` and the installed
  pack's declared build commit `fc4e9643243978bd52ce4481ae1eecab94dabb0b` have the same Git
  tree: `9ec80cf0baaba83c9bf3253e7c8404c50d2ccef1`. Their Git content diff is empty.
  The build commit was fetched from the [official repository](https://github.com/github/codeql-coding-standards/commit/fc4e9643243978bd52ce4481ae1eecab94dabb0b)
  into a disposable clone; the reference repository was not fetched into or modified.
- All 233 MISRA `.ql`, `.qll` and `.qls` sources match the installed pack exactly (221 queries,
  five libraries and seven suites). All 2,067 installed original pack files match the
  MISRA archive member; the separately retained source license is supplemental.
- The original release archive hash matches the installed record. The MISRA, common C++
  and reporting members contain 2,067, 1,568 and 928 files respectively. Original member,
  file-manifest, pack, lock and embedded dependency identities are retained. These are
  identities of distributed artifacts, not authenticated or reproduced build provenance.

## Reporting and unresolved prerequisites

The pinned manual requires Python 3.9 for reporting; the pinned `time` example selects 3.12.
A compatible reporting environment has not been selected or executed. The default MISRA suite
excludes native audit/default-disabled tags, and there is no `misra-cpp-audit.qls` at the pin.
No additional suite or guideline mapping was invented.

The original `time` report patch has SHA-256
`c45662cdc8845c11fb9d71d153eee5c22d9f3421e245791b249392e7f8f3ea08`.
Plain `git apply --check` returns 128 (`corrupt patch at line 13`). An explicit
`git apply --recount` succeeds in a disposable source copy: pristine `utils.py` hash
`3fea33a2f8bbfe33f5270d562864f0041f669d675d851dd91f3978022bf6917a` becomes
`202bffac54dbe1d84084a59a7f0730c9739d053905cfb783a5afb24c9556a1ef`.
The native Bazel patch implementation was not exercised. This measured transformation is
not adopted report configuration, unmodified distribution qualification or a patch-engine
compatibility claim. Reference files remain unchanged.

Source-tree equality resolves the earlier source content discrepancy. Compiled query build
provenance remains unverified. Project-use eligibility, selected primary execution,
compatible reporting and owner tool/configuration review remain unresolved. The
[official CLI documentation](https://docs.github.com/en/code-security/concepts/code-scanning/codeql/codeql-cli)
describes supported use contexts; this fabric record does not decide project eligibility.
No CodeQL database, query, report or native configuration processor was executed.

## Reproduce the read-only checks

Use existing read-only checkouts and the disposable reconciliation clone containing both
commit objects. The exact source paths below are this session's selected environment:

```bash
SCORE_SOURCE=/home/jefferson/score \
SCORE_CPP_POLICIES_SOURCE=/tmp/s-core-foundation/references/score_cpp_policies \
SCORE_TIME_SOURCE=/tmp/s-core-foundation/references/time \
CODEQL_CODING_STANDARDS_SOURCE=/tmp/s-core-foundation/references/codeql-coding-standards \
CODEQL_RECONCILIATION_SOURCE=/tmp/quality-010-codeql-reconcile \
CODEQL_MISRA_COMPILED_PACK=/home/jefferson/.local/share/s-core-tools/codeql-coding-standards-2.61.0 \
CODEQL_CODING_STANDARDS_ARCHIVE=/home/jefferson/.local/share/s-core-tools/downloads/codeql-coding-standards-2.61.0/coding-standards-codeql-packs.zip \
uv run --frozen pytest tests/integration/test_quality_native_sources.py -q --tb=short
```

Five tests exercise real selected files and Git objects. Git optional locks and fsmonitor are
disabled during reference inspection. The patch test creates and modifies only its temporary
copy. Unselected native inputs skip explicitly and cannot satisfy T029 or readiness.

Verification: five selected integration tests passed in 1.77 seconds. Ruff check and format
(442 files), mypy (107 source files), foundation consistency and `uv build` passed. Existing assessment regression remains
1,382 passed and 11 existing skips; native source verification is an additional selected gate.
Zero accepted claims; engineering readiness not_evaluated. Human T032, 009 T018 and 005 T009
remain open. This work does not authorize 011.
