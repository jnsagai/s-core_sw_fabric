# Plan: Account-backed infrastructure recovery

Spec: [spec.md](spec.md). Active increment 010; no new feature activation or branch.

## Technical context

Python >=3.12, standard library, frozen uv environment, pytest/Ruff/mypy.
Linux user systemd services supply observer liveness. Existing pinned Fabro owns
native run lifecycle, API state and Docker sandbox. Codex CLI 0.159.3 uses the normal
ChatGPT login, gpt-6.1-sol, medium; API credentials are removed and login is forced.
JSON receipts and incident records are derived local evidence, not a scheduler/db.

## Constitution check

Pass: authorized repair is scoped to fabric infrastructure. No human decisions,
merging, publishing, reference repository writes or competing execution scheduler.
The model proposes code; fixed deterministic tools validate scope, drift and repair.
Active frozen packages are preserved. Unknown readiness and ambiguous intents block.

## Design

Shared runtime supervision provides classification, private atomic receipts, exact
process identity, file hashes, locking and independently restarted observer admission.
A SOME/IP adapter supplies ownership, preservation, isolated repair, deterministic
verification and fresh native launch. Existing launches freeze observer dependencies
and require a matching ready receipt; host guards enforce heartbeat/process liveness.
A successor gets its own observer before native start. The predecessor retains the
incident and successor ID, and its observer exits normally.

## Verification

Negative-first contract tests; fixture fault/recovery state tests; actual account
repair drill; actual systemd service/ready receipt and native run observation.
Frozen sync, Ruff, mypy, required foundation check and package build.

Reboot maintenance: replace the lost `/tmp` executable/server defaults with an
internally installed, hash-recorded runtime and private persistent server state.
Use persistent enabled systemd user units for the server and observer. Preserve
old policy/storage bindings and admit a new SSD workspace after remount; Linux
device numbers changed and must not be rewritten as if the old binding survived.

Response-overflow maintenance: the pinned server's `/runs/{id}` summary and
`/runs/{id}/questions` list supply the observer's lifecycle/human-gate needs without
stage output or full run projection. Keep the existing 4 MiB bound. Cancellation
reconciliation records both native terminal state and worker absence, waits up to
120 seconds for native settlement and refuses unresolved quiescence. Verify against
the actual oversized predecessor and negative contract tests before freezing a new
observer. Preserve the old frozen observer/package; disable its blocked service.
