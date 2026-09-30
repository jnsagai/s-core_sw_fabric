# ADR 0006: Native artifact ownership and traceability

Date: 2026-09-27. Status: **Proposed; catalogue in 001, edits in 004; owner review pending**.

## Decision

Keep RST/native needs authoritative. Preserve wrappers, child statuses, IDs, relation directions, source locations and selector text. Namespace external records internally without rewriting native IDs. Measure links against expected obligation sets, including missing items; backlinks and prose links are distinct.

## Source evidence

[docs-as-code: src/extensions/score_metamodel/metamodel.yaml](https://github.com/eclipse-score/docs-as-code/blob/d5f3de608cdfc034952c57d40979c78d8cd35957/src/extensions/score_metamodel/metamodel.yaml); [module_template: score/component_example/docs/safety_analysis/fmea.rst](https://github.com/eclipse-score/module_template/blob/c4d4ad090c6584e58279f0e5d0b6894f7fc4cf0d/score/component_example/docs/safety_analysis/fmea.rst)

## Alternatives considered

Exporting RST from an authoritative proprietary JSON store is lossy. Global draft/stale statuses violate native type constraints. Counting only discovered links rewards deletion.

## Consequences

Wrappers allow draft/valid/invalid while analyses allow valid/invalid. Staleness belongs to derived assessment. Source maps retain mounted docname and verified checkout-relative path separately; unavailable line/path stays explicit.

## Unresolved assumptions

Round-trip editing and source mapping must be validated in 004; 001 is read-only ingestion.
