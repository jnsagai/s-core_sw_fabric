"""Portable historical run records and their offline verification without Fabro."""

from __future__ import annotations

import base64
import binascii
import hashlib
import re
from typing import Any

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.runtime.client import FabroClient
from score_sw_fabric.runtime.inspect import TERMINAL_STATUSES, inspect_run, lifecycle_conflict
from score_sw_fabric.runtime.models import MAX_BLOB_BYTES, MAX_EXPORTED_BYTES, validate_export
from score_sw_fabric.runtime.projection import project_version
from score_sw_fabric.runtime.request import parse_json, parse_yaml

SOURCE_PACKAGE_ID = "source:package"
SOURCE_PROFILE_ID = "source:compiler-profile"
BLOB_KEY = re.compile(r"(?:.*_)?blob")
SHA256 = re.compile(r"[0-9a-f]{64}")
OUTPUT_PAGE = 1_000_000
FIXED_LIMITATIONS = [
    "Fabro events, outputs and answers are runtime_observation; they are not 005 receipts or "
    "human decisions.",
    "Native run status is not engineering readiness; engineering_readiness is not_evaluated.",
    "Production 005 trust root, collector, decision, role, policy and time services are "
    "unavailable (005 T009 pending).",
]


def blob_references(value: Any) -> set[str]:
    """Collect native content-addressed references named `blob` or `*_blob`."""
    found: set[str] = set()
    stack: list[tuple[Any, str]] = [(value, "")]
    while stack:
        item, key = stack.pop()
        if isinstance(item, dict):
            stack.extend((child, name) for name, child in item.items())
        elif isinstance(item, list):
            stack.extend((child, key) for child in item)
        elif isinstance(item, str) and BLOB_KEY.fullmatch(key) and SHA256.fullmatch(item):
            found.add(item)
    return found


def _stage_blob_id(stage: str) -> str:
    return "stage-output:" + stage.replace("@", ":")


def _blob(identifier: str, payload: bytes, origin: str) -> dict[str, Any]:
    return {
        "id": identifier,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "base64": base64.b64encode(payload).decode("ascii"),
        "origin": origin,
    }


def _stage_output(
    client: FabroClient, run_id: str, stage: str, maximum: int
) -> tuple[bytes | None, str | None]:
    offset = 0
    collected = bytearray()
    for _ in range(1000):
        page = client.get_object(
            "output_read",
            f"/api/v1/runs/{run_id}/stages/{stage}/logs/output?offset={offset}&limit={OUTPUT_PAGE}",
        )
        encoded = page.get("bytes_base64")
        next_offset = page.get("next_offset")
        if (
            not isinstance(encoded, str)
            or type(next_offset) is not int
            or page.get("offset") != offset
            or type(page.get("eof")) is not bool
        ):
            return None, "STAGE_OUTPUT_MALFORMED"
        if page.get("cas_ref") is not None:
            return None, "STAGE_OUTPUT_CAS_REF_UNSUPPORTED"
        try:
            chunk = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error):
            return None, "STAGE_OUTPUT_MALFORMED"
        if next_offset != offset + len(chunk):
            return None, "STAGE_OUTPUT_MALFORMED"
        collected.extend(chunk)
        if len(collected) > maximum:
            return None, "STAGE_OUTPUT_LIMIT"
        offset = next_offset
        if page["eof"]:
            total = page.get("total_bytes")
            if type(total) is not int or total != len(collected):
                return None, "STAGE_OUTPUT_MALFORMED"
            return bytes(collected), None
        if not chunk:
            return None, "STAGE_OUTPUT_STALLED"
    return None, "STAGE_OUTPUT_LIMIT"


def build_export(
    client: FabroClient,
    binding: dict[str, Any],
    *,
    package_bytes: bytes,
    compiler_profile_bytes: bytes,
    assurance_references: list[dict[str, Any]],
    output_limit: int,
    max_pages: int = 100,
) -> dict[str, Any]:
    """Read one native run and seal every included byte and its declared origin."""
    package = parse_json(package_bytes, "/source_package")
    compiler_profile = parse_yaml(compiler_profile_bytes, "/compiler_profile")
    if not isinstance(package, dict) or not isinstance(compiler_profile, dict):
        raise InputError("PACKAGE_DRIFT", "Export source bytes are not records")
    projection = project_version(package, compiler_profile)
    if (
        package.get("digest") != binding["source_package_digest"]
        or projection["wire_digest"] != binding["wire_digest"]
        or binding["version_id"] != binding["wire_digest"]
    ):
        raise InputError("PACKAGE_DRIFT", "Export source differs from the run binding")
    run_id = binding["run_id"]
    if binding["creation_state"] != "run_known" or not isinstance(run_id, str):
        raise InputError("RUN_ID_UNKNOWN", "Export requires a known native run ID")
    if not {"blob_read", "output_read", "stage_list"} <= set(
        client.profile["demonstrated_capabilities"]
    ):
        raise InputError("RUNTIME_CAPABILITY_UNAVAILABLE", "Export read routes are unavailable")
    inspection = inspect_run(client, run_id, max_pages=max_pages)
    reasons = set(inspection["reason_codes"])
    blobs = [
        _blob(SOURCE_PACKAGE_ID, package_bytes, "fabric_source"),
        _blob(SOURCE_PROFILE_ID, compiler_profile_bytes, "fabric_source"),
    ]
    total = sum(item["bytes"] for item in blobs)
    for reference in sorted(
        blob_references(inspection["events"]) | blob_references(inspection["checkpoints"])
    ):
        status, payload = client.request(
            "blob_read", "GET", f"/api/v1/runs/{run_id}/blobs/{reference}"
        )
        total += len(payload)
        if status != 200 or hashlib.sha256(payload).hexdigest() != reference:
            reasons.add("BLOB_MISSING")
            continue
        if len(payload) > MAX_BLOB_BYTES or total > MAX_EXPORTED_BYTES // 2:
            raise InputError("LIMIT_EXCEEDED", "Native blob closure exceeds export limit")
        blobs.append(_blob("native-blob:" + reference, payload, "runtime_observation"))
    stages = inspection["stages"] if isinstance(inspection["stages"], list) else []
    for stage in sorted(item["id"] for item in stages):
        output, problem = _stage_output(client, run_id, stage, output_limit)
        if output is None:
            reasons.add(problem or "STAGE_OUTPUT_MALFORMED")
            continue
        total += len(output)
        if total > MAX_EXPORTED_BYTES // 2:
            raise InputError("LIMIT_EXCEEDED", "Stage output closure exceeds export limit")
        blobs.append(_blob(_stage_blob_id(stage), output, "runtime_observation"))
    references = []
    for item in sorted(assurance_references, key=lambda value: value["assessment_digest"]):
        if item.get("assurance_domain") == "production":
            raise InputError(
                "PRODUCTION_AUTHORITY_UNAVAILABLE",
                "Production 005 authority is unavailable; the reference cannot be exported",
            )
        references.append(item)
    status_record = inspection["native_summary"].get("lifecycle", {})
    answers = sum(
        1
        for item in inspection["events"]
        if isinstance(item.get("item"), dict)
        and isinstance(item["item"].get("record"), dict)
        and item["item"]["record"].get("kind") == "interview.answered"
    )
    limitations = sorted(FIXED_LIMITATIONS + sorted(reasons))
    record = seal(
        {
            "schema_version": 1,
            "kind": "runtime_export",
            "source_package": {
                "blob_id": SOURCE_PACKAGE_ID,
                "compiler_profile_blob_id": SOURCE_PROFILE_ID,
                "sha256": hashlib.sha256(package_bytes).hexdigest(),
                "digest": package["digest"],
                "entrypoint": package["entrypoint"],
            },
            "wire_projection": {
                "source_entrypoint": projection["source_entrypoint"],
                "wire_entrypoint": projection["wire_entrypoint"],
                "wire_digest": projection["wire_digest"],
                "wire_bytes": projection["wire_bytes"],
                "workflow_dependencies": {},
            },
            "runtime": {
                "profile_id": client.profile["id"],
                "profile_digest": client.profile["digest"],
                "source_commit": client.profile["source_commit"],
                "executable_sha256": client.profile["executable_sha256"],
                "source_api_sha256": client.profile["source_api_sha256"],
                "status": client.profile["status"],
            },
            "binding": binding,
            "run_summary": inspection["native_summary"],
            "status": {
                "native_status": inspection["native_status"],
                "native_reason": inspection["native_reason"],
                "native_blocked_reason": inspection["native_blocked_reason"],
                "pending_control": status_record.get("pending_control")
                if isinstance(status_record, dict)
                else None,
                "event_position": inspection["event_position"],
                "event_contract_version": inspection["event_contract_version"],
                "native_answers_observed": answers,
                "assurance_decisions": 0,
                "engineering_readiness": "not_evaluated",
            },
            "events": inspection["events"],
            "checkpoints": inspection["checkpoints"],
            "stages": stages,
            "questions": inspection["questions"],
            "blobs": sorted(blobs, key=lambda item: item["id"]),
            "assurance_references": references,
            "completeness": "complete" if not reasons else "incomplete",
            "limitations": limitations,
        }
    )
    return validate_export(record)


def verify_export(value: Any) -> dict[str, Any]:
    """Recompute every closure predicate from exported bytes, with no Fabro access."""
    record = validate_export(value)
    binding = record["binding"]
    blobs = {item["id"]: base64.b64decode(item["base64"]) for item in record["blobs"]}
    origins = {item["id"]: item["origin"] for item in record["blobs"]}
    reasons: set[str] = set()
    source = record["source_package"]
    package_bytes = blobs.get(SOURCE_PACKAGE_ID)
    profile_bytes = blobs.get(SOURCE_PROFILE_ID)
    if (
        package_bytes is None
        or profile_bytes is None
        or origins.get(SOURCE_PACKAGE_ID) != "fabric_source"
        or origins.get(SOURCE_PROFILE_ID) != "fabric_source"
        or hashlib.sha256(package_bytes).hexdigest() != source.get("sha256")
    ):
        reasons.add("EXPORT_CLOSURE_MISMATCH")
    else:
        try:
            package = parse_json(package_bytes, "/source_package")
            projection = project_version(package, parse_yaml(profile_bytes, "/compiler_profile"))
        except (InputError, KeyError, TypeError, AttributeError):
            reasons.add("EXPORT_CLOSURE_MISMATCH")
        else:
            wire = record["wire_projection"]
            if (
                package.get("digest") != binding["source_package_digest"]
                or package.get("digest") != source.get("digest")
                or projection["wire_digest"] != binding["wire_digest"]
                or projection["wire_digest"] != binding["version_id"]
                or wire.get("wire_digest") != projection["wire_digest"]
                or wire.get("wire_bytes") != projection["wire_bytes"]
                or wire.get("wire_entrypoint") != projection["wire_entrypoint"]
                or wire.get("source_entrypoint") != projection["source_entrypoint"]
            ):
                reasons.add("EXPORT_CLOSURE_MISMATCH")
    if record["runtime"].get("source_commit") != binding["runtime_commit"]:
        reasons.add("RUNTIME_IDENTITY_MISMATCH")
    run_id = binding["run_id"]
    events = record["events"]
    if run_id is None or record["run_summary"].get("id") != run_id:
        reasons.add("EXPORT_CLOSURE_MISMATCH")
    seen: set[Any] = set()
    for index, item in enumerate(events, start=1):
        if (
            item.get("stream_seq") != index
            or item.get("run_id") != run_id
            or item.get("id") in seen
        ):
            reasons.add("EVENT_GAP")
            break
        seen.add(item.get("id"))
    created = [
        item["item"]["record"]
        for item in events
        if item.get("kind") == "platform"
        and isinstance(item.get("item"), dict)
        and isinstance(item["item"].get("record"), dict)
        and item["item"]["record"].get("kind") == "run.created"
    ]
    if (
        len(created) != 1
        or not isinstance(created[0].get("spec"), dict)
        or created[0]["spec"].get("workflow_version_id") != binding["version_id"]
    ):
        reasons.add("EXPORT_CLOSURE_MISMATCH")
    status = record["status"]
    lifecycle = record["run_summary"].get("lifecycle")
    summary_status = lifecycle.get("status") if isinstance(lifecycle, dict) else None
    if (
        status.get("event_position") != len(events)
        or not isinstance(summary_status, dict)
        or status.get("native_status") != summary_status.get("kind")
        or status.get("engineering_readiness") != "not_evaluated"
        or status.get("assurance_decisions") != 0
    ):
        reasons.add("EXPORT_CLOSURE_MISMATCH")
    if lifecycle_conflict(summary_status, events):
        reasons.add("NATIVE_STATE_CONFLICT")
    expected = {SOURCE_PACKAGE_ID, SOURCE_PROFILE_ID}
    expected |= {
        "native-blob:" + item
        for item in blob_references(events) | blob_references(record["checkpoints"])
    }
    expected |= {_stage_blob_id(item.get("id", "")) for item in record["stages"]}
    missing = expected - set(blobs)
    if missing:
        reasons.add("BLOB_MISSING")
    if set(blobs) - expected:
        reasons.add("EXPORT_CLOSURE_MISMATCH")
    for identifier, payload in blobs.items():
        if identifier.startswith("native-blob:") and (
            hashlib.sha256(payload).hexdigest() != identifier.removeprefix("native-blob:")
            or origins[identifier] != "runtime_observation"
        ):
            reasons.add("EXPORT_CLOSURE_MISMATCH")
        if identifier.startswith("stage-output:") and origins[identifier] != "runtime_observation":
            reasons.add("EXPORT_CLOSURE_MISMATCH")
    for item in record["assurance_references"]:
        if item["assurance_domain"] == "production":
            reasons.add("PRODUCTION_AUTHORITY_UNAVAILABLE")
    recorded_limits = {item for item in record["limitations"] if item not in set(FIXED_LIMITATIONS)}
    if not set(FIXED_LIMITATIONS) <= set(record["limitations"]):
        reasons.add("EXPORT_CLOSURE_MISMATCH")
    mismatch = {"EXPORT_CLOSURE_MISMATCH", "RUNTIME_IDENTITY_MISMATCH"} & reasons
    # Verification never upgrades a record: an exporter's incomplete marker stays incomplete.
    closed = not (reasons | recorded_limits) and record["completeness"] == "complete"
    computed = "complete" if closed else "incomplete"
    if record["completeness"] == "complete" and computed != "complete":
        reasons.add("EXPORT_CLOSURE_MISMATCH")
    reproduced = not mismatch and "EXPORT_CLOSURE_MISMATCH" not in reasons
    if computed != "complete":
        reasons.add("EXPORT_INCOMPLETE")
    return {
        "reproduced": reproduced,
        "completeness": computed,
        "export_digest": record["digest"],
        "run_id": run_id,
        "version_id": binding["version_id"],
        "native_status": status.get("native_status"),
        "native_reason": status.get("native_reason"),
        "native_terminal": status.get("native_status") in TERMINAL_STATUSES,
        "event_count": len(events),
        "blob_count": len(blobs),
        "native_answers_observed": status.get("native_answers_observed"),
        "assurance_decisions": 0,
        "assurance_references": [
            {
                "assessment_digest": item["assessment_digest"],
                "assurance_domain": item["assurance_domain"],
                "origin": item["origin"],
                "production_eligible": False,
            }
            for item in record["assurance_references"]
        ],
        "reason_codes": sorted(reasons),
        "engineering_readiness": "not_evaluated",
    }
