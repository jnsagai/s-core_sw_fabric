# SOME/IP reboot recovery observation

Authority: the user requested resuming the SOME/IP queue after Linux crashed.
Observation: 2026-10-02T14:42:39Z. Engineering acceptance remains pending.

## Preserved work and continuation

The original run `01M3XZAQ65TTE35XSGXC4JAMAH` lost its dedicated native database,
credentials and executable when reboot cleared `/tmp`. No checkpoint backup was
found. Its exact stopped Docker container, pinned image and disconnected networking
were checked before exporting the workspace. Six candidate source files and 13
draft reports were retained on the original bound SSD image. Original storage
bindings and native statuses were preserved; changed Linux device numbers were
measured for newly selected workspaces.

The successor `01M3YGTGYFEN406VDEVVTJTRWV` is a fresh supervised run from that
preserved source. It retains DeepSeek Flash/high, no fallback, one complete pass,
all declared obligations and no clock cutoff. It leaves the human gate unanswered.
[Lineage and source hashes](../../../docs/handoff/someip-84/factory/runs/score-someip84-factory-mfwqxi3a/recovery-provenance.json)
and [frozen workflow](../../../docs/handoff/someip-84/factory/runs/score-someip84-factory-mfwqxi3a/workflow.fabro)
record the scope. This is not same-run checkpoint continuation.

## Runtime and infrastructure

Fabro commit `1b4fb15281ebb724426f9e480dce48d0100ff79b` was built with locked
dependencies offline in a disposable source/cache/target copy selected through
fabric storage. Build hooks were inspected. The recorded Petri coding-agent event
capacity overlay was reproduced at 32,768. The reference repository and global
Cargo cache were not modified. The resulting executable SHA-256 is
`8d7ef1e66f19a4da4b806ea64944d58ee33652e959f46c142645c4feb7468fbe`.
It is installed with license, lockfile, overlay and provenance at
`/home/jefferson/.local/share/s-core-tools/fabro-1b4fb152-agent32768/`.

The private dedicated server now uses
`/home/jefferson/.local/state/s-core/fabro/someip84-server/` and port 43916.
Credentials and native state remain internal. Native environment migration was
measured, its original configuration preserved, and the hash binding updated to
the actual migrated configuration. The original DeepSeek credential was imported
into this isolated native store without exporting it to evidence. Dedicated server
restart was exercised, including authenticated access and retained credential state.
Native preflight's required `default` environment was explicitly registered with
the same pinned image and blocked networking as `someip84`.

Missing process/template reference directories formerly under `/tmp` are handled
only through genuine preserved exports whose repository, commit, path, source ID
and bytes match the original frozen source index. Invalid, duplicate, symlinked or
absent source records refuse preparation. Remaining native tool/configuration and
engineering limitations retain their own explicit outcomes.

An initial preflight failure submitted no run. The first submitted replacement,
`01M3YGBHTTM3NCGTMYAN76363M`, failed before engineering agent work because the
new server PATH omitted `/usr/sbin`, hiding `losetup`. That attempt and incident
remain preserved; its observer was stopped and disabled. The resulting isolated
repair proposal was not applied. The server PATH was corrected. The actual frozen
storage guard then passed using the dedicated server's measured environment
before the current replacement was submitted.
[Storage probe](../../../docs/handoff/someip-84/factory/runs/score-someip84-factory-mfwqxi3a/server-storage-probe.json)
retains this check.

## Live observation and checks

Native status was `running`; the exact worker was alive. The owned container
`ecc83520d57bcc718421923e9f1014bfe0b0e9930d672ef4cb7310d94812c52b`
was running the pinned image with no network attachments. The observer's fresh
receipt matched the run, policy, process identity and frozen controls. Both dedicated
server and observer services were enabled and active.
[Restart status](../../../docs/handoff/someip-84/factory/runs/score-someip84-factory-mfwqxi3a/restart-status.json)
is a point-in-time observation, not a completion claim. Another reboot of this
replacement has not been exercised.

Verification passed: frozen sync; Ruff check/format; mypy over 122 source files;
84 focused contracts with one skip before the final PATH correction; all 39 runtime
supervision contracts after it; foundation consistency over 64 requirements and 19
dependency rows; and source/wheel builds using fabric-selected SSD scratch.
Tests cover persistent services, altered runtime/configuration rejection, restricted
server environment and verified preserved-source reuse. Operational fixes do not
establish target readiness, tool qualification, review independence or acceptance.
