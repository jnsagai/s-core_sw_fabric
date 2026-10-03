"""Transfer container source snapshots without extracting runtime Git metadata."""

from __future__ import annotations

import posixpath
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import BinaryIO

MAX_ARCHIVE_BYTES = 512 * 1024**2
MAX_MEMBERS = 50000


def extract_workspace_archive(stream: BinaryIO, destination: Path) -> None:
    """Extract into empty disposable storage, keeping source bytes and file modes."""
    if not destination.is_dir() or any(p.is_symlink() for p in (destination, *destination.parents)):
        raise ValueError("Snapshot destination must be a real directory")
    if any(destination.iterdir()):
        raise ValueError("Snapshot destination must be empty")
    members = 0
    total = 0
    seen: set[str] = set()

    def filtered(member: tarfile.TarInfo, path: str) -> tarfile.TarInfo | None:
        nonlocal members, total
        members += 1
        total += member.size
        if members > MAX_MEMBERS or total > MAX_ARCHIVE_BYTES:
            raise ValueError("Container source snapshot exceeds its size allowance")
        name = PurePosixPath(member.name)
        if name.is_absolute() or ".." in name.parts:
            raise ValueError("Unsafe container snapshot path")
        if name.parts and name.parts[0] == ".git":
            return None
        if member.islnk() or member.issym():
            base = name.parent if member.issym() else PurePosixPath(".")
            target = PurePosixPath(posixpath.normpath(str(base / member.linkname)))
            if target.parts and target.parts[0] == ".git":
                raise ValueError("Snapshot link refers to excluded runtime Git metadata")
        if str(name) in seen and not member.isdir():
            raise ValueError("Duplicate container snapshot path")
        seen.add(str(name))
        safe = tarfile.data_filter(member, path)
        # Metadata times are outside our source identity. Avoid setting timestamps
        # on read-only files: fuse2fs can reject that even for the file's owner.
        return safe.replace(
            mode=member.mode & 0o777 if member.isreg() or member.islnk() else safe.mode,
            mtime=None,  # type: ignore[arg-type]  # Python 3.12 supports skipping timestamps.
        )

    with tarfile.open(fileobj=stream, mode="r|", errorlevel=2) as archive:
        archive.extractall(destination, filter=filtered)


def snapshot_workspace(container: str, destination: Path) -> None:
    """Ask Docker for an archive; extraction stays on the selected host filesystem."""
    if not re.fullmatch(r"[0-9a-f]{12,64}", container):
        raise ValueError("Invalid container identity for workspace snapshot")
    # The surrounding snapshot verifies run ownership, image and disconnected
    # networking first. No additional container or network access is introduced.
    with tempfile.TemporaryFile(dir=destination.parent) as archive:
        result = subprocess.run(
            ["/usr/bin/docker", "cp", container + ":/workspace/.", "-"],
            stdout=archive,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
        if result.returncode:
            raise ValueError("Docker workspace export failed: " + result.stderr.decode()[:4096])
        if archive.tell() > MAX_ARCHIVE_BYTES:
            raise ValueError("Container source archive exceeds its size allowance")
        archive.seek(0)
        try:
            extract_workspace_archive(archive, destination)
        except tarfile.TarError as error:
            raise ValueError("Docker workspace archive rejected: " + str(error)) from error
