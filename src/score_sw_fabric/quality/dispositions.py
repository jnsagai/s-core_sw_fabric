"""Keep drafts pending and observe corrections only through fresh bounded execution."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from score_sw_fabric.agents.models import input_file, protected_roots
from score_sw_fabric.assurance.models import bounded_list, exact, seal, version
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality import complementary, runner
from score_sw_fabric.quality import disposition_models as dm
from score_sw_fabric.quality.import_models import choice, control, selected_control
from score_sw_fabric.quality.models import baseline, identity_state, load_inputs
from score_sw_fabric.runtime.models import output_path


def execute_current(
    request: Path, adapter: str
) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    """Run adapter-owned commands now; no imported report can substitute for execution."""
    return runner.run(request) if adapter == "clang-tidy" else complementary.run(request, adapter)


def _history(
    base: Path, selected_ref: dict[str, Any], draft: dict[str, Any], subject: dict[str, Any]
) -> tuple[dict[str, Any], list[Path]]:
    """Verify every linked ancestor and protect its bytes; labels grant no authority."""
    paths: list[Path] = []
    seen: set[Path] = set()
    selected = selected_ref
    nearest = None
    child = None
    total = 0
    while True:
        path, record = selected_control(base, selected, max_bytes=dm.MAX_RECORD)
        if path.resolve() in seen:
            raise InputError("DISPOSITION_HISTORY", "Cyclic disposition history")
        seen.add(path.resolve())
        paths.append(path)
        total += len(canonical(record))
        if total > dm.MAX_RECORD or len(paths) > 999:
            raise InputError("LIMIT_EXCEEDED", "History exceeds aggregate byte/revision bounds")
        record = dm.previous(record, draft, subject)
        if child is not None:
            link = child["previous"]
            if (
                record["digest"] != link["digest"]
                or record["state"] != link["state"]
                or record["revision"] + 1 != child["revision"]
            ):
                raise InputError(
                    "DISPOSITION_HISTORY", "Linked history identity or revision differs"
                )
        else:
            nearest = record
        if record["previous"] is None:
            if record["revision"] != 1:
                raise InputError("DISPOSITION_HISTORY", "History root must be revision 1")
            break
        child = record
        selected = record["previous"]["ref"]
        base = path.parent
    assert nearest is not None
    return nearest, paths


def _scope_changes(old: dict[str, Any], current: dict[str, Any], local: bool) -> list[str]:
    reasons = []
    if old["component"] != current["component"] or (
        old["expected_units"] is None
        or current["expected_units"] is None
        or set(old["expected_units"]) != set(current["expected_units"])
    ):
        reasons.append("ANALYSIS_SCOPE_CHANGED")
    if set(dm.files(old["files"])) != set(dm.files(current["files"])):
        reasons.append("CONSTRUCT_SCOPE_CHANGED")
    if old["profile"]["sha256"] != current["profile"]["sha256"]:
        reasons.append("POLICY_CHANGED")
    if local:
        for key, reason in (
            ("toolchain", "TOOL_CHANGED"),
            ("configuration", "CONFIGURATION_CHANGED"),
        ):
            if old[key]["sha256"] != current[key]["sha256"]:
                reasons.append(reason)
        for key in ("translation_units", "include_dirs", "defines", "language"):
            if old[key] != current[key]:
                reasons.append("ANALYSIS_SCOPE_CHANGED")
    return reasons


def _fresh_reasons(
    record: dict[str, Any], expected: dict[str, Any], native_id: str, prior: dict[str, Any]
) -> list[str]:
    reasons = []
    if record["baseline"] != expected or record["source_integrity"] != "unchanged":
        reasons.append("BASELINE_DRIFT")
    if record["extraction"]["adequacy"] != "adequate" or record["outcome"] not in {
        "completed",
        "findings",
    }:
        reasons.append("FRESH_ANALYSIS_INADEQUATE")
    if record["capability"]["state"] != "available":
        reasons.append("CAPABILITY_UNAVAILABLE")
    if record["capability"]["checks"] != prior["capability"]["checks"]:
        reasons.append("CHECK_CONFIGURATION_CHANGED")
    expected_units = expected["expected_units"]
    if not expected_units or set(record["processed_units"]) != set(expected_units):
        reasons.append("EXTRACTION_PARTIAL")
    for phase in record["phases"]:
        finding_exit = (phase["name"].startswith("analyze:") and phase["exit_code"] in {1, 2}) or (
            phase["name"] == "runtime" and phase["exit_code"] == 55
        )
        if (
            phase["timed_out"]
            or phase["error"]
            or (phase["exit_code"] != 0 and not (finding_exit and record["diagnostics"]))
        ):
            reasons.append("PHASE_FAILED")
        if any(phase[key]["truncated"] for key in ("stdout", "stderr")):
            reasons.append("OUTPUT_TRUNCATED")
    if any(artifact["truncated"] for artifact in record["artifacts"]):
        reasons.append("OUTPUT_TRUNCATED")
    # Compliance prerequisites stay visible but do not masquerade as execution failures.
    known = set(record["profile"]["required_obligations"]) | {
        "RULE_MAPPING_UNKNOWN",
        "MANUAL_REVIEW_PENDING",
        "PRODUCTION_AUTHORITY_UNAVAILABLE",
        "TOOL_CONFIDENCE_UNKNOWN",
    }
    execution_gaps = [
        gap
        for gap in record["gaps"]
        if gap not in known
        and not gap.startswith(("CAPABILITY_NOT_SELECTED:", "ADAPTER_UNIMPLEMENTED:"))
    ]
    reasons.extend(execution_gaps)
    if any(f["native_id"] == native_id for f in record["diagnostics"]):
        reasons.append("FINDING_STILL_PRESENT")
    return reasons


def review(
    request_path: Path, out: Path | None = None
) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    """Publish a proposal/history observation, never authenticated engineering acceptance."""
    request_path = request_path.absolute()
    request = version(
        control(request_path, yaml=True),
        "quality_disposition_request",
        dm.REQUEST_FIELDS,
        "/request",
    )
    base = request_path.parent
    action = choice(request["action"], {"draft", "check_correction"}, "/action")
    current_selection = exact(request["current"], {"adapter", "request"}, "/current")
    adapter = choice(
        current_selection["adapter"], {"clang-tidy", "cppcheck", "asan", "ubsan"}, "/adapter"
    )
    origin_path, original = selected_control(base, request["origin"], max_bytes=dm.MAX_RECORD)
    original, findings, origin_adapter = dm.origin(original)
    draft_path, draft = selected_control(base, request["draft"])
    draft = dm.draft(draft, original, findings)
    if action == "check_correction" and draft["requested_kind"] != "correction":
        raise InputError(
            "DISPOSITION_KIND", "Only a correction proposal can execute a correction check"
        )
    current_path, current_bytes = input_file(base, current_selection["request"], "/current/request")
    if len(current_bytes) > 1024 * 1024:
        raise InputError("LIMIT_EXCEEDED", "Current run request exceeds 1 MiB")
    current = load_inputs(current_path, "run", adapter)
    current_baseline = baseline(current)
    subject = seal(
        {
            "origin_ref": request["origin"],
            "origin_digest": original["digest"],
            "origin_class": original["origin"],
            "finding_index": draft["finding_index"],
            "finding": findings[draft["finding_index"]],
            "baseline": original["baseline"],
        }
    )
    inputs = [request_path, origin_path, draft_path, current_path, *current.inputs]
    protected = [
        *protected_roots(
            base,
            bounded_list(request["protected_roots"], 32, "/protected_roots"),
            "/protected_roots",
        ),
        *current.protected,
    ]
    if origin_adapter is None:
        from score_sw_fabric.quality.import_models import native_root

        protected.append(native_root(original["baseline"]["root"]))
    # Resolve proposal references relative to the draft, preserving original references.
    reference_bytes = 0
    for key in ("compensating_evidence", "decision_refs"):
        for ref in draft[key]:
            path, data = input_file(draft_path.parent, ref, "/draft/" + key)
            reference_bytes += len(data)
            if reference_bytes > 64 * 1024 * 1024:
                raise InputError("LIMIT_EXCEEDED", "Proposal reference bytes exceed 64 MiB")
            inputs.append(path)
    previous = None
    revision = 1
    prior = None
    if request["previous"] is not None:
        prior, history_paths = _history(base, request["previous"], draft, subject)
        inputs.extend(history_paths)
        previous = {"ref": request["previous"], "digest": prior["digest"], "state": prior["state"]}
        revision = prior["revision"] + 1
    if out is not None:
        output_path(out, inputs, protected)
    observed = datetime.now(UTC)
    reasons = _scope_changes(original["baseline"], current_baseline, origin_adapter is not None)
    if origin_adapter is not None:
        if origin_adapter != adapter:
            reasons.append("TOOL_CHANGED")
        if original["profile"] != current.profile:
            reasons.append("POLICY_CHANGED")
        if original["toolchain"] != current.toolchain:
            reasons.append("TOOL_CHANGED")
    if not identity_state(current.toolchain):
        reasons.append("CAPABILITY_UNAVAILABLE")
    if (
        draft["expires_at"] is not None
        and dm.timestamp(draft["expires_at"], "/expires_at") <= observed
    ):
        reasons.append("DISPOSITION_EXPIRED")
    stale_reasons = list(reasons)
    path = draft["construct"]["path"]
    changed = dm.files(current_baseline["files"]).get(path) != draft["construct"]["sha256"]
    if action == "draft" and prior is not None and prior["state"] == "corrected":
        if prior["current_baseline"] != current_baseline:
            stale_reasons.append("DISPOSITION_STALE")
            reasons.append("DISPOSITION_STALE")
    if draft["requested_kind"] != "correction" and changed:
        stale_reasons.append("CONSTRUCT_CHANGED")
        reasons.append("CONSTRUCT_CHANGED")
    if draft["decision_refs"]:
        reasons.append("DECISION_NOT_REPRODUCED")
    if draft["requested_kind"] in {"deviation", "recategorization", "suppression"}:
        reasons.append("DEVIATION_POLICY_UNKNOWN")
    fresh = None
    if stale_reasons:
        state = "stale"
    elif draft["requested_kind"] != "correction":
        state = "pending_review"
        reasons.append("HUMAN_REVIEW_PENDING")
    elif action == "draft":
        state = "open"
        reasons.append("FRESH_ANALYSIS_REQUIRED")
    elif origin_adapter is None:
        state = "blocked"
        reasons.append("IMPORTED_CORRECTION_SCOPE_UNVERIFIED")
    elif not changed:
        state = "open"
        reasons.append("TRACKED_SOURCE_UNCHANGED")
    else:
        # Refreeze the selected transport before execution; the adapter checks all actual inputs.
        _, repeated = input_file(base, current_selection["request"], "/current/request")
        if repeated != current_bytes:
            raise InputError("INPUT_DRIFT", "Current request changed after validation")
        _, fresh, run_inputs, run_protected = execute_current(current_path, adapter)
        inputs.extend(run_inputs)
        protected.extend(run_protected)
        reasons.extend(
            _fresh_reasons(fresh, current_baseline, subject["finding"]["native_id"], original)
        )
        observed = datetime.now(UTC)
        if (
            draft["expires_at"] is not None
            and dm.timestamp(draft["expires_at"], "/expires_at") <= observed
        ):
            reasons.append("DISPOSITION_EXPIRED")
        if "BASELINE_DRIFT" in reasons or "DISPOSITION_EXPIRED" in reasons:
            state = "stale"
        elif "FINDING_STILL_PRESENT" in reasons:
            state = "open"
        elif reasons:
            state = "blocked"
        else:
            state = "corrected"
            reasons.append("FRESH_LOCAL_CORRECTION_OBSERVED")
    record = seal(
        {
            "schema_version": 1,
            "kind": "quality_disposition_review",
            "draft": draft,
            "subject": subject,
            "current_baseline": current_baseline,
            "fresh_run": fresh,
            "previous": previous,
            "revision": revision,
            "observed_at": observed.isoformat(),
            "time_basis": "local_untrusted",
            "state": state,
            "reasons": sorted(set(reasons)),
            "outcome": "completed" if state == "corrected" else "unresolved",
            "origin": "local_unprotected_execution",
            "assurance_eligibility": "not_eligible",
            "engineering_readiness": "not_evaluated",
            "limitations": [
                "Proposals, native metadata, category and previous states are unauthenticated.",
                "Historical origin labels and seals cannot authenticate earlier execution.",
                "Whole-file scope; matching checks anywhere in the component remain open.",
                "Fresh execution is local and unprotected; mapping and acceptance remain pending.",
                "005 decision replay and protected production authority remain unavailable.",
            ],
        }
    )
    if len(canonical(record)) > dm.MAX_RECORD:
        raise InputError("LIMIT_EXCEEDED", "Disposition review exceeds 96 MiB")
    if out is not None:
        output_path(out, inputs, protected)
    return 0 if state == "corrected" else 1, record, inputs, protected
