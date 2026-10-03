"""Prefer mounted external SSDs for disposable fabric work, with internal fallback."""

from __future__ import annotations

import json
import os
import pwd
import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Fabro workers isolate HOME. Storage registration belongs to the OS account,
# independent of a worker's disposable auth/config home.
ACCOUNT_HOME = Path(pwd.getpwuid(os.getuid()).pw_dir)
CONFIG = ACCOUNT_HOME / ".config/s-core/storage.json"
VOLUMES = ACCOUNT_HOME / ".local/share/s-core/build-volumes"
STATE = ACCOUNT_HOME / ".local/state/s-core/fabro"
NATIVE_FILESYSTEMS = {"ext4", "ext3", "ext2", "xfs", "btrfs", "f2fs"}
MIN_FREE = 20 * 1024**3


@dataclass(frozen=True)
class SSD:
    uuid: str
    device: str
    mount: Path
    filesystem: str


@dataclass
class Selection:
    kind: str
    run_parent: str
    mount: str | None = None
    backing_uuid: str | None = None
    backing_mount: str | None = None
    filesystem: str | None = None
    free_bytes: int = 0
    rejected: list[str] = field(default_factory=list)
    policy: str = "mounted_external_ssd_first"
    schema_version: int = 1
    mount_device: int | None = None


def discover_ssds() -> list[SSD]:
    """Require mounted nonrotating USB/hotplug block devices; never mount raw disks."""
    raw = subprocess.check_output(
        [
            "lsblk",
            "-J",
            "-b",
            "-e",
            "7",
            "-o",
            "NAME,PATH,TYPE,TRAN,ROTA,HOTPLUG,FSTYPE,MOUNTPOINTS,UUID",
        ],
        text=True,
        timeout=10,
    )
    result: list[SSD] = []

    def visit(node: dict[str, Any], external: bool = False, ssd: bool = False) -> None:
        external = external or node.get("tran") == "usb" or node.get("hotplug") is True
        if node.get("type") == "disk":
            ssd = node.get("rota") is False
        if external and ssd and node.get("uuid"):
            for mount in node.get("mountpoints") or []:
                if mount and Path(mount).is_mount():
                    result.append(
                        SSD(
                            str(node["uuid"]),
                            str(node["path"]),
                            Path(mount),
                            str(node.get("fstype") or "unknown"),
                        )
                    )
        for child in node.get("children") or []:
            visit(child, external, ssd)

    for device in json.loads(raw)["blockdevices"]:
        visit(device)
    return sorted(result, key=lambda item: item.uuid)


def probe_posix(directory: Path) -> None:
    """Measure writable permissions, symlinks, hard links and execution, not FS labels."""
    with tempfile.TemporaryDirectory(prefix=".storage-probe-", dir=directory) as name:
        probe = Path(name)
        probe.chmod(0o700)
        unit = probe / "file"
        unit.write_text("#!/bin/sh\nexit 0\n")
        unit.chmod(0o600)
        if unit.stat().st_mode & 0o777 != 0o600 or probe.stat().st_mode & 0o777 != 0o700:
            raise OSError("Storage does not preserve private POSIX permissions")
        (probe / "symlink").symlink_to("file")
        os.link(unit, probe / "hardlink")
        if (probe / "symlink").read_text() != unit.read_text():
            raise OSError("Storage symlink probe failed")
        unit.chmod(0o700)
        subprocess.run([str(unit)], check=True, timeout=5, capture_output=True)


def mounted_source(mount: Path) -> str | None:
    if not mount.is_mount():
        return None
    value = json.loads(
        subprocess.check_output(
            ["findmnt", "-J", "-T", str(mount), "-o", "TARGET,SOURCE,FSTYPE"],
            text=True,
            timeout=5,
        )
    )["filesystems"][0]
    return str(value["source"]) if Path(value["target"]) == mount else None


def kernel_image_mount(image: Path, *, create: bool = False) -> Path:
    """Resolve a registered image through UDisks; never mount a raw SSD device."""

    def devices() -> list[str]:
        rows = json.loads(
            subprocess.check_output(
                ["losetup", "--list", "--json", "--output", "NAME,BACK-FILE"],
                text=True,
                timeout=5,
            )
        )["loopdevices"]
        return [str(row["name"]) for row in rows if row.get("back-file") == str(image)]

    matches = devices()
    if not matches and create:
        subprocess.run(
            ["udisksctl", "loop-setup", "--no-user-interaction", "--file", str(image)],
            check=True,
            timeout=20,
            capture_output=True,
        )
        matches = devices()
    if len(matches) != 1 or not re.fullmatch(r"/dev/loop[0-9]+", matches[0]):
        raise OSError("Registered build image must have exactly one kernel loop mapping")
    device = matches[0]

    def mounts() -> list[dict[str, Any]]:
        result = subprocess.run(
            ["findmnt", "-J", "--source", device, "-o", "TARGET,SOURCE,FSTYPE,FSROOT"],
            text=True,
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 1:
            return []
        result.check_returncode()
        # Native sandboxes add writable binds of subdirectories on the same
        # device. They do not create another mount of the filesystem root.
        return [
            item
            for item in json.loads(result.stdout)["filesystems"]
            if item.get("fsroot", "/") == "/"
        ]

    mounted = mounts()
    if not mounted and create:
        subprocess.run(
            ["udisksctl", "mount", "--no-user-interaction", "--block-device", device],
            check=True,
            timeout=20,
            capture_output=True,
        )
        mounted = mounts()
    if len(mounted) != 1 or mounted[0]["fstype"] not in NATIVE_FILESYSTEMS:
        raise OSError("Registered kernel build image is not mounted on a native filesystem")
    mount = Path(mounted[0]["target"])
    if mounted_source(mount) != device:
        raise OSError("Kernel build image mount identity differs")
    return mount


def bridge_mount(ssd: SSD, settings: dict[str, Any]) -> Path:
    """Mount only a registered existing Linux image, using unprivileged FUSE."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", ssd.uuid):
        raise ValueError("Unsafe external filesystem UUID")
    relative = Path(settings["image_relative"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Linux image must be relative to the registered SSD")
    image = ssd.mount / relative
    if any(p.is_symlink() for p in (image, *image.parents)) or not image.is_file():
        raise OSError("Registered Linux build image is unavailable")
    actual_uuid = subprocess.check_output(
        ["/usr/sbin/blkid", "-p", "-s", "UUID", "-o", "value", str(image)],
        text=True,
        timeout=5,
    ).strip()
    if actual_uuid != settings["image_uuid"]:
        raise OSError("Registered Linux image identity changed")
    backend = settings.get("mount_backend", "fuse2fs")
    if backend == "udisks":
        # Keep admission serialized, including loop creation and desktop auto-mount.
        VOLUMES.mkdir(mode=0o700, parents=True, exist_ok=True)
        with (VOLUMES / (ssd.uuid + ".lock")).open("a") as lock:
            import fcntl

            fcntl.flock(lock, fcntl.LOCK_EX)
            return kernel_image_mount(image, create=True)
    if backend != "fuse2fs":
        raise ValueError("Unknown registered build image mount backend")
    mount = VOLUMES / ssd.uuid
    mount.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (mount.parent / (ssd.uuid + ".lock")).open("a") as lock:
        import fcntl

        fcntl.flock(lock, fcntl.LOCK_EX)
        actual = mounted_source(mount)
        if actual is not None and actual != str(image):
            raise OSError("Build volume mount belongs to another image")
        if actual is None:
            if any(mount.iterdir()):
                raise OSError("Refusing to hide files beneath a new build mount")
            command = Path(settings["fuse2fs"])
            if not command.is_file():
                raise OSError("Registered FUSE helper is unavailable")
            env = dict(os.environ, LD_LIBRARY_PATH=str(settings["library_path"]))
            subprocess.run(
                [str(command), str(image), str(mount), "-o", "rw"],
                env=env,
                check=True,
                timeout=20,
                capture_output=True,
            )
            if mounted_source(mount) != str(image):
                raise OSError("Linux build image did not mount at the registered location")
    return mount


def select_storage(
    *,
    mode: str | None = None,
    devices: list[SSD] | None = None,
    config: Path | None = None,
    internal: Path = Path("/tmp"),
) -> Selection:
    mode = mode or os.environ.get("SCORE_STORAGE_MODE", "auto")
    if mode not in {"auto", "internal"}:
        raise ValueError("SCORE_STORAGE_MODE must be auto or internal")
    rejected: list[str] = []
    if mode == "auto":
        try:
            settings_path = config or CONFIG
            settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
            if not isinstance(settings, dict) or not isinstance(settings.get("volumes", {}), dict):
                raise ValueError("Storage configuration must contain a volumes mapping")
            candidates = discover_ssds() if devices is None else devices
            for ssd in candidates:
                try:
                    if ssd.filesystem in NATIVE_FILESYSTEMS:
                        mount = ssd.mount
                    elif ssd.uuid in settings.get("volumes", {}):
                        mount = bridge_mount(ssd, settings["volumes"][ssd.uuid])
                    else:
                        raise OSError("Filesystem needs a registered Linux build volume")
                    if any(char in str(mount) for char in '\n\r"\\'):
                        raise OSError(
                            "Storage path cannot be represented by the native hook template"
                        )
                    base = mount / ".s-core-build/runs"
                    if any(path.is_symlink() for path in (base, *base.parents)):
                        raise OSError("External build path contains a symbolic ancestor")
                    base.mkdir(mode=0o700, parents=True, exist_ok=True)
                    probe_posix(base)
                    free = shutil.disk_usage(base).free
                    if free < MIN_FREE:
                        raise OSError("External build volume has less than 20 GiB free")
                    return Selection(
                        "external_ssd",
                        str(base),
                        str(mount),
                        ssd.uuid,
                        str(ssd.mount),
                        ssd.filesystem,
                        free,
                        rejected,
                        mount_device=mount.stat().st_dev,
                    )
                except (
                    OSError,
                    ValueError,
                    KeyError,
                    TypeError,
                    subprocess.SubprocessError,
                ) as error:
                    rejected.append(f"{ssd.uuid}: {error}")
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
            rejected.append("External storage discovery: " + str(error))
    internal = internal.resolve(strict=True)
    probe_posix(internal)
    return Selection(
        "internal", str(internal), free_bytes=shutil.disk_usage(internal).free, rejected=rejected
    )


def new_run_root(prefix: str = "score-fabric-") -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", prefix):
        raise ValueError("Unsafe disposable workspace prefix")
    selected = select_storage()
    root = Path(tempfile.mkdtemp(prefix=prefix, dir=selected.run_parent))
    (root / "storage-selection.json").write_text(json.dumps(asdict(selected), indent=2) + "\n")
    return root


def temporary_directory(*, prefix: str = "score-fabric-") -> tempfile.TemporaryDirectory[str]:
    """Use the shared preference for build/analysis scratch, preserving automatic cleanup."""
    selected = select_storage()
    directory = tempfile.TemporaryDirectory(prefix=prefix, dir=selected.run_parent)
    (Path(directory.name) / "storage-selection.json").write_text(
        json.dumps(asdict(selected), indent=2) + "\n"
    )
    return directory


def validate_run_root(root: Path, *, account_home: Path | None = None) -> None:
    """Reject detached or substituted managed volumes; never relocate existing work."""
    root = root.absolute()
    if not root.is_dir() or any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError("Expected a disposable workspace without symbolic ancestors")
    record = root / "storage-selection.json"
    if not record.exists():
        if not root.is_relative_to(Path(tempfile.gettempdir()).resolve()):
            raise ValueError("External workspace lacks storage selection provenance")
        return
    selected = json.loads(record.read_text())
    if root.parent != Path(selected["run_parent"]):
        raise ValueError("Workspace differs from its bound storage selection")
    if selected["kind"] == "external_ssd":
        matches = [ssd for ssd in discover_ssds() if ssd.uuid == selected["backing_uuid"]]
        if len(matches) != 1 or str(matches[0].mount) != selected["backing_mount"]:
            raise OSError("Bound external SSD is disconnected; prepare new work for fallback")
        ssd = matches[0]
        if ssd.filesystem in NATIVE_FILESYSTEMS:
            mount = ssd.mount
        else:
            owner_config = account_home / ".config/s-core/storage.json" if account_home else CONFIG
            owner_volumes = (
                account_home / ".local/share/s-core/build-volumes" if account_home else VOLUMES
            )
            settings = json.loads(owner_config.read_text())["volumes"][ssd.uuid]
            image = ssd.mount / settings["image_relative"]
            if settings.get("mount_backend", "fuse2fs") == "udisks":
                mount = kernel_image_mount(image)
            else:
                mount = owner_volumes / ssd.uuid
                if mounted_source(mount) != str(image):
                    raise OSError("Bound Linux build image is not mounted")
        if (
            not mount.is_mount()
            or str(mount) != selected["mount"]
            or root.parent != mount / ".s-core-build/runs"
            or root.stat().st_dev != mount.stat().st_dev
            or selected.get("mount_device") != mount.stat().st_dev
        ):
            raise OSError("Workspace is no longer on its bound external build volume")
    elif selected["kind"] != "internal" or root.parent != Path("/tmp"):
        raise ValueError("Unknown workspace storage selection")


def disposable_root_allowed(root: Path) -> bool:
    """Extend the reviewed temporary-root boundary only to bound managed workspaces."""
    if (root / "storage-selection.json").exists():
        try:
            validate_run_root(root)
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
            return False
        return True
    temporary = Path(tempfile.gettempdir()).resolve()
    return root != temporary and root.is_relative_to(temporary)


def build_environment(root: Path) -> dict[str, str]:
    """Explicit tool scratch/cache overrides; authentication stays in the caller's home."""
    validate_run_root(root)
    values = {
        "TMPDIR": root / "tool-tmp",
        "UV_CACHE_DIR": root / "cache/uv",
        "XDG_CACHE_HOME": root / "cache",
        "PRE_COMMIT_HOME": root / "cache/pre-commit",
        "BAZELISK_HOME": root / "cache/bazelisk",
        "TEST_TMPDIR": root / "cache/bazel",
        "CARGO_TARGET_DIR": root / "cargo-target",
    }
    for path in values.values():
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    return {key: str(value) for key, value in values.items()}


def private_server_root(root: Path, label: str) -> Path:
    """Keep native state and credentials on the internal, user-private filesystem."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", label):
        raise ValueError("Unsafe server label")
    path = STATE / root.name / label
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.chmod(0o700)
    return path


if __name__ == "__main__":
    print(json.dumps(asdict(select_storage()), indent=2))
