"""Check foundation traceability, local documentation links and lock consistency."""

import json
import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    brief = (ROOT / "S_CORE_SW_FABRIC_SPEC_KIT_IMPLEMENTATION_BRIEF.md").read_text()
    index = (ROOT / "docs/backlog/requirements-index.md").read_text()
    pattern = r"^\| (FAB-\d{3}) \| (.*?) \| (\d{3}) \|"
    source_rows = re.findall(pattern, brief, re.MULTILINE)
    assert len(source_rows) == 64
    assert re.findall(pattern, index, re.MULTILINE) == source_rows
    roadmap = (ROOT / "docs/backlog/roadmap.md").read_text()
    source_roadmap = re.findall(r"^\| (\d{3}) \| `([^`]+)` \| (.*?) \|", brief, re.MULTILINE)
    assert len(source_roadmap) == 19
    for number, slug, dependencies in source_roadmap:
        row = next(line for line in roadmap.splitlines() if f"{number} {slug}" in line)
        assert f"| {dependencies} |" in row, number
    integration = json.loads((ROOT / ".specify/integration.json").read_text())
    assert integration["version"] == "1.0.12"
    assert integration["integration_settings"]["codex"]["parsed_options"]["skills"] is True
    for skill in (
        "constitution",
        "specify",
        "clarify",
        "plan",
        "checklist",
        "tasks",
        "analyze",
        "implement",
        "converge",
    ):
        assert (ROOT / f".agents/skills/speckit-{skill}/SKILL.md").is_file()
    lock = yaml.safe_load((ROOT / "upstream.lock.yaml").read_text())
    assert lock["schema_version"] == 1
    sources = lock["sources"]
    assert len({item["id"] for item in sources}) == len(sources)
    for item in sources:
        assert re.fullmatch(r"[0-9a-f]{40}", item["commit"]), item["id"]
        assert item["license"] and item["source_paths"] and item["license_path"]
        assert set(item["source_paths"]) == set(item["source_file_sha256"])
        assert all(re.fullmatch(r"[0-9a-f]{64}", h) for h in item["source_file_sha256"].values())
    tools = yaml.safe_load((ROOT / "toolchain.lock.yaml").read_text())
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert tools["python_dependencies"]["runtime"] == project["project"]["dependencies"]
    assert tools["python_dependencies"]["development"] == project["dependency-groups"]["dev"]
    assert [tools["python_dependencies"]["backend"]] == project["build-system"]["requires"]
    files = (
        [ROOT / "README.md"]
        + list((ROOT / "docs").rglob("*.md"))
        + list((ROOT / "specs").rglob("*.md"))
    )
    broken = []
    for file in files:
        for target in re.findall(r"\[[^\]]*\]\(([^)\s]+)\)", file.read_text()):
            if "://" in target or target.startswith(("#", "/", "mailto:")):
                continue
            path = target.split("#", 1)[0]
            if path and not (file.parent / path).exists():
                broken.append(f"{file.relative_to(ROOT)} -> {target}")
    assert not broken, "Broken documentation links: " + "; ".join(broken)
    print(
        "PASS: 64 unchanged FAB requirements; 19 dependency rows; "
        "Spec Kit skills; locks; local links"
    )
    print(
        "Scope: foundation consistency only; no engineering acceptance or native build validation"
    )


if __name__ == "__main__":
    main()
