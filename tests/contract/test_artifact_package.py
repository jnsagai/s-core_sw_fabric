from __future__ import annotations

from pathlib import Path

import pytest

from score_sw_fabric.artifacts.models import ArtifactSemanticError
from score_sw_fabric.artifacts.package import candidate_request, load_profile, validate_candidate
from score_sw_fabric.process_source.reader import InputError
from tests.artifact_support import prepare_artifact_case, sentinel


def test_candidate_is_sealed_complete_and_trace_is_not_claimed(tmp_path: Path) -> None:
    request, output = prepare_artifact_case(tmp_path, operation="candidate")
    candidate = candidate_request(request, output)
    assert output.is_file()
    assert candidate["trace_validation"] == "not_requested"
    assert candidate["report"] is None
    assert candidate["overlay_files"][0]["content"]
    profile = load_profile(Path("profiles/s_core_native_artifacts_v1.yaml"))
    assert validate_candidate(candidate, profile)["valid"] is True


def test_failed_candidate_preserves_prior_output(tmp_path: Path) -> None:
    request, output = prepare_artifact_case(tmp_path, operation="candidate")
    expected = sentinel(output)
    text = request.read_text().replace(
        "expected_preimage: ", "expected_preimage: " + "0" * 64 + " # ", 1
    )
    request.write_text(text)
    with pytest.raises((ArtifactSemanticError, InputError)):
        candidate_request(request, output)
    assert output.read_bytes() == expected


def test_explicit_trace_candidate_attaches_matching_report() -> None:
    from score_sw_fabric.process_source.reader import read_json

    request = Path("tests/fixtures/artifacts/component/update-and-trace-request.yaml")
    output = Path("tests/fixtures/artifacts/out/component-trace-candidate.json")
    candidate = candidate_request(request, output)
    assert candidate["trace_validation"] == "passed"
    assert candidate["report"]["status"] == "passed"
    assert candidate["report"]["bindings"]["index"] == candidate["index"]["digest"]
    assert candidate["capabilities"]["engineering_readiness"] == "not_evaluated"
    assert read_json(output) == candidate


def test_resealed_trace_report_with_wrong_index_is_rejected() -> None:
    from copy import deepcopy

    from score_sw_fabric.compiler.reader import semantic_digest
    from score_sw_fabric.process_source.reader import read_json

    candidate = deepcopy(
        read_json(Path("tests/fixtures/artifacts/out/component-trace-candidate.json"))
    )
    candidate["report"]["bindings"]["index"] = "0" * 64
    candidate["report"]["digest"] = semantic_digest(candidate["report"])
    candidate["digest"] = semantic_digest(candidate)
    with pytest.raises(InputError, match="bindings"):
        validate_candidate(
            candidate, load_profile(Path("profiles/s_core_native_artifacts_v1.yaml"))
        )


def test_explicit_blocked_candidate_trace_preserves_prior_output() -> None:
    request = Path("tests/fixtures/artifacts/invalid/missing-verification/candidate-request.yaml")
    output = Path("tests/fixtures/artifacts/out/missing-verification-candidate.json")
    expected = sentinel(output)
    try:
        with pytest.raises(ArtifactSemanticError, match="unresolved obligations"):
            candidate_request(request, output)
        assert output.read_bytes() == expected
    finally:
        output.unlink()
