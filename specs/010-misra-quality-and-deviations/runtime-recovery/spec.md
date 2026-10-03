# Specification: Account-backed infrastructure recovery

Date: 2026-10-02. Bounded maintenance under active increment 010.
Authority: user "do it" after requesting automatic supervisor escalation to Codex;
"be sure to not commit this failure again" requires a mandatory launch gate.
Engineering acceptance remains human-owned.

Reboot recovery authority (2026-10-02): user requests resuming the SOME/IP queue.
The prior dedicated server and runtime executable were in `/tmp` and were lost
on reboot. Preserve its owned container source and reports; rebuild the same
source pin and recorded 32,768-event overlay in bound disposable SSD storage.
Install the executable and keep replacement server state/credentials on internal
persistent storage. Admit one supervised successor with the original Flash/high,
single-pass/no-clock-cutoff policy and explicit predecessor provenance. Missing
native checkpoints cannot be reconstructed or represented as same-run continuation.

Supervisor repair authority (2026-10-02): user "go" after the status identified
full-state response overflow and blocked cancellation recovery. Use the pinned
native compact status and questions endpoints for supervision, preserving bounded
reads and human-gate checks. Reconcile terminal state and exact worker exit before
preservation/application/restart. Preserve the cancelled run's latest source,
reports and incident, then admit one fresh supervised successor with the same scope.

## User stories and requirements

1. A deterministic observer detects native failure, lost worker, broken bound storage
   or unavailable server and requests gpt-6.1-sol/medium through the existing ChatGPT
   Codex login. Ordinary compiler/analyzer findings and unanswered human gates are
   never infrastructure incidents. No OpenAI API credentials or fallback are used.
2. The observer runs as an independently restarted user service. Fabro retains sole
   run/execution authority. Native statuses are observed, never rewritten.
3. Every incident is claimed once. Before repair, preserve source and reports from
   the exact owned, pinned, disconnected Docker workspace. Quiesce only that run.
4. Codex repairs an isolated fabric copy. A deterministic allowlist and compare-and-
   swap protect user work. Host tools verify changes before applying them or starting
   a fresh, supervised Fabro run. Preserve failed attempts, evidence and lineage.
5. Launch must refuse missing, stale, wrong-run, dead or substituted supervision.
   New runs require readiness before native start and before stage/tool admission.
   Existing immutable runs may receive an external observer without editing packages.
6. Supervisor recovery intents survive crashes. Ambiguous submission or repair state
   must be reconciled, never blindly repeated. Unknown/unfixable failures retain a
   visible blocked incident; human review, acceptance and cancellation are respected.

## Acceptance scenarios

Inject missing worker, unavailable collector, native terminal failure, missing receipt,
wrong run ID, stale heartbeat, PID reuse, altered controls, duplicate incident, repair
outside scope, user-file drift, failed verification and uncertain restart. Confirm
human gates and substantive findings do not dispatch a repair. Exercise the actual
account-backed CLI on an isolated reproducible fault, and attach a real service to
the active Fabro run. Fixture tests do not prove a live failure/restart.
