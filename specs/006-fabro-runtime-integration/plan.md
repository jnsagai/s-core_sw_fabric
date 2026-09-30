# Implementation Plan: Fabro runtime integration

**Branch**: `006-fabro-runtime-integration` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-fabro-runtime-integration/spec.md`

## Summary

Create a narrow adapter over a verified Fabro lifecycle version. It accepts a sealed 003
workflow package, derives an exact native version projection, registers and starts one run,
reads native status/events/questions/checkpoints, guards resume against 005 freshness drift,
and exports a portable historical run record. A durable intent ledger correlates operator
requests but never substitutes for Fabro run state. Ambiguous run creation stops for manual
reconciliation because the inspected pinned API has no atomic idempotency key. Fabro runtime
success remains separate from authenticated 005 evidence and human acceptance.

## Technical Context

**Language/Version**: Python >=3.12, existing frozen project environment.

**Primary Dependencies**: Existing stdlib HTTP/JSON, hashing and bounded reader helpers unless
Phase 0 validation shows a specific missing capability. The pinned Fabro source at
`1b4fb15281ebb724426f9e480dce48d0100ff79b` documents candidate HTTP lifecycle routes;
the executable has only been proven for `version` and `validate`. A compatible runtime/server
and authentication profile must be selected and validated before claiming live use. No model
provider, approval signer or protected collector is included.

**Storage**: Immutable 003 package and native wire projection; guarded local intent/run binding
and content-addressed run export. Fabro stores authoritative registration, events, checkpoints,
questions and run state. No second scheduler, queue or run-state database.

**Testing**: Contract tests for closure, projection, limits, intent ambiguity, status mapping,
event pagination, gate-subject binding, resume freshness and export closure; disposable local
Fabro integration for a command step and waiting human gate if the selected pin supports it.
Run frozen pytest, Ruff, mypy, foundation checker and offline build. No paid model call.

**Target Platform / Project Type**: Linux CLI/library in the existing Python package, with a
Fabro server or supported native lifecycle transport only after identity and capability probe.
Portable export verification runs without Fabro.

**Performance Goals**: Bound response/page counts, event/output bytes, retry attempts and
wall time with measured acceptance values. No unmeasured latency SLA. One request and one
response are not proof of exactly-once creation after a transport failure.

**Constraints**: Check 003 package limits and Fabro's distinct 512-file, 512-KiB/file,
2-MiB canonical version-wire ceilings. Recheck files before submission; never write reference
repositories. Normalize safe paths, reject symlink/traversal/extra or missing files, guard
outputs with atomic replacement, and keep secrets out of logs/exports. A selected Fabro version
must demonstrate the needed API and auth. Unknown native status or source/receipt drift is a
non-success state. Human-gate auto-approve and timeout-default paths are prohibited for required
review; agents have no approval or collector credential. Production 005 authority remains blocked
until T009 and owner-controlled services are supplied.

**Scale/Scope**: One package/version/run per operator intent, finite event pages, one active
review question at a time for the first integration, bounded output and export. No paid model
execution, external publishing/merging/deployment, APM role context (007), engineering readiness
or release gates (014+). Native lifecycle operations remain Fabro's responsibility.

## Constitution Check

*GATE: Passed before Phase 0 research and re-checked after Phase 1 design.*

| Principle / gate | Pre-research decision | Post-design result |
| --- | --- | --- |
| Native authority and explicit policy (I, III) | Keep S-CORE artifacts and 003/005 source bindings outside runtime | Preserved; native package is an exact projection and runtime status cannot create engineering policy |
| Portable record (II) | Retain original package and independent historical export | Preserved; export closure and offline verifier do not need Fabro |
| Human accountability (IV) | Stop at required questions; bind exact 005 subject and external authority | Preserved; native answers and auto-approve are not 005 decisions |
| Deterministic checks / fail closed (V, VI) | Verify package, version, evidence and status before actions | Preserved; uncertainty and drift stop automatic continuation |
| Traceable changes (VII) | Compare source/policy/tool/subject/evidence vector on resume | Preserved; historical events stay immutable |
| One runtime (VIII) | Native Fabro owns all lifecycle state | Preserved; ledger is only an intent correlation and side-effect guard |
| Bounded AI (IX) | No agent-held approval/collector credentials or paid model call | Preserved; initial integration uses command and human-waiting graph |
| Incremental delivery (X) | Cover FAB-024–FAB-026 only | Preserved; 007 context, 014+ readiness and production trust provisioning remain separate |
| Truthful evidence / provenance (XI, XII) | Label Fabro output as runtime context | Preserved; only independent 005 receipts and decisions may provide assurance authority |
| Reference immutability (XII) | Inspect pinned source read-only, build/test in disposable environment | Preserved; no reference repository write is planned |

No constitutional exception is needed. The proposed constitution and 005 production trust policy
retain their actual pending review states. Candidate Fabro source behavior is not a selected
production runtime claim.

## Project Structure

### Documentation delivered in this planning step

```text
specs/006-fabro-runtime-integration/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── runtime.md
└── checklists/
    └── requirements.md
```

`tasks.md` belongs to the subsequent Spec Kit tasks phase.

### Planned source code

```text
src/score_sw_fabric/
├── runtime/
│   ├── models.py         # versioned intent, native binding and export envelopes
│   ├── projection.py     # closed 003-to-Fabro version projection
│   ├── client.py         # selected native lifecycle transport and bounded reads
│   ├── ledger.py         # guarded operator intent and uncertain-response reconciliation
│   ├── inspect.py        # native status/event/question/checkpoint view
│   ├── resume.py         # freshness and partial-effect admission
│   └── export.py         # portable closure and offline verification
└── cli.py                # proposed runtime register/run/status/resume/cancel/export/verify

schemas/
├── runtime-intent.schema.json
├── runtime-binding.schema.json
├── runtime-profile.schema.json
└── runtime-export.schema.json

tests/
├── contract/test_runtime_*.py
├── integration/test_runtime_fabro.py
└── fixtures/runtime/
```

**Structure Decision**: A separate runtime package references sealed 003/005 records without
editing them. The client handles only demonstrated native capabilities; the ledger correlates
requests and prevents unsafe automatic repeats, while Fabro is the single execution authority.
The verifier reads exported bytes without a Fabro client.

## Phase 0 — Research outcome

[Research](research.md) records source-grounded decisions for the 003 entrypoint projection,
native version size and closure, HTTP create/start separation, lost-response fail-closed behavior,
event/question/checkpoint inspection, exact subject binding, resume admission, and portable
export. The inspected pin does not expose a caller idempotency key for run creation, a stable
public state projection, or a full workflow-version retrieval route. These are explicit design
limits, not unresolved hidden assumptions. Live capability and credential validation remain
implementation prerequisites because only native validation has actually been executed.

## Phase 1 — Design outcome

[Data model](data-model.md) defines package projection, intent ledger, native run binding,
event/question/checkpoint view, resume decision and export closure. [Runtime contract](contracts/runtime.md)
defines proposed CLI/request/exit behavior, native transport boundaries and fail-closed cases.
[Quickstart](quickstart.md) names executable validation steps to run after implementation and
the exact candidate capability gate before any live example. The design preserves a waiting
human question and does not claim an authenticated 005 decision.

Post-design review passes every constitution gate. The lack of native run-create idempotency
is handled by a visible reconciliation-required state; it is not claimed solved by labels.

## Complexity Tracking

No constitutional violation requires justification.
