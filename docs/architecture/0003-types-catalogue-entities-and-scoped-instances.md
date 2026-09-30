# ADR 0003: Types, catalogue entities and scoped instances

Date: 2026-09-27. Status: **Proposed; catalogue in 001, planning in 002; owner review pending**.

## Decision

Distinguish metamodel type definitions, native process entities of type workproduct/workflow/role/guidance, and target document instances. Keep native IDs untouched. Internal identity is source namespace + native ID + native revision. Instance identity includes source-qualified work product, target repository namespace, scope kind/ID and purpose; review purpose is mandatory to separate plan/package/analysis FDRs.

## Source evidence

[docs-as-code: src/extensions/score_metamodel/metamodel.yaml](https://github.com/eclipse-score/docs-as-code/blob/d5f3de608cdfc034952c57d40979c78d8cd35957/src/extensions/score_metamodel/metamodel.yaml); [module_template: docs/module/safety_mgt/module_safety_plan.rst](https://github.com/eclipse-score/module_template/blob/c4d4ad090c6584e58279f0e5d0b6894f7fc4cf0d/docs/module/safety_mgt/module_safety_plan.rst)

## Alternatives considered

One row per wp__ ID conflates many reviews. A fabricated work-product type for each purpose changes S-CORE semantics. Baseline-dependent instance IDs prevent stable change tracking.

## Consequences

Keep baseline hashes separate from logical identity. Template-tagged documents stay templates. 001 records definitions and observed documents; it does not derive obligatory instance plans.

## Unresolved assumptions

Purpose vocabulary must come from explicit project configuration and reviewed mappings; no universal applicability inferred from the seed list.
