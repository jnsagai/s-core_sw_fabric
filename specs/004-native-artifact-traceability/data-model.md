# Data model: native artifact traceability

All persisted envelopes use exact integer `schema_version: 1`, reject unknown normative fields,
and carry a SHA-256 digest over canonical semantic content excluding only the digest field itself.
Operational local paths never enter semantic identity.

## Identity conventions

- **Source identity**: `(source_id, repository, commit)` from the selected source lock.
- **Native entity key**: `(target_namespace, source_id, native_id, native_version)`; an export key,
  document path, title, workflow node ID, or unqualified ID is not a substitute.
- **Native file key**: normalized, case-preserving relative POSIX path plus content SHA-256.
- **Plan instance key**: exact `instance_id` from the sealed 002 plan.
- **Expected-obligation key**: canonical tuple of plan instance, obligation kind, trace-path rule,
  source role, target role, scope, and purpose.
- **Candidate identity**: digest of normalized input semantic digests, complete base-file records,
  overlay bytes, edit/source-map records, index/report digests, profile identities, and native receipt.

No identity is allocated from list position, title text, filename substring, traversal order, or
workflow node ID.

## ArtifactRequest

One operation request with conditional required inputs.

Fields:

- `schema_version`, `operation`: `index | candidate | trace`.
- `target_snapshot`: local file reference, transport SHA-256, and expected semantic digest.
- `artifact_profile`: reference, transport SHA-256, and expected semantic digest.
- `trace_profile`: required for `trace`; optional for `candidate` only when trace evaluation is explicitly requested; omitted for pure `index`.
- `plan`: complete sealed-plan reference/digest, required for `candidate` and `trace`.
- `workflow_package`: validated 003 package reference/digest, required for `candidate` and `trace`.
- `operations`: ordered only by explicit dependency; otherwise canonicalized by operation identity.
- `local_paths`: operational roots for snapshot, templates, build tool/cache, and output protection.
- `output_root`: local allowed output boundary, excluded from semantic identity.

Validation:

- Referenced bytes and self-digests must agree before any target file is read.
- Plan must be complete/closed; package must validate and bind the exact plan/mapping/profiles.
- Index requests cannot carry edit operations. Candidate requests require at least one operation.
- All paths must resolve below declared roots with no input/output/source aliases.

## TargetSnapshot

Immutable manifest for the candidate base.

Fields:

- `schema_version`, `target_namespace`, `snapshot_id`.
- `source`: `source_id`, repository, exact commit, revision label, source-lock reference/digest.
- `configuration`: native docs root, configuration/build files, dependency lock, metamodel reference.
- `files[]`: relative path, byte size, SHA-256, media kind, semantic role, executable bit.
- `external_exports[]`: allowed imported-needs source identity, export digest, namespace/prefix.
- `build_closure`: exact required files and immutable external dependency bindings.
- `digest`.

Validation:

- File paths are unique under exact and case-normalized comparison.
- Every file exists with matching bytes; symlinks, non-regular files, devices, traversal, and
  multiply-linked aliases are rejected.
- Declared total/file counts and bytes must match observed values and fit the profile.
- Source commit/reference is identity data; it is not inferred from the local working tree.

## NativeArtifactProfile

Reviewed versioned configuration for parsing, editing, packaging, and native validation.

Fields:

- Profile ID/version/digest and visible review state/source references.
- Supported target/source-lock/catalogue/plan/package schema versions.
- Exact metamodel/build identities and digests.
- Supported directive types with ID regex, required/optional options, status vocabulary,
  required/optional relation fields, target types, and wrapper policy.
- Template records: immutable source identity/path/hash, destination class, placeholder/anchor rules.
- Identifier policies by target namespace, scope, artifact class, and native type.
- Allowed edit operations and writable fields/relations by artifact class.
- External-reference rules and imported namespace requirements.
- Canonicalization, source scanning, diagnostic, file/entity/relation/edit/output limits.
- Native validator fixed argv, environment allowlist, timeout/output caps, expected export path,
  and tool/dependency identities.

Validation: extracted rules must match the selected metamodel digest; pending review remains visible
and cannot authorize a production mutation.

## TraceProfile

Source-cited declaration of expected artifacts, output classifications, trace paths, exclusions,
and impact expansion.

Fields:

- Profile ID/version/digest and review/source references.
- `artifact_rules[]`: exact native work-product/purpose/scope selector to required wrapper type,
  contained-need roles/types, template, identity policy, and cardinality.
- `output_rules[]`: exact package action/output selector to `native_artifact | non_native_record |
  external_boundary`, with plan-instance and native-role binding where applicable.
- `path_rules[]`: path ID, applicability selector, ordered hops of relation name/direction and
  permitted source/target types, completeness (`full | partial_allowed`), and cardinality.
- `exclusion_rules[]`: bounded subject, authority/source reference, rationale requirements, and
  denominator treatment.
- `impact_rules[]`: triggering subject type/field/change category, affected roles/scopes, traversal
  relations, expansion behavior, and block condition.
- Limits and canonical digest.

Validation:

- Every applicable plan instance and every package expected output/data destination is covered by
  exactly one agreeing rule or an explicit authorized external/non-native classification.
- Relation names/types must exist in the artifact profile/metamodel.
- Rules cannot encode accepted evidence, approval, or readiness.

## NativeSourceFile and DirectiveSpan

`NativeSourceFile` records normalized path, bytes/digest, newline convention, UTF-8 result,
directive spans, and source identity. A managed RST file must be valid UTF-8.

`DirectiveSpan` records:

- directive name/title argument and whether it is a profiled native type;
- start/end byte and line/column positions; indentation and exact original digest;
- ordered option spans with exact names/raw values;
- content span and opaque nested/literal regions;
- enclosing directive/literal context;
- parsed native ID/version only when declared by the directive.

Validation: spans do not overlap illegally, option names are unique, boundaries remain within the
file, and need-looking text inside opaque literal content cannot become a live record.

## DocumentWrapper, ContainedNeed, and NativeRelation

`DocumentWrapper`:

- Native entity key, title/content/status, safety/security/classification options.
- Exact `realizes` links, source file/span, template/plan/source references.
- Ordered set of contained need keys and independent validation findings.

`ContainedNeed`:

- Native entity key/type/title/content/status/version.
- Type-specific options and normalized native relations.
- Wrapper key, source file/span, plan/obligation/source references.
- Independent validation findings and semantic fingerprint.

`NativeRelation`:

- Origin entity key, exact native field/direction, raw selectors in source order.
- Parsed target native ID/version selector and resolved source-qualified target, or diagnostic.
- Metamodel rule reference, source span, external/import state.

Validation:

- Wrapper and need statuses use their own native type rules. Wrapper validity never changes a
  child's outcome.
- Each managed contained need maps to one wrapper according to the profile's file policy.
- All mandatory fields/links, ID rules, types, directions, selectors, and target types are exact.
- Duplicate/colliding identities and ambiguous/unexpected external targets fail.

## NativeArtifactIndex

Derived, non-authoritative index.

Fields:

- Schema/profile/snapshot/native-export identities.
- Source file records and fingerprints.
- Sorted wrappers, contained needs, other indexed native entities, and relations.
- Source-to-export reconciliation records.
- Counts, deterministic findings, validity, limitations.
- `registration`, `execution`, `evidence`, `acceptance`, `engineering_readiness`, `release` all
  fixed to `not_evaluated`.
- Digest.

An index is usable only when source scan, metamodel validation, native export, and reconciliation
are all valid. It never supersedes native source.

## EditOperation and EditResult

Common fields: stable operation ID, kind, plan instance, target path/entity/anchor, expected
preimage digest, exact values, artifact/trace rule IDs, source/decision references, rationale.

Kinds:

- `create_document`: copy one exact template to a new declared path and realize declared
  placeholders/directives.
- `set_option`: replace or add one allowed option on one exact directive.
- `set_content`: replace one exact directive content span with explicitly supplied text.
- `add_link` / `remove_link`: change one exact metamodel-supported relation target.
- `insert_need`: insert one complete explicitly supplied native directive at a declared anchor.

Deletion, rename, whole-tree template evaluation, arbitrary search/replace, and executing template
code are outside version 1.

`EditResult` records pre/post file and semantic fingerprints, changed spans, unchanged-complement
proof, source-map entries, and findings. Any preimage mismatch, scope escape, unsupported field,
unintended span change, or unresolved placeholder blocks the whole candidate.

## CandidateFile and ArtifactCandidatePackage

`CandidateFile` records relative path, semantic role, base digest or `null` for a create, complete
post-edit UTF-8 content, byte count/digest, contributing edit IDs, and source-map entries.

`ArtifactCandidatePackage` fields:

- Schema and candidate identity.
- Input/profile/source/baseline digests.
- Complete base snapshot file records plus overlay candidate files.
- Applied edit results and source map.
- Valid artifact index over the materialized candidate.
- Optional expected-obligation/coverage/impact report, attached only by the corresponding explicit operation.
- `trace_validation`: `not_requested`, `passed`, or `blocked`; plain candidate creation records `not_requested`.
- Native build receipt.
- Integrity/closure results, limitations, fixed unevaluated capability fields, digest.

Validation: every changed byte belongs to an edit result; every edit and changed semantic element
has origins; materialized base+overlay matches the indexed/exported source set; native validation is
accepted; self-digest and nested digests agree. If trace results are attached, their status and
evidence must be internally consistent; candidate validation makes no trace-coverage claim when
`trace_validation` is `not_requested`.

## ExpectedObligation

Fields:

- Stable obligation key/ID and kind: `artifact | wrapper | contained_need | relation | allocation |
  verification | review_baseline | external_boundary | non_native_record`.
- Plan instance, target namespace, scope, purpose, disposition.
- Artifact/output/trace rule IDs and exact source origins.
- Required source/target roles, native types, relation path, cardinality, completeness.
- Package action logical key and output/destination string when applicable.
- Exclusion/external authority, rationale, and denominator treatment if allowed.

States: `expected -> satisfied | partial | excluded | unresolved | mismatched`. Only `satisfied`
counts in a full-required numerator. `partial` counts only for an explicitly partial-allowed rule.
Mandatory `unresolved` or `mismatched` makes trace validation fail.

## ObservedTrace and CoverageResult

`ObservedTrace` contains path-rule ID, obligation ID, ordered native entity/relation hops, source
locations/revisions, semantic fingerprints, and match findings. Each hop must use the exact native
field/direction/types selected by the trace profile.

`CoverageResult` contains metric ID/scope/path, full ordered expected denominator IDs, satisfied
numerator IDs, partial/excluded/unresolved/mismatched IDs, integer counts, exact ratio components,
source refs, and validity. Percentages are presentation only and never replace numerator/denominator.

## ImpactResult

Fields:

- Before/after index and baseline identities.
- Categorized changed, added, and removed native subjects.
- Direct reverse-link paths and conservative impact-rule expansions.
- Newly expected/unlinked subjects, unknown/external dependencies, affected plan instances/scopes,
  required review subjects, blockers, findings.
- Prior accepted revision references preserved as facts; candidate staleness assessment separate.
- Validity and digest.

State: `complete` only when all applicable expansion rules resolved; otherwise `blocked`. It never
changes a native status or human decision.

## NativeBuildReceipt

Fields:

- Exact validator/profile/tool/dependency/source-lock identities.
- Candidate source-set digest and disposable invocation identifiers without host paths.
- Fixed argv identifiers for export and docs check, bounded exit classes, elapsed milliseconds.
- Export/log digests, bounded diagnostics/counts, fresh native-export digest.
- `accepted` and cleanup result.

The receipt proves only that the materialized candidate ran through the declared native boundary.
It is not evidence acceptance or engineering approval.

## ArtifactReport and ArtifactDiff

`ArtifactReport` combines request/input identities, index validation, expected obligations,
coverage, impact, native receipt, candidate identity where present, findings, limitations, and
fixed unevaluated capability fields.

`ArtifactDiff` compares two valid identities with categorized changes for baseline, wrapper, need,
option/status/classification, content, relation, containment, obligation, coverage, impact,
template/profile, native validator, and file bytes. It records `equivalent` and digest.

Drift is a separate result: file/integrity drift, source/profile/request drift, rederivation
identity, and `clean`. A direct edit can never be promoted through the drift interface.

## Candidate lifecycle

```text
loaded inputs
  -> verified snapshot/profile/plan/package bindings
  -> scanned base source
  -> applied in-memory scoped edits
  -> validated changed-span complement
  -> materialized disposable candidate
  -> native export + docs check
  -> reconciled source/export index
  -> derived expected set + trace coverage + impact
  -> sealed package
  -> protected atomic publication
```

Any failure before sealing leaves a prior valid output unchanged and all sources untouched.
Publication means only a reviewable candidate package; production apply, approval, acceptance,
readiness, registration, execution, release, and deployment do not occur.
