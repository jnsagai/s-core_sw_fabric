"""Validated input contracts for native catalogue exports."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Source:
    source_id: str
    repository: str
    commit: str
    root: Path  # Operational location, excluded from semantic catalogue hashes.


@dataclass(frozen=True)
class Export:
    source_id: str
    path: Path
    logical_path: str
    sha256: str
    version: str
    relation_owners: dict[str, str]


@dataclass(frozen=True)
class Metamodel:
    source_id: str
    path: Path
    logical_path: str
    sha256: str


@dataclass(frozen=True)
class Mount:
    source_id: str
    docname_prefix: str
    path_prefix: str


@dataclass(frozen=True)
class Manifest:
    sources: tuple[Source, ...]
    exports: tuple[Export, ...]
    metamodel: Metamodel
    metamodel_schema: Metamodel
    mounts: tuple[Mount, ...]
    semantic: dict[str, Any]


@dataclass(frozen=True)
class SourceRef:
    source_id: str
    repository: str
    commit: str
    native_id: str | None
    native_version: int | None
    path: str | None
    content_digest: str | None
    location_state: str
    docname: str | None
    lineno: int | None
    export_ref: str | None
    pointer: str
    rendered_url: str | None
