# Increment 007 acceptance evidence

**Status:** Implemented for disposable use: 21/22 tasks complete. T022 (owner review of the
context lock and of role, model and budget profiles) is human-owned and open. This record is
fabric development evidence. It is not engineering acceptance, does not select a runtime, and
authorizes no live model call, provider credential, role assignment, publication, merge or
deployment. The 005 T009 production trust root and the 006 T025 same-run resume remain open.

## Fixed identities

| Item | Identity |
| --- | --- |
| S-CORE `mcp-servers` source | `29aeaa8251bd006d7ed3b0ea64229ea8589ce826` (Apache-2.0), read-only checkout `/home/jefferson/mcp-servers`, clean before and after |
| Context lock | `profiles/apm-context-29aeaa8-v1.yaml` `fba91b666d38b10579537cee7baf2fbe197cd70e43616b756130c1ee5dabce4a`; manifest/source digests equal `upstream.lock.yaml` |
| Draft developer role | `profiles/agent-role-developer-draft-v1.yaml` `7d67482a7b1ceae30535a2e39fabd8d51b69085fcaa3a8b204fdb997b276a573` |
| Draft critic role | `profiles/agent-role-critic-draft-v1.yaml` `324fef3e4dfddc1eb9a6efcfc6f2fb7236d3a9cecccc35e11dfcd98797b75c30` |
| Draft model profiles | `profiles/agent-model-profiles-draft-v1.yaml` `9c935e72175a24ebcc1ebc061f5903b102d04b61ffe675bb54f3ceea9640b35a` |
| Fabro candidate for catalogue | `1b4fb15281ebb724426f9e480dce48d0100ff79b`, executable `09d338fbbe107d6c2e41fe9f3b33531c72b54782a2e17dac7c720b89898a68cf` |
| Catalogue pages | `models-offset-0.json` `d5fd82e4b8f000c0a0b3f477e6d67fa252e3cb23c40277f3fd120680e2b9ce86`, `models-offset-100.json` `5409cc1f898f32f989bac306bae423f608f31347fcbf451e721b6f9464756bae`, `providers.json` `66025cdab3ec1332a94706cda107cc3385cd939137583b111c1591ab9c1d7223` |
| Interpreter running the servers | Project `.venv` Python 3.12.14, with `-s -B` and `PYTHONPATH` limited to the verified copy |

## T001 — Probes (2026-09-30)

**MCP servers.** A `git archive` copy of the pinned commit was made under
`/tmp/score-mcp-007-*`; every locked file matched. Both runnable servers answered `initialize`
with `protocolVersion: 2024-11-05` and `serverInfo` `apm-setup 0.1.0` / `context-discipline
0.1.0`. `tools/list` returned 3 and 8 tools; their canonical digests are the lock's
`schema_sha256` values. `verify_setup`, `get_working_memory` (`[]`), `get_unverified_assumptions`
(`[]`) and `query_graph` (setup hint, `"ok": false`, because `graphify` is absent) returned real
results. Starting `context-discipline` created `.score-local/` and `agent-salt` before any tool
call. `setup_context_discipline` appended `.score-local/` to `.gitignore`; a second run changed
nothing. The upstream `uvx` launch references name no revision and were not executed.

**Model catalogue.** A disposable server ran the pinned executable in
`/tmp/score-fabro-007-w2tdG1` (`server start --foreground --no-web --bind 127.0.0.1:43907
--storage-dir <root>/storage --config <root>/settings.toml --max-concurrent-runs 1`, dev-token
auth only, `env -i` with no provider variables). `/proc/3560311/exe` resolved to the pinned
executable and `/proc/3560311/cwd` to the root. The dev token had to match
`fabro_dev_<64 hex>`; a bare hex token was refused at start. `GET /api/v1/models` (two pages of
limit 100) returned 129 unique offerings from 14 providers, all `configured: false`.
`GET /api/v1/providers` returned 14 providers. No `POST /api/v1/models/{id}/test` was sent. The
server was stopped with SIGTERM after capture; the Fabro checkout stayed clean at the pin.

Catalogue observations: documentation IDs and prices differ from the catalogue (for example
`claude-opus-4-8` vs `claude-opus-4.8`; `gpt-5.6-sol` $5/$30 vs $4/$20 per Mtok); only 28 of
119 reasoning-capable rows expose named effort levels; `vercel/jev` reports
`context_window: 0` and `max_output: null`.

## Acceptance criteria

| AC | Evidence | Result |
| --- | --- | --- |
| AC007-01 | `tests/integration/test_agent_mcp.py` (real servers, four real read-tool calls); `test_discovery_records_identity_tools_probe_and_startup_writes` | Met for the pinned copy |
| AC007-02 | `test_discovery_blocks_on_each_drift` (identity, protocol, extra/missing/changed tool, crash, timeout, undeclared write, tool error), file/manifest drift tests, integration drift case | Met |
| AC007-03 | Setup changed then unchanged (fixture and real), undeclared-write and protected-root refusals, `SETUP_FORBIDDEN` for roles | Met |
| AC007-04 | `graphify-codegraph` recorded `unsupported`; runtime-client protocol compatibility `not_verified`; `UPSTREAM_LAUNCH_UNPINNED` findings | Met (explicitly unsupported) |
| AC007-05 | Context tests: commit, sources with revision/digest; `NATIVE_SOURCE_DRIFT`, `NATIVE_SOURCE_UNCOMMITTED` | Met |
| AC007-06 | `test_observations_are_hints_with_current_stale_and_uncertain_states` | Met |
| AC007-07 | Texts omitted unless selected; credential-like text withheld; credential in task refused | Met |
| AC007-08 | `test_role_refusals_name_the_grant` (28 cases) | Met |
| AC007-09 | Output tests: out of scope, `.git/hooks` write, undeclared, declared-not-changed; integration out-of-scope case | Met |
| AC007-10 | Candidate TOML with `fabro_tools = false`, pinned command, no setup server | Met as candidate; not executed by Fabro |
| AC007-11 | Admission capability cases on the captured catalogue | Met |
| AC007-12 | Fallback allowlist, destination, compatibility and price-escalation cases | Met |
| AC007-13 | Budget, unknown-usage, call, retry and visit cases | Met |
| AC007-14 | Malformed-result cases; self-reports kept as `agent_assertion` | Met |

`within_bounds`, `admissible` and `available` are deterministic check outcomes only. No role
output has been reviewed or accepted.

## Repository checks

Run on 2026-09-30 from the repository root:

| Command | Result |
| --- | --- |
| `uv run --frozen ruff check .` | All checks passed |
| `uv run --frozen ruff format --check .` | 304 files already formatted |
| `uv run --frozen mypy` | No issues in 73 source files |
| `uv run --frozen pytest -q tests/contract/test_agent_*.py` | 141 passed (lock 19, discovery 27, roles 32, context 8, output 13, admission 35, CLI 7) |
| `SCORE_MCP_SERVERS_SOURCE=/home/jefferson/mcp-servers uv run --frozen pytest -q tests/integration/test_agent_mcp.py` | 1 passed |
| `SCORE_FABRO_BIN=<disposable>/target/debug/fabro SCORE_MCP_SERVERS_SOURCE=/home/jefferson/mcp-servers uv run --frozen pytest -q` | 1029 passed, 8 skipped (006 runtime ×6, 004 artifact native, 001 native export: selections not configured) |
| `uv run --frozen pytest -q` (no selections) | 3 failed by design (003 native tests require `SCORE_FABRO_BIN`), 9 skipped |
| `uv run --frozen python scripts/check_foundation.py` | PASS |
| `uv build --offline` | wheel `99e58e0f47d89f354577d869a56dc62eaf5218c91be18965ff730a9a8b0dba70`, sdist `9cce27fad054fe70d077655f60d8c726d3cc5a0e1310761c9cc9271212b64ace` (the sdist includes documentation, so later doc edits change its bytes) |

## Defects found and fixed during implementation

- Discovery originally checked startup writes only after probes ran; it now checks after the
  handshake and skips calls on an undeclared write.
- Snapshots originally skipped `.git`, so a hook write was invisible; `.git/config`, hooks and
  info are now recorded.
- The lock originally required only some file under a launch path; it now requires the
  launched module file.
- Catalogue parsing originally rejected rows with unknown limits; they are now kept as unknown.

## Limitations and open authority

- No Fabro agent stage ran with these servers or profiles; Fabro's acceptance of the
  `2024-11-05` server protocol response is unverified.
- No model was called. Credentials, billing records, reasoning metadata and real usage are
  unobserved; admission estimates use catalogue prices and maximum output.
- Graph-dependent context (`graphify`) is unsupported until an owner approves its dependency.
- Fabro registers every tool of a granted server; granting `context-discipline` also grants its
  hint-writing tools, whose output is labelled as hints.
- Role, model and budget profiles are drafts (T022). Constitution ratification, 005 T009 and
  006 T025 remain open.
