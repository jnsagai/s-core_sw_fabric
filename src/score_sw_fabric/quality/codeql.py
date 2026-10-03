"""Read-only CodeQL prerequisites: installation bytes never unlock native analysis."""

from __future__ import annotations

import hashlib
import os
import re
import stat
from pathlib import Path
from typing import Any

from score_sw_fabric.agents.models import relative_path, string_list
from score_sw_fabric.assurance.models import seal
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.codeql_models import parse_control, read_control
from score_sw_fabric.quality.import_models import bounded_tree
from score_sw_fabric.quality.models import (
    MAX_ARTIFACT,
    MAX_TOTAL,
    Budget,
    Inputs,
    baseline,
    digest,
    environment,
    execute,
    load_inputs,
    raw_bytes,
)
from score_sw_fabric.runtime.models import output_path
from score_sw_fabric.runtime.request import _local
from score_sw_fabric.storage import temporary_directory

INSPECTOR = Path("/usr/bin/git")
SOURCE_PREFIX = "cpp/misra/src/"
REQUIREMENTS = ["scripts/reports/requirements.txt", "scripts/configuration/requirements.txt"]
SOURCE_CONTROLS = [
    "LICENSE.md",
    "docs/user_manual.md",
    "supported_codeql_configs.json",
    *REQUIREMENTS,
    "scripts/reports/utils.py",
]


def _file(path: Path, limit: int = MAX_ARTIFACT, *, git_blob: bool = False) -> dict[str, Any]:
    _local(path.parent, str(path.absolute()), "/native_file")
    try:
        before = path.stat()
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise InputError("LIMIT_EXCEEDED", "Native identity file is not bounded and regular")
        total, identity = 0, hashlib.sha256()
        blob = hashlib.sha1(usedforsecurity=False)
        blob.update(f"blob {before.st_size}\0".encode())
        with path.open("rb") as stream:
            while data := stream.read(1024 * 1024):
                total += len(data)
                if total > limit:
                    raise InputError("LIMIT_EXCEEDED", "Native identity file grew past its bound")
                identity.update(data)
                if git_blob:
                    blob.update(data)
        after = path.stat()
        keys = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        if total != before.st_size or any(getattr(before, k) != getattr(after, k) for k in keys):
            raise InputError("INPUT_DRIFT", "Native identity changed during measurement")
        return {
            "path": str(path),
            "sha256": identity.hexdigest(),
            "bytes": total,
            **({"git_object": blob.hexdigest()} if git_blob else {}),
        }
    except OSError as exc:
        raise InputError("INPUT_UNAVAILABLE", "Cannot measure native identity") from exc


def _names(root: Path) -> list[str]:
    pending, names, nodes = [root], [], 0
    while pending:
        current = pending.pop()
        _local(current.parent, str(current.absolute()), "/native_root")
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    nodes += 1
                    if nodes > 10000:
                        raise InputError(
                            "LIMIT_EXCEEDED", "Native directory entry count exceeds its bound"
                        )
                    path = Path(entry.path)
                    name = relative_path(path.relative_to(root).as_posix(), "/native_path")
                    if any(ord(character) < 32 or ord(character) == 127 for character in name):
                        raise InputError(
                            "INPUT_PATH", "Native paths cannot contain control characters"
                        )
                    if any(part.startswith("-") or part == ".git" for part in Path(name).parts):
                        raise InputError(
                            "INPUT_PATH", "Metadata and option-shaped paths are unsupported"
                        )
                    if entry.is_symlink():
                        raise InputError(
                            "INPUT_PATH", "Native identity trees cannot contain symlinks"
                        )
                    if entry.is_dir(follow_symlinks=False):
                        pending.append(path)
                    elif entry.is_file(follow_symlinks=False):
                        names.append(name)
                        if len(names) > 5000:
                            raise InputError("LIMIT_EXCEEDED", "Native file count exceeds 5000")
                    else:
                        raise InputError("INPUT_NOT_FILE", "Special native files are unsupported")
        except OSError as exc:
            raise InputError("INPUT_UNAVAILABLE", "Cannot enumerate native identity tree") from exc
    return sorted(names)


def _manifest(
    root: Path, names: list[str], git_objects: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    rows, total = [], 0
    for name in sorted(set(names)):
        relative_path(name, "/native_path")
        row = {**_file(root / name, git_blob=git_objects is not None), "path": name}
        if git_objects is not None and row.pop("git_object") != git_objects.get(name):
            raise InputError("NATIVE_SOURCE_DRIFT", "Selected source differs from its Git blob")
        total += row["bytes"]
        if total > MAX_TOTAL:
            raise InputError("LIMIT_EXCEEDED", "Native identity manifest exceeds 64 MiB")
        rows.append(row)
    return rows


def _chain(chain: dict[str, Any]) -> bool:
    available = True
    for row in [chain["tool"], *chain["dependencies"]]:
        path = Path(row["path"])
        _local(path.parent, str(path), "/tool")
        if not path.exists():
            available = False
            continue
        if _file(path, 512 * 1024 * 1024)["sha256"] != row["sha256"]:
            raise InputError(
                "TOOL_IDENTITY_MISMATCH", "Tool or runtime identity differs from selection"
            )
    return available


def _git(
    selected: Inputs,
    record: dict[str, Any],
    work: Path,
    budget: Budget,
    name: str,
    root: Path,
    *args: str,
) -> str | None:
    env = environment(work, {"library_dirs": []})
    env.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL="/dev/null",
        GIT_OPTIONAL_LOCKS="0",
        GIT_TERMINAL_PROMPT="0",
    )
    phase = execute(
        name,
        [
            str(INSPECTOR),
            "--no-optional-locks",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.hooksPath=/dev/null",
            "-C",
            str(root),
            *args,
        ],
        work,
        selected.request["timeout_seconds"],
        budget,
        env,
    )
    record["phases"].append(phase)
    if any(phase[key]["truncated"] for key in ("stdout", "stderr")):
        record["gaps"].append("OUTPUT_TRUNCATED")
        return None
    if phase["exit_code"] != 0 or phase["timed_out"] or phase["error"]:
        record["gaps"].append("SOURCE_INSPECTION_PHASE_FAILED:" + name)
        return None
    try:
        return raw_bytes(phase["stdout"]).decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise InputError("NATIVE_SOURCE_UNSUPPORTED", "Git source identity is not UTF-8") from exc


def _state(
    selected: Inputs, record: dict[str, Any], work: Path, budget: Budget, prefix: str
) -> tuple[str | None, str | None, str | None]:
    root = Path(selected.settings["effective"]["source_root"])
    head = _git(selected, record, work, budget, prefix + ":head", root, "rev-parse", "HEAD")
    tree = _git(selected, record, work, budget, prefix + ":tree", root, "rev-parse", "HEAD^{tree}")
    status = _git(
        selected,
        record,
        work,
        budget,
        prefix + ":status",
        root,
        "status",
        "--porcelain",
        "--untracked-files=all",
    )
    if head is not None and head != selected.settings["source"]["commit"]:
        raise InputError("NATIVE_SOURCE_DRIFT", "Native source HEAD differs from the selected lock")
    if status:
        raise InputError("NATIVE_SOURCE_DRIFT", "Native source checkout is not clean")
    if tree is not None and not re.fullmatch(r"[a-f0-9]{40}", tree):
        raise InputError("NATIVE_SOURCE_UNSUPPORTED", "Git tree identity must be full")
    return head, tree, status


def _suite(root: Path, name: str) -> dict[str, Any]:
    imports: list[dict[str, Any]] = []
    excluded: set[str] = set()
    included: set[str] = set()
    seen: set[str] = set()

    def read(path: str, depth: int) -> tuple[str, list[dict[str, Any]]]:
        if depth > 8 or len(seen) >= 16 or path in seen:
            raise InputError("SUITE_UNSUPPORTED", "Native suite imports are cyclic or excessive")
        if not re.fullmatch(r"codeql-suites/[A-Za-z0-9][A-Za-z0-9_.-]*\.qls", path):
            raise InputError(
                "SUITE_UNSUPPORTED", "Native suite import is outside the selected pack"
            )
        seen.add(path)
        data = read_control(root / path, "/suite")
        definition = parse_control(data, "/suite")
        if (
            not isinstance(definition, list)
            or not 1 <= len(definition) <= 64
            or any(not isinstance(row, dict) for row in definition)
        ):
            raise InputError("SUITE_UNSUPPORTED", "Native suite must contain bounded directives")
        for row in definition:
            for key, target in (("include", included), ("exclude", excluded)):
                if key in row:
                    if not isinstance(row[key], dict):
                        raise InputError("SUITE_UNSUPPORTED", "Suite filter must be a mapping")
                    tags = row[key].get("tags contain", [])
                    target.update(string_list(tags, "/suite/tags", limit=100, length=256))
            if "import" in row:
                imported = relative_path(row["import"], "/suite/import")
                identity, value = read(imported, depth + 1)
                imports.append({"path": imported, "sha256": identity, "definition": value})
        return digest(data), definition

    identity, definition = read(name, 0)
    return {
        "path": name,
        "sha256": identity,
        "definition": definition,
        "imports": sorted(imports, key=lambda row: row["path"]),
        "excluded_tags": sorted(excluded),
        "included_tags": sorted(included),
    }


def _pack(
    selected: Inputs, source_files: list[dict[str, Any]], source_suite: dict[str, Any]
) -> dict[str, Any] | None:
    c = selected.settings["effective"]
    if c["compiled_pack_root"] is None or not Path(c["compiled_pack_root"]).exists():
        return None
    root = Path(c["compiled_pack_root"])
    manifest = _manifest(root, _names(root))
    identity = parse_control(read_control(root / "qlpack.yml", "/pack/identity"), "/pack/identity")
    lock = parse_control(read_control(root / "codeql-pack.lock.yml", "/pack/lock"), "/pack/lock")
    if (
        not isinstance(identity, dict)
        or identity.get("name") != "codeql/misra-cpp-coding-standards"
        or identity.get("version") != "2.61.0"
    ):
        raise InputError("QUERY_PACK_IDENTITY_MISMATCH", "Select the researched MISRA pack 2.61.0")
    metadata = identity.get("buildMetadata")
    if (
        not isinstance(metadata, dict)
        or metadata.get("cliVersion") != "2.21.4"
        or not isinstance(metadata.get("sha"), str)
        or not re.fullmatch(r"[a-f0-9]{40}", metadata["sha"])
    ):
        raise InputError(
            "QUERY_PACK_IDENTITY_MISMATCH", "Pack build CLI/commit identities are unsupported"
        )
    if (
        not isinstance(lock, dict)
        or lock.get("compiled") is not True
        or not isinstance(lock.get("dependencies"), dict)
        or len(lock["dependencies"]) > 32
    ):
        raise InputError(
            "QUERY_PACK_IDENTITY_MISMATCH", "Compiled pack dependency lock is required"
        )
    suites = _suite(root, c["suite"])
    if suites != source_suite:
        raise InputError(
            "QUERY_PACK_IDENTITY_MISMATCH", "Installed suite differs from selected native source"
        )
    indexed = {row["path"]: row for row in manifest}
    libraries, library_gaps = [], []
    for name, entry in sorted(lock["dependencies"].items()):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", name) or any(
            part.startswith("-") for part in name.split("/")
        ):
            raise InputError("QUERY_PACK_IDENTITY_MISMATCH", "Native library name is unsupported")
        version = entry.get("version") if isinstance(entry, dict) else None
        if not isinstance(version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
            raise InputError(
                "QUERY_PACK_IDENTITY_MISMATCH", "Native library version is unsupported"
            )
        path = f".codeql/libraries/{name}/{version}/qlpack.yml"
        if path not in indexed:
            library_gaps.append("LIBRARY_UNAVAILABLE:" + name)
            continue
        original = parse_control(read_control(root / path, "/library"), "/library")
        if (
            not isinstance(original, dict)
            or original.get("name") != name
            or original.get("version") != version
        ):
            raise InputError(
                "QUERY_PACK_IDENTITY_MISMATCH", "Embedded library differs from the native lock"
            )
        libraries.append({**indexed[path], "name": name, "version": version, "metadata": original})
    queries = [
        row
        for row in source_files
        if row["path"].startswith(SOURCE_PREFIX)
        and Path(row["path"]).suffix in {".ql", ".qll", ".qls"}
    ]
    for row in queries:
        local = row["path"][len(SOURCE_PREFIX) :]
        expected = {**row, "path": local}
        if indexed.get(local) != expected:
            raise InputError(
                "QUERY_PACK_IDENTITY_MISMATCH", "Installed query source differs from native source"
            )
    return {
        "root": str(root),
        "manifest": manifest,
        "manifest_digest": digest(canonical(manifest)),
        "identity": identity,
        "lock": lock,
        "suite": suites,
        "included_source_state": "matched",
        "included_source_count": len(queries),
        "compiled_artifact_provenance": "unverified",
        "libraries": libraries,
        "library_state": "incomplete" if library_gaps else "matched",
        "library_gaps": library_gaps,
    }


def inspect(selected: Inputs, work: Path, budget: Budget) -> dict[str, Any]:
    c, source = selected.settings["effective"], selected.settings["source"]
    cli = _chain(selected.toolchain)
    inspector = _file(INSPECTOR, 512 * 1024 * 1024)
    record: dict[str, Any] = {
        "schema_version": 1,
        "kind": "quality_codeql_capability_inventory",
        "profile": selected.profile,
        "toolchain": selected.toolchain,
        "configuration": {"selection": selected.request["config"], "effective": c},
        "phases": [],
        "artifacts": [],
        "gaps": list(selected.profile["required_obligations"]),
        "outcome": "unavailable",
        "origin": "local_unprotected_inspection",
        "assurance_eligibility": "not_eligible",
        "engineering_readiness": "not_evaluated",
        "accepted_claims": 0,
        "analysis_executed": False,
        "inspector": {
            "path": inspector["path"],
            "sha256": inspector["sha256"],
            "qualification": "unknown",
        },
        "limitations": [
            "No CodeQL CLI, database, query, build, patch or reporting interpreter executes.",
            "Original suite/configuration filters are retained; applicability is unreviewed.",
            "Selected launcher/dependency bytes do not qualify the full CLI/runtime distribution.",
            "Source equality does not authenticate or reproduce compiled query artifacts.",
            "Eligibility originals are unverified; its gate is unimplemented.",
            "Native MISRA rule text and tool binaries are not redistributed.",
        ],
    }
    state = _state(selected, record, work, budget, "source")
    root = Path(c["source_root"])
    query_root = root / SOURCE_PREFIX
    query_names = [
        SOURCE_PREFIX + name
        for name in _names(query_root)
        if Path(name).suffix in {".ql", ".qll", ".qls"}
    ]
    tracked = _git(
        selected,
        record,
        work,
        budget,
        "source:tracked",
        root,
        "ls-tree",
        "-r",
        "-z",
        "HEAD",
        "--",
        SOURCE_PREFIX,
        *SOURCE_CONTROLS,
        *source["source_file_sha256"],
    )
    source_valid = all(value is not None for value in state) and tracked is not None
    git_objects: dict[str, str] | None = None
    if tracked is not None:
        git_objects = {}
        for entry in tracked.split("\0"):
            if not entry:
                continue
            fields, separator, path = entry.partition("\t")
            values = fields.split()
            if (
                not separator
                or len(values) != 3
                or values[1] != "blob"
                or not re.fullmatch(r"[a-f0-9]{40}", values[2])
            ):
                raise InputError(
                    "NATIVE_SOURCE_UNSUPPORTED", "Selected Git entries must be regular blobs"
                )
            git_objects[path] = values[2]
        tracked_names = sorted(
            name
            for name in git_objects
            if name.startswith(SOURCE_PREFIX) and Path(name).suffix in {".ql", ".qll", ".qls"}
        )
        if tracked_names != query_names:
            raise InputError(
                "NATIVE_SOURCE_DRIFT", "Native query file closure differs from the locked Git tree"
            )
    names = sorted(set(query_names + list(source["source_file_sha256"]) + SOURCE_CONTROLS))
    if not names or len(names) > 500:
        raise InputError("LIMIT_EXCEEDED", "Native source identities exceed 500 files")
    source_files = _manifest(root, names, git_objects)
    indexed = {row["path"]: row["sha256"] for row in source_files}
    if any(indexed[path] != expected for path, expected in source["source_file_sha256"].items()):
        raise InputError(
            "NATIVE_SOURCE_DRIFT", "Locked native source content differs from its hash"
        )
    manual = read_control(root / "docs/user_manual.md", "/native_manual")
    if b"A Python interpreter version 3.9" not in manual:
        raise InputError(
            "NATIVE_SOURCE_UNSUPPORTED", "Inspected reporting requirement is unavailable"
        )
    supported = parse_control(
        read_control(root / "supported_codeql_configs.json", "/supported_cli"), "/supported_cli"
    )
    if (
        not isinstance(supported, dict)
        or not isinstance(supported.get("supported_environment"), list)
        or not any(
            isinstance(row, dict) and row.get("codeql_cli") == "2.21.4"
            for row in supported["supported_environment"]
        )
    ):
        raise InputError(
            "NATIVE_SOURCE_UNSUPPORTED", "Native release does not declare the selected CLI"
        )
    suite = _suite(query_root, c["suite"])
    pack = _pack(selected, source_files, suite)
    if pack is not None and not source_valid:
        pack["included_source_state"] = "unknown"
    declared = pack["identity"]["buildMetadata"]["sha"] if pack is not None else None
    built = None
    if declared is not None and c["build_source_root"] is not None:
        built = _git(
            selected,
            record,
            work,
            budget,
            "build:tree",
            Path(c["build_source_root"]),
            "rev-parse",
            declared + "^{tree}",
        )
        if built is not None and not re.fullmatch(r"[a-f0-9]{40}", built):
            raise InputError(
                "NATIVE_SOURCE_UNSUPPORTED", "Declared build tree identity must be full"
            )
    relation = (
        "unknown"
        if not source_valid or built is None
        else ("source_trees_equal" if built == state[1] else "source_trees_different")
    )
    reporting = selected.settings["reporting"]
    reporting_state = (
        "not_selected"
        if reporting is None
        else ("bytes_verified" if _chain(reporting) else "unavailable")
    )
    provenance = "fixture" if source.get("verification") == "fixture" else "locked_source_selection"
    record["source_inspection"] = {
        "lock": c["source_lock"],
        "repository": source["repository"],
        "commit": source["commit"],
        "tree": state[1],
        "status": "unknown" if state[2] is None else "clean",
        "origin": provenance,
        "files": source_files,
        "files_digest": digest(canonical(source_files)),
        "matched_locked_sources": len(source["source_file_sha256"]),
        "source_build": {
            "locked_tree": state[1],
            "declared_build_commit": declared,
            "build_tree": built,
            "state": relation,
            "compiled_artifact_provenance": "unverified",
        },
        "reporting": {
            "manual_python_version": "3.9",
            "requirements": [row for row in source_files if row["path"] in REQUIREMENTS],
            "interpreter_state": reporting_state,
            "compatibility": "unexecuted",
            "eligibility_ref": c["eligibility"],
            "eligibility_state": "not_selected" if c["eligibility"] is None else "unverified",
        },
    }
    record["pack_inspection"] = pack
    scan = parse_control(selected.assets["scan_config"], "/scan_config")
    if not isinstance(scan, dict):
        raise InputError("CONFIG_UNSUPPORTED", "Native scan configuration must be a mapping")
    record["capability"] = {
        "state": "unavailable",
        "installation_state": "bytes_verified" if cli else "unavailable",
        "declared_cli_version": "2.21.4",
        "checks": [],
        "effective_config": scan,
        "suite_exclusions": suite["excluded_tags"],
        "analysis_state": "not_executed",
    }
    rows = [
        (
            "cli_selected_bytes",
            "available" if cli else "unavailable",
            [] if cli else ["CAPABILITY_UNAVAILABLE"],
        ),
        (
            "native_source_identity",
            "available" if source_valid else "unknown",
            [] if source_valid else ["NATIVE_SOURCE_IDENTITY_UNKNOWN"],
        ),
        (
            "compiled_pack_selected_bytes",
            "available" if pack is not None else "unavailable",
            [] if pack is not None else ["QUERY_PACK_UNAVAILABLE"],
        ),
        (
            "source_build_content",
            "available" if relation == "source_trees_equal" else "unknown",
            []
            if relation == "source_trees_equal"
            else [
                "SOURCE_BUILD_RECONCILIATION_UNKNOWN"
                if relation == "unknown"
                else "SOURCE_BUILD_CONTENT_DIFFERS"
            ],
        ),
        ("compiled_artifact_provenance", "unknown", ["COMPILED_ARTIFACT_PROVENANCE_UNVERIFIED"]),
        (
            "embedded_library_identities",
            "available"
            if pack is not None and pack["library_state"] == "matched"
            else "unavailable",
            pack["library_gaps"] if pack is not None else ["LIBRARY_CLOSURE_UNAVAILABLE"],
        ),
        ("library_source_provenance", "unknown", ["LIBRARY_SOURCE_RECONCILIATION_UNVERIFIED"]),
        ("cli_runtime_closure", "unknown", ["CODEQL_RUNTIME_CLOSURE_UNVERIFIED"]),
        ("project_use_eligibility", "unknown", ["CODEQL_ELIGIBILITY_UNKNOWN"]),
        (
            "reporting_interpreter_bytes",
            "available" if reporting_state == "bytes_verified" else "unavailable",
            []
            if reporting_state == "bytes_verified"
            else [
                "REPORTING_INTERPRETER_NOT_SELECTED"
                if reporting_state == "not_selected"
                else "REPORTING_INTERPRETER_UNAVAILABLE"
            ],
        ),
        ("native_report_compatibility", "unknown", ["NATIVE_REPORTING_UNEXECUTED"]),
        ("execution_adapter", "unavailable", ["CODEQL_EXECUTION_UNIMPLEMENTED"]),
        ("native_configuration_adoption", "unknown", ["CODEQL_CONFIGURATION_REVIEW_PENDING"]),
    ]
    record["prerequisites"] = [
        {"id": identifier, "state": value, "reasons": reasons}
        for identifier, value, reasons in rows
    ]
    record["gaps"].extend(reason for _, _, reasons in rows for reason in reasons)
    record["gaps"].extend("SUITE_EXCLUDES:" + tag for tag in suite["excluded_tags"])
    if provenance == "fixture":
        record["gaps"].append("FIXTURE_NATIVE_SOURCE")
    elif source.get("verification") != "source_inspected":
        record["gaps"].append("NATIVE_SOURCE_PROVENANCE_UNKNOWN")
    for key, data in sorted(selected.assets.items()):
        if key.startswith("_"):
            continue
        if key in {"profile", "toolchain", "configuration"}:
            path = selected.request["config" if key == "configuration" else key]["path"]
        else:
            path = c[key]["path"]
        record["artifacts"].append({"id": key, "path": path, **budget.capture(data)})
    for identifier, control_path in [
        ("native-license", root / "LICENSE.md"),
        *(
            ("native-requirements-" + str(index), root / name)
            for index, name in enumerate(REQUIREMENTS)
        ),
    ]:
        record["artifacts"].append(
            {
                "id": identifier,
                "path": str(control_path),
                **budget.capture(read_control(control_path, "/native_control")),
            }
        )
    if pack is not None:
        pack_root = Path(pack["root"])
        controls = [
            "qlpack.yml",
            "codeql-pack.lock.yml",
            c["suite"],
            *[row["path"] for row in pack["suite"]["imports"]],
        ]
        for index, name in enumerate(controls):
            path = pack_root / name
            record["artifacts"].append(
                {
                    "id": "pack-control-" + str(index),
                    "path": str(path),
                    **budget.capture(read_control(path, "/pack_control")),
                }
            )
        for index, library in enumerate(pack["libraries"]):
            path = pack_root / library["path"]
            record["artifacts"].append(
                {
                    "id": "pack-library-" + str(index),
                    "path": str(path),
                    **budget.capture(read_control(path, "/pack_library")),
                }
            )
    if any(row["truncated"] for row in record["artifacts"]):
        record["gaps"].append("OUTPUT_TRUNCATED")
    selected.settings["_observed"] = {
        "state": state,
        "source_names": names,
        "source_files": source_files,
        "git_objects": git_objects,
        "query_names": query_names,
        "pack": pack,
        "cli": cli,
        "reporting": reporting_state,
        "inspector": inspector,
        "build_tree": built,
    }
    return record


def _refreeze(selected: Inputs, record: dict[str, Any], work: Path, budget: Budget) -> None:
    observed, c = selected.settings["_observed"], selected.settings["effective"]
    root = Path(c["source_root"])
    names = [
        SOURCE_PREFIX + name
        for name in _names(root / SOURCE_PREFIX)
        if Path(name).suffix in {".ql", ".qll", ".qls"}
    ]
    if (
        names != observed["query_names"]
        or _manifest(root, observed["source_names"], observed["git_objects"])
        != observed["source_files"]
    ):
        raise InputError("INPUT_DRIFT", "Native source closure changed before publication")
    pack = observed["pack"]
    if pack is None:
        if c["compiled_pack_root"] is not None and Path(c["compiled_pack_root"]).exists():
            raise InputError("INPUT_DRIFT", "Native pack availability changed before publication")
    elif _manifest(Path(pack["root"]), _names(Path(pack["root"]))) != pack["manifest"]:
        raise InputError("INPUT_DRIFT", "Native pack closure changed before publication")
    if _state(selected, record, work, budget, "refreeze") != observed["state"]:
        raise InputError("INPUT_DRIFT", "Native Git state changed before publication")
    declared = record["source_inspection"]["source_build"]["declared_build_commit"]
    if declared is not None and c["build_source_root"] is not None:
        current_tree = _git(
            selected,
            record,
            work,
            budget,
            "refreeze:build-tree",
            Path(c["build_source_root"]),
            "rev-parse",
            declared + "^{tree}",
        )
        if current_tree != observed["build_tree"]:
            raise InputError("INPUT_DRIFT", "Declared build Git tree changed before publication")
    if _chain(selected.toolchain) != observed["cli"]:
        raise InputError("INPUT_DRIFT", "CLI availability changed before publication")
    reporting = selected.settings["reporting"]
    current = (
        "not_selected"
        if reporting is None
        else ("bytes_verified" if _chain(reporting) else "unavailable")
    )
    if (
        current != observed["reporting"]
        or _file(INSPECTOR, 512 * 1024 * 1024) != observed["inspector"]
    ):
        raise InputError("INPUT_DRIFT", "Inspector/reporting identity changed before publication")
    for path, expected in selected.settings["_controls"].items():
        if read_control(path, "/control_refreeze") != expected:
            raise InputError("INPUT_DRIFT", "Selected control changed before publication")
    if selected.data:
        component = Path(selected.request["root"])
        for name, data in selected.data.items():
            if _file(component / name, MAX_TOTAL)["sha256"] != digest(data):
                raise InputError("BASELINE_DRIFT", "Component source changed before publication")


def _inspect(
    request_path: Path, operation: str, out: Path | None
) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    request_bytes = read_control(request_path, "/request")
    selected = load_inputs(request_path, operation, "codeql")
    c = selected.settings["effective"]
    controls = {request_path.absolute(): request_bytes}
    for index, key in enumerate(("profile", "toolchain", "configuration")):
        controls[selected.inputs[index]] = selected.assets[key]
    config_base = selected.inputs[2].parent
    for key in ("source_lock", "scan_config", "report_patch", "reporting_toolchain", "eligibility"):
        if c[key] is not None:
            controls[_local(config_base, c[key]["path"], "/control")] = selected.assets[key]
    selected.settings["_controls"] = controls
    selected.inputs.append(INSPECTOR)
    if out is not None:
        output_path(out, [request_path, *selected.inputs], selected.protected)
    budget = Budget(selected.request["output_limit_bytes"])
    with temporary_directory(prefix="score-codeql-inspection-") as temporary:
        work = Path(temporary)
        record = inspect(selected, work, budget)
        _refreeze(selected, record, work, budget)
    if operation == "run":
        record.update(
            kind="quality_codeql_analysis_run",
            baseline=baseline(selected),
            processed_units=[],
            diagnostics=[],
            source_integrity="unchanged",
            extraction={
                "expected_state": "unknown"
                if selected.request["expected_units"] is None
                else "declared",
                "expected_units": selected.request["expected_units"],
                "processed_units": [],
                "missing_units": selected.request["expected_units"] or [],
                "unexpected_units": [],
                "adequacy": "unknown",
                "limitations": [
                    "Extraction/queries did not execute; empty findings are not clean evidence."
                ],
            },
        )
        record["gaps"].extend(["EXTRACTION_UNKNOWN", *selected.gaps])
    record["gaps"] = sorted(set(record["gaps"]))
    bounded_tree(record)
    if len(canonical(record)) > 96 * 1024 * 1024:
        raise InputError("LIMIT_EXCEEDED", "CodeQL inspection record exceeds 96 MiB")
    return 1, seal(record), selected.inputs, selected.protected


def capabilities(
    request_path: Path, out: Path | None = None
) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    return _inspect(request_path, "capabilities", out)


def run(
    request_path: Path, out: Path | None = None
) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    raw = parse_control(read_control(request_path, "/request"), "/request")
    if isinstance(raw, dict) and raw.get("kind") == "quality_codeql_demonstration_request":
        from score_sw_fabric.quality.codeql_demonstration import run as demonstrate

        return demonstrate(request_path, out)
    return _inspect(request_path, "run", out)
