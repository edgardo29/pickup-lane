# Production-Readiness Pass Execution Register

This register records accepted implementation history, current work, and
remaining production-readiness units.

The corrected master blueprint controls current production-readiness scope and
roadmap. The original 42 parent entries and prior decompositions remain useful
historical provenance, but they do not restore scope rejected by the corrected
master. This register is a navigation and execution-state record used with
current `develop`, applicable prerequisites, and the corrected master.

The register does not, by itself, authorize implementation or invent ordering
when durable authority leaves multiple equally valid choices.

## 1. Current Basis

| Field | Value |
|---|---|
| Register purpose | Distinguish original blueprint parent passes from actual executable passes and record accepted progression state. |
| Current reconciliation point | 39 passes are accepted in `develop`, including `WS03-05A` and accepted WS04/WS05 work; `WS03-05B` is implemented in open PR #176 but unmerged and requires the correction defined by the corrected master before it may merge. |
| Current accepted develop SHA at reconciliation | `662c4ae4536e1fb266e5a25b88ae48681f5a9bab`. |
| Historical blueprint register | 42 original parent-level planned entries, retained as provenance. |
| Accepted implemented passes | 39 merged/accepted passes. |
| Implemented but unmerged | `WS03-05B` in PR #176; correction required before merge. |
| Remaining roadmap | 27 genuinely unimplemented units under section 8 of the corrected master. |
| Next unit selected by this register? | Not by itself. Use the corrected master, applicable prerequisites, current `develop`, and owner selection when more than one unit is valid. |

The recorded accepted `develop` SHA is a historical reconciliation basis for
this register version. It is not a mutable instruction and is not the
current-session source of truth. Current execution always comes from current
`origin/develop`, current repository state, durable authority, and the current
production-readiness run instruction.

## 2. Program Summary

| Metric | Count | Meaning |
|---|---:|---|
| Historical parent-level entries | 42 | Original planning inventory retained as provenance. |
| Merged/accepted implemented passes | 39 | Current authoritative audit status from the corrected master. |
| Implemented but unmerged passes | 1 | `WS03-05B` in PR #176; not accepted or merge-ready. |
| Genuinely unimplemented remaining units | 27 | Corrected roadmap units in master section 8. |

Count magnitude is not production-readiness proof. Completion depends on the
actual surviving safety obligations and final evidence required by the corrected
master.

## 3. How To Use This Register

Before starting or resuming production-readiness work:

1. Read the read-first document, program context, and applicable workflow.
2. Identify the current parent blueprint pass or accepted executable child from
   current repository state.
3. Check this register for accepted implementation, dependency state, and
   remaining corrected scope.
4. Use Stage 0 only when the selected unit genuinely needs scoping or
   decomposition; create a planning artifact only when the work is complex
   enough to need one.
5. Determine subsequent work from the corrected master, applicable
   prerequisites, current repository truth, and owner direction.
6. If more than one unit is valid and the corrected master does not select one,
   stop for owner selection.
7. Never infer progression from alphabetical order, filename order, stale branch
   names, or old chat context.
8. Apply the final-infrastructure timing rule from the read-first document,
   Program Context, implementation workflow, and master blueprint. Temporary
   Vercel, Render, and Neon demo/prototype values do not satisfy final-production
   provider, topology, configuration, capacity, or runtime prerequisites. When a
   parent mixes provider-independent work with final-infrastructure-dependent
   work, keep executable work provider-neutral where practical and record the
   remaining provider-specific obligation with its owner, trigger, and required
   completion boundary.

## 4. Original Blueprint Parent-Pass Register

The table below mirrors the original 42 parent-level planned passes for
navigation. It does not replace the master blueprint.

| Blueprint pass | Title | Execution-register state |
|---|---|---|
| `BASE-00` | Repository baseline and isolation gate | Historical program setup predecessor; no current executable scope. |
| `GOV-01` | Import and reconcile the approved governance package | Historical governance predecessor; no current executable scope. |
| `EN-01` | Early current-test taxonomy and isolation baseline | Accepted executable pass. |
| `EN-02` | Early correlation, event-envelope, and redaction contract | Accepted executable pass. |
| `EN-03` | Early secrets, control-plane access, and evidence-handling foundation | Accepted executable pass. |
| `WS02-01` | Typed settings and environment isolation | Accepted executable pass. |
| `WS02-02` | Runtime process, lifecycle, health, and deployability | Accepted executable pass. |
| `WS02-03` | Proxy, host, TLS, CORS, and response-class security headers | Accepted executable pass. |
| `WS02-04` | Request limits, timeouts, rate controls, and stable errors | Decomposed into accepted executable child passes `WS02-04A` through `WS02-04C3B`; source-owned closeout recorded. |
| `WS02-05` | HTTP contracts, schemas, docs, cache, and end-to-end chain | Decomposed into accepted executable child passes `WS02-05A`, `WS02-05B1`, and `WS02-05B2`. |
| `WS03-01` | Identity authority and verifier-controlled field protection | Accepted executable pass. |
| `WS03-02` | Provisioning, account-state lifecycle, and concurrent first login | Accepted executable pass. |
| `WS03-03` | High-risk authentication and Firebase control verification | Decomposed into accepted executable child passes `WS03-03A` and `WS03-03B`. |
| `WS03-04` | Complete authorization matrix and negative proof | Decomposed into accepted executable child passes `WS03-04A`, `WS03-04B`, `WS03-04C`, and `WS03-04D`; WS03-04 parent complete, with the Stripe webhook lifecycle gap explicitly covered elsewhere by `WS05`. |
| `WS03-05` | Moderation states, safe notices, and minimum-necessary admin data | `WS03-05A` is accepted. `WS03-05B` is implemented but unmerged and must be reduced to the corrected master target before merge. Corrected `WS03-05C` and `WS03-05D` scope remains in master section 8.1. |
| `WS04-01` | Database engine/session lifecycle, connection budget, and least-privilege roles | Structurally revised after accepted `WS04-01A` and `WS04-01B`: revised `WS04-01C` accepted the provider-independent production-verification framework; final production topology/budget/role proof is preserved for mandatory later `WS04-01D` after final infrastructure is selected. |
| `WS04-02` | Transactions, invariants, locks, and deterministic concurrency | Accepted children `WS04-02A`, `WS04-02B`, and `WS04-02C`; later-owned corrected-master work remains outside this historical parent. |
| `WS04-03` | Migration policy, compatibility, interruption, and production-like rehearsal | `WS04-03A` is accepted; corrected `WS04-03B` final migration/runtime rehearsal remains deferred. |
| `WS05-01` | Durable job model, claim/lease lifecycle, and worker deployment | `WS05-01A` is accepted; corrected `WS05-01B` final worker deployment/runtime proof remains deferred. |
| `WS05-02` | Payment and booking state machines with webhook authority | Accepted; surviving later refund, provider/runtime, observability, and operations work is governed by the corrected master. |
| `WS05-03` | Refunds, credits, notices and reconciliation | Not implemented. Corrected scope is governed by master section 8.3; scope or decompose only if genuinely needed. |
| `WS05-04` | Failure/concurrency/provider verification | Not implemented. Corrected scope is governed by master section 8.3; scope or decompose only if genuinely needed. |
| `WS06-01` | Admin upload authority and initiation | Not implemented. Corrected scope is governed by master section 8.4; scope or decompose only if genuinely needed. |
| `WS06-02` | Image validation and sanitization | Not implemented. Corrected scope is governed by master section 8.4; scope or decompose only if genuinely needed. |
| `WS06-03` | R2 lifecycle and repair | Not implemented. Corrected scope is governed by master section 8.4; scope or decompose only if genuinely needed. |
| `WS07-01` | Production build and public configuration | Not implemented. Corrected scope is governed by master section 8.5; scope or decompose only if genuinely needed. |
| `WS07-02` | Identity-scoped state and safe retries | Not implemented. Corrected scope is governed by master section 8.5; scope or decompose only if genuinely needed. |
| `WS07-03` | Routes, forms and resilient UI state | Not implemented. Corrected scope is governed by master section 8.5; scope or decompose only if genuinely needed. |
| `WS07-04` | Browser security and third-party code | Not implemented. Corrected scope is governed by master section 8.5; scope or decompose only if genuinely needed. |
| `WS07-05` | Accessibility, browser support and performance | Not implemented. Corrected scope is governed by master section 8.5; scope or decompose only if genuinely needed. |
| `WS08-01` | Current test inventory and gap cleanup | Not implemented. Corrected scope is governed by master section 8.6; do not recreate trusted-root, checker, or permanent compliance mapping. |
| `WS08-02` | Critical risk-based suites | Not implemented. Corrected scope is governed by master section 8.6; scope or decompose only if genuinely needed. |
| `WS08-03` | CI and supply-chain hardening | Not implemented. Corrected scope is governed by master section 8.6; no default SBOM or custom provenance/signing framework. |
| `WS09-01` | Structured logging | Not implemented. Corrected scope is governed by master section 8.7; scope or decompose only if genuinely needed. |
| `WS09-02` | Administrative auditability | Not implemented. Corrected scope is governed by master section 8.7; scope or decompose only if genuinely needed. |
| `WS09-03` | Metrics, alerts and capacity | Not implemented. Corrected scope is governed by master section 8.7; no formal SLO/error-budget bureaucracy. |
| `WS10-01` | Privacy/data lifecycle | Not implemented. Corrected scope is governed by master section 8.8; scope or decompose only if genuinely needed. |
| `WS10-02` | Secrets and control-plane access | Not implemented. Corrected scope is governed by master section 8.8; scope or decompose only if genuinely needed. |
| `WS10-03` | Incident readiness | Not implemented. Corrected scope is governed by master section 8.8; scope or decompose only if genuinely needed. |
| `WS10-04` | Backup and recovery | Not implemented. Corrected scope is governed by master section 8.8; scope or decompose only if genuinely needed. |
| `CLOSE-01` | Final discrepancy/completeness sweep | Not implemented. Use the small corrected-master check; do not build a universal evidence index or control dossier. |
| `CLOSE-02` | Final readiness decision | Not implemented. Decide against actual corrected requirements, repository state, final evidence, and unresolved material risk. |

## 5. Accepted Executable Passes

The following 39 executable passes are merged and accepted in the current
repository. Plan paths are retained as implementation provenance, not current
scope authority. Every path is relative to `docs/production-readiness/planning/`.

| Executable pass | Historical parent | Plan | State |
|---|---|---|---|
| `EN-01` | `EN-01` | `passes/en/en-01-test-taxonomy-and-isolation-baseline.md` | Accepted |
| `EN-02` | `EN-02` | `passes/en/en-02-correlation-event-envelope-redaction-contract.md` | Accepted |
| `EN-03` | `EN-03` | `passes/en/en-03-secrets-control-plane-evidence-foundation.md` | Accepted |
| `WS02-01` | `WS02-01` | `passes/ws02/ws02-01-typed-settings-environment-isolation.md` | Accepted |
| `WS02-02` | `WS02-02` | `passes/ws02/ws02-02-runtime-lifecycle-health-deployability.md` | Accepted |
| `WS02-03` | `WS02-03` | `passes/ws02/ws02-03-proxy-host-tls-cors-security-headers.md` | Accepted |
| `WS02-04A` | `WS02-04` | `passes/ws02/ws02-04a-stable-error-contracts.md` | Accepted |
| `WS02-04B1` | `WS02-04` | `passes/ws02/ws02-04b1-source-owned-boundaries.md` | Accepted |
| `WS02-04B2A1` | `WS02-04` | `passes/ws02/ws02-04b2a1-portable-request-boundaries.md` | Accepted |
| `WS02-04B2A2A` | `WS02-04` | `passes/ws02/ws02-04b2a2a-active-workflow-schema-bounds.md` | Accepted |
| `WS02-04B2A2B1` | `WS02-04` | `passes/ws02/ws02-04b2a2b1-route-lifecycle-cleanup.md` | Accepted |
| `WS02-04B2A2B2` | `WS02-04` | `passes/ws02/ws02-04b2a2b2-opaque-provider-payment-inputs.md` | Accepted |
| `WS02-04B2A2B3` | `WS02-04` | `passes/ws02/ws02-04b2a2b3-policy-legal-request-ownership.md` | Accepted |
| `WS02-04B2A2C` | `WS02-04` | `passes/ws02/ws02-04b2a2c-ordinary-json-request-body-limit.md` | Accepted |
| `WS02-04C1` | `WS02-04` | `passes/ws02/ws02-04c1-operation-timeouts-cancellation.md` | Accepted |
| `WS02-04C2` | `WS02-04` | `passes/ws02/ws02-04c2-retry-reconciliation-backpressure.md` | Accepted |
| `WS02-04C3A` | `WS02-04` | `passes/ws02/ws02-04c3a-chat-rate-limit-contract.md` | Accepted |
| `WS02-04C3B` | `WS02-04` | `passes/ws02/ws02-04c3b-provider-cost-rate-limit-deferral.md` | Accepted |
| `WS02-05A` | `WS02-05` | `passes/ws02/ws02-05a-http-openapi-cache-contracts.md` | Accepted |
| `WS02-05B1` | `WS02-05` | `passes/ws02/ws02-05b1-request-ownership.md` | Accepted |
| `WS02-05B2` | `WS02-05` | `passes/ws02/ws02-05b2-response-minimization.md` | Accepted |
| `WS03-01` | `WS03-01` | `passes/ws03/ws03-01-identity-authority.md` | Accepted |
| `WS03-02` | `WS03-02` | `passes/ws03/ws03-02-account-lifecycle-concurrency.md` | Accepted |
| `WS03-03A` | `WS03-03` | `passes/ws03/ws03-03a-recent-auth-step-up.md` | Accepted |
| `WS03-03B` | `WS03-03` | `passes/ws03/ws03-03b-app-check-admin-mfa-firebase-governance.md` | Accepted |
| `WS03-04A` | `WS03-04` | `passes/ws03/ws03-04a-authorization-matrix-foundation.md` | Accepted |
| `WS03-04B` | `WS03-04` | `passes/ws03/ws03-04b-self-owned-account-notification-financial-authorization.md` | Accepted |
| `WS03-04C` | `WS03-04` | `passes/ws03/ws03-04c-game-community-roster-chat-need-a-sub-relationship-authorization.md` | Accepted |
| `WS03-04D` | `WS03-04` | `passes/ws03/ws03-04d-admin-route-list-high-risk-function-authorization.md` | Accepted |
| `WS03-05A` | `WS03-05` | `passes/ws03/ws03-05a-versioned-moderation-taxonomy-finding-evidence-lifecycle.md` | Accepted |
| `WS04-01A` | `WS04-01` | `passes/ws04/ws04-01a-application-database-lifecycle-pool-settings-role-credential-boundaries.md` | Accepted |
| `WS04-01B` | `WS04-01` | `passes/ws04/ws04-01b-query-cursor-database-access-behavior.md` | Accepted |
| `WS04-01C` | `WS04-01` | `passes/ws04/ws04-01c-production-postgresql-topology-connection-budget-role-verification.md` | Accepted |
| `WS04-02A` | `WS04-02` | `passes/ws04/ws04-02a-transaction-boundary-external-side-effect-safety.md` | Accepted |
| `WS04-02B` | `WS04-02` | `passes/ws04/ws04-02b-database-enforced-invariants-locks-deterministic-concurrency.md` | Accepted |
| `WS04-02C` | `WS04-02` | `passes/ws04/ws04-02c-database-value-default-and-sql-safety-compatibility.md` | Accepted |
| `WS04-03A` | `WS04-03` | `passes/ws04/ws04-03a-provider-independent-migration-policy-compatibility-graph-drift-controlled-rehearsal.md` | Accepted |
| `WS05-01A` | `WS05-01` | `passes/ws05/ws05-01a-provider-independent-durable-job-model-claim-lease-lifecycle-portable-worker-runtime.md` | Accepted |
| `WS05-02` | `WS05-02` | `passes/ws05/ws05-02-payment-booking-state-machines-webhook-authority.md` | Accepted |

## 6. Historical Decomposition And Intake Records

These records explain how accepted work was divided. Their paths and historical
SHAs are provenance only; future work does not require a frozen intake artifact.

| Parent pass | Intake record | Historical SHA-256 | Accepted by executable pass | Accepted state |
|---|---|---|---|---|
| `WS03-04` | `docs/production-readiness/planning/passes/ws03/ws03-04-intake.md` | `e8dd5cda0aad2325df5c25d7d80f0e01a4849a9a1de205e91f0ac8d919869eb4` | `WS03-04A`, `WS03-04B`, `WS03-04C`, `WS03-04D` | Historical four-child decomposition; all four children are accepted in `develop`. |
| `WS03-05` | `docs/production-readiness/planning/passes/ws03/ws03-05-intake.md` | `4c255545449a085591f412175253f0b0207abcfc53c61f0c4cd60c89125a1a02` | `WS03-05A` | Historical four-child decomposition. A is accepted; B is implemented but unmerged and requires corrected-master correction; current C/D scope comes from master section 8.1. |
| `WS04-01` | `docs/production-readiness/planning/passes/ws04/ws04-01-intake.md` | `cb26606f6bca7dbc304a07e172771eeeebcece5312f73627fe8c67738a960ced` | `WS04-01A`, `WS04-01B`, `WS04-01C` | Accepted A/B/C structure preserved; mandatory later `WS04-01D` remains deferred until final production infrastructure is selected. |
| `WS04-02` | `docs/production-readiness/planning/passes/ws04/ws04-02-intake.md` | `bbcea141dec04890be5c0812131996548f86f82f6bc80ad66ce7f700e6ba3701` | `WS04-02A`, `WS04-02B`, `WS04-02C` | Accepted three-child structure: `WS04-02A -> WS04-02B -> WS04-02C`; all three children are accepted. |
| `WS04-03` | `docs/production-readiness/planning/passes/ws04/ws04-03-intake.md` | `ffc3e81d2d55ce9cca60d6ae40390d8ae9df2d8f8d3995b4b9c8464c101cfb48` | `WS04-03A` | Accepted split: `WS04-03A` is the current provider-independent migration-policy/rehearsal child; mandatory `WS04-03B` remains deferred until final production database provider, deployment topology, migration runner, and production-equivalent rehearsal inputs are selected and evidenced. |
| `WS05-01` | `docs/production-readiness/planning/passes/ws05/ws05-01-intake.md` | `1cfa5be5898cf0e53730c7841e5c5c89d9a824c8e10b644b0fcb835e50890720` | `WS05-01A` | Accepted split: `WS05-01A` is the current provider-independent durable-job foundation child; mandatory `WS05-01B` remains deferred until final worker platform, service topology, process/instance model, scaling/resource settings, provider deployment path, and runtime verification environment are selected and evidenced. |
| `WS05-02` | `docs/production-readiness/planning/passes/ws05/ws05-02-intake.md` | `4450d47c4bd44678b7f9ccd07a229740aad5fdec443153a0d8677dd3491f8ab1` | `WS05-02` | Accepted direct executable pass; surviving later payment, provider/runtime, observability, and operations work is governed by the corrected master. |

Historical WS02-04, WS02-05, and WS03-03 decompositions remain accepted
provenance. Do not fabricate retroactive intake records for them. For future
work, record a decomposition only when the selected corrected-master unit
genuinely needs one.

## 7. Parent Decomposition Records

The detailed records below describe accepted implementation history. Historical
plans, labels, paths, and SHAs are provenance only and do not control future
scope or require the old frozen-artifact workflow.

### WS02-04

Original parent: `WS02-04 - Request limits, timeouts, rate controls, and stable
errors`.

Accepted executable children:

1. `WS02-04A`
2. `WS02-04B1`
3. `WS02-04B2A1`
4. `WS02-04B2A2A`
5. `WS02-04B2A2B1`
6. `WS02-04B2A2B2`
7. `WS02-04B2A2B3`
8. `WS02-04B2A2C`
9. `WS02-04C1`
10. `WS02-04C2`
11. `WS02-04C3A`
12. `WS02-04C3B`

Source-owned closeout: `passes/ws02/ws02-04-source-owned-closeout.md`.

The closeout records source-owned completion for the accepted repository-owned
slices. It does not close provider, runtime, staging, durable-worker, or other
external evidence gaps.

### WS02-05

Original parent: `WS02-05 - HTTP contracts, schemas, docs, cache, and
end-to-end chain`.

Accepted executable children:

1. `WS02-05A`
2. `WS02-05B1`
3. `WS02-05B2`

The child passes separate HTTP/OpenAPI/cache behavior, request ownership, and
response minimization. Remaining permanent HTTP-chain, runtime, browser, and
external evidence is not closed by local child-pass pytest alone.

### WS03-03

Original parent: `WS03-03 - High-risk authentication and Firebase control
verification`.

Accepted executable children:

1. `WS03-03A`
2. `WS03-03B`

`WS03-03A` owns source recent-authentication and frontend step-up evidence.
`WS03-03B` owns source Firebase App Check foundation and records administrator
MFA plus Firebase/GCP credential-governance provider boundaries. Broader live
provider/runtime/governance evidence remains later-owned.

### WS03-04

Original parent: `WS03-04 - Complete authorization matrix and negative proof`.

Historical Stage 0 intake:
`docs/production-readiness/planning/passes/ws03/ws03-04-intake.md`

Historical intake SHA-256:
`e8dd5cda0aad2325df5c25d7d80f0e01a4849a9a1de205e91f0ac8d919869eb4`

Historical executable-child plan:

1. `WS03-04A`
2. `WS03-04B`
3. `WS03-04C`
4. `WS03-04D`

Historical dependency graph:
`WS03-04A -> {WS03-04B, WS03-04C} -> WS03-04D`

`WS03-04A` owns the authorization matrix foundation and route drift guard.
It records every current FastAPI route/action key, deterministic backend
authorization dependencies, child-owner or non-WS03-04 dispositions, source
traceability, and canonical uncovered gaps. It does not prove final behavioral
authorization closure.

`WS03-04B` owns self-owned account, notification, inbox, saved-card, credit,
payment, refund, and host-fee surfaces.

`WS03-04C` owns games, community games, checkout, bookings, participants,
waitlists, chats/messages, My Games, and Need-a-Sub relationship surfaces.

`WS03-04D` owns admin/high-risk route proof and final parent-gap disposition.
Its canonical plan path is
`docs/production-readiness/planning/passes/ws03/ws03-04d-admin-route-list-high-risk-function-authorization.md`.

WS03-04 parent complete: A/B/C/D accepted evidence accounts for the parent
authorization-matrix obligations. The accepted `WS03-04A-G001` Stripe webhook
lifecycle gap remains `covered_elsewhere` by `WS05` and does not block WS03-04
completion because the provider callback payment lifecycle belongs to later
WS05 payment/webhook evidence.

### WS03-05

Original parent: `WS03-05 - Moderation states, safe notices, and
minimum-necessary admin data`.

Historical Stage 0 intake:
`docs/production-readiness/planning/passes/ws03/ws03-05-intake.md`

Historical intake SHA-256:
`4c255545449a085591f412175253f0b0207abcfc53c61f0c4cd60c89125a1a02`

Historical executable-child plan:

1. `WS03-05A - Versioned moderation taxonomy and finding-evidence lifecycle`
2. `WS03-05B - Conflict-safe moderation review-case lifecycle`
3. `WS03-05C - Action-scoped moderation enforcement and safe-notice contract`
4. `WS03-05D - Minimum-necessary admin data and audited sensitive access`

Historical dependency graph:
`WS03-05A -> WS03-05B -> {WS03-05C, WS03-05D}`, with `WS03-05D` also
requiring the applicable accepted reusable append-only audit capability under
`WS09-02`.

`WS03-05A` owns `ADM-009`/`ADM-010` taxonomy and finding-evidence identity. Its
canonical plan is
`docs/production-readiness/planning/passes/ws03/ws03-05a-versioned-moderation-taxonomy-finding-evidence-lifecycle.md`
with historical SHA-256
`279aee40401cf123bdcee1c5d17b605e6da99bf4ca0f1c87b800364bf265337b`.
`WS03-05A` is accepted in `develop`. It does not expand review-case state,
enforcement, notices, or sensitive administrative access.

`WS03-05B` was implemented under the historical `ADM-012` review-case lifecycle
scope. Its canonical plan is
`docs/production-readiness/planning/passes/ws03/ws03-05b-conflict-safe-moderation-review-case-lifecycle.md`
with historical SHA-256
`7fc296334af820bff3e24adbda47cd0450782c271ed2ea539c546789eaa94a28`.
PR #176 is unmerged and must not merge as currently implemented. The corrected
master requires retaining only the necessary review-case safety behavior and
removing assignment, reopen, merge, formal note-correction, expanded history UI,
and duplicate PL/pgSQL workflow machinery. Current `WS03-05C` and `WS03-05D`
scope is defined only by corrected-master section 8.1.

No final-infrastructure follow-up is created by this parent. Durable notice
delivery/reconciliation remains `WS05-03`-owned and minimum necessary
administrative auditability remains later-owned. Parent completion depends on
the surviving obligations in the corrected master, not the historical child
contract or control labels.

### WS04-01

Original parent: `WS04-01 - Database engine/session lifecycle, connection
budget, and least-privilege roles`.

Historical Stage 0 intake, structurally revised after accepted A/B:
`docs/production-readiness/planning/passes/ws04/ws04-01-intake.md`

Historical intake SHA-256:
`cb26606f6bca7dbc304a07e172771eeeebcece5312f73627fe8c67738a960ced`

Accepted executable children:

1. `WS04-01A`
2. `WS04-01B`
3. `WS04-01C - Production PostgreSQL verification framework and evidence contract`

Historical dependency graph:
`WS04-01A + WS04-01B -> WS04-01C`

`WS04-01A` owns application database lifecycle, pool settings, request-session
behavior, and application-versus-migration credential boundaries. It establishes
source-owned per-process application pool behavior without claiming final
production provider capacity, production role grants, or deployment topology.

`WS04-01B` owns query, cursor, pagination, and database-access behavior.

Accepted `WS04-01C` owns the provider-independent production database
verification framework. It defines and validates:

- the sanitized topology/budget/role evidence contract;
- the deployment-wide connection-budget formula and required connection-consumer
  categories;
- evidence-safety and completeness rules;
- pooler/direct-connection compatibility evidence requirements;
- runtime topology verification requirements;
- role/grant/search-path/default-privilege verification requirements;
- the budget telemetry-plan contract, reassessment triggers, and safe-adjustment
  or rollback evidence requirements.

`WS04-01C` does not record or claim final provider capacity, final deployed
process counts, final pool values, final budget/headroom, or concrete production
roles/grants while final infrastructure is intentionally undecided.

Mandatory deferred follow-up:

`WS04-01D - Final production PostgreSQL topology, connection budget, and role
verification`

`WS04-01D` is not part of the immediate child progression while its external
trigger is false. It becomes executable after the final production database and
hosting/deployment topology are selected and the launch database consumers can
be bounded from sanitized evidence.

`WS04-01D` will apply the accepted C framework to the real production system and
verify:

- actual provider usable connection capacity and pooler/proxy/direct mode;
- actual API instance/process/autoscaling/rolling-overlap topology;
- deployed application pool values and connection wait behavior;
- migration, worker/job, monitoring, reporting/support, human, and reserve
  connection demand;
- final deployment-wide peak and headroom;
- concrete production application/migration/support/reporting/human database
  roles, grants, schema ownership, search path, and default privileges;
- required runtime/provider evidence and safe adjustment paths.

The durable final-infrastructure timing rule applies here: current Neon and
Render usage is temporary development/demo infrastructure and must not be used as
substitute final-production provider/deployment evidence. Final provider-specific
values remain late-bound until the final infrastructure is selected.

After accepted `WS04-01C`, the provider-independent database foundation is
complete for downstream engineering that needs only accepted source/database
contracts. Final `DB-002` budget evidence and final `DB-015` production
role/grant evidence remain explicitly deferred to `WS04-01D` and those
requirements must not be treated as complete.

No current `WS04-01` child remains executable while the `WS04-01D` external
trigger is false. `WS04-01` remains incomplete until `WS04-01D` is accepted or
the deferred obligation is otherwise truthfully resolved under durable
authority.

A downstream unit may proceed from A/B/C only when its own required inputs are
already accepted. If it requires a D-owned production fact, it must stop on that
specific missing prerequisite rather than inventing it.

`WS04-01D` is mandatory before `CLOSE-01` and final production-readiness
reassessment. It may be executed earlier as soon as its final-infrastructure
trigger is satisfied.

### WS04-02

Original parent: `WS04-02 - Transactions, invariants, locks, and deterministic
concurrency`.

Historical Stage 0 intake:
`docs/production-readiness/planning/passes/ws04/ws04-02-intake.md`

Historical intake SHA-256:
`bbcea141dec04890be5c0812131996548f86f82f6bc80ad66ce7f700e6ba3701`

Accepted executable children:

1. `WS04-02A - Transaction boundary and external-side-effect safety`
2. `WS04-02B - Database-enforced invariants, locks, and deterministic concurrency`
3. `WS04-02C - Database value, default, and SQL-safety compatibility`

Accepted dependency graph:
`WS04-02A -> WS04-02B -> WS04-02C`

`WS04-02A` owns current source transaction boundaries and side-effect safety for
workflows that combine database mutation with provider operations or
user-visible/admin-visible outcomes. It records the source-owned transaction
boundary policy, reconciles provider retry classifications for checkout,
community publish, refunds, paid waitlist auto-promotion, saved-card/account
cleanup, R2 metadata, notifications, platform notices, support/admin effects,
and preserves the accepted checkout/game serialization contract while adding
durable pre-provider checkpoints for the current risky request workflows.

`WS04-02A` does not close database-enforced game/roster/financial invariants,
deterministic independent-session domain concurrency, database value/default
compatibility, SQL/logging safety, durable worker execution, Stripe sandbox
lifecycle proof, final provider/runtime proof, migration compatibility,
dashboards, alerts, or final production infrastructure evidence.

`WS04-02B` owns the current database-enforced invariant policy; game, roster,
waitlist, and credit financial dispositions; deterministic game-first locking
proof; independent-session PostgreSQL contention evidence; account-deletion
multi-game roster cleanup ordering; and the recorded test evidence for
database-enforced invariants.

`WS04-02B` does not close database value/default compatibility, SQL/logging
safety, durable worker execution, Stripe sandbox lifecycle proof, final
provider/runtime proof, migration compatibility, dashboards, alerts, or final
production infrastructure evidence.

`WS04-02C` owns the current database value/default and SQL-safety contract;
timezone-aware database values and deliberate update timestamps; integer-cent
money and explicit current USD compatibility; status/default compatibility;
JSON/JSONB default and payload-shape safety; current raw-SQL construction and
parameterization; repository-owned SQL/value logging safety; and compatibility
proof that accepted `WS04-01A/B/C` and `WS04-02A/B` contracts remain intact.

With `WS04-02C` accepted, the historical executable `WS04-02` child set is
complete. Later-owned obligations explicitly allocated to `WS05`, `WS04-03`,
`WS09`, `WS10`, or `WS04-01D` remain preserved outside this parent and are not
claimed as closed by `WS04-02A`, `WS04-02B`, or `WS04-02C`.

### WS04-03

Original parent: `WS04-03 - Migration policy, compatibility, interruption, and
production-like rehearsal`.

Historical Stage 0 intake:
`docs/production-readiness/planning/passes/ws04/ws04-03-intake.md`

Historical intake SHA-256:
`ffc3e81d2d55ce9cca60d6ae40390d8ae9df2d8f8d3995b4b9c8464c101cfb48`

Accepted executable and deferred children:

1. `WS04-03A - Provider-independent migration policy, compatibility, graph/drift checks, and controlled rehearsal`
2. `WS04-03B - Final provider/runtime migration rehearsal and rollout evidence`

Accepted dependency graph:
`WS04-03A -> WS04-03B`

`WS04-03A` owns repository-owned migration policy, expand/contract rules,
old/new compatibility expectations, Alembic graph and drift checks,
empty-database and controlled prior-schema upgrades, dedicated migration-test
database safety, interruption/retry/reset rehearsal, current migration
operation classification, and migration evidence under
`backend/tests/migrations/`.

`WS04-03A` does not close final provider/runtime migration ceilings,
production-equivalent volume, final migration runner behavior, final
rolling-overlap topology, final provider lock/runtime behavior, or final rollout
evidence.

`WS04-03B` remains mandatory and deferred until final production database
provider, deployment topology, migration runner, and production-equivalent
rehearsal inputs are selected and evidenced enough to measure provider/runtime
migration behavior safely. `WS04-03` remains incomplete until `WS04-03B` is
accepted or otherwise truthfully resolved under durable authority.

### WS05-01

Original parent: `WS05-01 - Durable job model, claim/lease lifecycle, and
worker deployment`.

Historical Stage 0 intake:
`docs/production-readiness/planning/passes/ws05/ws05-01-intake.md`

Historical intake SHA-256:
`1cfa5be5898cf0e53730c7841e5c5c89d9a824c8e10b644b0fcb835e50890720`

Accepted executable and deferred children:

1. `WS05-01A - Provider-independent durable job model, claim/lease lifecycle, and portable worker runtime`
2. `WS05-01B - Final worker hosting topology, deployment configuration, and runtime proof`

Accepted dependency graph:
`WS05-01A -> WS05-01B`

`WS05-01A` owns the repository-owned PostgreSQL durable job schema, append-only
job event history, portable worker heartbeat state, idempotent transactional
enqueue, atomic claim/lease/heartbeat mechanics, expired-lease recovery,
bounded retry/exhaustion/repair framework, version-compatible handler registry,
portable worker command, safe source-level operator summaries, and
provider-independent PostgreSQL evidence under `backend/tests/platform/durable_jobs/`.

`WS05-01A` does not close final worker hosting, provider deployment topology,
autoscaling/resource settings, final worker process or instance counts,
production worker runtime proof, final worker database connection budget,
payment/refund/credit/notice/moderation/storage consumer handlers, Stripe
sandbox evidence, deployed dashboards, alerts, incidents, or backup/recovery
operations.

`WS05-01B` remains mandatory and deferred until final worker platform, service
topology, process/instance model, scaling/resource settings, provider
deployment configuration path, and safe runtime verification environment are
selected and evidenced enough to verify deployed worker behavior honestly.
`WS05-01` remains incomplete until `WS05-01B` is accepted or otherwise
truthfully resolved under durable authority.

### WS05-02

Original parent: `WS05-02 - Payment and booking state machines with webhook
authority`.

Historical Stage 0 intake:
`docs/production-readiness/planning/passes/ws05/ws05-02-intake.md`

Historical intake SHA-256:
`4450d47c4bd44678b7f9ccd07a229740aad5fdec443153a0d8677dd3491f8ab1`

Accepted executable pass:

1. `WS05-02 - Payment and booking state machines with webhook authority`

Canonical plan:
`docs/production-readiness/planning/passes/ws05/ws05-02-payment-booking-state-machines-webhook-authority.md`

Historical canonical-plan SHA-256:
`12f3a3c10a87a5558872e59a74d1d1d9c8bcb9ec139e2a199553ae844defe0ea`

`WS05-02` is a direct executable parent pass. It owns the source-owned payment,
booking, reservation, participant, saved-card, webhook-event, durable
payment-job, and compensation-obligation transitions implemented under the
historical canonical plan. It preserves provider authority, bounded webhook/event/job
payloads, game-first lock ordering for capacity-sensitive transitions,
database-time reservation expiry, late-success compensation handoff, and
saved-payment-method operation reconciliation.

`WS05-02` does not close final worker hosting, Stripe sandbox/dashboard or
deployed webhook observations, broad scheduled reconciliation, actual refund or
credit-restoration execution, dispute handling, production observability,
alerts, runbooks, or other final infrastructure evidence. Those obligations
remain deferred exactly as declared by `WS05-02-R8` to `WS05-01B`, `WS05-03`,
`WS05-04`, `WS09`, and `WS10`.

## 8. Remaining Work And Progression

The corrected master defines the 27 remaining units and their surviving scope.
This register records state but does not select or expand that work.

For each selected unit:

1. start from current accepted `develop` and inspect current repository truth;
2. apply the corrected master's scope, real prerequisites, ownership, and
   provider-timing rules;
3. use Stage 0 only when scope or decomposition genuinely needs clarification;
4. use Gate A only when the work is complex enough to benefit from a reviewed
   engineering plan;
5. ask the owner to choose when more than one unit is valid and no real
   dependency selects one.

Late-bound final-infrastructure work becomes executable only when its provider,
topology, runtime, or production-evidence inputs exist. Temporary demo values do
not satisfy those facts. A deferred fact blocks only work that actually depends
on it, and deferred evidence never counts as proof of completion.

Before final readiness is declared, reconcile every surviving deferred
obligation required by the corrected master.

## 9. Parent Completion And Consistency Rules

Maintain these invariants:

- each child has one parent;
- every parent obligation is allocated;
- a decomposed parent completes its current executable child set only when all
  accepted current children complete;
- a deferred follow-up may preserve later provider/runtime proof only when the
  exact later pass, trigger, obligations, and latest completion boundary are
  recorded;
- deferred or covered-elsewhere evidence does not satisfy the underlying
  requirement;
- no duplicate child ID;
- no missing child;
- no unapproved overlap;
- summary counts equal detailed tables.

## 10. Register Maintenance Rules

Update this register when:

- a new executable pass is accepted into `develop`;
- a parent pass is decomposed;
- a source-owned closeout is accepted;
- an accepted pass is reverted or superseded;
- a register entry is found stale while scoping, planning, or reviewing work.

Register updates normally travel with the substantive pass PR that makes the
new state true.

When a substantive change alters accepted execution state, update this register
in that change rather than through a routine tracker-only PR. Record enough
parent/child and deferred-obligation context to keep the status truthful. Do not
mark work complete while a surviving corrected-master obligation remains open.
Git/PR finalization must not invent or semantically rewrite execution state.

Do not update this register to:

- claim completion without reassessment;
- store exact pytest node IDs;
- document secret, provider-private, or personal evidence;
- act as the sole source for selecting the next pass.
