"""Account-backed isolated proposals; deterministic scope and drift checks own application."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from score_sw_fabric.runtime.supervision import atomic, digest, read

IGNORED = {
    ".git",
    ".venv",
    ".tools",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
}


def account_environment() -> dict[str, str]:
    # Deliberate environment allowlist, so provider/API/federation overrides cannot select billing.
    keys = ("HOME", "USER", "LOGNAME", "PATH", "LANG", "LC_ALL", "SHELL", "XDG_RUNTIME_DIR")
    return {key: os.environ[key] for key in keys if key in os.environ}


def account_status() -> None:
    result = subprocess.run(
        ["codex", "-c", 'forced_login_method="chatgpt"', "login", "status"],
        env=account_environment(),
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode or "ChatGPT" not in result.stdout + result.stderr:
        raise ValueError("Codex ChatGPT login is required; no API fallback permitted")


def inventory(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in IGNORED for part in relative.parts):
            continue
        if path.is_symlink():
            result[str(relative)] = {"link": os.readlink(path)}
        elif path.is_file():
            result[str(relative)] = {"sha256": digest(path), "mode": path.stat().st_mode & 0o777}
    return result


def changed_files(before: dict[str, dict[str, Any]], root: Path, allowed: list[str]) -> list[str]:
    after = inventory(root)
    changes = sorted(
        key for key in before.keys() | after.keys() if before.get(key) != after.get(key)
    )
    for key in changes:
        if key not in allowed or key not in after or "link" in after[key]:
            raise ValueError("Codex proposal escaped its file scope: " + key)
    return changes


def apply_verified(
    source: Path, candidate: Path, before: dict[str, dict[str, Any]], changes: list[str]
) -> None:
    # Check all user-owned inputs before any application. Evidence records the intended hashes.
    for key in changes:
        path = source / key
        old = before.get(key)
        if (
            old is None
            or not path.is_file()
            or path.is_symlink()
            or any(p.is_symlink() for p in path.parents)
        ):
            raise ValueError("Unsafe or new original repair path: " + key)
        if digest(path) != old["sha256"] or path.stat().st_mode & 0o777 != old["mode"]:
            raise ValueError("User work changed during repair; application refused: " + key)
    for key in changes:
        path = source / key
        if digest(path) != before[key]["sha256"]:
            raise ValueError("User work changed before atomic application: " + key)
        stage = path.with_name(path.name + ".repair-" + str(os.getpid()))
        try:
            shutil.copyfile(candidate / key, stage)
            stage.chmod((candidate / key).stat().st_mode & 0o777)
            stage.replace(path)
        finally:
            stage.unlink(missing_ok=True)


def propose(work: Path, evidence: Path, prompt: str) -> dict[str, Any]:
    """Run one fresh exact-model proposal. A prior invocation is never silently duplicated."""
    evidence.mkdir(mode=0o700, parents=True, exist_ok=True)
    intent = evidence / "intent.json"
    if intent.exists():
        saved = read(intent)
        output = evidence / "proposal.json"
        if saved.get("status") == "completed" and saved.get("exit_code") == 0 and output.exists():
            return read(output)
        raise ValueError("Prior Codex invocation is uncertain or failed; inspect retained intent")
    account_status()
    schema = evidence / "schema.json"
    atomic(
        schema,
        {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["ready", "blocked"]},
                "summary": {"type": "string"},
            },
            "required": ["status", "summary"],
            "additionalProperties": False,
        },
    )
    atomic(
        intent,
        {
            "status": "invoking",
            "model": "gpt-6.1-sol",
            "reasoning_effort": "medium",
            "authentication": "ChatGPT",
            "api_fallback": False,
        },
    )
    argv = [
        "codex",
        "exec",
        "--ignore-user-config",
        "--ephemeral",
        "--skip-git-repo-check",
        "--json",
        "-m",
        "gpt-6.1-sol",
        "-c",
        'model_reasoning_effort="medium"',
        "-c",
        'forced_login_method="chatgpt"',
        "-c",
        'approval_policy="never"',
        "-c",
        'web_search="disabled"',
        "-s",
        "workspace-write",
        "-C",
        str(work),
        "--output-schema",
        str(schema),
        "--output-last-message",
        str(evidence / "proposal.json"),
        "-",
    ]
    (evidence / "prompt.txt").write_text(prompt)
    with (evidence / "events.jsonl").open("wb") as stdout:
        with (evidence / "stderr.txt").open("wb") as stderr:
            process = subprocess.Popen(
                argv,
                env=account_environment(),
                stdin=subprocess.PIPE,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
            atomic(intent, {**read(intent), "status": "running", "pid": process.pid})
            try:
                process.communicate(prompt.encode(), timeout=1800)
            except subprocess.TimeoutExpired:
                import signal

                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
                atomic(intent, {**read(intent), "status": "timed_out"})
                raise
    atomic(intent, {**read(intent), "status": "completed", "exit_code": process.returncode})
    if process.returncode:
        raise RuntimeError(
            "Codex account repair failed; retained stderr and events need inspection"
        )
    return read(evidence / "proposal.json")
