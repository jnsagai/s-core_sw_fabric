"""Execution instructions are private operator inputs; estimates never become bills."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from score_sw_fabric.optimization.common import OptimizationError, record


def instruction(tmp_path: Path) -> tuple[Path, str, dict]:
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    decision = record(
        "token_governor_decision",
        decision="admissible",
        call_authorized=False,
        limits={"input_tokens": 20000, "output_tokens": 2000, "calls": 3, "context_tokens": 24000},
    )
    governor = private / "governor.json"
    governor.write_text(json.dumps(decision))
    governor.chmod(0o600)
    binding = private / "run.json"
    binding.write_text(json.dumps({"run_id": "native-run", "stopped": False}))
    binding.chmod(0o600)
    artifacts = {
        "context": record("qualification_context", task="B1"),
        "role": record("qualification_role", role="draft"),
        "skills": record("qualification_skills", skills=[]),
    }
    files = {str(governor): hashlib.sha256(governor.read_bytes()).hexdigest()}
    bindings = {"governor": decision["digest"]}
    for name, artifact in artifacts.items():
        file = private / (name + ".json")
        file.write_text(json.dumps(artifact))
        file.chmod(0o600)
        files[str(file)] = hashlib.sha256(file.read_bytes()).hexdigest()
        bindings[name] = artifact["digest"]
    value = {
        "kind": "qualification_instruction",
        "scope": "qualification_only",
        "owner_instructions": ["go", "deepseek flash only"],
        "workspace": str(workspace),
        "run_binding": str(binding),
        "stage": "draft",
        "task": "B1",
        "bindings": bindings,
        "files": files,
        "provider": "deepseek",
        "models": ["deepseek-flash", "deepseek-v4-flash"],
        "limits": {
            "requests": 10,
            "request_bytes": 24000,
            "output_tokens": 2000,
            "cost_microusd": 100000,
        },
        "price_bounds": {"input_microusd_per_token": 0.3, "output_microusd_per_token": 1.2},
        "tasks": [
            {"marker": "qualification:B1", "prompt": "qualification:B1 do task", "max_requests": 1}
        ],
    }
    path = private / "instruction.json"
    path.write_text(json.dumps(value))
    path.chmod(0o600)
    return path, hashlib.sha256(path.read_bytes()).hexdigest(), decision


def test_private_activation_requires_pins_run_and_current_files(tmp_path: Path) -> None:
    from score_sw_fabric.optimization.activation import verify_instruction
    from score_sw_fabric.optimization.runtime_boundary import guard

    path, pin, decision = instruction(tmp_path)
    context = {"event": "stage_start", "node_id": "draft", "run_id": "native-run"}
    assert (
        guard(context, decision, stage="draft", instruction=path, instruction_sha256=pin)[
            "decision"
        ]
        == "allow"
    )
    with pytest.raises(OptimizationError, match="INSTRUCTION_DIGEST"):
        verify_instruction(path, "0" * 64)
    with pytest.raises(OptimizationError, match="RUN_BINDING"):
        guard(
            dict(context, run_id="other"),
            decision,
            stage="draft",
            instruction=path,
            instruction_sha256=pin,
        )
    (path.parent / "governor.json").write_text("changed")
    with pytest.raises(OptimizationError, match="ACTIVATION_FILE_DRIFT"):
        verify_instruction(path, pin)


def test_instruction_public_file_or_workspace_or_symlink_is_refused(tmp_path: Path) -> None:
    from score_sw_fabric.optimization.activation import verify_instruction

    path, pin, _ = instruction(tmp_path)
    path.chmod(0o644)
    with pytest.raises(OptimizationError, match="PRIVATE_INSTRUCTION_REQUIRED"):
        verify_instruction(path, pin)
    path.chmod(0o600)
    link = path.parent / "link.json"
    link.symlink_to(path)
    with pytest.raises(OptimizationError, match="PRIVATE_INSTRUCTION_REQUIRED"):
        verify_instruction(link, pin)
    value = json.loads(path.read_bytes())
    value["workspace"] = str(path.parent)
    path.write_text(json.dumps(value))
    with pytest.raises(OptimizationError, match="INSTRUCTION_IN_WORKSPACE"):
        verify_instruction(path, hashlib.sha256(path.read_bytes()).hexdigest())


def request(**changes) -> bytes:
    value = {
        "model": "deepseek-flash",
        "max_tokens": 200,
        "messages": [{"role": "user", "content": "qualification:B1 do task"}],
    }
    value.update(changes)
    return json.dumps(value).encode()


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"model": "deepseek-pro"}, "FLASH_ONLY"),
        ({"max_tokens": 2001}, "OUTPUT_LIMIT"),
        ({"max_tokens": True}, "OUTPUT_LIMIT"),
        ({"messages": [{"role": "user", "content": "x" * 24000}]}, "CONTEXT_LIMIT"),
        ({"messages": [{"role": "user", "content": "unbound task"}]}, "TASK_BINDING"),
    ],
)
def test_meter_refusals_persist_across_restart(tmp_path: Path, changes: dict, reason: str) -> None:
    from score_sw_fabric.optimization.provider_boundary import RequestMeter

    path, pin, _ = instruction(tmp_path)
    state = path.parent / "meter.json"
    with pytest.raises(OptimizationError, match=reason):
        RequestMeter(path, pin, state).reserve(request(**changes))
    with pytest.raises(OptimizationError, match="QUALIFICATION_STOPPED"):
        RequestMeter(path, pin, state).reserve(request())


def test_meter_reserves_before_send_and_unknown_usage_stops(tmp_path: Path) -> None:
    from score_sw_fabric.optimization.provider_boundary import RequestMeter

    path, pin, _ = instruction(tmp_path)
    state = path.parent / "meter.json"
    meter = RequestMeter(path, pin, state)
    ticket = meter.reserve(request())
    assert json.loads(state.read_bytes())["requests"] == 1
    assert json.loads(state.read_bytes())["reserved_microusd"] > 0
    with pytest.raises(OptimizationError, match="USAGE_UNKNOWN"):
        meter.finish(ticket, {})
    with pytest.raises(OptimizationError, match="QUALIFICATION_STOPPED"):
        RequestMeter(path, pin, state).reserve(request())


def test_meter_keeps_usage_and_derived_cost_separate_and_denies_repeat(tmp_path: Path) -> None:
    from score_sw_fabric.optimization.provider_boundary import RequestMeter

    path, pin, _ = instruction(tmp_path)
    meter = RequestMeter(path, pin, path.parent / "meter.json")
    ticket = meter.reserve(request())
    result = meter.finish(
        ticket,
        {
            "prompt_tokens": 30,
            "completion_tokens": 20,
            "prompt_cache_hit_tokens": 10,
            "prompt_cache_miss_tokens": 20,
        },
    )
    assert result["actual_cost_usd"] is None
    assert result["reasoning_tokens"] is None
    assert result["cost_upper_bound_microusd"] == 33
    with pytest.raises(OptimizationError, match="TASK_CALL_LIMIT"):
        meter.reserve(request())


def test_inflight_restart_and_instruction_substitution_stop(tmp_path: Path) -> None:
    from score_sw_fabric.optimization.provider_boundary import RequestMeter

    path, pin, _ = instruction(tmp_path)
    state = path.parent / "meter.json"
    RequestMeter(path, pin, state).reserve(request())
    with pytest.raises(OptimizationError, match="INFLIGHT_REQUEST"):
        RequestMeter(path, pin, state).reserve(request())
    path.write_text(path.read_text() + " ")
    with pytest.raises(OptimizationError):
        RequestMeter(path, hashlib.sha256(path.read_bytes()).hexdigest(), state).reserve(request())


def test_pinned_petri_hook_identity_requires_exact_private_native_cwd(tmp_path: Path) -> None:
    from score_sw_fabric.optimization.runtime_boundary import guard

    path, pin, decision = instruction(tmp_path)
    cwd = tmp_path / "storage/scratch/20261003-native-run/petri/scopes/invocation-0-scope-0/work"
    cwd.mkdir(parents=True)
    binding = path.parent / "run.json"
    value = json.loads(binding.read_text())
    value["native_context"] = {
        "run_id": "petri",
        "cwd": str(cwd),
        "server_root": str(tmp_path),
        "source_commit": "1b4fb15281ebb724426f9e480dce48d0100ff79b",
    }
    binding.write_text(json.dumps(value))
    context = {"event": "stage_start", "node_id": "draft", "run_id": "petri", "cwd": str(cwd)}
    assert (
        guard(context, decision, stage="draft", instruction=path, instruction_sha256=pin)[
            "decision"
        ]
        == "allow"
    )
    tool = {
        "event": "pre_tool_use",
        "run_id": "petri",
        "node_id": "draft",
        "tool_name": "mcp__score_bounded__evidence_summary",
        "tool_input": {"path": "raw.sarif"},
    }
    assert (
        guard(
            tool, decision, stage="draft", instruction=path, instruction_sha256=pin, host_cwd=cwd
        )["decision"]
        == "allow"
    )
    with pytest.raises(OptimizationError, match="RUN_BINDING"):
        guard(
            tool,
            decision,
            stage="draft",
            instruction=path,
            instruction_sha256=pin,
            host_cwd=tmp_path,
        )
    for change in ({"cwd": "/workspace"}, {"run_id": "native-run"}, {"cwd": str(cwd) + "/.."}):
        with pytest.raises(OptimizationError, match="RUN_BINDING"):
            guard(
                dict(context, **change),
                decision,
                stage="draft",
                instruction=path,
                instruction_sha256=pin,
            )


@pytest.mark.parametrize(
    "field,ceiling,reason",
    [
        ("requests", 1, "CALL_LIMIT"),
        ("cost_microusd", 1, "COST_LIMIT"),
    ],
)
def test_meter_global_call_and_cost_caps(
    tmp_path: Path, field: str, ceiling: int, reason: str
) -> None:
    from score_sw_fabric.optimization.provider_boundary import RequestMeter

    path, _, _ = instruction(tmp_path)
    value = json.loads(path.read_text())
    value["limits"][field] = ceiling
    value["tasks"][0]["max_requests"] = 2
    path.write_text(json.dumps(value))
    pin = hashlib.sha256(path.read_bytes()).hexdigest()
    meter = RequestMeter(path, pin, path.parent / "meter.json")
    if field == "requests":
        ticket = meter.reserve(request())
        meter.finish(
            ticket,
            {
                "prompt_tokens": 30,
                "completion_tokens": 20,
                "prompt_cache_hit_tokens": 0,
                "prompt_cache_miss_tokens": 30,
            },
        )
    with pytest.raises(OptimizationError, match=reason):
        meter.reserve(request())


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"prompt_cache_miss_tokens": 29}, "USAGE_INCONSISTENT"),
        ({"completion_tokens": 201}, "USAGE_EXCEEDS_BOUND"),
        ({"prompt_tokens": True}, "USAGE_UNKNOWN"),
    ],
)
def test_meter_bad_usage_stops(tmp_path: Path, changes: dict, reason: str) -> None:
    from score_sw_fabric.optimization.provider_boundary import RequestMeter

    path, pin, _ = instruction(tmp_path)
    meter = RequestMeter(path, pin, path.parent / "meter.json")
    ticket = meter.reserve(request())
    usage = {
        "prompt_tokens": 30,
        "completion_tokens": 20,
        "prompt_cache_hit_tokens": 0,
        "prompt_cache_miss_tokens": 30,
    }
    usage.update(changes)
    with pytest.raises(OptimizationError, match=reason):
        meter.finish(ticket, usage)
    assert json.loads(meter.state.read_bytes())["stopped"] == reason


def test_actual_http_boundary_sends_only_reserved_flash_and_never_records_credentials(
    tmp_path: Path, monkeypatch
) -> None:
    import io
    import threading
    import urllib.error
    import urllib.request

    import score_sw_fabric.optimization.provider_boundary as boundary

    path, pin, _ = instruction(tmp_path)
    calls = []

    class Response(io.BytesIO):
        status = 200
        headers = {"Content-Type": "application/json"}

    class Opener:
        def open(self, value, timeout):
            calls.append(value)
            assert json.loads((path.parent / "meter.json").read_bytes())["requests"] == 1
            return Response(
                json.dumps(
                    {
                        "usage": {
                            "prompt_tokens": 30,
                            "completion_tokens": 20,
                            "prompt_cache_hit_tokens": 0,
                            "prompt_cache_miss_tokens": 30,
                        }
                    }
                ).encode()
            )

    monkeypatch.setattr(boundary, "build_opener", lambda *args: Opener())
    server = boundary.boundary_server(
        boundary.RequestMeter(path, pin, path.parent / "meter.json"), 0, "n" * 32, tmp_path
    )
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/" + "n" * 32 + "/chat/completions"
        req = urllib.request.Request(url, request(), {"Authorization": "Bearer test-private-key"})
        with urllib.request.urlopen(req, timeout=5) as reply:
            assert reply.status == 200
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(req, timeout=5)
        assert len(calls) == 1
        assert calls[0].full_url == "https://api.deepseek.com/chat/completions"
        assert "test-private-key" not in (tmp_path / "request-00.json").read_text()
        assert "test-private-key" not in (path.parent / "meter.json").read_text()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def test_sse_usage_is_observed_and_missing_usage_stays_empty() -> None:
    from score_sw_fabric.optimization.provider_boundary import reported_usage

    assert reported_usage(b'data: {"choices":[]}\n\ndata: [DONE]\n\n', stream=True) == {}
    assert reported_usage(b'data: {"usage":{"prompt_tokens":30}}\n\n', stream=True) == {
        "prompt_tokens": 30
    }


def test_meter_retains_explicit_reasoning_tokens(tmp_path: Path) -> None:
    from score_sw_fabric.optimization.provider_boundary import RequestMeter

    path, pin, _ = instruction(tmp_path)
    meter = RequestMeter(path, pin, path.parent / "meter.json")
    ticket = meter.reserve(request())
    result = meter.finish(
        ticket,
        {
            "prompt_tokens": 30,
            "completion_tokens": 20,
            "prompt_cache_hit_tokens": 0,
            "prompt_cache_miss_tokens": 30,
            "completion_tokens_details": {"reasoning_tokens": 4},
        },
    )
    assert result["reasoning_tokens"] == 4
    assert result["usage"]["completion_tokens"] == 20


def test_native_tool_projection_preserves_messages_and_selected_declarations() -> None:
    from score_sw_fabric.optimization.provider_boundary import project_request

    root = Path(__file__).resolve().parents[2]
    capture = (
        root
        / "specs/011-change-impact-and-freshness/evidence/qualification/native-request-capture.json"
    )
    raw = capture.read_bytes()
    original = json.loads(raw)
    config = {"tool_projection": {"allowed_tools": ["evidence_summary"]}}
    projected = json.loads(project_request(raw, config))
    assert projected["messages"] == original["messages"]
    assert projected["tools"] == [
        t
        for t in original["tools"]
        if t["function"]["name"] == "mcp__score_bounded__evidence_summary"
    ]
    assert {k: v for k, v in projected.items() if k != "tools"} == {
        k: v for k, v in original.items() if k != "tools"
    }
    assert len(project_request(raw, config)) < len(raw)
    no_tools = json.loads(project_request(raw, {"tool_projection": {"allowed_tools": []}}))
    assert no_tools["messages"] == original["messages"]
    assert "tools" not in no_tools and "tool_choice" not in no_tools


@pytest.mark.parametrize(
    "choice",
    [
        "required",
        {"type": "function", "function": {"name": "shell"}},
        {"type": "function", "function": "shell"},
    ],
)
def test_projection_refuses_unavailable_explicit_choices(choice) -> None:
    from score_sw_fabric.optimization.provider_boundary import project_request

    with pytest.raises(OptimizationError, match="TOOL_CHOICE"):
        project_request(request(tool_choice=choice), {"tool_projection": {"allowed_tools": []}})


def test_projection_cannot_hide_oversized_native_input_or_bypass_selection(tmp_path: Path) -> None:
    from score_sw_fabric.optimization.provider_boundary import RequestMeter
    from score_sw_fabric.optimization.runtime_boundary import guard

    path, _, decision = instruction(tmp_path)
    value = json.loads(path.read_text())
    value["tool_projection"] = {"allowed_tools": []}
    path.write_text(json.dumps(value))
    pin = hashlib.sha256(path.read_bytes()).hexdigest()
    meter = RequestMeter(path, pin, path.parent / "meter.json")
    raw = request(
        tools=[{"type": "function", "function": {"name": "shell", "description": "x" * 24000}}]
    )
    with pytest.raises(OptimizationError, match="CONTEXT_LIMIT"):
        meter.reserve(raw)
    with pytest.raises(OptimizationError, match="TOOL_SELECTION"):
        guard(
            {
                "event": "pre_tool_use",
                "node_id": "draft",
                "run_id": "native-run",
                "tool_name": "mcp__score_bounded__evidence_summary",
                "tool_input": {"path": "raw.sarif"},
            },
            decision,
            stage="draft",
            instruction=path,
            instruction_sha256=pin,
        )


@pytest.mark.parametrize(
    "name,limit,reason",
    [
        ("input_tokens", 1, "OPERATIONAL_INPUT_LIMIT"),
        ("output_tokens", 199, "OUTPUT_LIMIT"),
        ("calls", 1, "TASK_CALL_LIMIT"),
    ],
)
def test_meter_narrows_private_experiment_to_pinned_governor(
    tmp_path: Path, name: str, limit: int, reason: str
) -> None:
    from score_sw_fabric.optimization.provider_boundary import RequestMeter

    path, _, decision = instruction(tmp_path)
    limits = dict(decision["limits"], **{name: limit})
    changed = record(
        "token_governor_decision", decision="admissible", call_authorized=False, limits=limits
    )
    governor = path.parent / "governor.json"
    governor.write_text(json.dumps(changed))
    value = json.loads(path.read_text())
    value["files"][str(governor)] = hashlib.sha256(governor.read_bytes()).hexdigest()
    value["bindings"]["governor"] = changed["digest"]
    value["tasks"][0]["max_requests"] = 2
    path.write_text(json.dumps(value))
    meter = RequestMeter(
        path, hashlib.sha256(path.read_bytes()).hexdigest(), path.parent / "meter.json"
    )
    if name == "calls":
        ticket = meter.reserve(request())
        meter.finish(
            ticket,
            {
                "prompt_tokens": 30,
                "completion_tokens": 20,
                "prompt_cache_hit_tokens": 0,
                "prompt_cache_miss_tokens": 30,
            },
        )
    with pytest.raises(OptimizationError, match=reason):
        meter.reserve(request())
