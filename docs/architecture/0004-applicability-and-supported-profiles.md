# ADR 0004: Applicability and supported profiles

Date: 2026-09-27. Status: **Proposed; implement in 002; owner review pending**.

## Decision

Compute obligation closure from selected native process, accepted scope/classification and authorized tailoring. Each instance disposition is create/update/reuse/tailored_out/external_obligation/unresolved with source or decision evidence. Default target language policy is C++17/MISRA C++:2023; ASIL_B examples are not approved classifications or ASIL_D support.

## Source evidence

[module_template: docs/module/safety_mgt/module_safety_plan.rst](https://github.com/eclipse-score/module_template/blob/c4d4ad090c6584e58279f0e5d0b6894f7fc4cf0d/docs/module/safety_mgt/module_safety_plan.rst); [score: docs/contribute/development/cpp/coding_guidelines.rst](https://github.com/eclipse-score/score/blob/e2373d822fc2f6e9a3f8a0538904f3faa39309ea/docs/contribute/development/cpp/coding_guidelines.rst)

## Alternatives considered

Requiring every work product for every feature duplicates platform work. Inferring exclusions from security:NO or an OSS label hides independent obligations. Accepting arbitrary language/ASIL strings falsely promises support.

## Consequences

Unknown applicability blocks affected acceptance. Reuse binds exact accepted revision and freshness; OSS classification only applies where justified. Maintain a supported-profile matrix with actual evidence.

## Unresolved assumptions

No supported safety/reliability profile is established in 000; accountable classification and tailoring roles are target-specific.
