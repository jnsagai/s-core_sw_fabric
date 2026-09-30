"""Contract tests for the selected, sealed catalogue boundary."""

from __future__ import annotations

import hashlib
import json

import pytest

from score_sw_fabric.catalog.export import canonical, seal
from score_sw_fabric.catalog.reader import load_catalogue
from score_sw_fabric.process_source.reader import MAX_INPUT_BYTES, InputError
from tests.planning_support import catalogue_payload, sha256, write_catalogue


def test_loads_selected_catalogue_and_indexes_qualified_identity(tmp_path) -> None:
    path = tmp_path / "catalogue.json"
    catalogue, transport = write_catalogue(path)
    index = load_catalogue(path, transport_sha256=transport, expected_digest=catalogue["digest"])
    assert len(index.workproducts) == 2
    assert ("process", "wp__plan", 1) in index.entities


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda value: value["entities"].append(value["entities"][0]), "CATALOGUE_IDENTITY"),
        (
            lambda value: value["entities"][0].update({"type": "unknown"}),
            "CATALOGUE_REFERENCE",
        ),
        (
            lambda value: value["relations"].append(
                {
                    "source_id": "process",
                    "native_id": "wp__plan",
                    "native_version": 1,
                    "target_source_id": "process",
                    "target_id": "missing",
                    "resolved_native_version": 1,
                    "direction": "forward",
                    "field": "input",
                }
            ),
            "CATALOGUE_REFERENCE",
        ),
    ],
)
def test_rejects_ambiguous_or_dangling_catalogue_content(tmp_path, mutation, code) -> None:
    payload = catalogue_payload()
    mutation(payload)
    catalogue, data = seal(payload)
    path = tmp_path / "catalogue.json"
    path.write_bytes(data)
    with pytest.raises(InputError, match="Duplicate|Unknown|endpoint") as raised:
        load_catalogue(path, transport_sha256=sha256(path), expected_digest=catalogue["digest"])
    assert raised.value.code == code


def test_rejects_duplicate_json_keys_before_semantic_validation(tmp_path) -> None:
    path = tmp_path / "catalogue.json"
    path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
    with pytest.raises(InputError) as raised:
        load_catalogue(path, transport_sha256=sha256(path), expected_digest="0" * 64)
    assert raised.value.code == "DUPLICATE_JSON_KEY"


def test_rejects_self_digest_transport_and_resealed_baseline_mismatches(tmp_path) -> None:
    path = tmp_path / "catalogue.json"
    original, transport = write_catalogue(path)
    damaged = json.loads(path.read_text(encoding="utf-8"))
    damaged["entities"][0]["title"] = "tampered"
    path.write_bytes(canonical(damaged))
    with pytest.raises(InputError) as raised:
        load_catalogue(path, transport_sha256=sha256(path), expected_digest=original["digest"])
    assert raised.value.code == "CATALOGUE_DIGEST"

    changed_payload = catalogue_payload()
    changed_payload["entities"][0]["title"] = "resealed alteration"
    changed, data = seal(changed_payload)
    path.write_bytes(data)
    with pytest.raises(InputError) as raised:
        load_catalogue(path, transport_sha256=sha256(path), expected_digest=original["digest"])
    assert raised.value.code == "CATALOGUE_BASELINE"
    assert changed["digest"] != original["digest"]

    with pytest.raises(InputError) as raised:
        load_catalogue(path, transport_sha256="0" * 64, expected_digest=changed["digest"])
    assert raised.value.code == "HASH_MISMATCH"


def test_rejects_catalogue_larger_than_64_mib(tmp_path) -> None:
    path = tmp_path / "catalogue.json"
    with path.open("wb") as stream:
        stream.seek(MAX_INPUT_BYTES)
        stream.write(b"x")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(InputError) as raised:
        load_catalogue(path, transport_sha256=digest, expected_digest="0" * 64)
    assert raised.value.code == "INPUT_TOO_LARGE"
