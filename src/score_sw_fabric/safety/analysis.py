"""Deterministic component FMEA/DFA checks: coverage, native rules, promotions and feedback."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from score_sw_fabric.agents.lock import load_lock
from score_sw_fabric.agents.models import (
    READINESS,
    glob_match,
    input_file,
    json_file,
    load_request,
    local_dir,
    protected_roots,
    relative_path,
    yaml_file,
)
from score_sw_fabric.agents.roles import validate_role
from score_sw_fabric.assurance.models import exact, seal, sha, stable_id, verify_digest
from score_sw_fabric.process_source.reader import InputError, read_bytes
from score_sw_fabric.safety.native import PLACEHOLDER, NativeSet, links, read_native
from score_sw_fabric.safety.profile import load_profile

CHECK_FIELDS = {
    "profile",
    "component",
    "analysis",
    "current",
    "baseline",
    "agent_checks",
    "platform_allocation",
    "iteration",
    "roles",
    "protected_roots",
}
FILE_ROLES = frozenset({"requirements", "architecture", "analysis", "allocation"})
MAX_FILES = 200
NON_BLOCKING = frozenset({"AOU_TRANSFER_REVIEW", "PROMOTION_UNREVIEWED"})


@dataclass(frozen=True)
class FileSet:
    root: Path
    files: list[dict[str, str]]
    native: NativeSet


def _file_set(base: Path, value: Any, pointer: str, directives: set[str]) -> FileSet:
    record = exact(value, {"root", "files"}, pointer)
    root = local_dir(base, record["root"], pointer + "/root")
    raw = record["files"]
    if not isinstance(raw, list) or not raw or len(raw) > MAX_FILES:
        raise InputError("LIMIT_EXCEEDED", "Select 1-200 native files", pointer + "/files")
    files = []
    loaded = []
    for index, item in enumerate(raw):
        entry = exact(item, {"path", "sha256", "role"}, f"{pointer}/files/{index}")
        path = relative_path(entry["path"], f"{pointer}/files/{index}/path")
        if entry["role"] not in FILE_ROLES:
            raise InputError("FIELD_ENUM", "Unknown file role", f"{pointer}/files/{index}/role")
        full = root / path
        if any(
            parent.is_symlink() for parent in (full, *full.parents) if parent.is_relative_to(root)
        ):
            raise InputError(
                "INPUT_ALIAS", "Native file path is a link", f"{pointer}/files/{index}"
            )
        data = read_bytes(full)
        if hashlib.sha256(data).hexdigest() != sha(
            entry["sha256"], f"{pointer}/files/{index}/sha256"
        ):
            raise InputError("INPUT_DRIFT", "Native file bytes changed", f"{pointer}/files/{index}")
        files.append({"path": path, "sha256": entry["sha256"], "role": entry["role"]})
        loaded.append((path, data, entry["role"]))
    if len({item["path"] for item in files}) != len(files):
        raise InputError("DUPLICATE_ID", "Duplicate native file", pointer + "/files")
    return FileSet(root=root, files=files, native=read_native(loaded, directives))


def _finding(code: str, subject: str, detail: str, rule: str | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "subject": subject,
        "detail": detail[:1024],
        "rule": rule,
        "blocking": code not in NON_BLOCKING,
    }


def _allocation(profile: dict[str, Any], native: NativeSet, value: Any) -> str | None:
    """Return the resolved platform allocation ID, or None when absent or unresolvable."""
    if value is None:
        return None
    stable_id(value, "/platform_allocation")
    need = native.needs.get(value)
    policy = profile["platform_allocation"]
    if need is None or need["role"] != "allocation":
        return None
    if need["type"] in policy["accepted_directives"]:
        return str(value)
    realizes = links(need["options"].get("realizes", ""))
    if need["type"] == "document" and set(realizes) & set(policy["accepted_work_products"]):
        return str(value)
    return None


def _coverage(
    spec: dict[str, Any],
    native: NativeSet,
    items: list[dict[str, Any]],
    allocation: str | None,
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    catalogue = {entry["id"]: entry for entry in spec["catalogue"]}
    rows: dict[str, list[dict[str, Any]]] = {}
    for native_row in native.rows:
        identifier = native_row["columns"].get("ID", "").strip()
        if "Applicability" not in native_row["columns"] or not identifier:
            continue
        if identifier not in catalogue:
            location = f"{native_row['path']}:{native_row['line']}"
            findings.append(_finding("UNKNOWN_CATALOGUE_ID", identifier, location))
            continue
        rows.setdefault(identifier, []).append(native_row)
    result = []
    for identifier, entry in catalogue.items():
        matching = [item["id"] for item in items if item["catalogue_id"] == identifier]
        selected = rows.get(identifier, [])
        if len(selected) > 1:
            findings.append(
                _finding("DUPLICATE_ROW", identifier, "Applicability given more than once")
            )
        row: dict[str, Any] | None = selected[0] if selected else None
        applicability = None if row is None else row["columns"]["Applicability"].strip().lower()
        rationale = None if row is None else row["columns"].get("Rationale", "").strip()
        if row is None:
            if entry["scope"] == "platform" and allocation is not None:
                state = "allocated"
            elif entry["scope"] == "platform":
                state = "uncovered"
                findings.append(
                    _finding(
                        "ALLOCATION_UNRESOLVED",
                        identifier,
                        "Platform-scope initiator omitted without a resolvable platform allocation",
                    )
                )
            else:
                state = "uncovered"
                findings.append(
                    _finding("CATALOGUE_ID_UNCOVERED", identifier, "No applicability row")
                )
        elif applicability not in {"yes", "no"} or not row["complete"]:
            state = "unknown_applicability"
            findings.append(
                _finding("APPLICABILITY_UNKNOWN", identifier, f"{row['path']}:{row['line']}")
            )
        elif applicability == "yes":
            state = "analysed" if matching else "applicable_without_item"
            if not matching:
                findings.append(
                    _finding(
                        "APPLICABLE_WITHOUT_ITEM", identifier, "Applicable without an analysis item"
                    )
                )
        elif not rationale or PLACEHOLDER.search(rationale):
            state = "excluded_without_rationale"
            findings.append(
                _finding("EXCLUSION_WITHOUT_RATIONALE", identifier, f"{row['path']}:{row['line']}")
            )
        else:
            state = "excluded"
        result.append(
            {
                "catalogue_id": identifier,
                "group": entry["group"],
                "scope": entry["scope"],
                "applicability": applicability,
                "rationale": rationale,
                "items": matching,
                "state": state,
            }
        )
    return result


def _item(
    profile: dict[str, Any], spec: dict[str, Any], native: NativeSet, need: dict[str, Any]
) -> dict[str, Any]:
    options = need["options"]
    violations: list[dict[str, Any]] = []
    identifier = need["id"]
    for option, pattern in spec["mandatory"].items():
        value = need["content"] if option == "content" else options.get(option)
        if value is None or value == "":
            violations.append(
                _finding(
                    "MANDATORY_OPTION" if option != "content" else "CONTENT_MISSING",
                    identifier,
                    option,
                )
            )
        elif re.fullmatch(pattern, value) is None:
            violations.append(
                _finding("OPTION_FORMAT", identifier, f"{option} does not match {pattern}")
            )
    for name, value in [*options.items(), ("content", need["content"])]:
        if PLACEHOLDER.search(str(value)):
            violations.append(_finding("PLACEHOLDER", identifier, name))
    catalogue_ids = {entry["id"] for entry in spec["catalogue"]}
    catalogue_id = options.get(spec["catalogue_field"])
    if catalogue_id and catalogue_id not in catalogue_ids:
        violations.append(_finding("UNKNOWN_CATALOGUE_ID", identifier, str(catalogue_id)))
    violates = links(options.get("violates", ""))
    mitigated_by = links(options.get("mitigated_by", ""))
    if not violates:
        violations.append(_finding("MANDATORY_OPTION", identifier, "violates"))
    for link_name, targets, allowed in (
        ("violates", violates, spec["violates"]),
        ("mitigated_by", mitigated_by, spec["mitigated_by"]),
    ):
        for target in targets:
            found = native.needs.get(target)
            if found is None:
                violations.append(_finding("LINK_UNRESOLVED", identifier, f"{link_name} {target}"))
            elif found["type"] not in allowed:
                violations.append(
                    _finding("LINK_TYPE", identifier, f"{link_name} {target} is {found['type']}")
                )
    issue = options.get("mitigation_issue")
    if issue and re.fullmatch(profile["mitigation_issue_pattern"], issue) is None:
        violations.append(_finding("MITIGATION_ISSUE_FORMAT", identifier, issue))
    rules = {rule["check"]: rule["id"] for rule in profile["rules"]}
    sufficient = options.get("sufficient")
    status = options.get("status")
    if sufficient == "yes" and not mitigated_by:
        violations.append(
            _finding(
                "SUFFICIENT_WITHOUT_MITIGATION",
                identifier,
                "sufficient: yes",
                rules["sufficient_requires_mitigation"],
            )
        )
    if status == "valid" and not mitigated_by:
        violations.append(
            _finding(
                "VALID_WITHOUT_MITIGATION",
                identifier,
                "status: valid",
                rules["valid_requires_mitigation"],
            )
        )
    if not mitigated_by:
        state = "proposed" if issue else "missing"
        violations.append(
            _finding(
                "MITIGATION_UNRESOLVED",
                identifier,
                "Mitigation issue open, no mitigating requirement linked"
                if issue
                else "No mitigation and no mitigation issue",
                None if issue else rules["open_mitigation_requires_issue"],
            )
        )
    elif sufficient == "yes" and status == "valid":
        state = "claimed_sufficient"
    else:
        state = "linked_pending_review"
    internal = any(
        str(catalogue_id).startswith(prefix) for prefix in profile["internal_fault_prefixes"]
    )
    if (
        internal
        and mitigated_by
        and all(native.needs.get(target, {}).get("type") == "aou_req" for target in mitigated_by)
    ):
        violations.append(
            _finding("AOU_TRANSFER_REVIEW", identifier, "Internal failure mitigated only by AoUs")
        )
    return {
        "id": identifier,
        "path": need["path"],
        "line": need["line"],
        "digest": need["digest"],
        "catalogue_id": catalogue_id,
        "violates": violates,
        "mitigated_by": mitigated_by,
        "mitigation_issue": issue,
        "failure_effect": options.get("failure_effect"),
        "content_sha256": hashlib.sha256(need["content"].encode()).hexdigest(),
        "sufficient": sufficient,
        "status": status,
        "mitigation_state": state,
        "violations": violations,
        "reanalysis_required": False,
    }


def _agent_paths(base: Path, value: Any) -> set[str]:
    if not isinstance(value, list) or len(value) > 100:
        raise InputError("LIMIT_EXCEEDED", "Too many agent checks", "/agent_checks")
    paths: set[str] = set()
    for index, item in enumerate(value):
        _, _, record = json_file(base, item, f"/agent_checks/{index}")
        verify_digest(record, f"/agent_checks/{index}")
        if record.get("kind") != "agent_output_check":
            raise InputError(
                "KIND_MISMATCH", "Expected a 007 agent_output_check", f"/agent_checks/{index}"
            )
        paths.update(str(change["path"]) for change in record.get("changes", []))
    return paths


def _roles(
    base: Path, value: Any, current: FileSet, findings: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Check that FMEA and DFA analyst roles are separate and confined to their analyses."""
    if value is None:
        return []
    record = exact(value, {"lock", "fmea", "dfa"}, "/roles")
    _, lock_bytes = input_file(base, record["lock"], "/roles/lock")
    lock = load_lock(lock_bytes)
    roles = {}
    for kind in ("fmea", "dfa"):
        _, data, raw = yaml_file(base, record[kind], f"/roles/{kind}")
        roles[kind] = validate_role(raw, lock)
        roles[kind]["sha256"] = hashlib.sha256(data).hexdigest()
    expected = {"fmea": "fmea_analyst", "dfa": "dfa_analyst"}
    if (
        any(roles[kind]["role"] != expected[kind] for kind in roles)
        or roles["fmea"]["id"] == roles["dfa"]["id"]
    ):
        findings.append(
            _finding("ROLE_NOT_SEPARATE", "roles", "FMEA and DFA need distinct analyst roles")
        )
    work_products: dict[str, set[str]] = {"fmea": set(), "dfa": set()}
    for document in current.native.documents:
        for product in links(document["options"].get("realizes", "")):
            for kind in ("fmea", "dfa"):
                if product.endswith(f"_{kind}"):
                    work_products[kind].add(document["path"])
    for item in current.files:
        owners = [
            kind
            for kind in roles
            if any(glob_match(pattern, item["path"]) for pattern in roles[kind]["write_scope"])
        ]
        if len(owners) > 1:
            findings.append(
                _finding(
                    "ROLE_SCOPE_OVERLAP", item["path"], "Both analyst roles may write this file"
                )
            )
        for kind in owners:
            if item["path"] not in work_products[kind]:
                findings.append(
                    _finding(
                        "ROLE_SCOPE_EXCEEDS_ANALYSIS",
                        item["path"],
                        f"{kind} analyst may write a non-{kind} file",
                    )
                )
    return [
        {
            "kind": kind,
            "id": role["id"],
            "role": role["role"],
            "sha256": role["sha256"],
            "write_scope": role["write_scope"],
        }
        for kind, role in roles.items()
    ]


def check(request_path: Path) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    record, base = load_request(request_path, "safety_check_request", CHECK_FIELDS)
    profile_path, profile_bytes = input_file(base, record["profile"], "/profile")
    profile = load_profile(profile_bytes)
    kind = record["analysis"]
    if kind not in {"fmea", "dfa"}:
        raise InputError("FIELD_ENUM", "Analysis must be fmea or dfa", "/analysis")
    spec = profile["analyses"][kind]
    component = stable_id(record["component"], "/component")
    iteration = record["iteration"]
    if type(iteration) is not int or not 1 <= iteration <= 100:
        raise InputError("LIMIT_EXCEEDED", "Iteration must be 1-100", "/iteration")
    directives = {
        spec["directive"],
        *profile["requirement_directives"],
        *profile["architecture_directives"],
        *profile["platform_allocation"]["accepted_directives"],
    }
    current = _file_set(base, record["current"], "/current", directives)
    baseline = (
        None
        if record["baseline"] is None
        else _file_set(base, record["baseline"], "/baseline", directives)
    )
    protected = protected_roots(base, record["protected_roots"], "/protected_roots")
    findings: list[dict[str, Any]] = []
    for duplicate in current.native.duplicates:
        findings.append(_finding("DUPLICATE_NEED", duplicate, "Need ID defined more than once"))
    needs = [
        need
        for need in current.native.needs.values()
        if need["type"] == spec["directive"] and need["role"] == "analysis"
    ]
    items = [
        _item(profile, spec, current.native, need)
        for need in sorted(needs, key=lambda item: item["id"])
    ]
    allocation = _allocation(profile, current.native, record["platform_allocation"])
    if record["platform_allocation"] is not None and allocation is None:
        findings.append(
            _finding(
                "ALLOCATION_UNRESOLVED",
                str(record["platform_allocation"]),
                "Allocation is not a platform DFA record in the allocation files",
            )
        )
    coverage = _coverage(spec, current.native, items, allocation, findings)
    agent_paths = _agent_paths(base, record["agent_checks"])
    promotions = []
    for item in items:
        prior = None if baseline is None else baseline.native.needs.get(item["id"])
        for field, promoted in (("sufficient", "yes"), ("status", "valid")):
            before = None if prior is None else prior["options"].get(field)
            if item[field] == promoted and before != promoted:
                classification = (
                    "UNTRUSTED_PROMOTION" if item["path"] in agent_paths else "PROMOTION_UNREVIEWED"
                )
                promotions.append(
                    {
                        "item": item["id"],
                        "field": field,
                        "from": before,
                        "to": promoted,
                        "classification": classification,
                    }
                )
                findings.append(
                    _finding(classification, item["id"], f"{field}: {before} -> {promoted}")
                )
    reanalysis: dict[str, Any] = {
        "changed": [],
        "removed": [],
        "new": [],
        "affected_items": [],
        "reanalysed_items": [],
        "unreferenced_new_elements": [],
    }
    if baseline is not None:
        element_types = {*profile["requirement_directives"], *profile["architecture_directives"]}
        old = {
            key: need
            for key, need in baseline.native.needs.items()
            if need["type"] in element_types
        }
        new = {
            key: need for key, need in current.native.needs.items() if need["type"] in element_types
        }
        reanalysis["changed"] = sorted(
            key for key in old.keys() & new.keys() if old[key]["digest"] != new[key]["digest"]
        )
        reanalysis["removed"] = sorted(old.keys() - new.keys())
        reanalysis["new"] = sorted(new.keys() - old.keys())
        touched = set(reanalysis["changed"]) | set(reanalysis["removed"]) | set(reanalysis["new"])
        for item in items:
            if not touched & set(item["violates"] + item["mitigated_by"]):
                continue
            prior = baseline.native.needs.get(item["id"])
            if prior is not None and prior["digest"] == item["digest"]:
                item["reanalysis_required"] = True
                reanalysis["affected_items"].append(item["id"])
                findings.append(
                    _finding(
                        "REANALYSIS_REQUIRED",
                        item["id"],
                        "References changed elements; the item itself is unchanged",
                    )
                )
            else:
                reanalysis["reanalysed_items"].append(item["id"])
        referenced = {target for item in items for target in item["violates"]}
        for key in reanalysis["new"]:
            if new[key]["type"] in spec["violates"] and key not in referenced:
                reanalysis["unreferenced_new_elements"].append(key)
                findings.append(
                    _finding(
                        "NEW_ELEMENT_UNANALYSED", key, "New architecture element is not analysed"
                    )
                )
    max_iterations = profile["loop"]["max_iterations"]
    feedback = []
    for item in items:
        if item["mitigation_state"] not in {"missing", "proposed"}:
            continue
        if iteration >= max_iterations:
            feedback.append(
                {
                    "item": item["id"],
                    "action": "escalate_to_human",
                    "routes": ["safety_review"],
                    "iteration": iteration,
                    "max_iterations": max_iterations,
                }
            )
            findings.append(
                _finding(
                    "ESCALATE_TO_HUMAN", item["id"], f"Unresolved after {iteration} iterations"
                )
            )
        else:
            feedback.append(
                {
                    "item": item["id"],
                    "action": "requirement_or_aou_review",
                    "routes": ["requirements_review", "architecture_review", "reanalysis"],
                    "iteration": iteration,
                    "max_iterations": max_iterations,
                }
            )
    roles = _roles(base, record["roles"], current, findings)
    for item in items:
        findings.extend(item["violations"])
    blocking = sorted({item["code"] for item in findings if item["blocking"]})
    output = {
        "schema_version": 1,
        "kind": "safety_analysis_report",
        "profile": {
            "id": profile["id"],
            "sha256": hashlib.sha256(profile_bytes).hexdigest(),
            "status": profile["status"],
        },
        "component": component,
        "analysis": kind,
        "directive": spec["directive"],
        "iteration": iteration,
        "current_files": current.files,
        "baseline_files": None if baseline is None else baseline.files,
        "platform_allocation": allocation,
        "coverage": coverage,
        "items": items,
        "baseline_items": []
        if baseline is None
        else [
            {
                key: value
                for key, value in _item(profile, spec, baseline.native, need).items()
                if key != "violations"
            }
            for need in sorted(baseline.native.needs.values(), key=lambda item: item["id"])
            if need["type"] == spec["directive"] and need["role"] == "analysis"
        ],
        "promotions": promotions,
        "reanalysis": reanalysis,
        "feedback": feedback,
        "roles": roles,
        "findings": findings,
        "design_prerequisites": {
            "state": "blocked" if blocking else "ready_for_design_review",
            "reasons": blocking,
        },
        "outcome": "blocked" if blocking else "complete",
        "engineering_readiness": READINESS,
        "limitations": [
            "Structural and native-rule checks only; they do not establish analysis adequacy.",
            "sufficient/status claims are unreviewed until a verified decision binds these bytes.",
            "Feedback proposals route work to human review; they contain no engineering content.",
        ],
    }
    return 1 if blocking else 0, seal(output), [profile_path], [*protected, current.root]
