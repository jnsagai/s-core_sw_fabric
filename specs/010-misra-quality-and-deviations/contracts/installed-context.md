# Candidate installed context in quality profiles, version 1

T001 consolidates recorded candidate installations into `profiles/s-core-quality-v1.yaml`.
Existing version 1 profiles remain valid without this optional section. When present,
`installed_context` is mandatory in full: no unknown/missing nested fields or null substitute
is accepted. Original profile transports and historical evidence retain their original bytes.
Current requests must select the new profile SHA; policy changes make old results stale for
new assessment, while sealed historical packets remain independently replayable.

## Exact fields

`installed_context` has `origin`, `state`, `qualification`, `project_use_eligibility`, `tools`,
`codeql_pack`. Origin is `local_unprotected_observation` or explicitly `fixture`; state is
`owner_review_pending`; qualification and project-use eligibility are always `unknown`.

`tools` is 1–32 unique candidate toolchain IDs. Each item contains exactly `toolchain` and
`license_notice`. Toolchains use the existing exact Clang-Tidy, Cppcheck, sanitizer or CodeQL
toolchain schema, including declared versions and original executable/dependency SHA identities.
This list records installations; execution continues to use the explicitly selected request
toolchain and its live identity verification. Presence in the list never selects or qualifies
a tool, enables checks or adopts configuration.

Each original `license_notice` has exactly `path`, `bytes`, `sha256`, `base64`. Paths are absolute
labels, original bytes are at most 1 MiB, the complete decoded bytes must reproduce their size
and SHA-256, and truncation is unsupported. These are original notices, not legal eligibility
determinations. Pure validation does not probe historical host paths. Overall control limits
remain 1 MiB/depth 64/200,000 nodes; no executable or query-rule text is embedded.

`codeql_pack` has exactly `name`, `version`, `manifest_sha256`, `metadata_sha256`,
`reviewed_source_commit`, `declared_build_commit`, `locked_tree`, `build_tree`, `state`,
`compiled_artifact_provenance`, `library_source_provenance`, `reporting_compatibility`,
`observation_digest`, `license_notice`.

The installed pack name/version are the selected `codeql/misra-cpp-coding-standards` 2.61.0.
SHA-256 fields bind original metadata/full pack manifest and the retained observation record;
Git commits are full 40-hex identities and trees are full identities or null. `state` is
`source_trees_equal`, `source_trees_different` or `unknown`, consistent with the recorded tree
pair. Compiled/library provenance remains `unverified` and reporting `unexecuted`. The source
commit discrepancy is retained even when the measured trees agree. An observation digest is
a trace reference, not authentication or an automatic authority upgrade.

## Boundaries

Native policy source pins, IDs/statuses, license notices, C++17/MISRA edition and unknown mapping
are preserved. Deviation categories/decision policy remain unknown/null. CodeQL execution still
requires its explicit native/eligibility/reporting prerequisites and owner review. This additive
record changes neither historical origins nor pending human gates and grants no accepted claims.
