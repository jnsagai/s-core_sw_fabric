"""A candidate client can call only selected, demonstrated local routes."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.process_source.reader import InputError, read_json, read_yaml
from score_sw_fabric.runtime.client import (
    FabroClient,
    validate_runtime_profile,
    verify_candidate_files,
)

COMMIT = "a" * 40
SHA = "b" * 64
DEV_TOKEN = "fabro_dev_" + "c" * 64


def _profile() -> dict[str, Any]:
    return seal(
        {
            "schema_version": 1,
            "kind": "runtime_profile",
            "id": "local-006",
            "source_commit": COMMIT,
            "executable_sha256": SHA,
            "source_api_sha256": SHA,
            "base_url": "http://127.0.0.1:43286",
            "auth_mode": "dev_token_disposable",
            "declared_capabilities": ["run_create", "workflow_register"],
            "demonstrated_capabilities": ["workflow_register"],
            "limits": {"timeout_seconds": 5, "response_bytes": 1024},
            "status": "candidate_only",
        }
    )


def test_exact_candidate_profile_and_selected_route() -> None:
    calls: list[tuple[str, str, bytes | None, float, int, str]] = []

    def transport(
        method: str, url: str, body: bytes | None, timeout: float, maximum: int, token: str
    ) -> tuple[int, bytes]:
        calls.append((method, url, body, timeout, maximum, token))
        return 201, b'{"workflow_version_id":"wv-006"}'

    client = FabroClient(
        _profile(),
        expected_commit=COMMIT,
        credential_provider=lambda: DEV_TOKEN,
        transport=transport,
    )
    assert (
        client.request("workflow_register", "POST", "/api/v1/workflow-versions", {"x": 1})[0] == 201
    )
    assert calls == [
        (
            "POST",
            "http://127.0.0.1:43286/api/v1/workflow-versions",
            b'{"x":1}\n',
            5.0,
            1024,
            DEV_TOKEN,
        )
    ]


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("base_url", "http://example.com:43286", "RUNTIME_URL"),
        ("base_url", "http://127.0.0.1:43286/path", "RUNTIME_URL"),
        ("base_url", "http://127.0.0.1:bad", "RUNTIME_URL"),
        ("base_url", "http://secret@127.0.0.1:43286", "RUNTIME_URL"),
        ("auth_mode", "protected_bearer", "RUNTIME_CAPABILITY_UNAVAILABLE"),
        ("source_commit", "c" * 40, "RUNTIME_IDENTITY_MISMATCH"),
        ("demonstrated_capabilities", ["workflow_register", "run_create"], "FIELD_TYPE"),
        ("demonstrated_capabilities", ["output_read"], "RUNTIME_CAPABILITY_UNAVAILABLE"),
    ],
)
def test_profile_boundary(field: str, value: object, code: str) -> None:
    profile = _profile()
    profile[field] = value
    with pytest.raises(InputError) as error:
        validate_runtime_profile(seal(profile), expected_commit=COMMIT)
    assert error.value.code == code


def test_unproven_and_wrong_routes_never_reach_transport() -> None:
    calls = 0

    def transport(
        _method: str, _url: str, _body: bytes | None, _timeout: float, _maximum: int, _token: str
    ) -> tuple[int, bytes]:
        nonlocal calls
        calls += 1
        return 200, b"{}"

    client = FabroClient(
        _profile(),
        expected_commit=COMMIT,
        credential_provider=lambda: DEV_TOKEN,
        transport=transport,
    )
    with pytest.raises(InputError) as error:
        client.request("run_create", "POST", "/api/v1/runs", {})
    assert error.value.code == "RUNTIME_CAPABILITY_UNAVAILABLE"
    with pytest.raises(InputError) as error:
        client.request("workflow_register", "POST", "/api/v1/secrets", {})
    assert error.value.code == "RUNTIME_PATH"
    with pytest.raises(InputError) as error:
        client.request("workflow_register", "GET", "/api/v1/workflow-versions")
    assert error.value.code == "RUNTIME_PATH"
    assert calls == 0


def test_response_and_transport_failure_are_bounded() -> None:
    def oversized(
        _method: str, _url: str, _body: bytes | None, _timeout: float, _maximum: int, _token: str
    ) -> tuple[int, bytes]:
        return 200, b"x" * 1025

    client = FabroClient(
        _profile(),
        expected_commit=COMMIT,
        credential_provider=lambda: DEV_TOKEN,
        transport=oversized,
    )
    with pytest.raises(InputError) as error:
        client.request("workflow_register", "POST", "/api/v1/workflow-versions", {})
    assert error.value.code == "LIMIT_EXCEEDED"

    def failed(
        _method: str, _url: str, _body: bytes | None, _timeout: float, _maximum: int, _token: str
    ) -> tuple[int, bytes]:
        raise RuntimeError("secret-token")

    client = FabroClient(
        _profile(), expected_commit=COMMIT, credential_provider=lambda: DEV_TOKEN, transport=failed
    )
    with pytest.raises(InputError) as error:
        client.request("workflow_register", "POST", "/api/v1/workflow-versions", {})
    assert error.value.code == "RUNTIME_UNAVAILABLE"
    assert "secret-token" not in str(error.value)


def test_candidate_file_bytes_are_checked_without_server_access(tmp_path: Path) -> None:
    executable = tmp_path / "fabro"
    api = tmp_path / "fabro-api.yaml"
    executable.write_bytes(b"candidate binary")
    api.write_bytes(b"candidate API")
    profile = _profile()
    profile["executable_sha256"] = hashlib.sha256(executable.read_bytes()).hexdigest()
    profile["source_api_sha256"] = hashlib.sha256(api.read_bytes()).hexdigest()
    selected = validate_runtime_profile(seal(profile), expected_commit=COMMIT)
    verify_candidate_files(selected, executable=executable, source_api=api)
    alias = tmp_path / "fabro-hardlink"
    alias.hardlink_to(executable)
    verify_candidate_files(selected, executable=executable, source_api=api)
    symlink = tmp_path / "fabro-symlink"
    symlink.symlink_to(executable)
    with pytest.raises(InputError) as error:
        verify_candidate_files(selected, executable=symlink, source_api=api)
    assert error.value.code == "RUNTIME_IDENTITY_MISMATCH"
    alias_dir = tmp_path / "alias-dir"
    alias_dir.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(InputError) as error:
        verify_candidate_files(selected, executable=alias_dir / "fabro", source_api=api)
    assert error.value.code == "RUNTIME_IDENTITY_MISMATCH"
    api.write_bytes(b"changed API")
    with pytest.raises(InputError) as error:
        verify_candidate_files(selected, executable=executable, source_api=api)
    assert error.value.code == "RUNTIME_IDENTITY_MISMATCH"


def test_missing_or_invalid_disposable_token_never_sends_request() -> None:
    calls = 0

    def transport(
        _method: str, _url: str, _body: bytes | None, _timeout: float, _maximum: int, _token: str
    ) -> tuple[int, bytes]:
        nonlocal calls
        calls += 1
        return 201, b"{}"

    for supplier in (lambda: "", lambda: "production-secret", lambda: 123):
        client = FabroClient(
            _profile(), expected_commit=COMMIT, credential_provider=supplier, transport=transport
        )
        with pytest.raises(InputError) as error:
            client.request("workflow_register", "POST", "/api/v1/workflow-versions", {})
        assert error.value.code == "RUNTIME_AUTH_UNAVAILABLE"
    assert calls == 0


def test_register_package_rejects_changed_003_bytes_before_transport() -> None:
    root = Path(__file__).resolve().parents[2]
    fixture = root / "tests/fixtures/compiler/linear"
    package = deepcopy(read_json(fixture / "out/package.json"))
    package["files"]["workflow.fabro"] += "\n"
    calls = 0

    def transport(
        _method: str, _url: str, _body: bytes | None, _timeout: float, _maximum: int, _token: str
    ) -> tuple[int, bytes]:
        nonlocal calls
        calls += 1
        return 201, b"{}"

    client = FabroClient(
        _profile(),
        expected_commit=COMMIT,
        credential_provider=lambda: DEV_TOKEN,
        transport=transport,
    )
    with pytest.raises(InputError):
        client.register_package(package, read_yaml(fixture / "compiler_profile.yaml"))
    assert calls == 0


def test_blob_read_accepts_only_lowercase_sha256_path() -> None:
    calls: list[str] = []

    def transport(
        _method: str, url: str, _body: bytes | None, _timeout: float, _maximum: int, _token: str
    ) -> tuple[int, bytes]:
        calls.append(url)
        return 200, b"native blob bytes"

    profile = _profile()
    profile["declared_capabilities"] = ["blob_read", "run_create", "workflow_register"]
    profile["demonstrated_capabilities"] = ["blob_read", "workflow_register"]
    client = FabroClient(
        seal(profile),
        expected_commit=COMMIT,
        credential_provider=lambda: DEV_TOKEN,
        transport=transport,
    )
    valid = "/api/v1/runs/native-run/blobs/" + "a" * 64
    assert client.request("blob_read", "GET", valid) == (200, b"native blob bytes")
    for invalid in (valid[:-1] + "G", valid + "/extra", "/api/v1/runs/native-run/blobs/../secret"):
        with pytest.raises(InputError) as error:
            client.request("blob_read", "GET", invalid)
        assert error.value.code == "RUNTIME_PATH"
    assert len(calls) == 1
