"""Offline fabric diagnostics and deterministic catalogue/planning commands."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from score_sw_fabric import __version__


def diagnose(root: Path) -> dict[str, Any]:
    """Check foundation files without executing configuration or external tools."""
    checks: list[dict[str, str]] = []
    for name in ("upstream.lock.yaml", "toolchain.lock.yaml"):
        try:
            data = yaml.safe_load((root / name).read_text(encoding="utf-8"))
            if (
                not isinstance(data, dict)
                or type(data.get("schema_version")) is not int
                or data["schema_version"] != 1
            ):
                raise ValueError("expected a mapping with schema_version: 1")
            checks.append({"path": name, "outcome": "pass"})
        except (OSError, ValueError, yaml.YAMLError) as exc:
            checks.append({"path": name, "outcome": "blocked", "reason": str(exc)})
    return {
        "schema_version": 1,
        "scope": "fabric_foundation_files",
        "outcome": "pass" if all(c["outcome"] == "pass" for c in checks) else "blocked",
        "checks": checks,
        "engineering_readiness": "not_evaluated",
        "runtime_integration": "candidate_only_not_selected",
        "limitations": [
            "Only lock-file readability and envelope versions are checked.",
            "Source compatibility, tool availability, credentials and approvals are not checked.",
        ],
    }


def _command_error(exc: Exception) -> dict[str, Any]:
    def bounded(value: Any) -> str | None:
        return None if value is None else str(value)[:4096]

    return {
        "code": bounded(getattr(exc, "code", "UNEXPECTED_ERROR")),
        "source_ref": bounded(getattr(exc, "source_ref", None)),
        "pointer": bounded(getattr(exc, "pointer", "")),
        "native_id": bounded(getattr(exc, "native_id", None)),
        "message": bounded(exc),
        "required_action": bounded(getattr(exc, "action", "Inspect input and rerun.")),
    }


def _catalogue(args: argparse.Namespace) -> int:
    from score_sw_fabric.catalog.export import seal, write_catalogue
    from score_sw_fabric.catalog.importer import build_catalogue
    from score_sw_fabric.process_source.reader import InputError, IntegrityError, load_manifest

    try:
        manifest = load_manifest(args.manifest)
        catalogue, data = seal(build_catalogue(manifest))
        write_catalogue(args.out, data, manifest, args.manifest)
    except (InputError, IntegrityError) as exc:
        error = _command_error(exc)
        pointer = error["pointer"]
        if error["native_id"] is None and "/needs/" in pointer:
            error["native_id"] = pointer.split("/needs/", 1)[1].split("/", 1)[0]
        if error["source_ref"] is None and "manifest" in locals() and len(manifest.exports) == 1:
            source = next(
                source
                for source in manifest.sources
                if source.source_id == manifest.exports[0].source_id
            )
            error["source_ref"] = {
                "source_id": source.source_id,
                "repository": source.repository,
                "commit": source.commit,
                "export_ref": manifest.exports[0].sha256,
            }
        if args.as_json:
            print(json.dumps(error, sort_keys=True), file=sys.stderr)
        else:
            print(f"{error['code']}: {error['message']} ({error['pointer']})", file=sys.stderr)
        return 2 if isinstance(exc, InputError) else 1
    response = {
        "catalogue_path": str(args.out),
        "digest": catalogue["digest"],
        "entities": len(catalogue["entities"]),
        "engineering_readiness": "not_evaluated",
    }
    if args.as_json:
        print(json.dumps(response, sort_keys=True))
    else:
        print(f"Catalogue: {args.out} ({catalogue['digest']})")
    return 0


def _plan(args: argparse.Namespace) -> int:
    from score_sw_fabric.planning import build_plan
    from score_sw_fabric.planning.export import seal_plan, write_plan
    from score_sw_fabric.planning.reader import load_planning_inputs
    from score_sw_fabric.process_source.reader import InputError, IntegrityError

    try:
        inputs = load_planning_inputs(args.input)
        planning_result, data = seal_plan(build_plan(inputs))
        write_plan(args.out, data, inputs)
    except (InputError, IntegrityError) as exc:
        error = _command_error(exc)
        if args.as_json:
            print(json.dumps(error, sort_keys=True), file=sys.stderr)
        else:
            print(f"{error['code']}: {error['message']} ({error['pointer']})", file=sys.stderr)
        return 2
    response = {
        "plan_path": str(args.out),
        "digest": planning_result["digest"],
        "planning_status": planning_result["planning_status"],
        "instances": len(planning_result["instances"]),
        "findings": len(planning_result["findings"]),
        "plan_kind": "draft",
        "engineering_readiness": "not_evaluated",
    }
    stream = sys.stdout if planning_result["planning_status"] == "complete" else sys.stderr
    if args.as_json:
        print(json.dumps(response, sort_keys=True), file=stream)
    else:
        print(
            f"Draft plan: {args.out} "
            f"({planning_result['planning_status']}, {planning_result['digest']})",
            file=stream,
        )
    return 0 if planning_result["planning_status"] == "complete" else 1


def _workflow(args: argparse.Namespace) -> int:
    from score_sw_fabric.compiler.diff import compare_packages
    from score_sw_fabric.compiler.drift import inspect_drift
    from score_sw_fabric.compiler.models import CompilerSemanticError
    from score_sw_fabric.compiler.package import compile_request, read_package, validate_package
    from score_sw_fabric.compiler.reader import load_compiler_inputs, verify_self_digest
    from score_sw_fabric.compiler.validator import validate_native
    from score_sw_fabric.process_source.reader import InputError, read_json, read_yaml

    try:
        if args.workflow_command == "compile":
            package = compile_request(args.request, args.out)
            result: dict[str, Any] = {
                "package_path": str(args.out),
                "package_identity": package["manifest"]["package_identity"],
                "digest": package["digest"],
                "status": package["compile_report"]["status"],
                "capabilities": package["compile_report"]["capabilities"],
            }
        else:
            profile = read_yaml(args.profile)
            verify_self_digest(profile, "/profile")
            if args.workflow_command == "validate":
                package = read_package(args.package, profile)
                selected_validator = package["manifest"]["validator"]
                if selected_validator["id"] != profile.get("id") or selected_validator[
                    "digest"
                ] != profile.get("digest"):
                    raise InputError(
                        "VALIDATOR_PROFILE_MISMATCH",
                        "Package and selected validator profiles differ",
                    )
                native = validate_native(package["files"], package["entrypoint"], profile)
                result = {
                    **validate_package(package, profile),
                    "native_validation": native,
                    "capabilities": package["compile_report"]["capabilities"],
                }
            elif args.workflow_command == "diff":
                before = read_package(args.before, profile)
                after = read_package(args.after, profile)
                result = compare_packages(before, after, profile)
            else:
                package = read_json(args.package)
                inputs = load_compiler_inputs(args.request) if args.request else None
                result = inspect_drift(package, profile, inputs=inputs)
    except (InputError, CompilerSemanticError) as exc:
        error = _command_error(exc)
        if isinstance(exc, CompilerSemanticError):
            error["findings"] = exc.findings
        if args.as_json:
            print(json.dumps(error, sort_keys=True), file=sys.stderr)
        else:
            print(f"{error['code']}: {error['message']}", file=sys.stderr)
        return 1 if isinstance(exc, CompilerSemanticError) else 2
    if args.as_json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(json.dumps(result, sort_keys=True, indent=2))
    if args.workflow_command in {"diff", "drift"} and not result.get(
        "equivalent", result.get("clean", True)
    ):
        return 1
    return 0


def _artifact(args: argparse.Namespace) -> int:
    from score_sw_fabric.artifacts.diff import compare_artifacts
    from score_sw_fabric.artifacts.drift import inspect_drift
    from score_sw_fabric.artifacts.models import ArtifactSemanticError
    from score_sw_fabric.artifacts.package import (
        candidate_request,
        index_request,
        load_profile,
        read_candidate,
        trace_request,
        validate_candidate,
    )
    from score_sw_fabric.process_source.reader import InputError, read_json

    try:
        command = args.artifact_command
        if command == "index":
            value = index_request(args.request, args.out)
            result: dict[str, Any] = {
                "path": str(args.out),
                "digest": value["digest"],
                "valid": value["valid"],
                "counts": value["counts"],
                "capabilities": value["capabilities"],
            }
            status = 0
        elif command == "candidate":
            value = candidate_request(args.request, args.out)
            result = {
                "path": str(args.out),
                "digest": value["digest"],
                "candidate_identity": value["candidate_identity"],
                "trace_validation": value["trace_validation"],
                "capabilities": value["capabilities"],
            }
            status = 0
        elif command == "trace":
            value, valid = trace_request(args.request, args.out)
            result = {
                "path": str(args.out),
                "digest": value["digest"],
                "status": value["status"],
                "coverage": value["coverage"],
                "findings": value["findings"],
                "capabilities": value["capabilities"],
            }
            status = 0 if valid else 1
        elif command == "validate":
            profile = load_profile(args.profile)
            candidate = read_candidate(args.candidate, profile)
            result = validate_candidate(candidate, profile)
            status = 0
        elif command == "diff":
            profile = load_profile(args.profile)
            before = read_json(args.before)
            after = read_json(args.after)
            if before.get("kind") == "artifact_candidate":
                validate_candidate(before, profile)
            if after.get("kind") == "artifact_candidate":
                validate_candidate(after, profile)
            result = compare_artifacts(before, after)
            status = 0 if result["equivalent"] else 1
        else:
            profile = load_profile(args.profile)
            candidate = read_json(args.candidate)
            result = inspect_drift(candidate, profile, request=args.request)
            status = 0 if result["clean"] else 1
    except (InputError, ArtifactSemanticError) as exc:
        error = _command_error(exc)
        if isinstance(exc, ArtifactSemanticError):
            error["findings"] = exc.findings
        if args.as_json:
            print(json.dumps(error, sort_keys=True), file=sys.stderr)
        else:
            print(f"{error['code']}: {error['message']}", file=sys.stderr)
        return 1 if isinstance(exc, ArtifactSemanticError) else 2
    stream = sys.stdout if status == 0 else sys.stderr
    if args.as_json:
        print(json.dumps(result, sort_keys=True), file=stream)
    else:
        print(json.dumps(result, sort_keys=True, indent=2), file=stream)
    return status


def _assurance(args: argparse.Namespace) -> int:
    from score_sw_fabric.assurance.package import (
        decision_request,
        evidence_request,
        gate_request,
        subject_request,
        verify_assessment,
    )
    from score_sw_fabric.process_source.reader import InputError, read_json

    if args.assurance_command == "verify":
        try:
            result = verify_assessment(read_json(args.assessment), read_json(args.trust_context))
        except InputError as exc:
            error = _command_error(exc)
            if args.as_json:
                print(json.dumps(error, sort_keys=True), file=sys.stderr)
            else:
                print(f"{error['code']}: {error['message']}", file=sys.stderr)
            return 2
        print(json.dumps(result, sort_keys=True, indent=None if args.as_json else 2))
        return 0 if result["reproduced"] else 1

    try:
        if args.assurance_command == "subject":
            record = subject_request(args.request, args.out)
        elif args.assurance_command == "evidence":
            record = evidence_request(args.request, args.out)
        elif args.assurance_command == "decision":
            record = decision_request(args.request, args.out)
        elif args.assurance_command == "gate":
            record = gate_request(args.request, args.out)
        else:
            raise InputError("OPERATION_UNAVAILABLE", "Assurance operation is not implemented")
    except InputError as exc:
        error = _command_error(exc)
        if args.as_json:
            print(json.dumps(error, sort_keys=True), file=sys.stderr)
        else:
            print(f"{error['code']}: {error['message']}", file=sys.stderr)
        return 2
    response = {
        "path": str(args.out),
        "digest": record["digest"],
        "assurance_domain": record.get(
            "assurance_domain", record.get("readable_report", {}).get("assurance_domain")
        ),
        "scope": record.get("scope", record.get("readable_report", {}).get("scope")),
        "engineering_readiness": "not_evaluated",
    }
    if args.assurance_command in {"evidence", "decision"}:
        response["outcome"] = record["outcome"]
        response["reasons"] = sorted(
            {code for item in record["eligibility"] for code in item["reason_codes"]}
        )
    elif args.assurance_command == "gate":
        gate = record["gate_results"][0]
        response["outcome"] = gate["outcome"]
        response["reasons"] = gate["reason_codes"]
    print(json.dumps(response, sort_keys=True, indent=None if args.as_json else 2))
    return 0 if response.get("outcome", "eligible") in {"eligible", "pass"} else 1


RUNTIME_SUMMARY_FIELDS = (
    "intent_id",
    "run_id",
    "version_id",
    "creation_state",
    "start_state",
    "native_status",
    "native_reason",
    "decision",
    "native_action",
    "cancellation",
    "completeness",
    "reason_codes",
    "changed_bindings",
    "next_action",
)


def _runtime(args: argparse.Namespace) -> int:
    from score_sw_fabric.process_source.reader import InputError, read_json
    from score_sw_fabric.runtime import operations
    from score_sw_fabric.runtime.export import verify_export
    from score_sw_fabric.runtime.models import bounded_diagnostic, publish
    from score_sw_fabric.runtime.request import load_request

    def fail(exc: InputError) -> int:
        print(json.dumps(bounded_diagnostic(exc), sort_keys=True), file=sys.stderr)
        return 2

    if args.runtime_command == "verify":
        try:
            result = verify_export(read_json(args.export))
        except InputError as exc:
            return fail(exc)
        status = 0 if result["reproduced"] and result["completeness"] == "complete" else 1
        print(
            json.dumps(result, sort_keys=True, indent=None if args.as_json else 2),
            file=sys.stdout if status == 0 else sys.stderr,
        )
        return status
    handlers = {
        "register": operations.register,
        "run": operations.run,
        "status": operations.status,
        "resume": operations.resume,
        "cancel": operations.cancel,
        "export": operations.export,
    }
    try:
        request = load_request(args.request)
        status, record = handlers[args.runtime_command](request)
        publish(
            args.out,
            record,
            inputs=request.inputs(),
            protected_roots=[*request.protected_roots, request.ledger_root],
        )
    except InputError as exc:
        return fail(exc)
    if "native_status" in record and isinstance(record["native_status"], dict):
        native = record["native_status"]
        record = {
            **record,
            "native_status": native.get("kind"),
            "native_reason": native.get("reason"),
        }
    if record.get("kind") == "runtime_export":
        record = {**record, **record["status"], "run_id": record["binding"]["run_id"]}
    response = {name: record[name] for name in RUNTIME_SUMMARY_FIELDS if name in record}
    response.update(
        {
            "path": str(args.out),
            "kind": record["kind"],
            "digest": record["digest"],
            "engineering_readiness": "not_evaluated",
        }
    )
    print(
        json.dumps(response, sort_keys=True, indent=None if args.as_json else 2),
        file=sys.stdout if status == 0 else sys.stderr,
    )
    return status


AGENT_SUMMARY_FIELDS = ("outcome", "decision", "reasons", "idempotent", "structure", "violations")


def _agent(args: argparse.Namespace) -> int:
    from score_sw_fabric.agents import admission, context, discover, output
    from score_sw_fabric.agents.models import bounded_diagnostic
    from score_sw_fabric.process_source.reader import InputError
    from score_sw_fabric.runtime.models import publish

    handlers = {
        "discover": discover.discover,
        "setup": discover.setup,
        "context": context.build_context,
        "admit": admission.admit,
        "check": output.check,
    }
    try:
        status, record, inputs, protected = handlers[args.agent_command](args.request)
        publish(
            args.out, record, inputs=[args.request.absolute(), *inputs], protected_roots=protected
        )
    except InputError as exc:
        print(json.dumps(bounded_diagnostic(exc), sort_keys=True), file=sys.stderr)
        return 2
    response = {name: record[name] for name in AGENT_SUMMARY_FIELDS if name in record}
    if record["kind"] == "agent_capability_inventory":
        response["servers"] = {item["id"]: item["status"] for item in record["servers"]}
        response["findings"] = sorted(
            {finding["code"] for item in record["servers"] for finding in item["findings"]}
        )
    response.update(
        {
            "path": str(args.out),
            "kind": record["kind"],
            "digest": record["digest"],
            "engineering_readiness": "not_evaluated",
        }
    )
    print(
        json.dumps(response, sort_keys=True, indent=None if args.as_json else 2),
        file=sys.stdout if status == 0 else sys.stderr,
    )
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="check foundation lock envelopes offline")
    doctor.add_argument("--root", type=Path, default=Path.cwd())
    doctor.add_argument("--json", action="store_true", dest="as_json")
    catalog = commands.add_parser("catalog", help="native source catalogue")
    catalog_commands = catalog.add_subparsers(dest="catalog_command", required=True)
    export = catalog_commands.add_parser("export", help="import and seal a pinned native export")
    export.add_argument("--manifest", type=Path, required=True)
    export.add_argument("--out", type=Path, required=True)
    export.add_argument("--json", action="store_true", dest="as_json")
    plan = commands.add_parser("plan", help="derive a deterministic draft work-product plan")
    plan.add_argument("--input", type=Path, required=True)
    plan.add_argument("--out", type=Path, required=True)
    plan.add_argument("--json", action="store_true", dest="as_json")
    artifact = commands.add_parser("artifact", help="index and inspect native artifacts")
    artifact_commands = artifact.add_subparsers(dest="artifact_command", required=True)
    for name in ("index", "candidate", "trace"):
        artifact_request = artifact_commands.add_parser(name, help=f"{name} native artifacts")
        artifact_request.add_argument("--request", type=Path, required=True)
        artifact_request.add_argument("--out", type=Path, required=True)
        artifact_request.add_argument("--json", action="store_true", dest="as_json")
    artifact_validate = artifact_commands.add_parser(
        "validate", help="validate a sealed artifact candidate"
    )
    artifact_validate.add_argument("--candidate", type=Path, required=True)
    artifact_validate.add_argument("--profile", type=Path, required=True)
    artifact_validate.add_argument("--json", action="store_true", dest="as_json")
    artifact_diff = artifact_commands.add_parser("diff", help="compare sealed artifact records")
    artifact_diff.add_argument("--before", type=Path, required=True)
    artifact_diff.add_argument("--after", type=Path, required=True)
    artifact_diff.add_argument("--profile", type=Path, required=True)
    artifact_diff.add_argument("--json", action="store_true", dest="as_json")
    artifact_drift = artifact_commands.add_parser("drift", help="inspect artifact candidate drift")
    artifact_drift.add_argument("--candidate", type=Path, required=True)
    artifact_drift.add_argument("--profile", type=Path, required=True)
    artifact_drift.add_argument("--request", type=Path)
    artifact_drift.add_argument("--json", action="store_true", dest="as_json")
    workflow = commands.add_parser("workflow", help="compile and inspect workflow packages")
    workflow_commands = workflow.add_subparsers(dest="workflow_command", required=True)
    compile_command = workflow_commands.add_parser("compile", help="compile a reviewed workflow")
    compile_command.add_argument("--request", type=Path, required=True)
    compile_command.add_argument("--out", type=Path, required=True)
    compile_command.add_argument("--json", action="store_true", dest="as_json")
    validate_command = workflow_commands.add_parser("validate", help="validate a sealed package")
    validate_command.add_argument("--package", type=Path, required=True)
    validate_command.add_argument(
        "--validator", "--profile", dest="profile", type=Path, required=True
    )
    validate_command.add_argument("--json", action="store_true", dest="as_json")
    diff_command = workflow_commands.add_parser("diff", help="compare two sealed packages")
    diff_command.add_argument("--before", type=Path, required=True)
    diff_command.add_argument("--after", type=Path, required=True)
    diff_command.add_argument("--profile", type=Path, required=True)
    diff_command.add_argument("--json", action="store_true", dest="as_json")
    drift_command = workflow_commands.add_parser(
        "drift", help="inspect package integrity and drift"
    )
    drift_command.add_argument("--package", type=Path, required=True)
    drift_command.add_argument("--profile", type=Path, required=True)
    drift_command.add_argument("--request", type=Path)
    drift_command.add_argument("--json", action="store_true", dest="as_json")
    assurance = commands.add_parser("assurance", help="inspect scoped assurance records")
    assurance_commands = assurance.add_subparsers(dest="assurance_command", required=True)
    assurance_subject = assurance_commands.add_parser(
        "subject", help="seal an exact 002/004 subject"
    )
    assurance_subject.add_argument("--request", type=Path, required=True)
    assurance_subject.add_argument("--out", type=Path, required=True)
    assurance_subject.add_argument("--json", action="store_true", dest="as_json")
    assurance_evidence = assurance_commands.add_parser("evidence", help="classify signed evidence")
    assurance_evidence.add_argument("--request", type=Path, required=True)
    assurance_evidence.add_argument("--out", type=Path, required=True)
    assurance_evidence.add_argument("--json", action="store_true", dest="as_json")
    assurance_decision = assurance_commands.add_parser("decision", help="classify human decisions")
    assurance_decision.add_argument("--request", type=Path, required=True)
    assurance_decision.add_argument("--out", type=Path, required=True)
    assurance_decision.add_argument("--json", action="store_true", dest="as_json")
    assurance_gate = assurance_commands.add_parser("gate", help="evaluate a scoped gate")
    assurance_gate.add_argument("--request", type=Path, required=True)
    assurance_gate.add_argument("--out", type=Path, required=True)
    assurance_gate.add_argument("--json", action="store_true", dest="as_json")
    assurance_verify = assurance_commands.add_parser("verify", help="replay a portable assessment")
    assurance_verify.add_argument("--assessment", type=Path, required=True)
    assurance_verify.add_argument("--trust-context", type=Path, required=True)
    assurance_verify.add_argument("--json", action="store_true", dest="as_json")
    runtime = commands.add_parser("runtime", help="operate a selected disposable Fabro runtime")
    runtime_commands = runtime.add_subparsers(dest="runtime_command", required=True)
    for name, help_text in (
        ("register", "register a sealed 003 package version"),
        ("run", "create and start one run for an intent"),
        ("status", "read native run status without implying readiness"),
        ("resume", "admit and request same-run checkpoint continuation"),
        ("cancel", "request native cancellation and observe terminal state"),
        ("export", "build a portable historical run record"),
    ):
        runtime_request = runtime_commands.add_parser(name, help=help_text)
        runtime_request.add_argument("--request", type=Path, required=True)
        runtime_request.add_argument("--out", type=Path, required=True)
        runtime_request.add_argument("--json", action="store_true", dest="as_json")
    runtime_verify = runtime_commands.add_parser("verify", help="verify a run export offline")
    runtime_verify.add_argument("--export", type=Path, required=True)
    runtime_verify.add_argument("--json", action="store_true", dest="as_json")
    agent = commands.add_parser("agent", help="bounded agent context, admission and checks")
    agent_commands = agent.add_subparsers(dest="agent_command", required=True)
    for name, help_text in (
        ("discover", "observe pinned context servers from a disposable copy"),
        ("setup", "run one explicit, idempotent context setup operation"),
        ("context", "build a baseline-bound role context bundle"),
        ("admit", "check model capability, fallback and budget before a call"),
        ("check", "validate a role result against its write scope and real changes"),
    ):
        agent_request = agent_commands.add_parser(name, help=help_text)
        agent_request.add_argument("--request", type=Path, required=True)
        agent_request.add_argument("--out", type=Path, required=True)
        agent_request.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    if args.command == "agent":
        return _agent(args)
    if args.command == "runtime":
        return _runtime(args)
    if args.command == "assurance":
        return _assurance(args)
    if args.command == "catalog":
        return _catalogue(args)
    if args.command == "plan":
        return _plan(args)
    if args.command == "artifact":
        return _artifact(args)
    if args.command == "workflow":
        return _workflow(args)
    result = diagnose(args.root)
    if args.as_json:
        print(json.dumps(result, sort_keys=True, indent=2))
    else:
        print(f"Foundation files: {result['outcome']}")
        for check in result["checks"]:
            print(f"  {check['path']}: {check['outcome']} {check.get('reason', '')}".rstrip())
        print(
            "Engineering readiness: not_evaluated; runtime integration: candidate_only_not_selected"
        )
        for limitation in result["limitations"]:
            print(f"  {limitation}")
    return 0 if result["outcome"] == "pass" else 2


if __name__ == "__main__":
    sys.exit(main())
