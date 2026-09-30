# ADR 0002: Structured native import and baseline

Date: 2026-09-27. Status: **Proposed; validate in 001; owner review pending**.

## Decision

Import Sphinx-Needs versioned JSON plus the pinned metamodel YAML/schema and an explicit source/export manifest. Select process2.1.2/docs8.2 through platform/template dependency declarations. Restore sparse fields only through the matching needs_schema defaults; preserve raw records, export keys, native IDs and integer need versions separately.

## Source evidence

[docs-as-code: src/extensions/score_metamodel/metamodel.yaml](https://github.com/eclipse-score/docs-as-code/blob/d5f3de608cdfc034952c57d40979c78d8cd35957/src/extensions/score_metamodel/metamodel.yaml); [docs-as-code: src/extensions/score_metamodel/external_needs.py](https://github.com/eclipse-score/docs-as-code/blob/d5f3de608cdfc034952c57d40979c78d8cd35957/src/extensions/score_metamodel/external_needs.py); [process_description: MODULE.bazel](https://github.com/eclipse-score/process_description/blob/98d1d5f42dad412a09a888ea25e59c62fa6371ce/MODULE.bazel)

## Alternatives considered

HTML scraping loses typed relations; broad RST regex parsing misreads code blocks and misses extensions. Mutable published main exports lack commit provenance. Independently pinning latest process/docs is not compatibility evidence.

## Consequences

001 needs genuine export fixtures and a disposable native build. Fail on unsupported envelope/schema, duplicate/ambiguous identities, unresolvable mandatory external links or selectors. Build input hashes and source mounts must accompany exports.

## Unresolved assumptions

Process standalone declares docs8.0.1; consumer resolution to8.2 requires execution evidence. No Bazel installed.
