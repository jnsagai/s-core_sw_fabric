# Implementation Plan: Shared storage preference

Explicit Spec Kit directory: `specs/010-misra-quality-and-deviations/storage-preference`.
This maintenance stays inside active increment 010; parent activation is restored
following this bounded specification workflow.

## Constitution check

Reference sources and historical run scripts stay untouched. No scheduler, model
call, global Docker migration or engineering acceptance is introduced. Fabro owns
run state. Explicit artifact paths and atomic output writes retain their filesystem.

## Design

- `score_sw_fabric.storage` selects mounted USB/hotplug nonrotating devices using
  UUID, real POSIX capability probes and free-space measurement, otherwise `/tmp`.
- Non-Linux backing filesystems require a registered ext4 image with UDisks/kernel
  mounting or rootless fuse2fs; initialization exclusively creates a new image and never formats an
  existing file or device. No automatic formatting occurs during selection.
- Persist selection in each workspace; validate mount, backing UUID and device
  identity before native run creation and existing factory tool reuse.
- Share temporary-directory allocation across native artifacts, workflow validation,
  verification, assurance and quality adapters. Auth homes remain private/internal.
- Expose status, workspace, configure and exec through `score-fabric storage`.
  Explicit command wrapping sets scratch/cache locations without changing HOME.
- Feature-local wrappers delegate to shared code. Future SOME/IP servers use private
  internal state. Existing snapshots are unchanged; no run is restarted here.

## Verification

Frozen sync; Ruff; strict mypy; storage fallback and identity contracts; affected
runtime, validator, quality and verification contracts; real external native compile;
internal allocation probe; foundation check and package build.

## Local deployment

Lexar ES3 UUID `002B-CE31`, mounted `/media/jefferson/Lexar`, uses a 128 GiB
image `.s-core-build/build-volume-v1.ext4`, mounted under
`~/.local/share/s-core/build-volumes/002B-CE31`. Portable fuse2fs 1.46.5 and its
libraries are under `~/.local/share/s-core-tools/fuse2fs-1.46.5`, with package
checksums and copyright notices retained. Configuration is `~/.config/s-core/storage.json`.
The unencrypted image contains public source/build scratch only; private native
server state and credentials stay under `~/.local/state/s-core/fabro`.

## Collector repair and verified kernel backend

Docker extraction into the initial FUSE volume failed on read-only Git objects.
Shared streamed archive extraction now omits runtime Git metadata and timestamps,
preserves source bytes/modes, and rejects unsafe paths, links and special files.
Real coverage retries also exposed repeated FUSE write/connection failures.
Offline read-only filesystem checks found no structural inconsistencies; the
image was retained and mounted through UDisks/kernel ext4 at
`/media/jefferson/11c42dee-73a3-4c2b-ab42-a0440011d9e0`.

The registration chooses `mount_backend: "udisks"`. Exact loop backing-file and
native mount identity are verified; authorization prompts are disabled. Existing
workspace validation does not create a mapping or silently relocate work. New
queues freeze this implementation. The separately authorized queue restart carries
preserved source and reports to a new bound workspace.

Real compiler, focused coverage and process collection completed on kernel storage.
GCC tests passed; Clang failed its compilation; focused production coverage remains
77.8% line / 64.3% branch. Process applicability and human reviews remain pending.
Ruff, mypy, 46 relevant contracts, foundation consistency and `uv build` passed.
