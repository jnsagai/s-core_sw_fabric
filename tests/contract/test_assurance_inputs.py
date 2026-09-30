"""Strict assurance envelope and local path boundary tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from score_sw_fabric.assurance.models import MAX_DEPTH, version
from score_sw_fabric.assurance.reader import REQUEST_FIELDS, read_request, resolve_file, safe_path
from score_sw_fabric.process_source.reader import InputError


@pytest.mark.parametrize("value", [True, 1.0, "1", 2, None])
def test_version_requires_exact_integer_one(value: object) -> None:
    with pytest.raises(InputError):
        version({"schema_version": value, "kind": "sample"}, "sample", set(), "/")


def test_unknown_envelope_field_rejected() -> None:
    with pytest.raises(InputError):
        version({"schema_version": 1, "kind": "sample", "new": 1}, "sample", set(), "/")


@pytest.mark.parametrize("value", ["../x", "./x", "a//b", "a/./b", "a/../b", "/tmp/x", "a\\b"])
def test_unsafe_logical_paths_rejected(value: str) -> None:
    with pytest.raises(InputError):
        safe_path(value, "/path")


def test_symlink_and_hardlink_input_rejected(tmp_path: Path) -> None:
    original = tmp_path / "original.json"
    original.write_text("{}")
    (tmp_path / "link.json").symlink_to(original)
    with pytest.raises(InputError):
        resolve_file(tmp_path, "link.json", "/ref")
    import os

    os.link(original, tmp_path / "hard.json")
    with pytest.raises(InputError):
        resolve_file(tmp_path, "hard.json", "/ref")


def test_duplicate_json_key_rejected(tmp_path: Path) -> None:
    path = tmp_path / "request.json"
    path.write_text('{"schema_version":1,"schema_version":1}')
    with pytest.raises(InputError, match="Duplicate JSON key"):
        read_request(path, "subject")


def test_request_suffix_must_be_supported(tmp_path: Path) -> None:
    request = tmp_path / "request.txt"
    request.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "operation": "subject",
                "assurance_domain": "fixture_contract",
                "scope": {"kind": "component", "id": "component-005", "purpose": "test"},
                "inputs": {},
                "local_paths": {"protected_roots": []},
                "output_root": "out",
                "as_of": "2026-09-29T10:00:00Z",
            }
        )
    )
    with pytest.raises(InputError) as error:
        read_request(request, "subject")
    assert error.value.code == "FIELD_UNKNOWN"


def test_reference_depth_limit(tmp_path: Path) -> None:
    path = tmp_path / "request.json"
    nested: dict[str, object] = {}
    for _ in range(MAX_DEPTH + 1):
        nested = {"x": nested}
    request = {
        "schema_version": 1,
        "operation": "subject",
        "assurance_domain": "fixture_contract",
        "scope": {"kind": "component", "id": "component-005", "purpose": "test"},
        "inputs": {},
        "local_paths": nested,
        "output_root": "out",
        "as_of": "2026-09-29T10:00:00Z",
    }
    path.write_text(json.dumps(request))
    with pytest.raises(InputError, match="nesting"):
        read_request(path, "subject")


def test_parser_recursion_is_bounded_input_error_and_preserves_prior(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from score_sw_fabric.cli import main

    request = tmp_path / "deep.json"
    request.write_text("[" * 10_000 + "0" + "]" * 10_000)
    out = tmp_path / "out/result.json"
    out.parent.mkdir()
    out.write_bytes(b"prior complete output")
    assert (
        main(["assurance", "subject", "--request", str(request), "--out", str(out), "--json"]) == 2
    )
    response = json.loads(capsys.readouterr().err)
    assert response["code"] == "LIMIT_EXCEEDED"
    assert len(response["message"]) <= 4096
    assert out.read_bytes() == b"prior complete output"


def test_deep_selected_reference_parser_returns_limit_error(tmp_path: Path) -> None:
    import hashlib

    from score_sw_fabric.assurance.reader import read_reference

    content = ("[" * 10_000 + "0" + "]" * 10_000).encode()
    (tmp_path / "deep.json").write_bytes(content)
    reference = {
        "path": "deep.json",
        "sha256": hashlib.sha256(content).hexdigest(),
        "semantic_digest": "0" * 64,
    }
    with pytest.raises(InputError) as error:
        read_reference(tmp_path, reference, "/selected")
    assert error.value.code == "LIMIT_EXCEEDED"


def test_absent_protected_root_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "request.json"
    request = {
        "schema_version": 1,
        "operation": "subject",
        "assurance_domain": "fixture_contract",
        "scope": {"kind": "component", "id": "component-005", "purpose": "test"},
        "inputs": {},
        "local_paths": {"protected_roots": ["missing/source"]},
        "output_root": "out",
        "as_of": "2026-09-29T10:00:00Z",
    }
    path.write_text(json.dumps(request))
    with pytest.raises(InputError):
        read_request(path, "subject")


def test_unknown_local_path_field_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "request.json"
    request = {
        "schema_version": 1,
        "operation": "subject",
        "assurance_domain": "fixture_contract",
        "scope": {"kind": "component", "id": "component-005", "purpose": "test"},
        "inputs": {},
        "local_paths": {"protected_roots": [], "trust_me": True},
        "output_root": "out",
        "as_of": "2026-09-29T10:00:00Z",
    }
    path.write_text(json.dumps(request))
    with pytest.raises(InputError):
        read_request(path, "subject")


def test_output_root_symlink_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from score_sw_fabric.assurance.reader import output_path

    real = tmp_path / "real"
    real.mkdir()
    (tmp_path / "linked").symlink_to(real, target_is_directory=True)
    monkeypatch.chdir(tmp_path)
    request = {"output_root": "linked", "local_paths": {"protected_roots": []}}
    with pytest.raises(InputError):
        output_path(tmp_path / "request.json", request, tmp_path / "linked/result.json", [])


def test_output_must_not_alias_existing_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from score_sw_fabric.assurance.reader import output_path

    out = tmp_path / "out"
    out.mkdir()
    source = out / "input.json"
    source.write_text("{}")
    monkeypatch.chdir(tmp_path)
    request = {"output_root": "out", "local_paths": {"protected_roots": []}}
    with pytest.raises(InputError):
        output_path(tmp_path / "request.json", request, source, [source])


def test_output_cannot_overlap_raw_observation_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from score_sw_fabric.assurance.reader import output_path

    raw = tmp_path / "raw"
    raw.mkdir()
    monkeypatch.chdir(tmp_path)
    request = {
        "output_root": "raw",
        "local_paths": {"protected_roots": [], "raw_root": "raw"},
    }
    with pytest.raises(InputError) as error:
        output_path(tmp_path / "request.json", request, raw / "result.json", [])
    assert error.value.code == "OUTPUT_SOURCE_ROOT"


@pytest.mark.parametrize("operation", ["evidence", "gate"])
def test_public_raw_root_can_follow_relocated_request(
    operation: str, capsys: pytest.CaptureFixture[str]
) -> None:
    import shutil
    from tempfile import TemporaryDirectory

    from score_sw_fabric.cli import main
    from score_sw_fabric.process_source.reader import read_yaml

    root = Path(__file__).resolve().parents[2]
    fixture = root / "tests/fixtures/assurance/passing-scope"
    with TemporaryDirectory(prefix=".assurance-relocated-", dir=root) as directory:
        scratch = Path(directory)
        shutil.copytree(fixture / "raw", scratch / "raw")
        request = read_yaml(fixture / f"{operation}-request.yaml")
        request["local_paths"]["raw_root"] = "raw"
        request["output_root"] = f"{scratch.name}/out"
        path = scratch / "request.json"
        path.write_text(json.dumps(request))
        out = scratch / f"out/{operation}.json"
        assert (
            main(
                [
                    "assurance",
                    operation,
                    "--request",
                    str(path),
                    "--out",
                    str(out),
                    "--json",
                ]
            )
            == 0
        )
        assert json.loads(capsys.readouterr().out)["outcome"] in {"eligible", "pass"}
        assert out.is_file()


def test_transport_semantic_and_nested_digest_mismatches(tmp_path: Path) -> None:
    import hashlib
    from copy import deepcopy

    from score_sw_fabric.assurance.reader import read_reference
    from score_sw_fabric.compiler.reader import semantic_digest
    from score_sw_fabric.process_source.reader import read_json

    source = (
        Path(__file__).resolve().parents[2]
        / "tests/fixtures/artifacts/out/component-candidate.json"
    )
    value = read_json(source)
    copied = tmp_path / "candidate.json"
    copied.write_bytes(source.read_bytes())
    ref = {
        "path": "candidate.json",
        "sha256": hashlib.sha256(copied.read_bytes()).hexdigest(),
        "semantic_digest": value["digest"],
    }
    bad = deepcopy(ref)
    bad["sha256"] = "0" * 64
    with pytest.raises(InputError, match="Transport hash"):
        read_reference(tmp_path, bad, "/candidate")
    bad = deepcopy(ref)
    bad["semantic_digest"] = "0" * 64
    with pytest.raises(InputError, match="Semantic digest"):
        read_reference(tmp_path, bad, "/candidate")
    value["index"]["digest"] = "0" * 64
    value["digest"] = semantic_digest(value)
    copied.write_text(json.dumps(value))
    ref["sha256"] = hashlib.sha256(copied.read_bytes()).hexdigest()
    ref["semantic_digest"] = value["digest"]
    from score_sw_fabric.assurance.subjects import build_subject
    from score_sw_fabric.process_source.reader import read_yaml

    root = Path(__file__).resolve().parents[2]
    request = read_yaml(root / "tests/fixtures/assurance/passing-scope/subject-request.yaml")
    inputs = {
        "plan": read_json(root / "tests/fixtures/compiler/linear/plan.json"),
        "candidate": value,
        "artifact_profile": read_yaml(root / "profiles/s_core_native_artifacts_v1.yaml"),
        "snapshot": read_json(root / "tests/fixtures/artifacts/component/snapshot.json"),
        "workflow_package": read_json(root / "tests/fixtures/compiler/linear/out/package.json"),
        "artifact_request": read_yaml(
            root / "tests/fixtures/artifacts/component/update-request.yaml"
        ),
    }
    with pytest.raises(InputError, match="Self-digest"):
        build_subject(request, inputs)


def test_exact_input_size_ceiling_and_one_over(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import hashlib

    import score_sw_fabric.assurance.reader as reader

    content = b"{}"
    path = tmp_path / "input.json"
    path.write_bytes(content)
    ref = {
        "path": "input.json",
        "sha256": hashlib.sha256(content).hexdigest(),
        "semantic_digest": "0" * 64,
    }
    monkeypatch.setattr(reader, "MAX_CONTROL_BYTES", len(content))
    with pytest.raises(InputError) as exact:
        reader.read_reference(tmp_path, ref, "/input")
    assert exact.value.code != "LIMIT_EXCEEDED"
    monkeypatch.setattr(reader, "MAX_CONTROL_BYTES", len(content) - 1)
    with pytest.raises(InputError) as over:
        reader.read_reference(tmp_path, ref, "/input")
    assert over.value.code == "LIMIT_EXCEEDED"


def test_public_request_byte_ceiling_exact_and_one_over(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from score_sw_fabric.process_source import reader as source_reader

    request = tmp_path / "request.json"
    monkeypatch.setattr(source_reader, "MAX_INPUT_BYTES", 2)
    request.write_bytes(b"{}")
    with pytest.raises(InputError) as exact:
        read_request(request, "subject")
    assert exact.value.code == "FIELD_UNKNOWN"
    request.write_bytes(b"{ }")
    with pytest.raises(InputError) as over:
        read_request(request, "subject")
    assert over.value.code == "INPUT_TOO_LARGE"


def test_case_variant_input_alias_is_rejected(tmp_path: Path) -> None:
    import hashlib

    from score_sw_fabric.assurance.models import seal
    from score_sw_fabric.assurance.reader import load_inputs
    from score_sw_fabric.catalog.export import canonical

    refs = {}
    for name in ("A.json", "a.json"):
        value = seal({"kind": "assurance_subject", "schema_version": 1, "name": name})
        path = tmp_path / name
        path.write_bytes(canonical(value))
        refs[name] = {
            "path": name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "semantic_digest": value["digest"],
        }
    request = {"inputs": {"first": refs["A.json"], "second": refs["a.json"]}}
    with pytest.raises(InputError):
        load_inputs(tmp_path / "request.json", request, {"first", "second"})


def test_unknown_assurance_domain_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "request.json"
    request = {
        "schema_version": 1,
        "operation": "subject",
        "assurance_domain": "unknown_domain",
        "scope": {"kind": "component", "id": "component-005", "purpose": "test"},
        "inputs": {},
        "local_paths": {"protected_roots": []},
        "output_root": "out",
        "as_of": "2026-09-29T10:00:00Z",
    }
    path.write_text(json.dumps(request))
    with pytest.raises(InputError):
        read_request(path, "subject")


def test_fixture_inputs_cannot_be_promoted_to_production(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from score_sw_fabric.cli import main

    root = Path(__file__).resolve().parents[2]
    folder = root / "tests/fixtures/assurance/production-refusal-scope"
    out = folder / "out/assessment.json"
    assert (
        main(
            [
                "assurance",
                "gate",
                "--request",
                str(folder / "gate-request.yaml"),
                "--out",
                str(out),
                "--json",
            ]
        )
        == 1
    )
    response = json.loads(capsys.readouterr().out)
    assert response["outcome"] == "blocked"
    assert "PRODUCTION_ORIGIN_UNAVAILABLE" in response["reasons"]


def test_ambiguous_base_and_workspace_input_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = tmp_path / "request"
    base.mkdir()
    (base / "shared.json").write_text("{}")
    (tmp_path / "shared.json").write_text("{}")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(InputError, match="Ambiguous input"):
        resolve_file(base, "shared.json", "/ref")


def test_reference_parses_the_bytes_it_hashed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import hashlib

    from score_sw_fabric.assurance import reader
    from score_sw_fabric.assurance.models import seal
    from score_sw_fabric.catalog.export import canonical

    value = seal({"kind": "assurance_subject", "schema_version": 1, "name": "selected"})
    selected = tmp_path / "selected.json"
    selected.write_bytes(canonical(value))
    ref = {
        "path": "selected.json",
        "sha256": hashlib.sha256(selected.read_bytes()).hexdigest(),
        "semantic_digest": value["digest"],
    }
    monkeypatch.setattr(reader, "read_json", lambda _: (_ for _ in ()).throw(AssertionError()))
    assert reader.read_reference(tmp_path, ref, "/selected")[1] == value


def test_reference_rejects_non_string_kind_without_crash(tmp_path: Path) -> None:
    import hashlib

    from score_sw_fabric.assurance.reader import read_reference
    from score_sw_fabric.catalog.export import canonical

    value = {"schema_version": 1, "kind": None, "digest": "0" * 64}
    path = tmp_path / "bad.json"
    path.write_bytes(canonical(value))
    ref = {
        "path": "bad.json",
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "semantic_digest": "0" * 64,
    }
    with pytest.raises(InputError, match="Invalid kind"):
        read_reference(tmp_path, ref, "/bad")


def test_selected_reference_requires_schema_version(tmp_path: Path) -> None:
    import hashlib

    from score_sw_fabric.assurance.models import seal
    from score_sw_fabric.assurance.reader import read_reference
    from score_sw_fabric.catalog.export import canonical

    value = seal({"kind": "assurance_subject", "name": "unversioned"})
    content = canonical(value)
    (tmp_path / "unversioned.json").write_bytes(content)
    ref = {
        "path": "unversioned.json",
        "sha256": hashlib.sha256(content).hexdigest(),
        "semantic_digest": value["digest"],
    }
    with pytest.raises(InputError) as error:
        read_reference(tmp_path, ref, "/selected")
    assert error.value.code == "VERSION_UNSUPPORTED"


def test_policy_gate_selection_rejects_non_array_predicates() -> None:
    from score_sw_fabric.assurance.package import _selected_gate

    with pytest.raises(InputError, match="must be an array"):
        _selected_gate({}, {"predicates": 42}, {})


def test_portable_assessment_embeds_current_decision_policy_and_gate_schemas() -> None:
    import json

    root = Path(__file__).resolve().parents[2] / "schemas"
    assessment = json.loads((root / "assurance-assessment.schema.json").read_text())
    for key, name in (
        ("decision", "assurance-decision"),
        ("gate_policy", "assurance-gate-policy"),
        ("gate_result", "assurance-gate-result"),
    ):
        standalone = json.loads((root / f"{name}.schema.json").read_text())
        for metadata in ("$id", "$schema", "title"):
            standalone.pop(metadata, None)
        embedded = {k: v for k, v in assessment["$defs"][key].items() if k != "title"}
        assert embedded == standalone


@pytest.mark.parametrize("field", sorted(REQUEST_FIELDS))
def test_every_missing_public_request_field_preserves_output(
    field: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from score_sw_fabric.cli import main

    request = {
        "schema_version": 1,
        "operation": "subject",
        "assurance_domain": "fixture_contract",
        "scope": {"kind": "component", "id": "component-005", "purpose": "test"},
        "inputs": {},
        "local_paths": {"protected_roots": []},
        "output_root": "out",
        "as_of": "2026-09-29T10:00:00Z",
    }
    request.pop(field)
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request))
    out = tmp_path / "out/subject.json"
    out.parent.mkdir()
    out.write_bytes(b"prior complete record")
    assert main(["assurance", "subject", "--request", str(path), "--out", str(out), "--json"]) == 2
    diagnostic = json.loads(capsys.readouterr().err)
    assert diagnostic["code"] == "FIELD_UNKNOWN"
    assert len(diagnostic["message"]) <= 4096
    assert out.read_bytes() == b"prior complete record"


@pytest.mark.parametrize("operation", ["subject", "evidence", "decision", "gate"])
def test_every_public_writer_preserves_prior_on_over_limit_request(
    operation: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from score_sw_fabric.assurance.models import MAX_REFERENCES
    from score_sw_fabric.cli import main

    request = {
        "schema_version": 1,
        "operation": operation,
        "assurance_domain": "fixture_contract",
        "scope": {"kind": "component", "id": "component-005", "purpose": "test"},
        "inputs": {f"ref-{index:05d}": None for index in range(MAX_REFERENCES + 1)},
        "local_paths": {"protected_roots": []},
        "output_root": "out",
        "as_of": "2026-09-29T10:00:00Z",
    }
    if operation == "gate":
        request["gate_mode"] = "normal"
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request))
    out = tmp_path / f"out/{operation}.json"
    out.parent.mkdir()
    out.write_bytes(b"prior complete record")
    assert main(["assurance", operation, "--request", str(path), "--out", str(out), "--json"]) == 2
    diagnostic = json.loads(capsys.readouterr().err)
    assert diagnostic["code"] == "LIMIT_EXCEEDED"
    assert len(diagnostic["message"]) <= 4096
    assert out.read_bytes() == b"prior complete record"
