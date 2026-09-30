# Implementation Plan: Native process catalogue

Branch: 001-native-process-catalog | Date: 2026-09-27 | Spec: spec.md
Status: implemented and verified for pinned minimal consumer; owner review pending.

## Summary

Implement a read-only, deterministic adapter over native exports and metamodel rules.
Its catalogue is a rebuildable index. A fresh native build must validate the chosen
schema/baseline before claiming complete integration.

## Technical Context

Reuse Python >=3.12, uv, PyYAML and existing package/test tooling. Decide strict model
implementation during T001-02 using explicit dataclasses/validation or a pinned schema
library only if justified; no database or service. JSON byte inputs preserve duplicate
key detection before parsing. Native build uses pinned Bazel/docs dependencies in a
disposable consumer workspace. Performance: bounded file size and record count, no
network during import; choose documented limits from actual export size before coding.

## Constitution Check

Pre/post-design: read-only native sources, no process reinterpretation, no execution
state or target artifact edits, fail closed on unknown normative schema, no models or
human acceptance synthesis. All provenance binds immutable inputs. No exception.

## Project Structure

Add only `src/score_sw_fabric/process_source/` (manifest/export readers, source mapping),
`src/score_sw_fabric/catalog/` (typed entities, resolution, canonical export), CLI command
registration, `schemas/` for validated source/catalogue schema, `tests/fixtures/native/`
with LICENSE/provenance/regeneration guide and `tests/contract/`, `tests/integration/`.
Do not create compiler/policy/approval/runtime packages in 001.

## Research and Implementation Sequence

1. Check 000 review/handoff and source hashes; preserve existing work. Prepare an isolated
   native consumer checkout at recorded pins. Inspect hooks, use pinned Bazel and separate
   output/cache dirs. Build `//:needs_json` and run `//:docs_check`; retain logs/resolution.
   If source compatibility fails, diagnose/update this plan and report partial integration.
2. Inspect genuine export envelope/keys/defaults/selectors/source mounts. Derive the minimal
   fixture from licensed source; keep source and build command alongside expected export.
3. Finalize only SourceRef/ExportManifest/NativeType/NativeEntity/Relation/Catalogue models
   against those bytes. Mark schema version and bounds explicitly; preserve original data.
4. Implement input validation then source identity, type projection, entity import, link
   resolution and deterministic serialization. Never fetch URLs or evaluate selector code.
5. Expose proposed `score-fabric catalog export --manifest PATH --out PATH [--json]`.
   Validate before atomic output replacement; don't overwrite sources or follow symlinks.
   Error diagnostics include location and remediation; preserve previous good output.
6. Run positive/negative/determinism contracts and native integration; update requirement
   evidence and supported-schema matrix. Complete consistency review and handoff to 002.

## Deliberate Boundaries

No work-product obligation derivation, scheduling edges, compiler, artifact writer,
trusted evidence collector, approval provider or release evaluator. Forward contracts
for instances/evidence/gates document intended consumers, not 001 implementation tasks.

## Blockers and Decisions

A pinned Bazelisk/Bazel 8.7.0 disposable minimal consumer verified docs-as-code 8.2.0
with process_description 2.1.2 despite the process standalone 8.0.1 request.
Full score/module_template documentation bundle builds remain unverified. Any new
selector or source-mount grammar requires a contract update and fixture.
Fabro runtime and model decisions do not block catalogue development.

## Complexity Tracking

Prefer standard library plus existing YAML dependency; add schema tooling only with a
clear validation need. Avoid custom generic knowledge-graph/query service or RST parser.
