"""Source/native-export reconciliation and source-qualified artifact indexes."""

from __future__ import annotations

import hashlib
from typing import Any

from score_sw_fabric.artifacts.models import (
    ArtifactSemanticError,
    Finding,
    enforce_limit,
    finding,
    unevaluated_capabilities,
)
from score_sw_fabric.artifacts.rst import scan_rst
from score_sw_fabric.compiler.reader import semantic_digest


def _key(namespace: str, source_id: str, native_id: str, version: str) -> str:
    return f"{namespace}:{source_id}:{native_id}@{version}"


def _export_needs(export: dict[str, Any]) -> list[dict[str, Any]]:
    direct = export.get("needs")
    if isinstance(direct, list):
        return [item for item in direct if isinstance(item, dict)]
    versions = export.get("versions")
    if isinstance(versions, dict):
        result: list[dict[str, Any]] = []
        for version in versions.values():
            needs = version.get("needs") if isinstance(version, dict) else None
            if isinstance(needs, dict):
                result.extend(item for item in needs.values() if isinstance(item, dict))
            elif isinstance(needs, list):
                result.extend(item for item in needs if isinstance(item, dict))
        return result
    return []


def _export_source_path(item: dict[str, Any], profile: dict[str, Any]) -> str | None:
    direct = item.get("path")
    if isinstance(direct, str):
        return direct
    docname = item.get("docname")
    if not isinstance(docname, str):
        return None
    mounts = profile.get("native_validator", {}).get("source_mounts", [])
    if not isinstance(mounts, list):
        return None
    for mount in mounts:
        if not isinstance(mount, dict):
            continue
        docname_prefix = mount.get("docname_prefix")
        source_prefix = mount.get("source_prefix")
        if not isinstance(docname_prefix, str) or not isinstance(source_prefix, str):
            continue
        if (
            docname_prefix
            and docname != docname_prefix
            and not docname.startswith(docname_prefix + "/")
        ):
            continue
        suffix = docname[len(docname_prefix) :].lstrip("/") if docname_prefix else docname
        return "/".join(part for part in (source_prefix.rstrip("/"), suffix + ".rst") if part)
    return None


def build_index(
    files: dict[str, str],
    snapshot: dict[str, Any],
    profile: dict[str, Any],
    native_export: dict[str, Any],
    native_receipt: dict[str, Any],
) -> dict[str, Any]:
    supported = set(profile["directives"])
    namespace = snapshot["target_namespace"]
    source_id = snapshot["source"]["source_id"]
    revision = snapshot["source"]["commit"]
    scanned = [scan_rst(path, content, supported) for path, content in sorted(files.items())]
    findings: list[Finding] = []
    wrappers: list[dict[str, Any]] = []
    needs: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    identities: dict[str, dict[str, Any]] = {}
    folded_ids: dict[str, str] = {}
    wrapper_by_path: dict[str, str] = {}
    directives: list[dict[str, Any]] = []
    for source_file in scanned:
        for directive in source_file["directives"]:
            directives.append(directive)
            native_id = directive["native_id"]
            if not isinstance(native_id, str) or not native_id:
                findings.append(
                    finding(
                        "NATIVE_ID_MISSING",
                        "Managed directive has no native ID",
                        directive["path"],
                        str(directive["start_line"]),
                    )
                )
                continue
            version = str(directive["native_version"])
            identity = _key(namespace, source_id, native_id, version)
            if identity in identities or native_id.casefold() in folded_ids:
                findings.append(
                    finding(
                        "NATIVE_ID_COLLISION",
                        "Duplicate or case-colliding native ID",
                        native_id,
                        directive["path"],
                    )
                )
                continue
            folded_ids[native_id.casefold()] = native_id
            rule = profile["directives"][directive["name"]]
            options = directive["option_values"]
            for required in rule.get("required_options", []):
                if not options.get(required):
                    findings.append(
                        finding(
                            "NATIVE_REQUIRED_OPTION",
                            f"Missing required option {required}",
                            native_id,
                            directive["path"],
                        )
                    )
            status = options.get("status")
            if status not in rule.get("statuses", []):
                findings.append(
                    finding(
                        "NATIVE_STATUS",
                        f"Status {status!r} is invalid for {directive['name']}",
                        native_id,
                        directive["path"],
                    )
                )
            entity_relations: list[dict[str, Any]] = []
            for relation_name, target_types in rule.get("relations", {}).items():
                raw = options.get(relation_name)
                if not raw:
                    continue
                for selector in [item.strip() for item in raw.split(",") if item.strip()]:
                    relation = {
                        "source": identity,
                        "source_native_id": native_id,
                        "field": relation_name,
                        "direction": "forward",
                        "raw_selector": selector,
                        "target_native_id": selector.split("@", 1)[0],
                        "target_version": selector.split("@", 1)[1] if "@" in selector else None,
                        "allowed_target_types": target_types,
                        "target": None,
                        "external": False,
                        "source_location": {
                            "path": directive["path"],
                            "line": directive["start_line"],
                        },
                    }
                    relations.append(relation)
                    entity_relations.append(relation)
            entity = {
                "key": identity,
                "target_namespace": namespace,
                "source_id": source_id,
                "native_id": native_id,
                "native_version": version,
                "type": directive["name"],
                "title": directive["title"],
                "content": directive["content"].strip(),
                "status": status,
                "options": dict(sorted(options.items())),
                "relations": entity_relations,
                "source": {
                    "path": directive["path"],
                    "start_line": directive["start_line"],
                    "end_line": directive["end_line"],
                    "revision": revision,
                },
                "wrapper_key": None,
                "origins": [],
            }
            entity["fingerprint"] = hashlib.sha256(
                str(sorted((k, v) for k, v in entity.items() if k != "fingerprint")).encode()
            ).hexdigest()
            identities[native_id] = entity
            if directive["name"] == "document":
                if directive["path"] in wrapper_by_path:
                    findings.append(
                        finding(
                            "WRAPPER_CARDINALITY",
                            "Managed file contains multiple document wrappers",
                            directive["path"],
                        )
                    )
                wrapper_by_path[directive["path"]] = identity
                wrappers.append(entity)
            else:
                needs.append(entity)
    optional_wrapper_paths = set(profile.get("containment", {}).get("wrapper_optional_paths", []))
    for need in needs:
        wrapper = wrapper_by_path.get(need["source"]["path"])
        if wrapper is None and need["source"]["path"] not in optional_wrapper_paths:
            findings.append(
                finding(
                    "CONTAINMENT_MISSING",
                    "Contained need has no document wrapper",
                    need["native_id"],
                    need["source"]["path"],
                )
            )
        need["wrapper_key"] = wrapper
    external_ids = {
        native_id
        for external in snapshot.get("external_exports", [])
        if isinstance(external, dict)
        for native_id in external.get("native_ids", [])
        if isinstance(native_id, str)
    }
    external_prefixes = {
        prefix
        for external in snapshot.get("external_exports", [])
        if isinstance(external, dict)
        for prefix in external.get("prefixes", [])
        if isinstance(prefix, str)
    }
    for relation in relations:
        target = identities.get(relation["target_native_id"])
        if target is not None:
            relation["target"] = target["key"]
            if target["type"] not in relation["allowed_target_types"]:
                findings.append(
                    finding(
                        "RELATION_TARGET_TYPE",
                        "Relation resolves to a forbidden target type",
                        relation["source_native_id"],
                        relation["target_native_id"],
                    )
                )
        elif (
            relation["target_native_id"] in external_ids
            or any(relation["target_native_id"].startswith(prefix) for prefix in external_prefixes)
            or "work_product" in relation["allowed_target_types"]
        ):
            relation["external"] = True
        else:
            findings.append(
                finding(
                    "RELATION_UNRESOLVED",
                    "Relation target is unresolved",
                    relation["source_native_id"],
                    relation["target_native_id"],
                )
            )
    export_items = _export_needs(native_export)
    export_by_id: dict[str, dict[str, Any]] = {}
    for item in export_items:
        native_id = item.get("id")
        if not isinstance(native_id, str) or native_id in export_by_id:
            findings.append(
                finding("EXPORT_ID", "Native export has a missing or duplicate ID", str(native_id))
            )
            continue
        export_by_id[native_id] = item
    reconciliation: list[dict[str, Any]] = []
    for native_id, entity in sorted(identities.items()):
        exported = export_by_id.get(native_id)
        state = "matched"
        mismatches: list[str] = []
        if exported is None:
            state = "source_only"
            mismatches.append("missing export record")
        else:
            pairs = {
                "type": (entity["type"], exported.get("type")),
                "title": (entity["title"], exported.get("title")),
                "status": (entity["status"], exported.get("status")),
                "version": (entity["native_version"], exported.get("version")),
                "path": (
                    entity["source"]["path"],
                    _export_source_path(exported, profile),
                ),
                "line": (
                    entity["source"]["start_line"],
                    exported.get("lineno", exported.get("line")),
                ),
            }
            for field, (expected, actual) in pairs.items():
                if str(actual) != str(expected):
                    mismatches.append(field)
            if mismatches:
                state = "mismatched"
        if state != "matched":
            findings.append(
                finding(
                    "SOURCE_EXPORT_MISMATCH",
                    f"Source/export reconciliation failed: {', '.join(mismatches)}",
                    native_id,
                )
            )
        reconciliation.append({"native_id": native_id, "state": state, "mismatches": mismatches})
    for native_id in sorted(export_by_id.keys() - identities.keys()):
        findings.append(
            finding("EXPORT_ONLY", "Native export record has no live source directive", native_id)
        )
        reconciliation.append(
            {
                "native_id": native_id,
                "state": "export_only",
                "mismatches": ["missing source record"],
            }
        )
    limits = profile["limits"]
    for name, observed in (
        ("entities", len(identities)),
        ("relations", len(relations)),
        ("findings", len(findings)),
    ):
        enforce_limit(
            limits,
            name,
            observed,
            "ARTIFACT_LIMIT",
            f"Artifact index exceeds declared {name} limit",
            semantic=True,
        )
    index = {
        "schema_version": 1,
        "kind": "native_artifact_index",
        "profile": {
            "id": profile["id"],
            "version": profile["version"],
            "digest": profile["digest"],
        },
        "snapshot": {
            "target_namespace": namespace,
            "snapshot_id": snapshot["snapshot_id"],
            "digest": snapshot["digest"],
            "source": snapshot["source"],
        },
        "native_receipt": native_receipt,
        "files": scanned,
        "wrappers": sorted(wrappers, key=lambda item: item["key"]),
        "needs": sorted(needs, key=lambda item: item["key"]),
        "relations": sorted(
            relations, key=lambda item: (item["source"], item["field"], item["raw_selector"])
        ),
        "reconciliation": sorted(reconciliation, key=lambda item: item["native_id"]),
        "counts": {
            "files": len(scanned),
            "wrappers": len(wrappers),
            "needs": len(needs),
            "relations": len(relations),
            "findings": len(findings),
        },
        "findings": sorted(findings, key=lambda item: (item["code"], item["subjects"])),
        "valid": not findings and native_receipt.get("accepted") is True,
        "limitations": ["Derived index; native RST remains authoritative."],
        "capabilities": unevaluated_capabilities(),
    }
    index["digest"] = semantic_digest(index)
    return index


def require_valid_index(index: dict[str, Any]) -> dict[str, Any]:
    if not index.get("valid"):
        raise ArtifactSemanticError(
            "ARTIFACT_INDEX_INVALID",
            "Native artifact index is invalid",
            findings=index.get("findings", []),
        )
    return index
