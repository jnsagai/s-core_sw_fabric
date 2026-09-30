"""Bounded compiler request, plan, mapping, and profile loading."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
from typing import Any

from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.compiler.models import CompilerInputs, CompilerSemanticError
from score_sw_fabric.planning.reader import normalize
from score_sw_fabric.process_source.reader import InputError, read_json, read_yaml, verify_sha

REQUEST_FIELDS = {"schema_version", "inputs", "local_paths"}
INPUT_KINDS = {"plan", "execution_mapping", "compiler_profile", "validator_profile"}
INPUT_REF_FIELDS = {"path", "sha256", "semantic_digest"}
LOCAL_FIELDS = {"output_root", "protected_roots"}
SHA = set("0123456789abcdef")


def _exact(value: Any, fields: set[str], pointer: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        actual = set(value) if isinstance(value, dict) else set()
        raise InputError(
            "COMPILER_FIELDS",
            f"{pointer}: unexpected={sorted(actual - fields)}, missing={sorted(fields - actual)}",
            pointer,
        )
    return value


def _version(value: dict[str, Any], pointer: str) -> None:
    if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise InputError("COMPILER_VERSION", f"Supported schema_version is 1 at {pointer}")


def _sha(value: Any, pointer: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in SHA for character in value)
    ):
        raise InputError("SHA256_FORMAT", f"Invalid SHA-256 at {pointer}", pointer)
    return value


def semantic_digest(value: dict[str, Any]) -> str:
    unsigned = dict(value)
    unsigned.pop("digest", None)
    return hashlib.sha256(canonical(normalize(unsigned))).hexdigest()


def verify_self_digest(value: dict[str, Any], pointer: str) -> str:
    digest = _sha(value.get("digest"), pointer + "/digest")
    actual = semantic_digest(value)
    if digest != actual:
        raise InputError("SEMANTIC_DIGEST", f"Self-digest mismatch at {pointer}", pointer)
    return digest


def _relative_file(base: Path, raw: Any, pointer: str) -> Path:
    if not isinstance(raw, str) or not raw or "\\" in raw:
        raise InputError("PATH_ESCAPE", f"Unsafe path at {pointer}", pointer)
    logical = PurePosixPath(raw)
    if logical.is_absolute() or any(part in ("", ".", "..") for part in logical.parts):
        raise InputError("PATH_ESCAPE", f"Unsafe path at {pointer}: {raw}", pointer)
    candidate = base / Path(*logical.parts)
    if candidate.is_symlink() or any(
        parent.is_symlink() for parent in candidate.parents if parent.is_relative_to(base)
    ):
        raise InputError("SYMLINK_ESCAPE", f"Input path traverses a symlink at {pointer}", pointer)
    path = candidate.resolve()
    if not path.is_relative_to(base.resolve()) or not path.is_file():
        raise InputError("INPUT_UNAVAILABLE", f"Missing or escaping input at {pointer}", pointer)
    return path


def _relative_directory(base: Path, raw: Any, pointer: str) -> Path:
    if not isinstance(raw, str) or not raw or "\\" in raw:
        raise InputError("PATH_ESCAPE", f"Unsafe directory at {pointer}", pointer)
    logical = PurePosixPath(raw)
    if logical.is_absolute() or any(part in ("", ".", "..") for part in logical.parts):
        raise InputError("PATH_ESCAPE", f"Unsafe directory at {pointer}", pointer)
    candidate = base / Path(*logical.parts)
    if candidate.is_symlink() or any(
        parent.is_symlink() for parent in candidate.parents if parent.is_relative_to(base)
    ):
        raise InputError("OUTPUT_SYMLINK", f"Directory traverses a symlink at {pointer}", pointer)
    path = candidate.resolve()
    if not path.is_relative_to(base.resolve()):
        raise InputError("PATH_ESCAPE", f"Directory escapes request root at {pointer}", pointer)
    if path.exists() and not path.is_dir():
        raise InputError("INPUT_NOT_DIRECTORY", f"Expected directory at {pointer}", pointer)
    return path


def _load_selected(base: Path, name: str, raw: Any) -> tuple[Path, dict[str, Any], str]:
    reference = _exact(raw, INPUT_REF_FIELDS, f"/inputs/{name}")
    path = _relative_file(base, reference["path"], f"/inputs/{name}/path")
    verify_sha(path, _sha(reference["sha256"], f"/inputs/{name}/sha256"), f"/inputs/{name}")
    value = read_json(path) if name == "plan" else read_yaml(path)
    _version(value, f"/inputs/{name}")
    if name == "plan":
        selected = verify_self_digest(value, f"/inputs/{name}")
    else:
        selected = verify_self_digest(value, f"/inputs/{name}")
    expected = _sha(reference["semantic_digest"], f"/inputs/{name}/semantic_digest")
    if selected != expected:
        raise InputError("SELECTED_DIGEST", f"Selected semantic digest mismatch for {name}")
    return path, value, selected


def validate_mapping_rule_count(rules: Any) -> list[Any]:
    if not isinstance(rules, list) or not rules or len(rules) > 50_000:
        raise InputError("MAPPING_RULE_LIMIT", "Execution mapping requires 1..50,000 rules")
    return rules


def _validate_plan(plan: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "plan_kind",
        "planning_status",
        "closure_complete",
        "engineering_readiness",
        "target_namespace",
        "change",
        "semantic_inputs",
        "scopes",
        "coverage",
        "instances",
        "findings",
        "digest",
    }
    if set(plan) != required:
        raise InputError("PLAN_FIELDS", "Unsupported sealed 002 plan shape")
    if plan["plan_kind"] != "draft" or plan["engineering_readiness"] != "not_evaluated":
        raise InputError("PLAN_IDENTITY", "Expected a sealed 002 draft with unevaluated readiness")
    if plan["planning_status"] != "complete" or plan["closure_complete"] is not True:
        raise CompilerSemanticError("PLAN_BLOCKED", "Only complete sealed plan closure can compile")
    if plan["findings"]:
        raise CompilerSemanticError(
            "PLAN_FINDINGS", "Plan findings must be resolved before compile"
        )
    instances = plan["instances"]
    if not isinstance(instances, list) or len(instances) > 10_000:
        raise InputError("PLAN_INSTANCE_LIMIT", "Plan exceeds 10,000 instances")
    identifiers: set[str] = set()
    edges = 0
    for index, instance in enumerate(instances):
        if not isinstance(instance, dict) or not isinstance(instance.get("instance_id"), str):
            raise InputError("PLAN_INSTANCE", f"Invalid plan instance at /instances/{index}")
        identifier = instance["instance_id"]
        if identifier in identifiers:
            raise InputError("PLAN_INSTANCE", f"Duplicate plan instance {identifier}")
        identifiers.add(identifier)
        if instance.get("applicability") != "required" or instance.get("effective_disposition") in (
            None,
            "unresolved",
        ):
            raise CompilerSemanticError(
                "PLAN_UNRESOLVED", f"Plan instance {identifier} is not executable"
            )
        dependencies = instance.get("dependency_ids")
        if not isinstance(dependencies, list):
            raise InputError("PLAN_DEPENDENCY", f"Invalid dependencies for {identifier}")
        edges += len(dependencies)
    if edges > 100_000:
        raise InputError("PLAN_DEPENDENCY_LIMIT", "Plan exceeds 100,000 dependency edges")
    dangling = sorted(
        dependency
        for instance in instances
        for dependency in instance["dependency_ids"]
        if dependency not in identifiers
    )
    if dangling:
        raise CompilerSemanticError("PLAN_DANGLING", f"Dangling plan dependencies: {dangling}")


def load_compiler_inputs(path: Path) -> CompilerInputs:
    """Load and verify a strict local compilation request and selected documents."""

    try:
        request_path = path.resolve(strict=True)
    except OSError as exc:
        raise InputError("INPUT_UNAVAILABLE", str(exc)) from exc
    request = _exact(read_yaml(request_path), REQUEST_FIELDS, "/")
    _version(request, "/")
    refs = _exact(request["inputs"], INPUT_KINDS, "/inputs")
    base = request_path.parent
    paths: list[Path] = []
    documents: dict[str, dict[str, Any]] = {}
    digests: dict[str, str] = {}
    for name in sorted(INPUT_KINDS):
        selected_path, value, digest = _load_selected(base, name, refs[name])
        paths.append(selected_path)
        documents[name] = value
        digests[name] = digest
    _validate_plan(documents["plan"])
    compiler_profile = _exact(
        documents["compiler_profile"],
        {
            "schema_version",
            "id",
            "version",
            "canonicalization",
            "semantic_rules",
            "allowed_actions",
            "allowed_native_types",
            "model_capabilities",
            "limits",
            "digest",
        },
        "/inputs/compiler_profile",
    )
    validator_profile = _exact(
        documents["validator_profile"],
        {
            "schema_version",
            "id",
            "version",
            "source_commit",
            "source_hashes",
            "license",
            "command",
            "timeout_seconds",
            "executable_sha256",
            "digest",
        },
        "/inputs/validator_profile",
    )
    if (
        compiler_profile["canonicalization"] != "canonical-json-v1"
        or compiler_profile["semantic_rules"] != "s-core-workflow-v1"
    ):
        raise InputError("COMPILER_PROFILE", "Unsupported compiler profile semantics")
    if validator_profile["command"] != "validate" or validator_profile["license"] != "MIT":
        raise InputError("VALIDATOR_PROFILE", "Unsupported validator profile contract")
    mapping = _exact(
        documents["execution_mapping"],
        {
            "schema_version",
            "id",
            "version",
            "plan_version",
            "compiler_profile",
            "review",
            "rules",
            "edges",
            "loop_policies",
            "fan_groups",
            "support_files",
            "digest",
        },
        "/inputs/execution_mapping",
    )
    if mapping["plan_version"] != 1 or mapping["compiler_profile"] != compiler_profile["id"]:
        raise InputError(
            "PROFILE_COMPATIBILITY", "Mapping does not select the plan/compiler profile"
        )
    validate_mapping_rule_count(mapping.get("rules"))
    review = mapping.get("review")
    if not isinstance(review, dict) or set(review) != {"state", "reference"}:
        raise InputError("MAPPING_REVIEW", "Mapping review record is required")
    if review["state"] != "reviewed" or not isinstance(review["reference"], dict):
        raise CompilerSemanticError("MAPPING_UNREVIEWED", "Execution mapping is not reviewed")
    local = _exact(request["local_paths"], LOCAL_FIELDS, "/local_paths")
    output_root = _relative_directory(base, local["output_root"], "/local_paths/output_root")
    raw_roots = local["protected_roots"]
    if not isinstance(raw_roots, list):
        raise InputError("FIELD_TYPE", "protected_roots must be an array")
    protected = tuple(
        _relative_directory(base, item, f"/local_paths/protected_roots/{index}")
        for index, item in enumerate(raw_roots)
    )
    all_inputs = (request_path, *paths)
    folded = [str(item).casefold() for item in all_inputs]
    if len(folded) != len(set(folded)):
        raise InputError("INPUT_CASE_COLLISION", "Selected input paths collide by case")
    for index, left in enumerate(all_inputs):
        for right in all_inputs[index + 1 :]:
            if os.path.samefile(left, right):
                raise InputError("INPUT_ALIAS", "Selected inputs alias the same file")
    if any(output_root == root or output_root.is_relative_to(root) for root in protected):
        raise InputError("OUTPUT_SOURCE_ROOT", "Output root overlaps a protected root")
    return CompilerInputs(
        request_path=request_path,
        request=request,
        plan=documents["plan"],
        mapping=mapping,
        compiler_profile=documents["compiler_profile"],
        validator_profile=documents["validator_profile"],
        semantic_digests=digests,
        input_paths=all_inputs,
        output_root=output_root,
        protected_roots=protected,
    )
