# Increment 009 validation guide

**Status:** Validation steps for `score-fabric verify`. Results are in [acceptance](acceptance.md).

## Contract and local toolchain checks

```bash
uv run --frozen pytest -q tests/contract/test_verification_profile.py \
  tests/contract/test_verification_design.py tests/contract/test_verification_run.py \
  tests/contract/test_verification_report.py tests/contract/test_verification_cli.py
```

The run tests compile and execute the demo with the host toolchain. When the host does not match
`profiles/cpp17-gcc11-gtest-local-v1.yaml` they are skipped with the mismatch named; a mismatch
never falls back to another compiler.

## Pinned native re-derivation

```bash
SCORE_PROCESS_DESCRIPTION_SOURCE=<process_description at 98d1d5f> \
SCORE_MODULE_TEMPLATE_SOURCE=<module_template at c4d4ad0> \
SCORE_DOCS_AS_CODE_SOURCE=<docs-as-code at d5f3de6> \
SCORE_CPP_POLICIES_SOURCE=<score_cpp_policies at 9bcfe82> \
uv run --frozen pytest -q tests/integration/test_verification_native.py
```

## Demo

`tests/fixtures/verification/telemetry_guard/` holds the component requirements, detailed design,
C++17 sources (`src/`), the seeded off-by-one variant (`src-defect/`) and GoogleTest tests.
A passing run, the seeded failure and the fix together form the correction-loop demonstration.
