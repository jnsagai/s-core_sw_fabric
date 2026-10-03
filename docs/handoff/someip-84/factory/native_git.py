"""Restore real baseline Git identity in disposable native collector workspaces."""

from __future__ import annotations

import json
import re
from pathlib import Path

from measure import digest


def restore_native_git(commands, root: Path, result: dict) -> None:
    record = root / "native-git-baseline.json"
    if not record.exists():
        return  # Historical collectors and unrelated tests have no such binding.
    baseline = json.loads(record.read_text())
    bundle = root / "native-git-baseline.bundle"
    if digest(bundle) != baseline["bundle_sha256"]:
        raise ValueError("Native Git baseline bundle changed")
    commit, tree = baseline["commit"], baseline["tree"]
    if not all(re.fullmatch(r"[0-9a-f]{40}", value) for value in (commit, tree)):
        raise ValueError("Invalid native Git baseline identity")
    repository = baseline["repository"]
    if repository != "eclipse-score/inc_someip_gateway":
        raise ValueError("Unexpected native Git repository")
    git = ["/usr/bin/git", "-c", "core.hooksPath=/dev/null", "-c", "credential.helper="]
    metadata = commands.source / ".git"
    if not metadata.exists():
        for label, argv in (
            ("native-git-init", [*git, "init"]),
            ("native-git-hooks", [*git, "config", "core.hooksPath", "/dev/null"]),
            ("native-git-fetch", [*git, "fetch", "--no-tags", str(bundle), commit]),
            ("native-git-index", [*git, "reset", "--mixed", commit]),
            (
                "native-git-origin",
                [*git, "remote", "add", "origin", "https://github.com/" + repository],
            ),
        ):
            if commands.run(label, argv, 60):
                raise ValueError("Disposable native Git restoration failed: " + label)
    if commands.run("native-git-identity", [*git, "rev-parse", "HEAD", "HEAD^{tree}"]):
        raise ValueError("Cannot measure restored native Git identity")
    actual = (commands.out / "native-git-identity.stdout").read_text().splitlines()
    if actual != [commit, tree]:
        raise ValueError("Restored native Git baseline identity differs")
    if commands.run("native-git-remote", [*git, "remote", "get-url", "origin"]):
        raise ValueError("Cannot measure restored native Git remote")
    if (commands.out / "native-git-remote.stdout").read_text().strip() != (
        "https://github.com/" + repository
    ):
        raise ValueError("Restored native Git remote differs")
    result["git_provenance"] = {
        **baseline,
        "candidate_status": "worktree_changes_against_real_pinned_baseline",
        "hooks": "disabled",
        "origin": "local_unprotected_metadata_restoration",
    }
