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
