# Verification contract (009)

**Status:** Proposed contract implemented with a local candidate toolchain. Owner review of the
verification and toolchain profiles is pending. No command writes sources, native files or
reference repositories, calls a model, or records a decision.

## Commands

```text
score-fabric verify design --request <design.yaml> --out <design.json> [--json]
score-fabric verify run    --request <run.yaml>    --out <run.json>    [--json]
score-fabric verify report --request <report.yaml> --out <report.json> [--json]
```

Exits: `0` complete design / passed run / `verified_on_baseline`; `1` published non-success
(`blocked` design, `failed`/`blocked` run, `failures_open`/`blocked` report); `2` malformed,
unsafe or unavailable input (including a toolchain that does not match its profile) with a
bounded diagnostic and prior output preserved.

## Requests

| Kind | Fields |
| --- | --- |
| `verification_design_request` | `profile`, `component`, `root`, `requirements[]`, `design[]`, `sources[]` (each `{path, sha256}` under `root`), `requirement_scope` (IDs or `null` for all component requirements), `protected_roots[]` |
| `verification_run_request` | `profile`, `toolchain`, `component`, `root`, `requirements[]`, `sources[]`, `tests[]`, `include_dirs[]`, `coverage`, `timeout_seconds`, `protected_roots[]` |
| `verification_report_request` | `profile`, `design_report`, `runs[]` (chronological), `safety_reports[]` (008 reports), `protected_roots[]` |

## Reason codes

Design: `DESIGN_MISSING`, `DESIGN_WORK_PRODUCT`, `DESIGN_SECTION_MISSING`, `DESIGN_DIAGRAM_MISSING`,
`PLACEHOLDER`, `UNIT_UNTAGGED`, `TAG_UNRESOLVED`, `TAG_TYPE`, `REQUIREMENT_UNIMPLEMENTED`.
Toolchain (exit 2): `TOOLCHAIN_MISMATCH`, `TOOLCHAIN_UNAVAILABLE`.
Run: `BUILD_FAILED`, `TEST_BINARY_FAILED`, `TEST_TIMEOUT`, `TEST_REPORT_MISSING`, `TEST_FAILED`,
`METADATA_MISSING`, `METADATA_VALUE`, `DESCRIPTION_EMPTY`, `VERIFIES_MISSING`,
`VERIFIES_UNRESOLVED`, `COVERAGE_UNAVAILABLE`.
Report: `FAILURE_OPEN`, `NONDETERMINISTIC_RESULT`, `ESCALATE_TO_HUMAN`, `DESIGN_BLOCKED`,
`BASELINE_MISMATCH`.

## Guarantees

- The compiler, GoogleTest header/libraries and gcov must match the toolchain profile digests and
  version strings before anything is compiled.
- Builds run in a fresh temporary directory with a minimal environment; outputs never land under
  the source root.
- Results are `local_unprotected_execution`, `assurance_eligibility: not_eligible`.
- Coverage is reported as counts with no threshold; pending obligations are always listed.
