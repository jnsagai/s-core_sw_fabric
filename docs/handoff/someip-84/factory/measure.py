"""Fixed native measurement payload; Fabro invokes this in a disposable target.

This validates an external candidate. It neither implements through an agent nor
provides trusted engineering evidence. Source and test notices stay in the copies.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_tree(root: Path, manifest: dict) -> None:
    for entry in manifest["files"]:
        path = root / entry["path"]
        data = os.readlink(path).encode() if entry["mode"] == "120000" else path.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if blob != entry["sha"] or len(data) != entry["size"]:
            raise ValueError(f"Source drift: {entry['path']}")


def main() -> None:
    phase, raw_inputs, expected = sys.argv[1:]
    if phase not in {"baseline", "external-candidate"}:
        raise ValueError("Unsupported measurement phase")
    inputs_path = Path(raw_inputs)
    if digest(inputs_path) != expected:
        raise ValueError("Measurement inputs changed")
    inputs = json.loads(inputs_path.read_bytes())
    target = Path(inputs["target"]).resolve(strict=True)
    if not target.is_relative_to(Path(inputs["disposable_root"]).resolve(strict=True)):
        raise ValueError("Target is not disposable")
    for item in inputs["controls"]:
        if digest(Path(item["path"])) != item["sha256"]:
            raise ValueError(f"Control drift: {item['path']}")
    source = Path(inputs["baseline"])
    gtest = Path(inputs["googletest"])
    source_manifest = json.loads(Path(inputs["source_manifest"]).read_bytes())
    gtest_manifest = json.loads(Path(inputs["googletest_manifest"]).read_bytes())
    verify_tree(source, source_manifest)
    verify_tree(gtest, gtest_manifest)
    out = target / ".llm_tmp" / phase
    out.mkdir(parents=True, exist_ok=False)
    work = out / "source"
    shutil.copytree(source, work, symlinks=True)

    def run(name: str, command: list[str], expected_exit: int) -> None:
        with (out / f"{name}.stdout").open("wb") as stdout:
            with (out / f"{name}.stderr").open("wb") as stderr:
                result = subprocess.run(
                    command, cwd=work, stdout=stdout, stderr=stderr, timeout=180, check=False
                )
        (out / f"{name}.json").write_text(
            json.dumps({"argv": command, "exit_code": result.returncode}, indent=2) + "\n"
        )
        if result.returncode != expected_exit:
            raise ValueError(f"{name}: exit {result.returncode}, expected {expected_exit}")

    candidates = json.loads(Path(inputs["candidate_files"]).read_bytes())
    if phase == "external-candidate":
        run(
            "apply-external-patch",
            [inputs["patch_tool"], "--batch", "-p1", "-i", inputs["patch"]],
            0,
        )
        for name, identity in candidates.items():
            if digest(work / name) != identity["sha256"]:
                raise ValueError(f"External candidate differs: {name}")
    else:
        # The regression is an external test input; production source stays at the baseline.
        test = "score/socom/test/unit/service_identifier_tests.cpp"
        payload = Path(inputs["candidate_root"]) / test
        if digest(payload) != candidates[test]["sha256"]:
            raise ValueError("External regression test changed")
        shutil.copyfile(payload, work / test)

    exe = out / "service-identifier-tests"
    run(
        "compile",
        [
            inputs["compiler"],
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pthread",
            "-I.",
            f"-I{gtest}/googletest/include",
            f"-I{gtest}/googletest",
            "score/socom/impl/service_identifier.cpp",
            "score/socom/impl/string_registry.cpp",
            "score/socom/test/unit/service_identifier_tests.cpp",
            f"{gtest}/googletest/src/gtest-all.cc",
            f"{gtest}/googletest/src/gtest_main.cc",
            "-o",
            str(exe),
        ],
        0,
    )
    expected_exit, failures = (1, 7) if phase == "baseline" else (0, 0)
    run("regression", [str(exe), f"--gtest_output=json:{out}/tests.json"], expected_exit)
    result = json.loads((out / "tests.json").read_bytes())
    if result["tests"] != 13 or result["failures"] != failures or result["disabled"] != 0:
        raise ValueError("Unexpected native test counts")
    verify_tree(source, source_manifest)
    verify_tree(gtest, gtest_manifest)
    if digest(inputs_path) != expected:
        raise ValueError("Measurement inputs changed during execution")
    for item in inputs["controls"]:
        if digest(Path(item["path"])) != item["sha256"]:
            raise ValueError(f"Control changed during execution: {item['path']}")
    record = {
        "phase": phase,
        "initiator": "Fabro native command stage",
        "inputs_sha256": expected,
        "source_commit": source_manifest["commit"],
        "compiler": inputs["compiler"],
        "exit_code": expected_exit,
        "tests": result["tests"],
        "failures": result["failures"],
        "engineering_acceptance": "pending",
        "agent_implementation": "not_performed",
        "outputs": {p.name: digest(p) for p in sorted(out.iterdir()) if p.is_file() and p != exe},
    }
    (out / "measurement.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
