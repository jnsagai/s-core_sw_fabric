"""Start one prepared account-backed Fabro run from a host with Docker access.

Fabro owns execution. No automatic human answers or platform API keys are used.
The existing Codex auth file is read without refreshing or changing its tokens.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import secrets
import shutil
import socket
import subprocess
import time
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

from measure import verify_tree
from prepare import BINARY, HERE, sha, write
from run_host import cli_auth_file
from storage import private_server_root, validate_run_root


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prepared_root", type=Path)
    parser.add_argument("--port", type=int, default=43917)
    args = parser.parse_args()
    root = args.prepared_root.resolve(strict=True)
    validate_run_root(root)
    overlay = json.loads((root / "operational-overlay.json").read_bytes())
    if (overlay["provider"], overlay["model"], overlay["reasoning_effort"]) != (
        "openai-codex",
        "gpt-6.1-sol",
        "medium",
    ):
        raise ValueError("Prepared model selection differs from the authorized account alternative")
    for filename, key in (
        ("workflow/workflow.toml", "native_entrypoint_sha256"),
        ("out/package.json", "compiled_package_sha256"),
        ("guard_agent_tools.py", "tool_hook_sha256"),
        ("isolate_docker.py", "sandbox_hook_sha256"),
    ):
        if sha(root / filename) != overlay[key]:
            raise ValueError(f"Prepared input changed: {filename}")
    package = json.loads((root / "out/package.json").read_bytes())
    for name, content in package["files"].items():
        if name != "workflow.toml" and (root / "workflow" / name).read_text() != content:
            raise ValueError(f"Compiled workflow input changed: {name}")
    native_validation = json.loads((root / "native-validation.json").read_bytes())
    if sha(BINARY) != native_validation["validator"]["executable_sha256"]:
        raise ValueError("Fabro executable changed since native compilation")
    verify_tree(root / "target", json.loads((HERE.parent / "source-manifest.json").read_bytes()))

    # Fail before reading credentials or creating a server if host access is denied.
    try:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", args.port))
    except PermissionError:
        raise SystemExit(
            "Host socket access is denied by this session. No credentials read or run created."
        ) from None
    image = subprocess.check_output(
        ["docker", "image", "inspect", "score-someip84-agent:20261001", "--format", "{{.Id}}"],
        text=True,
        timeout=10,
    ).strip()
    if image != overlay["docker_image_id"]:
        raise ValueError("Docker image identity changed")
    if subprocess.check_output(
        ["docker", "ps", "-q", "--filter", "ancestor=" + image], text=True, timeout=10
    ).strip():
        raise ValueError("Another matching container is active; isolation hook requires a sole run")

    login = json.loads(Path("/home/jefferson/.codex/auth.json").read_bytes())
    if login.get("auth_mode") != "chatgpt":
        raise ValueError("Existing Codex login is not a ChatGPT account")
    account = login["tokens"]
    payload = account["access_token"].split(".")[1]
    expires = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))["exp"]
    expiry = datetime.fromtimestamp(expires, UTC)
    if expiry <= datetime.now(UTC) + timedelta(hours=4):
        raise ValueError("Codex access token expires too soon; renew the normal Codex login first")
    credential = {
        "tokens": {
            "access_token": account["access_token"],
            "refresh_token": None,
            "expires_at": expiry.isoformat(),
        },
        "account_id": account["account_id"],
        "config": {
            "auth_url": "https://auth.openai.com",
            "token_url": "https://auth.openai.com/oauth/token",
            "client_id": "app_EMoamEEZ73f0CkXaXp7hrann",
            "scopes": ["openid", "profile", "email", "offline_access"],
            "redirect_uri": "https://auth.openai.com/deviceauth/callback",
            "use_pkce": False,
        },
    }
    server_root = private_server_root(root, "codex-server")
    (server_root / "home").mkdir()
    config = server_root / "settings.toml"
    shutil.copyfile(HERE / "codex-catalogue.toml", config)
    with config.open("a") as stream:
        stream.write(
            '\n[environments.someip84]\nprovider = "docker"\n'
            '\n[environments.someip84.image]\ndocker = "score-someip84-agent:20261001"\n'
            '\n[environments.someip84.network]\nmode = "block"\n'
        )
    base_url = f"http://127.0.0.1:{args.port}"
    token = "fabro_dev_" + secrets.token_hex(32)
    auth_file = cli_auth_file(server_root, base_url, token)
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.endswith("_API_KEY") and key not in {"CODEX_ACCESS_TOKEN", "OPENAI_CODEX_TOKEN"}
    }
    env.update(
        {
            "HOME": str(server_root / "home"),
            "FABRO_AUTH_FILE": str(auth_file),
            "FABRO_DEV_TOKEN": token,
            "SESSION_SECRET": secrets.token_hex(32),
            "FABRO_NO_UPGRADE_CHECK": "true",
            "FABRO_HTTP_PROXY_POLICY": "disabled",
        }
    )
    with (server_root / "server.log").open("wb") as log:
        server = subprocess.Popen(
            [
                str(BINARY),
                "server",
                "start",
                "--foreground",
                "--bind",
                f"127.0.0.1:{args.port}",
                "--storage-dir",
                str(server_root / "storage"),
                "--config",
                str(config),
                "--no-web",
            ],
            env=env,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )
    write(
        server_root / "server-record.json",
        {
            "pid": server.pid,
            "base_url": base_url,
            "storage": str(server_root / "storage"),
            "executable_sha256": sha(BINARY),
            "config_sha256_before_migration": sha(config),
        },
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        for _ in range(40):
            if server.poll() is not None:
                raise RuntimeError("Fabro server exited; inspect preserved server.log")
            try:
                request = urllib.request.Request(
                    base_url + "/api/v1/runs", headers={"Authorization": "Bearer " + token}
                )
                with opener.open(request, timeout=1):
                    break
            except OSError:
                time.sleep(0.25)
        else:
            raise RuntimeError("Fabro server did not become ready")
        request = urllib.request.Request(
            base_url + "/api/v1/secrets",
            method="POST",
            data=json.dumps(
                {"name": "OPENAI_CODEX", "value": json.dumps(credential), "type": "oauth"}
            ).encode(),
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        )
        with opener.open(request, timeout=10):
            pass
        print(
            "ChatGPT access imported into the isolated vault; original login unchanged.", flush=True
        )

        def cli(label: str, command: list[str], timeout: int = 120) -> str:
            with (root / f"{label}.stdout").open("w") as output:
                with (root / f"{label}.stderr").open("w") as errors:
                    subprocess.run(
                        [str(BINARY), "--server", base_url, "--json", *command],
                        env=env,
                        cwd=root,
                        stdout=output,
                        stderr=errors,
                        timeout=timeout,
                        check=True,
                    )
            return (root / f"{label}.stdout").read_text()

        print("Testing Fabro tools with gpt-6.1-sol medium before starting.", flush=True)
        smoke = json.loads(
            cli(
                "codex-model-smoke",
                [
                    "model",
                    "test",
                    "--provider",
                    "openai-codex",
                    "--model",
                    "gpt-6.1-sol",
                    "--reasoning-effort",
                    "medium",
                    "--tools",
                ],
            )
        )
        if smoke["results"] != [
            {"provider": "openai-codex", "model": "gpt-6.1-sol", "result": "pass"}
        ]:
            raise RuntimeError("Exact Fabro account tool smoke did not pass; no run started")
        cli(
            "codex-preflight",
            [
                "preflight",
                str(root / "workflow/workflow.toml"),
                "--environment",
                "someip84",
            ],
        )
    except BaseException:
        server.terminate()
        raise
    # A submission timeout may follow successful creation; retain the server and
    # native output so the operator can inspect state instead of submitting twice.
    native = cli(
        "codex-run-start",
        [
            "run",
            str(root / "workflow/workflow.toml"),
            "--target-from",
            str(root / "target"),
            "--model",
            "gpt-6.1-sol",
            "--provider",
            "openai-codex",
            "--environment",
            "someip84",
            "--label",
            "scope=someip84-codex-account",
            "--detach",
        ],
    )
    print(native, flush=True)
    print(f"Fabro server: {base_url}; evidence: {root}", flush=True)


if __name__ == "__main__":
    main()
