# Proposed native artifact and traceability contract v1

Status: design only; implement and test in 004. This is a deterministic adapter contract over
native S-CORE artifacts. It is not a new native schema, requirements authority, approval channel,
or production repository writer.

## Public CLI

~~~text
score-fabric artifact index --request REQUEST.yaml --out INDEX.json [--json]
score-fabric artifact candidate --request REQUEST.yaml --out CANDIDATE.json [--json]
score-fabric artifact validate --candidate CANDIDATE.json --profile PROFILE.yaml [--json]
score-fabric artifact trace --request REQUEST.yaml --out REPORT.json [--json]
score-fabric artifact diff --before BEFORE.json --after AFTER.json --profile PROFILE.yaml [--json]
score-fabric artifact drift --candidate CANDIDATE.json --profile PROFILE.yaml [--request REQUEST.yaml] [--json]
~~~

| Exit | Meaning | Output behavior |
| --- | --- | --- |
| 0 | Requested index/candidate/validation/trace succeeded; or diff/drift found equivalence/clean state | Publish validated result atomically |
| 1 | Well-formed domain input failed semantic/native/coverage checks; or diff/drift found change | Candidate/index not replaced; `trace` may publish a bounded blocked report; comparison result is emitted |
| 2 | Malformed, unsupported, unsafe, integrity-invalid, tool-unavailable, or infrastructure input | Preserve every prior output and source; emit bounded diagnostic |

`--json` emits a bounded summary, identities, status, counts, and findings. It does not emit a
second unbounded copy of target content. Every successful or blocked report includes the six
`not_evaluated` capability fields.

## Operation inputs

- `index` requires a target snapshot and native artifact profile. It runs the native build/export
  unless an exact fresh export is supplied and the profile explicitly permits that validation mode.
- `candidate` requires a complete sealed 002 plan, validated 003 package bound to that plan,
  artifact profile, target snapshot, and one or more typed edit operations. A trace profile is optional
  and used only when trace evaluation is explicitly requested.
- `trace` requires the same plan/package bindings, a reviewed trace profile, and either a target
  snapshot or a valid candidate package. It can publish a blocked report so missing obligations remain
  reviewable.
- `validate` rechecks a sealed candidate's integrity, closure, profile compatibility, native
  receipt/source set, index, and report. It does not trust embedded `valid` flags alone.
- `diff` accepts two independently valid indexes/candidates. `drift` verifies bytes and can
  rederive from an exact request; neither command adopts edited output.

Every referenced file has a transport hash and, where defined, a verified semantic/self-digest.
Local roots are operational data. Inputs, protected reference trees, and output destinations cannot
alias by lexical path, resolved path, inode, or hardlink.

## Authority and trust

Authority order is:

1. Pinned S-CORE native source, metamodel, and actual template/configuration.
2. Reviewed target/project artifact and trace profiles with exact sources.
3. Explicit request values and authorized decision references within those profiles.
4. Derived indexes, candidates, and reports.

The sealed plan establishes work-product obligations. The workflow package supplies source-bound
expected outputs and data boundaries, but its nodes, traversal, labels, and filenames do not define
native IDs or relation semantics. A local `reviewed` string is not authenticated authority; pending
production profiles stay visibly pending and are ineligible for production mutation.

Expected outputs, native-build success, trace existence, and zero findings are not proof of content
correctness, evidence trust, review, or acceptance.

## Source scan and native-export reconciliation

The scanner accepts UTF-8 RST within the declared closure and records exact byte/line spans. It
recognizes only directive names/types selected by the profile, preserves option spelling/order and
content bytes, and treats literal/code-block bodies as opaque. It does not execute RST, Python,
Jinja, includes, substitutions, or template code.

The native validator produces a fresh `needs.json`. For each local live wrapper/need, reconciliation
requires:

- exact source-qualified ID, integer native version, type, title/content/status;
- exact normalized required/optional fields and relation selectors;
- matching source path/docname and source location within the configured tolerance;
- one source record and one export record;
- no source need fabricated from literal example text.

Imported external needs must match a declared immutable export/namespace/prefix and the selected
external-reference policy. Unknown source-only/export-only/ambiguous records fail.

## Native type and status semantics

The selected metamodel, not a global status list, defines each type. Version 1 explicitly preserves:

- `document`: `draft | valid | invalid`, mandatory `safety`, `security`, and `realizes` work product;
- `feat_req` and `comp_req`: `valid | invalid` plus their distinct required fields/links;
- `aou_req`: `valid | invalid` and its own required fields;
- feature/component architecture types and their exact allocation/fulfilment relations;
- feature/component FMEA/DFA and security-analysis fields and mitigation target types;
- `testcase` full/partial verification links and `mod_ver_report` aggregation links.

The profile may support a strict subset but cannot widen a regex, status, field, relation, or target
type. Unsupported types are indexed as opaque only when normative completeness is unchanged and no
operation/obligation targets them; otherwise fail.

Managed document classes declare whether exactly one `document` wrapper is required. Wrapper and
children retain separate outcomes. A `valid` wrapper with an invalid/missing/unresolved mandatory
child is invalid as a candidate aggregate; no child receives wrapper status by propagation.

## Scoped candidate edits

Every edit binds stable operation ID, plan instance, exact source-qualified subject/anchor, target
path, expected preimage, allowed rule, explicit new value, origin, and rationale.

Supported version-1 operations are `create_document`, `set_option`, `set_content`, `add_link`,
`remove_link`, and `insert_need`. All are exact-span transformations. A create copies a hashed native
template and applies only declared replacements. Inserted needs provide complete explicit native
fields/content/relations. No semantic value is generated from a title, filename, prose, default
status, workflow ID, or model call.

The engine computes changed spans and proves every byte outside their union unchanged. It rejects:

- stale preimages or duplicate/ambiguous subjects;
- field/relation/type/status outside profile/metamodel policy;
- unresolved template placeholders or executable template constructs;
- path/scope escape, case collision, symlink/hardlink alias, rename, deletion, or arbitrary patch;
- unexpected whitespace/comment/prose/link/ID/manual-decision change;
- parse, native build/export, reconciliation, or round-trip mismatch.

All edits are applied in memory before one disposable validation. No partial candidate is published.

## Expected obligation derivation

Derivation proceeds before target inspection:

1. Validate the complete sealed plan and every applicable instance/disposition.
2. Validate the 003 package, package self-digest, selected plan/mapping/profile digests, full source
   map, and action/expected-output/data-destination bindings.
3. Match each plan instance to exactly one agreeing artifact rule per required purpose.
4. Classify every package expected output and destination as native artifact, non-native record, or
   external boundary using exact source-cited rules.
5. Expand required wrapper, contained-need, relation, allocation, verification, review-baseline, and
   aggregation path obligations from applicable trace rules.
6. Freeze canonical obligation IDs and denominator sets.
7. Only then inspect observed native artifacts and relations.

Missing/conflicting rules, an unclassified package output, unknown applicability, unresolved
mandatory disposition, or source/baseline mismatch blocks derivation. `external_obligation` remains
unresolved unless an explicit rule records owner/interface/boundary/evidence owed and denominator
treatment; it is never silently satisfied.

## Trace matching and coverage

A path rule is an ordered set of native relation hops. Each hop fixes field name, direction,
permitted source/target type, version behavior, and cardinality. Backlinks and narrative `:need:`
roles do not substitute for declared forward relations. A present wrong-type, wrong-direction,
wrong-scope, wrong-version, external, or partial link does not satisfy a full obligation.

Coverage output contains literal ordered denominator and numerator ID lists, exclusions, partial,
unresolved, and mismatched lists plus integer counts and exact source references. A display
percentage is derived from counts. Removing an observed artifact/link cannot remove its expected
obligation. Mandatory unresolved/mismatched obligations make trace status `blocked` and exit 1.

Required path families are selected only where applicable: context to feature requirement;
feature requirement to architecture/component allocation; component requirement to design and
implementation; requirement/design to testcase and result/report; FMEA/DFA/security analysis to
architecture, failure/threat input, mitigation/AoU, and verification; AoU to responsible boundary
and manual; work-product instance to review/baseline; aggregate report to included evidence and
dependencies.

Trace presence is structural coverage only. Content correctness, test adequacy, mitigation
effectiveness, and evidence trust remain unevaluated.

## Impact and history

Impact starts with an identity-based semantic diff, traverses declared reverse native relations in
stable order, then applies conservative profile rules for shared resources, allocation, interfaces,
assumptions, analysis coverage, templates/metamodel, and baseline changes. A new expected subject
with no link, an unknown relation, or an unavailable external dependency expands scope or blocks.

Reports bind before/after fingerprints and name affected subjects, scopes, plan instances, paths,
reviews, and blockers. They never mutate prior accepted artifacts or rewrite a historical status.
Staleness is an assessment of the current candidate baseline.

## Native build boundary

Materialize the declared base snapshot plus overlay under a new bounded temporary root. Use an
isolated HOME and build output/cache. Invoke the exact profile argv without a shell, including
locked dependency mode. Capture bounded stdout/stderr, exit category, elapsed time, export/log
digests, and cleanup result. Never run a command from imported content.

Both the exact `needs_json` export target and `docs_check` must succeed, and the fresh export must
reconcile. Native syntax success cannot override fabric semantic/coverage/drift failure. Tool
unavailability or identity mismatch is exit 2, not simulated acceptance.

## Canonical package and source map

Canonical JSON is UTF-8 with sorted keys, compact separators, finite numbers, explicit nulls,
defined ordering for sets, preserved ordering for native content, and one final newline. Absolute
paths, timestamps, cache locations, and host settings are excluded from semantic identity.

Every candidate file, changed span, wrapper/need/relationship change, obligation, coverage match,
impact expansion, and material decision maps to exact plan/profile/template/request/native sources.
The overlay lists all changed/new bytes and the manifest lists every unchanged base file. Undeclared
files or unmapped semantics fail closure.

Protected publication uses a sibling temporary file, flush/fsync where supported, and atomic
replace only after all validations. Invalid requests preserve prior output.

## Diff and drift

Semantic diff categories are `baseline`, `wrapper`, `need`, `option_status_classification`,
`content`, `relation`, `containment`, `obligation`, `coverage`, `impact`, `template_profile`,
`native_validator`, and `file_bytes`. Stable sources with reordered set-like input are equivalent.

Drift verifies nested/self-digests, base bindings, overlay bytes, source map, index/report/receipt,
and optional full rederivation. It distinguishes direct package/file edits from reviewed request,
snapshot, template, metamodel, artifact-profile, or trace-profile changes. Drift has no accept or
repair flag; resolution is source change plus regeneration or an explicitly reviewed native update.

## Required finding vocabulary

Minimum stable codes:

`SNAPSHOT_DIGEST`, `SNAPSHOT_FILE`, `SNAPSHOT_ALIAS`, `PROFILE_UNSUPPORTED`,
`PROFILE_REVIEW_PENDING`, `METAMODEL_DIGEST`, `TEMPLATE_DIGEST`, `DIRECTIVE_PARSE`,
`LITERAL_FALSE_NEED`, `EXPORT_SOURCE_MISMATCH`, `DUPLICATE_NATIVE_ID`,
`NATIVE_ID_COLLISION`, `NATIVE_STATUS`, `NATIVE_FIELD`, `RELATION_UNSUPPORTED`,
`RELATION_DIRECTION`, `RELATION_TARGET_TYPE`, `REFERENCE_UNRESOLVED`,
`EXTERNAL_REFERENCE_FORBIDDEN`, `WRAPPER_MISSING`, `WRAPPER_MULTIPLE`, `CHILD_INVALID`,
`EDIT_PREIMAGE`, `EDIT_SCOPE`, `EDIT_UNRELATED_CHANGE`, `PLACEHOLDER_UNRESOLVED`,
`PLAN_PACKAGE_BINDING`, `ARTIFACT_RULE_MISSING`, `OUTPUT_UNCLASSIFIED`,
`EXPECTED_ARTIFACT_MISSING`, `ALLOCATION_MISSING`, `VERIFICATION_MISSING`,
`TRACE_MISMATCH`, `EXCLUSION_AUTHORITY`, `IMPACT_UNKNOWN`, `IMPACT_UNLINKED`,
`NATIVE_TOOL_IDENTITY`, `NATIVE_BUILD_FAILED`, `NATIVE_EXPORT_MISSING`, `CLOSURE_LIMIT`,
`OUTPUT_ALIAS`, `PACKAGE_INTEGRITY`, `GENERATED_DRIFT`.

Each finding includes phase, stable pointer, source-qualified subjects, source refs, message, and
required action. Codes are adapter diagnostics, never native statuses or gate outcomes.

## Explicit exclusions

Version 1 does not delete or rename native artifacts; apply candidate changes to production;
invent engineering text, identifiers, classification, status, or relations; call models/providers;
fetch external links; authenticate decisions; collect/accept trusted evidence; assess content
adequacy; register/run workflows; or change engineering/readiness/release state.
