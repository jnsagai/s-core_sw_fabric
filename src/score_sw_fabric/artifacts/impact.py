"""Conservative native reverse-dependency and declared-rule impact expansion."""

from __future__ import annotations

from collections import deque
from typing import Any

from score_sw_fabric.compiler.reader import semantic_digest


def analyze_impact(
    before: dict[str, Any], after: dict[str, Any], trace_profile: dict[str, Any]
) -> dict[str, Any]:
    before_entities = {
        item["key"]: item for item in [*before.get("wrappers", []), *before.get("needs", [])]
    }
    after_entities = {
        item["key"]: item for item in [*after.get("wrappers", []), *after.get("needs", [])]
    }
    added = sorted(after_entities.keys() - before_entities.keys())
    removed = sorted(before_entities.keys() - after_entities.keys())
    modified = sorted(
        key
        for key in before_entities.keys() & after_entities.keys()
        if before_entities[key].get("fingerprint") != after_entities[key].get("fingerprint")
    )
    direct = sorted(set(added + removed + modified))
    reverse: dict[str, set[str]] = {}
    for relation in after.get("relations", []):
        target = relation.get("target")
        if target:
            reverse.setdefault(target, set()).add(relation["source"])
    queue = deque((item, [item]) for item in direct)
    paths: dict[str, list[str]] = {item: [item] for item in direct}
    while queue:
        subject, path = queue.popleft()
        for parent in sorted(reverse.get(subject, set())):
            candidate = [*path, parent]
            if parent not in paths or (len(candidate), candidate) < (
                len(paths[parent]),
                paths[parent],
            ):
                paths[parent] = candidate
                queue.append((parent, candidate))
    new_unlinked = sorted(
        key
        for key in added
        if not reverse.get(key)
        and not any(r.get("source") == key for r in after.get("relations", []))
    )
    unknown = sorted(
        relation["source"]
        for relation in after.get("relations", [])
        if not relation.get("target") and not relation.get("external")
    )
    blockers = sorted(set(new_unlinked + unknown))
    result = {
        "before": before.get("digest"),
        "after": after.get("digest"),
        "changed": modified,
        "added": added,
        "removed": removed,
        "dependency_paths": [{"subject": key, "path": paths[key]} for key in sorted(paths)],
        "rule_expansions": [
            {"rule_id": rule["id"], "subjects": direct}
            for rule in trace_profile.get("impact_rules", [])
            if direct
        ],
        "newly_unlinked": new_unlinked,
        "unknown_dependencies": unknown,
        "affected_plan_instances": sorted(
            {
                str(origin["plan_instance"])
                for item in after_entities.values()
                for origin in item.get("origins", [])
                if isinstance(origin, dict) and isinstance(origin.get("plan_instance"), str)
            }
        ),
        "required_reviews": sorted(paths),
        "blockers": blockers,
        "state": "blocked" if blockers else "complete",
        "valid": not blockers,
    }
    result["digest"] = semantic_digest(result)
    return result
