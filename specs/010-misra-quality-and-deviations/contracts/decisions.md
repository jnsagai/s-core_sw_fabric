# Disposition decisions through independent 005 replay

This slice implements T020/T022. Existing draft/correction records remain unchanged.
Production stays blocked while 005 T009 is unavailable. Fixture acceptance describes
contract behavior only and never writes native status or engineering approval.

## Commands and records

`quality decision-subject --request REQUEST.yaml --out BINDING.json [--json]`
prepares a deterministic binding for inclusion in a 005 subject's file closure.
`quality decision --request REQUEST.yaml --out RESULT.json [--json]` independently
replays selected assessments and checks current use of their signed human decisions.
Neither command runs an analyzer or signs a decision.

Version 1 `quality_disposition_subject_request` has exactly `review`,
`disposition_request`, `policy`, `protected_roots`, plus version/kind. Review and
disposition request are transport refs. Policy is a transport ref or null. The selected
existing disposition request must use action `draft`; revalidation executes no tool.
The review is validated against its original draft/finding/native provenance. Its
current baseline must still match current source/tool/configuration selection.

`quality_disposition_decision_request` adds `decisions`, `assurance_domain`, `as_of`.
Decisions are at most 20 distinct `{assessment, trust_context}` transport-ref pairs.
Domain is `fixture_contract|production`. As-of is RFC 3339 fixture evaluation time,
never trusted production time. Missing decisions remain pending; malformed refs refuse.

Sealed `quality_disposition_policy` fields: `id`, `assurance_domain`, `status`,
`source_ref`, `source_path`, `source_prefix`, `binding_path`, `scope`, `gate_id`,
`obligation_ids`, `required_role`, `rules`, `digest`, plus version/kind.
Scope is the exact 005 `{kind, id, purpose}` with component ID matching the draft.
Source ref selects actual policy-source bytes; source path and binding path name their
logical 005 closure paths. Source prefix maps every frozen source/header file into that
closure. They are distinct safe relative paths, without wildcards or traversal.
Fixture status is `fixture_only`; production status is `pending_production_review|reviewed`.
These status declarations cannot authenticate adoption or enable production acceptance.

At most 1000 unique rule rows: `{tool, native_id, category, permission, allowed_kinds,
scope}`. Category is nullable text; permission is `allowed|prohibited|unknown`.
Kinds are explicit subsets of `false_positive|deviation|recategorization|suppression`.
Rule scope is `{component, translation_units, files}`. Effective use requires exact
component, full expected units and the single tracked construct file, plus exact native
tool/check/category/kind. No default category or proprietary guideline text is supplied.

Sealed `quality_disposition_binding`: `review`, `policy`, `current_baseline`,
`current_context`, `required_files`, `reasons`, `outcome`, `origin`,
`assurance_eligibility`, `engineering_readiness`, `digest`, plus version/kind.
Context freezes current adapter, profile, toolchain, configuration hash, settings and
native asset hashes. Required files are `{path, sha256}` for all selected sources and
policy-source bytes. Outcome is `emitted|blocked`; all bindings remain `not_eligible`.
Binding bytes in a 005 closure must equal canonical serialization of the entire record.

Sealed `quality_disposition_decision_result`: `binding`, `assurance_domain`, `as_of`,
`time_basis`, `state`, `reasons`, `decisions`, `accepted_decision_digests`, `outcome`,
`origin`, `assurance_eligibility`, `engineering_readiness`, `limitations`, `digest`,
plus version/kind. Every selected assessment/context and its replay/current-use result
is retained, including `current_gate` (null if independent replay/binding fails).
States: `pending_review|accepted_fixture|stale|blocked`; outcomes:
`completed|unresolved`. Eligibility stays `not_eligible`, readiness `not_evaluated`.

## Independent predicates

The 005 verifier must reproduce the assessment from native closure, originals and an
independently selected trust context. Its file closure must contain exact binding bytes,
every selected source/header hash, and policy-source bytes. Matching filenames, native
approval names, self-seals or a gate pass without a signed human decision do not suffice.

Require the dedicated gate, exact scope and declared obligation set, policy role and
required human predicates. Reclassify and reconcile signed decisions at current fixture
as-of using 005 receipt, actor, authority, independence, role, validity and revocation
checks. Current time cannot precede historical gate time. Gate and decision maximum age
remain binding. Conditional decisions with unresolved conditions stay blocked; this
bridge supplies no condition discharge from agent assertions.

Reevaluate the complete 005 gate at current fixture as-of, using its verified original
raw outputs, to enforce every evidence/predicate validity bound as well as human validity.
An absent native category remains unknown even if a row declares null allowed. Reused
receipt sequences across distinct selected payloads and conflicting decision IDs block.

Reject/withdraw/request-changes/conflicts and conflicting signed identities cannot be
ignored in favor of a passing record. Unknown/prohibited category, broadened suppression,
changed source/tool/profile/configuration/query-pack/suite/construct/policy scope, expiry,
missing authority and mismatched subjects remain unresolved with explicit reasons.
Correction proposals still require the existing fresh analyzer workflow.

Controls/policy: 1 MiB. Record and combined selected assessment/context bytes: 96 MiB;
existing nesting/node limits, 32 protected roots and 20 total signed decisions apply.
At most 1000 rule rows and 500 source files. Guard all selected input, source, configuration
and historical paths before atomic publication. Rejected input preserves previous output.
Exit 0 means emitted binding or accepted fixture demonstration, 1 unresolved/blocked,
2 malformed/unsafe/unavailable input. No production pass is possible in this slice.
