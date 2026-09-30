"""Independently replay observations and keep missing engineering prerequisites explicit."""

from __future__ import annotations

import base64
import stat
from pathlib import Path
from typing import Any

from score_sw_fabric.agents.models import protected_roots
from score_sw_fabric.assurance.models import (
    bounded_list,
    exact,
    seal,
    sha,
    stable_id,
    verify_digest,
    version,
)
from score_sw_fabric.assurance.package import verify_assessment as verify_005
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality import decisions, packet
from score_sw_fabric.quality import disposition_models as dm
from score_sw_fabric.quality import dispositions as draft_reviews
from score_sw_fabric.quality import import_models as im
from score_sw_fabric.quality.models import Budget, raw_bytes
from score_sw_fabric.quality.models import digest as byte_digest
from score_sw_fabric.quality.packet_models import bounded_record, label
from score_sw_fabric.quality.profile import load_profile
from score_sw_fabric.runtime.models import output_path
from score_sw_fabric.runtime.request import _local, parse_json

REQUEST_FIELDS = {
    "profile",
    "packet",
    "current_baseline",
    "decisions",
    "assurance_domain",
    "as_of",
    "protected_roots",
}
ASSESSMENT_FIELDS = {
    "request_path",
    "packet_bytes",
    "request",
    "profile",
    "profile_bytes",
    "packet",
    "packet_replay",
    "current_baseline",
    "decisions",
    "dispositions",
    "obligations",
    "denominator",
    "gaps",
    "outcome",
    "accepted_claims",
    "assurance_domain",
    "as_of",
    "time_basis",
    "origin",
    "assurance_eligibility",
    "engineering_readiness",
    "limitations",
    "digest",
}
LIMITATIONS = [
    "Independent structural replay cannot authenticate local or imported analyzer execution.",
    "The supported unmapped profile cannot produce a fixture or production compliance pass.",
    "Caller-selected time and fixture receipt keys cannot authenticate production decisions.",
    "Supporting 005 decisions do not adopt guideline mappings or discharge manual review.",
    "Historical correction observations are unprotected and are never reexecuted here.",
    "Native policy/status and human-owned 005/009/010 reviews remain unchanged.",
]


def _selected_bytes(base: Path, ref: Any, limit: int = dm.MAX_RECORD) -> tuple[Path, bytes]:
    """Retain bounded original transports rather than reconstructing JSON serialization."""
    selected = dm.ref(ref, "/selected")
    path = _local(base, selected["path"], "/selected/path")
    try:
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise InputError("LIMIT_EXCEEDED", "Selected original exceeds regular-file/byte bounds")
        with path.open("rb") as stream:
            data = stream.read(limit + 1)
    except OSError as exc:
        raise InputError("INPUT_INVALID", "Selected original is unavailable") from exc
    if len(data) > limit or byte_digest(data) != selected["sha256"]:
        raise InputError("INPUT_DRIFT", "Selected original grew or changed")
    return path, data


def _record_original(raw: Any, ref: Any, record: dict[str, Any]) -> None:
    """Strict complete original bytes for a selected derived record, bounded at 96 MiB."""
    exact(
        raw,
        {"format", "bytes", "sha256", "retained_sha256", "base64", "truncated"},
        "/record_bytes",
    )
    dm.ref(ref, "/record_ref")
    if (
        raw["format"] != "bytes"
        or raw["truncated"] is not False
        or type(raw["bytes"]) is not int
        or not 0 <= raw["bytes"] <= dm.MAX_RECORD
        or not isinstance(raw["base64"], str)
        or len(raw["base64"]) > 134217728
    ):
        raise InputError("LIMIT_EXCEEDED", "Selected record original exceeds bounds")
    try:
        data = base64.b64decode(raw["base64"], validate=True)
    except (ValueError, TypeError) as exc:
        raise InputError("INPUT_DRIFT", "Invalid original encoding") from exc
    expected_hash = sha(ref["sha256"], "/record_ref/sha256")
    if (
        len(data) != raw["bytes"]
        or byte_digest(data) != expected_hash
        or raw["sha256"] != expected_hash
        or raw["retained_sha256"] != expected_hash
        or parse_json(data, "/record_original") != record
    ):
        raise InputError("INPUT_DRIFT", "Selected record does not match its original transport")


def _current(
    current: dict[str, Any] | None, request: dict[str, Any], request_path: Path
) -> dict[str, Any] | None:
    if current is None:
        if request["current_baseline"] is not None:
            raise InputError("PACKET_CLOSURE_MISSING", "Current baseline originals are absent")
        return None
    if request["current_baseline"] is None:
        raise InputError("FIELD_TYPE", "Unselected current baseline")
    exact(current, {"record", "record_bytes", "snapshot", "sources"}, "/current_baseline")
    raw = current["record_bytes"]
    dm._raw(raw)
    if (
        raw["truncated"]
        or raw["format"] != "bytes"
        or raw["sha256"] != request["current_baseline"]["sha256"]
    ):
        raise InputError("INPUT_DRIFT", "Current baseline control differs")
    b = version(
        parse_json(raw_bytes(raw), "/current_baseline"),
        "quality_import_baseline",
        im.BASELINE_FIELDS,
        "/current_baseline",
    )
    if b != current["record"]:
        raise InputError("INPUT_DRIFT", "Current baseline control was changed")
    verify_digest(b, "/current_baseline")
    stable_id(b["component"], "/component")
    expected = dm.files(b["files"])
    sources = {}
    total = 0
    for s in bounded_list(current["sources"], 500, "/current/sources"):
        exact(s, {"path", "raw"}, "/current/source")
        name = s["path"]
        dm._raw(s["raw"])
        if name in sources or name not in expected:
            raise InputError("BASELINE_DRIFT", "Duplicate or unselected current source")
        data = raw_bytes(s["raw"])
        if (
            s["raw"]["truncated"]
            or s["raw"]["format"] != "bytes"
            or byte_digest(data) != expected[name]
        ):
            raise InputError("INPUT_DRIFT", "Current source bytes differ")
        total += len(data)
        if total > 64 * 1024 * 1024:
            raise InputError("LIMIT_EXCEEDED", "Current source closure exceeds 64 MiB")
        sources[name] = data
    if set(sources) != set(expected):
        raise InputError("PACKET_CLOSURE_MISSING", "Current source closure is incomplete")
    if b["expected_units"] is not None:
        im.units(b["expected_units"], "/expected_units", sources)
    identities = {}
    for ident in bounded_list(b["identities"], 32, "/identities"):
        ident = im.identity(ident)
        if ident["id"] in identities:
            raise InputError("DUPLICATE_ID", "Duplicate current analyzer")
        identities[ident["id"]] = ident
    if not identities:
        raise InputError("FIELD_TYPE", "Current analyzer identities are absent")
    from score_sw_fabric.assurance.models import digest

    snapshot: dict[str, Any] = current["snapshot"]
    root = im.native_root(snapshot["root"])
    baseline_path = label(request_path.parent, request["current_baseline"]["path"])
    if root != label(baseline_path.parent, b["root"]):
        raise InputError("BASELINE_DRIFT", "Current source root differs from original selection")
    source = {k: b[k] for k in ("component", "files", "expected_units")}
    rebuilt = {
        **b,
        "root": str(root),
        "source_digest": digest(source),
        "profile": request["profile"],
        "full_digest": digest(
            {**source, "profile": request["profile"], "identities": b["identities"]}
        ),
        "kind": "quality_import_baseline_snapshot",
        "input_digest": b["digest"],
    }
    rebuilt.pop("digest")
    if seal(rebuilt) != snapshot:
        raise InputError("BASELINE_DRIFT", "Current baseline snapshot does not reproduce")
    return snapshot


def _support(
    selected: list[dict[str, Any]], original: dict[str, Any], request: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    results = []
    gaps = []
    identities: dict[str, str] = {}
    sequences: dict[tuple[str, str, str], set[str]] = {}
    packet_sha = byte_digest(canonical(original))
    as_of = dm.timestamp(request["as_of"], "/as_of")
    for pair in selected:
        exact(
            pair,
            {"selection", "assessment", "trust_context", "assessment_bytes", "trust_context_bytes"},
            "/decision",
        )
        exact(pair["selection"], {"assessment", "trust_context"}, "/selection")
        for key in ("assessment", "trust_context"):
            _record_original(pair[key + "_bytes"], pair["selection"][key], pair[key])
        result = verify_005(pair["assessment"], pair["trust_context"])
        binding = "not_checked"
        current_gate = None
        reasons = []
        if not result["reproduced"]:
            reasons = ["DECISION_NOT_REPRODUCED", *result["reason_codes"]]
        else:
            a = pair["assessment"]
            candidates = [
                entry for entry in a["subject"]["source_files"] if entry["sha256"] == packet_sha
            ]
            closure = a["subject"]["manifest"]["file_closure"]
            exact_packet = [
                entry
                for entry in candidates
                if any(
                    row["path"] == entry["path"] and row["sha256"] == packet_sha for row in closure
                )
            ]
            binding = "exact_packet" if exact_packet else "other_subject"
            if not exact_packet:
                reasons.append("DECISION_SUBJECT_MISMATCH")
            historical_gate = a["gate_results"][0]
            historical = dm.timestamp(historical_gate["as_of"], "/historical_gate/as_of")
            if as_of < historical:
                reasons.append("DECISION_TIME_REVERSED")
            if historical_gate["assurance_domain"] != request["assurance_domain"]:
                reasons.append("DOMAIN_MISMATCH")
            policy = a["policy_refs"][0]["record"]
            if (as_of - historical).total_seconds() > policy["freshness_rules"]["max_age_seconds"]:
                reasons.append("DECISION_EXPIRED")
            for decision in a["decision_records"]:
                if (
                    as_of - dm.timestamp(decision["issued_at"], "/decision/issued_at")
                ).total_seconds() > policy["freshness_rules"]["max_age_seconds"]:
                    reasons.append("DECISION_EXPIRED")
                identity = decision["decision_id"]
                previous = identities.get(identity)
                if previous is not None and previous != decision["digest"]:
                    reasons.append("DECISION_CONFLICT")
                identities[identity] = decision["digest"]
            for receipt in a["receipts"]:
                if receipt["payload_kind"] == "assurance_decision":
                    sequence = (
                        receipt["issuer_id"],
                        receipt["key_id"],
                        receipt["nonce_or_sequence"],
                    )
                    sequences.setdefault(sequence, set()).add(receipt["payload_digest"])
            if not a["decision_records"]:
                reasons.append("HUMAN_DECISION_REQUIRED")
            current_gate = decisions._current_gate(a, pair["trust_context"], as_of)
            if current_gate["outcome"] != "pass":
                reasons.extend(["CURRENT_GATE_NOT_PASSED", *current_gate["reason_codes"]])
        results.append(
            {
                **pair,
                "replay": result,
                "binding": binding,
                "current_gate": current_gate,
                "reasons": sorted(set(reasons)),
            }
        )
        gaps.extend(reasons)
    if any(len(payloads) > 1 for payloads in sequences.values()):
        gaps.append("RECEIPT_REPLAY")
    return results, gaps


def _dispositions(
    original: dict[str, Any], request: dict[str, Any], current: dict[str, Any] | None
) -> tuple[list[dict[str, Any]], list[str]]:
    results = []
    gaps = []
    as_of = dm.timestamp(request["as_of"], "/as_of")
    for entry in original["dispositions"]:
        review = entry["review"]
        reasons = []
        if as_of < dm.timestamp(review["observed_at"], "/review/observed_at"):
            reasons.append("DISPOSITION_TIME_REVERSED")
        if review["state"] in {"stale", "blocked"}:
            reasons.extend(review["reasons"])
            reasons.append(
                "DISPOSITION_STALE" if review["state"] == "stale" else "DISPOSITION_BLOCKED"
            )
        if review["state"] == "corrected":
            fresh = review["fresh_run"]
            _, _, original_adapter = dm.origin(entry["origin"])
            if review["draft"]["requested_kind"] != "correction":
                reasons.append("DISPOSITION_KIND_INVALID")
            if fresh is None:
                reasons.append("FRESH_ANALYSIS_REQUIRED")
            elif original_adapter is None:
                reasons.append("IMPORTED_CORRECTION_SCOPE_UNVERIFIED")
            else:
                reasons.extend(
                    draft_reviews._scope_changes(
                        entry["origin"]["baseline"], review["current_baseline"], True
                    )
                )
                reasons.extend(
                    draft_reviews._fresh_reasons(
                        fresh,
                        review["current_baseline"],
                        review["subject"]["finding"]["native_id"],
                        entry["origin"],
                    )
                )
                construct = review["draft"]["construct"]
                if (
                    dm.files(review["current_baseline"]["files"]).get(construct["path"])
                    == construct["sha256"]
                ):
                    reasons.append("TRACKED_SOURCE_UNCHANGED")
        if review["draft"]["expires_at"] is not None and as_of >= dm.timestamp(
            review["draft"]["expires_at"], "/expires_at"
        ):
            reasons.append("DISPOSITION_EXPIRED")
        if current is None:
            reasons.append("BASELINE_FRESHNESS_UNKNOWN")
        else:
            b = review["current_baseline"]
            if any(b[k] != current[k] for k in ("component", "files", "expected_units")):
                reasons.append("DISPOSITION_STALE")
            if b["profile"]["sha256"] != current["profile"]["sha256"]:
                reasons.append("POLICY_CHANGED")
            local = review["fresh_run"] if review["fresh_run"] is not None else entry["origin"]
            _, _, adapter = dm.origin(local)
            if adapter is not None:
                identity = next((i for i in current["identities"] if i["id"] == adapter), None)
                if identity is None or (
                    identity["tool_sha256"] != local["toolchain"]["tool"]["sha256"]
                    or identity["version"] != local["toolchain"]["tool"]["version"]
                    or {i["sha256"] for i in identity["libraries"]}
                    != {i["sha256"] for i in local["toolchain"]["dependencies"]}
                ):
                    reasons.append("TOOL_CHANGED")
                if identity is None or identity["config_sha256"] != b["configuration"]["sha256"]:
                    reasons.append("CONFIGURATION_CHANGED")
        result = None
        decision = entry["decision"]
        if decision is not None:
            if current is not None:
                context = decision["result"]["binding"]["current_context"]
                identities = {i["id"]: i for i in current["identities"]}
                identity = identities.get(context["adapter"])
                if identity is None or (
                    identity["tool_sha256"] != context["toolchain"]["tool"]["sha256"]
                    or identity["version"] != context["toolchain"]["tool"]["version"]
                    or {i["sha256"] for i in identity["libraries"]}
                    != {i["sha256"] for i in context["toolchain"]["dependencies"]}
                ):
                    reasons.append("TOOL_CHANGED")
                if identity is None or identity["config_sha256"] != context["configuration_sha256"]:
                    reasons.append("CONFIGURATION_CHANGED")
            selected = [
                (
                    {"assessment": r["assessment_ref"], "trust_context": r["trust_context_ref"]},
                    r["assessment"],
                    r["trust_context"],
                )
                for r in decision["result"]["decisions"]
            ]
            refreshed_request = {
                **decision["request"],
                "as_of": request["as_of"],
                "assurance_domain": request["assurance_domain"],
            }
            result = decisions.evaluate(refreshed_request, decision["result"]["binding"], selected)
            reasons.extend(result["reasons"])
        if reasons:
            observation = (
                "stale"
                if any(
                    r in reasons
                    for r in (
                        "DISPOSITION_STALE",
                        "DISPOSITION_EXPIRED",
                        "DECISION_EXPIRED",
                        "TOOL_CHANGED",
                        "CONFIGURATION_CHANGED",
                        "POLICY_CHANGED",
                        "DISPOSITION_TIME_REVERSED",
                    )
                )
                else "blocked"
            )
        elif result is not None and result["state"] == "accepted_fixture":
            observation = "accepted_fixture"
        elif review["state"] == "corrected":
            observation = "retained_local_correction"
            reasons.append("CORRECTION_EXECUTION_UNPROTECTED")
        else:
            observation = "pending_review"
            reasons.append("HUMAN_REVIEW_PENDING")
        results.append(
            {
                "id": review["draft"]["id"],
                "review_digest": review["digest"],
                "historical_state": review["state"],
                "observation": observation,
                "current_decision": result,
                "reasons": sorted(set(reasons)),
            }
        )
        gaps.extend(reasons)
    return results, gaps


def evaluate(
    request: dict[str, Any],
    profile_bytes: dict[str, Any],
    original: dict[str, Any],
    current: dict[str, Any] | None,
    selected: list[dict[str, Any]],
    *,
    request_path: Path,
    packet_bytes: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate retained originals; fixture 005 replay uses fresh temporary directories."""
    version(request, "quality_assessment_request", REQUEST_FIELDS, "/request")
    domain = im.choice(request["assurance_domain"], {"fixture_contract", "production"}, "/domain")
    dm.timestamp(request["as_of"], "/as_of")
    dm._raw(profile_bytes)
    if (
        profile_bytes["truncated"]
        or profile_bytes["format"] != "bytes"
        or profile_bytes["sha256"] != request["profile"]["sha256"]
    ):
        raise InputError("PROFILE_DRIFT", "Selected profile original differs")
    profile = load_profile(raw_bytes(profile_bytes))
    _record_original(packet_bytes, request["packet"], original)
    replay = packet.verify_packet(original)
    if not replay["reproduced"]:
        raise InputError("PACKET_NOT_REPRODUCED", "Selected packet does not replay")
    frozen = _current(current, request, request_path)
    pairs = bounded_list(request["decisions"], 20, "/decisions")
    if [entry["selection"] for entry in selected] != pairs:
        raise InputError("DECISION_NOT_REPRODUCED", "Selected supporting pairs differ from request")
    count = total = 0
    seen_pairs = set()
    for entry in selected:
        pair_id = canonical(entry["selection"])
        if pair_id in seen_pairs:
            raise InputError("DUPLICATE_ID", "Duplicate supporting decision selection")
        seen_pairs.add(pair_id)
        count += decisions._decision_count(entry["assessment"])
        total += len(canonical(entry["assessment"])) + len(canonical(entry["trust_context"]))
    for entry in original["dispositions"]:
        if entry["decision"] is not None:
            for row in entry["decision"]["result"]["decisions"]:
                count += decisions._decision_count(row["assessment"])
                total += len(canonical(row["assessment"])) + len(canonical(row["trust_context"]))
    if count > 20 or total > dm.MAX_RECORD:
        raise InputError("LIMIT_EXCEEDED", "Supporting/disposition decision closure exceeds bounds")
    gaps = (
        set(original["gaps"])
        | set(profile["required_obligations"])
        | {
            "RULE_MAPPING_UNKNOWN",
            "MANUAL_REVIEW_PENDING",
            "GUIDELINE_REVIEW_PENDING",
            "PRIMARY_EXECUTION_UNAVAILABLE",
            "CODEQL_ELIGIBILITY_UNKNOWN",
            "PRODUCTION_AUTHORITY_UNAVAILABLE",
            "TOOL_CONFIDENCE_UNKNOWN",
            "CURRENT_TOOL_STATE_UNVERIFIED",
        }
    )
    if request["profile"]["sha256"] != original["request"]["profile"]["sha256"]:
        gaps.add("PROFILE_CHANGED")
    matrix = original["coverage"]["report"] if original["coverage"] is not None else None
    expected = matrix["baseline"] if matrix else original["analyses"][0]["report"]["baseline"]
    if frozen is None:
        gaps.add("BASELINE_FRESHNESS_UNKNOWN")
    else:
        for key in ("component", "files", "expected_units", "identities", "profile"):
            if frozen[key] != expected[key]:
                gaps.add("BASELINE_DRIFT:" + key)
    supporting, support_gaps = _support(selected, original, request)
    dispositions, disposition_gaps = _dispositions(original, request, frozen)
    gaps.update(support_gaps)
    gaps.update(disposition_gaps)
    obligations = [
        {
            "kind": "prerequisite",
            "id": "primary-misra",
            "outcome": "blocked",
            "reasons": ["PRIMARY_EXECUTION_UNAVAILABLE", "CODEQL_ELIGIBILITY_UNKNOWN"],
        },
        {
            "kind": "prerequisite",
            "id": "production-authority",
            "outcome": "blocked",
            "reasons": ["PRODUCTION_AUTHORITY_UNAVAILABLE"],
        },
        {
            "kind": "prerequisite",
            "id": "manual-review",
            "outcome": "blocked",
            "reasons": ["MANUAL_REVIEW_PENDING"],
        },
    ]
    denominator = matrix["denominator"] if matrix else None
    if denominator is None:
        gaps.add("GUIDELINE_DENOMINATOR_UNKNOWN")
    for row in matrix["rows"] if matrix else []:
        reasons = sorted(set([*row["reasons"], "GUIDELINE_REVIEW_PENDING"]))
        obligations.append(
            {
                "kind": "guideline",
                "id": row["guideline_id"],
                "outcome": "fail" if row["findings"] else "blocked",
                "reasons": reasons,
                "observation": row["state"],
            }
        )
    for entry in original["analyses"]:
        report = entry["report"]
        reasons = list(report["extraction"]["gaps"])
        adequacy = report["extraction"]["adequacy"]
        compared = frozen if frozen is not None else expected
        drift = [
            "ANALYSIS_HISTORICAL:" + key
            for key in ("component", "files", "expected_units", "identities", "profile")
            if report["baseline"][key] != compared[key]
        ]
        reasons.extend(drift)
        if frozen is None:
            reasons.append("BASELINE_FRESHNESS_UNKNOWN")
        if report["findings"]:
            reasons.append("NATIVE_FINDING_OPEN")
        obligations.append(
            {
                "kind": "analysis",
                "id": report["digest"],
                "outcome": "blocked"
                if adequacy != "adequate" or drift or frozen is None
                else "fail"
                if report["findings"]
                else "pass",
                "reasons": sorted(set(reasons)),
                "observation": report["outcome"],
            }
        )
    record = seal(
        {
            "schema_version": 1,
            "kind": "quality_compliance_assessment",
            "request_path": str(request_path),
            "request": request,
            "profile": profile,
            "profile_bytes": profile_bytes,
            "packet": original,
            "packet_bytes": packet_bytes,
            "packet_replay": replay,
            "current_baseline": current,
            "decisions": supporting,
            "dispositions": dispositions,
            "obligations": obligations,
            "denominator": denominator,
            "gaps": sorted(gaps),
            "outcome": "blocked",
            "accepted_claims": 0,
            "assurance_domain": domain,
            "as_of": request["as_of"],
            "time_basis": "untrusted_request",
            "origin": "fixture_contract_evaluation"
            if domain == "fixture_contract"
            else "local_unprotected_evaluation",
            "assurance_eligibility": "not_eligible",
            "engineering_readiness": "not_evaluated",
            "limitations": LIMITATIONS,
        }
    )
    bounded_record(record)
    return record


def assess(
    request_path: Path, out: Path | None = None
) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    path = request_path.absolute()
    request = version(
        im.control(path, yaml=True), "quality_assessment_request", REQUEST_FIELDS, "/request"
    )
    # Validate time/domain before expensive replay.
    dm.timestamp(request["as_of"], "/as_of")
    im.choice(request["assurance_domain"], {"fixture_contract", "production"}, "/domain")
    pp, _ = im.selected_control(path.parent, request["profile"], yaml=True)
    _, pb = _selected_bytes(path.parent, request["profile"], 1024 * 1024)
    packet_path, original = im.selected_control(
        path.parent, request["packet"], max_bytes=dm.MAX_RECORD
    )
    _, packet_data = _selected_bytes(path.parent, request["packet"])
    if not packet.verify_packet(original)["reproduced"]:
        raise InputError("PACKET_NOT_REPRODUCED", "Selected packet does not replay")
    inputs = [path, pp, packet_path, *(Path(f["path"]) for f in original["files"])]
    protected = protected_roots(path.parent, request["protected_roots"], "/protected_roots")
    protected.extend(label(Path("/"), s["root"]) for s in original["sources"])
    current = None
    frozen = None
    if request["current_baseline"] is not None:
        frozen, files, _, paths, root = im.freeze_baseline(
            path.parent, request["current_baseline"], request["profile"]
        )
        bp, raw = _selected_bytes(path.parent, request["current_baseline"], 1024 * 1024)
        _, b = im.selected_control(path.parent, request["current_baseline"])
        current = {
            "record": b,
            "record_bytes": Budget(1024 * 1024).capture(raw, "bytes"),
            "snapshot": frozen,
            "sources": [
                {"path": name, "raw": Budget(16 * 1024 * 1024).capture(data, "bytes")}
                for name, data in files.items()
            ],
        }
        inputs.extend([bp, *paths])
        protected.append(root)
    selected = []
    total = count = 0
    seen = set()
    for entry in bounded_list(request["decisions"], 20, "/decisions"):
        pair = exact(entry, {"assessment", "trust_context"}, "/decision")
        ap, a = im.selected_control(path.parent, pair["assessment"], max_bytes=dm.MAX_RECORD)
        tp, t = im.selected_control(path.parent, pair["trust_context"], max_bytes=dm.MAX_RECORD)
        identity = (ap, tp)
        if identity in seen:
            raise InputError("DUPLICATE_ID", "Duplicate supporting decision pair")
        seen.add(identity)
        total += len(canonical(a)) + len(canonical(t))
        count += decisions._decision_count(a)
        if total > dm.MAX_RECORD or count > 20:
            raise InputError("LIMIT_EXCEEDED", "Supporting decision closure exceeds bounds")
        _, assessment_bytes = _selected_bytes(path.parent, pair["assessment"])
        _, context_bytes = _selected_bytes(path.parent, pair["trust_context"])
        selected.append(
            {
                "selection": pair,
                "assessment": a,
                "trust_context": t,
                "assessment_bytes": Budget(dm.MAX_RECORD, dm.MAX_RECORD).capture(
                    assessment_bytes, "bytes"
                ),
                "trust_context_bytes": Budget(dm.MAX_RECORD, dm.MAX_RECORD).capture(
                    context_bytes, "bytes"
                ),
            }
        )
        inputs.extend([ap, tp])
    for entry in original["dispositions"]:
        if entry["decision"] is not None:
            for record in entry["decision"]["result"]["decisions"]:
                count += decisions._decision_count(record["assessment"])
    if count > 20:
        raise InputError(
            "LIMIT_EXCEEDED", "Selected supporting and disposition decisions exceed 20"
        )
    if out is not None:
        output_path(out, inputs, protected)
    record = evaluate(
        request,
        Budget(1024 * 1024).capture(pb, "bytes"),
        original,
        current,
        selected,
        request_path=path,
        packet_bytes=Budget(dm.MAX_RECORD, dm.MAX_RECORD).capture(packet_data, "bytes"),
    )
    if im.control(path, yaml=True) != request:
        raise InputError("INPUT_DRIFT", "Assessment request changed during replay")
    im.selected_control(path.parent, request["profile"], yaml=True)
    im.selected_control(path.parent, request["packet"], max_bytes=dm.MAX_RECORD)
    if (
        frozen is not None
        and im.freeze_baseline(path.parent, request["current_baseline"], request["profile"])[0]
        != frozen
    ):
        raise InputError("INPUT_DRIFT", "Current baseline changed during replay")
    for entry in selected:
        for key in ("assessment", "trust_context"):
            im.selected_control(path.parent, entry["selection"][key], max_bytes=dm.MAX_RECORD)
    if out is not None:
        output_path(out, inputs, protected)
    return 1, record, inputs, protected


def verify_assessment(value: Any) -> dict[str, Any]:
    """Reevaluate all retained packet/source/005 originals, without original host paths."""
    try:
        record = version(value, "quality_compliance_assessment", ASSESSMENT_FIELDS, "/assessment")
        bounded_record(record)
        verify_digest(record, "/assessment")
        selected = [
            {
                k: r[k]
                for k in (
                    "selection",
                    "assessment",
                    "trust_context",
                    "assessment_bytes",
                    "trust_context_bytes",
                )
            }
            for r in record["decisions"]
        ]
        rebuilt = evaluate(
            record["request"],
            record["profile_bytes"],
            record["packet"],
            record["current_baseline"],
            selected,
            request_path=label(Path("/"), record["request_path"]),
            packet_bytes=record["packet_bytes"],
        )
        if rebuilt != record:
            raise InputError("ASSESSMENT_NOT_REPRODUCED", "Quality evaluation does not replay")
        return {"reproduced": True, "reason_codes": [], "outcome": record["outcome"]}
    except (InputError, KeyError, TypeError, ValueError, RecursionError) as exc:
        code = exc.code if isinstance(exc, InputError) else "ASSESSMENT_NOT_REPRODUCED"
        return {"reproduced": False, "reason_codes": [code], "outcome": "blocked"}
