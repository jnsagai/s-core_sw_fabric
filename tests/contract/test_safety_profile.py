"""008 pinned safety profile and native list-table parsing (008-R01)."""

from __future__ import annotations

import copy
from typing import Any

import pytest
import yaml

from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.safety.native import links, list_table_rows, read_native
from score_sw_fabric.safety.profile import extract_catalogue, load_profile, validate_profile
from tests.agent_support import ROOT
from tests.safety_support import PROFILE

RAW: dict[str, Any] = yaml.safe_load(PROFILE.read_text())


def test_profile_catalogues_rules_and_sources() -> None:
    profile = load_profile(PROFILE.read_bytes())
    fmea = profile["analyses"]["fmea"]
    dfa = profile["analyses"]["dfa"]
    assert len(fmea["catalogue"]) == 15 and {item["scope"] for item in fmea["catalogue"]} == {
        "component"
    }
    assert len(dfa["catalogue"]) == 35
    platform = {item["id"][:2] for item in dfa["catalogue"] if item["scope"] == "platform"}
    assert platform == {"SR", "SC"}
    assert fmea["violates"] == ["comp_arc_dyn", "comp_arc_sta"] and dfa["violates"] == [
        "comp_arc_sta"
    ]
    assert fmea["mandatory"]["sufficient"] == "^(yes|no)$"
    assert {rule["id"] for rule in profile["rules"]} == {
        "gd_req__saf_attr_sufficient",
        "gd_req__saf_attr_mitigated_by",
        "gd_req__saf_attr_mitigation_issue",
    }
    assert [item["id"] for item in profile["checklist"]] == [f"Gen {n}" for n in range(1, 7)]
    assert profile["status"] == "draft_owner_review_pending"
    assert profile["platform_allocation"]["status"] == "fabric_policy_pending_owner_review"


def test_profile_sources_match_000_locks_where_locked() -> None:
    upstream = yaml.safe_load((ROOT / "upstream.lock.yaml").read_text())
    locked = {
        (source["repository"], path): value
        for source in upstream["sources"]
        for path, value in source.get("source_file_sha256", {}).items()
    }
    matched = 0
    for source in RAW["sources"]:
        key = (source["repository"], source["path"])
        if key in locked:
            assert locked[key] == source["sha256"], key
            matched += 1
        commit = next(
            item["commit"]
            for item in upstream["sources"]
            if item["repository"] == source["repository"]
        )
        assert commit == source["commit"]
    assert matched == 4


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda value: value.update(extra=1), "FIELD_UNKNOWN"),
        (
            lambda value: value["analyses"]["fmea"]["catalogue"].append(
                value["analyses"]["fmea"]["catalogue"][0]
            ),
            "DUPLICATE_ID",
        ),
        (lambda value: value["analyses"]["fmea"]["catalogue"][0].update(id="MF-1"), "ID_FORMAT"),
        (
            lambda value: value["analyses"]["dfa"]["catalogue"][0].update(scope="feature"),
            "FIELD_ENUM",
        ),
        (lambda value: value["analyses"]["fmea"]["mandatory"].pop("fault_id"), "PROFILE_FIELD"),
        (lambda value: value["analyses"]["fmea"]["mandatory"].update(status="("), "PROFILE_REGEX"),
        (lambda value: value["rules"].pop(), "PROFILE_FIELD"),
        (lambda value: value["gates"].update(closure=value["gates"]["design"]), "PROFILE_FIELD"),
        (lambda value: value["loop"].update(max_iterations=0), "LIMIT_EXCEEDED"),
        (lambda value: value["checklist"][0].update(source="unpinned"), "FIELD_ENUM"),
        (lambda value: value["sources"][0].update(commit="main"), "HASH_FORMAT"),
    ],
)
def test_profile_refusals(mutate: Any, code: str) -> None:
    value = copy.deepcopy(RAW)
    mutate(value)
    with pytest.raises(InputError) as error:
        validate_profile(value)
    assert error.value.code == code


def test_list_table_rows_join_continuations_and_skip_header() -> None:
    body = """   :header-rows: 1

   * - ID
     - Text
   * - MF_01_01
     - first line
       continued
   * - MF_01_02
     - second
"""
    assert [row["cells"] for row in list_table_rows(body)] == [
        ["MF_01_01", "first line continued"],
        ["MF_01_02", "second"],
    ]
    assert links("a, b  c") == ["a", "b", "c"]


def test_catalogue_extraction_uses_id_column_and_platform_titles() -> None:
    text = """.. list-table:: DFA shared resources (used for Platform DFA)
   :header-rows: 1

   * - ID
     - Cause
   * - SR_01_01
     - Reused software

.. list-table:: Fault Models
   :header-rows: 1

   * - Element
     - ID
     - Mode
   * - message
     - MF_01_01
     - lost
"""
    assert extract_catalogue(text) == [
        {
            "id": "SR_01_01",
            "group": "DFA shared resources (used for Platform DFA)",
            "scope": "platform",
        },
        {"id": "MF_01_01", "group": "Fault Models", "scope": "component"},
    ]


def test_native_reader_ignores_code_blocks_and_records_duplicates() -> None:
    text = """.. comp_req:: A
   :id: comp_req__a
   :status: valid

   Body.

.. code-block:: rst

   .. comp_req:: Example
      :id: comp_req__example

.. comp_req:: A again
   :id: comp_req__a
"""
    native = read_native([("req.rst", text.encode(), "requirements")], {"comp_req"})
    assert set(native.needs) == {"comp_req__a"}
    assert native.duplicates == ["comp_req__a"]
    assert native.needs["comp_req__a"]["content"] == "Body."
