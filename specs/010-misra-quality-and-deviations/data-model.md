# Increment 010 proposed data model

Version1 envelopes reject missing/unknown fields and duplicate keys. Every record carries
`schema_version: 1`, a fixed `kind`, canonical `digest` and
`engineering_readiness: not_evaluated`. All identities/provenance remain explicit.

## Shared bounds and bindings

- Control request: at most 1MiB; at most500 source files and 32 tools per component.
- Native output: at most 16MiB per artifact; 64 MiB combined; larger output returns incomplete,
  retains its bounded prefix and full-stream digest, and cannot count as clean evidence.
- At most10000 findings, 1000 guideline rows, 1000 disposition records and 20 decision references.
- Execution timeout: integer 1–3600 seconds per declared phase. No retries or scheduling loop.
- All local file references are `{path, sha256}`; relative source paths reject traversal and
  links. Tool references include absolute path, content digest and measured version.
- Raw retained output records contain original bounded bytes, SHA-256, original byte count and
  truncation flag. Original YAML/XML/text is never described as original SARIF.

## Quality profile (`quality_profile`)

`id`, `status`, `native_sources[]` (`repository`, full commit, path, sha256, native IDs/status,
license/reference), `language: c++17`, `guideline_edition: MISRA C++:2023`,
`analyzers[]` (role `primary|complementary`, tool/config identity, selected checks/suite,
phase limits, availability and eligibility requirement), `sanitizers[]` (native feature,
runtime settings, incompatibilities, selected suppression references), `mapping_state`
(`unknown|supplied`), `required_obligations[]`, `decision_policy_ref` or null.

The default mapping state is `unknown`; a tool support catalogue does not replace project
applicability. No default allowable deviation category is implied.

The implemented optional `installed_context` records 1–32 unique candidate toolchains, complete
original notice bytes/hashes, and CodeQL pack/source/build identities and discrepancy. Its
qualification/eligibility stay unknown; execution still uses explicit request selections.
Historical profiles without it remain valid. [Exact contract](contracts/installed-context.md).

## Frozen analysis baseline (`quality_baseline`)

`component`, optional 009run digest, source/test/header files, explicit expected translation units,
includes/defines/platform/config, source/tool/policy/query-pack/suite/configuration digests,
generated inputs and exclusions with provenance. `source_digest` and `full_digest` bind canonical
identities. An unknown expected-unit set is a separate state, not an empty complete set.

## Analyzer capability record (`quality_capability_inventory`)

For every requested tool: measured version/hash, expanded checks, effective config, library/pack
identity, supported formats, unavailable capabilities, license/qualification state and probe
phase outputs. States are `available|unavailable|unsupported|unknown`; they describe capability
only. Installation probes are labelled `local_installation_smoke_test`.

## Analysis run (`quality_analysis_run`)

Baseline/profile refs; selected tools; each phase with bounded argv, status, exit/timing/output
hashes; original artifacts; findings; expected/processed/extracted units; configuration/report
failures/exclusions; source/tool drift findings; origin and assurance eligibility.
Outcome: `completed|findings|incomplete|unavailable|failed`.

Origins: `local_unprotected_execution|imported_unverified|fixture` until a separately replayed 005
assessment supplies eligible evidence. Importing bytes or checking a self-digest cannot upgrade
origin or authority.

## Normalized finding

Fabric `id` plus original tool/check/rule ID, analyzer run/artifact/result index, original
fingerprints, guideline references only when supplied by a sourced mapping, original severity,
message, all physical/logical/related locations, suppression statuses/properties and deduplication
contributors. Deduplication requires the same tool/check/baseline and normalized location/message;
identical fingerprints alone do not authorize merging distinct locations or runs.

## Extraction assessment

`expected_state`, expected/extracted/processed units, missing/unexpected units, declared/generated
scope, exclusions and their justification refs, extraction errors, failed queries, each report
phase status, findings. `adequacy: adequate|incomplete|unknown`. Missing mandatory report,
truncation, unsupported output or nonzero phase cannot be adequate.

## Guideline matrix

`scope`, `scope_state: unknown|declared`, `source_refs`, `review_state`, `rows[]` with guideline ID,
original category, applicability/source/rationale, mechanisms (tool/check/query/compiler/manual,
version/config, automation class and limitations), expected/manual/audit evidence and current
state. States: `covered|findings_open|pending_manual|unsupported|excluded_pending_review|unknown`.
Missing rows from a declared expected set remain missing obligations. Native summaries cannot
change the denominator, category or applicability.

The implemented [coverage contract](contracts/coverage.md) uses a source-linked supplied
manifest and separate measurement matrix. All declared IDs materialize, including missing
rows; unknown denominator stays null. Reproduced imports and retained local check selection
support structural observations only. Partial/manual/audit/excluded obligations stay unresolved,
required raw artifacts cannot be omitted, and accepted claims stay zero. Prior manifest and
changed applicability/mappings are retained. Full target source byte closure belongs to packets.

## Disposition/deviation record

Stable ID, originating finding/rule/construct, source/baseline/tool/policy refs, native category,
requested kind (`correction|false_positive|deviation|recategorization|suppression`), rationale,
safety/security impact, alternatives, compensating evidence, scope, expiry/review triggers,
original native fields and 005decision refs. State: `open|pending_review|corrected|accepted_fixture|
stale|blocked`. Draft names/dates are provenance fields, not authenticated approvers.

`corrected` needs a fresh adequately executed run showing absence of the original finding at
its tracked construct. `accepted_fixture` requires reproduced005fixture decision and exact
record/source closure; production authority stays blocked while 005 T009 is unavailable. Source,
rule policy, query/suite, construct/scope or validity drift reopens/stales the disposition.

The implemented decision bridge uses separate version 1 records under
[the exact decision contract](contracts/decisions.md), preserving existing draft/correction
review records. A deterministic binding contains the full review, current frozen context,
category policy and required 005 source/policy file hashes. Decision results retain complete
selected assessments/trust contexts, independent historical replay, current gate evaluation
and signed decision reconciliation. Only this result can be `accepted_fixture`; it grants
no production or native status. Unknown category policy remains blocked.

## Review packet and compliance assessment

Packet includes current/prior run refs, baseline, extraction, complete guideline expectation or
explicit unknown state, raw-output closure, disposition history, source/tool/license notices and
checklist questions with `answer: pending_human`.

Assessment includes obligation outcomes/reasons, findings/dispositions, verified 005refs,
`assurance_domain: fixture_contract|production`, and `outcome: pass|fail|blocked|not_evaluated`.
Production cannot pass without protected 005 authority and eligible evidence. Zero analyzer findings
alone cannot yield a compliance pass. Fabric local output never changes authoritative native status.

The implemented [packet contract](contracts/packet.md) retains an original-byte archive,
explicit baseline-bound current/prior source snapshots, complete selected disposition
history and fixture decision originals. Offline import/matrix/fixture decision replay
needs no original host paths or analyzer execution. Notices explicitly associate with
selected native source/tool IDs. Structural completeness never discharges compliance gaps
or pending human questions. All packets have zero accepted claims.

The implemented [assessment contract](contracts/assessment.md) replays original portable
packet/profile/005 transports and nullable current source closure. Every guideline stays
visible; missing primary/mapping/manual/authority prerequisites block both domains.
Supporting exact packet-bound 005 passes do not adopt policy, fixture disposition validity
is reevaluated at the requested time/domain, and historical correction headers alone cannot
resolve a finding. Independent replay needs no original host files or analyzer execution.

## CodeQL prerequisite inspection

The separate [internal native phase contract](contracts/codeql-native-phases.md) defines pure
bounded command recipes and strict extracted-file string/URL projection. Native diagnostic
query output contains absolute disposable paths and four position fields; both identities must
match selected files. [Demonstration records](codeql-native-demonstration-acceptance.md) retain
raw phases/artifacts and unaccepted synthetic origin; they are reproduction artifacts outside
the public request/run schema, not a replacement for a complete execution adapter.

The [Python 3.9 reporting extension](codeql-python39-reporting-acceptance.md) retains selected
interpreter/dependency identities, original report failures, configuration YAML/generated XML,
original and transformed patch-source hashes and all four native Markdown reports for fresh
seeded/corrected databases. The optional recount variant stays explicit and unqualified;
native statuses, source IDs and the primary prerequisite configuration remain intact.

[Exact contract](contracts/codeql-prerequisites.md): frozen source lock, reviewed source root,
nullable declared-build object root and compiled pack root, native suite/config/patch source
descriptors, nullable reporting toolchain and unverified eligibility evidence. Inventory/run
records preserve original controls, measured Git trees/blobs, source/pack manifests, library
metadata, suite imports/filters and gaps. Origin is `local_unprotected_inspection`; no analysis
phase executes, diagnostics/processed units stay empty and extraction remains unknown.
These inspection records are distinct from completed native runs and cannot establish freshness
or satisfy portable packet analysis evidence. Existing version 1 packet/import records remain
unchanged.

## CodeQL imported disposition context

Distinct `quality_codeql_disposition_request` and `quality_codeql_disposition_review` version 1
records bind an original imported CodeQL finding and proposal to unavailable native inspection.
The review adds `inspection`, requires fresh_run null and unresolved open/pending_review/stale/
blocked states. Pack SHA means the complete installed manifest; suite/library identities use
original selected metadata bytes. Packets retain original context controls and immutable history;
005 bindings preserve unavailable execution/eligibility. Offline replay checks original metadata
and classification without host probes. [Contract](contracts/codeql-dispositions.md).

## Public fixed CodeQL demonstration

The distinct `quality_codeql_demonstration_request` selects only an adapter-owned synthetic
case, prerequisite/compiler/reporting/license references, patch mode, resource bounds and
protected roots. `quality_codeql_demonstration_run` retains the sealed prerequisite inventory,
original source/configuration/XML/SARIF/CSV/reports, measured patch transformation, native phases
and normalized diagnostics with original native records. Independent extraction adequacy and
execution outcome remain separate from unresolved qualification/manual/target gaps. See the
[exact contract](contracts/codeql-demonstration.md); accepted claims remain zero.
