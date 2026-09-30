# Forward contracts — proposals, no implementation in 001

## InstanceIdentity and work-product plan (002)

Stable tuple: `(target_namespace, native_work_product_source_id, native_work_product_id,
scope_kind, scope_id, purpose)`. Scope kind is feature/component/module/platform;
purpose is required for multi-purpose reviews and explicit otherwise. Use a structured
tuple or unambiguous canonical encoding, not ambiguous slash concatenation. Hashes,
native work-product revisions and baselines are **bindings**, not part of logical identity.

Plan record: schema_version, identity, native type/version SourceRef, source baseline,
create/update/reuse/tailored_out/external_obligation/unresolved disposition, applicability
state+rationale+source/decision refs, template/document refs, expected verification,
required review roles and independence. Absence/unknown must not remove an obligation.
Unresolved and downstream-owned are not synonyms for satisfied.

## SubjectManifest and EvidenceManifest (005)

SubjectManifest: schema version, scope, sorted exact artifacts (logical path, source,
revision, SHA-256), repository baseline vector, process/metamodel/tool/policy/mapping/
workflow digests and expected obligation identity set. Its digest excludes itself and
approval records. Changing any relevant binding makes reuse stale unless a scoped,
authenticated impact decision covers both baselines. Preserve historical subjects.

EvidenceManifest: schema_version, evidence_id, origin enum, collector identity and
verifiable attestation reference, run/stage, scope/obligations, subject digest, input
hashes, source/process/policy/compiler/workflow/tool versions, sanitized argv/working
root mapping/environment, start/end, exit/termination/infrastructure state, stdout/
stderr/raw output refs+hashes, normalized measurements, limits/exclusions and result.
Origins: real_tool_execution, human_decision, imported_verified_evidence, fixture_replay,
agent_assertion. Origin strings and hashes alone are not authenticated provenance.
Gate policy must verify the protected collector/attestation and allowed origin.
Missing usage/extraction/result is unknown, not zero or clean. Imported verified evidence
needs its original attestation/subject and explicit trust policy, not relabeling.

## HumanDecision (005)

Record authenticated actor, assigned role/authority, independence, decision class,
subject digest/scope/process/policy baseline, accept/reject/request_changes decision,
rationale, conditions, issued time and trusted channel/receipt. Use a protected submission
service or runner whose credentials and records are inaccessible to engineering agents.
Identity/trust provider choice remains unresolved; do not implement cryptographic-looking
self-signed YAML as proof. Revocation and expiry must be checked before using a decision.
Fabro interview answer is an interaction reference, not this decision's authority.

## GateResult (005)

Required fields: schema_version, gate_id, scope, subject_manifest_ref+digest,
evaluator version/policy digest, outcome, reasons[], evidence_refs[], decision_refs[],
unmet_obligations[] and next_route from explicit mappings. Origin of gate policy must be
upstream/project_configuration/human_decision with the corresponding source reference.

Outcomes: `pass`, `fail`, `blocked`, `not_evaluated`, `not_applicable`, `stale`.
Missing/unknown enum, parse error, absent response, timeout or stale subject can never
coerce to pass. Fail means measured unmet requirement; blocked means unavailable input,
authority/tool/evidence; not_evaluated means no evaluation; stale means prior baseline;
not_applicable needs an accepted scope-specific applicability/tailoring decision.
Every non-pass carries stable reason code, artifact/obligation ref and required action.
Pass requires complete policy predicates; it applies only to that gate/scope/subject.
Required review missing => blocked even with passing deterministic checks. Aggregate
readiness checks the expected instance set; empty/missing results cannot pass by vacuity.

This vocabulary is neither native S-CORE status nor Fabro run state. Technical readiness,
approved scoped readiness, actual release authorization/publishing and downstream
deployment remain separate. Portable manifests must be evaluable without Fabro access.
