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

Increment 007 adds `apm-context-lock`, `agent-role-profile`, `agent-model-profiles`,
`agent-budget-ledger` and `agent-result` input schemas, the five `agent-*-request` schemas, and
the `agent-capability-inventory`, `agent-setup-record`, `agent-context-bundle`,
`agent-admission` and `agent-output-check` output schemas. A contract test keeps every
required-field set equal to the readers and to real outputs. Runtime validation additionally
enforces request-file SHA-256 bindings, verified disposable copies, exact MCP tool-schema
digests, workspace snapshots (including `.git/config`, hooks and info), whole-segment globs,
catalogue pagination completeness, unknown-usage refusal and guarded atomic publication.
`available`, `admissible` and `within_bounds` are deterministic check outcomes, never
engineering acceptance.

Increment 008 adds `safety-analysis-profile`, the `safety-check-request`,
`safety-packet-request` and `safety-gate-request` schemas, and the `safety-analysis-report`,
`safety-review-packet` and `safety-gate-evaluation` outputs. A contract test keeps their required
fields equal to the readers and real outputs, and an env-gated test re-derives the profile
catalogues and field rules from the pinned native checkouts. Runtime checks additionally enforce
native-file SHA-256 bindings, literal-block exclusion, list-table column resolution, native
attribute rules, 005 assessment replay and exact file-closure binding. Checklist answers are
always `pending_human`; no 008 record is a safety acceptance.

Increment 009 adds `verification-profile`, `verification-toolchain-profile`,
`verification-design-request`, `verification-run-request`, `verification-report-request`,
`verification-design-report`, `verification-run` and `verification-milestone-report` schemas.
The readers additionally enforce selected file digests, local toolchain hashes/versions,
native tags and metadata, exact run-history digests and guarded publication. A passing local
run remains `local_unprotected_execution` and cannot satisfy 005 evidence or design acceptance.

Increment 010 adds quality adapter/import schemas and `quality-disposition-draft`,
`quality-disposition-request` and `quality-disposition-review`. Runtime checks bind the
exact original finding, frozen file, current tool/policy/scope and every linked historical
review. Explicit correction checks execute the bounded local adapter again; labels,
native names/dates and stored reports cannot replace execution or authenticate a decision.
No draft/review schema grants 005 decision eligibility or engineering readiness.

Increment 010 portable `quality-packet-request` and `quality-review-packet` schemas
retain strict selections, original byte hashes, scoped target source snapshots, full
disposition history, native/fixture originals and source/tool notice associations.
The runtime replays imports, extraction, coverage and current fixture decision validity
from portable originals, retains incomplete closure and fixes all human answers at
`pending_human`. Structural completeness is separate from engineering readiness.
