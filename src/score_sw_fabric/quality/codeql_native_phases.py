"""Pure native argument recipes; callers retain execution, eligibility and identity gates."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.models import _unique_paths
from score_sw_fabric.quality.profile import load_toolchain


def extracted_units(
    rows: Any, source: Path, selected_files: list[str], units: list[str]
) -> list[str]:
    """Bind native string/url CSV entities to the frozen disposable source closure."""
    _path(source, "/extraction/source")
    files = _unique_paths(selected_files, "/extraction/files")
    expected = _unique_paths(units, "/extraction/units")
    if not set(expected).issubset(files):
        raise InputError("EXTRACTION_UNKNOWN", "Expected native units must be selected files")
    if not isinstance(rows, list) or len(rows) > 500:
        raise InputError("NATIVE_OUTPUT_INVALID", "Native extraction rows must be bounded")
    observed = set()
    for row in rows:
        if (
            not isinstance(row, list)
            or len(row) != 2
            or any(not isinstance(value, str) or len(value) > 4096 for value in row)
        ):
            raise InputError("NATIVE_OUTPUT_INVALID", "Native File entities need string and URL")
        native = Path(row[0])
        _path(native, "/extraction/file")
        try:
            name = native.relative_to(source).as_posix()
        except ValueError as exc:
            raise InputError(
                "INPUT_PATH", "Native extraction refers outside selected source"
            ) from exc
        url, *positions = row[1].rsplit(":", 4)
        if len(positions) != 4 or any(
            re.fullmatch(r"[0-9]+", value) is None for value in positions
        ):
            raise InputError("NATIVE_OUTPUT_INVALID", "Native extraction URL lacks positions")
        try:
            parsed = urlsplit(url)
        except ValueError as exc:
            raise InputError("NATIVE_OUTPUT_INVALID", "Malformed native extraction URL") from exc
        if (
            parsed.scheme != "file"
            or parsed.netloc
            or parsed.query
            or parsed.fragment
            or unquote(parsed.path) != str(native)
            or name not in files
            or name in observed
        ):
            raise InputError(
                "NATIVE_OUTPUT_INVALID", "Native extraction string/URL/closure differs"
            )
        observed.add(name)
    return sorted(observed.intersection(expected))


def _path(value: Path, pointer: str) -> str:
    if (
        not isinstance(value, Path)
        or not value.is_absolute()
        or any(part == ".." or part.startswith("-") for part in value.parts)
        or any(ord(c) < 32 or ord(c) == 127 for c in str(value))
    ):
        raise InputError("INPUT_PATH", "Native recipe requires a safe absolute path", pointer)
    return str(value)


def commands(
    *,
    cli: Path,
    compiler: dict[str, Any],
    pack: Path,
    suite: str,
    work: Path,
    units: list[str],
    include_dirs: list[str],
    defines: list[str],
    scan_config: Path,
    native_source: Path,
    reporting: dict[str, Any] | None,
    timeout_seconds: int,
    threads: int = 1,
    ram_mib: int = 2048,
) -> list[dict[str, Any]]:
    """Build the complete recipe without probing files or authorizing native execution."""
    for key, value, low, high in (
        ("timeout_seconds", timeout_seconds, 1, 3600),
        ("threads", threads, 1, 32),
        ("ram_mib", ram_mib, 1024, 8192),
    ):
        if type(value) is not int or not low <= value <= high:
            raise InputError("LIMIT_EXCEEDED", "Native resource selection is invalid", "/" + key)
    executable = _path(cli, "/cli")
    pack_path = _path(pack, "/pack")
    _path(work, "/work")
    config_path = _path(scan_config, "/scan_config")
    native_path = _path(native_source, "/native_source")
    chain = load_toolchain(
        canonical(compiler), "quality_sanitizer_toolchain_profile", check_paths=False
    )
    cxx = _path(Path(chain["tool"]["path"]), "/compiler")
    if (
        not isinstance(suite, str)
        or re.fullmatch(r"codeql-suites/[A-Za-z0-9][A-Za-z0-9_.-]*\.qls", suite) is None
    ):
        raise InputError("INPUT_PATH", "Native suite must be explicitly selected")
    unit_names = _unique_paths(units, "/translation_units")
    include_names = _unique_paths(include_dirs, "/include_dirs", 32)
    if not unit_names or any(
        Path(name).suffix not in {".cpp", ".cc", ".cxx"} for name in unit_names
    ):
        raise InputError("INPUT_PATH", "Native trace units must be C++ source files")
    for name in [*unit_names, *include_names]:
        if any(part.startswith("-") for part in Path(name).parts) or any(
            ord(c) < 32 or ord(c) == 127 for c in name
        ):
            raise InputError("INPUT_PATH", "Native source names cannot contain options or controls")
    if (
        not isinstance(defines, list)
        or len(defines) > 64
        or any(
            not isinstance(value, str)
            or len(value) > 256
            or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:=-?[0-9]+)?", value) is None
            for value in defines
        )
    ):
        raise InputError("FIELD_TYPE", "Only bounded identifier/integer defines are supported")
    python = None
    if reporting is not None:
        report_chain = load_toolchain(
            canonical(reporting), "quality_codeql_reporting_toolchain_profile", check_paths=False
        )
        if re.fullmatch(r"Python 3\.9\.[0-9]+", report_chain["tool"]["version"]) is None:
            raise InputError("VERSION_UNSUPPORTED", "Native reporting requires selected Python 3.9")
        python = _path(Path(report_chain["tool"]["path"]), "/reporting")
    source = str(work / "source")
    database = str(work / "database")
    sarif = str(work / "results.sarif")
    csv = str(work / "results.csv")
    selector = "codeql/misra-cpp-coding-standards@2.61.0:" + suite
    resources = [f"--threads={threads}", f"--ram={ram_mib}"]
    result: list[dict[str, Any]] = []

    def add(name: str, argv: list[str] | None) -> None:
        result.append(
            {
                "name": name,
                "argv": argv,
                "timeout_seconds": timeout_seconds,
                "state": "planned" if argv is not None else "unavailable",
                "reason_codes": [] if argv is not None else ["REPORTING_INTERPRETER_NOT_SELECTED"],
            }
        )

    add("version", [executable, "version", "--format=json"])
    add(
        "database:init",
        [
            executable,
            "database",
            "init",
            "--language=cpp",
            "--build-mode=manual",
            "--source-root=" + source,
            "--codescanning-config=" + config_path,
            "--",
            database,
        ],
    )
    add(
        "configuration:convert",
        [
            python,
            native_path + "/scripts/configuration/process_coding_standards_config.py",
            "--skip-indexing",
            "--save-temps",
            "--working-dir=" + source,
        ]
        if python is not None
        else None,
    )
    add(
        "configuration:index",
        [
            executable,
            "database",
            "index-files",
            *resources,
            "--language=xml",
            "--include=**/coding-standards.xml",
            "--size-limit=10m",
            "--working-dir=" + source,
            "--",
            database,
        ],
    )
    for index, name in enumerate(unit_names):
        add(
            "database:trace:" + name,
            [
                executable,
                "database",
                "trace-command",
                *resources,
                "--",
                database,
                cxx,
                "-std=c++17",
                *["-I" + source + "/" + value for value in include_names],
                *["-D" + value for value in defines],
                "-c",
                source + "/" + name,
                "-o",
                str(work / f"object-{index}.o"),
            ],
        )
    add("database:finalize", [executable, "database", "finalize", *resources, "--", database])
    add(
        "database:queries",
        [
            executable,
            "database",
            "run-queries",
            *resources,
            "--search-path=" + pack_path,
            "--",
            database,
            selector,
        ],
    )
    for name, format_name, output in (("sarif", "sarifv2.1.0", sarif), ("csv", "csv", csv)):
        add(
            "database:interpret:" + name,
            [
                executable,
                "database",
                "interpret-results",
                "--search-path=" + pack_path,
                "--format=" + format_name,
                "--output=" + output,
                "--",
                database,
                selector,
            ],
        )
    add(
        "native:report",
        [
            python,
            native_path + "/scripts/reports/analysis_report.py",
            database,
            sarif,
            str(work / "native-reports"),
        ]
        if python is not None
        else None,
    )
    return result
