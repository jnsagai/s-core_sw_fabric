"""Untrusted drafts cannot dispose findings; correction scope must stay exact."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from score_sw_fabric.assurance.models import seal, verify_digest
from score_sw_fabric.cli import main
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality import dispositions
from score_sw_fabric.quality.runner import run
from tests.quality_disposition_support import change_draft, change_request, selection, write
from tests.quality_support import ROOT, ref, request


@pytest.fixture
def selected(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    current = request(tmp_path)
    _, seeded, _, _ = run(current)
    assert seeded["extraction"]["adequacy"] == "adequate" and seeded["diagnostics"]
    return selection(tmp_path, seeded, current), seeded


def corrected_selection(path: Path, **overrides: Any) -> None:
    tmp = path.parent
    shutil.copy2(ROOT / "tests/fixtures/quality/corrected/check.cpp", tmp / "component/check.cpp")
    current = request(tmp, **overrides)
    change_request(path, current={"adapter": "clang-tidy", "request": ref(current)})


@pytest.mark.parametrize(
    "kind", ["correction", "false_positive", "deviation", "recategorization", "suppression"]
)
def test_drafts_keep_names_dates_and_do_not_execute(
    selected: tuple[Path, dict[str, Any]], kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, original = selected
    change_draft(path, requested_kind=kind)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("draft must not execute an analyzer")

    monkeypatch.setattr(dispositions, "execute_current", forbidden)
    code, review, _, _ = dispositions.review(path)
    assert code == 1 and review["state"] == ("open" if kind == "correction" else "pending_review")
    assert review["fresh_run"] is None
    assert review["draft"]["native_metadata"]["approved-by"] == "agent"
    assert review["subject"]["finding"] == original["diagnostics"][review["draft"]["finding_index"]]
    assert review["engineering_readiness"] == "not_evaluated"
    assert review["assurance_eligibility"] == "not_eligible"
    verify_digest(review, "/review")
    if kind in {"deviation", "recategorization", "suppression"}:
        assert "DEVIATION_POLICY_UNKNOWN" in review["reasons"]


def test_source_change_alone_is_not_fresh_correction(selected: tuple[Path, dict[str, Any]]) -> None:
    path, _ = selected
    corrected_selection(path)
    _, record, _, _ = dispositions.review(path)
    assert record["state"] == "open" and record["fresh_run"] is None
    assert "FRESH_ANALYSIS_REQUIRED" in record["reasons"]


def test_unchanged_tracked_file_cannot_use_clean_other_file(
    selected: tuple[Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = selected
    change_request(path, action="check_correction")
    monkeypatch.setattr(dispositions, "execute_current", lambda *a: pytest.fail("no change"))
    _, record, _, _ = dispositions.review(path)
    assert record["state"] == "open"
    assert "TRACKED_SOURCE_UNCHANGED" in record["reasons"]


@pytest.mark.parametrize("overrides", [{"defines": ["FILTER=1"]}, {"expected_units": []}])
def test_filter_or_scope_changes_stale_before_execution(
    selected: tuple[Path, dict[str, Any]],
    overrides: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path, _ = selected
    corrected_selection(path, **overrides)
    change_request(path, action="check_correction")
    monkeypatch.setattr(dispositions, "execute_current", lambda *a: pytest.fail("scope drift"))
    _, record, _, _ = dispositions.review(path)
    assert record["state"] == "stale" and "ANALYSIS_SCOPE_CHANGED" in record["reasons"]


def test_policy_drift_is_named_and_does_not_execute(
    selected: tuple[Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = selected
    corrected_selection(path)
    profile = path.parent / "profile.yaml"
    profile.write_bytes((ROOT / "profiles/s-core-quality-v1.yaml").read_bytes() + b"\n# drift\n")
    current = request(path.parent, profile=ref(profile))
    change_request(
        path, current={"adapter": "clang-tidy", "request": ref(current)}, action="check_correction"
    )
    monkeypatch.setattr(dispositions, "execute_current", lambda *a: pytest.fail("policy drift"))
    _, review, _, _ = dispositions.review(path)
    assert review["state"] == "stale" and "POLICY_CHANGED" in review["reasons"]


@pytest.mark.parametrize("expires", ["2020-01-01T00:00:00Z", "2020-01-01T01:00:00+01:00"])
def test_expired_draft_stays_stale(selected: tuple[Path, dict[str, Any]], expires: str) -> None:
    path, _ = selected
    change_draft(path, expires_at=expires)
    _, review, _, _ = dispositions.review(path)
    assert review["state"] == "stale" and "DISPOSITION_EXPIRED" in review["reasons"]
    assert review["time_basis"] == "local_untrusted"


@pytest.mark.parametrize(
    "change",
    [
        {"finding_index": True},
        {"finding_index": 10000},
        {"expires_at": "2026-09-30"},
        {"expires_at": []},
        {"origin_digest": "0" * 64},
        {"construct": {"kind": "file", "path": "../check.cpp", "sha256": "0" * 64}},
        {"state": "accepted_fixture"},
        {"decision_refs": [{}] * 21},
        {"native_category": {}},
    ],
)
def test_bad_drafts_preserve_existing_output(
    selected: tuple[Path, dict[str, Any]], change: dict[str, Any]
) -> None:
    path, _ = selected
    change_draft(path, **change)
    out = path.parent / "review.json"
    out.write_text("previous output")
    assert main(["quality", "disposition", "--request", str(path), "--out", str(out)]) == 2
    assert out.read_text() == "previous output"


def test_construct_must_bind_a_native_location(selected: tuple[Path, dict[str, Any]]) -> None:
    path, _ = selected
    change_draft(path, construct={"kind": "file", "path": "other.cpp", "sha256": "0" * 64})
    with pytest.raises(InputError, match="construct"):
        dispositions.review(path)


def test_decision_bytes_are_preserved_but_not_replayed(
    selected: tuple[Path, dict[str, Any]],
) -> None:
    path, _ = selected
    decision = write(path.parent / "decision.json", {"approved-by": "agent", "outcome": "approved"})
    change_draft(path, requested_kind="false_positive", decision_refs=[decision])
    _, review, _, _ = dispositions.review(path)
    assert review["state"] == "pending_review"
    assert "DECISION_NOT_REPRODUCED" in review["reasons"]


@pytest.mark.parametrize(
    "mutate",
    [
        "incomplete",
        "suppression",
        "changed_baseline",
        "moved_finding",
        "phase_failed",
        "truncated",
        "checks_filtered",
    ],
)
def test_fresh_execution_cannot_hide_inadequacy_or_moved_check(
    selected: tuple[Path, dict[str, Any]], mutate: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, seeded = selected
    corrected_selection(path)
    fresh_path = Path(json.loads(path.read_text())["current"]["request"]["path"])
    _, fresh, inputs, protected = run(fresh_path)
    if mutate == "incomplete":
        fresh["extraction"]["adequacy"] = "incomplete"
        fresh["outcome"] = "incomplete"
    elif mutate == "suppression":
        fresh["gaps"].append("UNAPPROVED_SUPPRESSION")
    elif mutate == "changed_baseline":
        fresh["baseline"] = seeded["baseline"]
    elif mutate == "phase_failed":
        fresh["phases"][-1]["exit_code"] = 9
    elif mutate == "truncated":
        fresh["phases"][-1]["stderr"]["truncated"] = True
    elif mutate == "checks_filtered":
        fresh["capability"]["checks"] = []
    else:
        diagnostic = dict(
            seeded["diagnostics"][
                json.loads((path.parent / "draft.json").read_text())["finding_index"]
            ]
        )
        diagnostic["locations"] = [{"path": "other.cpp", "byte_offset": 0}]
        fresh["diagnostics"] = [diagnostic]
        fresh["outcome"] = "findings"
    fresh = seal(fresh)
    monkeypatch.setattr(dispositions, "execute_current", lambda *a: (1, fresh, inputs, protected))
    change_request(path, action="check_correction")
    _, review, _, _ = dispositions.review(path)
    assert review["state"] != "corrected" and review["fresh_run"] == fresh


def test_output_in_component_is_refused_before_execution(
    selected: tuple[Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = selected
    corrected_selection(path)
    change_request(path, action="check_correction")
    monkeypatch.setattr(dispositions, "execute_current", lambda *a: pytest.fail("unsafe output"))
    with pytest.raises(InputError):
        dispositions.review(path, path.parent / "component/review.json")


def test_other_kind_cannot_execute_correction(selected: tuple[Path, dict[str, Any]]) -> None:
    path, _ = selected
    change_draft(path, requested_kind="deviation")
    change_request(path, action="check_correction")
    with pytest.raises(InputError):
        dispositions.review(path)


def test_previous_wrong_subject_and_changed_rationale_refuse(
    selected: tuple[Path, dict[str, Any]],
) -> None:
    path, _ = selected
    _, prior, _, _ = dispositions.review(path)
    previous = write(path.parent / "previous.json", prior)
    change_request(path, previous=previous)
    change_draft(path, rationale="Changed review subject")
    with pytest.raises(InputError):
        dispositions.review(path)


def test_declared_accepted_history_is_never_effective(
    selected: tuple[Path, dict[str, Any]],
) -> None:
    path, _ = selected
    _, prior, _, _ = dispositions.review(path)
    prior["state"] = "accepted_fixture"
    previous = write(path.parent / "previous.json", seal(prior))
    change_request(path, previous=previous)
    with pytest.raises(InputError):
        dispositions.review(path)


def test_all_history_ancestors_are_guarded_against_overwrite(
    selected: tuple[Path, dict[str, Any]],
) -> None:
    path, _ = selected
    _, first, _, _ = dispositions.review(path)
    first_path = path.parent / "first.json"
    first_ref = write(first_path, first)
    original_bytes = first_path.read_bytes()
    change_request(path, previous=first_ref)
    _, second, _, _ = dispositions.review(path)
    change_request(path, previous=write(path.parent / "second.json", second))
    with pytest.raises(InputError):
        dispositions.review(path, first_path)
    assert first_path.read_bytes() == original_bytes


def test_missing_history_root_is_refused(selected: tuple[Path, dict[str, Any]]) -> None:
    path, _ = selected
    _, first, _, _ = dispositions.review(path)
    first["revision"] = 999
    change_request(path, previous=write(path.parent / "forged.json", seal(first)))
    with pytest.raises(InputError, match="root"):
        dispositions.review(path)


@pytest.mark.parametrize("field", ["capability", "phases", "native_bytes"])
def test_malformed_historical_output_refuses_without_traceback(
    selected: tuple[Path, dict[str, Any]], field: str
) -> None:
    path, original = selected
    if field == "native_bytes":
        original["artifacts"][0]["base64"] = "bad encoding"
    else:
        original[field] = None
    original = seal(original)
    change_request(path, origin=write(path.parent / "origin.json", original))
    change_draft(path, origin_digest=original["digest"])
    out = path.parent / "existing.json"
    out.write_text("preserved")
    assert main(["quality", "disposition", "--request", str(path), "--out", str(out)]) == 2
    assert out.read_text() == "preserved"


def test_expiry_during_analysis_stales_observation(
    selected: tuple[Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = selected
    corrected_selection(path)
    deadline = datetime(2030, 1, 1, tzinfo=UTC)
    change_draft(path, expires_at=deadline.isoformat())
    change_request(path, action="check_correction")

    class LocalClock:
        calls = 0

        @classmethod
        def now(cls, tz: Any) -> datetime:
            cls.calls += 1
            return deadline + timedelta(seconds=-1 if cls.calls == 1 else 1)

    monkeypatch.setattr(dispositions, "datetime", LocalClock)
    _, review, _, _ = dispositions.review(path)
    assert review["fresh_run"] is not None
    assert review["state"] == "stale"
    assert "DISPOSITION_EXPIRED" in review["reasons"]
