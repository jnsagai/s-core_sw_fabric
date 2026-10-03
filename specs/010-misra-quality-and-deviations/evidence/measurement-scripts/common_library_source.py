import json
import os
import subprocess
from pathlib import Path

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.quality import codeql

root = Path("/tmp/s-core-foundation/references/codeql-coding-standards")
inventory = json.loads(
    Path(
        "specs/010-misra-quality-and-deviations/evidence/codeql-prerequisites-current.json"
    ).read_bytes()
)
commit = inventory["source_inspection"]["commit"]
library = next(
    v
    for v in inventory["pack_inspection"]["libraries"]
    if v["name"] == "codeql/common-cpp-coding-standards"
)
prefix = "cpp/common/src/"
args = [
    "/usr/bin/git",
    "--no-optional-locks",
    "-c",
    "core.fsmonitor=false",
    "-c",
    "core.hooksPath=/dev/null",
    "-C",
    str(root),
]
env = dict(
    os.environ,
    GIT_CONFIG_NOSYSTEM="1",
    GIT_CONFIG_GLOBAL="/dev/null",
    GIT_OPTIONAL_LOCKS="0",
    GIT_TERMINAL_PROMPT="0",
)


def git(*parts):
    result = subprocess.run(
        args + list(parts), env=env, capture_output=True, check=True, timeout=30
    )
    assert len(result.stdout) + len(result.stderr) <= 1024 * 1024
    return result.stdout


assert git("rev-parse", "HEAD").decode().strip() == commit
assert git("status", "--porcelain", "--untracked-files=all") == b""
objects = {}
for entry in git("ls-tree", "-r", "-z", commit, "--", prefix).decode().split("\0"):
    if not entry:
        continue
    spec, path = entry.split("\t")
    mode, kind, object_id = spec.split()
    assert kind == "blob" and mode in {"100644", "100755"}
    if Path(path).suffix in {".ql", ".qll", ".qls"}:
        objects[path] = object_id
assert 0 < len(objects) <= 5000
source_rows = codeql._manifest(root, sorted(objects), objects)
native_prefix = str(Path(library["path"]).parent) + "/"
indexed = {v["path"]: v for v in inventory["pack_inspection"]["manifest"]}
rows = []
for row in source_rows:
    packed = native_prefix + row["path"][len(prefix) :]
    assert indexed[packed]["sha256"] == row["sha256"]
    assert indexed[packed]["bytes"] == row["bytes"]
    actual = codeql._file(Path(inventory["pack_inspection"]["root"]) / packed)
    assert actual["sha256"] == row["sha256"]
    rows.append(
        {
            "source_path": row["path"],
            "installed_path": packed,
            "sha256": row["sha256"],
            "bytes": row["bytes"],
        }
    )
assert git("rev-parse", "HEAD").decode().strip() == commit
assert git("status", "--porcelain", "--untracked-files=all") == b""
record = seal(
    {
        "measurement": "read_only_common_library_source_comparison",
        "source_commit": commit,
        "source_repository": "https://github.com/github/codeql-coding-standards",
        "source_prefix": prefix,
        "library": library,
        "files": rows,
        "matched_query_sources": len(rows),
        "total_bytes": sum(v["bytes"] for v in rows),
        "unreconciled_libraries": [
            v["name"]
            for v in inventory["pack_inspection"]["libraries"]
            if v["name"] != library["name"]
        ],
        "compiled_artifact_provenance": "unverified",
        "analysis_executed": False,
        "accepted_claims": 0,
        "engineering_readiness": "not_evaluated",
        "source_lock_changed": False,
    }
)
out = Path("specs/010-misra-quality-and-deviations/evidence/common-library-source-comparison.json")
out.write_bytes(canonical(record) + b"\n")
print(
    json.dumps(
        {
            "matched": len(rows),
            "bytes": record["total_bytes"],
            "unreconciled": len(record["unreconciled_libraries"]),
            "digest": record["digest"],
        }
    )
)
