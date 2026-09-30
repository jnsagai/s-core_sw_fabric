"""Native import preservation, conservative deduplication and refusal contracts."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path

import pytest

from score_sw_fabric.assurance.models import digest, seal
from score_sw_fabric.cli import main
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.imports import import_outputs
from tests.quality_import_support import identity, sarif, selection
from tests.quality_support import ref


def test_all_native_contributors_and_multiple_runs(tmp_path: Path) -> None:
    native = sarif()
    first = native["runs"][0]["results"][0]
    first["suppressions"] = [
        {"kind": "external", "status": "accepted", "properties": {"approved-by": "agent"}}
    ]
    first["relatedLocations"] = [{"logicalLocations": [{"fullyQualifiedName": "synthetic.main"}]}]
    second = copy.deepcopy(first)
    third = copy.deepcopy(first)
    third["locations"][0]["physicalLocation"]["region"]["startLine"] = 1
    native["runs"][0]["results"] = [first, second, third]
    native["runs"].append(copy.deepcopy(native["runs"][0]))
    code, result, _, _ = import_outputs(selection(tmp_path, native=native))
    assert code == 1 and len(result["findings"]) == 4
    assert sum(len(f["contributors"]) for f in result["findings"]) == 6
    assert "UNAPPROVED_SUPPRESSION" in result["gaps"]
    assert result["origin"] == "fixture" and result["assurance_eligibility"] == "not_eligible"
    assert result["engineering_readiness"] == "not_evaluated"
    c = result["findings"][0]["contributors"][0]
    assert c["native_record"]["suppressions"][0]["properties"]["approved-by"] == "agent"
    assert c["fingerprints"]["partialFingerprints"] == {"fixture/v1": "same"}
    assert any(loc.get("logical") for f in result["findings"] for loc in f["locations"])


def test_indexed_artifacts_uri_bases_extensions_and_flow_locations(tmp_path: Path) -> None:
    native = sarif()
    run = native["runs"][0]
    run["originalUriBaseIds"] = {
        "ROOT": {"uri": "file:///native/source/"},
        "ALIAS": {"uri": "", "uriBaseId": "ROOT"},
    }
    run["artifacts"] = [{"location": {"uri": "check.cpp", "uriBaseId": "ALIAS"}}]
    run["tool"]["extensions"][0]["rules"] = [{"id": "fixture/extension"}]
    r = run["results"][0]
    r.pop("ruleIndex")
    r["rule"] = {"index": 0, "toolComponent": {"index": 0}}
    loc = {"physicalLocation": {"artifactLocation": {"index": 0}, "region": {"startLine": 2}}}
    r["locations"] = [loc]
    r["codeFlows"] = [{"threadFlows": [{"locations": [{"location": loc}]}]}]
    r["stacks"] = [{"frames": [{"location": loc}]}]
    r["fixes"] = [
        {
            "description": {"text": "fixture fix"},
            "artifactChanges": [
                {
                    "artifactLocation": {"index": 0},
                    "replacements": [{"deletedRegion": {"startLine": 2}}],
                }
            ],
        }
    ]
    code, result, _, _ = import_outputs(selection(tmp_path, native=native))
    assert code == 1
    assert result["findings"][0]["native_id"] == "fixture/extension"
    assert len(result["findings"][0]["locations"]) >= 4
    assert all(loc["path"] == "check.cpp" for loc in result["findings"][0]["locations"])


@pytest.mark.parametrize(
    "mutation",
    [
        "version",
        "index",
        "external",
        "traversal",
        "line",
        "identity",
        "base_cycle",
        "property_file",
    ],
)
def test_bad_native_selection_preserves_prior_output(tmp_path: Path, mutation: str) -> None:
    native = sarif()
    run = native["runs"][0]
    loc = run["results"][0]["locations"][0]["physicalLocation"]
    if mutation == "version":
        native["version"] = "1.0"
    elif mutation == "index":
        loc["artifactLocation"] = {"index": 9}
    elif mutation == "external":
        loc["artifactLocation"] = {"uri": "https://example.org/a.cpp"}
    elif mutation == "traversal":
        loc["artifactLocation"] = {"uri": "%2e%2e/check.cpp"}
    elif mutation == "line":
        loc["region"]["startLine"] = 999
    elif mutation == "identity":
        run["tool"]["driver"]["semanticVersion"] = "0.0"
    elif mutation == "base_cycle":
        run["originalUriBaseIds"] = {"A": {"uri": "", "uriBaseId": "A"}}
        loc["artifactLocation"] = {"uri": "check.cpp", "uriBaseId": "A"}
    else:
        run["externalPropertyFileReferences"] = {"results": [{"location": {"uri": "remote"}}]}
    request = selection(tmp_path, native=native)
    out = tmp_path / "out.json"
    out.write_text("prior")
    assert main(["quality", "import", "--request", str(request), "--out", str(out)]) == 2
    assert out.read_text() == "prior"


def test_byte_drift_and_output_alias_refused(tmp_path: Path) -> None:
    path = selection(tmp_path)
    assert main(["quality", "import", "--request", str(path), "--out", str(path)]) == 2
    native = tmp_path / "analysis.sarif"
    native.write_text('{"version": "broken"}')
    with pytest.raises(InputError):
        import_outputs(path)


def test_reported_baseline_drift_is_visible(tmp_path: Path) -> None:
    path = selection(tmp_path)
    r = json.loads(path.read_text())
    r["artifacts"][0]["bindings"]["source_digest"] = "0" * 64
    path.write_text(json.dumps(r))
    code, result, _, _ = import_outputs(path)
    assert code == 1 and result["outcome"] == "incomplete"
    assert "BASELINE_DRIFT" in result["gaps"]


def test_duplicate_json_keys_are_refused(tmp_path: Path) -> None:
    path = selection(tmp_path)
    native = tmp_path / "analysis.sarif"
    native.write_text('{"version":"2.1.0","version":"2.1.0","runs":[]}')
    r = json.loads(path.read_text())
    r["artifacts"][0]["ref"] = ref(native)
    path.write_text(json.dumps(r))
    with pytest.raises(InputError):
        import_outputs(path)


def test_native_invocation_failure_is_independent_of_manifest(tmp_path: Path) -> None:
    native = sarif([])
    native["runs"][0]["invocations"] = [
        {
            "executionSuccessful": False,
            "toolExecutionNotifications": [
                {
                    "level": "error",
                    "message": {"text": "Synthetic failure"},
                    "exception": {"kind": "fixture"},
                }
            ],
        }
    ]
    code, record, _, _ = import_outputs(selection(tmp_path, native=native))
    assert code == 1 and record["outcome"] == "incomplete"
    assert {"PHASE_FAILED", "QUERY_FAILED", "SARIF_NOTIFICATION"} <= set(record["gaps"])


def test_logical_index_and_message_id_preserve_native_reference(tmp_path: Path) -> None:
    native = sarif()
    run = native["runs"][0]
    run["logicalLocations"] = [{"name": "fixture-function", "parentIndex": 1}, {"name": "scope"}]
    result = run["results"][0]
    result["locations"][0]["logicalLocations"] = [{"index": 0}]
    result["message"] = {"id": "fixture-message", "arguments": ["argument"]}
    run["tool"]["driver"]["rules"][0]["messageStrings"] = {"fixture-message": {"text": "{0}"}}
    code, record, _, _ = import_outputs(selection(tmp_path, native=native))
    assert code == 1
    contributor = record["findings"][0]["contributors"][0]
    assert contributor["native_record"]["message"]["id"] == "fixture-message"
    assert contributor["message"]["resolved_template"]["text"] == "{0}"
    assert any(
        loc.get("logical", {}).get("parent", {}).get("name") == "scope"
        for loc in record["findings"][0]["locations"]
    )


def test_oversize_native_stream_retains_hash_and_prefix(tmp_path: Path) -> None:
    path = selection(tmp_path, native=sarif([]))
    native = tmp_path / "analysis.sarif"
    native.write_bytes(b"x" * (16 * 1024 * 1024 + 1))
    request = json.loads(path.read_text())
    request["artifacts"][0]["ref"] = ref(native)
    path.write_text(json.dumps(request))
    code, record, _, _ = import_outputs(path)
    assert code == 1 and "OUTPUT_TRUNCATED" in record["gaps"]
    raw = record["artifacts"][0]["raw"]
    assert raw["truncated"] and raw["bytes"] == 16 * 1024 * 1024 + 1
    assert raw["sha256"] == ref(native)["sha256"]
    prefix = base64.b64decode(raw["base64"])
    assert len(prefix) == 16 * 1024 * 1024
    assert hashlib.sha256(prefix).hexdigest() == raw["retained_sha256"]


@pytest.mark.parametrize(
    "field,value", [("origin", "production"), ("origin", ["fixture"]), ("unknown", "extra")]
)
def test_import_controls_refuse_origin_upgrade_and_unknown_fields(
    tmp_path: Path, field: str, value: object
) -> None:
    path = selection(tmp_path)
    record = json.loads(path.read_text())
    record[field] = value
    path.write_text(json.dumps(record))
    with pytest.raises(InputError):
        import_outputs(path)


@pytest.mark.parametrize(
    "native",
    [
        "Diagnostics: []\nDiagnostics: []\n",
        "Diagnostics: &anchor []\nOther: *anchor\n",
        "Diagnostics:\n - DiagnosticName: fixture/check\n   DiagnosticMessage:\n"
        "     Message: Synthetic defect\n     FilePath: check.cpp\n     FileOffset: 0\n"
        "     Replacements:\n      - {FilePath: /external/check.cpp, Offset: 0, Length: 1}\n"
        "   Level: Warning\n",
        "Diagnostics:\n - DiagnosticName: fixture/check\n   DiagnosticMessage:\n"
        "     Message: Synthetic defect\n     FilePath: check.cpp\n     FileOffset: 0\n"
        "   ExtraNativeProperty: .nan\n   Level: Warning\n",
    ],
)
def test_native_yaml_alias_duplicate_range_and_nonfinite_refused(
    tmp_path: Path, native: str
) -> None:
    path = selection(tmp_path)
    request = json.loads(path.read_text())
    baseline_path = Path(request["baseline"]["path"])
    baseline = json.loads(baseline_path.read_text())
    selected_identity = {
        **identity("cppcheck"),
        "id": "clang-tidy",
        "name": "clang-tidy",
        "version": "19.1.7",
    }
    baseline["identities"] = [selected_identity]
    baseline_path.write_text(json.dumps(seal(baseline)))
    request["baseline"] = ref(baseline_path)
    for artifact in request["artifacts"]:
        artifact["tool"] = "clang-tidy"
        artifact["bindings"]["identity_digest"] = digest(selected_identity)
    raw = tmp_path / "analysis.yaml"
    raw.write_text(native)
    request["artifacts"][0].update(format="clang-tidy-yaml", ref=ref(raw))
    manifest_path = Path(request["extraction"]["path"])
    manifest = json.loads(manifest_path.read_text())
    manifest["observations"][0].update(
        tool="clang-tidy", extracted_units=None, identity_digest=digest(selected_identity)
    )
    manifest_path.write_text(json.dumps(seal(manifest)))
    request["extraction"] = ref(manifest_path)
    path.write_text(json.dumps(request))
    with pytest.raises(InputError):
        import_outputs(path)
