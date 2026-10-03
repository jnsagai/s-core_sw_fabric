# CodeQL prerequisite inspection, version 1

This bounded implementation inspects explicit CodeQL selections through `quality capabilities`
and `quality run --adapter codeql`. It does not implement database creation, extraction, queries,
report generation or eligible execution. T011/T012 remain open. Every published result is
unavailable/blocked, with zero processed units, zero accepted claims and readiness not_evaluated.

## Exact inputs

Requests reuse the capability/run fields and bounds from [Clang-Tidy](clang-tidy.md), with kinds
`quality_codeql_capability_request` and `quality_codeql_run_request`. Run source bytes are frozen
as before. No shell/build/query arguments, user cache or arbitrary native targets are accepted.

The generic toolchain fields are unchanged; kind is `quality_codeql_toolchain_profile`.
The tool's version is a declared `2.21.4`, not a version probe result. This mode never executes
the selected CLI or any reporting interpreter. Tool/runtime hashes are checked; absence is a
published capability gap and changed selected bytes refuse. The controlled Git inspector is
host `/usr/bin/git`; its identity is retained without tool qualification.

Configuration kind `quality_codeql_configuration` has exactly:
`id`, `status`, `source_lock`, `source_root`, `build_source_root`, `compiled_pack_root`,
`suite`, `scan_config`, `report_patch`, `native_sources`, `reporting_toolchain`, `eligibility`.
Envelope is `schema_version: 1`, `kind`. File selections are `{path, sha256}`.

- `source_lock` selects the existing fabric upstream lock, with one Coding Standards source
  and its full commit/source hashes. The reviewed lock is a content baseline, not human acceptance.
- `source_root` selects a read-only Coding Standards checkout. Its HEAD must match that lock,
  selected locked sources must match, and tracked source status must be clean.
- `build_source_root` is a read-only Git object checkout or null. If selected, the inspector
  compares the source/build Git trees without fetching or modifying it. Missing build objects
  keep reconciliation unknown; different trees block rather than claim equivalence.
- `compiled_pack_root` is a selected installed MISRA pack directory or null. At most 5,000
  regular files, 64 MiB total and 16 MiB per file are streamed into an identity manifest.
  Symlinks, special files, traversal and option-shaped path components refuse. Binaries and
  compiled query artifacts are never archived or redistributed. Native pack/lock/suite controls
  are retained. Pack name/version/declared CLI must be the inspected 2.61.0/2.21.4 baseline.
  Each embedded library's name/version must match the lock; missing libraries remain named
  gaps. Library source/build provenance remains unverified.
- `suite` is an explicit relative `.qls` path within `codeql-suites`; the exact source and installed
  bytes must agree. Native filters/excluded tags remain visible. No audit suite is invented.
- `scan_config` and `report_patch` select the pinned `time` configuration/patch hashes measured
  during [source reconciliation](../source-reconciliation.md). These inputs are retained as
  proposed selections, not executed or adopted configuration.
- `native_sources` contains exactly the fabric source labels `scan_config` and `report_patch`,
  with the same descriptor fields as the quality profile's native sources. Their repository and
  commit must match the selected lock's `time` entry and their hashes must bind the controls.
  Native statuses, license and notice metadata remain supplied provenance, not acceptance.
- `reporting_toolchain` is null or a file reference to the generic toolchain structure with kind
  `quality_codeql_reporting_toolchain_profile`. A declared 3.9 version and hash-bound interpreter
  and dependencies can establish selected byte identities only. Compatibility is unexecuted.
- `eligibility` is null or a bounded reference to an existing supporting record. Its original
  bytes are retained as unverified supporting input. Names, signatures, `eligible` strings or
  a fixture decision cannot unlock execution: no adopted eligibility gate is implemented here.

Controls are at most 1 MiB each; retained controls/output use existing per-artifact/64 MiB
capture bounds. Native source query/library/suite identities are at most 500 files/64 MiB,
without query text redistribution. All selected controls, source and pack manifests, tool
identities and Git state are checked again before guarded publication. Added/removed/drifting
pack files or native source/control races refuse, preserving an earlier output.

Parsed controls and final records retain depth 64/node 200,000 bounds; final serialized
records are at most 96 MiB. Source bytes are compared directly with the selected commit's
Git blob identities, including when index flags hide a modified working file.

## Execution and output

Only bounded, adapter-owned Git inspection commands execute, after output protection checks.
They disable optional locks, fsmonitor and hooks, use an isolated temporary HOME/config/cache,
and never run code from selected checkouts. Native source roots, pack roots and component inputs
remain protected. No download, patch application, source build or reporting script executes.

Output kinds `quality_codeql_capability_inventory` / `quality_codeql_analysis_run` have exact
common fields: profile, toolchain, configuration, capability, prerequisites, source_inspection,
pack_inspection, phases, artifacts, gaps, outcome, origin, assurance_eligibility,
engineering_readiness, accepted_claims, analysis_executed, inspector, limitations.
Run adds baseline, processed_units, extraction, diagnostics and source_integrity.
Envelope/digest are as before. Origin is `local_unprotected_inspection`.

Source inspection retains lock selection, repository/commit/tree, read-only status, selected file
manifest, source/build relation and reporting input identities. Pack inspection retains explicit
root, streamed full file manifest/digest, native identity/lock/suite and included-source comparison.
These are measured/declared identities with unknown compiled artifact provenance.
Pack fields additionally include `libraries`, `library_state`, `library_gaps`; each library
has name/version/path/sha256/bytes and original metadata. Native control mappings remain original
objects, with fabric-owned envelope fields strict. Process elapsed times are actual measurements;
identical selections have stable semantic observations/exit codes rather than identical durations.

Prerequisite rows retain available/unavailable/unsupported/unknown states and reasons. Equal
source trees, installed bytes or declared Python 3.9 do not clear unknown use eligibility,
unexecuted native reporting, owner configuration/tool confidence or missing execution adapter.
Every missing capability, native suite exclusion, primary/manual/mapping/production gap remains
named. Empty diagnostics are explicitly unexecuted, with unknown extraction.

Exits: 1 for a published blocked inspection; 2 for malformed/unsafe/drifting input or unsafe
publication, preserving old output. There is no successful analysis/eligibility path or exit 0
in this version. Source tree equality never authenticates compiled artifacts or engineering claims.

Original embedded-library qlpack metadata is retained as bounded `pack-library-<index>` artifacts
in library order. Earlier version 1 records remain valid; no field or native library identity is
inferred from the absence of those historical captures. The added originals establish byte
closure for history, not library source provenance or analyzer execution.
