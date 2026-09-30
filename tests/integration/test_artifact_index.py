from __future__ import annotations

from pathlib import Path

from score_sw_fabric.artifacts.package import index_request
from tests.artifact_support import prepare_artifact_case


def test_index_relocation_is_byte_identical(tmp_path: Path) -> None:
    request_a, output_a = prepare_artifact_case(tmp_path / "a")
    request_b, output_b = prepare_artifact_case(tmp_path / "b")
    first = index_request(request_a, output_a)
    second = index_request(request_b, output_b)
    assert first == second
    assert output_a.read_bytes() == output_b.read_bytes()
