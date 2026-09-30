"""Namespace ambiguity, owner binding and link direction are explicit."""

import pytest

from score_sw_fabric.catalog.relations import relations
from score_sw_fabric.process_source.reader import IntegrityError


def entity(source: str, native_id: str, links: list[str] | None = None) -> dict:
    return {
        "source_id": source,
        "native_id": native_id,
        "native_version": 1,
        "type": "tool_req",
        "normalized": {"links": links or [], "links_back": []},
        "source_ref": {"pointer": f"/{source}/{native_id}"},
    }


def test_ambiguous_cross_namespace_target_requires_owner() -> None:
    origin = entity("origin", "tool_req__origin", ["tool_req__shared"])
    a = entity("a", "tool_req__shared")
    b = entity("b", "tool_req__shared")
    context = (origin, {"links": {"field_type": "links"}}, {})
    rules = {"tool_req": {"optional_links": {"links": "ANY"}}}
    with pytest.raises(IntegrityError) as error:
        relations([origin, a, b], [context], rules)
    assert error.value.code == "AMBIGUOUS_RELATION"
    resolved = relations(
        [origin, a, b],
        [(origin, {"links": {"field_type": "links"}}, {"tool_req__shared": "b"})],
        rules,
    )
    assert resolved[0]["target_source_id"] == "b"
    assert resolved[0]["direction"] == "forward"


def test_backlink_not_recast_as_forward_dependency() -> None:
    origin = entity("a", "tool_req__origin")
    target = entity("a", "tool_req__target")
    origin["normalized"]["links_back"] = ["tool_req__target"]
    resolved = relations(
        [origin, target],
        [(origin, {"links_back": {"field_type": "backlinks"}}, {})],
        {"tool_req": {}},
    )
    assert resolved[0]["direction"] == "backlink"


def test_wrong_declared_target_type_fails() -> None:
    origin = entity("a", "tool_req__origin", ["tool_req__target"])
    target = entity("a", "tool_req__target")
    with pytest.raises(IntegrityError) as error:
        relations(
            [origin, target],
            [(origin, {"links": {"field_type": "links"}}, {})],
            {"tool_req": {"mandatory_links": {"links": "workflow"}}},
        )
    assert error.value.code == "TARGET_TYPE"
