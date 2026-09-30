# Delivered foundation CLI

`score-fabric --help`, `score-fabric --version`, `score-fabric doctor [--root PATH] [--json]`.
Only two lock-file envelopes are read; unknown command/options use argparse exit 2.
Doctor JSON includes schema_version, scope=fabric_foundation_files, outcome, per-path
checks, engineering_readiness=not_evaluated, runtime_integration=not_implemented and
limitations. Exit 0 is file-envelope success only; missing/invalid locks return 2.
No credentials, remote capabilities or native engineering gates are inspected.
