# Quality contracts and remaining proposed execution (010)

**Status:** Implemented interfaces are listed below; native CodeQL execution remains a design
proposal awaiting prerequisites and implementation. Owner review remains pending. The local Clang-Tidy
capability/run slice follows [its exact implemented contract](clang-tidy.md), additional local
tools follow [their contract](complementary-tools.md), and read-only native imports follow
[the import contract](native-import.md). Draft/correction observations follow
[their implemented contract](dispositions.md), fixture decisions follow
[independent replay](decisions.md), and coverage follows [its exact contract](coverage.md).
Packets follow [their implemented contract](packet.md), and independent assessment follows
[its implemented contract](assessment.md).
CodeQL installation/source inspection follows [its exact prerequisite contract](codeql-prerequisites.md);
it invokes no analyzer or reporting interpreter and has no eligible execution path.

## Commands and outcomes

```text
score-fabric quality capabilities [--adapter ADAPTER] --request REQUEST.yaml --out INVENTORY.json [--json]
score-fabric quality run          [--adapter ADAPTER] --request REQUEST.yaml --out RUN.json       [--json]
score-fabric quality import       --request REQUEST.yaml --out RUN.json       [--json]
score-fabric quality disposition  --request REQUEST.yaml --out REVIEW.json    [--json]
score-fabric quality decision-subject --request REQUEST.yaml --out BINDING.json [--json]
score-fabric quality decision     --request REQUEST.yaml --out DECISION.json  [--json]
score-fabric quality coverage     --request REQUEST.yaml --out MATRIX.json    [--json]
score-fabric quality packet       --request REQUEST.yaml --out PACKET.json    [--json]
score-fabric quality assess       --request REQUEST.yaml --out ASSESSMENT.json [--json]
```

Exits:0 for an observed complete capability/processed import/emitted review packet, a run without
findings or incompleteness, or a fresh local correction observation;1 for a published
finding/incomplete/unavailable/blocked/non-pass result;2 for malformed, unsafe or unavailable
selected input with previous output preserved. A capability0 or packet0 is not engineering
acceptance. Each command uses exact version 1 fields and guarded atomic publication.
`assess` cannot pass with the current unmapped profile. Decision replay may return 0 only
for an independently replayed `accepted_fixture` observation. CodeQL inspection always returns
1 or refuses with 2; it never returns successful analysis. Adapter defaults to `clang-tidy`;
explicit choices are `clang-tidy`, `cppcheck`, `asan`, `ubsan`, `codeql`. Combined modes refuse.

## Selected requests

All requests have `schema_version: 1`, an exact `kind`, transport SHA-256 selections and
`protected_roots`. The table gives the complete required field sets beyond the envelope;
nullable selections and nested field enums are defined in the linked exact contracts/schemas.
No optional field is inferred from the command prose.

| Kind | Core fields |
| --- | --- |
| `quality_capability_request` and adapter capability variants | profile, toolchain, config, timeout_seconds, output_limit_bytes, protected_roots |
| `quality_run_request` and adapter run variants | all capability fields; component, root, files, translation_units, expected_units, include_dirs, defines |
| `quality_import_request` | profile, frozen baseline, raw artifacts with native format/tool/pack/suite identity, extraction/phase manifests, declared origin, protected roots |
| `quality_disposition_request` | origin, draft, current, previous, action, protected_roots |
| `quality_disposition_subject_request` | review, disposition_request, policy, protected_roots |
| `quality_disposition_decision_request` | all subject fields; decisions, assurance_domain, as_of |
| `quality_coverage_request` | profile, baseline, manifest, previous_manifest, analyses, protected_roots |
| `quality_packet_request` | profile, coverage pair or null, current/prior import pairs, disposition selections, explicit source snapshots, notice associations, protected roots |
| `quality_assessment_request` | profile, packet, nullable current baseline, 005assessment/trust-context pairs, domain/as-of, protected roots |

For imports the literal fields are `profile`, `baseline`, `artifacts`, `extraction`, `origin`,
`protected_roots`. For packets they are `profile`, `coverage`, `analyses`, `dispositions`,
`source_snapshots`, `notices`, `protected_roots`. Assessments require `profile`, `packet`,
`current_baseline`, `decisions`, `assurance_domain`, `as_of`, `protected_roots`.

Adapter request kinds use `quality_<adapter>_capability_request` / `quality_<adapter>_run_request`
for cppcheck/asan/ubsan/codeql. Clang-Tidy preserves the original unprefixed kinds. Supporting
requests/records use the literal names in their exact contracts. [Schemas](../../../schemas/README.md)
and reader field sets are tested together; native vendor payloads retain their original fields.
Existing reader bounds/path safeguards and the [data model](../data-model.md) apply.

## Profile and selection composition

The current `s-core-quality-v1.yaml` binds C++17/MISRA C++:2023, pinned native policy source
hashes/statuses/notices, primary/complementary roles, required gaps and sanitizer candidates.
Its mapping remains `unknown`, and `decision_policy_ref` remains null. Installed byte identities
belong to each explicitly selected toolchain; effective configuration belongs to the selected
native/candidate configuration. Requests bind all three by original transport SHA-256, and run
baselines bind their source/scope and those selections together. Historical transports preserve
their original bytes and hashes. The current candidate adds the explicit optional
[`installed_context`](installed-context.md): four installed candidate toolchains, complete original
license notices and the CodeQL source/build discrepancy. Older profiles without this section
remain valid, and the exact preceding profile bytes are retained in the legacy fixture.
The new current profile hash is a new policy selection; it does not rewrite old evidence.

CodeQL's selected configuration adds the reviewed source lock, roots, native suite, time scan
configuration/report patch and native source descriptors, with nullable reporting/eligibility
inputs. The measured [source checkpoint](../source-reconciliation.md) establishes equal reviewed
and declared-build trees; [prerequisite inspection](../codeql-prerequisites-acceptance.md) measures
240 native source files, 2,068 installed files and 13 embedded library identities. Compiled build
provenance, qualification and eligible-use/report configuration remain unverified. Local tool
identities and native status strings are provenance; owner engineering decisions remain pending.

Original T001's candidate consolidation is complete, with qualification/eligibility unknown.
T011/T012's eligible native phase interfaces remain incomplete. The selection composition is explicit;
future adopted/mapped profiles or native execution interfaces require their own reconciled contract.
No current fixture or proposed profile satisfies human T032.

## Execution boundary

- Materialize verified source bytes in a disposable copy and inspect hooks before any native build.
  Execute only adapter-owned argument templates; no user-provided shell command.
- Record source, include/header/generated input and effective configuration identities. Expand
  native Clang-Tidy checks and compare requested/available mechanisms before claiming support.
- Retain original Clang-Tidy YAML/text and Cppcheck XML. No native-SARIF label for a generated
  projection. Cppcheck is optional/complementary; its checks are not fabricated MISRA mappings.
- Sanitizer binaries must actually execute with independently retained build/runtime statuses.
  Preserve runtime settings and scoped suppression refs, refuse incompatible combinations.
- Local readers bound control bytes before parsing and validate depth/nodes/JSON values. Original
  request/profile/toolchain/configuration/native controls are refrozen before returning results.
  Changed controls refuse with exit 2 and prior output intact. Tool availability is checked across
  every selected dependency; one absent asset cannot hide another changed identity.
  LeakSanitizer fatal errors keep execution/import scope incomplete even beside an ASan finding;
  original stderr survives portable replay. [Current sandbox failure](../sanitizer-environment.md)
  remains an unmet native runtime validation gate.
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
