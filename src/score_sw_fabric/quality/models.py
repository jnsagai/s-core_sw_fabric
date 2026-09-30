"""Strict inputs and bounded native process capture for the Clang-Tidy slice."""

from __future__ import annotations

import base64
import hashlib
import os
import re
import selectors
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from score_sw_fabric.agents.models import (
    input_file,
    load_request,
    local_dir,
    protected_roots,
    relative_path,
    string_list,
)
from score_sw_fabric.assurance.models import stable_id
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.profile import load_profile, load_toolchain
from score_sw_fabric.runtime.request import parse_yaml
from score_sw_fabric.verification.design import root_files

CAPABILITY_FIELDS = {
    "profile",
    "toolchain",
    "config",
    "timeout_seconds",
    "output_limit_bytes",
    "protected_roots",
}
RUN_FIELDS = CAPABILITY_FIELDS | {
    "component",
    "root",
    "files",
    "translation_units",
    "expected_units",
    "include_dirs",
    "defines",
}
MAX_ARTIFACT = 16 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024


@dataclass
class Inputs:
    request: dict[str, Any]
    profile: dict[str, Any]
    toolchain: dict[str, Any]
    config: bytes
    inputs: list[Path]
    protected: list[Path]
    data: dict[str, bytes] = field(default_factory=dict)
    gaps: list[str] = field(default_factory=list)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    try:
        if not path.is_file() or path.stat().st_size > 512 * 1024 * 1024:
            raise InputError("TOOL_UNAVAILABLE", "Tool asset is absent or too large")
        with path.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()
    except OSError as exc:
        raise InputError("TOOL_UNAVAILABLE", "Cannot read tool asset") from exc


def _unique_paths(value: Any, pointer: str, limit: int = 500) -> list[str]:
    paths = [relative_path(p, pointer) for p in string_list(value, pointer, limit=limit)]
    if len(paths) != len(set(paths)):
        raise InputError("DUPLICATE_ID", "Duplicate selected path", pointer)
    return paths


def load_inputs(path: Path, operation: str) -> Inputs:
    kind = "quality_capability_request" if operation == "capabilities" else "quality_run_request"
    fields = CAPABILITY_FIELDS if operation == "capabilities" else RUN_FIELDS
    r, base = load_request(path, kind, fields)
    for key, low, high in [
        ("timeout_seconds", 1, 3600),
        ("output_limit_bytes", 1024, MAX_ARTIFACT),
    ]:
        if type(r[key]) is not int or not low <= r[key] <= high:
            raise InputError("LIMIT_EXCEEDED", f"Invalid {key}", f"/{key}")
    pp, pb = input_file(base, r["profile"], "/profile")
    tp, tb = input_file(base, r["toolchain"], "/toolchain")
    cp, cb = input_file(base, r["config"], "/config")
    if len(pb) > 1024 * 1024 or len(tb) > 1024 * 1024 or len(cb) > 1024 * 1024:
        raise InputError("LIMIT_EXCEEDED", "Profile/configuration too large")
    profile, chain = load_profile(pb), load_toolchain(tb)
    native_config = next(s for s in profile["native_sources"] if s["id"] == "clang_tidy")
    if digest(cb) != native_config["sha256"]:
        raise InputError(
            "CONFIG_IDENTITY_MISMATCH", "Configuration differs from pinned native bytes"
        )
    config = parse_yaml(cb, "/config")
    if not isinstance(config, dict) or any(k in config for k in ("ExtraArgs", "ExtraArgsBefore")):
        raise InputError("CONFIG_UNSUPPORTED", "Extra compiler arguments are unsupported")
    if config.get("InheritParentConfig"):
        raise InputError("CONFIG_UNSUPPORTED", "Parent configuration inheritance is unsupported")
    selected = Inputs(
        r,
        profile,
        chain,
        cb,
        [pp, tp, cp],
        protected_roots(base, r["protected_roots"], "/protected_roots"),
    )
    selected.inputs.extend(Path(d["path"]) for d in [chain["tool"], *chain["dependencies"]])
    selected.protected.extend(Path(d) for d in chain["library_dirs"])
    if operation == "capabilities":
        return selected
    stable_id(r["component"], "/component")
    root = local_dir(base, r["root"], "/root")
    if not isinstance(r["files"], list) or not 1 <= len(r["files"]) <= 500:
        raise InputError("LIMIT_EXCEEDED", "Source selection must contain 1–500 bounded files")
    total = 0
    for raw in r["files"]:
        _, groups = root_files(base, r["root"], {"files": [raw]})
        for name, data in groups["files"].data.items():
            if name in selected.data:
                raise InputError("DUPLICATE_ID", "Duplicate selected source")
            total += len(data)
            if total > MAX_TOTAL:
                raise InputError("LIMIT_EXCEEDED", "Combined sources exceed 64 MiB")
            selected.data[name] = data
    for name in selected.data:
        if (
            name.startswith(".git/")
            or name == ".git"
            or any(p.startswith("-") for p in name.split("/"))
        ):
            raise InputError("INPUT_PATH", "Metadata/options are not source paths")
    selected.inputs.extend(root / name for name in selected.data)
    selected.protected.append(root)
    r["root"] = str(root)
    units = _unique_paths(r["translation_units"], "/translation_units")
    if not units or any(
        u not in selected.data or Path(u).suffix not in {".cpp", ".cc", ".cxx"} for u in units
    ):
        raise InputError("INPUT_PATH", "Translation units must be selected C++ sources")
    if r["expected_units"] is not None:
        expected = _unique_paths(r["expected_units"], "/expected_units")
        if any(u not in selected.data for u in expected):
            raise InputError("INPUT_PATH", "Expected units must be selected files")
    includes = _unique_paths(r["include_dirs"], "/include_dirs", 32)
    for d in includes:
        if not any(p.startswith(d + "/") for p in selected.data):
            raise InputError("INPUT_PATH", "Include directory has no selected files")
    defines = string_list(r["defines"], "/defines", limit=64, length=256)
    if any(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:=-?[0-9]+)?", d) is None for d in defines):
        raise InputError("FIELD_TYPE", "Only identifier/integer defines are supported")
    for name, data in selected.data.items():
        text = data.decode("utf-8", "replace")
        if re.search(r"\bNOLINT(?:NEXTLINE|BEGIN|END)?\b", text):
            selected.gaps.append("UNAPPROVED_SUPPRESSION")
        for match in re.finditer(
            r'^\s*#\s*(?:include|include_next)\s+([<"])([^>"\n]+)[>"]', text, re.M
        ):
            target = relative_path(match[2], "/source/include")
            if match[1] == '"':
                candidates = [
                    str(Path(name).parent / target),
                    target,
                    *(f"{d}/{target}" for d in includes),
                ]
                if not any(p in selected.data for p in candidates):
                    selected.gaps.append("UNDECLARED_LOCAL_INCLUDE")
        if re.search(r'^\s*#\s*(?:include|include_next)\s+[^<"\s]', text, re.M):
            selected.gaps.append("DYNAMIC_INCLUDE_UNKNOWN")
        if re.search(r"^\s*#\s*include_next\b", text, re.M):
            selected.gaps.append("INCLUDE_NEXT_UNSUPPORTED")
    return selected


@dataclass
class Budget:
    per_artifact: int
    remaining: int = MAX_TOTAL

    def capture(self, data: bytes, format: str = "text") -> dict[str, Any]:
        acc = Accumulator(self, format)
        acc.add(data)
        return acc.record()


class Accumulator:
    def __init__(self, budget: Budget, format: str) -> None:
        self.budget, self.format = budget, format
        self.prefix = bytearray()
        self.hash = hashlib.sha256()
        self.bytes = 0

    def add(self, data: bytes) -> None:
        self.bytes += len(data)
        self.hash.update(data)
        keep = min(len(data), self.budget.per_artifact - len(self.prefix), self.budget.remaining)
        self.prefix.extend(data[:keep])
        self.budget.remaining -= keep

    def record(self) -> dict[str, Any]:
        prefix = bytes(self.prefix)
        return {
            "format": self.format,
            "bytes": self.bytes,
            "sha256": self.hash.hexdigest(),
            "retained_sha256": digest(prefix),
            "base64": base64.b64encode(prefix).decode(),
            "truncated": self.bytes > len(prefix),
        }


def raw_bytes(artifact: dict[str, Any]) -> bytes:
    return base64.b64decode(artifact["base64"], validate=True)


def environment(work: Path, chain: dict[str, Any]) -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin",
        "LC_ALL": "C",
        "LANG": "C",
        "HOME": str(work / "home"),
        "TMPDIR": str(work),
        "LD_LIBRARY_PATH": ":".join(chain["library_dirs"]),
    }


def execute(
    name: str, argv: list[str], work: Path, timeout: int, budget: Budget, env: dict[str, str]
) -> dict[str, Any]:
    """Drain pipes with bounded retention/full-stream hashing; kill the process group on timeout."""
    captures = {key: Accumulator(budget, "text") for key in ("stdout", "stderr")}
    started = time.monotonic()
    timed_out = False
    code: int | None = None
    error: str | None = None
    try:
        with subprocess.Popen(
            argv,
            cwd=work,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        ) as process:
            with selectors.DefaultSelector() as selector:
                for key, pipe in (("stdout", process.stdout), ("stderr", process.stderr)):
                    assert pipe is not None
                    os.set_blocking(pipe.fileno(), False)
                    selector.register(pipe, selectors.EVENT_READ, key)
                while selector.get_map() or process.poll() is None:
                    if not timed_out and time.monotonic() - started >= timeout:
                        timed_out = True
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    if timed_out and time.monotonic() - started > timeout + 1:
                        # Bound draining if a descendant keeps inherited pipes open.
                        break
                    for event, _ in selector.select(timeout=0.05):
                        data = os.read(event.fd, 65536)
                        if data:
                            captures[event.data].add(data)
                        else:
                            selector.unregister(event.fileobj)
                code = process.wait()
    except OSError:
        error = "PROCESS_UNAVAILABLE"
    return {
        "name": name,
        "argv": argv,
        "exit_code": code,
        "timed_out": timed_out,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "error": error,
        **{key: acc.record() for key, acc in captures.items()},
    }


def identity_state(chain: dict[str, Any]) -> bool:
    """Missing assets are capabilities; changed assets are rejected identities."""
    for asset in [chain["tool"], *chain["dependencies"]]:
        try:
            observed = file_digest(Path(asset["path"]))
        except InputError:
            return False
        if observed != asset["sha256"]:
            raise InputError("TOOL_IDENTITY_MISMATCH", "Tool/runtime asset differs from selection")
    return True


def baseline(selected: Inputs) -> dict[str, Any]:
    r = selected.request
    source = {
        "files": r["files"],
        "translation_units": r["translation_units"],
        "expected_units": r["expected_units"],
        "include_dirs": r["include_dirs"],
        "defines": r["defines"],
        "language": "c++17",
    }
    record = {
        "component": r["component"],
        **source,
        "source_digest": digest(canonical(source)),
        "profile": r["profile"],
        "toolchain": r["toolchain"],
        "configuration": r["config"],
    }
    record["full_digest"] = digest(canonical(record))
    return record
