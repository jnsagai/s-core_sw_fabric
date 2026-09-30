"""Disposable fixture copies, workspaces and requests for 007 agent contract tests."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import yaml

from score_sw_fabric.agents.lock import tool_digest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/agents"
CATALOGUE = ROOT / "docs/evidence/007/fabro-catalogue"
REPO_LOCK = ROOT / "profiles/apm-context-29aeaa8-v1.yaml"
DEVELOPER = ROOT / "profiles/agent-role-developer-draft-v1.yaml"
CRITIC = ROOT / "profiles/agent-role-critic-draft-v1.yaml"
MODELS = ROOT / "profiles/agent-model-profiles-draft-v1.yaml"
RUNTIME_COMMIT = "1b4fb15281ebb724426f9e480dce48d0100ff79b"
EXECUTABLE = "09d338fbbe107d6c2e41fe9f3b33531c72b54782a2e17dac7c720b89898a68cf"
ROLE_ID = "role.fake.draft"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref(path: Path) -> dict[str, str]:
    return {"path": str(path), "sha256": digest(path)}


def write_yaml(path: Path, value: Any) -> dict[str, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False))
    return ref(path)


def write_json(path: Path, value: Any) -> dict[str, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    return ref(path)


def git(workspace: Path, *arguments: str) -> str:
    return subprocess.run(
        [
            "git",
            "-C",
            str(workspace),
            "-c",
            "user.email=t@example.invalid",
            "-c",
            "user.name=t",
            *arguments,
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def make_workspace(tmp: Path) -> Path:
    workspace = tmp / "workspace"
    (workspace / "docs").mkdir(parents=True)
    (workspace / "docs/req.rst").write_text("COMP_REQ_1 shall return 1.\n")
    git(workspace, "init", "-q")
    git(workspace, "add", ".")
    git(workspace, "commit", "-qm", "source")
    return workspace


def _fixture_tools(setup: bool) -> list[dict[str, Any]]:
    spec = importlib.util.spec_from_file_location("fake_mcp_fixture", FIXTURES / "fake_mcp.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tools: list[dict[str, Any]] = module.TOOLS
    return tools if setup else tools[:2]


MANIFEST = {
    "name": "fake",
    "dependencies": {
        "mcp": [
            {
                "name": "fake",
                "command": "uvx",
                "args": ["--from", "git+https://example.invalid/fake#subdirectory=pkg", "fake"],
            },
            {
                "name": "fake-setup",
                "command": "uvx",
                "args": ["--from", f"git+https://example.invalid/fake@{'a' * 40}", "fake-setup"],
            },
            {"name": "graph", "command": "uvx", "args": ["graph"]},
        ]
    },
}


def make_copy(tmp: Path, mode: str | None = None) -> Path:
    copy = tmp / "copy"
    (copy / "pkg/src").mkdir(parents=True)
    (copy / "LICENSE").write_text("Apache-2.0 fixture\n")
    (copy / "NOTICE").write_text("Fixture notice\n")
    (copy / "pkg/apm.yml").write_text(yaml.safe_dump(MANIFEST))
    for name in ("fake_mcp.py", "fake_setup.py"):
        shutil.copy(FIXTURES / name, copy / "pkg/src" / name)
    if mode is not None:
        (copy / "pkg/src/mode.txt").write_text(mode)
    return copy


def _server(server_id: str, module: str, setup: bool) -> dict[str, Any]:
    entry = next(item for item in MANIFEST["dependencies"]["mcp"] if item["name"] == server_id)  # type: ignore[index]
    classes = {"read_info": "context_read", "note": "local_observation_write"}
    return {
        "id": server_id,
        "package": server_id,
        "manifest": "pkg/apm.yml",
        "status": "supported",
        "unsupported_reason": None,
        "upstream_launch": {"command": entry["command"], "args": entry["args"]},
        "launch": {"kind": "python_module", "python_path": ["pkg/src"], "module": module},
        "expected": {
            "server_name": "fake",
            "server_version": "1.0.0",
            "protocol_version": "2024-11-05",
        },
        "startup_writes": [".score-local/**"],
        "tools": [
            {
                "name": tool["name"],
                "classification": classes.get(tool["name"], "setup_privileged"),
                "schema_sha256": tool_digest(tool),
            }
            for tool in _fixture_tools(setup)
        ],
    }


def lock_record(copy: Path) -> dict[str, Any]:
    files = ["LICENSE", "NOTICE", "pkg/apm.yml", "pkg/src/fake_mcp.py", "pkg/src/fake_setup.py"]
    return {
        "schema_version": 1,
        "kind": "apm_context_lock",
        "id": "fixture-lock",
        "status": "fixture",
        "source": {
            "repository": "https://example.invalid/fake",
            "commit": "b" * 40,
            "license": "Apache-2.0",
            "license_path": "LICENSE",
            "notice_path": "NOTICE",
        },
        "files": [{"path": name, "sha256": digest(copy / name)} for name in files],
        "servers": [
            _server("fake", "fake_mcp", False),
            _server("fake-setup", "fake_setup", True),
            {
                "id": "graph",
                "package": "graph",
                "manifest": "pkg/apm.yml",
                "status": "unsupported",
                "unsupported_reason": "External dependency is not installed.",
                "upstream_launch": {"command": "uvx", "args": ["graph"]},
                "launch": None,
                "expected": {"server_name": None, "server_version": None, "protocol_version": None},
                "startup_writes": [],
                "tools": [],
            },
        ],
        "setup_operations": [
            {
                "id": "store",
                "server": "fake-setup",
                "tool": "setup_store",
                "declared_writes": [".score-local/**", ".gitignore"],
            }
        ],
        "runtime_client": {
            "name": "fabro-rmcp",
            "protocol_version": "2025-03-26",
            "compatibility": "not_verified",
        },
        "limits": {
            "handshake_seconds": 5,
            "tool_seconds": 5,
            "line_bytes": 4096,
            "result_bytes": 4096,
        },
    }


class Scenario:
    """One disposable copy, workspace and lock with request writers."""

    def __init__(self, tmp: Path, mode: str | None = None) -> None:
        self.tmp = tmp
        self.copy = make_copy(tmp, mode)
        self.workspace = make_workspace(tmp)
        self.lock = lock_record(self.copy)
        self.lock_ref = write_yaml(tmp / "control/lock.yaml", self.lock)
        self.protected = [str(ROOT)]

    def rewrite_lock(self) -> None:
        self.lock_ref = write_yaml(self.tmp / "control/lock.yaml", self.lock)

    def discover(self, servers: list[str] | None = None, probes: list[Any] | None = None) -> Path:
        path = self.tmp / "control/discover.yaml"
        write_yaml(
            path,
            {
                "schema_version": 1,
                "kind": "agent_discover_request",
                "lock": self.lock_ref,
                "copy_root": str(self.copy),
                "workspace": str(self.workspace),
                "servers": servers if servers is not None else ["fake"],
                "probes": probes
                if probes is not None
                else [
                    {
                        "server": "fake",
                        "tool": "read_info",
                        "arguments": {"repo_path": "$WORKSPACE"},
                    }
                ],
                "protected_roots": self.protected,
            },
        )
        return path

    def setup(self, operation: str = "store") -> Path:
        path = self.tmp / "control/setup.yaml"
        write_yaml(
            path,
            {
                "schema_version": 1,
                "kind": "agent_setup_request",
                "lock": self.lock_ref,
                "copy_root": str(self.copy),
                "workspace": str(self.workspace),
                "operation": operation,
                "protected_roots": self.protected,
            },
        )
        return path

    def role(self, **changes: Any) -> dict[str, Any]:
        role: dict[str, Any] = yaml.safe_load(DEVELOPER.read_text())
        role.update(
            {
                "id": ROLE_ID,
                "mcp_servers": ["fake"],
                "write_scope": ["src/**", ".score-local/**"],
                "allowed_inputs": ["docs/**", "src/**"],
            }
        )
        role.update(changes)
        return role

    def inventory(self) -> dict[str, str]:
        from score_sw_fabric.agents.discover import discover

        status, record, _, _ = discover(self.discover())
        assert status == 0, record
        return write_json(self.tmp / "control/inventory.json", record)

    def context(
        self,
        *,
        role: dict[str, Any] | None = None,
        inventory: dict[str, str] | None = None,
        sources: list[dict[str, Any]] | None = None,
        observations: dict[str, Any] | None = None,
        task: str = "Implement COMP_REQ_1 in src/component.cpp.",
    ) -> Path:
        path = self.tmp / "control/context.yaml"
        write_yaml(
            path,
            {
                "schema_version": 1,
                "kind": "agent_context_request",
                "lock": self.lock_ref,
                "inventory": inventory or self.inventory(),
                "role": write_yaml(self.tmp / "control/role.yaml", role or self.role()),
                "model_profiles": ref(MODELS),
                "workspace": str(self.workspace),
                "task": {"id": "task.1", "statement": task},
                "native_sources": sources
                if sources is not None
                else [
                    {
                        "id": "COMP_REQ_1",
                        "path": "docs/req.rst",
                        "sha256": digest(self.workspace / "docs/req.rst"),
                    }
                ],
                "assumptions": ["Safety classification is not approved."],
                "observations": observations or {"include_text": False, "bindings": []},
                "protected_roots": self.protected,
            },
        )
        return path

    def bundle(self, **kwargs: Any) -> tuple[Path, dict[str, Any]]:
        from score_sw_fabric.agents.context import build_context

        status, record, _, _ = build_context(self.context(**kwargs))
        assert status == 0
        path = self.tmp / "control/bundle.json"
        write_json(path, record)
        return path, record

    def note(self, text: str = "hint") -> None:
        from score_sw_fabric.agents.discover import launch_argv, launch_environment
        from score_sw_fabric.agents.mcp import McpSession, call_tool, initialize

        server = next(item for item in self.lock["servers"] if item["id"] == "fake")
        home = self.tmp / "home"
        home.mkdir(exist_ok=True)
        with McpSession(
            launch_argv(server),
            cwd=self.workspace,
            environment=launch_environment(server, self.copy, home),
            line_bytes=4096,
        ) as session:
            initialize(session, "2024-11-05", 5)
            call_tool(session, "note", {"text": text}, 5, 4096)

    def result(self, bundle: dict[str, Any], **changes: Any) -> dict[str, Any]:
        result = {
            "schema_version": 1,
            "kind": "agent_result",
            "role_id": bundle["role"]["id"],
            "context_digest": bundle["digest"],
            "changed_paths": ["src/component.cpp"],
            "native_ids_affected": ["COMP_REQ_1"],
            "evidence_refs": [{"kind": "test", "ref": "tests/test_component.cpp"}],
            "unresolved_assumptions": [],
            "proposed_next_action": "Run the trusted unit-test runner.",
            "self_reported_checks": [{"name": "unit tests", "result": "pass"}],
        }
        result.update(changes)
        return result

    def check(self, bundle_path: Path, result: Any) -> Path:
        path = self.tmp / "control/check.yaml"
        result_path = self.tmp / "control/result.json"
        result_path.write_text(result if isinstance(result, str) else json.dumps(result))
        write_yaml(
            path,
            {
                "schema_version": 1,
                "kind": "agent_check_request",
                "lock": self.lock_ref,
                "bundle": ref(bundle_path),
                "result": ref(result_path),
                "protected_roots": self.protected,
            },
        )
        return path


def admit_request(
    tmp: Path,
    *,
    call: dict[str, Any] | None = None,
    entries: list[dict[str, Any]] | None = None,
    role: dict[str, Any] | None = None,
    profiles: dict[str, Any] | None = None,
    pages: list[Path] | None = None,
) -> Path:
    role_value = role or yaml.safe_load(DEVELOPER.read_text())
    selected_pages = pages or [
        CATALOGUE / "models-offset-0.json",
        CATALOGUE / "models-offset-100.json",
    ]
    path = tmp / "admit.yaml"
    write_yaml(
        path,
        {
            "schema_version": 1,
            "kind": "agent_admit_request",
            "lock": ref(REPO_LOCK),
            "role": write_yaml(tmp / "role.yaml", role_value),
            "model_profiles": write_yaml(tmp / "models.yaml", profiles)
            if profiles is not None
            else ref(MODELS),
            "catalogue": {
                "runtime_commit": RUNTIME_COMMIT,
                "executable_sha256": EXECUTABLE,
                "pages": [ref(item) for item in selected_pages],
            },
            "ledger": write_yaml(
                tmp / "ledger.yaml",
                {
                    "schema_version": 1,
                    "kind": "agent_budget_ledger",
                    "role_id": role_value["id"],
                    "entries": entries or [],
                },
            ),
            "call": call
            or {
                "call_id": "call.new",
                "attempt": "initial",
                "profile": role_value["model_profile"],
                "estimated_input_tokens": 100_000,
            },
            "protected_roots": [str(ROOT)],
        },
    )
    return path


def entry(call_id: str, attempt: str = "initial", **usage: Any) -> dict[str, Any]:
    known = {"input_tokens": 1000, "output_tokens": 1000, "cost_microusd": 1000, "wall_seconds": 10}
    known.update(usage)
    origin = "unknown" if all(value is None for value in known.values()) else "runtime_observation"
    return {
        "call_id": call_id,
        "attempt": attempt,
        "profile": "model.routine.deepseek-v4-flash",
        "usage_origin": origin,
        **known,
    }
