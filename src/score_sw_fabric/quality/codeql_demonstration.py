"""Bounded native CodeQL execution on fixed synthetic software demonstrations."""

from __future__ import annotations

import csv
import io
import json
import math
import time
from pathlib import Path
from typing import Any

import score_sw_fabric.quality.codeql as codeql
from score_sw_fabric.agents.models import protected_roots
from score_sw_fabric.assurance.models import seal, stable_id
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.codeql_models import (
    read_control,
    reference,
    request,
    selection,
)
from score_sw_fabric.quality.codeql_native_phases import commands, extracted_units
from score_sw_fabric.quality.import_models import bounded_tree
from score_sw_fabric.quality.models import (
    Accumulator,
    Budget,
    Inputs,
    digest,
    environment,
    execute,
    identity_state,
    load_inputs,
    raw_bytes,
)
from score_sw_fabric.quality.profile import load_toolchain
from score_sw_fabric.quality.sarif import parse_report
from score_sw_fabric.runtime.models import output_path
from score_sw_fabric.runtime.request import _local
from score_sw_fabric.storage import temporary_directory

KIND = "quality_codeql_demonstration_request"
LICENSE_SHA = "d0d6cfdc857c1e0153bbd2b6f0d4ab42dfc38acec9b97b2f7f55c1f51ffe9fbf"
PATCH_SHA = "c45662cdc8845c11fb9d71d153eee5c22d9f3421e245791b249392e7f8f3ea08"
FIELDS = {
    "id",
    "purpose",
    "case",
    "prerequisites",
    "compiler",
    "reporting_toolchain",
    "license",
    "report_patch_mode",
    "timeout_seconds",
    "total_timeout_seconds",
    "output_limit_bytes",
    "protected_roots",
}
REFERENCES = ("prerequisites", "compiler", "reporting_toolchain", "license")
REPORTS = {
    "database_integrity_report.md",
    "deviations_report.md",
    "guideline_compliance_summary.md",
    "guideline_recategorizations_report.md",
}
PREFIXES = (
    "cpp/report/src/",
    "cpp/common/src/",
    "scripts/configuration/",
    "scripts/reports/",
    "scripts/shared/",
    "supported_codeql_configs.json",
    "LICENSE.md",
)


class NativeFailure(Exception):
    """A measured incomplete operation, rather than rejected caller input."""


def parse_request(path: Path) -> dict[str, Any]:
    obj, base = request(path, KIND, FIELDS)
    stable_id(obj["id"], "/id")
    for name, permitted in (
        ("purpose", {"software_demonstration"}),
        ("case", {"seeded", "corrected"}),
        ("report_patch_mode", {"unmodified", "git_recount"}),
    ):
        if not isinstance(obj[name], str) or obj[name] not in permitted:
            raise InputError("FIELD_ENUM", "Unsupported demonstration selection", "/" + name)
    for name, maximum in (
        ("timeout_seconds", 3600),
        ("total_timeout_seconds", 3600),
        ("output_limit_bytes", 16777216),
    ):
        minimum = 1024 if name == "output_limit_bytes" else 1
        if type(obj[name]) is not int or not minimum <= obj[name] <= maximum:
            raise InputError("LIMIT_EXCEEDED", "Invalid demonstration bound", "/" + name)
    for name in REFERENCES:
        reference(obj[name], "/" + name)
    protected_roots(base, obj["protected_roots"], "/protected_roots")
    return obj


class Operation:
    def __init__(
        self, record: dict[str, Any], work: Path, limits: dict[str, Any], budget: Budget
    ) -> None:
        self.record, self.work = record, work
        self.budget = budget
        self.timeout = limits["timeout_seconds"]
        self.deadline = time.monotonic() + limits["total_timeout_seconds"]

    def step(
        self,
        name: str,
        argv: list[str],
        env: dict[str, str],
        *,
        cwd: Path | None = None,
        expected: int = 0,
    ) -> dict[str, Any]:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise NativeFailure("TIME_BUDGET_EXHAUSTED")
        phase = execute(
            name,
            argv,
            cwd or self.work,
            min(self.timeout, math.ceil(remaining)),
            self.budget,
            env,
        )
        self.record["phases"].append(phase)
        if not phase["error"]:
            if name.startswith("database:trace:"):
                self.record["analysis_executed"] = True
            elif name == "native:report":
                self.record["native_reporting_executed"] = True
        if phase["timed_out"]:
            raise NativeFailure("PHASE_TIMEOUT")
        if phase["error"] or phase["exit_code"] != expected:
            raise NativeFailure("PHASE_FAILED")
        if any(phase[key]["truncated"] for key in ("stdout", "stderr")):
            raise NativeFailure("OUTPUT_TRUNCATED")
        return phase

    def capture(self, path: Path, identifier: str, format_name: str = "text") -> None:
        if not path.exists():
            return
        codeql._file(path)
        acc = Accumulator(self.budget, format_name)
        with path.open("rb") as stream:
            while chunk := stream.read(65536):
                acc.add(chunk)
        self.record["artifacts"].append({"id": identifier, **acc.record()})


def _controls(selected: Inputs, path: Path, original: bytes) -> None:
    controls = {path.absolute(): original}
    for index, name in enumerate(("profile", "toolchain", "configuration")):
        controls[selected.inputs[index]] = selected.assets[name]
    for name in (
        "source_lock",
        "scan_config",
        "report_patch",
        "reporting_toolchain",
        "eligibility",
    ):
        if selected.settings["effective"][name] is not None:
            ref = selected.settings["effective"][name]
            controls[_local(selected.inputs[2].parent, ref["path"], "/control")] = selected.assets[
                name
            ]
    selected.settings["_controls"] = controls


def _copy_sources(
    selected: Inputs,
    inventory: dict[str, Any],
    operation: Operation,
    native: Path,
) -> dict[str, str]:
    root = Path(selected.settings["effective"]["source_root"])
    observed: dict[str, Any] = {"phases": [], "gaps": []}
    tree = codeql._git(
        selected,
        observed,
        operation.work,
        operation.budget,
        "report-source:tree",
        root,
        "ls-tree",
        "-r",
        "-z",
        inventory["source_inspection"]["commit"],
        "--",
        *PREFIXES,
    )
    operation.record["phases"].extend(observed["phases"])
    if tree is None or observed["gaps"]:
        raise NativeFailure("NATIVE_SOURCE_UNAVAILABLE")
    objects: dict[str, str] = {}
    for entry in tree.split("\0"):
        if not entry:
            continue
        fields, separator, name = entry.partition("\t")
        values = fields.split()
        if not separator or len(values) != 3 or values[:2] != ["100644", "blob"]:
            # Executable scripts are copied as data too; no hooks execute.
            if not separator or len(values) != 3 or values[:2] != ["100755", "blob"]:
                raise InputError("NATIVE_SOURCE_UNSUPPORTED", "Unsafe native Git entry")
        if any(ord(c) < 32 for c in name) or len(objects) >= 5000:
            raise InputError("LIMIT_EXCEEDED", "Invalid or excessive native source names")
        objects[name] = values[2]
    manifest = codeql._manifest(root, list(objects), objects)
    operation.record["report_sources"] = manifest
    for row in manifest:
        data = (root / row["path"]).read_bytes()
        if digest(data) != row["sha256"]:
            raise InputError("INPUT_DRIFT", "Native source changed during copy")
        target = native / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    operation.capture(native / "LICENSE.md", "native-source-license")
    pack = inventory["pack_inspection"]
    for row in pack["manifest"]:
        if not row["path"].startswith(".codeql/libraries/"):
            continue
        source = Path(pack["root"]) / row["path"]
        if codeql._file(source)["sha256"] != row["sha256"]:
            raise InputError("INPUT_DRIFT", "Library bytes changed before copy")
        data = source.read_bytes()
        if digest(data) != row["sha256"]:
            raise InputError("INPUT_DRIFT", "Library bytes changed during copy")
        target = operation.work / "home/.codeql/packages" / row["path"][len(".codeql/libraries/") :]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return objects


def _patch(selected: Inputs, op: Operation, native: Path, env: dict[str, str]) -> None:
    data = selected.assets["report_patch"]
    if digest(data) != PATCH_SHA:
        raise InputError("NATIVE_POLICY_IDENTITY_MISMATCH", "Unreviewed report patch")
    path = op.work / "selected-time-report.patch"
    path.write_bytes(data)
    target = native / "scripts/reports/utils.py"
    original = digest(target.read_bytes())
    for name, flags, expected in (
        ("original-check", ["--check"], 128),
        ("recount-check", ["--recount", "--check"], 0),
        ("recount-apply", ["--recount"], 0),
    ):
        op.step(
            "report-patch:" + name,
            [str(codeql.INSPECTOR), "apply", *flags, "--", str(path)],
            env,
            cwd=native,
            expected=expected,
        )
    op.record["report_patch"] = {
        "original_patch_sha256": digest(data),
        "original_utils_sha256": original,
        "transformed_utils_sha256": digest(target.read_bytes()),
        "method": "explicit_git_apply_recount",
        "native_patch_qualification": "unknown",
    }
    op.capture(path, "selected-time-report.patch")
    op.capture(target, "native/scripts/reports/utils.py")


def _diagnostics(record: dict[str, Any], source: Path, files: dict[str, bytes]) -> None:
    artifact = next(a for a in record["artifacts"] if a["id"] == "results.sarif")
    if artifact["truncated"]:
        raise NativeFailure("OUTPUT_TRUNCATED")
    data = raw_bytes(artifact)
    document = json.loads(data)
    bounded_tree(document)
    runs = document.get("runs", [])
    if len(runs) != 1:
        raise NativeFailure("NATIVE_OUTPUT_INVALID")
    pack = record["prerequisite_inventory"]["pack_inspection"]
    metadata = {pack["identity"]["name"]: pack["identity"]}
    metadata.update({row["name"]: row["metadata"] for row in pack["libraries"]})
    expected = []
    for name in (
        "codeql/misra-cpp-coding-standards",
        "codeql/common-cpp-coding-standards",
        "codeql/cpp-all",
    ):
        value = metadata[name]
        expected.append(
            {"name": name, "version": value["version"] + "+" + value["buildMetadata"]["sha"]}
        )
    try:
        diagnostics, gaps = parse_report(
            data,
            "results.sarif",
            source,
            files,
            {
                "name": "CodeQL",
                "version": "2.21.4",
                "query_pack": expected[0],
                "libraries": expected[1:],
            },
            source_root_base="%SRCROOT%",
        )
    except InputError as exc:
        raise NativeFailure(exc.code) from exc
    record["diagnostics"], record["result_count"] = diagnostics, len(diagnostics)
    if gaps:
        record["execution_gaps"].extend(gaps)
        raise NativeFailure("NATIVE_ANALYSIS_INCOMPLETE")


def _native(
    selected: Inputs,
    record: dict[str, Any],
    work: Path,
    limits: dict[str, Any],
    budget: Budget,
) -> None:
    op = Operation(record, work, limits, budget)
    native, source = work / "native", work / "source"
    source.mkdir()
    source_bytes = (
        "// Synthetic software demonstration; no target engineering evidence.\n"
        + (
            "int main() { int unused = 7; return 0; }\n"
            if limits["case"] == "seeded"
            else "int main() { return 0; }\n"
        )
    ).encode()
    record["source"] = {
        "path": "check.cpp",
        "sha256": digest(source_bytes),
        "base64": op.budget.capture(source_bytes)["base64"],
    }
    (source / "check.cpp").write_bytes(source_bytes)
    config = b"report-deviated-alerts: true\n"
    (source / "coding-standards.yml").write_bytes(config)
    scan = work / "native-scan.yaml"
    scan.write_bytes(selected.assets["scan_config"])
    objects = _copy_sources(selected, record["prerequisite_inventory"], op, native)
    env = environment(work, selected.toolchain)
    env.update(
        PATH=str(Path(selected.toolchain["tool"]["path"]).parent) + ":/usr/bin:/bin",
        PYTHONDONTWRITEBYTECODE="1",
        XDG_CONFIG_HOME=str(work / "home/config"),
        XDG_CACHE_HOME=str(work / "home/cache"),
    )
    try:
        if limits["report_patch_mode"] == "git_recount":
            _patch(selected, op, native, env)
        op.step(
            "reporting:dependencies",
            [
                record["reporting_toolchain"]["tool"]["path"],
                "-I",
                "-c",
                "import sys,yaml,pytest; print(sys.version); print('PyYAML',yaml.__version__); "
                "print('pytest',pytest.__version__); sys.exit(0 if sys.version_info[:2] == (3,9) "
                "and yaml.__version__ == '5.4' and pytest.__version__ == '7.2.0' else 1)",
            ],
            env,
        )
        recipe = commands(
            cli=Path(selected.toolchain["tool"]["path"]),
            compiler=record["compiler"],
            pack=Path(record["prerequisite_inventory"]["pack_inspection"]["root"]),
            suite=selected.settings["effective"]["suite"],
            work=work,
            units=["check.cpp"],
            include_dirs=[],
            defines=[],
            scan_config=scan,
            native_source=native,
            reporting=record["reporting_toolchain"],
            timeout_seconds=limits["timeout_seconds"],
        )
        record["recipe"] = recipe
        for item in recipe:
            if item["name"] == "native:report":
                continue
            op.step(item["name"], item["argv"], env)
        for identifier, format_name in (("results.sarif", "sarif"), ("results.csv", "csv")):
            op.capture(work / identifier, identifier, format_name)
        files = {
            "check.cpp": source_bytes,
            "coding-standards.yml": config,
            "coding-standards.xml": (source / "coding-standards.xml").read_bytes(),
        }
        _diagnostics(record, source, files)
        queries = [
            native / "cpp/report/src/Diagnostics" / (name + ".ql")
            for name in ("SuccessfullyExtractedFiles", "ExtractionErrors")
        ]
        cli = selected.toolchain["tool"]["path"]
        op.step(
            "extraction:queries",
            [
                cli,
                "database",
                "run-queries",
                "--threads=1",
                "--ram=2048",
                "--additional-packs=" + str(native / "cpp/report/src"),
                "--",
                str(work / "database"),
                *map(str, queries),
            ],
            env,
        )
        for name, key in (
            ("SuccessfullyExtractedFiles", "native_rows"),
            ("ExtractionErrors", "errors"),
        ):
            bqrs = (
                work
                / "database/results/codeql/report-cpp-coding-standards/Diagnostics"
                / (name + ".bqrs")
            )
            phase = op.step(
                "extraction:decode:" + name,
                [
                    cli,
                    "bqrs",
                    "decode",
                    "--format=csv",
                    "--entities=string,url",
                    "--no-titles",
                    "--",
                    str(bqrs),
                ],
                env,
            )
            record["extraction"][key] = list(
                csv.reader(io.StringIO(raw_bytes(phase["stdout"]).decode()))
            )
        try:
            extracted = extracted_units(
                record["extraction"]["native_rows"], source, list(files), ["check.cpp"]
            )
        except InputError as exc:
            raise NativeFailure(exc.code) from exc
        record["extraction"]["extracted_units"] = extracted
        if extracted != ["check.cpp"] or record["extraction"]["errors"]:
            raise NativeFailure("EXTRACTION_INCOMPLETE")
        item = next(p for p in recipe if p["name"] == "native:report")
        op.step(item["name"], item["argv"], env)
        actual = {path.name for path in (work / "native-reports").glob("*.md")}
        if actual != REPORTS:
            raise NativeFailure("REPORT_MISSING")
        record["extraction"]["adequacy"] = "adequate"
    finally:
        for name in (
            "results.sarif",
            "results.csv",
            "source/coding-standards.yml",
            "source/coding-standards.xml",
        ):
            if not any(a["id"] == name for a in record["artifacts"]):
                op.capture(work / name, name)
        for name in sorted(REPORTS):
            op.capture(work / "native-reports" / name, "native-reports/" + name)
        if (source / "check.cpp").read_bytes() != source_bytes or (
            source / "coding-standards.yml"
        ).read_bytes() != config:
            raise InputError("BASELINE_DRIFT", "Synthetic source/configuration changed")
        for row in record["report_sources"]:
            expected_hash = row["sha256"]
            if record["report_patch"] is not None and row["path"] == "scripts/reports/utils.py":
                expected_hash = record["report_patch"]["transformed_utils_sha256"]
            if digest((native / row["path"]).read_bytes()) != expected_hash:
                raise InputError("INPUT_DRIFT", "Copied native source changed")
        pack = record["prerequisite_inventory"]["pack_inspection"]
        for row in pack["manifest"]:
            if row["path"].startswith(".codeql/libraries/"):
                cached = work / "home/.codeql/packages" / row["path"][len(".codeql/libraries/") :]
                if codeql._file(cached)["sha256"] != row["sha256"]:
                    raise InputError("INPUT_DRIFT", "Copied library changed")
        root = Path(selected.settings["effective"]["source_root"])
        if codeql._manifest(root, list(objects), objects) != record["report_sources"]:
            raise InputError("INPUT_DRIFT", "Original native sources changed")
        for row in record["artifacts"]:
            if row["truncated"]:
                record["execution_gaps"].append("OUTPUT_TRUNCATED")


def run(path: Path, out: Path | None = None) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    obj = parse_request(path)
    original = read_control(path, "/request")
    selected_refs = {name: selection(path.parent, obj[name], "/" + name) for name in REFERENCES}
    prerequisite_path, prerequisite_bytes = selected_refs["prerequisites"]
    selected = load_inputs(prerequisite_path, "capabilities", "codeql")
    _controls(selected, prerequisite_path, prerequisite_bytes)
    compiler = load_toolchain(selected_refs["compiler"][1], "quality_sanitizer_toolchain_profile")
    reporting = load_toolchain(
        selected_refs["reporting_toolchain"][1], "quality_codeql_reporting_toolchain_profile"
    )
    license_path, license_bytes = selected_refs["license"]
    if (
        digest(license_bytes) != LICENSE_SHA
        or license_path != Path(selected.toolchain["tool"]["path"]).parent / "LICENSE.md"
    ):
        raise InputError("LICENSE_IDENTITY_MISMATCH", "Demonstration requires original CLI terms")
    if selected.settings["effective"]["suite"] != "codeql-suites/misra-cpp-default.qls":
        raise InputError(
            "SUITE_UNSUPPORTED", "Only the verified default demonstration suite is supported"
        )
    inputs = [
        path.absolute(),
        *selected.inputs,
        codeql.INSPECTOR,
        *[p for p, _ in selected_refs.values()],
    ]
    roots = [
        *selected.protected,
        *protected_roots(path.parent, obj["protected_roots"], "/protected_roots"),
    ]
    for chain in (compiler, reporting):
        inputs.extend(Path(a["path"]) for a in [chain["tool"], *chain["dependencies"]])
        roots.extend(Path(d) for d in chain["library_dirs"])
    if out is not None:
        output_path(out, inputs, roots)
    available = all(
        [identity_state(selected.toolchain), identity_state(compiler), identity_state(reporting)]
    )
    budget = Budget(obj["output_limit_bytes"])
    with temporary_directory(prefix="score-codeql-demonstration-") as temporary:
        work = Path(temporary)
        inventory = codeql.inspect(selected, work, budget)
        record: dict[str, Any] = {
            "schema_version": 1,
            "kind": "quality_codeql_demonstration_run",
            "id": obj["id"],
            "purpose": obj["purpose"],
            "case": obj["case"],
            "request": {"path": str(path.absolute()), "sha256": digest(original)},
            "prerequisite_inventory": inventory,
            "compiler": compiler,
            "reporting_toolchain": reporting,
            "license": {"selection": obj["license"], "original": budget.capture(license_bytes)},
            "source": None,
            "recipe": [],
            "report_sources": [],
            "report_patch": None,
            "phases": [],
            "artifacts": [],
            "diagnostics": [],
            "result_count": 0,
            "extraction": {
                "expected_units": ["check.cpp"],
                "extracted_units": [],
                "native_rows": [],
                "errors": [],
                "adequacy": "unknown",
            },
            "execution_gaps": [],
            "gaps": [],
            "outcome": "unavailable",
            "origin": "local_unprotected_execution",
            "analysis_executed": False,
            "native_reporting_executed": False,
            "source_integrity": "unchanged",
            "assurance_eligibility": "not_eligible",
            "engineering_readiness": "not_evaluated",
            "accepted_claims": 0,
            "limitations": [
                "Fixed synthetic software demonstration; target-project analysis remains gated.",
                "Selected runtime/provenance/applicability and manual reviews remain unqualified.",
                "Native report labels and recount transformation do not grant acceptance.",
            ],
        }
        pack = inventory["pack_inspection"]
        if (
            not available
            or pack is None
            or inventory["source_inspection"]["source_build"]["state"] != "source_trees_equal"
            or pack["library_state"] != "matched"
            or inventory["source_inspection"]["origin"] == "fixture"
            or any(a["truncated"] for a in inventory["artifacts"])
            or any(p[k]["truncated"] for p in inventory["phases"] for k in ("stdout", "stderr"))
            or record["license"]["original"]["truncated"]
        ):
            record["execution_gaps"].append("EXECUTION_PREREQUISITES_UNAVAILABLE")
        elif reporting["tool"]["version"] != "Python 3.9.25":
            record["execution_gaps"].append("REPORTING_VERSION_UNSUPPORTED")
        else:
            try:
                _native(selected, record, work, obj, budget)
            except NativeFailure as exc:
                record["execution_gaps"].append(str(exc))
            except InputError as exc:
                if "DRIFT" in exc.code or "MISMATCH" in exc.code or "INPUT_" in exc.code:
                    raise
                record["execution_gaps"].append(exc.code)
            except (OSError, ValueError, KeyError, StopIteration) as exc:
                record["execution_gaps"].append("NATIVE_OUTPUT_INVALID")
                record["limitations"].append("Native measurement failed: " + type(exc).__name__)
            record["outcome"] = (
                "incomplete"
                if record["execution_gaps"]
                else ("findings" if record["diagnostics"] else "completed")
            )
            if record["execution_gaps"]:
                record["extraction"]["adequacy"] = "incomplete"
        codeql._refreeze(selected, inventory, work, budget)
        record["prerequisite_inventory"] = seal(inventory)
    if read_control(path, "/request") != original:
        raise InputError("INPUT_DRIFT", "Demonstration request changed")
    for name, (control_path, data) in selected_refs.items():
        if read_control(control_path, "/" + name) != data:
            raise InputError("INPUT_DRIFT", "Selected demonstration control changed")
    for chain in (compiler, reporting):
        if not identity_state(chain) and available:
            raise InputError("INPUT_DRIFT", "Selected runtime disappeared")
    record["execution_gaps"] = sorted(set(record["execution_gaps"]))
    record["gaps"] = sorted(set(inventory["gaps"] + record["execution_gaps"]))
    bounded_tree(record)
    if len(canonical(record)) > 96 * 1024 * 1024:
        raise InputError("LIMIT_EXCEEDED", "Demonstration result exceeds 96 MiB")
    return 0 if record["outcome"] == "completed" else 1, seal(record), inputs, roots
