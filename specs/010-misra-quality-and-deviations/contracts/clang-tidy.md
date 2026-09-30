# Clang-Tidy adapter contract, version 1

This bounded implementation slice covers `quality capabilities` and `quality run` for Clang-Tidy.
Other 010 interfaces remain proposed. It does not implement MISRA compliance assessment.

Both requests require exactly `schema_version: 1`, the corresponding `kind`, `profile`,
`toolchain`, `config`, `timeout_seconds`, `output_limit_bytes`, `protected_roots`.
The three selections are `{path, sha256}` refs. Limits: timeout integer 1–3600 seconds,
output limit integer 1024–16777216 bytes per artifact, aggregate retained bytes 67108864.
Capability kind: `quality_capability_request`. Run kind: `quality_run_request`, additionally
requiring `component`, `root`, `files`, `translation_units`, `expected_units`, `include_dirs`,
`defines`. No optional/unknown fields are accepted.

`files` contains 1–500 unique `{path, sha256}` source/header/test/generated-input refs below
root, maximum 64 MiB combined. Paths reject links/traversal. Translation units are unique
selected C++ source paths; expected_units is a unique selected-path list or null (unknown).
Include directories are 0–32 relative selected-tree directories; defines are 0–64 identifiers
with an optional integer value. No arbitrary compiler flags, compilation database, config
extra arguments, parent-config inheritance, analyzer plugin or shell command is accepted.
Only selected bytes are copied. Absolute includes in source and undeclared local headers
fail clean adequacy; system headers remain host-dependent and tool confidence stays unknown.

Profile exact fields: `id`, `status`, `native_sources`, `language`, `guideline_edition`,
`mapping_state`, `decision_policy_ref`, `required_obligations`, `analyzers`, `sanitizers`.
Envelope: `schema_version: 1`, `kind: quality_profile`. Native sources have exact fields
`id`, `repository`, `commit`, `path`, `sha256`, `native_status`, `license`, `notice`.
Analyzer entries: `id`, `role`, `state`; sanitizer entries: `id`, `state`.
The current slice requires mapping_state unknown and decision_policy_ref null; it cannot
consume or silently approve a supplied mapping/decision policy.

Toolchain envelope: `schema_version: 1`, `kind: quality_toolchain_profile`;
exact fields `id`, `status`, `tool`, `dependencies`, `library_dirs`.
Tool: absolute regular `path`, `sha256`, exact first-line `version`.
Dependencies: at most 32 absolute `{path, sha256}` refs to selected runtime assets.
Library directories: at most 8 absolute paths; every selected library dependency must lie
within one. The controlled environment names PATH, LC_ALL, LANG, HOME, TMPDIR and
LD_LIBRARY_PATH only. System ABI/header closure is not qualified by these selections.

Capability phases are version, verify-config, list-checks and dump-config. Native config bytes
must match the pinned clang_tidy source hash in the profile. The adapter explicitly sets a
header filter for the disposable selected source tree and records that override. Run phases
include capabilities and independent per-translation-unit analysis; no --fix is used.

Every output is sealed with a canonical digest and engineering_readiness not_evaluated.
Capability output exact fields beyond the envelope/digest: profile, toolchain, configuration,
capability, phases, artifacts, gaps, outcome, origin, assurance_eligibility.
Run output adds baseline, processed_units, extraction, diagnostics, source_integrity.
Raw artifacts retain format, base64 prefix, total bytes, full-stream sha256, retained_sha256,
truncated. Native YAML retains diagnostics/notes/fixes verbatim; derived indexes bind artifact
ID/result index and preserve native diagnostic name/level and byte offsets. No SARIF projection
or full cross-tool normalization is claimed. Suppression/filter counters stay in raw stdout/stderr.

Exit 0: completed capability probe or completed selected analysis with no diagnostics/gaps in
execution. Compliance/authority gaps remain reported separately and never imply readiness.
Exit 1: unavailable/unsupported capability, findings, incomplete extraction or failed phase.
Exit 2: malformed or unsafe inputs, identity/config drift, unsafe output selection.
Prior output is preserved on exit 2; output alias/protected-root checks precede tool execution.
No CodeQL execution, automatic source fixes, correction disposition or trusted evidence promotion.
