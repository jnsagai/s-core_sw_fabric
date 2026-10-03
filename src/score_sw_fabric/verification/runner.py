"""Deterministic C++17 build/test adapter with native result classes and metadata rules."""

from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from score_sw_fabric.agents.models import (
    READINESS,
    input_file,
    load_request,
    protected_roots,
    relative_path,
)
from score_sw_fabric.assurance.models import seal, stable_id
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.safety.native import links
from score_sw_fabric.storage import temporary_directory
from score_sw_fabric.verification.design import in_scope, requirement_needs, root_files
from score_sw_fabric.verification.profile import load_profile, load_toolchain, verify_toolchain

RUN_FIELDS = {
    "profile",
    "toolchain",
    "component",
    "root",
    "requirements",
    "sources",
    "tests",
    "include_dirs",
    "coverage",
    "timeout_seconds",
    "protected_roots",
}
MAX_OUTPUT = 64 * 1024
MAX_XML = 16 * 1024 * 1024
STEP_TIMEOUT = 300
ENVIRONMENT = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C"}


def _bounded(data: bytes) -> dict[str, Any]:
    return {
        "text": data[:MAX_OUTPUT].decode("utf-8", "replace"),
        "truncated": len(data) > MAX_OUTPUT,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _step(
    name: str, argv: list[str], cwd: Path, timeout: float, replacements: dict[str, str]
) -> dict[str, Any]:
    def sanitize(value: str) -> str:
        for old, new in replacements.items():
            value = value.replace(old, new)
        return value

    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            env={**ENVIRONMENT, "TMPDIR": str(cwd)},
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        code, out, err, timed_out = completed.returncode, completed.stdout, completed.stderr, False
    except subprocess.TimeoutExpired as exc:
        code, out, err, timed_out = None, exc.stdout or b"", exc.stderr or b"", True
    stdout = _bounded(out)
    stderr = _bounded(err)
    return {
        "step": name,
        "argv": [sanitize(item) for item in argv],
        "exit_code": code,
        "timed_out": timed_out,
        "stdout": stdout,
        "stderr": stderr,
    }


def native_result(testcase: ET.Element) -> tuple[str, str]:
    """docs-as-code classes: error and failure are failed; skipped is skipped; else passed."""
    for tag, result in (("error", "failed"), ("failure", "failed"), ("skipped", "skipped")):
        element = testcase.find(tag)
        if element is not None:
            return result, element.get("message", "")[:4096]
    if testcase.get("status") == "notrun":
        return "skipped", "not run"
    return "passed", ""


def parse_results(data: bytes) -> list[dict[str, Any]]:
    if len(data) > MAX_XML or b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        raise InputError("TEST_REPORT_INVALID", "Test report is too large or declares entities")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise InputError("TEST_REPORT_INVALID", "Test report is not valid XML") from exc
    tests = []
    for testcase in root.iter("testcase"):
        properties = {
            str(item.get("name")): str(item.get("value", ""))
            for item in testcase.iterfind("properties/property")
        }
        result, text = native_result(testcase)
        tests.append(
            {
                "suite": testcase.get("classname", ""),
                "name": testcase.get("name", ""),
                "result": result,
                "result_text": text,
                "test_type": properties.get("TestType"),
                "derivation_technique": properties.get("DerivationTechnique"),
                "fully_verifies": links(properties.get("FullyVerifies", "")),
                "partially_verifies": links(properties.get("PartiallyVerifies", "")),
                "description": properties.get("Description"),
            }
        )
    return tests


def metadata_findings(
    profile: dict[str, Any], tests: list[dict[str, Any]], needs: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    rules = {rule["check"]: rule["id"] for rule in profile["rules"]}
    findings = []

    def finding(code: str, test: dict[str, Any], detail: str, rule: str) -> None:
        findings.append(
            {
                "code": code,
                "subject": f"{test['suite']}.{test['name']}",
                "detail": detail,
                "rule": rule,
            }
        )

    for test in tests:
        for field, allowed in (
            ("test_type", profile["test_types"]),
            ("derivation_technique", profile["derivation_techniques"]),
        ):
            value = test[field]
            if not value:
                finding("METADATA_MISSING", test, field, rules["metadata_required"])
            elif value not in allowed:
                finding("METADATA_VALUE", test, f"{field}={value}", rules["metadata_values"])
        if not (test["description"] or "").strip():
            finding("DESCRIPTION_EMPTY", test, "Description", rules["metadata_required"])
        linked = test["fully_verifies"] + test["partially_verifies"]
        if not linked:
            rule = (
                rules["requirement_link"]
                if test["test_type"] == "requirements-based"
                else rules["metadata_required"]
            )
            finding("VERIFIES_MISSING", test, "No verified component requirement", rule)
        for identifier in linked:
            if identifier not in needs or needs[identifier]["type"] != "comp_req":
                finding("VERIFIES_UNRESOLVED", test, identifier, rules["metadata_required"])
    return findings


def requirement_matrix(scoped: list[str], tests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matrix = []
    for identifier in scoped:

        def names(field: str, result: str, identifier: str = identifier) -> list[str]:
            return sorted(
                f"{test['suite']}.{test['name']}"
                for test in tests
                if identifier in test[field] and test["result"] == result
            )

        failing = sorted(
            set(names("fully_verifies", "failed") + names("partially_verifies", "failed"))
        )
        full = names("fully_verifies", "passed")
        partial = names("partially_verifies", "passed")
        state = (
            "failing"
            if failing
            else "verified"
            if full
            else "partially_verified"
            if partial
            else "unverified"
        )
        matrix.append(
            {
                "id": identifier,
                "fully_verified_by": full,
                "partially_verified_by": partial,
                "failing": failing,
                "state": state,
            }
        )
    return matrix


def _coverage(build: Path, gcov: str, sources: dict[str, Path]) -> dict[str, Any]:
    step = _step(
        "coverage",
        [
            gcov,
            "--json-format",
            "--branch-probabilities",
            "--branch-counts",
            *sorted(str(path) for path in build.glob("*.gcda")),
        ],
        build,
        STEP_TIMEOUT,
        {str(build): "$BUILD"},
    )
    units = {}
    for report in sorted(build.glob("*.gcov.json.gz")):
        try:
            data = json.loads(gzip.decompress(report.read_bytes()))
        except (OSError, ValueError):
            continue
        for entry in data.get("files", []):
            for relative, full in sources.items():
                if Path(entry.get("file", "")).resolve() == full.resolve():
                    lines = entry.get("lines", [])
                    branches = [branch for line in lines for branch in line.get("branches", [])]
                    units[relative] = {
                        "path": relative,
                        "lines_total": len(lines),
                        "lines_executed": sum(1 for line in lines if line.get("count", 0) > 0),
                        "branches_total": len(branches),
                        "branches_executed": sum(
                            1 for branch in branches if branch.get("count", 0) > 0
                        ),
                    }
    status = "imported" if step["exit_code"] == 0 and units else "unavailable"
    return {"status": status, "units": [units[key] for key in sorted(units)], "step": step}


def run(request_path: Path) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    record, base = load_request(request_path, "verification_run_request", RUN_FIELDS)
    profile_path, profile_bytes = input_file(base, record["profile"], "/profile")
    profile = load_profile(profile_bytes)
    toolchain_path, toolchain_bytes = input_file(base, record["toolchain"], "/toolchain")
    toolchain = load_toolchain(toolchain_bytes)
    component = stable_id(record["component"], "/component")
    root, groups = root_files(
        base, record["root"], {name: record[name] for name in ("requirements", "sources", "tests")}
    )
    includes = record["include_dirs"]
    if not isinstance(includes, list) or len(includes) > 32:
        raise InputError("LIMIT_EXCEEDED", "Too many include directories", "/include_dirs")
    include_paths = [
        relative_path(item, f"/include_dirs/{index}") for index, item in enumerate(includes)
    ]
    if not isinstance(record["coverage"], bool):
        raise InputError("FIELD_TYPE", "coverage must be boolean", "/coverage")
    timeout = record["timeout_seconds"]
    if type(timeout) is not int or not 1 <= timeout <= 3600:
        raise InputError("LIMIT_EXCEEDED", "timeout_seconds must be 1-3600", "/timeout_seconds")
    protected = protected_roots(base, record["protected_roots"], "/protected_roots")
    observed = verify_toolchain(toolchain)
    needs = requirement_needs(profile, groups["requirements"])
    scoped = in_scope(profile, needs, None)
    flags = ["-std=c++17", *toolchain["policy"]["flags"]]
    baseline = {
        "sources": groups["sources"].files,
        "tests": groups["tests"].files,
        "requirements": groups["requirements"].files,
        "toolchain": observed,
        "flags": flags,
        "link_flags": toolchain["link_flags"],
        "include_dirs": include_paths,
        "coverage": record["coverage"],
    }
    baseline["source_digest"] = hashlib.sha256(canonical(groups["sources"].files)).hexdigest()
    baseline["full_digest"] = hashlib.sha256(canonical(baseline)).hexdigest()
    findings: list[dict[str, Any]] = []
    steps = []
    tests: list[dict[str, Any]] = []
    coverage: dict[str, Any] = {"status": "not_requested", "units": []}
    execution: dict[str, Any] | None = None
    compiler = toolchain["compiler"]["path"]
    with temporary_directory(prefix="score-verify-") as directory:
        build = Path(directory)
        replacements = {str(root): "$ROOT", str(build): "$BUILD"}
        objects = []
        units = [
            (path, "source") for path in groups["sources"].data if path.endswith((".cpp", ".cc"))
        ]
        units += [(path, "test") for path in groups["tests"].data if path.endswith((".cpp", ".cc"))]
        built = True
        for index, (path, kind) in enumerate(units):
            obj = build / f"{index:03d}_{Path(path).stem}.o"
            argv = [
                compiler,
                *flags,
                *(f"-I{root / item}" for item in include_paths),
                f"-I{toolchain['test_library']['include']}",
            ]
            if record["coverage"] and kind == "source":
                argv.append("--coverage")
            argv += ["-c", str(root / path), "-o", str(obj)]
            step = _step(f"compile {path}", argv, build, STEP_TIMEOUT, replacements)
            steps.append(step)
            objects.append(str(obj))
            if step["exit_code"] != 0:
                built = False
                findings.append(
                    {
                        "code": "BUILD_FAILED",
                        "subject": path,
                        "detail": step["stderr"]["text"][:512],
                        "rule": None,
                    }
                )
        binary = build / "unit_tests"
        if built:
            argv = [
                compiler,
                *objects,
                *(item["path"] for item in reversed(toolchain["test_library"]["libraries"])),
                *toolchain["link_flags"],
            ]
            if record["coverage"]:
                argv.append("--coverage")
            argv += ["-o", str(binary)]
            step = _step("link", argv, build, STEP_TIMEOUT, replacements)
            steps.append(step)
            if step["exit_code"] != 0:
                built = False
                findings.append(
                    {
                        "code": "BUILD_FAILED",
                        "subject": "link",
                        "detail": step["stderr"]["text"][:512],
                        "rule": None,
                    }
                )
        if built:
            report = build / "results.xml"
            execution = _step(
                "test", [str(binary), f"--gtest_output=xml:{report}"], build, timeout, replacements
            )
            if execution["timed_out"]:
                findings.append(
                    {
                        "code": "TEST_TIMEOUT",
                        "subject": "unit_tests",
                        "detail": f"{timeout}s",
                        "rule": None,
                    }
                )
            if report.is_file():
                data = report.read_bytes()
                execution["xml_sha256"] = hashlib.sha256(data).hexdigest()
                tests = parse_results(data)
            else:
                execution["xml_sha256"] = None
                findings.append(
                    {
                        "code": "TEST_REPORT_MISSING",
                        "subject": "unit_tests",
                        "detail": "No XML report",
                        "rule": None,
                    }
                )
            if execution["exit_code"] not in (0, 1) and not execution["timed_out"]:
                findings.append(
                    {
                        "code": "TEST_BINARY_FAILED",
                        "subject": "unit_tests",
                        "detail": f"exit {execution['exit_code']}",
                        "rule": None,
                    }
                )
            elif execution["exit_code"] == 1 and not any(
                test["result"] == "failed" for test in tests
            ):
                findings.append(
                    {
                        "code": "TEST_BINARY_FAILED",
                        "subject": "unit_tests",
                        "detail": "Test binary exited 1 without a failed testcase",
                        "rule": None,
                    }
                )
            if record["coverage"]:
                sources = {path: root / path for path in groups["sources"].data}
                coverage = _coverage(build, toolchain["coverage_tool"]["path"], sources)
                if coverage["status"] != "imported":
                    findings.append(
                        {
                            "code": "COVERAGE_UNAVAILABLE",
                            "subject": "coverage",
                            "detail": "No gcov data",
                            "rule": None,
                        }
                    )
    test_digest = hashlib.sha256(canonical(groups["tests"].files)).hexdigest()
    for test in tests:
        test["source_digest"] = baseline["source_digest"]
        test["test_digest"] = test_digest
        test["baseline_digest"] = baseline["full_digest"]
        test["toolchain_digest"] = hashlib.sha256(canonical(observed)).hexdigest()
        if test["result"] == "failed":
            findings.append(
                {
                    "code": "TEST_FAILED",
                    "subject": f"{test['suite']}.{test['name']}",
                    "detail": test["result_text"][:512],
                    "rule": None,
                }
            )
        elif test["result"] == "skipped":
            findings.append(
                {
                    "code": "TEST_SKIPPED",
                    "subject": f"{test['suite']}.{test['name']}",
                    "detail": test["result_text"][:512],
                    "rule": None,
                }
            )
    metadata = metadata_findings(profile, tests, needs)
    invalid_tests = {item["subject"] for item in metadata}
    creditable_tests = [
        test
        for test in tests
        if test["result"] == "failed" or f"{test['suite']}.{test['name']}" not in invalid_tests
    ]
    failed = any(
        item["code"]
        in {
            "BUILD_FAILED",
            "TEST_FAILED",
            "TEST_TIMEOUT",
            "TEST_REPORT_MISSING",
            "TEST_BINARY_FAILED",
        }
        for item in findings
    )
    outcome = "failed" if failed else "blocked" if metadata or findings or not tests else "passed"
    output = {
        "schema_version": 1,
        "kind": "unit_verification_run",
        "profile": {"id": profile["id"], "sha256": hashlib.sha256(profile_bytes).hexdigest()},
        "toolchain_profile": {
            "id": toolchain["id"],
            "sha256": hashlib.sha256(toolchain_bytes).hexdigest(),
            "status": toolchain["status"],
        },
        "policy": {
            key: toolchain["policy"][key]
            for key in ("source", "selected_levels", "unavailable_levels", "unsupported_flags")
        },
        "component": component,
        "baseline": baseline,
        "build": {
            "steps": steps,
            "outcome": "ok"
            if all(step["exit_code"] == 0 for step in steps) and steps
            else "failed",
        },
        "execution": execution,
        "tests": tests,
        "metadata_findings": metadata,
        "requirements": requirement_matrix(scoped, creditable_tests),
        "coverage": {"status": coverage["status"], "units": coverage["units"]},
        "findings": findings,
        "origin": "local_unprotected_execution",
        "assurance_eligibility": "not_eligible",
        "outcome": outcome,
        "engineering_readiness": READINESS,
        "limitations": [
            "Local candidate toolchain, not the selected S-CORE Bazel toolchain.",
            "Results are unprotected local execution and are not 005 evidence.",
            "Structural coverage has no threshold; no verification plan is approved.",
        ],
    }
    status = 0 if outcome == "passed" else 1
    return status, seal(output), [profile_path, toolchain_path], [*protected, root]
