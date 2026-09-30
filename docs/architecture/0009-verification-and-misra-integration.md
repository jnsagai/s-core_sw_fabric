# ADR 0009: Verification and MISRA integration

Date: 2026-09-27. Status: **Proposed; implement in 010; owner review pending**.

## Decision

Reuse native Bazel build/tests, shared C++ policies, and time module CodeQL wrapper as source-grounded integration examples. Preserve raw diagnostics/SARIF, extraction integrity, rule/manual coverage and scoped deviations. Pin query/source/report versions together and respect their distinct licenses.

## Source evidence

[time: MODULE.bazel](https://github.com/eclipse-score/time/blob/3723ce687e4abc7d6cb4c0efdbbd30455ed7c303/MODULE.bazel); [time: tools/static_analysis/codeql_lint.py](https://github.com/eclipse-score/time/blob/3723ce687e4abc7d6cb4c0efdbbd30455ed7c303/tools/static_analysis/codeql_lint.py); [codeql-coding-standards: supported_codeql_configs.json](https://github.com/github/codeql-coding-standards/blob/06dc6bc32b05152fbe94dbf341a3e854574c9df5/supported_codeql_configs.json)

## Alternatives considered

A clean Clang-Tidy result or query-pack marketing coverage cannot establish MISRA compliance. Custom analyzer development is outside scope. Treating all guidelines as deviable is unjustified.

## Consequences

Empty/partial extraction and missing manual obligations block corresponding claims. AI can propose deviations; authorized people decide permitted scope/expiry. C++ guideline edition is not C++ language version.

## Unresolved assumptions

CLI eligibility, exact policy override, report Python3.9 environment, extraction targets and tool confidence remain to be validated. No analyzer or target C++ build run in 000.
