# Increment 009 acceptance evidence

**Status:** Implemented for a synthetic local fixture: 17/18 tasks complete. T018, owner review
of the native verification profile, local toolchain profile and substitution, remains open. No
design acceptance, trusted 005 collection, mitigation closure, MISRA compliance, release or model
call is claimed.

## Demonstration

The [sealed records](../../docs/evidence/009/) come from a disposable copy of the C++17 telemetry
guard. `run-defect.json` compiled the off-by-one variant and retained two GoogleTest failures
(`AgeEqualToTimeoutIsValid`, `OutOfOrderSampleKeepsNewest`) with raw bounded build/test output,
digests and requirement/unit/test routes. `run-corrected.json` compiled the corrected source on a
different source digest; all 13 tests passed. `design.json` reports both source units and their
native `req-Id` tags. `milestone.json` retains both runs, resolves the failure history on the
changed source, and imports the 008 v2 FMEA report (`safety-v2.json`). It lists three mitigation
candidates, each with `missing_005_verified_evidence`; the AoU is outside unit-test scope.

The local candidate was GCC 11.4.0, GoogleTest 1.11.0 and gcov 11.4.0, pinned by SHA-256 in
`profiles/cpp17-gcc11-gtest-local-v1.yaml`. `minimal` + `strict` + warnings-as-errors from the
pinned GCC policy compiled without warnings; `all` remains unavailable on GCC 11.4. The corrected
run imported 20/20 executable lines and 11/12 branches in `telemetry_guard.cpp`. These are
counts, with no approved threshold. Source, test, requirement, compiler, library, flags and
coverage selection are bound in the run baseline; each test includes the source, test, toolchain
and full-baseline digests. All records are `local_unprotected_execution` and `not_eligible` for
005 evidence.

## Acceptance scenarios

| Scenario | Evidence | Result |
| --- | --- | --- |
| AC009-01/02 | `test_verification_design.py`: template sections, units/tags, missing section and unknown tag | Met for fixture |
| AC009-03/05 | `test_verification_run.py`: real C++17 compile/test, 13 tests, changed source digest; `test_verification_profile.py`: toolchain mismatch | Met for local candidate |
| AC009-04 | `test_verification_run.py`: missing/unknown metadata and native rule IDs | Met |
| AC009-06 | Corrected run: 20/20 lines, 11/12 branches, no threshold | Met |
| AC009-07/08 | Defect and corrected run in `milestone.json`; retained diagnostics and routes | Met |
| AC009-09/10 | `test_verification_report.py`: same-baseline conflict and three-attempt escalation | Met |
| AC009-11/12/13 | `test_verification_cli.py`: 008 v2 context, missing 005 evidence, pending obligations and inspection answers | Met |
| 009-R10 | `test_verification_cli.py`: 0/2 exits and prior output preservation; defect test covers 1 | Met |

## Checks (2026-09-30)

| Command | Result |
| --- | --- |
| `uv run --frozen pytest -q tests/contract/test_verification_*.py` | 9 passed |
| Pinned-source `tests/integration/test_verification_native.py` with four `SCORE_*_SOURCE` selections | 1 passed; references remained clean |
| Full `pytest -q` with four native selections, MCP selection and installed Fabro | 1105 passed, 8 skipped, 3 failed in 003 native validation because installed Fabro `a192bce` differs from the pinned `1b4fb152` profile; unrelated to 009 |
| `pytest -q --ignore=tests/integration/test_workflow_compiler_native.py` with four native selections and MCP selection | 1105 passed, 8 skipped |
| `uv run --frozen ruff check .` / `ruff format --check .` / `mypy` | Passed; 350 files formatted; 84 source files typed |
| `uv run --frozen python scripts/check_foundation.py` | PASS |
| `uv build --offline` | Built wheel and sdist |

## Limits and review

- The S-CORE Bazel toolchain and native targets were unavailable here; this is a recorded local
  candidate, not selected engineering verification infrastructure. Owner review T018 is open.
- Source tags follow the pinned upstream parser, which can also match a tag embedded in a string
  literal. The structural check cannot establish design adequacy; every inspection answer remains
  `pending_human`.
- The stale-detection requirement is `partially_verified` in the native metadata matrix. The
  milestone outcome describes the passing local test run on its baseline, not completion of an
  approved verification plan or acceptance of every requirement.
- The 008 v2 analysis is `ready_for_design_review`, without an eligible 005 decision. The
  implementation and local tests cannot turn its mitigation candidates into closure evidence.
- MISRA/static analysis, integration, security, protected collection, approved verification plan
  and release remain pending with the owning increments or people listed in `milestone.json`.

**Invariant:** If Fabro disappeared tomorrow, the native source/design/test records and these
sealed local results would remain intelligible; no Fabro state is used as engineering authority.
