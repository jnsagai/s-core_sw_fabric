"""Bind measured files; legacy imports require an already archived checksum anchor."""

from __future__ import annotations

import hashlib
import json
import tarfile
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def measured_files(out: Path) -> dict[str, str]:
    files = [p for p in out.iterdir() if p.is_file() and p.name != "result.json"]
    artifacts = out / "native-artifacts"
    if artifacts.exists():
        files.extend(p for p in artifacts.rglob("*") if p.is_file())
    return {str(p.relative_to(out)): sha(p) for p in sorted(files)}


def seal_result(out: Path, result: dict) -> None:
    result["evidence_files"] = measured_files(out)
    result["evidence_binding_origin"] = "collector_at_measurement_completion"


def verify_result(path: Path, result: dict, binding: dict | None = None) -> None:
    files = result.get("evidence_files")
    if files is None and binding:
        files = binding.get("evidence_files")
        archive = binding.get("archive_origin")
        if files is not None and not archive:
            raise ValueError("Legacy passing evidence has no archived checksum origin")
        if archive:
            if sha(Path(archive["path"])) != archive["sha256"]:
                raise ValueError("Legacy archive identity changed")
            # Re-derive the import from the archived manifest, not today's raw logs.
            original = archived_binding(Path(archive["path"]), archive["sha256"], result["check"])
            if original["path"] != str(path) or original["evidence_files"] != files:
                raise ValueError("Legacy evidence differs from archived checksum anchor")
    if files is None:
        if result.get("status") == "completed":
            raise ValueError("Passing evidence is unbound; recollect or import archived checksums")
        return  # Historical failures remain diagnostic-only, separately hash-bound on import.
    required = {
        command["label"] + suffix
        for command in result.get("commands", [])
        for suffix in (".stdout", ".stderr", ".command.json")
    }
    required.update(result.get("native_artifacts", {}))
    if not required.issubset(files):
        raise ValueError("Measured command or artifact evidence is unbound")
    for name, expected in files.items():
        original = path.parent / name
        if not original.resolve().is_relative_to(path.parent.resolve()):
            raise ValueError("Evidence path escapes measured result")
        if sha(original) != expected:
            raise ValueError("Evidence identity changed: " + name)


def archived_binding(archive: Path, expected: str, check: str) -> dict:
    if sha(archive) != expected:
        raise ValueError("Legacy archive identity changed")
    with tarfile.open(archive, "r:gz") as bundle:
        members = [
            m
            for m in bundle.getmembers()
            if m.name.rstrip("/").endswith("/review-packet.json") or m.name == "review-packet.json"
        ]
        if len(members) != 1:
            raise ValueError("Archive must contain one original review packet")
        member = members[0]
        packet = json.load(bundle.extractfile(member))
        record = packet["evidence"][check]
        prefix = member.name.removesuffix("review-packet.json")
        evidence_prefix = "evidence/" + check + "/"
        files = {}
        for name, checksum in record["portable_evidence"].items():
            raw = bundle.extractfile(prefix + name)
            if raw is None or hashlib.file_digest(raw, "sha256").hexdigest() != checksum:
                raise ValueError("Archived portable evidence identity changed")
            relative = name.removeprefix(evidence_prefix)
            if not name.startswith(evidence_prefix):
                raise ValueError("Archive evidence scope differs")
            if relative != "result.json":
                files[relative] = checksum
        original = Path(record["path"])
        if sha(original) != record["sha256"]:
            raise ValueError("Original result identity changed")
        binding = {
            "path": str(original),
            "sha256": record["sha256"],
            "evidence_files": files,
            "archive_origin": {
                "path": str(archive),
                "sha256": expected,
                "provenance": "original_portable_packet_not_retrospective_measurement",
            },
        }
        for name, checksum in files.items():
            if sha(original.parent / name) != checksum:
                raise ValueError("Evidence identity changed: " + name)
        return binding
