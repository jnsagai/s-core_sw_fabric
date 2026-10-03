"""Fixed host collectors; results remain local measurements, never engineering approval."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import time
from pathlib import Path

from isolate_docker import docker
from measure import digest, verify_tree
from obligations import CHECKS

GCC = "/usr/bin/x86_64-linux-gnu-g++-12"
LLVM = Path("/home/jefferson/.local/share/s-core-tools/llvm-19.1.7/usr/lib/llvm-19/bin")
CODEQL = "/home/jefferson/.local/share/s-core-tools/codeql-2.21.4/codeql/codeql"
PACK = "/home/jefferson/.local/share/s-core-tools/codeql-coding-standards-2.61.0"
BAZEL = "/tmp/s-core-001/bin/bazel"
REUSE = "/tmp/score-someip84-obligation-tools/bin/reuse"
PRECOMMIT = "/tmp/score-someip84-obligation-tools/bin/pre-commit"
FORMAT = "/tmp/score-someip84-obligation-tools/bin/clang-format"


def collector_identity() -> dict[str, str | None]:
    paths = [
        str(Path(__file__).resolve()),
        str(Path(__file__).with_name("obligations.py")),
        GCC,
        str(LLVM / "clang++"),
        str(LLVM / "clang-tidy"),
        CODEQL,
        PACK + "/qlpack.yml",
        PACK + "/codeql-suites/misra-cpp-default.qls",
        BAZEL,
        REUSE,
        PRECOMMIT,
        FORMAT,
        "/usr/bin/gcov-12",
        "/usr/bin/gcovr",
        "/usr/bin/cppcheck",
        "/tmp/score-someip84-obligation-tools/usr/bin/valgrind",
        "/tmp/score-someip84-obligation-tools/bin/gitleaks",
    ]
    return {p: digest(Path(p)) if Path(p).is_file() else None for p in paths}


def source_identity(source: Path) -> dict[str, str]:
    return {
        str(p.relative_to(source)): digest(p)
        for p in sorted((source / "score").rglob("*"))
        if p.is_file() and not p.is_symlink()
    }


def snapshot(root: Path, policy: dict, out: Path) -> tuple[Path, str]:
    run = (root / "native-run-id").read_text().strip()
    if not re.fullmatch(r"[0-9A-HJKMNP-TV-Z]{26}", run):
        raise ValueError("Invalid native run binding")
    ids = docker("ps", "--filter", "label=petri.run=" + run, "--format", "{{.ID}}").split()
    if len(ids) != 1:
        raise ValueError("Expected one owned live container")
    record = json.loads(docker("inspect", ids[0]))[0]
    if (
        record["Image"] != policy["image_id"]
        or record["NetworkSettings"]["Networks"]
        or record["Config"]["Labels"].get("petri.run") != run
    ):
        raise ValueError("Owned container identity/network mismatch")
    source = out / "source"
    source.mkdir()
    docker("cp", ids[0] + ":/workspace/.", str(source))
    inputs = json.loads((root / "measurement-inputs.json").read_text())
    verify_tree(Path(inputs["baseline"]), json.loads(Path(inputs["source_manifest"]).read_text()))
    verify_tree(
        Path(inputs["googletest"]), json.loads(Path(inputs["googletest_manifest"]).read_text())
    )
    for item in inputs["controls"]:
        if digest(Path(item["path"])) != item["sha256"]:
            raise ValueError("Frozen measurement input changed")
    original = root / "target"
    paths = {
        str(p.relative_to(tree))
        for tree in (original, source)
        for p in tree.rglob("*")
        if p.is_file() or p.is_symlink()
    }
    for relative in paths:
        if relative.startswith((".llm_tmp/overnight/", ".git/")):
            continue
        a, b = original / relative, source / relative
        same = (a.is_symlink() and b.is_symlink() and os.readlink(a) == os.readlink(b)) or (
            not a.is_symlink()
            and not b.is_symlink()
            and a.is_file()
            and b.is_file()
            and digest(a) == digest(b)
            and (a.stat().st_mode & 0o777) == (b.stat().st_mode & 0o777)
        )
        if not same and "/workspace/" + relative not in policy["source_write_paths"]:
            raise ValueError("Out-of-scope source change: " + relative)
    return source, ids[0]


class Commands:
    def __init__(self, root: Path, out: Path, source: Path, deadline: float):
        self.out, self.source, self.deadline = out, source, deadline
        self.records: list[dict] = []
        self.env = {
            "PATH": (
                "/tmp/score-someip84-obligation-tools/bin:/tmp/s-core-001/bin:/usr/loca"
                "l/bin:/usr/bin:/bin"
            ),
            "HOME": str(root / "tool-home"),
            "TMPDIR": str(root / "tool-tmp"),
            "BAZELISK_HOME": str(root / "bazelisk"),
            "USE_BAZEL_VERSION": "8.6.0",
            "PRE_COMMIT_HOME": str(root / "precommit-cache"),
            "XDG_CACHE_HOME": str(root / "tool-cache"),
            "LANG": "C.UTF-8",
            "LD_LIBRARY_PATH": (
                "/home/jefferson/.local/share/s-core-tools/llvm-19.1.7/usr/lib/x86_64-linux-gnu"
            ),
            "VALGRIND_LIB": "/tmp/score-someip84-obligation-tools/usr/libexec/valgrind",
        }
        for key in ("HOME", "TMPDIR", "BAZELISK_HOME", "XDG_CACHE_HOME"):
            Path(self.env[key]).mkdir(parents=True, exist_ok=True)

    def run(self, label: str, argv: list[str], seconds: int = 240) -> int:
        allowed = max(0, min(seconds, int(self.deadline - time.time() - 10)))
        rec = {
            "label": label,
            "argv": argv,
            "cwd": str(self.source),
            "environment": dict(self.env),
            "timeout_seconds": allowed,
        }
        stdout, stderr = self.out / (label + ".stdout"), self.out / (label + ".stderr")
        code = 124
        if allowed < 1:
            rec["reason"] = "Collection time allowance exhausted"
        else:
            try:
                with stdout.open("wb") as o, stderr.open("wb") as e:
                    child = subprocess.Popen(
                        argv,
                        cwd=self.source,
                        env=self.env,
                        stdout=o,
                        stderr=e,
                        start_new_session=True,
                    )
                    try:
                        code = child.wait(timeout=allowed)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGTERM)
                        try:
                            child.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            os.killpg(child.pid, signal.SIGKILL)
                            child.wait(timeout=3)
                        rec["reason"] = "Command timed out; owned process group stopped"
            except OSError as error:
                code = 127
                rec["reason"] = str(error)
        rec["exit_code"] = code
        self.records.append(rec)
        (self.out / (label + ".command.json")).write_text(json.dumps(rec, indent=2) + "\n")
        return code


def compile_args(source: Path, exe: Path, compiler: str = GCC) -> list[str]:
    gtest = source / ".llm_tmp/googletest/googletest"
    # GoogleTest is a separately verified frozen input, provisioned below.
    return [
        compiler,
        "-std=c++17",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-pthread",
        "-I.",
        "-I" + str(gtest / "include"),
        "-I" + str(gtest),
        "score/socom/impl/service_identifier.cpp",
        "score/socom/impl/string_registry.cpp",
        "score/socom/test/unit/service_identifier_tests.cpp",
        str(gtest / "src/gtest-all.cc"),
        str(gtest / "src/gtest_main.cc"),
        "-o",
        str(exe),
    ]


def bazel(c: Commands, root: Path, label: str, operation: str, args: list[str], seconds=780):
    (c.source / ".bazel_config").write_text("host\n")
    return c.run(
        label,
        [
            BAZEL,
            "--batch",
            "--output_user_root=" + str(root / "bazel-cache"),
            operation,
            *([] if operation == "mod" else ["--jobs=2"]),
            *args,
        ],
        seconds,
    )


def execute(check: str, c: Commands, root: Path, result: dict) -> None:
    source, out = c.source, c.out
    if check == "compiler_diagnostics":
        for name, compiler in (("gcc", GCC), ("clang", str(LLVM / "clang++"))):
            exe = out / name
            if c.run(name + "-compile", compile_args(source, exe, compiler)) == 0:
                c.run(
                    name + "-tests",
                    [str(exe), "--gtest_output=json:" + str(out / (name + "-tests.json"))],
                )
        result["limits"] = [
            "Focused executable only; GCC 12.3 / Clang 19 differ from native toolchain pins"
        ]
    elif check in {"focused_coverage", "focused_asan_lsan", "focused_tsan"}:
        exe = out / "focused"
        argv = compile_args(source, exe)
        flags = {
            "focused_coverage": ["--coverage", "-O0", "-g"],
            "focused_asan_lsan": [
                "-fsanitize=address,leak,undefined",
                "-fno-sanitize-recover=all",
                "-g",
            ],
            "focused_tsan": ["-fsanitize=thread", "-g"],
        }[check]
        if c.run("compile", argv + flags) == 0:
            c.env.update(
                ASAN_OPTIONS="detect_leaks=1:halt_on_error=1", UBSAN_OPTIONS="halt_on_error=1"
            )
            c.run("tests", [str(exe), "--gtest_output=json:" + str(out / "tests.json")])
            if check == "focused_coverage":
                c.run(
                    "gcovr",
                    [
                        "/usr/bin/gcovr",
                        "--root",
                        str(source),
                        "--filter",
                        r"score/socom/impl/",
                        "--object-directory",
                        str(out),
                        "--gcov-executable",
                        "/usr/bin/gcov-12",
                        "--json",
                        str(out / "coverage.json"),
                        "--json-summary",
                        str(out / "coverage-summary.json"),
                        "--print-summary",
                    ],
                )
                coverage = out / "coverage.json"
                if coverage.exists():
                    data = json.loads(coverage.read_text())
                    summary = json.loads((out / "coverage-summary.json").read_text())
                    result["coverage"] = {
                        "files": [f["file"] for f in data.get("files", [])],
                        "production_filter": "score/socom/impl/",
                        "tests_and_third_party_excluded": True,
                        "line_total": summary["line_total"],
                        "line_covered": summary["line_covered"],
                        "branch_total": summary["branch_total"],
                        "branch_covered": summary["branch_covered"],
                        "line_percent": summary["line_percent"],
                        "branch_percent": summary["branch_percent"],
                        "platform_goals": {"QM": 85, "safety": 100},
                        "safety_class": "unknown_requires_authorized_selection",
                        "complete_target_scope": False,
                    }
                    if not summary["line_total"]:
                        result["blockers"].append("Empty coverage scope")
        result["limits"] = [
            "Focused identifier executable; full native runtime scope measured separately"
        ]
    elif check == "focused_clang_tidy":
        tidy = str(LLVM / "clang-tidy")
        config = source / ".clang-tidy"
        valid = c.run("native-config", [tidy, "--verify-config", "--config-file=" + str(config)])
        if valid == 0:
            for index, unit in enumerate(("service_identifier.cpp", "string_registry.cpp")):
                c.run(
                    "tidy-" + str(index),
                    [
                        tidy,
                        "score/socom/impl/" + unit,
                        "--config-file=" + str(config),
                        "--export-fixes=" + str(out / (unit + ".yaml")),
                        "--",
                        "-std=c++17",
                        "-I.",
                    ],
                )
        else:
            result["blockers"].append(
                "Native analyzer configuration incompatible; no replacement called MISRA"
            )
    elif check == "focused_cppcheck":
        c.run(
            "cppcheck",
            [
                "/usr/bin/cppcheck",
                "--std=c++17",
                "--enable=warning,style,performance,portability",
                "--xml",
                "--xml-version=2",
                "--error-exitcode=2",
                "-I.",
                "score/socom/impl/service_identifier.cpp",
                "score/socom/impl/string_registry.cpp",
            ],
        )
        result["limits"] = ["Optional complementary checks; no inferred MISRA rule coverage"]
    elif check == "focused_memcheck":
        exe = out / "memcheck-tests"
        if c.run("compile", compile_args(source, exe) + ["-g"]) == 0:
            c.run(
                "memcheck",
                [
                    "/tmp/score-someip84-obligation-tools/usr/bin/valgrind",
                    "--tool=memcheck",
                    "--leak-check=full",
                    "--error-exitcode=42",
                    "--xml=yes",
                    "--xml-file=" + str(out / "memcheck.xml"),
                    str(exe),
                ],
            )
        result["limits"] = ["Optional complementary focused memory analysis"]
    elif check == "secret_dependency_checks":
        c.run(
            "gitleaks",
            [
                "/tmp/score-someip84-obligation-tools/bin/gitleaks",
                "dir",
                str(source),
                "--redact=100",
                "--report-format=json",
                "--report-path=" + str(out / "secret-findings.json"),
            ],
        )
        modules = source / "MODULE.bazel"
        content = modules.read_text()
        result["dependency_inventory"] = re.findall(
            r'bazel_dep\s*\([^)]*name\s*=\s*"([^\"]+)"[^)]*version\s*=\s*"([^\"]+)"',
            content,
            re.S,
        )
        result["lock_sha256"] = digest(source / "MODULE.bazel.lock")
        result["blockers"].append(
            "No adopted vulnerability database/ecosystem mapping or GitHub dependency scan "
            "receipt; dependency inventory is not a vulnerability scan"
        )
    elif check.startswith("native_") or check == "cross_compilation":
        # Keep one collector-owned workspace so Bazel can reuse its outputs.
        # Each native suite is still bound to the freshly captured source hashes.
        native_source = root / "native-workspace"
        if not native_source.exists():
            shutil.copytree(source, native_source, symlinks=True)
        else:
            policy = json.loads((root / "overnight-policy.json").read_text())
            for path in policy["source_write_paths"]:
                relative = path.removeprefix("/workspace/")
                if (source / relative).exists():
                    shutil.copyfile(source / relative, native_source / relative)
                elif (native_source / relative).exists():
                    (native_source / relative).unlink()
        if source_identity(native_source) != source_identity(source):
            raise ValueError("Collector native workspace source drift")
        result["captured_source_path"] = str(source)
        result["native_workspace"] = str(native_source)
        c.source = native_source
        source = native_source
        suites = {
            "native_build": [("build", "build", ["//..."], 780)],
            "native_tests": [("tests", "test", ["//...", "--build_tests_only"], 780)],
            "native_coverage": [
                ("coverage", "coverage", ["//...", "--build_tests_only"], 650),
                (
                    "report",
                    "run",
                    [
                        "@score_coverage//:generate_coverage_html",
                        "--",
                        "--archive-dir",
                        str(out / "coverage"),
                    ],
                    200,
                ),
            ],
            "native_lint": [
                ("clang-tidy", "run", ["//:clang-tidy.check"], 420),
                ("ruff", "run", ["//:ruff.check"], 360),
            ],
            "native_sanitizers": [
                (
                    "sanitizers",
                    "test",
                    [
                        "//score/...",
                        "//tests/...",
                        "--build_tests_only",
                        "--features=asan",
                        "--features=lsan",
                        "--features=ubsan_clang",
                    ],
                    780,
                )
            ],
            "native_tsan": [
                (
                    "tsan",
                    "test",
                    ["//score/...", "//tests/...", "--build_tests_only", "--features=tsan"],
                    780,
                )
            ],
            "native_integration": [
                (
                    "qemu",
                    "test",
                    ["--config=qemu-integration", "//quality/...", "//tests/integration_test/..."],
                    780,
                )
            ],
            "native_performance": [
                (
                    "benchmarks",
                    "test",
                    ["--config=perf-tests", "//tests/benchmarks/...", "--build_tests_only"],
                    300,
                ),
                (
                    "profiling",
                    "test",
                    [
                        "--config=perf-tests-flamegraphs",
                        "//tests/benchmarks/...",
                        "--build_tests_only",
                    ],
                    200,
                ),
            ],
            "cross_compilation": [
                ("x86", "build", ["--config=x86_64-linux", "//score/...", "//tests/..."], 390),
                ("arm", "build", ["--config=aarch64-linux", "//score/...", "//tests/..."], 390),
            ],
            "native_docs": [("docs", "run", ["//:docs"], 480)],
            "native_traceability": [
                ("unit-component-tests", "test", ["//:unit_tests", "//:component_tests"], 200),
                ("docs", "run", ["//:docs"], 200),
                (
                    "traceability",
                    "run",
                    [
                        "//:traceability_gate",
                        "--",
                        "--metrics-json",
                        str(source / "_build/metrics.json"),
                        "--need-type=comp_req",
                    ],
                    100,
                ),
            ],
        }
        if check == "native_coverage":
            c.env["COVERAGE_THRESHOLD"] = "73"
            result["limits"] = [
                "Repository CI threshold 73 is not platform 85/100 line-and-branch acceptance"
            ]
        if check == "native_integration":
            result["prerequisites"] = {
                "kvm_exists": Path("/dev/kvm").exists(),
                "qemu": shutil.which("qemu-system-x86_64"),
            }
        if check == "cross_compilation":
            result["blockers"].append(
                "QNX SDK entitlement and target execution not configured; no credential acquired"
            )
        for label, operation, args, timeout in suites[check]:
            bazel(c, root, label, operation, args, timeout)
    elif check == "format_precommit":
        # Recreate collector-owned Git metadata; never run checkpoint hooks.
        shutil.rmtree(source / ".git", ignore_errors=True)
        c.run("git-init", ["/usr/bin/git", "-c", "core.hooksPath=/dev/null", "init"])
        c.run("git-add", ["/usr/bin/git", "-c", "core.hooksPath=/dev/null", "add", "--all"])
        bazel(c, root, "format", "test", ["//:format.check"], 180)
        c.run("precommit", [PRECOMMIT, "run", "--all-files"], 180)
        c.run("reuse", [REUSE, "lint"], 90)
        bazel(c, root, "module-tidy", "mod", ["tidy"], 40)
        bazel(c, root, "lockfile", "mod", ["deps", "--lockfile_mode=error"], 40)
        result["limits"] = [
            "Formatting/pre-commit mutations occur only in this disposable collector copy"
        ]
    elif check in {"codeql_security", "codeql_misra"}:
        # Public open-source analysis authorized by the owner; no report upload.
        db = out / "database"
        build = out / "codeql-build.sh"
        exe = out / "codeql-tests"
        build.write_text(
            "#!/bin/sh\nset -eu\n"
            + shlex.join(compile_args(source, exe))
            + "\n"
            + shlex.join([str(exe)])
            + "\n"
        )
        build.chmod(0o700)
        result["licensing"] = {
            "scope": "Public Apache-2.0 eclipse-score/inc_someip_gateway only",
            "source": (
                "https://docs.github.com/en/code-security/concepts/code-scanning/codeql/codeql-cli"
            ),
        }
        created = c.run(
            "database-create",
            [
                CODEQL,
                "database",
                "create",
                str(db),
                "--language=cpp",
                "--source-root=" + str(source),
                "--command=" + str(build),
                "--threads=1",
                "--ram=6000",
            ],
            360,
        )
        if created == 0:
            suite = (
                "codeql/cpp-queries@1.4.1:codeql-suites/cpp-security-and-quality.qls"
                if check == "codeql_security"
                else PACK + "/codeql-suites/misra-cpp-default.qls"
            )
            code = c.run(
                "analyze",
                [
                    CODEQL,
                    "database",
                    "analyze",
                    str(db),
                    suite,
                    "--format=sarif-latest",
                    "--output=" + str(out / "results.sarif"),
                    "--threads=1",
                    "--ram=6000",
                ],
                450,
            )
            if code == 0 and (out / "results.sarif").exists():
                sarif = json.loads((out / "results.sarif").read_text())
                result["findings"] = [
                    {
                        "rule_id": f.get("ruleId"),
                        "level": f.get("level"),
                        "locations": f.get("locations", []),
                    }
                    for run in sarif.get("runs", [])
                    for f in run.get("results", [])
                ]
                result["scan_runs"] = len(sarif.get("runs", []))
        result["limits"] = [
            "Focused linked executable, not full target extraction; dependency findings retained"
        ]
        if check == "codeql_misra":
            result["blockers"] += [
                "MISRA applicability/mapping draft and incomplete",
                "Default suite omits manual/audit obligations",
                "Compiled query qualification and human deviations pending",
            ]
    elif check == "process_checks":
        metadata = []
        for name in ("runtime_tests.cpp", "service_identifier_tests.cpp"):
            path = source / "score/socom/test/unit" / name
            content = path.read_text() if path.exists() else ""
            metadata.append(
                {
                    "path": str(path.relative_to(source)),
                    "sha256": digest(path) if path.exists() else None,
                    "test_macros": len(re.findall(r"\bTEST(?:_F|_P)?\s*\(", content)),
                    "record_properties": re.findall(r'RecordProperty\s*\(\s*"([^\"]+)"', content),
                }
            )
        result["metadata_inventory"] = metadata
        result["blockers"] += [
            "Lexical metadata inventory cannot prove semantic requirement coverage",
            "Safety/QM applicability and approved tailoring unknown",
            "Independent inspection and acceptance required",
            "External AoU and full integration verification require scoped review",
        ]
    elif check == "tool_assurance":
        tools = [
            GCC,
            str(LLVM / "clang++"),
            str(LLVM / "clang-tidy"),
            BAZEL,
            CODEQL,
            "/usr/bin/gcov-12",
            "/usr/bin/gcovr",
            "/usr/bin/cppcheck",
            FORMAT,
            PRECOMMIT,
            REUSE,
            "/usr/bin/qemu-system-x86_64",
            "/usr/bin/perf",
            "/usr/bin/valgrind",
            "/tmp/score-someip84-obligation-tools/usr/bin/valgrind",
            "/tmp/score-someip84-obligation-tools/bin/gitleaks",
        ]
        result["tool_inventory"] = [
            {
                "path": p,
                "available": Path(p).exists(),
                "sha256": digest(Path(p)) if Path(p).is_file() else None,
            }
            for p in tools
        ]
        for index, p in enumerate(tools):
            if Path(p).exists():
                c.run(
                    "version-" + str(index),
                    [p, "version"] if p == CODEQL or p.endswith("/gitleaks") else [p, "--version"],
                    4,
                )
        result["blockers"] += [
            (
                "Tool confidence evaluation, qualification where applicable, and "
                "acceptance require authorized humans"
            ),
            "Coverity not installed/adopted here; reconcile guideline/development-plan discrepancy",
            "Memcheck is an optional complement, not a universal process mandate",
        ]
    elif check == "rework_progress":
        state = root / "rework-source-hashes.json"
        previous = json.loads(state.read_text())
        current = source_identity(source)
        result["source_changed_this_round"] = previous != current
        result["rework_requested"] = previous != current
        result["stop_reason"] = (
            "Source changed; revisit measured findings with fresh results"
            if previous != current
            else "No further source progress; unresolved findings and human decisions stay pending"
        )
        state.write_text(json.dumps(current, indent=2) + "\n")
    elif check == "verification_report":
        current = source_identity(source)
        latest = {}
        for path in sorted((root / "obligation-results").glob("*/result.json")):
            item = json.loads(path.read_text())
            if item["check"] not in {"verification_report", "rework_progress"}:
                latest[item["check"]] = item
        result["results"] = [
            {
                "check": key,
                "status": value["status"],
                "result_path": value["result_path"],
                "matches_current_source": value["source_hashes"] == current,
                "blockers": value.get("blockers", []),
                "findings_count": len(value.get("findings", [])),
            }
            for key, value in latest.items()
        ]
        result["missing_checks"] = sorted(
            set(CHECKS) - {"verification_report", "rework_progress"} - set(latest)
        )
        result["blockers"] += [
            "Independent PR approval pending",
            "Safety/security/quality decisions, MISRA manual review and deviations pending",
            "Module/platform release acceptance and target qualification pending",
        ]
        if result["missing_checks"]:
            result["blockers"].append("Some collectors did not execute")
        if any(not item["matches_current_source"] for item in result["results"]):
            result["blockers"].append("Earlier measurement source differs from final source")
    else:
        raise ValueError("Unknown fixed obligation collector")


def collect(root: Path, policy: dict, node: dict) -> None:
    check = node["mode"].removeprefix("obligation:")
    if check not in CHECKS:
        raise ValueError("Unknown obligation collector")
    out = root / "obligation-results" / (check + "-" + str(time.time_ns()))
    out.mkdir(parents=True)
    source, container = snapshot(root, policy, out)
    inputs = json.loads((root / "measurement-inputs.json").read_text())
    gtest = source / ".llm_tmp/googletest"
    if gtest.exists():
        shutil.rmtree(gtest)
    shutil.copytree(inputs["googletest"], gtest, symlinks=True)
    result = {
        "check": check,
        "check_ref": node["ref"],
        "result_path": str(out / "result.json"),
        "origin": "local_unprotected_measurement",
        "engineering_acceptance": "pending",
        "source_hashes": source_identity(source),
        "collector_identity": collector_identity(),
        "blockers": [],
        "commands": [],
        "status": "unavailable",
        "started_at_epoch": time.time(),
    }
    commands = Commands(
        root, out, source, min(policy["deadline_epoch"] - 60, time.time() + CHECKS[check])
    )
    state = root / "rework-source-hashes.json"
    if not state.exists():
        state.write_text(json.dumps(result["source_hashes"], indent=2) + "\n")
    reusable = None
    if node["ref"].startswith("recollect_"):
        for previous in sorted((root / "obligation-results").glob(check + "-*/result.json")):
            candidate = json.loads(previous.read_text())
            if (
                candidate["source_hashes"] == result["source_hashes"]
                and candidate.get("collector_identity") == result["collector_identity"]
                and candidate["status"] != "unavailable"
            ):
                reusable = candidate
    try:
        if reusable:
            # Reuse is explicit evidence provenance, never presented as a new tool run.
            result.update(
                {
                    key: value
                    for key, value in reusable.items()
                    if key
                    not in {"check_ref", "result_path", "started_at_epoch", "completed_at_epoch"}
                }
            )
            result["reused_from"] = reusable["result_path"]
            result["original_execution_started_at_epoch"] = reusable["started_at_epoch"]
            commands.records = reusable["commands"]
        else:
            execute(check, commands, root, result)
        result["commands"] = commands.records
        errors = [r for r in commands.records if r["exit_code"] != 0]
        result["status"] = (
            "findings_or_execution_failure" if errors or result.get("findings") else "completed"
        )
        if result["blockers"] and result["status"] == "completed":
            result["status"] = "completed_with_blockers"
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        result["commands"] = commands.records
        result["blockers"].append(type(error).__name__ + ": " + str(error))
    result["completed_at_epoch"] = time.time()
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    feedback = out / "feedback"
    feedback.mkdir()
    # Successful collection is distinct from successful verification. Continue
    # collecting other obligations even when tools find defects or are unavailable.
    (feedback / "collection-result").write_text("1\n" if result.get("rework_requested") else "0\n")
    shutil.copyfile(out / "result.json", feedback / "result.json")
    for p in out.iterdir():
        if p.is_file() and p.suffix in {".stdout", ".stderr", ".json", ".sarif", ".yaml", ".xml"}:
            shutil.copyfile(p, feedback / p.name)
    if reusable:
        original_feedback = Path(reusable["result_path"]).parent / "feedback"
        for p in original_feedback.iterdir():
            if p.is_file() and p.name not in {"result.json", "collection-result"}:
                shutil.copyfile(p, feedback / p.name)
    destination = "/workspace/.llm_tmp/overnight/obligations/" + check
    docker("exec", container, "mkdir", "-p", destination)
    docker("cp", str(feedback) + "/.", container + ":" + destination + "/")
    # The host archive is portable and preserves every original attempt.
    archive = root / "portable-obligation-evidence"
    archive.mkdir(exist_ok=True)
    shutil.copytree(feedback, archive / out.name)
    (root / "latest-obligation.json").write_text(json.dumps(result, indent=2) + "\n")
