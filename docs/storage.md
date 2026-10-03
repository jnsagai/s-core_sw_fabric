# Fabric storage preference

All features use `score_sw_fabric.storage` for new disposable build, native
validation and analysis workspaces. A mounted, nonrotating USB/hotplug SSD is
preferred when its build volume is writable, supports permissions, links and
execution, and has at least 20 GiB free. Otherwise new work uses internal `/tmp`;
the selection includes rejection reasons. This is recorded in [AGENTS.md](../AGENTS.md).

```bash
uv run --frozen score-fabric storage status
uv run --frozen score-fabric storage workspace
uv run --frozen score-fabric storage exec -- uv build
```

`exec` runs one command in the current working directory with selected `TMPDIR`,
`UV_CACHE_DIR`, `XDG_CACHE_HOME`, `PRE_COMMIT_HOME`, `BAZELISK_HOME`, `TEST_TMPDIR`
and `CARGO_TARGET_DIR`. It preserves HOME and credentials, returns the command's
exit code, and retains the printed workspace for inspection. Bazel profiles that
explicitly set `--output_user_root` must set it inside their disposable workspace.
This command does not modify global Docker data or installed tool locations.
Explicit artifact destinations remain authoritative; atomic staging stays next
to its destination.

Each managed workspace contains `storage-selection.json`. Native runtime target
validation and prepared factory hooks reject a missing or substituted bound SSD.
Active runs are never silently moved. Connecting an SSD affects new allocations;
existing queues, build directories and historical evidence retain their paths.

To intentionally use internal storage for a new allocation:

```bash
SCORE_STORAGE_MODE=internal uv run --frozen score-fabric storage status
```

## Connected Lexar SSD

The Lexar ES3 is mounted at `/media/jefferson/Lexar`, UUID `002B-CE31`, with exFAT.
Because exFAT lacks the Linux file behavior needed by native builds, a new
128 GiB ext4 image was created at:

```text
/media/jefferson/Lexar/.s-core-build/build-volume-v1.ext4
```

The initial rootless FUSE mount was:

```text
/home/jefferson/.local/share/s-core/build-volumes/002B-CE31
```

Real Docker snapshots and coverage collection exposed permission errors and
repeated FUSE failures. The existing image now uses a kernel ext4 mount created
through UDisks, without formatting or changing SSD partitions:

```text
/media/jefferson/11c42dee-73a3-4c2b-ab42-a0440011d9e0
```

The volume registration selects `mount_backend: "udisks"`. Selection resolves
the exact image through its loop backing file and mount identity. UDisks commands
disable interactive authorization; an unavailable backend causes internal fallback.
Validation of existing work never creates or relocates a mount. Kernel loop device
numbers are discovered rather than assumed. Historical FUSE paths remain recorded;
their files are retained in the same image under the kernel mount.

New workspaces are under `.s-core-build/runs` on that volume. Existing SSD files
and partitions were preserved. The image is unencrypted and contains public
source/build scratch; credentials and private Fabro server state remain internal
under `~/.local/state/s-core/fabro`.

Registration is stored in `~/.config/s-core/storage.json`. Selection can remount
this registered image when the SSD is mounted again. It validates the image UUID,
refuses to hide files under an occupied mount point, and never formats storage
during discovery. Setup is explicit and uses exclusive creation, refusing existing
image files:

```bash
uv run --frozen score-fabric storage configure --uuid 002B-CE31 --size-gib 128
```

The initial portable helper was fuse2fs 1.46.5, with libext2fs2 and libfuse2, extracted
from Ubuntu packages under `~/.local/share/s-core-tools/fuse2fs-1.46.5`.
Package checksums, provenance and copyright notices are retained there. No system
packages, disk partitions or global Docker settings were changed. FUSE registrations
remain supported, but the connected Lexar uses the verified kernel backend. Another
host without its registered backend reports it unavailable and falls back internally.

## Verification and specification

The [bounded Spec Kit specification](../specs/010-misra-quality-and-deviations/storage-preference/spec.md)
and its [implementation plan](../specs/010-misra-quality-and-deviations/storage-preference/plan.md)
record this shared maintenance within current increment 010. Verification covers
external preference, absent/unsuitable storage, private state and disconnection.
Real host measurements are in [storage evidence](handoff/storage-verification.json).
These checks do not imply native engineering acceptance.
