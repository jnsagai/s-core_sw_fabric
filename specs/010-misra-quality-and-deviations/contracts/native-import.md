# Native import and extraction contract, version 1

Implemented interface for the authorized US2 slice: `quality import --request REQUEST --out
RECORD [--json]`. Imports read files only and never invoke analyzers or reporting scripts.
The broader packet/disposition/coverage interfaces remain proposed.

## Exact selections

Request kind `quality_import_request` has exactly `schema_version`, `kind`, `profile`,
`baseline`, `artifacts`, `extraction`, `origin`, `protected_roots`. File selections are
`{path, sha256}`. Origin is `imported_unverified` or explicitly `fixture`; neither can be
upgraded by native labels, a self-digest or a declared phase status.

Baseline kind `quality_import_baseline` has exactly `schema_version`, `kind`, `component`,
`root`, `files`, `expected_units`, `identities`, `digest`. It is sealed, at most 1 MiB,
contains 1–500 hash-bound relative source/header files (64 MiB total) and a nullable unique
expected translation-unit set. Expected entries must be selected C++ source files.
Root is a local directory, protected against output writes. Source digest binds component,
file hashes and independent expected set; full baseline digest additionally binds profile and
tool identities. Native compilation/configuration details remain declared identities, not a
reconstructed or qualified build.

Each of 1–32 identities has exactly `id`, `name`, `version`, `tool_sha256`, `config_sha256`,
`query_pack`, `suite`, `libraries`, `license`, `notice`. IDs select `clang-tidy`, `cppcheck`,
`asan`, `ubsan`, `codeql`. Pack is null or `{name, version, sha256}`; suite is null or
`{name, sha256}`; libraries contain the pack-shaped identities (at most 32). CodeQL requires
pack/suite, other tools require null pack/suite. These are reported identities; import neither
requires executable availability nor verifies eligibility. The report's version/name and
extension identities must agree wherever the native format supplies them.

Each of 1–500 artifacts has exactly `id`, `tool`, `format`, `role`, `ref`, `source_root`,
`units`, `bindings`. Roles are `diagnostics`, `supporting`, `log`. Formats are
`clang-tidy-yaml`, `clang-tidy-text`, `cppcheck-xml`, `sarif-2.1.0`, `asan-text`, `ubsan-text`, `text`.
Bindings are `{source_digest, profile_sha256, identity_digest}`. Mismatched bindings remain
`BASELINE_DRIFT`/`TOOL_IDENTITY_MISMATCH` gaps; selected-byte drift rejects the request.
Units are selected translation units; source_root is an absolute POSIX analysis root used only
for deterministic location mapping. It is never opened or fetched. Per-artifact retention is
16 MiB, total 64 MiB, with at most 512 MiB original input bytes hashed across the import.
Larger original input rejects before parsing. Oversize retained inputs preserve bounded prefixes/full-stream hashes and
are incomplete; they are not parsed as complete outputs. Reference aliases/links are refused.

## Native preservation and supported SARIF

The output baseline is a sealed `quality_import_baseline_snapshot`, adding `input_digest`,
`source_digest`, `profile`, `full_digest` to the input baseline fields and retaining the original
input digest separately from its own snapshot digest.

Original formats/bytes are retained independently of normalized findings. Empty Clang-Tidy
stdout/stderr can be imported as `clang-tidy-text` because a real clean run emits no fixes YAML.
Only empty text with a successful declared analyze phase can be structurally adequate;
nonempty unparsed text stays incomplete. No synthetic fixes YAML is substituted.
Existing Clang YAML,
Cppcheck XML and sanitizer readers retain native records. SARIF 2.1.0 supports at most 32 runs,
10000 results total, explicit/descriptor-index rule references (driver or extension), direct
and indexed artifacts, chained originalUriBaseIds, primary/related locations, logical locations,
code flows, stacks, fixes and attachment artifact locations. Indexed references are resolved
without network access. Every original result, rule descriptor, fingerprint, severity,
suppression/property bag and contributor remains available. Messages by ID resolve only from
the referenced descriptor/component message strings; unresolved references are refused.

This is a bounded supported subset, not a claim of complete SARIF schema support. External
property files/inline external properties, remote URIs, unresolved indexes/bases, malformed
regions, unsupported native versions and locations outside frozen files reject with exit 2.
URI decoding rejects traversal, query/fragment, backslash, NUL and nonlocal authorities.
Embedded source hashes/content must match selected bytes. Unknown property bags remain native
data. Traversal/resource limits apply before processing deeply nested input.

Deduplication compares tool identity, source/profile baseline, native ID/severity/result kind,
rule component, normalized
message and all normalized locations. SARIF run index remains part of identity; distinct runs
are retained independently. Fingerprints alone never merge different locations. Each grouped
finding retains every contributor with artifact/run/result reference, original native record,
fingerprints and suppression. Suppressions are visible and add `UNAPPROVED_SUPPRESSION`;
native accepted/approved labels authenticate no decision.

## Independent extraction manifest

Sealed kind `quality_extraction_manifest` has exactly `schema_version`, `kind`,
`source_digest`, `observations`, `outer_exit_code`, `digest` (at most 1 MiB).
At most 32 observations have exactly `tool`, `identity_digest`, `processed_units`,
`extracted_units`, `exclusions`, `warnings`, `errors`, `failed_queries`, `filtered_checks`,
`required_reports`, `phases`. Exclusions have `{unit, reason, justification}` with nullable
hash-bound justification; justification bytes do not authorize exclusion. Each of at most
1000 phases has `{id, role, status, exit_code, timed_out, artifacts}`; role is
`extract|analyze|report`, status is `completed|failed|missing`. All phase artifact IDs must
resolve. Missing/failed/timed-out phases and failed exit codes are incomplete even if outer
exit is zero. Native finding exits are accepted only with a corresponding parsed diagnostic:
Clang-Tidy 1, Cppcheck 2, ASan/UBSan 55. Other phases require native exit 0; every actual
native code stays retained. CodeQL nonzero exit always blocks adequacy.

Every selected tool needs an analyze phase referencing all its diagnostic artifacts.
Processed units must equal their artifact-unit union. CodeQL also needs extract/report phases,
an extracted set, and native supporting IDs `database_integrity_report.md`,
`deviations_report.md`, `guideline_recategorizations_report.md`,
`guideline_compliance_summary.md`. Database integrity report counts/listing are independently
checked against the extracted units. Other tools' extracted_units must be null: no CodeQL
extraction is inferred. Native `Compliant` text is retained and has no effect on readiness.

Adequacy compares each observed set with the independent expected set. Empty, partial, unknown,
unresolved exclusions, warnings/errors, failed queries, filters, missing reports, unobserved
tools, binding drift or truncation block clean evidence. Assessment reports per-tool scope,
missing/unexpected units, native report checks and explicit gaps. Declared imported phases
remain unverified execution evidence even where structural adequacy is `adequate`.

## Output and exits

Kind `quality_native_import` has exactly `schema_version`, `kind`, `profile`, `baseline`,
`identities`, `artifacts`, `findings`, `extraction`, `gaps`, `outcome`, `origin`,
`assurance_eligibility`, `engineering_readiness`, `limitations`, `digest`.
Outcome `completed|findings|incomplete`. Exit 0 means complete declared import without findings;
1 publishes findings/incompleteness; 2 rejects malformed/unsafe/changed selected input and
preserves previous output. Outputs remain `not_eligible`, readiness `not_evaluated`.
