"""Prepare a bounded operational demonstration using the real fabric compiler.

The local plan describes measurement work, not accepted native engineering needs.
The authorization reference covers draft execution only. Human reviews stay pending.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
from pathlib import Path

import yaml
from storage import new_run_root

from score_sw_fabric import storage as fabric_storage
from score_sw_fabric import workspace_transfer as fabric_transfer
from score_sw_fabric.compiler.package import compile_request
from score_sw_fabric.compiler.reader import semantic_digest

REPO = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
PIN = "1b4fb15281ebb724426f9e480dce48d0100ff79b"
BINARY = Path(
    os.environ.get(
        "SCORE_FABRO_BIN",
        "/home/jefferson/.local/share/s-core-tools/fabro-1b4fb152-agent32768/fabro",
    )
)
SOURCE = Path("/home/jefferson/fabro")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def semantic_seal(value: dict) -> dict:
    value = {k: v for k, v in value.items() if k != "digest"}
    return {**value, "digest": semantic_digest(value)}


def prepare(root: Path | None = None) -> Path:
    root = root or new_run_root()
    root.mkdir(parents=True, exist_ok=True)
    # Freeze the shared implementation with each prepared run, just like other tools.
    shutil.copyfile(Path(fabric_storage.__file__), root / "storage.py")
    shutil.copyfile(Path(fabric_transfer.__file__), root / "workspace_transfer.py")
    target = root / "target"
    target.mkdir()
    (root / "out").mkdir()
    handoff = HERE.parent
    compiler = Path(shutil.which("g++-12") or "").resolve(strict=True)
    patch = Path(shutil.which("patch") or "").resolve(strict=True)
    controls = [
        handoff / name
        for name in (
            "source-manifest.json",
            "googletest-manifest.json",
            "candidate-files.json",
            "someip-84.patch",
            "issue-snapshot.json",
        )
    ] + [HERE / "measure.py", compiler, patch]
    measurement = {
        "target": str(target),
        "disposable_root": str(root),
        "baseline": str(REPO / ".tools/someip-84/baseline"),
        "googletest": str(REPO / ".tools/someip-84/work/.llm_tmp/googletest"),
        "source_manifest": str(handoff / "source-manifest.json"),
        "googletest_manifest": str(handoff / "googletest-manifest.json"),
        "candidate_files": str(handoff / "candidate-files.json"),
        "candidate_root": str(REPO / ".tools/someip-84/work"),
        "patch": str(handoff / "someip-84.patch"),
        "compiler": str(compiler),
        "patch_tool": str(patch),
        "controls": [{"path": str(p), "sha256": sha(p)} for p in controls],
    }
    write(root / "measurement-inputs.json", measurement)
    authority = {
        "scope": "Draft operational factory demonstrator; no engineering acceptance",
        "user_direction": "Build the software factory; use SOME/IP; go",
        "date": "2026-10-01",
        "engineering_review": "pending",
        "paid_calls": "disabled",
        "live_agent_admission": "pending provider and spending limit",
    }
    write(root / "task-authority.json", authority)
    origin = {
        "kind": "authorized_human_decision",
        "source_ref": {"path": "task-authority.json", "sha256": sha(root / "task-authority.json")},
        "pointer": "/scope",
        "decision_ref": "user-continuation-20261001",
        "rationale": "User authorized operational execution; engineering decisions remain pending.",
    }
    ids = [
        "local-baseline-measurement",
        "local-external-candidate-measurement",
        "local-agent-admission",
    ]
    plan = semantic_seal(
        {
            "schema_version": 1,
            "plan_kind": "draft",
            "planning_status": "complete",
            "closure_complete": True,
            "engineering_readiness": "not_evaluated",
            "target_namespace": "local-operational-demonstrator",
            "change": {"id": "someip84-factory-measurement"},
            "semantic_inputs": {"task_authority": sha(root / "task-authority.json")},
            "scopes": [],
            "coverage": [],
            "findings": [],
            "instances": [
                {
                    "instance_id": name,
                    "applicability": "required",
                    "effective_disposition": "create",
                    "dependency_ids": ids[i - 1 : i],
                }
                for i, name in enumerate(ids)
            ],
        }
    )
    profile = yaml.safe_load((REPO / "profiles/deterministic-compiler-v1.yaml").read_text())
    validator = yaml.safe_load((REPO / "profiles/fabro-conformance-1b4fb152-v1.yaml").read_text())
    for name, expected in validator["source_hashes"].items():
        if sha(SOURCE / name) != expected:
            raise ValueError(f"Pinned Fabro source differs: {name}")
    validator["executable_sha256"] = sha(BINARY)
    validator = semantic_seal(validator)
    actions, support = [], []
    refs = ["baseline", "external_candidate", "admission"]
    for i, ref in enumerate(refs):
        human = ref == "admission"
        action = {
            "ref": ref,
            "purpose": (
                "Configure live provider and budget; engineering review stays pending"
                if human
                else f"Measure {ref} using frozen native sources and external regression"
            ),
            "type": "human" if human else "deterministic_check",
            "label": "Agent admission pending: provider and spending limit" if human else ref,
            "instance_ids": ids if human else [ids[i]],
            "role": "configuration_owner" if human else "measurement_runner",
            "allowed_inputs": ["measurement-inputs.json", "task-authority.json"],
            "allowed_paths": [str(target), measurement["baseline"], measurement["googletest"]],
            "expected_outputs": []
            if human
            else [f".llm_tmp/{'baseline' if i == 0 else 'external-candidate'}/measurement.json"],
            "data_destinations": ["local:disposable-target"],
            "write_scope": [] if human else [str(target / ".llm_tmp")],
            "tool_profile": "none" if human else "frozen-gcc12-native-gtest-measurement-v1",
            "model_capability": "none",
            "budget": {
                "wall_time_seconds": 420,
                "attempts": 1,
                "tool_calls": 4,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_microunits": 0,
            },
            "completion_predicate": "Expected phase exits and 13 native test counts match"
            if not human
            else "Admission unavailable; external configuration required",
            "evidence_expectation": "Original native output and JSON counts"
            if not human
            else "No agent or engineering decision is admitted by this demonstration",
            "fallible_outcomes": ["failure", "success"] if not human else ["success"],
            "prohibited_authority": [
                "approval",
                "trusted_evidence_collection",
                "automatic_approval",
                "replayed_approval",
            ],
            "support_files": [],
            "origin": origin,
        }
        if not human:
            phase = "baseline" if i == 0 else "external-candidate"
            path = f"commands/{ref}.sh"
            args = [
                str(REPO / ".venv/bin/python"),
                "-",
                phase,
                str(root / "measurement-inputs.json"),
                sha(root / "measurement-inputs.json"),
            ]
            script = "exec " + shlex.join(args) + " <<'SCORE_MEASUREMENT_PY'\n"
            script += (HERE / "measure.py").read_text() + "\nSCORE_MEASUREMENT_PY\n"
            action["command_file"] = path
            action["support_files"] = [path]
            support.append({"path": path, "content": script, "origin": origin})
        actions.append(action)

    def edge(source: str, destination: str, outcome: str | None) -> dict:
        return {
            "source": source,
            "target": destination,
            "type": "failure" if outcome == "failure" else "success",
            "outcome": outcome,
            "condition": None,
            "loop_id": None,
            "origin": origin,
        }

    mapping = semantic_seal(
        {
            "schema_version": 1,
            "id": "someip84-operational-measurement",
            "version": 1,
            "plan_version": 1,
            "compiler_profile": profile["id"],
            "review": {
                "state": "reviewed",
                "reference": {
                    **origin["source_ref"],
                    "scope": "Authorized operational execution; native mapping review pending",
                },
            },
            "rules": [
                {
                    "id": "authorized-operational-demonstration",
                    "instance_ids": ids,
                    "actions": actions,
                }
            ],
            "edges": [
                edge("start", "baseline", None),
                edge("baseline", "external_candidate", "success"),
                edge("baseline", "admission", "failure"),
                edge("external_candidate", "admission", "success"),
                edge("external_candidate", "admission", "failure"),
                edge("admission", "exit", "success"),
            ],
            "loop_policies": [],
            "fan_groups": [],
            "support_files": support,
        }
    )
    selections = {
        "plan": plan,
        "execution_mapping": mapping,
        "compiler_profile": profile,
        "validator_profile": validator,
    }
    for name, value in selections.items():
        if name == "plan":
            write(root / "plan.json", value)
        else:
            (root / f"{name}.yaml").write_text(yaml.safe_dump(value, sort_keys=True))
    request = {
        "schema_version": 1,
        "inputs": {},
        "local_paths": {"output_root": "out", "protected_roots": ["target"]},
    }
    for name, value in selections.items():
        path = "plan.json" if name == "plan" else f"{name}.yaml"
        request["inputs"][name] = {
            "path": path,
            "sha256": sha(root / path),
            "semantic_digest": value["digest"],
        }
    (root / "compile.yaml").write_text(yaml.safe_dump(request, sort_keys=True))
    package = compile_request(root / "compile.yaml", root / "out/package.json")
    write(root / "native-validation.json", package["native_validation"])
    print(f"Prepared factory workflow: {root}", flush=True)
    return root


if __name__ == "__main__":
    prepare()
