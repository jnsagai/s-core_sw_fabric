"""Refuse malformed selections and output aliases before analyzer execution."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from score_sw_fabric.cli import main
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.models import load_inputs
from tests.quality_support import request


@pytest.mark.parametrize(
    "changes",
    [
        {"extra": True},
        {"timeout_seconds": True},
        {"timeout_seconds": 0},
        {"timeout_seconds": 3601},
        {"output_limit_bytes": 1},
        {"output_limit_bytes": 16777217},
        {"defines": ["X;touch bad"]},
        {"include_dirs": ["../external"]},
        {"translation_units": ["check.cpp", "check.cpp"]},
        {"files": []},
        {"expected_units": ["missing.cpp"]},
    ],
)
def test_bad_inputs(changes: dict[str, object], tmp_path: Path) -> None:
    with pytest.raises(InputError):
        load_inputs(request(tmp_path, **changes), "run")


def test_duplicate_and_drift(tmp_path: Path) -> None:
    path = request(tmp_path)
    original = path.read_text()
    path.write_text(
        original.replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1')
    )
    with pytest.raises(InputError):
        load_inputs(path, "run")
    path.write_text(original)
    (tmp_path / "component/check.cpp").write_text("changed")
    with pytest.raises(InputError, match="changed"):
        load_inputs(path, "run")


def test_linked_source(tmp_path: Path) -> None:
    path = request(tmp_path)
    source = tmp_path / "component/check.cpp"
    moved = tmp_path / "source.cpp"
    source.rename(moved)
    source.symlink_to(moved)
    with pytest.raises(InputError):
        load_inputs(path, "run")


def test_rejected_cli_preserves_output_and_preflights_alias(tmp_path: Path) -> None:
    out = tmp_path / "out.json"
    out.write_text("old")
    path = request(tmp_path, extra=True)
    assert main(["quality", "run", "--request", str(path), "--out", str(out)]) == 2
    assert out.read_text() == "old"
    path = request(tmp_path)
    with patch(
        "score_sw_fabric.quality.capabilities.probe", side_effect=AssertionError("executed")
    ):
        assert main(["quality", "run", "--request", str(path), "--out", str(path)]) == 2
        source = tmp_path / "component/out.json"
        assert main(["quality", "run", "--request", str(path), "--out", str(source)]) == 2


def test_request_schemas_match_readers() -> None:
    from score_sw_fabric.quality.models import CAPABILITY_FIELDS, RUN_FIELDS
    from tests.quality_support import ROOT

    for name, fields in [("capability", CAPABILITY_FIELDS), ("run", RUN_FIELDS)]:
        schema = json.loads((ROOT / f"schemas/quality-{name}-request.schema.json").read_text())
        assert set(schema["required"]) == {"schema_version", "kind", *fields}
        assert schema["additionalProperties"] is False


def test_tool_drift_missing_and_version_mismatch(tmp_path: Path) -> None:
    import yaml

    from score_sw_fabric.quality.capabilities import capabilities
    from tests.quality_support import TOOLCHAIN, ref

    chain = yaml.safe_load(TOOLCHAIN.read_bytes())
    custom = tmp_path / "toolchain.yaml"
    custom.write_text(yaml.safe_dump(chain))
    chain["tool"]["sha256"] = "0" * 64
    custom.write_text(yaml.safe_dump(chain))
    out = tmp_path / "out.json"
    out.write_text("previous")
    path = request(tmp_path, "capabilities", toolchain=ref(custom))
    assert main(["quality", "capabilities", "--request", str(path), "--out", str(out)]) == 2
    assert out.read_text() == "previous"
    chain["tool"]["path"] = str(tmp_path / "missing-clang-tidy")
    custom.write_text(yaml.safe_dump(chain))
    code, record, _, _ = capabilities(request(tmp_path, "capabilities", toolchain=ref(custom)))
    assert code == 1 and record["capability"]["state"] == "unavailable"
    chain = yaml.safe_load(TOOLCHAIN.read_bytes())
    chain["tool"]["version"] = "wrong version"
    custom.write_text(yaml.safe_dump(chain))
    with pytest.raises(InputError, match="Version"):
        capabilities(request(tmp_path, "capabilities", toolchain=ref(custom)))


def test_config_bytes_and_source_includes_are_confined(tmp_path: Path) -> None:
    from tests.quality_support import CONFIG, ref

    custom = tmp_path / "config.yaml"
    custom.write_bytes(CONFIG.read_bytes() + b"\nChecks: '*'\n")
    with pytest.raises(InputError):
        load_inputs(request(tmp_path, config=ref(custom)), "run")
    request(tmp_path)
    (tmp_path / "component/check.cpp").write_text('#include "/tmp/host.h"\nint main() {return 0;}')
    with pytest.raises(InputError):
        load_inputs(request(tmp_path), "run")


def test_profile_fields_types_and_gap_defaults(tmp_path: Path) -> None:
    import yaml

    from score_sw_fabric.quality.profile import load_profile, load_toolchain
    from tests.quality_support import PROFILE, TOOLCHAIN

    p = yaml.safe_load(PROFILE.read_bytes())
    for name, value in [
        ("mapping_state", "supplied"),
        ("decision_policy_ref", {}),
        ("language", "c++23"),
        ("native_sources", []),
        ("required_obligations", 3),
    ]:
        changed = dict(p, **{name: value})
        with pytest.raises(InputError):
            load_profile(yaml.safe_dump(changed).encode())
    chain = yaml.safe_load(TOOLCHAIN.read_bytes())
    chain["dependencies"] *= 2
    with pytest.raises(InputError):
        load_toolchain(yaml.safe_dump(chain).encode())
