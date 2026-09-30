"""Validate and index a sealed native catalogue for downstream consumers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import InputError, read_json, verify_sha

TOP_LEVEL = {
    "schema_version",
    "manifest",
    "metamodel_raw",
    "types",
    "entities",
    "relations",
    "engineering_readiness",
    "digest",
}
ENTITY_REQUIRED = {
    "source_id",
    "native_id",
    "native_version",
    "type",
    "source_ref",
    "raw",
    "normalized",
}
RELATION_REQUIRED = {
    "source_id",
    "native_id",
    "native_version",
    "target_source_id",
    "target_id",
    "resolved_native_version",
    "direction",
    "field",
}


@dataclass(frozen=True)
class CatalogueIndex:
    """A validated catalogue and indices that preserve qualified native identity."""

    data: dict[str, Any]
    digest: str
    sources: dict[str, dict[str, str]]
    types: frozenset[str]
    entities: dict[tuple[str, str, int], dict[str, Any]]
    workproducts: tuple[dict[str, Any], ...]


def _mapping(value: Any, pointer: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InputError("CATALOGUE_SHAPE", f"Expected object at {pointer}", pointer)
    return value


def _list(value: Any, pointer: str) -> list[Any]:
    if not isinstance(value, list):
        raise InputError("CATALOGUE_SHAPE", f"Expected array at {pointer}", pointer)
    return value


def _identity(value: dict[str, Any], pointer: str) -> tuple[str, str, int]:
    source_id = value.get("source_id")
    native_id = value.get("native_id")
    revision = value.get("native_version")
    if (
        not isinstance(source_id, str)
        or not source_id
        or not isinstance(native_id, str)
        or not native_id
        or type(revision) is not int
        or revision < 0
    ):
        raise InputError("CATALOGUE_IDENTITY", f"Invalid native identity at {pointer}", pointer)
    return source_id, native_id, revision


def load_catalogue(path: Path, *, transport_sha256: str, expected_digest: str) -> CatalogueIndex:
    """Load a bounded catalogue and verify both its bytes and semantic selection."""

    verify_sha(path, transport_sha256, "/catalogue/sha256")
    data = read_json(path)
    if set(data) != TOP_LEVEL:
        raise InputError(
            "CATALOGUE_SHAPE",
            f"Catalogue fields differ: {sorted(set(data) ^ TOP_LEVEL)}",
            "/",
        )
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise InputError("CATALOGUE_VERSION", "Supported catalogue schema_version is 1")
    if data["engineering_readiness"] != "not_evaluated":
        raise InputError("CATALOGUE_SHAPE", "Catalogue readiness must remain not_evaluated")
    digest = data["digest"]
    if not isinstance(digest, str) or len(digest) != 64:
        raise InputError("CATALOGUE_DIGEST", "Invalid catalogue digest", "/digest")
    payload = {key: value for key, value in data.items() if key != "digest"}
    computed = hashlib.sha256(canonical(payload)).hexdigest()
    if digest != computed:
        raise InputError("CATALOGUE_DIGEST", "Catalogue self-digest mismatch", "/digest")
    if digest != expected_digest:
        raise InputError(
            "CATALOGUE_BASELINE",
            "Catalogue does not match the intake-selected semantic baseline",
            "/digest",
        )

    manifest = _mapping(data["manifest"], "/manifest")
    raw_sources = _list(manifest.get("sources"), "/manifest/sources")
    sources: dict[str, dict[str, str]] = {}
    for position, raw in enumerate(raw_sources):
        item = _mapping(raw, f"/manifest/sources/{position}")
        if set(item) != {"id", "repository", "commit"} or not all(
            isinstance(item.get(key), str) and item[key] for key in item
        ):
            raise InputError(
                "CATALOGUE_REFERENCE",
                "Invalid catalogue source binding",
                f"/manifest/sources/{position}",
            )
        source_id = item["id"]
        if source_id in sources:
            raise InputError("CATALOGUE_REFERENCE", f"Duplicate source {source_id}")
        sources[source_id] = item

    type_names: set[str] = set()
    for position, raw in enumerate(_list(data["types"], "/types")):
        item = _mapping(raw, f"/types/{position}")
        name = item.get("name")
        source_ref = _mapping(item.get("source_ref"), f"/types/{position}/source_ref")
        if (
            not isinstance(name, str)
            or not name
            or name in type_names
            or source_ref.get("source_id") not in sources
        ):
            raise InputError("CATALOGUE_REFERENCE", f"Invalid native type at /types/{position}")
        type_names.add(name)

    entities: dict[tuple[str, str, int], dict[str, Any]] = {}
    workproducts: list[dict[str, Any]] = []
    for position, raw in enumerate(_list(data["entities"], "/entities")):
        item = _mapping(raw, f"/entities/{position}")
        if not ENTITY_REQUIRED.issubset(item):
            raise InputError("CATALOGUE_SHAPE", "Entity fields missing", f"/entities/{position}")
        identity = _identity(item, f"/entities/{position}")
        if identity in entities:
            raise InputError("CATALOGUE_IDENTITY", f"Duplicate entity {identity}")
        if identity[0] not in sources or item.get("type") not in type_names:
            raise InputError("CATALOGUE_REFERENCE", f"Unknown entity source/type {identity}")
        source_ref = _mapping(item["source_ref"], f"/entities/{position}/source_ref")
        if (
            source_ref.get("source_id") != identity[0]
            or source_ref.get("native_id") != identity[1]
            or source_ref.get("native_version") != identity[2]
            or source_ref.get("repository") != sources[identity[0]]["repository"]
            or source_ref.get("commit") != sources[identity[0]]["commit"]
        ):
            raise InputError("CATALOGUE_REFERENCE", f"Entity/source reference mismatch {identity}")
        entities[identity] = item
        if item["type"] == "workproduct":
            workproducts.append(item)

    for position, raw in enumerate(_list(data["relations"], "/relations")):
        item = _mapping(raw, f"/relations/{position}")
        if not RELATION_REQUIRED.issubset(item):
            raise InputError("CATALOGUE_SHAPE", "Relation fields missing", f"/relations/{position}")
        origin = _identity(item, f"/relations/{position}")
        target = (
            item.get("target_source_id"),
            item.get("target_id"),
            item.get("resolved_native_version"),
        )
        if origin not in entities or target not in entities:
            raise InputError(
                "CATALOGUE_REFERENCE",
                f"Relation endpoint is not present: {origin} -> {target}",
                f"/relations/{position}",
            )
        if item.get("direction") not in ("forward", "backlink"):
            raise InputError("CATALOGUE_SHAPE", "Invalid relation direction")

    return CatalogueIndex(
        data=data,
        digest=digest,
        sources=sources,
        types=frozenset(type_names),
        entities=entities,
        workproducts=tuple(sorted(workproducts, key=lambda item: _identity(item, "/entities"))),
    )
