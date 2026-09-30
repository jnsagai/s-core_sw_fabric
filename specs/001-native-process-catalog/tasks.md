# Tasks: Native process catalogue

Implementation and selected native process baseline validation are complete on
branch 001-native-process-catalog. The acceptance record contains the fresh
export, locked minimal consumer, native docs check, full-catalogue import and
negative contracts. The full score/module_template documentation bundles remain
unverified outside this bounded acceptance. No target engineering acceptance or
increment 002 implementation is implied.

- [x] T001-01 [US1] FAB-006: verify source locks, create disposable native export build and minimal licensed fixture; files `tests/fixtures/native/{README.md,LICENSE,source,needs.json,export-manifest.yaml}`, `acceptance.md`; deps reviewed 000; evidence AC001-01/02/09/10/12 including exact Bazel command, dependency resolution and output hashes. Never build in references.
- [x] T001-02 [US1/US2] FAB-006/FAB-007: finalize strict source/export/type/entity/relation models and schemas from real output; files `process_source/models.py`, `catalog/models.py` under `src/score_sw_fabric/`, `schemas/source-manifest.schema.json`, `schemas/catalogue.schema.json`, `contracts/catalogue.md`; deps T001-01; evidence versioned schema contract cases AC001-03/04/06/11; record model-library choice. Do not implement forward gate/evidence contracts.
- [x] T001-03 [US2] FAB-007: implement bounded local manifest/export loading, duplicate JSON-key detection, digest/root/path validation and typed diagnostics; files `process_source/reader.py`, `tests/contract/test_source_import.py`; deps T001-02; evidence AC001-06/07/11, no remote/script execution and unchanged previous output on failure.
- [x] T001-04 [US1] FAB-006: import metamodel rules, restore per-version defaults, preserve entities/source maps/template flags and metadata; files `catalog/importer.py`, `process_source/locations.py`, `tests/contract/test_native_catalogue.py`; deps T001-03; evidence AC001-02/03/09/10/11 and native IDs/version distinctions.
- [x] T001-05 [US1/US2] FAB-006/FAB-007: resolve source-qualified links/selectors with explicit namespace ambiguity and version checks; files `catalog/relations.py`, `tests/contract/test_relations.py`; deps T001-04; evidence AC001-04/05, forward/backlink distinctions and no scheduling inference.
- [x] T001-06 [US3/US2] FAB-007: canonical export/digest plus CLI atomic output and diagnostics; files `catalog/export.py`, `cli.py`, `tests/contract/test_catalogue_cli.py`; deps T001-05; evidence AC001-08 and documented exits (0 generation,1 semantic failure,2 input/infrastructure), read-only inputs and no partial-success artifact.
- [x] T001-07 [US1/US2/US3] FAB-006/FAB-007: run fresh native integration/negative contracts and reconcile evidence; files `tests/integration/test_native_export.py`, `README.md`, `acceptance.md`, supported-schema documentation and requirement index; deps T001-06; evidence all AC001-01–12, lint/type/package checks and explicit blocked native cases. Update source locks only with reviewed compatibility evidence; stop before 002 implementation.
