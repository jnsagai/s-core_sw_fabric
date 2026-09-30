"""008 `score-fabric safety` exits, guarded outputs and schema alignment."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from score_sw_fabric.cli import main
from score_sw_fabric.safety import analysis, gates, packet, profile
from tests.agent_support import ROOT, ref, write_yaml
from tests.safety_support import FIXTURES, PROFILE, check_request, copy_version


def run(capsys: pytest.CaptureFixture[str], *arguments: str) -> tuple[int, dict[str, object]]:
    status = main(["safety", *arguments, "--json"])
    captured = capsys.readouterr()
    return status, json.loads(
        (captured.out if status == 0 else captured.err).strip().splitlines()[-1]
    )


def test_demo02_pipeline_exits(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "out"
    status, summary = run(
        capsys,
        "check",
        "--request",
        str(check_request(tmp_path, FIXTURES / "v1", name="v1.yaml")),
        "--out",
        str(out / "v1.json"),
    )
    assert status == 1 and summary["outcome"] == "blocked"
    request = check_request(
        tmp_path, FIXTURES / "v2", baseline=FIXTURES / "v1", iteration=2, name="v2.yaml"
    )
    status, summary = run(capsys, "check", "--request", str(request), "--out", str(out / "v2.json"))
    assert status == 0 and summary["outcome"] == "complete"
    packet_request = tmp_path / "control/packet.yaml"
    write_yaml(
        packet_request,
        {
            "schema_version": 1,
            "kind": "safety_packet_request",
            "profile": ref(PROFILE),
            "report": ref(out / "v2.json"),
            "evidence": [],
            "protected_roots": [str(ROOT)],
        },
    )
    status, summary = run(
        capsys, "packet", "--request", str(packet_request), "--out", str(out / "packet.json")
    )
    assert status == 0 and summary["packet_state"] == "review_requestable"
    gate_request = tmp_path / "control/gate.yaml"
    write_yaml(
        gate_request,
        {
            "schema_version": 1,
            "kind": "safety_gate_request",
            "profile": ref(PROFILE),
            "packet": ref(out / "packet.json"),
            "decisions": [],
            "protected_roots": [str(ROOT)],
        },
    )
    status, summary = run(
        capsys, "gate", "--request", str(gate_request), "--out", str(out / "gate.json")
    )
    assert status == 1
    assert summary["design_acceptance"] == "awaiting_decision" and summary["closure"] == "blocked"


def test_invalid_input_preserves_prior_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    current = copy_version(tmp_path, "v2")
    request = check_request(tmp_path, current)
    target = tmp_path / "out/report.json"
    target.parent.mkdir()
    target.write_text("prior")
    (current / "fmea.rst").write_text("drift")
    status, diagnostic = run(capsys, "check", "--request", str(request), "--out", str(target))
    assert status == 2 and diagnostic["code"] == "INPUT_DRIFT"
    assert target.read_text() == "prior"


def test_output_cannot_overwrite_native_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    current = copy_version(tmp_path, "v2")
    request = check_request(tmp_path, current)
    before = (current / "fmea.rst").read_bytes()
    status, diagnostic = run(
        capsys, "check", "--request", str(request), "--out", str(current / "report.json")
    )
    assert status == 2 and diagnostic["code"] == "OUTPUT_PROTECTED"
    assert (current / "fmea.rst").read_bytes() == before and not (current / "report.json").exists()


def _required(name: str) -> set[str]:
    value = json.loads((ROOT / f"schemas/{name}.schema.json").read_text())["required"]
    return set(value)


def test_schemas_match_code_and_outputs(tmp_path: Path) -> None:
    envelope = {"schema_version", "kind"}
    assert _required("safety-analysis-profile") == profile.PROFILE_FIELDS | envelope
    assert _required("safety-check-request") == analysis.CHECK_FIELDS | envelope
    assert _required("safety-packet-request") == packet.PACKET_FIELDS | envelope
    assert _required("safety-gate-request") == gates.GATE_FIELDS | envelope
    assert set(yaml.safe_load(PROFILE.read_text())) == _required("safety-analysis-profile")
    from tests.contract.test_safety_gates import build_packet
    from tests.safety_support import report

    record = report(tmp_path, FIXTURES / "v2", baseline=FIXTURES / "v1", iteration=2)
    _, packet_value = build_packet(tmp_path, record)
    evaluation = gates.evaluate(profile.load_profile(PROFILE.read_bytes()), packet_value, [])
    assert set(record) == _required("safety-analysis-report")
    assert set(packet_value) == _required("safety-review-packet")
    gate_keys = {
        "packet_digest",
        "profile",
        "component",
        "analysis",
        "decisions",
        *evaluation,
        "engineering_readiness",
        "limitations",
        "digest",
    }
    assert gate_keys | {"schema_version", "kind"} == _required("safety-gate-evaluation")
