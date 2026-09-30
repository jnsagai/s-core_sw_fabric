"""Resolve native docnames only through declared, confined source mounts."""

import hashlib
from pathlib import Path
from typing import Any

from score_sw_fabric.process_source.models import Manifest, SourceRef
from score_sw_fabric.process_source.reader import IntegrityError


def source_ref(
    manifest: Manifest,
    source_id: str,
    record: dict[str, Any],
    export_ref: str,
    pointer: str,
) -> SourceRef:
    source = next(s for s in manifest.sources if s.source_id == source_id)
    native_id = record.get("id")
    version = record.get("version")
    docname = record.get("docname")
    lineno = record.get("lineno")
    if docname is not None and (
        not isinstance(docname, str)
        or not docname
        or docname.startswith("/")
        or "\\" in docname
        or any(p in ("", ".", "..") for p in docname.split("/"))
    ):
        raise IntegrityError("DOCNAME_PATH", "Unsafe native docname", pointer)
    if lineno is not None and (type(lineno) is not int or lineno < 1):
        raise IntegrityError("LINE_NUMBER", "Invalid native line number", pointer)
    logical: str | None = None
    content_digest: str | None = None
    state = "external" if record.get("is_external", False) else "unavailable"
    if docname and state != "external":
        candidates: list[str] = []
        for mount in manifest.mounts:
            if mount.source_id != source_id:
                continue
            prefix = mount.docname_prefix.strip("/")
            if prefix and docname != prefix and not docname.startswith(prefix + "/"):
                continue
            suffix = docname[len(prefix) :].lstrip("/") if prefix else docname
            for extension in (".rst", ".md"):
                rel = Path(mount.path_prefix) / f"{suffix}{extension}"
                candidate = (source.root / rel).resolve()
                if not candidate.is_relative_to(source.root):
                    raise IntegrityError(
                        "SOURCE_ESCAPE", "Mounted source escapes repository", pointer
                    )
                if candidate.is_file():
                    candidates.append(rel.as_posix())
        if len(set(candidates)) > 1:
            raise IntegrityError(
                "SOURCE_AMBIGUOUS", "Docname maps to multiple source files", pointer
            )
        if candidates:
            logical, state = candidates[0], "verified"
            content_digest = hashlib.sha256((source.root / logical).read_bytes()).hexdigest()
    return SourceRef(
        source_id,
        source.repository,
        source.commit,
        native_id,
        version,
        logical,
        content_digest,
        state,
        docname,
        lineno,
        export_ref,
        pointer,
        record.get("external_url") or None,
    )
