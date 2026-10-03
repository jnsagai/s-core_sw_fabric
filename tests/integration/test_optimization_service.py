"""Real subprocess stdio service and host hook; no model calls."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from score_sw_fabric.optimization.server import BoundedService, serve


def test_actual_service_subprocess_contains_evidence(tmp_path: Path) -> None:
    (tmp_path / "raw.sarif").write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "results": [
                            {
                                "ruleId": "native-1",
                                "message": {"text": "x" * 1_100_000},
                                "locations": [],
                            }
                        ]
                    }
                ]
            }
        )
    )
    requests = [
        {"id": 1, "method": "initialize"},
        {"id": 2, "method": "tools/list"},
        {
            "id": 3,
            "method": "tools/call",
            "params": {"name": "finding_list", "arguments": {"path": "raw.sarif"}},
        },
        {
            "id": 4,
            "method": "tools/call",
            "params": {"name": "read_file", "arguments": {"path": "raw.sarif"}},
        },
    ]
    code = (
        "from pathlib import Path; "
        "from score_sw_fabric.optimization.server import BoundedService,serve; "
        "import sys; serve(BoundedService(Path(sys.argv[1]),Path(sys.argv[2])))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path), str(tmp_path / "state.json")],
        input="\n".join(json.dumps(i) for i in requests) + "\n",
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    replies = [json.loads(line) for line in completed.stdout.splitlines()]
    summary = json.loads(replies[2]["result"]["content"][0]["text"])
    assert summary["findings"][0]["rule"] == "native-1"
    assert len(json.dumps(replies[2]).encode()) < 5000
    assert len(completed.stdout.encode()) < 12000
    assert replies[3]["error"]["message"] == "BOUNDED_TOOL_REQUIRED"
    assert "read_file" not in {i["name"] for i in replies[1]["result"]["tools"]}


def test_restart_retains_stage_context_usage(tmp_path: Path) -> None:
    (tmp_path / "raw.sarif").write_text('{"runs":[{"results":[]}]}')
    BoundedService(tmp_path, tmp_path / "state.json").call(
        "evidence_summary", {"path": "raw.sarif"}
    )
    import io

    output = io.StringIO()
    serve(
        BoundedService(tmp_path, tmp_path / "state.json"),
        io.StringIO(
            json.dumps(
                {
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": "evidence_summary", "arguments": {"path": "raw.sarif"}},
                }
            )
            + "\n"
        ),
        output,
    )
    assert json.loads(output.getvalue())["error"]["message"] == "REPEATED_QUERY"


def test_native_command_hook_refuses_unguarded_call(tmp_path: Path) -> None:
    from score_sw_fabric.optimization.common import record

    decision = record("token_governor_decision", decision="admissible", call_authorized=False)
    path = tmp_path / "decision.json"
    path.write_text(json.dumps(decision))
    context = {
        "event": "pre_tool_use",
        "node_id": "implementation",
        "tool_name": "grep",
        "tool_input": {"pattern": ".", "path": "/workspace/result.sarif"},
    }
    for name in ("grep", None, 7, []):
        context["tool_name"] = name
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "score_sw_fabric.optimization.cli",
                "guard",
                "--decision",
                str(path),
                "--stage",
                "implementation",
            ],
            input=json.dumps(context),
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        assert completed.returncode == 2
        assert json.loads(completed.stdout)["decision"] == "block"
        assert json.loads(completed.stdout)["reason"] == "BOUNDED_TOOL_REQUIRED"


def test_generic_someip_hook_refuses_raw_reports_and_broad_grep() -> None:
    root = Path(__file__).resolve().parents[2]
    for name, arguments in [
        ("read_file", {"file_path": "/workspace/result.sarif"}),
        ("grep", {"pattern": ".", "path": "/workspace"}),
    ]:
        context = {"event": "pre_tool_use", "tool_name": name, "tool_input": arguments}
        result = subprocess.run(
            [sys.executable, str(root / "docs/handoff/someip-84/factory/guard_agent_tools.py")],
            input=json.dumps(context),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert result.returncode == 2
        assert json.loads(result.stdout)["decision"] == "block"


def test_service_failure_survives_restart_and_alternate_query(tmp_path: Path) -> None:
    import pytest

    from score_sw_fabric.optimization.common import OptimizationError

    service = BoundedService(tmp_path, tmp_path / "state.json")
    with pytest.raises(OptimizationError, match="BOUNDED_TOOL_REQUIRED"):
        service.call("read_file", {"path": "raw.sarif"})
    with pytest.raises(OptimizationError, match="STAGE_STOPPED"):
        BoundedService(tmp_path, tmp_path / "state.json").call(
            "evidence_summary", {"path": "other.sarif"}
        )


def test_mutating_governor_boolean_never_creates_live_authority() -> None:
    import pytest

    from score_sw_fabric.optimization.common import OptimizationError, record
    from score_sw_fabric.optimization.runtime_boundary import guard

    forged = record("token_governor_decision", decision="admissible", call_authorized=True)
    with pytest.raises(OptimizationError, match="UNTRUSTED_EXECUTION_GRANT"):
        guard({"event": "stage_start", "node_id": "stage"}, forged, stage="stage")


def test_stage_evidence_digest_binding_survives_restart(tmp_path: Path) -> None:
    import pytest

    from score_sw_fabric.optimization.common import OptimizationError

    (tmp_path / "raw.sarif").write_text('{"runs":[{"results":[]}]}')
    BoundedService(tmp_path, tmp_path / "state.json").call(
        "evidence_summary", {"path": "raw.sarif"}
    )
    (tmp_path / "raw.sarif").write_text('{"runs":[{"results":[{"ruleId":"changed"}]}]}')
    with pytest.raises(OptimizationError, match="EVIDENCE_DRIFT"):
        BoundedService(tmp_path, tmp_path / "state.json").call(
            "finding_list", {"path": "raw.sarif"}
        )


def test_service_stops_on_managed_volume_disconnection(tmp_path: Path, monkeypatch) -> None:
    import pytest

    import score_sw_fabric.storage as storage
    from score_sw_fabric.optimization.common import OptimizationError

    (tmp_path / "storage-selection.json").write_text('{"fixture":"bound-volume"}')
    service = BoundedService(tmp_path, tmp_path / "state.json")
    monkeypatch.setattr(
        storage, "validate_run_root", lambda root: (_ for _ in ()).throw(OSError("disconnected"))
    )
    with pytest.raises(OptimizationError, match="STORAGE_DISCONNECTED"):
        service.call("evidence_summary", {"path": "raw.sarif"})
    assert not (tmp_path / "state.json").exists()


def test_source_excerpt_is_exact_manifest_bound_and_stops_on_drift(tmp_path: Path) -> None:
    import hashlib

    import pytest

    from score_sw_fabric.optimization.common import OptimizationError

    source = tmp_path / "a.cpp"
    source.write_text("first\nsecond\nthird\n")
    sources = {"a.cpp": hashlib.sha256(source.read_bytes()).hexdigest()}
    service = BoundedService(tmp_path, tmp_path / "state.json", sources=sources)
    excerpt = service.call("get_source_excerpt", {"path": "a.cpp", "start": 2, "end": 2})
    assert excerpt["text"] == "second"
    assert excerpt["raw"]["sha256"] == sources["a.cpp"]
    source.write_text("changed\n")
    with pytest.raises(OptimizationError, match="EVIDENCE_DRIFT"):
        service.call("get_source_excerpt", {"path": "a.cpp", "start": 1, "end": 1})
    with pytest.raises(OptimizationError, match="STAGE_STOPPED"):
        BoundedService(tmp_path, tmp_path / "state.json", sources=sources).call(
            "get_source_excerpt", {"path": "other.cpp", "start": 1, "end": 1}
        )


def test_optimized_projection_and_candidate_config_pass_pinned_native_validation(tmp_path) -> None:
    import os

    import pytest

    from score_sw_fabric.compiler.ir import build_ir
    from score_sw_fabric.compiler.mapping import project_mapping
    from score_sw_fabric.compiler.optimization import narrow_projection
    from score_sw_fabric.compiler.reader import load_compiler_inputs, semantic_digest
    from score_sw_fabric.compiler.render import render_native
    from score_sw_fabric.compiler.validator import validate_native
    from score_sw_fabric.optimization.common import record
    from score_sw_fabric.optimization.runtime_boundary import runtime_config
    from score_sw_fabric.optimization.token_governor import govern
    from score_sw_fabric.optimization.workflow_modes import mode_plan
    from tests.compiler_support import action, prepare_case

    if not os.environ.get("SCORE_FABRO_BIN"):
        pytest.fail("SCORE_FABRO_BIN is required for optimization native conformance")
    request, _ = prepare_case(tmp_path, "shared-parallel-review")
    inputs = load_compiler_inputs(request)
    inputs.mapping["rules"][0]["actions"][0] = action(
        "prepare", ["obligation-a"], action_type="agent"
    )
    inputs.mapping["digest"] = semantic_digest(inputs.mapping)
    projected = project_mapping(inputs.plan, inputs.mapping, inputs.compiler_profile)
    context = record(
        "optimized_context_bundle",
        manifest_digest="0" * 64,
        l0={"task": "native-test", "constraints": ["retain human review"]},
        l1={"a.cpp": "bounded source"},
        skills=[],
    )
    admission = record(
        "agent_admission",
        decision="admissible",
        call_authorized=False,
        remaining={"input_tokens": 1000000, "output_tokens": 100000, "calls": 6},
        profile={"id": "fixture-only", "max_output_tokens": 32000},
        provider_configured=True,
        offering={"id": "fixture-only"},
    )
    governor = govern("S1", admission, 1000, [], manifest_digest=context["manifest_digest"])
    bindings = {
        action["ref"]: {"context": context, "governor": governor}
        for action in projected["actions"]
        if action["type"] in {"agent", "prompt"}
    }
    checks = [
        a["ref"] for a in projected["actions"] if a["type"] in {"command", "deterministic_check"}
    ]
    humans = [a["ref"] for a in projected["actions"] if a["type"] == "human"]
    narrowed, receipt = narrow_projection(projected, bindings, mode_plan("delta", checks, humans))
    assert receipt["agent_bindings"]
    graph = build_ir(narrowed, inputs.mapping, inputs.compiler_profile)
    files = render_native(graph, inputs.mapping["support_files"])
    files["workflow.toml"] += runtime_config(
        Path(sys.executable), tmp_path, tmp_path / "state.json", tmp_path / "governor.json", "test"
    )
    result = validate_native(files, "workflow.toml", inputs.validator_profile)
    assert result["accepted"] is True
    assert receipt["execution_authorized"] is False
