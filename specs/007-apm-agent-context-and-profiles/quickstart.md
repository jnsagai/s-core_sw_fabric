# Increment 007 validation guide

**Status:** Validation steps for the implemented `score-fabric agent` commands. Results are
recorded in [acceptance](acceptance.md). No model prompt, provider credential or approval is
used.

## Prerequisites

1. `uv sync --frozen` with Python >=3.12.
2. A read-only checkout of `eclipse-score/mcp-servers` at
   `29aeaa8251bd006d7ed3b0ea64229ea8589ce826`. Never write to it; make a disposable copy:

   ```bash
   COPY=$(mktemp -d /tmp/score-mcp-007-XXXXXX)
   git -C <mcp-servers-checkout> archive 29aeaa8251bd006d7ed3b0ea64229ea8589ce826 | tar -x -C "$COPY"
   ```

3. A disposable Git work tree as the role workspace, outside every reference checkout.

## Contract checks

```bash
uv run --frozen pytest -q tests/contract/test_agent_lock.py tests/contract/test_agent_discovery.py \
  tests/contract/test_agent_roles.py tests/contract/test_agent_context.py \
  tests/contract/test_agent_admission.py tests/contract/test_agent_output.py \
  tests/contract/test_agent_cli.py
```

## Real MCP integration

```bash
SCORE_MCP_SERVERS_SOURCE=<mcp-servers-checkout> \
uv run --frozen pytest -q tests/integration/test_agent_mcp.py
```

The test archives the pinned revision into `tmp_path`, verifies the lock, runs discovery with
real `verify_setup`, `get_working_memory` and `get_unverified_assumptions` calls, runs setup twice,
builds a context, and checks a disposable role change. It confirms the reference checkout is
unchanged.

## Model admission

`profiles/agent-model-profiles-draft-v1.yaml` is reviewed against the raw catalogue pages in
`docs/evidence/007/fabro-catalogue/`. To recapture, start a disposable pinned server as in 006
(`FABRO_DEV_TOKEN` must be `fabro_dev_` plus 64 hex characters; no provider credential in the
environment) and read `GET /api/v1/models?page[limit]=100&page[offset]=N` until
`meta.has_more` is false. Do not call `POST /api/v1/models/{id}/test`; it sends a prompt.

## Repository checks

```bash
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen mypy
uv run --frozen pytest -q
uv run --frozen python scripts/check_foundation.py
uv build --offline
```

A discovery `available`, an `admissible` admission or a `within_bounds` check is not engineering
acceptance and not authority for a live model call.
