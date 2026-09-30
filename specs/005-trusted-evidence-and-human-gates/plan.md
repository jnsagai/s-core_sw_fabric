# Implementation Plan: Trusted evidence and authenticated human gates

**Branch**: `005-trusted-evidence-and-human-gates` | **Date**: 2026-09-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-trusted-evidence-and-human-gates/spec.md`

## Summary

Build a separate portable assurance layer over sealed 002 plans and 004 artifact candidates/reports.
It verifies externally issued evidence and human-decision receipts, checks exact subject and policy
bindings, evaluates complete scoped predicates fail-closed, and preserves immutable historical
results. A checked-in fixture trust domain exercises contracts; absent owner-selected production
identity, issuer, collector, and gate policy blocks real acceptance. No Fabro execution integration
or production signing/submission service is part of this increment.

## Technical Context

**Language/Version**: Python >=3.12, matching the existing package and frozen project lock.

**Primary Dependencies**: Existing PyYAML 6.0.3 and canonical JSON/hash helpers; add and pin a
Python 3.12-compatible `cryptography` release for Ed25519 public-key verification, with its
transitive dependencies and license recorded in `uv.lock` during implementation. No production
private key is a package input. The actual native build and Fabro binaries are not invoked by 005.

**Storage**: Content-addressed, canonical JSON inputs/receipts/assessment outputs and optional
human-readable report. No database or hidden mutable gate state. Historical records are append-only
facts; current applicability is recomputed.

**Testing**: pytest 9.1.1 for schema/contract, adversarial signature, subject, role, scope,
independence, import, time, timeout, status, staleness, relocation, and portability cases; Ruff
0.16.9, strict mypy 2.3.1, foundation checker, and offline wheel/sdist build. A positive fixture
pass is explicitly labelled `fixture_contract` and cannot satisfy production predicates.

**Target Platform / Project Type**: Offline Linux CLI/library in the existing Python package. The
portable verifier needs no Fabro process or network connection. A real production pass depends on
an externally protected receipt issuer and owner-approved trust configuration.

**Performance Goals**: Deterministic bounded validation and evaluation of all declared records at
the selected profile maxima. Record elapsed time and output size in acceptance evidence; no
unmeasured latency SLA. Sort and deduplicate identities before evaluation so input order and
relocation do not change semantic results.

**Constraints**: Exact version-1 envelopes; 64 MiB per control/package; at most 100,000 expected
predicates, 100,000 evidence records, 10,000 decisions, 20,000 findings, 10,000 references, and
32 nested reference levels; profile ceilings may only lower these hard maxima. Bound raw bytes,
verification duration, signature count, and path traversal. Input roots are read-only; output
replacement is atomic. A signed receipt must cover domain-separated canonical payload bytes and
must be checked against an independently supplied trust root. A user-selected `as_of` is sufficient
for historical replay only; current production pass requires authenticated time authority.

**Scale/Scope**: Version 1 covers exact 002 plan and 004 candidate/report closures, protected
observed results, policy-authorized imported results, fixture/agent classifications, authenticated
human decisions, six gate outcomes, staleness, and portable verification. Representative
feature/component/analysis fixtures use sealed 004 records. Aggregate module/platform readiness,
release, runtime registration/execution, and target mutation belong to later scope.

## Constitution Check

*GATE: Passed before Phase 0 research and re-checked after Phase 1 design.*

| Principle / gate | Pre-research decision | Post-design result |
| --- | --- | --- |
| Native authority and explicit policy (I, III) | Bind exact 002/004 identities; require cited reviewed predicate and origin policy | Preserved; 005 records reference native artifacts and refuse inferred authority |
| Portable record and one runtime (II, VIII) | Independent JSON verification; no run database | Preserved; assessments are portable and do not schedule or inspect Fabro |
| Human accountability (IV) | Require authenticated actor, role, authority, independence, subject and scope | Preserved; claimed names and 002 decision references alone are ineligible |
| Deterministic checks and fail-closed readiness (V, VI) | Separate factual result, eligibility, and gate predicates | Preserved; unknown, missing, timeout, stale and empty sets cannot pass |
| Traceable changes (VII) | Freeze expected set before observations; use 004 impact and exact bindings | Preserved; changed and unlinked dependencies widen review or block |
| Bounded AI (IX) | Agents receive neither signer keys nor approval credentials | Preserved; fixture-domain records cannot be promoted to production authority |
| Incremental delivery (X) | Implement FAB-019–FAB-023 contracts only | Preserved; 006 runtime and later readiness remain separate |
| Truthful evidence and provenance (XI, XII) | Verify signed origin independently of digest; retain raw references and limitations | Preserved; origin classes and immutable history remain explicit |
| Reference immutability (XII / workflow) | Read sealed inputs; publish derived 005 records separately | Preserved; 004 candidate/report bytes stay unchanged |

No constitutional exception is required. The constitution and production trust/gate policies retain
their actual owner-review states; planning does not ratify them.

## Project Structure

### Documentation delivered in this planning step

```text
specs/005-trusted-evidence-and-human-gates/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── assurance.md
└── checklists/
    └── requirements.md
```

`tasks.md` belongs to the subsequent `$speckit-tasks` step.

### Planned source code

```text
src/score_sw_fabric/
├── assurance/
│   ├── __init__.py
│   ├── models.py          # exact versioned records and limits
│   ├── reader.py          # closure, digest, version, path and alias validation
│   ├── subjects.py        # canonical subject from 002/004 identities
│   ├── origins.py         # domain-separated Ed25519 receipt verification
│   ├── evidence.py        # evidence class, raw result and import eligibility
│   ├── decisions.py       # actor, authority, independence and lifecycle
│   ├── predicates.py      # complete expected set and deterministic checks
│   ├── freshness.py       # current-use staleness, impact and history
│   ├── gates.py           # six outcomes and reason/route calculation
│   └── package.py         # portable closure, independent verify, atomic output
└── cli.py                 # assurance subject/evidence/decision/gate/verify

schemas/
├── assurance-subject.schema.json
├── assurance-trust-profile.schema.json
├── assurance-receipt.schema.json
├── assurance-evidence.schema.json
├── assurance-decision.schema.json
├── assurance-gate-policy.schema.json
└── assurance-assessment.schema.json

profiles/
└── assurance-fixture-v1.yaml  # test-only, never production authority

tests/
├── assurance_support.py
├── contract/
│   ├── test_assurance_inputs.py
│   ├── test_assurance_subjects.py
│   ├── test_assurance_origins.py
│   ├── test_assurance_evidence.py
│   ├── test_assurance_decisions.py
│   ├── test_assurance_gates.py
│   ├── test_assurance_freshness.py
│   ├── test_assurance_limits.py
│   ├── test_assurance_portability.py
│   └── test_assurance_cli.py
├── integration/
│   └── test_assurance_from_artifacts.py
└── fixtures/assurance/
    ├── fixture-trust/
    ├── passing-scope/
    ├── blocked-scope/
    └── mutations/
```

**Structure Decision**: A cohesive `assurance` package sits beside `artifacts` and references
004 outputs without altering them. Separate origin, evidence, decision, predicate, freshness, and
gate modules make each trust boundary independently testable. Public-key verification uses a
pinned library; private signing and human submission remain outside the agent-writable package.

## Phase 0 - Research outcome

[Research](research.md) resolves the design choices: verify Ed25519 receipt origin separately from
SHA-256 integrity; separate fixture and production assurance domains; bind exact 002/004 subject
closure; keep 002 claimed decision references inert; evaluate factual authenticity, policy
eligibility, and gate outcomes separately; freeze assessment time with an authenticated basis;
preserve history while current applicability changes; and export a Fabro-free portable record.
Owner-selected production identity and collector services remain prerequisites for *live*
authority, never guessed defaults or unresolved internal design markers.

## Phase 1 - Design outcome

[Data model](data-model.md) defines the subject, trust profile, receipt, evidence, decision,
predicate, gate policy, freshness and assessment records with validation and state transitions.
[Assurance contract](contracts/assurance.md) defines public CLI inputs/exits, canonical signed
payload, trust-domain rules, exact eligibility, gate precedence, portable verification and stable
reason codes. [Quickstart](quickstart.md) gives fixture-positive, real-domain-denial, mutation,
expired/revoked, timeout, and Fabro-free verification scenarios.

Post-design review passes every constitution gate. No internal design clarification remains.

## Complexity Tracking

No constitutional violation requires justification.
