"""A native question is a handoff, never a 005 human decision."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.process_source.reader import InputError, read_json, read_yaml
from score_sw_fabric.runtime.inspect import bind_pending_questions
from score_sw_fabric.runtime.projection import project_version

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "tests/fixtures/runtime/shared-human/package.json"
PROFILE = ROOT / "tests/fixtures/compiler/shared-parallel-review/compiler_profile.yaml"
NODE = "node_b3a60d7744d0e9fc356f57e8"


def _inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    package = read_json(PACKAGE)
    profile = read_yaml(PROFILE)
    subject = seal(
        {
            "schema_version": 1,
            "kind": "assurance_subject",
            "assurance_domain": "fixture_contract",
            "artifact_candidate": {"bindings": {"workflow_package": package["digest"]}},
            "expected_obligation_ids": ["obligation-a", "obligation-b"],
        }
    )
    version_id = project_version(package, profile)["wire_digest"]
    inspection = {
        "native_status": "blocked",
        "native_blocked_reason": "human_input_required",
        "complete": True,
        "events": [
            {
                "kind": "platform",
                "item": {
                    "record": {
                        "kind": "run.created",
                        "spec": {
                            "workflow_version_id": version_id,
                            "settings": {"run": {"execution": {"approval": "prompt"}}},
                        },
                    }
                },
            }
        ],
        "questions": [{"id": NODE + "#7", "stage": NODE + "@1"}],
    }
    return inspection, package, profile, subject


def test_waiting_question_maps_to_exact_gate_and_subject_without_answer() -> None:
    inspection, package, profile, subject = _inputs()
    mapped = bind_pending_questions(
        inspection, package, profile, subject, expected_subject_digest=subject["digest"]
    )
    assert mapped == [
        {
            "question_id": NODE + "#7",
            "stage": NODE + "@1",
            "gate_id": NODE,
            "gate_purpose": "Execute shared_review",
            "covered_obligation_ids": ["obligation-a", "obligation-b"],
            "subject_digest": subject["digest"],
            "assurance_domain": "fixture_contract",
            "source_map_binding": next(
                item["content_binding"]
                for item in package["source_map"]
                if item["kind"] == "gate" and item["id"] == NODE
            ),
            "next_action": "external_authorized_human_decision_required",
            "engineering_readiness": "not_evaluated",
        }
    ]
    assert "answer" not in mapped[0] and "decision" not in mapped[0]


@pytest.mark.parametrize(
    "change",
    [
        "subject_digest",
        "package",
        "obligations",
        "stage",
        "status",
        "auto_approve",
        "default_choice",
        "timeout_default",
        "native_answer",
        "version_id",
    ],
)
def test_wrong_subject_or_native_question_refuses_mapping(change: str) -> None:
    inspection, package, profile, subject = _inputs()
    expected_digest = subject["digest"]
    if change == "subject_digest":
        expected_digest = "a" * 64
    elif change == "package":
        subject["artifact_candidate"]["bindings"]["workflow_package"] = "b" * 64
        subject = seal(subject)
        expected_digest = subject["digest"]
    elif change == "obligations":
        subject["expected_obligation_ids"] = ["obligation-a"]
        subject = seal(subject)
        expected_digest = subject["digest"]
    elif change == "stage":
        inspection = deepcopy(inspection)
        inspection["questions"][0]["stage"] = "other@1"
    elif change == "auto_approve":
        inspection = deepcopy(inspection)
        inspection["events"][0]["item"]["record"]["spec"]["settings"]["run"]["execution"][
            "approval"
        ] = "auto"
    elif change == "default_choice":
        inspection = deepcopy(inspection)
        inspection["questions"][0]["default_choice"] = "yes"
    elif change == "timeout_default":
        inspection = deepcopy(inspection)
        inspection["questions"][0]["timeout_default"] = "success"
    elif change == "native_answer":
        inspection = deepcopy(inspection)
        inspection["events"].append(
            {
                "kind": "platform",
                "item": {
                    "record": {
                        "kind": "interview.answered",
                        "question": NODE + "#7",
                        "answer": "yes",
                    }
                },
            }
        )
    elif change == "version_id":
        inspection = deepcopy(inspection)
        inspection["events"][0]["item"]["record"]["spec"]["workflow_version_id"] = "c" * 64
    else:
        inspection = deepcopy(inspection)
        inspection["native_status"] = "succeeded"
    with pytest.raises(InputError) as error:
        bind_pending_questions(
            inspection, package, profile, subject, expected_subject_digest=expected_digest
        )
    assert error.value.code == "QUESTION_SUBJECT_UNKNOWN"
