# Increment 011 implementation acceptance

Status: local implementation and scoped native development qualification verified; owner and
real engineering/live-target acceptance pending T032/T033. Initial local-phase evidence below
remains historical; the continuation section records the later authorized Flash measurements. Constitution 1.1.0 is a proposal for owner review.

## Initial local-phase authority and preserved checkpoint

Checkpoint `b2aa9a7a49a054621f38e59f3aef6d6e5daf3cce` was pushed to `origin/main` before
011 edits. Implementation is on `011-change-impact-and-freshness`; no merge, deployment,
provider call or running queue migration occurred. The v3 owner brief is a verbatim copy from
Downloads. The original foundation brief and frozen `factory/runs/` evidence remain unchanged.
The current user instruction authorizes development beyond the historical first-session stop.

Spec Kit v1.0.12 at `e77daa9021d20db26b878f7dfa5640fe5a42d04e` was installed in a disposable,
volume-bound external Linux workspace through shared storage selection. Global v0.14.0 and global
tool/cache settings remain unchanged. Spec Kit scripts used the pinned CLI on PATH and explicit
`SPECIFY_FEATURE_DIRECTORY`. `.specify/extensions.yml` is absent. The brief resolves local
implementation choices; unavailable provider/runtime proof remains explicit.

## Development measurements

Baseline before 011: format, Ruff, mypy (122 modules), foundation and build passed. The initial
baseline suite reported 1,989 passed, 22 skipped and three failures because `SCORE_FABRO_BIN`
was absent. All three required compiler/native cases passed when supplied the pinned binary.

The final optimization suite passes 67 checks, including an actual subprocess stdio service,
blocking command hook, a single-line SARIF exceeding 1 MiB, immutable raw digests, exact location queries,
traversal/symlink refusals, restart budgets, repeated-query stops, source/Skill/baseline drift,
unknown usage/dependencies, hard role ceilings, five modes, policy drift and compiler narrowing.
The pinned native validator accepts the narrowed agent graph with its candidate hook/MCP TOML.
This establishes configuration conformance only: no agent stage was activated.

The first full 011 regression reported 2,055 passed, 22 skipped and one failure. Changed-relation
seeds had replaced the existing `A -> B` impact witness with `B`. Expansion now preserves
content-change witnesses and widens remaining scope from relation-only seeds; the existing test
was kept unchanged. The focused impact regression passes 95 checks. Original failed-run logs
are retained rather than overwritten.

Full regression rerun: **2,056 passed, 22 skipped** in 384.95 seconds. Subsequent convergence
adds focused checks for oversized collector metadata, actual summary-only transmission and
broad sensitive scope. The final affected-scope regression passes **139 checks**, including
all affected SOME/IP helpers, all 67 optimization cases and three required native compiler cases.
These results are recorded separately and do not inflate the full-run test count. Required native compiler cases and optimization conformance use
`SCORE_FABRO_BIN=/home/jefferson/.local/share/s-core-tools/fabro-1b4fb152-agent32768/fabro`.
The 22 existing skips concern explicitly unselected native checkouts/builds/exports, CodeQL
requests, the 006 runtime environment and full catalogue. They are not native readiness evidence.

Convergence also aligns generated command/expected-output paths with `summary.json`, keeps
complete host evidence, and caps the serialized feedback file including its trailing newline at
5,000 bytes. Classifier thresholds and precedence are explicit in candidate policy and audited;
broad safety/architecture work cannot bypass S4 supervision by taking the S3 branch.

Development log inventory: [validation/](evidence/validation/), including initial and final JUnit,
pytest, format, Ruff, mypy, foundation, build and frozen dependency synchronization logs.
The foundation check preserves all 64 FAB rows, 19 roadmap dependency rows, locks and local links.

## Benchmarks and consistency

Five retained pre-budget fixture contexts run through the actual old/new impact, manifest and
context-bundle pipeline. The same deterministic outcome predicates cover scope, trace IDs,
mandatory check records, raw evidence references and pending human acceptance before/after.

| Fixture | Activity | Estimated context reduction |
| --- | --- | --- |
| B1 | Metadata | 95.12% |
| B2 | Local C++ correction | 93.07% |
| B3 | Unit tests | 91.03% |
| B4 | Component feature | 88.98% |
| B5 | Safety/architecture | 86.94% |

These are conservative UTF-8-byte context estimates over explicitly synthetic development
fixtures. Provider input/cache/output/reasoning tokens, cost and runtime savings remain null.
The live 60–80% uncached reduction target is **unmeasured**. Fixture equivalence cannot establish
native engineering adequacy or acceptance. See [baseline](evidence/benchmark/baseline.json),
[optimized comparison](evidence/benchmark/optimized.json) and [self-audit](evidence/self-audit.json).

The self-audit checks all 17 functional requirements and their task/code/test/symbol links,
policy envelopes, eight digest-bound procedural Skills, disabled live policy, control documents
and roadmap linkage. Its `complete` state means consistency checks passed, not feature or
engineering acceptance. [coverage.yaml](coverage.yaml) supplies the explicit mapping.

Final Spec Kit analysis checks 17 functional requirements, 14 acceptance scenarios, four success
criteria and 36 tasks against 15 constitutional principles. Every functional requirement has
traceable tasks; no new consistency conflict or local buildable gap remains. The 34 local tasks
are checked only after measured validation. Convergence remains partial for the two existing
owner/external tasks below; no duplicate task or empty convergence section is appended.

## Open owner/external work

- T032 remains unchecked: review constitution proposal, policy, Skill mapping and the seven
  reviewer-owned requirements checklist items. No review has been accepted by an agent.
- T033 remains unchecked: owner engineering review, actual S-CORE engineering qualification
  and the 60–80% live routine target remain open. Scoped development guard/service wiring and
  two separately authorized ten-call Flash comparisons are measured below. Tool projection
  reaches 66.32–66.60% on controlled rendering fixtures, without proving engineering adequacy.
  Default native guard use still refuses execution without a private operator instruction.


The SOME/IP helpers produce summary-only new feedback and deny generic raw reports/broad grep.
Frozen queue helper snapshots and prior feedback/raw evidence are unchanged. Existing queues
must not be retroactively treated as protected or migrated by this feature. The initial local phase added no native S-CORE build, real CodeQL qualification, engineering
acceptance or paid call; the separate owner-authorized qualification follows.

## Scoped continuation and measured overhead convergence

The owner instructed `go`, then `deepseek flash only`. T037–T040 prepare the review subject,
implement private activation/transport caps, qualify pinned native behavior and measure ten
Flash-only requests. [Review draft](review-draft.md) pins constitution/policy/Skills/checklist
subjects without accepting them. Existing 007 profiles and default live policy remain disabled.

[Qualification evidence](evidence/qualification/README.md) reports 30.46–30.63% uncached input
reduction over five paired structured-rendering development proxies. All ten outputs match
fixture expectations, cache hits are zero and native input/output/reasoning reconciles with
provider usage. These measurements do not satisfy real S-CORE engineering adequacy or the
60–80% target. Conservative peak-price cost totals $0.019258; actual billed cost stays null.
The request meter is closed at ten requests and its cap cannot be reset by a restart.

Real native hooks revealed `run_id=petri` and missing tool-event cwd. A pinned, exact private
process/workspace binding now identifies the API run and prevents cross-run/stage reuse.
Native fixture-provider tool execution returns a 379-byte bounded summary from >1 MiB SARIF
and blocks generic `read_file`; that local fixture is not real-provider acceptance evidence.
A native run can succeed despite a provider-stage error, so stage/raw-provider records are
checked separately instead of accepting the outer run status.

T042 removes only already-denied/unselected tool declarations from optional experimental
provider input. It preserves every message and selected schema, rejects explicit unavailable
tool choices, checks original/projected ceilings and records both hashes. Tests and offline
replay of real native requests validate this path; no new live savings are asserted.
Current ordinary activation, human checklist decisions and engineering authority remain pending.

The original experiment's outer 24 KB bound did not independently compare serialized
provider input with the S0 governor's conservative 20,000-token limit, although every
observed input was below it. Final transport hardening now applies the pinned per-task
input/output/call limits before transmission; regression covers each refusal. Retained
original measurements are not rewritten into validation of this later implementation.

Continuation validation: full regression **2,083 passed, 22 skipped**; after final per-task
ceiling hardening, affected regression **166 passed**. These are separate measured runs.
Frozen sync, repository format/Ruff, mypy (148 modules), foundation consistency and package
build pass. [validation-summary](evidence/qualification/validation-summary.json) links
retained logs. Final self-audit maps 18 functional requirements and 42 tasks with no missing
artifact/symbol links, 40 local tasks complete and T032/T033 still unchecked. No engineering
decision or checklist item has been accepted by an agent.

## Authorized second comparison

The subsequent owner `go` approved ten additional Flash requests capped at $0.10. A fresh
volume-bound workspace/private server/ledger retained the original fixture prompts and expected
outputs, with the same empty tool selection in both variants. The original evidence and closed
ledger remain byte-identical. [New evidence](evidence/projection-qualification/README.md) reports
66.32–66.60% uncached input reduction: B1 3,237→1,081, B2 3,238→1,090, B3 3,230→1,088,
B4 3,245→1,088 and B5 3,250→1,091. All ten JSON outputs, required fixture IDs/checks/evidence
references and pending review remain equal. Cache hits are zero, so total-input and uncached
reductions agree. Each native agent stage succeeded and its usage reconciles before continuation.

Original native messages are preserved; 23 unused tool declarations are removed before
transmission. Both full native payload and transmitted payload pass current ceilings, including
the exact pinned governor's per-task limits. Conservative peak-price observed cost totals
$0.008103; worst-case pre-request reservations total $0.047131 against the $0.10 cap. Actual
billing remains null. The meter stops at ten requests and both native/transport servers stop.

The fixture target is measured and met; real S-CORE engineering performance and human
acceptance remain pending T032/T033. The audit retains the initial experiment result separately
from `development_fixture_projection_live_savings`, while `live_savings` remains unmeasured.
T043/T044 track measurement and reconciliation; no subsequent increment is authorized.

Second-comparison verification: **166 affected tests passed**; frozen sync, repository
format/Ruff, mypy (148 modules), foundation consistency and package build passed. The
independent capture verifier checks ten requests, five pairs, exact outputs and native
usage, plus byte identity of all original evidence. [Validation summary](evidence/projection-qualification/validation-summary.json)
distinguishes these checks from prior full regressions. The current audit maps 18 requirements
and 44 tasks, with 42 local tasks closed and T032/T033 pending; the owner review subjects'
hashes are unchanged. No full-suite rerun or human acceptance is claimed for this small
audit/evidence reconciliation change.
