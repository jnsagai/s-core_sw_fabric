# Increment 008 data model

Version-1 records reject unknown or missing fields and duplicate keys, bound strings, arrays and
bytes, carry `digest` over canonical JSON without `digest`, and state
`engineering_readiness: not_evaluated`. Native RST is read only.

## Safety analysis profile (`safety_analysis_profile`, YAML)

`id`, `status`, `sources[]` (`id`, `repository`, `commit`, `path`, `sha256`), per analysis
(`fmea`, `dfa`): `directive`, `work_product`, `catalogue_field`, `mandatory` (option → regex),
`violates[]`, `mitigated_by[]`, `catalogue[]` (`id`, `group`, `scope` = `component|platform`,
`source`); `requirement_directives[]`, `architecture_directives[]`, `mitigation_issue_pattern`,
`rules[]` (`id`, `check`, `source`), `platform_allocation` (`status`, `accepted_directives[]`,
`accepted_work_products[]`), `internal_fault_prefixes[]`, `checklist[]` (`id`, `question`),
`gates` (`design`, `closure`), `loop.max_iterations`.

## Native analysis set

Needs from the scanned files: `id`, `type` (directive), `path`, `line`, `digest` (raw directive
bytes), `options`, `links`, `content`. Applicability rows from list-tables in analysis files:
`id`, `description`, `applicability` (`yes|no|placeholder`), `rationale`, `path`, `line`.

## Analysis report (`safety_analysis_report`)

Profile identity, component, analysis kind, iteration, current and baseline file digests,
coverage rows (`catalogue_id`, `group`, `scope`, `applicability`, `rationale`, `items[]`,
`state` = `analysed|excluded|allocated|uncovered|applicable_without_item|
excluded_without_rationale|unknown_applicability`), items (`id`, `digest`, `catalogue_id`,
`violates`, `mitigated_by`, `mitigation_issue`, `sufficient`, `status`, `mitigation_state` =
`missing|proposed|linked_pending_review|claimed_sufficient`, `violations[]`,
`reanalysis_required`), promotions (`item`, `field`, `from`, `to`, `classification` =
`UNTRUSTED_PROMOTION|PROMOTION_UNREVIEWED`), re-analysis (`changed`, `removed`, `new`,
`affected_items`, `unreferenced_new_elements`), feedback (`item`, `action` =
`requirement_or_aou_review|escalate_to_human`, `routes`, `iteration`, `max_iterations`), flags,
findings (`code`, `subject`, `detail`, `rule`), `design_prerequisites` (`state` =
`blocked|ready_for_design_review`, `reasons`), `outcome` (`complete|blocked`).

## Review packet (`safety_review_packet`)

Report identity and all report file digests, `native_diff` (added/removed/changed items and
fields), `coverage`, `affected` requirements and architecture, `mitigation_changes`,
`verification_evidence[]` (as supplied, `verification: not_verified`), `missing_evidence[]`,
`uncertainties[]`, `checklist[]` (`id`, `question`, `answer: pending_human`, `support`), and
`approval_scopes` for `design_acceptance` and `closure` (`gate_id`, `subject_files`,
`subject_items`, `authorizes`, `does_not_authorize`, `pending`).

## Gate evaluation (`safety_gate_evaluation`)

Packet digest, verified decisions (`assessment_digest`, `gate_id`, `assurance_domain`,
`outcome`, `binding` = `exact|other_subject`), and per gate `state`
(`blocked|awaiting_decision|stale|accepted`), `reasons`, `domain`. Closure is never `accepted`
unless design is `accepted`.
