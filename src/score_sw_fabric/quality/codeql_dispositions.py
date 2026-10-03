"""Measured CodeQL context for imported proposals; inspection cannot correct a finding."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from score_sw_fabric.agents.models import input_file, protected_roots, relative_path
from score_sw_fabric.assurance.models import (
    bounded_list,
    exact,
    nonempty,
    seal,
    sha,
    verify_digest,
    version,
)
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality import codeql
from score_sw_fabric.quality import disposition_models as dm
from score_sw_fabric.quality.codeql_models import reference, validate_configuration
from score_sw_fabric.quality.codeql_observations import verify_observations
from score_sw_fabric.quality.controls import read_control
from score_sw_fabric.quality.import_models import (
    bounded_tree,
    choice,
    native_root,
    selected_control,
    strings,
)
from score_sw_fabric.quality.models import Budget, baseline, digest, load_inputs, raw_bytes
from score_sw_fabric.quality.profile import load_profile, load_toolchain
from score_sw_fabric.runtime.models import output_path
from score_sw_fabric.runtime.request import _local
from score_sw_fabric.storage import temporary_directory

REQUEST_KIND = "quality_codeql_disposition_request"
REVIEW_KIND = "quality_codeql_disposition_review"
INSPECTION_FIELDS = {
    "profile",
    "toolchain",
    "configuration",
    "capability",
    "prerequisites",
    "source_inspection",
    "pack_inspection",
    "phases",
    "artifacts",
    "gaps",
    "outcome",
    "origin",
    "assurance_eligibility",
    "engineering_readiness",
    "accepted_claims",
    "analysis_executed",
    "inspector",
    "limitations",
    "baseline",
    "processed_units",
    "extraction",
    "diagnostics",
    "source_integrity",
    "digest",
}
IDENTITY_REASONS = {
    "TOOL_CHANGED",
    "CONFIGURATION_CHANGED",
    "QUERY_PACK_CHANGED",
    "QUERY_SUITE_CHANGED",
    "QUERY_LIBRARIES_CHANGED",
    "POLICY_CHANGED",
    "ANALYSIS_SCOPE_CHANGED",
    "CONSTRUCT_SCOPE_CHANGED",
    "CONSTRUCT_CHANGED",
    "DISPOSITION_EXPIRED",
}


def validate_inspection(value: Any) -> dict[str, Any]:
    """Check unprotected inspection structure without touching its original host paths."""
    r = version(value, "quality_codeql_analysis_run", INSPECTION_FIELDS, "/inspection")
    bounded_tree(r)
    verify_digest(r, "/inspection")
    extraction = exact(
        r["extraction"],
        {
            "expected_state",
            "expected_units",
            "processed_units",
            "missing_units",
            "unexpected_units",
            "adequacy",
            "limitations",
        },
        "/inspection/extraction",
    )
    load_profile(canonical(r["profile"]))
    load_toolchain(canonical(r["toolchain"]), "quality_codeql_toolchain_profile", check_paths=False)
    configuration = exact(
        r["configuration"], {"selection", "effective"}, "/inspection/configuration"
    )
    validate_configuration(configuration["effective"])
    if (
        r["analysis_executed"] is not False
        or type(r["accepted_claims"]) is not int
        or r["accepted_claims"] != 0
        or r["outcome"] != "unavailable"
        or r["origin"] != "local_unprotected_inspection"
        or r["assurance_eligibility"] != "not_eligible"
        or r["engineering_readiness"] != "not_evaluated"
        or r["processed_units"] != []
        or r["diagnostics"] != []
        or r["extraction"]["adequacy"] != "unknown"
    ):
        raise InputError(
            "CODEQL_INSPECTION", "Inspection cannot claim executed or adequate analysis"
        )
    dm.baseline(r["baseline"])
    if (
        configuration["selection"] != r["baseline"]["configuration"]
        or extraction["expected_units"] != r["baseline"]["expected_units"]
        or extraction["expected_state"]
        != ("unknown" if r["baseline"]["expected_units"] is None else "declared")
        or extraction["processed_units"] != []
        or extraction["unexpected_units"] != []
        or extraction["missing_units"] != (r["baseline"]["expected_units"] or [])
    ):
        raise InputError("BASELINE_DRIFT", "Inspection selection or extraction scope differs")

    def manifest(rows: Any, maximum: int) -> None:
        names = []
        total = 0
        for row in bounded_list(rows, maximum, "/manifest"):
            exact(row, {"path", "sha256", "bytes"}, "/manifest/file")
            names.append(relative_path(row["path"], "/manifest/path"))
            sha(row["sha256"], "/manifest/sha256")
            if type(row["bytes"]) is not int or not 0 <= row["bytes"] <= 16 * 1024 * 1024:
                raise InputError("LIMIT_EXCEEDED", "Manifest file exceeds its byte bound")
            total += row["bytes"]
        if names != sorted(set(names)) or total > 64 * 1024 * 1024:
            raise InputError("CODEQL_INSPECTION", "Manifest ordering, identity or bytes differ")

    def integer(value: Any, maximum: int, pointer: str) -> None:
        if type(value) is not int or not 0 <= value <= maximum:
            raise InputError("LIMIT_EXCEEDED", "Integer exceeds its declared bound", pointer)

    def git_identity(value: Any, pointer: str, *, optional: bool = False) -> None:
        if optional and value is None:
            return
        if not isinstance(value, str) or re.fullmatch(r"[a-f0-9]{40}", value) is None:
            raise InputError("HASH_FORMAT", "Retained Git identity must be full", pointer)

    def texts(value: Any, maximum: int, length: int, pointer: str) -> None:
        for text in bounded_list(value, maximum, pointer):
            nonempty(text, pointer, max_length=length)

    choice(r["source_integrity"], {"unchanged", "changed"}, "/source_integrity")
    inspector = exact(r["inspector"], {"path", "sha256", "qualification"}, "/inspector")
    native_root(inspector["path"])
    sha(inspector["sha256"], "/inspector/sha256")
    choice(inspector["qualification"], {"unknown"}, "/inspector/qualification")
    texts(r["limitations"], 32, 2048, "/limitations")
    prerequisite_ids = set()
    for row in bounded_list(r["prerequisites"], 32, "/prerequisites"):
        exact(row, {"id", "state", "reasons"}, "/prerequisite")
        name = nonempty(row["id"], "/prerequisite/id", max_length=128)
        if name in prerequisite_ids:
            raise InputError("DUPLICATE_ID", "Duplicate prerequisite identity")
        prerequisite_ids.add(name)
        choice(
            row["state"],
            {"available", "unavailable", "unsupported", "unknown"},
            "/prerequisite/state",
        )
        texts(row["reasons"], 100, 256, "/prerequisite/reasons")

    source = exact(
        r["source_inspection"],
        {
            "lock",
            "repository",
            "commit",
            "tree",
            "status",
            "origin",
            "files",
            "files_digest",
            "matched_locked_sources",
            "source_build",
            "reporting",
        },
        "/source_inspection",
    )
    manifest(source["files"], 500)
    reference(source["lock"], "/source/lock")
    nonempty(source["repository"], "/source/repository", max_length=1024)
    git_identity(source["commit"], "/source/commit")
    git_identity(source["tree"], "/source/tree", optional=True)
    choice(source["origin"], {"locked_source_selection", "fixture"}, "/source/origin")
    integer(source["matched_locked_sources"], 500, "/source/matched_locked_sources")
    choice(source["status"], {"clean", "unknown"}, "/source/status")
    source_build = exact(
        source["source_build"],
        {
            "locked_tree",
            "declared_build_commit",
            "build_tree",
            "state",
            "compiled_artifact_provenance",
        },
        "/source/source_build",
    )
    reporting = exact(
        source["reporting"],
        {
            "manual_python_version",
            "requirements",
            "interpreter_state",
            "compatibility",
            "eligibility_ref",
            "eligibility_state",
        },
        "/source/reporting",
    )
    for key in ("locked_tree", "declared_build_commit", "build_tree"):
        git_identity(source_build[key], "/source_build/" + key, optional=True)
    choice(
        source_build["state"],
        {"source_trees_equal", "source_trees_different", "unknown"},
        "/source_build/state",
    )
    if reporting["manual_python_version"] != "3.9":
        raise InputError("VERSION_UNSUPPORTED", "Native manual Python version differs")
    manifest(reporting["requirements"], 10)
    choice(
        reporting["eligibility_state"],
        {"not_selected", "unverified"},
        "/reporting/eligibility_state",
    )
    if reporting["eligibility_ref"] is not None:
        reference(reporting["eligibility_ref"], "/reporting/eligibility_ref")
    choice(
        reporting["interpreter_state"],
        {"not_selected", "bytes_verified", "unavailable"},
        "/source/reporting/interpreter_state",
    )
    capability = exact(
        r["capability"],
        {
            "state",
            "installation_state",
            "declared_cli_version",
            "checks",
            "effective_config",
            "suite_exclusions",
            "analysis_state",
        },
        "/capability",
    )
    choice(
        capability["installation_state"],
        {"bytes_verified", "unavailable"},
        "/capability/installation_state",
    )
    if capability["declared_cli_version"] != "2.21.4":
        raise InputError("VERSION_UNSUPPORTED", "Declared CodeQL CLI version differs")
    texts(capability["suite_exclusions"], 100, 256, "/capability/suite_exclusions")
    if (
        capability["state"] != "unavailable"
        or capability["checks"] != []
        or capability["analysis_state"] != "not_executed"
        or not isinstance(capability["effective_config"], dict)
        or source_build["compiled_artifact_provenance"] != "unverified"
        or reporting["compatibility"] != "unexecuted"
    ):
        raise InputError("CODEQL_INSPECTION", "Native execution or provenance is unverified")
    strings(r["gaps"], "/gaps", 500)
    required_gaps = {
        "CODEQL_EXECUTION_UNIMPLEMENTED",
        "CODEQL_ELIGIBILITY_UNKNOWN",
        "COMPILED_ARTIFACT_PROVENANCE_UNVERIFIED",
        "CODEQL_RUNTIME_CLOSURE_UNVERIFIED",
        "NATIVE_REPORTING_UNEXECUTED",
        *r["profile"]["required_obligations"],
    }
    if not required_gaps.issubset(r["gaps"]):
        raise InputError(
            "CODEQL_INSPECTION", "Unavailable native execution obligations are missing"
        )
    if source["files_digest"] != digest(canonical(source["files"])):
        raise InputError("CODEQL_INSPECTION", "Source manifest digest differs")
    pack = r["pack_inspection"]
    if pack is not None:
        exact(
            pack,
            {
                "root",
                "manifest",
                "manifest_digest",
                "identity",
                "lock",
                "suite",
                "included_source_state",
                "included_source_count",
                "compiled_artifact_provenance",
                "libraries",
                "library_state",
                "library_gaps",
            },
            "/pack_inspection",
        )
        manifest(pack["manifest"], 5000)
        native_root(pack["root"])
        choice(pack["included_source_state"], {"matched", "unknown"}, "/pack/included_source_state")
        integer(pack["included_source_count"], 500, "/pack/included_source_count")
        if (
            not isinstance(pack["identity"], dict)
            or pack["identity"].get("name") != "codeql/misra-cpp-coding-standards"
            or pack["identity"].get("version") != "2.61.0"
            or not isinstance(pack["lock"], dict)
            or pack["compiled_artifact_provenance"] != "unverified"
        ):
            raise InputError("CODEQL_INSPECTION", "Selected pack identity or provenance differs")
        exact(
            pack["suite"],
            {"path", "sha256", "definition", "imports", "excluded_tags", "included_tags"},
            "/pack/suite",
        )
        suite = pack["suite"]
        for definition in [suite, *bounded_list(suite["imports"], 16, "/suite/imports")]:
            if definition is not suite:
                exact(definition, {"path", "sha256", "definition"}, "/suite/import")
            relative_path(definition["path"], "/suite/path")
            sha(definition["sha256"], "/suite/sha256")
            for directive in bounded_list(definition["definition"], 64, "/suite/definition"):
                if not isinstance(directive, dict):
                    raise InputError(
                        "CODEQL_INSPECTION", "Native suite directives must be mappings"
                    )
        strings(suite["included_tags"], "/suite/included_tags", 100)
        strings(suite["excluded_tags"], "/suite/excluded_tags", 100)
        indexed = {row["path"]: row for row in pack["manifest"]}
        dependencies = pack["lock"].get("dependencies")
        if not isinstance(dependencies, dict) or len(dependencies) > 32:
            raise InputError("CODEQL_INSPECTION", "Native library lock is invalid")
        library_names = set()
        for library in bounded_list(pack["libraries"], 32, "/pack/libraries"):
            exact(library, {"path", "bytes", "sha256", "name", "version", "metadata"}, "/library")
            relative_path(library["path"], "/library/path")
            sha(library["sha256"], "/library/sha256")
            nonempty(library["name"], "/library/name", max_length=256)
            nonempty(library["version"], "/library/version", max_length=64)
            integer(library["bytes"], 1024 * 1024, "/library/bytes")
            if not isinstance(library["metadata"], dict):
                raise InputError("CODEQL_INSPECTION", "Native library metadata must be a mapping")
            name = library["name"]
            if name in library_names or name not in dependencies:
                raise InputError("CODEQL_INSPECTION", "Native library identity differs from lock")
            library_names.add(name)
            entry = dependencies[name]
            if (
                not isinstance(entry, dict)
                or entry.get("version") != library["version"]
                or library["metadata"].get("name") != name
                or library["metadata"].get("version") != library["version"]
                or indexed.get(library["path"])
                != {key: library[key] for key in ("path", "bytes", "sha256")}
            ):
                raise InputError("CODEQL_INSPECTION", "Native library bytes or metadata differ")
        missing = set(dependencies) - library_names
        if pack["library_state"] != ("incomplete" if missing else "matched") or pack[
            "library_gaps"
        ] != sorted("LIBRARY_UNAVAILABLE:" + name for name in missing):
            raise InputError("CODEQL_INSPECTION", "Native library closure state differs")
        if pack["manifest_digest"] != digest(canonical(pack["manifest"])):
            raise InputError("CODEQL_INSPECTION", "Compiled pack manifest digest differs")
    total = 0
    ids = set()
    for raw in bounded_list(r["artifacts"], 100, "/artifacts"):
        exact(
            raw,
            {"id", "path", "format", "bytes", "sha256", "retained_sha256", "base64", "truncated"},
            "/artifact",
        )
        name = nonempty(raw["id"], "/artifact/id", max_length=128)
        if name in ids:
            raise InputError("DUPLICATE_ID", "Duplicate inspection original")
        ids.add(name)
        nonempty(raw["path"], "/artifact/path", max_length=1024)
        choice(raw["format"], {"text", "clang-tidy-yaml"}, "/artifact/format")
        dm._raw({k: v for k, v in raw.items() if k not in {"id", "path"}})
        total += len(raw_bytes(raw))
    for phase in bounded_list(r["phases"], 32, "/phases"):
        exact(
            phase,
            {
                "name",
                "argv",
                "stdout",
                "stderr",
                "elapsed_seconds",
                "error",
                "exit_code",
                "timed_out",
            },
            "/phase",
        )
        argv = bounded_list(phase["argv"], 2000, "/phase/argv")
        nonempty(phase["name"], "/phase/name", max_length=1024)
        if (
            type(phase["elapsed_seconds"]) not in {int, float}
            or phase["elapsed_seconds"] < 0
            or type(phase["timed_out"]) is not bool
            or (phase["exit_code"] is not None and type(phase["exit_code"]) is not int)
            or (phase["error"] is not None and not isinstance(phase["error"], str))
        ):
            raise InputError("FIELD_TYPE", "Malformed retained phase status or timing")
        for argument in argv:
            nonempty(argument, "/phase/argv/argument", max_length=1024)
        if not argv or argv[0] != "/usr/bin/git":
            raise InputError(
                "CODEQL_INSPECTION", "Only bounded Git inspection phases are supported"
            )
        dm._raw(phase["stdout"])
        dm._raw(phase["stderr"])
        for key in ("stdout", "stderr"):
            choice(phase[key]["format"], {"text", "clang-tidy-yaml"}, "/phase/" + key + "/format")
        total += len(raw_bytes(phase["stdout"])) + len(raw_bytes(phase["stderr"]))
    if total > 64 * 1024 * 1024 or len(canonical(r)) > dm.MAX_RECORD:
        raise InputError("LIMIT_EXCEEDED", "Inspection originals exceed aggregate bounds")
    verify_observations(r)
    return r


def context_reasons(identity: dict[str, Any], inspected: dict[str, Any]) -> list[str]:
    """Compare declared import identities with measured installed context; grant no authority."""
    reasons = []
    tool = inspected["toolchain"]["tool"]
    if identity["tool_sha256"] != tool["sha256"] or identity["version"] != tool["version"]:
        reasons.append("TOOL_CHANGED")
    if identity["config_sha256"] != inspected["baseline"]["configuration"]["sha256"]:
        reasons.append("CONFIGURATION_CHANGED")
    pack = inspected["pack_inspection"]
    if pack is None:
        return reasons + [
            "QUERY_PACK_CONTEXT_UNKNOWN",
            "QUERY_SUITE_CONTEXT_UNKNOWN",
            "QUERY_LIBRARIES_CONTEXT_UNKNOWN",
        ]
    expected = {
        "name": pack["identity"]["name"],
        "version": pack["identity"]["version"],
        "sha256": pack["manifest_digest"],
    }
    if identity["query_pack"] != expected:
        reasons.append("QUERY_PACK_CHANGED")
    suite = inspected["configuration"]["effective"]["suite"]
    suite_hash = next((row["sha256"] for row in pack["manifest"] if row["path"] == suite), None)
    if identity["suite"] != {"name": suite, "sha256": suite_hash}:
        reasons.append("QUERY_SUITE_CHANGED")
    libraries = sorted(
        [{k: row[k] for k in ("name", "version", "sha256")} for row in pack["libraries"]],
        key=lambda r: r["name"],
    )
    if sorted(identity["libraries"], key=lambda r: r["name"]) != libraries:
        reasons.append("QUERY_LIBRARIES_CHANGED")
    if pack["library_state"] != "matched":
        reasons.append("QUERY_LIBRARIES_CONTEXT_UNKNOWN")
    return reasons


def classify(
    original: dict[str, Any],
    draft: dict[str, Any],
    inspected: dict[str, Any],
    action: str,
    observed: datetime,
) -> tuple[str, list[str]]:
    """Reproduce unresolved context states from original declarations and measured identities."""
    from score_sw_fabric.quality.dispositions import _scope_changes

    ident = next((row for row in original["identities"] if row["id"] == "codeql"), None)
    if ident is None:
        raise InputError("TOOL_IDENTITY_MISMATCH", "Imported CodeQL identity is missing")
    frozen = inspected["baseline"]
    reasons = _scope_changes(original["baseline"], frozen, False) + context_reasons(
        ident, inspected
    )
    if (
        draft["requested_kind"] != "correction"
        and dm.files(frozen["files"]).get(draft["construct"]["path"])
        != draft["construct"]["sha256"]
    ):
        reasons.append("CONSTRUCT_CHANGED")
    if (
        draft["expires_at"] is not None
        and dm.timestamp(draft["expires_at"], "/expires_at") <= observed
    ):
        reasons.append("DISPOSITION_EXPIRED")
    stale = bool(set(reasons) & IDENTITY_REASONS)
    reasons.extend(inspected["gaps"])
    reasons.append("CODEQL_INSPECTION_UNAUTHENTICATED")
    if stale:
        state = "stale"
    elif draft["requested_kind"] != "correction":
        state = "pending_review"
        reasons.append("HUMAN_REVIEW_PENDING")
    elif action == "draft":
        state = "open"
        reasons.append("FRESH_CODEQL_ANALYSIS_REQUIRED")
    else:
        state = "blocked"
        reasons.append("FRESH_CODEQL_ANALYSIS_REQUIRED")
    if draft["decision_refs"]:
        reasons.append("DECISION_NOT_REPRODUCED")
    if draft["requested_kind"] in {"deviation", "recategorization", "suppression"}:
        reasons.append("DEVIATION_POLICY_UNKNOWN")
    return state, sorted(set(reasons))


def review(
    request_path: Path,
    request: dict[str, Any],
    request_bytes: bytes,
    out: Path | None = None,
    *,
    draft_only: bool = False,
) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    from score_sw_fabric.quality.dispositions import _history

    request = version(request, REQUEST_KIND, dm.REQUEST_FIELDS, "/request")
    base = request_path.parent
    action = choice(request["action"], {"draft", "check_correction"}, "/action")
    if draft_only and action != "draft":
        raise InputError("DISPOSITION_ACTION", "Decision preparation requires a draft")
    selection = exact(request["current"], {"adapter", "request"}, "/current")
    choice(selection["adapter"], {"codeql"}, "/current/adapter")
    current_path, _ = input_file(base, selection["request"], "/current/request")
    selected = load_inputs(current_path, "run", "codeql")
    origin_path, original = selected_control(base, request["origin"], max_bytes=dm.MAX_RECORD)
    original, findings, adapter = dm.origin(original)
    if adapter is not None or original["kind"] != "quality_native_import":
        raise InputError("DISPOSITION_ORIGIN", "Select an imported CodeQL finding")
    draft_path, draft = selected_control(base, request["draft"])
    draft = dm.draft(draft, original, findings)
    finding = findings[draft["finding_index"]]
    if finding.get("tool") != "codeql":
        raise InputError("DISPOSITION_ORIGIN", "Selected finding must come from CodeQL")
    if action == "check_correction" and draft["requested_kind"] != "correction":
        raise InputError("DISPOSITION_KIND", "Only a correction proposal can request correction")
    subject = seal(
        {
            "origin_ref": request["origin"],
            "origin_digest": original["digest"],
            "origin_class": original["origin"],
            "finding_index": draft["finding_index"],
            "finding": finding,
            "baseline": original["baseline"],
        }
    )
    inputs = [
        request_path,
        current_path,
        origin_path,
        draft_path,
        codeql.INSPECTOR,
        *selected.inputs,
    ]
    protected = [
        native_root(original["baseline"]["root"]),
        *selected.protected,
        *protected_roots(
            base,
            bounded_list(request["protected_roots"], 32, "/protected_roots"),
            "/protected_roots",
        ),
    ]
    total = 0
    for key in ("compensating_evidence", "decision_refs"):
        for ref in draft[key]:
            path, data = input_file(draft_path.parent, ref, "/draft/" + key)
            total += len(data)
            if total > 64 * 1024 * 1024:
                raise InputError("LIMIT_EXCEEDED", "Proposal originals exceed their bound")
            inputs.append(path)
    previous = None
    revision = 1
    if request["previous"] is not None:
        parent, paths = _history(base, request["previous"], draft, subject)
        if parent["kind"] != REVIEW_KIND:
            raise InputError("DISPOSITION_HISTORY", "CodeQL context history kind differs")
        inputs.extend(paths)
        previous = {
            "ref": request["previous"],
            "digest": parent["digest"],
            "state": parent["state"],
        }
        revision = parent["revision"] + 1
    if out is not None:
        output_path(out, inputs, protected)
    inspector = codeql._file(codeql.INSPECTOR, 512 * 1024 * 1024)
    _, inspected, run_inputs, run_protected = codeql.run(current_path)
    inputs.extend(run_inputs)
    protected.extend(run_protected)
    validate_inspection(inspected)
    frozen = baseline(selected)
    if inspected["baseline"] != frozen:
        raise InputError("INPUT_DRIFT", "Current context changed during inspection")
    observed = datetime.now(UTC)
    state, reasons = classify(original, draft, inspected, action, observed)
    record = seal(
        {
            "schema_version": 1,
            "kind": REVIEW_KIND,
            "draft": draft,
            "subject": subject,
            "current_baseline": frozen,
            "inspection": inspected,
            "fresh_run": None,
            "previous": previous,
            "revision": revision,
            "observed_at": observed.isoformat(),
            "time_basis": "local_untrusted",
            "state": state,
            "reasons": sorted(set(reasons)),
            "outcome": "unresolved",
            "origin": "local_unprotected_inspection",
            "assurance_eligibility": "not_eligible",
            "engineering_readiness": "not_evaluated",
            "limitations": [
                "Native imports, names and inspection labels remain unprotected.",
                "No CodeQL analysis, correction, eligible decision or acceptance is established.",
                "Native query text and tool binaries remain external byte identities.",
            ],
        }
    )
    if len(canonical(record)) > dm.MAX_RECORD:
        raise InputError("LIMIT_EXCEEDED", "CodeQL review exceeds 96 MiB")
    if read_control(request_path) != request_bytes:
        raise InputError("INPUT_DRIFT", "Disposition request changed during inspection")
    selected_control(base, request["origin"], max_bytes=dm.MAX_RECORD)
    selected_control(base, request["draft"])
    input_file(base, selection["request"], "/current/request")
    if request["previous"] is not None:
        _history(base, request["previous"], draft, subject)
    for key in ("compensating_evidence", "decision_refs"):
        for ref in draft[key]:
            input_file(draft_path.parent, ref, "/draft/" + key)
    # Freeze material content again after proposal assembly; these are measurements, not retries.
    source_root = Path(selected.settings["effective"]["source_root"])
    if (
        codeql._manifest(source_root, [r["path"] for r in inspected["source_inspection"]["files"]])
        != inspected["source_inspection"]["files"]
    ):
        raise InputError("INPUT_DRIFT", "Native source content changed during proposal assembly")
    pack = inspected["pack_inspection"]
    if (
        pack is not None
        and codeql._manifest(Path(pack["root"]), codeql._names(Path(pack["root"])))
        != pack["manifest"]
    ):
        raise InputError("INPUT_DRIFT", "Installed pack content changed during proposal assembly")
    for ref in selected.request["files"]:
        input_file(Path(selected.request["root"]), ref, "/current/files")
    refreshed = load_inputs(current_path, "run", "codeql")
    if (
        refreshed.request != selected.request
        or refreshed.profile != selected.profile
        or refreshed.toolchain != selected.toolchain
        or refreshed.settings != selected.settings
        or refreshed.assets != selected.assets
    ):
        raise InputError("INPUT_DRIFT", "Selected CodeQL controls changed during proposal assembly")
    controls = {}
    controls[current_path] = input_file(base, selection["request"], "/current/request")[1]
    for raw in inspected["artifacts"]:
        control_base = current_path.parent
        if raw["id"] in {
            "source_lock",
            "scan_config",
            "report_patch",
            "reporting_toolchain",
            "eligibility",
        }:
            control_base = selected.inputs[2].parent
        controls[_local(control_base, raw["path"], "/inspection/artifact")] = raw_bytes(raw)
        if raw["truncated"]:
            # Publication cannot refreeze a control whose original bytes were not retained.
            raise InputError("OUTPUT_TRUNCATED", "CodeQL context original is incomplete")
    selected.settings["_controls"] = controls
    source = inspected["source_inspection"]
    head_phase = next(
        (phase for phase in inspected["phases"] if phase["name"] == "source:head"), None
    )
    if head_phase is None:
        raise InputError("CODEQL_INSPECTION", "Original native HEAD inspection phase is missing")
    observed_head = None
    if (
        head_phase["exit_code"] == 0
        and not head_phase["timed_out"]
        and not head_phase["error"]
        and not any(head_phase[key]["truncated"] for key in ("stdout", "stderr"))
    ):
        try:
            observed_head = raw_bytes(head_phase["stdout"]).decode("utf-8").strip()
        except UnicodeDecodeError as exc:
            raise InputError(
                "CODEQL_INSPECTION", "Original native HEAD identity is not UTF-8"
            ) from exc
    selected.settings["_observed"] = {
        "state": (observed_head, source["tree"], "" if source["status"] == "clean" else None),
        "source_names": [row["path"] for row in source["files"]],
        "source_files": source["files"],
        "git_objects": None,
        "query_names": [
            row["path"]
            for row in source["files"]
            if row["path"].startswith(codeql.SOURCE_PREFIX)
            and Path(row["path"]).suffix in {".ql", ".qll", ".qls"}
        ],
        "pack": pack,
        "cli": inspected["capability"]["installation_state"] == "bytes_verified",
        "reporting": source["reporting"]["interpreter_state"],
        "inspector": inspector,
        "build_tree": source["source_build"]["build_tree"],
    }
    retained = sum(len(raw_bytes(raw)) for raw in inspected["artifacts"])
    retained += sum(
        len(raw_bytes(phase[key])) for phase in inspected["phases"] for key in ("stdout", "stderr")
    )
    budget = Budget(selected.request["output_limit_bytes"], 64 * 1024 * 1024 - retained)
    with temporary_directory(prefix="score-codeql-review-refreeze-") as temporary:
        codeql._refreeze(selected, inspected, Path(temporary), budget)
    inspected["gaps"] = sorted(set(inspected["gaps"]))
    inspected = seal(inspected)
    validate_inspection(inspected)
    state, reasons = classify(original, draft, inspected, action, observed)
    record = seal({**record, "inspection": inspected, "state": state, "reasons": reasons})
    if len(canonical(record)) > dm.MAX_RECORD:
        raise InputError("LIMIT_EXCEEDED", "CodeQL review exceeds 96 MiB")
    if read_control(request_path) != request_bytes:
        raise InputError("INPUT_DRIFT", "Disposition request changed during final context check")
    selected_control(base, request["origin"], max_bytes=dm.MAX_RECORD)
    selected_control(base, request["draft"])
    if request["previous"] is not None:
        _history(base, request["previous"], draft, subject)
    for key in ("compensating_evidence", "decision_refs"):
        for ref in draft[key]:
            input_file(draft_path.parent, ref, "/draft/" + key)
    if out is not None:
        output_path(out, inputs, protected)
    return 1, record, inputs, protected
