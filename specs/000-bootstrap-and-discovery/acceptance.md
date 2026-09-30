# Increment 000 acceptance evidence

Date: 2026-09-27. **Partial: implementation delivered, owner review pending.**
T000-01–07 complete; T000-08 unchecked. No native/engineering acceptance claimed.

| Requirement / task | Actual evidence | Result |
| --- | --- | --- |
| FAB-001 / T000-01,05 | Independent branch/package; wheel+sdist, CLI checks | pass for foundation |
| FAB-002 / T000-01,07 | Clean initial/final statuses for 12 selected sources; pinned source-file hashes; original LICENSE unchanged | pass |
| FAB-003 / T000-03 | Exact source/tool pins/licenses; declared compatibility and unresolved cases recorded | discovery complete; native/runtime validation pending |
| FAB-004 / T000-02,06,07 | Spec Kit init1.0.12/Codex manifests; constitution; 000+001 spec/plan/tasks; 64 IDs/19 increments | pass for artifacts; owner review pending |
| FAB-005 / T000-04,06 | ADR boundaries; diagnostic always not_evaluated for engineering readiness; no target artifacts/runtime | pass for foundation |

## Final local checks

Exact argv, output and individual exit status: [verification.txt](../../docs/evidence/000/verification.txt).
The final run includes frozen sync, Ruff lint/format, mypy, eight pytest cases, foundation
consistency, CLI help/version/doctor, both Spec Kit prerequisite checks, wheel/sdist build
and Git whitespace check. Actual result: **15/15 commands passed; 8 tests passed, 0 failed, 0 skipped**.
Built wheel was also installed and smoke-tested in an isolated environment. Use the
actual log as authority if rerunning changes results. Hosted CI has not run.

Reference/source checks and final hashes: [references.json](../../docs/evidence/000/references.json).
The optional X-Verse checkout gained external changes; no session write targeted it.
All selected source pins and files were compared with discovery snapshots; no reference builds
were run. Original LICENSE checked against HEAD. User brief SHA-256 recorded for handoff;
no command wrote the brief. Original sandbox failed before execution; subsequent escalated
commands ran with reviewer authorization.

## Failures found and fixed

- Initial ordinary shell calls failed before execution: bubblewrap mountinfo path error.
- First editable package build failed because README was not yet written. Added required
  metadata and repeated synchronization/build successfully.
- First scripts/check_foundation.py write failed because scripts/ did not exist. Created
  directory and wrote checker; initial lint/format findings then corrected.
- First pytest run failed during unrelated ROS launch_testing plugin auto-discovery
  (host PYTHONPATH; missing lark). Added supported pytest --disable-plugin-autoload to
  project configuration. Actual project tests then ran; no test was hidden or skipped.
- Invalid boolean schema_version originally compared equal to integer1 in Python; fixed
  exact type check and added negative case. Final suite has eight cases.
- Exploratory nonexistent paths (e.g. score/pyproject.toml, docs/BUILD, old template dirs,
  Fabro LICENSE instead of LICENSE.md) were replaced with discovered real paths. Missing
  metamodel-flow package is a real selected-baseline limitation, not a corrected path.

## Not run / pending

Native Sphinx/Bazel documentation build, source catalogue import, Fabro validation/run/
resume, MCP handshake, target C++ build, analyzer, provider calls and portable evidence
verification: **not run**, outside delivered implementation or missing prerequisites.
Live model calls/cost from demonstrators: **0 / 0**. Neither fixtures nor simulations
were substituted for those checks. No target readiness outcome beyond not_evaluated.

## Clarification and consistency review

Source-backed decisions and alternatives are recorded in research/ADRs. User scope
controls stopping after 000 preparation. FAB index preserves all text/owners; no later
implementation tasks checked. Source refs/types/instances/evidence/gates have proposed
contracts; no implemented schema claim. Native consumer declarations are not marked
build-verified; Fabro stable/nightly difference is explicit; human review remains pending.
The consistency check is local deterministic/reviewer preparation, not independent
engineering approval or an assertion that every installed Spec Kit chat skill was run.

Full [handoff](../../docs/handoff/000-to-001.md), [changed files](../../docs/handoff/000-files.md)
and [command record](../../docs/evidence/000/commands.md). Comparison baseline is initial
HEAD b11332e17aa1ea4b920c24af9d9a20b18fc71ade; no commits/staging were performed.
