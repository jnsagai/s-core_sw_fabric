# Implementation Plan: Deterministic workflow compiler

**Branch**: `003-deterministic-workflow-compiler` | **Date**: 2026-09-27 |
**Spec**: [spec.md](spec.md)

**Input**: The 003 specification, brief §20.6, FAB-012–FAB-015, the completed 002
handoff, ADR0005, and pinned Fabro source research. Status: planning complete;
implementation, execution-mapping owner review, and native-validator evidence pending.

## Summary

Add an offline deterministic compiler that accepts only a complete sealed 002 plan plus a
reviewed execution mapping and exact compiler/validator profiles. Derive a typed execution IR,
enforce fabric graph semantics, render a conservative explicit Fabro graph and closed source set,
and publish one canonical workflow-package JSON only after a matching native validator accepts a
disposable materialization. Include complete provenance, semantic diff, and drift verification.

003 stops at compiled conformance evidence. It does not register or execute workflows, select the
production Fabro runtime, call models, edit target artifacts, authenticate human decisions, accept
engineering evidence, or change readiness.

## Technical Context

**Language/Version**: Existing Python >=3.12 integration package. Generated Fabro DOT/TOML and
support files are UTF-8 text governed by a versioned conformance profile.

**Primary Dependencies**: Existing pinned Python standard library and PyYAML 6.0.3; no new runtime
package. Invoke an external Fabro validator whose binary/build identity matches pinned candidate
commit `1b4fb15281ebb724426f9e480dce48d0100ff79b`.

**Storage**: Local immutable inputs and one canonical JSON package file. Native files are held in
the package's `entrypoint`/`files` map and materialized only in a disposable validation directory.
No service, database, registry, or mutable workflow state.

**Testing**: Existing pytest 9.1.1, Ruff 0.16.9, strict mypy 2.3.1, foundation checks, and offline
wheel build. Contract/property fixtures cover semantic invariants and determinism. Integration
uses a real matching validator via `SCORE_FABRO_BIN`; successful native evidence is mandatory for
003 acceptance even if an unavailable local binary causes an interim explicit skip.

**Target Platform / Project Type**: Offline Linux CLI/library within the existing single Python
package; generated package is portable and path-independent.

**Performance Goals**: Demonstrate deterministic completion at declared maximum representative
bounds and record elapsed time/peak package size in acceptance evidence. Use linear or near-linear
graph algorithms over sorted adjacency; do not claim an unmeasured latency SLA.

**Constraints**: 64 MiB per input and package; 10,000 plan instances; 100,000 plan dependencies;
50,000 mapping rules; 50,000 IR nodes; 200,000 IR edges; 10,000 cyclic components. Native closure
is limited to 512 files, 512 KiB per file, and 2 MiB total source text. Inputs are read-only;
output is path/alias protected and atomically replaced only after semantic and native validation.
All cycles/retries are finite. Host paths, timestamps, randomness, and host settings are excluded
from semantic identity. Every action declares allowed paths and data destinations, a tool/permission
profile, a model-capability profile or explicit non-model binding, and finite profile-bounded
wall-time, attempt, tool-call, token, and cost budgets as applicable; unlimited values are invalid.

**Scale/Scope**: Compiler schema/profile v1 over sealed 002 plan schema v1 and one reviewed
mapping vocabulary. Conservative native node subset: start, exit, agent, prompt, command, human,
conditional, parallel, and parallel fan-in. The internal `deterministic-check` action has explicit
typed semantics and renders only as a native `command`; its outcome edges retain the check result.
Three representative packages cover linear work, shared parallel review, and bounded correction
feedback.

## Constitution Check

| Principle / gate | Pre-research decision | Post-design result |
| --- | --- | --- |
| Native authority and explicit policy (I, III) | Compile only sealed plans and reviewed, source-cited mapping rules | Preserved; native relations never become schedule edges implicitly and every generated semantic element has origins |
| Portable record and one runtime (II, VIII) | Emit a closed derived package; use native validation without a scheduler | Preserved; package stays independently inspectable and 003 adds no run state, registry, or competing runtime |
| Human accountability and truthful evidence (IV, XI) | Model human stops without approval credentials or trust claims | Preserved; auto/replayed approval and success timeout defaults are rejected; validation is conformance evidence only |
| Deterministic checks and fail-closed readiness (V, VI) | Validate typed semantics before native syntax; publish only after both pass | Preserved; unknown/missing/failure outcomes never default to success and readiness stays `not_evaluated` |
| Traceability and provenance (VII, XII) | Bind sources, profiles, transformations, files, and validator identity | Preserved; complete source map, content digests, diff, drift, and exact source pin are required |
| Bounded AI execution and increments (IX, X) | Require explicit paths, tools, model capabilities, data destinations, budgets, outcomes, and loop bounds and stop before runtime | Preserved; missing/unlimited/above-profile action policy is rejected and 004–006 behavior is not claimed |

No constitutional exception is required. The constitution itself remains pending owner review;
planning does not ratify it or approve the project execution mapping.

## Project Structure

### Documentation delivered in this planning step

```text
specs/003-deterministic-workflow-compiler/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── compiler.md
└── checklists/
    └── requirements.md
```

`tasks.md` is intentionally deferred to the next Spec Kit step.

### Planned source code

```text
src/score_sw_fabric/
├── compiler/
│   ├── __init__.py
│   ├── models.py             # strict request, profile, IR, package, diff/drift shapes
│   ├── reader.py             # bounded inputs, versions, digests, path/alias checks
│   ├── mapping.py            # finite reviewed-rule matching and origin projection
│   ├── ir.py                 # deterministic node/edge derivation and stable IDs
│   ├── graph_validation.py   # reachability, gate dominance, SCC/loop, outcome/fan checks
│   ├── render.py             # canonical DOT/TOML/support-file rendering
│   ├── package.py            # closure, canonical identity, sealing, atomic publication
│   ├── validator.py          # isolated profiled native validation and receipt
│   ├── diff.py               # categorized semantic comparison
│   └── drift.py              # integrity and source-regeneration comparison
└── cli.py                    # workflow compile/validate/diff/drift commands

schemas/
├── compiler-request.schema.json
├── execution-mapping.schema.json
├── compiler-profile.schema.json
├── validator-profile.schema.json
├── workflow-package.schema.json
├── workflow-source-map.schema.json
├── compile-report.schema.json
└── workflow-diff.schema.json

profiles/
├── deterministic-compiler-v1.yaml
└── fabro-conformance-1b4fb152-v1.yaml

policies/
└── s_core_execution_mapping_v1.yaml

tests/
├── compiler_support.py
├── contract/
│   ├── test_compiler_inputs.py
│   ├── test_compiler_validator.py
│   ├── test_compiler_ir.py
│   ├── test_compiler_graph_semantics.py
│   ├── test_compiler_rendering.py
│   ├── test_compiler_package.py
│   ├── test_compiler_diff_drift.py
│   └── test_compiler_cli.py
├── integration/
│   ├── test_workflow_compiler.py
│   └── test_workflow_compiler_native.py
└── fixtures/compiler/
    ├── linear/
    ├── shared-parallel-review/
    ├── bounded-correction/
    ├── invalid/
    └── expected/
```

**Structure Decision**: Keep compilation in the existing Python package and CLI. Split pure typed
derivation, graph checks, rendering, package sealing, validator invocation, and comparisons so each
boundary can be tested independently. Reuse existing bounded-reader and protected-output patterns;
do not create a service, scheduler, registry client, or second requirements store.

## Phase 0 — Research outcome

[Research](research.md) resolves every technical choice needed for design:

- typed IR is authoritative; rendered DOT is an output;
- the exact pinned nightly Fabro source is a conformance candidate, not runtime selection;
- a conservative explicit graph subset excludes implicit types, random selection, success-on-
  failure, partial mandatory merges, unbounded visits, and automatic/replayed approval;
- one canonical JSON bundle carries a registry-compatible `entrypoint`/`files` map, semantic
  manifest, source map, reports, receipts, and self-digest;
- stable IDs use canonical structured logical tuples, while mutable baselines remain bindings;
- dominance/reachability, complete outcome partitions, deterministic SCC analysis, exact fan sets,
  and source-map coverage implement the semantic gate;
- semantic diff and drift remain separate; publication is protected and atomic.

There is no unresolved product clarification. Production runtime selection, authenticated decision
verification, mapping approval, and engineering acceptance are explicit later or owner-owned inputs.

## Phase 1 — Data model, contracts, and algorithm

Use the [data model](data-model.md) and [compiler contract](contracts/compiler.md) in this order:

1. Parse the bounded compilation request and selected files. Verify transport hashes before parsing,
   reject unknown normative fields, validate exact schema/profile compatibility, self-digests, and
   semantic bindings. Confirm output containment/alias safety without creating output.
2. Validate the sealed 002 plan as a complete compiler input. Reject blocked closure, unresolved
   dispositions, dangling dependencies, unsupported external debt, tampering, or profile mismatch.
3. Match every retained instance to reviewed finite execution rules. Build canonical logical action,
   gate, ordering, branch, merge, retry, and failure records with explicit origins. Deduplicate only
   exact agreeing gate tuples; report conflicts instead of applying precedence. Bind allowed paths,
   data destinations, tools/permissions, model capabilities or explicit non-model status, and finite
   per-profile execution budgets to every action.
4. Construct the immutable IR in sorted logical-key order. Generate IDs from canonical tuple hashes,
   retain the tuples, and reject normalization collisions. Never derive schedule edges from native
   relations without an explicit rule.
5. Validate one start/exit, endpoints and reachability, gate dominance with concrete bypass paths,
   complete/disjoint outcomes, bounded cyclic components with exhaustion, exact non-empty fan-in,
   path/destination/capability/budget boundaries, prohibited approval behavior, and total source-map
   coverage.
6. Render canonical DOT, TOML, and support files from the validated IR. Enforce normalized relative
   paths, content identity, closure, native file/count bounds, and deterministic byte ordering.
7. Materialize the files map into a disposable isolated tree and invoke only the matching profiled
   native validator. Capture a bounded semantic receipt and delete the tree. A native failure or
   unavailable/mismatched validator prevents publication.
8. Build and self-validate the canonical workflow package. Bind compiler and validator identity,
   inputs, IR, files, source map, report, and receipts. Atomically replace the output only after all
   gates pass; preserve the previous file on every error.
9. Validate existing packages read-only. Diff two valid packages by semantic category. Drift-check
   integrity and then recompile declared sources in memory; never adopt direct generated edits.

Canonical JSON is UTF-8 with sorted keys, compact separators, finite values, and one trailing newline.
The DOT renderer has explicit escaping and sorted statements. Only explicitly set-like collections
are reordered. Absolute paths, timestamps, temporary locations, and host state are non-semantic.

## Validation and handoff to task generation

[Quickstart](quickstart.md) defines the future runnable acceptance flow. Tasks must map every
AC003 scenario and requirement to contract, integration, or acceptance evidence. The negative suite
must independently exercise gate bypass, outcome gaps, dangling endpoints, unbounded/excess loops,
fan mismatch, auto/replayed approval, unsafe closure, source-map gaps, mapping conflicts, profile
mismatch, missing/unlimited/above-profile action capabilities or budgets, and output/source aliasing
while proving prior output preservation.

Permutation and relocation tests require byte-identical output. Single-source semantic mutations
must affect only their intended diff category. Direct generated edits must yield drift. Maximum and
one-over-limit cases must cover node, edge, cycle, file, per-file byte, total native byte, input, and
package bounds with stable diagnostics.

Three representative packages—linear obligations, shared parallel review, and bounded correction
feedback—must pass both semantic validation and an actual matching Fabro validator. Frozen lint,
format, strict typing, full pytest, foundation checks, and offline build must pass. Acceptance records
the exact validator identity and source pin. A skipped native test cannot complete increment 003.

Implementation stops before registration or execution. The next planning workflow is task generation.

## Complexity Tracking

No constitution violation or additional project boundary is required.
