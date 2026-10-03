import hashlib
import json
import tarfile
from pathlib import Path

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.quality import codeql

feature = Path("specs/010-misra-quality-and-deviations")
comparison = json.loads((feature / "evidence/bundle-library-comparison.json").read_bytes())
archive = Path(
    "/home/jefferson/.local/share/s-core-tools/downloads/codeql-2.21.4/codeql-bundle-linux64.tar.gz"
)
identity = codeql._file(archive, 1024 * 1024 * 1024)
expected = "a94f674bb3c23ea5e9a2ad06b64847dd0277b15014d2517ecd9c41c88e6caa65"
assert identity["sha256"] == expected
selected = {}
for lib in comparison["libraries"]:
    if lib["state"] == "compared":
        for row in lib["matched_files"]:
            key = f"codeql/qlpacks/{lib['name']}/{lib['version']}/{row['path']}"
            assert key not in selected
            selected[key] = row
rows, count, total = [], 0, 0
with tarfile.open(archive, "r|gz") as stream:
    for member in stream:
        count += 1
        total += member.size
        assert count <= 200000 and total <= 8 * 1024 * 1024 * 1024
        if member.name not in selected:
            continue
        row = selected.pop(member.name)
        assert member.isfile() and member.size == row["bytes"] <= codeql.MAX_ARTIFACT
        body = stream.extractfile(member)
        assert body is not None
        identity_hash = hashlib.sha256()
        size = 0
        with body:
            while block := body.read(1024 * 1024):
                size += len(block)
                assert size <= row["bytes"]
                identity_hash.update(block)
        assert size == row["bytes"] and identity_hash.hexdigest() == row["sha256"]
        rows.append({"archive_path": member.name, "sha256": row["sha256"], "bytes": size})
assert not selected
assert codeql._file(archive, 1024 * 1024 * 1024) == identity
record = seal(
    {
        "measurement": "read_only_bundle_archive_selected_library_comparison",
        "comparison_digest": comparison["digest"],
        "archive": identity,
        "archive_sha256_origin": "previous_local_installation_record_not_publisher_authentication",
        "archive_members_scanned": count,
        "archive_declared_bytes_scanned": total,
        "matched_files": sorted(rows, key=lambda row: row["archive_path"]),
        "files_written_or_extracted": 0,
        "analysis_executed": False,
        "source_provenance": "unverified",
        "compiled_artifact_provenance": "unverified",
        "accepted_claims": 0,
        "engineering_readiness": "not_evaluated",
    }
)
(feature / "evidence/bundle-archive-library-comparison.json").write_bytes(canonical(record) + b"\n")
print(
    json.dumps(
        {
            "matched": len(rows),
            "scanned": count,
            "archive_sha256": identity["sha256"],
            "digest": record["digest"],
        }
    )
)
