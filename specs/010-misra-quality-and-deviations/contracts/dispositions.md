# Disposition drafts and correction checks

This bounded US3 slice preserves proposals and local observations. Decision replay and
`accepted_fixture` remain pending T020/T022. Every output is `not_eligible` with
`engineering_readiness: not_evaluated`; `corrected` is a local analyzer observation.

## Exact version 1 interface

`score-fabric quality disposition --request REQUEST.yaml --out REVIEW.json [--json]`

`quality_disposition_request` fields: `origin`, `draft`, `current`, `previous`,
`action`, `protected_roots`, plus `schema_version: 1`, `kind`.
Origin/draft/previous use transport `{path, sha256}` refs; previous is nullable.
Current is `{adapter, request}` selecting an existing strict run request for
`clang-tidy|cppcheck|asan|ubsan`. Action is `draft|check_correction`.
Origin is a sealed local analysis run or native import. Import claims stay unverified;
imports cannot establish a correction in this slice.

Sealed `quality_disposition_draft` fields: `id`, `requested_kind`, `origin_digest`,
`finding_index`, `construct`, `scope`, `native_category`, `rationale`, `impact`,
`alternatives`, `compensating_evidence`, `expires_at`, `review_triggers`,
`native_metadata`, `decision_refs`, `digest`, plus version/kind.
Kinds: `correction|false_positive|deviation|recategorization|suppression`.
Finding index selects the original diagnostic/result. Construct is
`{kind: file, path, sha256}`, conservatively binding the entire frozen file and a
native physical location. Scope is `{component, translation_units}`, matching the
origin component and complete declared expected units. No AST mapping is inferred.
Native category is nullable text, an unauthenticated declaration, not adopted policy.
Impact is `{safety, security}` text. Rationale is nonempty text. Alternatives and
review triggers are distinct bounded strings. Compensating evidence and decision
refs are transport refs (32 and 20); their bytes are checked, not their claims.
Native metadata is a bounded JSON object retaining names/dates/status. Expiry is
null or RFC 3339 with timezone. Expiry is checked before and after fresh analysis.
The local UTC clock is untrusted for acceptance.

Controls/drafts: 1 MiB; selected origin/previous records and output: 96 MiB with
bounded nesting/nodes. Existing source/execution/output limits still apply.
History: at most 1000 linked revisions and 96 MiB combined linked records. Protected
roots: at most 32; proposal reference bytes: at most 64 MiB combined.
Missing/unknown fields, boolean versions or
indices, duplicate keys, bad digests, unsafe links/paths and mismatched subjects refuse.

Sealed `quality_disposition_review` fields: `draft`, `subject`, `current_baseline`,
`fresh_run`, `previous`, `revision`, `observed_at`, `time_basis`, `state`, `reasons`,
`outcome`, `origin`, `assurance_eligibility`, `engineering_readiness`, `limitations`,
`digest`, plus version/kind. Subject is `{origin_ref, origin_digest, origin_class,
finding_index, finding, baseline, digest}`. Previous is null or `{ref, digest, state}`;
immutable linked records retain history. Fresh run is null or the full newly executed
run with native raw outputs. Origin is `local_unprotected_execution`; time basis is
`local_untrusted`. States: `open|pending_review|corrected|stale|blocked`.
Outcome is `completed` for corrected, otherwise `unresolved`.

## Freshness predicates

Draft creation invokes no tool. A correction requires explicit `check_correction`, a
correction draft, changed tracked file and unchanged component, file membership,
expected/selected units, includes, defines, language and profile/toolchain/config hashes.
Added, removed or renamed files need new scope review. Expiry and source/scope/tool/policy
drift remain named reasons. Existing adapters verify current selected bytes and identities.

After input validation and output protection the command executes the selected adapter
afresh. It accepts no old clean report as freshness input. The new baseline must equal
the current selection, extraction must be adequate, native execution complete and
source unchanged during execution. The original check must be absent across the
entire component, conservatively keeping moved or unrelated occurrences open.
Filtering, suppression, incomplete scope, failed phases and truncation prevent correction.
Seals, timestamps and prior state labels cannot authenticate historical execution.

A changed current baseline stales a previous corrected observation during draft review.
Rechecking always executes again. The same draft and origin subject bind every linked
revision; revised rationale or scope needs a new draft. Old records remain untouched.
False-positive/deviation/recategorization/suppression drafts stay pending or stale.
Unknown category policy and unreplayed decisions stay explicit. Names/dates/native
suppression flags never authenticate approval or clear a finding.

Exit 0 publishes a local corrected observation; 1 publishes unresolved/stale/blocked
state; 2 refuses malformed/unsafe/unavailable input with previous output preserved.
No source fix, signer, accepted native status or readiness claim is produced.
