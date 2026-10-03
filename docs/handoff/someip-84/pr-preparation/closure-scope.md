# PR preparation and closure scope

Prepared locally following the user's explicit approval. No PR, issue, branch push,
commit, merge or publication was created. The destination for this contribution
is `eclipse-score/inc_someip_gateway`; the current fabric workspace remains intact.

The proposed title is **fix(socom): reject duplicate servers across minor versions**.
[PR body](pr-description.md) follows the pinned native bugfix template's structure.
The template's closing-keyword placeholder is replaced by a related-ticket reference
because [#84](https://github.com/eclipse-score/inc_someip_gateway/issues/84) describes
broader identifier/discovery work. A dedicated bugfix ticket can be selected by
maintainers when the contribution is submitted. No ticket is invented here.

## Approved subject

[External user approval](../factory/runs/score-someip84-repair-b4ard87e/external-user-approval.json)
transcribes the user's decision outside Fabro and binds it to the previously
presented final run, 269 candidate source hashes and portable archive checksum.
It records approval of the scoped work and local PR preparation. It does not claim
an upstream maintainer decision or a signed assurance receipt. The original packet,
native terminal record and failed-run history retain their measurement-time statuses.
Human-owned task markers remain unchanged under the repository instructions.

## Native change boundary

| File | Purpose |
|---|---|
| `score/socom/impl/service_identifier.cpp` | Registration comparison excludes minor version |
| `score/socom/impl/service_identifier.hpp` | Documents registration identity and compatibility semantics |
| `score/socom/BUILD` | Exposes the internal header needed by the regression target |
| `score/socom/test/unit/BUILD` | Integrates the registration-key test source |
| `score/socom/test/unit/service_identifier_tests.cpp` | Registration, ordering, identity and boundary regression matrix |
| `score/socom/test/unit/runtime_tests.cpp` | Connector duplication, compatibility, lifecycle and slot isolation cases |

The reviewed patch has 3,198 insertions and six deletions; most additions are the
regression matrix. Fabric orchestration, scoped capture/perf helpers and the R1–R3
guard fixes provide verification provenance in this repository and are not added
to the upstream native patch.

## Closure decision

The local repair and PR-preparation scope is complete and user-approved. The patch
supports closing a bounded duplicate-registration bugfix after upstream review,
required CI and merge into its intended branch. No upstream issue is closed now.

Use **Related to #84** in the prepared body. Retain #84 for the public identifier
model, discovery requests with optional minor/instance filters, and the representation
of minor version as a service-instance property. Closing the whole of #84 requires
implementation of that remaining scope or an explicit upstream maintainer decision
that records where the remaining obligations are tracked. Local user approval does
not establish that upstream scope decision.

The native contribution guide assigns content review and merge to Committers and
uses a bugfix review ticket. At submission, the submitter must follow that process,
provide the real evidence attachment location, and confirm any rebase still matches
the validated candidate or supply affected verification for changes. No completed
upstream review, CI run or contribution identity/sign-off is asserted here.

## Exact patch and verification

The original `someip-84.patch` and original candidate manifest predate later candidate
expansion/formatting. They remain preserved as historical artifacts. Use
[someip-84-verified.patch](someip-84-verified.patch), exported from the approved final
packet against baseline `f8a196c3b16d5172d898394ab99b0ed81346d63d`.
Its SHA-256 is `c581f6319e5301d751b0a1caf2e51fbc8eda374d172199b121c1962158479732`.

[Preparation verification](preparation-verification.json) records clean application
with `git apply --check --whitespace=error`, followed by actual application in a
disposable baseline copy and equality with all six final candidate file hashes.
All 269 candidate source hashes and the original archive identity were checked.
[Candidate files](candidate-files.json) bind the six native file identities.
No native test queue was rerun for this documentation/patch export.

[Repair evidence](../factory/review-repair-run.md),
[offline packet verification](../factory/runs/score-someip84-repair-b4ard87e/offline-packet-verification.json)
and [portable archive](../factory/runs/score-someip84-repair-b4ard87e/review-packet.tar.gz)
provide the exact validation subject. The archive remains 36,969,655 bytes with
SHA-256 `2b8f5c40ae194ba06f8e6c95933c05727ec8f4bec563ef7c4fc10ef3e33fa6da`.
