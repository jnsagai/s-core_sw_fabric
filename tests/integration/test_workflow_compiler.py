from __future__ import annotations

from pathlib import Path

from score_sw_fabric.compiler.package import compile_package
from score_sw_fabric.compiler.reader import load_compiler_inputs
from tests.compiler_support import RecordingValidator, prepare_case


def test_linear_and_shared_review_journeys_are_deterministic(tmp_path: Path) -> None:
    identities = []
    for scenario in ("linear", "shared-parallel-review"):
        request, _ = prepare_case(tmp_path / scenario, scenario)
        inputs = load_compiler_inputs(request)
        before = {path: path.read_bytes() for path in inputs.input_paths}
        first = compile_package(inputs, native_validator=RecordingValidator())
        second = compile_package(inputs, native_validator=RecordingValidator())
        assert first == second
        assert {path: path.read_bytes() for path in inputs.input_paths} == before
        identities.append(first["manifest"]["package_identity"])
        if scenario == "shared-parallel-review":
            assert len(first["manifest"]["ir"]["gates"]) == 1
            assert first["manifest"]["ir"]["gates"][0]["subjects"] == [
                "obligation-a",
                "obligation-b",
            ]
    assert identities[0] != identities[1]
