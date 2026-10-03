"""Register a Linux build image on an exFAT SSD without formatting the disk."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from score_sw_fabric.storage import (
    ACCOUNT_HOME,
    CONFIG,
    NATIVE_FILESYSTEMS,
    bridge_mount,
    discover_ssds,
    select_storage,
)


def configure(uuid: str, size_gib: int = 128) -> dict[str, object]:
    matches = [disk for disk in discover_ssds() if disk.uuid == uuid]
    if len(matches) != 1:
        raise ValueError("Expected exactly one mounted external SSD with the selected UUID")
    disk = matches[0]
    if disk.filesystem in NATIVE_FILESYSTEMS:
        return {"selection": select_storage().__dict__}
    settings: dict[str, Any] = (
        json.loads(CONFIG.read_text()) if CONFIG.exists() else {"schema_version": 1}
    )
    if not isinstance(settings, dict) or not isinstance(settings.get("volumes", {}), dict):
        raise ValueError("Storage configuration must contain a volumes mapping")
    volumes = settings.setdefault("volumes", {})
    if disk.uuid not in volumes:
        if not 32 <= size_gib <= 1024:
            raise ValueError("Build volume size must be between 32 and 1024 GiB")
        size = size_gib * 1024**3
        if shutil.disk_usage(disk.mount).free < size + 10 * 1024**3:
            raise OSError("External SSD lacks space for the new image plus 10 GiB headroom")
        tools = ACCOUNT_HOME / ".local/share/s-core-tools/fuse2fs-1.46.5"
        helper = tools / "usr/bin/fuse2fs"
        if not helper.is_file():
            raise OSError("Install the recorded portable fuse2fs prerequisite first")
        relative = Path(".s-core-build/build-volume-v1.ext4")
        folder = disk.mount / relative.parent
        if folder.is_symlink():
            raise ValueError("Refusing a symlink for the external build image directory")
        folder.mkdir(exist_ok=True)
        image = disk.mount / relative
        # Exclusive creation is essential: never mkfs an existing file or device.
        with image.open("xb") as stream:
            print(f"Allocating {size_gib} GiB Linux build image on {disk.mount}", flush=True)
            stream.truncate(size)
        print("Initializing the new image; existing disk files remain untouched", flush=True)
        subprocess.run(
            [
                "/usr/sbin/mkfs.ext4",
                "-q",
                "-m",
                "0",
                "-E",
                f"root_owner={os.getuid()}:{os.getgid()},nodiscard",
                "-F",
                str(image),
            ],
            check=True,
        )
        volumes[disk.uuid] = {
            "image_relative": str(relative),
            "image_size_bytes": size,
            "fuse2fs": str(helper),
            "library_path": str(tools / "lib/x86_64-linux-gnu"),
            "image_uuid": subprocess.check_output(
                ["/usr/sbin/blkid", "-p", "-s", "UUID", "-o", "value", str(image)],
                text=True,
            ).strip(),
        }
        CONFIG.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        temporary = CONFIG.with_suffix(".new")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            json.dump(settings, stream, indent=2)
            stream.write("\n")
        temporary.replace(CONFIG)
    mount = bridge_mount(disk, volumes[disk.uuid])
    return {"linux_volume": str(mount), "selection": select_storage().__dict__}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uuid", required=True)
    parser.add_argument("--size-gib", type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(configure(args.uuid, args.size_gib), indent=2))


if __name__ == "__main__":
    main()
