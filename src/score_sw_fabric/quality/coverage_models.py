"""Explicit supplied expectations and source references; no inferred native rule set."""

from __future__ import annotations

from typing import Any

from score_sw_fabric.agents.models import relative_path
from score_sw_fabric.assurance.models import (
    bounded_list,
    exact,
    nonempty,
    sha,
    stable_id,
    verify_digest,
    version,
)
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality import disposition_models as dm
from score_sw_fabric.quality.import_models import TOOLS, choice, strings

REQUEST_FIELDS = {
    "profile",
    "baseline",
    "manifest",
    "previous_manifest",
    "analyses",
    "protected_roots",
}
MANIFEST_FIELDS = {
    "id",
    "origin",
    "scope",
    "expected_guidelines",
    "source_refs",
    "rows",
    "review_state",
    "digest",
}
SOURCE_FIELDS = {"id", "guideline_ids", "license", "notice", "native_status"}
STATES = {
    "covered",
    "findings_open",
    "pending_manual",
    "unsupported",
    "excluded_pending_review",
    "unknown",
}


def manifest(value: Any) -> dict[str, Any]:
    m = version(value, "quality_guideline_manifest", MANIFEST_FIELDS, "/manifest")
    verify_digest(m, "/manifest")
    stable_id(m["id"], "/manifest/id")
    choice(m["origin"], {"fixture", "external_unverified"}, "/manifest/origin")
    choice(m["review_state"], {"pending_human"}, "/manifest/review_state")
    scope = exact(m["scope"], {"component", "files", "translation_units"}, "/scope")
    stable_id(scope["component"], "/scope/component")
    for key in ("files", "translation_units"):
        if key == "translation_units" and scope[key] is None:
            continue
        for path in strings(scope[key], "/scope/" + key, 500):
            relative_path(path, "/scope/" + key)
    sources = {}
    for raw in bounded_list(m["source_refs"], 32, "/source_refs"):
        source = exact(raw, {"id", "ref", "license", "notice", "native_status"}, "/source_ref")
        name = stable_id(source["id"], "/source/id")
        if name in sources:
            raise InputError("DUPLICATE_ID", "Duplicate guideline source")
        for key in ("license", "notice", "native_status"):
            nonempty(source[key], "/source/" + key, max_length=1024)
        dm.ref(source["ref"], "/source/ref")
        sources[name] = source

    def refs(value: Any) -> None:
        if not set(strings(value, "/source_ids", 32)).issubset(sources):
            raise InputError("SOURCE_REF", "Guideline refers to an unselected source")

    expected = {}
    if m["expected_guidelines"] is not None:
        entries = bounded_list(m["expected_guidelines"], 1000, "/expected_guidelines")
        if not entries:
            raise InputError("FIELD_TYPE", "An empty list cannot declare a guideline denominator")
        for raw in entries:
            row = exact(
                raw,
                {"guideline_id", "native_category", "applicability", "rationale", "source_ids"},
                "/expectation",
            )
            name = nonempty(row["guideline_id"], "/guideline_id", max_length=1024)
            if name in expected:
                raise InputError("DUPLICATE_ID", "Duplicate expected guideline")
            if row["native_category"] is not None:
                nonempty(row["native_category"], "/native_category", max_length=1024)
            choice(
                row["applicability"], {"applicable", "not_applicable", "unknown"}, "/applicability"
            )
            nonempty(row["rationale"], "/rationale", max_length=4096)
            refs(row["source_ids"])
            expected[name] = row
    rows = set()
    for raw in bounded_list(m["rows"], 1000, "/rows"):
        row = exact(
            raw,
            {"guideline_id", "source_ids", "mechanisms", "expected_evidence", "manual_evidence"},
            "/row",
        )
        name = nonempty(row["guideline_id"], "/row/guideline_id", max_length=1024)
        if name in rows or (m["expected_guidelines"] is not None and name not in expected):
            raise InputError("GUIDELINE_SET", "Duplicate or undeclared mapping row")
        rows.add(name)
        refs(row["source_ids"])
        for key in ("expected_evidence", "manual_evidence"):
            strings(row[key], "/" + key, 32)
        seen = set()
        for raw in bounded_list(row["mechanisms"], 32, "/mechanisms"):
            mechanism = exact(
                raw,
                {
                    "id",
                    "kind",
                    "automation_class",
                    "tool",
                    "native_id",
                    "identity_digest",
                    "availability",
                    "enabled",
                    "limitations",
                    "source_ids",
                },
                "/mechanism",
            )
            identifier = stable_id(mechanism["id"], "/mechanism/id")
            if identifier in seen:
                raise InputError("DUPLICATE_ID", "Duplicate mechanism")
            seen.add(identifier)
            kind = choice(mechanism["kind"], {"tool", "manual", "audit", "unsupported"}, "/kind")
            automation = choice(
                mechanism["automation_class"],
                {"automatic", "partial", "manual", "audit", "unsupported"},
                "/automation",
            )
            if (kind == "tool" and automation not in {"automatic", "partial", "audit"}) or (
                kind != "tool" and automation != kind
            ):
                raise InputError("FIELD_ENUM", "Mechanism kind/automation differ")
            choice(
                mechanism["availability"], {"supported", "unsupported", "unknown"}, "/availability"
            )
            if mechanism["enabled"] is not None and type(mechanism["enabled"]) is not bool:
                raise InputError("FIELD_TYPE", "Enabled must be boolean or null")
            if kind == "tool":
                choice(mechanism["tool"], TOOLS, "/tool")
                nonempty(mechanism["native_id"], "/native_id", max_length=1024)
                sha(mechanism["identity_digest"], "/identity_digest")
            elif any(
                mechanism[k] is not None
                for k in ("tool", "native_id", "identity_digest", "enabled")
            ):
                raise InputError("FIELD_TYPE", "Non-tool mechanisms cannot assert a tool selection")
            strings(mechanism["limitations"], "/limitations", 32)
            refs(mechanism["source_ids"])
    return m
