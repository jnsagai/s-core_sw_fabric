# Guideline coverage measurement (T023/T025)

`quality coverage --request REQUEST.yaml --out MATRIX.json [--json]` is read only.
It never runs an analyzer, adopts a policy, discharges a human review or clears a finding
using a suppression/disposition. Existing packet/assessment work remains separate.

Version 1 `quality_coverage_request` fields: `profile`, `baseline`, `manifest` transport
refs; nullable `previous_manifest`; `analyses` (at most 20 `{request, report}` ref pairs,
existing native-import selections/reports); `protected_roots` (at most 32).
The current baseline is the existing sealed `quality_import_baseline`: actual frozen
source bytes, complete file/expected-unit set and declared tool/config/pack/suite identities.
Selected reports must reproduce exactly by read-only import of their original inputs.
Different source/component/profile/tool identities remain drift, never current clean evidence.

Sealed `quality_guideline_manifest` fields: `id`, `origin` (`fixture|external_unverified`),
`scope` (`component`, complete `files`, nullable complete `translation_units`),
`expected_guidelines` (null for unknown denominator, otherwise a nonempty list),
`source_refs`, `rows`, `review_state: pending_human`, `digest`, plus version/kind.
At most 1000 unique expected IDs and rows; rows outside a declared set are rejected.
Every declared ID generates a cell, even when its mapping row is missing. Unknown scopes
also preserve every supplied row; no count of findings or query-pack rules fills the denominator.
Expected entries are `{guideline_id, native_category, applicability, rationale, source_ids}`;
applicability is `applicable|not_applicable|unknown`. Categories may be null and remain unknown.

Source refs are `{id, ref, license, notice, native_status}`; ref selects a bounded JSON
`quality_guideline_source` with exactly version/kind, `id`, `guideline_ids`, `license`,
`notice`, `native_status`. Source IDs, categories and mappings are supplied declarations,
not authenticated adoption. Each linked source must actually list the referenced guideline.
Sources contain IDs/references only; proprietary guideline text stays external.

Rows: `{guideline_id, source_ids, mechanisms, expected_evidence, manual_evidence}`.
Expected evidence names exact original artifact IDs; missing or truncated required artifacts
remain unresolved. Manual evidence names remain pending human review regardless of presence.
At most 32 mechanisms per row, each `{id, kind, automation_class, tool, native_id,
identity_digest, availability, enabled, limitations, source_ids}`. Kinds are
`tool|manual|audit|unsupported`; automation classes `automatic|partial|manual|audit|unsupported`;
availability `supported|unsupported|unknown`. Tool/check/identity are required for tool
mechanisms and null otherwise. Enabled is boolean or null, never inferred from zero findings.
An automatic clean mechanism needs adequate independently reproduced import and a matching
retained local run proving exact check selection and source/profile/tool/config identity.
CodeQL coverage stays unknown/unsupported while eligibility and genuine execution are unavailable.

Cell states: `covered|findings_open|pending_manual|unsupported|excluded_pending_review|unknown`.
Matching native findings take precedence, including suppressed findings. All required
mechanisms must be satisfied; manual/audit/partial mechanisms and manual evidence stay pending.
Exclusions never shrink the denominator. Missing source/category/mapping, disabled checks,
drift, incomplete extraction and unavailable evidence remain explicit reasons.
`covered` measures local structural observations only, never compliance or review acceptance.

Sealed `quality_guideline_matrix` retains profile, current baseline, manifest, original
source records, reproduced analyses, prior manifest and changes, all cells and counts/gaps.
Fields: `profile`, `baseline`, `manifest`, `sources`, `analyses`, `previous`, `changes`,
`scope_state`, `denominator`, `rows`, `counts`, `gaps`, `accepted_claims: 0`, `outcome`,
`origin: local_unprotected_evaluation`, `assurance_eligibility: not_eligible`,
`engineering_readiness: not_evaluated`, `limitations`, `digest`, plus version/kind.
All current profile compliance gaps remain; no fixture or locally covered row clears them.
Exit 0 requires no unresolved coverage/profile gaps; 1 publishes an incomplete matrix;
2 rejects malformed/unsafe/unavailable input and preserves prior output.

Controls/source JSON: 1 MiB each, 32 sources/16 MiB aggregate; reports/output/aggregate
selected records: 96 MiB. Existing depth/node/source/native-output bounds apply. Guard all
controls, sources, native input/report paths and selected source roots before atomic output.
Recheck selected transports and frozen source bytes before publication.
