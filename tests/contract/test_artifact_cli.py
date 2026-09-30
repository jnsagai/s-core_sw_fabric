from __future__ import annotations

import json
from pathlib import Path

from score_sw_fabric.cli import main
from tests.artifact_support import prepare_artifact_case


def test_public_index_candidate_validate_exit_semantics(tmp_path: Path, capsys: object) -> None:
    index_request, index_output = prepare_artifact_case(tmp_path / "index")
    assert (
        main(
            [
                "artifact",
                "index",
                "--request",
                str(index_request),
                "--out",
                str(index_output),
                "--json",
            ]
        )
        == 0
    )
    candidate_request, candidate_output = prepare_artifact_case(
        tmp_path / "candidate", operation="candidate"
    )
    assert (
        main(
            [
                "artifact",
                "candidate",
                "--request",
                str(candidate_request),
                "--out",
                str(candidate_output),
                "--json",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "artifact",
                "validate",
                "--candidate",
                str(candidate_output),
                "--profile",
                "profiles/s_core_native_artifacts_v1.yaml",
                "--json",
            ]
        )
        == 0
    )
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert "not_evaluated" in captured.out


def test_public_trace_publishes_bounded_blocked_report(tmp_path: Path, capsys: object) -> None:
    request, output = prepare_artifact_case(tmp_path, operation="trace")
    status = main(["artifact", "trace", "--request", str(request), "--out", str(output), "--json"])
    assert status in {0, 1}
    assert output.is_file()
    report = json.loads(output.read_text())
    assert report["status"] in {"passed", "blocked"}
    capsys.readouterr()  # type: ignore[attr-defined]
