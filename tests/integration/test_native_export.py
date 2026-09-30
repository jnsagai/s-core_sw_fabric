"""Pinned upstream fixture and fresh process export integration evidence."""

import hashlib
import json
import os
from pathlib import Path

import pytest

from score_sw_fabric.catalog.importer import build_catalogue
from score_sw_fabric.process_source.reader import load_manifest

ROOT = Path(__file__).resolve().parents[2]
FMEA_DFA_FDR = {
    "wp__feature_fmea",
    "wp__feature_dfa",
    "wp__sw_component_fmea",
    "wp__sw_component_dfa",
    "wp__fdr_reports",
}


def test_pinned_upstream_expected_export() -> None:
    path = ROOT / "tests/fixtures/native/export-manifest.yaml"
    catalogue = build_catalogue(load_manifest(path))
    assert catalogue["entities"][0]["native_id"] == "tool_req__docs_bzl_nested_bundle"


def test_saved_fresh_process_export_bytes_and_definitions() -> None:
    path = ROOT / "specs/001-native-process-catalog/evidence/process-needs.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        "931f1a57ff36208807bfd901ab7eee8d6629edfe60e93790f3f45c70407d65f8"
    )
    data = json.loads(path.read_text())
    assert data["current_version"] == "0.1"
    block = data["versions"]["0.1"]
    assert block["creator"] == {"program": "sphinx_needs", "version": "8.3.1"}
    assert block["needs_defaults_removed"] is True
    assert block["needs_amount"] == len(block["needs"]) == 1251
    for native_id in FMEA_DFA_FDR:
        assert block["needs"][native_id]["type"] == "workproduct"
        assert block["needs"][native_id]["version"] == 1


def test_live_fresh_process_catalogue_when_manifest_supplied() -> None:
    configured = os.environ.get("SCORE_NATIVE_EXPORT_MANIFEST")
    if not configured:
        pytest.skip("set SCORE_NATIVE_EXPORT_MANIFEST after a fresh native build")
    catalogue = build_catalogue(load_manifest(Path(configured)))
    assert len(catalogue["entities"]) == 1251
    assert len(catalogue["relations"]) == 7056
    assert all(e["source_ref"]["location_state"] == "verified" for e in catalogue["entities"])
    assert FMEA_DFA_FDR.issubset({e["native_id"] for e in catalogue["entities"]})
    assert catalogue["engineering_readiness"] == "not_evaluated"
