# <Domain> Backend Testing

Status: draft domain testing intent

## Authoritative Sources

- `docs/agent-notes/<domain>.md`
- `docs/production-readiness/planning/<pass>.md`

## Test Intent

Summarize the backend behavior this domain must prove. Point to source
documents instead of copying product specifications.

## Important Risks

- Authorization, ownership, and stale relationship states.
- Persisted side effects and prohibited side effects.
- PostgreSQL invariants and transaction behavior.
- Provider boundaries or explicit not-applicable decisions.

## Applicability Notes

Record meaningful `covered_elsewhere`, `not_applicable`, manual, or deferred
decisions with short reasons.

## Known Gaps

- `<GAP-ID>`: concise gap, owner/pass, and reason.

## Manifest

Machine-readable traceability lives in `testing_manifest.yaml` beside this
file. Keep the manifest small and source-linked.
