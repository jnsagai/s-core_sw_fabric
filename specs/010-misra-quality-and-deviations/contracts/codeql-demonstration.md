# Public CodeQL software demonstration, version 1

`quality run --adapter codeql` additionally accepts a distinct
`quality_codeql_demonstration_request`. Existing capability and target run requests keep their
inspection-only contract. The new path executes only internally fixed synthetic C++ programs;
it accepts no target root, source files, arbitrary queries/build commands or engineering approvals.
It implements a bounded public execution component of T011/T012/T078/T079; their full target
acceptance scopes remain open. Human tasks stay unchecked.

## Exact request

Envelope: `schema_version: 1`, `kind: quality_codeql_demonstration_request`.
All following fields are required; unknown fields, duplicate YAML keys and malformed values
refuse before execution:

- `id`: stable identifier; `purpose`: exactly `software_demonstration`.
- `case`: `seeded` or `corrected`. Fixed source is the labelled program from the existing
  native measurement: respectively `int main() { int unused = 7; return 0; }` or
  `int main() { return 0; }`. Expected translation units are exactly `check.cpp`.
- `prerequisites`: `{path, sha256}` selecting an existing CodeQL capability request. All of
  its profile/source/build/pack/suite/scan/patch identities are inspected and refrozen. A run
  request or a recursively nested demonstration cannot substitute for capability selection.
- `compiler`, `reporting_toolchain`, `license`: `{path, sha256}` selections. Compiler and
  reporting reuse existing strict schemas; this execution slice requires observed Python 3.9.25,
  PyYAML 5.4 and pytest 7.2.0. License selects the
  original CLI `LICENSE.md` next to the selected executable, SHA
  `d0d6cfdc857c1e0153bbd2b6f0d4ab42dfc38acec9b97b2f7f55c1f51ffe9fbf`.
  This ties the fixed demonstration to the inspected publisher terms; it cannot grant target
  or commercial-use eligibility, publisher authentication or tool qualification.
- `report_patch_mode`: `unmodified` or `git_recount`. The latter explicitly transforms the
  pinned `time` report patch in the disposable tree and preserves its original plain-check
  refusal, both recount phases and original/transformed source identities.
- `timeout_seconds`: integer 1–3600 per phase; `total_timeout_seconds`: integer 1–3600 for
  the native operation (preparation and execution); `output_limit_bytes`: integer 1024–16777216 per retained stream.
  Capture has the shared 64 MiB aggregate bound. Actual Git/native/report subcommands are
  adapter-owned; read-only prerequisite inspection/refreezing retain the nested request bounds.
  Native execution uses process-group termination on timeout and no retries or downloads.
- `protected_roots`: existing safe absolute directories, at most 32. All selected controls,
  executables/dependencies, native/source/pack roots and their inferred protections also apply.

Input controls are at most 1 MiB; depth 64 and 200000-node bounds apply. Source copying is
limited to 5000 regular Git blobs/64 MiB, excludes hooks/build execution, retains original
LICENSE and verifies copied bytes against reviewed Git object identities. Library cache copying
uses the already inspected embedded pack manifest; source and cache aliases refuse.

## Execution and failures

Outputs are checked against every input/protected root before any Git or native phase runs.
Malformed, aliased or drifting input returns 2 and preserves earlier output. Missing tools,
pack, unreconciled source/build trees, incompatible reporting versions/dependencies, failed or
timed-out phases, truncated output, malformed/empty/partial extraction and missing reports
produce a sealed `unavailable` or `incomplete` result (exit 1). No native phase executes until
the exact source/build/pack/library metadata and declared tool identities have passed inspection.
Unqualified provenance/closure/applicability remain named gaps even when the demonstration runs.

The original Python configuration script generates XML from the fixed
`report-deviated-alerts: true` configuration. Independent XML indexing, C++ compilation,
finalization, default-suite queries, SARIF/CSV interpretation and extraction queries have separate
retained statuses. Original reporting follows extraction. All four Markdown reports are required;
partial output is retained before reporting failure propagates. The original report's known
`KeyError: 'misra'` remains a failure in `unmodified` mode. Native report labels do not imply
MISRA applicability, omitted audit/default-disabled coverage or compliance.

Every phase records original argv, exit/status, elapsed time and bounded original stdout/stderr
with full-stream hashes. A nonzero original patch check is an explicit retained observation in
`git_recount` mode, never a cleared native patch-qualification gate. Inputs and original/copy
source/pack/tool/runtime identities are refrozen after success or failure before publication.
Internal measurement failures use bounded named reason codes; raw native failures stay retained.

## Exact result

Envelope: `schema_version: 1`, `kind: quality_codeql_demonstration_run`, `digest`.
Fields: `id`, `purpose`, `case`, `request`, `prerequisite_inventory`, `compiler`,
`reporting_toolchain`, `license`, `source`, `recipe`, `report_sources`, `report_patch`, `phases`,
`artifacts`, `extraction`, `diagnostics`, `result_count`, `execution_gaps`, `gaps`, `outcome`,
`origin`, `analysis_executed`, `native_reporting_executed`, `source_integrity`,
`assurance_eligibility`, `engineering_readiness`, `accepted_claims`, `limitations`.

References retain `{path, sha256}`; source retains `{path, sha256, base64}`; compiler/reporting
are original selected profile objects, prerequisite inventory is the existing sealed inspection.
`license` retains selection plus original bounded capture. `report_sources` retains the original
Git-verified manifest. `report_patch` is null or the measured recount record defined by the
internal native contract. `recipe`, `phases`, `artifacts` retain their existing native forms.
Extraction fields: `expected_units`, `extracted_units`, `native_rows`, `errors`, `adequacy`.
Diagnostics use existing native SARIF parsing; original rules/locations/statuses are preserved.

Origin is `local_unprotected_execution`, assurance eligibility `not_eligible`, readiness
`not_evaluated`, accepted claims 0. Outcome is `completed` (exit 0) only when all required phases,
extraction and four complete reports succeed and zero diagnostics remain; `findings` exits 1.
Unexecuted/failed extraction has `unknown`/`incomplete` adequacy; empty diagnostics cannot imply
clean analysis. `gaps` retains prerequisite/qualification/target/manual/production gaps together
with `execution_gaps`; demonstration success does not resolve those engineering gates.
Serialized results are bounded to 96 MiB; original analyzer binaries/compiled queries are never
redistributed. No scheduler, engineering acceptance or automatic approvals are introduced.

## Native SARIF resolution

The consumer binds `%SRCROOT%` to the disposable source root passed to native database
initialization, without modifying original SARIF. Descriptor self-indexes must equal their
containing artifact row; omitted `endLine` defaults to `startLine`. Source hashes/content,
URI/index agreement, frozen paths and column bounds remain checked. These follow
[OASIS SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html),
§3.4.4–3.4.5 and §3.30.7. General imports still require their declared URI bases.
