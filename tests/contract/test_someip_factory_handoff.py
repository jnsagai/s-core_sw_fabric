"""Host handoff must authenticate its native waiter and retain incomplete phases."""

from __future__ import annotations

import importlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def handoff(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.syspath_prepend(str(ROOT / "docs/handoff/someip-84/factory"))
    return importlib.import_module("run_host")


def test_native_cli_reads_private_disposable_auth(tmp_path: Path, handoff: Any) -> None:
    binary = Path("/tmp/score-fabro-build-kDgEvg/target/debug/fabro")
    if not binary.exists():
        pytest.skip("Pinned rebuilt Fabro is unavailable")
    token = "fabro_dev_" + "b" * 64
    path = handoff.cli_auth_file(tmp_path, "http://127.0.0.1:43913", token)
    assert path.stat().st_mode & 0o077 == 0
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(tmp_path),
        "FABRO_AUTH_FILE": str(path),
        "FABRO_NO_UPGRADE_CHECK": "true",
    }
    result = subprocess.run(
        [str(binary), "--json", "auth", "status", "--server", "http://127.0.0.1:43913"],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert "dev-token" in result.stdout
    assert token not in result.stdout + result.stderr


def test_missing_phase_keeps_available_original_bytes(tmp_path: Path, handoff: Any) -> None:
    source = tmp_path / "target/.llm_tmp/baseline"
    source.mkdir(parents=True)
    (source / "regression.stderr").write_bytes(b"original\x00bytes\n")
    dest = tmp_path / "evidence"
    dest.mkdir()
    result = handoff.collect_measurements(tmp_path, dest)
    assert (dest / "baseline/regression.stderr").read_bytes() == b"original\x00bytes\n"
    assert result["external-candidate"] == "missing"
    assert result["baseline"] == "measurement_missing"


def test_partial_measurements_cannot_count_as_factory_validation(
    tmp_path: Path, handoff: Any
) -> None:
    source = tmp_path / "target/.llm_tmp/baseline"
    source.mkdir(parents=True)
    (source / "measurement.json").write_text(json.dumps({"tests": 13, "failures": 7}))
    dest = tmp_path / "evidence"
    dest.mkdir()
    result = handoff.collect_measurements(tmp_path, dest)
    assert result == {"baseline": "present", "external-candidate": "missing"}
