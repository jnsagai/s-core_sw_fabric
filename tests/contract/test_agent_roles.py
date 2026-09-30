"""007 role profiles: forbidden grants and derived runtime configuration (AC007-08/10)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from score_sw_fabric.agents.lock import load_lock
from score_sw_fabric.agents.roles import (
    covers,
    granted_tools,
    role_prompt,
    runtime_agent_config,
    validate_role,
)
from score_sw_fabric.process_source.reader import InputError
from tests.agent_support import CRITIC, DEVELOPER, REPO_LOCK

LOCK = load_lock(REPO_LOCK.read_bytes())


def developer(**changes: Any) -> dict[str, Any]:
    role: dict[str, Any] = yaml.safe_load(DEVELOPER.read_text())
    role.update(changes)
    return role


def test_repository_draft_roles_validate() -> None:
    dev = validate_role(developer(), LOCK)
    critic = validate_role(yaml.safe_load(CRITIC.read_text()), LOCK)
    assert dev["status"] == critic["status"] == "draft_owner_review_pending"
    assert critic["write_scope"] == [] and critic["runtime"]["permissions"] == "read-only"
    tools = granted_tools(dev, LOCK)
    assert {item["classification"] for item in tools} == {"context_read", "local_observation_write"}
    assert "mcp__context_discipline__record_decision" in {item["qualified_name"] for item in tools}


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"credentials": ["approval_signer"]}, "CREDENTIAL_FORBIDDEN"),
        ({"credentials": ["evidence_collector_key"]}, "CREDENTIAL_FORBIDDEN"),
        ({"credentials": ["question_answer_route"]}, "CREDENTIAL_FORBIDDEN"),
        ({"credentials": ["run_resume"]}, "CREDENTIAL_FORBIDDEN"),
        ({"credentials": ["fabro_dev_token"]}, "CREDENTIAL_FORBIDDEN"),
        (
            {"runtime": {"fabro_tools": True, "human_gate": "stop", "permissions": "read-write"}},
            "RUN_TOOLS_FORBIDDEN",
        ),
        (
            {
                "runtime": {
                    "fabro_tools": False,
                    "human_gate": "auto_approve",
                    "permissions": "read-write",
                }
            },
            "HUMAN_GATE",
        ),
        (
            {"runtime": {"fabro_tools": False, "human_gate": "stop", "permissions": "full"}},
            "TOOL_FORBIDDEN",
        ),
        ({"mcp_servers": ["fabro"]}, "RUN_TOOLS_FORBIDDEN"),
        ({"builtin_tools": ["fabro_run_interact"]}, "RUN_TOOLS_FORBIDDEN"),
        ({"builtin_tools": ["shell"]}, "TOOL_FORBIDDEN"),
        ({"builtin_tools": ["web_fetch"]}, "TOOL_FORBIDDEN"),
        ({"builtin_tools": ["spawn_agent"]}, "TOOL_FORBIDDEN"),
        ({"builtin_tools": ["teleport"]}, "TOOL_FORBIDDEN"),
        ({"mcp_servers": ["apm-setup"]}, "SETUP_FORBIDDEN"),
        ({"mcp_servers": ["graphify-codegraph"]}, "SERVER_UNSUPPORTED"),
        ({"write_scope": ["src/**", ".score-local/**"]}, "SERVER_WRITES_OUT_OF_SCOPE"),
        ({"write_scope": [], "mcp_servers": []}, "WRITE_SCOPE_MISSING"),
        ({"write_scope": [".git/**"]}, "PROTECTED_PATH"),
        ({"write_scope": ["**"]}, "PROTECTED_PATH"),
        ({"allowed_inputs": [".git/config"]}, "PROTECTED_PATH"),
        ({"prohibited_decisions": []}, "FIELD_TYPE"),
        ({"retry_limit": 11}, "LIMIT_EXCEEDED"),
        ({"loopback": {"max_correction_visits": -1}}, "LIMIT_EXCEEDED"),
        ({"budget": {"cost_microusd": 1}}, "FIELD_UNKNOWN"),
        ({"role": "approver"}, "FIELD_ENUM"),
        ({"expected_output": {"kind": "free_text", "schema_version": 1}}, "OUTPUT_UNSUPPORTED"),
        ({"extra": True}, "FIELD_UNKNOWN"),
    ],
)
def test_role_refusals_name_the_grant(changes: dict[str, Any], code: str) -> None:
    with pytest.raises(InputError) as error:
        validate_role(developer(**changes), LOCK)
    assert error.value.code == code


def test_scope_cover_is_conservative() -> None:
    assert covers(".score-local/**", ".score-local/**")
    assert covers("a/**", "a/b/**")
    assert covers("score-context/**", "score-context/**")
    assert not covers("score-context/*", "score-context/**")
    assert not covers("src/**", ".score-local/**")


def test_runtime_config_is_candidate_with_run_tools_disabled(tmp_path: Path) -> None:
    role = validate_role(developer(), LOCK)
    text = runtime_agent_config(role, LOCK, tmp_path)
    assert text.startswith("# Candidate only")
    assert "fabro_tools = false" in text
    assert "[run.agent.mcps.context-discipline]" in text
    assert "apm-setup" not in text and "uvx" not in text
    assert str(tmp_path / "packages/context-discipline/src") in text


def test_role_prompt_is_deterministic_and_states_boundaries() -> None:
    role = validate_role(developer(), LOCK)
    args = (
        role,
        {"id": "t", "statement": "Do it."},
        [{"id": "REQ", "path": "docs/a.rst", "sha256": "0" * 64}],
        granted_tools(role, LOCK),
        ["A1"],
        "c" * 40,
    )
    first = role_prompt(*args)
    assert first == role_prompt(*args)
    for text in (
        "Prohibited decisions",
        "Writable paths",
        "cannot approve",
        "assertions",
        "c" * 40,
    ):
        assert text in first
