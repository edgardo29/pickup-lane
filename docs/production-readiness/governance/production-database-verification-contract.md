# Production Database Verification Contract

This document is the current behavioral authority for repository-owned
production database verification. Historical WS04 plans and evidence records
remain provenance; active tests must not depend on their wording or pass-based
ownership.

The machine-readable companion is the
[production database verification contract](production-database-verification-contract.json).

## Provider-independent template

Before final production infrastructure is selected, the repository must retain
a complete verification template without inventing production values. The
template must:

- identify every required topology, connection-budget, role/grant, evidence,
  telemetry, rollback, and reassessment field;
- keep final provider, deployment, capacity, pool, and role/grant facts deferred
  with null values and explicit reasons;
- require a complete connection-budget formula covering steady API use,
  rolling overlap, non-API consumers, operational reserve, provider capacity,
  total peak, and remaining headroom;
- prohibit unsafe application-runtime privileges and require explicit evidence
  for ownership, search path, default privileges, and role attributes;
- reject credentials, private dashboard URLs, raw evidence, personal data, and
  other sensitive values from repository-safe evidence.

## Final production verification

Final production verification is mandatory before production closeout. It must
replace every deferred final fact with verified or explicitly not-applicable
evidence, including:

- selected database service and control plane;
- direct, pooled, or proxied connection mode and applicable ceilings;
- API instance/process/autoscaling/rolling-overlap topology;
- deployed pool values and connection-wait behavior;
- deployment-wide peak connection budget and positive headroom;
- effective application, migration, ownership, support, reporting, backup, and
  human-access roles and grants;
- evidence source metadata, sanitized repository references, reviewer, date,
  open gaps, telemetry, and safe-adjustment/rollback obligations.

Temporary development or demo infrastructure is not final production evidence.
No production value may be inferred from local, CI, framework, or temporary
service defaults.

This evidence contract does not itself authorize production application source,
database migrations or schema changes, deployment settings, service settings,
credentials, or changes to real production roles and grants.

## Compatibility and provenance

The
[historical WS04 evidence record](../planning/passes/ws04/ws04-01c-production-database-evidence-contract.json)
remains unchanged and is not the active contract. The current governance JSON
preserves its operational field coverage while using functional owners and
final-verification states instead of pass IDs.
