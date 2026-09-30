from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from score_sw_fabric.compiler.models import CompilerSemanticError
from score_sw_fabric.compiler.reader import load_compiler_inputs
from score_sw_fabric.process_source.reader import InputError
from tests.compiler_support import prepare_case


def test_loads_complete_digest_bound_inputs(tmp_path: Path) -> None:
    request, output = prepare_case(tmp_path)
    inputs = load_compiler_inputs(request)
    assert inputs.output_root == output.parent
    assert set(inputs.semantic_digests) == {
        "plan",
        "execution_mapping",
        "compiler_profile",
        "validator_profile",
    }


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("semantic", "SELECTED_DIGEST"),
        ("transport", "HASH_MISMATCH"),
        ("traversal", "PATH_ESCAPE"),
    ],
)
def test_rejects_tampering_and_traversal(tmp_path: Path, mutation: str, code: str) -> None:
    request, _ = prepare_case(tmp_path)
    value = yaml.safe_load(request.read_text())
    if mutation == "semantic":
        value["inputs"]["plan"]["semantic_digest"] = "0" * 64
    elif mutation == "transport":
        value["inputs"]["plan"]["sha256"] = "0" * 64
    else:
        value["inputs"]["plan"]["path"] = "../plan.json"
    request.write_text(yaml.safe_dump(value, sort_keys=False))
    with pytest.raises(InputError) as caught:
        load_compiler_inputs(request)
    assert caught.value.code == code


def test_rejects_duplicate_yaml_keys(tmp_path: Path) -> None:
    request, _ = prepare_case(tmp_path)
    request.write_text("schema_version: 1\nschema_version: 1\n")
    with pytest.raises(InputError) as caught:
        load_compiler_inputs(request)
    assert caught.value.code == "DUPLICATE_YAML_KEY"


def test_pending_mapping_is_a_semantic_block(tmp_path: Path) -> None:
    request, _ = prepare_case(tmp_path)
    request_value = yaml.safe_load(request.read_text())
    mapping_path = tmp_path / request_value["inputs"]["execution_mapping"]["path"]
    mapping = yaml.safe_load(mapping_path.read_text())
    mapping["review"] = {"state": "pending", "reference": None}
    from score_sw_fabric.compiler.reader import semantic_digest

    mapping["digest"] = semantic_digest(mapping)
    mapping_path.write_text(yaml.safe_dump(mapping, sort_keys=False))
    reference = request_value["inputs"]["execution_mapping"]
    reference["sha256"] = hashlib.sha256(mapping_path.read_bytes()).hexdigest()
    reference["semantic_digest"] = mapping["digest"]
    request.write_text(yaml.safe_dump(request_value, sort_keys=False))
    with pytest.raises(CompilerSemanticError) as caught:
        load_compiler_inputs(request)
    assert caught.value.code == "MAPPING_UNREVIEWED"
