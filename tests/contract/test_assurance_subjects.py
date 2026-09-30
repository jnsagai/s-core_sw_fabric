"""Exact sealed 002/004 closure forms a stable subject, including missing-trace limits."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.assurance.subjects import build_subject
from score_sw_fabric.process_source.reader import InputError, read_json, read_yaml

ROOT = Path(__file__).resolve().parents[2]
REQUEST = ROOT / "tests/fixtures/assurance/passing-scope/subject-request.yaml"


def _inputs() -> dict[str, Any]:
    return {
        "plan": read_json(ROOT / "tests/fixtures/compiler/linear/plan.json"),
        "candidate": read_json(ROOT / "tests/fixtures/artifacts/out/component-candidate.json"),
        "artifact_profile": read_yaml(ROOT / "profiles/s_core_native_artifacts_v1.yaml"),
        "snapshot": read_json(ROOT / "tests/fixtures/artifacts/component/snapshot.json"),
        "workflow_package": read_json(ROOT / "tests/fixtures/compiler/linear/out/package.json"),
        "artifact_request": read_yaml(
            ROOT / "tests/fixtures/artifacts/component/update-request.yaml"
        ),
    }


def test_subject_binds_plan_candidate_source_and_missing_trace() -> None:
    request = read_yaml(REQUEST)
    subject = build_subject(request, _inputs())
    assert subject["plan"]["digest"] == _inputs()["plan"]["digest"]
    assert subject["artifact_candidate"]["digest"] == _inputs()["candidate"]["digest"]
    assert subject["expected_obligation_ids"] == ["obligation-a", "obligation-b"]
    assert "TRACE_NOT_EVALUATED" in subject["limitations"]
    assert subject["assurance_domain"] == "fixture_contract"
    assert subject["digest"] == build_subject(request, _inputs())["digest"]


@pytest.mark.parametrize("binding", ["plan", "artifact_profile", "snapshot", "workflow_package"])
def test_changed_bound_identity_rejected(binding: str) -> None:
    inputs = deepcopy(_inputs())
    inputs["candidate"]["bindings"][binding] = "0" * 64
    with pytest.raises(InputError):
        build_subject(read_yaml(REQUEST), inputs)


def test_changed_overlay_content_rejected() -> None:
    inputs = _inputs()
    inputs["candidate"]["overlay_files"][0]["content"] += "tampered"
    with pytest.raises(InputError):
        build_subject(read_yaml(REQUEST), inputs)


def test_report_not_bound_to_candidate_is_rejected() -> None:
    inputs = _inputs()
    inputs["report"] = read_json(ROOT / "tests/fixtures/artifacts/out/component-trace.json")
    with pytest.raises(InputError):
        build_subject(read_yaml(REQUEST), inputs)


def test_sealed_but_unbound_004_report_is_rejected_publicly(capsys) -> None:  # type: ignore[no-untyped-def]
    from score_sw_fabric.cli import main

    request = ROOT / "tests/fixtures/assurance/mutations/report-mismatch-request.yaml"
    out = ROOT / "tests/fixtures/assurance/mutations/out/subject.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"prior-complete-result")
    try:
        assert (
            main(["assurance", "subject", "--request", str(request), "--out", str(out), "--json"])
            == 2
        )
        assert out.read_bytes() == b"prior-complete-result"
        assert "SUBJECT_MISMATCH" in capsys.readouterr().err
    finally:
        out.unlink()


def test_resealed_candidate_identity_or_native_receipt_substitution_rejected() -> None:
    from score_sw_fabric.compiler.reader import semantic_digest

    for change in ("identity", "receipt"):
        inputs = _inputs()
        candidate = inputs["candidate"]
        if change == "identity":
            candidate["candidate_identity"] = "0" * 64
        else:
            candidate["native_receipt"]["log_digest"] = "0" * 64
        candidate["digest"] = semantic_digest(candidate)
        with pytest.raises(InputError):
            build_subject(read_yaml(REQUEST), inputs)


def test_template_byte_change_rejected_even_when_profile_digest_is_unchanged() -> None:
    inputs = _inputs()
    root = Path(__file__).resolve().parents[2]
    snapshot_root = root / inputs["artifact_request"]["local_paths"]["snapshot_root"]
    overrides = {
        item["path"]: (snapshot_root / item["path"]).read_bytes()
        for item in inputs["snapshot"]["files"]
    }
    for item in inputs["artifact_profile"]["templates"]:
        overrides[item["path"]] = (root / item["path"]).read_bytes()
    selected = inputs["artifact_profile"]["templates"][0]["path"]
    overrides[selected] += b"changed"
    with pytest.raises(InputError, match="template"):
        build_subject(read_yaml(REQUEST), inputs, source_override=overrides)


def test_source_byte_change_rejected_without_editing_selected_native_record() -> None:
    inputs = _inputs()
    snapshot_root = ROOT / inputs["artifact_request"]["local_paths"]["snapshot_root"]
    overrides = {
        item["path"]: (snapshot_root / item["path"]).read_bytes()
        for item in inputs["snapshot"]["files"]
    }
    for item in inputs["artifact_profile"]["templates"]:
        overrides[item["path"]] = (ROOT / item["path"]).read_bytes()
    first = inputs["snapshot"]["files"][0]["path"]
    overrides[first] += b"changed"
    with pytest.raises(InputError) as error:
        build_subject(read_yaml(REQUEST), inputs, source_override=overrides)
    assert error.value.code == "SUBJECT_MISMATCH"


def test_subject_order_and_circular_decision_exclusion() -> None:
    request = read_yaml(REQUEST)
    inputs = _inputs()
    original = build_subject(request, inputs)
    reversed_inputs = dict(reversed(list(inputs.items())))
    assert build_subject(request, reversed_inputs) == original
    assert "decision" not in original and "evidence" not in original
    reversed_inputs["decision"] = read_json(
        ROOT / "tests/fixtures/assurance/passing-scope/decision.json"
    )
    with pytest.raises(InputError) as error:
        build_subject(request, reversed_inputs)
    assert error.value.code == "CLOSURE_MISSING"


def test_public_trace_bound_candidate_and_report_form_positive_subject() -> None:
    from score_sw_fabric.cli import main

    root = Path(__file__).resolve().parents[2]
    request = root / "tests/fixtures/assurance/traced-scope/subject-request.yaml"
    output = root / "tests/fixtures/assurance/traced-scope/out/subject.json"
    assert (
        main(["assurance", "subject", "--request", str(request), "--out", str(output), "--json"])
        == 0
    )
    subject = read_json(output)
    candidate = read_json(root / "tests/fixtures/artifacts/out/component-trace-candidate.json")
    report = read_json(root / "tests/fixtures/artifacts/out/component-trace-candidate-report.json")
    assert subject["artifact_candidate"]["digest"] == candidate["digest"]
    assert subject["artifact_report"]["digest"] == report["digest"]
    assert set(subject["artifact_report"]["expected_obligation_ids"]).issubset(
        subject["expected_obligation_ids"]
    )
    assert set(report["capabilities"].values()) == {"not_evaluated"}
    assert "engineering_readiness" not in subject and "release" not in subject
    assert "TRACE_NOT_EVALUATED" not in subject["limitations"]


def test_resealed_attached_trace_report_cannot_invent_obligation_result() -> None:
    from score_sw_fabric.compiler.reader import semantic_digest

    root = Path(__file__).resolve().parents[2]
    inputs = _inputs()
    inputs["candidate"] = read_json(
        root / "tests/fixtures/artifacts/out/component-trace-candidate.json"
    )
    inputs["report"] = read_json(
        root / "tests/fixtures/artifacts/out/component-trace-candidate-report.json"
    )
    inputs["trace_profile"] = read_yaml(root / "policies/s_core_trace_profile_v1.yaml")
    inputs["artifact_request"] = read_yaml(
        root / "tests/fixtures/artifacts/component/update-and-trace-request.yaml"
    )
    tampered = deepcopy(inputs["report"])
    tampered["obligations"][0]["state"] = "unresolved"
    tampered["digest"] = semantic_digest(tampered)
    inputs["report"] = tampered
    inputs["candidate"]["report"] = tampered
    inputs["candidate"]["digest"] = semantic_digest(inputs["candidate"])
    request = read_yaml(root / "tests/fixtures/assurance/traced-scope/subject-request.yaml")
    with pytest.raises(InputError, match="report obligations"):
        build_subject(request, inputs)


@pytest.mark.parametrize(
    ("record", "path", "replacement", "code"),
    [
        ("plan", ("target_namespace",), "other-namespace", "SUBJECT_MISMATCH"),
        ("candidate", ("native_receipt", "validator", "id"), "other-validator", "SUBJECT_MISMATCH"),
        ("artifact_profile", ("metamodel", "sha256"), "0" * 64, "ARTIFACT_PROFILE_MISMATCH"),
        ("snapshot", ("source", "commit"), "a" * 40, "SUBJECT_MISMATCH"),
        ("workflow_package", ("entrypoint",), "other-entrypoint", "SUBJECT_MISMATCH"),
        ("artifact_request", ("output_root",), "other-out", "SUBJECT_MISMATCH"),
    ],
)
def test_resealed_single_upstream_binding_change_refuses_subject(
    record: str, path: tuple[str, ...], replacement: str, code: str
) -> None:
    from score_sw_fabric.compiler.reader import semantic_digest

    inputs = _inputs()
    selected = inputs[record]
    target = selected
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = replacement
    if "digest" in selected:
        selected["digest"] = semantic_digest(selected)
    with pytest.raises(InputError) as error:
        build_subject(read_yaml(REQUEST), inputs)
    assert error.value.code == code
