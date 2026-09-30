"""Re-derive the 008 safety profile from pinned native checkouts (008-R01).

Set SCORE_PROCESS_DESCRIPTION_SOURCE, SCORE_MODULE_TEMPLATE_SOURCE and SCORE_DOCS_AS_CODE_SOURCE
to read-only checkouts at the profile's commits. The checkouts are only read.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

from score_sw_fabric.safety.native import read_native
from score_sw_fabric.safety.profile import (
    extract_catalogue,
    extract_checklist,
    extract_metamodel,
    load_profile,
)
from tests.safety_support import PROFILE

SOURCES = {
    "https://github.com/eclipse-score/process_description": "SCORE_PROCESS_DESCRIPTION_SOURCE",
    "https://github.com/eclipse-score/module_template": "SCORE_MODULE_TEMPLATE_SOURCE",
    "https://github.com/eclipse-score/docs-as-code": "SCORE_DOCS_AS_CODE_SOURCE",
}
pytestmark = pytest.mark.skipif(
    not all(os.environ.get(name) for name in SOURCES.values()),
    reason="native checkouts are selected by SCORE_*_SOURCE variables",
)


def _head(root: Path) -> tuple[str, str]:
    def git(*arguments: str) -> str:
        return subprocess.run(
            ["git", "-C", str(root), *arguments], check=True, capture_output=True, text=True
        ).stdout.strip()

    return git("rev-parse", "HEAD"), git("status", "--porcelain")


def test_profile_rederives_from_pinned_sources() -> None:
    profile = load_profile(PROFILE.read_bytes())
    roots = {repository: Path(os.environ[name]) for repository, name in SOURCES.items()}
    before = {repository: _head(root) for repository, root in roots.items()}
    text = {}
    for source in profile["sources"]:
        root = roots[source["repository"]]
        assert before[source["repository"]][0] == source["commit"]
        data = (root / source["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == source["sha256"], source["path"]
        text[source["id"]] = data.decode()
    for kind, source_id in (("fmea", "fault_models"), ("dfa", "dfa_failure_initiators")):
        expected = [
            {"id": item["id"], "group": item["group"], "scope": item["scope"]}
            for item in profile["analyses"][kind]["catalogue"]
        ]
        assert extract_catalogue(text[source_id]) == expected
        metamodel = extract_metamodel(text["metamodel"], profile["analyses"][kind]["directive"])
        assert metamodel["mandatory"] == profile["analyses"][kind]["mandatory"]
        assert metamodel["violates"] == profile["analyses"][kind]["violates"]
        assert metamodel["mitigation_issue"] == profile["mitigation_issue_pattern"]
    assert extract_checklist(text["safety_analysis_fdr_checklist"]) == [
        {"id": item["id"], "question": item["question"]} for item in profile["checklist"]
    ]
    for rule in profile["rules"]:
        assert f":id: {rule['id']}" in text["safety_analysis_process_reqs"]
    template = read_native(
        [("fmea.rst", text["component_fmea_template"].encode(), "analysis")], {"comp_saf_fmea"}
    )
    assert not [need for need in template.needs.values() if need["type"] == "comp_saf_fmea"]
    template_ids = {row["columns"]["ID"] for row in template.rows}
    catalogue = {item["id"] for item in profile["analyses"]["fmea"]["catalogue"]}
    assert template_ids == catalogue
    assert {repository: _head(root) for repository, root in roots.items()} == before
