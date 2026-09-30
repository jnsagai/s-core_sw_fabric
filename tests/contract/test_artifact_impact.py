from __future__ import annotations

import copy

from score_sw_fabric.artifacts.impact import analyze_impact


def test_reverse_dependencies_and_new_unlinked_are_conservative() -> None:
    before = {"digest": "a", "wrappers": [], "needs": [], "relations": []}
    after = copy.deepcopy(before)
    after["digest"] = "b"
    after["needs"] = [{"key": "REQ", "fingerprint": "new", "origins": []}]
    result = analyze_impact(before, after, {"impact_rules": [{"id": "conservative"}]})
    assert result["newly_unlinked"] == ["REQ"]
    assert result["state"] == "blocked"
    assert result["required_reviews"] == ["REQ"]
