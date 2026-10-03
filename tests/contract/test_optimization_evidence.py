"""Negative-first emergency containment, raw identity and persistent stage budgets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from score_sw_fabric.optimization.common import OptimizationError, canonical
from score_sw_fabric.optimization.evidence_query import query
from score_sw_fabric.optimization.firewall import admit_tool
from score_sw_fabric.optimization.tool_results import StageBudget, summarize_output


def sarif(path: Path, size: int = 1_100_000) -> bytes:
    value = {
        "version": "2.1.0",
        "runs": [
            {
                "tool": {"driver": {"name": "fixture"}},
                "results": [
                    {
                        "ruleId": "cpp/native-rule",
                        "message": {"text": "x" * size},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": "src/a.cpp"},
                                    "region": {"startLine": 23},
                                }
                            }
                        ],
                    },
                    {"ruleId": "cpp/other", "locations": []},
                ],
            }
        ],
    }
    data = json.dumps(value, separators=(",", ":")).encode()
    path.write_bytes(data)
    return data


@pytest.mark.parametrize(
    "name", ["read_file", "grep", "shell", "read_many_files", "mcp__raw__read"]
)
def test_generic_tools_cannot_bypass_evidence_boundary(name: str) -> None:
    with pytest.raises(OptimizationError, match="BOUNDED_TOOL_REQUIRED"):
        admit_tool(name, {"path": "result.sarif"})


def test_single_line_evidence_is_normalized_without_raw_ingress(tmp_path: Path) -> None:
    data = sarif(tmp_path / "result.sarif")
    result = query(tmp_path, "result.sarif", operation="findings", rule="cpp/native-rule")
    assert result["total"] == 1
    assert result["findings"][0]["rule"] == "cpp/native-rule"
    assert result["findings"][0]["locations"] == [{"path": "src/a.cpp", "line": 23}]
    assert result["raw"]["sha256"] == hashlib.sha256(data).hexdigest()
    assert len(canonical(result)) <= 12000
    assert (tmp_path / "result.sarif").read_bytes() == data
    assert "message" not in result["findings"][0]


def test_missing_location_never_disappears_from_summary(tmp_path: Path) -> None:
    sarif(tmp_path / "result.sarif", 2)
    result = query(tmp_path, "result.sarif", operation="summary")
    assert result["total"] == 2
    assert result["location_gaps"] == 1


@pytest.mark.parametrize("path", ["../raw.sarif", "/tmp/raw.sarif", "a/../../raw", "a\\b"])
def test_unsafe_paths_refused(tmp_path: Path, path: str) -> None:
    with pytest.raises(OptimizationError):
        query(tmp_path, path)


def test_symlink_and_digest_drift_refused(tmp_path: Path) -> None:
    sarif(tmp_path / "raw.sarif", 2)
    (tmp_path / "linked").symlink_to(tmp_path)
    with pytest.raises(OptimizationError, match="SYMLINK"):
        query(tmp_path, "linked/raw.sarif")
    with pytest.raises(OptimizationError, match="EVIDENCE_DRIFT"):
        query(tmp_path, "raw.sarif", expected_sha256="0" * 64)


def test_duplicate_json_keys_and_malformed_runs_refused(tmp_path: Path) -> None:
    for data in [b'{"runs":[],"runs":[]}', b'{"runs":"bad"}', b'{"runs":[]}']:
        (tmp_path / "raw.sarif").write_bytes(data)
        with pytest.raises(OptimizationError):
            query(tmp_path, "raw.sarif")


def test_pagination_filters_and_long_native_id_are_explicit(tmp_path: Path) -> None:
    sarif(tmp_path / "raw.sarif", 2)
    result = query(tmp_path, "raw.sarif", operation="findings", file="src/a.cpp", line=23)
    assert result["total"] == 1
    assert (
        query(tmp_path, "raw.sarif", operation="findings", offset=1)["findings"][0]["rule"]
        == "cpp/other"
    )
    value = json.loads((tmp_path / "raw.sarif").read_bytes())
    value["runs"][0]["results"][0]["ruleId"] = "a" * 20000
    (tmp_path / "raw.sarif").write_text(json.dumps(value))
    result = query(tmp_path, "raw.sarif", operation="findings")
    assert result["omitted_fields"] >= 1
    assert result["findings"][0]["rule"] is None


def test_summary_deterministic_and_duplicate_query_persists(tmp_path: Path) -> None:
    sarif(tmp_path / "raw.sarif", 2)
    result = query(tmp_path, "raw.sarif")
    assert result == query(tmp_path, "raw.sarif")
    state = tmp_path / "stage.json"
    StageBudget(state, "stage-a").consume({"name": "summary"}, result)
    with pytest.raises(OptimizationError, match="REPEATED_QUERY"):
        StageBudget(state, "stage-a").consume({"name": "summary"}, result)
    with pytest.raises(OptimizationError, match="STAGE_MISMATCH"):
        StageBudget(state, "stage-b").consume({"name": "summary"}, result)


def test_byte_and_stage_ceilings_are_not_bypassed_by_unicode(tmp_path: Path) -> None:
    stage = StageBudget(tmp_path / "state.json", "stage", max_total_tokens=200)
    with pytest.raises(OptimizationError, match="RESULT_LIMIT"):
        stage.consume({"q": 0}, {"data": "💥" * 4000})
    stage.consume({"q": 1}, {"data": "x" * 100})
    with pytest.raises(OptimizationError, match="STAGE_BUDGET"):
        stage.consume({"q": 2}, {"data": "x" * 100})


def test_log_preview_retains_complete_raw_bytes_and_failure(tmp_path: Path) -> None:
    raw = b"FAIL case_a\n" + b"x" * 40000 + b"\nterminal error"
    record = summarize_output(raw, tmp_path, "build.log", max_bytes=1000)
    assert record["truncated"]
    assert "FAIL case_a" in record["preview"]
    assert "terminal error" in record["preview"]
    assert record["raw"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert (tmp_path / "build.log").read_bytes() == raw
    assert len(canonical(record)) <= 1000
    with pytest.raises(OptimizationError, match="EVIDENCE_EXISTS"):
        summarize_output(b"changed", tmp_path, "build.log")


def test_collector_summary_keeps_machine_payload_off_feedback(tmp_path: Path) -> None:
    from score_sw_fabric.optimization.collector_summary import collector_summary

    sarif(tmp_path / "result.sarif")
    result = {"check_ref": "native-quality", "status": "findings", "commands": [], "blockers": []}
    raw = json.dumps({**result, "unbounded": "x" * 50000}).encode()
    (tmp_path / "result.json").write_bytes(raw)
    summary = collector_summary(result, tmp_path)
    assert len(canonical(summary)) <= 5000
    assert summary["raw"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert summary["structured_evidence"][0]["findings"][0]["rule"] == "cpp/native-rule"
    assert "unbounded" not in summary


def test_requested_location_beyond_preview_is_still_queryable(tmp_path: Path) -> None:
    value = {
        "runs": [
            {
                "results": [
                    {
                        "ruleId": "fixture-rule",
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": "a.cpp"},
                                    "region": {"startLine": n},
                                }
                            }
                            for n in range(1, 50)
                        ],
                    }
                ]
            }
        ]
    }
    (tmp_path / "raw.sarif").write_text(json.dumps(value))
    result = query(tmp_path, "raw.sarif", operation="findings", line=49)
    assert result["total"] == 1
    assert result["findings"][0]["locations"] == [{"path": "a.cpp", "line": 49}]
    assert result["findings"][0]["locations_omitted"] == 48


@pytest.mark.parametrize(
    "run,reason",
    [
        ({"tool": {"driver": {"rules": [None]}}, "results": []}, "SARIF_RULES"),
        ({"artifacts": [None], "results": []}, "SARIF_ARTIFACTS"),
        (
            {"results": [{"locations": [{"physicalLocation": {"region": []}}]}]},
            "SARIF_REGION",
        ),
    ],
)
def test_malformed_native_nested_fields_refuse(tmp_path: Path, run: dict, reason: str) -> None:
    (tmp_path / "raw.sarif").write_text(json.dumps({"runs": [run]}))
    with pytest.raises(OptimizationError, match=reason):
        query(tmp_path, "raw.sarif")


def test_collector_metadata_cannot_exceed_summary_ceiling(tmp_path: Path) -> None:
    from score_sw_fabric.optimization.collector_summary import collector_summary

    result = {"check_ref": "x" * 1_100_000, "status": "y" * 1_100_000, "commands": []}
    (tmp_path / "result.json").write_text(json.dumps(result))
    summary = collector_summary(result, tmp_path)
    assert len(canonical(summary)) <= 4999
    assert set(summary["omitted_fields"]) == {"check_ref", "status"}
    assert summary["raw"]["bytes"] > 2_000_000


def test_actual_repair_feedback_retains_full_host_result_and_copies_summary(
    tmp_path, monkeypatch
) -> None:
    import importlib

    factory = Path(__file__).resolve().parents[2] / "docs/handoff/someip-84/factory"
    monkeypatch.syspath_prepend(str(factory))
    hooks = importlib.import_module("repair_hooks")
    copied = []
    monkeypatch.setattr(hooks, "owned", lambda root, policy: "owned-fixture-container")
    monkeypatch.setattr(hooks, "docker", lambda *args: copied.append(args))
    result = {"status": "failed", "check_ref": "native-fixture", "raw_stdout": "x" * 1_100_000}
    hooks.feedback(tmp_path, {}, "fixture", result, False)
    host = next((tmp_path / "repair-feedback").iterdir())
    assert json.loads((host / "result.json").read_text()) == result
    directory = Path(next(call[1] for call in copied if call[0] == "cp"))
    assert directory == host / "agent-feedback"
    assert {path.name for path in directory.iterdir()} == {"summary.json", "pass-result"}
    assert (directory / "summary.json").stat().st_size <= 5000
    assert json.loads((directory / "summary.json").read_text())["raw"]["bytes"] > 1_000_000
