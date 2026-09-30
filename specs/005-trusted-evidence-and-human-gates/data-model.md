# Data model: trusted evidence and authenticated human gates

All records are version 1, strict-field, bounded UTF-8 JSON except reviewed policy inputs, which
may be YAML before canonicalization. A digest is SHA-256 over canonical JSON excluding only its own
`digest` field. Maps use sorted keys; set-valued arrays use unique stable IDs and sort by ID.
Ordered observations and reason paths retain declared order. Paths are logical relative POSIX
paths and never part of a semantic identity through their host root. Unknown versions, enum values,
fields, duplicate keys/IDs, malformed digests, or lossy conversions are errors.

## SubjectManifest

**Purpose:** Exact engineering subject for evidence and decisions. It is a derived reference
closure, never an editable requirements store.

**Fields:** `schema_version`, `kind=assurance_subject`, `assurance_domain`, `scope` (kind, stable
scope ID, purpose), `plan` (digest, target namespace, source locks, instance IDs/dispositions),
`artifact_candidate` (digest, candidate identity, bindings, base/overlay file hashes, index and
native receipt digests), `artifact_report` (digest/status/expected obligation IDs and coverage),
`source_baselines` (repository, commit, declared content digests), `process_baseline`,
`toolchain`, `profiles` (artifact/trace/build/compiler/validator as consumed), `policy_bindings`,
`expected_obligation_ids`, `file_closure`, `limitations`, `digest`.

**Rules:** Revalidate 002 and 004 envelopes, digests, nested closure and mutual bindings before
sealing. A structurally valid candidate with no trace report remains representable but cannot meet
trace predicates. The digest excludes receipts, evidence, decisions, gate results and itself, so
later approval cannot change the subject it approves. Every ref has a transport hash and semantic
digest where the source format defines one. Missing declared bytes block use.

## TrustProfile and external root context

**Purpose:** Reviewed policy for permitted issuers, algorithms, roles, scopes and assurance domain.

**Fields:** `schema_version`, `kind=assurance_trust_profile`, `id`, `assurance_domain`,
`authority_source` (upstream/project configuration/authenticated decision plus source ref),
`issuer_keys` (key ID, issuer ID, public key digest, permitted receipt kinds, scopes, validity),
`identity_providers`, `role_assignments`, `independence_rules`, `import_rules`, `revocations`,
`time_authorities`, `limits`, `status`, `digest`.

**Rules:** The production root bundle and approval of this profile must be provisioned and pinned
outside the agent-writable candidate/checkout. The profile cannot authorize itself by adding a key.
`fixture_contract` keys and receipts are permanently ineligible for `production` assessments.
Missing or stale roots, revocation data, owner review, role assignment or protected deployment
basis block production use. No production private key or reusable credential is stored here.

## SignedReceipt

**Purpose:** Authenticate the origin of an immutable evidence, decision, policy or time payload.

**Fields:** `schema_version`, `kind=signed_receipt`, `assurance_domain`, `payload_kind`,
`payload_digest`, `issuer_id`, `key_id`, `algorithm=Ed25519`, `issued_at`, `nonce_or_sequence`,
`signature`, `receipt_digest`.

**Rules:** The signature covers a domain-separated canonical encoding of all receipt fields except
`signature` and `receipt_digest`; `payload_digest` binds the full canonical payload bytes. The
verifier resolves the issuer key from the external trust context, checks key scope/time/revocation,
verifies the signature, then compares the actual payload digest. A syntactically valid envelope or
matching hash alone proves no trusted origin. Replay is rejected where the selected policy requires
a unique sequence, freshness or single-use decision.

## EvidenceRecord

**Purpose:** Immutable result and raw observation references, separate from trust eligibility.

**Fields:** `schema_version`, `kind=assurance_evidence`, `evidence_id`, `origin_class`
(`protected_observed`, `imported_verified`, `fixture_replay`, `agent_assertion`),
`assurance_domain`, `subject_digest`, `scope`, `obligation_ids`, `inputs` (hashes),
`process_baseline`, `tool` (name/version/executable digest), `execution_policy_digest`,
`profile_digests`, `collector_id`, `started_at`, `finished_at`, `termination` (completed/failed/
timeout/crash/infrastructure_error), `raw_outputs` (content-addressed refs, byte counts and hashes),
`measurements`, `result`, `limits`, `exclusions`, `receipt_ref`, `import_chain`, `limitations`,
`digest`.

**Rules:** Every bound field is validated against the subject and gate policy. The original
issuer/attestation and each transformation remain visible for imports. A timeout, missing raw
output, missing measurement, or unsupported tool result is unknown/blocked, never clean/zero. An
authentic result may remain ineligible because its scope, age, issuer, type, transformation or
policy differs. Fixture/replay/agent classes never satisfy production trusted predicates.

## HumanDecision

**Purpose:** Authenticated human judgment with a narrow authority and immutable lifecycle.

**Fields:** `schema_version`, `kind=assurance_decision`, `decision_id`, `assurance_domain`,
`actor_id`, `role`, `authority_ref`, `identity_provider`, `authentication_method`,
`independence` (rule IDs, checked relationships, result), `subject_digest`, `scope`,
`obligation_ids`, `gate_ids`, `policy_digest`, `outcome` (approve/reject/conditional_approve/
request_changes/withdraw), `rationale`, `conditions`, `issued_at`, `valid_from`, `valid_until`,
`supersedes`, `receipt_ref`, `digest`.

**Rules:** An issuer receipt authenticates the decision payload and binds the actor assertion. The
trust profile must authorize issuer, actor role, exact decision class, scope and independence.
Claims in the 002 decision-reference schema are not evidence of authentication. A later withdrawal
or supersession is a new authenticated event referencing the prior ID; it does not rewrite that
record. Expiry and revocation affect current eligibility. Conflicting live decisions block an
unqualified pass. A condition must be discharged by exact eligible evidence or decision reference.

## GatePolicy and ExpectedPredicate

**Purpose:** Define the complete scoped gate before considering observed results.

**GatePolicy fields:** `schema_version`, `kind=assurance_gate_policy`, `id`, `assurance_domain`,
`authority_source`, `applicable_scopes`, `subject_requirements`, `expected_set_rule`,
`predicates`, `required_roles`, `independence_rules`, `allowed_evidence`, `freshness_rules`,
`not_applicable_rules`, `outcome_routes`, `limits`, `status`, `digest`.

**ExpectedPredicate fields:** `predicate_id`, `gate_id`, `subject_ref`, `obligation_id`, `scope`,
`predicate_class` (deterministic_check/trusted_evidence/human_decision), `required`,
`source_ref`, `policy_rule_ref`, `acceptable_result`, `applicability`, `authority_ref`.
A `deterministic_check` adds `check`: `candidate_valid` requires a validated native candidate;
`trace_obligation_satisfied` requires a recomputed, passed 004 report that contains that exact
obligation ID. Neither check authenticates evidence or a human decision.

**Rules:** Derive the expected set from applicable 002 instances, 004 obligations and reviewed gate
rules before inspecting evidence. Empty, conflicting, duplicate, unresolved or unclassified
mandatory sets block. Tailoring keeps the obligation visible and links its exact authenticated
decision; it does not shrink the denominator. Policy may define a stricter rule but cannot allow
fixture, agent, missing, unknown, stale or timeout data to count as a production pass.

## PredicateResult and FreshnessAssessment

**PredicateResult fields:** `predicate_id`, `state` (satisfied/failed/blocked/not_evaluated/
not_applicable/stale), `evidence_ids`, `decision_ids`, `reason_codes`, `subject_refs`,
`required_action`.

**FreshnessAssessment fields:** `prior_subject_digest`, `current_subject_digest`,
`changed_bindings`, `affected_evidence_ids`, `affected_decision_ids`, `affected_gate_ids`,
`impact_paths`, `unknown_dependencies`, `scope_expansion`, `state`, `reasons`.

**Rules:** Freshness is computed for current use and never mutates prior evidence, decisions or
gate results. A scoped `no_impact` decision, where the policy permits one, adds a signed
`baseline_change` containing prior assessment, old/new subject and policy digests, and sorted exact
changed paths. Only mechanical predicate subject-reference rebinding may accompany a subject
change. It narrows review scope but cannot revive a stale gate or old subject-bound evidence. Unknown/new unlinked dependencies expand review or block.

## GateResult and PortableAssessment

**GateResult fields:** `schema_version`, `kind=assurance_gate_result`, `gate_id`,
`assurance_domain`, `scope`, `subject_digest`, `policy_digest`, `trust_profile_digest`,
`evaluator_identity`, `as_of`, `time_basis_ref`, `outcome` (`pass`, `fail`, `blocked`,
`not_evaluated`, `not_applicable`, `stale`), `expected_predicate_ids`, `predicate_results`,
`evidence_digests`, `decision_digests`, `unmet_obligation_ids`, `reason_codes`,
`required_actions`, `next_route`, `limitations`, `digest`.

**PortableAssessment fields:** `schema_version`, `kind=assurance_assessment`, `subject`,
`policy_refs`, `trust_context_refs`, `evidence_records`, `decision_records`, `receipts`,
`gate_results`, `raw_output_refs`, `history_refs`, `readable_report`, `limitations`, `digest`.

**Rules:** Evaluation outputs are derived and unsigned. `pass` requires complete non-empty expected
predicates, eligible inputs and decisions, no conflicting live decision, and authenticated time for
current production use. A prior `pass` used with a changed identity becomes `stale` for the new
assessment. `not_evaluated` means no evaluation was performed; a started evaluation missing a
required input is `blocked`. Every non-pass has stable reason, affected ref and action. The
portable verifier rechecks references, receipts, policy eligibility, predicate matrix and gate
outcome without Fabro; missing external bytes block. The 004 capability fields remain unchanged.

## State and authority transitions

```text
004 sealed candidate/report + 002 sealed plan
  → subject constructed and closure verified
  → external receipt verified (authentic or untrusted)
  → evidence/decision eligibility checked (eligible or ineligible)
  → complete expected predicates evaluated
  → scoped gate result sealed
  → later baseline/policy/revocation change: current use stale or blocked
```

A 005 gate result never transitions a native need status, 004 report capability, Fabro run state,
engineering release state, or deployment state. Historical facts remain immutable; a new
assessment is a new record.
