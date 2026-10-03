"""Frozen tool installations fail closed on drift, missing identity and detachment."""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[2] / "docs/handoff/someip-84/factory"


@pytest.fixture
def installed(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(HERE))
    module = importlib.import_module("queue_tools")
    root = tmp_path / "installation"
    root.mkdir()
    (root / "storage-selection.json").write_text("{}")
    tool = root / "tool"
    tool.write_text("original tool")
    manifest = tmp_path / "frozen.json"
    manifest.write_text(
        json.dumps(
            {
                "storage_root": str(root),
                "tools": {"test": str(tool)},
                "identities": {str(tool): hashlib.sha256(tool.read_bytes()).hexdigest()},
            }
        )
    )
    monkeypatch.setattr(module, "validate_run_root", lambda _root: None)
    return module, manifest, tool


def test_changed_tool_rejected(installed):
    module, manifest, tool = installed
    module.validate_tools(manifest)
    tool.write_text("substituted tool")
    with pytest.raises(ValueError, match="installation changed"):
        module.validate_tools(manifest)


def test_disconnected_installation_rejected(installed, monkeypatch):
    module, manifest, _tool = installed

    def disconnected(_root):
        raise OSError("Bound external SSD is disconnected")

    monkeypatch.setattr(module, "validate_run_root", disconnected)
    with pytest.raises(OSError, match="disconnected"):
        module.validate_tools(manifest)


def test_unmeasured_entrypoint_rejected(installed):
    module, manifest, _tool = installed
    data = json.loads(manifest.read_text())
    data["identities"] = {}
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="lacks a measured identity"):
        module.validate_tools(manifest)


def test_tool_symlink_escape_rejected(installed):
    module, manifest, tool = installed
    outside = manifest.parent / "unbound-tool"
    outside.write_bytes(tool.read_bytes())
    tool.unlink()
    tool.symlink_to(outside)
    with pytest.raises(ValueError, match="escapes"):
        module.validate_tools(manifest)


def test_frozen_run_ignores_later_registration(installed, monkeypatch):
    module, manifest, _tool = installed
    root = manifest.parent / "run"
    root.mkdir()
    monkeypatch.setattr(module, "REGISTRATION", manifest)
    module.freeze_tools(root)
    expected = (root / "queue-tools.json").read_bytes()
    manifest.write_text("invalid new registration")
    assert (root / "queue-tools.json").read_bytes() == expected
    module.validate_tools(root / "queue-tools.json")
