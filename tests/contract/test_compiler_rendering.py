from __future__ import annotations

from score_sw_fabric.compiler.ir import build_ir
from score_sw_fabric.compiler.mapping import project_mapping
from score_sw_fabric.compiler.render import render_native
from tests.compiler_support import compiler_profile, mapping, plan


def test_renderer_is_canonical_explicit_and_closed() -> None:
    selected = mapping()
    graph = build_ir(
        project_mapping(plan(), selected, compiler_profile()), selected, compiler_profile()
    )
    first = render_native(graph, [])
    second = render_native(graph, [])
    assert first == second
    dot = first["workflow.fabro"]
    assert 'type="start"' in dot
    assert 'type="exit"' in dot
    assert 'type="command"' in dot
    assert 'on_failure="route"' in dot
    assert "allow_partial=false" in dot
    assert "random" not in dot
    assert first["workflow.toml"] == '_version = 1\n\n[workflow]\ngraph = "workflow.fabro"\n'
