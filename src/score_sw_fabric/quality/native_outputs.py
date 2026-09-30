"""Index native Clang-Tidy diagnostics without discarding their original YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.runtime.request import parse_yaml


def diagnostics(
    data: bytes, artifact_id: str, source: Path, files: dict[str, bytes]
) -> list[dict[str, Any]]:
    record = parse_yaml(data, "/clang-tidy-yaml")
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
