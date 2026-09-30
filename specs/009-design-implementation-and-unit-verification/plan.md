# Implementation Plan: Detailed design, implementation and unit verification

**Branch**: `009-design-implementation-and-unit-verification` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

## Summary

Add `score-fabric verify design|run|report`. A verification profile pins the native S-CORE
verification metadata rules, source tags, detailed-design template sections and implementation
inspection checklist. A toolchain profile records the local candidate compiler, GoogleTest,
gcov and the selected levels of the pinned `score_cpp_policies` GCC warning policy with digests.
`design` checks the native detailed design and `req-Id` source tags against component
requirements. `run` builds and tests the C++17 telemetry freshness guard in a disposable directory,
parses the GoogleTest XML with native result classes, checks test metadata, maps results to
requirements and imports gcov coverage. `report` keeps run history, routes failures, detects
same-baseline nondeterminism, attaches 008 mitigation context, emits the inspection packet and
lists pending obligations. Results are local unprotected execution, never 005 evidence.

## Technical Context

**Language/Version**: Python >=3.12 (fabric); C++17 (demo).

**Primary Dependencies**: Existing strict readers, canonical digests, guarded publication, 004 RST
scanner and 008 native reader. Local candidate toolchain: GCC 11.4.0 (`/usr/bin/g++`), GoogleTest
1.11.0 system package, gcov 11.4.0. Native pins: `process_description` `98d1d5f`, `module_template`
`c4d4ad0`, `docs-as-code` `d5f3de6`, `score_cpp_policies` `9bcfe82`.

**Storage**: Sealed JSON outputs; builds in a fresh temporary directory removed after the run;
bounded raw diagnostics embedded in the run record.

**Testing**: Contract tests for profiles, design checks, XML/metadata parsing, requirement
matrix, history/nondeterminism/escalation and reports; real compile-and-test runs of the demo
(pass, seeded failure, fix) gated on the local toolchain matching the profile; an env-gated test
re-deriving the warning flags and native rules from pinned checkouts.

**Constraints**: Bazel and the S-CORE toolchain are unavailable offline; the local toolchain is a
labelled candidate. The pinned policy's `all` level contains four flags GCC 11 rejects, so the
profile selects `minimal` + `strict` + warnings-as-errors and records `all` as unavailable. No
coverage threshold is invented. Time is injected through the demo interface; no host timing is
measured. The run never writes under the source root.

**Scale/Scope**: One component, one test binary. MISRA/static analysis (010), integration (012),
security (013), release (014+) and protected collection (005 T009) remain pending.

## Constitution Check

| Principle / gate | Result |
| --- | --- |
| Native authority, explicit policy (I, III) | Metadata rules, tags, template, checklist and warning flags cite pinned sources; the toolchain substitution is explicit |
| Portable record (II) | Runs bind digests and keep raw diagnostics |
| Human accountability (IV) | Inspection checklist unanswered; no acceptance recorded |
| Deterministic checks / fail closed (V, VI) | Toolchain mismatch refuses; failures, nondeterminism and metadata faults block |
| Traceable changes (VII) | Source/test/tool digests and requirement links per result |
| One runtime (VIII) | No scheduler; the adapter is a single deterministic command |
| Bounded AI (IX) | No model call; code written by the implementer |
| Incremental delivery (X) | FAB-036–038 only; 010+ listed pending |
| Truthful evidence (XI) | `local_unprotected_execution`, not 005 evidence |
| Reproducibility (XII) | Pinned sources; disposable build dirs; references read-only |

No constitutional exception; the local toolchain substitution is recorded as a limitation.

## Project Structure

```text
src/score_sw_fabric/verification/{__init__,profile,toolchain,design,runner,report}.py
profiles/s-core-verification-v1.yaml, profiles/cpp17-gcc11-gtest-local-v1.yaml
schemas/verification-*.schema.json
tests/fixtures/verification/telemetry_guard/{docs,src,tests}/ and src-defect/
tests/verification_support.py, tests/contract/test_verification_*.py,
tests/integration/test_verification_native.py
```

## Complexity Tracking

No violations. A direct compiler invocation (no CMake, no generated build system) is the minimum
adapter while Bazel is unavailable; it is replaced by native Bazel targets when selected.
