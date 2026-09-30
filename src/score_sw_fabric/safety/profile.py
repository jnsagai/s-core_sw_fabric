"""Pinned native safety-analysis profile: catalogues, field rules, checklist and gates."""

from __future__ import annotations

import re
from typing import Any

import yaml

from score_sw_fabric.agents.models import relative_path, string_list
from score_sw_fabric.assurance.models import exact, nonempty, sha, stable_id, version
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.runtime.request import parse_yaml
from score_sw_fabric.safety.native import list_table_rows

PROFILE_FIELDS = {
    "id",
    "status",
    "sources",
    "analyses",
    "requirement_directives",
    "architecture_directives",
    "mitigation_issue_pattern",
    "rules",
    "platform_allocation",
    "internal_fault_prefixes",
    "checklist",
    "gates",
    "loop",
}
ANALYSIS_FIELDS = {
    "directive",
    "work_product",
    "catalogue_field",
    "mandatory",
    "violates",
    "mitigated_by",
    "catalogue",
}
RULE_CHECKS = frozenset(
    {
        "sufficient_requires_mitigation",
        "valid_requires_mitigation",
        "open_mitigation_requires_issue",
    }
)
CATALOGUE_ID = re.compile(r"^[A-Z]{2}_[0-9]{2}_[0-9]{2}$")
LIST_TABLE = re.compile(r"^\.\. list-table:: (?P<title>.*)$")
CHECKLIST_ID = re.compile(r"^Gen [0-9]+$")


def _regex(value: Any, pointer: str) -> str:
    text = nonempty(value, pointer, max_length=512)
    try:
        re.compile(text)
    except re.error as exc:
        raise InputError("PROFILE_REGEX", f"Invalid regex at {pointer}", pointer) from exc
    return text


def validate_profile(value: Any) -> dict[str, Any]:
    profile = version(value, "safety_analysis_profile", PROFILE_FIELDS, "/safety_analysis_profile")
    stable_id(profile["id"], "/id")
    nonempty(profile["status"], "/status", max_length=64)
    sources = profile["sources"]
    if not isinstance(sources, list) or not sources or len(sources) > 32:
        raise InputError("LIMIT_EXCEEDED", "Profile sources must be bounded", "/sources")
    source_ids = set()
    for index, raw in enumerate(sources):
        pointer = f"/sources/{index}"
        source = exact(raw, {"id", "repository", "commit", "path", "sha256"}, pointer)
        source_ids.add(stable_id(source["id"], pointer + "/id"))
        nonempty(source["repository"], pointer + "/repository", max_length=512)
        if not isinstance(source["commit"], str) or not re.fullmatch(
            r"[0-9a-f]{40}", source["commit"]
        ):
            raise InputError("HASH_FORMAT", "Expected a full commit", pointer + "/commit")
        relative_path(source["path"], pointer + "/path")
        sha(source["sha256"], pointer + "/sha256")
    if len(source_ids) != len(sources):
        raise InputError("DUPLICATE_ID", "Duplicate source", "/sources")
    analyses = exact(profile["analyses"], {"fmea", "dfa"}, "/analyses")
    for name, raw in analyses.items():
        pointer = f"/analyses/{name}"
        analysis = exact(raw, ANALYSIS_FIELDS, pointer)
        for key in ("directive", "work_product", "catalogue_field"):
            stable_id(analysis[key], f"{pointer}/{key}")
        mandatory = analysis["mandatory"]
        if not isinstance(mandatory, dict) or analysis["catalogue_field"] not in mandatory:
            raise InputError(
                "PROFILE_FIELD", "Mandatory rules must include the catalogue field", pointer
            )
        for option, pattern in mandatory.items():
            _regex(pattern, f"{pointer}/mandatory/{option}")
        for key in ("violates", "mitigated_by"):
            string_list(analysis[key], f"{pointer}/{key}", limit=16, length=64)
        catalogue = analysis["catalogue"]
        if not isinstance(catalogue, list) or not catalogue or len(catalogue) > 500:
            raise InputError("LIMIT_EXCEEDED", "Catalogue must be bounded", pointer + "/catalogue")
        ids = set()
        for position, entry in enumerate(catalogue):
            item = exact(
                entry, {"id", "group", "scope", "source"}, f"{pointer}/catalogue/{position}"
            )
            if not isinstance(item["id"], str) or not CATALOGUE_ID.fullmatch(item["id"]):
                raise InputError(
                    "ID_FORMAT", "Invalid catalogue ID", f"{pointer}/catalogue/{position}"
                )
            if item["scope"] not in {"component", "platform"} or item["source"] not in source_ids:
                raise InputError("FIELD_ENUM", "Invalid catalogue scope or source", pointer)
            nonempty(item["group"], pointer, max_length=128)
            ids.add(item["id"])
        if len(ids) != len(catalogue):
            raise InputError("DUPLICATE_ID", "Duplicate catalogue ID", pointer + "/catalogue")
    for key in ("requirement_directives", "architecture_directives", "internal_fault_prefixes"):
        string_list(profile[key], f"/{key}", limit=16, length=64)
    _regex(profile["mitigation_issue_pattern"], "/mitigation_issue_pattern")
    rules = profile["rules"]
    if (
        not isinstance(rules, list)
        or {rule.get("check") for rule in rules if isinstance(rule, dict)} != RULE_CHECKS
    ):
        raise InputError("PROFILE_FIELD", "Profile must bind every native attribute rule", "/rules")
    for index, raw in enumerate(rules):
        rule = exact(raw, {"id", "check", "source"}, f"/rules/{index}")
        stable_id(rule["id"], f"/rules/{index}/id")
        if rule["source"] not in source_ids:
            raise InputError("FIELD_ENUM", "Rule source is not pinned", f"/rules/{index}")
    allocation = exact(
        profile["platform_allocation"],
        {"status", "accepted_directives", "accepted_work_products"},
        "/platform_allocation",
    )
    nonempty(allocation["status"], "/platform_allocation/status", max_length=64)
    for key in ("accepted_directives", "accepted_work_products"):
        string_list(allocation[key], f"/platform_allocation/{key}", limit=16, length=64)
    checklist = profile["checklist"]
    if not isinstance(checklist, list) or not checklist or len(checklist) > 64:
        raise InputError("LIMIT_EXCEEDED", "Checklist must be bounded", "/checklist")
    for index, raw in enumerate(checklist):
        item = exact(raw, {"id", "question", "source"}, f"/checklist/{index}")
        nonempty(item["id"], f"/checklist/{index}/id", max_length=32)
        nonempty(item["question"], f"/checklist/{index}/question", max_length=1024)
        if item["source"] not in source_ids:
            raise InputError("FIELD_ENUM", "Checklist source is not pinned", f"/checklist/{index}")
    gates = exact(profile["gates"], {"design", "closure"}, "/gates")
    if gates["design"] == gates["closure"]:
        raise InputError("PROFILE_FIELD", "Design and closure gates must differ", "/gates")
    for key in ("design", "closure"):
        stable_id(gates[key], f"/gates/{key}")
    loop = exact(profile["loop"], {"max_iterations"}, "/loop")
    if type(loop["max_iterations"]) is not int or not 1 <= loop["max_iterations"] <= 20:
        raise InputError("LIMIT_EXCEEDED", "Loop budget must be 1-20", "/loop/max_iterations")
    return profile


def load_profile(data: bytes) -> dict[str, Any]:
    return validate_profile(parse_yaml(data, "/safety_analysis_profile"))


def _tables(text: str) -> list[tuple[str, str]]:
    """Top-level list-tables of a native RST file as (title, body) pairs."""
    lines = text.splitlines()
    tables = []
    for index, line in enumerate(lines):
        match = LIST_TABLE.match(line)
        if not match:
            continue
        body = []
        for following in lines[index + 1 :]:
            if following.strip() and not following.startswith(" "):
                break
            body.append(following)
        tables.append((match.group("title").strip(), "\n".join(body)))
    return tables


def extract_catalogue(text: str) -> list[dict[str, str]]:
    """Catalogue IDs from a native guideline; `(… Platform DFA)` tables are platform scope."""
    entries = []
    for title, body in _tables(text):
        scope = "platform" if "Platform DFA" in title else "component"
        rows = list_table_rows(body, header_rows=0)
        if not rows or "ID" not in rows[0]["cells"]:
            continue
        column = rows[0]["cells"].index("ID")
        for row in rows[1:]:
            cells = row["cells"]
            if len(cells) > column and CATALOGUE_ID.fullmatch(cells[column]):
                entries.append({"id": cells[column], "group": title, "scope": scope})
    return entries


def extract_checklist(text: str) -> list[dict[str, str]]:
    for title, body in _tables(text):
        if title == "General Checklist":
            return [
                {"id": row["cells"][0], "question": row["cells"][1]}
                for row in list_table_rows(body)
                if row["cells"] and CHECKLIST_ID.fullmatch(row["cells"][0])
            ]
    return []


def extract_metamodel(text: str, directive: str) -> dict[str, Any]:
    need = yaml.safe_load(text)["needs_types"][directive]
    return {
        "mandatory": dict(need["mandatory_options"]),
        "violates": [item.strip() for item in need["mandatory_links"]["violates"].split(",")],
        "mitigated_by": [
            item.strip()
            for item in need.get("optional_links", {}).get("mitigated_by", "").split(",")
        ],
        "mitigation_issue": need["optional_options"]["mitigation_issue"],
    }
