"""Container snapshots preserve source while excluding runtime Git metadata."""

from __future__ import annotations

import io
import os
import tarfile
from pathlib import Path

import pytest

from score_sw_fabric.workspace_transfer import extract_workspace_archive


def archive(members: list[tarfile.TarInfo]) -> io.BytesIO:
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w") as tar:
        for member in members:
            member.uid = member.gid = 0
            tar.addfile(member, io.BytesIO(b"source bytes"[: member.size]))
    data.seek(0)
    return data


def unit(name: str, *, mode: int = 0o644) -> tarfile.TarInfo:
    member = tarfile.TarInfo(name)
    member.size = 12
    member.mode = mode
    return member


def test_snapshot_preserves_source_modes_not_runtime_git(tmp_path: Path) -> None:
    git = unit("./.git/objects/aa/object", mode=0o444)
    cpp = unit("./score/check.cpp")
    script = unit("./tools/check", mode=0o755)
    extract_workspace_archive(archive([git, cpp, script]), tmp_path)
    assert not (tmp_path / ".git").exists()
    assert (tmp_path / "score/check.cpp").read_bytes() == b"source bytes"
    assert (tmp_path / "tools/check").stat().st_mode & 0o777 == 0o755
    assert (tmp_path / "score/check.cpp").stat().st_uid == os.getuid()


@pytest.mark.parametrize("name", ["../escape", "/absolute", "score/../../escape"])
def test_snapshot_refuses_unsafe_archive_paths(name: str, tmp_path: Path) -> None:
    with pytest.raises((ValueError, tarfile.FilterError)):
        extract_workspace_archive(archive([unit(name)]), tmp_path)


@pytest.mark.parametrize("target", ["/outside", "../../outside", ".git/objects/private"])
def test_snapshot_refuses_links_outside_source_or_into_excluded_git(
    target: str, tmp_path: Path
) -> None:
    member = tarfile.TarInfo("linked")
    member.type = tarfile.SYMTYPE
    member.linkname = target
    with pytest.raises((ValueError, tarfile.FilterError)):
        extract_workspace_archive(archive([member]), tmp_path)


def test_snapshot_preserves_safe_relative_symlink(tmp_path: Path) -> None:
    link = tarfile.TarInfo("score/alias.cpp")
    link.type = tarfile.SYMTYPE
    link.linkname = "check.cpp"
    extract_workspace_archive(archive([unit("score/check.cpp"), link]), tmp_path)
    assert (tmp_path / "score/alias.cpp").is_symlink()
    assert (tmp_path / "score/alias.cpp").read_bytes() == b"source bytes"


def test_snapshot_refuses_existing_destination_files(tmp_path: Path) -> None:
    (tmp_path / "keep").write_text("user file")
    with pytest.raises(ValueError, match="empty"):
        extract_workspace_archive(archive([unit("keep")]), tmp_path)
    assert (tmp_path / "keep").read_text() == "user file"


def test_snapshot_rejects_special_files(tmp_path: Path) -> None:
    member = tarfile.TarInfo("device")
    member.type = tarfile.CHRTYPE
    with pytest.raises(tarfile.FilterError):
        extract_workspace_archive(archive([member]), tmp_path)
