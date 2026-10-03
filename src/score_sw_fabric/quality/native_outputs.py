"""Index native Clang-Tidy diagnostics without discarding their original YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from score_sw_fabric.assurance.models import nonempty
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.controls import yaml_tree


def diagnostics(
    data: bytes,
    artifact_id: str,
    source: Path,
    files: dict[str, bytes],
    *,
    include_ranges: bool = False,
) -> list[dict[str, Any]]:
    record = yaml_tree(data, "/clang-tidy-yaml", max_bytes=16 * 1024 * 1024)
    if not isinstance(record, dict) or not isinstance(record.get("Diagnostics"), list):
        raise InputError("NATIVE_OUTPUT_INVALID", "Missing native Diagnostics list")
    raw = record["Diagnostics"]
    if len(raw) > 10000:
        raise InputError("LIMIT_EXCEEDED", "Too many native diagnostics")
    findings = []
    for index, d in enumerate(raw):
        if (
            not isinstance(d, dict)
            or not isinstance(d.get("DiagnosticName"), str)
            or not isinstance(d.get("DiagnosticMessage"), dict)
        ):
            raise InputError("NATIVE_OUTPUT_INVALID", "Malformed native diagnostic")
        nonempty(d["DiagnosticName"], "/native_id", max_length=1024)
        if d.get("Level") is not None:
            nonempty(d["Level"], "/native_level", max_length=1024)
        locations = []
        notes = d.get("Notes", [])
        if not isinstance(notes, list) or len(notes) > 1000:
            raise InputError("NATIVE_OUTPUT_INVALID", "Malformed or excessive native notes")
        messages = [d["DiagnosticMessage"], *notes]
        for message in messages:
            if not isinstance(message, dict) or not isinstance(message.get("Message"), str):
                raise InputError("NATIVE_OUTPUT_INVALID", "Malformed native message")
            path = message.get("FilePath", "")
            offset = message.get("FileOffset", 0)
            if not isinstance(path, str) or type(offset) is not int or offset < 0:
                raise InputError("NATIVE_OUTPUT_INVALID", "Malformed native location")
            relative = None
            if path:
                candidate = Path(path)
                candidate = candidate if candidate.is_absolute() else source / candidate
                if not candidate.is_relative_to(source):
                    raise InputError(
                        "NATIVE_LOCATION_UNRESOLVED", "Diagnostic is outside selected source"
                    )
                relative = str(candidate.relative_to(source))
                if relative not in files or offset > len(files[relative]):
                    raise InputError(
                        "NATIVE_LOCATION_UNRESOLVED", "Diagnostic has an unselected location"
                    )
            locations.append(
                {"path": relative, "byte_offset": offset, "message": message["Message"]}
            )
            if include_ranges:
                for key, offset_key in (("Ranges", "FileOffset"), ("Replacements", "Offset")):
                    items = message.get(key, [])
                    if not isinstance(items, list) or len(items) > 1000:
                        raise InputError("NATIVE_OUTPUT_INVALID", "Malformed native range/fix list")
                    for item in items:
                        if not isinstance(item, dict):
                            raise InputError("NATIVE_OUTPUT_INVALID", "Malformed native range/fix")
                        path = item.get("FilePath")
                        start, length = item.get(offset_key), item.get("Length")
                        if (
                            not isinstance(path, str)
                            or not path
                            or type(start) is not int
                            or type(length) is not int
                            or start < 0
                            or length < 0
                        ):
                            raise InputError(
                                "NATIVE_OUTPUT_INVALID", "Malformed native range coordinates"
                            )
                        candidate = Path(path)
                        candidate = candidate if candidate.is_absolute() else source / candidate
                        if not candidate.is_relative_to(source):
                            raise InputError(
                                "NATIVE_LOCATION_UNRESOLVED", "External native range/fix"
                            )
                        relative = str(candidate.relative_to(source))
                        if relative not in files or start + length > len(files[relative]):
                            raise InputError(
                                "NATIVE_LOCATION_UNRESOLVED", "Range exceeds frozen bytes"
                            )
                        locations.append(
                            {
                                "path": relative,
                                "byte_offset": start,
                                "byte_length": length,
                                "kind": key,
                            }
                        )
        if len(locations) > 1000:
            raise InputError("LIMIT_EXCEEDED", "Too many aggregate native diagnostic locations")
        findings.append(
            {
                "native_id": d["DiagnosticName"],
                "native_level": d.get("Level"),
                "artifact_id": artifact_id,
                "result_index": index,
                "locations": locations,
                "native_record": d,
            }
        )
    return findings


def normalize(
    findings: list[dict[str, Any]], baseline_digest: str, identities: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Group equal native observations; fingerprints never erase distinct contributors."""
    from score_sw_fabric.assurance.models import digest

    grouped: dict[str, dict[str, Any]] = {}
    for finding in findings:
        tool = finding["tool"]
        native = finding["native_record"]
        message = finding.get("message")
        if message is None:
            if tool == "clang-tidy":
                message = native["DiagnosticMessage"]["Message"]
            elif tool == "cppcheck":
                message = native["attributes"]["msg"]
            else:
                message = native["message"]
        locations = []
        for location in finding["locations"]:
            # Host-specific original paths/attributes remain in the native contributor.
            locations.append(
                {k: v for k, v in location.items() if k not in {"native_path", "native_attributes"}}
            )
        key = {
            "tool": tool,
            "identity_digest": digest(identities[tool]),
            "baseline_digest": baseline_digest,
            "native_id": finding["native_id"],
            "native_level": finding["native_level"],
            "message": message,
            "locations": locations,
            "run_index": finding.get("run_index", 0),
            "rule_component": finding.get("rule_component", {}),
            "native_kind": finding.get("native_kind"),
        }
        identifier = "finding_" + digest(key)
        contributor = {k: v for k, v in finding.items() if k != "tool"}
        contributor.setdefault("run_index", 0)
        contributor.setdefault("fingerprints", {})
        contributor.setdefault("suppressions", [])
        if identifier not in grouped:
            grouped[identifier] = {**key, "id": identifier, "contributors": []}
        grouped[identifier]["contributors"].append(contributor)
    return [grouped[k] for k in sorted(grouped)]
