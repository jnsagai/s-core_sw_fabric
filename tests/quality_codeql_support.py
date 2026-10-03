"""Explicitly synthetic CodeQL prerequisite selections; no query engine is executed."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from tests.quality_support import PROFILE, ref, request


def write(path: Path, value: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    return path


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout.strip()


def selected(tmp_path: Path, operation: str = "capabilities") -> Path:
    source = tmp_path / "fixture-source"
    source.mkdir()
    native = {
        "LICENSE.md": "MIT fixture notice; synthetic identity only.\n",
        "docs/user_manual.md": "Synthetic manual fixture: A Python interpreter version 3.9\n",
        "scripts/reports/requirements.txt": "pyyaml==5.4\npytest==7.2.0\n",
        "scripts/configuration/requirements.txt": "pyyaml==5.4\n",
        "scripts/reports/utils.py": "# Synthetic report fixture; not executed.\n",
        "cpp/misra/src/rules/fixture.ql": "// Synthetic query identity; never executed.\n",
    }
    for name, data in native.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
    write(
        source / "supported_codeql_configs.json",
        {"supported_environment": [{"codeql_cli": "2.21.4"}]},
    )
    suite = "codeql-suites/misra-cpp-default.qls"
    suite_value = [
        {"description": "Synthetic MISRA fixture suite"},
        {"qlpack": "codeql/misra-cpp-coding-standards"},
        {"include": {"kind": ["problem", "path-problem"]}},
        {"exclude": {"tags contain": ["external/misra/audit", "external/misra/default-disabled"]}},
    ]
    write(source / "cpp/misra/src" / suite, suite_value)
    git(source, "init", "-q")
    git(source, "add", ".")
    git(
        source,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-qm",
        "Synthetic source identity fixture",
    )
    commit = git(source, "rev-parse", "HEAD")
    pack = tmp_path / "fixture-pack"
    pack.mkdir()
    write(pack / suite, suite_value)
    query = pack / "rules/fixture.ql"
    query.parent.mkdir()
    query.write_bytes((source / "cpp/misra/src/rules/fixture.ql").read_bytes())
    write(
        pack / "qlpack.yml",
        {
            "name": "codeql/misra-cpp-coding-standards",
            "version": "2.61.0",
            "license": "MIT",
            "buildMetadata": {"sha": commit, "cliVersion": "2.21.4"},
            "dependencies": {"codeql/cpp-all": "5.0.0"},
        },
    )
    write(
        pack / "codeql-pack.lock.yml",
        {"dependencies": {"codeql/cpp-all": {"version": "5.0.0"}}, "compiled": True},
    )
    interpreter = tmp_path / "fixture-cli"
    interpreter.write_text("#!/bin/sh\ntouch never-run-cli-marker\nexit 99\n")
    interpreter.chmod(0o755)
    license_file = tmp_path / "fixture-cli-license.txt"
    license_file.write_text("Synthetic CLI license identity only; no eligibility.\n")
    chain = write(
        tmp_path / "toolchain.json",
        {
            "schema_version": 1,
            "kind": "quality_codeql_toolchain_profile",
            "id": "fixture-codeql-toolchain",
            "status": "fixture_not_eligible",
            "tool": {**ref(interpreter), "version": "2.21.4"},
            "dependencies": [ref(license_file)],
            "library_dirs": [],
        },
    )
    scan = write(
        tmp_path / "scan.json",
        {"query-filters": [{"exclude": {"tags": "exclude-from-incremental"}}]},
    )
    patch = tmp_path / "report.patch"
    patch.write_text("Synthetic patch bytes; never applied by the adapter.\n")
    time_commit = "a" * 40
    lock = write(
        tmp_path / "source-lock.json",
        {
            "schema_version": 1,
            "sources": [
                {
                    "id": "codeql-coding-standards",
                    "repository": "https://github.com/github/codeql-coding-standards",
                    "commit": commit,
                    "verification": "fixture",
                    "source_file_sha256": {
                        name: ref(source / name)["sha256"]
                        for name in [
                            "LICENSE.md",
                            "docs/user_manual.md",
                            "supported_codeql_configs.json",
                        ]
                    },
                },
                {
                    "id": "time",
                    "repository": "https://github.com/eclipse-score/time",
                    "commit": time_commit,
                    "verification": "fixture",
                    "source_file_sha256": {},
                },
            ],
        },
    )
    descriptors = [
        {
            "id": key,
            "repository": "https://github.com/eclipse-score/time",
            "commit": time_commit,
            "path": name,
            "sha256": ref(path)["sha256"],
            "native_status": "synthetic fixture, never accepted",
            "license": "fixture",
            "notice": "Synthetic test bytes; no upstream or engineering authority.",
        }
        for key, path, name in [
            ("scan_config", scan, "tools/static_analysis/config.yaml"),
            ("report_patch", patch, "third_party/codeql/codeql_coding_standards_misra.patch"),
        ]
    ]
    config = write(
        tmp_path / "config.json",
        {
            "schema_version": 1,
            "kind": "quality_codeql_configuration",
            "id": "fixture-codeql-configuration",
            "status": "fixture_not_eligible",
            "source_lock": ref(lock),
            "source_root": str(source),
            "build_source_root": str(source),
            "compiled_pack_root": str(pack),
            "suite": suite,
            "scan_config": ref(scan),
            "report_patch": ref(patch),
            "native_sources": descriptors,
            "reporting_toolchain": None,
            "eligibility": None,
        },
    )
    path = request(tmp_path, "run" if operation == "run" else "capabilities")
    value = json.loads(path.read_bytes())
    value.update(
        kind=f"quality_codeql_{'run' if operation == 'run' else 'capability'}_request",
        profile=ref(PROFILE),
        toolchain=ref(chain),
        config=ref(config),
    )
    path.write_text(json.dumps(value))
    return path


def change_config(path: Path, **changes: Any) -> dict[str, Any]:
    request_value = json.loads(path.read_bytes())
    config = Path(request_value["config"]["path"])
    value = json.loads(config.read_bytes())
    value.update(changes)
    config.write_text(json.dumps(value))
    request_value["config"] = ref(config)
    path.write_text(json.dumps(request_value))
    return value
