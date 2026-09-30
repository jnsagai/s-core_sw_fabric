"""In-memory Fabro wire simulator for 006 contract tests; never a native capability claim.

Response shapes mirror the disposable pinned-candidate observations recorded in 006
acceptance. Scenario switches reproduce observed native hazards deterministically.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.process_source.reader import read_json, read_yaml
from score_sw_fabric.runtime.client import FabroClient
from score_sw_fabric.runtime.projection import project_version

ROOT = Path(__file__).resolve().parents[1]
LINEAR = ROOT / "tests/fixtures/compiler/linear"
COMMIT = "a" * 40
TOKEN = "fabro_dev_" + "c" * 64
ALL_CAPABILITIES = [
    "blob_read",
    "event_read",
    "output_read",
    "question_read",
    "run_cancel",
    "run_create",
    "run_inspect",
    "run_resume",
    "run_start",
    "stage_list",
    "timeline_read",
    "workflow_register",
]
DEMONSTRATED = [item for item in ALL_CAPABILITIES if item != "run_resume"]


def profile(demonstrated: list[str] | None = None) -> dict[str, Any]:
    return seal(
        {
            "schema_version": 1,
            "kind": "runtime_profile",
            "id": "simulated-006",
            "source_commit": COMMIT,
            "executable_sha256": "d" * 64,
            "source_api_sha256": "e" * 64,
            "base_url": "http://127.0.0.1:43286",
            "auth_mode": "dev_token_disposable",
            "declared_capabilities": ALL_CAPABILITIES,
            "demonstrated_capabilities": sorted(demonstrated or DEMONSTRATED),
            "limits": {"timeout_seconds": 5, "response_bytes": 8 * 1024 * 1024},
            "status": "candidate_only",
        }
    )


def linear_sources() -> tuple[dict[str, Any], dict[str, Any]]:
    return read_json(LINEAR / "out/package.json"), read_yaml(LINEAR / "compiler_profile.yaml")


def platform(seq: int, run_id: str, record: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "stream_seq": seq,
        "kind": "platform",
        "id": f"p{seq}",
        "recorded_at": 1790753916330 + seq,
        "item": {"seq": seq, "record": record},
    }


@dataclass
class Run:
    id: str
    version: str
    status: dict[str, Any]
    events: list[dict[str, Any]] = field(default_factory=list)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    stages: list[dict[str, Any]] = field(default_factory=list)
    questions: list[dict[str, Any]] = field(default_factory=list)
    outputs: dict[str, bytes] = field(default_factory=dict)
    pending_control: str | None = None
    cancel_polls: int = 0

    def record(self, record: dict[str, Any]) -> None:
        self.events.append(platform(len(self.events) + 1, self.id, record))

    def lifecycle(
        self, transition: str, status: dict[str, Any] | None = None, **extra: Any
    ) -> None:
        record: dict[str, Any] = {"kind": "run.lifecycle", "transition": transition, **extra}
        if status is not None:
            record["status"] = status
            self.status = status
        self.record(record)


@dataclass
class FakeFabro:
    """Deterministic native state machine behind the real bounded client."""

    runs: dict[str, Run] = field(default_factory=dict)
    versions: set[str] = field(default_factory=set)
    blobs: dict[str, bytes] = field(default_factory=dict)
    calls: list[tuple[str, str]] = field(default_factory=list)
    lose_create_response: bool = False
    start_outcome: str = "succeeded"
    cancel_after_polls: int = 1
    cancel_outcome: dict[str, Any] = field(
        default_factory=lambda: {"kind": "failed", "reason": "cancelled"}
    )
    resume_inert: bool = True
    missing_blobs: set[str] = field(default_factory=set)

    def client(self, demonstrated: list[str] | None = None) -> FabroClient:
        return FabroClient(
            profile(demonstrated),
            expected_commit=COMMIT,
            credential_provider=lambda: TOKEN,
            transport=self.transport,
        )

    def posts(self, suffix: str) -> int:
        return sum(1 for method, url in self.calls if method == "POST" and url.endswith(suffix))

    def _blob(self, payload: bytes) -> str:
        digest = hashlib.sha256(payload).hexdigest()
        self.blobs[digest] = payload
        return digest

    def _complete(self, run: Run) -> None:
        stages = ["start@1", "node_2e028993944f88df30dfca7b@1", "node_7d7113bb6893c9053161eed9@1"]
        for index, stage in enumerate([*stages, "exit@1"], start=1):
            patch = self._blob(f"diff for {stage}\n".encode())
            run.record(
                {
                    "kind": "checkpoint",
                    "firing": index,
                    "git_commit_sha": f"{index:040x}",
                    "patch_blob": patch,
                }
            )
            run.timeline.append(
                {
                    "checkpoint_seq": index,
                    "stage": stage,
                    "ordinal": index,
                    "run_commit_sha": f"{index:040x}",
                }
            )
            run.stages.append({"id": stage, "status": "succeeded"})
            run.outputs[stage] = b"" if stage != stages[1] else b"hello-006"
        run.lifecycle("succeeded", {"kind": "succeeded", "reason": "completed"})

    def transport(
        self, method: str, url: str, body: bytes | None, _timeout: float, maximum: int, token: str
    ) -> tuple[int, bytes]:
        assert token == TOKEN
        path = url.removeprefix("http://127.0.0.1:43286")
        self.calls.append((method, path))
        payload = json.loads(body) if body else None
        status, response = self._route(method, path, payload)
        data = response if isinstance(response, bytes) else json.dumps(response).encode()
        assert len(data) <= maximum
        return status, data

    def _route(self, method: str, path: str, body: Any) -> tuple[int, Any]:
        if method == "POST" and path == "/api/v1/workflow-versions":
            identifier = hashlib.sha256(canonical(body).removesuffix(b"\n")).hexdigest()
            self.versions.add(identifier)
            return 201, {"workflow_version_id": identifier}
        if method == "POST" and path == "/api/v1/runs":
            assert body["workflow_version_id"] in self.versions
            assert body["args"]["auto_approve"] is False
            run = Run(f"run-{len(self.runs) + 1}", body["workflow_version_id"], {})
            definition = self._blob(b"definition " + run.id.encode())
            run.record(
                {
                    "kind": "run.created",
                    "spec": {
                        "workflow_version_id": run.version,
                        "definition_blob": definition,
                        "settings": {"run": {"execution": {"approval": "prompt"}}},
                    },
                }
            )
            run.lifecycle("submitted", {"kind": "submitted"})
            self.runs[run.id] = run
            if self.lose_create_response:
                raise TimeoutError("response lost after native acceptance")
            return 201, {"id": run.id}
        match = re.fullmatch(r"/api/v1/runs/([A-Za-z0-9_-]+)(/.*)?", path.split("?")[0])
        if match is None or match.group(1) not in self.runs:
            return 404, {"errors": [{"status": "404"}]}
        run = self.runs[match.group(1)]
        tail = match.group(2) or ""
        query = (
            dict(item.split("=", 1) for item in path.split("?", 1)[1].split("&"))
            if "?" in path
            else {}
        )
        if method == "GET" and tail == "":
            if run.pending_control == "cancel":
                run.cancel_polls += 1
                if run.cancel_polls >= self.cancel_after_polls:
                    run.pending_control = None
                    run.lifecycle(self.cancel_outcome["kind"], dict(self.cancel_outcome))
            return 200, {
                "id": run.id,
                "lifecycle": {"status": run.status, "pending_control": run.pending_control},
                "usage": {"tokens": {"input": 0, "output": 0}},
            }
        if method == "POST" and tail == "/start":
            if body and body.get("resume") is True:
                run.lifecycle("start_requested", source="resume")
                run.lifecycle("runnable", {"kind": "runnable"}, source="start_requested")
                if self.resume_inert:
                    # Observed candidate behavior: the worker refuses and the summary keeps
                    # the prior terminal status while the stream records runnable.
                    run.status = {"kind": "failed", "reason": "terminated"}
                return 200, {"id": run.id, "lifecycle": {"status": run.status}}
            if run.status.get("kind") != "submitted":
                return 409, {"errors": [{"status": "409"}]}
            run.lifecycle("start_requested", source="start")
            run.lifecycle("runnable", {"kind": "runnable"}, source="start_requested")
            if self.start_outcome == "succeeded":
                self._complete(run)
            elif self.start_outcome == "blocked":
                run.stages.append({"id": "review@1", "status": "running"})
                run.questions.append({"id": "review#1", "stage": "review@1"})
                run.status = {"kind": "blocked", "blocked_reason": "human_input_required"}
            elif self.start_outcome == "terminated":
                run.timeline.append({"checkpoint_seq": 1, "stage": "start@1", "ordinal": 1})
                run.stages.extend(
                    [
                        {"id": "start@1", "status": "succeeded"},
                        {"id": "hold@1", "status": "running"},
                    ]
                )
                run.outputs.update({"start@1": b"", "hold@1": b""})
                run.lifecycle("failed", {"kind": "failed", "reason": "terminated"})
            return 200, {"id": run.id, "lifecycle": {"status": {"kind": "runnable"}}}
        if method == "POST" and tail == "/cancel":
            if run.status.get("kind") in {"succeeded", "failed", "dead"}:
                return 409, {"errors": [{"status": "409"}]}
            run.pending_control = "cancel"
            run.lifecycle("cancel_requested")
            return 202, {"status": run.status, "pending_control": "cancel"}
        if method == "GET" and tail == "/events":
            after, limit = int(query["after"]), int(query["limit"])
            page = [item for item in run.events if item["stream_seq"] > after][:limit]
            more = bool(page) and page[-1]["stream_seq"] < len(run.events)
            return 200, {"data": page, "meta": {"has_more": more}, "event_contract_version": 3}
        if method == "GET" and tail == "/timeline":
            return 200, {"entries": run.timeline}
        if method == "GET" and tail == "/questions":
            return 200, {"data": run.questions, "meta": {"has_more": False}}
        if method == "GET" and tail == "/stages":
            return 200, {"data": run.stages, "meta": {"has_more": False}}
        blob = re.fullmatch(r"/blobs/([0-9a-f]{64})", tail)
        if method == "GET" and blob:
            if blob.group(1) in self.missing_blobs or blob.group(1) not in self.blobs:
                return 404, {"errors": [{"status": "404"}]}
            return 200, self.blobs[blob.group(1)]
        output = re.fullmatch(r"/stages/([A-Za-z0-9_-]+@[0-9]+)/logs/output", tail)
        if method == "GET" and output:
            data = run.outputs.get(output.group(1), b"")
            offset = int(query["offset"])
            chunk = data[offset : offset + int(query["limit"])]
            return 200, {
                "offset": offset,
                "next_offset": offset + len(chunk),
                "total_bytes": len(data),
                "eof": offset + len(chunk) >= len(data),
                "bytes_base64": base64.b64encode(chunk).decode(),
                "cas_ref": None,
                "live_streaming": False,
            }
        return 405, {"errors": [{"status": "405"}]}


def intent(
    package: dict[str, Any],
    client: FabroClient,
    *,
    identifier: str = "intent-006",
    evidence: list[str] | None = None,
    attempts: int = 2,
) -> dict[str, Any]:
    package_bytes = (LINEAR / "out/package.json").read_bytes()
    return seal(
        {
            "schema_version": 1,
            "kind": "runtime_intent",
            "intent_id": identifier,
            "package_ref": {
                "path": "package.json",
                "sha256": hashlib.sha256(package_bytes).hexdigest(),
                "semantic_digest": package["digest"],
            },
            "runtime_profile_ref": {
                "path": "runtime-profile.json",
                "sha256": hashlib.sha256(canonical(client.profile)).hexdigest(),
                "semantic_digest": client.profile["digest"],
            },
            "baseline": baseline(evidence=evidence),
            "start_args": {"target_id": "local", "labels": {}},
            "limits": {
                "timeout_seconds": 5,
                "event_pages": 10,
                "output_bytes": 4096,
                "attempts": attempts,
            },
        }
    )


def baseline(**changes: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "source_digest": "1" * 64,
        "process_digest": "2" * 64,
        "policy_digest": "3" * 64,
        "tool_digest": "4" * 64,
        "subject_digest": "5" * 64,
        "evidence_digests": [],
    }
    for key, item in changes.items():
        if key == "evidence":
            value["evidence_digests"] = sorted(item or [])
        else:
            value[key] = item
    return value


def project(package: dict[str, Any], compiler_profile: dict[str, Any]) -> dict[str, Any]:
    return project_version(package, compiler_profile)


def write_request(
    root: Path,
    fabro: FakeFabro,
    *,
    identifier: str = "intent-006",
    baseline_now: dict[str, Any] | None = None,
    effects: list[dict[str, Any]] | None = None,
    evidence: list[tuple[Path, Path]] | None = None,
    evidence_digests: list[str] | None = None,
    demonstrated: list[str] | None = None,
) -> Path:
    """Write a complete version-1 runtime request with exact local byte bindings."""
    import os

    import yaml

    root.mkdir(parents=True, exist_ok=True)
    client = fabro.client(demonstrated)
    package_bytes = (LINEAR / "out/package.json").read_bytes()
    (root / "package.json").write_bytes(package_bytes)
    profile_bytes = (LINEAR / "compiler_profile.yaml").read_bytes()
    (root / "compiler_profile.yaml").write_bytes(profile_bytes)
    runtime_bytes = canonical(client.profile)
    (root / "runtime-profile.json").write_bytes(runtime_bytes)
    package, _ = linear_sources()
    selected = intent(package, client, identifier=identifier, evidence=evidence_digests)
    intent_bytes = canonical(selected)
    (root / "intent.json").write_bytes(intent_bytes)
    for name in ("fabro", "fabro-api.yaml"):
        (root / name).write_bytes(b"candidate placeholder")
    token = root / "token"
    token.write_text(TOKEN + "\n")
    os.chmod(token, 0o600)
    (root / "target").mkdir(exist_ok=True)

    def ref(name: str, data: bytes) -> dict[str, str]:
        return {"path": name, "sha256": hashlib.sha256(data).hexdigest()}

    request = {
        "schema_version": 1,
        "kind": "runtime_request",
        "runtime_commit": COMMIT,
        "intent": ref("intent.json", intent_bytes),
        "package": ref("package.json", package_bytes),
        "compiler_profile": ref("compiler_profile.yaml", profile_bytes),
        "runtime_profile": ref("runtime-profile.json", runtime_bytes),
        "candidate": {"executable": "fabro", "source_api": "fabro-api.yaml"},
        "credential_file": "token",
        "ledger_root": "ledger",
        "target": {
            "path": str(root / "target"),
            "disposable_root": str(root),
            "environment_id": "local",
        },
        "baseline_now": baseline_now,
        "evidence": [
            {
                "assessment": {
                    "path": str(assessment),
                    "sha256": hashlib.sha256(assessment.read_bytes()).hexdigest(),
                },
                "trust_context": {
                    "path": str(context),
                    "sha256": hashlib.sha256(context.read_bytes()).hexdigest(),
                },
            }
            for assessment, context in evidence or []
        ],
        "effects": effects or [],
        "subject": None,
        "protected_roots": ["protected"],
    }
    (root / "protected").mkdir(exist_ok=True)
    path = root / "request.yaml"
    path.write_text(yaml.safe_dump(request, sort_keys=True))
    return path
