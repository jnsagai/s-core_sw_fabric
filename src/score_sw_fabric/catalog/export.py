"""Canonical, content-addressed catalogue output."""

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from score_sw_fabric.process_source.models import Manifest
from score_sw_fabric.process_source.reader import InputError


def canonical(value: Any) -> bytes:
    return (
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        )
        + "\n"
    ).encode("utf-8")


def seal(payload: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    digest = hashlib.sha256(canonical(payload)).hexdigest()
    catalogue = {**payload, "digest": digest}
    return catalogue, canonical(catalogue)


def write_catalogue(path: Path, data: bytes, manifest: Manifest, manifest_path: Path) -> None:
    base = manifest_path.resolve().parent
    target = (Path.cwd() / path).absolute()
    if not target.resolve().is_relative_to(base) or target == manifest_path.resolve():
        raise InputError(
            "OUTPUT_PATH", "Output must be beneath manifest root and separate from inputs"
        )
    if target.is_symlink() or any(
        parent.is_symlink()
        for parent in target.parents
        if parent != base and parent.is_relative_to(base)
    ):
        raise InputError("OUTPUT_SYMLINK", "Output path may not traverse a symlink")
    if any(target.resolve().is_relative_to(source.root) for source in manifest.sources):
        raise InputError("OUTPUT_SOURCE_ROOT", "Output may not modify a declared source tree")
    inputs = {
        manifest_path.resolve(),
        manifest.metamodel.path,
        manifest.metamodel_schema.path,
        *(e.path for e in manifest.exports),
    }
    if target.resolve() in inputs or (
        target.exists() and any(os.path.samefile(target, source) for source in inputs)
    ):
        raise InputError("OUTPUT_ALIAS", "Output aliases an input file")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".catalogue-", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    except OSError as exc:
        raise InputError("OUTPUT_IO", str(exc)) from exc
