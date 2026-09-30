# Increment 009 verification research

**Source baseline:** Read-only inspection of the 000-locked checkouts in
`/tmp/s-core-foundation/references` (clean at their pins) and the local host toolchain.

## Decision 1 — Native test metadata and result classes

`gd_req__verification_link_tests` (`verification_process_reqs.rst`,
`e8969129de240560a88c9b69b1352b8068bdb815240dc8a39a2866d5dd6a3144`) defines `PartiallyVerifies`,
`FullyVerifies`, `Description`, `TestType` (`fault-injection`, `interface-test`,
`requirements-based`, `resource-usage`) and `DerivationTechnique` (`requirements-analysis`,
`design-analysis`, `boundary-values`, `equivalence-classes`, `fuzz-testing`, `error-guessing`,
`explorative-testing`). `gd_req__verification_checks` requires `TestType`/`DerivationTechnique`,
a non-empty description, and unit tests linking at least one component requirement;
`gd_req__verification_checks_extended` requires requirement links for `requirements-based` tests.
The C++ template sets them with GoogleTest `RecordProperty` (`verification_templates.rst`,
`c02d00d7…641c`). The docs-as-code parser (`xml_parser.py`, `bc20ae47…a596`) classifies
`<error>` and `<failure>` as `failed` and `<skipped>` as `skipped`.

## Decision 2 — Native source tags

`scripts_bazel/source_code_link_parser.py` (`3ffda02e…bf6`) recognises `# req-Id:`,
`// req-Id:`, `# req-traceability:` and `// req-traceability:`, splitting IDs on commas and spaces.
The fabric uses the same tags and splitting.

## Decision 3 — Detailed design template

`detailed_design_example.rst` (`module_template`) realizes `wp__sw_implementation` and has the
sections "Description", "Rationale Behind Decomposition into Units", "Static Diagrams for Unit
Interactions" (a `uml` or `image` directive) and "Units within the Component"; units are implied by
file path. The implementation inspection checklist `chklst_impl_inspection.rst`
(`e0c4f070…9dee`) lists `IMPL_01_01…IMPL_03_02` (8 items).

## Decision 4 — Local candidate toolchain and pinned warning policy

Bazel and the S-CORE toolchain are not available offline. The host has GCC 11.4.0, GoogleTest
1.11.0 (`libgtest-dev`) and gcov 11.4.0. GoogleTest 1.11 writes `RecordProperty` values as
`<properties><property name value/>` in its XML output (verified). `score_cpp_policies`
`warnings/gcc/args/linux/BUILD` (`90a434a2…ba05`) defines `minimal`, `strict` and `all` levels plus
`warnings_as_errors`. GCC 11 accepts every `minimal`/`strict`/`warnings_as_errors` flag but rejects
`-Warray-compare`, `-Wdangling-pointer=2`, `-Winfinite-recursion` and `-Wuse-after-free=2` from `all`.
The profile selects `minimal` + `strict` + `warnings_as_errors` and records `all` as unavailable.

## Decision 5 — Evidence origin

The fabric's runner is not a protected collector (005 T009), so each result is
`local_unprotected_execution` with `assurance_eligibility: not_eligible`. It can inform review but
cannot be 005 evidence, design acceptance or closure.

## Decision 6 — History semantics

A failure is resolved only by a pass on a different source baseline digest. Differing results for
the same full baseline (sources, tests, toolchain, flags) are `NONDETERMINISTIC_RESULT`. The
attempt budget (profile, 3) escalates to a human.

## Remaining unknowns

- Native Bazel build/test targets and the S-CORE toolchain.
- Sanitizers, Clang-Tidy, CodeQL/MISRA (010), integration (012).
- Coverage expectations per ASIL from an approved verification plan.
