"""Run the dedicated SOME/IP server from persistent, private internal state."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from prepare import BINARY, PIN

from score_sw_fabric.runtime import supervision as s
from score_sw_fabric.storage import STATE


def main() -> None:
    root = Path(sys.argv[1]).absolute()
    if root != STATE / "someip84-server" or any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError("Expected the dedicated private internal server root")
    bootstrap = s.read(root / "bootstrap.json")
    if (
        bootstrap["source_commit"] != PIN
        or not BINARY.is_file()
        or BINARY.is_symlink()
        or s.digest(BINARY) != bootstrap["binary_sha256"]
    ):
        raise ValueError("Registered SOME/IP runtime identity differs")
    config = root / "settings.toml"
    if s.digest(config) != bootstrap["config_sha256"]:
        raise ValueError("Dedicated server configuration changed")
    environment = {
        "PATH": os.environ["PATH"] + ":/usr/sbin:/sbin",
        "HOME": str(root / "home"),
        "FABRO_AUTH_FILE": str(root / "cli-auth.json"),
        "FABRO_DEV_TOKEN": bootstrap["dev_token"],
        "SESSION_SECRET": s.read(root / "server-recovery-auth.json")["session_secret"],
        "FABRO_HTTP_PROXY_POLICY": "disabled",
        "FABRO_NO_UPGRADE_CHECK": "true",
    }
    s.atomic(
        root / "queue-server.json",
        {
            "pid": os.getpid(),
            "process_identity": s.process_identity(os.getpid()),
            "config_path": str(config),
            "launcher": str(Path(__file__).resolve()),
            "source_commit": PIN,
            "binary_sha256": bootstrap["binary_sha256"],
            "storage": str(root / "storage"),
            "base_url": "http://127.0.0.1:43916",
        },
    )
    os.execve(
        str(BINARY),
        [
            str(BINARY),
            "server",
            "start",
            "--foreground",
            "--bind",
            "127.0.0.1:43916",
            "--storage-dir",
            str(root / "storage"),
            "--config",
            str(config),
            "--no-web",
        ],
        environment,
    )


if __name__ == "__main__":
    main()
