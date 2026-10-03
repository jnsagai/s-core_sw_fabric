"""Reproduce approved software demonstrations; never target engineering acceptance."""

from __future__ import annotations

import argparse
import csv
import io
import json
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import yaml

import score_sw_fabric.quality.codeql as codeql
from score_sw_fabric.assurance.models import seal
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.quality.codeql_models import read_control
from score_sw_fabric.quality.codeql_native_phases import commands, extracted_units
from score_sw_fabric.quality.models import (
    Accumulator,
    Budget,
    digest,
    environment,
    execute,
    identity_state,
    load_inputs,
    raw_bytes,
)
from score_sw_fabric.quality.profile import load_toolchain
from score_sw_fabric.runtime.models import output_path


@contextmanager
def retained_workspace(
    destination: Path,
    phases: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
    details: dict[str, Any],
) -> Iterator[Path]:
    """Keep original phase failures as evidence before disposable cleanup."""
    with tempfile.TemporaryDirectory(prefix="quality-codeql-demo-") as temporary:
        try:
            yield Path(temporary)
        except Exception as exc:
            destination.write_bytes(
                canonical(
                    seal(
                        {
                            "schema_version": 1,
                            "kind": "codeql_software_demonstration_failure",
                            "origin": "local_installation_smoke_test",
                            "assurance_eligibility": "not_eligible",
                            "engineering_readiness": "not_evaluated",
                            "accepted_claims": 0,
                            "error": type(exc).__name__,
                            "phases": phases,
                            "artifacts": artifacts,
                            "details": details,
                        }
                    )
                )
            )
            raise


def measure(
    case: str,
    destination: Path,
    reporting_profile: Path | None = None,
    apply_report_patch: bool = False,
) -> None:
    root = Path(__file__).resolve().parents[4]
    request = root / "examples/quality/codeql-prerequisites.yaml"
    selected = load_inputs(request, "capabilities", "codeql")
    output_path(destination, selected.inputs, [root, *selected.protected])
    if destination.exists():
        raise FileExistsError("Retained demonstrations require a new output path")
    if apply_report_patch and reporting_profile is None:
        raise ValueError("The report patch requires an explicit reporting profile")
    _, inventory, _, _ = codeql.capabilities(request)
    compiler_bytes = (root / "profiles/gcc11-sanitizers-local-v1.yaml").read_bytes()
    compiler = yaml.safe_load(compiler_bytes)
    assert identity_state(selected.toolchain) and identity_state(compiler)
    reporting_bytes = (
        read_control(reporting_profile, "/reporting_profile")
        if reporting_profile is not None
        else None
    )
    reporting = (
        load_toolchain(reporting_bytes, "quality_codeql_reporting_toolchain_profile")
        if reporting_bytes is not None
        else None
    )
    if reporting is not None:
        assert reporting_profile is not None
        assert identity_state(reporting)
        output_path(
            destination,
            [
                *[Path(asset["path"]) for asset in [reporting["tool"], *reporting["dependencies"]]],
                reporting_profile,
            ],
            [Path(directory) for directory in reporting["library_dirs"]],
        )
    source_bytes = (
        "// Synthetic software demonstration; no target engineering evidence.\n"
        + (
            "int main() { int unused = 7; return 0; }\n"
            if case == "seeded"
            else "int main() { return 0; }\n"
        )
    ).encode()
    budget = Budget(1024 * 1024)
    phases: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    details: dict[str, Any] = {"case": case, "inventory_digest": inventory["digest"]}
    if reporting is not None:
        details.update(reporting_toolchain=reporting, prerequisite_inventory=inventory)
    with retained_workspace(destination, phases, artifacts, details) as work:
        (work / "home").mkdir()
        source = work / "source"
        source.mkdir()
        (source / "check.cpp").write_bytes(source_bytes)
        scan = work / "native-scan.yaml"
        scan.write_bytes(selected.assets["scan_config"])
        native = work / "native"
        pack = Path(inventory["pack_inspection"]["root"])

        # Copy original scripts and queries before any native phase needs them.
        native_root = Path(selected.settings["effective"]["source_root"])
        prefix = "cpp/report/src/"
        paths = [prefix, "LICENSE.md"]
        if reporting is not None:
            paths.extend(
                [
                    "scripts/configuration/",
                    "scripts/reports/",
                    "scripts/shared/",
                    "supported_codeql_configs.json",
                    "cpp/common/src/",
                ]
            )
        observed: dict[str, Any] = {"phases": [], "gaps": []}
        tree = codeql._git(
            selected,
            observed,
            work,
            budget,
            "report-source:tree",
            native_root,
            "ls-tree",
            "-r",
            inventory["source_inspection"]["commit"],
            "--",
            *paths,
        )
        phases.extend(observed["phases"])
        assert tree is not None and not observed["gaps"]
        objects = {
            line.split("\t", 1)[1]: line.split("\t", 1)[0].split()[2] for line in tree.splitlines()
        }
        report_manifest = codeql._manifest(native_root, list(objects), objects)
        for row in report_manifest:
            path = native / row["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((native_root / row["path"]).read_bytes())
        libraries = work / "home/.codeql/packages"
        libraries.parent.mkdir(parents=True)
        shutil.copytree(pack / ".codeql/libraries", libraries)
        report_pack = native / prefix

        env = environment(work, selected.toolchain)
        env.update(
            XDG_CONFIG_HOME=str(work / "home/config"),
            XDG_CACHE_HOME=str(work / "home/cache"),
            PYTHONDONTWRITEBYTECODE="1",
            PATH=str(Path(selected.toolchain["tool"]["path"]).parent) + ":/usr/bin:/bin",
        )
        patch_observation = None
        if apply_report_patch:
            patch_path = work / "selected-time-report.patch"
            patch_bytes = selected.assets["report_patch"]
            patch_path.write_bytes(patch_bytes)
            target = native / "scripts/reports/utils.py"
            original_hash = digest(target.read_bytes())
            for name, options, expected_exit in (
                ("report-patch:original-check", ["--check"], 128),
                ("report-patch:recount-check", ["--recount", "--check"], 0),
                ("report-patch:recount-apply", ["--recount"], 0),
            ):
                phase = execute(
                    name,
                    [str(codeql.INSPECTOR), "apply", *options, "--", str(patch_path)],
                    native,
                    30,
                    budget,
                    env,
                )
                phases.append(phase)
                assert (
                    phase["exit_code"] == expected_exit
                    and not phase["timed_out"]
                    and not phase["error"]
                )
            transformed = target.read_bytes()
            patch_observation = {
                "original_patch_sha256": digest(patch_bytes),
                "original_utils_sha256": original_hash,
                "transformed_utils_sha256": digest(transformed),
                "method": "explicit_git_apply_recount",
                "native_patch_qualification": "unknown",
            }
            details["report_patch"] = patch_observation
            artifacts.extend(
                [
                    {"id": patch_path.name, **budget.capture(patch_bytes)},
                    {"id": "native/scripts/reports/utils.py", **budget.capture(transformed)},
                ]
            )
        if reporting is not None:
            probe = execute(
                "reporting:dependencies",
                [
                    reporting["tool"]["path"],
                    "-I",
                    "-c",
                    "import sys,yaml,pytest; print(sys.version); "
                    "print('PyYAML',yaml.__version__); print('pytest',pytest.__version__); "
                    "sys.exit(0 if sys.version_info[:2] == (3,9) and "
                    "yaml.__version__ == '5.4' and pytest.__version__ == '7.2.0' else 1)",
                ],
                work,
                30,
                budget,
                env,
            )
            phases.append(probe)
            assert probe["exit_code"] == 0 and not probe["timed_out"] and not probe["error"]
            (source / "coding-standards.yml").write_text("report-deviated-alerts: true\n")
        recipe = commands(
            cli=Path(selected.toolchain["tool"]["path"]),
            compiler=compiler,
            pack=pack,
            suite=selected.settings["effective"]["suite"],
            work=work,
            units=["check.cpp"],
            include_dirs=[],
            defines=[],
            scan_config=scan,
            native_source=native,
            reporting=reporting,
            timeout_seconds=180,
        )
        omitted = (
            {"configuration:convert", "configuration:index", "native:report"}
            if reporting is None
            else set()
        )
        details.update(recipe=recipe, report_query_sources=report_manifest)
        for item in recipe:
            if item["name"] in omitted or item["name"] == "native:report":
                continue
            phase = execute(item["name"], item["argv"], work, item["timeout_seconds"], budget, env)
            phases.append(phase)
            print(
                json.dumps({"case": case, "phase": phase["name"], "exit_code": phase["exit_code"]}),
                flush=True,
            )
            assert phase["exit_code"] == 0 and not phase["timed_out"] and not phase["error"], phase[
                "name"
            ]
            assert not any(phase[key]["truncated"] for key in ("stdout", "stderr"))

        diagnostic_queries = [
            report_pack / "Diagnostics" / (name + ".ql")
            for name in ("SuccessfullyExtractedFiles", "ExtractionErrors")
        ]
        cli = selected.toolchain["tool"]["path"]
        phase = execute(
            "extraction:queries",
            [
                cli,
                "database",
                "run-queries",
                "--threads=1",
                "--ram=2048",
                "--additional-packs=" + str(report_pack),
                "--",
                str(work / "database"),
                *map(str, diagnostic_queries),
            ],
            work,
            180,
            budget,
            env,
        )
        phases.append(phase)
        assert phase["exit_code"] == 0 and not phase["timed_out"] and not phase["error"]
        extracted: list[list[str]] = []
        errors: list[list[str]] = []
        details.update(extracted=extracted, extraction_errors=errors)
        for name, rows in (("SuccessfullyExtractedFiles", extracted), ("ExtractionErrors", errors)):
            bqrs = (
                work
                / "database/results/codeql/report-cpp-coding-standards/Diagnostics"
                / (name + ".bqrs")
            )
            phase = execute(
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
                work,
                30,
                budget,
                env,
            )
            phases.append(phase)
            assert phase["exit_code"] == 0 and not phase["timed_out"] and not phase["error"]
            assert not any(phase[key]["truncated"] for key in ("stdout", "stderr"))
            rows.extend(csv.reader(io.StringIO(raw_bytes(phase["stdout"]).decode())))
        artifact_names = [("results.sarif", "sarif"), ("results.csv", "csv")]
        if reporting is not None:
            artifact_names.extend(
                ("source/" + name, "text")
                for name in ("coding-standards.yml", "coding-standards.xml")
            )
        for name, format_name in artifact_names:
            acc = Accumulator(budget, format_name)
            with (work / name).open("rb") as stream:
                while chunk := stream.read(65536):
                    acc.add(chunk)
            artifacts.append({"id": name, **acc.record()})
        files = ["check.cpp"]
        if reporting is not None:
            files.extend(["coding-standards.yml", "coding-standards.xml"])
        normalized_units = extracted_units(extracted, source, files, ["check.cpp"])
        assert not errors and normalized_units == ["check.cpp"]
        assert not any(a["truncated"] for a in artifacts)
        sarif = json.loads(raw_bytes(next(a for a in artifacts if a["id"] == "results.sarif")))
        results = [result for run in sarif["runs"] for result in run.get("results", [])]
        identifier = "cpp/misra/unused-limited-visibility-variable"
        assert any(r["ruleId"] == identifier for r in results) if case == "seeded" else not results
        assert (source / "check.cpp").read_bytes() == source_bytes
        details.update(result_count=len(results), extracted_units=normalized_units)
        if reporting is not None:
            item = next(row for row in recipe if row["name"] == "native:report")
            phase = execute(item["name"], item["argv"], work, item["timeout_seconds"], budget, env)
            phases.append(phase)
            for path in sorted((work / "native-reports").glob("*.md")):
                acc = Accumulator(budget, "text")
                with path.open("rb") as stream:
                    while chunk := stream.read(65536):
                        acc.add(chunk)
                artifacts.append({"id": "native-reports/" + path.name, **acc.record()})
            assert phase["exit_code"] == 0 and not phase["timed_out"] and not phase["error"]
            assert {a["id"] for a in artifacts if a["id"].startswith("native-reports/")} == {
                "native-reports/database_integrity_report.md",
                "native-reports/deviations_report.md",
                "native-reports/guideline_compliance_summary.md",
                "native-reports/guideline_recategorizations_report.md",
            }
            assert not any(a["truncated"] for a in artifacts)
            assert not any(p[key]["truncated"] for p in phases for key in ("stdout", "stderr"))
            for artifact in artifacts:
                if artifact["id"].startswith("source/"):
                    assert digest((work / artifact["id"]).read_bytes()) == artifact["sha256"]
            assert identity_state(reporting)
            assert reporting_profile is not None
            assert read_control(reporting_profile, "/reporting_profile") == reporting_bytes
        assert codeql._manifest(native_root, list(objects), objects) == report_manifest
        for row in report_manifest:
            expected_hash = row["sha256"]
            if patch_observation is not None and row["path"] == "scripts/reports/utils.py":
                expected_hash = patch_observation["transformed_utils_sha256"]
            assert digest((native / row["path"]).read_bytes()) == expected_hash
        assert digest((root / "profiles/gcc11-sanitizers-local-v1.yaml").read_bytes()) == digest(
            compiler_bytes
        )
        assert identity_state(selected.toolchain) and identity_state(compiler)
        _, current_inventory, _, _ = codeql.capabilities(request)
        assert (
            current_inventory["pack_inspection"]["manifest_digest"]
            == inventory["pack_inspection"]["manifest_digest"]
        )
        assert (
            current_inventory["source_inspection"]["files_digest"]
            == inventory["source_inspection"]["files_digest"]
        )
        record = seal(
            {
                "schema_version": 1,
                "kind": "codeql_software_demonstration",
                "case": case,
                "origin": "local_installation_smoke_test",
                "assurance_eligibility": "not_eligible",
                "engineering_readiness": "not_evaluated",
                "accepted_claims": 0,
                "scope": (
                    "Approved software demonstration, synthetic source, MIT queries; "
                    "not target analysis"
                ),
                "prerequisite_inventory": inventory,
                "compiler": compiler,
                "source": {
                    "path": "check.cpp",
                    "sha256": digest(source_bytes),
                    "base64": budget.capture(source_bytes)["base64"],
                },
                "recipe": recipe,
                "omitted_phases": sorted(omitted),
                "phases": phases,
                "artifacts": artifacts,
                "report_query_sources": report_manifest,
                "extracted": extracted,
                "extraction_errors": errors,
                "extracted_units": normalized_units,
                "result_count": len(results),
                "native_reporting_executed": reporting is not None,
                "reporting_toolchain": reporting,
                "report_patch": patch_observation,
                "limitations": [
                    "Full public T011/T012 execution and target acceptance remains unmet",
                    *(
                        ["Demonstration omits unavailable Python/XML/native-report phases"]
                        if reporting is None
                        else ["Reporting runtime assets are a measured subset, not qualification"]
                    ),
                    "Fixture source is synthetic; native commands/results/extraction are genuine",
                    "No acceptance, qualification, publisher authentication or target eligibility",
                    *(
                        ["Explicit Git recount variant does not prove native Bazel patch support"]
                        if patch_observation is not None
                        else []
                    ),
                ],
            }
        )
        destination.write_bytes(canonical(record))
    print(
        json.dumps(
            {
                "case": case,
                "digest": record["digest"],
                "results": len(results),
                "extracted": extracted,
                "output": str(destination),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, choices=["seeded", "corrected"])
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--reporting-profile", type=Path)
    parser.add_argument("--apply-report-patch", action="store_true")
    args = parser.parse_args()
    measure(args.case, args.out, args.reporting_profile, args.apply_report_patch)
