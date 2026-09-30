"""Bounded Fabro HTTP transport gated by an exact disposable runtime profile."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import stat
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from score_sw_fabric.assurance.models import (
    bounded_limits,
    nonempty,
    sha,
    unique_strings,
    verify_digest,
    version,
)
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.runtime.ledger import IntentLedger
from score_sw_fabric.runtime.projection import project_version

PROFILE_FIELDS = {
    "id",
    "source_commit",
    "executable_sha256",
    "source_api_sha256",
    "base_url",
    "auth_mode",
    "declared_capabilities",
    "demonstrated_capabilities",
    "limits",
    "status",
    "digest",
}
CAPABILITIES = {
    "blob_read",
    "workflow_register",
    "run_create",
    "run_start",
    "run_inspect",
    "event_read",
    "timeline_read",
    "question_read",
    "run_resume",
    "run_cancel",
    "output_read",
}
ROUTES = {
    "blob_read": ("GET", r"/api/v1/runs/[A-Za-z0-9_-]{1,128}/blobs/[0-9a-f]{64}"),
    "workflow_register": ("POST", r"/api/v1/workflow-versions"),
    "run_create": ("POST", r"/api/v1/runs"),
    "run_start": ("POST", r"/api/v1/runs/[A-Za-z0-9_-]{1,128}/start"),
    "run_inspect": ("GET", r"/api/v1/runs/[A-Za-z0-9_-]{1,128}"),
    "event_read": (
        "GET",
        r"/api/v1/runs/[A-Za-z0-9_-]{1,128}/events(?:\?after=(?:0|[1-9][0-9]{0,19})(?:&limit=(?:[1-9][0-9]{0,2}|1000))?)?",
    ),
    "timeline_read": ("GET", r"/api/v1/runs/[A-Za-z0-9_-]{1,128}/timeline"),
    "question_read": ("GET", r"/api/v1/runs/[A-Za-z0-9_-]{1,128}/questions"),
    "run_resume": ("POST", r"/api/v1/runs/[A-Za-z0-9_-]{1,128}/start"),
    "run_cancel": ("POST", r"/api/v1/runs/[A-Za-z0-9_-]{1,128}/cancel"),
    "output_read": (
        "GET",
        r"/api/v1/runs/[A-Za-z0-9_-]{1,128}/stages/[A-Za-z0-9_-]{1,120}@[1-9][0-9]{0,6}/logs/output(?:\?offset=(?:0|[1-9][0-9]{0,19})(?:&limit=(?:[1-9][0-9]{0,6}))?)?",
    ),
}
Transport = Callable[[str, str, bytes | None, float, int, str], tuple[int, bytes]]
CredentialProvider = Callable[[], str]


def _loopback(host: str) -> bool:
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host == "localhost"


def validate_runtime_profile(value: Any, *, expected_commit: str) -> dict[str, Any]:
    profile = version(value, "runtime_profile", PROFILE_FIELDS, "/runtime_profile")
    verify_digest(profile, "/runtime_profile")
    nonempty(profile["id"], "/runtime_profile/id", max_length=256)
    commit = profile["source_commit"]
    if (
        not isinstance(commit, str)
        or len(commit) != 40
        or set(commit) - set("0123456789abcdef")
        or commit != expected_commit
    ):
        raise InputError("RUNTIME_IDENTITY_MISMATCH", "Runtime source commit differs")
    for name in ("executable_sha256", "source_api_sha256"):
        sha(profile[name], f"/runtime_profile/{name}")
    selected_url = nonempty(profile["base_url"], "/runtime_profile/base_url", max_length=512)
    parsed = urllib.parse.urlsplit(selected_url)
    try:
        port = parsed.port
    except ValueError as exc:
        raise InputError("RUNTIME_URL", "Runtime URL port is invalid") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or port is None
    ):
        raise InputError("RUNTIME_URL", "Runtime base URL is not an exact HTTP origin")
    if parsed.scheme == "http" and not _loopback(parsed.hostname):
        raise InputError("RUNTIME_URL", "Plain HTTP is limited to loopback")
    if profile["auth_mode"] != "dev_token_disposable" or profile["status"] != "candidate_only":
        raise InputError(
            "RUNTIME_CAPABILITY_UNAVAILABLE", "Only disposable runtime profiles are supported"
        )
    if not _loopback(parsed.hostname):
        raise InputError("RUNTIME_URL", "Disposable runtime must be loopback")
    declared = unique_strings(
        profile["declared_capabilities"],
        len(CAPABILITIES),
        "/runtime_profile/declared_capabilities",
    )
    demonstrated = unique_strings(
        profile["demonstrated_capabilities"],
        len(CAPABILITIES),
        "/runtime_profile/demonstrated_capabilities",
    )
    if set(declared) - CAPABILITIES or set(demonstrated) - set(declared):
        raise InputError("RUNTIME_CAPABILITY_UNAVAILABLE", "Unknown or unproven runtime operation")
    if (
        declared != profile["declared_capabilities"]
        or demonstrated != profile["demonstrated_capabilities"]
    ):
        raise InputError("FIELD_TYPE", "Runtime capabilities must be sorted")
    limits = bounded_limits(
        profile["limits"],
        {"timeout_seconds": 300, "response_bytes": 64 * 1024 * 1024},
        "/runtime_profile/limits",
    )
    if any(item == 0 for item in limits.values()):
        raise InputError("LIMIT_EXCEEDED", "Runtime transport limits must be positive")
    return profile


def verify_candidate_files(profile: dict[str, Any], *, executable: Path, source_api: Path) -> None:
    """Check selected local candidate bytes without contacting a server."""
    for path, field in (
        (executable, "executable_sha256"),
        (source_api, "source_api_sha256"),
    ):
        selected = path.absolute()
        if any(part.is_symlink() for part in (selected, *selected.parents)):
            raise InputError("RUNTIME_IDENTITY_MISMATCH", "Candidate file is absent or symbolic")
        try:
            descriptor = os.open(selected, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(descriptor, "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise InputError("RUNTIME_IDENTITY_MISMATCH", "Candidate file is not regular")
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
        except OSError as exc:
            raise InputError("RUNTIME_IDENTITY_MISMATCH", "Candidate file is unavailable") from exc
        if actual != profile[field]:
            raise InputError("RUNTIME_IDENTITY_MISMATCH", "Candidate file digest differs")


def _default_transport(
    method: str, url: str, body: bytes | None, timeout: float, maximum: int, token: str
) -> tuple[int, bytes]:
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer " + token,
        },
    )

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(
            self, request: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
        ) -> None:
            return None

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    try:
        response = opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as error:
        response = error
    except (OSError, urllib.error.URLError) as exc:
        raise InputError("RUNTIME_UNAVAILABLE", "Disposable Fabro server is unavailable") from exc
    with response:
        payload = response.read(maximum + 1)
        if len(payload) > maximum:
            raise InputError("LIMIT_EXCEEDED", "Fabro response exceeds selected byte limit")
        return response.status, payload


class FabroClient:
    """Candidate-only transport; token comes from an external disposable provider."""

    def __init__(
        self,
        profile: dict[str, Any],
        *,
        expected_commit: str,
        credential_provider: CredentialProvider,
        transport: Transport = _default_transport,
    ) -> None:
        self.profile = validate_runtime_profile(profile, expected_commit=expected_commit)
        self.credential_provider = credential_provider
        self.transport = transport

    def request(
        self,
        operation: str,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> tuple[int, bytes]:
        if operation not in self.profile["demonstrated_capabilities"]:
            raise InputError(
                "RUNTIME_CAPABILITY_UNAVAILABLE", "Fabro operation is not demonstrated"
            )
        selected_route = ROUTES.get(operation)
        if (
            selected_route is None
            or method != selected_route[0]
            or re.fullmatch(selected_route[1], path) is None
        ):
            raise InputError("RUNTIME_PATH", "Unsupported Fabro request path")
        if method == "GET" and payload is not None:
            raise InputError("FIELD_UNKNOWN", "GET cannot carry a runtime payload")
        body = canonical(payload) if payload is not None else None
        maximum = self.profile["limits"]["response_bytes"]
        if body is not None and len(body) > maximum:
            raise InputError("LIMIT_EXCEEDED", "Fabro request exceeds selected byte limit")
        url = self.profile["base_url"].rstrip("/") + path
        try:
            token = self.credential_provider()
        except Exception as exc:
            raise InputError(
                "RUNTIME_AUTH_UNAVAILABLE", "Disposable credential unavailable"
            ) from exc
        if not isinstance(token, str) or re.fullmatch(r"fabro_dev_[0-9a-f]{64}", token) is None:
            raise InputError("RUNTIME_AUTH_UNAVAILABLE", "Disposable credential is invalid")
        try:
            status, response = self.transport(
                method,
                url,
                body,
                float(self.profile["limits"]["timeout_seconds"]),
                maximum,
                token,
            )
        except InputError:
            raise
        except Exception as exc:
            raise InputError("RUNTIME_UNAVAILABLE", "Fabro transport failed") from exc
        if (
            type(status) is not int
            or status < 100
            or status > 599
            or not isinstance(response, bytes)
        ):
            raise InputError("RUNTIME_RESPONSE", "Invalid Fabro transport response")
        if len(response) > maximum:
            raise InputError("LIMIT_EXCEEDED", "Fabro response exceeds selected byte limit")
        return status, response

    def register_package(self, package: dict[str, Any], compiler_profile: dict[str, Any]) -> str:
        """Revalidate a sealed 003 package before any native registration."""
        projection = project_version(package, compiler_profile)
        wire = projection.get("wire")
        expected = projection.get("wire_digest")
        if not isinstance(wire, dict) or not isinstance(expected, str):
            raise InputError("PACKAGE_DRIFT", "Projected workflow version is incomplete")
        actual = hashlib.sha256(canonical(wire).removesuffix(b"\n")).hexdigest()
        if actual != expected:
            raise InputError("PACKAGE_DRIFT", "Projected workflow version changed")
        status, body = self.request("workflow_register", "POST", "/api/v1/workflow-versions", wire)
        response = _native_object(status, body, expected_status=201)
        if response.get("workflow_version_id") != expected:
            raise InputError("RUNTIME_RESPONSE", "Fabro version ID differs from projected bytes")
        return expected

    def create_run(
        self,
        ledger: IntentLedger,
        intent_id: str,
        *,
        target: Path,
        disposable_root: Path,
        environment_id: str,
        labels: dict[str, str],
    ) -> dict[str, Any]:
        """Send native create once after durable intent marking."""
        selected_target = target.absolute()
        selected_root = disposable_root.absolute()
        temporary_root = Path(tempfile.gettempdir()).resolve()
        if (
            ".." in target.parts
            or ".." in disposable_root.parts
            or not selected_root.is_relative_to(temporary_root)
            or selected_root == temporary_root
            or not selected_target.is_relative_to(selected_root)
            or not selected_target.resolve().is_relative_to(selected_root.resolve())
            or not selected_target.is_dir()
            or any(path.is_symlink() for path in (selected_target, *selected_target.parents))
            or any(path.is_symlink() for path in (selected_root, *selected_root.parents))
        ):
            raise InputError("RUNTIME_TARGET", "Native target must be a disposable directory")
        nonempty(environment_id, "/environment_id", max_length=128)
        if not isinstance(labels, dict) or "score_intent" in labels or len(labels) > 31:
            raise InputError("RUNTIME_LABELS", "Runtime labels are invalid")
        for key, value in labels.items():
            nonempty(key, "/labels/key", max_length=64)
            nonempty(value, "/labels/value", max_length=256)
        if "run_create" not in self.profile["demonstrated_capabilities"]:
            raise InputError("RUNTIME_CAPABILITY_UNAVAILABLE", "Run creation is not demonstrated")
        binding = ledger.begin_create(intent_id)
        try:
            status, body = self.request(
                "run_create",
                "POST",
                "/api/v1/runs",
                {
                    "workflow_version_id": binding["version_id"],
                    "target": {"kind": "folder", "path": str(selected_target)},
                    "environment_id": environment_id,
                    "args": {
                        "labels": {**labels, "score_intent": intent_id},
                        "auto_approve": False,
                        "dry_run": False,
                    },
                },
            )
            response = _native_object(status, body, expected_status=201)
            run_id = response.get("id")
            if not isinstance(run_id, str) or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", run_id) is None:
                raise InputError("RUN_ID_UNKNOWN", "Fabro create response has no valid run ID")
            return ledger.record_create_response(intent_id, run_id)
        except Exception:
            ledger.mark_create_uncertain(intent_id)
            raise

    def start_known_run(self, ledger: IntentLedger, intent_id: str) -> dict[str, Any]:
        """Inspect a durable run ID before one start request; uncertainty stops retries."""
        binding = ledger.read(intent_id)
        if binding["creation_state"] != "run_known" or binding["run_id"] is None:
            raise InputError("RUN_ID_UNKNOWN", "Native run ID is not safely known")
        if binding["start_state"] == "started":
            return binding
        if not {"run_inspect", "run_start"} <= set(self.profile["demonstrated_capabilities"]):
            raise InputError(
                "RUNTIME_CAPABILITY_UNAVAILABLE", "Start prerequisites are unavailable"
            )
        binding = ledger.begin_start(intent_id)
        run_id = binding["run_id"]
        path = f"/api/v1/runs/{run_id}"
        try:
            status, body = self.request("run_inspect", "GET", path)
            observed = _native_object(status, body, expected_status=200)
            lifecycle = observed.get("lifecycle")
            native_status = lifecycle.get("status") if isinstance(lifecycle, dict) else None
            if (
                observed.get("id") != run_id
                or not isinstance(native_status, dict)
                or native_status.get("kind") != "submitted"
            ):
                raise InputError("RUN_START_UNCERTAIN", "Known run is not submitted")
            status, body = self.request("run_start", "POST", path + "/start", {})
            started = _native_object(status, body, expected_status=200)
            if started.get("id") != run_id:
                raise InputError("RUN_START_UNCERTAIN", "Native start returned a different run")
            return ledger.record_start_response(intent_id)
        except Exception:
            ledger.mark_start_uncertain(intent_id)
            raise


def _native_object(status: int, body: bytes, *, expected_status: int) -> dict[str, Any]:
    if status != expected_status:
        raise InputError("RUNTIME_RESPONSE", f"Fabro returned HTTP {status}")
    try:
        value = json.loads(body)
    except (ValueError, UnicodeError) as exc:
        raise InputError("RUNTIME_RESPONSE", "Fabro returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise InputError("RUNTIME_RESPONSE", "Fabro returned a non-object")
    return value
