"""Candidate installed identities retain originals and never confer authority."""

from __future__ import annotations

import base64
import copy
import hashlib
from pathlib import Path
from typing import Any

import pytest
import yaml

from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.profile import load_profile

LEGACY = Path("tests/fixtures/quality/profiles/s-core-quality-legacy-v1.yaml")


def candidate() -> dict[str, Any]:
    profile = yaml.safe_load(LEGACY.read_bytes())
    body = b"Synthetic notice; no real installation or engineering authority.\n"
    notice = {
        "path": "/fixture/LICENSE.txt",
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "base64": base64.b64encode(body).decode(),
    }
    profile["installed_context"] = {
        "origin": "fixture",
        "state": "owner_review_pending",
        "qualification": "unknown",
        "project_use_eligibility": "unknown",
        "tools": [
            {
                "toolchain": {
                    "schema_version": 1,
                    "kind": "quality_codeql_toolchain_profile",
                    "id": "fixture-codeql",
                    "status": "fixture_only",
                    "tool": {
                        "path": "/fixture/never-run-codeql",
                        "sha256": "0" * 64,
                        "version": "2.21.4",
                    },
                    "dependencies": [],
                    "library_dirs": [],
                },
                "license_notice": notice,
            }
        ],
        "codeql_pack": {
            "name": "codeql/misra-cpp-coding-standards",
            "version": "2.61.0",
            "manifest_sha256": "0" * 64,
            "metadata_sha256": "1" * 64,
            "reviewed_source_commit": "0" * 40,
            "declared_build_commit": "1" * 40,
            "locked_tree": "2" * 40,
            "build_tree": "2" * 40,
            "state": "source_trees_equal",
            "compiled_artifact_provenance": "unverified",
            "library_source_provenance": "unverified",
            "reporting_compatibility": "unexecuted",
            "observation_digest": "3" * 64,
            "license_notice": copy.deepcopy(notice),
        },
    }
    return profile


def test_candidate_context_retains_original_notices_without_host_probes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = candidate()
    with monkeypatch.context() as guard:
        guard.setattr(Path, "open", lambda *a, **k: pytest.fail("offline host read"))
        guard.setattr(Path, "stat", lambda *a, **k: pytest.fail("offline host probe"))
        loaded = load_profile(canonical(value))
    assert loaded == value
    assert loaded["mapping_state"] == "unknown" and loaded["decision_policy_ref"] is None
    assert loaded["installed_context"]["qualification"] == "unknown"


def test_legacy_profile_transport_remains_exact() -> None:
    original = LEGACY.read_bytes()
    assert (
        hashlib.sha256(original).hexdigest()
        == "720a64d14ecc193e034a45e3c68dffed27df1d23837b886268af55acd1413ec9"
    )
    assert "installed_context" not in load_profile(original)


@pytest.mark.parametrize(
    "target",
    [
        "qualification",
        "eligibility",
        "notice_hash",
        "notice_size",
        "notice_encoding",
        "notice_field",
        "duplicate_tool",
        "tool_kind",
        "pack_field",
        "pack_hash",
        "build_commit",
        "relation",
        "empty_tools",
        "context_scalar",
    ],
)
def test_malformed_or_promoted_installed_context_refuses(target: str) -> None:
    value = candidate()
    context = value["installed_context"]
    notice = context["tools"][0]["license_notice"]
    if target == "qualification":
        context["qualification"] = "qualified"
    elif target == "eligibility":
        context["project_use_eligibility"] = "eligible"
    elif target == "notice_hash":
        notice["sha256"] = "0" * 64
    elif target == "notice_size":
        notice["bytes"] += 1
    elif target == "notice_encoding":
        notice["base64"] = "!"
    elif target == "notice_field":
        notice["approved"] = True
    elif target == "duplicate_tool":
        context["tools"].append(copy.deepcopy(context["tools"][0]))
    elif target == "tool_kind":
        context["tools"][0]["toolchain"]["kind"] = []
    elif target == "pack_field":
        context["codeql_pack"]["accepted"] = True
    elif target == "pack_hash":
        context["codeql_pack"]["manifest_sha256"] = None
    elif target == "build_commit":
        context["codeql_pack"]["declared_build_commit"] = "unknown"
    elif target == "relation":
        context["codeql_pack"]["state"] = "source_trees_different"
    elif target == "empty_tools":
        context["tools"] = []
    else:
        value["installed_context"] = None
    with pytest.raises(InputError):
        load_profile(canonical(value))
