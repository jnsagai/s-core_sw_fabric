# 002 design review and handoff

Date: 2026-09-27. Status: specification and Phase 1 design prepared for task generation;
002 implementation and human owner review remain pending. The user's continuation authorizes
this work without claiming that human review or target engineering acceptance occurred.

## Delivered artifacts

[Specification](spec.md): four user stories, 15 requirements linked to FAB-008–FAB-011,
16 acceptance scenarios and six measurable success criteria.
[Plan](plan.md), [research](research.md), [data model](data-model.md),
[contract](contracts/planning.md) and [quickstart](quickstart.md) define the bounded implementation.
[Source review](evidence/source-review.json) records 16 files verified byte-for-byte against
the two pinned commits and the native export's 74 work-product definitions.
[Requirements checklist](checklists/requirements.md) is complete for specification quality;
[owner checklist](checklists/review.md) remains unchecked.

## Findings and resolutions

| Finding | Resolution and acceptance coverage |
| --- | --- |
| No generic native applicability field | Explicit source-cited mapping and all-work-product/scope coverage; gaps remain blocked (AC002-01,07) |
| Security process/template FDR IDs conflict | Preserve wp__fdr_reports_security and conflicting wp__fdr_reports template ref; no rewrite (AC002-07) |
| Native tailoring statement/status could be mistaken for target permission | Keep native evidence and target decision separate; requested/effective dispositions and authority blockers (AC002-08,11,16) |
| Safety tailoring omitted a bound impact-analysis prerequisite | Require exact element-level impact evidence and missing/stale findings (AC002-11) |
| Reuse route could conflate classification, change-request and artifact approval | Separate bound references including Safety Manager classification approval (AC002-09,10) |
| Hashing raw auxiliary files contradicted input permutation invariance | Normalize semantic input digests; transport hashes belong only in validation receipts (AC002-13) |
| Sorting final output did not stabilize limit failures or positional findings | Normalize before evaluation, sorted worklist traversal and identity-based sealed findings (AC002-13,15) |
| Multiple native revisions could collide in stable identity | Exact active revision selection, explicit non-selected revision coverage, ambiguity/conflict blockers (AC002-14) |
| Invalid mapping refs versus missing scope context had ambiguous exits | Invalid declared refs exit 2 and preserve output; unavailable context exits 1 with blocked draft (AC002-04,15) |
| Coverage and instance applicability used inconsistent vocabulary | Coverage selected/outside_scope/unresolved; instance applicability required/unresolved |
| Template requirement could falsely require a template for every work product | Only mapping-declared mandatory templates are required for create |
| 001 lacked persisted-catalogue validation | Plan adds bounded structural/semantic/digest reader before planning (AC002-15) |
| 001 output writer could modify its source inputs | Fixed during prerequisite review; three regression tests pass; recorded in 001 acceptance |

These were agent source/code/design reviews for preparation, not independent engineering
approval. No target classification, profile support, source-conflict adoption or tailoring
was invented to close a design question. Target-specific unknowns have specified blocked outcomes.

## Workflow and verification

No `.specify/extensions.yml` exists; pre/post specify and plan hooks were therefore absent.
The active spec template was resolved through the pinned Spec Kit template stack. The feature
was persisted, and `setup-plan.sh --json` ran with explicit `SPECIFY_FEATURE_DIRECTORY`, returning
the 002 branch/spec/plan paths. `check-prerequisites.sh --json` discovered research, data model,
contracts and quickstart. The planning skill ends after Phase 1; `tasks.md` is not yet created.

The prerequisite code repair passed frozen Ruff lint/format, strict mypy, 38 tests with the live
001 manifest (37 plus one explicit skip without it), and the offline wheel/sdist build. Those
are 001/package results; no 002 planner command or acceptance test has run. The deterministic
foundation checker and final document audit are recorded at completion below.

## Next implementation step

Use the [copy-ready Sol prompt](../../docs/handoff/sol-002-prompt.md) to generate 002 tasks,
run Spec Kit cross-artifact analysis and implement only this increment. The task phase must
map every AC002 scenario to actual work/tests and preserve expected blocked outcomes. Full
score/module_template bundle compatibility and protected authority verification remain outside
the present design result. Stop before 003.


## Completion checks and change inventory

- `uv run --frozen python scripts/check_foundation.py`: passed; 64 unchanged FAB requirements,
  19 dependency rows, locks and local documentation links.
- A direct document audit passed: four stories, 15 requirements, AC002-01–16, six success
  criteria, no unresolved template placeholders, and unchanged unchecked human review markers.
- `git diff --check` and `git diff --stat` were empty. This repository's generated foundation
  and increment files remain untracked, so those commands do not cover their content. The
  document audit, link checker and package checks are the substantive validation here.
- No extension hooks were configured or dispatched. No 002 command has been implemented or run.

New files are the ten artifacts under this feature directory and
`docs/handoff/sol-002-prompt.md`. Spec Kit persists this feature in `.specify/feature.json`.
Existing documentation updated: root README, roadmap, requirement index, the 001-to-002 handoff,
and 001 catalogue contract/acceptance. The prerequisite fix changes
`src/score_sw_fabric/catalog/export.py` and `tests/contract/test_catalogue_cli.py` only.

The active branch is `002-applicability-and-work-product-plan`. No commit, publication,
merge, release, deployment or source-reference modification was performed. The user's original
brief and all pre-existing work were preserved.
