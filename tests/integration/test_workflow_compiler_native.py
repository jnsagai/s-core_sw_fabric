from __future__ import annotations

import os
from pathlib import Path

import pytest

from score_sw_fabric.compiler.package import compile_package
from score_sw_fabric.compiler.reader import load_compiler_inputs
from tests.compiler_support import prepare_case


@pytest.mark.parametrize("scenario", ["linear", "shared-parallel-review", "bounded-correction"])
def test_representative_package_passes_pinned_fabro(tmp_path: Path, scenario: str) -> None:
    binary = os.environ.get("SCORE_FABRO_BIN")
    if not binary:
        pytest.fail("SCORE_FABRO_BIN is required; a skip is ineligible for 003 acceptance")
    request, _ = prepare_case(tmp_path, scenario)
    package = compile_package(load_compiler_inputs(request))
    assert package["native_validation"]["accepted"] is True
    assert package["compile_report"]["capabilities"]["execution"] == "not_evaluated"
