"""Runtime records reject malformed, over-limit, aliased and partial inputs."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.runtime.models import (
    BINDING_FIELDS,
    EXPORT_FIELDS,
    INTENT_FIELDS,
    bounded_diagnostic,
    output_path,
    publish,
    validate_binding,
    validate_export,
    validate_intent,
)

SHA = "a" * 64


def _intent() -> dict[str, Any]:
    reference = {"path": "selected.json", "sha256": SHA, "semantic_digest": SHA}
    return seal(
        {
            "schema_version": 1,
            "kind": "runtime_intent",
            "intent_id": "intent-006",
            "package_ref": reference,
            "runtime_profile_ref": {**reference, "path": "runtime-profile.json"},
            "baseline": {
                "source_digest": SHA,
                "process_digest": SHA,
                "policy_digest": SHA,
                "tool_digest": SHA,
                "subject_digest": SHA,
                "evidence_digests": [],
            },
            "start_args": {"target_id": "local-006", "labels": {}},
            "limits": {
                "timeout_seconds": 30,
                "event_pages": 10,
                "output_bytes": 1024,
                "attempts": 2,
            },
        }
    )


def _binding() -> dict[str, Any]:
    return seal(
        {
            "schema_version": 1,
            "kind": "runtime_binding",
            "intent_id": "intent-006",
            "intent_digest": SHA,
            "source_package_digest": SHA,
            "wire_digest": SHA,
            "runtime_commit": "b" * 40,
            "version_id": "version-006",
            "run_id": None,
            "creation_state": "prepared",
            "start_state": "not_requested",
            "baseline_digest": SHA,
            "native_observation": None,
            "reason_codes": [],
        }
    )


def _export() -> dict[str, Any]:
    raw = b"observed output"
    return seal(
        {
            "schema_version": 1,
            "kind": "runtime_export",
            "source_package": {},
            "wire_projection": {},
            "binding": _binding(),
            "run_summary": {},
            "events": [],
            "checkpoints": [],
            "questions": [],
            "blobs": [
                {
                    "id": "output-006",
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "bytes": len(raw),
                    "base64": base64.b64encode(raw).decode(),
                    "origin": "runtime_observation",
                }
            ],
            "completeness": "incomplete",
            "limitations": ["Native run source has not been selected."],
        }
    )


def test_valid_version_one_intent_and_binding() -> None:
    assert validate_intent(_intent())["intent_id"] == "intent-006"
    assert validate_binding(_binding())["run_id"] is None
    assert validate_export(_export())["completeness"] == "incomplete"


@pytest.mark.parametrize("field", sorted(INTENT_FIELDS | {"schema_version", "kind"}))
def test_missing_intent_field_is_rejected(field: str) -> None:
    intent = _intent()
    intent.pop(field)
    with pytest.raises(InputError) as error:
        validate_intent(intent)
    assert error.value.code == "FIELD_UNKNOWN"


@pytest.mark.parametrize("field", sorted(BINDING_FIELDS | {"schema_version", "kind"}))
def test_missing_binding_field_is_rejected(field: str) -> None:
    binding = _binding()
    binding.pop(field)
    with pytest.raises(InputError) as error:
        validate_binding(binding)
    assert error.value.code == "FIELD_UNKNOWN"


@pytest.mark.parametrize("field", sorted(EXPORT_FIELDS | {"schema_version", "kind"}))
def test_missing_export_field_is_rejected(field: str) -> None:
    exported = _export()
    exported.pop(field)
    with pytest.raises(InputError) as error:
        validate_export(exported)
    assert error.value.code == "FIELD_UNKNOWN"


def test_export_raw_bytes_are_checked_even_when_incomplete() -> None:
    exported = _export()
    exported["blobs"][0]["base64"] = base64.b64encode(b"substituted raw").decode()
    with pytest.raises(InputError) as error:
        validate_export(seal(exported))
    assert error.value.code == "HASH_MISMATCH"


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("schema_version", 2, "VERSION_UNSUPPORTED"),
        ("kind", "runtime_binding", "KIND_MISMATCH"),
        ("intent_id", "", "ID_FORMAT"),
        ("package_ref", {"path": "selected.json"}, "FIELD_UNKNOWN"),
        (
            "limits",
            {"timeout_seconds": 0, "event_pages": 10, "output_bytes": 1024, "attempts": 2},
            "LIMIT_EXCEEDED",
        ),
    ],
)
def test_intent_one_field_mutations_are_bounded(field: str, value: object, code: str) -> None:
    intent = _intent()
    intent[field] = value
    intent = seal(intent)
    with pytest.raises(InputError) as error:
        validate_intent(intent)
    assert error.value.code == code


def test_intent_limit_and_baseline_order() -> None:
    intent = _intent()
    intent["baseline"]["evidence_digests"] = ["b" * 64, "a" * 64]
    with pytest.raises(InputError, match="unique and sorted"):
        validate_intent(seal(intent))
    intent = _intent()
    intent["limits"]["attempts"] = 101
    with pytest.raises(InputError) as error:
        validate_intent(seal(intent))
    assert error.value.code == "LIMIT_EXCEEDED"


def test_binding_states_cannot_claim_unknown_run_as_started() -> None:
    binding = _binding()
    binding["start_state"] = "started"
    with pytest.raises(InputError) as error:
        validate_binding(seal(binding))
    assert error.value.code == "FIELD_TYPE"
    binding = _binding()
    binding["creation_state"] = "run_known"
    with pytest.raises(InputError) as error:
        validate_binding(seal(binding))
    assert error.value.code == "FIELD_TYPE"


def test_output_guard_preserves_existing_bytes(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    source.write_bytes(b"source")
    prior = tmp_path / "out" / "binding.json"
    prior.parent.mkdir()
    prior.write_bytes(b"prior")
    assert output_path(prior, [source], [tmp_path / "protected"]) == prior
    with pytest.raises(InputError) as error:
        publish(source, _binding(), inputs=[source], protected_roots=[])
    assert error.value.code == "OUTPUT_ALIAS"
    assert source.read_bytes() == b"source"
    protected = tmp_path / "protected"
    protected.mkdir()
    with pytest.raises(InputError) as error:
        publish(
            protected / "binding.json", _binding(), inputs=[source], protected_roots=[protected]
        )
    assert error.value.code == "OUTPUT_PROTECTED"
    assert prior.read_bytes() == b"prior"
    publish(prior, _binding(), inputs=[source], protected_roots=[protected])
    assert hashlib.sha256(prior.read_bytes()).hexdigest() != hashlib.sha256(b"prior").hexdigest()


def test_output_parent_symlink_is_rejected(tmp_path: Path) -> None:
    destination = tmp_path / "real"
    destination.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(destination, target_is_directory=True)
    with pytest.raises(InputError) as error:
        output_path(alias / "binding.json", [], [])
    assert error.value.code == "OUTPUT_ALIAS"


def test_public_diagnostic_is_bounded_and_redacts_input() -> None:
    error = InputError("FIELD_UNKNOWN", "secret-token" * 1000, "/runtime_intent/secret-key")
    diagnostic = bounded_diagnostic(error)
    assert diagnostic["code"] == "FIELD_UNKNOWN"
    assert diagnostic["pointer"] == "/runtime_intent"
    assert "secret" not in str(diagnostic)
    assert len(diagnostic["message"]) < 100


def test_interrupted_atomic_replace_preserves_prior_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from score_sw_fabric.runtime import models

    out = tmp_path / "binding.json"
    out.write_bytes(b"prior")

    def interrupted(_source: str, _target: Path) -> None:
        raise OSError("interrupted")

    monkeypatch.setattr(models.os, "replace", interrupted)
    with pytest.raises(InputError) as error:
        publish(out, _binding(), inputs=[], protected_roots=[])
    assert error.value.code == "OUTPUT_IO"
    assert out.read_bytes() == b"prior"
    assert sorted(tmp_path.iterdir()) == [out]
