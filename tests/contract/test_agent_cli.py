"""007 `score-fabric agent` exits, diagnostics, guarded outputs and schema alignment."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from score_sw_fabric.agents import admission, context, discover, lock, output, roles
from score_sw_fabric.cli import main
from tests.agent_support import MODELS, REPO_LOCK, ROOT, Scenario, admit_request


def run(capsys: pytest.CaptureFixture[str], *arguments: str) -> tuple[int, dict[str, object]]:
    status = main(["agent", *arguments, "--json"])
    captured = capsys.readouterr()
    text = captured.out if status == 0 else captured.err
    return status, json.loads(text.strip().splitlines()[-1])


def test_pipeline_exits_and_summaries(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    scenario = Scenario(tmp_path)
    out = tmp_path / "out"
    status, summary = run(
        capsys, "discover", "--request", str(scenario.discover()), "--out", str(out / "inv.json")
    )
    assert status == 0 and summary["outcome"] == "available"
    assert summary["servers"] == {"fake": "available"}
    assert summary["engineering_readiness"] == "not_evaluated"
    status, summary = run(
        capsys, "setup", "--request", str(scenario.setup()), "--out", str(out / "setup.json")
    )
    assert status == 0 and summary["outcome"] == "changed"
    status, summary = run(
        capsys,
        "context",
        "--request",
        str(scenario.context()),
        "--out",
        str(out / "bundle.json"),
    )
    assert status == 0 and summary["kind"] == "agent_context_bundle"
    status, summary = run(
        capsys, "admit", "--request", str(admit_request(tmp_path)), "--out", str(out / "a.json")
    )
    assert status == 0 and summary["decision"] == "admissible"


def test_blocked_discovery_exits_one_and_publishes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    scenario = Scenario(tmp_path, "identity")
    target = tmp_path / "out/inv.json"
    status, summary = run(
        capsys, "discover", "--request", str(scenario.discover()), "--out", str(target)
    )
    assert status == 1 and summary["outcome"] == "blocked"
    assert "SERVER_IDENTITY_MISMATCH" in summary["findings"]
    assert json.loads(target.read_text())["outcome"] == "blocked"


def test_invalid_input_exits_two_and_preserves_prior_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    scenario = Scenario(tmp_path)
    target = tmp_path / "out/inv.json"
    target.parent.mkdir()
    target.write_text("prior")
    scenario.lock["servers"][0]["tools"][0]["classification"] = "approve"
    scenario.rewrite_lock()
    status, diagnostic = run(
        capsys, "discover", "--request", str(scenario.discover()), "--out", str(target)
    )
    assert status == 2 and diagnostic["code"] == "FIELD_ENUM"
    assert set(diagnostic) == {"code", "pointer", "message"}
    assert target.read_text() == "prior"


@pytest.mark.parametrize("where", ["workspace", "protected", "input"])
def test_output_cannot_land_in_workspace_protected_root_or_input(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], where: str
) -> None:
    scenario = Scenario(tmp_path)
    request = scenario.discover()
    target = {
        "workspace": scenario.workspace / "inv.json",
        "protected": ROOT / "inv-should-not-exist.json",
        "input": request,
    }[where]
    before = request.read_bytes()
    status, diagnostic = run(capsys, "discover", "--request", str(request), "--out", str(target))
    assert status == 2 and diagnostic["code"] in {"OUTPUT_PROTECTED", "OUTPUT_ALIAS"}
    assert not (ROOT / "inv-should-not-exist.json").exists()
    assert request.read_bytes() == before


def _schema(name: str) -> dict[str, object]:
    return json.loads((ROOT / f"schemas/{name}.schema.json").read_text())


def _required(name: str) -> set[str]:
    value = _schema(name)["required"]
    assert isinstance(value, list)
    return set(value)


def test_schemas_match_code_fields_and_real_outputs(tmp_path: Path) -> None:
    envelope = {"schema_version", "kind"}
    assert _required("apm-context-lock") == lock.LOCK_FIELDS | envelope
    assert _required("agent-role-profile") == roles.ROLE_FIELDS | envelope
    assert _required("agent-model-profiles") == admission.PROFILES_FIELDS | envelope
    assert _required("agent-budget-ledger") == admission.LEDGER_FIELDS | envelope
    assert _required("agent-result") == output.RESULT_FIELDS | envelope
    assert _required("agent-discover-request") == discover.DISCOVER_FIELDS | envelope
    assert _required("agent-setup-request") == discover.SETUP_FIELDS | envelope
    assert _required("agent-context-request") == context.CONTEXT_FIELDS | envelope
    assert _required("agent-admit-request") == admission.ADMIT_FIELDS | envelope
    assert _required("agent-check-request") == output.CHECK_FIELDS | envelope
    for path in (REPO_LOCK, MODELS):
        data = yaml.safe_load(path.read_text())
        name = "apm-context-lock" if path == REPO_LOCK else "agent-model-profiles"
        assert set(data) == _required(name)
    scenario = Scenario(tmp_path)
    _, inventory, _, _ = discover.discover(scenario.discover())
    _, record, _, _ = discover.setup(scenario.setup())
    bundle_path, bundle = scenario.bundle()
    (scenario.workspace / "src").mkdir()
    (scenario.workspace / "src/component.cpp").write_text("x\n")
    _, checked, _, _ = output.check(scenario.check(bundle_path, scenario.result(bundle)))
    _, admitted, _, _ = admission.admit(admit_request(tmp_path))
    for name, value in (
        ("agent-capability-inventory", inventory),
        ("agent-setup-record", record),
        ("agent-context-bundle", bundle),
        ("agent-output-check", checked),
        ("agent-admission", admitted),
    ):
        assert set(value) == _required(name), name
    lock_schema = _schema("apm-context-lock")
    tools = lock_schema["$defs"]["tool"]["properties"]["classification"]["enum"]  # type: ignore[index]
    assert set(tools) == lock.CLASSIFICATIONS
    role_schema = _schema("agent-role-profile")
    assert set(role_schema["properties"]["role"]["enum"]) == roles.ROLES  # type: ignore[index]
