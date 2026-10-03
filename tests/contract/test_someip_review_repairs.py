"""Regression evidence for the three independently reproduced review defects."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

HERE = Path(__file__).resolve().parents[2] / "docs/handoff/someip-84/factory"


@pytest.fixture
def modules(monkeypatch):
    monkeypatch.syspath_prepend(str(HERE))
    return importlib.import_module("perf_bridge"), importlib.import_module("repair_workflow")


@pytest.mark.parametrize(
    "workload,profiler,expected", [(-11, 0, 139), (-9, 0, 137), (7, 0, 7), (0, 254, 254), (0, 0, 0)]
)
def test_workload_failure_survives_successful_recording(modules, workload, profiler, expected):
    bridge, _ = modules
    assert bridge.execution_exit(workload, profiler) == expected


@pytest.mark.parametrize(
    "path,code,allowed",
    [
        ("/owned/bin/tests/benchmarks/echo_server", -9, True),
        ("/owned/bin/score/gatewayd/gatewayd", -9, True),
        ("/owned/bin/score/someipd/someipd", -9, True),
        ("/owned/bin/tests/benchmarks/ipc_benchmarks", -9, False),
        ("/owned/bin/tests/benchmarks/echo_server", -11, False),
        ("/owned/echo_server", -9, False),
    ],
)
def test_native_cleanup_requires_known_daemon_and_sigkill(modules, path, code, allowed):
    assert modules[0].native_cleanup(Path(path), code) is allowed


@pytest.mark.parametrize(
    "changed", ["qemu.stdout", "qemu.stderr", "qemu.command.json", "native-artifacts/test.xml"]
)
def test_local_pass_rejects_changed_original_evidence(modules, tmp_path, changed):
    _, repair = modules
    evidence = importlib.import_module("evidence")
    out = tmp_path / "obligation-results/native_integration-1"
    out.mkdir(parents=True)
    for name in ("qemu.stdout", "qemu.stderr", "qemu.command.json", "native-artifacts/test.xml"):
        path = out / name
        path.parent.mkdir(exist_ok=True)
        path.write_text("Original measured bytes")
    result = {"status": "completed", "commands": [{"label": "qemu", "exit_code": 0}]}
    evidence.seal_result(out, result)
    (out / "result.json").write_text(json.dumps(result))
    repair.latest(tmp_path, "native_integration")
    (out / changed).write_text("Substituted bytes")
    with pytest.raises(ValueError, match="identity changed"):
        repair.latest(tmp_path, "native_integration")


def test_unbound_legacy_pass_is_refused(modules, tmp_path):
    _, repair = modules
    out = tmp_path / "obligation-results/native_tests-1"
    out.mkdir(parents=True)
    (out / "result.json").write_text(
        json.dumps({"status": "completed", "commands": [{"label": "tests", "exit_code": 0}]})
    )
    with pytest.raises(ValueError, match="unbound"):
        repair.latest(tmp_path, "native_tests")


def test_legacy_import_uses_archived_hashes_not_current_logs(modules, tmp_path):
    import io
    import tarfile

    evidence = importlib.import_module("evidence")
    original = tmp_path / "original"
    original.mkdir()
    result = original / "result.json"
    result.write_text(
        json.dumps(
            {
                "check": "native_tests",
                "status": "completed",
                "commands": [{"label": "tests", "exit_code": 0}],
            }
        )
    )
    for suffix in ("stdout", "stderr", "command.json"):
        (original / ("tests." + suffix)).write_text("Original measured evidence")
    checksums = {"evidence/native_tests/" + p.name: evidence.sha(p) for p in original.iterdir()}
    packet = {
        "evidence": {
            "native_tests": {
                "path": str(result),
                "sha256": evidence.sha(result),
                "portable_evidence": checksums,
            }
        }
    }
    archive = tmp_path / "packet.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        raw = json.dumps(packet).encode()
        member = tarfile.TarInfo("review-packet.json")
        member.size = len(raw)
        bundle.addfile(member, io.BytesIO(raw))
        for p in original.iterdir():
            bundle.add(p, arcname="evidence/native_tests/" + p.name)
    binding = evidence.archived_binding(archive, evidence.sha(archive), "native_tests")
    evidence.verify_result(result, json.loads(result.read_text()), binding)
    (original / "tests.stdout").write_text("Changed before import")
    with pytest.raises(ValueError, match="identity changed"):
        evidence.archived_binding(archive, evidence.sha(archive), "native_tests")


def integration_xml(tmp_path, integration):
    for target, names in integration.CASES.items():
        suite = ET.Element("testsuite")
        for name in sorted(names):
            case = ET.SubElement(suite, "testcase", name=name)
            if name == integration.EXCLUDED_CASE:
                ET.SubElement(
                    case, "skipped", type="pytest.skip", message=integration.EXCLUDED_REASON
                )
        destination = tmp_path / "native-artifacts" / target / "test.xml"
        destination.parent.mkdir(parents=True)
        ET.ElementTree(suite).write(destination)


@pytest.mark.parametrize(
    "defect",
    [
        None,
        "skip_applicable",
        "all_skipped",
        "missing_case",
        "wrong_reason",
        "changed_source",
        "wrong_platform",
        "failure",
    ],
)
def test_integration_case_outcomes_and_native_applicability(modules, tmp_path, defect):
    integration = importlib.import_module("integration_evidence")
    integration_xml(tmp_path, integration)
    result = {
        "integration_platform": "linux_qemu",
        "source_hashes": {integration.EXCLUSION_SOURCE: integration.EXCLUSION_SOURCE_SHA256},
    }
    log = "Executed 6 out of 6 tests: 6 tests pass.\n"
    application = tmp_path / "native-artifacts/test_score_test_applications/test.xml"
    tree = ET.parse(application)
    first = tree.getroot().find("testcase")
    if defect == "skip_applicable":
        ET.SubElement(first, "skipped", message="Target lacks required capabilities")
    elif defect == "all_skipped":
        for case in tree.iter("testcase"):
            ET.SubElement(case, "skipped", message="Target unavailable")
    elif defect == "missing_case":
        tree.getroot().remove(first)
    elif defect == "failure":
        ET.SubElement(first, "failure", message="Assertion failed")
    elif defect == "wrong_reason":
        next(tree.iter("skipped")).set("message", "Required capability missing")
    elif defect == "changed_source":
        result["source_hashes"][integration.EXCLUSION_SOURCE] = "changed"
    elif defect == "wrong_platform":
        result["integration_platform"] = "qnx"
    tree.write(application)
    assert integration.case_outcomes(tmp_path, result, log)["passed"] is (defect is None)
