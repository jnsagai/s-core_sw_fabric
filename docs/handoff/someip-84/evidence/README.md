# Native trial evidence

These measurements concern the bounded SOME/IP #84 draft patch.
Engineering acceptance and native build/policy gates remain pending.
These commands were initiated directly through Codex terminal tools; there is no corresponding Fabro run or factory collector receipt.
They are local trial measurements and do not establish an end-to-end factory execution.
The structured [summary](summary.json) records tool versions, scope, results and pending reviews.
[File hashes](file-hashes.json) bind the retained measurement files.

## Regression evidence

- [Original comparison](baseline-final.txt): seven failures, six passes; exit 1.
- [Corrected comparison](final.txt): all 13 focused tests pass; exit 0.
- [UBSan](ubsan-final.txt): all 13 tests pass; exit 0.
- [Runtime syntax check](runtime-syntax.txt): exit 0; the existing GoogleMock deprecation warning remains visible.
- [Local Clang-Tidy trial](clang-tidy-local.txt): exit 0 with `-*,clang-analyzer-*,bugprone-use-after-move` on the changed comparison translation unit.
- [Native Clang-Tidy configuration verification](clang-tidy-config.txt): exit 1; unknown names/options and folded YAML comment text are preserved.
- [Bazel](bazel.txt) and [pre-commit](pre-commit.txt): exit 127, commands unavailable locally.
- [Fabric foundation](fabric-foundation-final.txt) and [package build](fabric-build-final.txt): exit 0; packaging used existing pinned dependencies copied into a disposable writable cache for offline operation.

## CodeQL evidence

CodeQL 2.21.4 completed the installed public `codeql/cpp-queries@1.4.1` C++ security-and-quality suite (181 queries).
The final extraction compiled and linked the focused executable and executed all 13 tests.
It contains two native production translation units, the focused regression translation unit, and the pinned GoogleTest implementation and main translation units.
The exact [build command](build-command.txt), [creation log](codeql-create-linked.txt), [test results](codeql-build-tests.json), [analysis log](codeql-analyze-linked.txt) and complete [SARIF](codeql-linked.sarif) are retained.

The analysis reports 35 findings: 33 in GoogleTest and two at the new parameterized-test registration macro.
The latter are `cpp/unused-static-function` and `cpp/unused-static-variable` findings at `INSTANTIATE_TEST_SUITE_P`.
Execution evidence confirms that all nine generated parameter combinations run.
Inference for review: these two findings appear to reflect CodeQL's treatment of GoogleTest registration; their engineering dispositions remain pending.
All findings are preserved, with no suppressions or accepted deviations.
No finding points to the modified production comparison in this extraction.

The tool reports seven native files scanned out of 150 C/C++ files for this invocation.
This is a focused executable analysis; the complete SOCom library, gateway daemons and eight new runtime cases still require native build validation.
This public suite supplies security/quality evidence; MISRA applicability and qualification remain pending.

## Earlier attempts

- The first 2 GiB analysis [ran out of Java heap](codeql-analyze.txt), exit 99; the original [creation log](codeql-create.txt) is retained.
- A fresh 6 GiB database with only the three native translation units completed with 16 findings: [creation](codeql-create-final.txt), [analysis](codeql-analyze-final.txt), [SARIF](codeql-final.sarif).
- The final complete focused build used one analysis thread and 6 GiB, completed successfully, and retained the larger dependency result set.

The earlier results are historical attempts; use the linked executable SARIF for the current candidate trial.
