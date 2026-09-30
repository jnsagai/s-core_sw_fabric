# Implementation Plan: C++ quality, MISRA, and deviations

**Branch**: `010-misra-quality-and-deviations` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: [009 handoff](../../docs/handoff/009-to-010.md), FAB-039–042, [research](research.md).

## Current implementation slice

The user authorized Clang-Tidy and then Cppcheck/ASan/UBSan adapters. See the
[Clang-Tidy contract](contracts/clang-tidy.md), [complementary contract](contracts/complementary-tools.md),
[initial acceptance](acceptance.md) and [complementary validation](complementary-acceptance.md).
Sixteen scoped tasks and US2 T014–T018 capture completed work, including
[native import/extraction](native-import-acceptance.md) under [its exact contract](contracts/native-import.md).
The subsequent [draft/correction slice](disposition-acceptance.md) implements scoped T049–T052
under [its exact contract](contracts/dispositions.md). The subsequent
[005 decision bridge](decision-acceptance.md) implements T020/T022 and scoped T053–T056
under [its exact contract](contracts/decisions.md). The remaining plan is outstanding for
CodeQL execution, coverage and engineering review authority.

## Summary

Add `score-fabric quality capabilities|run|import|disposition|decision-subject|decision|packet|assess`.
Use strict version 1 selections,
existing guarded publication/digests and disposable copies. Import native policy provenance and
measure local Clang-Tidy 19.1.7, optional Cppcheck 2.7 and GCC 11.4 ASan/UBSan. Preserve native YAML/XML,
raw diagnostics and immutable run outputs. Ingest SARIF and supporting CodeQL reports with separate
extraction/phase checks. Build an explicit guideline matrix, disposition history and human review
packet. Compliance remains blocked when coverage/applicability, CodeQL eligibility/execution,
manual reviews or protected 005 evidence are missing.

## Technical Context

**Language/Version**: Python >=3.12 for fabric; C++17 target; separate pinned Python 3.9 reporting
candidate for Coding Standards 2.61.0.

**Primary Dependencies**: Existing PyYAML/stdlib, strict input/digest/path/copy readers,004 native
indexing and 005 assessment replay. No new database or scheduler. Installed local Clang-Tidy 19.1.7,
CodeQL 2.21.4 plus compiled MISRA pack 2.61.0; compiler/test identities from 009 are candidate inputs.

**Storage**: Sealed JSON manifests with file SHA-256 references and bounded base64 original-output
bytes for portable closure; disposable workspaces/caches removed after collecting outputs.

**Testing**: Contract tests for strict envelopes, Clang YAML, Cppcheck XML and bounded SARIF2.1.0
normalization, expected/extracted units, coverage and scoped 005 decisions. Real seeded Clang-Tidy,
Cppcheck and ASan/UBSan integration. Env-selected CodeQL/native report integration requires exact
binary/pack/source selections and explicit eligible use; absence remains recorded, never a fixture
substitution. Negative imported records are labelled fixtures.

**Target Platform**: Linux x86_64 local candidate.

**Project Type**: Existing Python package/CLI.

**Performance Goals**: One bounded component analysis at a time; finite timeout/file/output/query
budgets. No throughput benchmark or new scheduling loop.

**Constraints**: Reference repositories read-only; inspected hooks before any disposable native
build. No shell commands supplied by requests. Original license notices retained; MISRA text
external. Guideline denominator unknown by default. Production005 decisions unavailable. Clang19
config acceptance measured, policy self-test uses22.1.7; record effective check availability.

**Scale/Scope**: 009 synthetic component plus seeded quality/sanitizer defects. No target release,
review acceptance, qualification, new analyzer, live model call or automatic continuation to011.

## Constitution Check

| Principle | Before research / after design |
| --- | --- |
| I,III Native authority and sourced policy | Preserve document IDs/status/pins and absent CSV; no invented mapping, suite or allowed deviation category |
| II,XII Portable record/reproducibility | Retain native bytes/notices and exact source/tool/config/output identities, independently readable without Fabro |
| IV Human accountability | Drafts and native names do not authenticate decisions; replay005 and exact scope/validity; human tasks unchecked |
| V,VI Deterministic checks/fail closed | Expected-set comparison, phase failures, missing denominator/manual/primary capability block corresponding claims |
| VII Traceable changes | Bind findings/dispositions to source/tool/query/suite/policy/construct, preserve corrections/history and stale use |
| VIII One runtime | Single command adapters, Fabro retains execution/run-state ownership; no competing scheduler |
| IX,X Bounded execution/increments | No paid model calls; bounded commands/paths; detailed tasks010 only |
| XI Truthful evidence | Local installation smoke, local analysis, raw imports, fixtures and replayed 005 evidence labelled separately |

Both reviews pass as a design proposal. Required owner decisions and tool confidence remain open
prerequisites, without a constitutional exception.

## Project Structure

```text
specs/010-misra-quality-and-deviations/
  spec.md plan.md research.md data-model.md quickstart.md tasks.md
  checklists/requirements.md contracts/quality.md evidence/*.json
src/score_sw_fabric/quality/
  __init__.py models.py profile.py capabilities.py runner.py
  native_outputs.py extraction.py coverage.py dispositions.py packet.py assessment.py
profiles/s-core-quality-v1.yaml
profiles/cpp17-quality-local-v1.yaml
schemas/quality-*.schema.json
tests/quality_support.py
tests/fixtures/quality/{seeded,corrected,sanitizers,sarif,extraction,dispositions}/
tests/contract/test_quality_*.py
tests/integration/test_quality_tools.py
tests/integration/test_quality_native_sources.py
tests/integration/test_quality_codeql.py
```

**Structure Decision**: A package beside009verification with shared existing infrastructure.
CodeQL invocation remains an explicit mode of the bounded runner after prerequisite validation;
no copies of native wrappers become new fabric authority.

## Complexity Tracking

No constitutional violations. Multiple native output formats are required by the selected tools;
one normalized finding representation keeps source-result provenance without pretending each
original format is SARIF. Missing capabilities are data in assessments, not alternate hidden policy.
