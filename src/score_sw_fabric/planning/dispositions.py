"""Match expected instances to inventory without fabricating authority."""

from __future__ import annotations

from typing import Any

from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.planning.mapping import finding
from score_sw_fabric.planning.models import Finding, PlanningInputs, WorkProductInstance
from score_sw_fabric.process_source.reader import InputError


def _identity_key(identity: dict[str, Any]) -> bytes:
    return canonical(identity)


def apply_dispositions(
    instances: dict[str, WorkProductInstance], inputs: PlanningInputs
) -> list[Finding]:
    """Apply inventory requests while authority-dependent outcomes remain unresolved."""

    inventory = inputs.inventory
    if set(inventory) != {"schema_version", "completeness", "artifacts"}:
        raise InputError("INVENTORY_FIELDS", "Artifact inventory fields differ")
    if inventory["completeness"] not in ("complete", "partial"):
        raise InputError("INVENTORY_FIELDS", "Inventory completeness must be complete/partial")
    artifacts = inventory["artifacts"]
    if not isinstance(artifacts, list):
        raise InputError("INVENTORY_FIELDS", "artifacts must be an array")
    by_identity: dict[bytes, dict[str, Any]] = {}
    for position, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict) or "identity" not in artifact:
            raise InputError("INVENTORY_BINDING", f"Invalid artifact at {position}")
        key = _identity_key(artifact["identity"])
        if key in by_identity:
            raise InputError("INVENTORY_BINDING", "Duplicate artifact identity")
        by_identity[key] = artifact

    decisions = inputs.decisions
    if set(decisions) != {"schema_version", "references"} or not isinstance(
        decisions["references"], list
    ):
        raise InputError("DECISION_FIELDS", "Decision-reference fields differ")
    decision_ids: set[str] = set()
    for position, decision in enumerate(decisions["references"]):
        if not isinstance(decision, dict) or not isinstance(decision.get("id"), str):
            raise InputError("DECISION_REFERENCE", f"Invalid decision reference at {position}")
        if decision["id"] in decision_ids or "trusted" in decision or "approved" in decision:
            raise InputError("DECISION_REFERENCE", "Duplicate or self-declared trust field")
        decision_ids.add(decision["id"])

    findings: list[Finding] = []
    for identifier, instance in sorted(instances.items()):
        artifact = by_identity.get(_identity_key(instance["identity"]))
        if artifact is None:
            if inventory["completeness"] == "complete":
                instance["requested_disposition"] = "create"
                instance["effective_disposition"] = (
                    "unresolved" if instance["applicability"] == "unresolved" else "create"
                )
                instance["rationale"] = (
                    f"{instance['rationale']} Inventory confirms this expected instance is absent."
                )
            else:
                instance["finding_codes"].append("INVENTORY_INCOMPLETE")
                findings.append(
                    finding(
                        "INVENTORY_INCOMPLETE",
                        f"instance:{identifier}",
                        "Partial inventory cannot prove the artifact is absent",
                        "Complete the exact-baseline inventory or bind the artifact.",
                        instance_id=identifier,
                    )
                )
            continue
        requested = artifact.get("requested_disposition")
        if requested not in (
            "create",
            "update",
            "reuse",
            "tailored_out",
            "external_obligation",
            "unresolved",
        ):
            raise InputError("INVENTORY_BINDING", f"Invalid disposition for {identifier}")
        instance["requested_disposition"] = requested
        instance["artifact_bindings"] = artifact.get("artifact_bindings", [])
        instance["decision_refs"] = artifact.get("decision_refs", [])
        if any(ref not in decision_ids for ref in instance["decision_refs"]):
            raise InputError("DECISION_REFERENCE", f"Dangling decision reference for {identifier}")

        def block(
            code: str,
            message: str,
            action: str,
            instance: WorkProductInstance = instance,
            identifier: str = identifier,
        ) -> None:
            instance["effective_disposition"] = "unresolved"
            instance["finding_codes"].append(code)
            findings.append(
                finding(
                    code,
                    f"instance:{identifier}",
                    message,
                    action,
                    instance_id=identifier,
                )
            )

        if requested == "create":
            instance["effective_disposition"] = "create"
        elif requested == "update":
            if not artifact.get("impact_reason"):
                block(
                    "UPDATE_IMPACT_MISSING",
                    "Update lacks an explicit impact reason",
                    "Bind the change impact rationale.",
                )
            else:
                instance["effective_disposition"] = "update"
        elif requested == "reuse":
            accepted_revision = artifact.get("accepted_revision")
            if not accepted_revision:
                block(
                    "REUSE_BINDING_STALE",
                    "Reuse prerequisite accepted_revision is missing",
                    "Provide an exact accepted revision binding.",
                )
            bindings = artifact.get("artifact_bindings", [])
            if not isinstance(bindings, list):
                raise InputError("INVENTORY_BINDING", "artifact_bindings must be an array")
            if accepted_revision and not any(
                isinstance(binding, dict) and binding.get("revision") == accepted_revision
                for binding in bindings
            ):
                block(
                    "REUSE_BINDING_STALE",
                    "Accepted revision does not match an exact artifact binding",
                    "Bind the accepted revision and content digest to this instance.",
                )
            if not artifact.get("applicability_rationale"):
                block(
                    "REUSE_APPLICABILITY_MISSING",
                    "Reuse applicability rationale is missing",
                    "Provide scope-specific reuse applicability and coverage.",
                )
            if artifact.get("dependencies_current") is not True:
                block(
                    "REUSE_BINDING_STALE",
                    "Reuse dependency bindings are not current",
                    "Refresh exact dependency bindings for this baseline.",
                )
            for field, code in (
                ("classification_approval_ref", "CLASSIFICATION_APPROVAL_MISSING"),
                ("accepted_change_request_ref", "CHANGE_REQUEST_ACCEPTANCE_MISSING"),
            ):
                reference = artifact.get(field)
                if not isinstance(reference, str) or reference not in decision_ids:
                    block(
                        code,
                        f"Reuse prerequisite {field} is missing or does not resolve",
                        f"Provide a separate decision reference for {field}.",
                    )
            scope = next(
                (
                    item
                    for item in inputs.intake["scopes"]
                    if item["kind"] == instance["identity"]["scope_kind"]
                    and item["id"] == instance["identity"]["scope_id"]
                ),
                None,
            )
            facts = scope["facts"] if scope is not None else {}
            route = artifact.get("reuse_route", facts.get("reuse_route"))
            safety = facts.get("safety_classification")
            if route == "NQ" and safety not in ("QM", "not_applicable"):
                block(
                    "CLASSIFICATION_ROUTE_UNSUPPORTED",
                    "NQ reuse cannot satisfy a safety-classified scope",
                    "Select and approve the applicable Q/QR route or remove the reuse proposal.",
                )
            if facts.get("development_origin") == "modified_reused" and not artifact.get(
                "impact_reason"
            ):
                block(
                    "REUSE_REASSESSMENT_REQUIRED",
                    "Modified reuse lacks a reassessment impact rationale",
                    "Provide baseline-bound reassessment evidence.",
                )
            block(
                "AUTHORITY_UNVERIFIED",
                "Production 002 cannot authenticate reuse decisions",
                "Verify the bound decisions through the protected 005 authority interface.",
            )
        elif requested == "tailored_out":
            for field, code in (
                ("upstream_permission_ref", "TAILORING_PERMISSION_MISSING"),
                ("impact_analysis_ref", "TAILORING_IMPACT_MISSING"),
                ("tailoring_rationale", "TAILORING_PERMISSION_MISSING"),
            ):
                if not artifact.get(field):
                    block(
                        code,
                        f"Tailoring prerequisite {field} is missing",
                        f"Bind {field} to the exact subject/baseline.",
                    )
            if artifact.get("impact_analysis_state") == "stale":
                block(
                    "TAILORING_IMPACT_STALE",
                    "Tailoring impact analysis is stale",
                    "Refresh impact analysis for this baseline.",
                )
            block(
                "AUTHORITY_UNVERIFIED",
                "Production 002 cannot authenticate tailoring decisions",
                "Verify the bound decision through the protected 005 authority interface.",
            )
        elif requested == "external_obligation":
            if not all(
                artifact.get(field) for field in ("owner", "interface", "evidence_owed", "boundary")
            ):
                block(
                    "EXTERNAL_OWNER_MISSING",
                    "External obligation lacks owner/interface/evidence/boundary",
                    "Declare the external responsibility and evidence owed.",
                )
            else:
                instance["effective_disposition"] = "external_obligation"
        else:
            instance["effective_disposition"] = "unresolved"
    return sorted(findings, key=canonical)
