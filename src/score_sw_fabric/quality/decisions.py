"""Bind quality proposals to independently replayed 005 fixture human decisions."""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path
from typing import Any

from score_sw_fabric.agents.models import input_file, protected_roots
from score_sw_fabric.assurance.decisions import classify_decision, reconcile_decisions
from score_sw_fabric.assurance.gates import evaluate_gate
from score_sw_fabric.assurance.models import bounded_list, digest, exact, seal, version
from score_sw_fabric.assurance.package import verify_assessment
from score_sw_fabric.assurance.reader import safe_path
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality import decision_models as models
from score_sw_fabric.quality import disposition_models as dm
from score_sw_fabric.quality import dispositions
from score_sw_fabric.quality.import_models import choice, control, selected_control
from score_sw_fabric.quality.models import baseline, load_inputs
from score_sw_fabric.quality.models import digest as byte_digest
from score_sw_fabric.runtime.models import output_path


def _binding(path: Path, request: dict[str, Any]) -> tuple[dict[str, Any], list[Path], list[Path]]:
    base = path.absolute().parent
    disposition_path, selection = selected_control(base, request["disposition_request"], yaml=True)
    version(selection, "quality_disposition_request", dm.REQUEST_FIELDS, "/disposition_request")
    if selection["action"] != "draft":
        raise InputError("DISPOSITION_ACTION", "Decision preparation requires action draft")
    # Freeze the selection again immediately before the no-execution draft reader.
    selected_control(base, request["disposition_request"], yaml=True)
    _, refreshed, inputs, protected = dispositions.review(disposition_path, draft_only=True)
    selected_control(base, request["disposition_request"], yaml=True)
    review_path, review = selected_control(base, request["review"], max_bytes=dm.MAX_RECORD)
    dm.previous(review, refreshed["draft"], refreshed["subject"], max_revision=1000)
    inputs.extend([path.absolute(), review_path])
    if review["previous"] is not None:
        _, ancestors = dispositions._history(
            review_path.parent, review["previous"]["ref"], review["draft"], review["subject"]
        )
        inputs.extend(ancestors)
        parent_path, parent = selected_control(
            review_path.parent, review["previous"]["ref"], max_bytes=dm.MAX_RECORD
        )
        link = review["previous"]
        if (
            parent["digest"] != link["digest"]
            or parent["state"] != link["state"]
            or parent["revision"] + 1 != review["revision"]
        ):
            raise InputError("DISPOSITION_HISTORY", "Selected review history differs")
        inputs.append(parent_path)
    elif review["revision"] != 1:
        raise InputError("DISPOSITION_HISTORY", "Selected history root must have revision 1")
    current_path, _ = input_file(
        disposition_path.parent, selection["current"]["request"], "/current/request"
    )
    current = load_inputs(current_path, "run", selection["current"]["adapter"])
    frozen = baseline(current)
    if frozen != refreshed["current_baseline"]:
        raise InputError("INPUT_DRIFT", "Current baseline changed during preparation")
    p, policy_paths = models.policy(base, request["policy"])
    inputs.extend([*current.inputs, *policy_paths])
    protected.extend(current.protected)
    protected.extend(
        protected_roots(
            base,
            bounded_list(request["protected_roots"], 32, "/protected_roots"),
            "/protected_roots",
        )
    )
    finding_tool = review["subject"]["finding"].get("tool", current.adapter)
    reasons = models.permission(p, review, finding_tool)
    if (
        refreshed["state"] == "stale"
        or review["current_baseline"] != frozen
        or dm.files(review["subject"]["baseline"]["files"]) != dm.files(frozen["files"])
    ):
        reasons.append("DISPOSITION_STALE")
        reasons.extend(
            r
            for r in refreshed["reasons"]
            if r
            not in {"HUMAN_REVIEW_PENDING", "DEVIATION_POLICY_UNKNOWN", "DECISION_NOT_REPRODUCED"}
        )
    required = []
    if p is not None:
        required = [
            {"path": p["source_prefix"] + "/" + name, "sha256": byte_digest(data)}
            for name, data in sorted(current.data.items())
        ]
        required.append({"path": p["source_path"], "sha256": p["source_ref"]["sha256"]})
    binding = seal(
        {
            "schema_version": 1,
            "kind": "quality_disposition_binding",
            "review": review,
            "policy": p,
            "current_baseline": frozen,
            "current_context": {
                "adapter": current.adapter,
                "profile": current.profile,
                "toolchain": current.toolchain,
                "configuration_sha256": byte_digest(current.config),
                "settings": current.settings,
                "assets": {
                    name: byte_digest(data) for name, data in sorted(current.assets.items())
                },
            },
            "required_files": required,
            "reasons": sorted(set(reasons)),
            "outcome": "blocked" if reasons else "emitted",
            "origin": "local_unprotected_execution",
            "assurance_eligibility": "not_eligible",
            "engineering_readiness": "not_evaluated",
        }
    )
    _bounded(binding)
    return binding, inputs, protected


def _bounded(value: dict[str, Any]) -> None:
    if len(canonical(value)) > dm.MAX_RECORD:
        raise InputError("LIMIT_EXCEEDED", "Quality decision record exceeds 96 MiB")


def _decision_count(assessment: dict[str, Any]) -> int:
    """Bound signed records in selected history as well as the terminal assessment."""
    count = 0
    pending = [(assessment, 0)]
    while pending:
        record, depth = pending.pop()
        if not isinstance(record, dict):
            raise InputError("FIELD_TYPE", "Assessment history must contain objects")
        count += len(bounded_list(record.get("decision_records"), 20, "/decision_records"))
        if count > 20 or depth > 32:
            raise InputError("LIMIT_EXCEEDED", "Decision/history count exceeds bridge bounds")
        for prior in bounded_list(record.get("history_refs"), 1, "/history_refs"):
            pending.append((prior, depth + 1))
    return count


def subject(
    request_path: Path, out: Path | None = None
) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    request = version(
        control(request_path, yaml=True),
        "quality_disposition_subject_request",
        models.COMMON_FIELDS,
        "/request",
    )
    binding, inputs, protected = _binding(request_path, request)
    if out is not None:
        output_path(out, inputs, protected)
    return 0 if binding["outcome"] == "emitted" else 1, binding, inputs, protected


def _matches(assessment: dict[str, Any], binding: dict[str, Any]) -> bool:
    p = binding["policy"]
    if p is None:
        return False
    closure = assessment["subject"]["manifest"]["file_closure"]
    expected = [
        *binding["required_files"],
        {"path": p["binding_path"], "sha256": byte_digest(canonical(binding))},
    ]
    for item in expected:
        matches = [row for row in closure if row["path"] == item["path"]]
        if len(matches) != 1 or matches[0]["sha256"] != item["sha256"]:
            return False
    return True


def _gate_reasons(assessment: dict[str, Any], p: dict[str, Any], as_of: Any) -> list[str]:
    manifest = assessment["subject"]["manifest"]
    gate = assessment["gate_results"][0]
    policy = assessment["policy_refs"][0]["record"]
    reasons = []
    if (
        gate["gate_id"] != p["gate_id"]
        or gate["scope"] != p["scope"]
        or manifest["scope"] != p["scope"]
        or set(manifest["expected_obligation_ids"]) != set(p["obligation_ids"])
    ):
        reasons.append("DECISION_SCOPE_MISMATCH")
    predicates = [
        row
        for row in policy["predicates"]
        if row["gate_id"] == p["gate_id"]
        and row["scope"] == p["scope"]
        and row["subject_ref"] == manifest["digest"]
        and row["predicate_class"] == "human_decision"
        and row["required"] is True
        and row["role"] == p["required_role"]
        and row["applicability"] == "required"
        and row["acceptable_result"] == "approve"
    ]
    if (
        set(row["obligation_id"] for row in predicates) != set(p["obligation_ids"])
        or p["required_role"] not in policy["required_roles"]
    ):
        reasons.append("HUMAN_DECISION_REQUIRED")
    historical = dm.timestamp(gate["as_of"], "/gate/as_of")
    if as_of < historical:
        reasons.append("DECISION_TIME_REVERSED")
    if (as_of - historical).total_seconds() > policy["freshness_rules"]["max_age_seconds"]:
        reasons.append("DECISION_EXPIRED")
    return reasons


def _current_gate(
    assessment: dict[str, Any], context: dict[str, Any], as_of: Any
) -> dict[str, Any]:
    """Reevaluate only after independent replay authenticated the complete byte closure."""
    gate = assessment["gate_results"][0]
    with tempfile.TemporaryDirectory(prefix="quality-decision-") as temporary:
        root = Path(temporary)
        for entry in assessment["raw_output_refs"]:
            logical = safe_path(entry["path"], "/raw_output/path")
            destination = root.joinpath(*logical.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(base64.b64decode(entry["content_base64"], validate=True))
        return evaluate_gate(
            assessment["subject"]["manifest"],
            assessment["policy_refs"][0]["record"],
            context["profile"],
            assessment["evidence_records"],
            [r for r in assessment["receipts"] if r["payload_kind"] == "assurance_evidence"],
            assessment["decision_records"],
            [r for r in assessment["receipts"] if r["payload_kind"] == "assurance_decision"],
            requested_domain=gate["assurance_domain"],
            requested_scope=gate["scope"],
            gate_id=gate["gate_id"],
            as_of=as_of,
            raw_root=root,
        )


def assess(
    request_path: Path, out: Path | None = None
) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    request = version(
        control(request_path, yaml=True),
        "quality_disposition_decision_request",
        models.DECISION_FIELDS,
        "/request",
    )
    choice(request["assurance_domain"], {"fixture_contract", "production"}, "/domain")
    dm.timestamp(request["as_of"], "/as_of")
    pairs = bounded_list(request["decisions"], 20, "/decisions")
    binding, inputs, protected = _binding(request_path, request)
    selected = []
    total = count = 0
    seen_pairs = set()
    for raw in pairs:
        pair = exact(raw, {"assessment", "trust_context"}, "/decisions/pair")
        ap, assessment = selected_control(
            request_path.parent, pair["assessment"], max_bytes=dm.MAX_RECORD
        )
        tp, context = selected_control(
            request_path.parent, pair["trust_context"], max_bytes=dm.MAX_RECORD
        )
        pair_id = (ap.resolve(), tp.resolve())
        if pair_id in seen_pairs:
            raise InputError("DUPLICATE_ID", "Duplicate assessment/context pair")
        seen_pairs.add(pair_id)
        total += len(canonical(assessment)) + len(canonical(context))
        count += _decision_count(assessment)
        if total > dm.MAX_RECORD or count > 20:
            raise InputError("LIMIT_EXCEEDED", "Selected decision closure exceeds aggregate bounds")
        inputs.extend([ap, tp])
        selected.append((pair, assessment, context))
    if out is not None:
        output_path(out, inputs, protected)
    record = evaluate(request, binding, selected)
    if control(request_path, yaml=True) != request:
        raise InputError("INPUT_DRIFT", "Decision request changed during replay")
    for pair, _, _ in selected:
        selected_control(request_path.parent, pair["assessment"], max_bytes=dm.MAX_RECORD)
        selected_control(request_path.parent, pair["trust_context"], max_bytes=dm.MAX_RECORD)
    # Replay can take time. Refreeze current inputs before reporting acceptance.
    repeated, final_inputs, final_protected = _binding(request_path, request)
    if repeated != binding:
        raise InputError("INPUT_DRIFT", "Quality subject changed during decision replay")
    inputs.extend(final_inputs)
    protected.extend(final_protected)
    if out is not None:
        output_path(out, inputs, protected)
    return 0 if record["state"] == "accepted_fixture" else 1, record, inputs, protected


def evaluate(
    request: dict[str, Any],
    binding: dict[str, Any],
    selected: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]],
) -> dict[str, Any]:
    """Replay a frozen binding and selected 005 originals, including current fixture validity."""
    domain = choice(request["assurance_domain"], {"fixture_contract", "production"}, "/domain")
    as_of = dm.timestamp(request["as_of"], "/as_of")
    p = binding["policy"]
    reasons = list(binding["reasons"])
    draft = binding["review"]["draft"]
    if as_of < dm.timestamp(binding["review"]["observed_at"], "/review/observed_at"):
        reasons.append("DECISION_TIME_REVERSED")
    if draft["expires_at"] is not None and as_of >= dm.timestamp(
        draft["expires_at"], "/expires_at"
    ):
        reasons.append("DISPOSITION_EXPIRED")
    if domain == "production":
        reasons.append("PRODUCTION_AUTHORITY_UNAVAILABLE")
    if p is not None and p["assurance_domain"] != domain:
        reasons.append("DOMAIN_MISMATCH")
    entries = []
    classified: dict[str, dict[str, Any]] = {}
    sequences: dict[tuple[str, str, str], set[str]] = {}
    for pair, assessment, context in selected:
        replay = verify_assessment(assessment, context)
        local_reasons: list[str] = []
        current = []
        current_gate = None
        match = "not_checked"
        if not replay["reproduced"]:
            local_reasons.append("DECISION_NOT_REPRODUCED")
            local_reasons.extend(replay["reason_codes"])
        elif not _matches(assessment, binding):
            match = "other_subject"
            local_reasons.append("DECISION_SUBJECT_MISMATCH")
        elif p is not None:
            match = "exact"
            local_reasons.extend(_gate_reasons(assessment, p, as_of))
            current_gate = _current_gate(assessment, context, as_of)
            if current_gate["outcome"] != "pass":
                local_reasons.append("CURRENT_GATE_NOT_PASSED")
                local_reasons.extend(current_gate["reason_codes"])
            gate_policy = assessment["policy_refs"][0]["record"]
            receipts = {
                row["payload_digest"]: row
                for row in assessment["receipts"]
                if row["payload_kind"] == "assurance_decision"
            }
            for receipt in receipts.values():
                sequence = (receipt["issuer_id"], receipt["key_id"], receipt["nonce_or_sequence"])
                sequences.setdefault(sequence, set()).add(receipt["payload_digest"])
            for decision in assessment["decision_records"]:
                result = classify_decision(
                    decision,
                    receipts.get(digest(decision, exclude="__none__")),
                    assessment["subject"]["manifest"],
                    gate_policy,
                    context["profile"],
                    requested_domain=domain,
                    requested_scope=p["scope"],
                    gate_id=p["gate_id"],
                    as_of=as_of,
                )
                if result["role"] != p["required_role"]:
                    result["reason_codes"] = sorted(
                        set([*result["reason_codes"], "ROLE_UNAUTHORIZED"])
                    )
                    result["eligible"] = result["approves"] = False
                if (
                    as_of - dm.timestamp(decision["issued_at"], "/decision/issued_at")
                ).total_seconds() > gate_policy["freshness_rules"]["max_age_seconds"]:
                    result["reason_codes"] = sorted(
                        set([*result["reason_codes"], "DECISION_EXPIRED"])
                    )
                    result["eligible"] = result["approves"] = False
                current.append(result)
                existing = classified.get(result["decision_id"])
                if (
                    existing is not None
                    and existing["decision_digest"] != result["decision_digest"]
                ):
                    local_reasons.append("DECISION_CONFLICT")
                elif existing is not None and existing != result:
                    local_reasons.append("DECISION_CONFLICT")
                else:
                    classified[result["decision_id"]] = result
            if replay["outcome"] != "pass":
                local_reasons.append("DECISION_GATE_NOT_PASSED")
            if not current:
                local_reasons.append("HUMAN_DECISION_REQUIRED")
        entries.append(
            {
                "assessment_ref": pair["assessment"],
                "trust_context_ref": pair["trust_context"],
                "assessment": assessment,
                "trust_context": context,
                "replay": replay,
                "binding": match,
                "current": current,
                "current_gate": current_gate,
                "reasons": sorted(set(local_reasons)),
            }
        )
        reasons.extend(local_reasons)
    reconciled = reconcile_decisions(list(classified.values()))
    if any(len(payloads) > 1 for payloads in sequences.values()):
        reasons.append("RECEIPT_REPLAY")
    by_id = {row["decision_id"]: row for row in reconciled}
    for entry in entries:
        for row in entry["current"]:
            lifecycle = by_id[row["decision_id"]]
            if lifecycle["decision_digest"] == row["decision_digest"]:
                # Preserve this context's validity findings while applying lifecycle restrictions.
                row["reason_codes"] = sorted(
                    set([*row["reason_codes"], *lifecycle["reason_codes"]])
                )
                row["eligible"] = row["eligible"] and lifecycle["eligible"]
                row["approves"] = row["approves"] and lifecycle["approves"]
    for row in reconciled:
        reasons.extend(r for r in row["reason_codes"] if r != "DECISION_SUPERSEDED")
        if row["eligible"] and row["outcome"] in {"reject", "request_changes", "withdraw"}:
            reasons.append("DECISION_NEGATIVE")
    approvals = [row for row in reconciled if row["approves"]]
    covered = set().union(*(set(row["obligation_ids"]) for row in approvals))
    if not approvals or p is None or covered != set(p["obligation_ids"]):
        reasons.append("HUMAN_REVIEW_PENDING")
    reasons = sorted(set(reasons))
    if not reasons and domain == "fixture_contract":
        state = "accepted_fixture"
    elif domain == "production":
        state = "blocked"
    elif any(r.startswith("DEVIATION_") for r in binding["reasons"]):
        state = "blocked"
    elif any(
        r in reasons
        for r in (
            "DISPOSITION_STALE",
            "DISPOSITION_EXPIRED",
            "DECISION_EXPIRED",
            "DECISION_SUBJECT_MISMATCH",
            "DECISION_TIME_REVERSED",
        )
    ):
        state = "stale"
    elif binding["reasons"] or selected:
        state = "blocked"
    else:
        state = "pending_review"
    record = seal(
        {
            "schema_version": 1,
            "kind": "quality_disposition_decision_result",
            "binding": binding,
            "assurance_domain": domain,
            "as_of": request["as_of"],
            "time_basis": "untrusted_fixture_request",
            "state": state,
            "reasons": reasons,
            "decisions": entries,
            "accepted_decision_digests": sorted(row["decision_digest"] for row in approvals)
            if state == "accepted_fixture"
            else [],
            "outcome": "completed" if state == "accepted_fixture" else "unresolved",
            "origin": "fixture_contract_evaluation",
            "assurance_eligibility": "not_eligible",
            "engineering_readiness": "not_evaluated",
            "limitations": [
                "Fixture trust and caller-selected time cannot authenticate production decisions.",
                "Protected 005 production authority remains unavailable.",
                "This command performs no analyzer execution or condition discharge.",
                "Native categories and policy adoption require authorized human review.",
            ],
        }
    )
    _bounded(record)
    return record
