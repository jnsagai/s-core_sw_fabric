"""007 bounded MCP client, capability discovery and explicit setup (AC007-01–04)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from score_sw_fabric.agents.discover import discover, setup
from score_sw_fabric.agents.mcp import McpError, McpSession, call_tool, initialize, list_tools
from score_sw_fabric.process_source.reader import InputError
from tests.agent_support import FIXTURES, Scenario, git


def _session(tmp: Path, mode: str | None = None, line_bytes: int = 4096) -> McpSession:
    source = tmp / "src"
    source.mkdir(exist_ok=True)
    (source / "fake_mcp.py").write_text((FIXTURES / "fake_mcp.py").read_text())
    if mode:
        (source / "mode.txt").write_text(mode)
    return McpSession(
        [sys.executable, "-s", "-B", "-m", "fake_mcp"],
        cwd=tmp,
        environment={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(source), "HOME": str(tmp)},
        line_bytes=line_bytes,
    )


def test_client_handshake_lists_and_calls_skipping_notifications(tmp_path: Path) -> None:
    with _session(tmp_path) as session:
        init = initialize(session, "2024-11-05", 5)
        assert init["serverInfo"] == {"name": "fake", "version": "1.0.0"}
        assert [tool["name"] for tool in list_tools(session, 5, 10)] == ["read_info", "note"]
        assert call_tool(session, "read_info", {}, 5, 4096) == '{"ok": true, "mode": "normal"}'
        with pytest.raises(McpError) as error:
            call_tool(session, "unknown", {}, 5, 4096)
        assert error.value.code == "JSONRPC_ERROR"
        with pytest.raises(McpError) as error:
            call_tool(session, "read_info", {}, 5, 5)
        assert error.value.code == "RESULT_LIMIT"
    assert session.returncode == 0
    assert session.stderr_sha256 is not None


@pytest.mark.parametrize(
    ("mode", "code", "line_bytes"),
    [
        ("timeout", "TIMEOUT", 4096),
        ("oversize", "LINE_LIMIT", 1000),
        ("invalid_json", "PROTOCOL_ERROR", 4096),
        ("crash", "HANDSHAKE_FAILED", 4096),
    ],
)
def test_client_faults_have_stable_codes(
    tmp_path: Path, mode: str, code: str, line_bytes: int
) -> None:
    with pytest.raises(McpError) as error, _session(tmp_path, mode, line_bytes) as session:
        initialize(session, "2024-11-05", 1)
    assert error.value.code == code


def test_client_reports_tool_errors(tmp_path: Path) -> None:
    with _session(tmp_path, "tool_error") as session:
        initialize(session, "2024-11-05", 5)
        with pytest.raises(McpError) as error:
            call_tool(session, "read_info", {}, 5, 4096)
    assert error.value.code == "TOOL_ERROR"


def test_discovery_records_identity_tools_probe_and_startup_writes(tmp_path: Path) -> None:
    scenario = Scenario(tmp_path)
    status, record, _, protected = discover(scenario.discover())
    assert status == 0 and record["outcome"] == "available"
    server = record["servers"][0]
    assert server["status"] == "available" and server["findings"] == []
    assert server["observed"]["protocol_version"] == "2024-11-05"
    assert [tool["classification"] for tool in server["observed"]["tools"]] == [
        "local_observation_write",
        "context_read",
    ]
    assert {item["path"] for item in server["workspace_changes"]} == {
        ".score-local",
        ".score-local/started",
    }
    probe = record["probes"][0]
    assert probe["outcome"] == "ok" and probe["origin"] == "mcp_tool_result"
    assert '"ok": true' in probe["result_text"]
    assert record["unsupported"][0]["id"] == "graph"
    assert record["engineering_readiness"] == "not_evaluated"
    assert scenario.workspace in protected and scenario.copy in protected


@pytest.mark.parametrize(
    ("mode", "code"),
    [
        ("identity", "SERVER_IDENTITY_MISMATCH"),
        ("protocol", "PROTOCOL_MISMATCH"),
        ("extra_tool", "TOOL_UNLISTED"),
        ("missing_tool", "TOOL_MISSING"),
        ("schema_drift", "TOOL_SCHEMA_DRIFT"),
        ("crash", "HANDSHAKE_FAILED"),
        ("timeout", "HANDSHAKE_FAILED"),
        ("undeclared_write", "UNDECLARED_WORKSPACE_WRITE"),
        ("tool_error", "TOOL_CALL_FAILED"),
    ],
)
def test_discovery_blocks_on_each_drift(tmp_path: Path, mode: str, code: str) -> None:
    scenario = Scenario(tmp_path, mode)
    status, record, _, _ = discover(scenario.discover())
    assert status == 1 and record["outcome"] == "blocked"
    assert code in {item["code"] for item in record["servers"][0]["findings"]}
    if code != "TOOL_CALL_FAILED":
        assert all(item["outcome"] != "ok" for item in record["probes"])


def test_discovery_blocks_on_file_drift_without_launching(tmp_path: Path) -> None:
    scenario = Scenario(tmp_path)
    (scenario.copy / "NOTICE").write_text("changed")
    status, record, _, _ = discover(scenario.discover())
    assert status == 1
    assert record["servers"][0]["findings"] == [{"code": "LOCK_FILE_DRIFT", "detail": "NOTICE"}]
    assert not (scenario.workspace / ".score-local").exists()


def test_unsupported_server_is_explicit_and_blocks(tmp_path: Path) -> None:
    scenario = Scenario(tmp_path)
    status, record, _, _ = discover(scenario.discover(["fake", "graph"]))
    assert status == 1
    graph = record["servers"][1]
    assert graph["status"] == "unsupported" and graph["observed"] is None


@pytest.mark.parametrize(
    ("probes", "code"),
    [
        ([{"server": "fake", "tool": "note", "arguments": {}}], "PROBE_FORBIDDEN"),
        ([{"server": "fake-setup", "tool": "read_info", "arguments": {}}], "PROBE_FORBIDDEN"),
        ([{"server": "nope", "tool": "read_info", "arguments": {}}], "SERVER_UNKNOWN"),
        ([{"server": "fake", "tool": "read_info", "arguments": []}], "FIELD_TYPE"),
    ],
)
def test_discovery_refuses_unsafe_probes(tmp_path: Path, probes: list[object], code: str) -> None:
    scenario = Scenario(tmp_path)
    with pytest.raises(InputError) as error:
        discover(scenario.discover(probes=probes))
    assert error.value.code == code


def test_roots_must_be_disjoint_and_unprotected(tmp_path: Path) -> None:
    scenario = Scenario(tmp_path)
    scenario.protected = [str(scenario.workspace)]
    with pytest.raises(InputError) as error:
        discover(scenario.discover())
    assert error.value.code == "PROTECTED_ROOT"
    scenario.protected = []
    nested = scenario.copy / "ws"
    nested.mkdir()
    git(nested, "init", "-q")
    scenario.workspace = nested
    with pytest.raises(InputError) as error:
        discover(scenario.discover())
    assert error.value.code == "ROOT_OVERLAP"


def test_setup_is_explicit_idempotent_and_recorded(tmp_path: Path) -> None:
    scenario = Scenario(tmp_path)
    status, first, _, _ = setup(scenario.setup())
    assert status == 0 and first["outcome"] == "changed" and not first["idempotent"]
    assert {item["path"] for item in first["changes"]} == {
        ".gitignore",
        ".score-local",
        ".score-local/started",
    }
    status, second, _, _ = setup(scenario.setup())
    assert status == 0 and second["outcome"] == "unchanged" and second["idempotent"]
    assert second["changes"] == []


def test_setup_blocks_undeclared_writes_and_unknown_operations(tmp_path: Path) -> None:
    scenario = Scenario(tmp_path, "setup_stray")
    status, record, _, _ = setup(scenario.setup())
    assert status == 1 and record["outcome"] == "blocked"
    assert record["undeclared"] == ["stray.txt"]
    with pytest.raises(InputError) as error:
        setup(scenario.setup("install_everything"))
    assert error.value.code == "SETUP_UNSUPPORTED"


def test_setup_refuses_protected_workspace(tmp_path: Path) -> None:
    scenario = Scenario(tmp_path)
    scenario.protected = [str(tmp_path)]
    with pytest.raises(InputError) as error:
        setup(scenario.setup())
    assert error.value.code == "PROTECTED_ROOT"
    assert not (scenario.workspace / ".gitignore").exists()


def test_workspace_must_be_git_top_level(tmp_path: Path) -> None:
    scenario = Scenario(tmp_path)
    inner = scenario.workspace / "docs"
    scenario.workspace = inner
    with pytest.raises(InputError) as error:
        discover(scenario.discover())
    assert error.value.code == "WORKSPACE_NOT_GIT"
