"""Selections for genuine local quality adapter tests."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "profiles/s-core-quality-v1.yaml"
TOOLCHAIN = ROOT / "profiles/cpp17-quality-local-v1.yaml"
CONFIG = ROOT / "profiles/native-quality/clang-tidy.yaml"


def ref(path: Path) -> dict[str, str]:
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def request(tmp_path: Path, kind: str = "run", **overrides: Any) -> Path:
    component = tmp_path / "component"
    component.mkdir(exist_ok=True)
    if not (component / "check.cpp").exists():
        shutil.copy2(ROOT / "tests/fixtures/quality/seeded/check.cpp", component / "check.cpp")
    record: dict[str, Any] = {
        "schema_version": 1,
        "kind": f"quality_{'capability' if kind == 'capabilities' else kind}_request",
        "profile": ref(PROFILE),
        "toolchain": ref(TOOLCHAIN),
        "config": ref(CONFIG),
        "timeout_seconds": 30,
        "output_limit_bytes": 1024 * 1024,
        "protected_roots": [str(ROOT)],
    }
    if kind == "run":
        record.update(
            component="seeded_quality_probe",
            root=str(component),
            files=[dict(ref(component / "check.cpp"), path="check.cpp")],
            translation_units=["check.cpp"],
            expected_units=["check.cpp"],
            include_dirs=[],
            defines=[],
        )
    record.update(overrides)
    path = tmp_path / f"{kind}-request.json"
    path.write_text(json.dumps(record))
    return path


def complementary_request(
    tmp_path: Path, adapter: str, kind: str = "run", **overrides: Any
) -> Path:
    """Exact selections for independently executed complementary modes."""
    chain_name = "cppcheck27-local-v1" if adapter == "cppcheck" else "gcc11-sanitizers-local-v1"
    config_name = (
        "cppcheck-cpp17-local-v1" if adapter == "cppcheck" else adapter + "-gcc11-local-v1"
    )
    chain = ROOT / f"profiles/{chain_name}.yaml"
    config = ROOT / f"profiles/{config_name}.yaml"
    path = request(tmp_path, kind)
    record = json.loads(path.read_text())
    record["kind"] = (
        f"quality_{adapter}_{'capability' if kind == 'capabilities' else 'run'}_request"
    )
    record["toolchain"] = ref(chain)
    record["config"] = ref(config)
    if kind == "run" and adapter != "cppcheck":
        source = tmp_path / "component/check.cpp"
        shutil.copy2(ROOT / f"tests/fixtures/quality/sanitizers/{adapter}-seeded/check.cpp", source)
        record["files"] = [dict(ref(source), path="check.cpp")]
    record.update(overrides)
    path.write_text(json.dumps(record))
    return path
