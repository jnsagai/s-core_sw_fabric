"""Measure declared guideline coverage while retaining every unresolved obligation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from score_sw_fabric.agents.models import input_file, protected_roots
from score_sw_fabric.assurance.models import bounded_list, digest, exact, seal, version
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality import coverage_models as cm
from score_sw_fabric.quality import disposition_models as dm
from score_sw_fabric.quality import imports
from score_sw_fabric.quality.import_models import (
    bounded_tree,
    control,
    freeze_baseline,
    selected_control,
    strings,
)
from score_sw_fabric.quality.models import raw_bytes
from score_sw_fabric.quality.profile import load_profile
from score_sw_fabric.runtime.models import output_path
from score_sw_fabric.runtime.request import parse_json


def _selected_check(report: dict[str, Any], mechanism: dict[str, Any]) -> bool:
    """Only retained matching local check selection can support a clean structural observation."""
    for artifact in report["artifacts"]:
        if artifact["role"] != "log" or artifact["raw"]["truncated"]:
            continue
        data = raw_bytes(artifact["raw"])
        if not data.lstrip().startswith(b"{"):
            continue
        try:
            record = parse_json(data, "/original_run")
            bounded_tree(record)
            local, _, adapter = dm.origin(record)
        except (InputError, RecursionError, ValueError):
            continue
        if adapter != mechanism["tool"] or local["capability"]["state"] != "available":
            continue
        b = local["baseline"]
        imported = report["baseline"]
        identities = {i["id"]: i for i in report["identities"]}
        identity = identities[adapter]
        if (
            b["component"] != imported["component"]
            or b["files"] != imported["files"]
            or b["expected_units"] != imported["expected_units"]
            or b["profile"]["sha256"] != imported["profile"]["sha256"]
            or local["profile"] != report["profile"]
            or local["toolchain"]["tool"]["sha256"] != identity["tool_sha256"]
            or local["toolchain"]["tool"]["version"] != identity["version"]
            or b["configuration"]["sha256"] != identity["config_sha256"]
            or local["source_integrity"] != "unchanged"
            or local["extraction"]["adequacy"] != "adequate"
            or local["outcome"] not in {"completed", "findings"}
            or not b["expected_units"]
            or set(local["processed_units"]) != set(b["expected_units"])
        ):
            continue
        if mechanism["native_id"] in local["capability"]["checks"]:
            if adapter == "clang-tidy":
                probes = [p for p in local["phases"] if p["name"] == "list-checks"]
                if len(probes) != 1:
                    continue
                measured = [
                    line.strip()
                    for line in raw_bytes(probes[0]["stdout"])
                    .decode("utf-8", "replace")
                    .splitlines()
                    if line.startswith("    ") and line.strip()
                ]
                if measured != local["capability"]["checks"]:
                    continue
            # Phase failure/truncation cannot be hidden by declaring extraction adequate.
            if all(
                not p["timed_out"]
                and p["error"] is None
                and p["exit_code"] == 0
                and not p["stdout"]["truncated"]
                and not p["stderr"]["truncated"]
                for p in local["phases"]
            ) and not any(a["truncated"] for a in local["artifacts"]):
                return True
    return False


def _mechanism(mechanism: dict[str, Any], analyses: list[dict[str, Any]]) -> dict[str, Any]:
    reasons: list[str] = []
    state = "unknown"
    findings: list[dict[str, Any]] = []
    selected_reports = []
    if mechanism["kind"] == "tool":
        for entry in analyses:
            report = entry["report"]
            matches = [
                i
                for i in report["identities"]
                if i["id"] == mechanism["tool"] and digest(i) == mechanism["identity_digest"]
            ]
            if not matches:
                continue
            findings.extend(
                {"analysis_digest": report["digest"], "finding": finding}
                for finding in report["findings"]
                if finding["tool"] == mechanism["tool"]
                and finding["native_id"] == mechanism["native_id"]
            )
            if len(findings) > 10000:
                raise InputError("LIMIT_EXCEEDED", "Mechanism finding associations exceed 10000")
            if entry["current"]:
                selected_reports.append(report)
            else:
                reasons.extend(entry["reasons"])
    if findings:
        state = "findings_open"
        reasons.append("NATIVE_FINDING_OPEN")
    elif mechanism["kind"] in {"manual", "audit"}:
        state = "pending_manual"
        reasons.append("MANUAL_REVIEW_PENDING")
    elif mechanism["kind"] == "unsupported" or mechanism["availability"] == "unsupported":
        state = "unsupported"
        reasons.append("MECHANISM_UNSUPPORTED")
    elif mechanism["availability"] == "unknown":
        reasons.append("MECHANISM_AVAILABILITY_UNKNOWN")
    elif mechanism["automation_class"] in {"partial", "audit"}:
        state = "pending_manual"
        reasons.append(
            "PARTIAL_AUTOMATION_REQUIRES_REVIEW"
            if mechanism["automation_class"] == "partial"
            else "AUDIT_REVIEW_PENDING"
        )
        if mechanism["enabled"] is not True:
            reasons.append("CHECK_NOT_SELECTED")
    elif mechanism["enabled"] is not True:
        state = "unsupported" if mechanism["enabled"] is False else "unknown"
        reasons.append("CHECK_NOT_SELECTED")
    elif mechanism["tool"] == "codeql":
        state = "unsupported"
        reasons.extend(["CODEQL_ELIGIBILITY_UNKNOWN", "PRIMARY_EXECUTION_UNAVAILABLE"])
    elif not selected_reports:
        reasons.append("CURRENT_ANALYSIS_MISSING")
    elif any(
        r["extraction"]["adequacy"] != "adequate" or r["outcome"] not in {"completed", "findings"}
        for r in selected_reports
    ):
        reasons.append("ANALYSIS_INADEQUATE")
    elif any("UNAPPROVED_SUPPRESSION" in r["gaps"] for r in selected_reports):
        reasons.append("SUPPRESSION_PENDING_REVIEW")
    elif all(_selected_check(r, mechanism) for r in selected_reports):
        state = "covered"
    else:
        reasons.append("CHECK_SELECTION_UNVERIFIED")
    return {
        "selection": mechanism,
        "state": state,
        "reasons": sorted(set(reasons)),
        "findings": findings,
    }


def _cell(
    name: str,
    expectation: dict[str, Any] | None,
    mapping: dict[str, Any] | None,
    analyses: list[dict[str, Any]],
) -> dict[str, Any]:
    reasons = []
    mechanisms = [_mechanism(m, analyses) for m in mapping["mechanisms"]] if mapping else []
    findings_by_id = {
        (finding["analysis_digest"], finding["finding"]["id"]): finding
        for m in mechanisms
        for finding in m["findings"]
    }
    findings = list(findings_by_id.values())
    if len(findings) > 10000:
        raise InputError("LIMIT_EXCEEDED", "Cell finding associations exceed 10000")
    references = [expectation, mapping, *(m["selection"] for m in mechanisms)]
    for item in references:
        if item is not None and not item["source_ids"]:
            reasons.append("GUIDELINE_SOURCE_UNKNOWN")
    if expectation is None or expectation["native_category"] is None:
        reasons.append("GUIDELINE_CATEGORY_UNKNOWN")
    if mapping is None:
        reasons.append("MAPPING_ROW_MISSING")
    if expectation is None or expectation["applicability"] == "unknown":
        reasons.append("GUIDELINE_APPLICABILITY_UNKNOWN")
    if expectation is not None and expectation["applicability"] == "not_applicable":
        reasons.append("EXCLUSION_PENDING_REVIEW")
    reasons.extend(r for m in mechanisms for r in m["reasons"])
    if mapping is not None and mapping["manual_evidence"]:
        reasons.append("MANUAL_REVIEW_PENDING")
    if mapping is not None:
        available = {
            artifact["id"]
            for entry in analyses
            if entry["current"]
            for artifact in entry["report"]["artifacts"]
            if not artifact["raw"]["truncated"]
        }
        if not set(mapping["expected_evidence"]).issubset(available):
            reasons.append("EXPECTED_EVIDENCE_MISSING")
    if mapping is not None and not mechanisms:
        reasons.append("MECHANISM_MISSING")
    if findings:
        state = "findings_open"
    elif any(
        r in reasons
        for r in (
            "GUIDELINE_SOURCE_UNKNOWN",
            "GUIDELINE_CATEGORY_UNKNOWN",
            "MAPPING_ROW_MISSING",
            "GUIDELINE_APPLICABILITY_UNKNOWN",
        )
    ):
        state = "unknown"
    elif "EXCLUSION_PENDING_REVIEW" in reasons:
        state = "excluded_pending_review"
    elif "MANUAL_REVIEW_PENDING" in reasons or any(
        m["state"] == "pending_manual" for m in mechanisms
    ):
        state = "pending_manual"
    elif any(m["state"] == "unsupported" for m in mechanisms):
        state = "unsupported"
    elif mechanisms and all(m["state"] == "covered" for m in mechanisms) and not reasons:
        state = "covered"
    else:
        state = "unknown"
    return {
        "guideline_id": name,
        "expectation": expectation,
        "mapping": mapping,
        "state": state,
        "reasons": sorted(set(reasons)),
        "mechanisms": mechanisms,
        "findings": findings,
    }


def measure(
    request_path: Path, out: Path | None = None
) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    request_path = request_path.absolute()
    request = version(
        control(request_path, yaml=True), "quality_coverage_request", cm.REQUEST_FIELDS, "/request"
    )
    base = request_path.parent
    profile_ref = dm.ref(request["profile"], "/profile")
    profile_path = profile_ref["path"]
    # Bound selected YAML before the shared byte/hash/profile reader.
    from score_sw_fabric.runtime.request import _local

    control(_local(base, profile_path, "/profile"), yaml=True)
    pp, data = input_file(base, request["profile"], "/profile")
    profile = load_profile(data)
    baseline, _, _, paths, root = freeze_baseline(base, request["baseline"], request["profile"])
    inputs = [request_path, pp, *paths]
    protected = [
        root,
        *protected_roots(
            base,
            bounded_list(request["protected_roots"], 32, "/protected_roots"),
            "/protected_roots",
        ),
    ]
    mp, m = selected_control(base, request["manifest"])
    m = cm.manifest(m)
    inputs.append(mp)
    if (
        m["scope"]["component"] != baseline["component"]
        or set(m["scope"]["files"]) != {f["path"] for f in baseline["files"]}
        or (m["scope"]["translation_units"] is None) != (baseline["expected_units"] is None)
        or set(m["scope"]["translation_units"] or []) != set(baseline["expected_units"] or [])
    ):
        raise InputError("SCOPE_MISMATCH", "Guideline scope differs from frozen component")
    sources = []
    source_records = {}
    source_total = 0
    for source in m["source_refs"]:
        sp, record = selected_control(mp.parent, source["ref"])
        version(record, "quality_guideline_source", cm.SOURCE_FIELDS, "/source")
        if any(record[k] != source[k] for k in ("id", "license", "notice", "native_status")):
            raise InputError("SOURCE_REF", "Guideline source metadata differs from original")
        strings(record["guideline_ids"], "/source/guideline_ids", 1000)
        source_total += len(canonical(record))
        if source_total > 16 * 1024 * 1024:
            raise InputError("LIMIT_EXCEEDED", "Guideline sources exceed 16 MiB")
        source_records[source["id"]] = record
        sources.append({"selection": source, "record": record})
        inputs.append(sp)
    expected = {r["guideline_id"]: r for r in m["expected_guidelines"] or []}
    mappings = {r["guideline_id"]: r for r in m["rows"]}
    for name in expected.keys() | mappings.keys():
        mapping = mappings.get(name)
        linked = [
            expected.get(name),
            mapping,
            *(mapping["mechanisms"] if mapping is not None else []),
        ]
        for row in linked:
            if row is not None and any(
                name not in source_records[s]["guideline_ids"] for s in row["source_ids"]
            ):
                raise InputError("SOURCE_REF", "Selected source does not list the guideline")
    previous = None
    changes = []
    if request["previous_manifest"] is not None:
        prev_path, prior = selected_control(base, request["previous_manifest"])
        prior = cm.manifest(prior)
        inputs.append(prev_path)
        for source in prior["source_refs"]:
            inputs.append(_local(prev_path.parent, source["ref"]["path"], "/previous/source_ref"))
        previous = {"ref": request["previous_manifest"], "manifest": prior}
        old = {r["guideline_id"]: r for r in prior["expected_guidelines"] or []}
        old_rows = {r["guideline_id"]: r for r in prior["rows"]}
        for name in sorted(old.keys() | old_rows.keys() | expected.keys() | mappings.keys()):
            before = {"expectation": old.get(name), "mapping": old_rows.get(name)}
            after = {"expectation": expected.get(name), "mapping": mappings.get(name)}
            if before != after:
                changes.append({"guideline_id": name, "previous": before, "current": after})
        if any(prior[k] != m[k] for k in ("scope", "source_refs", "origin")):
            changes.append(
                {
                    "guideline_id": None,
                    "previous": {k: prior[k] for k in ("scope", "source_refs", "origin")},
                    "current": {k: m[k] for k in ("scope", "source_refs", "origin")},
                }
            )
    analyses = []
    selected_pairs = bounded_list(request["analyses"], 20, "/analyses")
    total = 0
    seen = set()
    for pair in selected_pairs:
        exact(pair, {"request", "report"}, "/analysis")
        ap, _ = selected_control(base, pair["request"], yaml=True)
        rp, report = selected_control(base, pair["report"], max_bytes=dm.MAX_RECORD)
        identity = (ap.resolve(), rp.resolve())
        if identity in seen:
            raise InputError("DUPLICATE_ID", "Duplicate analysis selection")
        seen.add(identity)
        total += len(canonical(report))
        if total > dm.MAX_RECORD:
            raise InputError("LIMIT_EXCEEDED", "Selected analysis records exceed 96 MiB")
        _, reproduced, analysis_inputs, analysis_protected = imports.import_outputs(ap)
        if reproduced != report:
            raise InputError(
                "ANALYSIS_NOT_REPRODUCED", "Selected import differs from original replay"
            )
        drift = []
        for key in ("component", "files", "expected_units", "identities", "profile"):
            if report["baseline"][key] != baseline[key]:
                drift.append("BASELINE_DRIFT:" + key)
        analyses.append(
            {"selection": pair, "report": report, "current": not drift, "reasons": sorted(drift)}
        )
        inputs.extend([ap, rp, *analysis_inputs])
        protected.extend(analysis_protected)
    if out is not None:
        output_path(out, inputs, protected)
    rows = []
    row_bytes = total
    for name in sorted(expected.keys() | mappings.keys()):
        row = _cell(name, expected.get(name), mappings.get(name), analyses)
        row_bytes += len(canonical(row))
        if row_bytes > dm.MAX_RECORD:
            raise InputError("LIMIT_EXCEEDED", "Coverage associations exceed 96 MiB")
        rows.append(row)
    counts = {state: sum(row["state"] == state for row in rows) for state in sorted(cm.STATES)}
    gaps = list(profile["required_obligations"]) + [
        "RULE_MAPPING_UNKNOWN",
        "PRODUCTION_AUTHORITY_UNAVAILABLE",
        "GUIDELINE_REVIEW_PENDING",
    ]
    if m["expected_guidelines"] is None:
        gaps.append("GUIDELINE_DENOMINATOR_UNKNOWN")
    if baseline["expected_units"] is None or not baseline["expected_units"]:
        gaps.append("ANALYSIS_SCOPE_UNKNOWN")
    for row in rows:
        if row["state"] != "covered":
            gaps.append("GUIDELINE_UNRESOLVED:" + row["guideline_id"])
        gaps.extend(row["reasons"])
    for entry in analyses:
        gaps.extend(entry["reasons"])
        gaps.extend(entry["report"]["gaps"])
    if changes:
        gaps.append("GUIDELINE_DECLARATION_CHANGED")
    record = seal(
        {
            "schema_version": 1,
            "kind": "quality_guideline_matrix",
            "profile": profile,
            "baseline": baseline,
            "manifest": m,
            "sources": sources,
            "analyses": analyses,
            "previous": previous,
            "changes": changes,
            "scope_state": "unknown" if m["expected_guidelines"] is None else "declared",
            "denominator": None if m["expected_guidelines"] is None else len(expected),
            "rows": rows,
            "counts": counts,
            "gaps": sorted(set(gaps)),
            "accepted_claims": 0,
            "outcome": "incomplete" if gaps else "completed",
            "origin": "local_unprotected_evaluation",
            "assurance_eligibility": "not_eligible",
            "engineering_readiness": "not_evaluated",
            "limitations": [
                "Declared denominator, categories and source associations await authorized review.",
                "Covered measures local observations; engineering acceptance stays pending.",
                "Manual/audit/partial review and exclusions are never discharged by this command.",
                "Suppressed findings and dispositions cannot remove coverage obligations.",
                "CodeQL primary execution and protected authority remain unavailable.",
                "Prior declarations are unverified history, not current evidence.",
            ],
        }
    )
    if len(canonical(record)) > dm.MAX_RECORD:
        raise InputError("LIMIT_EXCEEDED", "Guideline matrix exceeds 96 MiB")
    bounded_tree(record)
    if control(request_path, yaml=True) != request:
        raise InputError("INPUT_DRIFT", "Coverage request changed during evaluation")
    for key in ("manifest", "previous_manifest"):
        if request[key] is not None:
            selected_control(base, request[key])
    for source in m["source_refs"]:
        selected_control(mp.parent, source["ref"])
    for pair in selected_pairs:
        ap, _ = selected_control(base, pair["request"], yaml=True)
        _, expected_report = selected_control(base, pair["report"], max_bytes=dm.MAX_RECORD)
        _, refreshed, _, _ = imports.import_outputs(ap)
        if refreshed != expected_report:
            raise InputError("INPUT_DRIFT", "Analysis originals changed during coverage evaluation")
    _, repeated = input_file(base, request["profile"], "/profile")
    if (
        repeated != data
        or freeze_baseline(base, request["baseline"], request["profile"])[0] != baseline
    ):
        raise InputError("INPUT_DRIFT", "Current coverage baseline changed")
    if out is not None:
        output_path(out, inputs, protected)
    return 1 if gaps else 0, record, inputs, protected
