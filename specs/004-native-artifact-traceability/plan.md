# Implementation Plan: Native artifact traceability

**Branch**: `004-native-artifact-traceability` | **Date**: 2026-09-28 |
**Spec**: [spec.md](spec.md)

**Input**: The clarified 004 specification, brief §10 and §20.7, FAB-016–FAB-018,
the completed 003 handoff, the pinned native source lock, and actual S-CORE
metamodel/templates. Status: planning complete; implementation and owner review pending.

## Summary

Add an offline native-artifact adapter that reads a bounded immutable target snapshot,
reconciles exact RST directive spans with a native Sphinx-Needs export, and produces a
source-qualified artifact index. It can realize only explicitly requested template-based
creates and preimage-bound directive edits into an isolated candidate overlay, validate that
overlay with the pinned native documentation stack, derive expected trace obligations from the
sealed 002 plan plus validated 003 package through reviewed trace rules, and report coverage,
drift, and conservative impact.

Native RST remains authoritative. The derived JSON records are indexes, candidate transport,
and reports; they cannot invent engineering content, approve artifacts, accept evidence, alter
production targets, or use workflow node IDs as native IDs.

## Technical Context

**Language/Version**: Existing Python >=3.12 package. Native target content is UTF-8 RST plus
bounded supporting files; schemas use JSON Schema draft 2020-12.

**Primary Dependencies**: Existing Python standard library and PyYAML 6.0.3; no new runtime
package. Native validation invokes an exact profiled Bazel 8.7.0/Bazelisk 1.29.0 boundary with
docs-as-code 8.2.0, process-description 2.1.2, Python 3.12, and Sphinx-Needs 8.3.1. The active
metamodel file is pinned by SHA-256
`fe6a3b6af5ea69271e53c57e3a1694dc69d6ff3df16bd1505dc7242db9976290`.

**Storage**: Immutable local inputs; canonical JSON indexes/reports; and a sealed candidate
overlay containing every new/changed native text file plus exact bindings for every unchanged
snapshot file. Native candidate trees and build outputs exist only in disposable validation
directories. No database, service, production checkout mutation, or runtime state.

**Testing**: Existing pytest 9.1.1, Ruff 0.16.9, strict mypy 2.3.1, foundation checker, and
offline wheel build. Contract tests exercise source scanning, metamodel validation, edit
preservation, obligation denominators, relation typing, impact propagation, canonical identity,
and path/limit failures. Integration tests require a real locked native `needs_json` plus
`docs_check` run in a disposable fixture consumer; a skipped native run cannot complete 004.

**Target Platform / Project Type**: Offline Linux CLI/library in the existing single Python
package, with an external native documentation validator. Reports remain readable without Fabro.

**Performance Goals**: Use bounded single-pass source scanning, indexed joins, and sorted graph
traversal. Demonstrate deterministic completion at every declared maximum and record elapsed time
and peak output size; do not claim an unmeasured latency SLA.

**Constraints**: At most 64 MiB per control input or emitted package, 10,000 target files,
64 MiB declared target content, 2 MiB per text file, 100,000 wrappers/needs, 500,000 native
relations, 100,000 expected obligations, 10,000 edit operations, and 20,000 findings. Native
validator output is capped at 8 MiB and 1,800 seconds. Inputs are read-only; paths are relative,
unique, case-unambiguous, and free of traversal, symlinks, and hardlink aliases. Output replacement
occurs only after all required semantic and native checks pass. Host paths, timestamps, locale,
randomness, and build cache state do not affect semantic identity.

**Scale/Scope**: Profile/schema version 1 supports exact `document` wrappers and a reviewed subset
of native feature/component requirement, architecture, AoU, safety/security-analysis, test-case,
and verification-report types. The pinned S-CORE checkout currently contains 436 documentation
files (13,903,875 bytes), including 304 RST files (1,708,330 bytes), a largest RST file of 51,010
bytes, and 1,576 directive starts. Representative acceptance covers feature, component, and
analysis documents, create and update candidates, allocation and verification paths, missing
obligations, wrapper/child failures, direct drift, and conservative impact.

## Constitution Check

*GATE: Passed before research and after Phase 1 design.*

| Principle / gate | Pre-research decision | Post-design result |
| --- | --- | --- |
| Native authority and explicit policy (I, III) | RST, pinned metamodel, templates, and reviewed profiles define semantics | Preserved; JSON is derived, workflow paths are never native identity, and every edit/trace rule is source-cited |
| Portable record and one runtime (II, VIII) | Emit rebuildable indexes/reports and no scheduler/run state | Preserved; candidate overlays bind native sources and reports need no Fabro |
| Human accountability and truthful evidence (IV, XI) | Structural/native validation creates candidates only | Preserved; approval, evidence trust, adequacy, and readiness remain `not_evaluated` |
| Deterministic checks and fail-closed readiness (V, VI) | Reconcile source scan with native export and block missing mandatory obligations | Preserved; native build success cannot override semantic, coverage, or drift failures |
| Traceable changes and provenance (VII, XII) | Bind snapshot, plan, package, profile, template, preimage, edits, outputs, and validator | Preserved; full source map, stable denominator, revision fingerprints, diff/drift, and impact report are required |
| Bounded AI and increments (IX, X) | No provider call; realize only explicit typed content and stop before 005/006 | Preserved; no model capability or trusted channel exists in 004 |
| Reference immutability (XII / workflow) | Read pinned sources only and build disposable copies | Preserved; native materialization and Bazel outputs are isolated and input aliases are rejected |

No constitutional exception is required. The constitution, production execution mapping, artifact
mapping, and trace profile retain their actual review states; planning does not ratify them.

## Project Structure

### Documentation delivered in this planning step

```text
specs/004-native-artifact-traceability/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── artifacts.md
└── checklists/
    └── requirements.md
```

`tasks.md` was generated in the subsequent Spec Kit step and is the implementation work breakdown.

### Planned source code

```text
src/score_sw_fabric/
├── artifacts/
│   ├── __init__.py
│   ├── models.py          # strict request/profile/index/candidate/report records and limits
│   ├── reader.py          # bounded inputs, versions, digests, closure, path and alias checks
│   ├── rst.py             # lossless directive spans and preimage-bound scoped transformations
│   ├── index.py           # source/native-export reconciliation and wrapper/need index
│   ├── edit.py            # template realization, typed edit application, round-trip comparison
│   ├── obligations.py     # plan/package/output classification and stable expected set
│   ├── trace.py           # typed-path matching, allocation/verification coverage and report
│   ├── impact.py          # reverse dependencies and conservative impact expansion
│   ├── diff.py            # deterministic index and artifact diffing
│   ├── native.py          # isolated locked Bazel build/export and bounded receipt
│   ├── package.py         # overlay closure, canonical identity and protected publication
│   └── drift.py           # direct-output versus reviewed-source/profile change detection
└── cli.py                 # artifact index/candidate/validate/trace/diff/drift commands

schemas/
├── target-snapshot.schema.json
├── artifact-request.schema.json
├── native-artifact-profile.schema.json
├── trace-profile.schema.json
├── native-artifact-index.schema.json
├── artifact-candidate.schema.json
├── artifact-report.schema.json
└── artifact-diff.schema.json

profiles/
├── s_core_native_artifacts_v1.yaml
└── s_core_native_build_v1.yaml

policies/
├── s_core_artifact_mapping_v1.yaml
└── s_core_trace_profile_v1.yaml

tests/
├── artifact_support.py
├── contract/
│   ├── test_artifact_inputs.py
│   ├── test_artifact_rst.py
│   ├── test_artifact_index.py
│   ├── test_artifact_edits.py
│   ├── test_artifact_obligations.py
│   ├── test_artifact_trace.py
│   ├── test_artifact_impact.py
│   ├── test_artifact_package.py
│   ├── test_artifact_native.py
│   ├── test_artifact_limits.py
│   ├── test_artifact_diff_drift.py
│   └── test_artifact_cli.py
├── integration/
│   ├── test_artifact_native.py
│   ├── test_artifact_index.py
│   ├── test_artifact_candidate.py
│   ├── test_artifact_trace.py
│   └── test_artifact_review.py
└── fixtures/artifacts/
    ├── feature/
    ├── component/
    ├── analysis/
    ├── invalid/
    └── native-consumer/
```

**Structure Decision**: Add one cohesive `artifacts` package to the existing CLI/library. Keep
lossless source handling, native build/export, expected-set derivation, trace checking, impact,
and sealing separate so authority and failure boundaries are testable. Reuse existing canonical
JSON, bounded-reader, digest, diagnostic, and protected-output patterns. Do not add a second
requirements store, general RST formatter, target-repository writer, workflow client, or service.

## Phase 0 — Research outcome

[Research](research.md) resolves every technical decision needed for design:

- authoritative semantics come from exact native source plus the pinned metamodel and native
  export; source spans and export entries must reconcile one-to-one;
- a lossless bounded directive scanner edits exact spans while the actual native build/export is
  the compatibility oracle; examples inside literal/code blocks are never live needs;
- creates copy pinned templates and realize only explicit request values; updates require an exact
  subject, expected preimage, allowed operation, and reviewed source rule;
- one sealed overlay binds the complete immutable base snapshot and contains all changed/new native
  bytes, indexes, source map, native receipt, limitations, and self-digest; trace/impact results may be
  attached by their explicit operations without making candidate creation depend on them;
- an explicit reviewed trace profile classifies every package expected output and declares native
  relation/type paths; filenames, prose, and workflow topology have no implied trace semantics;
- coverage begins with the complete expected set and retains absent items in the denominator;
- impact combines native reverse links with conservative source-cited expansion rules for new or
  unknown dependencies; historical accepted records are never rewritten;
- index/diff/drift/trace outputs use canonical path-independent JSON and stable identities;
- exact limits cover and exceed the measured pinned target while keeping hostile inputs bounded.

There is no unresolved product clarification. Exact production identifier policy, artifact
mapping, and trace-profile owner approval remain explicit external prerequisites; fixture profiles
are sufficient for contract development and cannot be relabelled as production authority.

## Phase 1 — Design outcome

[Data model](data-model.md) defines strict versioned request, snapshot, profile, source-span,
wrapper/need/relation, edit, expected-obligation, coverage, impact, build-receipt, report, and
candidate-package records plus lifecycle transitions. [Artifact contract](contracts/artifacts.md)
defines CLI exits, trust and authority, source/native reconciliation, scoped edits, native
validation, expected-set coverage, trace paths, impact, deterministic sealing, and stable finding
codes. [Quickstart](quickstart.md) defines the feature/component/analysis acceptance flow and
negative mutations.

Post-design review passes every constitution gate. No planning unknown remains.

## Complexity Tracking

No constitutional violation requires justification.
