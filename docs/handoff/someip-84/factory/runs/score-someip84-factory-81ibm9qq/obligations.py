"""Sourced operational obligations for the owner-authorized expanded overnight run."""

CHECKS = {
    "compiler_diagnostics": 300,
    "focused_coverage": 300,
    "focused_asan_lsan": 300,
    "focused_tsan": 300,
    "focused_clang_tidy": 300,
    "focused_cppcheck": 300,
    "focused_memcheck": 300,
    "secret_dependency_checks": 300,
    "native_build": 900,
    "native_tests": 900,
    "native_coverage": 900,
    "native_lint": 900,
    "native_sanitizers": 900,
    "native_tsan": 900,
    "native_integration": 900,
    "native_performance": 600,
    "cross_compilation": 900,
    "native_docs": 600,
    "native_traceability": 600,
    "format_precommit": 600,
    "codeql_security": 900,
    "codeql_misra": 900,
    "process_checks": 120,
    "tool_assurance": 120,
    "verification_report": 120,
    "rework_progress": 120,
}

TASKS = [
    (
        "coverage_review",
        (
            "Assess measured line AND branch coverage against 85% QM and 100% "
            "safety platform goals; SOME/IP CI's 73% line threshold is separate. "
            "Do not choose the safety class or accept a deviation. List uncovered "
            "changed lines/branches and concrete follow-up tests."
        ),
        False,
    ),
    (
        "misra_applicability",
        (
            "Draft the applicable MISRA C++:2023 assessment. Use the licensed "
            "source references and measured CodeQL results. The pinned mapping is "
            "draft and lacks an active CSV; keep unmapped and manual rules "
            "explicit, without reproducing proprietary rule text or claiming "
            "complete compliance."
        ),
        False,
    ),
    (
        "misra_manual_review",
        (
            "Draft manual coding-guideline inspection of the changed "
            "implementation. Cite source constructs, guideline identifiers only "
            "when verified, evidence and unresolved manual obligations. Review "
            "initialization, lifetimes, conversions, ordering, error handling and "
            "concurrency. Human inspection remains pending."
        ),
        False,
    ),
    (
        "finding_classification",
        (
            "Reconcile original compiler, Clang-Tidy, Cppcheck, sanitizer and "
            "CodeQL findings. Preserve native IDs and severities; distinguish "
            "suggested Critical/High/Medium/Low ratings from authorized ratings "
            "and retain dependency findings. Never silently filter findings."
        ),
        False,
    ),
    (
        "deviation_drafts",
        (
            "Draft narrowly scoped deviation or false-positive proposals bound to "
            "exact rule, finding and source hashes; include rationale, "
            "alternatives, risk, compensating checks and review/expiry triggers. "
            "Every acceptance and risk decision remains unanswered."
        ),
        False,
    ),
    (
        "native_build_review",
        (
            "Review native build and full test outputs, selected toolchain and "
            "target identities. Separate actual results from unavailable "
            "dependencies and platform/configuration gaps. Focused GCC tests "
            "cannot satisfy full Bazel readiness."
        ),
        False,
    ),
    (
        "integration_aou_review",
        (
            "Review component/feature/platform integration, interface tests, "
            "external-component assumptions of use and QEMU results. Distinguish "
            "S-CORE reference integration from final-product integrator "
            "obligations and identify missing requirement links."
        ),
        False,
    ),
    (
        "sanitizer_review",
        (
            "Review ASan, LSan, UBSan and TSan outputs and scope. Distinguish "
            "runtime startup/infrastructure failures from source defects. Check "
            "runtime connector teardown/slot reuse coverage; focused identifier "
            "tests do not cover the runtime suite."
        ),
        False,
    ),
    (
        "performance_review",
        (
            "Review resource-usage, benchmark and profiling outputs against "
            "source-defined expectations. Record unmeasured latency, throughput "
            "and memory limits and unavailable perf/KVM prerequisites; invent no "
            "acceptance thresholds."
        ),
        False,
    ),
    (
        "cross_target_review",
        (
            "Review x86_64/aarch64 Linux cross-build results and documented "
            "QNX/integrator obligations. Unknown QNX SDK entitlements and actual "
            "target execution remain blockers; never acquire credentials or infer "
            "qualification."
        ),
        False,
    ),
    (
        "traceability_review",
        (
            "Review descriptions, TestType, DerivationTechnique, "
            "PartiallyVerifies/FullyVerifies links, requirement/interface types, "
            "source/design consistency and docs metrics. Missing links remain "
            "missing; the nonblocking CI traceability gate is not acceptance."
        ),
        False,
    ),
    (
        "tool_assurance_review",
        (
            "Draft tool identification, exact versions/configuration/digests, "
            "tool-impact and error-detection questions, confidence/qualification "
            "evidence inventory. Tool execution alone does not qualify the tools; "
            "owner acceptance stays pending."
        ),
        False,
    ),
    (
        "security_review",
        (
            "Review measured public CodeQL security-and-quality results, "
            "dependency and secret-scanning applicability, vulnerability "
            "disposition and changed API exposure. Preserve extraction scope and "
            "licensing limits. Do not upload reports or accept security risk."
        ),
        False,
    ),
    (
        "design_inspection_draft",
        (
            "Draft implementation inspection against specification, design, "
            "external libraries, static/dynamic analysis, manual coding checks and "
            "interface/traceability consistency. Draft remaining safety analysis "
            "FMEA/DFA impact questions; do not act as the independent reviewer."
        ),
        False,
    ),
    (
        "verification_report_draft",
        (
            "Prepare module verification report and release-evidence archive index "
            "with exact test IDs, pass/fail/skipped/unexecuted results, source "
            "hashes, coverage, analyzer findings and earlier attempts. All "
            "unexecuted applicable checks and deviations remain blockers."
        ),
        False,
    ),
    (
        "independent_review_handoff",
        (
            "Prepare an unanswered independent-review handoff: author/approver "
            "separation, safety/security/quality roles, qualification acceptance, "
            "deviations, test independence and integration/release decisions. No "
            "AI or native successful run counts as human approval."
        ),
        False,
    ),
]

SOURCES = {
    "coding_guidelines": (
        "score",
        "e2373d822fc2f6e9a3f8a0538904f3faa39309ea",
        "docs/contribute/development/cpp/coding_guidelines.rst",
    ),
    "code_analysis": (
        "score",
        "e2373d822fc2f6e9a3f8a0538904f3faa39309ea",
        "docs/contribute/development/cpp/code_analysis.rst",
    ),
    "misra_mapping": (
        "score",
        "e2373d822fc2f6e9a3f8a0538904f3faa39309ea",
        "docs/contribute/development/cpp/misra_2023_rule_mapping.rst",
    ),
    "verification_plan": (
        "score",
        "e2373d822fc2f6e9a3f8a0538904f3faa39309ea",
        "docs/platform_management_plan/software_verification.rst",
    ),
    "development_plan": (
        "score",
        "e2373d822fc2f6e9a3f8a0538904f3faa39309ea",
        "docs/platform_management_plan/software_development.rst",
    ),
    "tool_management": (
        "score",
        "e2373d822fc2f6e9a3f8a0538904f3faa39309ea",
        "docs/platform_management_plan/tool_management.rst",
    ),
    "verification_process": (
        "process_description",
        "98d1d5f42dad412a09a888ea25e59c62fa6371ce",
        "process/process_areas/verification/guidance/verification_process_reqs.rst",
    ),
    "verification_guideline": (
        "process_description",
        "98d1d5f42dad412a09a888ea25e59c62fa6371ce",
        "process/process_areas/verification/guidance/verification_guideline.rst",
    ),
    "inspection_checklist": (
        "module_template",
        "c4d4ad090c6584e58279f0e5d0b6894f7fc4cf0d",
        "score/component_example/docs/detailed_design/chklst_impl_inspection.rst",
    ),
}
