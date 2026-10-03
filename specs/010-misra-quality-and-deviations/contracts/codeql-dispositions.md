# CodeQL imported disposition context, version 1

Implemented context interface for T080; [verification](../codeql-dispositions-acceptance.md).
Existing local disposition version 1 records and hashes are preserved.

`quality disposition` selects `quality_codeql_disposition_request` with exactly the existing
request fields `origin`, `draft`, `current`, `previous`, `action`, `protected_roots`; current
adapter is exactly `codeql` and its request is a strict CodeQL run request. The origin must be
an original native import containing a CodeQL finding on a declared baseline. The draft uses
the existing exact proposal schema. No correction executes CodeQL or native reporting.

The new `quality_codeql_disposition_review` contains exactly the existing review fields plus
`inspection`, the original sealed unavailable CodeQL prerequisite run. Its baseline must equal
the review's current baseline. Origin is `local_unprotected_inspection`, fresh_run is null,
outcome unresolved, eligibility not_eligible and readiness not_evaluated. Allowed states are
open/pending_review/stale/blocked; corrected and accepted states are unavailable. Every query,
manual, eligibility, exclusion and native confidence gap from inspection remains visible.

Context comparison checks source/component/expected scope and policy, CLI transport hash/version,
configuration transport SHA, compiled pack full manifest SHA, selected native suite file SHA and
embedded library metadata hashes/versions. Imported `query_pack.sha256` means the digest of the
sorted complete installed manifest measured by prerequisite inspection; `suite.name` is the
explicit relative native suite path and its SHA is the original selected suite bytes. Library
names/versions/SHAs match original embedded qlpack metadata. These declarations stay unverified
imports; a hash match cannot establish extraction, eligibility or qualification.

A changed identity is stale. Unknown/missing pack/library context retains explicit blockers. Draft
corrections stay open pending fresh analysis; explicit correction checks remain blocked even
when source changed. False-positive/deviation proposals stay pending with all unmet prerequisites.
Only bounded Git inspection executes, after output/native-root/inspector guards. Original
request/profile/configuration/native/source/pack controls are refrozen before return.

Portable packets retain the new review, full linked history, its inspection originals/metadata
and source snapshots. Native query text/binaries remain external identities; inspection labels
are unprotected and cannot reproduce CodeQL execution. Offline replay never reads host paths.
The existing 005 subject/decision bridge retains the exact CodeQL context and its unavailable
execution blockers; no inspection or fixture unlocks a correction or production readiness.
Required notices cover CodeQL and its selected native scan/patch/source descriptors. Human
answers remain pending_human; T011/T012/T032 stay unmet.

Inspection now retains original embedded-library qlpack metadata bytes alongside pack/suite
controls. Packets replay these originals from each sealed review transport, including old versions
of replaced configuration/pack/library metadata. They do not reread a historical mutable native
path. Earlier packets with separately archived originals remain valid; older inspections without
library byte captures require their original selected library bytes to remain in the archive.

Inputs retain existing 1 MiB controls, 500 source files/64 MiB, 20 decision refs and bounded
1,000 history revisions. Inspection limits remain those in codeql-prerequisites.md; reviews
are at most 96 MiB, depth 64/200,000 nodes. Exit 1 publishes unresolved context; exit 2 refuses
malformed, unsafe or drifting selections and preserves prior output. There is no exit 0 here.

## Original observation consistency

Offline inspection validation compares retained source/build Git observations with their
summaries. Required initial HEAD/tree/status/tracked-source phases must be present, bounded and
bound to the selected source path; build-tree observations bind the pack's declared build commit
and selected build source. Subsequent refreeze observations must agree with the initial sample.
Source/build tree equality is recomputed only when the required source observations and build
tree are available. Partial/failed/truncated observations retain their explicit gaps and an
unknown relation; a known tree alone cannot imply a complete native source identity.

This checks internal consistency of unprotected originals. It does not authenticate Git output,
reproduce compiled artifacts, qualify the inspector, establish eligible use, or grant acceptance.
Original native query text remains external; its Git blob bytes are not inferred from SHA-256
identities. Existing source-lock/metadata/archive comparisons remain separate checks.
