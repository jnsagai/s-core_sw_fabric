"""Read-only package integrity and source-regeneration drift classification."""

from __future__ import annotations

import hashlib
from typing import Any

from score_sw_fabric.compiler.diff import compare_packages
from score_sw_fabric.compiler.models import CompilerInputs
from score_sw_fabric.compiler.package import NativeValidator, compile_package, validate_package


def inspect_drift(
    selected: dict[str, Any],
    profile: dict[str, Any],
    *,
    inputs: CompilerInputs | None = None,
    native_validator: NativeValidator | None = None,
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    files = selected.get("files", {})
    records = selected.get("manifest", {}).get("file_records", [])
    if isinstance(files, dict) and isinstance(records, list):
        declared: dict[str, dict[str, Any]] = {}
        for item in records:
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                declared[item["path"]] = item
        for subject in sorted(declared.keys() - files.keys()):
            entries.append({"class": "missing_file", "subject": subject})
        for subject in sorted(files.keys() - declared.keys()):
            entries.append({"class": "undeclared_file", "subject": subject})
        for subject in sorted(declared.keys() & files.keys()):
            content = files[subject]
            actual = (
                hashlib.sha256(content.encode()).hexdigest() if isinstance(content, str) else None
            )
            if actual != declared[subject].get("sha256"):
                entries.append(
                    {
                        "class": "file_content_mismatch",
                        "subject": subject,
                        "expected": declared[subject].get("sha256"),
                        "actual": actual,
                    }
                )
    try:
        validate_package(selected, profile)
        integrity = "valid"
    except Exception as exc:
        integrity = "invalid"
        code = getattr(exc, "code", "PACKAGE_INTEGRITY")
        drift_class = "self_digest_mismatch" if code == "PACKAGE_DIGEST" else "package_integrity"
        entries.append({"class": drift_class, "subject": "package", "message": str(exc)})
    reconstructed = None
    reproducibility = "not_evaluated"
    if inputs is not None and integrity == "valid":
        validator: NativeValidator = native_validator or (
            lambda files, entrypoint, validator_profile: selected["native_validation"]
        )
        candidate = compile_package(inputs, native_validator=validator)
        reconstructed = candidate["manifest"]["package_identity"]
        semantic = compare_packages(selected, candidate, profile)
        reproducibility = "reproduced" if semantic["equivalent"] else "diverged"
        entries.extend(
            {
                "class": "source_regeneration",
                "subject": item["subject"],
                "category": item["category"],
            }
            for item in semantic["changes"]
        )
    return {
        "schema_version": 1,
        "declared_identity": selected.get("manifest", {}).get("package_identity"),
        "integrity": integrity,
        "reproducibility": reproducibility,
        "reconstructed_identity": reconstructed,
        "entries": entries,
        "clean": integrity == "valid"
        and reproducibility in {"not_evaluated", "reproduced"}
        and not entries,
    }
