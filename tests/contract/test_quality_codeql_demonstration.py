"""Public demonstration refuses target inputs and preserves every execution failure."""

import base64
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

import score_sw_fabric.quality.codeql_demonstration as demonstration
from score_sw_fabric.cli import main
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.codeql_demonstration import NativeFailure, Operation, parse_request
from score_sw_fabric.quality.models import Budget
from tests.quality_codeql_support import selected, write
from tests.quality_support import ref


def request(tmp_path: Path) -> Path:
    ref = {"path": "absent.yaml", "sha256": "a" * 64}
    return write(
        tmp_path / "demo.json",
        {
            "schema_version": 1,
            "kind": "quality_codeql_demonstration_request",
            "id": "contract-demonstration",
            "purpose": "software_demonstration",
            "case": "seeded",
            "prerequisites": ref,
            "compiler": ref,
            "reporting_toolchain": ref,
            "license": ref,
            "report_patch_mode": "git_recount",
            "timeout_seconds": 300,
            "total_timeout_seconds": 600,
            "output_limit_bytes": 1048576,
            "protected_roots": [],
        },
    )


@pytest.mark.parametrize(
    "key,value",
    [
        ("purpose", "private_target_analysis"),
        ("purpose", True),
        ("case", "arbitrary"),
        ("case", ["seeded"]),
        ("report_patch_mode", "automatic"),
        ("report_patch_mode", False),
        ("timeout_seconds", True),
        ("timeout_seconds", 0),
        ("timeout_seconds", 3601),
        ("total_timeout_seconds", 0),
        ("total_timeout_seconds", 3601),
        ("output_limit_bytes", 1023),
        ("output_limit_bytes", 16777217),
        ("root", "/private/target"),
        ("files", ["private.cpp"]),
        ("build_command", "touch marker"),
        ("approved", True),
        ("license", {"path": "../outside", "sha256": "a" * 64}),
    ],
)
def test_demo_unsafe_scope_or_bounds_refuse(tmp_path: Path, key: str, value: Any) -> None:
    path = request(tmp_path)
    obj = json.loads(path.read_bytes())
    obj[key] = value
    write(path, obj)
    with pytest.raises(InputError):
        parse_request(path)


def test_demo_exact_request_has_no_source_selection(tmp_path: Path) -> None:
    obj = parse_request(request(tmp_path))
    assert obj["case"] == "seeded" and obj["purpose"] == "software_demonstration"
    assert not {"root", "files", "queries", "build_command"}.intersection(obj)


def test_demo_duplicate_yaml_refuses(tmp_path: Path) -> None:
    path = request(tmp_path)
    path.write_text("schema_version: 1\nschema_version: 1\n")
    with pytest.raises(InputError):
        parse_request(path)


def controls(tmp_path: Path) -> Path:
    prerequisite = selected(tmp_path)
    obj = json.loads(prerequisite.read_bytes())
    chain = json.loads((tmp_path / "toolchain.json").read_bytes())
    root = Path(__file__).resolve().parents[2]
    tools = yaml.safe_load((root / "profiles/s-core-quality-v1.yaml").read_bytes())[
        "installed_context"
    ]["tools"]
    license_bytes = base64.b64decode(
        next(
            t["license_notice"]["base64"]
            for t in tools
            if t["toolchain"]["kind"] == "quality_codeql_toolchain_profile"
        )
    )
    license_file = Path(chain["tool"]["path"]).parent / "LICENSE.md"
    license_file.write_bytes(license_bytes)
    compiler = {**chain, "kind": "quality_sanitizer_toolchain_profile"}
    reporter = {
        **chain,
        "kind": "quality_codeql_reporting_toolchain_profile",
        "tool": {**chain["tool"], "version": "Python 3.9.25"},
    }
    compiler_path = write(tmp_path / "compiler.json", compiler)
    reporter_path = write(tmp_path / "reporter.json", reporter)
    path = request(tmp_path)
    demo = json.loads(path.read_bytes())
    demo.update(
        prerequisites=ref(prerequisite),
        compiler=ref(compiler_path),
        reporting_toolchain=ref(reporter_path),
        license=ref(license_file),
        protected_roots=obj["protected_roots"],
    )
    return write(path, demo)


def test_demo_output_alias_refuses_before_inspection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = controls(tmp_path)
    monkeypatch.setattr(demonstration.codeql, "inspect", lambda *a: pytest.fail("inspection ran"))
    original = path.read_bytes()
    with pytest.raises(InputError):
        demonstration.run(path, path)
    assert path.read_bytes() == original


@pytest.mark.parametrize(
    "mutation", ["control_drift", "license_bytes", "license_location", "nested_request"]
)
def test_demo_invalid_selection_preserves_previous_output_before_inspection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    path = controls(tmp_path)
    obj = json.loads(path.read_bytes())
    if mutation == "control_drift":
        Path(obj["compiler"]["path"]).write_text("changed")
    elif mutation == "license_bytes":
        license_path = Path(obj["license"]["path"])
        license_path.write_text("unreviewed terms")
        obj["license"] = ref(license_path)
    elif mutation == "license_location":
        other = tmp_path / "different-LICENSE.md"
        other.write_bytes(Path(obj["license"]["path"]).read_bytes())
        obj["license"] = ref(other)
    else:
        nested = write(tmp_path / "nested.json", obj)
        obj["prerequisites"] = ref(nested)
    write(path, obj)
    out = tmp_path / "prior.json"
    out.write_text("previous result")
    monkeypatch.setattr(demonstration.codeql, "inspect", lambda *a: pytest.fail("inspection ran"))
    assert (
        main(["quality", "run", "--adapter", "codeql", "--request", str(path), "--out", str(out)])
        == 2
    )
    assert out.read_text() == "previous result"


def test_demo_fixtures_remain_unavailable_without_native_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = controls(tmp_path)
    monkeypatch.setattr(demonstration, "_native", lambda *a: pytest.fail("fixture execution"))
    code, record, _, _ = demonstration.run(path)
    assert code == 1 and record["outcome"] == "unavailable"
    assert not record["analysis_executed"] and not record["native_reporting_executed"]
    assert record["extraction"]["adequacy"] == "unknown"
    assert record["accepted_claims"] == 0 and record["diagnostics"] == []
    assert "EXECUTION_PREREQUISITES_UNAVAILABLE" in record["execution_gaps"]


@pytest.mark.parametrize(
    "exit_code,timed_out,truncated,error,reason",
    [
        (1, False, False, None, "PHASE_FAILED"),
        (-9, True, False, None, "PHASE_TIMEOUT"),
        (0, False, True, None, "OUTPUT_TRUNCATED"),
        (None, False, False, "OSError", "PHASE_FAILED"),
    ],
)
def test_demo_native_phase_failures_are_retained(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exit_code: int | None,
    timed_out: bool,
    truncated: bool,
    error: str | None,
    reason: str,
) -> None:
    record: dict[str, Any] = {"phases": [], "native_reporting_executed": False}
    phase = {
        "name": "native:report",
        "exit_code": exit_code,
        "timed_out": timed_out,
        "error": error,
        "stdout": {"truncated": truncated},
        "stderr": {"truncated": False},
    }
    monkeypatch.setattr(demonstration, "execute", lambda *a: phase)
    operation = Operation(
        record, tmp_path, {"timeout_seconds": 30, "total_timeout_seconds": 60}, Budget(1024)
    )
    with pytest.raises(NativeFailure, match=reason):
        operation.step("native:report", ["fixed", "args"], {})
    assert record["phases"] == [phase]
    assert record["native_reporting_executed"] is (error is None)


def test_demo_elapsed_budget_stops_before_native_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    operation = Operation(
        {"phases": []}, tmp_path, {"timeout_seconds": 30, "total_timeout_seconds": 60}, Budget(1024)
    )
    operation.deadline = 0
    monkeypatch.setattr(demonstration, "execute", lambda *a: pytest.fail("expired execution"))
    with pytest.raises(NativeFailure, match="TIME_BUDGET_EXHAUSTED"):
        operation.step("native:report", ["fixed", "args"], {})
