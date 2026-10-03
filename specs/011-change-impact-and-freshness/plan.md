# Implementation Plan: Change impact, freshness and bounded AI context

**Branch**: `011-change-impact-and-freshness` | **Date**: 2026-10-03
**Spec**: [spec.md](spec.md)

## Technical Context
Python >=3.12, frozen uv dependencies, stdlib JSON/hashlib/dataclasses/SQLite-free JSON state,
existing PyYAML and exact schema/digest readers. No new tokenizer/provider dependency.
Existing 004 artifact impact and 005 freshness remain authoritative. New 011 adapters validate
inputs and derive context; 007 admission still controls catalogue/destination/cost admission.
Fabro retains execution and run state. New stage accounting is a bounded derived context ledger,
not a scheduler, requirements store or approval source. Native tool/result interception is
verified against pinned source; no post-hook result mutation is assumed.

## Constitution Check
All fifteen principles preserved. XIII–XV are a 1.1.0 proposal expressly requested by the v3
brief; owner ratification remains pending. Existing first-session stop is superseded by the
current explicit 011 implementation request. Native reference trees are read-only. Credentials
and runtime server state stay internal. New analysis/build scratch uses `score-fabric storage`.
No paid calls, publishing, merging or target acceptance is authorized. Unknowns remain blockers.

## Architecture and File Structure
- `optimization/common.py`: exact records, conservative UTF-8 token estimate, immutable refs.
- `optimization/evidence_query.py`: deterministic bounded SARIF/JSON summaries and pagination.
- `optimization/tool_results.py`: output retention/preview and persistent stage budgets.
- `optimization/firewall.py`: generic-tool denial; runtime hook adapter and bounded MCP service.
- `optimization/telemetry.py`: nullable provider usage and dimension-bound aggregation.
- `optimization/impact.py`: old/new native reverse reachability and stale baseline reports.
- `optimization/task_classification.py`: explicit S0–S4 policy, unknown scope. Candidate
  thresholds/precedence are declared in policy and audited; broad sensitive work remains S4.
- `optimization/context_manifest.py`: native-index/impact/baseline/mapping-bound scope.
- `optimization/context_budget.py`: mandatory L0/L1, optional L2 and indexed observations.
- `optimization/skill_selection.py`: file/directory-safe registry/selection/lazy rendering.
- `optimization/token_governor.py`, `model_router.py`: operational ceilings + 007 admission.
- `optimization/review_pack.py`, `prompts.py`: structured results, bounded diffs, static prefix.
- `optimization/progress.py`, `workflow_modes.py`: bounded stop reasons and derived modes.
- `optimization/server.py`, `cli.py`: stdio bounded tools and additive CLI commands.
- `optimization/benchmark.py`, `audit.py`: five offline comparisons and consistency audit.
- `.agents/skills/score-*`: eight procedural Skills; versioned registry in `profiles/`.
- `policies/optimization-v1.yaml`: explicit reviewed-candidate limits/triggers, disabled live use.
- `schemas/optimization-*-v1.schema.json`: exact versioned input/output contracts.
- `agents/context.py`, `roles.py`: optional v2 context path, lazy observations, common prompts.
- `agents/admission.py`: additive narrowed admission bridge; keep v1 replay unchanged.
- `artifacts/impact.py`: old/new relation reachability and changed relation seeds.
- `compiler/optimization.py`: narrow reviewed action projections before computing native IR IDs;
  `compiler/`: consume derived mode plans via existing native graph compile interfaces; preserve
  expected collectors/human gates, no alternative scheduling.
- `docs/handoff/someip-84/factory/`: new raw-evidence guard, bounded feedback summaries and
  no-narration instructions; historical `runs/` and active frozen queues remain untouched.
- `tests/contract/test_optimization_*.py`, `tests/integration/test_optimization_service.py`:
  negative-first contract coverage and actual no-provider stdio/tool-hook execution.

## Sequencing and Migration
1. Specify/plan/checklist/tasks/analyze before code. Reproduce huge evidence privately.
2. Containment first: bounded query adapters, result/stage budgets, deny generic raw reads,
   collector summaries and common prompts. Converge before telemetry.
3. Record baseline telemetry and five context benchmarks before adding class budgets.
4. Impact → classification → manifest → context/Skills → governor/routing/critique.
5. Progress stops/modes/review pack; native source/config verification and service replay.
6. Benchmark, full regression, audit, analyze/converge and reconcile docs.
Existing v1 profiles and public CLI output remain replayable; new policy is opt-in and narrows
rights. No running queue migration. On missing dependencies, baseline drift, unavailable bounded
service or unsupported runtime interception, refuse optimized activation. Rollback selects old
profiles only within their existing separately authorized execution scope; no silent bypass.

## Benchmark and Acceptance Strategy
Five recorded synthetic deterministic tasks are development fixtures. Measure raw/context UTF-8
bytes and conservative estimates, gate outcomes and required-check/trace/evidence equality.
Provider usage/cost/cache/wall-time savings require separately authorized runtime observations;
null is retained in offline records. Target >=60% offline reduction on routine B1–B3; distinct
live 60–80% uncached reduction remains open. Full logs and raw SARIF stay unchanged on host.
See [contracts](contracts/optimization.md), [research](research.md), [data model](data-model.md)
and [quickstart](quickstart.md). Human acceptance and runtime live qualification stay open tasks.

## Scoped qualification continuation

Add `optimization/activation.py` for private operator-instruction validation and
`optimization/provider_boundary.py` for a localhost DeepSeek-only request meter. Fabro remains
executor: the meter only admits/forwards provider transport and retains usage, never schedules,
accepts artifacts or starts successor runs. The immutable instruction quotes the current owner
messages, scopes qualification only and is pinned in native hook commands. Use a separate private
Fabro server and credentials via `private_server_root`; select scratch via shared storage. Explicit
run titles prevent auxiliary title-generation calls. Global settings/profiles remain disabled.
Capture native source/config/worker identity and real hook events before any live transmission.
Provider prices are source-derived conservative bounds, not reported bills. Qualification datasets
are explicitly development fixtures and cannot satisfy native engineering readiness. Store new
measurements separately from prior acceptance evidence. Prepare a T032 agent review draft with
artifact digests and leave every human marker untouched.

The measured native overhead exposes 23 tools, of which 13 are already denied. Optional
operator-pinned tool projection removes only denied/unselected declarations, without editing
messages or selected schemas. The guard enforces the same selected bounded tool set. Preserve
original and transmitted request hashes and apply ceilings before and after projection. The
initial ten-call experiment remains immutable; qualification of this new path stays T033.
