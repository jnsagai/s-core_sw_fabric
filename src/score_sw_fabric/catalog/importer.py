"""Import pinned Sphinx-Needs 8.3.1 exports and their native metamodel."""

import re
from dataclasses import asdict
from typing import Any

from score_sw_fabric.process_source.locations import source_ref
from score_sw_fabric.process_source.models import Manifest
from score_sw_fabric.process_source.reader import InputError, IntegrityError, read_json, read_yaml

SELECTOR = re.compile(r"^([A-Za-z0-9_-]+)(?:\[version==([0-9]+)\])?$")
PINNED_DOCS_COMMIT = "d5f3de608cdfc034952c57d40979c78d8cd35957"
PINNED_METAMODEL_SHA256 = "fe6a3b6af5ea69271e53c57e3a1694dc69d6ff3df16bd1505dc7242db9976290"
PINNED_SCHEMA_SHA256 = "c3dc028691cc55e8d8e2c4d8d3804644d6a0f5977f53955c12489c636ffae724"


def _metamodel(manifest: Manifest) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source = next(s for s in manifest.sources if s.source_id == manifest.metamodel.source_id)
    if (
        source.repository != "https://github.com/eclipse-score/docs-as-code"
        or source.commit != PINNED_DOCS_COMMIT
        or manifest.metamodel.sha256 != PINNED_METAMODEL_SHA256
        or manifest.metamodel_schema.sha256 != PINNED_SCHEMA_SHA256
    ):
        raise InputError(
            "UNSUPPORTED_METAMODEL", "Only pinned docs-as-code v8.2.0 rules are supported"
        )
    raw = read_yaml(manifest.metamodel.path)
    if not isinstance(raw.get("needs_types"), dict) or not isinstance(
        raw.get("needs_extra_links"), dict
    ):
        raise InputError("METAMODEL_SCHEMA", "Expected native needs_types and needs_extra_links")
    reference = {
        "source_id": source.source_id,
        "repository": source.repository,
        "commit": source.commit,
        "path": manifest.metamodel.logical_path,
        "sha256": manifest.metamodel.sha256,
    }
    types = []
    for name, definition in sorted(raw["needs_types"].items()):
        if not isinstance(name, str) or not isinstance(definition, dict):
            raise InputError("METAMODEL_TYPE", f"Invalid native type {name!r}")
        mandatory = definition.get("mandatory_options", {})
        if not isinstance(mandatory, dict):
            raise InputError("METAMODEL_TYPE", f"Invalid mandatory_options for {name}")
        types.append(
            {
                "name": name,
                "definition": definition,
                "source_ref": {**reference, "pointer": f"/needs_types/{name}"},
            }
        )
    return types, raw


def _entity_records(
    manifest: Manifest, types: list[dict[str, Any]], metamodel: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[tuple[dict[str, Any], dict[str, Any], dict[str, str]]]]:
    names = {item["name"]: item["definition"] for item in types}
    allowed_links = set(metamodel["needs_extra_links"]) | {"links", "parent_needs"}
    entities: list[dict[str, Any]] = []
    contexts: list[tuple[dict[str, Any], dict[str, Any], dict[str, str]]] = []
    identities: set[tuple[str, str, int]] = set()
    for export in manifest.exports:
        try:
            data = read_json(export.path)
            versions = data.get("versions")
            if not isinstance(versions, dict) or export.version not in versions:
                raise InputError(
                    "EXPORT_VERSION", f"Missing selected export version {export.version}"
                )
            if not isinstance(data.get("current_version"), str):
                raise InputError("EXPORT_ENVELOPE", "Missing current_version")
            block = versions[export.version]
            if not isinstance(block, dict) or block.get("creator") != {
                "program": "sphinx_needs",
                "version": "8.3.1",
            }:
                raise InputError("UNSUPPORTED_CREATOR", "Expected sphinx_needs 8.3.1")
            needs = block.get("needs")
            schema = block.get("needs_schema")
            props = schema.get("properties") if isinstance(schema, dict) else None
            if (
                not isinstance(needs, dict)
                or not isinstance(props, dict)
                or type(block.get("needs_amount")) is not int
                or block["needs_amount"] != len(needs)
                or block.get("needs_defaults_removed") is not True
            ):
                raise InputError("EXPORT_SCHEMA", "Unsupported or inconsistent sparse needs export")
            for key, raw in sorted(needs.items()):
                pointer = f"/versions/{export.version}/needs/{key}"
                if not isinstance(key, str) or not isinstance(raw, dict):
                    raise InputError("NEED_RECORD", "Invalid need record", pointer)
                normalized = dict(raw)
                for field, spec in props.items():
                    if not isinstance(spec, dict) or spec.get("field_type") not in (
                        "core",
                        "extra",
                        "links",
                        "backlinks",
                    ):
                        raise InputError("EXPORT_SCHEMA", f"Invalid property schema {field}")
                    kind = spec["field_type"]
                    if kind == "links" and field not in allowed_links:
                        raise InputError("UNSUPPORTED_LINK_SCHEMA", f"Unknown link field {field}")
                    if kind == "backlinks" and (
                        not field.endswith("_back") or field[:-5] not in allowed_links
                    ):
                        raise InputError(
                            "UNSUPPORTED_LINK_SCHEMA", f"Unknown backlink field {field}"
                        )
                    if field not in normalized and "default" in spec:
                        normalized[field] = spec["default"]
                native_id, version, type_name = (
                    normalized.get("id"),
                    normalized.get("version"),
                    normalized.get("type"),
                )
                if (
                    not isinstance(native_id, str)
                    or not native_id
                    or type(version) is not int
                    or version < 0
                ):
                    raise IntegrityError(
                        "NATIVE_ID_VERSION", "Invalid native ID or version", pointer
                    )
                parsed = SELECTOR.fullmatch(key)
                if (
                    not parsed
                    or parsed.group(1) != native_id
                    or (parsed.group(2) is not None and int(parsed.group(2)) != version)
                ):
                    raise IntegrityError(
                        "EXPORT_KEY", "Export key and native identity disagree", pointer
                    )
                if not isinstance(type_name, str) or type_name not in names:
                    raise InputError(
                        "UNSUPPORTED_TYPE", f"Unknown native type {type_name}", pointer
                    )
                if type(normalized.get("is_external")) is not bool:
                    raise InputError("NEED_FIELD_TYPE", "is_external must be boolean", pointer)
                if not isinstance(normalized.get("parts"), dict):
                    raise InputError("NEED_FIELD_TYPE", "parts must be a mapping", pointer)
                for field in ("title", "content", "status"):
                    if normalized.get(field) is not None and not isinstance(normalized[field], str):
                        raise InputError(
                            "NEED_FIELD_TYPE", f"{field} must be string or null", pointer
                        )
                identity = (export.source_id, native_id, version)
                if identity in identities:
                    raise IntegrityError(
                        "DUPLICATE_IDENTITY", "Duplicate source-qualified need identity", pointer
                    )
                identities.add(identity)
                if normalized.get("parts"):
                    raise InputError(
                        "UNSUPPORTED_PARTS",
                        "Need parts require a separate native contract",
                        pointer,
                    )
                rules = names[type_name].get("mandatory_options", {})
                for field, pattern in rules.items():
                    value = normalized.get(field)
                    if not isinstance(pattern, str) or not isinstance(value, str):
                        raise IntegrityError(
                            "METAMODEL_RULE", f"{native_id}: missing {field}", pointer
                        )
                    if re.fullmatch(pattern, value) is None:
                        raise IntegrityError(
                            "METAMODEL_RULE", f"{native_id}: invalid {field}", pointer
                        )
                ref = source_ref(manifest, export.source_id, normalized, export.sha256, pointer)
                tags = normalized.get("tags", [])
                if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
                    raise InputError("NEED_TAGS", "Expected string tag list", pointer)
                template_keys: dict[str, str | None] = {}
                for kind in ("template", "pre_template", "post_template"):
                    value = normalized.get(kind)
                    if value is not None and not isinstance(value, str):
                        raise InputError("TEMPLATE_TYPE", f"{kind} must be string or null", pointer)
                    template_keys[kind] = value
                entity = {
                    "source_id": export.source_id,
                    "export_version": export.version,
                    "export_key": key,
                    "native_id": native_id,
                    "native_version": version,
                    "type": type_name,
                    "title": normalized.get("title"),
                    "content": normalized.get("content"),
                    "status": normalized.get("status"),
                    "is_external": normalized.get("is_external", False),
                    "is_template": type_name == "gd_temp" or "template" in tags,
                    "template_keys": template_keys,
                    "source_ref": asdict(ref),
                    "raw": raw,
                    "normalized": normalized,
                }
                entities.append(entity)
                contexts.append((entity, props, export.relation_owners))
        except (InputError, IntegrityError) as exc:
            source = next(s for s in manifest.sources if s.source_id == export.source_id)
            exc.source_ref = {
                "source_id": source.source_id,
                "repository": source.repository,
                "commit": source.commit,
                "export_ref": export.sha256,
            }
            if "/needs/" in exc.pointer:
                exc.native_id = exc.pointer.split("/needs/", 1)[1].split("/", 1)[0]
            raise
    return entities, contexts


def build_catalogue(manifest: Manifest) -> dict[str, Any]:
    types, metamodel = _metamodel(manifest)
    entities, contexts = _entity_records(manifest, types, metamodel)
    from score_sw_fabric.catalog.relations import relations

    return {
        "schema_version": 1,
        "manifest": manifest.semantic,
        "metamodel_raw": metamodel,
        "types": types,
        "entities": sorted(
            entities, key=lambda e: (e["source_id"], e["native_id"], e["native_version"])
        ),
        "relations": relations(entities, contexts, metamodel["needs_types"]),
        "engineering_readiness": "not_evaluated",
    }
