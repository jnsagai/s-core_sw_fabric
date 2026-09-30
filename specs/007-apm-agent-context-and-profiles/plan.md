# Implementation Plan: APM agent context and profiles

**Branch**: `007-apm-agent-context-and-profiles` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-apm-agent-context-and-profiles/spec.md`

## Summary

Add a deterministic `score-fabric agent` boundary around the pinned S-CORE context packages and
the pinned Fabro model catalogue. A reviewed lock pins the `mcp-servers` revision, file digests,
local launch modules and each advertised tool's schema digest and classification. Discovery
launches servers only from a verified disposable copy, speaks minimal MCP over stdio, compares
the live tool list with the lock and invokes only read-classified tools. Setup is a separate
explicit command with before/after workspace snapshots. Role profiles, context bundles,
pre-call admission (capability, fallback and budget) and post-action output checks are pure
deterministic tools. No command makes a model call, holds a credential or records an approval.

## Technical Context

**Language/Version**: Python >=3.12, existing frozen project environment.

**Primary Dependencies**: Stdlib `subprocess`/`selectors` for a bounded stdio JSON-RPC client,
existing strict readers, canonical digests and guarded publication. `git` is invoked read-only
for the workspace commit. Pinned upstream: `eclipse-score/mcp-servers`
`29aeaa8251bd006d7ed3b0ea64229ea8589ce826` (Apache-2.0); Fabro candidate
`1b4fb15281ebb724426f9e480dce48d0100ff79b` for the catalogue capture only. No new Python
dependency, no `uvx` network launch and no graph dependency install.

**Storage**: Sealed JSON outputs published atomically outside inputs and protected roots.
Upstream local working memory (`.score-local/`) remains the upstream package's hint store in
the disposable workspace; the fabric reads it only when explicitly selected and never promotes
it. Catalogue pages are checked in under `docs/evidence/007/fabro-catalogue/` as raw bytes.

**Testing**: Contract tests with a fixture stdio server for handshake, drift, limits and
side-effect cases; strict model/role/ledger/result validation; glob and change-set tests; CLI
exit tests. A real integration test launches the pinned servers from a disposable `git archive`
copy of the read-only reference checkout (enabled by `SCORE_MCP_SERVERS_SOURCE`). Ruff, mypy,
pytest, foundation checker, offline build.

**Target Platform / Project Type**: Linux CLI/library in the existing package.

**Performance Goals**: Bounded handshake/tool timeouts (default 10 s/30 s), 1 MiB per JSON-RPC
line, 256 tools per server, 20,000 workspace files and 256 MiB snapshot bytes, 10,000 ledger
entries. No latency SLA.

**Constraints**: Reference repositories stay read-only; discovery/setup run only on a disposable
copy and a named disposable workspace. Upstream `uvx` Git references are unpinned and are not
executed. Fabro skips failed MCP servers and exposes every tool of a configured server, so the
fabric blocks on required-server drift and refuses a role whose server exposes an ungranted tool.
Documentation model IDs/prices are not authoritative; only captured catalogue rows are used.
Live model calls and provider credentials are out of scope.

**Scale/Scope**: Three pinned packages (two runnable, one unsupported), draft developer and
independent-critic roles, draft DeepSeek routine profiles. FMEA/DFA and other domain roles
(008+), overnight budgets and recovery (016), and any paid smoke test are excluded.

## Constitution Check

*GATE: Passed before Phase 0 research and re-checked after Phase 1 design.*

| Principle / gate | Pre-research decision | Post-design result |
| --- | --- | --- |
| Native authority, explicit policy (I, III) | Profiles are drafts; no LLM-derived policy | Preserved; every refusal cites a lock, profile or catalogue field |
| Portable record (II) | Outputs self-contained and digest-sealed | Preserved; bundles and checks carry exact inputs and baseline |
| Human accountability (IV) | No approval or answer channel for roles | Preserved; forbidden grants refused, no decision records written |
| Deterministic checks / fail closed (V, VI) | Admission and output checks are code, not LLM judgment | Preserved; unknown usage, drift and malformed output stop |
| Traceable changes (VII) | Context binds commit and native source digests | Preserved; change sets compare exact snapshots |
| One runtime (VIII) | No scheduler; Fabro keeps run state | Preserved; derived agent config is candidate text only |
| Bounded AI (IX) | Paths, tools, models, destinations, budgets, retries explicit | Preserved; forbidden credentials and run tools refused |
| Incremental delivery (X) | Cover FAB-027–FAB-030 only | Preserved; 008 roles and 016 overnight budgets remain separate |
| Truthful evidence (XI) | Local observations and self-reports are hints/assertions | Preserved; labelled `local_observation_hint` and `agent_assertion` |
| Reproducibility, read-only references (XII) | Pinned revision and digests; disposable copies | Preserved; reference checkouts are read with `git archive` only |

No constitutional exception is needed. The constitution remains pending owner ratification.

## Project Structure

### Documentation (this feature)

```text
specs/007-apm-agent-context-and-profiles/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/agent.md
├── checklists/requirements.md
├── tasks.md
└── acceptance.md
```

### Source Code (repository root)

```text
src/score_sw_fabric/agents/
├── __init__.py
├── models.py      # shared limits, glob matching, workspace snapshots, request loading
├── lock.py        # apm_context_lock validation and disposable-copy verification
├── mcp.py         # bounded stdio MCP client
├── discover.py    # capability inventory and explicit setup
├── roles.py       # role profiles, derived runtime agent config
├── context.py     # role context bundle and observation classification
├── admission.py   # catalogue snapshot, model profiles, fallback, budget admission
└── output.py      # agent_result validation and change-set check
profiles/
├── apm-context-29aeaa8-v1.yaml
├── agent-role-developer-draft-v1.yaml
├── agent-role-critic-draft-v1.yaml
└── agent-model-profiles-draft-v1.yaml
schemas/agent-*.schema.json, schemas/apm-context-lock.schema.json
docs/evidence/007/fabro-catalogue/{models-offset-0.json,models-offset-100.json,providers.json}
tests/contract/test_agent_*.py, tests/integration/test_agent_mcp.py, tests/fixtures/agents/
```

**Structure Decision**: A new `agents` package beside `runtime`, reusing assurance/runtime
helpers for exact records, digests and guarded publication. CLI commands are
`score-fabric agent discover|setup|context|admit|check`.

## Complexity Tracking

No constitution violations. The bounded MCP client is the minimum needed to observe the pinned
servers without adopting the upstream unpinned `uvx` launch path.
