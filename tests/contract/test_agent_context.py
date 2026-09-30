"""007 baseline-bound role context and labelled observations (AC007-05–07)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from score_sw_fabric.agents.context import build_context
from score_sw_fabric.agents.output import check
from score_sw_fabric.process_source.reader import InputError
from tests.agent_support import Scenario, git, write_json


def test_context_names_baseline_sources_tools_and_instructions(tmp_path: Path) -> None:
    scenario = Scenario(tmp_path)
    _, bundle = scenario.bundle()
    head = git(scenario.workspace, "rev-parse", "HEAD")
    assert bundle["workspace"]["commit"] == head
    assert bundle["native_sources"] == [
        {
            "id": "COMP_REQ_1",
            "path": "docs/req.rst",
            "sha256": bundle["native_sources"][0]["sha256"],
            "revision": head,
        }
    ]
    assert {item["tool"] for item in bundle["mcp_tools"]} == {"read_info", "note"}
    assert bundle["write_scope"] == ["src/**", ".score-local/**"]
    assert bundle["unresolved_assumptions"] == ["Safety classification is not approved."]
    assert bundle["runtime_agent_config"]["status"] == "candidate_not_executed"
    assert "COMP_REQ_1" in bundle["role_prompt"]["text"]
    assert bundle["engineering_readiness"] == "not_evaluated"


def test_changed_missing_or_uncommitted_sources_block(tmp_path: Path) -> None:
    scenario = Scenario(tmp_path)
    source = {"id": "COMP_REQ_1", "path": "docs/req.rst", "sha256": "0" * 64}
    with pytest.raises(InputError) as error:
        build_context(scenario.context(sources=[source]))
    assert error.value.code == "NATIVE_SOURCE_DRIFT"
    (scenario.workspace / "docs/new.rst").write_text("draft\n")
    import hashlib

    draft = {
        "id": "NEW",
        "path": "docs/new.rst",
        "sha256": hashlib.sha256(b"draft\n").hexdigest(),
    }
    with pytest.raises(InputError) as error:
        build_context(scenario.context(sources=[draft]))
    assert error.value.code == "NATIVE_SOURCE_UNCOMMITTED"
    with pytest.raises(InputError) as error:
        build_context(scenario.context(sources=[{**draft, "path": "../x"}]))
    assert error.value.code == "INPUT_PATH"


def test_role_server_must_be_discovered_available(tmp_path: Path) -> None:
    scenario = Scenario(tmp_path)
    inventory = scenario.inventory()
    record = json.loads(Path(inventory["path"]).read_text())
    record["servers"][0]["status"] = "blocked"
    from score_sw_fabric.assurance.models import seal

    blocked = write_json(tmp_path / "control/blocked.json", seal(record))
    with pytest.raises(InputError) as error:
        build_context(scenario.context(inventory=blocked))
    assert error.value.code == "INVENTORY_NOT_AVAILABLE"
    record["servers"][0]["findings"] = [{"code": "EDITED", "detail": "x"}]
    tampered = write_json(tmp_path / "control/tampered.json", record)
    with pytest.raises(InputError) as error:
        build_context(scenario.context(inventory=tampered))
    assert error.value.code == "SEMANTIC_DIGEST"


def test_forbidden_role_is_refused_before_context(tmp_path: Path) -> None:
    scenario = Scenario(tmp_path)
    with pytest.raises(InputError) as error:
        build_context(scenario.context(role=scenario.role(credentials=["approval"])))
    assert error.value.code == "CREDENTIAL_FORBIDDEN"
    with pytest.raises(InputError) as error:
        build_context(scenario.context(role=scenario.role(mcp_servers=["fake-setup"])))
    assert error.value.code == "SETUP_FORBIDDEN"


def test_credentials_in_task_are_refused(tmp_path: Path) -> None:
    scenario = Scenario(tmp_path)
    with pytest.raises(InputError) as error:
        build_context(scenario.context(task="Use api_key=abcdefghijkl to call it."))
    assert error.value.code == "CREDENTIAL_IN_CONTEXT"


def test_observations_are_hints_with_current_stale_and_uncertain_states(tmp_path: Path) -> None:
    scenario = Scenario(tmp_path)
    scenario.note("unbound older hint")
    bundle_path, bundle = scenario.bundle()
    assert [item["state"] for item in bundle["observations"]] == ["uncertain"]
    assert bundle["observations"][0]["text"] is None
    assert any("omitted" in item for item in bundle["omissions"])
    scenario.note("bound to first commit")
    (scenario.workspace / "src").mkdir()
    (scenario.workspace / "src/component.cpp").write_text("int f();\n")
    status, first, _, _ = check(scenario.check(bundle_path, scenario.result(bundle)))
    assert status == 0 and len(first["observation_bindings"]) == 1
    first_ref = write_json(tmp_path / "control/check-1.json", first)
    git(scenario.workspace, "add", "src")
    git(scenario.workspace, "commit", "-qm", "component")
    bundle_path, bundle = scenario.bundle(
        observations={"include_text": True, "bindings": [first_ref]}
    )
    scenario.note("bound to second commit")
    (scenario.workspace / "src/component.cpp").write_text("int f() { return 1; }\n")
    status, second, _, _ = check(scenario.check(bundle_path, scenario.result(bundle)))
    assert status == 0
    second_ref = write_json(tmp_path / "control/check-2.json", second)
    git(scenario.workspace, "commit", "-qam", "again")
    _, final = scenario.bundle(
        observations={"include_text": True, "bindings": [first_ref, second_ref]}
    )
    states = {item["text"]: (item["state"], item["origin"]) for item in final["observations"]}
    assert states["unbound older hint"] == ("uncertain", "local_observation_hint")
    assert states["bound to first commit"][0] == "stale"
    assert states["bound to second commit"][0] == "stale"
    head_bindings = {"include_text": True, "bindings": [second_ref]}
    git(scenario.workspace, "reset", "-q", "--hard", "HEAD~1")
    _, current = scenario.bundle(observations=head_bindings)
    by_text = {item["text"]: item["state"] for item in current["observations"]}
    assert by_text["bound to second commit"] == "current"


def test_credential_like_observation_text_is_withheld(tmp_path: Path) -> None:
    scenario = Scenario(tmp_path)
    scenario.note("token = fabro_dev_" + "a" * 64)
    _, bundle = scenario.bundle(observations={"include_text": True, "bindings": []})
    assert bundle["observations"][0]["text"] is None
    assert any("credential-like" in item for item in bundle["omissions"])
    assert "fabro_dev_" not in json.dumps(bundle)


def test_bindings_must_be_sealed_checks(tmp_path: Path) -> None:
    scenario = Scenario(tmp_path)
    bogus = write_json(tmp_path / "control/bogus.json", {"kind": "agent_output_check"})
    with pytest.raises(InputError):
        build_context(scenario.context(observations={"include_text": False, "bindings": [bogus]}))
