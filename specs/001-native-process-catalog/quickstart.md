# Catalogue validation

From the repository root:

~~~
uv sync --frozen
uv run --frozen score-fabric catalog export --manifest tests/fixtures/native/export-manifest.yaml --out tests/fixtures/native/build/catalogue.json --json
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen mypy src
uv run --frozen pytest -q
~~~

The fixture is a byte-for-byte upstream checked-in Sphinx-Needs 8.3.1 expected
export, with pinned docs-as-code v8.2.0 metamodel and schema. Its export version
is the native empty string. The command is read-only with respect to source files.
The generated build directory can be removed after inspection.

For a fresh process export, follow tests/native_consumer/README.md in a disposable
workspace and compare the output with acceptance.md and evidence/process-needs.json.
The pinned minimal consumer passed both needs_json and docs_check. Full
score/module_template documentation builds remain unverified. Neither fixture nor
native-build success establishes engineering readiness.
