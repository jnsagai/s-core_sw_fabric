"""Strict quality decision controls; declared policy status grants no authority."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from score_sw_fabric.agents.models import input_file, relative_path
from score_sw_fabric.assurance.models import (
    bounded_list,
    exact,
    nonempty,
    scope,
    stable_id,
    verify_digest,
    version,
)
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality import disposition_models as dm
from score_sw_fabric.quality.import_models import TOOLS, choice, selected_control, strings
from score_sw_fabric.runtime.request import _local

COMMON_FIELDS = {"review", "disposition_request", "policy", "protected_roots"}
DECISION_FIELDS = COMMON_FIELDS | {"decisions", "assurance_domain", "as_of"}
POLICY_FIELDS = {
    "id",
    "assurance_domain",
    "status",
    "source_ref",
    "source_path",
    "source_prefix",
    "binding_path",
    "scope",
    "gate_id",
    "obligation_ids",
    "required_role",
    "rules",
    "digest",
}
ALLOWED_KINDS = dm.KINDS - {"correction"}


def logical(value: Any, pointer: str) -> str:
    name = relative_path(value, pointer)
    if any(char in name for char in "*?[]"):
        raise InputError("INPUT_PATH", "Policy paths cannot contain wildcards", pointer)
    return name


def policy(base: Path, ref: Any) -> tuple[dict[str, Any] | None, list[Path]]:
    if ref is None:
        return None, []
    path, p = selected_control(base, ref)
    version(p, "quality_disposition_policy", POLICY_FIELDS, "/policy")
    verify_digest(p, "/policy")
    stable_id(p["id"], "/policy/id")
    domain = choice(p["assurance_domain"], {"fixture_contract", "production"}, "/policy/domain")
    choice(
        p["status"],
        {"fixture_only"}
        if domain == "fixture_contract"
        else {"pending_production_review", "reviewed"},
        "/policy/status",
    )
    declared_scope = scope(p["scope"], "/policy/scope")
    if declared_scope["kind"] != "component":
        raise InputError("FIELD_ENUM", "Disposition policy requires component scope")
    for key in ("gate_id", "required_role"):
        nonempty(p[key], "/policy/" + key, max_length=256)
    if not strings(p["obligation_ids"], "/policy/obligation_ids", 20):
        raise InputError("FIELD_TYPE", "Policy must declare obligations")
    for key in ("source_path", "source_prefix", "binding_path"):
        logical(p[key], "/policy/" + key)
    prefix = p["source_prefix"] + "/"
    if (
        p["source_path"] == p["binding_path"]
        or any(
            p[key] == p["source_prefix"] or p[key].startswith(prefix)
            for key in ("source_path", "binding_path")
        )
        or any(
            p["source_prefix"].startswith(p[key] + "/") for key in ("source_path", "binding_path")
        )
        or p["source_path"].startswith(p["binding_path"] + "/")
        or p["binding_path"].startswith(p["source_path"] + "/")
    ):
        raise InputError("INPUT_PATH", "Policy closure paths overlap")
    seen = set()
    for raw in bounded_list(p["rules"], 1000, "/policy/rules"):
        row = exact(
            raw,
            {"tool", "native_id", "category", "permission", "allowed_kinds", "scope"},
            "/policy/rule",
        )
        choice(row["tool"], TOOLS, "/policy/rule/tool")
        nonempty(row["native_id"], "/policy/rule/native_id", max_length=1024)
        if row["category"] is not None:
            nonempty(row["category"], "/policy/rule/category", max_length=1024)
        choice(row["permission"], {"allowed", "prohibited", "unknown"}, "/policy/rule/permission")
        for kind in strings(row["allowed_kinds"], "/policy/rule/allowed_kinds", 4):
            choice(kind, ALLOWED_KINDS, "/policy/rule/kind")
        rule_scope = exact(
            row["scope"], {"component", "translation_units", "files"}, "/policy/rule/scope"
        )
        stable_id(rule_scope["component"], "/policy/rule/component")
        for key in ("translation_units", "files"):
            for name in strings(rule_scope[key], "/policy/rule/" + key, 500):
                logical(name, "/policy/rule/" + key)
        identity = canonical({key: row[key] for key in ("tool", "native_id", "category", "scope")})
        if identity in seen:
            raise InputError("DUPLICATE_ID", "Duplicate policy rule identity")
        seen.add(identity)
    source_ref = dm.ref(p["source_ref"], "/policy/source_ref")
    source_path = _local(path.parent, source_ref["path"], "/policy/source_ref/path")
    try:
        if not source_path.is_file() or source_path.stat().st_size > 1024 * 1024:
            raise InputError("LIMIT_EXCEEDED", "Policy source exceeds regular-file/1 MiB bounds")
    except OSError as exc:
        raise InputError("INPUT_INVALID", "Policy source unavailable") from exc
    source_path, data = input_file(path.parent, source_ref, "/policy/source_ref")
    if len(data) > 1024 * 1024:
        raise InputError("LIMIT_EXCEEDED", "Policy source grew beyond 1 MiB")
    return p, [path, source_path]


def permission(p: dict[str, Any] | None, review: dict[str, Any], adapter: str) -> list[str]:
    draft = review["draft"]
    if draft["requested_kind"] == "correction":
        return ["FRESH_ANALYSIS_REQUIRED"]
    if p is None:
        return ["DEVIATION_POLICY_UNKNOWN"]
    if draft["native_category"] is None:
        return ["DEVIATION_POLICY_UNKNOWN"]
    if p["scope"]["id"] != draft["scope"]["component"]:
        return ["DEVIATION_SCOPE_MISMATCH"]
    matches = [
        row
        for row in p["rules"]
        if row["tool"] == adapter
        and row["native_id"] == review["subject"]["finding"]["native_id"]
        and row["category"] == draft["native_category"]
    ]
    scoped = [
        row
        for row in matches
        if row["scope"]["component"] == draft["scope"]["component"]
        and set(row["scope"]["translation_units"]) == set(draft["scope"]["translation_units"])
        and row["scope"]["files"] == [draft["construct"]["path"]]
    ]
    if not scoped:
        return ["DEVIATION_SCOPE_MISMATCH" if matches else "DEVIATION_POLICY_UNKNOWN"]
    if any(row["permission"] == "prohibited" for row in scoped):
        return ["DEVIATION_POLICY_PROHIBITED"]
    if len(scoped) != 1 or scoped[0]["permission"] != "allowed":
        return ["DEVIATION_POLICY_UNKNOWN"]
    if draft["requested_kind"] not in scoped[0]["allowed_kinds"]:
        return ["DEVIATION_POLICY_PROHIBITED"]
    return []
