# Files changed and Git comparison

Baseline: `b11332e17aa1ea4b920c24af9d9a20b18fc71ade`; no commits or staging.
Existing tracked LICENSE is unchanged. The original brief was already untracked.
All delivered additions remain untracked for review.

Exact `git diff --stat` output:

```text

```

The empty output describes tracked unstaged changes only. It does not count the additions below.

Exact `git status --short` output:

```text
?? .agents/
?? .github/
?? .gitignore
?? .specify/
?? AGENTS.md
?? CONTRIBUTING.md
?? LICENSE.spec-kit
?? NOTICE
?? README.md
?? S_CORE_SW_FABRIC_SPEC_KIT_IMPLEMENTATION_BRIEF.md
?? docs/
?? profiles/
?? pyproject.toml
?? schemas/
?? scripts/
?? specs/
?? src/
?? tests/
?? toolchain.lock.yaml
?? upstream.lock.yaml
?? uv.lock
```

## Spec Kit (30 files)

Official pinned Codex skills, scripts/templates/manifests; project constitution.

- `.agents/skills/speckit-analyze/SKILL.md`
- `.agents/skills/speckit-checklist/SKILL.md`
- `.agents/skills/speckit-clarify/SKILL.md`
- `.agents/skills/speckit-constitution/SKILL.md`
- `.agents/skills/speckit-converge/SKILL.md`
- `.agents/skills/speckit-implement/SKILL.md`
- `.agents/skills/speckit-plan/SKILL.md`
- `.agents/skills/speckit-specify/SKILL.md`
- `.agents/skills/speckit-tasks/SKILL.md`
- `.agents/skills/speckit-taskstoissues/SKILL.md`
- `.specify/.gitignore`
- `.specify/init-options.json`
- `.specify/integration.json`
- `.specify/integrations/codex.manifest.json`
- `.specify/integrations/speckit.manifest.json`
- `.specify/memory/.constitution-template.json`
- `.specify/memory/constitution.md`
- `.specify/scripts/bash/check-prerequisites.sh`
- `.specify/scripts/bash/common.sh`
- `.specify/scripts/bash/create-new-feature.sh`
- `.specify/scripts/bash/resolve-template.sh`
- `.specify/scripts/bash/setup-plan.sh`
- `.specify/scripts/bash/setup-tasks.sh`
- `.specify/templates/checklist-template.md`
- `.specify/templates/constitution-template.md`
- `.specify/templates/plan-template.md`
- `.specify/templates/spec-template.md`
- `.specify/templates/tasks-template.md`
- `.specify/workflows/speckit/workflow.yml`
- `.specify/workflows/workflow-registry.json`

## Package, tooling and CI (8 files)

Installable foundation diagnostic, fail-closed envelope tests and reproducible checks.

- `.github/workflows/foundation.yml`
- `.gitignore`
- `pyproject.toml`
- `scripts/check_foundation.py`
- `src/score_sw_fabric/__init__.py`
- `src/score_sw_fabric/cli.py`
- `tests/test_foundation_cli.py`
- `uv.lock`

## Design, discovery and baseline locks (24 files)

Source-grounded boundaries, provenance, capabilities, alternatives and explicit future blockers.

- `docs/architecture/0001-workspace-and-authority-boundaries.md`
- `docs/architecture/0002-structured-native-import-and-baseline.md`
- `docs/architecture/0003-types-catalogue-entities-and-scoped-instances.md`
- `docs/architecture/0004-applicability-and-supported-profiles.md`
- `docs/architecture/0005-derived-execution-representation-and-deterministic-compiler.md`
- `docs/architecture/0006-native-artifact-ownership-and-traceability.md`
- `docs/architecture/0007-trusted-evidence-and-authenticated-human-decisions.md`
- `docs/architecture/0008-safety-design-acceptance-versus-implemented-closure.md`
- `docs/architecture/0009-verification-and-misra-integration.md`
- `docs/architecture/0010-apm-and-mcp-integration-boundary.md`
- `docs/architecture/0011-providers-budgets-and-unattended-operation.md`
- `docs/architecture/0012-baseline-hashes-impact-and-invalidation.md`
- `docs/architecture/0013-scoped-readiness-portable-evidence-and-upstream-boundary.md`
- `docs/architecture/README.md`
- `docs/discovery/capability-matrix.md`
- `docs/discovery/native-source-review.md`
- `docs/discovery/reference-workspace.json`
- `docs/discovery/runtime-source-review.md`
- `docs/discovery/upstream-inventory.md`
- `docs/discovery/upstream-prs.json`
- `profiles/foundation.yaml`
- `schemas/README.md`
- `toolchain.lock.yaml`
- `upstream.lock.yaml`

## Backlog and bounded specifications (21 files)

Preserve the complete requirements/roadmap while elaborating only 000 and 001.

- `docs/backlog/requirements-index.md`
- `docs/backlog/roadmap.md`
- `specs/000-bootstrap-and-discovery/acceptance.md`
- `specs/000-bootstrap-and-discovery/checklists/review.md`
- `specs/000-bootstrap-and-discovery/contracts/cli.md`
- `specs/000-bootstrap-and-discovery/data-model.md`
- `specs/000-bootstrap-and-discovery/plan.md`
- `specs/000-bootstrap-and-discovery/quickstart.md`
- `specs/000-bootstrap-and-discovery/research.md`
- `specs/000-bootstrap-and-discovery/spec.md`
- `specs/000-bootstrap-and-discovery/tasks.md`
- `specs/001-native-process-catalog/checklists/review.md`
- `specs/001-native-process-catalog/contracts/README.md`
- `specs/001-native-process-catalog/contracts/catalogue.md`
- `specs/001-native-process-catalog/contracts/forward-boundaries.md`
- `specs/001-native-process-catalog/data-model.md`
- `specs/001-native-process-catalog/plan.md`
- `specs/001-native-process-catalog/quickstart.md`
- `specs/001-native-process-catalog/research.md`
- `specs/001-native-process-catalog/spec.md`
- `specs/001-native-process-catalog/tasks.md`

## Handoff and acceptance evidence (7 files)

Actual command/check/source results, owner review handoff and Sol prompt.

- `docs/evidence/000/commands.md`
- `docs/evidence/000/references.json`
- `docs/evidence/000/tool-invocations.jsonl`
- `docs/evidence/000/verification.txt`
- `docs/handoff/000-files.md`
- `docs/handoff/000-to-001.md`
- `docs/handoff/sol-001-prompt.md`

## Project guidance and attribution (5 files)

Setup, contribution boundaries and retained third-party MIT notice.

- `AGENTS.md`
- `CONTRIBUTING.md`
- `LICENSE.spec-kit`
- `NOTICE`
- `README.md`

## Preserved input

- `S_CORE_SW_FABRIC_SPEC_KIT_IMPLEMENTATION_BRIEF.md` — pre-existing user input; not created or edited by this session.
- Final SHA-256: `1021991cd1c45dcd4641f34be3f883493d7a85006ff477a2b5093d0f37864382`.

Ignored generated/local outputs: `.venv/`, tool caches, `dist/`, and `.specify/feature.json`
(machine-local active feature pointer). No reference source or LICENSE edits.
