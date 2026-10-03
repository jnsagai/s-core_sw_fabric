import json
from pathlib import Path

from score_sw_fabric.assurance.models import seal
from score_sw_fabric.catalog.export import canonical
from score_sw_fabric.quality import codeql

feature = Path("specs/010-misra-quality-and-deviations")
inventory = json.loads((feature / "evidence/codeql-prerequisites-current.json").read_bytes())
pack = Path(inventory["pack_inspection"]["root"])
bundle = Path("/home/jefferson/.local/share/s-core-tools/codeql-2.21.4/codeql/qlpacks")
indexed = {row["path"]: row for row in inventory["pack_inspection"]["manifest"]}
comparisons = []
for library in inventory["pack_inspection"]["libraries"]:
    name, version = library["name"], library["version"]
    other = bundle / name / version
    if not other.is_dir():
        comparisons.append({"name": name, "version": version, "state": "bundle_copy_unavailable"})
        continue
    embedded = Path(library["path"]).parent
    left_root = pack / embedded
    left_names, right_names = codeql._names(left_root), codeql._names(other)
    left, right = codeql._manifest(left_root, left_names), codeql._manifest(other, right_names)
    for row in left:
        selected = indexed[str(embedded / row["path"])]
        assert (row["sha256"], row["bytes"]) == (selected["sha256"], selected["bytes"])
    left_index = {row["path"]: row for row in left}
    right_index = {row["path"]: row for row in right}
    pairs, differences = [], []
    for path in sorted(set(left_index) | set(right_index)):
        a, b = left_index.get(path), right_index.get(path)
        if (
            a is not None
            and b is not None
            and (a["sha256"], a["bytes"]) == (b["sha256"], b["bytes"])
        ):
            pairs.append(a)
        else:
            differences.append({"path": path, "embedded": a, "bundle": b})
    queries = [row for row in pairs if Path(row["path"]).suffix in {".ql", ".qll", ".qls"}]
    query_differences = [
        row for row in differences if Path(row["path"]).suffix in {".ql", ".qll", ".qls"}
    ]
    assert (
        codeql._names(left_root) == left_names and codeql._manifest(left_root, left_names) == left
    )
    assert codeql._names(other) == right_names and codeql._manifest(other, right_names) == right
    comparisons.append(
        {
            "name": name,
            "version": version,
            "state": "compared",
            "embedded_root": str(left_root),
            "bundle_root": str(other),
            "matched_files": pairs,
            "differences": differences,
            "matched_query_sources": len(queries),
            "query_source_differences": len(query_differences),
            "embedded_files": len(left),
            "bundle_files": len(right),
            "metadata": {"embedded": left_index["qlpack.yml"], "bundle": right_index["qlpack.yml"]},
            "source_provenance": "unverified",
        }
    )
    print(
        json.dumps(
            {
                "name": name,
                "matched": len(pairs),
                "differences": len(differences),
                "queries": len(queries),
                "query_differences": len(query_differences),
            }
        )
    )
record = seal(
    {
        "measurement": "read_only_embedded_to_installed_bundle_library_comparison",
        "inventory_digest": inventory["digest"],
        "bundle_root": str(bundle),
        "bundle_origin": "installed_distribution_copy_not_reconciled_git_source",
        "bounds": {
            "files_per_library": 5000,
            "directory_entries_per_library": 10000,
            "file_bytes": codeql.MAX_ARTIFACT,
            "total_bytes_per_library": codeql.MAX_TOTAL,
        },
        "libraries": comparisons,
        "source_provenance": "unverified",
        "compiled_artifact_provenance": "unverified",
        "runtime_qualification": "unverified",
        "analysis_executed": False,
        "accepted_claims": 0,
        "engineering_readiness": "not_evaluated",
        "source_lock_changed": False,
    }
)
(feature / "evidence/bundle-library-comparison.json").write_bytes(canonical(record) + b"\n")
print(
    json.dumps(
        {
            "digest": record["digest"],
            "compared": sum(row["state"] == "compared" for row in comparisons),
        }
    )
)
