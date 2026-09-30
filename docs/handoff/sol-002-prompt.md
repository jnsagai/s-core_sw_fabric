# Copy-ready implementation prompt: increment 002

Recommended starting model: `gpt-6-sol`, reasoning effort `xhigh`, for careful implementation
and verification against the now-explicit contracts. Select it in the client; this document
does not switch the session model.

~~~text
Implement increment 002, applicability and work-product planning, in s-core_sw_fabric.
This prompt authorizes fabric implementation through 002; do not implement 003 or later.

Read AGENTS.md, the constitution, specs/002-applicability-and-work-product-plan/{spec.md,
plan.md,research.md,data-model.md,contracts/planning.md,quickstart.md,design-review.md},
001 acceptance, the requirement index and source locks. Preserve existing untracked work.

Use the Spec Kit tasks skill to generate dependency-ordered tasks for 002, then the analyze
skill to check spec/plan/tasks consistency. Correct critical findings before using implement.
Human-owned review markers stay unchanged; continuation authorizes development, not native
engineering acceptance, classification approval or constitution ratification.

Implement the validated catalogue consumer before the planner. Reuse bounded parsers and
canonical encoding. Account for every native work-product/scope pair; no default exclusion,
latest-revision guessing, raw relation scheduling or inventory-driven obligation discovery.
Preserve source-qualified IDs, native revisions/statuses, stable instance identity, review
purposes, exact bindings, source conflicts, role requirements and licensing.

Production 002 has no protected decision verifier. Reuse/tailoring requests remain visible
with effective unresolved when authority is absent. Include bound tailoring impact analysis,
classification approval and accepted change-request refs as distinct prerequisites. No fake
approval flag, fixture trust switch, paid call or target artifact writer is allowed.

Use normalized semantic digests in sealed plans, transport hashes in validation receipts,
stable diagnostic locations and sorted bounded closure traversal. Input errors preserve old
output; blocked draft generation returns the documented nonzero status. Protect every supplied
input, hardlink alias and source/reference root. The 001 source-write defect was already fixed;
preserve its three regressions.

Derive source-backed planning fixtures from the pinned 74-work-product native catalogue.
Test all AC002-01–16, including expected blocked outcomes, independent input permutations,
multiple native revisions, missing mappings, scope fan-out, stale reuse and source conflict.
Never treat passing tests or generated plans as engineering acceptance. Keep readiness
not_evaluated. Do not rebuild large native consumers unless changed pins require it.

Reconcile tasks with actual results, write 002 acceptance evidence and handoff, update status
and requirement links, and run frozen lint/format/mypy/pytest, foundation checks, CLI scenarios
and offline package build. Report limitations, then stop before 003. End with the next concrete
step and an exact recommended model/reasoning effort with a task-specific reason.
~~~
