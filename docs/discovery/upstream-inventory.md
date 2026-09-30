# Upstream inventory

Inspected 2026-09-27. Source inspection is distinct from executable compatibility.
Existing implementation baseline: `b11332e17aa1ea4b920c24af9d9a20b18fc71ade`, branch
`main`, tracked LICENSE only. The supplied brief was untracked and is preserved.
No applicable ancestor/root AGENTS.md existed before bootstrap. Reference instructions
were read; their development/build rules do not authorize mutations to references.
The original sandbox could not start (`mountinfo path is not absolute`); approved
escalated commands were used. No sandbox protection is claimed for these checks.

## Exact pins and licenses

`upstream.lock.yaml` owns immutable IDs, relevant source paths and inspected file hashes.
Local locations are in `reference-workspace.json`; temporary clones are not installation
prerequisites and can be reconstructed from URLs/commits.

| Source | Commit | Revision label (not always release) | License evidence |
| --- | --- | --- | --- |
| score | `e2373d822fc2f6e9a3f8a0538904f3faa39309ea` | v0.7.2-43-ge2373d822fc | Apache-2.0; [score: LICENSE](https://github.com/eclipse-score/score/blob/e2373d822fc2f6e9a3f8a0538904f3faa39309ea/LICENSE) |
| mcp-servers | `29aeaa8251bd006d7ed3b0ea64229ea8589ce826` | 29aeaa8 | Apache-2.0; [mcp-servers: LICENSE](https://github.com/eclipse-score/mcp-servers/blob/29aeaa8251bd006d7ed3b0ea64229ea8589ce826/LICENSE) |
| fabro-nightly | `1b4fb15281ebb724426f9e480dce48d0100ff79b` | v0.362.0-nightly.0-200-g1b4fb1528 | MIT; [fabro-nightly: LICENSE.md](https://github.com/fabro-sh/fabro/blob/1b4fb15281ebb724426f9e480dce48d0100ff79b/LICENSE.md) |
| codeql-coding-standards | `06dc6bc32b05152fbe94dbf341a3e854574c9df5` | v2.61.0 | MIT; [codeql-coding-standards: LICENSE.md](https://github.com/github/codeql-coding-standards/blob/06dc6bc32b05152fbe94dbf341a3e854574c9df5/LICENSE.md) |
| docs-as-code | `d5f3de608cdfc034952c57d40979c78d8cd35957` | v8.2.0 | Apache-2.0; [docs-as-code: LICENSE](https://github.com/eclipse-score/docs-as-code/blob/d5f3de608cdfc034952c57d40979c78d8cd35957/LICENSE) |
| fabro-stable | `497aaba6f20c1fac052346c39f52e08fabadb179` | v0.254.0 | MIT; [fabro-stable: LICENSE.md](https://github.com/fabro-sh/fabro/blob/497aaba6f20c1fac052346c39f52e08fabadb179/LICENSE.md) |
| module_template | `c4d4ad090c6584e58279f0e5d0b6894f7fc4cf0d` | c4d4ad0 | Apache-2.0; [module_template: LICENSE](https://github.com/eclipse-score/module_template/blob/c4d4ad090c6584e58279f0e5d0b6894f7fc4cf0d/LICENSE) |
| process_description | `98d1d5f42dad412a09a888ea25e59c62fa6371ce` | v2.1.2 | Apache-2.0; [process_description: LICENSE](https://github.com/eclipse-score/process_description/blob/98d1d5f42dad412a09a888ea25e59c62fa6371ce/LICENSE) |
| reference_integration | `c4084156ccf7df963b7499fe5c2f67764496e8ae` | c408415 | Apache-2.0; [reference_integration: LICENSE](https://github.com/eclipse-score/reference_integration/blob/c4084156ccf7df963b7499fe5c2f67764496e8ae/LICENSE) |
| score_cpp_policies | `9bcfe8296038569a0ff7627fb8ce7a189018a7b3` | 9bcfe82 | Apache-2.0; [score_cpp_policies: LICENSE](https://github.com/eclipse-score/score_cpp_policies/blob/9bcfe8296038569a0ff7627fb8ce7a189018a7b3/LICENSE) |
| spec-kit | `e77daa9021d20db26b878f7dfa5640fe5a42d04e` | v1.0.12 | MIT; [spec-kit: LICENSE](https://github.com/github/spec-kit/blob/e77daa9021d20db26b878f7dfa5640fe5a42d04e/LICENSE) |
| time | `3723ce687e4abc7d6cb4c0efdbbd30455ed7c303` | 3723ce6 | Apache-2.0; [time: LICENSE](https://github.com/eclipse-score/time/blob/3723ce687e4abc7d6cb4c0efdbbd30455ed7c303/LICENSE) |

Query-source MIT has exceptions for CERT help (CC-BY-4.0) and bundled notices;
CodeQL CLI entitlement is unresolved and separate. No analyzer binary or proprietary
MISRA text is redistributed. Spec Kit MIT text is retained in LICENSE.spec-kit.
Existing project Apache-2.0 licensing is preserved, not newly selected.

## Compatible baseline selection

The platform and module template declare process 2.1.2 / docs-as-code 8.2.0 in their
MODULE.bazel. Those declarations, not unrelated latest branches, select the native
catalogue baseline. Process 2.1.2 itself declares docs-as-code 8.0.1. Consumer Bazel
resolution and native checks at 8.2.0 are **not yet build-verified**. Sphinx-Needs
8.3.1 is pinned in docs-as-code's hashed requirements. Increment 001 must preserve
resolved dependency and export manifests from a disposable consumer checkout.

The process build hook creates a .venv and training portals beside sources. Never
run it in a reference clone. Native commands discovered from docs.bzl are
`bazel build //:needs_json` and `bazel run //:docs_check`; neither was run here.
Bazel/bazelisk were absent on PATH. Published `/main/needs.json` is mutable and is
not an acceptable substitute for a commit-bound export.

Fabro source inspection includes stable v0.254.0 and the existing nightly SHA.
Stable lacks immutable workflow registration; nightly changes engine/checkpoint
internals and is unvalidated. No runtime release is selected. Resolve before 003/006,
without installing an unreviewed nightly or weakening registration requirements.

The time example declares CodeQL 2.21.4 and coding-standards 2.61.0, confirmed by the
query release's supported_codeql_configs.json. It uses a score_cpp_policies Git
override `9e3800913a3a7ac791d5e6fb9e7339d1e65980f9`; the inspected policy HEAD differs.
This foundation records that difference and does not claim a tested quality stack.
The exact override and report Python 3.9 environment need inspection before 010.
Reference integration is a future scope example, not a validated platform baseline.

## Actual discovery and adoption state

See [native review](native-source-review.md) for metamodel, wrapper/child statuses,
versioned links, template/FMEA/DFA/FDR/verification plans, source mounts and APM tools.
See [runtime review](runtime-source-review.md) for exact grammar/API/code paths,
automatic/default/replay hazards, provider limitations and CodeQL terms.

PR #3140 is open/unmerged at head `da32256d65692eef24c0bbb23d69016a83594239`.
All 13 issue comments, 8 review comments and 11 reviews were retrieved with pagination.
The discussion challenges duplicated artifacts, missing feedback loops and assumed
qualification; a later comment links a metamodel-flow sidecar at a different commit.
That package is absent from the selected MCP checkout, so it is a proposal/reference,
not an installed capability. PR #3188 is open/unmerged at head
`1c87bf2a7b39a803fd23b8b651a76fd2c6d66f7a`; 10 issue comments, no review comments or
submitted reviews. Its proposed DR contains `status: accepted` while its note still
says proposed. Neither field overrides actual adoption state.
Read-only API snapshots were fetched into `/tmp/s-core-foundation/api/` and summarized
in [PR evidence](upstream-prs.json). No comments or upstream changes were made.

Optional x-verse_fabric was only checked for baseline: commit
`3dba87565ca41f4dcae5595fb3c18e84210c640d`, pre-existing untracked
`.fabro/workflows/xcom-t010-flash-repair/`. It is not a dependency. No session writes targeted it; final observation found additional
external changes, preserved and listed in `docs/evidence/000/references.json`.

## Reproducible inspection

For each source: `git -C <path> rev-parse HEAD`, `git -C <path> status --porcelain`,
then read the paths and verify SHA-256 values in the lock. Fresh clones use the recorded
URL and detached commit. Do not fetch/reset existing reference clones to obtain pins.
Commands/results and known failed exploratory paths are retained in the 000 evidence.
