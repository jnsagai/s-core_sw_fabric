"""Freeze local queue tool locations and reject changed or disconnected installations."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from storage import validate_run_root

from score_sw_fabric.storage import ACCOUNT_HOME

REGISTRATION = ACCOUNT_HOME / ".config/s-core/someip84-tools.json"


def validate_tools(path: Path) -> dict:
    manifest = json.loads(path.read_text())
    roots = [Path(manifest["storage_root"])] + [
        Path(value) for value in manifest.get("additional_storage_roots", [])
    ]
    for root in roots:
        validate_run_root(root)
        if not (root / "storage-selection.json").is_file():
            raise ValueError("Queue tool installation lacks bound storage provenance")
    for filename, expected in manifest["identities"].items():
        unit = Path(filename)
        if not any(unit.resolve(strict=True).is_relative_to(root) for root in roots):
            raise ValueError("Queue tool identity escapes its bound installation")
        actual = hashlib.sha256(unit.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError("Queue tool installation changed: " + filename)
    for filename in manifest["tools"].values():
        if filename not in manifest["identities"]:
            raise ValueError("Queue tool entrypoint lacks a measured identity")
    return manifest


def freeze_tools(root: Path) -> None:
    """Only new runs consume the registration; historical frozen runs stay unchanged."""
    validate_tools(REGISTRATION)
    (root / "queue-tools.json").write_bytes(REGISTRATION.read_bytes())


def installed_tools() -> dict:
    frozen = Path(__file__).with_name("queue-tools.json")
    return validate_tools(frozen) if frozen.exists() else {}
