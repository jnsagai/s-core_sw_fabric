"""Declared assurance limits cannot exceed hard ceilings or be bypassed by stale reuse."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest

from score_sw_fabric.assurance.decisions import classify_decision
from score_sw_fabric.assurance.evidence import classify_evidence
from score_sw_fabric.assurance.gates import evaluate_gate
from score_sw_fabric.assurance.models import MAX_EVIDENCE, MAX_PREDICATES, seal
from score_sw_fabric.assurance.origins import validate_profile
from score_sw_fabric.process_source.reader import InputError, read_json, read_yaml

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "tests/fixtures/assurance/passing-scope"
NOW = datetime(2026, 9, 29, 10, tzinfo=UTC)


def _inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return (
        read_json(BASE / "out/subject.json"),
        read_json(BASE / "policy.json"),
        read_yaml(ROOT / "profiles/assurance-fixture-v1.yaml"),
    )


def _gate(policy: dict[str, Any], profile: dict[str, Any], *, mode: str = "normal") -> None:
    subject = _inputs()[0]
    evaluate_gate(
        subject,
        policy,
        profile,
        [read_json(BASE / "evidence.json")],
        [read_json(BASE / "evidence-receipt.json")],
        [read_json(BASE / "decision.json")],
        [read_json(BASE / "decision-receipt.json")],
        requested_domain="fixture_contract",
        requested_scope=subject["scope"],
        gate_id="component-verification",
        as_of=NOW,
        raw_root=BASE / "raw",
        mode=mode,
        prior_assessment=read_json(BASE / "out/assessment.json") if mode == "reuse_prior" else None,
    )


@pytest.mark.parametrize("selected", [MAX_PREDICATES + 1, True, -1])
def test_policy_predicate_limit_must_be_bounded_integer(selected: object) -> None:
    _, policy, profile = _inputs()
    policy["limits"]["predicates"] = selected
    policy = seal(policy)
    with pytest.raises(InputError, match="limit"):
        _gate(policy, profile)


def test_policy_predicate_count_cannot_exceed_declared_limit() -> None:
    _, policy, profile = _inputs()
    policy["limits"]["predicates"] = 2
    policy = seal(policy)
    with pytest.raises(InputError, match="Array limit"):
        _gate(policy, profile)


def test_stale_reuse_cannot_bypass_policy_evidence_limit() -> None:
    _, policy, profile = _inputs()
    policy["limits"]["evidence"] = 0
    policy = seal(policy)
    with pytest.raises(InputError, match="Gate input count"):
        _gate(policy, profile, mode="reuse_prior")


def test_trust_predicate_limit_applies_to_gate_matrix() -> None:
    _, policy, profile = _inputs()
    assert len(policy["predicates"]) == 3
    profile["limits"]["predicates"] = 3
    _gate(policy, seal(profile), mode="not_started")
    profile["limits"]["predicates"] = 2
    with pytest.raises(InputError) as error:
        _gate(policy, seal(profile), mode="not_started")
    assert error.value.code == "LIMIT_EXCEEDED"


def test_trust_reference_limit_applies_to_gate_receipts() -> None:
    subject, policy, profile = _inputs()
    profile["limits"]["references"] = 1
    selected = seal(profile)
    with pytest.raises(InputError) as error:
        evaluate_gate(
            subject,
            policy,
            selected,
            [read_json(BASE / "evidence.json")],
            [read_json(BASE / "evidence-receipt.json")],
            [read_json(BASE / "decision.json")],
            [read_json(BASE / "decision-receipt.json")],
            requested_domain="fixture_contract",
            requested_scope=subject["scope"],
            gate_id="component-verification",
            as_of=NOW,
            raw_root=BASE / "raw",
        )
    assert error.value.code == "LIMIT_EXCEEDED"


def test_trust_profile_rejects_one_over_and_boolean_limit() -> None:
    _, _, profile = _inputs()
    for selected in (MAX_EVIDENCE + 1, True):
        altered = deepcopy(profile)
        altered["limits"]["evidence"] = selected
        with pytest.raises(InputError, match="Invalid evidence limit"):
            validate_profile(seal(altered))


def test_elapsed_observation_over_declared_limit_is_ineligible() -> None:
    subject, policy, profile = _inputs()
    evidence = read_json(BASE / "evidence.json")
    evidence["limits"]["duration_seconds"] = 59
    evidence = seal(evidence)
    classified = classify_evidence(
        evidence,
        None,
        subject,
        policy,
        profile,
        requested_domain="fixture_contract",
        requested_scope=subject["scope"],
        as_of=NOW,
        raw_root=BASE / "raw",
    )
    assert not classified["eligible"]
    assert "LIMIT_EXCEEDED" in classified["reason_codes"]


@pytest.mark.parametrize(
    ("name", "maximum"),
    [
        ("control_bytes", 64 * 1024 * 1024),
        ("package_bytes", 64 * 1024 * 1024),
        ("predicates", MAX_PREDICATES),
        ("evidence", MAX_EVIDENCE),
        ("decisions", 10_000),
        ("references", 10_000),
        ("findings", 20_000),
        ("depth", 32),
    ],
)
def test_trust_limit_exact_ceiling_and_one_over(name: str, maximum: int) -> None:
    _, _, profile = _inputs()
    at_ceiling = deepcopy(profile)
    at_ceiling["limits"][name] = maximum
    validate_profile(seal(at_ceiling))
    over = deepcopy(profile)
    over["limits"][name] = maximum + 1
    with pytest.raises(InputError, match=f"Invalid {name} limit"):
        validate_profile(seal(over))


@pytest.mark.parametrize("kind", ["evidence", "decisions"])
def test_gate_count_exact_declared_limit_and_one_over(kind: str) -> None:
    _, policy, profile = _inputs()
    policy["limits"][kind] = 1
    policy = seal(policy)
    _gate(policy, profile, mode="not_started")
    subject = _inputs()[0]
    evidence = [read_json(BASE / "evidence.json")]
    decisions = [read_json(BASE / "decision.json")]
    selected = evidence if kind == "evidence" else decisions
    selected.append(deepcopy(selected[0]))
    with pytest.raises(InputError, match="Gate input count"):
        evaluate_gate(
            subject,
            policy,
            profile,
            evidence,
            [],
            decisions,
            [],
            requested_domain="fixture_contract",
            requested_scope=subject["scope"],
            gate_id="component-verification",
            as_of=NOW,
            raw_root=BASE / "raw",
            mode="not_started",
        )


def test_reference_depth_exact_ceiling_and_one_over() -> None:
    from score_sw_fabric.assurance.models import MAX_DEPTH
    from score_sw_fabric.assurance.reader import _depth

    nested: object = "leaf"
    for _ in range(MAX_DEPTH):
        nested = {"child": nested}
    _depth(nested)
    with pytest.raises(InputError, match="nesting exceeds"):
        _depth({"child": nested})


def test_freshness_findings_exact_ceiling_and_one_over(monkeypatch: pytest.MonkeyPatch) -> None:
    from score_sw_fabric.assurance import freshness

    monkeypatch.setattr(freshness, "MAX_FINDINGS", 2)
    changed: list[str] = []
    freshness._differences({"a": 0, "b": 0}, {"a": 1, "b": 1}, "", changed)
    assert changed == ["/a", "/b"]
    with pytest.raises(InputError, match="finding limit"):
        freshness._differences({"a": 0, "b": 0, "c": 0}, {"a": 1, "b": 1, "c": 1}, "", [])


def test_output_bytes_exact_ceiling_and_one_over_preserve_prior(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from score_sw_fabric.assurance import package
    from score_sw_fabric.catalog.export import canonical

    out = tmp_path / "result.json"
    record = {"kind": "test", "value": "complete"}
    size = len(canonical(record))
    monkeypatch.setattr(package, "MAX_CONTROL_BYTES", size)
    package.publish(out, record)
    original = out.read_bytes()
    assert len(original) == size
    monkeypatch.setattr(package, "MAX_CONTROL_BYTES", size - 1)
    with pytest.raises(InputError, match="exceeds 64 MiB"):
        package.publish(out, record)
    assert out.read_bytes() == original


def test_interrupted_atomic_publication_preserves_prior(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from score_sw_fabric.assurance import package

    out = tmp_path / "result.json"
    out.write_bytes(b"prior complete output")

    def interrupted(_source: object, _destination: object) -> None:
        raise OSError("simulated interrupted replacement")

    monkeypatch.setattr(package.os, "replace", interrupted)
    with pytest.raises(InputError, match="simulated interrupted replacement"):
        package.publish(out, {"kind": "test"})
    assert out.read_bytes() == b"prior complete output"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["result.json"]


def test_observation_duration_exact_declared_limit_and_one_over() -> None:
    subject, policy, profile = _inputs()
    evidence = read_json(BASE / "evidence.json")
    receipt = read_json(BASE / "evidence-receipt.json")
    evidence["limits"]["duration_seconds"] = 60
    at_limit = classify_evidence(
        seal(evidence),
        receipt,
        subject,
        policy,
        profile,
        requested_domain="fixture_contract",
        requested_scope=subject["scope"],
        as_of=NOW,
        raw_root=BASE / "raw",
    )
    assert "LIMIT_EXCEEDED" not in at_limit["reason_codes"]
    evidence["limits"]["duration_seconds"] = 59
    over_limit = classify_evidence(
        seal(evidence),
        receipt,
        subject,
        policy,
        profile,
        requested_domain="fixture_contract",
        requested_scope=subject["scope"],
        as_of=NOW,
        raw_root=BASE / "raw",
    )
    assert "LIMIT_EXCEEDED" in over_limit["reason_codes"]


def test_public_malformed_diagnostic_is_bounded(tmp_path: Path, capsys: Any) -> None:
    import json

    from score_sw_fabric.cli import main

    request = tmp_path / "oversized-key.json"
    request.write_text(json.dumps({"x" * 20_000: 1}))
    out = tmp_path / "prior.json"
    out.write_bytes(b"prior complete output")
    assert (
        main(["assurance", "subject", "--request", str(request), "--out", str(out), "--json"]) == 2
    )
    error = json.loads(capsys.readouterr().err)
    assert error["code"] == "FIELD_UNKNOWN"
    assert len(error["message"]) <= 4096
    assert out.read_bytes() == b"prior complete output"


def test_request_reference_count_exact_ceiling_and_one_over(tmp_path: Path) -> None:
    import json

    from score_sw_fabric.assurance.models import MAX_REFERENCES
    from score_sw_fabric.assurance.reader import read_request

    subject = _inputs()[0]
    request = {
        "schema_version": 1,
        "operation": "subject",
        "assurance_domain": "fixture_contract",
        "scope": subject["scope"],
        "inputs": {f"ref-{index:05d}": None for index in range(MAX_REFERENCES)},
        "local_paths": {"protected_roots": []},
        "output_root": "out",
        "as_of": "2026-09-29T10:00:00Z",
    }
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request))
    assert len(read_request(path, "subject")["inputs"]) == MAX_REFERENCES
    request["inputs"]["one-over"] = None
    path.write_text(json.dumps(request))
    with pytest.raises(InputError, match="Invalid assurance input set"):
        read_request(path, "subject")


@pytest.mark.parametrize(
    "name", ["MAX_PREDICATES", "MAX_EVIDENCE", "MAX_DECISIONS", "MAX_REFERENCES", "MAX_FINDINGS"]
)
def test_shared_array_hard_ceiling_exact_and_one_over(name: str) -> None:
    from score_sw_fabric.assurance import models

    limit = getattr(models, name)
    items = [None] * limit
    assert models.bounded_list(items, limit, "/matrix") is items
    items.append(None)
    with pytest.raises(InputError) as error:
        models.bounded_list(items, limit, "/matrix")
    assert error.value.code == "LIMIT_EXCEEDED"
    assert error.value.pointer == "/matrix"


@pytest.mark.parametrize(
    ("field", "ceiling"),
    [
        ("obligation_ids", 1),
        ("inputs", 2),
        ("raw_outputs", 2),
        ("import_chain", 2),
        ("exclusions", 2),
        ("limitations", 2),
    ],
)
def test_evidence_array_exact_limit_and_one_over(
    field: str, ceiling: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    from score_sw_fabric.assurance import evidence as module

    monkeypatch.setattr(module, "MAX_EVIDENCE", 1)
    monkeypatch.setattr(module, "MAX_REFERENCES", 2)
    subject, policy, profile = _inputs()
    original = read_json(BASE / "evidence.json")
    record = deepcopy(original)
    while len(record[field]) < ceiling:
        if field == "obligation_ids":
            record[field].append("extra-obligation")
        elif field == "raw_outputs":
            record[field].append(
                {"path": f"missing-{len(record[field])}.txt", "sha256": "0" * 64, "bytes": 0}
            )
        else:
            record[field].append({"extra": len(record[field])})
    exact = seal(record)
    try:
        classify_evidence(
            exact,
            None,
            subject,
            policy,
            profile,
            requested_domain="fixture_contract",
            requested_scope=subject["scope"],
            as_of=NOW,
            raw_root=BASE / "raw",
        )
    except InputError as error:
        assert error.code != "LIMIT_EXCEEDED"
    record[field].append(deepcopy(record[field][-1]))
    with pytest.raises(InputError) as error:
        classify_evidence(
            seal(record),
            None,
            subject,
            policy,
            profile,
            requested_domain="fixture_contract",
            requested_scope=subject["scope"],
            as_of=NOW,
            raw_root=BASE / "raw",
        )
    assert error.value.code == "LIMIT_EXCEEDED"
    assert error.value.pointer == f"/evidence/{field}"


@pytest.mark.parametrize(
    "path",
    [
        ("obligation_ids",),
        ("gate_ids",),
        ("conditions",),
        ("independence", "rule_ids"),
        ("independence", "checked_relationships"),
    ],
)
def test_decision_array_exact_limit_and_one_over(
    path: tuple[str, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    from score_sw_fabric.assurance import decisions as module

    monkeypatch.setattr(module, "MAX_DECISIONS", 2)
    subject, policy, profile = _inputs()
    record = read_json(BASE / "decision.json")
    selected = record
    for part in path[:-1]:
        selected = selected[part]
    field = path[-1]
    while len(selected[field]) < 2:
        selected[field].append(f"extra-{len(selected[field])}")
    exact = seal(record)
    try:
        classify_decision(
            exact,
            None,
            subject,
            policy,
            profile,
            requested_domain="fixture_contract",
            requested_scope=subject["scope"],
            gate_id="component-verification",
            as_of=NOW,
        )
    except InputError as error:
        assert error.code != "LIMIT_EXCEEDED"
    selected[field].append("one-over")
    with pytest.raises(InputError) as error:
        classify_decision(
            seal(record),
            None,
            subject,
            policy,
            profile,
            requested_domain="fixture_contract",
            requested_scope=subject["scope"],
            gate_id="component-verification",
            as_of=NOW,
        )
    assert error.value.code == "LIMIT_EXCEEDED"
    assert error.value.pointer == "/decision/" + "/".join(path)


@pytest.mark.parametrize(
    ("operation", "limit", "selected"),
    [
        ("evidence", "evidence", 0),
        ("decision", "decisions", 0),
        ("evidence", "references", 0),
        ("decision", "references", 0),
        ("gate", "references", 1),
        ("evidence", "predicates", 2),
        ("decision", "predicates", 2),
        ("gate", "predicates", 2),
    ],
)
def test_public_selected_trust_limit_preserves_prior(
    operation: str, limit: str, selected: int, capsys: pytest.CaptureFixture[str]
) -> None:
    import hashlib
    import json

    from score_sw_fabric.catalog.export import canonical
    from score_sw_fabric.cli import main

    with TemporaryDirectory(prefix=".assurance-limits-", dir=ROOT) as directory:
        scratch = Path(directory)
        profile = read_yaml(ROOT / "profiles/assurance-fixture-v1.yaml")
        profile["limits"][limit] = selected
        profile = seal(profile)
        profile_bytes = canonical(profile)
        (scratch / "profile.json").write_bytes(profile_bytes)
        request = read_yaml(BASE / f"{operation}-request.yaml")
        request["inputs"]["trust_profile"] = {
            "path": "profile.json",
            "sha256": hashlib.sha256(profile_bytes).hexdigest(),
            "semantic_digest": profile["digest"],
        }
        request["output_root"] = f"{scratch.name}/out"
        request_path = scratch / "request.json"
        request_path.write_text(json.dumps(request))
        out = scratch / f"out/{operation}.json"
        out.parent.mkdir()
        out.write_bytes(b"prior complete output")
        assert (
            main(
                [
                    "assurance",
                    operation,
                    "--request",
                    str(request_path),
                    "--out",
                    str(out),
                    "--json",
                ]
            )
            == 2
        )
        diagnostic = json.loads(capsys.readouterr().err)
        assert diagnostic["code"] == "LIMIT_EXCEEDED"
        assert out.read_bytes() == b"prior complete output"


@pytest.mark.parametrize(
    ("operation", "limit"), [("evidence", "evidence"), ("decision", "decisions")]
)
def test_public_selected_policy_limit_preserves_prior(
    operation: str, limit: str, capsys: pytest.CaptureFixture[str]
) -> None:
    import hashlib
    import json

    from score_sw_fabric.catalog.export import canonical
    from score_sw_fabric.cli import main

    with TemporaryDirectory(prefix=".assurance-limits-", dir=ROOT) as directory:
        scratch = Path(directory)
        policy = read_json(BASE / "policy.json")
        policy["limits"][limit] = 0
        policy = seal(policy)
        policy_bytes = canonical(policy)
        (scratch / "policy.json").write_bytes(policy_bytes)
        request = read_yaml(BASE / f"{operation}-request.yaml")
        request["inputs"]["policy"] = {
            "path": "policy.json",
            "sha256": hashlib.sha256(policy_bytes).hexdigest(),
            "semantic_digest": policy["digest"],
        }
        request["output_root"] = f"{scratch.name}/out"
        request_path = scratch / "request.json"
        request_path.write_text(json.dumps(request))
        out = scratch / f"out/{operation}.json"
        out.parent.mkdir()
        out.write_bytes(b"prior complete output")
        assert (
            main(
                [
                    "assurance",
                    operation,
                    "--request",
                    str(request_path),
                    "--out",
                    str(out),
                    "--json",
                ]
            )
            == 2
        )
        assert json.loads(capsys.readouterr().err)["code"] == "LIMIT_EXCEEDED"
        assert out.read_bytes() == b"prior complete output"
