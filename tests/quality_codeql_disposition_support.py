"""Synthetic imported CodeQL finding and measured prerequisite context, without queries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from score_sw_fabric.assurance.models import digest, seal
from score_sw_fabric.quality import codeql, imports
from tests.quality_codeql_support import selected, write
from tests.quality_disposition_support import selection
from tests.quality_import_support import identity, write_json
from tests.quality_import_support import selection as imported_selection
from tests.quality_support import ref


def controls(tmp: Path, *, mismatch: str | None = None) -> tuple[Path, Path, Path]:
    current = selected(tmp, "run")
    write(
        tmp / "fixture-pack/.codeql/libraries/codeql/cpp-all/5.0.0/qlpack.yml",
        {"name": "codeql/cpp-all", "version": "5.0.0"},
    )
    original_request = imported_selection(tmp)
    native_request = json.loads(current.read_bytes())
    imported = json.loads(original_request.read_bytes())
    baseline_path = Path(imported["baseline"]["path"])
    baseline = json.loads(baseline_path.read_bytes())
    (tmp / "component/check.cpp").write_bytes((tmp / "source/check.cpp").read_bytes())
    native_request.update(
        component=baseline["component"],
        files=baseline["files"],
        expected_units=baseline["expected_units"],
    )
    write(current, native_request)
    _, inspected, _, _ = codeql.run(current)
    pack = inspected["pack_inspection"]
    config = inspected["configuration"]["effective"]
    ident = identity()
    ident.update(
        tool_sha256=inspected["toolchain"]["tool"]["sha256"],
        config_sha256=ref(Path(native_request["config"]["path"]))["sha256"],
        query_pack={
            "name": pack["identity"]["name"],
            "version": pack["identity"]["version"],
            "sha256": pack["manifest_digest"],
        },
        suite={
            "name": config["suite"],
            "sha256": next(f["sha256"] for f in pack["manifest"] if f["path"] == config["suite"]),
        },
        libraries=[{k: row[k] for k in ("name", "version", "sha256")} for row in pack["libraries"]],
    )
    if mismatch in {"tool", "config"}:
        ident["tool_sha256" if mismatch == "tool" else "config_sha256"] = "0" * 64
    elif mismatch in {"pack", "suite"}:
        ident["query_pack" if mismatch == "pack" else "suite"]["sha256"] = "0" * 64
    elif mismatch == "library":
        ident["libraries"][0]["sha256"] = "0" * 64
    baseline["identities"] = [ident]
    imported["baseline"] = write_json(baseline_path, seal(baseline))
    for artifact in imported["artifacts"]:
        artifact["bindings"]["identity_digest"] = digest(ident)
        if artifact["format"] == "sarif-2.1.0":
            native_path = Path(artifact["ref"]["path"])
            native = json.loads(native_path.read_bytes())
            native["runs"][0]["tool"]["extensions"] = [
                {"name": row["name"], "semanticVersion": row["version"]}
                for row in [ident["query_pack"], *ident["libraries"]]
            ]
            artifact["ref"] = write_json(native_path, native)
    manifest_path = Path(imported["extraction"]["path"])
    manifest = json.loads(manifest_path.read_bytes())
    manifest["observations"][0]["identity_digest"] = digest(ident)
    imported["extraction"] = write_json(manifest_path, seal(manifest))
    write_json(original_request, imported)
    _, origin, _, _ = imports.import_outputs(original_request)
    assert origin["findings"]
    disposition = selection(tmp, origin, current, "codeql")
    record = json.loads(disposition.read_bytes())
    record["kind"] = "quality_codeql_disposition_request"
    write_json(disposition, record)
    return disposition, original_request, current


def packet_request(
    tmp: Path, disposition: Path, original_request: Path, review: dict[str, Any]
) -> Path:
    imported_request = json.loads(original_request.read_bytes())
    _, imported, _, _ = imports.import_outputs(original_request)
    notice = tmp / "NOTICE.txt"
    notice.write_text("Synthetic test identities only; no engineering acceptance.\n")
    path = tmp / "packet.json"
    write_json(
        path,
        {
            "schema_version": 1,
            "kind": "quality_packet_request",
            "profile": imported_request["profile"],
            "coverage": None,
            "analyses": [
                {
                    "request": ref(original_request),
                    "report": write_json(tmp / "import.json", imported),
                }
            ],
            "dispositions": [
                {
                    "request": ref(disposition),
                    "review": write_json(tmp / "review.json", review),
                    "decision": None,
                }
            ],
            "source_snapshots": [
                {
                    "baseline_digest": imported["baseline"]["full_digest"],
                    "root": str(tmp / "source"),
                },
                {
                    "baseline_digest": review["current_baseline"]["full_digest"],
                    "root": str(tmp / "component"),
                },
            ],
            "notices": [
                {
                    "id": "fixture-notice",
                    "license": "synthetic fixture",
                    "notice": "Test only",
                    "applies_to": [
                        "tool:codeql",
                        "native:scan_config",
                        "native:report_patch",
                        "source:codeql-coding-standards",
                        *("native:" + s["id"] for s in imported["profile"]["native_sources"]),
                    ],
                    "ref": ref(notice),
                }
            ],
            "protected_roots": [],
        },
    )
    return path
