# SOME/IP supervisor response-overflow recovery

Authority: user "go" after the failed supervisor/recovery status.
Observed 2026-10-02T16:54:40Z. Engineering acceptance remains pending.

The predecessor `01M3YGTGYFEN406VDEVVTJTRWV` completed 40 workflow stages before
its full `/state` response exceeded the observer's 4 MiB bound. The derived
infrastructure incident requested native cancellation. Recovery's 30-second worker
wait expired before worker shutdown settled; it refused application/restart. Its
isolated diagnostic proposal changed no files and was not applied.

The original native status remains `failed` with reason `cancelled`. Its worker
exited and its exact retained Docker container was stopped. Ownership, pinned image
and disconnected networking were verified before an SSD-bound workspace snapshot.
All six latest allowed candidate source files, 12 current reports and 13 older reports
are preserved. No native state was rewritten. The blocked observer service was
disabled; its frozen package, incident and recovery records remain preserved.

## Repair and measured verification

The observer now reads native `/runs/{id}` summary and `/runs/{id}/questions`,
which the pinned Fabro server handler explicitly provides. It no longer downloads
stage output or the full projection for supervision. The existing 4 MiB read bound
remains intact, and invalid pending-question responses block observation. Human
questions still suppress infrastructure repair. Native `failed/cancelled` status
is treated as cancellation rather than a new failure to recover automatically.

On the actual predecessor the summary was **1,820 bytes**, questions **37 bytes**,
and full state **4,592,494 bytes**. The corrected observer ran against that genuine
oversized predecessor, recognized its terminal cancellation and exited normally
without creating another incident. This exercises the actual endpoints beyond
fixture contracts.

Cancellation reconciliation now records both native terminal state and exact worker
absence. A settled previous cancellation returns without another control request.
Otherwise it waits up to 120 seconds for native settlement and worker exit; unresolved
state or a live worker still refuses source application/restart. Contracts cover both
negative cases and worker exit after 35 seconds. The actual predecessor passed this
reconciliation without a duplicate cancellation.

Ruff check/format, mypy over 122 source files, frozen sync, 91 focused contracts
with one skip, foundation consistency and source/wheel builds passed. Contract scope
includes runtime supervision, storage, workspace transfer, SOME/IP collectors and
handoff. Build scratch used fabric-selected SSD storage. Source preservation hashes
and the frozen storage guard using the actual dedicated server environment passed
before native submission.

## Successor observation

Run `01M3YRJEGXNY6CB81T7TKW774B` is a fresh supervised successor from the latest
preserved source, with DeepSeek Flash/high, no fallback, all declared obligations,
one complete pass and no clock cutoff. The native worker was alive, events current,
container running the exact pinned image with no network attachments, supervisor
receipt fresh and dependencies verified. Server and observer services were enabled
and active. There were no pending human questions at observation time.

[Live evidence](../../../docs/handoff/someip-84/factory/runs/score-someip84-factory-2fekt_ew/restart-status.json),
[lineage](../../../docs/handoff/someip-84/factory/runs/score-someip84-factory-2fekt_ew/recovery-provenance.json),
[preservation](../../../docs/handoff/someip-84/factory/runs/score-someip84-factory-2fekt_ew/preservation.json),
[oversized predecessor measurement](../../../docs/handoff/someip-84/factory/runs/score-someip84-factory-2fekt_ew/predecessor-observation.json),
[actual observer check](../../../docs/handoff/someip-84/factory/runs/score-someip84-factory-2fekt_ew/live-observer-check.json)
and [verification](../../../docs/handoff/someip-84/factory/runs/score-someip84-factory-2fekt_ew/verification.json)
retain the result. Native collector-stage completion does not establish passing
engineering checks; their findings and pending human acceptance remain explicit.
