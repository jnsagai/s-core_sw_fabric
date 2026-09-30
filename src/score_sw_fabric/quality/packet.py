"""Portable source/native/history closure without access to original host paths."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from score_sw_fabric.agents.models import local_dir, protected_roots
from score_sw_fabric.assurance.models import (
    bounded_list,
    digest,
    exact,
    nonempty,
    seal,
    sha,
    stable_id,
    verify_digest,
    version,
)
from score_sw_fabric.assurance.package import verify_assessment
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality import coverage, decisions, imports
from score_sw_fabric.quality import coverage_models as cm
from score_sw_fabric.quality import decision_models as decm
from score_sw_fabric.quality import disposition_models as dm
from score_sw_fabric.quality import import_models as im
from score_sw_fabric.quality import packet_models as pm
from score_sw_fabric.quality.models import MAX_ARTIFACT, Budget, raw_bytes
from score_sw_fabric.quality.profile import load_profile
from score_sw_fabric.runtime.models import output_path
from score_sw_fabric.runtime.request import parse_json, parse_yaml


class Closure:
    """Read only selected originals; the same assembly runs against an offline byte archive."""

    def __init__(self, archive: pm.Archive) -> None:
        self.archive = archive
        self.baselines: dict[str, dict[str, Any]] = {}
        self.analyses: dict[tuple[str, str], dict[str, Any]] = {}
        self.origins: set[str] = set()
        self.gaps: set[str] = set()
        self.closure_gaps: set[str] = set()

    def baseline(self, b: dict[str, Any]) -> None:
        identity = sha(b["full_digest"], "/baseline/full_digest")
        dm.files(b["files"])
        prior = self.baselines.get(identity)
        # Root and import sealing describe transport, not semantic baseline identity.
        if prior is not None and any(
            prior[k] != b[k] for k in ("component", "files", "expected_units")
        ):
            raise InputError("BASELINE_DRIFT", "Contradictory portable baseline identity")
        self.baselines[identity] = b

    def origin(self, record: dict[str, Any], context: Path | None = None) -> None:
        record, _, adapter = dm.origin(record)
        self.baseline(record["baseline"])
        self.origins.add(record["origin"])
        self.gaps.update(record["gaps"])
        if adapter is None:
            for a in record["artifacts"]:
                dm._raw(a["raw"])
        elif context is not None:
            b = record["baseline"]
            _, pb = self.archive.selected(context, b["profile"])
            _, chain = self.archive.control(context, b["toolchain"], yaml=True)
            cp, config = self.archive.control(context, b["configuration"], yaml=True)
            if load_profile(pb) != record["profile"] or chain != record["toolchain"]:
                raise InputError("TOOL_IDENTITY_MISMATCH", "Local origin profile/toolchain differs")
            if adapter in {"asan", "ubsan"}:
                for key in ("native_features", "native_runtime", "native_suppressions"):
                    self.archive.selected(cp.parent, config[key])
        if any(a.get("raw", a).get("truncated") for a in record["artifacts"]):
            self.closure_gaps.add("ORIGINAL_OUTPUT_TRUNCATED")

    def analysis(self, base: Path, pair: Any) -> dict[str, Any]:
        pair = exact(pair, {"request", "report"}, "/analysis")
        ap, request = self.archive.control(base, pair["request"], yaml=True)
        rp, report = self.archive.control(base, pair["report"], max_bytes=dm.MAX_RECORD)
        key = (str(ap), str(rp))
        if key in self.analyses:
            return self.analyses[key]
        version(request, "quality_import_request", im.REQUEST_FIELDS, "/import")
        im.choice(request["origin"], {"fixture", "imported_unverified"}, "/import/origin")
        for root_label in bounded_list(request["protected_roots"], 32, "/protected_roots"):
            pm.label(ap.parent, root_label)
        bp, b = self.archive.control(ap.parent, request["baseline"])
        version(b, "quality_import_baseline", im.BASELINE_FIELDS, "/baseline")
        verify_digest(b, "/baseline")
        stable_id(b["component"], "/component")
        root = pm.label(bp.parent, b["root"])
        files: dict[str, bytes] = {}
        for f in bounded_list(b["files"], 500, "/baseline/files"):
            dm.ref(f, "/file")
            from score_sw_fabric.agents.models import relative_path

            name = relative_path(f["path"], "/file/path")
            if name in files:
                raise InputError("DUPLICATE_ID", "Duplicate frozen source")
            _, data = self.archive.selected(root, f)
            files[name] = data
        if not files or sum(map(len, files.values())) > 64 * 1024 * 1024:
            raise InputError("LIMIT_EXCEEDED", "Empty or oversized frozen source")
        if b["expected_units"] is not None:
            im.units(b["expected_units"], "/expected_units", files)
        identities: dict[str, dict[str, Any]] = {}
        for item in bounded_list(b["identities"], 32, "/identities"):
            ident = im.identity(item)
            if ident["id"] in identities:
                raise InputError("DUPLICATE_ID", "Duplicate analyzer identity")
            identities[ident["id"]] = ident
        if not identities:
            raise InputError("FIELD_TYPE", "Analyzer identity is empty")
        source = {k: b[k] for k in ("component", "files", "expected_units")}
        snapshot = {
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
        snapshot.pop("digest")
        snapshot = seal(snapshot)
        _, profile_bytes = self.archive.selected(ap.parent, request["profile"])
        profile = load_profile(profile_bytes)
        _, manifest = self.archive.control(ap.parent, request["extraction"])
        artifacts = []
        budget = Budget(MAX_ARTIFACT)
        seen: set[str] = set()
        gaps = []
        expected_raw = {a["id"]: a["raw"] for a in report.get("artifacts", [])}
        for raw in bounded_list(request["artifacts"], 500, "/artifacts"):
            a = exact(raw, im.ARTIFACT_FIELDS, "/artifact")
            name = nonempty(a["id"], "/artifact/id", max_length=1024)
            if name in seen:
                raise InputError("DUPLICATE_ID", "Duplicate artifact")
            seen.add(name)
            im.choice(a["tool"], set(identities), "/artifact/tool")
            im.choice(a["role"], {"diagnostics", "supporting", "log"}, "/artifact/role")
            im.choice(
                a["format"],
                {
                    "clang-tidy-yaml",
                    "clang-tidy-text",
                    "cppcheck-xml",
                    "sarif-2.1.0",
                    "asan-text",
                    "ubsan-text",
                    "text",
                },
                "/artifact/format",
            )
            allowed = {
                "clang-tidy-yaml": "clang-tidy",
                "clang-tidy-text": "clang-tidy",
                "cppcheck-xml": "cppcheck",
                "asan-text": "asan",
                "ubsan-text": "ubsan",
            }
            if (
                (a["format"] in allowed and allowed[a["format"]] != a["tool"])
                or (a["role"] == "diagnostics" and a["format"] == "text")
                or (a["role"] != "diagnostics" and a["format"] != "text")
            ):
                raise InputError("FIELD_ENUM", "Native format/role/tool selection differs")
            im.native_root(a["source_root"])
            im.units(a["units"], "/artifact/units", files)
            bindings = exact(
                a["bindings"], {"source_digest", "profile_sha256", "identity_digest"}, "/bindings"
            )
            if (
                bindings["source_digest"] != snapshot["source_digest"]
                or bindings["profile_sha256"] != request["profile"]["sha256"]
            ):
                gaps.append("BASELINE_DRIFT")
            if bindings["identity_digest"] != digest(identities[a["tool"]]):
                gaps.append("TOOL_IDENTITY_MISMATCH")
            entry = self.archive.capture(pm.label(ap.parent, a["ref"]["path"]))
            if entry["raw"]["sha256"] != a["ref"]["sha256"]:
                raise InputError("INPUT_DRIFT", "Native original differs from selection")
            if not entry["raw"]["truncated"]:
                captured = budget.capture(raw_bytes(entry["raw"]), a["format"])
            else:
                # Full native stream is unavailable; verify retained original prefix and preserve
                # its declared full-stream hash without treating truncation as clean evidence.
                retained_record = expected_raw.get(name)
                if retained_record is None:
                    raise InputError("PACKET_CLOSURE_MISSING", "Truncated native output is absent")
                captured = retained_record
                dm._raw(captured)
                retained = raw_bytes(captured)
                if (
                    not captured["truncated"]
                    or captured["sha256"] != entry["raw"]["sha256"]
                    or captured["bytes"] != entry["raw"]["bytes"]
                    or not raw_bytes(entry["raw"]).startswith(retained)
                    or len(retained) != min(MAX_ARTIFACT, budget.remaining, captured["bytes"])
                    or captured["format"] != a["format"]
                ):
                    raise InputError("INPUT_DRIFT", "Native retained prefix differs")
                budget.remaining -= len(retained)
            if captured["truncated"]:
                gaps.append("OUTPUT_TRUNCATED")
                self.closure_gaps.add("ORIGINAL_OUTPUT_TRUNCATED")
            artifacts.append({**a, "raw": captured})
        selected = im.ImportInputs(
            request, profile, snapshot, files, identities, artifacts, manifest, [], [], gaps
        )
        reproduced = imports.evaluate(selected, ap.parent, resolve=self.archive.selected)
        if reproduced != report:
            raise InputError(
                "ANALYSIS_NOT_REPRODUCED", "Portable import differs from original-byte replay"
            )
        self.origin(report)
        # Retain source/config/tool notices carried by genuine local origin logs.
        for a in artifacts:
            if a["role"] == "log" and not a["raw"]["truncated"]:
                data = raw_bytes(a["raw"])
                if data.lstrip().startswith(b"{"):
                    local = parse_json(data, "/local_origin")
                    if isinstance(local, dict) and local.get("kind") in {
                        "quality_analysis_run",
                        "quality_cppcheck_analysis_run",
                        "quality_asan_analysis_run",
                        "quality_ubsan_analysis_run",
                    }:
                        self.origin(local, ap.parent)
        entry = {"selection": pair, "request_path": str(ap), "request": request, "report": report}
        self.analyses[key] = entry
        return entry

    def manifest_sources(self, path: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
        cm.manifest(manifest)
        sources = []
        for s in manifest["source_refs"]:
            _, r = self.archive.control(path.parent, s["ref"])
            version(r, "quality_guideline_source", cm.SOURCE_FIELDS, "/guideline_source")
            if any(r[k] != s[k] for k in ("id", "license", "notice", "native_status")):
                raise InputError("SOURCE_REF", "Guideline source metadata differs")
            im.strings(r["guideline_ids"], "/source/guideline_ids", 1000)
            sources.append({"selection": s, "record": r})
        records = {s["record"]["id"]: s["record"] for s in sources}
        for row in [*(manifest["expected_guidelines"] or []), *manifest["rows"]]:
            refs = [row, *row.get("mechanisms", [])]
            for item in refs:
                if any(
                    row["guideline_id"] not in records[s]["guideline_ids"]
                    for s in item["source_ids"]
                ):
                    raise InputError("SOURCE_REF", "Guideline is absent from selected source")
        return sources

    def matrix(self, base: Path, pair: Any) -> dict[str, Any]:
        pair = exact(pair, {"request", "report"}, "/coverage")
        ap, request = self.archive.control(base, pair["request"], yaml=True)
        _, matrix = self.archive.control(base, pair["report"], max_bytes=dm.MAX_RECORD)
        version(request, "quality_coverage_request", cm.REQUEST_FIELDS, "/coverage/request")
        verify_digest(matrix, "/matrix")
        if matrix.get("kind") != "quality_guideline_matrix" or matrix.get("accepted_claims") != 0:
            raise InputError("KIND_MISMATCH", "Invalid matrix")
        self.baseline(matrix["baseline"])
        _, selected_profile = self.archive.selected(ap.parent, request["profile"])
        if matrix["profile"] != load_profile(selected_profile):
            raise InputError("PROFILE_DRIFT", "Matrix profile differs")
        bp, b = self.archive.control(ap.parent, request["baseline"])
        verify_digest(b, "/baseline")
        # Selected baseline transport is retained; source bytes bind matrix identity.
        if matrix["baseline"]["input_digest"] != b["digest"] or any(
            matrix["baseline"][k] != b[k]
            for k in ("component", "files", "expected_units", "identities")
        ):
            raise InputError("BASELINE_DRIFT", "Matrix baseline differs")
        if matrix["baseline"]["root"] != str(pm.label(bp.parent, b["root"])):
            raise InputError("BASELINE_DRIFT", "Matrix source root differs")
        source = {k: b[k] for k in ("component", "files", "expected_units")}
        expected_baseline = {
            **b,
            "root": str(pm.label(bp.parent, b["root"])),
            "source_digest": digest(source),
            "profile": request["profile"],
            "full_digest": digest(
                {**source, "profile": request["profile"], "identities": b["identities"]}
            ),
            "input_digest": b["digest"],
            "kind": "quality_import_baseline_snapshot",
        }
        expected_baseline.pop("digest")
        if seal(expected_baseline) != matrix["baseline"]:
            raise InputError("BASELINE_DRIFT", "Matrix baseline digest closure differs")
        for f in b["files"]:
            self.archive.selected(Path(matrix["baseline"]["root"]), f)
        mp, m = self.archive.control(ap.parent, request["manifest"])
        sources = self.manifest_sources(mp, m)
        self.origins.add(m["origin"])
        if (
            m["scope"]["component"] != b["component"]
            or set(m["scope"]["files"]) != {f["path"] for f in b["files"]}
            or (m["scope"]["translation_units"] is None) != (b["expected_units"] is None)
            or set(m["scope"]["translation_units"] or []) != set(b["expected_units"] or [])
        ):
            raise InputError("SCOPE_MISMATCH", "Portable guideline scope differs")
        if m != matrix["manifest"]:
            raise InputError("SOURCE_REF", "Matrix declaration differs")
        previous = None
        changes = []
        if request["previous_manifest"] is not None:
            pp, prior = self.archive.control(ap.parent, request["previous_manifest"])
            self.manifest_sources(pp, prior)
            self.origins.add(prior["origin"])
            previous = {"ref": request["previous_manifest"], "manifest": prior}
            old = {r["guideline_id"]: r for r in prior["expected_guidelines"] or []}
            old_rows = {r["guideline_id"]: r for r in prior["rows"]}
            expected = {r["guideline_id"]: r for r in m["expected_guidelines"] or []}
            mappings = {r["guideline_id"]: r for r in m["rows"]}
            for name in sorted(old.keys() | old_rows.keys() | expected.keys() | mappings.keys()):
                before = {"expectation": old.get(name), "mapping": old_rows.get(name)}
                after = {"expectation": expected.get(name), "mapping": mappings.get(name)}
                if before != after:
                    changes.append({"guideline_id": name, "previous": before, "current": after})
            if any(prior[k] != m[k] for k in ("scope", "source_refs", "origin")):
                changes.append(
                    {
                        "guideline_id": None,
                        "previous": {k: prior[k] for k in ("scope", "source_refs", "origin")},
                        "current": {k: m[k] for k in ("scope", "source_refs", "origin")},
                    }
                )
        if matrix["previous"] != previous:
            raise InputError("SOURCE_REF", "Prior declaration differs")
        analyses = []
        for selected in bounded_list(request["analyses"], 20, "/analyses"):
            report = self.analysis(ap.parent, selected)["report"]
            drift = [
                "BASELINE_DRIFT:" + k
                for k in ("component", "files", "expected_units", "identities", "profile")
                if report["baseline"][k] != matrix["baseline"][k]
            ]
            analyses.append(
                {
                    "selection": selected,
                    "report": report,
                    "current": not drift,
                    "reasons": sorted(drift),
                }
            )
        reproduced = coverage.evaluate(
            matrix["profile"], matrix["baseline"], m, sources, previous, changes, analyses
        )
        if reproduced != matrix:
            raise InputError("COVERAGE_NOT_REPRODUCED", "Portable coverage evaluation differs")
        self.gaps.update(matrix["gaps"])
        self.origins.add(matrix["origin"])
        return {"selection": pair, "request_path": str(ap), "request": request, "report": matrix}

    def review(self, base: Path, pair: Any) -> dict[str, Any]:
        pair = exact(pair, {"request", "review", "decision"}, "/disposition")
        ap, request = self.archive.control(base, pair["request"], yaml=True)
        rp, review = self.archive.control(base, pair["review"], max_bytes=dm.MAX_RECORD)
        version(request, "quality_disposition_request", dm.REQUEST_FIELDS, "/disposition_request")
        im.choice(request["action"], {"draft", "check_correction"}, "/action")
        current_selection = exact(request["current"], {"adapter", "request"}, "/current")
        adapter = im.choice(
            current_selection["adapter"], {"clang-tidy", "cppcheck", "asan", "ubsan"}, "/adapter"
        )
        op, original = self.archive.control(ap.parent, request["origin"], max_bytes=dm.MAX_RECORD)
        original, findings, _ = dm.origin(original)
        self.origin(original, op.parent)
        dp, draft = self.archive.control(ap.parent, request["draft"])
        dm.draft(draft, original, findings)
        expected_subject = seal(
            {
                "origin_ref": request["origin"],
                "origin_digest": original["digest"],
                "origin_class": original["origin"],
                "finding_index": draft["finding_index"],
                "finding": findings[draft["finding_index"]],
                "baseline": original["baseline"],
            }
        )
        dm.previous(review, draft, expected_subject, max_revision=1000)
        self.baseline(review["current_baseline"])
        self.origins.add(review["origin"])
        self.gaps.update(review["reasons"])
        # Read the current run selection and configuration, never execute it.
        current_path, current = self.archive.control(
            ap.parent, request["current"]["request"], yaml=True
        )
        from score_sw_fabric.quality.models import RUN_FIELDS

        prefix = "quality" if adapter == "clang-tidy" else "quality_" + adapter
        version(current, prefix + "_run_request", RUN_FIELDS, "/current/run_request")
        for key in ("profile", "toolchain", "config"):
            self.archive.selected(current_path.parent, current[key])
        _, config = self.archive.control(current_path.parent, current["config"], yaml=True)
        if request["current"]["adapter"] in {"asan", "ubsan"}:
            config_path = pm.label(current_path.parent, current["config"]["path"])
            for key in ("native_features", "native_runtime", "native_suppressions"):
                self.archive.selected(config_path.parent, config[key])
        current_source = {
            k: current[k]
            for k in ("files", "translation_units", "expected_units", "include_dirs", "defines")
        }
        current_baseline = {
            "component": current["component"],
            **current_source,
            "language": "c++17",
            "source_digest": digest({**current_source, "language": "c++17"}),
            "profile": current["profile"],
            "toolchain": current["toolchain"],
            "configuration": current["config"],
        }
        current_baseline["full_digest"] = digest(current_baseline)
        if current_baseline != review["current_baseline"]:
            raise InputError("BASELINE_DRIFT", "Current selection differs from retained review")
        if request["previous"] != (review["previous"]["ref"] if review["previous"] else None):
            raise InputError("DISPOSITION_HISTORY", "Selected review request differs from history")
        for key in ("compensating_evidence", "decision_refs"):
            for ref in draft[key]:
                self.archive.selected(dp.parent, ref)
        history: list[dict[str, Any]] = []
        child, child_path = review, rp
        seen = {str(rp)}
        size = 0
        while child["previous"] is not None:
            hp, prior = self.archive.control(
                child_path.parent, child["previous"]["ref"], max_bytes=dm.MAX_RECORD
            )
            if str(hp) in seen:
                raise InputError("DISPOSITION_HISTORY", "Cyclic portable review history")
            seen.add(str(hp))
            dm.previous(prior, draft, expected_subject)
            size += len(canonical(prior))
            if len(history) >= 999 or size > dm.MAX_RECORD:
                raise InputError("LIMIT_EXCEEDED", "Portable review history exceeds bounds")
            if (
                prior["digest"] != child["previous"]["digest"]
                or prior["state"] != child["previous"]["state"]
                or prior["revision"] + 1 != child["revision"]
            ):
                raise InputError("DISPOSITION_HISTORY", "History linkage differs")
            history.append({"path": str(hp), "record": prior})
            child, child_path = prior, hp
        if child["revision"] != 1:
            raise InputError("DISPOSITION_HISTORY", "History root is not revision 1")
        for r in [review, *(p["record"] for p in history)]:
            self.baseline(r["current_baseline"])
            for control_key in ("profile", "toolchain", "configuration"):
                # Baseline transport references keep their original path labels. Relative
                # paths belong to the explicitly retained current run selection's directory.
                self.archive.selected(current_path.parent, r["current_baseline"][control_key])
            if r["fresh_run"] is not None:
                self.origin(r["fresh_run"], current_path.parent)
        decision = None
        if pair["decision"] is not None:
            selection = exact(pair["decision"], {"request", "result"}, "/decision")
            ep, er = self.archive.control(base, selection["request"], yaml=True)
            _, result = self.archive.control(base, selection["result"], max_bytes=dm.MAX_RECORD)
            version(
                er,
                "quality_disposition_decision_request",
                decm.DECISION_FIELDS,
                "/decision",
            )
            verify_digest(result, "/decision_result")
            if (
                result.get("kind") != "quality_disposition_decision_result"
                or result["binding"]["review"] != review
            ):
                raise InputError("DISPOSITION_SUBJECT_MISMATCH", "Decision selects another review")
            self.archive.selected(ep.parent, er["review"])
            self.archive.selected(ep.parent, er["disposition_request"])
            if er["policy"] is not None:
                pp, policy = self.archive.control(ep.parent, er["policy"])
                self.archive.selected(pp.parent, policy["source_ref"])
            selected_decisions = []
            count = total = 0
            for entry, refs in zip(result["decisions"], er["decisions"], strict=True):
                _, assessment = self.archive.control(
                    ep.parent, refs["assessment"], max_bytes=dm.MAX_RECORD
                )
                _, context = self.archive.control(
                    ep.parent, refs["trust_context"], max_bytes=dm.MAX_RECORD
                )
                if assessment != entry["assessment"] or context != entry["trust_context"]:
                    raise InputError("DECISION_NOT_REPRODUCED", "005 originals differ")
                if verify_assessment(assessment, context) != entry["replay"]:
                    raise InputError("DECISION_NOT_REPRODUCED", "005 replay differs")
                count += decisions._decision_count(assessment)
                total += len(canonical(assessment)) + len(canonical(context))
                if count > 20 or total > dm.MAX_RECORD:
                    raise InputError("LIMIT_EXCEEDED", "Portable decision closure exceeds bounds")
                selected_decisions.append((refs, assessment, context))
            if decisions.evaluate(er, result["binding"], selected_decisions) != result:
                raise InputError(
                    "DECISION_NOT_REPRODUCED", "Current fixture decision replay differs"
                )
            self.baseline(result["binding"]["current_baseline"])
            self.origins.add(result["origin"])
            self.gaps.update(result["reasons"])
            decision = {
                "selection": selection,
                "request_path": str(ep),
                "request": er,
                "result": result,
            }
        return {
            "selection": pair,
            "request_path": str(ap),
            "request": request,
            "origin_path": str(op),
            "origin": original,
            "review": review,
            "history": history,
            "decision": decision,
        }


def _assemble(path: Path, request: dict[str, Any], archive: pm.Archive) -> dict[str, Any]:
    version(request, "quality_packet_request", pm.REQUEST_FIELDS, "/request")
    base = path.parent
    _, profile_bytes = archive.selected(base, request["profile"])
    profile = load_profile(profile_bytes)
    closure = Closure(archive)
    closure.gaps.update(profile["required_obligations"])
    closure.gaps.update(
        {"RULE_MAPPING_UNKNOWN", "PRODUCTION_AUTHORITY_UNAVAILABLE", "HUMAN_REVIEW_PENDING"}
    )
    matrix = closure.matrix(base, request["coverage"]) if request["coverage"] is not None else None
    if matrix is None:
        closure.gaps.add("GUIDELINE_DENOMINATOR_UNKNOWN")
    explicit = set()
    for pair in bounded_list(request["analyses"], 20, "/analyses"):
        entry = closure.analysis(base, pair)
        pair_key = (entry["request_path"], entry["selection"]["report"]["sha256"])
        if pair_key in explicit:
            raise InputError("DUPLICATE_ID", "Duplicate explicit analysis")
        explicit.add(pair_key)
    if not closure.baselines:
        raise InputError("FIELD_TYPE", "Packet needs a current baseline or analysis")
    if len(closure.analyses) > 20:
        raise InputError("LIMIT_EXCEEDED", "Packet analyses exceed 20")
    reviews = []
    seen = set()
    for pair in bounded_list(request["dispositions"], 1000, "/dispositions"):
        review = closure.review(base, pair)
        identity = review["review"]["draft"]["id"]
        if identity in seen:
            raise InputError("DUPLICATE_ID", "Select one terminal history per disposition")
        seen.add(identity)
        reviews.append(review)
        pm.bounded_record({"dispositions": reviews})
    sources = []
    selected = set()
    for snapshot in bounded_list(request["source_snapshots"], 500, "/source_snapshots"):
        exact(snapshot, {"baseline_digest", "root"}, "/source_snapshot")
        key = sha(snapshot["baseline_digest"], "/baseline_digest")
        if key in selected or key not in closure.baselines:
            raise InputError("BASELINE_DRIFT", "Duplicate or unselected snapshot identity")
        selected.add(key)
        b = closure.baselines[key]
        root = pm.label(base, snapshot["root"])
        for ref in b["files"]:
            archive.selected(root, ref)
        sources.append(
            {
                "baseline_digest": key,
                "root": str(root),
                "component": b["component"],
                "files": b["files"],
                "expected_units": b["expected_units"],
            }
        )
    for key in closure.baselines.keys() - selected:
        closure.closure_gaps.add("SOURCE_SNAPSHOT_MISSING:" + key)
    notices = []
    seen = set()
    for raw in bounded_list(request["notices"], 64, "/notices"):
        n = exact(raw, {"id", "license", "notice", "ref", "applies_to"}, "/notice")
        identity = stable_id(n["id"], "/notice/id")
        if identity in seen:
            raise InputError("DUPLICATE_ID", "Duplicate notice ID")
        seen.add(identity)
        for key in ("license", "notice"):
            nonempty(n[key], "/notice/" + key, max_length=1024)
        im.strings(n["applies_to"], "/notice/applies_to", 64)
        fp, _ = archive.selected(base, n["ref"])
        notices.append({**n, "path": str(fp)})
    if not notices:
        closure.closure_gaps.add("LICENSE_NOTICE_CLOSURE_MISSING")
    required_notices = {"native:" + s["id"] for s in profile["native_sources"]}
    required_notices.update(
        "tool:" + i["id"] for a in closure.analyses.values() for i in a["report"]["identities"]
    )
    required_notices.update(
        "tool:" + i["id"] for b in closure.baselines.values() for i in b.get("identities", [])
    )
    for review in reviews:
        origins = [review["origin"]]
        if review["review"]["fresh_run"] is not None:
            origins.append(review["review"]["fresh_run"])
        for origin in origins:
            if origin["kind"] != "quality_native_import":
                adapter = dm.origin(origin)[2]
                assert adapter is not None
                required_notices.add("tool:" + adapter)
    supplied_notices = {name for n in notices for name in n["applies_to"]}
    for name in required_notices - supplied_notices:
        closure.closure_gaps.add("LICENSE_NOTICE_MISSING:" + name)
    for entry in archive.listing():
        if entry["raw"]["truncated"]:
            closure.closure_gaps.add("ARCHIVE_ORIGINAL_TRUNCATED")
    return seal(
        {
            "schema_version": 1,
            "kind": "quality_review_packet",
            "request_path": str(path),
            "request": request,
            "profile": profile,
            "coverage": matrix,
            "analyses": list(closure.analyses.values()),
            "dispositions": reviews,
            "sources": sorted(sources, key=lambda s: s["baseline_digest"]),
            "notices": notices,
            "files": archive.listing(),
            "origins": sorted(closure.origins),
            "gaps": sorted(closure.gaps | closure.closure_gaps),
            "questions": copy.deepcopy(pm.QUESTIONS),
            "packet_state": "incomplete" if closure.closure_gaps else "complete",
            "accepted_claims": 0,
            "outcome": "incomplete" if closure.closure_gaps else "emitted",
            "origin": "local_unprotected_evaluation",
            "assurance_eligibility": "not_eligible",
            "engineering_readiness": "not_evaluated",
            "limitations": pm.LIMITATIONS,
        }
    )


def packet(
    request_path: Path, out: Path | None = None
) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    path = request_path.absolute()
    request = version(
        im.control(path, yaml=True), "quality_packet_request", pm.REQUEST_FIELDS, "/request"
    )
    archive = pm.Archive()
    archive.capture(path)
    # Retained observations must reproduce at selection time; no analyzer execution occurs.
    if request["coverage"] is not None:
        pair = exact(request["coverage"], {"request", "report"}, "/coverage")
        ap, _ = im.selected_control(path.parent, pair["request"], yaml=True)
        _, supplied = im.selected_control(path.parent, pair["report"], max_bytes=dm.MAX_RECORD)
        _, reproduced, _, _ = coverage.measure(ap)
        if supplied != reproduced:
            raise InputError(
                "COVERAGE_NOT_REPRODUCED", "Selected matrix differs from coverage replay"
            )
    for pair in bounded_list(request["dispositions"], 1000, "/dispositions"):
        exact(pair, {"request", "review", "decision"}, "/disposition")
        if pair["decision"] is not None:
            selection = exact(pair["decision"], {"request", "result"}, "/decision")
            ap, _ = im.selected_control(path.parent, selection["request"], yaml=True)
            _, result = im.selected_control(
                path.parent, selection["result"], max_bytes=dm.MAX_RECORD
            )
            _, reproduced, _, _ = decisions.assess(ap)
            if reproduced != result:
                raise InputError(
                    "DECISION_NOT_REPRODUCED", "Selected decision differs from bridge replay"
                )
    record = _assemble(path, request, archive)
    pm.bounded_record(record)
    inputs = [Path(entry["path"]) for entry in archive.listing()]
    protected = protected_roots(path.parent, request["protected_roots"], "/protected_roots")
    protected.extend(
        local_dir(path.parent, s["root"], "/snapshot/root") for s in request["source_snapshots"]
    )
    for entry in record["analyses"]:
        protected.append(Path(entry["report"]["baseline"]["root"]))
        protected.extend(
            pm.label(Path(entry["request_path"]).parent, root)
            for root in entry["request"]["protected_roots"]
        )
    if record["coverage"] is not None:
        protected.append(Path(record["coverage"]["report"]["baseline"]["root"]))
        protected.extend(
            pm.label(Path(record["coverage"]["request_path"]).parent, root)
            for root in record["coverage"]["request"]["protected_roots"]
        )
    for entry in record["dispositions"]:
        protected.extend(
            pm.label(Path(entry["request_path"]).parent, root)
            for root in entry["request"]["protected_roots"]
        )
        original = entry["origin"]
        if original["kind"] == "quality_native_import":
            protected.append(im.native_root(original["baseline"]["root"]))
        current_path, current = archive.control(
            Path(entry["request_path"]).parent, entry["request"]["current"]["request"], yaml=True
        )
        protected.append(pm.label(current_path.parent, current["root"]))
        _, chain = archive.control(current_path.parent, current["toolchain"], yaml=True)
        inputs.extend(Path(asset["path"]) for asset in [chain["tool"], *chain["dependencies"]])
        protected.extend(Path(root) for root in chain["library_dirs"])
    if out is not None:
        output_path(out, inputs, protected)
    archive.recheck()
    if im.control(path, yaml=True) != request:
        raise InputError("INPUT_DRIFT", "Packet request changed")
    if out is not None:
        output_path(out, inputs, protected)
    return 0 if record["packet_state"] == "complete" else 1, record, inputs, protected


def verify_packet(value: Any) -> dict[str, Any]:
    """Rebuild portable structural closure using embedded originals only; no host file access."""
    try:
        record = version(value, "quality_review_packet", pm.PACKET_FIELDS, "/packet")
        pm.bounded_record(record)
        verify_digest(record, "/packet")
        archive = pm.Archive(bounded_list(record["files"], 5000, "/files"))
        path = pm.label(Path("/"), record["request_path"])
        original = archive.capture(path)
        if original["raw"]["truncated"]:
            raise InputError("PACKET_CLOSURE_TRUNCATED", "Packet request is truncated")
        request = parse_yaml(raw_bytes(original["raw"]), "/request")
        rebuilt = _assemble(path, request, archive)
        if rebuilt != record:
            raise InputError(
                "PACKET_NOT_REPRODUCED", "Portable packet differs from original-byte closure"
            )
        if archive.used != set(archive.entries):
            raise InputError("PACKET_CLOSURE_EXTRA", "Unselected archive bytes")
        return {"reproduced": True, "reason_codes": [], "packet_state": record["packet_state"]}
    except (InputError, KeyError, TypeError, ValueError, RecursionError) as exc:
        code = exc.code if isinstance(exc, InputError) else "PACKET_NOT_REPRODUCED"
        return {"reproduced": False, "reason_codes": [code], "packet_state": "incomplete"}
