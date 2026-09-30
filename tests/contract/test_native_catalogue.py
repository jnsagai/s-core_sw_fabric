"""Contract checks against a copied genuine sparse Sphinx-Needs export."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest
import yaml

from score_sw_fabric.catalog.export import seal
from score_sw_fabric.catalog.importer import build_catalogue
from score_sw_fabric.process_source.reader import InputError, IntegrityError, load_manifest

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/native"
NEED_ID = "tool_req__docs_bzl_nested_bundle"


def fixture_at(tmp_path: Path) -> Path:
    root = tmp_path / "native"
    shutil.copytree(FIXTURE, root, ignore=shutil.ignore_patterns("build"))
    return root


def manifest_at(root: Path) -> Path:
    return root / "export-manifest.yaml"


def mutate_export(root: Path, change: object) -> None:
    path = root / "needs.json"
    data = json.loads(path.read_text())
    change(data)
    path.write_text(json.dumps(data, sort_keys=True))
    manifest = yaml.safe_load(manifest_at(root).read_text())
    manifest["exports"][0]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_at(root).write_text(yaml.safe_dump(manifest))


def build(root: Path) -> dict:
    return build_catalogue(load_manifest(manifest_at(root)))


def test_genuine_export_and_defaults(tmp_path: Path) -> None:
    catalogue = build(fixture_at(tmp_path))
    assert len(catalogue["types"]) == 50
    entity = catalogue["entities"][0]
    assert entity["native_id"] == NEED_ID
    assert entity["native_version"] == 1
    assert entity["export_version"] == ""
    assert entity["raw"].get("is_external") is None
    assert entity["normalized"]["is_external"] is False
    assert entity["normalized"]["parts"] == {}
    assert (
        entity["source_ref"]["path"]
        == "src/tests/docs_bzl/scenarios/nested_bundles/parent/index.rst"
    )
    assert entity["source_ref"]["content_digest"]
    assert catalogue["engineering_readiness"] == "not_evaluated"


def test_relocation_and_source_content_digest(tmp_path: Path) -> None:
    left = fixture_at(tmp_path / "a")
    right = fixture_at(tmp_path / "b")
    assert seal(build(left))[1] == seal(build(right))[1]
    source = right / "source/src/tests/docs_bzl/scenarios/nested_bundles/parent/index.rst"
    source.write_text(source.read_text() + "\nChanged.\n")
    assert seal(build(left))[1] != seal(build(right))[1]


def test_hash_mismatch_rejected(tmp_path: Path) -> None:
    root = fixture_at(tmp_path)
    (root / "needs.json").write_bytes((root / "needs.json").read_bytes() + b" ")
    with pytest.raises(InputError, match="mismatch"):
        build(root)


def test_duplicate_json_key_rejected(tmp_path: Path) -> None:
    root = fixture_at(tmp_path)
    path = root / "needs.json"
    path.write_text('{"versions": {}, "versions": {}}')
    manifest = yaml.safe_load(manifest_at(root).read_text())
    manifest["exports"][0]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_at(root).write_text(yaml.safe_dump(manifest))
    with pytest.raises(InputError) as error:
        build(root)
    assert error.value.code == "DUPLICATE_JSON_KEY"


def test_creator_and_count_rejected(tmp_path: Path) -> None:
    root = fixture_at(tmp_path)
    mutate_export(
        root, lambda d: next(iter(d["versions"].values()))["creator"].update(version="9.0")
    )
    with pytest.raises(InputError) as error:
        build(root)
    assert error.value.code == "UNSUPPORTED_CREATOR"
    root = fixture_at(tmp_path / "count")
    mutate_export(root, lambda d: next(iter(d["versions"].values())).update(needs_amount=2))
    with pytest.raises(InputError) as error:
        build(root)
    assert error.value.code == "EXPORT_SCHEMA"


def test_resolved_version_selector_and_missing_target(tmp_path: Path) -> None:
    root = fixture_at(tmp_path)

    def add_target(data: dict) -> None:
        needs = next(iter(data["versions"].values()))["needs"]
        clone = dict(needs[NEED_ID])
        clone["id"] = "tool_req__other"
        needs["tool_req__other"] = clone
        needs[NEED_ID]["links"] = ["tool_req__other[version==1]"]
        next(iter(data["versions"].values()))["needs_amount"] = 2

    mutate_export(root, add_target)
    catalogue = build(root)
    assert catalogue["relations"][0]["target_version_selector"] == 1
    assert catalogue["relations"][0]["target_source_id"] == "docs_as_code"
    mutate_export(
        root,
        lambda d: next(iter(d["versions"].values()))["needs"][NEED_ID].update(
            links=["tool_req__other[version==2]"]
        ),
    )
    with pytest.raises(IntegrityError) as error:
        build(root)
    assert error.value.code == "UNRESOLVED_RELATION"


def test_unsupported_selector_rejected(tmp_path: Path) -> None:
    root = fixture_at(tmp_path)
    mutate_export(
        root,
        lambda d: next(iter(d["versions"].values()))["needs"][NEED_ID].update(
            links=["tool_req__other[version>=1]"]
        ),
    )
    with pytest.raises(InputError) as error:
        build(root)
    assert error.value.code == "UNSUPPORTED_SELECTOR"


def test_template_tag_preserved_without_text_parsing(tmp_path: Path) -> None:
    root = fixture_at(tmp_path)
    mutate_export(
        root,
        lambda d: next(iter(d["versions"].values()))["needs"][NEED_ID].update(
            tags=["template"],
            template="content.j2",
            pre_template="before.j2",
            post_template="after.j2",
            content=".. tool_req:: example\n   :id: tool_req__phantom",
        ),
    )
    catalogue = build(root)
    assert catalogue["entities"][0]["is_template"] is True
    assert catalogue["entities"][0]["template_keys"] == {
        "template": "content.j2",
        "pre_template": "before.j2",
        "post_template": "after.j2",
    }
    assert len(catalogue["entities"]) == 1


def test_unsupported_metamodel_even_with_updated_manifest_digest(tmp_path: Path) -> None:
    root = fixture_at(tmp_path)
    path = root / "source/src/extensions/score_metamodel/metamodel.yaml"
    path.write_text(path.read_text() + "\n# changed\n")
    manifest = yaml.safe_load(manifest_at(root).read_text())
    manifest["metamodel"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_at(root).write_text(yaml.safe_dump(manifest))
    with pytest.raises(InputError) as error:
        build(root)
    assert error.value.code == "UNSUPPORTED_METAMODEL"


def test_wrong_native_field_type_rejected(tmp_path: Path) -> None:
    root = fixture_at(tmp_path)
    mutate_export(
        root,
        lambda d: next(iter(d["versions"].values()))["needs"][NEED_ID].update(is_external="false"),
    )
    with pytest.raises(InputError) as error:
        build(root)
    assert error.value.code == "NEED_FIELD_TYPE"


def test_source_root_escape_rejected(tmp_path: Path) -> None:
    root = fixture_at(tmp_path)
    manifest = yaml.safe_load(manifest_at(root).read_text())
    manifest["sources"][0]["root"] = "../outside"
    manifest_at(root).write_text(yaml.safe_dump(manifest))
    with pytest.raises(InputError) as error:
        build(root)
    assert error.value.code == "PATH_ESCAPE"


def test_missing_source_location_is_explicit(tmp_path: Path) -> None:
    root = fixture_at(tmp_path)
    (root / "source/src/tests/docs_bzl/scenarios/nested_bundles/parent/index.rst").unlink()
    ref = build(root)["entities"][0]["source_ref"]
    assert ref["location_state"] == "unavailable"
    assert ref["path"] is None
    assert ref["docname"] == "concepts/example_bundle/index"
    assert ref["lineno"] == 18


def test_symlink_source_escape_rejected(tmp_path: Path) -> None:
    root = fixture_at(tmp_path)
    path = root / "source/src/tests/docs_bzl/scenarios/nested_bundles/parent/index.rst"
    outside = tmp_path / "outside.rst"
    outside.write_text("outside")
    path.unlink()
    path.symlink_to(outside)
    with pytest.raises(IntegrityError) as error:
        build(root)
    assert error.value.code == "SOURCE_ESCAPE"


def test_unknown_metadata_is_preserved_and_changes_digest(tmp_path: Path) -> None:
    root = fixture_at(tmp_path)
    first = seal(build(root))[0]["digest"]
    mutate_export(
        root,
        lambda d: next(iter(d["versions"].values()))["needs"][NEED_ID].update(
            custom_non_normative="changed"
        ),
    )
    catalogue = build(root)
    assert catalogue["entities"][0]["raw"]["custom_non_normative"] == "changed"
    assert seal(catalogue)[0]["digest"] != first


def test_unknown_normative_link_schema_rejected(tmp_path: Path) -> None:
    root = fixture_at(tmp_path)

    def add_schema(data: dict) -> None:
        props = next(iter(data["versions"].values()))["needs_schema"]["properties"]
        props["invented_relation"] = dict(props["links"])

    mutate_export(root, add_schema)
    with pytest.raises(InputError) as error:
        build(root)
    assert error.value.code == "UNSUPPORTED_LINK_SCHEMA"


def test_duplicate_identity_across_exports_rejected(tmp_path: Path) -> None:
    root = fixture_at(tmp_path)
    other = root / "needs-copy.json"
    other.write_bytes((root / "needs.json").read_bytes())
    manifest = yaml.safe_load(manifest_at(root).read_text())
    copied = dict(manifest["exports"][0])
    copied["path"] = "needs-copy.json"
    manifest["exports"].append(copied)
    manifest_at(root).write_text(yaml.safe_dump(manifest))
    with pytest.raises(IntegrityError) as error:
        build(root)
    assert error.value.code == "DUPLICATE_IDENTITY"
