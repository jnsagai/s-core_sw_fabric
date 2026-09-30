# Implementation Plan: Bootstrap and discovery

Branch: `000-bootstrap-and-discovery` | Date: 2026-09-27 | [Spec](spec.md)

## Summary

Deliver source-grounded discovery, native Spec Kit artifacts, design proposals and
an installable diagnostic skeleton. Stop before catalogue implementation.

## Technical Context

Python >=3.12; local uv environment 3.12.14, shell Python3.13.13. uv0.12.17;
Hatchling1.32.4; PyYAML6.0.3 for human-editable locks. Ruff/mypy/pytest exact pins
in pyproject/uv.lock. Linux CLI, files only, no database or daemon. Diagnostic does
no network/subprocess execution. Scope is lock envelope visibility, not a full doctor.
Performance target: local checks need no models, analyzers, native build or runtime.

## Constitution Check

Pre-design: preserves all seven governing layers, read-only references and native
artifact authority. Post-design: no target artifact or runtime generated; all future
contracts proposed; tests cannot promote readiness. No exception requested. Foundation
owner review remains pending separately from automated checks.

## Project Structure

`src/score_sw_fabric/{__init__,cli}.py`, `tests/test_foundation_cli.py`,
`scripts/check_foundation.py`, `.github/workflows/foundation.yml`, exact lock files,
`docs/{architecture,discovery,backlog,handoff}`, `specs/000-*` and `specs/001-*`.
Avoid empty implementations for every future module. Schemas directory explains staging.

## Phases and Evidence

1. Preserve baseline and inspect actual references/instructions. Record commits/licenses.
2. Install isolated pinned Spec Kit, init Codex skills, resolve constitution and plan templates.
3. Capture declarations and differences; research native and runtime sources independently.
4. Author ADRs/contracts, roadmap and verbatim FAB mapping. Reconcile ambiguity as explicit
   blocking assumptions for owning increments. No speculative later task expansion.
5. Package minimal offline diagnostic and CI checks. Exercise failure semantics and build.
6. Verify no reference drift, record exact commands/results/files, prepare Sol handoff.

## Complexity Tracking

No new execution platform, schema implementation, orchestration engine or target artifact
store. PyYAML is the single runtime dependency needed to read the selected lock format.
