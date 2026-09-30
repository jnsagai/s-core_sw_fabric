# Increment 008 validation guide

**Status:** Validation steps for `score-fabric safety`. Results are recorded in
[acceptance](acceptance.md). No model call, native write or human decision is involved.

## Contract checks

```bash
uv run --frozen pytest -q tests/contract/test_safety_profile.py tests/contract/test_safety_analysis.py \
  tests/contract/test_safety_gates.py tests/contract/test_safety_cli.py
```

## Pinned native catalogue re-derivation

```bash
SCORE_PROCESS_DESCRIPTION_SOURCE=<process_description checkout at 98d1d5f> \
SCORE_MODULE_TEMPLATE_SOURCE=<module_template checkout at c4d4ad0> \
SCORE_DOCS_AS_CODE_SOURCE=<docs-as-code checkout at d5f3de6> \
uv run --frozen pytest -q tests/integration/test_safety_native.py
```

The test reads the checkouts only, checks each profile source digest, and re-derives the fault
model and initiator IDs, metamodel field rules and checklist IDs.

## Fixture demonstrations

`tests/fixtures/safety/telemetry_guard/` holds synthetic native files:

- `v1/`: FMEA with an applicable late-sample fault (`MF_01_02`) and no mitigation (DEMO-02 start).
- `v2/`: added stale-data requirement, changed architecture, FMEA item linked to it with an issue,
  still `sufficient: no` (feedback applied; ready for design review, not accepted).
- The agent-promotion variant (`sufficient: yes`/`status: valid` in an agent-changed file) is
  derived from `v2/` inside the tests.
- `dfa/`: DFA where evaluator and monitor share the time/configuration source (`SI_01_02`),
  with platform initiators omitted (DEMO-03).

## Repository checks

```bash
uv run --frozen ruff check . && uv run --frozen ruff format --check . && uv run --frozen mypy
uv run --frozen pytest -q
uv run --frozen python scripts/check_foundation.py
uv build --offline
```

A `complete` report, a packet or an evaluated gate is not safety acceptance.
