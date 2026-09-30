"""Real pinned S-CORE MCP servers from a disposable archive (AC007-01/03/05/06/09).

Set SCORE_MCP_SERVERS_SOURCE to a read-only checkout that contains the pinned commit. The
checkout is only read through `git archive`; the test asserts it is unchanged afterwards.
"""

from __future__ import annotations

import io
import os
import subprocess
import tarfile
from pathlib import Path

import pytest
import yaml

from score_sw_fabric.agents.context import build_context
from score_sw_fabric.agents.discover import discover, launch_argv, launch_environment, setup
from score_sw_fabric.agents.lock import load_lock
from score_sw_fabric.agents.mcp import McpSession, call_tool, initialize
from score_sw_fabric.agents.output import check
from tests.agent_support import (
    DEVELOPER,
    MODELS,
    REPO_LOCK,
    ROOT,
    digest,
    git,
    ref,
    write_json,
    write_yaml,
)

SOURCE = os.environ.get("SCORE_MCP_SERVERS_SOURCE")
LOCK = load_lock(REPO_LOCK.read_bytes())
COMMIT = LOCK["source"]["commit"]

pytestmark = pytest.mark.skipif(
    not SOURCE, reason="SCORE_MCP_SERVERS_SOURCE selects the read-only pinned checkout"
)


def _state(source: Path) -> tuple[str, str]:
    head = git(source, "rev-parse", "HEAD")
    status = git(source, "status", "--porcelain", "--ignored")
    return head, status


def _archive(source: Path, target: Path) -> None:
    payload = subprocess.run(
        ["git", "-C", str(source), "archive", COMMIT], check=True, capture_output=True
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(payload)) as archive:
        archive.extractall(target, filter="data")


def test_pinned_servers_discover_setup_context_and_check(tmp_path: Path) -> None:
    assert SOURCE is not None
    source = Path(SOURCE).resolve()
    before = _state(source)
    copy = tmp_path / "copy"
    _archive(source, copy)
    workspace = tmp_path / "workspace"
    (workspace / "docs").mkdir(parents=True)
    (workspace / "docs/req.rst").write_text("COMP_REQ_1 shall return 1.\n")
    git(workspace, "init", "-q")
    git(workspace, "add", ".")
    git(workspace, "commit", "-qm", "source")
    control = tmp_path / "control"
    protected = [str(source), str(ROOT)]
    base = {
        "schema_version": 1,
        "lock": ref(REPO_LOCK),
        "copy_root": str(copy),
        "workspace": str(workspace),
        "protected_roots": protected,
    }
    probes = [
        {"server": "apm-setup", "tool": "verify_setup", "arguments": {"repo_path": "$WORKSPACE"}},
        {"server": "context-discipline", "tool": "get_working_memory", "arguments": {}},
        {"server": "context-discipline", "tool": "get_unverified_assumptions", "arguments": {}},
        {"server": "context-discipline", "tool": "query_graph", "arguments": {"query": "main"}},
    ]
    request = control / "discover.yaml"
    write_yaml(
        request,
        {
            **base,
            "kind": "agent_discover_request",
            "servers": ["apm-setup", "context-discipline"],
            "probes": probes,
        },
    )
    status, inventory, _, _ = discover(request)
    assert status == 0, inventory["servers"]
    assert [item["outcome"] for item in inventory["probes"]] == ["ok"] * 4
    assert '"graphify_installed": false' in inventory["probes"][0]["result_text"]
    assert inventory["probes"][1]["result_text"] == "[]"
    assert '"ok": false' in inventory["probes"][3]["result_text"]
    assert {item["code"] for item in inventory["upstream_findings"]} == {"UPSTREAM_LAUNCH_UNPINNED"}
    inventory_ref = write_json(control / "inventory.json", inventory)

    unsupported = control / "unsupported.yaml"
    write_yaml(
        unsupported,
        {**base, "kind": "agent_discover_request", "servers": ["graphify-codegraph"], "probes": []},
    )
    status, record, _, _ = discover(unsupported)
    assert status == 1 and record["servers"][0]["status"] == "unsupported"

    setup_request = control / "setup.yaml"
    write_yaml(
        setup_request,
        {**base, "kind": "agent_setup_request", "operation": "context_discipline_store"},
    )
    status, first, _, _ = setup(setup_request)
    assert status == 0 and first["outcome"] == "changed"
    assert {item["path"] for item in first["changes"]} == {".gitignore"}
    assert (workspace / ".gitignore").read_text() == ".score-local/\n"
    status, second, _, _ = setup(setup_request)
    assert status == 0 and second["outcome"] == "unchanged" and second["idempotent"]

    context_request = control / "context.yaml"
    write_yaml(
        context_request,
        {
            "schema_version": 1,
            "kind": "agent_context_request",
            "lock": ref(REPO_LOCK),
            "inventory": inventory_ref,
            "role": ref(DEVELOPER),
            "model_profiles": ref(MODELS),
            "workspace": str(workspace),
            "task": {"id": "task.integration", "statement": "Implement COMP_REQ_1."},
            "native_sources": [
                {
                    "id": "COMP_REQ_1",
                    "path": "docs/req.rst",
                    "sha256": digest(workspace / "docs/req.rst"),
                }
            ],
            "assumptions": [],
            "observations": {"include_text": True, "bindings": []},
            "protected_roots": protected,
        },
    )
    status, bundle, _, _ = build_context(context_request)
    assert status == 0
    assert bundle["workspace"]["commit"] == git(workspace, "rev-parse", "HEAD")
    assert "mcp__context_discipline__get_prior_context" in {
        item["qualified_name"] for item in bundle["mcp_tools"]
    }
    bundle_ref = write_json(control / "bundle.json", bundle)

    server = next(item for item in LOCK["servers"] if item["id"] == "context-discipline")
    home = tmp_path / "home"
    home.mkdir()
    with McpSession(
        launch_argv(server),
        cwd=workspace,
        environment=launch_environment(server, copy, home),
        line_bytes=LOCK["limits"]["line_bytes"],
    ) as session:
        initialize(session, "2024-11-05", 10)
        call_tool(
            session, "initialize_session", {"goal": "COMP_REQ_1", "subgoals": ["code"]}, 30, 1 << 18
        )
        call_tool(
            session,
            "record_decision",
            {"decision": "Return a constant", "reason": ["Requirement is constant"]},
            30,
            1 << 18,
        )
    (workspace / "src").mkdir()
    (workspace / "src/component.cpp").write_text("int component() { return 1; }\n")
    result = {
        "schema_version": 1,
        "kind": "agent_result",
        "role_id": bundle["role"]["id"],
        "context_digest": bundle["digest"],
        "changed_paths": ["src/component.cpp"],
        "native_ids_affected": ["COMP_REQ_1"],
        "evidence_refs": [],
        "unresolved_assumptions": [],
        "proposed_next_action": "Run the trusted unit-test runner.",
        "self_reported_checks": [],
    }
    check_request = control / "check.yaml"
    write_yaml(
        check_request,
        {
            "schema_version": 1,
            "kind": "agent_check_request",
            "lock": ref(REPO_LOCK),
            "bundle": bundle_ref,
            "result": write_json(control / "result.json", result),
            "protected_roots": protected,
        },
    )
    status, checked, _, _ = check(check_request)
    assert status == 0 and checked["outcome"] == "within_bounds", checked["reasons"]
    assert len(checked["observation_bindings"]) >= 2

    (workspace / "README.md").write_text("outside scope\n")
    status, stopped, _, _ = check(check_request)
    assert status == 1
    assert {"code": "WRITE_OUT_OF_SCOPE", "path": "README.md"} in stopped["violations"]

    (copy / "packages/context-discipline/src/context_policy.py").write_text("# changed\n")
    status, drift, _, _ = discover(request)
    assert status == 1
    assert drift["servers"][1]["findings"] == [
        {"code": "LOCK_FILE_DRIFT", "detail": "packages/context-discipline/src/context_policy.py"}
    ]
    assert _state(source) == before
    assert yaml.safe_load(REPO_LOCK.read_text())["source"]["commit"] == COMMIT
