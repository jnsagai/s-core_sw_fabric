# Implementation Plan: Component safety feedback

**Branch**: `008-component-safety-feedback` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/008-component-safety-feedback/spec.md`

## Summary

Add a deterministic `score-fabric safety` boundary over native component FMEA/DFA documents. A
reviewed profile pins the native fault-model and DFA-initiator catalogues, metamodel field rules,
native attribute rules and the formal-review checklist. `safety check` reads native requirement,
architecture and analysis RST with the 004 scanner and reports coverage, item violations,
mitigation states, untrusted promotions, re-analysis against a prior baseline, bounded feedback
proposals and gate prerequisites. `safety packet` renders the reviewer-facing packet with both
gate scopes. `safety gate` evaluates design acceptance and closure separately, counting human
decisions only from a verified 005 assessment bound to the packet's exact file digests. FMEA and
DFA analyst roles are 007 role profiles checked for separation. No command writes native files
or calls a model.

## Technical Context

**Language/Version**: Python >=3.12, existing frozen environment.

**Primary Dependencies**: Existing 004 `scan_rst`, 005 `verify_assessment`, 007 role validation,
strict readers, canonical digests and guarded publication. Native sources (read-only):
`process_description` `98d1d5f42dad412a09a888ea25e59c62fa6371ce`, `module_template`
`c4d4ad090c6584e58279f0e5d0b6894f7fc4cf0d`, `docs-as-code`
`d5f3de608cdfc034952c57d40979c78d8cd35957`. No new dependency.

**Storage**: Sealed JSON reports, packets and gate evaluations published outside inputs and
protected roots. Native RST stays authoritative and is never modified.

**Testing**: Contract tests on synthetic telemetry-freshness-guard fixtures (v1 gap, v2 feedback,
agent promotion, DFA shared dependency), profile validation, list-table parsing, rules, promotion,
re-analysis, loop budget, packet and gate evaluator; CLI exit tests; an env-gated test that
re-derives the catalogues from the pinned process checkout.

**Constraints**: Catalogue IDs only from pinned sources. `sufficient`/`status` semantics follow
`gd_req__saf_attr_*`; no RPN or ranking is invented. Example directives inside `code-block` are
ignored. 005 production authority (T009) is absent, so production decisions cannot be eligible.

**Scale/Scope**: Component scope only (feature/platform propagation later); one component per
check; fixture demonstrations DEMO-02 and DEMO-03. No live drafting, closure evidence collection,
or native-file writer.

## Constitution Check

*GATE: Passed before Phase 0 research and re-checked after Phase 1 design.*

| Principle / gate | Pre-research decision | Post-design result |
| --- | --- | --- |
| Native authority, explicit policy (I, III) | Catalogues, fields and rules cite pinned sources | Preserved; the one fabric policy (platform allocation) is labelled and pending review |
| Portable record (II) | Reports bind file digests; native RST unchanged | Preserved |
| Human accountability (IV) | Sufficiency/validity only via verified human decision | Preserved; agent promotions refused |
| Deterministic checks / fail closed (V, VI) | Structural checks only; adequacy left to reviewers | Preserved; checklist answers stay `pending_human` |
| Traceable changes (VII) | Re-analysis on changed/new referenced elements | Preserved |
| One runtime (VIII) | No scheduler or safety database | Preserved; loop state is derived from native files |
| Bounded AI (IX) | FMEA/DFA roles via 007 refusals | Preserved; disjoint write scopes |
| Incremental delivery (X) | FAB-031/032 component scope only | Preserved |
| Truthful evidence (XI) | Recommendations are drafts; fixtures labelled | Preserved |
| Reproducibility (XII) | Pinned sources, read-only references | Preserved |

No constitutional exception is needed.

## Project Structure

```text
specs/008-component-safety-feedback/{spec,plan,research,data-model,quickstart,tasks,acceptance}.md
specs/008-component-safety-feedback/contracts/safety.md
src/score_sw_fabric/safety/
├── __init__.py
├── profile.py    # safety_analysis_profile validation and catalogue extraction
├── native.py     # native RST needs and list-table applicability parsing
├── analysis.py   # coverage, item rules, mitigation states, promotions, re-analysis, feedback
├── packet.py     # review packet
└── gates.py      # design-acceptance and closure evaluation
profiles/s-core-safety-analysis-v1.yaml
profiles/agent-role-{fmea,dfa}-analyst-draft-v1.yaml
schemas/safety-*.schema.json
tests/fixtures/safety/telemetry_guard/{v1,v2,dfa}/
tests/safety_support.py, tests/contract/test_safety_*.py, tests/integration/test_safety_native.py
```

**Structure Decision**: New `safety` package reusing 004/005/007 helpers; CLI
`score-fabric safety check|packet|gate`.

## Complexity Tracking

No violations. A list-table row parser is added because the applicability tables are native
list-tables; it reads only the four native columns and refuses malformed rows.
