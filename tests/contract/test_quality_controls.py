"""Live controls and native output must remain bounded and frozen through publication."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from score_sw_fabric.cli import main
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality import capabilities, complementary, runner
from score_sw_fabric.quality.models import identity_state, load_inputs
from score_sw_fabric.quality.native_outputs import diagnostics
from score_sw_fabric.quality.profile import load_profile
from tests.quality_support import complementary_request, ref, request


def local_controls(tmp_path: Path, adapter: str, operation: str) -> Path:
    path = (
        request(tmp_path, operation)
        if adapter == "clang-tidy"
        else complementary_request(tmp_path, adapter, operation)
    )
    selected = json.loads(path.read_bytes())
    (tmp_path / "controls").mkdir()
    (tmp_path / "native").mkdir()
    for key in ("profile", "toolchain", "config"):
        dest = tmp_path / "controls" / (key + ".yaml")
        dest.write_bytes(Path(selected[key]["path"]).read_bytes())
        selected[key] = ref(dest)
    if adapter in {"asan", "ubsan"}:
        config = yaml.safe_load((tmp_path / "controls/config.yaml").read_bytes())
        for key in ("native_features", "native_runtime", "native_suppressions"):
            dest = tmp_path / "native" / (key + ".txt")
            dest.write_bytes(Path(config[key]["path"]).read_bytes())
            config[key] = ref(dest)
        (tmp_path / "controls/config.yaml").write_text(yaml.safe_dump(config))
        selected["config"] = ref(tmp_path / "controls/config.yaml")
    path.write_text(json.dumps(selected))
    return path


@pytest.mark.parametrize("adapter", ["clang-tidy", "cppcheck", "asan", "ubsan"])
@pytest.mark.parametrize("operation", ["capabilities", "run"])
@pytest.mark.parametrize("target", ["request", "profile", "toolchain", "config"])
def test_changed_control_preserves_output_before_return(
    tmp_path: Path, adapter: str, operation: str, target: str
) -> None:
    path = local_controls(tmp_path, adapter, operation)
    out = tmp_path / "record.json"
    out.write_text("original output")

    def drift(selected: Any, *args: Any) -> dict[str, Any]:
        changed = path if target == "request" else tmp_path / "controls" / (target + ".yaml")
        changed.write_bytes(changed.read_bytes() + b"\n# late control drift\n")
        record = capabilities.base_record(selected, "quality_capability_inventory")
        record["gaps"].append("CAPABILITY_UNAVAILABLE")
        return record

    module = (
        (runner if operation == "run" else capabilities)
        if adapter == "clang-tidy"
        else complementary
    )
    with patch.object(module, "probe", side_effect=drift) as measured:
        code = main(
            ["quality", operation, "--adapter", adapter, "--request", str(path), "--out", str(out)]
        )
    measured.assert_called_once()
    assert code == 2
    assert out.read_text() == "original output"


@pytest.mark.parametrize("adapter", ["asan", "ubsan"])
@pytest.mark.parametrize("target", ["native_features", "native_runtime", "native_suppressions"])
def test_changed_native_runtime_control_preserves_output(
    tmp_path: Path, adapter: str, target: str
) -> None:
    path = local_controls(tmp_path, adapter, "capabilities")
    out = tmp_path / "record.json"
    out.write_text("original output")

    def drift(selected: Any, *args: Any) -> dict[str, Any]:
        changed = tmp_path / "native" / (target + ".txt")
        changed.write_bytes(changed.read_bytes() + b"\n# changed\n")
        return capabilities.base_record(selected, "quality_capability_inventory")

    with patch.object(complementary, "probe", side_effect=drift) as measured:
        assert (
            main(
                [
                    "quality",
                    "capabilities",
                    "--adapter",
                    adapter,
                    "--request",
                    str(path),
                    "--out",
                    str(out),
                ]
            )
            == 2
        )
    measured.assert_called_once()
    assert out.read_text() == "original output"


def test_missing_tool_cannot_hide_changed_dependency(tmp_path: Path) -> None:
    dependency = tmp_path / "runtime"
    dependency.write_bytes(b"reviewed runtime")
    chain = {
        "tool": {"path": str(tmp_path / "absent"), "sha256": "0" * 64},
        "dependencies": [ref(dependency)],
    }
    dependency.write_bytes(b"changed runtime")
    with pytest.raises(InputError, match="differs"):
        identity_state(chain)


@pytest.mark.parametrize(
    "raw", [b"a: &cycle [*cycle]\n", b"extra: .nan\n", b"extra: !!binary aA==\n"]
)
def test_live_profile_checks_tree_before_field_validation(raw: bytes) -> None:
    with pytest.raises(InputError) as error:
        load_profile(raw)
    assert error.value.code in {
        "LIMIT_EXCEEDED",
        "NATIVE_OUTPUT_INVALID",
        "INPUT_INVALID",
        "INVALID_YAML",
    }


@pytest.mark.parametrize(
    "raw",
    [
        b"Diagnostics: []\nextra: &cycle [*cycle]\n",
        b"Diagnostics: []\nextra: .inf\n",
        b"Diagnostics: []\nextra: !!binary aA==\n",
    ],
)
def test_live_native_yaml_refuses_invalid_tree(raw: bytes, tmp_path: Path) -> None:
    with pytest.raises(InputError):
        diagnostics(raw, "native", tmp_path, {"check.cpp": b"x"})


def test_oversize_regular_control_refuses_before_parse(tmp_path: Path) -> None:
    path = local_controls(tmp_path, "cppcheck", "capabilities")
    config = tmp_path / "controls/config.yaml"
    config.write_bytes(b"#" + b"x" * 1024 * 1024)
    record = json.loads(path.read_bytes())
    record["config"] = ref(config)
    path.write_text(json.dumps(record))
    with patch(
        "score_sw_fabric.quality.configuration.load_configuration",
        side_effect=AssertionError("parsed"),
    ):
        with pytest.raises(InputError) as error:
            load_inputs(path, "capabilities", "cppcheck")
    assert error.value.code == "LIMIT_EXCEEDED"


def test_deep_native_output_is_a_stable_refusal(tmp_path: Path) -> None:
    data = b"Diagnostics: []\nextra: " + b"[" * 80 + b"0" + b"]" * 80
    with pytest.raises(InputError) as error:
        diagnostics(data, "native", tmp_path, {"check.cpp": b"x"})
    assert error.value.code in {
        "LIMIT_EXCEEDED",
        "NATIVE_OUTPUT_INVALID",
        "INPUT_INVALID",
        "INVALID_YAML",
    }


@pytest.mark.parametrize("mutation", ["empty_id", "invalid_level", "locations"])
def test_live_diagnostics_fit_the_retained_record_contract(tmp_path: Path, mutation: str) -> None:
    message = {"Message": "fixture", "FilePath": "check.cpp", "FileOffset": 0}
    diagnostic: dict[str, Any] = {
        "DiagnosticName": "fixture/check",
        "Level": "Warning",
        "DiagnosticMessage": message,
    }
    if mutation == "empty_id":
        diagnostic["DiagnosticName"] = ""
    elif mutation == "invalid_level":
        diagnostic["Level"] = True
    else:
        diagnostic["Notes"] = [message] * 1000
    with pytest.raises(InputError):
        diagnostics(
            yaml.safe_dump({"Diagnostics": [diagnostic]}).encode(),
            "native",
            tmp_path,
            {"check.cpp": b"x"},
        )
