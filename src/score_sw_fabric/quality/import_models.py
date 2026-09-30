"""Strict, bounded read-only native import selections and declared bindings."""

from __future__ import annotations

import hashlib
import math
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from score_sw_fabric.agents.models import input_file, local_dir, protected_roots, relative_path
from score_sw_fabric.assurance.models import (
    bounded_list,
    digest,
    exact,
    nonempty,
    seal,
    sha,
    stable_id,
    verify_digest,
    version,
)
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.models import MAX_ARTIFACT, MAX_TOTAL, Accumulator, Budget
from score_sw_fabric.quality.profile import load_profile
from score_sw_fabric.runtime.models import output_path
from score_sw_fabric.runtime.request import _local, _no_links, parse_json, parse_yaml

TOOLS = {"clang-tidy", "cppcheck", "asan", "ubsan", "codeql"}
REQUEST_FIELDS = {"profile", "baseline", "artifacts", "extraction", "origin", "protected_roots"}
BASELINE_FIELDS = {"component", "root", "files", "expected_units", "identities", "digest"}
IDENTITY_FIELDS = {
    "id",
    "name",
    "version",
    "tool_sha256",
    "config_sha256",
    "query_pack",
    "suite",
    "libraries",
    "license",
    "notice",
}
ARTIFACT_FIELDS = {"id", "tool", "format", "role", "ref", "source_root", "units", "bindings"}
MAX_ORIGINAL = 512 * 1024 * 1024


def choice(value: Any, choices: set[str], pointer: str) -> str:
    if not isinstance(value, str) or value not in choices:
        raise InputError("FIELD_ENUM", "Unsupported selection", pointer)
    return value


def strings(value: Any, pointer: str, limit: int = 1000) -> list[str]:
    items = [nonempty(x, pointer, max_length=1024) for x in bounded_list(value, limit, pointer)]
    if len(items) != len(set(items)):
        raise InputError("DUPLICATE_ID", "Duplicate selected string", pointer)
    return items


def units(value: Any, pointer: str, files: dict[str, bytes]) -> list[str]:
    names = strings(value, pointer, 500)
    for name in names:
        relative_path(name, pointer)
        if name not in files or Path(name).suffix not in {".cpp", ".cc", ".cxx"}:
            raise InputError("INPUT_PATH", "Translation unit is not a frozen C++ file", pointer)
    return names


def native_root(value: Any) -> Path:
    text = nonempty(value, "/source_root", max_length=1024)
    if (
        not text.startswith("/")
        or "\\" in text
        or "\x00" in text
        or any(p in {".", ".."} for p in text.split("/"))
        or "//" in text
    ):
        raise InputError("INPUT_PATH", "Native source root must be an absolute POSIX path")
    return Path(text)


def bounded_tree(value: Any) -> None:
    """Bound native nesting/nodes and refuse cycles or non-JSON YAML values."""
    pending = [(value, 0)]
    count = 0
    while pending:
        node, depth = pending.pop()
        count += 1
        if depth > 64 or count > 200_000:
            raise InputError("LIMIT_EXCEEDED", "Native nesting/node limit exceeded")
        if isinstance(node, dict):
            if any(not isinstance(k, str) for k in node):
                raise InputError("NATIVE_OUTPUT_INVALID", "Native object keys must be strings")
            pending.extend((v, depth + 1) for v in node.values())
        elif isinstance(node, list):
            pending.extend((v, depth + 1) for v in node)
        elif type(node) is float and not math.isfinite(node):
            raise InputError("NATIVE_OUTPUT_INVALID", "Nonfinite native number")
        elif node is not None and type(node) not in {str, int, float, bool}:
            raise InputError("NATIVE_OUTPUT_INVALID", "Non-JSON native value")


def control(path: Path, *, yaml: bool = False) -> dict[str, Any]:
    path = _no_links(path, "/control")
    try:
        details = path.stat()
        if not stat.S_ISREG(details.st_mode) or details.st_size > 1024 * 1024:
            raise InputError("LIMIT_EXCEEDED", "Control must be a regular file of at most 1 MiB")
        with path.open("rb") as stream:
            data = stream.read(1024 * 1024 + 1)
        if len(data) > 1024 * 1024:
            raise InputError("LIMIT_EXCEEDED", "Control exceeds 1 MiB")
        record = parse_yaml(data, "/control") if yaml else parse_json(data, "/control")
        bounded_tree(record)
    except (OSError, RecursionError, ValueError) as exc:
        raise InputError("INPUT_INVALID", "Cannot read bounded control") from exc
    if not isinstance(record, dict):
        raise InputError("FIELD_TYPE", "Control root must be an object")
    return record


def selected_control(
    base: Path, value: Any, *, max_bytes: int = 1024 * 1024
) -> tuple[Path, dict[str, Any]]:
    ref = exact(value, {"path", "sha256"}, "/control")
    path = _local(base, ref["path"], "/control/path")
    try:
        details = path.stat()
        if not stat.S_ISREG(details.st_mode) or details.st_size > max_bytes:
            raise InputError("LIMIT_EXCEEDED", "Selected control exceeds regular-file/byte bounds")
        with path.open("rb") as stream:
            data = stream.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise InputError("LIMIT_EXCEEDED", "Selected control grew beyond byte bounds")
        if hashlib.sha256(data).hexdigest() != sha(ref["sha256"], "/control/sha256"):
            raise InputError("INPUT_DRIFT", "Selected control bytes changed")
        record = parse_json(data, "/control")
        bounded_tree(record)
    except (OSError, RecursionError, ValueError) as exc:
        raise InputError("INPUT_INVALID", "Cannot read selected control") from exc
    if not isinstance(record, dict):
        raise InputError("FIELD_TYPE", "Selected control must be an object")
    return path, record


def identity(value: Any) -> dict[str, Any]:
    item = exact(value, IDENTITY_FIELDS, "/identities")
    choice(item["id"], TOOLS, "/identities/id")
    for key in ("name", "version", "license", "notice"):
        nonempty(item[key], "/identities/" + key, max_length=1024)
    for key in ("tool_sha256", "config_sha256"):
        sha(item[key], "/identities/" + key)
    packs = bounded_list(item["libraries"], 32, "/libraries")
    if item["query_pack"] is not None:
        packs = [*packs, item["query_pack"]]
    names = set()
    for raw in packs:
        pack = exact(raw, {"name", "version", "sha256"}, "/pack")
        name = nonempty(pack["name"], "/pack/name", max_length=1024)
        nonempty(pack["version"], "/pack/version", max_length=1024)
        sha(pack["sha256"], "/pack/sha256")
        if name in names:
            raise InputError("DUPLICATE_ID", "Duplicate pack/library identity")
        names.add(name)
    if item["suite"] is not None:
        suite = exact(item["suite"], {"name", "sha256"}, "/suite")
        nonempty(suite["name"], "/suite/name", max_length=1024)
        sha(suite["sha256"], "/suite/sha256")
    if (item["id"] == "codeql" and (item["query_pack"] is None or item["suite"] is None)) or (
        item["id"] != "codeql" and (item["query_pack"] is not None or item["suite"] is not None)
    ):
        raise InputError("TOOL_IDENTITY_MISMATCH", "Pack/suite differs from selected tool mode")
    return item


@dataclass
class ImportInputs:
    request: dict[str, Any]
    profile: dict[str, Any]
    baseline: dict[str, Any]
    files: dict[str, bytes]
    identities: dict[str, dict[str, Any]]
    artifacts: list[dict[str, Any]]
    manifest: dict[str, Any]
    inputs: list[Path]
    protected: list[Path]
    gaps: list[str]


def load_import(path: Path, out: Path | None = None) -> ImportInputs:
    r = version(control(path, yaml=True), "quality_import_request", REQUEST_FIELDS, "/request")
    base = path.absolute().parent
    choice(r["origin"], {"fixture", "imported_unverified"}, "/origin")
    protected = protected_roots(base, r["protected_roots"], "/protected_roots")
    profile_ref = exact(r["profile"], {"path", "sha256"}, "/profile")
    profile_path = _local(base, profile_ref["path"], "/profile/path")
    control(profile_path, yaml=True)
    _, profile_bytes = input_file(base, profile_ref, "/profile")
    profile = load_profile(profile_bytes)
    baseline_path, b = selected_control(base, r["baseline"])
    version(b, "quality_import_baseline", BASELINE_FIELDS, "/baseline")
    verify_digest(b, "/baseline")
    stable_id(b["component"], "/component")
    root = local_dir(baseline_path.parent, b["root"], "/root")
    protected.append(root)
    inputs = [profile_path, baseline_path]
    files: dict[str, bytes] = {}
    total = 0
    raw_files = bounded_list(b["files"], 500, "/files")
    if not raw_files:
        raise InputError("LIMIT_EXCEEDED", "Frozen source manifest must not be empty")
    for raw in raw_files:
        item = exact(raw, {"path", "sha256"}, "/files")
        name = relative_path(item["path"], "/files/path")
        if name in files:
            raise InputError("DUPLICATE_ID", "Duplicate frozen file")
        fp, data = input_file(root, item, "/files")
        total += len(data)
        if total > MAX_TOTAL:
            raise InputError("LIMIT_EXCEEDED", "Frozen source exceeds 64 MiB")
        files[name] = data
        inputs.append(fp)
    if b["expected_units"] is not None:
        units(b["expected_units"], "/expected_units", files)
    identities = {}
    for raw in bounded_list(b["identities"], 32, "/identities"):
        ident = identity(raw)
        if ident["id"] in identities:
            raise InputError("DUPLICATE_ID", "Duplicate tool identity")
        identities[ident["id"]] = ident
    if not identities:
        raise InputError("LIMIT_EXCEEDED", "At least one selected tool is required")
    source = {k: b[k] for k in ("component", "files", "expected_units")}
    selected_baseline = {
        **b,
        "root": str(root),
        "source_digest": digest(source),
        "profile": r["profile"],
        "full_digest": digest({**source, "profile": r["profile"], "identities": b["identities"]}),
    }
    manifest_path, manifest = selected_control(base, r["extraction"])
    selected_baseline["kind"] = "quality_import_baseline_snapshot"
    selected_baseline["input_digest"] = selected_baseline.pop("digest")
    selected_baseline = seal(selected_baseline)
    inputs.append(manifest_path)
    raw_artifacts = bounded_list(r["artifacts"], 500, "/artifacts")
    if not raw_artifacts:
        raise InputError("LIMIT_EXCEEDED", "At least one native artifact is required")
    artifacts = []
    seen = set()
    gaps = []
    original_total = 0
    for raw in raw_artifacts:
        a = exact(raw, ARTIFACT_FIELDS, "/artifacts")
        name = nonempty(a["id"], "/artifact/id", max_length=1024)
        if name in seen:
            raise InputError("DUPLICATE_ID", "Duplicate artifact identity")
        seen.add(name)
        tool = choice(a["tool"], set(identities), "/artifact/tool")
        choice(a["role"], {"diagnostics", "supporting", "log"}, "/artifact/role")
        fmt = choice(
            a["format"],
            {
                "clang-tidy-yaml",
                "clang-tidy-text",
                "cppcheck-xml",
                "sarif-2.1.0",
                "asan-text",
                "ubsan-text",
                "text",
            },
            "/artifact/format",
        )
        allowed = {
            "clang-tidy-yaml": "clang-tidy",
            "clang-tidy-text": "clang-tidy",
            "cppcheck-xml": "cppcheck",
            "asan-text": "asan",
            "ubsan-text": "ubsan",
        }
        if (
            (fmt in allowed and allowed[fmt] != tool)
            or (a["role"] == "diagnostics" and fmt == "text")
            or (a["role"] != "diagnostics" and fmt != "text")
        ):
            raise InputError("FIELD_ENUM", "Artifact format/role differs from selected tool")
        native_root(a["source_root"])
        units(a["units"], "/artifact/units", files)
        bindings = exact(
            a["bindings"],
            {"source_digest", "profile_sha256", "identity_digest"},
            "/artifact/bindings",
        )
        for value in bindings.values():
            sha(value, "/bindings")
        if (
            bindings["source_digest"] != selected_baseline["source_digest"]
            or bindings["profile_sha256"] != r["profile"]["sha256"]
        ):
            gaps.append("BASELINE_DRIFT")
        if bindings["identity_digest"] != digest(identities[tool]):
            gaps.append("TOOL_IDENTITY_MISMATCH")
        ref = exact(a["ref"], {"path", "sha256"}, "/artifact/ref")
        sha(ref["sha256"], "/artifact/ref/sha256")
        fp = _local(base, ref["path"], "/artifact/ref/path")
        try:
            details = fp.stat()
        except OSError as exc:
            raise InputError("INPUT_INVALID", "Native artifact unavailable") from exc
        original_total += details.st_size
        if not stat.S_ISREG(details.st_mode) or original_total > MAX_ORIGINAL:
            raise InputError("LIMIT_EXCEEDED", "Native input exceeds regular-file/512 MiB bounds")
        inputs.append(fp)
        artifacts.append({**a, "path": fp})
    if out is not None:
        output_path(out, [path, *inputs], protected)
    budget = Budget(MAX_ARTIFACT)
    original_streamed = 0
    for artifact in artifacts:
        capture = Accumulator(budget, artifact["format"])
        try:
            with artifact.pop("path").open("rb") as stream:
                while chunk := stream.read(65536):
                    original_streamed += len(chunk)
                    capture.add(chunk)
                    if original_streamed > MAX_ORIGINAL:
                        raise InputError("LIMIT_EXCEEDED", "Native stream grew beyond bounded size")
        except OSError as exc:
            raise InputError("INPUT_INVALID", "Native artifact could not be read") from exc
        raw = capture.record()
        if raw["sha256"] != artifact["ref"]["sha256"]:
            raise InputError("INPUT_DRIFT", "Selected native artifact bytes changed")
        if raw["truncated"]:
            gaps.append("OUTPUT_TRUNCATED")
        artifact["raw"] = raw
    return ImportInputs(
        r,
        profile,
        selected_baseline,
        files,
        identities,
        artifacts,
        manifest,
        inputs,
        protected,
        gaps,
    )
