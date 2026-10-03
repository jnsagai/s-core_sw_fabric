"""Guarded assurance operation routing and same-directory atomic publication."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from score_sw_fabric.assurance.models import MAX_CONTROL_BYTES
from score_sw_fabric.assurance.reader import load_inputs, output_path, read_request
from score_sw_fabric.assurance.subjects import SUBJECT_INPUTS, build_subject
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import InputError


def _selected_gate(
    subject: dict[str, Any],
    policy: Any,
    request: dict[str, Any],
    profile: dict[str, Any] | None = None,
) -> str:
    from score_sw_fabric.assurance.predicates import expected_predicates

    if not isinstance(policy, dict) or not isinstance(policy.get("predicates"), list):
        raise InputError("FIELD_TYPE", "Selected gate policy predicates must be an array")
    selected_gates = {
        item.get("gate_id") for item in policy["predicates"] if isinstance(item, dict)
    }
    if len(selected_gates) != 1:
        raise InputError("SCOPE_MISMATCH", "Policy must select exactly one gate")
    selected = next(iter(selected_gates))
    if not isinstance(selected, str):
        raise InputError("SCOPE_MISMATCH", "Policy gate ID must be a string")
    predicates = expected_predicates(
        subject,
        policy,
        gate_id=selected,
        requested_domain=request["assurance_domain"],
        requested_scope=request["scope"],
    )
    if profile is not None and len(predicates) > profile["limits"]["predicates"]:
        raise InputError("LIMIT_EXCEEDED", "Selected gate predicate count exceeds trust bound")
    return selected


def _native_impact(prior: dict[str, Any] | None, records: dict[str, Any]) -> dict[str, Any] | None:
    """Rederive 004 dependency paths from the sealed old/new native indexes."""
    if prior is None:
        return None
    from score_sw_fabric.artifacts.impact import analyze_impact

    before = prior["subject"]["closure"]["candidate"]["record"]["index"]
    after = records["candidate"]["index"]
    return analyze_impact(before, after, records.get("trace_profile") or {})


def _readable_report(result: dict[str, Any]) -> dict[str, Any]:
    """Build the exact public summary from the replayed gate result."""
    return {
        "assurance_domain": result["assurance_domain"],
        "scope": result["scope"],
        "outcome": result["outcome"],
        "reason_codes": result["reason_codes"],
        "unmet_predicate_ids": result["unmet_predicate_ids"],
        "next_route": result["next_route"],
        "engineering_readiness": "not_evaluated",
        "release": "not_evaluated",
    }


def publish(out: Path, record: dict[str, Any]) -> None:
    payload = canonical(record)
    if len(payload) > MAX_CONTROL_BYTES:
        raise InputError("LIMIT_EXCEEDED", "Assurance output exceeds 64 MiB")
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".assurance-", dir=out.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, out)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    except OSError as exc:
        raise InputError("OUTPUT_IO", str(exc)) from exc


def subject_request(path: Path, out: Path) -> dict[str, Any]:
    request = read_request(path, "subject")
    inputs, paths = load_inputs(path, request, SUBJECT_INPUTS)
    destination = output_path(path, request, out, paths)
    subject = build_subject(request, inputs)
    publish(destination, subject)
    return subject


def evidence_request(path: Path, out: Path) -> dict[str, Any]:
    from score_sw_fabric.assurance.evidence import classify_evidence
    from score_sw_fabric.assurance.models import (
        MAX_EVIDENCE,
        MAX_REFERENCES,
        digest,
        instant,
        seal,
        sha,
    )
    from score_sw_fabric.assurance.origins import replayed_payloads, validate_profile
    from score_sw_fabric.assurance.reader import resolve_directory

    request = read_request(path, "evidence")
    names = {"subject", "policy", "trust_profile", "evidence", "receipts"}
    inputs, paths = load_inputs(path, request, names)
    destination = output_path(path, request, out, paths)
    subject = inputs["subject"]
    policy = inputs["policy"]
    profile = validate_profile(inputs["trust_profile"])
    _selected_gate(subject, policy, request, profile)
    raw_root = resolve_directory(
        path.parent, request["local_paths"].get("raw_root"), "/local_paths/raw_root"
    )
    evidence = [value for name, value in sorted(inputs.items()) if name.startswith("evidence/")]
    receipts = [value for name, value in sorted(inputs.items()) if name.startswith("receipts/")]
    if not evidence or len(evidence) > min(
        MAX_EVIDENCE, profile["limits"]["evidence"], policy["limits"]["evidence"]
    ):
        raise InputError("LIMIT_EXCEEDED", "Evidence set must be non-empty and bounded")
    if len(receipts) > min(MAX_REFERENCES, profile["limits"]["references"]):
        raise InputError("LIMIT_EXCEEDED", "Evidence receipt set exceeds trust bound")
    by_payload: dict[str, dict[str, Any]] = {}
    for receipt in receipts:
        payload_digest = sha(receipt.get("payload_digest"), "/receipt/payload_digest")
        if payload_digest in by_payload:
            raise InputError("DUPLICATE_ID", "Duplicate evidence receipt payload")
        by_payload[payload_digest] = receipt
    seen_sequences: set[tuple[str, str, str]] = set()
    classifications = [
        classify_evidence(
            record,
            by_payload.get(digest(record, exclude="__none__")),
            subject,
            policy,
            profile,
            requested_domain=request["assurance_domain"],
            requested_scope=request["scope"],
            as_of=instant(request["as_of"], "/as_of"),
            raw_root=raw_root,
            seen_sequences=seen_sequences,
        )
        for record in evidence
    ]
    replayed = replayed_payloads(receipts)
    for record, classification in zip(evidence, classifications, strict=True):
        if digest(record, exclude="__none__") in replayed:
            classification["eligible"] = False
            classification["reason_codes"] = sorted(
                set(classification["reason_codes"] + ["RECEIPT_REPLAY"])
            )
    if len({item["evidence_id"] for item in classifications}) != len(classifications):
        raise InputError("DUPLICATE_ID", "Duplicate evidence ID")
    classifications.sort(key=lambda item: item["evidence_id"])
    result = seal(
        {
            "schema_version": 1,
            "kind": "assurance_evidence_result",
            "assurance_domain": request["assurance_domain"],
            "scope": request["scope"],
            "subject_digest": subject["digest"],
            "policy_digest": policy["digest"],
            "trust_profile_digest": profile["digest"],
            "eligibility": classifications,
            "outcome": "eligible"
            if all(item["eligible"] for item in classifications)
            else "ineligible",
            "limitations": [
                "Fixture-domain verification only; no production collector is established."
            ]
            if request["assurance_domain"] == "fixture_contract"
            else ["Protected production collector and trust context unavailable."],
        }
    )
    publish(destination, result)
    return result


def decision_request(path: Path, out: Path) -> dict[str, Any]:
    from score_sw_fabric.assurance.decisions import classify_decision, reconcile_decisions
    from score_sw_fabric.assurance.models import (
        MAX_DECISIONS,
        MAX_REFERENCES,
        digest,
        instant,
        seal,
        sha,
    )
    from score_sw_fabric.assurance.origins import replayed_payloads, validate_profile

    request = read_request(path, "decision")
    names = {"subject", "policy", "trust_profile", "decisions", "receipts"}
    inputs, paths = load_inputs(path, request, names)
    destination = output_path(path, request, out, paths)
    subject = inputs["subject"]
    policy = inputs["policy"]
    profile = validate_profile(inputs["trust_profile"])
    _selected_gate(subject, policy, request, profile)
    decisions = [value for name, value in sorted(inputs.items()) if name.startswith("decisions/")]
    receipts = [value for name, value in sorted(inputs.items()) if name.startswith("receipts/")]
    if not decisions or len(decisions) > min(
        MAX_DECISIONS, profile["limits"]["decisions"], policy["limits"]["decisions"]
    ):
        raise InputError("LIMIT_EXCEEDED", "Decision set must be non-empty and bounded")
    if len(receipts) > min(MAX_REFERENCES, profile["limits"]["references"]):
        raise InputError("LIMIT_EXCEEDED", "Decision receipt set exceeds trust bound")
    by_payload: dict[str, dict[str, Any]] = {}
    for receipt in receipts:
        payload_digest = sha(receipt.get("payload_digest"), "/receipt/payload_digest")
        if payload_digest in by_payload:
            raise InputError("DUPLICATE_ID", "Duplicate decision receipt payload")
        by_payload[payload_digest] = receipt
    gates = {gate for decision in decisions for gate in decision.get("gate_ids", [])}
    if len(gates) != 1:
        raise InputError("SCOPE_MISMATCH", "Decision request must select exactly one gate")
    gate_id = next(iter(gates))
    seen_sequences: set[tuple[str, str, str]] = set()
    classified = [
        classify_decision(
            record,
            by_payload.get(digest(record, exclude="__none__")),
            subject,
            policy,
            profile,
            requested_domain=request["assurance_domain"],
            requested_scope=request["scope"],
            gate_id=gate_id,
            as_of=instant(request["as_of"], "/as_of"),
            seen_sequences=seen_sequences,
        )
        for record in decisions
    ]
    replayed = replayed_payloads(receipts)
    for record, classification in zip(decisions, classified, strict=True):
        if digest(record, exclude="__none__") in replayed:
            classification["eligible"] = False
            classification["approves"] = False
            classification["reason_codes"] = sorted(
                set(classification["reason_codes"] + ["RECEIPT_REPLAY"])
            )
    classifications = sorted(reconcile_decisions(classified), key=lambda item: item["decision_id"])
    result = seal(
        {
            "schema_version": 1,
            "kind": "assurance_decision_result",
            "assurance_domain": request["assurance_domain"],
            "scope": request["scope"],
            "gate_id": gate_id,
            "subject_digest": subject["digest"],
            "policy_digest": policy["digest"],
            "trust_profile_digest": profile["digest"],
            "eligibility": classifications,
            "outcome": "eligible"
            if all(item["eligible"] for item in classifications)
            else "ineligible",
            "limitations": [
                "Fixture-domain identity simulation only; no production person authenticated."
            ]
            if request["assurance_domain"] == "fixture_contract"
            else ["Protected production identity and role context unavailable."],
        }
    )
    publish(destination, result)
    return result


def gate_request(path: Path, out: Path) -> dict[str, Any]:
    import base64
    import hashlib

    from score_sw_fabric.assurance.gates import evaluate_gate
    from score_sw_fabric.assurance.models import MAX_CONTROL_BYTES, digest, instant, seal
    from score_sw_fabric.assurance.origins import validate_profile
    from score_sw_fabric.assurance.reader import resolve_directory, resolve_file

    request = read_request(path, "gate")
    names = {
        "subject",
        "policy",
        "trust_profile",
        "evidence",
        "evidence_receipts",
        "decisions",
        "decision_receipts",
        "prior_assessment",
        *SUBJECT_INPUTS,
    }
    inputs, paths = load_inputs(path, request, names)
    destination = output_path(path, request, out, paths)
    subject = inputs["subject"]
    policy = inputs["policy"]
    profile = validate_profile(inputs["trust_profile"])
    closure_records = {key: inputs[key] for key in SUBJECT_INPUTS if key in inputs}
    rederived = build_subject(
        {"assurance_domain": subject["assurance_domain"], "scope": subject["scope"]},
        closure_records,
    )
    if rederived != subject:
        raise InputError(
            "SUBJECT_MISMATCH", "Selected subject differs from its sealed 002/004 closure"
        )
    closure_refs: dict[str, Any] = {}
    for key in SUBJECT_INPUTS:
        ref = request["inputs"][key]
        if ref is None:
            continue
        source = resolve_file(path.parent, ref["path"], f"/inputs/{key}/path")
        raw = source.read_bytes()
        if len(raw) > MAX_CONTROL_BYTES:
            raise InputError("LIMIT_EXCEEDED", "Subject closure input exceeds 64 MiB")
        if hashlib.sha256(raw).hexdigest() != ref["sha256"]:
            raise InputError("HASH_MISMATCH", f"Subject closure input changed: {key}")
        closure_refs[key] = {
            "record": closure_records[key],
            "sha256": ref["sha256"],
            "semantic_digest": ref["semantic_digest"],
            "suffix": source.suffix,
            "content_base64": base64.b64encode(raw).decode("ascii"),
        }
    source_root = Path.cwd() / closure_records["artifact_request"]["local_paths"]["snapshot_root"]
    source_files = []
    for item in closure_records["snapshot"]["files"]:
        selected = resolve_file(source_root, item["path"], "/snapshot/files")
        raw = selected.read_bytes()
        if len(raw) > MAX_CONTROL_BYTES:
            raise InputError("LIMIT_EXCEEDED", "Source file exceeds 64 MiB")
        if len(raw) != item["bytes"] or hashlib.sha256(raw).hexdigest() != item["sha256"]:
            raise InputError("HASH_MISMATCH", "Selected source changed before publication")
        source_files.append(
            {
                "path": item["path"],
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
                "content_base64": base64.b64encode(raw).decode("ascii"),
            }
        )
    for item in closure_records["artifact_profile"].get("templates", []):
        selected = resolve_file(Path.cwd(), item["path"], "/profile/templates")
        raw = selected.read_bytes()
        if len(raw) > MAX_CONTROL_BYTES:
            raise InputError("LIMIT_EXCEEDED", "Template file exceeds 64 MiB")
        if hashlib.sha256(raw).hexdigest() != item["sha256"]:
            raise InputError("HASH_MISMATCH", "Selected template changed before publication")
        source_files.append(
            {
                "path": item["path"],
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
                "content_base64": base64.b64encode(raw).decode("ascii"),
            }
        )
    evidence = [v for k, v in sorted(inputs.items()) if k.startswith("evidence/")]
    evidence_receipts = [v for k, v in sorted(inputs.items()) if k.startswith("evidence_receipts/")]
    decisions = [v for k, v in sorted(inputs.items()) if k.startswith("decisions/")]
    decision_receipts = [v for k, v in sorted(inputs.items()) if k.startswith("decision_receipts/")]
    evidence.sort(key=lambda item: str(item.get("evidence_id", "")))
    decisions.sort(key=lambda item: str(item.get("decision_id", "")))
    evidence_receipts.sort(key=lambda item: str(item.get("payload_digest", "")))
    decision_receipts.sort(key=lambda item: str(item.get("payload_digest", "")))
    payloads = {
        (kind, digest(record, exclude="__none__"))
        for kind, records in (
            ("assurance_evidence", evidence),
            ("assurance_decision", decisions),
        )
        for record in records
    }
    if any(
        (receipt.get("payload_kind"), receipt.get("payload_digest")) not in payloads
        for receipt in evidence_receipts + decision_receipts
    ):
        raise InputError("CLOSURE_MISSING", "Gate receipt has no selected payload")
    gate_id = _selected_gate(subject, policy, request, profile)
    raw_root = resolve_directory(
        path.parent, request["local_paths"].get("raw_root"), "/local_paths/raw_root"
    )
    if request["gate_mode"] == "reuse_prior" and "prior_assessment" in inputs:
        historical = verify_assessment(
            inputs["prior_assessment"],
            {
                "schema_version": 1,
                "kind": "assurance_trust_context",
                "assurance_domain": "fixture_contract",
                "root_origin": "fixture_test_only",
                "profile": profile,
                "profile_digest": profile["digest"],
            },
        )
        if historical["reproduced"] is not True:
            raise InputError(
                "HISTORY_MISMATCH", "Prior assessment cannot be independently replayed"
            )
    result = evaluate_gate(
        subject,
        policy,
        profile,
        evidence,
        evidence_receipts,
        decisions,
        decision_receipts,
        requested_domain=request["assurance_domain"],
        requested_scope=request["scope"],
        gate_id=gate_id,
        as_of=instant(request["as_of"], "/as_of"),
        raw_root=raw_root,
        mode=request["gate_mode"],
        prior_assessment=inputs.get("prior_assessment"),
        artifact_impact=_native_impact(inputs.get("prior_assessment"), closure_records)
        if request["gate_mode"] == "reuse_prior"
        else None,
    )
    raw_output_refs = []
    for record in evidence:
        for item in record["raw_outputs"]:
            source = resolve_file(raw_root, item["path"], "/evidence/raw_outputs")
            raw = source.read_bytes()
            if len(raw) > MAX_CONTROL_BYTES:
                raise InputError("LIMIT_EXCEEDED", "Raw output exceeds 64 MiB")
            if len(raw) != item["bytes"] or hashlib.sha256(raw).hexdigest() != item["sha256"]:
                raise InputError("RAW_OUTPUT_MISMATCH", "Raw output changed before publication")
            raw_output_refs.append(
                {
                    **item,
                    "content_base64": base64.b64encode(raw).decode("ascii"),
                }
            )
    raw_output_refs.sort(key=lambda item: (item["path"], item["sha256"]))
    assessment = seal(
        {
            "schema_version": 1,
            "kind": "assurance_assessment",
            "subject": {
                "manifest": subject,
                "closure": closure_refs,
                "source_files": source_files,
            },
            "policy_refs": [{"record": policy, "selected_digest": policy["digest"]}],
            "trust_context_refs": [{"record": profile, "selected_digest": profile["digest"]}],
            "evidence_records": evidence,
            "decision_records": decisions,
            "receipts": evidence_receipts + decision_receipts,
            "gate_results": [result],
            "raw_output_refs": raw_output_refs,
            "history_refs": [inputs["prior_assessment"]] if "prior_assessment" in inputs else [],
            "readable_report": _readable_report(result),
            "limitations": result["limitations"],
        }
    )
    if request["assurance_domain"] == "fixture_contract":
        replay = verify_assessment(
            assessment,
            {
                "schema_version": 1,
                "kind": "assurance_trust_context",
                "assurance_domain": "fixture_contract",
                "root_origin": "fixture_test_only",
                "profile": profile,
                "profile_digest": profile["digest"],
            },
        )
        if replay["reproduced"] is not True:
            raise InputError("ASSESSMENT_MISMATCH", "New fixture assessment cannot be replayed")
    publish(destination, assessment)
    return assessment


def verify_assessment(value: Any, trust_context: Any, *, _history_depth: int = 0) -> dict[str, Any]:
    """Recompute a historical gate solely from its closure and an independent root selection."""
    import base64
    import binascii
    import hashlib

    from score_sw_fabric.assurance.gates import evaluate_gate
    from score_sw_fabric.assurance.models import (
        MAX_CONTROL_BYTES,
        MAX_DECISIONS,
        MAX_DEPTH,
        MAX_EVIDENCE,
        MAX_REFERENCES,
        bounded_list,
        digest,
        exact,
        instant,
        sha,
        verify_digest,
        version,
    )
    from score_sw_fabric.assurance.origins import validate_profile, verify_receipt
    from score_sw_fabric.assurance.reader import safe_path
    from score_sw_fabric.compiler.reader import semantic_digest, verify_self_digest
    from score_sw_fabric.process_source.reader import read_json, read_yaml
    from score_sw_fabric.storage import temporary_directory

    if _history_depth > MAX_DEPTH:
        raise InputError("LIMIT_EXCEEDED", "Assessment history exceeds nesting limit")
    fields = {
        "subject",
        "policy_refs",
        "trust_context_refs",
        "evidence_records",
        "decision_records",
        "receipts",
        "gate_results",
        "raw_output_refs",
        "history_refs",
        "readable_report",
        "limitations",
        "digest",
    }
    assessment = version(value, "assurance_assessment", fields, "/assessment")
    verify_digest(assessment, "/assessment")
    for name, limit in (
        ("policy_refs", 1),
        ("trust_context_refs", 1),
        ("evidence_records", MAX_EVIDENCE),
        ("decision_records", MAX_DECISIONS),
        ("receipts", MAX_EVIDENCE + MAX_DECISIONS),
        ("gate_results", 1),
        ("raw_output_refs", MAX_EVIDENCE),
        ("history_refs", 1),
        ("limitations", MAX_REFERENCES),
    ):
        bounded_list(assessment[name], limit, f"/assessment/{name}")
    if len(assessment["gate_results"]) != 1:
        raise InputError("FIELD_TYPE", "Expected one gate result")
    recorded = assessment["gate_results"][0]
    if not isinstance(recorded, dict):
        raise InputError("FIELD_TYPE", "Gate result must be an object")
    if type(recorded.get("schema_version")) is not int or recorded["schema_version"] != 1:
        raise InputError("VERSION_UNSUPPORTED", "Unsupported gate result version")
    if recorded.get("kind") != "assurance_gate_result":
        raise InputError("KIND_MISMATCH", "Expected assurance gate result")
    verify_digest(recorded, "/gate_result")

    def failure(code: str) -> dict[str, Any]:
        return {
            "reproduced": False,
            "outcome": recorded.get("outcome"),
            "reason_codes": [code],
        }

    if (
        not isinstance(trust_context, dict)
        or trust_context.get("kind") != "assurance_trust_context"
    ):
        return failure("TRUST_CONTEXT_MISSING")
    if trust_context.get("schema_version") != 1:
        return failure("VERSION_UNSUPPORTED")
    if (
        trust_context.get("assurance_domain") != "fixture_contract"
        or trust_context.get("root_origin") != "fixture_test_only"
    ):
        return failure("PRODUCTION_ORIGIN_UNAVAILABLE")
    profile = validate_profile(trust_context.get("profile"))
    if trust_context.get("profile_digest") != profile["digest"]:
        return failure("TRUST_CONTEXT_MISMATCH")
    if (
        len(assessment["trust_context_refs"]) != 1
        or assessment["trust_context_refs"][0].get("selected_digest") != profile["digest"]
    ):
        return failure("TRUST_CONTEXT_MISMATCH")
    if assessment["trust_context_refs"][0].get("record") != profile:
        return failure("TRUST_CONTEXT_MISMATCH")
    if len(assessment["policy_refs"]) != 1:
        return failure("POLICY_MISMATCH")
    policy = assessment["policy_refs"][0]["record"]
    verify_digest(policy, "/policy")
    if policy["digest"] != assessment["policy_refs"][0]["selected_digest"]:
        return failure("POLICY_MISMATCH")
    for index, record in enumerate(assessment["evidence_records"]):
        verify_digest(record, f"/evidence_records/{index}")
    for index, record in enumerate(assessment["decision_records"]):
        verify_digest(record, f"/decision_records/{index}")
    for index, receipt in enumerate(assessment["receipts"]):
        verify_digest(receipt, f"/receipts/{index}", field="receipt_digest")
    subject_bundle = exact(
        assessment["subject"], {"manifest", "closure", "source_files"}, "/subject"
    )
    subject = verify_digest(subject_bundle["manifest"], "/subject/manifest")
    closure = subject_bundle["closure"]
    if not isinstance(closure, dict) or set(closure) not in (
        SUBJECT_INPUTS - {"report", "trace_profile"},
        SUBJECT_INPUTS - {"report"},
        SUBJECT_INPUTS,
    ):
        return failure("CLOSURE_MISSING")
    records: dict[str, Any] = {}
    source_overrides: dict[str, bytes] = {}
    with temporary_directory(prefix="assurance-verify-") as temporary:
        root = Path(temporary)
        for name, wrapper in closure.items():
            entry = exact(
                wrapper,
                {"record", "sha256", "semantic_digest", "suffix", "content_base64"},
                f"/subject/closure/{name}",
            )
            suffix = entry["suffix"]
            if suffix not in {".json", ".yaml", ".yml"}:
                return failure("CLOSURE_MISSING")
            if not isinstance(entry["content_base64"], str):
                return failure("CLOSURE_MISSING")
            try:
                raw = base64.b64decode(entry["content_base64"], validate=True)
            except (ValueError, binascii.Error):
                return failure("CLOSURE_MISSING")
            if len(raw) > MAX_CONTROL_BYTES or hashlib.sha256(raw).hexdigest() != sha(
                entry["sha256"], "/sha256"
            ):
                return failure("CLOSURE_MISSING")
            selected_path = root / (name + suffix)
            selected_path.write_bytes(raw)
            parsed = read_json(selected_path) if suffix == ".json" else read_yaml(selected_path)
            if parsed != entry["record"]:
                return failure("CLOSURE_MISSING")
            selected_digest = (
                verify_self_digest(parsed, "/closure")
                if "digest" in parsed
                else semantic_digest(parsed)
            )
            if selected_digest != entry["semantic_digest"]:
                return failure("CLOSURE_MISSING")
            records[name] = parsed
        for item in bounded_list(
            subject_bundle["source_files"], MAX_REFERENCES, "/subject/source_files"
        ):
            entry = exact(item, {"path", "sha256", "bytes", "content_base64"}, "/source_file")
            path = safe_path(entry["path"], "/source_file/path").as_posix()
            if path in source_overrides:
                return failure("CLOSURE_MISSING")
            if not isinstance(entry["content_base64"], str):
                return failure("CLOSURE_MISSING")
            try:
                raw = base64.b64decode(entry["content_base64"], validate=True)
            except (ValueError, binascii.Error):
                return failure("CLOSURE_MISSING")
            if (
                len(raw) != entry["bytes"]
                or len(raw) > MAX_CONTROL_BYTES
                or hashlib.sha256(raw).hexdigest() != sha(entry["sha256"], "/source_file/sha256")
            ):
                return failure("CLOSURE_MISSING")
            source_overrides[path] = raw
        expected_source_paths = [
            safe_path(item["path"], "/snapshot/files/path").as_posix()
            for item in records["snapshot"]["files"]
        ] + [
            safe_path(item["path"], "/artifact_profile/templates/path").as_posix()
            for item in records["artifact_profile"].get("templates", [])
        ]
        if len(expected_source_paths) != len(source_overrides) or set(expected_source_paths) != set(
            source_overrides
        ):
            return failure("CLOSURE_MISSING")
        derived = build_subject(subject, records, source_override=source_overrides)
        if derived != subject:
            return failure("SUBJECT_MISMATCH")
        raw_root = root / "raw"
        raw_root.mkdir()
        raw_bindings: list[tuple[str, str, int]] = []
        for item in assessment["raw_output_refs"]:
            entry = exact(item, {"path", "sha256", "bytes", "content_base64"}, "/raw_output")
            logical = safe_path(entry["path"], "/raw_output/path")
            destination = raw_root.joinpath(*logical.parts)
            if destination.exists():
                return failure("DUPLICATE_ID")
            if not isinstance(entry["content_base64"], str):
                return failure("RAW_OUTPUT_MISMATCH")
            try:
                raw = base64.b64decode(entry["content_base64"], validate=True)
            except (ValueError, binascii.Error):
                return failure("RAW_OUTPUT_MISMATCH")
            if (
                len(raw) != entry["bytes"]
                or len(raw) > MAX_CONTROL_BYTES
                or hashlib.sha256(raw).hexdigest() != sha(entry["sha256"], "/raw_output/sha256")
            ):
                return failure("RAW_OUTPUT_MISMATCH")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
            raw_bindings.append((logical.as_posix(), entry["sha256"], entry["bytes"]))
        expected_raw: list[tuple[str, str, int]] = []
        for record in assessment["evidence_records"]:
            for item in bounded_list(
                record["raw_outputs"], MAX_REFERENCES, "/evidence/raw_outputs"
            ):
                entry = exact(item, {"path", "sha256", "bytes"}, "/evidence/raw_output")
                expected_raw.append(
                    (
                        safe_path(entry["path"], "/evidence/raw_output/path").as_posix(),
                        sha(entry["sha256"], "/evidence/raw_output/sha256"),
                        entry["bytes"],
                    )
                )
        if sorted(raw_bindings) != sorted(expected_raw):
            return failure("RAW_OUTPUT_MISMATCH")
        receipts = assessment["receipts"]
        if any(not isinstance(item, dict) for item in receipts):
            return failure("CLOSURE_MISSING")
        evidence_receipts = [
            item for item in receipts if item.get("payload_kind") == "assurance_evidence"
        ]
        decision_receipts = [
            item for item in receipts if item.get("payload_kind") == "assurance_decision"
        ]
        if len(evidence_receipts) + len(decision_receipts) != len(receipts):
            return failure("KIND_MISMATCH")
        payloads = {
            (kind, digest(record, exclude="__none__")): record
            for kind, records in (
                ("assurance_evidence", assessment["evidence_records"]),
                ("assurance_decision", assessment["decision_records"]),
            )
            for record in records
        }
        seen_sequences: set[tuple[str, str, str]] = set()
        receipt_index: dict[tuple[str, str], dict[str, Any]] = {}
        for receipt in receipts:
            kind = receipt.get("payload_kind")
            payload_digest = sha(receipt.get("payload_digest"), "/receipt/payload_digest")
            key = (kind, payload_digest)
            payload = payloads.get(key)
            if payload is None or key in receipt_index:
                return failure("CLOSURE_MISSING")
            receipt_index[key] = receipt
            # A stale reuse returns before predicate classification. Authenticate its
            # included receipts here, or a resealed signature could still replay.
            if recorded["evaluation_mode"] == "reuse_prior" and recorded["outcome"] == "stale":
                reasons = verify_receipt(
                    payload,
                    receipt,
                    profile,
                    payload_kind=kind,
                    requested_domain=recorded["assurance_domain"],
                    requested_scope=recorded["scope"],
                    as_of=instant(recorded["as_of"], "/gate_result/as_of"),
                    seen_sequences=seen_sequences,
                )
                if any(
                    code in reasons
                    for code in (
                        "SIGNATURE_INVALID",
                        "SUBJECT_MISMATCH",
                        "KIND_MISMATCH",
                        "RECEIPT_REPLAY",
                    )
                ):
                    return failure("CLOSURE_MISSING")
        if assessment["history_refs"]:
            prior_result = verify_assessment(
                assessment["history_refs"][0],
                trust_context,
                _history_depth=_history_depth + 1,
            )
            if prior_result["reproduced"] is not True:
                return failure("HISTORY_MISMATCH")
            if recorded["evaluation_mode"] == "reuse_prior" and recorded["outcome"] == "stale":
                prior = assessment["history_refs"][0]
                prior_payloads = {
                    (kind, digest(record, exclude="__none__"))
                    for kind, records in (
                        ("assurance_evidence", prior["evidence_records"]),
                        ("assurance_decision", prior["decision_records"]),
                    )
                    for record in records
                }
                prior_receipts = {
                    (item["payload_kind"], item["payload_digest"]): item
                    for item in prior["receipts"]
                }
                if any(
                    receipt_index.get(key) != prior_receipts.get(key)
                    for key in payloads.keys() & prior_payloads
                ):
                    return failure("CLOSURE_MISSING")
        calculated = evaluate_gate(
            subject,
            policy,
            profile,
            assessment["evidence_records"],
            evidence_receipts,
            assessment["decision_records"],
            decision_receipts,
            requested_domain=recorded["assurance_domain"],
            requested_scope=recorded["scope"],
            gate_id=recorded["gate_id"],
            as_of=instant(recorded["as_of"], "/gate_result/as_of"),
            raw_root=raw_root,
            mode=recorded.get("evaluation_mode", "normal"),
            prior_assessment=assessment["history_refs"][0] if assessment["history_refs"] else None,
            artifact_impact=_native_impact(assessment["history_refs"][0], records)
            if assessment["history_refs"] and recorded.get("evaluation_mode") == "reuse_prior"
            else None,
        )
    if calculated != recorded:
        return failure("ASSESSMENT_MISMATCH")
    if (
        assessment["readable_report"] != _readable_report(calculated)
        or assessment["limitations"] != calculated["limitations"]
    ):
        return failure("ASSESSMENT_MISMATCH")
    return {
        "reproduced": True,
        "outcome": calculated["outcome"],
        "assurance_domain": calculated["assurance_domain"],
        "scope": calculated["scope"],
        "reason_codes": calculated["reason_codes"],
    }
