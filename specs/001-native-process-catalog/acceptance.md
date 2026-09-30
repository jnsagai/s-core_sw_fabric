# Increment 001 acceptance record — 2026-09-27

Status: implementation complete for the pinned process_description 2.1.2 /
docs-as-code 8.2.0 baseline using the disposable minimal consumer. All AC001
scenarios below have actual evidence. This is a native catalogue result only:
engineering readiness remains not_evaluated. The full score and module_template
documentation bundles have not been built successfully and are not covered by
this compatibility claim. Increment 002 is untouched.

## Reproducible native build

The checked-in tests/native_consumer/ directory contains the exact minimal
MODULE.bazel, Bazel 8.7.0 selector, S-CORE registry configuration, BUILD
sentinel and MODULE.bazel.lock used here. The Bazel lock SHA-256 is
599b6a4d476fcb9b3df0b0d14bb726562db22355a7f0dfda55823597afe86c80.
Bazelisk 1.29.0 binary SHA-256 was
5a408715e932c0250d28bd84555f12edbf70117de42f9181691c736eacc4a992.
The consumer declares process 2.1.2, docs-as-code 8.2.0 and rules_python
1.8.5 with Python 3.12. The latter is required by the docs wheel set.

From the disposable minimal consumer workspace, the successful commands were:

~~~
BAZELISK_HOME=/tmp/s-core-001/bazelisk /tmp/s-core-001/bin/bazel --batch --output_user_root=/tmp/s-core-001/bazel-process-output build @score_process_description//:needs_json --jobs=2 --verbose_failures
BAZELISK_HOME=/tmp/s-core-001/bazelisk /tmp/s-core-001/bin/bazel --batch --output_user_root=/tmp/s-core-001/bazel-process-output run @score_process_description//:docs_check --jobs=2 --verbose_failures
BAZELISK_HOME=/tmp/s-core-001/bazelisk /tmp/s-core-001/bin/bazel --batch --output_user_root=/tmp/s-core-001/bazel-process-output build @score_process_description//:needs_json --jobs=2 --lockfile_mode=error --verbose_failures
~~~

The first build completed in 57.820 seconds with 62 actions. The docs check
completed with exit 0 after an exact copy of the process/ source tree and a
BUILD sentinel were placed in the disposable consumer; it reported zero schema
warnings. The locked rebuild completed with exit 0 and an action-cache hit.
Exact logs and the generated export are in evidence/. The build log SHA-256 is
a3538e6101b49cf1d1064f935ff40cbfd17e0a5e96ed49b8e64c3e5589e26a76;
the docs-check log SHA-256 is
4955165ffb8fdf6fb7ecaf2d0ae6e452bbd653e824fb098e1f73fc5ba79007b2.

The Bazel-resolved process source differs from the pinned commit
98d1d5f42dad412a09a888ea25e59c62fa6371ce only in registry-added
MODULE.bazel version/compatibility metadata. A recursive comparison found no
other differences, excluding MODULE.bazel.lock; all 315 process RST, Markdown
and Python files matched byte-for-byte. The metamodel and schema match pinned
docs-as-code commit d5f3de608cdfc034952c57d40979c78d8cd35957.
The native export is Apache-2.0 licensed; process-LICENSE is preserved beside it.

## Export and catalogue result

The fresh process-needs.json SHA-256 is
931f1a57ff36208807bfd901ab7eee8d6629edfe60e93790f3f45c70407d65f8.
Its selected version is 0.1, creator is sphinx_needs 8.3.1, defaults are
removed, and 1,251 needs are declared and present. Native schema validation
reported zero warnings; compatibility-findings.json reported zero findings.
These reports describe that native check only, not engineering acceptance.

The importer produced 1,251 entities, 50 native types and 7,056 directed
relation records (3,528 forward and 3,528 backlinks). Every entity has a
verified repository-relative RST path and source-content digest. The catalogue
digest is a69436e36d00e4950d46eb933488d5d71b806554da96902ca8ff6373c04727f3;
serialized JSON SHA-256 is
0dbbeac934314eb087d39692c1ce60765abeb7b5388044771db5f0840b6f9930.
The reviewed fresh-export manifest is in evidence/fresh-export-manifest.yaml;
its original operational paths refer to the disposable workspace.

Native work-product definitions found in the fresh export:

| ID | Type/version | Source RST line |
| --- | --- | --- |
| wp__feature_fmea | workproduct/1 | process/process_areas/safety_analysis/safety_analysis_workproducts.rst:27 |
| wp__feature_dfa | workproduct/1 | process/process_areas/safety_analysis/safety_analysis_workproducts.rst:38 |
| wp__sw_component_fmea | workproduct/1 | process/process_areas/safety_analysis/safety_analysis_workproducts.rst:51 |
| wp__sw_component_dfa | workproduct/1 | process/process_areas/safety_analysis/safety_analysis_workproducts.rst:65 |
| wp__fdr_reports | workproduct/1 | process/process_areas/safety_management/safety_management_workproducts.rst:80 |
| gd_temp__feat_saf_fmea | gd_temp/1 | process/process_areas/safety_analysis/guidance/fmea_templates.rst:20 |
| gd_temp__comp_saf_fmea | gd_temp/1 | process/process_areas/safety_analysis/guidance/fmea_templates.rst:41 |

The same complete source and manifest, copied under a second root, produced
byte-identical catalogue JSON. Changing one referenced RST file only in that
disposable copy changed the digest to
958105895bf955d14ba719a05dbf46e43d51e4d71a4855ebc89a581e880a28ba.

## Supported importer contract

The version-1 manifest binds local source/export/metamodel/schema paths to
SHA-256 and full Git commit IDs, records explicit source mounts and dependency
owners, and declares build provenance. The importer accepts only pinned
docs-as-code 8.2.0 metamodel/schema digests and Sphinx-Needs 8.3.1 sparse
version blocks. Individual input files are limited to 64 MiB. It restores
defaults from each selected version's schema, preserves unknown non-normative
metadata, and rejects unknown normative link fields, need parts, unsupported
selectors and unresolved/ambiguous relations. Plain IDs and exact
[version==N] selectors are supported; links, backlinks and narrative text
remain distinct. It never fetches a manifest URL or executes Sphinx config.

Canonical UTF-8 JSON includes source-content fingerprints and excludes
operational source roots and timestamps. Output must be inside the manifest
directory; it is atomically replaced after validation. Exit 0 means catalogue
generation only, exit 1 native semantic integrity failure, and exit 2 invalid
input/infrastructure. The model layer uses standard-library dataclasses and
TypedDict with PyYAML for bounded local YAML parsing; no schema execution
library or runtime database was added.

## Acceptance scenarios

| Scenario | Outcome | Evidence |
| --- | --- | --- |
| AC001-01 genuine fixture and fresh export | Pass | Byte-for-byte pinned docs-as-code fixture plus successful fresh process export/log. |
| AC001-02 FMEA/DFA/FDR definitions | Pass | Seven reviewed native work-product/template IDs and exact source lines above. |
| AC001-03 sparse defaults | Pass | Fixture and fresh 1,251-need export import with per-version defaults. |
| AC001-04 version selectors | Pass | Qualified resolution, mismatch and unsupported syntax contract cases. |
| AC001-05 namespace ambiguity/dangling link | Pass | Explicit owner, ambiguity and unresolved-target failures tested. |
| AC001-06 malformed schema/keys/identity | Pass | Creator/count/type/duplicate-key/duplicate-identity and normative-link failures tested. |
| AC001-07 hash/path/symlink | Pass | Tampering, traversal and source symlink escape rejected. |
| AC001-08 deterministic bytes/digest | Pass | Full-catalogue relocation equality and source-change sensitivity above. |
| AC001-09 template code blocks | Pass | Template keys/tags retained; code-block text never imported as instances. |
| AC001-10 source locations | Pass | All 1,251 live records verified; missing fixture source explicitly unavailable. |
| AC001-11 metadata/normative schema | Pass | Unknown record field retained; altered pinned metamodel and unknown link rejected. |
| AC001-12 native build failures visible | Pass | Initial module-template build interrupted for disk; minimal probe setup errors and corrections have retained logs. |

The earlier full module_template //:needs_json attempt analyzed 29,412 targets,
used about 14 GiB of temporary output and was interrupted with only 7.5 GiB
free. The later external process-target attempt in that workspace was also
interrupted as unrelated toolchains approached the disk guard. The minimal
probe initially lacked the S-CORE registry, Python 3.12, process/ source and
BUILD sentinel; the resulting diagnostic logs are retained in evidence/.
These failures are not hidden or misreported as process incompatibility.

## Initial validation and boundaries

With SCORE_NATIVE_EXPORT_MANIFEST set to the live disposable manifest, the full
suite passed 35 tests. Without that optional live input, 34 tests passed and
one fresh-build test skipped explicitly. Ruff lint/format, strict mypy,
scripts/check_foundation.py (64 FAB IDs and 19 dependency rows), and offline
wheel/sdist build passed. The generated export is preserved for review;
tests/native_consumer/ provides the rebuild recipe and lock.

Full score/module_template documentation bundle builds, Fabro/runtime and
engineering readiness evaluation remain outside this result. No imported
definition is itself a work-product review or accepted artifact. Stop before
implementing increment 002.


## Follow-on prerequisite review during 002 design — 2026-09-27

The read-only code review found that the original output guard could overwrite a native
metamodel schema or referenced RST, or create a file inside a declared source tree. All
three cases were reproduced through the real CLI in disposable fixture copies; each
incorrectly returned exit 0. No reference or project fixture was overwritten by the probes.
This was a gap in the prior source-write protection claim and acceptance coverage.

The writer now rejects every declared source-root destination before directory creation,
and includes the metamodel schema among protected input aliases. Three regression cases
require exit 2 and unchanged input bytes; the new-directory case also requires no directory
creation. AC001-07/08 and the CLI boundary evidence are supplemented by these cases.

Final checks after this correction:

- `uv run --frozen ruff check .`: passed.
- `uv run --frozen ruff format --check .`: passed.
- `uv run --frozen mypy src`: passed, 11 source files.
- `SCORE_NATIVE_EXPORT_MANIFEST=/tmp/s-core-001/fresh-export-manifest.yaml uv run --frozen pytest -q`: 38 passed.
- `uv run --frozen pytest -q`: 37 passed, one optional live test skipped.
- `uv build --offline`: wheel and sdist built successfully.

The correction changes only allowed output destinations. Native export, catalogue digest,
source pins and native build proof remain unchanged. No 002 planner is implemented by this fix.
