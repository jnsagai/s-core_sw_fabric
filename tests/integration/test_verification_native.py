"""Re-derive 009 rule and policy facts from pinned, read-only native checkouts."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

from score_sw_fabric.verification.profile import (
    extract_checklist,
    extract_policy,
    extract_tags,
    extract_values,
    load_profile,
    load_toolchain,
)
from tests.verification_support import PROFILE, TOOLCHAIN

SOURCES = {
    "https://github.com/eclipse-score/process_description": "SCORE_PROCESS_DESCRIPTION_SOURCE",
    "https://github.com/eclipse-score/module_template": "SCORE_MODULE_TEMPLATE_SOURCE",
    "https://github.com/eclipse-score/docs-as-code": "SCORE_DOCS_AS_CODE_SOURCE",
    "https://github.com/eclipse-score/score_cpp_policies": "SCORE_CPP_POLICIES_SOURCE",
}
pytestmark = pytest.mark.skipif(
    not all(os.environ.get(name) for name in SOURCES.values()),
    reason="native checkouts are selected by SCORE_*_SOURCE variables",
)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def test_profile_rederives_from_pinned_sources() -> None:
    profile = load_profile(PROFILE.read_bytes())
    toolchain = load_toolchain(TOOLCHAIN.read_bytes())
    roots = {repository: Path(os.environ[name]) for repository, name in SOURCES.items()}
    before = {
        repository: (_git(root, "rev-parse", "HEAD"), _git(root, "status", "--porcelain"))
        for repository, root in roots.items()
    }
    text = {}
    for source in [*profile["sources"], {"id": "policy", **toolchain["policy"]["source"]}]:
        root = roots[source["repository"]]
        assert before[source["repository"]][0] == source["commit"]
        data = (root / source["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == source["sha256"]
        text[source["id"]] = data.decode()
    assert extract_values(text["verification_process_reqs"], "TestType") == profile["test_types"]
    assert (
        extract_values(text["verification_process_reqs"], "DerivationTechnique")
        == profile["derivation_techniques"]
    )
    assert extract_tags(text["source_code_link_parser"]) == profile["source_tags"]
    assert extract_checklist(text["implementation_inspection_checklist"]) == [
        {"id": item["id"], "criterion": item["criterion"]}
        for item in profile["inspection_checklist"]
    ]
    assert (
        extract_policy(text["policy"], toolchain["policy"]["selected_levels"])
        == toolchain["policy"]["flags"]
    )
    for item in profile["rules"]:
        assert f":id: {item['id']}" in text["verification_process_reqs"]
    for section in profile["design"]["sections"]:
        assert section in text["detailed_design_template"]
    assert {
        repository: (_git(root, "rev-parse", "HEAD"), _git(root, "status", "--porcelain"))
        for repository, root in roots.items()
    } == before
