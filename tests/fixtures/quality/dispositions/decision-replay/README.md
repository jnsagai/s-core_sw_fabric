# Synthetic 005 quality decision fixture

These records demonstrate contract replay only. The signed decision uses the existing
public test key in [fixture trust](../../../assurance/fixture-trust/README.md), with
synthetic actor/authority IDs and declared December 2026 evaluation time. No human
engineering decision, adopted MISRA category, protected execution or production approval
is claimed. The invented `fixture_allowed` category is explicitly test only.

`binding.json` retains a local Clang-Tidy finding and proposal, exact source/tool/config
selection and synthetic category policy. `assessment.json` extends the existing synthetic
004/005 candidate/source closure with those exact binding, source and policy-source bytes;
its existing native IDs/statuses are preserved as fixture data. `result.json` retains both
historical independent replay and the current gate/decision classification. The temporary
paths are historical provenance; independent 005 replay uses retained original bytes.

The generator is `tests/quality_decision_support.py`; production code imports no fixture
builder or private signing material. Test keys cannot authenticate production. All results
remain `not_eligible`, with engineering readiness `not_evaluated`. Production profiles,
category mappings and native suppression files are unchanged.
