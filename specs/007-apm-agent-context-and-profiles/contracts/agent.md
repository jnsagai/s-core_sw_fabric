# Agent context contract (007)

**Status:** Proposed contract implemented for disposable use. Owner review of the lock, role,
model and budget profiles is pending. No command sends a model prompt, holds a credential or
records an approval.

## Commands

```text
score-fabric agent discover --request <discover.yaml> --out <inventory.json> [--json]
score-fabric agent setup    --request <setup.yaml>    --out <setup.json>     [--json]
score-fabric agent context  --request <context.yaml>  --out <bundle.json>    [--json]
score-fabric agent admit    --request <admit.yaml>    --out <admission.json> [--json]
score-fabric agent check    --request <check.yaml>    --out <check.json>     [--json]
```

Exit codes follow 006: `0` exact result (`available`, `changed`/`unchanged`, bundle built,
`admissible`, `within_bounds`); `1` explicit published non-success (`blocked`, `refused`,
`stopped`); `2` malformed, unsafe or unavailable input with a bounded diagnostic
`{code, pointer, message}` on stderr and any prior output preserved.

## Requests

Every request is YAML with `schema_version: 1` and `kind` naming the command. File inputs are
`{path, sha256}`; relative paths resolve against the request directory; symbolic links, `..`,
and digest mismatches are refused. `protected_roots[]` lists roots the command must not write
(reference checkouts, source repositories); outputs and workspaces inside them are refused.

| Kind | Fields |
| --- | --- |
| `agent_discover_request` | `lock`, `copy_root`, `workspace`, `servers[]`, `probes[]` (`server`, `tool`, `arguments`), `protected_roots[]` |
| `agent_setup_request` | `lock`, `copy_root`, `workspace`, `operation`, `protected_roots[]` |
| `agent_context_request` | `lock`, `inventory`, `role`, `model_profiles`, `workspace`, `task` (`id`, `statement`), `native_sources[]` (`id`, `path`, `sha256`), `assumptions[]`, `observations` (`include_text`, `bindings[]`), `protected_roots[]` |
| `agent_admit_request` | `lock`, `role`, `model_profiles`, `catalogue` (`runtime_commit`, `executable_sha256`, `pages[]`), `ledger`, `call` (`call_id`, `attempt`, `profile`, `estimated_input_tokens`), `protected_roots[]` |
| `agent_check_request` | `lock`, `bundle`, `result`, `protected_roots[]` |

Probe `arguments` may use the literal string `$WORKSPACE`, replaced with the workspace path.
Only `context_read` tools may be probed. The only setup operation is
`context_discipline_store` (`apm-setup` / `setup_context_discipline`).

## Guarantees

- Discovery and setup verify every locked file in `copy_root` before launch, run servers with a
  minimal environment (`PATH`, `PYTHONPATH`, isolated `HOME`) in the workspace, and never use the
  network launch in upstream manifests. `copy_root` and `workspace` must differ from and not
  contain each other or any protected root; the workspace must be a Git work tree.
- Discovery blocks on: missing/changed file or manifest launch record, unexpected server
  name/version/protocol, missing, extra or changed tool, handshake/tool timeout or oversize line,
  JSON-RPC or tool error on a probe, and workspace changes outside declared startup writes. Startup
  writes are checked after the handshake, before any probe runs.
- Workspace snapshots cover every entry outside `.git` plus `.git/config`, `.git/hooks/**` and
  `.git/info/**`, so a hook or configuration write is visible; the commit is compared separately.
- Setup is idempotent: a second run over an unchanged workspace publishes `unchanged`.
- Context refuses: role/lock/inventory mismatch, inventory not `available` for a role server,
  missing/changed/uncommitted native source, forbidden role grants, a credential-like task
  statement and conflicting observation bindings.
- Admission refuses: unknown offering, alias selector, missing tool support, unsupported
  reasoning option, output/context over the offering, unknown offering limit or price (the
  catalogue reports unknown limits as `0` or `null`), a non-fallback call off the role profile,
  incomplete catalogue, unallowlisted,
  incompatible, cross-destination or price-escalating fallback, exhausted budget, and unknown
  prior usage in a limited dimension. `call_authorized` is always `false`.
- Check stops on: malformed result, role/context mismatch, changed baseline commit, change outside
  write scope or under `.git/`, undeclared change, declared change that did not occur.

## Reason codes

Discovery/setup: `LOCK_FILE_DRIFT`, `MANIFEST_LAUNCH_DRIFT`, `SERVER_IDENTITY_MISMATCH`, `PROTOCOL_MISMATCH`,
`TOOL_MISSING`, `TOOL_UNLISTED`, `TOOL_SCHEMA_DRIFT`, `HANDSHAKE_FAILED`, `TOOL_CALL_FAILED`,
`UNDECLARED_WORKSPACE_WRITE`, `SERVER_UNSUPPORTED`, `UPSTREAM_LAUNCH_UNPINNED`
(informational), and input refusals `PROBE_FORBIDDEN`, `SETUP_UNSUPPORTED`, `PROTECTED_ROOT`,
`ROOT_OVERLAP`, `WORKSPACE_NOT_GIT`.
Roles/context: `CREDENTIAL_FORBIDDEN`, `RUN_TOOLS_FORBIDDEN`, `TOOL_FORBIDDEN`, `HUMAN_GATE`,
`SETUP_FORBIDDEN`, `WRITE_SCOPE_MISSING`, `SERVER_WRITES_OUT_OF_SCOPE`, `PROTECTED_PATH`,
`INVENTORY_MISMATCH`, `INVENTORY_NOT_AVAILABLE`, `NATIVE_SOURCE_DRIFT`,
`NATIVE_SOURCE_UNCOMMITTED`, `CREDENTIAL_IN_CONTEXT`, `BINDING_CONFLICT`.
Admission: `CATALOGUE_INCOMPLETE`, `CATALOGUE_MISMATCH`, `MODEL_UNKNOWN`, `MODEL_ALIAS`,
`TOOLS_UNSUPPORTED`, `REASONING_UNSUPPORTED`, `OUTPUT_LIMIT`, `CONTEXT_LIMIT`, `LIMIT_UNKNOWN`,
`PRICE_UNKNOWN`, `PROFILE_NOT_ROLE`, `FALLBACK_NOT_ALLOWLISTED`, `FALLBACK_DESTINATION`,
`FALLBACK_INCOMPATIBLE`, `FALLBACK_PRICE_ESCALATION`, `DESTINATION_NOT_ALLOWED`,
`BUDGET_EXHAUSTED`, `USAGE_UNKNOWN`, `CALL_LIMIT`, `RETRY_LIMIT`, `VISIT_LIMIT`, and input
refusal `LIVE_CALLS_UNAUTHORIZED`.
Check: `RESULT_MALFORMED`, `CONTEXT_MISMATCH`, `BASELINE_CHANGED`, `WRITE_OUT_OF_SCOPE`,
`PROTECTED_PATH`, `UNDECLARED_CHANGE`, `DECLARED_NOT_CHANGED`.

## Derived runtime agent configuration

The context bundle carries candidate Fabro run TOML: `[run.agent] fabro_tools = false` and one
`[run.agent.mcps.<server>]` stdio table per granted server with the pinned interpreter/module
command, `PYTHONPATH` env and lock timeouts. It is `candidate_not_executed`: no Fabro agent
stage ran in 007, and Fabro's acceptance of the servers' `2024-11-05` protocol response is
unverified.
