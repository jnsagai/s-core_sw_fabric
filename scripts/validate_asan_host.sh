#!/usr/bin/env bash
# Run explicitly from the normal terminal; preserve original native sanitizer settings.
set -u -o pipefail

quality_previous=""
case "${1:-}" in
  "") full=false; expected_arguments=0 ;;
  --full) full=true; expected_arguments=1 ;;
  --resume) full=true; expected_arguments=2; quality_previous=${2:-} ;;
  *) printf 'Usage: bash scripts/validate_asan_host.sh [--full | --resume EVIDENCE_DIRECTORY]\n' >&2; exit 2 ;;
esac
if (( $# != expected_arguments )); then
  printf 'Usage: bash scripts/validate_asan_host.sh [--full | --resume EVIDENCE_DIRECTORY]\n' >&2
  exit 2
fi

quality_repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P) || exit 2
cd -- "$quality_repo" || exit 2
quality_evidence=$(mktemp -d /tmp/score-quality-asan-host.XXXXXXXX) || exit 2
export UV_CACHE_DIR=/tmp/s-core-quality-uv-cache
printf 'Evidence directory: %s\n' "$quality_evidence"

phase() {
  local name=$1 expected=$2
  shift 2
  "$@" > "$quality_evidence/$name.log" 2>&1
  local actual=$?
  printf '%s: exit %s (expected %s)\n' "$name" "$actual" "$expected" |
    tee -a "$quality_evidence/status.txt"
  if (( actual != expected )); then
    cat -- "$quality_evidence/$name.log"
    printf 'Validation incomplete. Evidence retained: %s\n' "$quality_evidence" >&2
    exit 1
  fi
}

phase sync 0 uv sync --frozen
if [[ -n "$quality_previous" ]]; then
  printf '%s\n' "$quality_previous" > "$quality_evidence/previous-evidence.txt"
  phase records 0 uv run --frozen python scripts/verify_asan_host_records.py \
    "$quality_previous" --integration
else
  phase capabilities 0 uv run --frozen score-fabric quality capabilities --adapter asan \
  --request examples/quality/asan-capabilities.yaml --out "$quality_evidence/capabilities.json" --json
  phase seeded 1 uv run --frozen score-fabric quality run --adapter asan \
  --request examples/quality/asan-run.yaml --out "$quality_evidence/seeded.json" --json
  phase corrected 0 uv run --frozen score-fabric quality run --adapter asan \
  --request examples/quality/asan-correction-run.yaml --out "$quality_evidence/corrected.json" --json
  phase records 0 uv run --frozen python scripts/verify_asan_host_records.py "$quality_evidence"
  phase integration 0 timeout --signal=TERM --kill-after=10s 300s uv run --frozen pytest -q \
  'tests/integration/test_quality_complementary.py::test_genuine_available_seed_and_fresh_fix[asan-heap-buffer-overflow]' \
  'tests/integration/test_quality_dispositions.py::test_real_correction_and_immutable_stale_history[asan]' \
  'tests/integration/test_quality_import.py::test_genuine_outputs_seed_fix_and_portable_import[asan]' \
  --junitxml="$quality_evidence/integration.xml"
fi

if "$full"; then
  export SCORE_SOURCE=/home/jefferson/score
  export SCORE_CPP_POLICIES_SOURCE=/tmp/s-core-foundation/references/score_cpp_policies
  export SCORE_TIME_SOURCE=/tmp/s-core-foundation/references/time
  export CODEQL_CODING_STANDARDS_SOURCE=/tmp/s-core-foundation/references/codeql-coding-standards
  export CODEQL_RECONCILIATION_SOURCE=/tmp/quality-010-codeql-reconcile
  export CODEQL_MISRA_COMPILED_PACK=/home/jefferson/.local/share/s-core-tools/codeql-coding-standards-2.61.0
  export CODEQL_CODING_STANDARDS_ARCHIVE=/home/jefferson/.local/share/s-core-tools/downloads/codeql-coding-standards-2.61.0/coding-standards-codeql-packs.zip
  export SCORE_CODEQL_PREREQUISITE_REQUEST="$quality_repo/examples/quality/codeql-prerequisites.yaml"
  phase ruff 0 uv run --frozen ruff check .
  phase format 0 uv run --frozen ruff format --check .
  phase mypy 0 uv run --frozen mypy src scripts/verify_asan_host_records.py
  phase foundation 0 uv run --frozen python scripts/check_foundation.py
  phase regression 0 timeout --signal=TERM --kill-after=10s 900s uv run --frozen pytest \
    --ignore=tests/integration/test_workflow_compiler_native.py -q --tb=short \
    --junitxml="$quality_evidence/regression.xml"
  phase build 0 uv build --offline
fi
printf 'Validation passed for the selected checks; engineering acceptance remains pending.\n'
printf 'Evidence directory: %s\n' "$quality_evidence"
