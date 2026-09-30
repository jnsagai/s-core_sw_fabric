"""008 coverage, native rules, feedback loop, re-analysis, promotions and roles (AC008-01–11)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.safety.analysis import check
from tests.agent_support import REPO_LOCK, ROOT, ref, write_yaml
from tests.safety_support import FIXTURES, check_request, codes, copy_version, replace, report

LATE = "comp_saf_fmea__telemetry_guard__late_sample"
LOST = "comp_saf_fmea__telemetry_guard__sample_lost"


def item(record: dict[str, Any], identifier: str) -> dict[str, Any]:
    return next(entry for entry in record["items"] if entry["id"] == identifier)


def test_demo02_v1_gap_blocks_design_and_proposes_feedback(tmp_path: Path) -> None:
    status, record, _, _ = check(check_request(tmp_path, FIXTURES / "v1"))
    assert status == 1 and record["outcome"] == "blocked"
    assert record["design_prerequisites"] == {
        "state": "blocked",
        "reasons": ["MITIGATION_UNRESOLVED"],
    }
    assert item(record, LATE)["mitigation_state"] == "missing"
    unresolved = next(
        entry for entry in record["findings"] if entry["code"] == "MITIGATION_UNRESOLVED"
    )
    assert unresolved["rule"] == "gd_req__saf_attr_mitigation_issue"
    assert record["feedback"] == [
        {
            "item": LATE,
            "action": "requirement_or_aou_review",
            "routes": ["requirements_review", "architecture_review", "reanalysis"],
            "iteration": 1,
            "max_iterations": 3,
        }
    ]
    states = {row["catalogue_id"]: row["state"] for row in record["coverage"]}
    assert len(states) == 15 and states["MF_01_02"] == "analysed"
    assert set(states.values()) == {"analysed", "excluded"}
    assert "comp_saf_fmea__example__ignored" not in {entry["id"] for entry in record["items"]}
    assert "AOU_TRANSFER_REVIEW" in codes(record)
    assert record["engineering_readiness"] == "not_evaluated"


def test_demo02_v2_feedback_applied_is_ready_for_review_not_accepted(tmp_path: Path) -> None:
    status, record, _, _ = check(
        check_request(tmp_path, FIXTURES / "v2", baseline=FIXTURES / "v1", iteration=2)
    )
    assert status == 0 and record["design_prerequisites"]["state"] == "ready_for_design_review"
    late = item(record, LATE)
    assert late["mitigation_state"] == "linked_pending_review"
    assert late["mitigated_by"] == ["comp_req__telemetry_guard__stale_detection"]
    assert (late["sufficient"], late["status"]) == ("no", "invalid")
    reanalysis = record["reanalysis"]
    assert reanalysis["changed"] == ["comp_arc_dyn__telemetry_guard__evaluate"]
    assert "comp_req__telemetry_guard__stale_detection" in reanalysis["new"]
    assert set(reanalysis["reanalysed_items"]) == {
        LATE,
        LOST,
        "comp_saf_fmea__telemetry_guard__wrong_verdict",
    }
    assert record["feedback"] == [] and record["promotions"] == []


def test_unchanged_item_on_changed_element_requires_reanalysis(tmp_path: Path) -> None:
    current = copy_version(tmp_path, "v2")
    replace(
        current / "fmea.rst",
        " Re-analysed for the timeout check in v2; the check does not change this path.",
        "",
    )
    record = report(tmp_path, current, baseline=FIXTURES / "v1", iteration=2)
    assert item(record, LOST)["reanalysis_required"] is True
    assert "REANALYSIS_REQUIRED" in record["design_prerequisites"]["reasons"]


def test_new_architecture_element_must_be_analysed(tmp_path: Path) -> None:
    current = copy_version(tmp_path, "v2")
    replace(current / "fmea.rst", ", comp_arc_dyn__telemetry_guard__timeout_check", "")
    record = report(tmp_path, current, baseline=FIXTURES / "v1", iteration=2)
    assert "NEW_ELEMENT_UNANALYSED" in codes(record)
    assert record["reanalysis"]["unreferenced_new_elements"] == [
        "comp_arc_dyn__telemetry_guard__timeout_check"
    ]


def test_loop_budget_escalates_to_human(tmp_path: Path) -> None:
    record = report(tmp_path, FIXTURES / "v1", iteration=3)
    assert record["feedback"][0]["action"] == "escalate_to_human"
    assert "ESCALATE_TO_HUMAN" in record["design_prerequisites"]["reasons"]


@pytest.mark.parametrize(
    ("old", "new", "code"),
    [
        (
            "   * - MF_01_03\n     - sample received too early\n     - no\n",
            "",
            "CATALOGUE_ID_UNCOVERED",
        ),
        (
            "\n     - Analysed in comp_saf_fmea__telemetry_guard__wrong_verdict.",
            "",
            "APPLICABILITY_UNKNOWN",
        ),
        (
            "   * - MF_01_04\n     - sample not received by all recipients\n     - no",
            "   * - MF_01_04\n     - sample not received by all recipients\n     - yes",
            "APPLICABLE_WITHOUT_ITEM",
        ),
        (
            "   * - MF_01_05\n     - sample corrupted\n     - no",
            "   * - MF_01_05\n     - sample corrupted\n     - <yes | no>",
            "APPLICABILITY_UNKNOWN",
        ),
        (
            "   * - MF_01_06",
            "   * - XX_01_01\n     - bogus\n     - no\n     - Bogus row.\n   * - MF_01_06",
            "UNKNOWN_CATALOGUE_ID",
        ),
        (
            "   * - MF_01_07",
            "   * - MF_01_06\n     - again\n     - no\n     - Duplicate.\n   * - MF_01_07",
            "DUPLICATE_ROW",
        ),
    ],
)
def test_coverage_faults(tmp_path: Path, old: str, new: str, code: str) -> None:
    current = copy_version(tmp_path, "v2")
    replace(current / "fmea.rst", old, new)
    record = report(tmp_path, current)
    assert code in codes(record) and record["outcome"] == "blocked"


def test_exclusion_needs_rationale(tmp_path: Path) -> None:
    current = copy_version(tmp_path, "v2")
    text = (current / "fmea.rst").read_text()
    start = text.index("   * - MF_01_03")
    end = text.index("   * - MF_01_04")
    row = text[start:end].splitlines()
    row[-1] = "     - <Rationale if not applicable>"
    (current / "fmea.rst").write_text(text[:start] + "\n".join(row) + "\n" + text[end:])
    assert "EXCLUSION_WITHOUT_RATIONALE" in codes(report(tmp_path, current))


@pytest.mark.parametrize(
    ("old", "new", "code", "rule"),
    [
        (
            "verdict update.\n   :mitigated_by: comp_req__telemetry_guard__report_missing\n"
            "   :sufficient: no",
            "verdict update.\n   :sufficient: yes",
            "SUFFICIENT_WITHOUT_MITIGATION",
            "gd_req__saf_attr_sufficient",
        ),
        (
            ":mitigated_by: comp_req__telemetry_guard__report_missing\n"
            "   :sufficient: no\n   :status: invalid",
            ":sufficient: no\n   :status: valid",
            "VALID_WITHOUT_MITIGATION",
            "gd_req__saf_attr_mitigated_by",
        ),
        (
            ":failure_effect: The consumer receives no verdict update.",
            ":failure_effect: <description>",
            "PLACEHOLDER",
            None,
        ),
        (
            ":failure_effect: The consumer receives no verdict update.\n",
            "",
            "MANDATORY_OPTION",
            None,
        ),
        (
            ":sufficient: no\n   :status: invalid\n\n   Draft argument: reporting",
            ":sufficient: maybe\n   :status: invalid\n\n   Draft argument: reporting",
            "OPTION_FORMAT",
            None,
        ),
        (
            "mitigated_by: comp_req__telemetry_guard__report_missing",
            "mitigated_by: comp_req__telemetry_guard__nope",
            "LINK_UNRESOLVED",
            None,
        ),
        (
            "mitigated_by: comp_req__telemetry_guard__report_missing",
            "mitigated_by: comp_arc_dyn__telemetry_guard__evaluate",
            "LINK_TYPE",
            None,
        ),
        ("issues/12", "pull/12", "MITIGATION_ISSUE_FORMAT", None),
        (":fault_id: MF_01_01", ":fault_id: ZZ_09_09", "UNKNOWN_CATALOGUE_ID", None),
    ],
)
def test_item_rules_name_native_rule(
    tmp_path: Path, old: str, new: str, code: str, rule: str | None
) -> None:
    current = copy_version(tmp_path, "v2")
    replace(current / "fmea.rst", old, new)
    record = report(tmp_path, current)
    matching = [entry for entry in record["findings"] if entry["code"] == code]
    assert matching and record["outcome"] == "blocked"
    assert matching[0]["rule"] == rule


def test_dfa_violates_must_be_static_architecture(tmp_path: Path) -> None:
    current = copy_version(tmp_path, "dfa")
    replace(
        current / "dfa.rst",
        ":violates: comp_arc_sta__telemetry_guard__monitor",
        ":violates: comp_req__telemetry_guard__report_missing",
    )
    assert "LINK_TYPE" in codes(report(tmp_path, current, analysis="dfa"))


def test_demo03_platform_initiators_need_resolvable_allocation(tmp_path: Path) -> None:
    record = report(tmp_path, FIXTURES / "dfa", analysis="dfa")
    uncovered = {row["catalogue_id"] for row in record["coverage"] if row["state"] == "uncovered"}
    assert uncovered and all(identifier[:2] in {"SR", "SC"} for identifier in uncovered)
    assert "ALLOCATION_UNRESOLVED" in codes(record)
    names = [
        ("requirements.rst", "requirements"),
        ("architecture.rst", "architecture"),
        ("dfa.rst", "analysis"),
        ("platform_dfa.rst", "allocation"),
    ]
    allocated = report(
        tmp_path,
        FIXTURES / "dfa",
        analysis="dfa",
        names=names,
        allocation="doc__platform_dfa_fixture",
    )
    assert "ALLOCATION_UNRESOLVED" not in codes(allocated)
    assert {row["state"] for row in allocated["coverage"]} == {"analysed", "excluded", "allocated"}
    concern = item(allocated, "comp_saf_dfa__telemetry_guard__shared_time_source")
    assert concern["mitigation_state"] == "proposed" and concern["catalogue_id"] == "SI_01_02"
    assert allocated["design_prerequisites"]["reasons"] == ["MITIGATION_UNRESOLVED"]
    wrong = report(
        tmp_path,
        FIXTURES / "dfa",
        analysis="dfa",
        names=names,
        allocation="comp_req__telemetry_guard__report_missing",
    )
    assert "ALLOCATION_UNRESOLVED" in codes(wrong)


def _promoted(tmp_path: Path) -> Path:
    current = copy_version(tmp_path, "v2", "v2-agent")
    replace(
        current / "fmea.rst",
        "issues/12\n   :sufficient: no\n   :status: invalid",
        "issues/12\n   :sufficient: yes\n   :status: valid",
    )
    return current


def test_agent_promotion_is_untrusted(tmp_path: Path) -> None:
    current = _promoted(tmp_path)
    agent = seal(
        {
            "schema_version": 1,
            "kind": "agent_output_check",
            "changes": [{"path": "fmea.rst", "change": "modified"}],
        }
    )
    record = report(tmp_path, current, baseline=FIXTURES / "v2", agent_checks=[agent], iteration=2)
    assert {(entry["field"], entry["classification"]) for entry in record["promotions"]} == {
        ("sufficient", "UNTRUSTED_PROMOTION"),
        ("status", "UNTRUSTED_PROMOTION"),
    }
    assert (
        record["outcome"] == "blocked"
        and "UNTRUSTED_PROMOTION" in record["design_prerequisites"]["reasons"]
    )


def test_unreviewed_human_promotion_is_recorded_for_the_gate(tmp_path: Path) -> None:
    current = _promoted(tmp_path)
    record = report(tmp_path, current, baseline=FIXTURES / "v2", iteration=2)
    assert {entry["classification"] for entry in record["promotions"]} == {"PROMOTION_UNREVIEWED"}
    assert item(record, LATE)["mitigation_state"] == "claimed_sufficient"


def test_agent_checks_must_be_sealed_007_records(tmp_path: Path) -> None:
    with pytest.raises(InputError):
        check(
            check_request(tmp_path, FIXTURES / "v2", agent_checks=[{"kind": "agent_output_check"}])
        )


def _roles(
    tmp_path: Path, fmea: dict[str, Any] | None = None, dfa: dict[str, Any] | None = None
) -> tuple[Path, dict[str, Any]]:
    root = tmp_path / "component"
    (root / "docs/safety_analysis").mkdir(parents=True)
    for name in ("requirements.rst", "architecture.rst"):
        (root / "docs" / name).write_text((FIXTURES / "v2" / name).read_text())
    (root / "docs/safety_analysis/fmea.rst").write_text((FIXTURES / "v2/fmea.rst").read_text())
    base_fmea = yaml.safe_load(
        (ROOT / "profiles/agent-role-fmea-analyst-draft-v1.yaml").read_text()
    )
    base_dfa = yaml.safe_load((ROOT / "profiles/agent-role-dfa-analyst-draft-v1.yaml").read_text())
    roles = {
        "lock": ref(REPO_LOCK),
        "fmea": write_yaml(tmp_path / "control/fmea-role.yaml", {**base_fmea, **(fmea or {})}),
        "dfa": write_yaml(tmp_path / "control/dfa-role.yaml", {**base_dfa, **(dfa or {})}),
    }
    return root, roles


NAMES = [
    ("docs/requirements.rst", "requirements"),
    ("docs/architecture.rst", "architecture"),
    ("docs/safety_analysis/fmea.rst", "analysis"),
]


def test_fmea_and_dfa_roles_are_separate_and_confined(tmp_path: Path) -> None:
    root, roles = _roles(tmp_path)
    record = report(tmp_path, root, names=NAMES, roles=roles)
    assert [entry["role"] for entry in record["roles"]] == ["fmea_analyst", "dfa_analyst"]
    assert not {"ROLE_NOT_SEPARATE", "ROLE_SCOPE_OVERLAP", "ROLE_SCOPE_EXCEEDS_ANALYSIS"} & codes(
        record
    )


@pytest.mark.parametrize(
    ("fmea", "dfa", "code"),
    [
        (None, {"write_scope": ["docs/safety_analysis/*.rst"]}, "ROLE_SCOPE_OVERLAP"),
        ({"write_scope": ["docs/**"]}, None, "ROLE_SCOPE_EXCEEDS_ANALYSIS"),
        (None, {"role": "fmea_analyst"}, "ROLE_NOT_SEPARATE"),
        (None, {"id": "role.fmea-analyst.draft-v1"}, "ROLE_NOT_SEPARATE"),
    ],
)
def test_role_separation_faults(tmp_path: Path, fmea: Any, dfa: Any, code: str) -> None:
    root, roles = _roles(tmp_path, fmea, dfa)
    assert code in codes(report(tmp_path, root, names=NAMES, roles=roles))


def test_forbidden_role_grant_is_refused(tmp_path: Path) -> None:
    root, roles = _roles(tmp_path, {"credentials": ["approval_key"]})
    with pytest.raises(InputError) as error:
        check(check_request(tmp_path, root, names=NAMES, roles=roles))
    assert error.value.code == "CREDENTIAL_FORBIDDEN"


def test_native_input_drift_is_refused(tmp_path: Path) -> None:
    current = copy_version(tmp_path, "v2")
    request = check_request(tmp_path, current)
    (current / "fmea.rst").write_text("changed")
    with pytest.raises(InputError) as error:
        check(request)
    assert error.value.code == "INPUT_DRIFT"
