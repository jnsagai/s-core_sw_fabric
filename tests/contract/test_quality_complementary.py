"""Strict mode/config/native XML contracts and publication preflight."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from score_sw_fabric.cli import main
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.complementary import capabilities
from score_sw_fabric.quality.cppcheck import parse_report
from score_sw_fabric.quality.models import load_inputs
from tests.quality_support import ROOT, complementary_request, ref


@pytest.mark.parametrize("adapter", ["cppcheck", "asan", "ubsan"])
def test_kind_and_adapter_must_match(adapter: str, tmp_path: Path) -> None:
    path = complementary_request(tmp_path, adapter)
    with pytest.raises(InputError):
        load_inputs(path, "run")
    out = tmp_path / "out.json"
    out.write_text("prior")
    assert (
        main(["quality", "run", "--adapter", adapter, "--request", str(path), "--out", str(path)])
        == 2
    )
    assert out.read_text() == "prior"


def test_cppcheck_rejects_unsafe_or_unresearched_configuration(tmp_path: Path) -> None:
    cfg = yaml.safe_load((ROOT / "profiles/cppcheck-cpp17-local-v1.yaml").read_bytes())
    path = tmp_path / "config.yaml"
    for key, value in [
        ("enable", ["all", "misra"]),
        ("xml_version", 1),
        ("max_configs", True),
        ("error_exitcode", 0),
        ("language", "c"),
        ("extra_flags", ["--addon=x"]),
    ]:
        path.write_text(yaml.safe_dump(dict(cfg, **{key: value})))
        with pytest.raises(InputError):
            load_inputs(
                complementary_request(tmp_path, "cppcheck", config=ref(path)), "run", "cppcheck"
            )


def test_sanitizer_mode_and_native_identity_are_exact(tmp_path: Path) -> None:
    cfg = yaml.safe_load((ROOT / "profiles/asan-gcc11-local-v1.yaml").read_bytes())
    custom = tmp_path / "config.yaml"
    for key, value in [
        ("mode", "asan+tsan"),
        ("feature", "ubsan_clang"),
        ("native_runtime", {"path": cfg["native_runtime"]["path"], "sha256": "0" * 64}),
    ]:
        custom.write_text(yaml.safe_dump(dict(cfg, **{key: value})))
        with pytest.raises(InputError):
            load_inputs(complementary_request(tmp_path, "asan", config=ref(custom)), "run", "asan")


def test_xml_native_identity_all_locations_and_entities(tmp_path: Path) -> None:
    data = b'<results version="2"><cppcheck version="2.7"/><errors>'
    data += b'<error id="nullPointer" severity="error" msg="Null pointer" cwe="476">'
    data += b'<location file="check.cpp" line="3" column="12" info="primary"/>'
    data += b'<location file="check.cpp" line="2" column="5" info="related"/>'
    data += b"</error></errors></results>"
    result = parse_report(data, "report", tmp_path, {"check.cpp": b"x\nx\nx\n"}, "2.7")
    assert result[0]["native_id"] == "nullPointer"
    assert result[0]["native_record"]["attributes"]["cwe"] == "476"
    assert len(result[0]["locations"]) == 2
    for bad in (
        b'<!DOCTYPE x><results version="2"/>',
        '<!DOCTYPE x><results version="2"/>'.encode("utf-16"),
        data.replace(b'version="2"', b'version="1"'),
        data.replace(b"check.cpp", b"/other/check.cpp"),
        data.replace(b'line="3"', b'line="99"'),
        data.replace(b'version="2.7"', b'version="0"'),
    ):
        with pytest.raises(InputError):
            parse_report(bad, "report", tmp_path, {"check.cpp": b"x\nx\nx\n"}, "2.7")


def test_output_alias_is_rejected_before_build(tmp_path: Path) -> None:
    p = complementary_request(tmp_path, "asan")
    with patch(
        "score_sw_fabric.quality.sanitizers.build_and_execute",
        side_effect=AssertionError("executed"),
    ):
        record = json.loads(p.read_text())
        record["expected_units"] = None
        p.write_text(json.dumps(record))
        # Preflight an unsafe output before any build/runtime probe.
        assert (
            main(["quality", "run", "--adapter", "asan", "--request", str(p), "--out", str(p)]) == 2
        )


def test_sanitizer_unapproved_suppression_stays_blocked(tmp_path: Path) -> None:
    suppression = tmp_path / "asan.supp"
    suppression.write_text("interceptor_via_fun:unreviewed_function\n")
    profile = yaml.safe_load((ROOT / "profiles/s-core-quality-v1.yaml").read_bytes())
    for source in profile["native_sources"]:
        if source["id"] == "asan_suppressions":
            source["sha256"] = ref(suppression)["sha256"]
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(yaml.safe_dump(profile))
    config = yaml.safe_load((ROOT / "profiles/asan-gcc11-local-v1.yaml").read_bytes())
    config["native_suppressions"] = ref(suppression)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config))
    path = complementary_request(
        tmp_path, "asan", "capabilities", profile=ref(profile_path), config=ref(config_path)
    )
    code, record, _, _ = capabilities(path, "asan")
    assert code == 1 and record["capability"]["state"] != "available"
    assert "UNAPPROVED_SUPPRESSION" in record["gaps"]
    assert [p["name"] for p in record["phases"]] == ["version"]


def test_missing_selected_runtime_is_unavailable(tmp_path: Path) -> None:
    config = yaml.safe_load((ROOT / "profiles/gcc11-sanitizers-local-v1.yaml").read_bytes())
    config["dependencies"][0] = {"path": str(tmp_path / "missing-runtime"), "sha256": "0" * 64}
    chain = tmp_path / "chain.yaml"
    chain.write_text(yaml.safe_dump(config))
    path = complementary_request(tmp_path, "ubsan", "capabilities", toolchain=ref(chain))
    with patch("score_sw_fabric.quality.complementary.execute", side_effect=AssertionError):
        code, record, _, _ = capabilities(path, "ubsan")
    assert code == 1 and record["capability"]["state"] == "unavailable"
    assert "CAPABILITY_UNAVAILABLE" in record["gaps"]
