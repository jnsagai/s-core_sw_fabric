"""Native command construction must be bounded, pure and explicit about missing reporting."""

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml

from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.codeql_native_phases import commands, extracted_units

ROOT = Path(__file__).resolve().parents[2]


def inputs() -> dict[str, Any]:
    return {
        "cli": Path("/installed/codeql"),
        "compiler": yaml.safe_load((ROOT / "profiles/gcc11-sanitizers-local-v1.yaml").read_bytes()),
        "pack": Path("/installed/pack"),
        "suite": "codeql-suites/misra-cpp-default.qls",
        "work": Path("/disposable/work"),
        "units": ["check.cpp"],
        "include_dirs": ["headers"],
        "defines": ["TEST=1"],
        "scan_config": Path("/disposable/work/native-scan.yaml"),
        "native_source": Path("/disposable/work/native"),
        "reporting": None,
        "timeout_seconds": 30,
        "threads": 1,
        "ram_mib": 2048,
    }


def test_native_missing_reporting_is_explicit_and_construction_is_pure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = inputs()
    with monkeypatch.context() as guard:
        guard.setattr(Path, "open", lambda *a, **k: pytest.fail("host file read"))
        guard.setattr(Path, "stat", lambda *a, **k: pytest.fail("host path probe"))
        result = commands(**selected)
    missing = [p for p in result if p["state"] == "unavailable"]
    assert {p["name"] for p in missing} == {"configuration:convert", "native:report"}
    assert all(
        p["argv"] is None and p["reason_codes"] == ["REPORTING_INTERPRETER_NOT_SELECTED"]
        for p in missing
    )
    assert any(p["name"] == "database:queries" for p in result)
    assert all(
        set(p) == {"name", "argv", "timeout_seconds", "state", "reason_codes"} for p in result
    )


@pytest.mark.parametrize(
    "key,value",
    [
        ("units", []),
        ("units", ["../outside.cpp"]),
        ("units", ["-plugin.cpp"]),
        ("units", ["check.cpp", "check.cpp"]),
        ("units", ["check.py"]),
        ("units", ["unit" + str(i) + ".cpp" for i in range(501)]),
        ("defines", ["VALUE=$(touch marker)"]),
        ("defines", ["-include=/outside"]),
        ("include_dirs", ["../headers"]),
        ("suite", "../other.qls"),
        ("suite", "codeql-suites/-option.qls"),
        ("work", Path("relative")),
        ("pack", Path("/installed/../other")),
        ("cli", Path("/installed/-codeql")),
        ("threads", True),
        ("threads", 0),
        ("threads", 33),
        ("ram_mib", 1023),
        ("ram_mib", 8193),
        ("timeout_seconds", 0),
        ("timeout_seconds", 3601),
    ],
)
def test_native_unsafe_or_unbounded_recipe_refuses(key: str, value: Any) -> None:
    selected = inputs()
    selected[key] = value
    with pytest.raises(InputError):
        commands(**selected)


def test_native_compiler_identity_shape_and_reporting_version_are_checked() -> None:
    selected = inputs()
    broken = deepcopy(selected["compiler"])
    broken["tool"]["sha256"] = "unverified"
    selected["compiler"] = broken
    with pytest.raises(InputError):
        commands(**selected)
    selected = inputs()
    reporting = deepcopy(selected["compiler"])
    reporting["kind"] = "quality_codeql_reporting_toolchain_profile"
    reporting["tool"]["version"] = "3.12"
    selected["reporting"] = reporting
    with pytest.raises(InputError):
        commands(**selected)


def test_native_source_names_with_spaces_remain_single_arguments() -> None:
    selected = inputs()
    selected["units"] = ["source with spaces.cpp"]
    result = commands(**selected)
    traced = next(p for p in result if p["name"].startswith("database:trace:"))
    assert "/disposable/work/source/source with spaces.cpp" in traced["argv"]
    assert not any("sh -c" in arg for p in result for arg in (p["argv"] or []))


def test_native_declared_reporting_uses_existing_profile_version_convention() -> None:
    selected = inputs()
    reporting = deepcopy(selected["compiler"])
    reporting["kind"] = "quality_codeql_reporting_toolchain_profile"
    reporting["tool"]["version"] = "Python 3.9.25"
    selected["reporting"] = reporting
    result = commands(**selected)
    assert all(p["state"] == "planned" for p in result)
    conversion = next(p for p in result if p["name"] == "configuration:convert")
    assert "--skip-indexing" in conversion["argv"] and "--save-temps" in conversion["argv"]
    indexing = next(p for p in result if p["name"] == "configuration:index")
    assert "--threads=1" in indexing["argv"] and "--ram=2048" in indexing["argv"]
    # Declared identity alone never executes or qualifies this candidate interpreter.


def test_native_extraction_absolute_string_and_url_bind_to_selected_source() -> None:
    rows = [["/copy/source/check.cpp", "file:///copy/source/check.cpp:0:0:0:0"]]
    assert extracted_units(rows, Path("/copy/source"), ["check.cpp"], ["check.cpp"]) == [
        "check.cpp"
    ]
    spaces = [["/copy/source/a b.cpp", "file:///copy/source/a%20b.cpp:0:0:0:0"]]
    assert extracted_units(spaces, Path("/copy/source"), ["a b.cpp"], ["a b.cpp"]) == ["a b.cpp"]


@pytest.mark.parametrize(
    "rows",
    [
        [["/outside/check.cpp", "file:///outside/check.cpp:0:0:0:0"]],
        [["/copy/source/other.cpp", "file:///copy/source/other.cpp:0:0:0:0"]],
        [["/copy/source/check.cpp", "file:///outside/check.cpp:0:0:0:0"]],
        [["/copy/source/check.cpp", "https://example.invalid/check.cpp"]],
        [["/copy/source/check.cpp", "file://[unterminated/check.cpp:0:0:0:0"]],
        [["/copy/source/check.cpp", "file:///copy/source/check.cpp:0:0:0:0", "extra"]],
        [["/copy/source/check.cpp", "file:///copy/source/check.cpp:0:0:0:0"]] * 2,
        [None],
        "not rows",
    ],
)
def test_native_extraction_refuses_unselected_or_contradictory_rows(rows: Any) -> None:
    with pytest.raises(InputError):
        extracted_units(rows, Path("/copy/source"), ["check.cpp"], ["check.cpp"])
