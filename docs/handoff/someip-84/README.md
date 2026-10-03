# SOME/IP #84: duplicate-server version handling

Status: draft native contribution; full native validation and engineering review pending.

## Factory execution status

This candidate was researched and implemented directly in the Codex session.
Compiler, test and analyzer commands were launched directly through terminal tools.
Fabro did not orchestrate this work: there is no Fabro run ID, admitted factory agent execution, checkpoint history or factory collector receipt for this candidate.
The retained logs are measurements from the direct local trial, pending provenance and engineering review.

This work does not demonstrate the software factory implementing a native S-CORE feature.
The user identified that execution gap after reviewing the result.
The intended next work is to use SOME/IP as a factory demonstrator: bind native intent and sources, admit the supported agents/tools, let Fabro own execution and run state, collect exact evidence, and stop at required human gates.
Existing live-model profiles remain disabled and target CodeQL execution through the public fabric adapter remains inspection-only.
Those factory gaps must be handled explicitly in the bounded fabric workflow.

The [factory execution correction](factory/README.md) now adds real packaged command
bindings and a natively validated Fabro measurement workflow. A fresh host run executes
the baseline and external-candidate regression through Fabro; its own run records are
separate from the original direct trial. DeepSeek Flash is user-selected for the remaining
implementation stage, with provider credential and runtime admission/binding still pending.

## Scope

This is the first bounded slice of [Revise version handling in socom (#84)](https://github.com/eclipse-score/inc_someip_gateway/issues/84), authorized by the user's instruction to proceed with a C++ SOME/IP feature.

SOCom's `Service_database` groups connections by service ID, major version and instance.
The original `Service_instance_identifier` comparison also includes minor version.
Consequently, constructing another server for the same registration slot with a different minor version succeeds instead of returning `Construction_error::duplicate_service`.
Enabling both servers can then reach the duplicate-server assertion in `Service_record::register_server_connector`.
This crash path is inferred from the native source; the local reproduction exercises the faulty registration key.

The patch aligns the duplicate-server key with the existing database key.
It adds 13 focused registration-key tests and eight runtime cases covering disabled/enabled servers, minor-version boundaries and slot reuse after destruction.
The focused tests have their own native Bazel target, `//score/socom/test/unit:service_identifier_test`.
The runtime cases belong to the existing `//score/socom/test/unit:socom_test` target.

Issue #84 also proposes changes to public identifier types, discovery requests and minor-version representation.
Those remain later slices requiring native design review.
This patch preserves the existing public interface representation and exact-major/minimum-minor connection rules.

## Source and artifacts

- Upstream: `eclipse-score/inc_someip_gateway`.
- Candidate baseline commit: `f8a196c3b16d5172d898394ab99b0ed81346d63d`.
- Verified Git tree: `826a77c2f3ec0838f37230319f9397e442cef407`.
- Acquisition: all 391 Git blobs verified, including executable modes and the `CLAUDE.md` symlink; the reconstructed tree hash matches the commit's tree.
- Baseline snapshot: `.tools/someip-84/baseline/` in the fabric workspace.
- Disposable implementation: `.tools/someip-84/work/`.
- Native temporary files, dependencies and databases: implementation `.llm_tmp/`.
- [Candidate patch](someip-84.patch): six native files; applies without whitespace errors and reproduces their recorded SHA-256 hashes.
- [Source manifest](source-manifest.json), [candidate file hashes](candidate-files.json), [GoogleTest manifest](googletest-manifest.json), [baselibs header manifest](baselibs-manifest.json).
- [Issue snapshot](issue-snapshot.json): upstream proposal and observed native issue status.
- Upstream [LICENSE](LICENSE) and [NOTICE](NOTICE) accompany the patch.

The baseline is selected for this trial; promotion to a reviewed fabric source lock remains pending.
Existing fabric source locks and engineering acceptance items retain their previous status.

## Validation

| Check | Result and limits |
| --- | --- |
| Original comparison with final regression source | 7 failures and 6 passes, expected exit 1 |
| Corrected comparison | All 13 focused tests pass, exit 0 |
| UBSan on corrected focused executable | All 13 tests pass, exit 0 |
| Runtime test syntax | Pass with upstream baselibs 0.2.13 and GoogleTest/GoogleMock 1.18.0 headers; existing GoogleMock deprecation warning retained |
| Local Clang-Tidy trial | Changed comparison TU passes LLVM 19.1.7 core analyzer/use-after-move checks; this is a bounded trial profile |
| Native Clang-Tidy configuration | Verification fails: unknown checks/options, including folded YAML comment text interpreted as check names |
| Full native Bazel tests | Pending: `bazel` is unavailable locally; attempted command exits 127 |
| Native pre-commit gate | Pending: `pre-commit` is unavailable locally; attempted command exits 127 |
| Patch application | Clean application to a disposable baseline copy, with exact candidate file hash verification |
| Fabric foundation consistency | Pass; existing requirements, dependency rows and reviewed source locks remain consistent |
| Fabric package build | Pass with the pinned build backend from a writable copy of the existing cache, using `uv build --offline` |

The local compiler is GCC 12.3.0; upstream pins GCC 12.2.0 and LLVM 22.1.7.
Native compiler and policy qualification remains pending.
Runtime cases were syntax checked and still require execution in the native build.
CodeQL results and their exact extraction scope are recorded in [evidence](evidence/README.md).
MISRA applicability, deviations and engineering acceptance remain pending.

## Native host validation

Use a normal terminal with Git, Bazel/Bazelisk honoring `.bazelversion` (8.6.0), pre-commit and dependency network access.
The following creates a fresh disposable checkout and applies the reviewable patch.
An existing `host` directory causes `git clone` to stop; preserve any existing checkout.

```bash
cd /home/jefferson/s-core_sw_fabric
(
    set -e
    fabric_root="$PWD"
    git clone --no-checkout https://github.com/eclipse-score/inc_someip_gateway.git \
        "$fabric_root/.tools/someip-84/host"
    cd "$fabric_root/.tools/someip-84/host"
    git checkout --detach f8a196c3b16d5172d898394ab99b0ed81346d63d
    git apply --check "$fabric_root/docs/handoff/someip-84/someip-84.patch"
    git apply "$fabric_root/docs/handoff/someip-84/someip-84.patch"
    mkdir -p .llm_tmp
    export TMPDIR="$PWD/.llm_tmp"
    export PRE_COMMIT_HOME="$PWD/.llm_tmp/pre-commit"
    bazel --output_user_root="$PWD/.llm_tmp/bazel" test --config=x86_64-linux \
        //score/socom/test/unit:all
    pre-commit run --all-files
)
```

The native `.pre-commit-config.yaml` and build configuration were inspected before preparing these commands.
The pre-commit gate includes `bazel mod tidy` and a lockfile check; review any resulting module/lockfile changes.
After these focused native checks, the upstream-required `bazel test //score/...` and native Clang-Tidy checks remain review gates.
Publishing, merging and engineering acceptance require their own authorization and human decisions.
