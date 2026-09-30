# Proposed quality contract (010)

**Status:** Full design proposal, awaiting completion and owner review. The local Clang-Tidy
capability/run slice follows [its exact implemented contract](clang-tidy.md). Other interfaces
and multi-tool behavior below remain planned.

## Commands and outcomes

```text
score-fabric quality capabilities --request REQUEST.yaml --out INVENTORY.json [--json]
score-fabric quality run          --request REQUEST.yaml --out RUN.json       [--json]
score-fabric quality import       --request REQUEST.yaml --out RUN.json       [--json]
score-fabric quality packet       --request REQUEST.yaml --out PACKET.json    [--json]
score-fabric quality assess       --request REQUEST.yaml --out ASSESSMENT.json [--json]
```

Exits:0 for an observed complete capability/processed import/emitted review packet, a run without
findings or incompleteness, or an explicitly labelled fixture assessment pass;1 for a published
finding/incomplete/unavailable/blocked/non-pass result;2 for malformed, unsafe or unavailable
selected input with previous output preserved. A capability0 or packet0 is not engineering
acceptance. Each command uses exact version 1 fields and guarded atomic publication.

## Selected requests

All selections use transport SHA-256 references and `protected_roots[]`.

| Kind | Core fields |
| --- | --- |
| `quality_capability_request` | profile, local tool selections, explicit probe selection, protected roots |
| `quality_run_request` | profile, toolchain, frozen root/file manifest, optional 009run ref, explicit expected units, selected analyzers/sanitizers, configuration refs, isolated working/cache roots, timeout/output limits, eligibility refs, protected roots |
| `quality_import_request` | profile, frozen baseline, raw artifacts with native format/tool/pack/suite identity, extraction/phase manifests, declared origin, protected roots |
| `quality_packet_request` | profile, current/prior runs, applicability/matrix ref or null, disposition records, protected roots |
| `quality_assessment_request` | profile, packet,005assessment/trust-context pairs, current validity inputs, protected roots |

The implementation's schemas and exact field validators must be reconciled against this design
before tests; fields cannot be inferred from command prose. Existing reader bounds/path safeguards
and the [data model](../data-model.md) apply.

## Execution boundary

- Materialize verified source bytes in a disposable copy and inspect hooks before any native build.
  Execute only adapter-owned argument templates; no user-provided shell command.
- Record source, include/header/generated input and effective configuration identities. Expand
  native Clang-Tidy checks and compare requested/available mechanisms before claiming support.
- Retain original Clang-Tidy YAML/text and Cppcheck XML. No native-SARIF label for a generated
  projection. Cppcheck is optional/complementary; its checks are not fabricated MISRA mappings.
- Sanitizer binaries must actually execute with independently retained build/runtime statuses.
  Preserve runtime settings and scoped suppression refs, refuse incompatible combinations.
- The CodeQL mode must verify CLI/library/compiled-pack/suite/config/patch identities, project-use
  eligibility and report prerequisites before analysis. Installation/version probes do not satisfy
  analysis eligibility. Unknown eligibility publishes a blocked obligation; no automatic download,
  license approval or substitution occurs during run.
- Run each CodeQL phase independently in an isolated user/cache environment. Resolve native target
  and suite names from selected sources; no invented Bazel target or audit-suite alias. Preserve
  cquery/query/report failures, filters, skipped/incompatible targets and all raw supporting reports.

## Import and adequacy boundary

- Validate native schema/version/identity and bounded multiple SARIF runs. Reject malformed XML/YAML,
  duplicate keys, unresolved external locations and missing/drifting artifact bytes.
- Every normalized finding binds its original result/artifact/run, native ID, severity, all
  locations/fingerprints, suppression status and deduplication contributors. Native suppression,
  `approved-by` names and `Compliant` strings cannot authenticate engineering disposition.
- Expected-unit state must be explicit. Compare expected versus extracted/processed units and
  preserve exclusions. Zero findings on empty/partial/unknown extraction remains blocked.
- Phase status, extraction warnings/errors, failed queries, missing/native report failures and
  truncation are independent blockers. Do not trust an outer wrapper exit code alone.
- Unknown applicability/mapping retains an unknown denominator. Audit/manual/unsupported/excluded
  rows remain obligations. A primary analyzer's partial support cannot erase manual reviews.

## Disposition and assessment boundary

- Draft correction/false-positive/deviation/recategorization/suppression records stay pending.
  Missing category/permitted-scope policy blocks effective deviation use.
- A fresh correction must bind a current source/construct and adequate later run; absence in an
  old, filtered or incomplete report is insufficient.
- Replay 005assessments independently and compare exact draft record/source/tool/policy/finding
  closure, gate/scope, allowed category, authority and validity. Self-signed agent data, raw names,
  another subject or expired/changed scope is ineligible.
- While005 T009 remains open, production assessments are blocked. Pure evaluator and fixture-domain
  positive tests are labelled fixture evidence and never exported as a production approval.
- Raw imports, local runs and installation smoke remain distinct. No command writes native accepted
  status, suppresses source diagnostics in place, changes reference repos, or claims readiness.

## Required refusal/finding classes

Local fabric reason IDs (not native process IDs): `TOOL_IDENTITY_MISMATCH`,
`CHECK_CONFIGURATION_INCOMPLETE`, `CAPABILITY_UNAVAILABLE`, `CODEQL_ELIGIBILITY_UNKNOWN`,
`QUERY_PACK_IDENTITY_MISMATCH`, `BASELINE_DRIFT`, `EXTRACTION_EMPTY`, `EXTRACTION_PARTIAL`,
`EXTRACTION_UNKNOWN`, `PHASE_FAILED`, `REPORT_MISSING`, `OUTPUT_TRUNCATED`, `RULE_MAPPING_UNKNOWN`,
`MANUAL_REVIEW_PENDING`, `UNAPPROVED_SUPPRESSION`, `DEVIATION_POLICY_UNKNOWN`,
`DECISION_NOT_REPRODUCED`, `DECISION_SUBJECT_MISMATCH`, `DISPOSITION_STALE`,
`PRODUCTION_AUTHORITY_UNAVAILABLE`. Original tool/native IDs remain separate fields.
