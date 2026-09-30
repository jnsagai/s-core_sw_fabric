# Increment 007 data model

All records are version 1, reject unknown or missing fields and duplicate keys, bound strings,
arrays and bytes, and are published atomically outside inputs and protected roots. Sealed
outputs carry `digest` = SHA-256 of canonical JSON without `digest`, and
`engineering_readiness: not_evaluated`. Paths inside records are workspace-relative POSIX paths
without `..`, empty segments or a leading `/`.

## Context package lock (`apm_context_lock`, YAML profile)

| Field | Meaning |
| --- | --- |
| `id`, `status` | Stable lock ID; `draft_owner_review_pending` until reviewed |
| `source` | `repository`, full `commit`, `license`, `license_path`, `notice_path` |
| `files[]` | Every file the fabric reads or launches from the copy, with SHA-256 |
| `servers[]` | `id`, `package`, `manifest`, `status` (`supported`/`unsupported`), `unsupported_reason`, `upstream_launch` (manifest `command`/`args`, never executed), `launch` (`kind: python_module`, `python_path[]`, `module`, or `null`), `expected` (`server_name`, `server_version`, `protocol_version`), `startup_writes[]` globs, `tools[]` (`name`, `classification`, `schema_sha256`) |
| `setup_operations[]` | `id`, `server`, `tool`, `declared_writes[]`; arguments are fixed to `{repo_path: <workspace>}` |
| `runtime_client` | Fabro client `protocol_version` and `compatibility` (`not_verified`) |
| `limits` | `handshake_seconds`, `tool_seconds`, `line_bytes`, `result_bytes` |

Tool classifications: `context_read` (may be invoked by discovery), `local_observation_write`
(writes hint storage), `setup_privileged` (setup command only; never granted to a role).

## Capability inventory (`agent_capability_inventory`)

Lock identity, source commit, interpreter path/version, workspace commit, per-server `status`
(`available`, `blocked`, `unsupported`), observed identity/protocol/tool digests, findings
(`code`, `detail`), workspace changes during the session, probe results (`server`, `tool`,
`arguments_sha256`, `outcome`, bounded `result_text`, `result_sha256`, origin
`mcp_tool_result`), upstream findings (`UPSTREAM_LAUNCH_UNPINNED`), runtime-client
compatibility, overall `outcome` and limitations.

## Setup record (`agent_setup_record`)

Operation, workspace path/commit, before/after snapshot digests, `changes[]` (`path`, `change`
= `added|modified|removed`), `undeclared[]`, tool result text/digest, `outcome`
(`changed|unchanged|blocked`) and `idempotent` (true when no change was needed).

## Role profile (`agent_role_profile`, YAML)

`id`, `status`, `role` (brief §15.1 role name), `purpose`, `allowed_inputs[]` globs,
`expected_output` (`kind: agent_result`, `schema_version: 1`), `write_scope[]` globs,
`builtin_tools[]`, `mcp_servers[]`, `data_destinations[]`, `prohibited_decisions[]`,
`completion_criteria[]`, `uncertainties_to_report[]`, `loopback.max_correction_visits`,
`retry_limit`, `model_profile`, `budget` (`cost_microusd`, `input_tokens`, `output_tokens`,
`wall_seconds`, `calls`), `credentials[]` (must be empty), `runtime` (`fabro_tools: false`,
`human_gate: stop`, `permissions`).

Refusals: any credential; `fabro_tools: true` or a `fabro*` server/tool; `shell`, web or
sub-agent tools; a granted server exposing a `setup_privileged` tool; a server whose startup
writes or write tools fall outside the write scope; write tools without a write scope; a
write scope or input under `.git/**`.

## Role context bundle (`agent_context_bundle`)

Role identity and instructions, task, workspace (`path`, `commit`, `dirty_paths`, snapshot of
`path/kind/size/sha256` for every entry outside `.git` plus `.git/config`, `.git/hooks/**`,
`.git/info/**`, with digest), native sources (`id`, `path`, `sha256`, `revision`), granted
tools with schema digests, unresolved assumptions, observation index (`record_ids`, log
digests), observations (`id`, `record_type`, `session_id`, `timestamp`, optional bounded
`text`, `origin: local_observation_hint`, `baseline`, `state` = `current|stale|uncertain`,
`reason`), omissions, derived runtime agent config (`status: candidate_not_executed`), model
profile ID, rendered role prompt with digest.

## Model profiles (`agent_model_profiles`, YAML) and catalogue snapshot

`id`, `status`, `live_calls: disabled`, `catalogue` (`runtime_commit`, `pages_sha256[]`), and
`profiles[]`: `id`, `provider`, `model`, `reasoning_effort` (or `null`), `requires_tools`,
`max_output_tokens`, `max_context_tokens`, `timeout_seconds`, `data_destination`,
`fallbacks[]` (`profile`, `allow_higher_price`). The catalogue snapshot is derived from raw
`GET /api/v1/models` pages: unique `(provider, id)`, aliases, limits, features, controls,
costs, `configured`, and the last page's `has_more: false`. Limits reported as `0`/`null` and
missing prices are kept as unknown (`null`) and refuse admission only for a selected offering.

## Budget ledger (`agent_budget_ledger`) and admission (`agent_admission`)

Ledger entries: `call_id`, `attempt` (`initial|retry|correction_visit|fallback`), `profile`,
`usage_origin` (`runtime_observation|unknown`), and `input_tokens`, `output_tokens`,
`cost_microusd`, `wall_seconds` (integers, or all `null` when unknown).

Admission: role, call, selected offering, conservative estimate, known usage, remaining limits,
`decision` (`admissible|refused`), reasons, `call_authorized: false`, `provider_configured`.

## Role result (`agent_result`) and check (`agent_output_check`)

Result: `role_id`, `context_digest`, `changed_paths[]`, `native_ids_affected[]`,
`evidence_refs[]` (`kind`, `ref`), `unresolved_assumptions[]`, `proposed_next_action`,
`self_reported_checks[]` (`name`, `result` = `pass|fail|unknown`).

Check: bundle and result identities, `structure` (`valid|malformed`), observed changes,
violations (`code`, `path`), `outcome` (`within_bounds|stopped`), self-reported checks with
`origin: agent_assertion`, evidence references with `verification: not_verified`, observation
bindings (`record_id`, `baseline_commit`).

## State rules

- Inventory `available` requires every selected supported server to match the lock exactly.
- A context requires an `available` inventory for every role server, from the same lock bytes.
- Admission never authorizes a call (`call_authorized: false`) in 007.
- `within_bounds` means only that deterministic scope/structure checks passed; review remains
  required and self-reports stay assertions.
