# ADR 0008: Safety design acceptance versus implemented closure

Date: 2026-09-27. Status: **Proposed; implement in 008; owner review pending**.

## Decision

Permit distinct scoped design acceptance for mitigation concept and final closure only with implementation/verification/manual evidence and authorized review. FMEA/DFA roles draft separate native analyses; missing mitigation loops through reviewed requirement/AoU/architecture changes and re-analysis.

## Source evidence

[module_template: docs/module/safety_mgt/module_safety_analysis_fdr.rst](https://github.com/eclipse-score/module_template/blob/c4d4ad090c6584e58279f0e5d0b6894f7fc4cf0d/docs/module/safety_mgt/module_safety_analysis_fdr.rst); [module_template: score/component_example/docs/safety_analysis/dfa.rst](https://github.com/eclipse-score/module_template/blob/c4d4ad090c6584e58279f0e5d0b6894f7fc4cf0d/score/component_example/docs/safety_analysis/dfa.rst)

## Alternatives considered

A single sufficient flag hides missing implementation evidence. Generic RPNs or template shared-resource exclusions introduce ungrounded policy. Converting every defect into an AoU transfers responsibility without justification.

## Consequences

Native valid/sufficient promotion must obey source semantics and trust policy. Record exclusions and dependencies with rationale. Verification supports but cannot decide adequacy.

## Unresolved assumptions

Exact review independence and sufficiency timing must be reconciled for each adopted target template/profile.
