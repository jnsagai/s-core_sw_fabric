"""Request builders for the synthetic increment 009 component."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/verification/telemetry_guard"
PROFILE = ROOT / "profiles/s-core-verification-v1.yaml"
TOOLCHAIN = ROOT / "profiles/cpp17-gcc11-gtest-local-v1.yaml"


def ref(path: Path) -> dict[str, str]:
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def files(root: Path, paths: list[str]) -> list[dict[str, str]]:
    return [
        {"path": path, "sha256": hashlib.sha256((root / path).read_bytes()).hexdigest()}
        for path in paths
    ]


def fixture(tmp_path: Path, *, defect: bool = False) -> Path:
    destination = tmp_path / "component"
    shutil.copytree(FIXTURE, destination)
    if defect:
        shutil.copy2(
            destination / "src-defect/telemetry_guard.cpp", destination / "src/telemetry_guard.cpp"
        )
    return destination


def request(tmp_path: Path, kind: str, **overrides: Any) -> Path:
    root = tmp_path / "component"
    common: dict[str, Any] = {
        "schema_version": 1,
        "kind": f"verification_{kind}_request",
        "profile": ref(PROFILE),
        "component": "telemetry_guard",
        "root": str(root),
        "requirements": files(root, ["docs/requirements.rst"]),
        "sources": files(root, ["src/telemetry_guard.h", "src/telemetry_guard.cpp"]),
        "protected_roots": [str(ROOT)],
    }
    if kind == "design":
        common.update(design=files(root, ["docs/detailed_design.rst"]), requirement_scope=None)
    elif kind == "run":
        common.update(
            toolchain=ref(TOOLCHAIN),
            tests=files(root, ["tests/telemetry_guard_test.cpp"]),
            include_dirs=["src"],
            coverage=True,
            timeout_seconds=30,
        )
    common.update(overrides)
    path = tmp_path / f"{kind}.json"
    path.write_text(json.dumps(common), encoding="utf-8")
    return path
