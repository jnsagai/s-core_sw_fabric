"""Shared storage must preserve fallback and native target safety boundaries."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric import storage, storage_setup
from score_sw_fabric.cli import main


@pytest.fixture
def disk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> storage.SSD:
    mount = tmp_path / "external"
    mount.mkdir()
    value = storage.SSD("test-uuid", "/dev/test1", mount, "ext4")
    monkeypatch.setattr(storage, "discover_ssds", lambda: [value])
    monkeypatch.setattr(storage, "CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(Path, "is_mount", lambda self: self == mount)
    monkeypatch.setattr(
        storage.shutil, "disk_usage", lambda path: shutil._ntuple_diskusage(100 << 30, 0, 100 << 30)
    )
    return value


def test_external_selected_by_generic_workspace_and_temporary_tools(
    disk: storage.SSD,
) -> None:
    root = storage.new_run_root()
    try:
        assert root.is_relative_to(disk.mount)
        storage.validate_run_root(root)
        assert storage.disposable_root_allowed(root)
        with storage.temporary_directory(prefix="other-feature-") as temporary:
            work = Path(temporary)
            assert work.is_relative_to(disk.mount)
            storage.probe_posix(work)
        assert not work.exists()
    finally:
        shutil.rmtree(root)


@pytest.mark.parametrize(
    "reason", ["missing", "incompatible", "unwritable", "full", "discovery", "alias"]
)
def test_absent_or_unsuitable_external_falls_back(
    reason: str, disk: storage.SSD, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    internal = tmp_path / "internal"
    internal.mkdir()
    if reason == "missing":
        monkeypatch.setattr(storage, "discover_ssds", lambda: [])
    elif reason == "incompatible":
        monkeypatch.setattr(
            storage,
            "discover_ssds",
            lambda: [storage.SSD(disk.uuid, disk.device, disk.mount, "exfat")],
        )
    elif reason == "unwritable":
        original = storage.probe_posix

        def probe(directory: Path) -> None:
            if directory.is_relative_to(disk.mount):
                raise PermissionError("external read-only")
            original(directory)

        monkeypatch.setattr(storage, "probe_posix", probe)
    elif reason == "full":
        monkeypatch.setattr(
            storage.shutil,
            "disk_usage",
            lambda path: shutil._ntuple_diskusage(10 << 30, 0, 10 << 30),
        )
    elif reason == "alias":
        (disk.mount / ".s-core-build").symlink_to(internal, target_is_directory=True)
    else:

        def failed_discovery() -> list[storage.SSD]:
            raise OSError("lsblk unavailable")

        monkeypatch.setattr(storage, "discover_ssds", failed_discovery)
    selected = storage.select_storage(internal=internal)
    assert selected.kind == "internal"
    assert selected.run_parent == str(internal)
    assert bool(selected.rejected) is (reason != "missing")


def test_forced_internal_does_not_discover_or_mount(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unexpected() -> list[storage.SSD]:
        pytest.fail("forced internal mode must not discover devices")

    monkeypatch.setattr(storage, "discover_ssds", unexpected)
    assert storage.select_storage(mode="internal", internal=tmp_path).kind == "internal"


@pytest.mark.parametrize("change", ["unplugged", "device", "parent", "symlink"])
def test_bound_external_workspace_rejects_disconnection_and_substitution(
    change: str, disk: storage.SSD, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = storage.new_run_root()
    try:
        if change == "unplugged":
            monkeypatch.setattr(storage, "discover_ssds", lambda: [])
        elif change in {"device", "parent"}:
            record = root / "storage-selection.json"
            selected = json.loads(record.read_text())
            selected["mount_device" if change == "device" else "run_parent"] = (
                -1 if change == "device" else str(disk.mount)
            )
            record.write_text(json.dumps(selected))
        else:
            alias = disk.mount / "alias"
            alias.symlink_to(root, target_is_directory=True)
            root = alias
        with pytest.raises((OSError, ValueError)):
            storage.validate_run_root(root)
        assert not storage.disposable_root_allowed(root)
    finally:
        if root.is_symlink():
            actual = root.resolve()
            root.unlink()
            shutil.rmtree(actual)
        else:
            shutil.rmtree(root)


def test_private_state_is_internal_and_build_overrides_preserve_home(
    disk: storage.SSD, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(storage, "STATE", tmp_path / "private-state")
    root = storage.new_run_root()
    try:
        private = storage.private_server_root(root, "test-server")
        assert not private.is_relative_to(disk.mount)
        assert private.stat().st_mode & 0o077 == 0
        env = storage.build_environment(root)
        assert "HOME" not in env
        assert all(Path(path).is_relative_to(root) for path in env.values())
    finally:
        shutil.rmtree(root)


def test_occupied_mount_and_unregistered_images_are_never_formatted(
    disk: storage.SSD, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image = disk.mount / "image.ext4"
    image.write_bytes(b"existing bytes")
    volumes = tmp_path / "mounts"
    mount = volumes / disk.uuid
    mount.mkdir(parents=True)
    (mount / "keep").write_text("existing file")
    monkeypatch.setattr(storage, "VOLUMES", volumes)
    monkeypatch.setattr(storage, "mounted_source", lambda path: None)
    monkeypatch.setattr(storage.subprocess, "check_output", lambda *args, **kwargs: "image-uuid\n")

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("must not mount or format over existing files")

    monkeypatch.setattr(storage.subprocess, "run", forbidden)
    with pytest.raises(OSError, match="hide files"):
        storage.bridge_mount(disk, {"image_relative": "image.ext4", "image_uuid": "image-uuid"})
    assert image.read_bytes() == b"existing bytes"
    assert (mount / "keep").read_text() == "existing file"


def test_discovery_uses_external_nonrotating_parent_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def disk(transport: str, rotates: bool, uuid: str) -> dict[str, Any]:
        return {
            "type": "disk",
            "tran": transport,
            "rota": rotates,
            "children": [
                {
                    "uuid": uuid,
                    "path": "/dev/test1",
                    "fstype": "ext4",
                    "mountpoints": [str(tmp_path)],
                }
            ],
        }

    value = {
        "blockdevices": [
            disk("usb", False, "ssd"),
            disk("usb", True, "hdd"),
            disk("nvme", False, "internal"),
        ]
    }
    monkeypatch.setattr(storage.subprocess, "check_output", lambda *a, **k: json.dumps(value))
    monkeypatch.setattr(Path, "is_mount", lambda self: True)
    assert [ssd.uuid for ssd in storage.discover_ssds()] == ["ssd"]


def test_storage_cli_exec_routes_tool_caches_and_returns_native_exit(
    disk: storage.SSD, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[dict[str, Any]] = []
    original = subprocess.run

    def invoke(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if argv == ["test-tool"]:
            calls.append(kwargs)
            return subprocess.CompletedProcess(argv, 7)
        return original(argv, **kwargs)

    monkeypatch.setattr(subprocess, "run", invoke)
    assert main(["storage", "exec", "--", "test-tool"]) == 7
    assert Path(calls[0]["env"]["TMPDIR"]).is_relative_to(disk.mount)
    assert "Fabric workspace:" in capsys.readouterr().err


def test_malformed_configuration_falls_back_with_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "config.json"
    config.write_text("[]")
    selected = storage.select_storage(config=config, internal=tmp_path)
    assert selected.kind == "internal"
    assert selected.rejected
    assert asdict(selected)["policy"] == "mounted_external_ssd_first"


def test_setup_never_formats_an_existing_image(
    disk: storage.SSD, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image = disk.mount / ".s-core-build/build-volume-v1.ext4"
    image.parent.mkdir()
    image.write_bytes(b"existing user file")
    home = tmp_path / "home"
    helper = home / ".local/share/s-core-tools/fuse2fs-1.46.5/usr/bin/fuse2fs"
    helper.parent.mkdir(parents=True)
    helper.touch()
    monkeypatch.setattr(storage_setup, "ACCOUNT_HOME", home)
    monkeypatch.setattr(storage_setup, "CONFIG", tmp_path / "setup-config.json")
    monkeypatch.setattr(
        storage_setup,
        "discover_ssds",
        lambda: [storage.SSD(disk.uuid, disk.device, disk.mount, "exfat")],
    )

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("must not format any existing file or device")

    monkeypatch.setattr(subprocess, "run", forbidden)
    with pytest.raises(FileExistsError):
        storage_setup.configure(disk.uuid, size_gib=32)
    assert image.read_bytes() == b"existing user file"


@pytest.mark.parametrize("substitute", ["other-image", "unmounted", "wrong-source"])
def test_kernel_binding_rejects_substituted_or_missing_image(
    substitute: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image = tmp_path / "registered.ext4"
    image.touch()

    def output(argv: list[str], **kwargs: Any) -> str:
        assert argv[0] == "losetup"
        return json.dumps(
            {
                "loopdevices": [
                    {
                        "name": "/dev/loop9",
                        "back-file": str(image)
                        if substitute != "other-image"
                        else "/other/image.ext4",
                    }
                ]
            }
        )

    def invoke(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert argv[0] == "findmnt", "validation must not create a loop or mount"
        return subprocess.CompletedProcess(
            argv,
            1 if substitute == "unmounted" else 0,
            json.dumps(
                {
                    "filesystems": [
                        {"target": str(tmp_path), "source": "/dev/loop9", "fstype": "ext4"}
                    ]
                }
            ),
            "",
        )

    monkeypatch.setattr(storage.subprocess, "check_output", output)
    monkeypatch.setattr(storage.subprocess, "run", invoke)
    monkeypatch.setattr(storage, "mounted_source", lambda path: "/dev/loop10")
    with pytest.raises(OSError):
        storage.kernel_image_mount(image)
