"""Actual Cppcheck XML and native GCC instrumented defect/fix executions."""

from __future__ import annotations

import base64
import json
import shutil
from pathlib import Path

import pytest

from score_sw_fabric.cli import main
from score_sw_fabric.quality.complementary import capabilities, run
from tests.quality_support import ROOT, complementary_request, ref


@pytest.mark.parametrize(
    "adapter,native_id",
    [
        ("cppcheck", "nullPointer"),
        ("asan", "heap-buffer-overflow"),
        ("ubsan", "signed integer overflow"),
    ],
)
def test_genuine_available_seed_and_fresh_fix(adapter: str, native_id: str, tmp_path: Path) -> None:
    code, capability, _, _ = capabilities(
        complementary_request(tmp_path, adapter, "capabilities"), adapter
    )
    assert code == 0 and capability["capability"]["state"] == "available"
    path = complementary_request(tmp_path, adapter)
    source = tmp_path / "component/check.cpp"
    before = source.read_bytes()
    code, seeded, _, _ = run(path, adapter)
    assert code == 1 and seeded["outcome"] == "findings"
    assert any(native_id in d["native_id"] for d in seeded["diagnostics"])
    assert seeded["extraction"]["adequacy"] == "adequate"
    assert source.read_bytes() == before
    path = complementary_request(tmp_path, adapter)
    clean = ROOT / (
        "tests/fixtures/quality/corrected/check.cpp"
        if adapter == "cppcheck"
        else "tests/fixtures/quality/sanitizers/corrected/check.cpp"
    )
    shutil.copy2(clean, source)
    record = json.loads(path.read_text())
    record["files"] = [dict(ref(source), path="check.cpp")]
    path.write_text(json.dumps(record))
    code, corrected, _, _ = run(path, adapter)
    assert code == 0 and corrected["outcome"] == "completed"
    assert corrected["baseline"]["source_digest"] != seeded["baseline"]["source_digest"]
    assert corrected["diagnostics"] == []
    assert corrected["engineering_readiness"] == "not_evaluated"
    assert corrected["assurance_eligibility"] == "not_eligible"
    if adapter != "cppcheck":
        runtime = next(p for p in seeded["phases"] if p["name"] == "runtime")
        assert runtime["exit_code"] == 55
        assert native_id.encode() in base64.b64decode(runtime["stderr"]["base64"])
        assert seeded["configuration"]["effective"]["suppression_rules"] == []
        probe_effective = seeded["capability"]["effective_config"]
        effective = seeded["configuration"]["effective"]
        assert probe_effective["generated_binary"] != effective["generated_binary"]
        assert "/probe/" in probe_effective["rendered_runtime"][effective["runtime_name"]]
        assert "/probe/" not in effective["rendered_runtime"][effective["runtime_name"]]


@pytest.mark.parametrize("adapter", ["cppcheck", "asan", "ubsan"])
def test_unknown_scope_and_cli_publication(adapter: str, tmp_path: Path) -> None:
    path = complementary_request(tmp_path, adapter, expected_units=None)
    out = tmp_path / "run.json"
    assert (
        main(
            [
                "quality",
                "run",
                "--adapter",
                adapter,
                "--request",
                str(path),
                "--out",
                str(out),
                "--json",
            ]
        )
        == 1
    )
    record = json.loads(out.read_text())
    assert "EXTRACTION_UNKNOWN" in record["gaps"]
    assert record["extraction"]["adequacy"] != "adequate"
    schema = json.loads((ROOT / f"schemas/quality-{adapter}-analysis-run.schema.json").read_text())
    assert set(record) == set(schema["required"])


def test_compile_failure_does_not_become_clean_runtime(tmp_path: Path) -> None:
    path = complementary_request(tmp_path, "ubsan")
    source = tmp_path / "component/check.cpp"
    source.write_text("int main() { return undefined_value; }")
    record = json.loads(path.read_text())
    record["files"] = [dict(ref(source), path="check.cpp")]
    path.write_text(json.dumps(record))
    code, result, _, _ = run(path, "ubsan")
    assert code == 1 and result["outcome"] == "incomplete"
    assert "PHASE_FAILED" in result["gaps"]
    assert not any(p["name"] == "runtime" for p in result["phases"])
    assert "generated_binary" not in result["configuration"]["effective"]


def test_cppcheck_missing_include_blocks_clean_evidence(tmp_path: Path) -> None:
    path = complementary_request(tmp_path, "cppcheck")
    source = tmp_path / "component/check.cpp"
    source.write_text('#include "missing.h"\nint main() { return 0; }\n')
    request = json.loads(path.read_text())
    request["files"] = [dict(ref(source), path="check.cpp")]
    path.write_text(json.dumps(request))
    code, record, _, _ = run(path, "cppcheck")
    assert code == 1 and record["outcome"] == "incomplete"
    assert "CPPCHECK_ANALYSIS_INCOMPLETE" in record["gaps"]
    assert any(d["native_id"] == "missingInclude" for d in record["diagnostics"])
    assert record["extraction"]["adequacy"] == "incomplete"


def test_unknown_runtime_exit_does_not_become_clean(tmp_path: Path) -> None:
    path = complementary_request(tmp_path, "ubsan")
    source = tmp_path / "component/check.cpp"
    source.write_text("int main() { return 7; }\n")
    request = json.loads(path.read_text())
    request["files"] = [dict(ref(source), path="check.cpp")]
    path.write_text(json.dumps(request))
    code, record, _, _ = run(path, "ubsan")
    assert code == 1 and record["outcome"] == "incomplete"
    assert "SANITIZER_RUNTIME_INCOMPLETE" in record["gaps"]
    assert record["diagnostics"] == [] and record["processed_units"] == []


def test_sanitizer_truncated_probe_stays_incomplete(tmp_path: Path) -> None:
    code, record, _, _ = capabilities(
        complementary_request(tmp_path, "asan", "capabilities", output_limit_bytes=1024), "asan"
    )
    assert code == 1 and record["capability"]["state"] != "available"
    assert "OUTPUT_TRUNCATED" in record["gaps"]
