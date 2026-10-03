# Data model

All records carry schema_version, kind and canonical content digest. Paths are normalized relative
POSIX paths without traversal/symlinks. Unknown provider metrics are null. Human authority is never
stored as an agent-owned boolean.

- EvidenceReference: immutable path, sha256, bytes; safe root binding, verify before each query.
- EvidenceQuery: exact operation/filter/offset/limit; limit 1–30, bounded fields, counts include gaps.
- StageBudget: max_bytes 12,000/result, max_tokens 5,000/result and 12,000/stage; persistent queries
  and consumption, atomic locked write; rejected output never enters context.
- Usage: call/task/role/model/workflow/increment and nullable input/cache/output/reasoning/cost/time,
  calls/tools/corrections/escalations/critics; cache split sums exactly when all known.
- Impact: old/new indexes, direct and transitive keys, relation changes, unknowns and blockers.
- Classification: S0–S4 or unknown, deterministic reasons, policy digest, explicit scope facts.
- ContextManifest: task/baseline/index/impact/mapping digests, native IDs, primary/transitive paths,
  evidence refs; ordered and deterministic. Drift invalidates use.
- ContextBundle: mandatory L0/L1 + optional L2, selected observation metadata, rendered Skills,
  token accounting and omission reasons. Never silently truncate required context.
- SkillRegistry/Selection: ID/version/body and declared-reference digests, mapping, required and
  on-demand IDs. Changed bytes invalidate selection; undeclared references cannot load.
- GovernorDecision: narrowed limits/route/critic/stop reasons, admission + manifest + ledger digest;
  call_authorized remains false. No autonomous engineering acceptance.
- Progress/ModePlan/ReviewPack: measured fingerprints, explicit mode, mandatory checks/human gates,
  bounded summary/evidence refs. Plans are Fabro projections rather than execution/run state.
