"""Fabro output and answers stay runtime context; fixture 005 cannot become production."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.runtime.export import build_export, verify_export
from score_sw_fabric.runtime.ledger import IntentLedger
from tests.runtime_support import LINEAR, FakeFabro, intent, linear_sources, project

FIXTURE_REFERENCE = {
    "assessment_digest": "e291defaa985c8f9394aa144c2230bfab9480c66c88539b3d41b24a473c67bb0",
    "assurance_domain": "fixture_contract",
    "outcome": "pass",
    "origin": "authenticated_005_reference",
}


def _export(
    tmp_path: Path,
    fabro: FakeFabro,
    references: list[dict[str, Any]],
    *,
    answer: bool = False,
) -> Any:
    client = fabro.client()
    package, compiler_profile = linear_sources()
    selected = intent(package, client)
    ledger = IntentLedger(tmp_path / "ledger")
    ledger.prepare(
        selected,
        version_id=client.register_package(package, compiler_profile),
        runtime_commit="a" * 40,
        source_package_digest=package["digest"],
        wire_digest=project(package, compiler_profile)["wire_digest"],
    )
    (tmp_path / "target").mkdir()
    client.create_run(
        ledger,
        selected["intent_id"],
        target=tmp_path / "target",
        disposable_root=tmp_path,
        environment_id="local",
        labels={},
    )
    binding = client.start_known_run(ledger, selected["intent_id"])
    if answer:
        # A native answer from any actor is still a runtime observation.
        fabro.runs[binding["run_id"]].record(
            {"kind": "interview.answered", "question": "review#1", "actor": "claimed-reviewer"}
        )
    return build_export(
        client,
        binding,
        package_bytes=(LINEAR / "out/package.json").read_bytes(),
        compiler_profile_bytes=(LINEAR / "compiler_profile.yaml").read_bytes(),
        assurance_references=references,
        output_limit=4096,
    )


def test_native_answer_and_output_are_runtime_observations_only(tmp_path: Path) -> None:
    record = _export(tmp_path, FakeFabro(start_outcome="blocked"), [], answer=True)
    assert record["status"]["native_answers_observed"] == 1
    assert record["status"]["assurance_decisions"] == 0
    result = verify_export(record)
    assert result["native_answers_observed"] == 1
    assert result["assurance_decisions"] == 0
    assert result["engineering_readiness"] == "not_evaluated"
    assert {item["origin"] for item in record["blobs"] if not item["id"].startswith("source:")} == {
        "runtime_observation"
    }


def test_fixture_005_reference_is_retained_but_never_production_eligible(tmp_path: Path) -> None:
    record = _export(tmp_path, FakeFabro(), [FIXTURE_REFERENCE])
    assert record["assurance_references"] == [FIXTURE_REFERENCE]
    result = verify_export(record)
    assert result["reproduced"] is True
    assert result["assurance_references"] == [
        {
            "assessment_digest": FIXTURE_REFERENCE["assessment_digest"],
            "assurance_domain": "fixture_contract",
            "origin": "authenticated_005_reference",
            "production_eligible": False,
        }
    ]


def test_production_domain_reference_is_refused_while_authority_is_unavailable(
    tmp_path: Path,
) -> None:
    production = {**FIXTURE_REFERENCE, "assurance_domain": "production"}
    with pytest.raises(InputError) as error:
        _export(tmp_path / "build", FakeFabro(), [production])
    assert error.value.code == "PRODUCTION_AUTHORITY_UNAVAILABLE"
    (tmp_path / "copy").mkdir()
    record = deepcopy(_export(tmp_path / "copy", FakeFabro(), [FIXTURE_REFERENCE]))
    record["assurance_references"] = [production]
    result = verify_export(seal({key: value for key, value in record.items() if key != "digest"}))
    assert "PRODUCTION_AUTHORITY_UNAVAILABLE" in result["reason_codes"]
    assert result["completeness"] == "incomplete"


def test_unknown_reference_origin_or_domain_is_rejected(tmp_path: Path) -> None:
    record = _export(tmp_path, FakeFabro(), [FIXTURE_REFERENCE])
    for change in ({"origin": "fabro_answer"}, {"assurance_domain": "promoted"}):
        changed = deepcopy(record)
        changed["assurance_references"] = [{**FIXTURE_REFERENCE, **change}]
        with pytest.raises(InputError):
            verify_export(seal({key: value for key, value in changed.items() if key != "digest"}))
