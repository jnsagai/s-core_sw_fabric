"""Pure consistency replay of retained, unprotected Git inspection observations."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.models import raw_bytes


def verify_observations(record: dict[str, Any]) -> None:
    """Compare summaries with originals; neither self-digests nor Git labels authenticate them."""
    config = record["configuration"]["effective"]
    source = record["source_inspection"]
    build = source["source_build"]
    pack = record["pack_inspection"]
    originals: dict[str, str | None] = {}

    def output(phase: dict[str, Any]) -> str | None:
        if any(phase[key]["truncated"] for key in ("stdout", "stderr")):
            if "OUTPUT_TRUNCATED" not in record["gaps"]:
                raise InputError(
                    "CODEQL_INSPECTION", "Truncated original observation lacks its gap"
                )
            return None
        if phase["exit_code"] != 0 or phase["timed_out"] or phase["error"]:
            if "SOURCE_INSPECTION_PHASE_FAILED:" + phase["name"] not in record["gaps"]:
                raise InputError("CODEQL_INSPECTION", "Failed original observation lacks its gap")
            return None
        try:
            return raw_bytes(phase["stdout"]).decode("utf-8").strip()
        except UnicodeDecodeError as exc:
            raise InputError("CODEQL_INSPECTION", "Original Git observation is not UTF-8") from exc

    metadata = None if pack is None else pack["identity"].get("buildMetadata")
    if pack is not None and not isinstance(metadata, dict):
        raise InputError("CODEQL_INSPECTION", "Original pack build metadata is invalid")
    declared = None if metadata is None else metadata.get("sha")
    if declared != build["declared_build_commit"]:
        raise InputError("CODEQL_INSPECTION", "Declared build commit differs from original pack")
    commands = {
        "head": ["rev-parse", "HEAD"],
        "tree": ["rev-parse", "HEAD^{tree}"],
        "status": ["status", "--porcelain", "--untracked-files=all"],
    }
    prefix = [
        "/usr/bin/git",
        "--no-optional-locks",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.hooksPath=/dev/null",
        "-C",
    ]
    for phase in record["phases"]:
        name, argv = phase["name"], phase["argv"]
        kind, _, suffix = name.partition(":")
        if kind in {"source", "refreeze"} and suffix in commands:
            expected = prefix + [config["source_root"], *commands[suffix]]
        elif name == "source:tracked":
            expected = prefix + [config["source_root"], "ls-tree", "-r", "-z", "HEAD", "--"]
            if argv[: len(expected)] != expected or len(argv) <= len(expected):
                raise InputError("CODEQL_INSPECTION", "Original tracked-source command differs")
            expected = argv
        elif name in {"build:tree", "refreeze:build-tree"}:
            if declared is None or config["build_source_root"] is None:
                raise InputError("CODEQL_INSPECTION", "Unexpected build-tree observation")
            expected = prefix + [config["build_source_root"], "rev-parse", declared + "^{tree}"]
        else:
            raise InputError("CODEQL_INSPECTION", "Unknown original inspection phase")
        if argv != expected:
            raise InputError("CODEQL_INSPECTION", "Original observation command or source differs")
        observed = output(phase)
        if kind != "refreeze":
            if name in originals:
                raise InputError("CODEQL_INSPECTION", "Duplicate original source observation")
            originals[name] = observed
        else:
            original_name = "build:tree" if suffix == "build-tree" else "source:" + suffix
            if original_name not in originals or observed != originals[original_name]:
                raise InputError("CODEQL_INSPECTION", "Refrozen observation differs from original")
    if not {"source:head", "source:tree", "source:status", "source:tracked"} <= originals.keys():
        raise InputError("CODEQL_INSPECTION", "Required original source observation is missing")
    head, tree, status = (originals["source:" + name] for name in ("head", "tree", "status"))
    if (
        (head is not None and head != source["commit"])
        or tree != source["tree"]
        or (status is not None and status != "")
        or source["status"] != ("unknown" if status is None else "clean")
        or build["locked_tree"] != tree
    ):
        raise InputError("CODEQL_INSPECTION", "Original Git state differs from source summary")
    observed_build = originals.get("build:tree")
    if (
        declared is not None
        and config["build_source_root"] is not None
        and "build:tree" not in originals
    ):
        raise InputError("CODEQL_INSPECTION", "Required original build observation is missing")
    if observed_build != build["build_tree"]:
        raise InputError("CODEQL_INSPECTION", "Build tree differs from original observation")
    tracked = originals["source:tracked"]
    source_valid = all(value is not None for value in (head, tree, status, tracked))
    relation = (
        "unknown"
        if not source_valid or observed_build is None
        else ("source_trees_equal" if observed_build == tree else "source_trees_different")
    )
    if build["state"] != relation:
        raise InputError("CODEQL_INSPECTION", "Source/build relation differs from observations")
    if tracked is not None:
        names = set()
        for entry in tracked.split("\0"):
            if not entry:
                continue
            fields, separator, name = entry.partition("\t")
            values = fields.split()
            if (
                not separator
                or len(values) != 3
                or values[1] != "blob"
                or re.fullmatch(r"[a-f0-9]{40}", values[2]) is None
                or name in names
            ):
                raise InputError(
                    "CODEQL_INSPECTION", "Malformed original tracked-source observation"
                )
            names.add(name)
        selected_names = {row["path"] for row in source["files"]}
        if not selected_names <= names:
            raise InputError(
                "CODEQL_INSPECTION", "Selected source is absent from original Git tree"
            )

        def queries(items: set[str]) -> set[str]:
            return {
                name
                for name in items
                if name.startswith("cpp/misra/src/")
                and Path(name).suffix in {".ql", ".qll", ".qls"}
            }

        if queries(names) != queries(selected_names):
            raise InputError("CODEQL_INSPECTION", "Original query source closure differs")
    if not source_valid and "NATIVE_SOURCE_IDENTITY_UNKNOWN" not in record["gaps"]:
        raise InputError("CODEQL_INSPECTION", "Unavailable native source identity lacks its gap")
