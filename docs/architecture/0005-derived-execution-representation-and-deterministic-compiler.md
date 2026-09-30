# ADR 0005: Derived execution representation and deterministic compiler

Date: 2026-09-27. Status: **Proposed; implement in 003; owner review pending**.

## Decision

Compile a rebuildable versioned projection from native catalogue + instance plan + reviewed execution mappings. Nodes retain process/scope/input/output/actor/permissions/predicates/evidence/invalidation/failure routes and bounded attempts. Origin-tag every scheduling choice separately from native obligation. Emit explicit Fabro graph/config, dependency closure, source map and compile report.

## Source evidence

[process_description: process/process_areas/safety_analysis/safety_analysis_workflow.rst](https://github.com/eclipse-score/process_description/blob/98d1d5f42dad412a09a888ea25e59c62fa6371ce/process/process_areas/safety_analysis/safety_analysis_workflow.rst); [fabro-nightly: docs/public/agents/mcp.mdx](https://github.com/fabro-sh/fabro/blob/1b4fb15281ebb724426f9e480dce48d0100ff79b/docs/public/agents/mcp.mdx)

## Alternatives considered

Treating contains/realizes as control flow is semantically wrong. Per-run LLM compilation makes process interpretation unreviewable. Hand-maintained generated graphs drift.

## Consequences

Canonical UTF-8 JSON, sorted keyed sets, preserved ordered arrays, relative logical paths and no timestamps in semantic digests. Reject unknowns, missing gates, cycles without bounds, dangling dependencies and drift. Fabro alone executes.

## Unresolved assumptions

Choose compatible Fabro release/API subset before implementation; no compiler or runtime calls in 000/001.
