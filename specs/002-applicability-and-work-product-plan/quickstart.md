# 002 validation guide

Status: implementation complete for bounded draft planning; owner/profile review and the
security-FDR source conflict remain pending. The planner never authenticates human authority and
never reports engineering readiness.

## Supported command

```bash
uv run --frozen score-fabric plan \
  --input PATH/TO/intake.yaml \
  --out PATH/TO/output-root/plan.json \
  --json
```

The intake selects a sealed catalogue, review-draft profile, applicability mapping, artifact
inventory, and decision-reference document by local path and SHA-256. It also selects the
catalogue semantic digest. The output must stay beneath the intake's declared output root and
outside every input/reference tree.

| Exit | Meaning | Output |
| --- | --- | --- |
| 0 | Complete bounded draft | Sealed plan written; readiness remains `not_evaluated` |
| 1 | Valid inputs produced a blocked draft | Sealed plan written with retained candidates/findings |
| 2 | Invalid, corrupt, unavailable, or unsafe input/output | Prior output preserved |

The checked-in `profiles/cpp17-review-draft-v1.yaml` and
`policies/s_core_applicability_v1.yaml` bind the selected 74-work-product catalogue. Their
coverage is deliberately conservative and awaits owner review. The policy retains
`wp__fdr_reports_security` and the conflicting module-template `wp__fdr_reports` reference as
a blocker.

## Validation

Run from the repository root:

```bash
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen mypy
uv run --frozen pytest -q
uv run --frozen python scripts/check_foundation.py
uv build --offline
```

The planning-only suite is:

```bash
uv run --frozen pytest -q \
  tests/contract/test_catalogue_reader.py \
  tests/contract/test_planning_inputs.py \
  tests/contract/test_planning_coverage.py \
  tests/contract/test_planning_conservative_cases.py \
  tests/contract/test_planning_closure_cases.py \
  tests/contract/test_planning_dispositions.py \
  tests/contract/test_planning_routes_and_limits.py \
  tests/contract/test_planning_cli.py \
  tests/integration/test_work_product_plan.py
```

The full source-backed integration case uses `SCORE_FULL_CATALOGUE` when set and otherwise
looks for `/tmp/s-core-001/fresh-catalogue.json`. It skips explicitly if neither is available.
That catalogue must match the digest pinned by the checked-in profile.

Synthetic scenarios are generated under pytest temporary directories from
`tests/planning_support.py`; their independently stated expected sets and fixture-origin notice
are in `tests/fixtures/planning/`. No fixture contains `trusted` or `approved` authority
fields.

## Limits and boundaries

Each input is limited to 64 MiB. Version 1 allows at most 1,000 scopes, 10,000 mapping rules,
100,000 coverage rows, 10,000 retained instances, and 100,000 dependency edges. Coverage and
closure are deterministic under relocation and set-like input reordering. Exceeding an
instance/edge bound produces a blocked partial draft with `CLOSURE_LIMIT`.

A complete draft means only that bounded planning found no unresolved planner condition. Reuse
and tailoring remain unresolved when protected authority is required. External obligations remain
evidence owed. No plan schedules work, edits native artifacts, accepts decisions, or evaluates
release readiness.

See [acceptance](acceptance.md), [planning contract](contracts/planning.md), and the
[002-to-003 handoff](../../docs/handoff/002-to-003.md).
