"""Public test-key 005 closure fixtures; no production signer or native acceptance."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from score_sw_fabric.assurance.gates import evaluate_gate
from score_sw_fabric.assurance.models import seal
from score_sw_fabric.assurance.package import _readable_report, verify_assessment
from score_sw_fabric.assurance.subjects import build_subject
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.compiler.reader import semantic_digest
from score_sw_fabric.quality import dispositions, runner
from tests.assurance_support import fixture_receipt
from tests.quality_disposition_support import change_draft, selection, write
from tests.quality_support import ROOT, ref, request

AS_OF = "2026-12-01T10:00:00Z"
ISSUED = "2026-12-01T09:00:00Z"
CONTEXT = ROOT / "tests/fixtures/assurance/fixture-trust/context.json"
BASE = ROOT / "tests/fixtures/assurance/passing-scope/out/assessment.json"


def controls(tmp: Path, kind: str = "deviation") -> Path:
    current = request(tmp, component="component-005")
    _, original, _, _ = runner.run(current)
    selected = selection(tmp, original, current)
    change_draft(selected, requested_kind=kind, native_category="fixture_allowed")
    _, reviewed, _, _ = dispositions.review(selected)
    source = tmp / "policy-source.md"
    source.write_text(
        "Test-only category policy. No MISRA category or owner adoption is claimed.\n"
    )
    policy = seal(
        {
            "schema_version": 1,
            "kind": "quality_disposition_policy",
            "id": "fixture_quality_policy",
            "assurance_domain": "fixture_contract",
            "status": "fixture_only",
            "source_ref": ref(source),
            "source_path": "quality/policy-source.md",
            "source_prefix": "quality/source",
            "binding_path": "quality/disposition-binding.json",
            "scope": {
                "kind": "component",
                "id": "component-005",
                "purpose": "fixture verification",
            },
            "gate_id": "fixture-quality-disposition",
            "obligation_ids": ["obligation-a", "obligation-b"],
            "required_role": "component_reviewer",
            "rules": [
                {
                    "tool": "clang-tidy",
                    "native_id": reviewed["subject"]["finding"]["native_id"],
                    "category": "fixture_allowed",
                    "permission": "allowed",
                    "allowed_kinds": [
                        "false_positive",
                        "deviation",
                        "recategorization",
                        "suppression",
                    ],
                    "scope": {
                        "component": "component-005",
                        "translation_units": ["check.cpp"],
                        "files": ["check.cpp"],
                    },
                }
            ],
        }
    )
    record = {
        "schema_version": 1,
        "kind": "quality_disposition_decision_request",
        "review": write(tmp / "review.json", reviewed),
        "disposition_request": ref(selected),
        "policy": write(tmp / "policy.json", policy),
        "protected_roots": [str(ROOT)],
        "decisions": [],
        "assurance_domain": "fixture_contract",
        "as_of": AS_OF,
    }
    path = tmp / "decision-request.json"
    write(path, record)
    return path


def subject_request(path: Path) -> Path:
    r = json.loads(path.read_text())
    r["kind"] = "quality_disposition_subject_request"
    for name in ("decisions", "assurance_domain", "as_of"):
        r.pop(name)
    target = path.parent / "subject-request.json"
    write(target, r)
    return target


def replace_policy(path: Path, **changes: Any) -> None:
    r = json.loads(path.read_text())
    p = Path(r["policy"]["path"])
    record = json.loads(p.read_text())
    record.update(changes)
    r["policy"] = write(p, seal(record))
    write(path, r)


def fixture_assessment(
    tmp: Path,
    binding: dict[str, Any],
    *,
    decision_changes: dict[str, Any] | None = None,
    extra_decisions: list[dict[str, Any]] | None = None,
    human: bool = True,
    extra_bytes: dict[str, bytes] | None = None,
    missing_files: set[str] | None = None,
    context: dict[str, Any] | None = None,
    evidence_max_age: int | None = None,
    gate_id: str | None = None,
) -> dict[str, Any]:
    """Extend existing synthetic 004/005 source closure and replay it independently."""
    value = json.loads(BASE.read_text())
    records = {k: copy.deepcopy(v["record"]) for k, v in value["subject"]["closure"].items()}
    context = copy.deepcopy(context or json.loads(CONTEXT.read_text()))
    policy = binding["policy"]
    policy = {**policy, "gate_id": gate_id or policy["gate_id"]}
    additions = {
        policy["binding_path"]: canonical(binding),
        policy["source_path"]: Path(policy["source_ref"]["path"]).read_bytes(),
    }
    root = tmp / "component"
    for item in binding["current_baseline"]["files"]:
        additions[policy["source_prefix"] + "/" + item["path"]] = (root / item["path"]).read_bytes()
    additions.update(extra_bytes or {})
    for name in missing_files or set():
        additions.pop(name, None)
    source_overrides = {
        item["path"]: base64.b64decode(item["content_base64"])
        for item in value["subject"]["source_files"]
    }
    source_overrides.update(additions)
    snapshot = records["snapshot"]
    candidate = records["candidate"]
    for name, data in additions.items():
        file_hash = hashlib.sha256(data).hexdigest()
        candidate["base_files"].append({"path": name, "sha256": file_hash, "bytes": len(data)})
        snapshot["files"].append(
            {
                "path": name,
                "sha256": file_hash,
                "bytes": len(data),
                "executable": False,
                "media_kind": "application/octet-stream",
                "semantic_role": "fixture_support",
            }
        )
    snapshot["digest"] = semantic_digest(snapshot)
    artifact_request = records["artifact_request"]
    artifact_request["target_snapshot"]["semantic_digest"] = snapshot["digest"]
    artifact_request["target_snapshot"]["sha256"] = hashlib.sha256(canonical(snapshot)).hexdigest()
    candidate["bindings"]["snapshot"] = snapshot["digest"]
    candidate["bindings"]["request"] = semantic_digest(artifact_request)
    candidate["index"]["snapshot"]["digest"] = snapshot["digest"]
    candidate["index"]["digest"] = semantic_digest(candidate["index"])
    candidate["candidate_identity"] = hashlib.sha256(
        canonical(
            {
                "bindings": candidate["bindings"],
                "base_files": candidate["base_files"],
                "overlay_files": candidate["overlay_files"],
                "edit_results": candidate["edit_results"],
                "source_map": candidate["source_map"],
                "index": candidate["index"]["digest"],
                "native_receipt": candidate["index"]["native_receipt"],
            }
        )
    ).hexdigest()
    candidate["digest"] = semantic_digest(candidate)
    subject = build_subject(
        {"assurance_domain": "fixture_contract", "scope": policy["scope"]},
        records,
        source_override=source_overrides,
    )
    gate_policy = value["policy_refs"][0]["record"]
    gate_policy["predicates"] = []
    gate_policy["allowed_evidence"] = (
        [] if evidence_max_age is None else gate_policy["allowed_evidence"]
    )
    for obligation in subject["expected_obligation_ids"]:
        row = {
            "predicate_id": "fixture-" + obligation,
            "gate_id": policy["gate_id"],
            "subject_ref": subject["digest"],
            "obligation_id": obligation,
            "scope": policy["scope"],
            "predicate_class": "human_decision" if human else "deterministic_check",
            "required": True,
            "source_ref": "fixture-quality-policy",
            "policy_rule_ref": "fixture-quality-policy",
            "acceptable_result": "approve" if human else "pass",
            "applicability": "required",
            "authority_ref": gate_policy["id"],
        }
        row["role" if human else "check"] = policy["required_role"] if human else "candidate_valid"
        gate_policy["predicates"].append(row)
    gate_policy["required_roles"] = [policy["required_role"]]
    gate_policy["applicable_scopes"] = [policy["scope"]]
    if evidence_max_age is not None:
        gate_policy["allowed_evidence"][0]["max_age_seconds"] = evidence_max_age
        gate_policy["predicates"].append(
            {
                "predicate_id": "fixture-quality-evidence",
                "gate_id": policy["gate_id"],
                "subject_ref": subject["digest"],
                "obligation_id": "obligation-a",
                "scope": policy["scope"],
                "predicate_class": "trusted_evidence",
                "required": True,
                "source_ref": "fixture-quality-policy",
                "policy_rule_ref": "fixture-quality-policy",
                "acceptable_result": "pass",
                "applicability": "required",
                "authority_ref": gate_policy["id"],
                "evidence_id": "fixture-evidence-005",
            }
        )
    gate_policy = seal(gate_policy)
    decision = copy.deepcopy(value["decision_records"][0])
    decision.update(
        subject_digest=subject["digest"],
        policy_digest=gate_policy["digest"],
        gate_ids=[policy["gate_id"]],
        scope=policy["scope"],
        obligation_ids=policy["obligation_ids"],
        issued_at=ISSUED,
        valid_from=ISSUED,
        valid_until="2026-12-02T09:00:00Z",
    )
    decision.update(decision_changes or {})
    signed = []
    for raw in ([decision] if human else []) + (extra_decisions or []):
        raw = {**decision, **raw}
        raw = seal(raw)
        signed.append(
            (
                raw,
                fixture_receipt(
                    raw,
                    payload_kind="assurance_decision",
                    issued_at=raw["issued_at"],
                    nonce="quality-test-" + raw["decision_id"],
                ),
            )
        )
    evidence, evidence_receipts, originals = [], [], []
    if evidence_max_age is not None:
        observation = copy.deepcopy(value["evidence_records"][0])
        observation.update(
            subject_digest=subject["digest"],
            execution_policy_digest=gate_policy["digest"],
            started_at=ISSUED,
            finished_at="2026-12-01T09:01:00Z",
            inputs=[
                {"id": "plan", "digest": subject["plan"]["digest"]},
                {"id": "candidate", "digest": subject["artifact_candidate"]["digest"]},
            ],
        )
        observation = seal(observation)
        evidence = [observation]
        evidence_receipts = [
            fixture_receipt(
                observation,
                payload_kind="assurance_evidence",
                issued_at="2026-12-01T09:02:00Z",
                nonce="quality-test-evidence",
            )
        ]
        originals = value["raw_output_refs"]
        for raw in originals:
            destination = tmp / raw["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(base64.b64decode(raw["content_base64"]))
    result = evaluate_gate(
        subject,
        gate_policy,
        context["profile"],
        evidence,
        evidence_receipts,
        [d for d, _ in signed],
        [r for _, r in signed],
        requested_domain="fixture_contract",
        requested_scope=policy["scope"],
        gate_id=policy["gate_id"],
        as_of=datetime.fromisoformat(AS_OF),
        raw_root=tmp,
    )
    wrappers = {}
    for name, record in records.items():
        raw = canonical(record)
        wrappers[name] = {
            "record": record,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "semantic_digest": record.get("digest") or semantic_digest(record),
            "suffix": ".json",
            "content_base64": base64.b64encode(raw).decode(),
        }
    assessment = seal(
        {
            "schema_version": 1,
            "kind": "assurance_assessment",
            "subject": {
                "manifest": subject,
                "closure": wrappers,
                "source_files": [
                    {
                        "path": name,
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "bytes": len(data),
                        "content_base64": base64.b64encode(data).decode(),
                    }
                    for name, data in source_overrides.items()
                ],
            },
            "policy_refs": [{"record": gate_policy, "selected_digest": gate_policy["digest"]}],
            "trust_context_refs": [
                {
                    **value["trust_context_refs"][0],
                    "record": context["profile"],
                    "selected_digest": context["profile_digest"],
                }
            ],
            "evidence_records": evidence,
            "decision_records": [d for d, _ in signed],
            "receipts": [*evidence_receipts, *(r for _, r in signed)],
            "gate_results": [result],
            "raw_output_refs": originals,
            "history_refs": [],
            "readable_report": _readable_report(result),
            "limitations": result["limitations"],
        }
    )
    assert verify_assessment(assessment, context)["reproduced"] is True
    return assessment


def with_assessment(path: Path, assessment: dict[str, Any]) -> None:
    record = json.loads(path.read_text())
    record["decisions"] = [
        {
            "assessment": write(path.parent / "assessment.json", assessment),
            "trust_context": ref(CONTEXT),
        }
    ]
    write(path, record)
