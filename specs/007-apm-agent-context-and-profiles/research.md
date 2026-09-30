# Increment 007 agent context research

**Source baseline:** Read-only inspection of `eclipse-score/mcp-servers`
`29aeaa8251bd006d7ed3b0ea64229ea8589ce826` in `/home/jefferson/mcp-servers` and Fabro
`1b4fb15281ebb724426f9e480dce48d0100ff79b` in `/home/jefferson/fabro`, both clean at their pins.
Probes on 2026-09-30 used a disposable `git archive` copy (`/tmp/score-mcp-007-*`) and a
disposable pinned Fabro server (`/tmp/score-fabro-007-*`, executable
`09d338fbbe107d6c2e41fe9f3b33531c72b54782a2e17dac7c720b89898a68cf`, loopback, dev-token only, no
provider credentials). No model prompt was sent.

## Decision 1 — Launch pinned servers locally, never through the upstream `uvx` references

**Decision:** The lock records each package's local launch module (`apm_setup.serve`,
`context_discipline_mcp`) with its source path in a disposable copy verified file by file. The
upstream manifest launch (`uvx --from git+https://github.com/eclipse-score/mcp-servers#subdirectory=…`)
is recorded as `upstream_launch_unpinned` and never executed.

**Rationale:** The manifest Git references name no revision, so `uvx` would fetch whatever the
default branch holds. Both runnable servers are stdlib-only Python; the fabric's interpreter
(3.12) runs them offline. Lock digests for `apm.yml`, the three package manifests and
`context_discipline_mcp.py` match the 000 lock exactly.

**Evidence:** `packages/{apm-setup,context-discipline,graphify-codegraph}/apm.yml`
`dependencies.mcp[0].args`; `upstream.lock.yaml` `mcp-servers.source_file_sha256`.

**Alternatives considered:** Rewrite the manifest to `git+…@<commit>` and run `uvx` (network,
cache and resolver outside the lock); vendor upstream code (licensing churn, loses provenance).

## Decision 2 — Lock the runtime `tools/list`, not the package `mcp.yml`

**Decision:** Pin each tool by the SHA-256 of the canonical JSON object returned by
`tools/list` (name, description, input and output schema) and classify it as `context_read`,
`local_observation_write` or `setup_privileged`.

**Rationale:** The advertised runtime schemas differ from `mcp.yml` (for example
`initialize_session.assumptions` is `object` in `mcp.yml` but `["array","object","null"]` at
runtime; `mcp.yml` omits `outputSchema`). Descriptions are model instructions, so a changed
description is drift.

**Evidence:** Probe of both servers; `context_discipline_mcp.py` `TOOLS` (line 562 onward) versus
`packages/context-discipline/mcp.yml`.

## Decision 3 — Treat server start as a workspace write and snapshot it

**Decision:** Discovery and setup snapshot the workspace (paths and SHA-256 outside `.git`)
before and after each server session. Observed changes must be within the lock's declared
`startup_writes` or a setup operation's declared writes; anything else blocks.

**Rationale:** `ContextDisciplineMCP.__init__` creates `.score-local/`, `agent-salt` and
`sessions.jsonl` before any tool call (`context_discipline_mcp.py:207-208`).
`setup_context_discipline` creates `.score-local/` and appends `.gitignore`
(`apm_setup/serve.py:105-106`); `setup_graphify` can run `uv tool install` and writes
`graphify-out/` plus `.gitignore` (`serve.py:78,91`).

**Consequences:** Only `setup_context_discipline` is a supported setup operation. The two graph
setup/launch paths stay `unsupported` because `graphify` is absent and installing it needs
network access and a dependency decision.

## Decision 4 — Record the protocol mismatch as unverified runtime compatibility

**Decision:** Both servers answer `initialize` with `protocolVersion: 2024-11-05` whatever the
client requests. The fabric client accepts exactly the locked value. Fabro's agent client uses
`rmcp` with `2025-03-26`; compatibility with an older server response is `not_verified`.

**Evidence:** `apm_setup/serve.py:155`, `context_discipline_mcp.py:831`; Fabro
`docs/public/agents/mcp.mdx:405`.

## Decision 5 — Fail closed where Fabro fails open

**Decision:** A required server's failed handshake or drift blocks dependent roles. A role may
include a server only if every tool that server advertises is granted to it, because Fabro
registers every discovered tool and has no per-tool filter. The derived runtime configuration
always sets `fabro_tools = false`.

**Rationale:** Fabro logs and skips a failed MCP server (`mcp.mdx:328,400`); MCP tools are
auto-approved at `full`, and workflow agents typically run fully auto-approved
(`permissions.mdx:91`). `[run.agent] fabro_tools = true` would expose run create/interact,
including approve/deny (`run-configuration.mdx:492-505`, `mcp.mdx` tool table).

**Consequences:** Granting context-discipline also grants its local-observation write tools, so
the role's write scope must include `.score-local/**`. Those writes remain hints.

## Decision 6 — Validate models against a captured catalogue

**Decision:** Model admission reads the raw `GET /api/v1/models` pages captured from the pinned
disposable server, verifies their digests and pagination, and matches `(provider, id)` exactly.
Aliases are refused with the canonical ID named. A reasoning option is admitted only when the
row's `controls.reasoning_effort` lists it.

**Rationale:** The captured catalogue has 129 unique offerings across 14 providers, none
`configured`. Documentation disagrees with it: `models.mdx` lists `claude-opus-4-8` and
`gpt-5.6-sol` at $5/$30 per Mtok, while the catalogue has `claude-opus-4.8` and `gpt-5.6-sol` at
$4/$20. Of 119 rows with `features.reasoning`, only 28 expose named effort levels; for example
`deepseek-v4-flash` lists `low…max`, whereas the OpenAI and Anthropic rows list none.

**Evidence:** `docs/evidence/007/fabro-catalogue/models-offset-{0,100}.json`
(`d5fd82e4…ce86`, `5409cc1f…6bae`), `providers.json` (`66025cda…7223`).

**Alternatives considered:** `POST /api/v1/models/{id}/test` sends a prompt, so it needs cost
authority and credentials; documentation tables are not the runtime catalogue.

## Decision 7 — Budgets are pre-call ceilings; unknown usage blocks

**Decision:** Admission uses the catalogue input price times the estimated input tokens plus the
output price times the profile's maximum output, rounded up to micro-USD, and the profile timeout
as wall time. Each limited dimension subtracts known prior usage; any prior entry whose usage in
a limited dimension is `null` refuses admission. Calls, retries and correction visits are counted
separately.

**Rationale:** Brief §15.6 requires missing usage to stay unknown. In-flight overshoot is bounded
by using the maximum output rather than an expected value; provider-billed charges that differ
from catalogue estimates are a documented limitation.

## Decision 8 — Local observations are hints with explicit baseline binding

**Decision:** Upstream session records carry no repository revision, so they are `uncertain`
(`BASELINE_UNBOUND`). When `agent check` observes new `.score-local` records appended during a
role action, it binds their IDs to the context bundle's workspace commit. Later context builds
mark bound records `current` at that commit and `stale` otherwise. No state makes a record
evidence.

**Evidence:** `context_sessions.py` record dataclasses (lines 76-150) have `timestamp` and
`session_id` but no revision.

## Decision 9 — Change sets come from snapshots, not agent claims

**Decision:** `agent check` compares the bundle's workspace snapshot with the current tree.
Every changed path must match the role write scope and not `.git/**`; declared and observed
changed paths must be equal apart from lock-declared server writes. Self-reported checks are
kept only as `agent_assertion`.

**Rationale:** Brief §15.2 requires changed paths and says self-reported tests are not
verification evidence.

## Decision 10 — Keep unknown catalogue values unknown

**Decision:** Catalogue rows whose limits are `0` or `null`, or whose price is `null`, are kept
with `null` values. Admission of such an offering refuses with `LIMIT_UNKNOWN` or
`PRICE_UNKNOWN`; the rest of the catalogue stays usable.

**Evidence:** Implementation against the captured pages found `vercel/jev` with
`context_window: 0` and `max_output: null` (offset-0 page, row 83).

## Decision 11 — Snapshot the Git execution surface

**Decision:** Snapshots include `.git/config`, `.git/hooks/**` and `.git/info/**` besides the
work tree. Objects, refs and the index are excluded because ordinary Git reads and commits
change them; `HEAD` is compared as the baseline commit.

**Rationale:** A write tool could otherwise add a hook that runs on the next Git command
without the change check seeing it. Contract tests found this gap during implementation.

## Remaining unknowns

- Whether Fabro's `rmcp` client accepts the `2024-11-05` server response (no model-backed agent
  stage was run).
- Graph-dependent tools (`query_graph` data, `get_prior_context` structural attention,
  `graphify-codegraph`) without `graphify`.
- Provider credential behaviour, billing records and reasoning metadata from a real call.
- Owner approval of role, model and budget profiles.
