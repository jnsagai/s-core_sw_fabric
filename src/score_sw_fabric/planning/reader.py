"""Bounded planning input loading and semantic normalization."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.planning.models import PlanningInputs
from score_sw_fabric.process_source.reader import InputError, read_yaml, verify_sha

SHA256 = set("0123456789abcdef")
INTAKE_FIELDS = {
    "schema_version",
    "target_namespace",
    "change",
    "scopes",
    "affected_scopes",
    "catalogue",
    "profile",
    "mapping",
    "inventory",
    "decisions",
    "local_paths",
}
DOCUMENT_FIELDS = {"path", "sha256"}
CATALOGUE_FIELDS = {"path", "sha256", "digest"}
SCOPE_FIELDS = {"kind", "id", "parent", "facts"}


def _exact(value: Any, fields: set[str], pointer: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        actual = set(value) if isinstance(value, dict) else set()
        raise InputError(
            "PLANNING_FIELDS",
            f"{pointer}: unexpected={sorted(actual - fields)}, missing={sorted(fields - actual)}",
            pointer,
        )
    return value


def _version(value: dict[str, Any], pointer: str) -> None:
    if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise InputError("PLANNING_VERSION", f"Supported schema_version is 1 at {pointer}")


def _digest(value: Any, pointer: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in SHA256 for character in value)
    ):
        raise InputError("SHA256_FORMAT", f"Invalid SHA-256 at {pointer}", pointer)
    return value


def _safe_path(base: Path, value: Any, pointer: str, *, directory: bool = False) -> Path:
    if not isinstance(value, str) or not value:
        raise InputError("FIELD_TYPE", f"Expected nonempty path at {pointer}", pointer)
    relative = Path(value)
    if relative.is_absolute() or "\\" in value or any(p in ("", ".", "..") for p in relative.parts):
        raise InputError("PATH_ESCAPE", f"Unsafe path at {pointer}: {value}", pointer)
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()):
        raise InputError("PATH_ESCAPE", f"Path escapes intake root at {pointer}", pointer)
    if directory:
        if path.exists() and not path.is_dir():
            raise InputError("INPUT_NOT_DIRECTORY", f"Expected directory at {pointer}", pointer)
    elif not path.is_file():
        raise InputError("INPUT_UNAVAILABLE", f"Missing file at {pointer}: {value}", pointer)
    return path


def normalize(value: Any) -> Any:
    """Normalize the planning documents' set-like arrays deterministically."""

    if isinstance(value, dict):
        return {key: normalize(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        items = [normalize(item) for item in value]
        return sorted(items, key=canonical)
    if value is None or type(value) in (str, int, float, bool):
        return value
    raise InputError("PLANNING_VALUE", f"Unsupported value: {type(value).__name__}")


def semantic_digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(normalize(value))).hexdigest()


def _load_document(base: Path, raw: Any, name: str) -> tuple[Path, dict[str, Any], str]:
    ref = _exact(raw, DOCUMENT_FIELDS, f"/{name}")
    path = _safe_path(base, ref["path"], f"/{name}/path")
    digest = _digest(ref["sha256"], f"/{name}/sha256")
    verify_sha(path, digest, f"/{name}")
    data = read_yaml(path)
    _version(data, f"/{name}")
    return path, data, semantic_digest(data)


def _validate_scopes(intake: dict[str, Any]) -> None:
    scopes = intake["scopes"]
    if not isinstance(scopes, list) or not scopes or len(scopes) > 1000:
        raise InputError("SCOPE_COUNT", "Intake requires 1..1000 scopes", "/scopes")
    identities: set[tuple[str, str]] = set()
    parents: dict[tuple[str, str], tuple[str, str] | None] = {}
    for position, raw in enumerate(scopes):
        scope = _exact(raw, SCOPE_FIELDS, f"/scopes/{position}")
        kind, identifier = scope["kind"], scope["id"]
        if kind not in ("feature", "component", "module", "platform") or not isinstance(
            identifier, str
        ):
            raise InputError("SCOPE_IDENTITY", "Invalid scope identity", f"/scopes/{position}")
        key = kind, identifier
        if key in identities:
            raise InputError("SCOPE_IDENTITY", f"Duplicate scope {key}")
        identities.add(key)
        if not isinstance(scope["facts"], dict):
            raise InputError("FIELD_TYPE", "Scope facts must be a mapping")
        parent = scope["parent"]
        if parent is None:
            parents[key] = None
        else:
            parent_value = _exact(parent, {"kind", "id"}, f"/scopes/{position}/parent")
            parents[key] = parent_value["kind"], parent_value["id"]
    for key, parent in parents.items():
        seen = {key}
        current = parent
        while current is not None:
            if current in seen:
                raise InputError("SCOPE_CYCLE", f"Scope ownership cycle at {current}")
            seen.add(current)
            current = parents.get(current)
    affected = intake["affected_scopes"]
    if not isinstance(affected, list) or any(
        not isinstance(item, dict)
        or set(item) != {"kind", "id"}
        or (item["kind"], item["id"]) not in identities
        for item in affected
    ):
        raise InputError("AFFECTED_SCOPES", "Affected scopes must resolve exactly")


def load_planning_inputs(path: Path) -> PlanningInputs:
    """Load an intake and all local, hash-selected planning documents."""

    try:
        path = path.resolve(strict=True)
    except OSError as exc:
        raise InputError("INPUT_UNAVAILABLE", str(exc)) from exc
    intake = _exact(read_yaml(path), INTAKE_FIELDS, "/")
    _version(intake, "/")
    if not isinstance(intake["target_namespace"], str) or not intake["target_namespace"]:
        raise InputError("TARGET_NAMESPACE", "Target namespace must be nonempty")
    if not isinstance(intake["change"], dict):
        raise InputError("FIELD_TYPE", "Change must be a mapping", "/change")
    _validate_scopes(intake)

    base = path.parent
    catalogue_ref = _exact(intake["catalogue"], CATALOGUE_FIELDS, "/catalogue")
    catalogue_path = _safe_path(base, catalogue_ref["path"], "/catalogue/path")
    catalogue_sha = _digest(catalogue_ref["sha256"], "/catalogue/sha256")
    catalogue_digest = _digest(catalogue_ref["digest"], "/catalogue/digest")
    verify_sha(catalogue_path, catalogue_sha, "/catalogue")

    document_paths: list[Path] = []
    documents: dict[str, dict[str, Any]] = {}
    semantic_digests: dict[str, str] = {}
    for name in ("profile", "mapping", "inventory", "decisions"):
        document_path, document, digest = _load_document(base, intake[name], name)
        document_paths.append(document_path)
        documents[name] = document
        semantic_digests[name] = digest

    local_paths = _exact(intake["local_paths"], {"output_root", "reference_roots"}, "/local_paths")
    output_root = _safe_path(
        base, local_paths["output_root"], "/local_paths/output_root", directory=True
    )
    raw_roots = local_paths["reference_roots"]
    if not isinstance(raw_roots, list):
        raise InputError("FIELD_TYPE", "reference_roots must be an array")
    reference_roots = tuple(
        _safe_path(base, item, f"/local_paths/reference_roots/{position}", directory=True)
        for position, item in enumerate(raw_roots)
    )

    semantic_intake = dict(intake)
    semantic_intake.pop("local_paths")
    for name in ("profile", "mapping", "inventory", "decisions"):
        semantic_intake[name] = {"semantic_digest": semantic_digests[name]}
    semantic_intake["catalogue"] = {"digest": catalogue_digest}
    semantic_digests["intake"] = semantic_digest(semantic_intake)
    return PlanningInputs(
        intake_path=path,
        intake=intake,
        catalogue_path=catalogue_path,
        catalogue_transport_sha256=catalogue_sha,
        catalogue_digest=catalogue_digest,
        profile=documents["profile"],
        mapping=documents["mapping"],
        inventory=documents["inventory"],
        decisions=documents["decisions"],
        semantic_digests=semantic_digests,
        input_paths=(path, catalogue_path, *document_paths),
        reference_roots=reference_roots,
        output_root=output_root,
    )
