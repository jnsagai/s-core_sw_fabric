"""Native detailed-design and source-tag traceability checks."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from score_sw_fabric.agents.models import (
    READINESS,
    input_file,
    load_request,
    local_dir,
    protected_roots,
    relative_path,
    string_list,
)
from score_sw_fabric.assurance.models import exact, seal, sha, stable_id
from score_sw_fabric.process_source.reader import InputError, read_bytes
from score_sw_fabric.safety.native import PLACEHOLDER, links, read_native
from score_sw_fabric.verification.profile import load_profile

DESIGN_FIELDS = {
    "profile",
    "component",
    "root",
    "requirements",
    "design",
    "sources",
    "requirement_scope",
    "protected_roots",
}
UNDERLINE = re.compile(r"^([=\-*^~#\"'`+])\1{2,}\s*$")
TEMPLATE_MARKER = re.compile(r"\[Component Name\]")
MAX_FILES = 500


@dataclass(frozen=True)
class RootFiles:
    root: Path
    files: list[dict[str, str]]
    data: dict[str, bytes]


def root_files(
    base: Path, root_value: Any, groups: dict[str, Any]
) -> tuple[Path, dict[str, RootFiles]]:
    """Read `{path, sha256}` groups under one root, refusing links and drift."""
    root = local_dir(base, root_value, "/root")
    result = {}
    for name, value in groups.items():
        if not isinstance(value, list) or len(value) > MAX_FILES:
            raise InputError("LIMIT_EXCEEDED", f"Too many {name} files", f"/{name}")
        files = []
        data = {}
        for index, raw in enumerate(value):
            pointer = f"/{name}/{index}"
            item = exact(raw, {"path", "sha256"}, pointer)
            path = relative_path(item["path"], pointer + "/path")
            full = root / path
            for parent in (full, *full.parents):
                if parent == root:
                    break
                if parent.is_symlink():
                    raise InputError("INPUT_ALIAS", "Input path is a link", pointer)
            content = read_bytes(full)
            if hashlib.sha256(content).hexdigest() != sha(item["sha256"], pointer + "/sha256"):
                raise InputError("INPUT_DRIFT", "Input bytes changed", pointer)
            files.append({"path": path, "sha256": item["sha256"]})
            data[path] = content
        if len(data) != len(files):
            raise InputError("DUPLICATE_ID", f"Duplicate {name} file", f"/{name}")
        result[name] = RootFiles(root=root, files=files, data=data)
    return root, result


def requirement_needs(profile: dict[str, Any], files: RootFiles) -> dict[str, dict[str, Any]]:
    native = read_native(
        [(path, content, "requirements") for path, content in files.data.items()],
        set(profile["requirement_directives"]),
    )
    return native.needs


def source_tags(profile: dict[str, Any], text: str) -> list[dict[str, Any]]:
    """Native `req-Id`/`req-traceability` tags, split on commas and spaces as upstream does."""
    tags = []
    for number, line in enumerate(text.splitlines(), 1):
        for tag in profile["source_tags"]:
            index = line.find(tag)
            if index >= 0:
                for identifier in line[index + len(tag) :].replace(",", " ").split():
                    tags.append({"id": identifier.strip(), "line": number})
    return tags


def in_scope(profile: dict[str, Any], needs: dict[str, dict[str, Any]], scope: Any) -> list[str]:
    if scope is None:
        return sorted(key for key, need in needs.items() if need["type"] == "comp_req")
    selected = string_list(scope, "/requirement_scope", limit=1000, length=256)
    for index, identifier in enumerate(selected):
        if identifier not in needs:
            raise InputError(
                "SCOPE_UNRESOLVED",
                "Scoped requirement is not defined",
                f"/requirement_scope/{index}",
            )
    return sorted(set(selected))


def _sections(text: str) -> dict[str, str]:
    lines = text.splitlines()
    headings = [
        (index, lines[index].strip())
        for index in range(len(lines) - 1)
        if lines[index].strip()
        and UNDERLINE.match(lines[index + 1])
        and len(lines[index + 1].strip()) >= len(lines[index].strip())
    ]
    sections = {}
    for position, (index, title) in enumerate(headings):
        end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        sections[title] = "\n".join(lines[index + 2 : end]).strip()
    return sections


def check_design(
    profile: dict[str, Any],
    requirements: RootFiles,
    design: RootFiles,
    sources: RootFiles,
    scope: Any,
) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    def finding(code: str, subject: str, detail: str) -> None:
        findings.append({"code": code, "subject": subject, "detail": detail[:512]})

    needs = requirement_needs(profile, requirements)
    scoped = in_scope(profile, needs, scope)
    spec = profile["design"]
    design_text = "\n".join(content.decode("utf-8", "replace") for content in design.data.values())
    native = read_native(
        [(path, content, "design") for path, content in design.data.items()], set()
    )
    documents = [
        doc
        for doc in native.documents
        if spec["work_product"] in links(doc["options"].get("realizes", ""))
    ]
    if not documents:
        finding("DESIGN_MISSING", "design", f"No document realizes {spec['work_product']}")
    sections = _sections(design_text)
    for title in spec["sections"]:
        if not sections.get(title):
            finding(
                "DESIGN_SECTION_MISSING", title, "Required template section is missing or empty"
            )
    if not any(f".. {name}::" in design_text for name in spec["diagram_directives"]):
        finding(
            "DESIGN_DIAGRAM_MISSING",
            "Static Diagrams for Unit Interactions",
            "No uml or image directive",
        )
    for match in [*PLACEHOLDER.finditer(design_text), *TEMPLATE_MARKER.finditer(design_text)]:
        finding("PLACEHOLDER", "design", match.group(0))
    units = []
    implemented: dict[str, list[str]] = {identifier: [] for identifier in scoped}
    for path in sorted(sources.data):
        text = sources.data[path].decode("utf-8", "replace")
        tags = source_tags(profile, text)
        if not tags:
            finding("UNIT_UNTAGGED", path, "No native requirement tag")
        for tag in tags:
            need = needs.get(tag["id"])
            if need is None:
                finding("TAG_UNRESOLVED", path, f"line {tag['line']}: {tag['id']}")
            elif need["type"] not in profile["requirement_directives"]:
                finding("TAG_TYPE", path, f"line {tag['line']}: {tag['id']} is {need['type']}")
            elif tag["id"] in implemented and path not in implemented[tag["id"]]:
                implemented[tag["id"]].append(path)
        if path not in design_text:
            finding("UNIT_NOT_IN_DESIGN", path, "Unit is not named in the detailed design")
        units.append(
            {"path": path, "sha256": hashlib.sha256(sources.data[path]).hexdigest(), "tags": tags}
        )
    for identifier, paths in implemented.items():
        if not paths:
            finding(
                "REQUIREMENT_UNIMPLEMENTED",
                identifier,
                "No unit carries a tag for this requirement",
            )
    return {
        "design": {
            "document_id": documents[0]["id"] if documents else None,
            "work_product": spec["work_product"],
            "sections": {title: bool(sections.get(title)) for title in spec["sections"]},
        },
        "units": units,
        "requirements": [
            {
                "id": identifier,
                "type": needs[identifier]["type"],
                "implemented_by": implemented[identifier],
            }
            for identifier in scoped
        ],
        "findings": findings,
    }


def design(request_path: Path) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    record, base = load_request(request_path, "verification_design_request", DESIGN_FIELDS)
    profile_path, profile_bytes = input_file(base, record["profile"], "/profile")
    profile = load_profile(profile_bytes)
    component = stable_id(record["component"], "/component")
    root, groups = root_files(
        base,
        record["root"],
        {name: record[name] for name in ("requirements", "design", "sources")},
    )
    result = check_design(
        profile,
        groups["requirements"],
        groups["design"],
        groups["sources"],
        record["requirement_scope"],
    )
    protected = protected_roots(base, record["protected_roots"], "/protected_roots")
    output = {
        "schema_version": 1,
        "kind": "detailed_design_report",
        "profile": {"id": profile["id"], "sha256": hashlib.sha256(profile_bytes).hexdigest()},
        "component": component,
        "files": {name: group.files for name, group in groups.items()},
        **result,
        "outcome": "blocked" if result["findings"] else "complete",
        "engineering_readiness": READINESS,
        "limitations": [
            "Structural template and tag checks only; design quality needs the inspection.",
            "Tags are read as upstream does, including tags inside string literals.",
        ],
    }
    return (1 if result["findings"] else 0), seal(output), [profile_path], [*protected, root]
