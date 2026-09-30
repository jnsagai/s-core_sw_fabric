from __future__ import annotations

import copy
import subprocess
from pathlib import Path

import pytest
import yaml

from score_sw_fabric.artifacts.models import (
    DEFAULT_LIMITS,
    ArtifactSemanticError,
    enforce_limit,
)
from score_sw_fabric.artifacts.native import _bounded_output
from score_sw_fabric.artifacts.reader import _validate_limits, load_artifact_inputs
from score_sw_fabric.process_source.reader import InputError
from tests.artifact_support import prepare_artifact_case, reference, sentinel

LIMIT_CODES = {
    "control_bytes": "CONTROL_SIZE_LIMIT",
    "package_bytes": "PACKAGE_SIZE",
    "target_bytes": "TARGET_SIZE_LIMIT",
    "files": "TARGET_FILE_LIMIT",
    "text_file_bytes": "TARGET_TEXT_LIMIT",
    "entities": "ARTIFACT_LIMIT",
    "obligations": "OBLIGATION_LIMIT",
    "relations": "ARTIFACT_LIMIT",
    "edits": "EDIT_LIMIT",
    "findings": "ARTIFACT_LIMIT",
    "native_output_bytes": "NATIVE_OUTPUT_LIMIT",
    "native_timeout_seconds": "ARTIFACT_LIMITS",
}
SEMANTIC_LIMITS = {"entities", "obligations", "relations", "findings"}


def test_all_declared_version_one_maxima_are_accepted_together() -> None:
    assert _validate_limits({"limits": dict(DEFAULT_LIMITS)}) == DEFAULT_LIMITS


@pytest.mark.parametrize("name", sorted(DEFAULT_LIMITS))
def test_each_declared_one_over_maximum_is_rejected_stably(name: str) -> None:
    limits = dict(DEFAULT_LIMITS)
    limits[name] += 1
    with pytest.raises(InputError) as caught:
        _validate_limits({"limits": limits})
    assert caught.value.code == "ARTIFACT_LIMITS"
    assert name in str(caught.value)


@pytest.mark.parametrize("name", sorted(DEFAULT_LIMITS))
def test_runtime_boundary_is_inclusive_and_one_over_is_rejected(name: str) -> None:
    code = LIMIT_CODES[name]
    semantic = name in SEMANTIC_LIMITS
    enforce_limit(
        DEFAULT_LIMITS,
        name,
        DEFAULT_LIMITS[name],
        code,
        f"{name} exceeded",
        semantic=semantic,
    )
    error_type = ArtifactSemanticError if semantic else InputError
    with pytest.raises(error_type) as caught:
        enforce_limit(
            DEFAULT_LIMITS,
            name,
            DEFAULT_LIMITS[name] + 1,
            code,
            f"{name} exceeded",
            semantic=semantic,
        )
    assert caught.value.code == code


def test_exact_eight_mib_native_output_is_accepted_and_one_byte_over_is_rejected() -> None:
    maximum = DEFAULT_LIMITS["native_output_bytes"]
    result = subprocess.CompletedProcess(["validator"], 0, "x" * maximum, "")
    _, _, consumed = _bounded_output(result, maximum)
    assert consumed == maximum
    one_over = subprocess.CompletedProcess(["validator"], 0, "x" * (maximum + 1), "")
    with pytest.raises(InputError) as caught:
        _bounded_output(one_over, maximum)
    assert caught.value.code == "NATIVE_OUTPUT_LIMIT"


def test_oversize_control_is_rejected_before_parsing(tmp_path: Path) -> None:
    request = tmp_path / "request.yaml"
    with request.open("wb") as stream:
        stream.truncate(DEFAULT_LIMITS["control_bytes"] + 1)
    with pytest.raises(InputError) as caught:
        load_artifact_inputs(request)
    assert caught.value.code == "CONTROL_SIZE_LIMIT"


def test_one_over_edit_limit_preserves_prior_candidate_output(tmp_path: Path) -> None:
    request, output = prepare_artifact_case(tmp_path, operation="candidate")
    prior = sentinel(output, b"prior-candidate")
    request_value = yaml.safe_load(request.read_text())
    operation = request_value["operations"][0]
    request_value["operations"] = [
        {**copy.deepcopy(operation), "id": f"edit-{index}"}
        for index in range(DEFAULT_LIMITS["edits"] + 1)
    ]
    request.write_text(yaml.safe_dump(request_value, sort_keys=False))
    from score_sw_fabric.artifacts.package import candidate_request

    with pytest.raises(InputError) as caught:
        candidate_request(request, output)
    assert caught.value.code == "EDIT_LIMIT"
    assert output.read_bytes() == prior


def test_profile_limit_reference_one_over_preserves_prior_output(tmp_path: Path) -> None:
    request, output = prepare_artifact_case(tmp_path)
    prior = sentinel(output, b"prior-index")
    profile = yaml.safe_load(Path("profiles/s_core_native_artifacts_v1.yaml").read_text())
    profile["limits"]["entities"] = DEFAULT_LIMITS["entities"] + 1
    from score_sw_fabric.compiler.reader import semantic_digest

    profile["digest"] = semantic_digest(profile)
    local = tmp_path / "profile.yaml"
    local.write_text(yaml.safe_dump(profile, sort_keys=False))
    request_value = yaml.safe_load(request.read_text())
    request_value["artifact_profile"] = reference(local, logical="profile.yaml")
    request.write_text(yaml.safe_dump(request_value, sort_keys=False))
    with pytest.raises(InputError) as caught:
        load_artifact_inputs(request)
    assert caught.value.code == "ARTIFACT_LIMITS"
    assert output.read_bytes() == prior
