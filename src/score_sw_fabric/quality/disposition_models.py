"""Bounded, sealed proposal subjects; metadata and self-digests grant no authority."""

from __future__ import annotations

import base64
import binascii
import re
from datetime import UTC, datetime
from typing import Any

from score_sw_fabric.agents.models import relative_path
from score_sw_fabric.assurance.models import (
    bounded_list,
    digest,
    exact,
    nonempty,
    sha,
    stable_id,
    verify_digest,
    version,
)
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.import_models import choice, identity, strings
from score_sw_fabric.quality.models import MAX_ARTIFACT
from score_sw_fabric.quality.models import digest as byte_digest

MAX_RECORD = 96 * 1024 * 1024
KINDS = {"correction", "false_positive", "deviation", "recategorization", "suppression"}
STATES = {"open", "pending_review", "corrected", "stale", "blocked"}
REQUEST_FIELDS = {"origin", "draft", "current", "previous", "action", "protected_roots"}
DRAFT_FIELDS = {
    "id",
    "requested_kind",
    "origin_digest",
    "finding_index",
    "construct",
    "scope",
    "native_category",
    "rationale",
    "impact",
    "alternatives",
    "compensating_evidence",
    "expires_at",
    "review_triggers",
    "native_metadata",
    "decision_refs",
    "digest",
}
REVIEW_FIELDS = {
    "draft",
    "subject",
    "current_baseline",
    "fresh_run",
    "previous",
    "revision",
    "observed_at",
    "time_basis",
    "state",
    "reasons",
    "outcome",
    "origin",
    "assurance_eligibility",
    "engineering_readiness",
    "limitations",
    "digest",
}
RUN_FIELDS = {
    "profile",
    "toolchain",
    "configuration",
    "capability",
    "phases",
    "artifacts",
    "gaps",
    "outcome",
    "origin",
    "assurance_eligibility",
    "engineering_readiness",
    "baseline",
    "processed_units",
    "diagnostics",
    "source_integrity",
    "digest",
}
IMPORT_FIELDS = {
    "profile",
    "baseline",
    "identities",
    "artifacts",
    "findings",
    "extraction",
    "gaps",
    "outcome",
    "origin",
    "assurance_eligibility",
    "engineering_readiness",
    "limitations",
    "digest",
}
SOURCE_FIELDS = {
    "files",
    "translation_units",
    "expected_units",
    "include_dirs",
    "defines",
    "language",
}
BASELINE_FIELDS = SOURCE_FIELDS | {
    "component",
    "source_digest",
    "profile",
    "toolchain",
    "configuration",
    "full_digest",
}


def ref(value: Any, pointer: str) -> dict[str, Any]:
    item = exact(value, {"path", "sha256"}, pointer)
    nonempty(item["path"], pointer + "/path", max_length=1024)
    sha(item["sha256"], pointer + "/sha256")
    return item


def timestamp(value: Any, pointer: str) -> datetime:
    text = nonempty(value, pointer, max_length=64)
    if (
        re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
            r"(?:\.[0-9]+)?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])",
            text,
        )
        is None
    ):
        raise InputError("TIME_FORMAT", "Expected RFC 3339 timestamp", pointer)
    try:
        moment = datetime.fromisoformat(text)
    except ValueError as exc:
        raise InputError("TIME_FORMAT", "Expected ISO 8601 timestamp", pointer) from exc
    if moment.tzinfo is None:
        raise InputError("TIME_FORMAT", "Timestamp must include timezone", pointer)
    return moment.astimezone(UTC)


def files(value: Any) -> dict[str, str]:
    result = {}
    for raw in bounded_list(value, 500, "/files"):
        item = ref(raw, "/files")
        name = relative_path(item["path"], "/files/path")
        if name in result:
            raise InputError("DUPLICATE_ID", "Duplicate frozen file")
        result[name] = item["sha256"]
    if not result:
        raise InputError("LIMIT_EXCEEDED", "Frozen files are empty")
    return result


def baseline(value: Any) -> dict[str, Any]:
    b = exact(value, BASELINE_FIELDS, "/baseline")
    stable_id(b["component"], "/baseline/component")
    names = files(b["files"])
    for key, limit in (("translation_units", 500), ("include_dirs", 32), ("defines", 64)):
        strings(b[key], "/baseline/" + key, limit)
    for name in b["translation_units"]:
        relative_path(name, "/translation_units")
        if name not in names:
            raise InputError("INPUT_PATH", "Unit outside frozen baseline")
    if b["expected_units"] is not None:
        strings(b["expected_units"], "/expected_units", 500)
        if any(name not in names for name in b["expected_units"]):
            raise InputError("INPUT_PATH", "Expected unit outside frozen baseline")
    choice(b["language"], {"c++17"}, "/language")
    for key in ("profile", "toolchain", "configuration"):
        ref(b[key], "/baseline/" + key)
    sha(b["source_digest"], "/source_digest")
    sha(b["full_digest"], "/full_digest")
    if digest({k: b[k] for k in SOURCE_FIELDS}) != b["source_digest"]:
        raise InputError("SEMANTIC_DIGEST", "Frozen source digest differs")
    verify_digest(b, "/baseline", field="full_digest")
    return b


def _raw(value: Any) -> None:
    """Check retained original bytes; truncation never proves the unseen remainder."""
    r = exact(
        value,
        {
            "format",
            "bytes",
            "sha256",
            "retained_sha256",
            "base64",
            "truncated",
        },
        "/raw",
    )
    nonempty(r["format"], "/raw/format", max_length=64)
    sha(r["sha256"], "/raw/sha256")
    sha(r["retained_sha256"], "/raw/retained_sha256")
    if (
        type(r["bytes"]) is not int
        or r["bytes"] < 0
        or type(r["truncated"]) is not bool
        or not isinstance(r["base64"], str)
        or len(r["base64"]) > 22369624
    ):
        raise InputError("FIELD_TYPE", "Malformed native byte metadata")
    try:
        retained = base64.b64decode(r["base64"], validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InputError("NATIVE_OUTPUT_INVALID", "Invalid retained native encoding") from exc
    if len(retained) > MAX_ARTIFACT or len(retained) > r["bytes"]:
        raise InputError("LIMIT_EXCEEDED", "Native retained/original byte bounds differ")
    if byte_digest(retained) != r["retained_sha256"] or (
        not r["truncated"] and (len(retained) != r["bytes"] or r["sha256"] != r["retained_sha256"])
    ):
        raise InputError("INPUT_DRIFT", "Retained native bytes differ")


def _local_outputs(record: dict[str, Any]) -> set[str]:
    capability = exact(record["capability"], {"state", "checks", "effective_config"}, "/capability")
    choice(
        capability["state"],
        {"available", "unavailable", "unsupported", "unknown"},
        "/capability/state",
    )
    strings(capability["checks"], "/capability/checks", 10000)
    if capability["effective_config"] is not None and not isinstance(
        capability["effective_config"], (str, dict)
    ):
        raise InputError("FIELD_TYPE", "Effective config must be native text/object")
    artifact_ids = set()
    for artifact in bounded_list(record["artifacts"], 500, "/artifacts"):
        exact(
            artifact,
            {
                "format",
                "bytes",
                "sha256",
                "retained_sha256",
                "base64",
                "truncated",
                "id",
                "translation_unit",
            },
            "/artifact",
        )
        name = nonempty(artifact["id"], "/artifact/id", max_length=1024)
        if name in artifact_ids:
            raise InputError("DUPLICATE_ID", "Duplicate native artifact")
        artifact_ids.add(name)
        if artifact["translation_unit"] is not None:
            relative_path(artifact["translation_unit"], "/artifact/translation_unit")
        elif record["kind"] not in {"quality_asan_analysis_run", "quality_ubsan_analysis_run"}:
            raise InputError("FIELD_TYPE", "Static analyzer artifact requires a unit")
        _raw({k: v for k, v in artifact.items() if k not in {"id", "translation_unit"}})
    for phase in bounded_list(record["phases"], 2000, "/phases"):
        exact(
            phase,
            {
                "name",
                "argv",
                "stdout",
                "stderr",
                "elapsed_seconds",
                "error",
                "exit_code",
                "timed_out",
            },
            "/phase",
        )
        nonempty(phase["name"], "/phase/name", max_length=1024)
        for argument in bounded_list(phase["argv"], 512, "/phase/argv"):
            nonempty(argument, "/phase/argv", max_length=4096)
        if (
            type(phase["timed_out"]) is not bool
            or (phase["exit_code"] is not None and type(phase["exit_code"]) is not int)
            or type(phase["elapsed_seconds"]) not in {int, float}
            or phase["elapsed_seconds"] < 0
        ):
            raise InputError("FIELD_TYPE", "Malformed native phase status")
        if phase["error"] is not None:
            nonempty(phase["error"], "/phase/error", max_length=4096)
        _raw(phase["stdout"])
        _raw(phase["stderr"])
    return artifact_ids


def origin(value: Any) -> tuple[dict[str, Any], list[dict[str, Any]], str | None]:
    """Historical output is a bounded declaration, never authenticated execution."""
    if not isinstance(value, dict):
        raise InputError("FIELD_TYPE", "Origin record must be an object")
    kind = value.get("kind")
    kinds = {
        "quality_analysis_run": "clang-tidy",
        "quality_cppcheck_analysis_run": "cppcheck",
        "quality_asan_analysis_run": "asan",
        "quality_ubsan_analysis_run": "ubsan",
    }
    if kind == "quality_native_import":
        record = version(value, kind, IMPORT_FIELDS, "/origin")
        b = record["baseline"]
        version(
            b,
            "quality_import_baseline_snapshot",
            {
                "component",
                "root",
                "files",
                "expected_units",
                "identities",
                "input_digest",
                "source_digest",
                "profile",
                "full_digest",
                "digest",
            },
            "/baseline",
        )
        verify_digest(b, "/baseline")
        stable_id(b["component"], "/component")
        files(b["files"])
        if b["expected_units"] is not None:
            strings(b["expected_units"], "/expected_units", 500)
        for key in ("input_digest", "source_digest", "full_digest"):
            sha(b[key], "/" + key)
        ref(b["profile"], "/profile")
        identities = bounded_list(record["identities"], 32, "/identities")
        for item in identities:
            identity(item)
        if identities != b["identities"]:
            raise InputError("TOOL_IDENTITY_MISMATCH", "Imported identity closure differs")
        source = {k: b[k] for k in ("component", "files", "expected_units")}
        if (
            digest(source) != b["source_digest"]
            or digest(
                {
                    **source,
                    "profile": b["profile"],
                    "identities": identities,
                }
            )
            != b["full_digest"]
        ):
            raise InputError("SEMANTIC_DIGEST", "Imported baseline closure differs")
        choice(record["origin"], {"fixture", "imported_unverified"}, "/origin")
        findings = bounded_list(record["findings"], 10000, "/findings")
        adapter = None
    elif isinstance(kind, str) and kind in kinds:
        record = version(value, kind, RUN_FIELDS | {"extraction"}, "/origin")
        baseline(record["baseline"])
        choice(record["origin"], {"local_unprotected_execution"}, "/origin")
        findings = bounded_list(record["diagnostics"], 10000, "/diagnostics")
        adapter = kinds[kind]
        artifact_ids = _local_outputs(record)
    else:
        raise InputError("KIND_MISMATCH", "Unsupported origin report")
    verify_digest(record, "/origin")
    choice(record["assurance_eligibility"], {"not_eligible"}, "/assurance_eligibility")
    choice(record["engineering_readiness"], {"not_evaluated"}, "/engineering_readiness")
    choice(
        record["outcome"],
        {"completed", "findings", "incomplete", "unavailable", "failed"},
        "/outcome",
    )
    strings(record["gaps"], "/gaps")
    if not isinstance(record["extraction"], dict):
        raise InputError("FIELD_TYPE", "Extraction must be an object")
    for finding in findings:
        if not isinstance(finding, dict):
            raise InputError("FIELD_TYPE", "Native finding must be an object")
        nonempty(finding.get("native_id"), "/native_id", max_length=1024)
        for location in bounded_list(finding.get("locations"), 1000, "/locations"):
            if not isinstance(location, dict):
                raise InputError("FIELD_TYPE", "Native location must be an object")
        if adapter is not None and not isinstance(finding.get("native_record"), dict):
            raise InputError("FIELD_TYPE", "Original native record is missing")
        if adapter is not None:
            exact(
                finding,
                {
                    "native_id",
                    "native_level",
                    "artifact_id",
                    "result_index",
                    "locations",
                    "native_record",
                },
                "/diagnostic",
            )
            nonempty(finding["artifact_id"], "/artifact_id", max_length=1024)
            if type(finding["result_index"]) is not int or finding["result_index"] < 0:
                raise InputError("FIELD_TYPE", "Native result index must be a nonnegative integer")
            if finding["native_level"] is not None:
                nonempty(finding["native_level"], "/native_level", max_length=1024)
            if finding["artifact_id"] not in artifact_ids:
                raise InputError(
                    "NATIVE_LOCATION_UNRESOLVED", "Original native artifact is missing"
                )
        for location in finding["locations"]:
            if location.get("path") is not None:
                relative_path(location["path"], "/location/path")
            for key in ("byte_offset", "byte_length", "line", "column"):
                if key in location and (type(location[key]) is not int or location[key] < 0):
                    raise InputError(
                        "FIELD_TYPE", "Native coordinate must be a nonnegative integer"
                    )
    return record, findings, adapter


def draft(value: Any, record: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    d = version(value, "quality_disposition_draft", DRAFT_FIELDS, "/draft")
    verify_digest(d, "/draft")
    stable_id(d["id"], "/draft/id")
    choice(d["requested_kind"], KINDS, "/requested_kind")
    if sha(d["origin_digest"], "/origin_digest") != record["digest"]:
        raise InputError("DISPOSITION_SUBJECT_MISMATCH", "Draft origin differs")
    index = d["finding_index"]
    if type(index) is not int or not 0 <= index < len(findings):
        raise InputError("FIELD_TYPE", "Finding index is outside origin report")
    construct = exact(d["construct"], {"kind", "path", "sha256"}, "/construct")
    choice(construct["kind"], {"file"}, "/construct/kind")
    path = relative_path(construct["path"], "/construct/path")
    names = files(record["baseline"]["files"])
    if sha(construct["sha256"], "/construct/sha256") != names.get(path):
        raise InputError(
            "DISPOSITION_SUBJECT_MISMATCH", "Tracked construct differs from frozen file"
        )
    locations = findings[index]["locations"]
    paths = {loc.get("path") for loc in locations if isinstance(loc.get("path"), str)}
    # SARIF imports retain physical locations nested in their native representation.
    for loc in locations:
        physical = loc.get("physical")
        if isinstance(physical, dict) and isinstance(physical.get("path"), str):
            paths.add(physical["path"])
    if path not in paths:
        raise InputError("DISPOSITION_SUBJECT_MISMATCH", "Tracked construct has no native location")
    scope = exact(d["scope"], {"component", "translation_units"}, "/scope")
    stable_id(scope["component"], "/scope/component")
    selected = strings(scope["translation_units"], "/scope/translation_units", 500)
    expected = record["baseline"]["expected_units"]
    if (
        scope["component"] != record["baseline"]["component"]
        or expected is None
        or set(selected) != set(expected)
    ):
        raise InputError("DISPOSITION_SUBJECT_MISMATCH", "Draft scope differs from origin")
    if d["native_category"] is not None:
        nonempty(d["native_category"], "/native_category", max_length=1024)
    nonempty(d["rationale"], "/rationale")
    impact = exact(d["impact"], {"safety", "security"}, "/impact")
    for key in impact:
        nonempty(impact[key], "/impact/" + key)
    for key in ("alternatives", "review_triggers"):
        strings(d[key], "/" + key, 64)
    for key, limit in (("compensating_evidence", 32), ("decision_refs", 20)):
        items = bounded_list(d[key], limit, "/" + key)
        for item in items:
            ref(item, "/" + key)
        if len({(x["path"], x["sha256"]) for x in items}) != len(items):
            raise InputError("DUPLICATE_ID", "Duplicate proposal reference")
    if d["expires_at"] is not None:
        timestamp(d["expires_at"], "/expires_at")
    if not isinstance(d["native_metadata"], dict):
        raise InputError("FIELD_TYPE", "Native metadata must be an object")
    return d


def previous(
    value: Any, selected_draft: dict[str, Any], subject: dict[str, Any], *, max_revision: int = 999
) -> dict[str, Any]:
    p = version(value, "quality_disposition_review", REVIEW_FIELDS, "/previous")
    verify_digest(p, "/previous")
    if p["draft"] != selected_draft or p["subject"] != subject:
        raise InputError(
            "DISPOSITION_SUBJECT_MISMATCH", "Previous review belongs to another subject"
        )
    choice(p["state"], STATES, "/previous/state")
    choice(p["outcome"], {"completed", "unresolved"}, "/previous/outcome")
    for key, allowed in (
        ("origin", {"local_unprotected_execution"}),
        ("time_basis", {"local_untrusted"}),
        ("assurance_eligibility", {"not_eligible"}),
        ("engineering_readiness", {"not_evaluated"}),
    ):
        choice(p[key], allowed, "/previous/" + key)
    if type(p["revision"]) is not int or not 1 <= p["revision"] <= max_revision:
        raise InputError("LIMIT_EXCEEDED", "Linked review revision limit exceeded")
    timestamp(p["observed_at"], "/previous/observed_at")
    baseline(p["current_baseline"])
    strings(p["reasons"], "/previous/reasons")
    strings(p["limitations"], "/previous/limitations", 32)
    if p["previous"] is not None:
        item = exact(p["previous"], {"ref", "digest", "state"}, "/previous/previous")
        ref(item["ref"], "/previous/previous/ref")
        sha(item["digest"], "/previous/previous/digest")
        choice(item["state"], STATES, "/previous/previous/state")
    if p["fresh_run"] is not None:
        origin(p["fresh_run"])
    return p
