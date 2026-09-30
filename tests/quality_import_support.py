"""Explicitly labelled synthetic import selections; no native execution claim."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

from score_sw_fabric.assurance.models import digest, seal, verify_digest
from score_sw_fabric.catalog.export import canonical
from tests.quality_support import PROFILE, ROOT, ref


def identity(tool: str = "codeql") -> dict[str, Any]:
    return {
        "id": tool,
        "name": "CodeQL" if tool == "codeql" else "Cppcheck",
        "version": "2.21.4" if tool == "codeql" else "2.7",
        "tool_sha256": "1" * 64,
        "config_sha256": "2" * 64,
        "query_pack": {"name": "fixture-pack", "version": "2.61.0", "sha256": "3" * 64}
        if tool == "codeql"
        else None,
        "suite": {"name": "fixture-suite", "sha256": "4" * 64} if tool == "codeql" else None,
        "libraries": [],
        "license": "synthetic fixture",
        "notice": "No executable/pack copied",
    }


def sarif(results: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "CodeQL",
                        "semanticVersion": "2.21.4",
                        "rules": [
                            {"id": "fixture/check", "defaultConfiguration": {"level": "error"}}
                        ],
                    },
                    "extensions": [{"name": "fixture-pack", "semanticVersion": "2.61.0"}],
                },
                "results": results
                if results is not None
                else [
                    {
                        "ruleIndex": 0,
                        "message": {"text": "Synthetic defect"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": "check.cpp"},
                                    "region": {"startLine": 2, "startColumn": 1},
                                }
                            }
                        ],
                        "partialFingerprints": {"fixture/v1": "same"},
                    }
                ],
            }
        ],
    }


def write_json(path: Path, record: Any) -> dict[str, str]:
    path.write_text(json.dumps(record))
    return ref(path)


def selection(
    tmp: Path,
    *,
    expected: Any = ("check.cpp",),
    origin: str = "fixture",
    native: dict[str, Any] | None = None,
) -> Path:
    component = tmp / "source"
    component.mkdir(exist_ok=True)
    (component / "check.cpp").write_text("// synthetic\nint main() { return 0; }\n")
    files = [{"path": "check.cpp", "sha256": ref(component / "check.cpp")["sha256"]}]
    expected = list(expected) if expected is not None else None
    source_digest = hashlib.sha256(
        canonical({"component": "fixture_component", "files": files, "expected_units": expected})
    ).hexdigest()
    ident = identity()
    baseline = seal(
        {
            "schema_version": 1,
            "kind": "quality_import_baseline",
            "component": "fixture_component",
            "root": str(component),
            "files": files,
            "expected_units": expected,
            "identities": [ident],
        }
    )
    bindings = {
        "source_digest": source_digest,
        "profile_sha256": ref(PROFILE)["sha256"],
        "identity_digest": digest(ident),
    }
    artifact = {
        "id": "analysis",
        "tool": "codeql",
        "format": "sarif-2.1.0",
        "role": "diagnostics",
        "ref": write_json(tmp / "analysis.sarif", native or sarif()),
        "source_root": "/native/source",
        "units": ["check.cpp"],
        "bindings": bindings,
    }
    artifacts = [artifact]
    reports = [
        "database_integrity_report.md",
        "deviations_report.md",
        "guideline_recategorizations_report.md",
        "guideline_compliance_summary.md",
    ]
    for name in reports:
        path = tmp / name
        path.write_text(
            "# Database integrity report\n - 0 errors reported\n"
            " - 1 successfully analyzed files\n## Successfully extracted files\n - check.cpp\n"
            if name == reports[0]
            else "Synthetic fixture. Compliant. approved-by: agent\n"
        )
        artifacts.append(
            {
                **artifact,
                "id": name,
                "format": "text",
                "role": "supporting",
                "units": [],
                "ref": ref(path),
            }
        )
    phases = [
        {
            "id": "extract",
            "role": "extract",
            "status": "completed",
            "exit_code": 0,
            "timed_out": False,
            "artifacts": [reports[0]],
        },
        {
            "id": "analyze",
            "role": "analyze",
            "status": "completed",
            "exit_code": 0,
            "timed_out": False,
            "artifacts": ["analysis"],
        },
        {
            "id": "reports",
            "role": "report",
            "status": "completed",
            "exit_code": 0,
            "timed_out": False,
            "artifacts": reports,
        },
    ]
    manifest = seal(
        {
            "schema_version": 1,
            "kind": "quality_extraction_manifest",
            "source_digest": source_digest,
            "outer_exit_code": 0,
            "observations": [
                {
                    "tool": "codeql",
                    "identity_digest": digest(ident),
                    "processed_units": ["check.cpp"],
                    "extracted_units": ["check.cpp"],
                    "exclusions": [],
                    "warnings": [],
                    "errors": [],
                    "failed_queries": [],
                    "filtered_checks": [],
                    "required_reports": reports,
                    "phases": phases,
                }
            ],
        }
    )
    request = {
        "schema_version": 1,
        "kind": "quality_import_request",
        "profile": ref(PROFILE),
        "baseline": write_json(tmp / "baseline.json", baseline),
        "artifacts": artifacts,
        "extraction": write_json(tmp / "extraction.json", manifest),
        "origin": origin,
        "protected_roots": [str(ROOT)],
    }
    path = tmp / "request.json"
    path.write_text(json.dumps(request))
    return path


def change_manifest(request: Path, **changes: Any) -> None:
    r = json.loads(request.read_text())
    path = Path(r["extraction"]["path"])
    m = json.loads(path.read_text())
    m["observations"][0].update(changes)
    r["extraction"] = write_json(path, seal(m))
    request.write_text(json.dumps(r))


def from_local_run(tmp: Path, adapter: str, record: dict[str, Any], source: Path) -> Path:
    """Derive declared import bindings, retaining the genuine original run as a raw log."""
    verify_digest(record, "/run")
    chain = record["toolchain"]
    ident = {
        "id": adapter,
        "name": adapter,
        "version": chain["tool"]["version"],
        "tool_sha256": chain["tool"]["sha256"],
        "config_sha256": record["baseline"]["configuration"]["sha256"],
        "query_pack": None,
        "suite": None,
        "libraries": [
            {"name": Path(d["path"]).name, "version": "not_reported", "sha256": d["sha256"]}
            for d in chain["dependencies"]
        ],
        "license": "See selected distribution copyright/license assets",
        "notice": "Original toolchain and native profile notices retained in original-analysis-run",
    }
    files = record["baseline"]["files"]
    expected = record["baseline"]["expected_units"]
    component = record["baseline"]["component"]
    baseline = seal(
        {
            "schema_version": 1,
            "kind": "quality_import_baseline",
            "component": component,
            "root": str(source),
            "files": files,
            "expected_units": expected,
            "identities": [ident],
        }
    )
    bindings = {
        "source_digest": digest(
            {"component": component, "files": files, "expected_units": expected}
        ),
        "profile_sha256": ref(PROFILE)["sha256"],
        "identity_digest": digest(ident),
    }
    source_arg = next(
        arg
        for p in record["phases"]
        if not p["name"].startswith("probe:")
        for arg in p["argv"]
        if arg.endswith("/check.cpp")
    )
    native_root = str(Path(source_arg).parent)
    artifacts = []
    for raw in record["artifacts"]:
        if raw["id"].startswith("probe-"):
            continue
        fp = tmp / (raw["id"] + ".native")
        fp.write_bytes(base64.b64decode(raw["base64"]))
        artifacts.append(
            {
                "id": raw["id"],
                "tool": adapter,
                "format": raw["format"],
                "role": "diagnostics",
                "ref": ref(fp),
                "source_root": native_root,
                "units": record["processed_units"],
                "bindings": bindings,
            }
        )
    if adapter == "clang-tidy" and not artifacts:
        phase = next(p for p in record["phases"] if p["name"] == "analyze:check.cpp")
        for stream in ("stdout", "stderr"):
            fp = tmp / ("clean-clang-" + stream + ".native")
            fp.write_bytes(base64.b64decode(phase[stream]["base64"]))
            artifacts.append(
                {
                    "id": "clean-" + stream,
                    "tool": adapter,
                    "format": "clang-tidy-text",
                    "role": "diagnostics",
                    "ref": ref(fp),
                    "source_root": native_root,
                    "units": record["processed_units"],
                    "bindings": bindings,
                }
            )
    original = tmp / "original-analysis-run.json"
    write_json(original, record)
    artifacts.append(
        {
            "id": "original-analysis-run",
            "tool": adapter,
            "format": "text",
            "role": "log",
            "ref": ref(original),
            "source_root": native_root,
            "units": [],
            "bindings": bindings,
        }
    )
    execution = next(
        p
        for p in record["phases"]
        if p["name"] == ("runtime" if adapter in {"asan", "ubsan"} else "analyze:check.cpp")
    )
    observation = {
        "tool": adapter,
        "identity_digest": digest(ident),
        "processed_units": record["processed_units"],
        "extracted_units": None,
        "exclusions": [],
        "warnings": [],
        "errors": [],
        "failed_queries": [],
        "filtered_checks": [],
        "required_reports": [],
        "phases": [
            {
                "id": "analysis",
                "role": "analyze",
                "status": "completed",
                "exit_code": execution["exit_code"],
                "timed_out": execution["timed_out"],
                "artifacts": [a["id"] for a in artifacts if a["role"] == "diagnostics"],
            }
        ],
    }
    manifest = seal(
        {
            "schema_version": 1,
            "kind": "quality_extraction_manifest",
            "source_digest": bindings["source_digest"],
            "observations": [observation],
            "outer_exit_code": 0,
        }
    )
    r = {
        "schema_version": 1,
        "kind": "quality_import_request",
        "profile": ref(PROFILE),
        "baseline": write_json(tmp / "import-baseline.json", baseline),
        "artifacts": artifacts,
        "extraction": write_json(tmp / "import-extraction.json", manifest),
        "origin": "imported_unverified",
        "protected_roots": [str(ROOT)],
    }
    return Path(write_json(tmp / "import-request.json", r)["path"])
