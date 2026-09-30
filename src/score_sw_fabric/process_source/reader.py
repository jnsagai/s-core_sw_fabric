"""Bounded, non-executing manifest and JSON readers."""

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import yaml

from score_sw_fabric.process_source.models import Export, Manifest, Metamodel, Mount, Source

MAX_INPUT_BYTES = 64 * 1024 * 1024
SOURCE_ID = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")


class InputError(Exception):
    """Invalid or unavailable input; CLI exit status 2."""

    def __init__(self, code: str, message: str, pointer: str = "", action: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.pointer = pointer
        self.action = action or "Correct the input and rerun the import."
        self.source_ref: dict[str, Any] | None = None
        self.native_id: str | None = None


class IntegrityError(Exception):
    """Native semantic integrity failure; CLI exit status 1."""

    def __init__(self, code: str, message: str, pointer: str = "", action: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.pointer = pointer
        self.action = action or "Resolve the pinned native source inconsistency."
        self.source_ref: dict[str, Any] | None = None
        self.native_id: str | None = None


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in items:
        if key in value:
            raise InputError("DUPLICATE_JSON_KEY", f"Duplicate JSON key {key!r}")
        value[key] = item
    return value


class _UniqueSafeLoader(yaml.SafeLoader):
    pass


def _mapping(loader: _UniqueSafeLoader, node: yaml.MappingNode) -> dict[str, Any]:
    loader.flatten_mapping(node)
    result: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if not isinstance(key, str):
            raise InputError("YAML_KEY_TYPE", "YAML mapping keys must be strings")
        if key in result:
            raise InputError("DUPLICATE_YAML_KEY", f"Duplicate YAML key {key!r}")
        result[key] = loader.construct_object(value_node, deep=True)
    return result


_UniqueSafeLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def read_bytes(path: Path) -> bytes:
    try:
        if not path.is_file():
            raise InputError("INPUT_NOT_FILE", f"Input is not a regular file: {path}")
        if path.stat().st_size > MAX_INPUT_BYTES:
            raise InputError("INPUT_TOO_LARGE", f"Input exceeds {MAX_INPUT_BYTES} bytes: {path}")
        return path.read_bytes()
    except OSError as exc:
        raise InputError("INPUT_UNAVAILABLE", str(exc)) from exc


def _reject_constant(value: str) -> None:
    raise InputError("NONFINITE_NUMBER", f"Nonfinite JSON number {value} is unsupported")


def read_json(path: Path) -> dict[str, Any]:
    try:
        result: Any = json.loads(
            read_bytes(path), object_pairs_hook=_pairs, parse_constant=_reject_constant
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputError("INVALID_JSON", f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(result, dict):
        raise InputError("JSON_ROOT", f"Expected JSON object: {path}")
    return result


def read_yaml(path: Path) -> dict[str, Any]:
    try:
        result: Any = yaml.load(read_bytes(path), Loader=_UniqueSafeLoader)
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise InputError("INVALID_YAML", f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(result, dict):
        raise InputError("YAML_ROOT", f"Expected YAML mapping: {path}")
    _json_compatible(result, set())
    return result


def _json_compatible(value: Any, seen: set[int]) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float) and math.isfinite(value):
        return
    if isinstance(value, (dict, list)):
        if id(value) in seen:
            raise InputError("YAML_CYCLE", "Recursive YAML aliases are unsupported")
        seen.add(id(value))
        if isinstance(value, dict):
            if any(not isinstance(key, str) for key in value):
                raise InputError("YAML_KEY_TYPE", "YAML mapping keys must be strings")
            for item in value.values():
                _json_compatible(item, seen)
        else:
            for item in value:
                _json_compatible(item, seen)
        seen.remove(id(value))
        return
    raise InputError("YAML_VALUE", f"Unsupported YAML value type: {type(value).__name__}")


def _keys(value: dict[str, Any], expected: set[str], pointer: str) -> None:
    unknown = value.keys() - expected
    missing = expected - value.keys()
    if unknown or missing:
        raise InputError(
            "MANIFEST_FIELDS",
            f"{pointer}: unknown={sorted(unknown)}, missing={sorted(missing)}",
            pointer,
        )


def _str(value: Any, pointer: str) -> str:
    if not isinstance(value, str) or not value:
        raise InputError("FIELD_TYPE", f"Expected nonempty string at {pointer}", pointer)
    return value


def _path(base: Path, raw: Any, pointer: str, *, directory: bool = False) -> tuple[Path, str]:
    logical = _str(raw, pointer)
    candidate = Path(logical)
    if (
        "\\" in logical
        or "//" in logical
        or candidate.is_absolute()
        or any(part in (".", "..") for part in candidate.parts)
    ):
        raise InputError("PATH_ESCAPE", f"Unsafe path at {pointer}: {logical}", pointer)
    resolved = (base / candidate).resolve()
    if not resolved.is_relative_to(base.resolve()):
        raise InputError("SYMLINK_ESCAPE", f"Path escapes manifest root at {pointer}", pointer)
    if not (resolved.is_dir() if directory else resolved.is_file()):
        raise InputError("INPUT_UNAVAILABLE", f"Missing path at {pointer}: {logical}", pointer)
    return resolved, candidate.as_posix()


def _sha(raw: Any, pointer: str) -> str:
    value = _str(raw, pointer)
    if not SHA256.fullmatch(value):
        raise InputError("SHA256_FORMAT", f"Invalid SHA-256 at {pointer}", pointer)
    return value


def verify_sha(path: Path, expected: str, pointer: str) -> None:
    found = hashlib.sha256(read_bytes(path)).hexdigest()
    if found != expected:
        raise InputError("HASH_MISMATCH", f"SHA-256 mismatch at {pointer}: {path}", pointer)


def load_manifest(path: Path) -> Manifest:
    try:
        path = path.resolve(strict=True)
    except OSError as exc:
        raise InputError("INPUT_UNAVAILABLE", str(exc)) from exc
    data = read_yaml(path)
    _keys(
        data,
        {
            "schema_version",
            "sources",
            "exports",
            "metamodel",
            "metamodel_schema",
            "mounts",
            "provenance",
        },
        "/",
    )
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise InputError("MANIFEST_VERSION", "Supported manifest schema_version is 1")
    provenance = data["provenance"]
    if not isinstance(provenance, dict):
        raise InputError("PROVENANCE", "Expected provenance mapping", "/provenance")
    _keys(
        provenance,
        {"origin", "argv", "toolchain_ref", "build_log_sha256", "exit_code"},
        "/provenance",
    )
    if provenance["origin"] not in ("checked_in_expected", "fresh_build"):
        raise InputError("PROVENANCE", "Unsupported export origin", "/provenance/origin")
    if provenance["argv"] is not None and (
        not isinstance(provenance["argv"], list)
        or any(not isinstance(arg, str) for arg in provenance["argv"])
    ):
        raise InputError("PROVENANCE", "argv must be a string list or null", "/provenance/argv")
    for name in ("toolchain_ref", "build_log_sha256"):
        value = provenance[name]
        if value is not None and not isinstance(value, str):
            raise InputError("PROVENANCE", f"{name} must be string or null", f"/provenance/{name}")
    if provenance["build_log_sha256"] is not None:
        _sha(provenance["build_log_sha256"], "/provenance/build_log_sha256")
    if provenance["exit_code"] is not None and type(provenance["exit_code"]) is not int:
        raise InputError("PROVENANCE", "exit_code must be integer or null", "/provenance/exit_code")
    if provenance["origin"] == "fresh_build" and (
        not provenance["argv"] or provenance["exit_code"] != 0 or not provenance["build_log_sha256"]
    ):
        raise InputError("PROVENANCE", "Fresh build requires successful command and log digest")
    base = path.parent
    if not isinstance(data["sources"], list) or not data["sources"]:
        raise InputError("SOURCES_REQUIRED", "At least one source is required", "/sources")
    sources: list[Source] = []
    semantic_sources: list[dict[str, str]] = []
    for index, raw in enumerate(data["sources"]):
        pointer = f"/sources/{index}"
        if not isinstance(raw, dict):
            raise InputError("FIELD_TYPE", f"Expected mapping at {pointer}", pointer)
        _keys(raw, {"id", "repository", "commit", "root"}, pointer)
        source_id = _str(raw["id"], pointer + "/id")
        if not SOURCE_ID.fullmatch(source_id) or source_id in {s.source_id for s in sources}:
            raise InputError("SOURCE_ID", f"Invalid or duplicate source id {source_id!r}", pointer)
        commit = _str(raw["commit"], pointer + "/commit")
        if not COMMIT.fullmatch(commit):
            raise InputError("COMMIT_FORMAT", f"Expected full Git SHA at {pointer}", pointer)
        repository = _str(raw["repository"], pointer + "/repository")
        if not repository.startswith("https://"):
            raise InputError(
                "REPOSITORY_URL", f"Expected HTTPS repository URL at {pointer}", pointer
            )
        root, _ = _path(base, raw["root"], pointer + "/root", directory=True)
        sources.append(Source(source_id, repository, commit, root))
        semantic_sources.append({"id": source_id, "repository": repository, "commit": commit})
    known = {s.source_id for s in sources}
    meta = data["metamodel"]
    if not isinstance(meta, dict):
        raise InputError("FIELD_TYPE", "Expected metamodel mapping", "/metamodel")
    _keys(meta, {"source_id", "path", "sha256"}, "/metamodel")
    meta_source = _str(meta["source_id"], "/metamodel/source_id")
    if meta_source not in known:
        raise InputError("UNKNOWN_SOURCE", "Metamodel source is not declared", "/metamodel")
    meta_root = next(s.root for s in sources if s.source_id == meta_source)
    meta_path, meta_logical = _path(meta_root, meta["path"], "/metamodel/path")
    meta_hash = _sha(meta["sha256"], "/metamodel/sha256")
    verify_sha(meta_path, meta_hash, "/metamodel")
    model = Metamodel(meta_source, meta_path, meta_logical, meta_hash)
    schema_info = data["metamodel_schema"]
    if not isinstance(schema_info, dict):
        raise InputError("METAMODEL_SCHEMA", "Expected metamodel_schema mapping")
    _keys(schema_info, {"source_id", "path", "sha256"}, "/metamodel_schema")
    if schema_info["source_id"] != meta_source:
        raise InputError("METAMODEL_SCHEMA", "Metamodel/schema sources disagree")
    schema_path, schema_logical = _path(meta_root, schema_info["path"], "/metamodel_schema/path")
    schema_hash = _sha(schema_info["sha256"], "/metamodel_schema/sha256")
    verify_sha(schema_path, schema_hash, "/metamodel_schema")
    read_json(schema_path)
    model_schema = Metamodel(meta_source, schema_path, schema_logical, schema_hash)
    if not isinstance(data["exports"], list) or not data["exports"]:
        raise InputError("EXPORTS_REQUIRED", "At least one export is required", "/exports")
    exports: list[Export] = []
    semantic_exports: list[dict[str, Any]] = []
    for index, raw in enumerate(data["exports"]):
        pointer = f"/exports/{index}"
        if not isinstance(raw, dict):
            raise InputError("FIELD_TYPE", f"Expected mapping at {pointer}", pointer)
        _keys(raw, {"source_id", "path", "sha256", "version", "relation_owners"}, pointer)
        source_id = _str(raw["source_id"], pointer + "/source_id")
        if source_id not in known:
            raise InputError("UNKNOWN_SOURCE", f"Unknown source {source_id}", pointer)
        export_path, logical = _path(base, raw["path"], pointer + "/path")
        digest = _sha(raw["sha256"], pointer + "/sha256")
        verify_sha(export_path, digest, pointer)
        version = raw["version"]
        if not isinstance(version, str):
            raise InputError("FIELD_TYPE", "Export version must be a string", pointer + "/version")
        owners = raw["relation_owners"]
        if not isinstance(owners, dict) or any(
            not isinstance(key, str) or not isinstance(value, str) or value not in known
            for key, value in owners.items()
        ):
            raise InputError("RELATION_OWNERS", "Invalid relation owner mapping", pointer)
        if any(e.source_id == source_id and e.logical_path == logical for e in exports):
            raise InputError("DUPLICATE_EXPORT", "Duplicate source/export path", pointer)
        exports.append(Export(source_id, export_path, logical, digest, version, owners))
        semantic_exports.append(
            {
                "source_id": source_id,
                "path": logical,
                "sha256": digest,
                "version": version,
                "relation_owners": owners,
            }
        )
    if not isinstance(data["mounts"], list):
        raise InputError("MOUNTS_TYPE", "Expected mount list", "/mounts")
    mounts: list[Mount] = []
    for index, raw in enumerate(data["mounts"]):
        pointer = f"/mounts/{index}"
        if not isinstance(raw, dict):
            raise InputError("FIELD_TYPE", f"Expected mapping at {pointer}", pointer)
        _keys(raw, {"source_id", "docname_prefix", "path_prefix"}, pointer)
        source_id = _str(raw["source_id"], pointer + "/source_id")
        if source_id not in known:
            raise InputError("UNKNOWN_SOURCE", f"Unknown mount source {source_id}", pointer)
        doc_prefix = raw["docname_prefix"]
        path_prefix = raw["path_prefix"]
        if not isinstance(doc_prefix, str) or not isinstance(path_prefix, str):
            raise InputError("FIELD_TYPE", f"Expected mount prefixes at {pointer}", pointer)
        if Path(path_prefix).is_absolute() or ".." in Path(path_prefix).parts:
            raise InputError("PATH_ESCAPE", f"Unsafe mount path at {pointer}", pointer)
        mounts.append(Mount(source_id, doc_prefix, path_prefix))
    semantic = {
        "schema_version": 1,
        "provenance": provenance,
        "sources": sorted(semantic_sources, key=lambda s: s["id"]),
        "exports": sorted(semantic_exports, key=lambda e: (e["source_id"], e["path"])),
        "metamodel": {"source_id": meta_source, "path": meta_logical, "sha256": meta_hash},
        "metamodel_schema": {
            "source_id": meta_source,
            "path": schema_logical,
            "sha256": schema_hash,
        },
        "mounts": sorted(
            (m.__dict__ for m in mounts),
            key=lambda m: (m["source_id"], m["docname_prefix"], m["path_prefix"]),
        ),
    }
    return Manifest(tuple(sources), tuple(exports), model, model_schema, tuple(mounts), semantic)
