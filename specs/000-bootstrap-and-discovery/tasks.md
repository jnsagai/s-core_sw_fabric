# Tasks: Bootstrap and discovery

Status: implementation tasks complete; increment **partial pending owner review**.
Checkboxes denote implementation evidence, not engineering approval. Dependencies are
explicit; every task is tied to US1 or US2 in spec.md. Human decision: only T000-08.

- [x] T000-01 [US1] FAB-001/FAB-002: inspect Git/instructions/tooling and preserve brief/references; files `docs/discovery/upstream-inventory.md`, `reference-workspace.json`; deps none; evidence initial/final Git and brief hash checks in acceptance.
- [x] T000-02 [US1] FAB-004: initialize pinned Spec Kit Codex skills and constitution; files `.agents/skills/`, `.specify/`, `LICENSE.spec-kit`; deps T000-01; evidence init/version/integration manifests and prerequisite checks.
- [x] T000-03 [US1] FAB-003: inspect sources/licenses and resolve declared pins with explicit blockers; files `upstream.lock.yaml`, `toolchain.lock.yaml`, `docs/discovery/*`; deps T000-01; evidence source-file hashes, native/runtime research and PR history.
- [x] T000-04 [US2] FAB-005: define boundaries/ADRs/minimum proposals; files `docs/architecture/*`, `specs/001-native-process-catalog/contracts/*`, `schemas/README.md`, `profiles/foundation.yaml`; deps T000-03; evidence consistency review; no validated runtime contract claimed.
- [x] T000-05 [US1] FAB-001: package offline diagnostic and lightweight CI; files `src/`, `tests/`, `scripts/`, `pyproject.toml`, `uv.lock`, `.github/workflows/foundation.yml`, README/NOTICE/CONTRIBUTING/AGENTS; deps T000-02; evidence lint/type/tests/build and diagnostic results.
- [x] T000-06 [US2] FAB-004/FAB-005: preserve full roadmap/FAB index and prepare bounded next plan/tasks; files `docs/backlog/*`, `specs/000-*`, `specs/001-*`; deps T000-04; evidence 64-ID/19-increment check, clarify/consistency findings.
- [x] T000-07 [US2] FAB-002/FAB-004: reconcile actual results and handoff; files `acceptance.md`, `docs/handoff/000-to-001.md`, `docs/handoff/sol-001-prompt.md`, `docs/handoff/000-files.md`, command logs; deps T000-05/T000-06; evidence final checks/Git/reference comparison. No publish/commit/release actions.
- [ ] T000-08 [US2] FAB-004: owner reviews constitution/ADRs/001 scope; files `checklists/review.md`; deps T000-07; evidence actual owner's review record, not agent assertion. This is the intended handoff, not an external tooling blocker.
