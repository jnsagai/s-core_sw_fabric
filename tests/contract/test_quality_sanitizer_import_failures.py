"""Fixture runtime failures cannot become clean imports or portable evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from score_sw_fabric.assurance.models import digest, seal
from score_sw_fabric.quality import imports, packet
from score_sw_fabric.quality.models import raw_bytes
from tests.quality_import_support import identity, selection, write_json
from tests.quality_support import ROOT, ref


@pytest.mark.parametrize("exit_code", [0, 55])
@pytest.mark.parametrize("with_finding", [False, True])
def test_fatal_leak_runtime_survives_original_import_and_offline_replay(
    tmp_path: Path, exit_code: int, with_finding: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = selection(tmp_path)
    request = json.loads(path.read_bytes())
    ident = identity("asan")
    ident.update(name="fixture AddressSanitizer", version="fixture-only")
    baseline_path = Path(request["baseline"]["path"])
    baseline = json.loads(baseline_path.read_bytes())
    baseline["identities"] = [ident]
    request["baseline"] = write_json(baseline_path, seal(baseline))
    stderr = b"LeakSanitizer has encountered a fatal error.\n"
    stderr += b"HINT: LeakSanitizer does not work under ptrace (strace, gdb, etc)\n"
    if with_finding:
        stderr += b"ERROR: AddressSanitizer: heap-buffer-overflow\n"
        stderr += b"#0 fixture /native/source/check.cpp:2:1\n"
    native = tmp_path / "runtime-stderr.txt"
    native.write_bytes(stderr)
    artifact = request["artifacts"][0]
    artifact.update(tool="asan", format="asan-text", ref=ref(native))
    artifact["bindings"]["identity_digest"] = digest(ident)
    request["artifacts"] = [artifact]
    manifest_path = Path(request["extraction"]["path"])
    manifest = json.loads(manifest_path.read_bytes())
    observation = manifest["observations"][0]
    observation.update(
        tool="asan",
        identity_digest=digest(ident),
        extracted_units=None,
        required_reports=[],
        phases=[
            {
                "id": "runtime",
                "role": "analyze",
                "status": "completed",
                "exit_code": exit_code,
                "timed_out": False,
                "artifacts": [artifact["id"]],
            }
        ],
    )
    request["extraction"] = write_json(manifest_path, seal(manifest))
    write_json(path, request)
    code, imported, _, _ = imports.import_outputs(path)
    assert code == 1 and imported["outcome"] == "incomplete"
    assert imported["extraction"]["adequacy"] == "incomplete"
    assert bool(imported["findings"]) is with_finding
    assert {
        "LEAK_SANITIZER_RUNTIME_FAILED",
        "LEAK_SANITIZER_PTRACE_UNSUPPORTED",
        "SANITIZER_RUNTIME_INCOMPLETE",
    }.issubset(imported["gaps"])
    assert raw_bytes(imported["artifacts"][0]["raw"]) == stderr
    notice = tmp_path / "NOTICE.txt"
    notice.write_text("Synthetic fixture; no native execution or engineering acceptance.\n")
    packet_request = tmp_path / "packet.json"
    write_json(
        packet_request,
        {
            "schema_version": 1,
            "kind": "quality_packet_request",
            "profile": request["profile"],
            "coverage": None,
            "analyses": [
                {"request": ref(path), "report": write_json(tmp_path / "import.json", imported)}
            ],
            "dispositions": [],
            "source_snapshots": [
                {
                    "baseline_digest": imported["baseline"]["full_digest"],
                    "root": str(tmp_path / "source"),
                }
            ],
            "notices": [
                {
                    "id": "fixture-notice",
                    "license": "synthetic fixture",
                    "notice": "Test only",
                    "applies_to": [
                        "tool:asan",
                        *("native:" + s["id"] for s in imported["profile"]["native_sources"]),
                    ],
                    "ref": ref(notice),
                }
            ],
            "protected_roots": [str(ROOT)],
        },
    )
    _, portable, _, _ = packet.packet(packet_request)
    assert "SANITIZER_RUNTIME_INCOMPLETE" in portable["gaps"]
    assert portable["accepted_claims"] == 0
    monkeypatch.setattr(Path, "open", lambda *a, **k: pytest.fail("offline host read"))
    monkeypatch.setattr(Path, "stat", lambda *a, **k: pytest.fail("offline host probe"))
    assert packet.verify_packet(portable)["reproduced"]
