"""Fail-closed CodeQL prerequisite inspection; synthetic identities cannot unlock execution."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from score_sw_fabric.cli import main
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality import codeql
from tests.quality_codeql_support import change_config, git, selected, write
from tests.quality_support import ref


def test_fixture_sources_pack_and_clean_input_never_execute_codeql(tmp_path: Path) -> None:
    path = selected(tmp_path)
    code, record, _, _ = codeql.capabilities(path)
    assert code == 1 and record["outcome"] == "unavailable"
    assert record["origin"] == "local_unprotected_inspection"
    assert record["source_inspection"]["origin"] == "fixture"
    assert record["source_inspection"]["source_build"]["state"] == "source_trees_equal"
    assert record["pack_inspection"]["included_source_state"] == "matched"
    assert record["capability"]["installation_state"] == "bytes_verified"
    assert record["analysis_executed"] is False and record["accepted_claims"] == 0
    assert record["assurance_eligibility"] == "not_eligible"
    assert "CODEQL_ELIGIBILITY_UNKNOWN" in record["gaps"]
    assert "CODEQL_EXECUTION_UNIMPLEMENTED" in record["gaps"]
    assert "NATIVE_REPORTING_UNEXECUTED" in record["gaps"]
    assert record["capability"]["suite_exclusions"] == [
        "external/misra/audit",
        "external/misra/default-disabled",
    ]
    assert all(p["argv"][0] == "/usr/bin/git" for p in record["phases"])
    assert not list(tmp_path.rglob("never-run-cli-marker"))


def test_blocked_run_freezes_sources_and_reports_unknown_extraction(tmp_path: Path) -> None:
    path = selected(tmp_path, "run")
    source = tmp_path / "component/check.cpp"
    before = source.read_bytes()
    code, record, _, _ = codeql.run(path)
    assert code == 1 and source.read_bytes() == before
    assert record["processed_units"] == record["diagnostics"] == []
    assert record["extraction"]["adequacy"] == "unknown"
    assert "EXTRACTION_UNKNOWN" in record["gaps"]
    assert record["source_integrity"] == "unchanged"
    assert record["baseline"]["files"][0]["sha256"] == ref(source)["sha256"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("extra", True),
        ("compiled_pack_root", "../pack"),
        ("suite", "../audit.qls"),
        ("suite", "codeql-suites/--audit.qls"),
        ("source_root", "relative"),
        ("native_sources", []),
    ],
)
def test_strict_configuration_rejects_unknown_unsafe_selections(
    field: str, value: object, tmp_path: Path
) -> None:
    path = selected(tmp_path)
    change_config(path, **{field: value})
    with pytest.raises(InputError):
        codeql.capabilities(path)


def test_missing_pack_and_unselected_build_objects_are_named(tmp_path: Path) -> None:
    path = selected(tmp_path)
    change_config(path, compiled_pack_root=None, build_source_root=None)
    code, record, _, _ = codeql.capabilities(path)
    assert code == 1 and record["pack_inspection"] is None
    assert "QUERY_PACK_UNAVAILABLE" in record["gaps"]
    assert "SOURCE_BUILD_RECONCILIATION_UNKNOWN" in record["gaps"]


def test_different_declared_build_tree_cannot_claim_equivalence(tmp_path: Path) -> None:
    path = selected(tmp_path)
    root = tmp_path / "different-build"
    root.mkdir()
    (root / "fixture.txt").write_text("Synthetic different source tree.\n")
    git(root, "init", "-q")
    git(root, "add", ".")
    git(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-qm",
        "Different synthetic build",
    )
    commit = git(root, "rev-parse", "HEAD")
    pack = tmp_path / "fixture-pack/qlpack.yml"
    value = json.loads(pack.read_bytes())
    value["buildMetadata"]["sha"] = commit
    pack.write_text(json.dumps(value))
    change_config(path, build_source_root=str(root))
    code, record, _, _ = codeql.capabilities(path)
    assert code == 1
    assert record["source_inspection"]["source_build"]["state"] == "source_trees_different"
    assert "SOURCE_BUILD_CONTENT_DIFFERS" in record["gaps"]


def test_supporting_eligible_string_is_unverified_and_cannot_unlock(tmp_path: Path) -> None:
    path = selected(tmp_path)
    eligibility = write(
        tmp_path / "eligibility.json",
        {"eligible": True, "approved_by": "agent", "domain": "fixture_contract"},
    )
    change_config(path, eligibility=ref(eligibility))
    code, record, _, _ = codeql.capabilities(path)
    assert code == 1 and "CODEQL_ELIGIBILITY_UNKNOWN" in record["gaps"]
    assert record["source_inspection"]["reporting"]["eligibility_state"] == "unverified"
    assert any(a["id"] == "eligibility" for a in record["artifacts"])


def test_declared_python39_bytes_do_not_prove_report_compatibility(tmp_path: Path) -> None:
    path = selected(tmp_path)
    chain = json.loads((tmp_path / "toolchain.json").read_bytes())
    chain["kind"] = "quality_codeql_reporting_toolchain_profile"
    chain["tool"]["version"] = "Python 3.9.25"
    reporting = write(tmp_path / "reporting.json", chain)
    change_config(path, reporting_toolchain=ref(reporting))
    code, record, _, _ = codeql.capabilities(path)
    assert code == 1
    assert record["source_inspection"]["reporting"]["interpreter_state"] == "bytes_verified"
    assert record["source_inspection"]["reporting"]["compatibility"] == "unexecuted"
    assert "NATIVE_REPORTING_UNEXECUTED" in record["gaps"]
    assert not list(tmp_path.rglob("never-run-cli-marker"))


def test_changed_tool_identity_and_dirty_source_refuse(tmp_path: Path) -> None:
    path = selected(tmp_path)
    tool = tmp_path / "fixture-cli"
    tool.write_text("changed")
    with pytest.raises(InputError, match="identity|selection|differs"):
        codeql.capabilities(path)
    tool.write_text("#!/bin/sh\ntouch never-run-cli-marker\nexit 99\n")
    native = tmp_path / "fixture-source/cpp/misra/src/rules/fixture.ql"
    native.write_text("changed native source")
    with pytest.raises(InputError):
        codeql.capabilities(path)


def test_pack_symlink_and_changed_native_suite_refuse(tmp_path: Path) -> None:
    path = selected(tmp_path)
    link = tmp_path / "fixture-pack/unselected-link"
    link.symlink_to(tmp_path / "fixture-cli")
    with pytest.raises(InputError):
        codeql.capabilities(path)
    link.unlink()
    (tmp_path / "fixture-pack/codeql-suites/misra-cpp-default.qls").write_text("[]")
    with pytest.raises(InputError):
        codeql.capabilities(path)


def test_output_inside_native_source_refuses_before_inspection(tmp_path: Path) -> None:
    path = selected(tmp_path)
    out = tmp_path / "fixture-source/result.json"
    with patch.object(codeql, "inspect", side_effect=AssertionError("inspection must not start")):
        assert (
            main(
                [
                    "quality",
                    "capabilities",
                    "--adapter",
                    "codeql",
                    "--request",
                    str(path),
                    "--out",
                    str(out),
                    "--json",
                ]
            )
            == 2
        )
    assert not out.exists()


def test_inspector_binary_is_protected_before_any_native_inspection(tmp_path: Path) -> None:
    path = selected(tmp_path)
    with patch.object(codeql, "inspect", side_effect=AssertionError("inspection must not start")):
        assert (
            main(
                [
                    "quality",
                    "capabilities",
                    "--adapter",
                    "codeql",
                    "--request",
                    str(path),
                    "--out",
                    str(codeql.INSPECTOR),
                ]
            )
            == 2
        )


def test_wrong_complementary_route_cannot_execute_codeql(tmp_path: Path) -> None:
    from score_sw_fabric.quality import complementary

    path = selected(tmp_path)
    with patch.object(complementary, "execute", side_effect=AssertionError("CLI must not execute")):
        with pytest.raises(InputError):
            complementary.capabilities(path, "codeql")


def test_cli_atomic_publication_and_rejected_old_output(tmp_path: Path) -> None:
    path = selected(tmp_path)
    out = tmp_path / "out.json"
    args = [
        "quality",
        "capabilities",
        "--adapter",
        "codeql",
        "--request",
        str(path),
        "--out",
        str(out),
        "--json",
    ]
    assert main(args) == 1
    before = out.read_bytes()
    assert main(args) == 1
    first, second = json.loads(before), json.loads(out.read_bytes())
    for record in (first, second):
        record.pop("digest")
        for phase in record["phases"]:
            phase.pop("elapsed_seconds")
    assert first == second
    before = out.read_bytes()
    value = json.loads(path.read_bytes())
    value["extra"] = True
    path.write_text(json.dumps(value))
    assert main(args) == 2 and out.read_bytes() == before


def test_added_pack_file_during_measurement_refuses_final_publication(tmp_path: Path) -> None:
    path = selected(tmp_path)
    out = tmp_path / "old.json"
    out.write_text("prior")
    original = codeql.inspect

    def changed(*args: object, **kwargs: object) -> object:
        result = original(*args, **kwargs)
        (tmp_path / "fixture-pack/added.qlx").write_bytes(b"new artifact")
        return result

    with patch.object(codeql, "inspect", side_effect=changed):
        assert (
            main(
                [
                    "quality",
                    "capabilities",
                    "--adapter",
                    "codeql",
                    "--request",
                    str(path),
                    "--out",
                    str(out),
                ]
            )
            == 2
        )
    assert out.read_text() == "prior"


def test_index_flags_cannot_hide_changed_query_bytes(tmp_path: Path) -> None:
    path = selected(tmp_path)
    root = tmp_path / "fixture-source"
    name = "cpp/misra/src/rules/fixture.ql"
    git(root, "update-index", "--assume-unchanged", name)
    (root / name).write_text("// changed bytes hidden by the index flag\n")
    (tmp_path / "fixture-pack/rules/fixture.ql").write_bytes((root / name).read_bytes())
    assert git(root, "status", "--porcelain") == ""
    with pytest.raises(InputError, match="Git blob"):
        codeql.capabilities(path)


def test_native_fsmonitor_is_disabled_and_reference_index_unchanged(tmp_path: Path) -> None:
    path = selected(tmp_path)
    root = tmp_path / "fixture-source"
    marker = tmp_path / "forbidden-fsmonitor-execution"
    hook = tmp_path / "fsmonitor-hook"
    hook.write_text(f"#!/bin/sh\ntouch '{marker}'\n")
    hook.chmod(0o755)
    git(root, "config", "core.fsmonitor", str(hook))
    index = (root / ".git/index").read_bytes()
    code, _, _, _ = codeql.capabilities(path)
    assert code == 1 and not marker.exists()
    assert (root / ".git/index").read_bytes() == index


def test_missing_library_remains_a_named_gap_and_mismatch_refuses(tmp_path: Path) -> None:
    path = selected(tmp_path)
    code, record, _, _ = codeql.capabilities(path)
    assert code == 1 and record["pack_inspection"]["library_state"] == "incomplete"
    assert "LIBRARY_UNAVAILABLE:codeql/cpp-all" in record["gaps"]
    library = tmp_path / "fixture-pack/.codeql/libraries/codeql/cpp-all/5.0.0/qlpack.yml"
    write(library, {"name": "codeql/cpp-all", "version": "5.0.0", "license": "fixture"})
    code, record, _, _ = codeql.capabilities(path)
    assert code == 1 and record["pack_inspection"]["library_state"] == "matched"
    assert "LIBRARY_SOURCE_RECONCILIATION_UNVERIFIED" in record["gaps"]
    write(library, {"name": "codeql/cpp-all", "version": "999.0.0"})
    with pytest.raises(InputError):
        codeql.capabilities(path)


def test_missing_cli_does_not_hide_drifted_runtime_dependency(tmp_path: Path) -> None:
    path = selected(tmp_path)
    (tmp_path / "fixture-cli").unlink()
    code, record, _, _ = codeql.capabilities(path)
    assert code == 1 and "CAPABILITY_UNAVAILABLE" in record["gaps"]
    (tmp_path / "fixture-cli-license.txt").write_text("changed dependency")
    with pytest.raises(InputError):
        codeql.capabilities(path)


@pytest.mark.parametrize(
    "raw", [b"cycle: &cycle [*cycle]\n", b"value: " + b"[" * 100 + b"0" + b"]" * 100]
)
def test_cyclic_or_deep_native_controls_refuse(raw: bytes, tmp_path: Path) -> None:
    path = selected(tmp_path)
    (tmp_path / "fixture-pack/qlpack.yml").write_bytes(raw)
    with pytest.raises(InputError):
        codeql.capabilities(path)


def test_oversize_native_asset_refuses_without_publishing(tmp_path: Path) -> None:
    path = selected(tmp_path)
    with (tmp_path / "fixture-pack/excess.qlx").open("wb") as stream:
        stream.truncate(16 * 1024 * 1024 + 1)
    with pytest.raises(InputError):
        codeql.capabilities(path)


def test_truncated_control_capture_remains_blocked(tmp_path: Path) -> None:
    path = selected(tmp_path)
    value = json.loads(path.read_bytes())
    value["output_limit_bytes"] = 1024
    path.write_text(json.dumps(value))
    code, record, _, _ = codeql.capabilities(path)
    assert code == 1 and "OUTPUT_TRUNCATED" in record["gaps"]
    assert any(row["truncated"] for row in record["artifacts"])
    assert record["accepted_claims"] == 0
