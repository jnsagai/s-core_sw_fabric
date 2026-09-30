# Increment 010 research

## Native import/extraction measurements (2026-09-30)

The authorized US2 slice inspected pinned Coding Standards SARIF schema, diagnostic queries,
CSV decoder and reporting source read only; [exact source/license hashes](evidence/native-import-research.json)
bind commit `06dc6bc32b05152fbe94dbf341a3e854574c9df5`. The native integrity report includes
error/file counts and a successfully extracted file listing. Import checks those against the
independent manifest; native compliance summaries remain supporting bytes without decision authority.
The parser implements a documented bounded subset of
[SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html);
fixtures additionally validate against the full schema at the native pin.

Fresh real Clang-Tidy, Cppcheck and GCC sanitizer outputs were imported with their original run
and bytes retained. Clang-Tidy emits no fixes YAML on a clean run; empty stdout/stderr can be
bound to its recorded successful phase, without manufacturing YAML. Every import stays
unverified even when declared structural scope is adequate. No CodeQL query/reporting script
was executed. See [validation](native-import-acceptance.md).

## Complementary adapter measurements (2026-09-30)

The subsequent authorized Cppcheck/ASan/UBSan slice measures actual local probes and seeded/fresh
corrected runs; see [validation](complementary-acceptance.md) and its nine original-output records.
GCC 11.4 native `asan` and `ubsan_gcc` selections use flags derived from the pinned
`sanitizers/features/BUILD.bazel`, including implied debug symbols. The native runtime templates
are retained exactly and rendered with disposable suppression paths. Selected native suppression
files contain only comments. Active rules require review and block this adapter slice.
Actual ASan and UBSan defects each return native exit 55; corrected binaries return 0.
Cppcheck XML v2 preserves nullPointer/error/CWE and every native location. These measurements
establish local complementary capability, not MISRA mapping or a qualified system build closure.
Native assets retain their source IDs, commits, hashes and Apache-2.0 notices. Tool profiles
separately hash compiler helpers, sanitizer libraries, Cppcheck standard configuration and license
assets. No reference repository build or source hook runs.

Date: 2026-09-30. Research inspected read-only locked checkouts. The Spec Kit planning workflow
used two research agents for native policies/tool capabilities and the CodeQL source example.
No engineering decision was accepted. The user separately authorized installation of Clang-Tidy
and CodeQL during planning.

## Decision 1 — Preserve the native target policy and missing mapping

**Decision:** Bind `score` `e2373d822fc2f6e9a3f8a0538904f3faa39309ea` and
`score_cpp_policies` `9bcfe8296038569a0ff7627fb8ce7a189018a7b3`. Preserve native document IDs/statuses.
`doc__cpp_coding_guidelines` and `doc__cpp_code_analysis` are valid/version 1.
`doc__cpp_misra2023_rule_mapping` is draft/version 1; its CSV directive is commented out and
`docs/contribute/development/cpp/_assets/misra_2023.csv` is absent from the pinned tree.

**Rationale:** C++17/MISRA C++:2023 is sourced; a complete native guideline applicability/mapping
matrix is not. Import only verified IDs/references from an explicitly supplied matrix; until it
exists, denominator and MISRA coverage remain unknown/blocked. Public artifacts contain no
proprietary rule text.

**Alternatives:** Inventing native rule mappings or promoting a query-pack support count to
project applicability would erase unknown obligations.

| Source within `score` | SHA-256 |
| --- | --- |
| `docs/contribute/development/cpp/coding_guidelines.rst` | `472572e9adf89fae175193f82bbb8aff6dc55bf1aa29b65357cb22d4e6b36333` |
| `docs/contribute/development/cpp/code_analysis.rst` | `b959cdaea697ad8b46b7e179fedeb5d57fc0017544393666d1bdcf79714fd367` |
| `docs/contribute/development/cpp/misra_2023_rule_mapping.rst` | `09f6d917db2001c4dd0bec60913089ed8f4533326320b3cd4cbc66e1bdf09600` |

## Decision 2 — Use installed tools as local candidates

**Decision:** Install Clang-Tidy 19.1.7 from authenticated LLVM Jammy packages and the exact
CodeQL 2.21.4 bundle declared by the pinned `time` example. Keep installations under
`~/.local/share/s-core-tools/` with commands in `~/.local/bin/`. Preserve notices there;
checked-in evidence contains identities/output, not redistributed binaries.

[Installation evidence](evidence/tool-installation.json) records LLVM package checksums verified
against the signed package index (signing key `6084F3CF814B57C1CF12EFD515CF4D18AF4F7421`) and
CodeQL bundle checksum `a94f674bb3c23ea5e9a2ad06b64847dd0277b15014d2517ecd9c41c88e6caa65`.
The [Clang-Tidy smoke test](evidence/clang-tidy-install-smoke.json) accepted the native config
and detected `clang-analyzer-core.NullDereference`, exit 1. This validates local installation
and a native analyzer finding; it does not establish MISRA rule coverage or adapter completion.

Cppcheck 2.7 is also installed. A disposable seeded probe returned native XML v2, check
`nullPointer`, severity `error`, CWE 476, multiple source locations and exit 2 with explicit
`--error-exitcode=2`. It remains an optional complementary tool. No MISRA association is inferred.

**Rationale:** `time` selects LLVM 19.1.7, while the pinned policies self-test selects LLVM 22.1.7.
Config acceptance on LLVM 19.1.7 is measured; full check expansion/version support must still be
recorded by the adapter. Existing GCC 11.4/GoogleTest identities from 009 remain candidate inputs.

**Alternatives:** Updating the reviewed source baseline or substituting a latest CodeQL release
would invalidate the declared CLI/query compatibility. A system package upgrade is unnecessary.

## Decision 3 — Reuse policy assets while measuring effective configuration

**Decision:** Import `.clang-tidy` exactly and record expanded checks, effective configuration,
local overrides and filtering. Preserve unknown/disabled required checks as gaps.

Native baseline enables analyzer/CERT/guideline/bugprone/misc/performance/readability/modernize
families; only `clang-analyzer-*` is warnings-as-errors. The README says consumers wire aspects
directly, but `defs.bzl` actually provides `make_clang_tidy_aspect`/`make_clang_tidy_test`. Source
code defines the available API. Prepending the baseline does not prove later overrides cannot
weaken it.

| Source within `score_cpp_policies` | SHA-256 |
| --- | --- |
| `clang_tidy/.clang-tidy` | `fe06da767c62270a410d08bd07cdfc13cf2e1c01c0cd31fb15ac37c515f19901` |
| `clang_tidy/defs.bzl` | `d6e22acfec425f5b42b7a96539489d755f921e5b2fb7782f781857de62f40f73` |
| `sanitizers/features/BUILD.bazel` | `3b3ec4f0ef6ac8c421e1961e60a9d19e60827b3c061361c04e1e6d45b9c4f10c` |
| `sanitizers/templates/asan.env.template` | `9e65b0d94fed741c18df299b0e4bbedbbd39f5f384b94d39721ebfcb239ff5ab` |
| `sanitizers/templates/ubsan.env.template` | `2f7f6ed76d89be308e0f9f9c3ecc3ea1e0eee8b003cc2fa2f5d7ae47c0a5c170` |

## Decision 4 — Separate sanitizer capability from applicability

**Decision:** First validate GCC-compatible ASan/UBSan execution with disposable seeded fixtures.
Read exact flags from the native feature declarations and retain every selected runtime option
and suppression hash. The GCC policy uses `ubsan_gcc`; the convenience bazelrc selects the Clang
UBSan feature. Native runtime templates use exit 55/halt-on-error. LSan/TSan/TySan applicability
and availability remain explicit until measured and selected.

**Rationale:** Runtime library presence is insufficient evidence that instrumentation/execution
worked. Blanket suppression inheritance could hide relevant findings.

## Decision 5 — Constrain the CodeQL source example

**Decision:** Treat `time` `3723ce687e4abc7d6cb4c0efdbbd30455ed7c303` as an inspected adapter
example. Pair CLI 2.21.4 with Coding Standards 2.61.0 at
`06dc6bc32b05152fbe94dbf341a3e854574c9df5`. Record compiled pack/suite/library/config identities.
User authorization installs software; project-use eligibility remains unresolved. See the
[CLI terms](https://github.com/github/codeql-cli-binaries/blob/main/LICENSE.md) and
[official CLI documentation](https://docs.github.com/en/code-security/concepts/code-scanning/codeql/codeql-cli).
Installed-distribution terms/notices are retained in the installation location.

The compiled MISRA pack 2.61.0 is installed separately under
`~/.local/share/s-core-tools/codeql-coding-standards-2.61.0`. Its release archive SHA-256 is
`fdddef5a7ca1c66ebdbe6c79c60c7b5b6b274dbc3c9ecbc4bb9a0a13cead20a1`.
[Pack resolution](evidence/codeql-packs-resolved.json) succeeded with the additional pack root.
The pack declares build CLI 2.21.4 and build commit
`fc4e9643243978bd52ce4481ae1eecab94dabb0b`, which differs from inspected source commit
`06dc6bc32b05152fbe94dbf341a3e854574c9df5`. At installation their relationship was unverified.
The later [read-only reconciliation](source-reconciliation.md) measures identical Git source
trees and all 233 included MISRA query/library/suite files. Compiled artifact provenance
remains unverified; source equality does not reproduce or authenticate the build.
Installation does not establish query execution.

The Coding Standards manual requires Python 3.9 for reporting/configuration; `time` uses
Python 3.12, outside that stated requirement. CLI feature support for Python 3.12 is unrelated to
this reporting requirement. `time` applies a report-source patch to add the MISRA display name;
record pristine-source/patch hashes if using it. The later disposable patch probe records
plain Git's rejection and explicit recount transformation without claiming native Bazel
patch compatibility. Such modification is not unmodified-distribution qualification.
MISRA default suite excludes audit/default-disabled checks; the pinned tree has no
`misra-cpp-audit.qls`. Never invent a suite to satisfy missing coverage.

The wrapper uses shell commands, ignores partial `cquery --keep_going` failure when labels exist,
skips testonly/incompatible targets, filters `exclude-from-incremental`, mutates `~/.codeql/packages`
and swallows report-generation failures. The configuration processor does not check its
`database index-files` return code and deletes matching XML recursively. A fabric adapter must
use bounded argument lists, independently retained phase statuses and isolated copies/user/cache
locations, and keep every exclusion visible. Wrapper exit 0 alone is insufficient.

| Source | SHA-256 |
| --- | --- |
| `time/tools/static_analysis/codeql_lint.py` | `c4d12aa3d9fb899b5451f3a886f28aef6338f36fde7b56e9801ef5619533ce4d` |
| `time/tools/static_analysis/codeql.bzl` | `d75ee9b100be67aa09f652e7449852a9ab986b1bb36dded8acbbdd7a781f82d4` |
| `time/tools/static_analysis/config.yaml` | `31b56a258fefa61b321653e2450931758c8698dc76253c0ef7b4ebc65907d536` |
| `time/third_party/codeql/codeql_coding_standards_misra.patch` | `c45662cdc8845c11fb9d71d153eee5c22d9f3421e245791b249392e7f8f3ea08` |
| `codeql-coding-standards/supported_codeql_configs.json` | `199391f73f9900f137878eefd5be6b5950afd3210650ffb70fd62f4b9b06648a` |
| `codeql-coding-standards/docs/user_manual.md` | `8ef1034c800019d968aaaf92fe452f9139222c57eb47b35a70e0f8e87548f7da` |

## Decision 6 — Preserve native output and assess completeness independently

**Decision:** Retain SARIF2.1.0, raw stdout/stderr and native reports:
`database_integrity_report.md`, `deviations_report.md`,
`guideline_recategorizations_report.md`, `guideline_compliance_summary.md`.
Native Markdown summaries are supporting output, never a complete applicability denominator.
Use expected/extracted translation-unit manifests and phase outcomes to measure integrity.

CodeQL native reporting expects one SARIF run and driver CodeQL/semanticVersion/extension pack
identity. The fabric importer must explicitly handle bounded multiple runs instead of silently
choosing one. Preserve rule tags, IDs, original obligation category, locations, fingerprints and
suppression status. Native report code counts any nonempty suppression as a deviation and
omits deviated alerts by default; its `Compliant` label cannot authenticate authority or clear
missing manual/excluded rules. Native `raised-by`/`approved-by` names/dates are source fields,
not authentication. Deviated-alert retention requires verified configuration/query selection;
the example wrapper does not establish it.

## Decision 7 — Keep engineering decisions at the 005 boundary

**Decision:** Create local draft disposition records and review packets. Replayed 005 assessments
must bind the exact draft record and source/tool/policy/finding scope before disposition use.
Production decisions remain ineligible while 005 T009 is open. Fixture-domain tests remain fixtures.
Missing adopted category/recategorization policy blocks deviation use; no implicit allowable set.

**Rationale:** Analyzer severity, SARIF suppression status and agent rationale are distinct from
approved engineering disposition. Baseline, scope and validity changes require re-evaluation.

## Remaining external prerequisites

- Reviewed guideline applicability/mapping and allowable deviation/recategorization policy.
- CodeQL project-use eligibility and genuine selected extraction/report execution with a compatible
  reporting environment; installed binary and packs do not satisfy this requirement.
- 009 T018 owner review,005 T009 protected collection/decisions, and tool confidence/qualification.

These are represented as execution/compliance prerequisites, not unspecified implementation choices.
