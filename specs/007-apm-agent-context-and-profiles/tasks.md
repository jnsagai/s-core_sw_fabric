# Tasks: APM agent context and profiles

**Input**: [spec](spec.md), [plan](plan.md), [research](research.md),
[data model](data-model.md), [agent contract](contracts/agent.md), [quickstart](quickstart.md).

**Prerequisites**: 006 demonstrated capability list and runtime schemas only. No dev token,
answer route, `run_resume`, collector or approval credential is available to any task or role.
No paid model call is authorized.

**Tests**: Story-specific contract tests and one real MCP integration test are required by
AC007-01–14. The integration test uses a disposable archive of the pinned `mcp-servers` revision.

**Format**: `[ID] [P?] [Story] Description`.

## Phase 1: Setup

- [X] T001 Record the pinned `mcp-servers` and Fabro catalogue probe identities, raw catalogue pages and observed server behaviour in `docs/evidence/007/` and `specs/007-apm-agent-context-and-profiles/research.md`; keep reference checkouts unchanged (007-R01/R09).
- [X] T002 Create `src/score_sw_fabric/agents/__init__.py` and `tests/fixtures/agents/` with a fixture stdio MCP server (007-R02).
- [X] T003 [P] Add version-1 schemas `schemas/apm-context-lock.schema.json` and `schemas/agent-*.schema.json` for every 007 record and request (007-R13).

## Phase 2: Foundational

- [X] T004 Implement shared request loading, safe globs, workspace snapshots, Git baseline reads and guarded publication in `src/score_sw_fabric/agents/models.py` (007-R13).
- [X] T005 Implement `apm_context_lock` validation and disposable-copy verification in `src/score_sw_fabric/agents/lock.py`; add `profiles/apm-context-29aeaa8-v1.yaml` with observed tool schema digests (007-R01).
- [X] T006 Implement the bounded stdio MCP client in `src/score_sw_fabric/agents/mcp.py` (timeouts, line limit, JSON-RPC errors, minimal environment) (007-R02).
- [X] T007 [P] Add `tests/contract/test_agent_lock.py` for lock fields, file drift, globs and snapshots; client limits are covered in `tests/contract/test_agent_discovery.py` (007-R01/R02/R13).

## Phase 3: User Story 1 — Discover and set up explicitly (P1) 🎯 MVP

- [X] T008 [US1] Implement discovery and setup in `src/score_sw_fabric/agents/discover.py`: identity/protocol/tool comparison, read-only probes, startup-write checks, protected roots, idempotent setup (007-R02/R03).
- [X] T009 [US1] Add `score-fabric agent discover|setup` to `src/score_sw_fabric/cli.py` with 0/1/2 exits (007-R13).
- [X] T010 [P] [US1] Add contract tests for every discovery drift/failure case and setup idempotence/protection in `tests/contract/test_agent_discovery.py` (AC007-01–04).
- [X] T011 [US1] Add the real integration test `tests/integration/test_agent_mcp.py` against a disposable archive of the pinned revision (AC007-01/03).

## Phase 4: User Story 2 — Baseline-bound context (P1)

- [X] T012 [US2] Implement role-profile loading needed by context in `src/score_sw_fabric/agents/roles.py` and the context bundle, observation classification, redaction and role prompt in `src/score_sw_fabric/agents/context.py` (007-R04–R06).
- [X] T013 [P] [US2] Add `tests/contract/test_agent_context.py` for baseline, native source drift/uncommitted, current/stale/uncertain observations and omissions (AC007-05–07).

## Phase 5: User Story 3 — Role permissions and change checks (P1)

- [X] T014 [US3] Complete role refusals and derived runtime agent configuration in `src/score_sw_fabric/agents/roles.py`; add `profiles/agent-role-developer-draft-v1.yaml` and `profiles/agent-role-critic-draft-v1.yaml` (007-R07).
- [X] T015 [US3] Implement result validation and snapshot change-set checks with observation bindings in `src/score_sw_fabric/agents/output.py` (007-R08/R12).
- [X] T016 [P] [US3] Add `tests/contract/test_agent_roles.py` and `tests/contract/test_agent_output.py` for each forbidden grant, scope violation, undeclared/missing change and malformed result (AC007-08–10/14).

## Phase 6: User Story 4 — Capability and budget admission (P1)

- [X] T017 [US4] Implement catalogue snapshot, model profiles, fallback and budget admission in `src/score_sw_fabric/agents/admission.py`; add `profiles/agent-model-profiles-draft-v1.yaml` reviewed against the captured catalogue (007-R09–R11).
- [X] T018 [P] [US4] Add `tests/contract/test_agent_admission.py` for each capability, fallback, budget and unknown-usage case (AC007-11–13).
- [X] T019 [US3/US4] Add `score-fabric agent context|admit|check` and `tests/contract/test_agent_cli.py` for exits, diagnostics and prior-output preservation (007-R13).

## Phase 7: Polish and evidence

- [X] T020 Run Ruff, mypy, full pytest, the real MCP integration test, foundation checker and offline build; record commands, counts, identities and limitations in `specs/007-apm-agent-context-and-profiles/acceptance.md`.
- [X] T021 Update `README.md`, `schemas/README.md`, `docs/backlog/requirements-index.md`, `docs/backlog/roadmap.md` and write `docs/handoff/007-to-008.md` without claiming owner acceptance.
- [ ] T022 Owner review of the context lock, role, model and budget profiles (human-owned; not performed by an agent).

## Dependencies

T001–T003 → T004–T007 → US1 (T008–T011) → US2 (T012–T013) → US3 (T014–T016) → US4
(T017–T018) → T019 → T020–T021. T022 is outside agent authority.
