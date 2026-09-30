# Versioned catalogue and planning schemas

All schemas use JSON Schema draft 2020-12 and exact integer `schema_version: 1`.

- `source-manifest.schema.json` and `catalogue.schema.json` define the 001 import boundary.
- `intake.schema.json`, `planning-profile.schema.json`,
  `applicability-mapping.schema.json`, `artifact-inventory.schema.json`, and
  `decision-references.schema.json` define the 002 planner inputs.
- `work-product-plan.schema.json` defines the sealed 002 draft result.
- `compiler-request.schema.json`, `execution-mapping.schema.json`, `compiler-profile.schema.json`, and `validator-profile.schema.json` define the 003 selected inputs.
- `workflow-package.schema.json`, `workflow-source-map.schema.json`, `compile-report.schema.json`, and `workflow-diff.schema.json` define closed 003 outputs.

The runtime also enforces constraints that schemas cannot express alone, including 003 graph reachability, gate dominance, outcome partitions, bounded cycles, complete fan-in, native closure, validator identity, and atomic publication. Existing 001/002 checks include the 64 MiB input bound,
duplicate JSON/YAML key rejection, exact transport and semantic digests, source-qualified native
identities, relation closure, finite scope/rule/coverage/instance/edge limits, local path
confinement, hardlink and symlink protection, deterministic normalization, and atomic output
replacement.

Planning outputs are drafts. A complete planner result does not assert engineering acceptance or
release readiness. Reuse and tailoring that need human authority remain effectively unresolved in
002. See the [planning contract](../specs/002-applicability-and-work-product-plan/contracts/planning.md)
and [acceptance record](../specs/002-applicability-and-work-product-plan/acceptance.md).

Increment 004 adds `target-snapshot`, `artifact-request`, `native-artifact-profile`, `trace-profile`,
`native-artifact-index`, `artifact-candidate`, `artifact-report`, and `artifact-diff` schemas. Runtime
validation additionally enforces duplicate-key rejection, exact transport/self/nested digests,
immutable snapshot closure, source/export reconciliation, type-specific wrapper/child status and
relation rules, preimage-bound edit spans, expected-set denominators, protected atomic publication,
and six fixed `not_evaluated` capability fields.

Increment 005 adds `assurance-subject`, `assurance-trust-profile`, `assurance-receipt`,
`assurance-evidence`, `assurance-decision`, `assurance-gate-policy`,
`assurance-gate-result`, and `assurance-assessment` version-1 schemas. They require exact
integer version 1, explicit assurance domain, bounded arrays, SHA-256 identities, and strict
normative object fields. `assurance-assessment` validates embedded 005 records and its portable
closure wrappers. Embedded 002/004 source records remain opaque at the schema layer and are
revalidated by their own runtime readers and the 005 subject builder. The six gate outcomes are
`pass`, `fail`, `blocked`, `not_evaluated`, `not_applicable`, and `stale`. An optional signed
`no_impact` human decision binds the prior assessment, old/new subject and policy identities, and
exact changed paths. It requires an explicit gate-policy freshness rule and cannot turn a stale
gate into a pass or act as standalone human approval. Freshness `impact_paths` retains
004 native dependency paths under `/native/` (with JSON-pointer escaping) even when `/`
marks whole-gate review; changed receipt identities are separate freshness bindings.

Only the licensed test key under `tests/fixtures/assurance/fixture-trust/` is selected by the
checked-in `fixture_contract` profile. A production pass requires independently protected and
owner-reviewed trust roots, role/independence authority, collector and human submission services,
policy, and time basis; those services are not supplied by this repository. Offline `assurance
verify` rechecks embedded source/raw bytes and receipts against a separately supplied trust
context. It reproduces the historical gate result; current production use must reassess freshness
and protected time. CLI exits are 0 for a passing gate or faithful historical replay, 1 for a
well-formed non-pass or replay mismatch, and 2 for malformed, unsafe, or unavailable inputs.
Increment 006 runtime integration and 014+ readiness/release claims remain separate.

Increment 006 adds proposed version-1 `runtime-profile`, `runtime-intent`, `runtime-request`,
`runtime-binding`, `runtime-snapshot`, `runtime-resume-decision`, `runtime-cancellation`, and
`runtime-export` schemas. A contract test keeps their required fields equal to the runtime
readers. Runtime validation additionally enforces exact self-digests, request-file SHA-256
bindings, symlink refusal, owner-only credential files, loopback candidate profiles, sorted
demonstrated capabilities (`run_resume` stays undemonstrated), native route allowlists, bounded
responses, guarded atomic publication and offline export closure. Export blob origins are
`fabric_source` (sealed 003 package and compiler profile), `runtime_observation` (every Fabro
event, blob and stage output), and `authenticated_005_reference` only for a separately replayed 005
assessment. A `production` assurance reference is refused while 005 T009 is pending. Resume
decisions are `admit`, `refuse_terminal`, `block_unknown`, `block_drift`, or
`reconciliation_required`. Runtime exits are 0 for the exact operation or faithful observation,
1 for an explicit published non-success, and 2 for malformed, unsafe, or unavailable input.
