"""Native outputs imported without analyzer execution or authority upgrades."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from score_sw_fabric.assurance.models import nonempty, seal
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality import cppcheck, extraction, native_outputs, sanitizers, sarif
from score_sw_fabric.quality.import_models import ImportInputs, bounded_tree, load_import
from score_sw_fabric.quality.models import MAX_ARTIFACT, raw_bytes
from score_sw_fabric.runtime.models import output_path
from score_sw_fabric.runtime.request import parse_yaml


def import_outputs(
    request_path: Path, out: Path | None = None
) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    selected = load_import(request_path, out)
    record = evaluate(selected, request_path.absolute().parent)
    if out is not None:
        output_path(out, [request_path, *selected.inputs], selected.protected)
    return 0 if record["outcome"] == "completed" else 1, record, selected.inputs, selected.protected


def evaluate(
    selected: ImportInputs,
    base: Path,
    *,
    resolve: Callable[[Path, Any], tuple[Path, bytes]] | None = None,
) -> dict[str, Any]:
    """Derive observations from frozen bytes; portable replay supplies an archive resolver."""
    findings: list[dict[str, Any]] = []
    for artifact in selected.artifacts:
        if artifact["role"] != "diagnostics" or artifact["raw"]["truncated"]:
            continue
        data = raw_bytes(artifact["raw"])
        if len(data) > MAX_ARTIFACT:
            raise InputError("LIMIT_EXCEEDED", "Native parser input exceeds bounded retention")
        root = Path(artifact["source_root"])
        tool = artifact["tool"]
        format = artifact["format"]
        if format == "sarif-2.1.0":
            results, gaps = sarif.parse_report(
                data, artifact["id"], root, selected.files, selected.identities[tool]
            )
            selected.gaps.extend(gaps)
        elif format == "clang-tidy-text":
            results = []
            if data:
                selected.gaps.append("NATIVE_OUTPUT_UNSUPPORTED")
        elif format == "clang-tidy-yaml":
            try:
                # Export-fixes needs no YAML anchors; refuse alias expansion before construction.
                if any(
                    isinstance(token, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken))
                    for token in yaml.scan(data)
                ):
                    raise InputError("NATIVE_OUTPUT_UNSUPPORTED", "Native YAML anchors unsupported")
                native = parse_yaml(data, "/native")
                bounded_tree(native)
                if isinstance(native, dict) and "MainSourceFile" in native:
                    main = native["MainSourceFile"]
                    if not isinstance(main, str):
                        raise InputError("NATIVE_OUTPUT_INVALID", "Malformed main source filename")
                    main_path = Path(main)
                    main_path = main_path if main_path.is_absolute() else root / main_path
                    if (
                        not main_path.is_relative_to(root)
                        or str(main_path.relative_to(root)) not in artifact["units"]
                    ):
                        raise InputError(
                            "NATIVE_LOCATION_UNRESOLVED", "Main source is not selected"
                        )
            except (RecursionError, yaml.YAMLError) as exc:
                raise InputError(
                    "NATIVE_OUTPUT_INVALID", "Malformed or deeply nested native YAML"
                ) from exc
            results = native_outputs.diagnostics(
                data, artifact["id"], root, selected.files, include_ranges=True
            )
            if any(str(r["native_id"]).startswith("clang-diagnostic-") for r in results):
                selected.gaps.append("COMPILER_DIAGNOSTIC")
        elif format == "cppcheck-xml":
            results = cppcheck.parse_report(
                data,
                artifact["id"],
                root,
                selected.files,
                selected.identities[tool]["version"].removeprefix("Cppcheck "),
            )
            if any(r["native_id"] in cppcheck.INCOMPLETE_IDS for r in results):
                selected.gaps.append("CPPCHECK_ANALYSIS_INCOMPLETE")
        else:
            selected.gaps.extend(sanitizers.leak_runtime_gaps(data, tool))
            results = sanitizers.diagnostic_records(
                {"stderr": artifact["raw"]}, tool, root, selected.files
            )
            for result in results:
                result["artifact_id"] = artifact["id"]
            # Fatal signals/unrecognized reports are not silently clean sanitizer evidence.
            text = data.decode("utf-8", "replace")
            if not results and any(
                s in text for s in ("DEADLYSIGNAL", "runtime error:", "ERROR:", "SUMMARY:")
            ):
                selected.gaps.append("SANITIZER_RUNTIME_INCOMPLETE")
        for result in results:
            if len(result["locations"]) > 1000:
                raise InputError("LIMIT_EXCEEDED", "Too many aggregate native result locations")
            nonempty(result["native_id"], "/native_id", max_length=1024)
            if result["native_level"] is not None and not isinstance(result["native_level"], str):
                raise InputError("NATIVE_OUTPUT_INVALID", "Malformed native severity")
            if result["native_level"] is None:
                selected.gaps.append("NATIVE_LEVEL_UNKNOWN")
            if tool in {"asan", "ubsan"} and not result["locations"]:
                selected.gaps.append("NATIVE_LOCATION_UNRESOLVED")
            result["tool"] = tool
        findings.extend(results)
        if len(findings) > 10000:
            raise InputError("LIMIT_EXCEEDED", "Too many aggregate native findings")
        if any(result.get("suppressions") for result in results):
            selected.gaps.append("UNAPPROVED_SUPPRESSION")
    for data in selected.files.values():
        text = data.decode("utf-8", "replace")
        if "NOLINT" in text or "cppcheck-suppress" in text:
            selected.gaps.append("UNAPPROVED_SUPPRESSION")
    assessment = extraction.assess(selected, findings, base, resolve=resolve)
    normalized = native_outputs.normalize(
        findings, selected.baseline["full_digest"], selected.identities
    )
    gaps = sorted(
        set(
            assessment["gaps"]
            + selected.profile["required_obligations"]
            + [
                "RULE_MAPPING_UNKNOWN",
                "MANUAL_REVIEW_PENDING",
                "TOOL_CONFIDENCE_UNKNOWN",
                "PRODUCTION_AUTHORITY_UNAVAILABLE",
                "IMPORTED_EXECUTION_UNVERIFIED",
            ]
        )
    )
    if "codeql" in selected.identities:
        gaps = sorted(set(gaps + ["CODEQL_ELIGIBILITY_UNKNOWN", "QUERY_SOURCE_BUILD_UNRECONCILED"]))
    outcome = (
        "incomplete"
        if assessment["adequacy"] != "adequate"
        else "findings"
        if normalized
        else "completed"
    )
    record = seal(
        {
            "schema_version": 1,
            "kind": "quality_native_import",
            "profile": selected.profile,
            "baseline": selected.baseline,
            "identities": list(selected.identities.values()),
            "artifacts": selected.artifacts,
            "findings": normalized,
            "extraction": assessment,
            "gaps": gaps,
            "outcome": outcome,
            "origin": selected.request["origin"],
            "assurance_eligibility": "not_eligible",
            "engineering_readiness": "not_evaluated",
            "limitations": [
                "Native bindings and imported phase claims are unauthenticated.",
                "Original output is preserved; normalized findings are derived indexes.",
                "No analyzer execution, engineering decision or compliance is accepted.",
            ],
        }
    )
    return record
