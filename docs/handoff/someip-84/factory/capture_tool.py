"""Private tcpdump compatibility build for Bazel's single-user namespace.

Real capture, filtering and process status remain tcpdump's. The narrow patch
avoids resetting supplementary groups only when the requested identity already
matches, setgroups is denied, and the namespace has a single UID mapping.
The host collector separately refuses a host-root launcher for this variant.
It still executes setgid/setuid and propagates their failures. This tool variant
requires external engineering qualification; it is never a system installation.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

COMMIT = "5f552b5e6e9fe05f7ad9681d51d0303233daba6a"
DEV_VERSION = "1.10.1-4ubuntu1.22.04.2"
DEV_SHA = "1686d8f515e7f8c1efe85555d5d39aa524937bca08b16afea7ff742dc352379d"
HELPER = r"""
/* S-CORE disposable tool variant: preserve an already selected identity in
 * a single-user namespace. The authorized host launcher must be non-root. */
static int
score_same_identity_namespace(const struct passwd *pw)
{
    FILE *f;
    unsigned int inner, outer, count;
    char mode[16];
    int end;
    if (pw->pw_uid != 0 || pw->pw_gid != 0 ||
        geteuid() != pw->pw_uid || getegid() != pw->pw_gid)
        return 0;
    f = fopen("/proc/self/uid_map", "r");
    if (!f) return 0;
    if (fscanf(f, "%u %u %u", &inner, &outer, &count) != 3) {
        fclose(f); return 0;
    }
    do { end = fgetc(f); } while (end == ' ' || end == '\n' || end == '\t');
    fclose(f);
    if (inner != 0 || count != 1 || end != EOF) return 0;
    f = fopen("/proc/self/setgroups", "r");
    if (!f) return 0;
    mode[0] = 0;
    if (fscanf(f, "%15s", mode) != 1) { fclose(f); return 0; }
    fclose(f);
    if (strcmp(mode, "deny") != 0) return 0;
    fprintf(stderr, "score capture: preserving matching identity in restricted user namespace\n");
    return 1;
}
"""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def acquire(root: Path) -> None:
    from storage import validate_run_root

    validate_run_root(root)
    directory = root / "capture-inputs"
    directory.mkdir()
    env = {"PATH": "/usr/bin:/bin", "HOME": str(directory), "GIT_TERMINAL_PROMPT": "0"}
    with (directory / "acquisition.log").open("wb") as log:
        subprocess.run(
            [
                "git",
                "-c",
                "credential.helper=",
                "-c",
                "core.hooksPath=/dev/null",
                "clone",
                "--depth=1",
                "--branch=tcpdump-4.99.1",
                "https://github.com/the-tcpdump-group/tcpdump.git",
                str(directory / "source"),
            ],
            env=env,
            stdout=log,
            stderr=log,
            check=True,
            timeout=120,
        )
        actual = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=directory / "source", env=env, text=True
        ).strip()
        if actual != COMMIT:
            raise ValueError("tcpdump source tag identity differs")
        subprocess.run(
            ["apt-get", "download", "libpcap0.8-dev=" + DEV_VERSION],
            cwd=directory,
            env=env,
            stdout=log,
            stderr=log,
            check=True,
            timeout=120,
        )
    archive = next(directory.glob("*.deb"))
    if digest(archive) != DEV_SHA:
        raise ValueError("libpcap development archive identity differs")
    subprocess.run(["dpkg-deb", "-x", str(archive), str(directory / "dev")], check=True)
    identities = {
        str(p.relative_to(directory)): digest(p)
        for p in directory.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(directory).parts
    }
    (root / "capture-inputs.json").write_text(
        json.dumps(
            {
                "commit": COMMIT,
                "repository": "https://github.com/the-tcpdump-group/tcpdump",
                "dev_version": DEV_VERSION,
                "dev_sha256": DEV_SHA,
                "identities": identities,
                "qualification": "pending_external_human_validation",
            },
            indent=2,
        )
        + "\n"
    )
    provision_link_inputs(root)


def provision_link_inputs(root: Path) -> None:
    """Complete the private development prefix using the package's real archive."""
    from storage import validate_run_root

    validate_run_root(root)
    dev = root / "capture-inputs/dev/usr"
    directory = root / "libpcap"
    directory.mkdir(exist_ok=True)
    shutil.copyfile(dev / "lib/x86_64-linux-gnu/libpcap.a", directory / "libpcap.a")
    dbus = Path("/lib/x86_64-linux-gnu/libdbus-1.so.3").resolve(strict=True)
    script = (dev / "bin/pcap-config").read_text()
    script = script.replace('prefix="/usr"', 'prefix="' + str(dev) + '"').replace(
        'LIBS=" -ldbus-1"', 'LIBS=" ' + str(dbus) + '"'
    )
    config = directory / "pcap-config"
    config.write_text(script)
    config.chmod(0o755)
    (root / "capture-link-inputs.json").write_text(
        json.dumps(
            {
                "libpcap_archive_sha256": digest(directory / "libpcap.a"),
                "pcap_config_sha256": digest(config),
                "dbus_path": str(dbus),
                "dbus_sha256": digest(dbus),
                "system_installation_changed": False,
                "configuration": "Original package script relocated to private development prefix",
            },
            indent=2,
        )
        + "\n"
    )


def build(root: Path) -> None:
    from storage import validate_run_root

    validate_run_root(root)
    directory = root / "capture-inputs"
    inputs = json.loads((root / "capture-inputs.json").read_text())
    for name, expected in inputs["identities"].items():
        if digest(directory / name) != expected:
            raise ValueError("Frozen capture build input changed")
    links = json.loads((root / "capture-link-inputs.json").read_text())
    for path, expected in (
        (root / "libpcap/libpcap.a", links["libpcap_archive_sha256"]),
        (root / "libpcap/pcap-config", links["pcap_config_sha256"]),
        (Path(links["dbus_path"]), links["dbus_sha256"]),
    ):
        if digest(path) != expected:
            raise ValueError("Capture link input changed")
    work = root / "capture-build"
    shutil.copytree(
        directory / "source", work, ignore=shutil.ignore_patterns(".git"), dirs_exist_ok=True
    )
    code = work / "tcpdump.c"
    before = code.read_text()
    needle = "\t\tif (initgroups(pw->pw_name, pw->pw_gid) != 0 ||"
    anchor = "/* Drop root privileges and chroot if necessary */"
    if before.count(needle) != 1 or before.count(anchor) != 1:
        raise ValueError("Unexpected tcpdump source; refusing compatibility patch")
    after = before.replace(anchor, HELPER + "\n" + anchor).replace(
        needle,
        "\t\tif ((!score_same_identity_namespace(pw) && "
        "initgroups(pw->pw_name, pw->pw_gid) != 0) ||",
    )
    code.write_text(after)
    import difflib

    (root / "capture-identity.patch").write_text(
        "".join(
            difflib.unified_diff(
                before.splitlines(True),
                after.splitlines(True),
                fromfile="upstream/tcpdump.c",
                tofile="variant/tcpdump.c",
            )
        )
    )
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(root / "tool-home"),
        "TMPDIR": str(root / "tool-tmp"),
        "LC_ALL": "C",
        "CPPFLAGS": "-I" + str(directory / "dev/usr/include"),
    }
    for name in ("tool-home", "tool-tmp"):
        (root / name).mkdir(exist_ok=True)
    previous_log = root / "capture-build.log"
    if previous_log.exists():
        import time

        shutil.copyfile(previous_log, root / ("capture-build-" + str(time.time_ns()) + ".log"))
    with (root / "capture-build.log").open("wb") as log:
        for command in (
            ["./configure", "--without-crypto", "--without-cap-ng", "--disable-smb"],
            ["make", "-j2"],
        ):
            subprocess.run(
                command, cwd=work, env=env, stdout=log, stderr=log, check=True, timeout=180
            )
    binary = work / "tcpdump"
    # Bind the directory rather than spelling the executable in sandbox argv:
    # native stale-process assertions match the literal /usr/bin/tcpdump.
    bin_directory = root / "capture-bin"
    bin_directory.mkdir(exist_ok=True)
    for original in Path("/usr/bin").iterdir():
        if original.name != "tcpdump" and not (bin_directory / original.name).is_symlink():
            (bin_directory / original.name).symlink_to("/mnt/" + original.name)
    if not (bin_directory / "tcpdump").is_symlink():
        (bin_directory / "tcpdump").symlink_to(binary)
    (root / "capture-tool.json").write_text(
        json.dumps(
            {
                "path": str(binary),
                "sha256": digest(binary),
                "upstream_commit": COMMIT,
                "patch_sha256": digest(root / "capture-identity.patch"),
                "native_source_unchanged": True,
                "system_installation_changed": False,
                "qualification": "pending_external_human_validation",
                "libpcap_path": str(Path("/lib/x86_64-linux-gnu/libpcap.so.0.8").resolve()),
                "libpcap_sha256": digest(Path("/lib/x86_64-linux-gnu/libpcap.so.0.8")),
            },
            indent=2,
        )
        + "\n"
    )


def verify_binary(root: Path) -> Path:
    record = json.loads((root / "capture-tool.json").read_text())
    tool = Path(record["path"])
    if not tool.resolve().is_relative_to(root) or digest(tool) != record["sha256"]:
        raise ValueError("Private tcpdump identity differs")
    if digest(Path(record["libpcap_path"])) != record["libpcap_sha256"]:
        raise ValueError("Private tcpdump runtime identity differs")
    return tool


def sandbox_mounts(root: Path) -> list[str]:
    verify_binary(root)
    directory = root / "capture-bin"
    for original in Path("/usr/bin").iterdir():
        expected = (
            str(root / "capture-build/tcpdump")
            if original.name == "tcpdump"
            else "/mnt/" + original.name
        )
        if (
            not (directory / original.name).is_symlink()
            or str((directory / original.name).readlink()) != expected
        ):
            raise ValueError("Private capture binary directory changed")
    return [
        "--sandbox_add_mount_pair=/usr/bin:/mnt",
        "--sandbox_add_mount_pair=" + str(directory) + ":/usr/bin",
    ]
