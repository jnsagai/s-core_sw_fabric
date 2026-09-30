"""Deterministic test-only receipt helpers; never import into production modules."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from score_sw_fabric.assurance.models import digest
from score_sw_fabric.assurance.origins import signing_bytes
from score_sw_fabric.catalog.export import canonical

# Public test seed. Never use this key or any derived key for production authority.
FIXTURE_SEED = bytes.fromhex("05" * 32)
FIXTURE_PRIVATE_KEY = Ed25519PrivateKey.from_private_bytes(FIXTURE_SEED)
FIXTURE_PUBLIC_KEY = base64.b64encode(
    FIXTURE_PRIVATE_KEY.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
).decode("ascii")


def fixture_receipt(
    payload: dict[str, Any],
    *,
    payload_kind: str,
    issued_at: str = "2026-09-29T09:00:00Z",
    nonce: str = "fixture-sequence-1",
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": 1,
        "kind": "signed_receipt",
        "assurance_domain": "fixture_contract",
        "payload_kind": payload_kind,
        "payload_digest": hashlib.sha256(canonical(payload)).hexdigest(),
        "issuer_id": "fixture-issuer-005",
        "key_id": "fixture-key-005",
        "algorithm": "Ed25519",
        "issued_at": issued_at,
        "nonce_or_sequence": nonce,
    }
    body["signature"] = base64.b64encode(FIXTURE_PRIVATE_KEY.sign(signing_bytes(body))).decode(
        "ascii"
    )
    body["receipt_digest"] = digest(body, exclude="receipt_digest")
    return body


def reference(path: Path) -> dict[str, str]:
    from score_sw_fabric.compiler.reader import verify_self_digest
    from score_sw_fabric.process_source.reader import read_json, read_yaml

    value = read_json(path) if path.suffix == ".json" else read_yaml(path)
    selected = (
        value["digest"]
        if value.get("kind", "").startswith("assurance_")
        else verify_self_digest(value, "/reference")
    )
    return {
        "path": path.as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "semantic_digest": selected,
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value))


def read_json(path: Path) -> dict[str, Any]:
    value: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return value
