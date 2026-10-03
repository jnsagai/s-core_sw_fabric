"""Original candidate installation metadata; no selection, eligibility or authority."""

from __future__ import annotations

import base64
import binascii
import hashlib
import re
from typing import Any

from score_sw_fabric.assurance.models import bounded_list, exact, sha
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.import_models import choice, native_root

FIELDS = {"origin", "state", "qualification", "project_use_eligibility", "tools", "codeql_pack"}
PACK_FIELDS = {
    "name",
    "version",
    "manifest_sha256",
    "metadata_sha256",
    "reviewed_source_commit",
    "declared_build_commit",
    "locked_tree",
    "build_tree",
    "state",
    "compiled_artifact_provenance",
    "library_source_provenance",
    "reporting_compatibility",
    "observation_digest",
    "license_notice",
}


def _notice(value: Any) -> None:
    row = exact(value, {"path", "bytes", "sha256", "base64"}, "/installed_context/notice")
    native_root(row["path"])
    expected = sha(row["sha256"], "/installed_context/notice/sha256")
    if (
        type(row["bytes"]) is not int
        or not 0 <= row["bytes"] <= 1024 * 1024
        or not isinstance(row["base64"], str)
        or len(row["base64"]) > 1398104
    ):
        raise InputError("LIMIT_EXCEEDED", "Original installed notice exceeds its bound")
    try:
        data = base64.b64decode(row["base64"], validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InputError("NATIVE_OUTPUT_INVALID", "Malformed original installed notice") from exc
    if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != expected:
        raise InputError("INPUT_DRIFT", "Original installed notice bytes differ")


def validate(value: Any) -> None:
    """Pure validation of candidate snapshots, including full original notice bytes."""
    from score_sw_fabric.quality.profile import load_toolchain

    row = exact(value, FIELDS, "/installed_context")
    choice(row["origin"], {"local_unprotected_observation", "fixture"}, "/installed_context/origin")
    for key, expected in (
        ("state", "owner_review_pending"),
        ("qualification", "unknown"),
        ("project_use_eligibility", "unknown"),
    ):
        if row[key] != expected:
            raise InputError("PROFILE_UNSUPPORTED", "Installed snapshots cannot confer authority")
    tools = bounded_list(row["tools"], 32, "/installed_context/tools")
    if not tools:
        raise InputError("FIELD_TYPE", "Installed candidate snapshots require a tool identity")
    identifiers = set()
    for tool in tools:
        exact(tool, {"toolchain", "license_notice"}, "/installed_context/tool")
        chain = tool["toolchain"]
        if not isinstance(chain, dict):
            raise InputError("FIELD_TYPE", "Candidate toolchain must be a mapping")
        kind = choice(
            chain.get("kind"),
            {
                "quality_toolchain_profile",
                "quality_cppcheck_toolchain_profile",
                "quality_sanitizer_toolchain_profile",
                "quality_codeql_toolchain_profile",
            },
            "/installed_context/toolchain/kind",
        )
        load_toolchain(canonical(chain), kind, check_paths=False)
        if chain["id"] in identifiers:
            raise InputError("DUPLICATE_ID", "Duplicate installed candidate toolchain")
        identifiers.add(chain["id"])
        _notice(tool["license_notice"])
    pack = exact(row["codeql_pack"], PACK_FIELDS, "/installed_context/codeql_pack")
    if pack["name"] != "codeql/misra-cpp-coding-standards" or pack["version"] != "2.61.0":
        raise InputError("PROFILE_UNSUPPORTED", "Installed pack identity differs from the baseline")
    for key in ("manifest_sha256", "metadata_sha256", "observation_digest"):
        sha(pack[key], "/installed_context/codeql_pack/" + key)
    for key in ("reviewed_source_commit", "declared_build_commit", "locked_tree", "build_tree"):
        if pack[key] is None and key in {"locked_tree", "build_tree"}:
            continue
        if not isinstance(pack[key], str) or re.fullmatch(r"[a-f0-9]{40}", pack[key]) is None:
            raise InputError("HASH_FORMAT", "Installed source/build Git identity must be full")
    state = choice(
        pack["state"],
        {"source_trees_equal", "source_trees_different", "unknown"},
        "/installed_context/codeql_pack/state",
    )
    if state != "unknown" and (
        pack["locked_tree"] is None
        or pack["build_tree"] is None
        or (pack["locked_tree"] == pack["build_tree"]) != (state == "source_trees_equal")
    ):
        raise InputError("PROFILE_UNSUPPORTED", "Installed source/build tree relation differs")
    for key, expected in (
        ("compiled_artifact_provenance", "unverified"),
        ("library_source_provenance", "unverified"),
        ("reporting_compatibility", "unexecuted"),
    ):
        if pack[key] != expected:
            raise InputError(
                "PROFILE_UNSUPPORTED", "Installed source observations remain unqualified"
            )
    _notice(pack["license_notice"])
