"""Regenerate the deterministic fixture-only public old/new no-impact journey."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from score_sw_fabric.assurance.freshness import _differences
from score_sw_fabric.assurance.models import seal
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.cli import main
from score_sw_fabric.compiler.reader import semantic_digest
from score_sw_fabric.process_source.reader import read_json, read_yaml
from tests.assurance_support import fixture_receipt

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "tests/fixtures/assurance/passing-scope"
HERE = ROOT / "tests/fixtures/assurance/no-impact-scope"
OLD_AS_OF = "2026-09-29T10:00:00Z"
NEW_AS_OF = "2026-09-29T11:00:00Z"
REVIEW_TIME = "2026-09-29T10:30:00Z"


def ref(path: Path) -> dict[str, str]:
    value = read_yaml(path) if path.suffix in {".yaml", ".yml"} else read_json(path)
    selected = value.get("receipt_digest") or value.get("digest") or semantic_digest(value)
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "semantic_digest": selected,
    }


def record(path: Path, value: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value))
    return path


def request(path: Path, value: dict[str, Any]) -> Path:
    path.write_text(yaml.safe_dump(value, sort_keys=True))
    return path


def run(operation: str, selected: Path, out: Path, expected: int) -> None:
    actual = main(
        [
            "assurance",
            operation,
            "--request",
            str(selected.relative_to(ROOT)),
            "--out",
            str(out.relative_to(ROOT)),
            "--json",
        ]
    )
    if actual != expected:
        raise RuntimeError(f"{operation} returned {actual}, expected {expected}")


def main_fixture() -> None:
    HERE.mkdir(parents=True, exist_ok=True)
    old_subject_req = read_yaml(BASE / "subject-request.yaml")
    old_subject_req["inputs"]["artifact_request"] = ref(
        ROOT / "tests/fixtures/artifacts/component/before-request.yaml"
    )
    old_subject_req["inputs"]["candidate"] = ref(
        ROOT / "tests/fixtures/artifacts/out/before-candidate.json"
    )
    old_subject_req["output_root"] = "tests/fixtures/assurance/no-impact-scope/out"
    old_subject_request = request(HERE / "old-subject-request.yaml", old_subject_req)
    old_subject_path = HERE / "out/old-subject.json"
    run("subject", old_subject_request, old_subject_path, 0)
    old_subject = read_json(old_subject_path)
    current_subject = read_json(BASE / "out/subject.json")
    changed: list[str] = []
    _differences(old_subject, current_subject, "/subject", changed)
    old_policy = read_json(BASE / "policy.json")
    changed.extend(
        ["/policy/digest", "/as_of"]
        + [
            f"/policy/predicates/{index}/subject_ref"
            for index in range(len(old_policy["predicates"]))
        ]
    )
    paths = sorted(set(changed))
    old_policy["freshness_rules"]["no_impact"] = {
        "role": "component_reviewer",
        "authority_ref": "fixture-authority-005",
        "allowed_paths": paths,
    }
    for predicate in old_policy["predicates"]:
        predicate["subject_ref"] = old_subject["digest"]
    old_policy = seal(old_policy)
    old_policy_path = record(HERE / "old-policy.json", old_policy)
    current_policy = deepcopy(old_policy)
    for predicate in current_policy["predicates"]:
        predicate["subject_ref"] = current_subject["digest"]
    current_policy = seal(current_policy)
    current_policy_path = record(HERE / "current-policy.json", current_policy)

    evidence = read_json(BASE / "evidence.json")
    evidence["subject_digest"] = old_subject["digest"]
    evidence["execution_policy_digest"] = old_policy["digest"]
    for item in evidence["inputs"]:
        if item["id"] == "candidate":
            item["digest"] = old_subject["artifact_candidate"]["digest"]
    evidence = seal(evidence)
    evidence_path = record(HERE / "old-evidence.json", evidence)
    evidence_receipt_path = record(
        HERE / "old-evidence-receipt.json",
        fixture_receipt(
            evidence,
            payload_kind="assurance_evidence",
            issued_at=evidence["started_at"],
            nonce="no-impact-old-evidence-1",
        ),
    )
    old_decision = read_json(BASE / "decision.json")
    old_decision["subject_digest"] = old_subject["digest"]
    old_decision["policy_digest"] = old_policy["digest"]
    old_decision = seal(old_decision)
    old_decision_path = record(HERE / "old-decision.json", old_decision)
    old_decision_receipt_path = record(
        HERE / "old-decision-receipt.json",
        fixture_receipt(
            old_decision,
            payload_kind="assurance_decision",
            issued_at=old_decision["issued_at"],
            nonce="no-impact-old-decision-1",
        ),
    )
    old_gate = read_yaml(BASE / "gate-request.yaml")
    old_gate["inputs"].update(
        {
            "artifact_request": old_subject_req["inputs"]["artifact_request"],
            "candidate": old_subject_req["inputs"]["candidate"],
            "subject": ref(old_subject_path),
            "policy": ref(old_policy_path),
            "evidence": [ref(evidence_path)],
            "evidence_receipts": [ref(evidence_receipt_path)],
            "decisions": [ref(old_decision_path)],
            "decision_receipts": [ref(old_decision_receipt_path)],
        }
    )
    old_gate["output_root"] = "tests/fixtures/assurance/no-impact-scope/out"
    old_gate["as_of"] = OLD_AS_OF
    old_gate_request = request(HERE / "old-gate-request.yaml", old_gate)
    old_assessment_path = HERE / "out/old-assessment.json"
    run("gate", old_gate_request, old_assessment_path, 0)
    old_assessment = read_json(old_assessment_path)

    review = deepcopy(old_decision)
    review.update(
        {
            "decision_id": "fixture-no-impact-review-005",
            "outcome": "no_impact",
            "subject_digest": current_subject["digest"],
            "policy_digest": current_policy["digest"],
            "rationale": "Fixture review of exact before/after candidate bindings.",
            "issued_at": REVIEW_TIME,
            "valid_from": REVIEW_TIME,
            "conditions": [],
            "baseline_change": {
                "prior_assessment_digest": old_assessment["digest"],
                "prior_subject_digest": old_subject["digest"],
                "current_subject_digest": current_subject["digest"],
                "prior_policy_digest": old_policy["digest"],
                "current_policy_digest": current_policy["digest"],
                "changed_bindings": paths,
            },
        }
    )
    review = seal(review)
    review_path = record(HERE / "review.json", review)
    review_receipt_path = record(
        HERE / "review-receipt.json",
        fixture_receipt(
            review,
            payload_kind="assurance_decision",
            issued_at=REVIEW_TIME,
            nonce="no-impact-review-1",
        ),
    )
    current_gate = deepcopy(old_gate)
    current_gate["inputs"].update(
        {
            "artifact_request": ref(
                ROOT / "tests/fixtures/artifacts/component/update-request.yaml"
            ),
            "candidate": ref(ROOT / "tests/fixtures/artifacts/out/component-candidate.json"),
            "subject": ref(BASE / "out/subject.json"),
            "policy": ref(current_policy_path),
            "decisions": [ref(old_decision_path), ref(review_path)],
            "decision_receipts": [ref(old_decision_receipt_path), ref(review_receipt_path)],
            "prior_assessment": ref(old_assessment_path),
        }
    )
    current_gate["gate_mode"] = "reuse_prior"
    current_gate["as_of"] = NEW_AS_OF
    current_gate_request = request(HERE / "current-gate-request.yaml", current_gate)
    current_assessment_path = HERE / "out/current-assessment.json"
    run("gate", current_gate_request, current_assessment_path, 1)
    actual = read_json(current_assessment_path)["gate_results"][0]
    if (
        actual["outcome"] != "stale"
        or actual["freshness"].get("no_impact_decision_digest") != review["digest"]
    ):
        raise RuntimeError("Signed no-impact review was not retained in stale result")
    verified = main(
        [
            "assurance",
            "verify",
            "--assessment",
            str(current_assessment_path.relative_to(ROOT)),
            "--trust-context",
            "tests/fixtures/assurance/fixture-trust/context.json",
            "--json",
        ]
    )
    if verified != 0:
        raise RuntimeError("Portable current assessment did not reproduce")


if __name__ == "__main__":
    main_fixture()
