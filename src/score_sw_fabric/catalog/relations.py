"""Resolve only declared native link and backlink fields."""

from typing import Any

from score_sw_fabric.process_source.reader import InputError, IntegrityError


def relations(
    entities: list[dict[str, Any]],
    contexts: list[tuple[dict[str, Any], dict[str, Any], dict[str, str]]],
    type_rules: dict[str, Any],
) -> list[dict[str, Any]]:
    import re

    selector = re.compile(r"^([A-Za-z0-9_-]+)(?:\[version==([0-9]+)\])?$")
    result: list[dict[str, Any]] = []
    for origin, properties, owners in contexts:
        try:
            definition = type_rules[origin["type"]]
            mandatory = definition.get("mandatory_links", {})
            optional = definition.get("optional_links", {})
            for field in mandatory:
                if not origin["normalized"].get(field):
                    raise IntegrityError(
                        "MANDATORY_LINK",
                        f"{origin['native_id']}: missing {field}",
                        origin["source_ref"]["pointer"],
                    )
            for field, spec in sorted(properties.items()):
                kind = spec.get("field_type")
                if kind not in ("links", "backlinks"):
                    continue
                targets = origin["normalized"].get(field)
                if targets is None:
                    raise InputError(
                        "LINK_DEFAULT",
                        f"Missing link field/default {field}",
                        origin["source_ref"]["pointer"],
                    )
                if not isinstance(targets, list) or any(not isinstance(t, str) for t in targets):
                    raise IntegrityError(
                        "LINK_TYPE",
                        f"Expected link list for {field}",
                        origin["source_ref"]["pointer"],
                    )
                for index, raw_target in enumerate(targets):
                    pointer = origin["source_ref"]["pointer"] + f"/{field}/{index}"
                    parsed = selector.fullmatch(raw_target)
                    if not parsed:
                        raise InputError(
                            "UNSUPPORTED_SELECTOR",
                            f"Unsupported target selector: {raw_target}",
                            pointer,
                        )
                    native_id = parsed.group(1)
                    revision = int(parsed.group(2)) if parsed.group(2) is not None else None
                    owner = owners.get(raw_target, owners.get(native_id))
                    candidates = [
                        e
                        for e in entities
                        if e["native_id"] == native_id
                        and (revision is None or e["native_version"] == revision)
                        and (owner is None or e["source_id"] == owner)
                    ]
                    if owner is None:
                        local = [e for e in candidates if e["source_id"] == origin["source_id"]]
                        if local:
                            candidates = local
                    if len(candidates) != 1:
                        code = "UNRESOLVED_RELATION" if not candidates else "AMBIGUOUS_RELATION"
                        message = (
                            f"{origin['native_id']} {field} -> {raw_target} "
                            f"resolves to {len(candidates)} targets"
                        )
                        raise IntegrityError(code, message, pointer)
                    target = candidates[0]
                    allowed = mandatory.get(field, optional.get(field))
                    if allowed is not None:
                        allowed_types = {part.strip() for part in allowed.split(",")}
                        if "ANY" not in allowed_types and target["type"] not in allowed_types:
                            raise IntegrityError(
                                "TARGET_TYPE", f"{field} cannot target {target['type']}", pointer
                            )
                    result.append(
                        {
                            "source_id": origin["source_id"],
                            "native_id": origin["native_id"],
                            "native_version": origin["native_version"],
                            "field": field,
                            "direction": "forward" if kind == "links" else "backlink",
                            "raw_target": raw_target,
                            "target_id": native_id,
                            "target_version_selector": revision,
                            "target_source_id": target["source_id"],
                            "resolved_native_version": target["native_version"],
                            "source_ref": origin["source_ref"],
                            "pointer": pointer,
                        }
                    )
        except (InputError, IntegrityError) as exc:
            exc.source_ref = origin["source_ref"]
            exc.native_id = origin["native_id"]
            raise
    return sorted(
        result,
        key=lambda r: (
            r["source_id"],
            r["native_id"],
            r["native_version"],
            r["field"],
            r["raw_target"],
            r["pointer"],
        ),
    )
