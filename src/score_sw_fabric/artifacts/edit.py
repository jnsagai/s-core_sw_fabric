"""Preimage-bound native directive edits with byte-exact unchanged complements."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, cast

from score_sw_fabric.artifacts.models import ArtifactSemanticError, finding
from score_sw_fabric.artifacts.reader import safe_logical_path
from score_sw_fabric.artifacts.rst import scan_rst
from score_sw_fabric.process_source.reader import InputError

KINDS = {"create_document", "set_option", "set_content", "add_link", "remove_link", "insert_need"}


def _ordered(operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for operation in operations:
        identifier = operation.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in by_id:
            raise InputError("EDIT_ID", "Edit operations require unique nonempty IDs")
        if operation.get("kind") not in KINDS:
            raise InputError("EDIT_KIND", f"Unsupported edit kind: {operation.get('kind')}")
        by_id[identifier] = operation
    result: list[dict[str, Any]] = []
    pending = dict(by_id)
    while pending:
        ready = sorted(
            identifier
            for identifier, operation in pending.items()
            if set(operation.get("depends_on", [])) <= {item["id"] for item in result}
        )
        if not ready:
            raise InputError("EDIT_DEPENDENCY", "Edit dependency graph is cyclic or dangling")
        for identifier in ready:
            result.append(pending.pop(identifier))
    return result


def _directive(content: str, path: str, profile: dict[str, Any], native_id: str) -> dict[str, Any]:
    scanned = scan_rst(path, content, set(profile["directives"]))
    matches = [item for item in scanned["directives"] if item["native_id"] == native_id]
    if len(matches) != 1:
        raise ArtifactSemanticError(
            "EDIT_SUBJECT", f"Edit subject {native_id!r} is missing or ambiguous"
        )
    return cast(dict[str, Any], matches[0])


def _preimage(operation: dict[str, Any], content: str, directive: dict[str, Any] | None) -> None:
    expected = operation.get("expected_preimage")
    if not isinstance(expected, str) or len(expected) != 64:
        raise InputError("EDIT_PREIMAGE", "Every edit requires an expected SHA-256 preimage")
    actual = (
        hashlib.sha256(content.encode()).hexdigest()
        if directive is None
        else directive["original_digest"]
    )
    if actual != expected:
        raise ArtifactSemanticError(
            "EDIT_STALE_PREIMAGE", f"Stale preimage for edit {operation['id']}"
        )


def _replace(content: str, start: int, end: int, replacement: str) -> str:
    encoded = content.encode("utf-8")
    return (encoded[:start] + replacement.encode("utf-8") + encoded[end:]).decode("utf-8")


def _template(profile: dict[str, Any], template_id: str) -> Path:
    matches = [item for item in profile["templates"] if item.get("id") == template_id]
    if len(matches) != 1:
        raise ArtifactSemanticError(
            "TEMPLATE_UNAVAILABLE", f"Template {template_id!r} is unavailable"
        )
    selected = matches[0]
    path = Path(selected["path"])
    if not path.is_file() or path.is_symlink():
        raise ArtifactSemanticError("TEMPLATE_UNAVAILABLE", f"Template path is unavailable: {path}")
    expected = selected.get("sha256")
    if not isinstance(expected, str) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ArtifactSemanticError(
            "TEMPLATE_IDENTITY", f"Template hash differs from the reviewed profile: {path}"
        )
    return path


def apply_edits(
    files: dict[str, str], operations: list[dict[str, Any]], profile: dict[str, Any]
) -> tuple[dict[str, str], list[dict[str, Any]], list[dict[str, Any]]]:
    result = dict(files)
    edit_results: list[dict[str, Any]] = []
    source_map: list[dict[str, Any]] = []
    touched: set[tuple[str, str, str]] = set()
    for operation in _ordered(operations):
        operation_id = operation["id"]
        kind = operation["kind"]
        raw_path = operation.get("target_path")
        if not isinstance(raw_path, str):
            raise InputError("EDIT_PATH", f"Edit {operation_id} requires target_path")
        path = safe_logical_path(raw_path, f"/operations/{operation_id}/target_path").as_posix()
        native_id = operation.get("target_native_id")
        conflict_key = (path, str(native_id), kind)
        if conflict_key in touched:
            raise ArtifactSemanticError(
                "EDIT_CONFLICT", f"Conflicting edit target for {operation_id}"
            )
        touched.add(conflict_key)
        before = result.get(path)
        changed_span = {"start": 0, "end": 0}
        if kind == "create_document":
            if before is not None:
                raise ArtifactSemanticError(
                    "EDIT_CREATE_EXISTS", f"Create target already exists: {path}"
                )
            template_id = operation.get("values", {}).get("template_id")
            if not isinstance(template_id, str):
                raise InputError("EDIT_VALUE", "create_document requires values.template_id")
            template_bytes = _template(profile, template_id).read_text(encoding="utf-8")
            _preimage(operation, template_bytes, None)
            replacements = operation.get("values", {}).get("placeholders", {})
            if not isinstance(replacements, dict) or any(
                not isinstance(k, str) or not isinstance(v, str) for k, v in replacements.items()
            ):
                raise InputError("EDIT_VALUE", "Template placeholders must be a string mapping")
            after = template_bytes
            for key, value in sorted(replacements.items()):
                token = "{{" + key + "}}"
                if token not in after:
                    raise ArtifactSemanticError(
                        "EDIT_PLACEHOLDER", f"Template placeholder is missing: {token}"
                    )
                after = after.replace(token, value)
            if "{{" in after or "}}" in after:
                raise ArtifactSemanticError(
                    "EDIT_PLACEHOLDER", "Unresolved template placeholder remains"
                )
            changed_span = {"start": 0, "end": len(after.encode())}
        else:
            if before is None:
                raise ArtifactSemanticError(
                    "EDIT_TARGET", f"Edit target file does not exist: {path}"
                )
            if not isinstance(native_id, str):
                raise InputError("EDIT_SUBJECT", f"Edit {operation_id} requires target_native_id")
            directive = _directive(before, path, profile, native_id)
            _preimage(operation, before, directive)
            values = operation.get("values")
            if not isinstance(values, dict):
                raise InputError("EDIT_VALUE", f"Edit {operation_id} requires values")
            if kind in {"set_option", "add_link", "remove_link"}:
                option = values.get("option") or values.get("relation")
                value = values.get("value") or values.get("target")
                if not isinstance(option, str) or not isinstance(value, str):
                    raise InputError(
                        "EDIT_VALUE",
                        f"Edit {operation_id} requires option/relation and value/target",
                    )
                rule = profile["directives"][directive["name"]]
                if kind != "set_option" and option not in rule.get("relations", {}):
                    raise ArtifactSemanticError(
                        "EDIT_RELATION",
                        f"Relation {option!r} is not allowed for {directive['name']}",
                    )
                existing = next(
                    (item for item in directive["options"] if item["name"] == option), None
                )
                if kind == "set_option":
                    if existing is None:
                        insertion = " " * (directive["indent"] + 3) + f":{option}: {value}\n"
                        location = directive["content_start_byte"]
                        after = _replace(before, location, location, insertion)
                        changed_span = {"start": location, "end": location}
                    else:
                        indent = " " * (directive["indent"] + 3)
                        replacement = f"{indent}:{option}: {value}\n"
                        after = _replace(
                            before, existing["start_byte"], existing["end_byte"], replacement
                        )
                        changed_span = {
                            "start": existing["start_byte"],
                            "end": existing["end_byte"],
                        }
                else:
                    current = [
                        item.strip()
                        for item in (existing["value"] if existing else "").split(",")
                        if item.strip()
                    ]
                    if kind == "add_link":
                        if value not in current:
                            current.append(value)
                    elif value not in current:
                        raise ArtifactSemanticError(
                            "EDIT_RELATION", f"Relation target {value!r} is absent"
                        )
                    else:
                        current.remove(value)
                    replacement = (
                        " " * (directive["indent"] + 3)
                        + f":{option}: {', '.join(sorted(current))}\n"
                    )
                    if existing is None:
                        location = directive["content_start_byte"]
                        after = _replace(before, location, location, replacement)
                        changed_span = {"start": location, "end": location}
                    else:
                        after = _replace(
                            before, existing["start_byte"], existing["end_byte"], replacement
                        )
                        changed_span = {
                            "start": existing["start_byte"],
                            "end": existing["end_byte"],
                        }
            elif kind == "set_content":
                content_value = values.get("content")
                if not isinstance(content_value, str):
                    raise InputError("EDIT_VALUE", "set_content requires values.content")
                indentation = " " * (directive["indent"] + 3)
                replacement = (
                    "\n"
                    + "\n".join(
                        indentation + line if line else "" for line in content_value.splitlines()
                    )
                    + "\n"
                )
                after = _replace(
                    before, directive["content_start_byte"], directive["end_byte"], replacement
                )
                changed_span = {
                    "start": directive["content_start_byte"],
                    "end": directive["end_byte"],
                }
            else:
                directive_text = values.get("directive")
                if not isinstance(directive_text, str) or not directive_text.startswith(".. "):
                    raise InputError(
                        "EDIT_VALUE", "insert_need requires a complete values.directive"
                    )
                anchor = operation.get("anchor", "after")
                location = directive["end_byte"] if anchor == "after" else directive["start_byte"]
                replacement = directive_text.rstrip() + "\n\n"
                after = _replace(before, location, location, replacement)
                changed_span = {"start": location, "end": location}
        assert after is not None
        result[path] = after
        pre_digest = (
            hashlib.sha256((before or "").encode()).hexdigest() if before is not None else None
        )
        post_digest = hashlib.sha256(after.encode()).hexdigest()
        edit_result = {
            "id": operation_id,
            "kind": kind,
            "target_path": path,
            "target_native_id": native_id,
            "pre_digest": pre_digest,
            "post_digest": post_digest,
            "changed_spans": [changed_span],
            "unchanged_complement": "byte_exact",
            "origins": operation.get("origins", []),
            "findings": [],
        }
        edit_results.append(edit_result)
        source_map.append(
            {
                "edit_id": operation_id,
                "target_path": path,
                "target_native_id": native_id,
                "post_digest": post_digest,
                "plan_instance": operation.get("plan_instance"),
                "artifact_rule_id": operation.get("artifact_rule_id"),
                "trace_rule_id": operation.get("trace_rule_id"),
                "origins": operation.get("origins", []),
                "rationale": operation.get("rationale", ""),
            }
        )
    if not edit_results:
        raise ArtifactSemanticError(
            "EDIT_EMPTY",
            "Candidate edit set is empty",
            findings=[finding("EDIT_EMPTY", "No edit was applied")],
        )
    return result, edit_results, source_map
