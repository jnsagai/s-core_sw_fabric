# Feature Specification: Bootstrap and discovery

**Feature Branch**: `000-bootstrap-and-discovery`
**Created**: 2026-09-27
**Status**: Implementation delivered for owner review; increment partial until review.
**Input**: Implementation brief §20.3 plus first-session scope override.

## User Scenarios & Testing

### US1 — Reproduce a grounded baseline (P1)
A maintainer can identify exact inspected sources, their licenses, limitations and
supported development commands without relying on undocumented machine state.
Independent test: install the locked Python package and run documented local checks;
inspect source lock and read-only reference snapshot evidence.

1. Given pre-existing user work and reference checkouts, bootstrap preserves them.
2. Given missing Bazel/Fabro/APM or untested compatibility, records remain explicit
   and no runtime/engineering acceptance is claimed.

### US2 — Review the foundation and hand off 001 (P1)
The owner can review architecture boundaries, requirements and a bounded importer plan.
Independent test: follow every FAB-001–007 mapping and the 000-to-001 handoff.

1. Given all FAB-001–064 requirements, each retains its ID/text and owner in the index.
2. Given a successful package test, target engineering readiness remains not_evaluated.
3. Given the first-session limit, there is no compiler, importer, runtime or paid demo.

## Requirements

FAB-001 independent package; FAB-002 read-only references; FAB-003 recorded compatible
baseline declarations and explicit unresolved verification; FAB-004 native Spec Kit
constitution/spec/plan/tasks; FAB-005 fabric versus target artifact ownership.
Additionally deliver the ten requested architecture topics, minimal contract proposals,
lightweight CI/diagnostic and reviewable command/file handoff. No later implementation.

## Edge Cases

An existing global Specify version must not silently select incompatible templates.
A mutable reference URL, missing tool, failed command or draft source status cannot
be reported as proven compatibility or approval. An empty unstaged diff must disclose
untracked additions. Owner review checkboxes remain unchecked.

## Success Criteria

- SC000-01: All 64 requirement IDs and 19 dependency rows are preserved and checked.
- SC000-02: Pinned Spec Kit Codex assets and installable package pass local checks.
- SC000-03: Every source has exact inspection pin/license or explicit unresolved state.
- SC000-04: References and user brief remain unchanged; all logical changes documented.
- SC000-05: 001 spec/plan/tasks/contracts and copy-ready handoff exist; no 001 code.

## Assumptions and Scope Resolution

Keep the repository's existing Apache-2.0 license. Python >=3.12 matches the native
consumer toolchain while the fabric remains independent. Baseline declaration evidence
is sufficient for 000 discovery; fresh native export validation is required in 001.
Runtime selection is deferred explicitly, not declared compatible. Human foundation
review is requested by the owner and must occur after this session, without fabricated approval.
