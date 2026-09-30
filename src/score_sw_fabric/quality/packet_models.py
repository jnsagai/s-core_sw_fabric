"""Bounded portable originals; archive path labels never authorize filesystem access."""

from __future__ import annotations

import stat
from pathlib import Path
from typing import Any

from score_sw_fabric.assurance.models import exact, nonempty, sha
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality import disposition_models as dm
from score_sw_fabric.quality.import_models import bounded_tree, native_root
from score_sw_fabric.quality.models import MAX_ARTIFACT, MAX_TOTAL, Budget, raw_bytes
from score_sw_fabric.runtime.request import _no_links, parse_json, parse_yaml

REQUEST_FIELDS = {
    "profile",
    "coverage",
    "analyses",
    "dispositions",
    "source_snapshots",
    "notices",
    "protected_roots",
}
PACKET_FIELDS = {
    "request_path",
    "request",
    "profile",
    "coverage",
    "analyses",
    "dispositions",
    "sources",
    "notices",
    "files",
    "origins",
    "gaps",
    "questions",
    "packet_state",
    "accepted_claims",
    "outcome",
    "origin",
    "assurance_eligibility",
    "engineering_readiness",
    "limitations",
    "digest",
}
QUESTIONS = [
    {
        "id": "applicability",
        "question": "Has the complete guideline denominator and applicability been reviewed?",
        "answer": "pending_human",
    },
    {
        "id": "mapping",
        "question": (
            "Are native categories, mechanism mappings and exclusions adopted for this scope?"
        ),
        "answer": "pending_human",
    },
    {
        "id": "manual",
        "question": (
            "Have all manual, audit and partial automation obligations received authorized review?"
        ),
        "answer": "pending_human",
    },
    {
        "id": "tool-confidence",
        "question": (
            "Are tool confidence, source/build/configuration and analysis limitations accepted?"
        ),
        "answer": "pending_human",
    },
    {
        "id": "codeql-eligibility",
        "question": (
            "Is this exact CodeQL execution eligible with reconciled packs, "
            "reports and configuration?"
        ),
        "answer": "pending_human",
    },
    {
        "id": "dispositions",
        "question": (
            "Are outstanding finding dispositions and their exact scope, "
            "policy and validity reviewed?"
        ),
        "answer": "pending_human",
    },
    {
        "id": "verification-profile",
        "question": (
            "Has the prerequisite 009 verification/toolchain profile review been completed?"
        ),
        "answer": "pending_human",
    },
    {
        "id": "authority",
        "question": (
            "Are protected production evidence and authenticated human "
            "decision authority available?"
        ),
        "answer": "pending_human",
    },
]
LIMITATIONS = [
    "Portable closure and original hashes do not authenticate "
    "analyzer execution or human acceptance.",
    "Local execution, imported declarations and fixture decisions retain their distinct origins.",
    "Historical correction observations cannot be promoted to fresh or protected execution.",
    "Tool and library binaries are identities only, not redistributed or executed by this packet.",
    "Required human answers remain pending; native status and production readiness are unchanged.",
]


def label(base: Path, value: Any) -> Path:
    text = nonempty(value, "/path", max_length=1024)
    p = Path(text)
    if ".." in p.parts or "\x00" in text or "\\" in text:
        raise InputError("INPUT_PATH", "Unsafe archive path label")
    return native_root(str(p if p.is_absolute() else base / p))


class Archive:
    """Host capture or pure offline reader, with identical transport and byte checks."""

    def __init__(self, entries: list[dict[str, Any]] | None = None) -> None:
        self.offline = entries is not None
        self.entries: dict[str, dict[str, Any]] = {}
        self.used: set[str] = set()
        self.total = 0
        for entry in entries or []:
            exact(entry, {"path", "raw"}, "/files/entry")
            key = str(label(Path("/"), entry["path"]))
            if key in self.entries:
                raise InputError("DUPLICATE_ID", "Duplicate archive path")
            dm._raw(entry["raw"])
            data = raw_bytes(entry["raw"])
            if (
                len(data) > MAX_ARTIFACT
                or entry["raw"]["bytes"] > 512 * 1024 * 1024
                or entry["raw"]["format"] != "bytes"
            ):
                raise InputError("LIMIT_EXCEEDED", "Archive file exceeds 16 MiB")
            self.entries[key] = entry
            self.total += len(data)
        self._bounds()

    def _bounds(self) -> None:
        if self.total > MAX_TOTAL or len(self.entries) > 5000:
            raise InputError("LIMIT_EXCEEDED", "Archive exceeds 64 MiB/5000 files")

    def capture(self, path: Path) -> dict[str, Any]:
        key = str(label(Path("/"), str(path.absolute())))
        self.used.add(key)
        if key in self.entries:
            return self.entries[key]
        if self.offline:
            raise InputError("PACKET_CLOSURE_MISSING", "Selected original is absent from archive")
        path = _no_links(Path(key), "/archive")
        try:
            info = path.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_size > 512 * 1024 * 1024:
                raise InputError("LIMIT_EXCEEDED", "Archive input must be a bounded regular file")
            budget = Budget(MAX_ARTIFACT, min(MAX_ARTIFACT, MAX_TOTAL - self.total))
            from score_sw_fabric.quality.models import Accumulator

            capture = Accumulator(budget, "bytes")
            with path.open("rb") as stream:
                while chunk := stream.read(65536):
                    capture.add(chunk)
                    if capture.bytes > 512 * 1024 * 1024:
                        raise InputError("LIMIT_EXCEEDED", "Archive input grew beyond 512 MiB")
            entry: dict[str, Any] = {"path": key, "raw": capture.record()}
        except OSError as exc:
            raise InputError("INPUT_INVALID", "Cannot retain selected original") from exc
        self.entries[key] = entry
        self.total += len(raw_bytes(entry["raw"]))
        self._bounds()
        return entry

    def selected(self, base: Path, ref: Any) -> tuple[Path, bytes]:
        selected = dm.ref(ref, "/ref")
        path = label(base, selected["path"])
        entry = self.capture(path)
        if entry["raw"]["sha256"] != sha(selected["sha256"], "/ref/sha256"):
            raise InputError("INPUT_DRIFT", "Selected original bytes changed")
        if entry["raw"]["truncated"]:
            raise InputError("PACKET_CLOSURE_TRUNCATED", "Selected control/source is truncated")
        return path, raw_bytes(entry["raw"])

    def control(
        self, base: Path, ref: Any, *, yaml: bool = False, max_bytes: int = 1024 * 1024
    ) -> tuple[Path, dict[str, Any]]:
        path, data = self.selected(base, ref)
        if len(data) > max_bytes:
            raise InputError("LIMIT_EXCEEDED", "Selected control exceeds byte limit")
        record = parse_yaml(data, "/control") if yaml else parse_json(data, "/control")
        bounded_tree(record)
        if not isinstance(record, dict):
            raise InputError("FIELD_TYPE", "Selected control must be an object")
        return path, record

    def listing(self) -> list[dict[str, Any]]:
        return [self.entries[key] for key in sorted(self.entries)]

    def recheck(self) -> None:
        """Rehash all originals after potentially expensive replay, without changing the archive."""
        from score_sw_fabric.quality.models import file_digest

        for key, entry in self.entries.items():
            if file_digest(_no_links(Path(key), "/archive")) != entry["raw"]["sha256"]:
                raise InputError("INPUT_DRIFT", "Packet original changed during evaluation")


def bounded_record(record: dict[str, Any]) -> None:
    if len(canonical(record)) > dm.MAX_RECORD:
        raise InputError("LIMIT_EXCEEDED", "Portable quality record exceeds 96 MiB")
    bounded_tree(record)
