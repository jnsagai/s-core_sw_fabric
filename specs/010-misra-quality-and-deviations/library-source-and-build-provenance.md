# Library source and build provenance follow-up

2026-10-01 03:00 UTC. Read-only measurements and publisher/source inspection; no CodeQL
compilation, query, native report, model call or engineering acceptance occurs.

## Additional measured source closure

The embedded `codeql/common-cpp-coding-standards` 2.61.0 package contains **583** `.ql`, `.qll`
and `.qls` sources matching the reviewed repository's `cpp/common/src/` tree at
`06dc6bc32b05152fbe94dbf341a3e854574c9df5`. Each source is also checked against its Git blob,
including hidden index modifications, and against the actual installed file SHA/size. Total:
**2,469,547 bytes**. Reference HEAD/status are checked before and after; no source is changed.

[Retained comparison](evidence/common-library-source-comparison.json) includes original library
metadata and every source/installed path/hash/size pair. Digest:
`da957368368b4fcaaac904d3598344b2053bce1c444e0367208f79ada75ab43a`.
This is a standalone repository/library measurement, bounded by 5,000 files and 64 MiB;
component/native-run source selection bounds and current schemas are unchanged.

The other **12** embedded libraries still lack selected source reconciliation. Full library
source provenance, compiled artifacts, runtime confidence and eligible use remain unverified.
Current inspection's aggregate gaps are preserved; this partial measurement grants no readiness.

## Installed bundle and archive comparison

At 03:10 UTC, all **912 files** (19,051,700 bytes), including **597 query sources**, in eleven
embedded `codeql/*` libraries match the same names/versions in the installed CodeQL 2.21.4
bundle. No missing, extra or differing files were found in those eleven comparisons; metadata
also matches. The bundle contains neither `advanced-security/qtil` 0.0.3 nor the separately
measured common C++ coding standards package. This establishes distribution byte equality;
it does not establish the selected Git checkout used to produce those library packs.

[Retained bundle comparison](evidence/bundle-library-comparison.json), digest
`a5b45951c4132fd376df594711fbcd52349e8fd727dcea4552551717b644a84c`, records all matched paths
and SHA/size pairs and explicit unavailable copies. Per-library limits remain 5,000 files,
10,000 directory entries, 16 MiB per file and 64 MiB combined; both directory names and bytes
are remeasured before publication.

The same 912 files also match their entries in the original installed bundle archive. The
read-only stream scans 37,691 members and writes/extracts no files. The archive SHA-256 matches
the previous local installation record:
`a94f674bb3c23ea5e9a2ad06b64847dd0277b15014d2517ecd9c41c88e6caa65`.
[Retained archive comparison](evidence/bundle-archive-library-comparison.json), digest
`6650f1929f5e0d3412cb1b3ae2ab9342c249509d07cd27880336503a04a77c0d`, retains each selected
member identity. This local archive agreement does not authenticate the publisher or reconcile
the remaining library sources. The full CLI/runtime profile, source lock and aggregate gaps
are unchanged. No native CodeQL command executes.

### Reproducing these local measurements

The retained programs use the explicit read-only installation/reference paths above and write
only their measured JSON records in this feature's evidence directory. They call bounded Git
inspection/file readers, never CodeQL or native report tools. Run from the repository root,
in this order, with the same selected installation and current prerequisite inventory:

```bash
UV_CACHE_DIR=/tmp/s-core-quality-uv-cache uv run --frozen python specs/010-misra-quality-and-deviations/evidence/measurement-scripts/common_library_source.py
UV_CACHE_DIR=/tmp/s-core-quality-uv-cache uv run --frozen python specs/010-misra-quality-and-deviations/evidence/measurement-scripts/bundle_libraries.py
UV_CACHE_DIR=/tmp/s-core-quality-uv-cache uv run --frozen python specs/010-misra-quality-and-deviations/evidence/measurement-scripts/bundle_archive_libraries.py
```

These exact retained programs were executed successfully; the common/library comparison
digests reproduce unchanged. Source/archive absence or identity differences fail the measurement.
The programs are local evidence reproductions, not an analyzer interface or an eligibility gate.

## Published compatibility and pinned recipe

The publisher's [v2.61.0 release](https://github.com/github/codeql-coding-standards/releases/tag/v2.61.0)
identifies CLI 2.21.4 and the C++ standard library at `codeql-cli/v2.21.4`. The page displays a
verified signature for the release source commit; no local cryptographic verification or
compiled-asset attestation is inferred from that page label.

The pinned source recipe provides these observations:

- `.github/workflows/code-scanning-pack-gen.yml` compiles/bundles packs using the selected
  CLI/standard-library matrix and uploads workflow artifacts. It conditionally checks out and
  includes external help files from another repository. This permits extra build inputs;
  their actual inclusion/revision in this artifact is **unknown**.
- `.github/actions/install-codeql/action.yml` obtains the CLI release and a separate standard
  library checkout. Matched embedded metadata alone does not reconcile that checkout's sources.
- `scripts/release/update_release_assets.py` selects workflow runs/artifacts and uploads a
  generated release layout. `scripts/release/release-layout.yml` generates checksums for assets.
  The reviewed files do not show an attestation-generation step; this does not prove that no
  attestation exists elsewhere or that any particular released build is authenticated.

| Selected file | SHA-256 |
| --- | --- |
| Code-scanning workflow | `23c4a7eefe808a22d42440a1ee389abfb8a9975f3f2ed3e8b03df3c7ab10d5ca` |
| CLI/stdlib installation action | `747714df3b7182a3bbb81a7bac23901708ddc2f547b8459c40c72b7878a669f8` |
| Release asset updater | `b8d839b780e548b7ad91b81d38ed3541b884ab92e369f53017585a904e0f9331` |
| Release layout | `b666131300b8bd04be401bf5a372887503ee46606f0d4bca93f6f2e915ff9d96` |
| Supported CodeQL configurations | `199391f73f9900f137878eefd5be6b5950afd3210650ffb70fd62f4b9b06648a` |

The public release page was accessible; REST release metadata, expanded asset list and checksum
download were unavailable through the browsing tool. Their contents/attestations remain unknown,
not absent. No credential was requested or used and no release command or workflow was executed.

A subsequent 03:39 UTC read-only `git ls-remote` attempt for the exact
`github/codeql` tag `refs/tags/codeql-cli/v2.21.4` returned exit 128:
`Could not resolve host: github.com`. Credential helpers/prompts and global/system Git
configuration were disabled; no clone or source-lock change occurred. The selected remote
source identity remains unknown in this environment, rather than absent upstream.

## Concrete owner review needs

Obtain provenance for the exact installed artifact/archive digest, actual build inputs and
external-help selection; reconcile the remaining library sources; review complete CLI/runtime
and reporting compatibility; and provide independently established eligible-use evidence.
Source byte equality, checksums, GitHub page labels and successful upstream checks cannot alone
authenticate the compiled artifact or accept the S-CORE engineering decision. T032/T082 remain
human-owned; no source lock or native status is modified.
