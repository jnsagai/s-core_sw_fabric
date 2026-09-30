# Increment 006 validation guide

**Status:** Partial disposable validation recorded in [acceptance](acceptance.md). The
`score-fabric runtime` commands in the [contract](contracts/runtime.md) are proposed and do not
yet exist. The pinned candidate registered and ran command-only and human-gate fixtures on a
matching disposable server. No production runtime or approval channel is selected.

## Prerequisites and capability gate

1. Use Python >=3.12 and the frozen project environment: `uv sync --frozen`.
2. Keep reference repositories read-only. Use a disposable Fabro installation and disposable
   run storage. Record selected source commit, executable digest, server/API identity and auth
   mode; compare them to the reviewed runtime profile. The inspected candidate commit is
   `1b4fb15281ebb724426f9e480dce48d0100ff79b`, selected only for the disposable probe.
3. Before enabling live tests, demonstrate on the selected release: version registration with
   exact file closure; run create and start; summary, event, timeline and question reads;
   checkpoint resume; cancellation; raw output retrieval; and export. Record each actual
   request, response and expected status in 006 acceptance. A missing operation blocks its test.
4. Use a command-only disposable graph and no paid model provider. Never supply a production
   collector, signer or approval credential to an engineering agent. T009 and other 005
   production-authority prerequisites remain pending.

## Contract and fixture checks to run after implementation

From the repository root, the following are target test commands. Projection, intent and
inspection tests exist and pass; resume and export tests remain to be implemented:

```bash
uv run --frozen pytest -q tests/contract/test_runtime_projection.py
uv run --frozen pytest -q tests/contract/test_runtime_intents.py
uv run --frozen pytest -q tests/contract/test_runtime_inspection.py
uv run --frozen pytest -q tests/contract/test_runtime_resume.py
uv run --frozen pytest -q tests/contract/test_runtime_export.py
```

The positive registration fixture must preserve the original 003 package while projecting
`workflow.fabro` as Fabro's graph entrypoint with exact files and an empty child-workflow map.
Mutate one file, path, symlink, declared reference, wire-size boundary and runtime identity at a
time; each must prevent registration and preserve a prior output. Repeating version registration
must return one native version identity.

Simulate a lost `POST /runs` response after native acceptance. The intent must become
`reconciliation_required` with no automatic second create. A known run ID may be inspected and
started once. A label match alone must not clear ambiguity. Check bounded diagnostics and exact
0/1/2 exits through the proposed public commands after implementation.

## Disposable native journey to execute after capability validation

Use the selected native interface demonstrated in acceptance evidence, not a copied unverified
example. Register a closed command-plus-human-gate package; create and start one run; inspect
ordered events, output bytes, checkpoint and one pending question. Confirm that the run waits,
with zero automatic answers and no 005 human decision inferred from the native question. This
journey may stop at the gate if an authorized external human response channel is not available.

For resume, use a separate disposable command-only checkpoint scenario. Record one effect ID,
resume the same run with unchanged bindings, and count the effect once. Change each selected
source, policy, subject, tool and 005 evidence binding separately; require a blocked continuation
and unchanged historical bytes. A partial-effect or lost-response case must require
reconciliation. Confirm cancellation only after native terminal observation.

Export a completed run and a waiting run; move both exports away from Fabro and verify them
offline. Remove one event page, output byte blob or version file and require an incomplete or
mismatched result, never a reproduced complete record. Confirm that native runtime success and
005 engineering acceptance are separate fields.

## Repository checks

After implementing or changing foundation contracts, run:

```bash
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen mypy
uv run --frozen pytest -q
uv run --frozen python scripts/check_foundation.py
uv build --offline
```

The 006 acceptance record must include actual exit codes, counts, elapsed times, selected native
version/commit/executable digest, package/version/run IDs, output hashes, skipped cases, and
authority limitations. A fixture result or a native successful run is never a production
engineering pass.
