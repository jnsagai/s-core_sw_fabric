"""Observable diagnostic failure behavior, not engineering acceptance tests."""

import json
from pathlib import Path

import pytest

from score_sw_fabric.cli import main


def test_missing_locks_block(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["doctor", "--root", str(tmp_path), "--json"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["outcome"] == "blocked"
    assert all(c["outcome"] == "blocked" for c in result["checks"])
    assert result["engineering_readiness"] == "not_evaluated"


@pytest.mark.parametrize(
    "content",
    ["schema_version: 2", "schema_version: true", "[]", "[broken", "!!python/object:x {}"],
)
def test_unsupported_or_unsafe_yaml_blocks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], content: str
) -> None:
    (tmp_path / "upstream.lock.yaml").write_text(content)
    (tmp_path / "toolchain.lock.yaml").write_text("schema_version: 1")
    assert main(["doctor", "--root", str(tmp_path), "--json"]) == 2
    assert json.loads(capsys.readouterr().out)["outcome"] == "blocked"


def test_foundation_success_cannot_claim_engineering_readiness(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for name in ("upstream.lock.yaml", "toolchain.lock.yaml"):
        (tmp_path / name).write_text("schema_version: 1")
    assert main(["doctor", "--root", str(tmp_path), "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["scope"] == "fabric_foundation_files"
    assert result["engineering_readiness"] == "not_evaluated"
    assert result["runtime_integration"] == "not_implemented"


def test_unimplemented_command_is_rejected() -> None:
    with pytest.raises(SystemExit) as error:
        main(["run"])
    assert error.value.code == 2
