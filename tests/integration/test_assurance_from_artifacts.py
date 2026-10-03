"""Public 002/004-to-005 fixture journeys and offline historical replay."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from score_sw_fabric.cli import main
from score_sw_fabric.process_source.reader import read_json, read_yaml
from tests.assurance_support import fixture_receipt

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/assurance"
CONTEXT = FIXTURES / "fixture-trust/context.json"
SOURCE = ROOT / "tests/fixtures/artifacts/component/target/index.rst"
CANDIDATE = ROOT / "tests/fixtures/artifacts/out/component-candidate.json"
PLAN = ROOT / "tests/fixtures/compiler/linear/plan.json"


def test_public_subject_to_evidence_relocates_and_preserves_malformed_prior(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from score_sw_fabric.assurance.models import seal
    from score_sw_fabric.catalog.export import canonical

    folder = FIXTURES / "passing-scope"
    immutable = [PLAN, CANDIDATE, SOURCE]
    before = {str(path): path.read_bytes() for path in immutable}
    with TemporaryDirectory(prefix=".assurance-us1-", dir=ROOT) as directory:
        scratch = Path(directory)
        subject_request = read_yaml(folder / "subject-request.yaml")
        subject_request["output_root"] = f"{scratch.name}/out"
        subject_path = scratch / "subject-request.json"
        subject_path.write_text(json.dumps(subject_request))
        subject_out = scratch / "out/subject.json"
        assert (
            main(
                [
                    "assurance",
                    "subject",
                    "--request",
                    str(subject_path),
                    "--out",
                    str(subject_out),
                    "--json",
                ]
            )
            == 0
        )
        subject_summary = json.loads(capsys.readouterr().out)
        assert subject_summary["assurance_domain"] == "fixture_contract"
        assert subject_out.read_bytes() == (folder / "out/subject.json").read_bytes()

        evidence_request = read_yaml(folder / "evidence-request.yaml")
        evidence_request["output_root"] = f"{scratch.name}/out"
        evidence_request["inputs"]["subject"] = {
            "path": "out/subject.json",
            "sha256": hashlib.sha256(subject_out.read_bytes()).hexdigest(),
            "semantic_digest": read_json(subject_out)["digest"],
        }
        evidence_path = scratch / "evidence-request.json"
        evidence_path.write_text(json.dumps(evidence_request))
        evidence_out = scratch / "out/evidence-result.json"
        assert (
            main(
                [
                    "assurance",
                    "evidence",
                    "--request",
                    str(evidence_path),
                    "--out",
                    str(evidence_out),
                    "--json",
                ]
            )
            == 0
        )
        evidence_summary = json.loads(capsys.readouterr().out)
        assert evidence_summary["outcome"] == "eligible"
        assert evidence_summary["assurance_domain"] == "fixture_contract"
        prior = evidence_out.read_bytes()

        asserted = read_json(folder / "evidence.json")
        asserted["origin_class"] = "agent_assertion"
        asserted = seal(asserted)
        assertion_bytes = canonical(asserted)
        (scratch / "agent-assertion.json").write_bytes(assertion_bytes)
        evidence_request["inputs"]["evidence"] = [
            {
                "path": "agent-assertion.json",
                "sha256": hashlib.sha256(assertion_bytes).hexdigest(),
                "semantic_digest": asserted["digest"],
            }
        ]
        evidence_path.write_text(json.dumps(evidence_request))
        assertion_out = scratch / "out/agent-result.json"
        assert (
            main(
                [
                    "assurance",
                    "evidence",
                    "--request",
                    str(evidence_path),
                    "--out",
                    str(assertion_out),
                    "--json",
                ]
            )
            == 1
        )
        assert "EVIDENCE_UNTRUSTED" in json.loads(capsys.readouterr().out)["reasons"]

        evidence_request["inputs"]["evidence"][0]["sha256"] = "0" * 64
        evidence_path.write_text(json.dumps(evidence_request))
        assert (
            main(
                [
                    "assurance",
                    "evidence",
                    "--request",
                    str(evidence_path),
                    "--out",
                    str(evidence_out),
                    "--json",
                ]
            )
            == 2
        )
        assert json.loads(capsys.readouterr().err)["code"] == "HASH_MISMATCH"
        assert evidence_out.read_bytes() == prior
    assert {str(path): path.read_bytes() for path in immutable} == before


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("wrong_role", "ROLE_UNAUTHORIZED"),
        ("wrong_scope", "SCOPE_MISMATCH"),
        ("unverified_actor", "ORIGIN_UNVERIFIED"),
    ],
)
def test_public_decision_rejects_signed_wrong_authority_and_actor_claim(
    change: str, reason: str, capsys: pytest.CaptureFixture[str]
) -> None:
    from score_sw_fabric.assurance.models import seal
    from score_sw_fabric.catalog.export import canonical

    folder = FIXTURES / "passing-scope"
    immutable = [PLAN, CANDIDATE, SOURCE, folder / "decision.json"]
    before = {str(path): path.read_bytes() for path in immutable}
    with TemporaryDirectory(prefix=".assurance-us2-", dir=ROOT) as directory:
        scratch = Path(directory)
        decision = read_json(folder / "decision.json")
        if change == "wrong_role":
            decision["role"] = "release_owner"
        elif change == "wrong_scope":
            decision["scope"]["id"] = "sibling-component"
        else:
            decision["actor_id"] = "claimed-actor-from-002-or-fabro"
        decision = seal(decision)
        receipt = (
            read_json(folder / "decision-receipt.json")
            if change == "unverified_actor"
            else fixture_receipt(
                decision,
                payload_kind="assurance_decision",
                issued_at=decision["issued_at"],
                nonce="fixture-decision-sequence-1",
            )
        )
        records = {"decision": decision, "receipt": receipt}
        request = read_yaml(folder / "decision-request.yaml")
        for name, record in records.items():
            content = canonical(record)
            (scratch / f"{name}.json").write_bytes(content)
            request["inputs"]["decisions" if name == "decision" else "receipts"] = [
                {
                    "path": f"{name}.json",
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "semantic_digest": record["digest" if name == "decision" else "receipt_digest"],
                }
            ]
        request["output_root"] = f"{scratch.name}/out"
        path = scratch / "request.json"
        path.write_text(json.dumps(request))
        out = scratch / "out/decision-result.json"
        assert (
            main(
                [
                    "assurance",
                    "decision",
                    "--request",
                    str(path),
                    "--out",
                    str(out),
                    "--json",
                ]
            )
            == 1
        )
        summary = json.loads(capsys.readouterr().out)
        assert summary["assurance_domain"] == "fixture_contract"
        assert reason in summary["reasons"]
        assert read_json(out)["eligibility"][0]["eligible"] is False
    assert {str(path): path.read_bytes() for path in immutable} == before


def test_public_conflicting_decisions_block_without_changing_history(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from score_sw_fabric.assurance.models import seal
    from score_sw_fabric.catalog.export import canonical

    folder = FIXTURES / "passing-scope"
    immutable = [PLAN, CANDIDATE, SOURCE, folder / "decision.json"]
    before = {str(path): path.read_bytes() for path in immutable}
    with TemporaryDirectory(prefix=".assurance-us2-conflict-", dir=ROOT) as directory:
        scratch = Path(directory)
        first = read_json(folder / "decision.json")
        second = read_json(folder / "decision.json")
        second["decision_id"] = "fixture-conflict-005"
        second["outcome"] = "reject"
        second = seal(second)
        records = [first, second]
        receipts = [
            read_json(folder / "decision-receipt.json"),
            fixture_receipt(
                second,
                payload_kind="assurance_decision",
                issued_at=second["issued_at"],
                nonce="fixture-decision-sequence-2",
            ),
        ]
        request = read_yaml(folder / "decision-request.yaml")
        for kind, values in (("decisions", records), ("receipts", receipts)):
            refs = []
            for index, record in enumerate(values):
                content = canonical(record)
                name = f"{kind}-{index}.json"
                (scratch / name).write_bytes(content)
                refs.append(
                    {
                        "path": name,
                        "sha256": hashlib.sha256(content).hexdigest(),
                        "semantic_digest": record[
                            "receipt_digest" if kind == "receipts" else "digest"
                        ],
                    }
                )
            request["inputs"][kind] = refs
        request["output_root"] = f"{scratch.name}/out"
        path = scratch / "request.json"
        path.write_text(json.dumps(request))
        out = scratch / "out/decision-result.json"
        assert (
            main(
                [
                    "assurance",
                    "decision",
                    "--request",
                    str(path),
                    "--out",
                    str(out),
                    "--json",
                ]
            )
            == 1
        )
        summary = json.loads(capsys.readouterr().out)
        assert "DECISION_CONFLICT" in summary["reasons"]
        assert all(not item["eligible"] for item in read_json(out)["eligibility"])
    assert {str(path): path.read_bytes() for path in immutable} == before


def test_public_gate_record_array_permutation_has_identical_assessment_bytes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from score_sw_fabric.assurance.models import seal
    from score_sw_fabric.catalog.export import canonical

    folder = FIXTURES / "passing-scope"
    first = read_json(folder / "evidence.json")
    second = read_json(folder / "evidence.json")
    second["evidence_id"] = "unused-evidence-005"
    with TemporaryDirectory(prefix=".assurance-gate-order-", dir=ROOT) as directory:
        scratch = Path(directory)
        shutil.copytree(folder / "raw", scratch / "raw")
        shutil.copyfile(scratch / "raw/observed.json", scratch / "raw/observed-2.json")
        second["raw_outputs"][0]["path"] = "observed-2.json"
        second = seal(second)
        records = [first, second]
        receipts = [
            read_json(folder / "evidence-receipt.json"),
            fixture_receipt(second, payload_kind="assurance_evidence", nonce="fixture-sequence-2"),
        ]
        request = read_yaml(folder / "gate-request.yaml")
        request["local_paths"]["raw_root"] = "raw"
        for field, values in (("evidence", records), ("evidence_receipts", receipts)):
            refs = []
            for index, record in enumerate(values):
                content = canonical(record)
                name = f"{field}-{index}.json"
                (scratch / name).write_bytes(content)
                refs.append(
                    {
                        "path": name,
                        "sha256": hashlib.sha256(content).hexdigest(),
                        "semantic_digest": record[
                            "receipt_digest" if field == "evidence_receipts" else "digest"
                        ],
                    }
                )
            request["inputs"][field] = refs
        request["output_root"] = f"{scratch.name}/out"
        path = scratch / "request.json"
        out = scratch / "out/assessment.json"
        outputs = []
        for reverse in (False, True):
            for field in ("evidence", "evidence_receipts"):
                request["inputs"][field] = sorted(
                    request["inputs"][field], key=lambda item: item["path"], reverse=reverse
                )
            path.write_text(json.dumps(request))
            status = main(
                [
                    "assurance",
                    "gate",
                    "--request",
                    str(path),
                    "--out",
                    str(out),
                    "--json",
                ]
            )
            assert status in {0, 1}
            capsys.readouterr()
            outputs.append(out.read_bytes())
        assert outputs[0] == outputs[1]


@pytest.mark.parametrize(
    "name,outcome,exit_code",
    [
        ("passing-scope", "pass", 0),
        ("blocked-scope", "blocked", 1),
        ("failed-scope", "fail", 1),
        ("mixed-scope", "blocked", 1),
        ("not-evaluated-scope", "not_evaluated", 1),
        ("stale-scope", "stale", 1),
        ("not-applicable-scope", "not_applicable", 1),
        ("production-refusal-scope", "blocked", 1),
        ("imported-scope", "pass", 0),
    ],
)
def test_public_gate_outcomes_preserve_002_004_and_replay(
    name: str, outcome: str, exit_code: int, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = FIXTURES / name
    immutable = [PLAN, CANDIDATE, SOURCE]
    before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in immutable]
    request = folder / "gate-request.yaml"
    assessment = folder / "out/assessment.json"
    assert (
        main(["assurance", "gate", "--request", str(request), "--out", str(assessment), "--json"])
        == exit_code
    )
    summary = json.loads(capsys.readouterr().out)
    assert summary["outcome"] == outcome
    assert summary["engineering_readiness"] == "not_evaluated"
    assert [hashlib.sha256(path.read_bytes()).hexdigest() for path in immutable] == before
    assert (
        main(
            [
                "assurance",
                "verify",
                "--assessment",
                str(assessment),
                "--trust-context",
                str(
                    FIXTURES / "imported-scope/trust-context.json"
                    if name == "imported-scope"
                    else CONTEXT
                ),
                "--json",
            ]
        )
        == 0
    )
    replay = json.loads(capsys.readouterr().out)
    assert replay["reproduced"] is True and replay["outcome"] == outcome
    value = read_json(assessment)
    assert value["subject"]["manifest"]["plan"]["digest"] == read_json(PLAN)["digest"]
    assert (
        value["subject"]["manifest"]["artifact_candidate"]["digest"]
        == read_json(CANDIDATE)["digest"]
    )
    if name == "mixed-scope":
        assert {item["state"] for item in value["gate_results"][0]["predicate_results"]} == {
            "satisfied",
            "failed",
            "blocked",
        }
    if name == "production-refusal-scope":
        assert "PRODUCTION_ORIGIN_UNAVAILABLE" in summary["reasons"]
        assert value["gate_results"][0]["time_basis_ref"] == "untrusted-request-time"


def test_relocated_offline_verifier_needs_only_assessment_and_trust_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assessment = tmp_path / "assessment.json"
    context = tmp_path / "context.json"
    shutil.copyfile(FIXTURES / "passing-scope/out/assessment.json", assessment)
    shutil.copyfile(CONTEXT, context)
    monkeypatch.chdir(tmp_path)
    assert (
        main(
            [
                "assurance",
                "verify",
                "--assessment",
                str(assessment),
                "--trust-context",
                str(context),
                "--json",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["reproduced"] is True


def test_missing_raw_bytes_cannot_reproduce_prior_pass(tmp_path: Path) -> None:
    from score_sw_fabric.assurance.models import seal
    from score_sw_fabric.assurance.package import verify_assessment

    value = read_json(FIXTURES / "passing-scope/out/assessment.json")
    value["raw_output_refs"] = []
    value = seal(value)
    assert verify_assessment(value, read_json(CONTEXT))["reproduced"] is False


def test_trace_bound_subject_cannot_use_policy_missing_report_obligations(
    capsys: pytest.CaptureFixture[str],
) -> None:
    request = FIXTURES / "traced-scope/gate-incomplete-request.yaml"
    output = FIXTURES / "traced-scope/out/assessment.json"
    sentinel = b"prior-complete-assessment"
    output.write_bytes(sentinel)
    try:
        assert (
            main(["assurance", "gate", "--request", str(request), "--out", str(output), "--json"])
            == 2
        )
        assert output.read_bytes() == sentinel
        assert "OBLIGATION_SET_INCOMPLETE" in capsys.readouterr().err
    finally:
        output.unlink()


def test_trace_bound_complete_expected_set_replays_offline(
    capsys: pytest.CaptureFixture[str],
) -> None:
    request = FIXTURES / "traced-scope/gate-not-started-request.yaml"
    output = FIXTURES / "traced-scope/out/assessment.json"
    assert (
        main(["assurance", "gate", "--request", str(request), "--out", str(output), "--json"]) == 1
    )
    assert json.loads(capsys.readouterr().out)["outcome"] == "not_evaluated"
    assessment = read_json(output)
    manifest = assessment["subject"]["manifest"]
    matrix = assessment["gate_results"][0]["predicate_results"]
    assert len(matrix) == 11
    assert len(manifest["expected_obligation_ids"]) == 10
    assert (
        assessment["subject"]["closure"]["trace_profile"]["record"]["digest"]
        == (manifest["profiles"]["trace"])
    )
    assert (
        main(
            [
                "assurance",
                "verify",
                "--assessment",
                str(output),
                "--trust-context",
                str(CONTEXT),
                "--json",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["reproduced"] is True


def test_trace_bound_complete_gate_passes_and_relocates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    request = FIXTURES / "traced-scope/gate-request.yaml"
    output = FIXTURES / "traced-scope/out/passing-assessment.json"
    assert (
        main(["assurance", "gate", "--request", str(request), "--out", str(output), "--json"]) == 0
    )
    assert json.loads(capsys.readouterr().out)["outcome"] == "pass"
    assessment = read_json(output)
    manifest = assessment["subject"]["manifest"]
    matrix = assessment["gate_results"][0]["predicate_results"]
    assert len(matrix) == 11
    assert len(manifest["expected_obligation_ids"]) == 10
    assert all(item["state"] == "satisfied" for item in matrix)
    assert manifest["artifact_report"]["status"] == "passed"
    assert "trace_profile" in assessment["subject"]["closure"]
    relocated = tmp_path / "assessment.json"
    context = tmp_path / "context.json"
    shutil.copyfile(output, relocated)
    shutil.copyfile(CONTEXT, context)
    monkeypatch.chdir(tmp_path)
    assert (
        main(
            [
                "assurance",
                "verify",
                "--assessment",
                str(relocated),
                "--trust-context",
                str(context),
                "--json",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["reproduced"] is True


def test_public_old_new_no_impact_review_stays_stale_and_relocates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = FIXTURES / "no-impact-scope"
    old_assessment_path = folder / "out/old-assessment.json"
    current_assessment_path = folder / "out/current-assessment.json"
    immutable = [
        PLAN,
        CANDIDATE,
        SOURCE,
        ROOT / "tests/fixtures/artifacts/out/before-candidate.json",
        folder / "out/old-subject.json",
        old_assessment_path,
    ]
    before = [path.read_bytes() for path in immutable]
    old = read_json(old_assessment_path)
    review = read_json(folder / "review.json")
    assert old["gate_results"][0]["outcome"] == "pass"
    assert (
        main(
            [
                "assurance",
                "gate",
                "--request",
                str(folder / "current-gate-request.yaml"),
                "--out",
                str(current_assessment_path),
                "--json",
            ]
        )
        == 1
    )
    assert json.loads(capsys.readouterr().out)["outcome"] == "stale"
    current = read_json(current_assessment_path)
    freshness = current["gate_results"][0]["freshness"]
    assert freshness["prior_assessment_digest"] == old["digest"]
    assert freshness["no_impact_decision_digest"] == review["digest"]
    assert freshness["scope_expansion"] == "whole_gate"
    assert freshness["unknown_dependencies"] is False
    assert "/as_of" in freshness["changed_bindings"]
    assert freshness["impact_paths"] == [
        "/",
        "/native/fixture-component:score:COMP_REQ_001@1",
        "/native/fixture-component:score:COMP_REQ_001@1/fixture-component:score:INTERFACE_001@1",
        "/native/fixture-component:score:COMP_REQ_001@1/fixture-component:score:TEST_CASE_001@1",
    ]
    assert freshness["affected_evidence_ids"] == ["fixture-evidence-005"]
    assert freshness["affected_decision_ids"] == ["fixture-decision-005"]
    assert freshness["affected_gate_ids"] == ["component-verification"]
    assert all(item["state"] == "stale" for item in current["gate_results"][0]["predicate_results"])
    assert [path.read_bytes() for path in immutable] == before

    relocated = tmp_path / "assessment.json"
    context = tmp_path / "context.json"
    shutil.copyfile(current_assessment_path, relocated)
    shutil.copyfile(CONTEXT, context)
    monkeypatch.chdir(tmp_path)
    assert (
        main(
            [
                "assurance",
                "verify",
                "--assessment",
                str(relocated),
                "--trust-context",
                str(context),
                "--json",
            ]
        )
        == 0
    )
    replay = json.loads(capsys.readouterr().out)
    assert replay["reproduced"] is True
    assert replay["outcome"] == "stale"


def test_public_verify_exits_for_replay_mismatch_and_malformed_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import subprocess

    from score_sw_fabric import storage
    from score_sw_fabric.assurance.models import seal
    from score_sw_fabric.catalog.export import canonical

    selected_storage = storage.select_storage()
    monkeypatch.setattr(storage, "select_storage", lambda: selected_storage)

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("Offline verifier invoked an external runtime")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    blocked = FIXTURES / "blocked-scope/out/assessment.json"
    args = ["assurance", "verify", "--trust-context", str(CONTEXT), "--json"]
    assert main([*args, "--assessment", str(blocked)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["reproduced"] is True and result["outcome"] == "blocked"

    altered = read_json(blocked)
    altered["readable_report"]["next_route"] = "release"
    mismatch = tmp_path / "mismatch.json"
    mismatch.write_bytes(canonical(seal(altered)))
    assert main([*args, "--assessment", str(mismatch)]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["reproduced"] is False
    assert result["reason_codes"] == ["ASSESSMENT_MISMATCH"]

    altered["schema_version"] = 2
    malformed = tmp_path / "malformed.json"
    malformed.write_bytes(canonical(seal(altered)))
    assert main([*args, "--assessment", str(malformed)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert len(captured.err) < 8192
    assert json.loads(captured.err)["code"] == "VERSION_UNSUPPORTED"


def test_public_stale_gate_keeps_prior_output_on_forged_current_receipt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import yaml

    from score_sw_fabric.assurance.models import digest
    from score_sw_fabric.catalog.export import canonical
    from score_sw_fabric.process_source.reader import read_yaml

    folder = FIXTURES / "no-impact-scope"
    receipt = read_json(folder / "old-evidence-receipt.json")
    receipt["signature"] = (
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="
    )
    receipt["receipt_digest"] = digest(receipt, exclude="receipt_digest")
    selected_receipt = tmp_path / "forged-receipt.json"
    selected_receipt.write_bytes(canonical(receipt))
    request = read_yaml(folder / "current-gate-request.yaml")
    request["inputs"]["evidence_receipts"][0] = {
        "path": selected_receipt.name,
        "sha256": hashlib.sha256(selected_receipt.read_bytes()).hexdigest(),
        "semantic_digest": receipt["receipt_digest"],
    }
    selected_request = tmp_path / "request.yaml"
    selected_request.write_text(yaml.safe_dump(request))
    out = folder / "out/forged-current-guard.json"
    sentinel = b"prior-valid-output"
    out.write_bytes(sentinel)
    try:
        assert (
            main(
                [
                    "assurance",
                    "gate",
                    "--request",
                    str(selected_request),
                    "--out",
                    str(out),
                    "--json",
                ]
            )
            == 2
        )
        assert json.loads(capsys.readouterr().err)["code"] == "ASSESSMENT_MISMATCH"
        assert out.read_bytes() == sentinel
    finally:
        out.unlink()


def test_public_gate_identity_survives_request_path_and_input_order(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import yaml

    from score_sw_fabric.process_source.reader import read_yaml

    folder = FIXTURES / "passing-scope"
    original = folder / "out/assessment.json"
    original_bytes = original.read_bytes()
    request = read_yaml(folder / "gate-request.yaml")
    request["inputs"] = dict(reversed(list(request["inputs"].items())))
    relocated_request = tmp_path / "permuted-request.yaml"
    relocated_request.write_text(yaml.safe_dump(request, sort_keys=False))
    out = folder / "out/path-order-guard.json"
    try:
        assert (
            main(
                [
                    "assurance",
                    "gate",
                    "--request",
                    str(relocated_request),
                    "--out",
                    str(out),
                    "--json",
                ]
            )
            == 0
        )
        assert json.loads(capsys.readouterr().out)["outcome"] == "pass"
        assert out.read_bytes() == original_bytes
        assert original.read_bytes() == original_bytes
    finally:
        out.unlink(missing_ok=True)


def test_public_verify_missing_closed_ref_is_nonpass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from score_sw_fabric.assurance.models import seal
    from score_sw_fabric.catalog.export import canonical

    assessment = read_json(FIXTURES / "passing-scope/out/assessment.json")
    assessment["raw_output_refs"].clear()
    selected = tmp_path / "missing-raw.json"
    selected.write_bytes(canonical(seal(assessment)))
    assert (
        main(
            [
                "assurance",
                "verify",
                "--assessment",
                str(selected),
                "--trust-context",
                str(CONTEXT),
                "--json",
            ]
        )
        == 1
    )
    replay = json.loads(capsys.readouterr().out)
    assert replay["reproduced"] is False
    assert replay["reason_codes"] == ["RAW_OUTPUT_MISMATCH"]


def test_public_production_gate_cannot_promote_request_time(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import yaml

    from score_sw_fabric.process_source.reader import read_yaml

    folder = FIXTURES / "production-refusal-scope"
    original = folder / "out/assessment.json"
    original_bytes = original.read_bytes()
    request = read_yaml(folder / "gate-request.yaml")
    request["as_of"] = "2026-09-29T10:30:00Z"
    changed_request = tmp_path / "later-request.yaml"
    changed_request.write_text(yaml.safe_dump(request, sort_keys=False))
    out = folder / "out/later-time-guard.json"
    try:
        assert (
            main(
                [
                    "assurance",
                    "gate",
                    "--request",
                    str(changed_request),
                    "--out",
                    str(out),
                    "--json",
                ]
            )
            == 1
        )
        summary = json.loads(capsys.readouterr().out)
        assert summary["outcome"] == "blocked"
        assert "PRODUCTION_ORIGIN_UNAVAILABLE" in summary["reasons"]
        gate = read_json(out)["gate_results"][0]
        assert gate["outcome"] == "blocked"
        assert gate["time_basis_ref"] == "untrusted-request-time"
        assert original.read_bytes() == original_bytes
    finally:
        out.unlink(missing_ok=True)
