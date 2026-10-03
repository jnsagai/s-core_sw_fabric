# Feature Specification: Change impact, freshness and bounded AI context

**Feature Branch**: `011-change-impact-and-freshness`
**Created**: 2026-10-03
**Status**: Specified for implementation; human acceptance pending.
**Input**: [Owner v3 brief](../../S_CORE_SW_FABRIC_TOKEN_OPTIMIZATION_SPEC_KIT_CODEX_BRIEF_v3_NO_JEV.md).
Current user instruction explicitly authorizes 011, superseding historical first-session stops.
Existing 012–018 numbers and FAB-001–064 source rows remain unchanged.

## User Scenarios & Testing

Negative-first contract and integration tests are required. Engineering acceptance remains
separate from implementation checks. No provider call is authorized by this feature.

### US1 — Contain machine evidence (P1)
An agent queries normalized findings rather than reading a minified SARIF line. Raw bytes remain
unchanged and checksum-bound. Generic raw reads and broad searches are denied at admission.
AC1: A synthetic single-line 1 MiB SARIF is refused by generic read/grep; bounded rule/file/location
queries preserve exact IDs, paths and lines, pagination and raw digest without raw messages.
AC2: Every tool result is bounded in UTF-8 bytes and conservative token estimate; aggregate
stage budgets persist across server restarts. Exhaustion/repeated queries stop, with guidance.
AC3: Collectors retain full evidence outside the model-facing feedback and supply a summary.

### US2 — Observe token/cost usage (P1)
An operator records provider/runtime usage per call/task/role/model/workflow/increment.
AC4: Missing cache/reasoning/cost fields stay null; inconsistent cache splits are rejected.
Estimates never become reported provider usage. Aggregation preserves unknowns.

### US3 — Compute transitive impact and freshness (P1)
An engineer supplies old/new native artifact indexes and explicit trace relations.
AC5: Removed and new relations, cycles, additions/removals and unknown dependencies remain
visible. Reverse reachability uses both baselines. Unknown/new unlinked dependencies widen
scope or block narrowed execution. Changed baseline vectors invalidate relevant evidence and
decisions without editing history; 005 remains authoritative for trust and human decisions.

### US4 — Classify engineering tasks (P1)
AC6: Reviewed policy inputs yield S0 metadata, S1 local implementation, S2 component feature,
S3 safety/architecture/interface or S4 broad investigation. Unresolved scope is unknown and
blocked, never silently S0. Reasons and policy digest accompany the class.

### US5 — Construct lazy context (P1)
AC7: A baseline-bound manifest derives primary/transitive paths and native IDs from impact and
explicit artifact mapping, preserves required constraints/output schemas and refuses drift.
L0 constraints and required L1 safety/content cannot be trimmed; optional L2 is omitted first.
Observation text is opt-in and retrieved by ID, with a current-first bounded metadata index.
Accounting separately covers L0, L1, observations, tools and Skills using a labelled conservative
UTF-8-byte upper estimate, not an invented provider tokenizer.

### US6 — Select procedural Skills (P2)
AC8: Eight narrow activity Skills have version/content digests, explicit inputs/output/prohibitions
and stop conditions. Selection is deterministic from an explicit reviewed activity mapping;
unknown/missing mappings block. Only selected bodies load; references load explicitly within
selected Skill trees. Modifying any declared Skill file invalidates selection. Runtime rendering
is explicit; Codex installation is never treated as native Fabro Skill support.

### US7 — Govern calls and conditional escalation (P2)
AC9: Class operational limits intersect role/model absolute ceilings and existing 007 admission.
Unknown usage, budget exhaustion, stale context, unconfigured/unknown catalogue models,
missing trigger and human gates refuse calls. S4 requires explicit scoped authorization.
Critic skips/triggers carry deterministic reasons; required human reviewers remain mandatory.
No new model identifier, price, provider grant or automatic premium fallback is invented.

### US8 — Package review and stage results (P2)
AC10: Review packs contain intent, invariants, changed paths, bounded diff summary, verification
summaries and raw evidence refs. Autonomous prompts demand structured stage results and no
execution narration; schema-required engineering rationale remains permitted. Stable instructions
precede dynamic content. Self-reported checks cannot become trusted evidence.

### US9 — Stop stalled work (P2)
AC11: Repeated query/failure, unchanged correction state, no measured reduction, exhausted visits
or budget, unknown usage and human gates have explicit stop reasons. Evidence refresh can
progress by changing evidence without claiming a code correction. Fabro owns loops/run state.

### US10 — Execute bounded modes (P2)
AC12: Full/delta/correction/verification-only/evidence-refresh produce derived execution plans
with the entire supplied mandatory collector/gate set preserved. Verification/refresh omit
implementation agents. No second scheduler or requirements database is introduced.

### US11 — Measure and audit (P1)
AC13: Retain baseline and optimized records for B1 metadata, B2 C++ correction, B3 unit tests,
B4 component feature and B5 safety/architecture. Test deterministic outcome equivalence,
required checks, trace IDs and evidence preservation. Offline context-byte/token estimates are
labelled separately from live uncached usage, cost and wall time. Live savings target is 60–80%
for routine/local changes; absent provider evidence remains unmeasured, never achieved by fixture.
AC14: A self-audit links requirements/tasks/code/tests/contracts/schemas/profiles/ADRs/roadmap
and acceptance. Human review and live operational qualification remain visibly unchecked.

## Functional Requirements

- **FR-001 / FAB-045**: Enforce raw evidence admission and bounded deterministic SARIF/JSON
  queries; retain native identities, unknown locations and raw digests (US1/AC1).
- **FR-002 / FAB-045**: Limit per-result bytes/tokens/results and aggregate stage context;
  persistent duplicate-query detection and explicit omission/stop records (US1/AC2).
- **FR-003 / FAB-045**: Collector summaries accompany complete host evidence; never overwrite
  historical attempts or copy full raw machine outputs into new agent feedback (US1/AC3).
- **FR-004 / FAB-045**: Extend telemetry with nullable cache/reasoning/cost, dimensions and
  unknown-preserving aggregates; verify usage splits (US2/AC4).
- **FR-005 / FAB-043**: Traverse old/new reverse dependencies and conservative unknown/new-link
  scope; invalidate changed baseline-bound evidence/decisions via derived reports (US3/AC5).
- **FR-006 / FAB-044**: Deterministically classify S0–S4 with explicit policy reasons; unknown
  scope blocks narrow context and routing (US4/AC6).
- **FR-007 / FAB-045**: Bind manifest to native index/impact/baseline/mapping digests; deterministic
  ordering and exact scope, fail on stale input (US5/AC7).
- **FR-008 / FAB-045**: L0/L1/L2 disclosure and bounded ID retrieval; never drop required safety,
  constraints or output contract; observations lazy by default (US5/AC7).
- **FR-009 / FAB-045**: Version/digest-bound bounded Skill registry, deterministic selection,
  progressive disclosure and explicit Codex/Fabro rendering (US6/AC8).
- **FR-010 / FAB-045**: Governor narrows existing admission, preserves absolute budgets,
  unknown-usage stop and explicit escalation/critic rules (US7/AC9).
- **FR-011 / FAB-045**: Structured completion and bounded review pack, stable prompt prefixes,
  no execution narration, preserve schema-required rationale (US8/AC10).
- **FR-012 / FAB-045**: Measured progress and bounded stops without a parallel execution engine
  or automatic human acceptance (US9/AC11).
- **FR-013 / FAB-044**: Five derived modes preserve mandatory collectors and human gates;
  verification/refresh require no implementation agent (US10/AC12).
- **FR-014 / FAB-045**: Five before/after benchmarks separate estimates/replays/live facts;
  equivalent deterministic outcomes and measurable savings target (US11/AC13).
- **FR-015 / FAB-045**: Self-audit and acceptance reconcile every requirement and open task
  across the existing authoritative repository artifacts (US11/AC14).
- **FR-016 / FAB-045**: Runtime admission denies unguarded generic/MCP bypasses. Only a bounded
  repository-owned tool service may deliver evidence/context for optimized stages. Hook/config
  support is source-checked; live activation qualification requires separately measured evidence.
- **FR-017 / FAB-045**: Preserve v1 request/output replay, public CLI commands, native IDs,
  licenses and trust boundaries; optional optimization uses new versioned request contracts.

## Success Criteria

- SC-001: Single-line structured-evidence reproduction exceeds 1 MiB; model-facing result <=
  12,000 UTF-8 bytes, per-result estimate <=5,000 and stage <=12,000; unchanged raw digest.
- SC-002: All adversarial tests pass, including stale baselines/Skills, unknown usage/dependencies,
  traversal/symlink escape, aggregate exhaustion and repeated-query refusal.
- SC-003: Offline representative context estimates reduce by >=60% on B1–B3 and retain all
  mandatory checks/IDs/evidence references; live uncached-token savings remain unmeasured
  until provider observations demonstrate the distinct 60–80% target.
- SC-004: Full relevant regression, Ruff/mypy, foundation and package build pass; all buildable
  requirements map to implementation/test/task artifacts. Human-owned tasks stay open.

## Edge Cases and Authority

Oversized fields are omitted explicitly rather than clipped into false rule/path identities.
Malformed/duplicate-key JSON, missing SARIF runs, unsafe URIs, stale raw artifacts, repeated
pagination, Unicode byte amplification and changed policy bindings refuse or preserve gaps.
Unknown dependencies never shrink obligations. Digest validity establishes byte identity only.
Reference repositories remain read-only. The initial local scope excludes live calls; the explicit US12 continuation below
adds only bounded Flash qualification. Publishing, merge and deployment remain excluded. New scratch uses the shared storage policy; active work stops on disconnection.

## US12 — Scoped native qualification continuation (2026-10-03)

The owner instructed `go` after the T032/T033 handoff, then selected `deepseek flash only`.
This authorizes preparing and executing a bounded disposable qualification experiment, including
Flash-only measurements; it does not ratify the constitution, accept engineering decisions,
change existing global profiles, migrate queues or authorize other providers/fallbacks.

- **FR-018 / FAB-045**: Bind experimental native activation to a host-private, immutable instruction
  file pinned by checksum outside the agent workspace. Restrict it to qualification, exact task,
  stage, current context/governor/role/Skill digests and DeepSeek Flash. Per-provider-request
  admission must bound the entire serialized input, output, total calls and conservative spending
  before transmission; refusal persists and prevents later requests/restarts. Keep observed usage
  and derived price bounds separate. No agent-created boolean or fixture receipt grants authority.
- AC15: Real native runs demonstrate the candidate stage guard blocks before provider transmission;
  source/tool/digest/stop failures are measured, with full native logs retained. The experimental
  positive path uses the same exact guard binding and denies generic tools.
- AC16: Up to ten Flash-only requests at a $0.10 technical ceiling measure B1–B5 paired task
  variants. Fresh provider documentation reconciles stale catalogue prices. Missing required token
  usage stops continuation; absent billed-cost/reasoning data stays null. Development-fixture
  measurements establish token observations only, not real S-CORE engineering readiness.

- AC17: An optional pinned `tool_projection.allowed_tools` selects only registered bounded
  tool names. Provider projection removes declarations already denied by the native guard,
  preserves every message and selected declaration, refuses explicit unavailable tool choices
  and retains both original and transmitted request hashes. Request admission also enforces
  accumulated per-task limits from the exact pinned governor. Native input remains subject to
  the full ceiling before projection. Replay does not assert new live savings.

### Second bounded comparison authorization

The owner's subsequent `go` approves the proposed additional ten-request Flash comparison,
with a separate $0.10 ceiling. Preserve the closed initial experiment and its request cap.
Use the exact original five paired prompts/expected outputs, selecting no provider tools
for both variants because these fixtures explicitly require no tools. Check projected
payloads, native stages, output equivalence and usage before each successor request.
Retain cache hits and total input separately from uncached input. This extension remains
qualification only; T032/T033 and real engineering acceptance remain open.
