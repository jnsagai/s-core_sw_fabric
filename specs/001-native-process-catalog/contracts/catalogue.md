# Source and catalogue contracts — implemented subset v1

Review basis: ADR0002/0003/0006, docs-as-code 8.2.0 metamodel, checked-in
Sphinx-Needs 8.3.1 fixture and freshly built process export. Increment 001
delivers the catalogue/schema adapter for the pinned minimal-consumer baseline.

## SourceRef

| Field | Implemented constraint |
| --- | --- |
| source_id | Stable configured namespace; never inferred from repository basename alone |
| repository | Canonical repository URL; immutable identity also binds commit |
| commit | Full verified Git object ID, no branch names |
| content_digest | SHA-256 of exact referenced bytes; modified trees need explicit snapshot identity |
| native_id / native_version | Exact upstream ID and integer need version when applicable; not export version |
| path / location_state | Verified relative POSIX source path or null with reason; reject absolute/traversal/escape |
| docname / lineno | Preserve native values independently; nullable when not exported |
| export_ref / pointer | Export digest and JSON pointer/export key for reproducible lookup |
| rendered_url | Informational only; may be empty or mutable, never source identity |

Record source roots as local configuration outside deterministic content. Resolve physical
paths with symlink containment checks. If required ownership/path mapping is unavailable,
return a diagnostic; do not invent a line number or prepend docs/ blindly.

## ExportManifest

Versioned project envelope: `schema_version`, unique source namespaces/repository revisions,
export path+SHA-256, metamodel YAML and schema paths+SHA-256, selected export version,
creator program/version, mount/source maps and explicit dependency namespace bindings.
Build provenance includes command argv, tool/dependency lock refs, origin, exit state and
raw log/output refs. Operational absolute paths/timestamps stay outside semantic digest.
Do not execute commands from an imported manifest or fetch its URLs during import.

The native JSON is **not** this manifest. It has `current_version`, `versions`, and
per-version `creator`, `needs`, `needs_amount`, `needs_defaults_removed`, `needs_schema`.
Use a configured supported version, verifying presence; never silently select another.
If defaults were removed, interpret absent fields using that version's property defaults.
Preserve original bytes/record plus normalized view. Missing default is not permission
to invent one. Do not execute arbitrary JSON schema expressions or relation selectors.

## NativeType and NativeEntity

NativeType: exact directive/type name, prefix/ID constraints, mandatory/optional option
rules, allowed statuses and target-type rules from pinned metamodel, with SourceRefs.
The type catalogue differs from instances of those types in exported Needs.

NativeEntity: source namespace, export dictionary key, native ID, native version, exact
type, title/content/status, local/external/template classification, SourceRef(s), raw
attributes and normalized supported fields. Kinds include workproduct, workflow, role,
guidance/template/checklist and document as defined upstream; do not guess kind from ID.
Need part identities must be preserved or rejected with explicit unsupported diagnostics
until their native representation is exercised. No silent flattening.

Logical entity identity: `(source_id, native_id, native_version)`; export dictionary keys
can encode revision differently and are retained. Duplicate raw JSON keys are rejected
before ordinary dict parsing. The same ID in independent namespaces is allowed, but an
unqualified reference resolving to multiple sources is not. External copies may only
coalesce with a primary record when manifest identity/content agrees; otherwise fail.

Template references retain source path/native ID and relationship kind. Do not turn text
inside an RST code block into a need or treat template placeholders as accepted instances.
A work-product definition such as wp__fdr_reports is not a review of a target artifact.

## Relation

Store origin entity key, native relation name, direction, raw target selector, parsed
base ID, optional exact integer version, resolved source-qualified target or diagnostic,
and SourceRef. Source evidence permits plain IDs and `[version==N]`; reject unsupported
syntax rather than evaluating it. Dictionary-key behavior was exercised by the fresh export.
`field_type: links` differs from `backlinks`. Preserve narrative `:need:` references as
content/reference metadata, without upgrading them to normative dependency relations.

## Catalogue output and failure semantics

Versioned envelope contains source-lock/manifest/schema digests, types, entities,
relations, template refs and diagnostics. Mandatory unresolved references prevent a
usable output. Optional/uninterpreted metadata may survive with warnings only when
normative completeness is demonstrably unchanged. Never equate no findings with acceptance.

Canonical UTF-8 JSON uses sorted object keys, compact separators, no NaN/infinities,
explicit nulls, and deterministic sorting of sets by defined identity; arrays whose
order carries meaning retain their order. No uncontrolled Unicode/ID rewriting.
Digest is SHA-256 over canonical semantic payload excluding its own digest, operational
timestamps/absolute roots and human presentation. Include semantic raw data (excluding
only explicitly documented operational fields) so unknown content changes cannot vanish.
Diagnostic ordering is deterministic. Test relocation and permutation invariance plus
semantic change sensitivity. Keep output format/version choices explicit in tests.

Proposed CLI: `score-fabric catalog export --manifest PATH --out PATH [--json]`.
Exit 0: generated valid catalogue only. Exit 1: semantic integrity failure. Exit 2:
invalid/unsupported input, unavailable infrastructure or usage error. Write validated
output atomically; refuse input/output aliasing, all declared source-tree destinations,
out-of-root paths and symlink escapes.
Diagnostics: `code`, `source_ref`, `pointer`, `native_id`, `message`, `required_action`.

## Implementation limits recorded in 001

The supported manifest and output envelopes are published in
../../../schemas/source-manifest.schema.json and
../../../schemas/catalogue.schema.json. The importer enforces path/digest
checks, the pinned metamodel/schema identity, supported creator version,
sparse-default fields, native mandatory options/links, source-qualified
resolution and deterministic output. Build provenance is declarative and is
never executed on import. An expected export may have null build fields;
a fresh-build declaration requires a successful command and log digest.

The checked-in fixture establishes importer behavior; the fresh minimal-consumer
process build additionally verifies the pinned process baseline as recorded in
../acceptance.md. Full score/module_template documentation builds remain
unverified. No evidence or gate implementation is implied.
