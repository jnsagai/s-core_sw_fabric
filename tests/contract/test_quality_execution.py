"""Actual bounded process capture and fail-closed native diagnostics."""

from __future__ import annotations

import base64
import hashlib
import sys
from pathlib import Path

import pytest

from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.models import Budget, execute
from score_sw_fabric.quality.native_outputs import diagnostics


def test_output_prefix_full_digest_and_timeout(tmp_path: Path) -> None:
    data = b"x" * 20000
    phase = execute(
        "loud",
        [sys.executable, "-c", "import sys;sys.stdout.write('x'*20000)"],
        tmp_path,
        5,
        Budget(1024),
        {},
    )
    raw = phase["stdout"]
    assert raw["bytes"] == len(data) and raw["truncated"]
    assert base64.b64decode(raw["base64"]) == data[:1024]
    assert raw["sha256"] == hashlib.sha256(data).hexdigest()
    phase = execute(
        "timeout",
        [sys.executable, "-c", "import time;time.sleep(10)"],
        tmp_path,
        1,
        Budget(1024),
        {},
    )
    assert phase["timed_out"] and phase["exit_code"] is not None


def test_native_duplicate_keys_and_unselected_path(tmp_path: Path) -> None:
    with pytest.raises(InputError):
        diagnostics(b"Diagnostics: []\nDiagnostics: []", "a", tmp_path, {"check.cpp": b"x"})
    with pytest.raises(InputError):
        diagnostics(
            b"Diagnostics:\n- DiagnosticName: x\n  Level: Warning\n"
            b"  DiagnosticMessage: {Message: x, FilePath: /other/x.cpp, FileOffset: 0}\n",
            "a",
            tmp_path,
            {"check.cpp": b"x"},
        )
