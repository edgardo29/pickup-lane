# Production-Readiness Pass Execution Register

This register records how Pickup Lane's original parent-level production
readiness blueprint has been translated into actual executable passes.

The master blueprint remains authoritative for the original 42 planned parent
passes. This register does not alter that blueprint or close controls. It is a
navigation and accepted execution-state record used together with the master
blueprint, final remediation plan, accepted prerequisites, Stage 0 intake
records, and current `develop` to determine safe program progression.

The register does not, by itself, authorize implementation or invent ordering
when durable authority leaves multiple equally valid choices.

## 1. Current Basis

| Field | Value |
|---|---|
| Register purpose | Distinguish original blueprint parent passes from actual executable passes and record accepted progression state. |
| Current reconciliation point | Accepted `develop` at the `WS03-05A` implementation baseline; Gate B validation is complete, and this revision proposes the first `WS03-05` child acceptance state, which becomes true only after the substantive `WS03-05A` PR merges. |
| Current accepted develop SHA at reconciliation | `2fecae7e4b97a13d01265af178f59fc419556ddc`. |
| Original blueprint register | 42 parent-level planned passes in `docs/production-readiness/planning/program/pickup-lane-master-production-readiness-blueprint.md`. |
| Accepted executable requirement declarations through this point | 39 files under `backend/tests/support/requirements/`. |
| Next pass selected by this register? | Not by itself. Automated progression uses this register together with the master blueprint, remediation plan, accepted intake/dependencies, prerequisites, and current `develop`; owner selection is required only when durable authority does not determine one safe next unit. |

The recorded accepted `develop` SHA is a historical reconciliation basis for
this register version. It is not a mutable instruction and is not the
current-session source of truth. Current execution always comes from current
`origin/develop`, current repository state, durable authority, and the current
production-readiness run instruction.

## 2. Program Summary

| Metric | Count | Meaning |
|---|---:|---|
| Original blueprint parent-level entries | 42 | Parent-level entries mirrored from the master blueprint. |
| Accepted/completed parent-level entries | 16 | Includes `BASE-00` and `GOV-01` program predecessors plus accepted direct or decomposed parent entries through direct `WS05-02`. |
| Remaining parent-level entries | 26 | Parent-level entries not yet completed in this register; includes decomposed in-progress `WS04-01`, `WS04-03`, and `WS05-01`. |
| Accepted executable passes with requirement declarations | 39 | Current accepted executable passes after `WS03-05A` merges. |
| Remaining actual executable-pass count | Unknown | Future executable-unit count depends on Stage 0 decomposition of remaining parent scope. |

Count magnitude is not completion proof or control-closure proof. Controls
close only through accepted evidence and reassessment.

## 3. How To Use This Register

Before starting or resuming production-readiness work:

1. Read the read-first document, program context, and applicable workflow.
2. Identify the current parent blueprint pass or accepted executable child from
   current repository state.
3. Check this register for accepted child passes, accepted Stage 0 intake,
   dependency state, and remaining parent scope.
4. Use `docs/production-readiness/planning/templates/PASS-INTAKE-TEMPLATE.md`
   when a newly selected parent requires Stage 0 decomposition or readiness
   review.
5. For an already decomposed parent, use its accepted child graph to determine
   the next executable child whose prerequisites are satisfied.
6. When a parent is complete, determine the next parent from this register
   together with the master blueprint, final remediation plan, accepted
   prerequisites, and current `develop`.
7. If those durable sources determine exactly one next unit, automated
   progression may select it. If they leave multiple equally valid next units,
   stop for owner selection.
8. Never infer progression from alphabetical order, filename order, stale branch
   names, or old chat context.
9. Apply the final-infrastructure timing rule from the read-first document,
   Program Context, implementation workflow, and master blueprint. Temporary
   Vercel, Render, and Neon demo/prototype values do not satisfy final-production
   provider, topology, configuration, capacity, or runtime prerequisites. When a
   parent mixes provider-independent work with final-infrastructure-dependent
   work, Stage 0 must keep the executable work provider-neutral where practical
   and record the remaining provider-specific obligation as an explicit later
   owner/pass with a trigger and latest required completion boundary.

## 4. Original Blueprint Parent-Pass Register

The table below mirrors the original 42 parent-level planned passes for
navigation. It does not replace the master blueprint.

| Blueprint pass | Title | Execution-register state |
|---|---|---|
| `BASE-00` | Repository baseline and isolation gate | Historical program setup predecessor; no executable requirement declaration. |
| `GOV-01` | Import and reconcile the approved governance package | Historical governance predecessor; no executable requirement declaration in the current trusted backend architecture. |
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
| `WS03-05` | Moderation states, safe notices, and minimum-necessary admin data | Decomposed into `WS03-05A`, `WS03-05B`, `WS03-05C`, and `WS03-05D`; this revision records A accepted on merge, B as the next current child, C after B, and D after B plus its applicable reusable `WS09-02` audit-capability prerequisite. |
| `WS04-01` | Database engine/session lifecycle, connection budget, and least-privilege roles | Structurally revised after accepted `WS04-01A` and `WS04-01B`: revised `WS04-01C` accepted the provider-independent production-verification framework; final production topology/budget/role proof is preserved for mandatory later `WS04-01D` after final infrastructure is selected. |
| `WS04-02` | Transactions, invariants, locks, and deterministic concurrency | Decomposed into accepted executable children `WS04-02A`, `WS04-02B`, and `WS04-02C`; this revision records the current executable child set complete when the substantive `WS04-02C` PR merges, with later-owned migration, payment, observability, operations, and final-infrastructure evidence preserved outside `WS04-02`. |
| `WS04-03` | Migration policy, compatibility, interruption, and production-like rehearsal | Decomposed into current executable child `WS04-03A` plus mandatory deferred follow-up `WS04-03B`; this revision records `WS04-03A` as accepted on merge while final provider/runtime migration rehearsal remains open. |
| `WS05-01` | Durable job model, claim/lease lifecycle, and worker deployment | Decomposed into current executable child `WS05-01A` plus mandatory deferred follow-up `WS05-01B`; this revision records `WS05-01A` as accepted on merge while final worker hosting/runtime proof remains open. |
| `WS05-02` | Payment and booking state machines with webhook authority | Accepted direct executable pass on merge; source-owned payment/booking/webhook state-machine obligations are implemented while final worker hosting, provider/runtime proof, refund execution, observability, and operations evidence remain preserved for later owners. |
| `WS05-03` | Refunds, credits, notices, moderation delivery, and reconciliation | Not yet decomposed/implemented. Requires Stage 0 before first-time implementation when selected by current program progression. |
| `WS05-04` | Deterministic failure, replay, sandbox, and deployed-worker verification | Not yet decomposed/implemented. Requires Stage 0 before first-time implementation when selected by current program progression. |
| `WS06-01` | Admin-only venue-image authority and upload initiation | Not yet decomposed/implemented. Requires Stage 0 before first-time implementation when selected by current program progression. |
| `WS06-02` | Venue-image validation, sanitization, re-encoding, and derivatives | Not yet decomposed/implemented. Requires Stage 0 before first-time implementation when selected by current program progression. |
| `WS06-03` | R2 lifecycle, deletion, cache behavior, reconciliation, and recovery | Not yet decomposed/implemented. Requires Stage 0 before first-time implementation when selected by current program progression. |
| `WS07-01` | Production frontend build, public configuration, artifact identity, and source maps | Not yet decomposed/implemented. Requires Stage 0 before first-time implementation when selected by current program progression. |
| `WS07-02` | Authentication persistence, identity-scoped state, logout, switch, and safe retries | Not yet decomposed/implemented. Requires Stage 0 before first-time implementation when selected by current program progression. |
| `WS07-03` | Routes, API errors, forms, URLs, browser storage, and resilient UI state | Not yet decomposed/implemented. Requires Stage 0 before first-time implementation when selected by current program progression. |
| `WS07-04` | Third-party browser code, CSP/SRI posture, headers, and provider failure isolation | Not yet decomposed/implemented. Requires Stage 0 before first-time implementation when selected by current program progression. |
| `WS07-05` | WCAG 2.2 AA, browser support, and performance verification | Not yet decomposed/implemented. Requires Stage 0 before first-time implementation when selected by current program progression. |
| `WS08-01` | Complete current-test inventory, fixtures, and control mapping | Not yet decomposed/implemented. Requires Stage 0 before first-time implementation when selected by current program progression. |
| `WS08-02` | Critical workflow, deterministic concurrency, migration, provider, privacy, and recovery suites | Not yet decomposed/implemented. Requires Stage 0 before first-time implementation when selected by current program progression. |
| `WS08-03` | Reproducible CI, scans, branch protection, SBOM, provenance, and release evidence | Not yet decomposed/implemented. Requires Stage 0 before first-time implementation when selected by current program progression. |
| `WS09-01` | Structured request/event logging, correlation, redaction, and log aggregation | Not yet decomposed/implemented. Requires Stage 0 before first-time implementation when selected by current program progression. |
| `WS09-02` | Append-only administrative audit trail and sensitive-access controls | Not yet decomposed/implemented. Requires Stage 0 before first-time implementation when selected by current program progression. |
| `WS09-03` | Metrics, service objectives, dashboards, alerts, capacity, and cost evidence | Not yet decomposed/implemented. Requires Stage 0 before first-time implementation when selected by current program progression. |
| `WS10-01` | Data classification, table lifecycle, retention, privacy, and audit lifecycle | Not yet decomposed/implemented. Requires Stage 0 before first-time implementation when selected by current program progression. |
| `WS10-02` | Secrets, provider control-plane access, MFA, rotation, revocation, and offboarding | Not yet decomposed/implemented. Requires Stage 0 before first-time implementation when selected by current program progression. |
| `WS10-03` | Incident response, provider-outage handling, and operational runbooks | Not yet decomposed/implemented. Requires Stage 0 before first-time implementation when selected by current program progression. |
| `WS10-04` | Backup/PITR evidence, isolated restore, recovery validation, and exercises | Not yet decomposed/implemented. Requires Stage 0 before first-time implementation when selected by current program progression. |
| `CLOSE-01` | Cross-workstream evidence completeness and discrepancy sweep | Not yet selected in this register. Requires all workstream exit gates. |
| `CLOSE-02` | Fresh 163-control reassessment and production-readiness decision | Not yet selected in this register. Requires `CLOSE-01` and all correction/retest passes. |

## 5. Accepted Executable Passes

The following executable passes have accepted requirement declarations in the
current repository. Counts are declaration counts, not proof-strength ratings.
Every path in the Plan column is relative to
`docs/production-readiness/planning/`.

| Executable pass | Blueprint parent | Plan | Requirement declaration | Requirements | Required | Covered elsewhere | Deferred | Current trusted scope |
|---|---|---|---|---:|---:|---:|---:|---|
| `EN-01` | `EN-01` | `passes/en/en-01-test-taxonomy-and-isolation-baseline.md` | `en01.json` | 11 | 11 | 0 | 0 | `checker` |
| `EN-02` | `EN-02` | `passes/en/en-02-correlation-event-envelope-redaction-contract.md` | `en02.json` | 7 | 6 | 1 | 0 | `platform/observability` plus planning |
| `EN-03` | `EN-03` | `passes/en/en-03-secrets-control-plane-evidence-foundation.md` | `en03.json` | 6 | 1 | 5 | 0 | `platform/secrets`, governance, planning |
| `WS02-01` | `WS02-01` | `passes/ws02/ws02-01-typed-settings-environment-isolation.md` | `ws02_01.json` | 11 | 8 | 3 | 0 | `platform/settings` plus governance/planning |
| `WS02-02` | `WS02-02` | `passes/ws02/ws02-02-runtime-lifecycle-health-deployability.md` | `ws02_02.json` | 10 | 8 | 1 | 1 | `platform/runtime` plus governance/planning |
| `WS02-03` | `WS02-03` | `passes/ws02/ws02-03-proxy-host-tls-cors-security-headers.md` | `ws02_03.json` | 9 | 7 | 1 | 1 | `platform/http_security` plus governance/planning |
| `WS02-04A` | `WS02-04` | `passes/ws02/ws02-04a-stable-error-contracts.md` | `ws02_04a.json` | 8 | 7 | 0 | 1 | `platform/api_errors` plus governance |
| `WS02-04B1` | `WS02-04` | `passes/ws02/ws02-04b1-source-owned-boundaries.md` | `ws02_04b1.json` | 9 | 8 | 0 | 1 | `workflows/source_owned_boundaries` plus governance |
| `WS02-04B2A1` | `WS02-04` | `passes/ws02/ws02-04b2a1-portable-request-boundaries.md` | `ws02_04b2a1.json` | 8 | 7 | 0 | 1 | `platform/request_body_limits` plus governance |
| `WS02-04B2A2A` | `WS02-04` | `passes/ws02/ws02-04b2a2a-active-workflow-schema-bounds.md` | `ws02_04b2a2a.json` | 7 | 6 | 0 | 1 | `workflows/active_request_schema_bounds` plus governance |
| `WS02-04B2A2B1` | `WS02-04` | `passes/ws02/ws02-04b2a2b1-route-lifecycle-cleanup.md` | `ws02_04b2a2b1.json` | 7 | 6 | 0 | 1 | `workflows/route_lifecycle_cleanup` plus governance |
| `WS02-04B2A2B2` | `WS02-04` | `passes/ws02/ws02-04b2a2b2-opaque-provider-payment-inputs.md` | `ws02_04b2a2b2.json` | 8 | 7 | 0 | 1 | `workflows/provider_payment_input_ownership` plus governance |
| `WS02-04B2A2B3` | `WS02-04` | `passes/ws02/ws02-04b2a2b3-policy-legal-request-ownership.md` | `ws02_04b2a2b3.json` | 6 | 5 | 0 | 1 | `workflows/policy_legal_request_ownership` plus governance |
| `WS02-04B2A2C` | `WS02-04` | `passes/ws02/ws02-04b2a2c-ordinary-json-request-body-limit.md` | `ws02_04b2a2c.json` | 7 | 6 | 0 | 1 | `platform/request_body_limits` plus governance |
| `WS02-04C1` | `WS02-04` | `passes/ws02/ws02-04c1-operation-timeouts-cancellation.md` | `ws02_04c1.json` | 10 | 9 | 0 | 1 | `platform/operation_timeouts` plus governance |
| `WS02-04C2` | `WS02-04` | `passes/ws02/ws02-04c2-retry-reconciliation-backpressure.md` | `ws02_04c2.json` | 11 | 10 | 0 | 1 | `platform/retry_reconciliation` plus governance |
| `WS02-04C3A` | `WS02-04` | `passes/ws02/ws02-04c3a-chat-rate-limit-contract.md` | `ws02_04c3a.json` | 11 | 10 | 0 | 1 | `platform/chat_rate_limits` plus governance |
| `WS02-04C3B` | `WS02-04` | `passes/ws02/ws02-04c3b-provider-cost-rate-limit-deferral.md` | `ws02_04c3b.json` | 8 | 7 | 0 | 1 | `platform/provider_cost_rate_limits` plus governance |
| `WS02-05A` | `WS02-05` | `passes/ws02/ws02-05a-http-openapi-cache-contracts.md` | `ws02_05a.json` | 8 | 7 | 0 | 1 | `platform/http_contracts` plus governance |
| `WS02-05B1` | `WS02-05` | `passes/ws02/ws02-05b1-request-ownership.md` | `ws02_05b1.json` | 7 | 6 | 0 | 1 | `workflows/request_ownership` plus governance |
| `WS02-05B2` | `WS02-05` | `passes/ws02/ws02-05b2-response-minimization.md` | `ws02_05b2.json` | 10 | 9 | 0 | 1 | `workflows/response_minimization` plus governance |
| `WS03-01` | `WS03-01` | `passes/ws03/ws03-01-identity-authority.md` | `ws03_01.json` | 11 | 10 | 0 | 1 | `workflows/identity_authority` plus governance |
| `WS03-02` | `WS03-02` | `passes/ws03/ws03-02-account-lifecycle-concurrency.md` | `ws03_02.json` | 12 | 11 | 0 | 1 | `workflows/account_lifecycle_concurrency` plus governance |
| `WS03-03A` | `WS03-03` | `passes/ws03/ws03-03a-recent-auth-step-up.md` | `ws03_03a.json` | 14 | 11 | 0 | 3 | `workflows/recent_auth_step_up` plus governance |
| `WS03-03B` | `WS03-03` | `passes/ws03/ws03-03b-app-check-admin-mfa-firebase-governance.md` | `ws03_03b.json` | 10 | 7 | 0 | 3 | `workflows/app_check_provider_security` plus governance |
| `WS03-04A` | `WS03-04` | `passes/ws03/ws03-04a-authorization-matrix-foundation.md` | `ws03_04a.json` | 9 | 8 | 0 | 1 | `workflows/authorization_matrix_foundation` plus governance |
| `WS03-04B` | `WS03-04` | `passes/ws03/ws03-04b-self-owned-account-notification-financial-authorization.md` | `ws03_04b.json` | 10 | 9 | 0 | 1 | `workflows/self_owned_account_notification_financial_authorization` plus governance |
| `WS03-04C` | `WS03-04` | `passes/ws03/ws03-04c-game-community-roster-chat-need-a-sub-relationship-authorization.md` | `ws03_04c.json` | 12 | 11 | 0 | 1 | `workflows/game_community_roster_chat_need_a_sub_relationship_authorization` plus governance |
| `WS03-04D` | `WS03-04` | `passes/ws03/ws03-04d-admin-route-list-high-risk-function-authorization.md` | `ws03_04d.json` | 12 | 12 | 0 | 0 | `workflows/admin_route_list_high_risk_function_authorization` plus governance |
| `WS03-05A` | `WS03-05` | `passes/ws03/ws03-05a-versioned-moderation-taxonomy-finding-evidence-lifecycle.md` | `ws03_05a.json` | 6 | 6 | 0 | 0 | `workflows/moderation_taxonomy_finding_evidence_lifecycle` plus governance/migration compatibility |
| `WS04-01A` | `WS04-01` | `passes/ws04/ws04-01a-application-database-lifecycle-pool-settings-role-credential-boundaries.md` | `ws04_01a.json` | 7 | 7 | 0 | 0 | `workflows/application_database_lifecycle_pool_settings_role_credential_boundaries` |
| `WS04-01B` | `WS04-01` | `passes/ws04/ws04-01b-query-cursor-database-access-behavior.md` | `ws04_01b.json` | 7 | 7 | 0 | 0 | `workflows/query_cursor_database_access_behavior` |
| `WS04-01C` | `WS04-01` | `passes/ws04/ws04-01c-production-postgresql-topology-connection-budget-role-verification.md` | `ws04_01c.json` | 8 | 8 | 0 | 0 | `platform/production_database_verification` |
| `WS04-02A` | `WS04-02` | `passes/ws04/ws04-02a-transaction-boundary-external-side-effect-safety.md` | `ws04_02a.json` | 8 | 8 | 0 | 0 | `workflows/transaction_boundary_external_side_effect_safety` |
| `WS04-02B` | `WS04-02` | `passes/ws04/ws04-02b-database-enforced-invariants-locks-deterministic-concurrency.md` | `ws04_02b.json` | 9 | 9 | 0 | 0 | `workflows/database_invariants_locks_deterministic_concurrency` |
| `WS04-02C` | `WS04-02` | `passes/ws04/ws04-02c-database-value-default-and-sql-safety-compatibility.md` | `ws04_02c.json` | 8 | 8 | 0 | 0 | `workflows/database_value_default_sql_safety_compatibility` |
| `WS04-03A` | `WS04-03` | `passes/ws04/ws04-03a-provider-independent-migration-policy-compatibility-graph-drift-controlled-rehearsal.md` | `ws04_03a.json` | 8 | 8 | 0 | 0 | `migrations/migration_policy_compatibility_rehearsal` |
| `WS05-01A` | `WS05-01` | `passes/ws05/ws05-01a-provider-independent-durable-job-model-claim-lease-lifecycle-portable-worker-runtime.md` | `ws05_01a.json` | 9 | 8 | 0 | 1 | `platform/durable_jobs` plus runtime/migration/SQL-safety/retry compatibility |
| `WS05-02` | `WS05-02` | `passes/ws05/ws05-02-payment-booking-state-machines-webhook-authority.md` | `ws05_02.json` | 8 | 7 | 0 | 1 | `workflows/payment_booking_state_machines_webhook_authority` plus planning |

## 6. Accepted Stage 0 Intake Records

| Parent pass | Intake record | SHA-256 | Accepted by executable pass | Accepted state |
|---|---|---|---|---|
| `WS03-04` | `docs/production-readiness/planning/passes/ws03/ws03-04-intake.md` | `e8dd5cda0aad2325df5c25d7d80f0e01a4849a9a1de205e91f0ac8d919869eb4` | `WS03-04A` | Accepted in `develop` through `WS03-04A`; reused by the remaining `WS03-04` children. |
| `WS03-05` | `docs/production-readiness/planning/passes/ws03/ws03-05-intake.md` | `4c255545449a085591f412175253f0b0207abcfc53c61f0c4cd60c89125a1a02` | `WS03-05A` | Accepted four-child structure on merge: A accepted; B is the next current child; C follows B; D follows B and the applicable accepted reusable append-only audit capability under `WS09-02`. |
| `WS04-01` | `docs/production-readiness/planning/passes/ws04/ws04-01-intake.md` | `cb26606f6bca7dbc304a07e172771eeeebcece5312f73627fe8c67738a960ced` | `WS04-01A`, `WS04-01B`, `WS04-01C` | Accepted A/B/C structure preserved; mandatory later `WS04-01D` remains deferred until final production infrastructure is selected. |
| `WS04-02` | `docs/production-readiness/planning/passes/ws04/ws04-02-intake.md` | `bbcea141dec04890be5c0812131996548f86f82f6bc80ad66ce7f700e6ba3701` | `WS04-02A`, `WS04-02B`, `WS04-02C` | Accepted three-child structure: `WS04-02A -> WS04-02B -> WS04-02C`; this revision records the current child set complete when the substantive `WS04-02C` PR merges. |
| `WS04-03` | `docs/production-readiness/planning/passes/ws04/ws04-03-intake.md` | `ffc3e81d2d55ce9cca60d6ae40390d8ae9df2d8f8d3995b4b9c8464c101cfb48` | `WS04-03A` | Accepted split: `WS04-03A` is the current provider-independent migration-policy/rehearsal child; mandatory `WS04-03B` remains deferred until final production database provider, deployment topology, migration runner, and production-equivalent rehearsal inputs are selected and evidenced. |
| `WS05-01` | `docs/production-readiness/planning/passes/ws05/ws05-01-intake.md` | `1cfa5be5898cf0e53730c7841e5c5c89d9a824c8e10b644b0fcb835e50890720` | `WS05-01A` | Accepted split: `WS05-01A` is the current provider-independent durable-job foundation child; mandatory `WS05-01B` remains deferred until final worker platform, service topology, process/instance model, scaling/resource settings, provider deployment path, and runtime verification environment are selected and evidenced. |
| `WS05-02` | `docs/production-readiness/planning/passes/ws05/ws05-02-intake.md` | `4450d47c4bd44678b7f9ccd07a229740aad5fdec443153a0d8677dd3491f8ab1` | `WS05-02` | Accepted direct executable pass: source-owned payment/booking/webhook authority scope is complete on merge; final worker hosting, Stripe sandbox/deployed webhook proof, refund/credit execution, observability, and operations evidence remain deferred to the later owners named by `WS05-02-R8`. |

Historical WS02-04, WS02-05, and WS03-03 decompositions remain accepted. Do
not fabricate retroactive intake records for them.

Future Stage 0 intake records use:

```text
docs/production-readiness/planning/passes/<family>/<parent-id>-intake.md
```

A valid Stage 0 result freezes the exact intake path and SHA-256 for the current
automated run. When the first substantive child or direct parent PR merges, that
intake becomes accepted in `develop` and is reused by later children unless a
structural Stage 0 revision is required. The intake is not a Gate B-editable
file.

## 7. Parent Decomposition Records

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

Accepted Stage 0 intake:
`docs/production-readiness/planning/passes/ws03/ws03-04-intake.md`

Frozen intake SHA-256:
`e8dd5cda0aad2325df5c25d7d80f0e01a4849a9a1de205e91f0ac8d919869eb4`

Accepted executable children:

1. `WS03-04A`
2. `WS03-04B`
3. `WS03-04C`
4. `WS03-04D`

Accepted dependency graph:
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

Accepted Stage 0 intake:
`docs/production-readiness/planning/passes/ws03/ws03-05-intake.md`

Frozen intake SHA-256:
`4c255545449a085591f412175253f0b0207abcfc53c61f0c4cd60c89125a1a02`

Accepted executable children:

1. `WS03-05A - Versioned moderation taxonomy and finding-evidence lifecycle`
2. `WS03-05B - Conflict-safe moderation review-case lifecycle`
3. `WS03-05C - Action-scoped moderation enforcement and safe-notice contract`
4. `WS03-05D - Minimum-necessary admin data and audited sensitive access`

Accepted dependency graph:
`WS03-05A -> WS03-05B -> {WS03-05C, WS03-05D}`, with `WS03-05D` also
requiring the applicable accepted reusable append-only audit capability under
`WS09-02`.

`WS03-05A` owns `ADM-009`/`ADM-010` taxonomy and finding-evidence identity. Its
canonical plan is
`docs/production-readiness/planning/passes/ws03/ws03-05a-versioned-moderation-taxonomy-finding-evidence-lifecycle.md`
with frozen SHA-256
`279aee40401cf123bdcee1c5d17b605e6da99bf4ca0f1c87b800364bf265337b`.
This revision records A accepted on merge. It does not expand review-case state,
enforcement, notices, or sensitive administrative access.

`WS03-05B` owns `ADM-012` review-case lifecycle and is the deterministic next
current child after A. `WS03-05C` owns `ADM-013`/`ADM-014` action-scoped
enforcement and safe-notice semantics after B. `WS03-05D` owns
`ADM-007`/`ADM-015` minimum-necessary and audited sensitive access after B, but
must not enable audit-dependent access until the applicable reusable
append-only audit capability from `WS09-02` is accepted.

No final-infrastructure follow-up is created by this parent. Durable notice
delivery/reconciliation remains `WS05-03`-owned, reusable append-only audit
persistence/access remains `WS09-02`-owned, and those later responsibilities do
not block A, B, or C. The parent remains incomplete until A/B/C/D are accepted
and all allocated obligations are truthfully satisfied.

### WS04-01

Original parent: `WS04-01 - Database engine/session lifecycle, connection
budget, and least-privilege roles`.

Accepted Stage 0 intake, structurally revised after accepted A/B:
`docs/production-readiness/planning/passes/ws04/ws04-01-intake.md`

Current frozen intake SHA-256:
`cb26606f6bca7dbc304a07e172771eeeebcece5312f73627fe8c67738a960ced`

Accepted executable children:

1. `WS04-01A`
2. `WS04-01B`
3. `WS04-01C - Production PostgreSQL verification framework and evidence contract`

Current dependency graph:
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
role/grant evidence remain explicitly deferred to `WS04-01D` and the controls
must not be treated as closed.

No current `WS04-01` child remains executable while the `WS04-01D` external
trigger is false. `WS04-01` remains incomplete until `WS04-01D` is accepted or
the deferred obligation is otherwise truthfully resolved under durable
authority.

A downstream Stage 0 or Gate A may proceed from A/B/C only when its own required
inputs are already accepted. If it requires a D-owned production fact, it must
stop on that specific missing prerequisite rather than inventing it.

`WS04-01D` is mandatory before `CLOSE-01` and final production-readiness
reassessment. It may be executed earlier as soon as its final-infrastructure
trigger is satisfied.

### WS04-02

Original parent: `WS04-02 - Transactions, invariants, locks, and deterministic
concurrency`.

Accepted Stage 0 intake:
`docs/production-readiness/planning/passes/ws04/ws04-02-intake.md`

Frozen intake SHA-256:
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
multi-game roster cleanup ordering; and the current source testing record for
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

When `WS04-02C` is accepted, the current executable `WS04-02` child set is
complete. Later-owned obligations explicitly allocated to `WS05`, `WS04-03`,
`WS09`, `WS10`, or `WS04-01D` remain preserved outside this parent and are not
claimed as closed by `WS04-02A`, `WS04-02B`, or `WS04-02C`.

### WS04-03

Original parent: `WS04-03 - Migration policy, compatibility, interruption, and
production-like rehearsal`.

Accepted Stage 0 intake:
`docs/production-readiness/planning/passes/ws04/ws04-03-intake.md`

Frozen intake SHA-256:
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
operation classification, and trusted migration evidence under
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

Accepted Stage 0 intake:
`docs/production-readiness/planning/passes/ws05/ws05-01-intake.md`

Frozen intake SHA-256:
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
portable worker command, safe source-level operator summaries, and trusted
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

Accepted Stage 0 intake:
`docs/production-readiness/planning/passes/ws05/ws05-02-intake.md`

Frozen intake SHA-256:
`4450d47c4bd44678b7f9ccd07a229740aad5fdec443153a0d8677dd3491f8ab1`

Accepted executable pass:

1. `WS05-02 - Payment and booking state machines with webhook authority`

Canonical plan:
`docs/production-readiness/planning/passes/ws05/ws05-02-payment-booking-state-machines-webhook-authority.md`

Frozen canonical-plan SHA-256:
`12f3a3c10a87a5558872e59a74d1d1d9c8bcb9ec139e2a199553ae844defe0ea`

`WS05-02` is a direct executable parent pass. It owns the source-owned payment,
booking, reservation, participant, saved-card, webhook-event, durable
payment-job, and compensation-obligation transitions required by the frozen
canonical plan. It preserves provider authority, bounded webhook/event/job
payloads, game-first lock ordering for capacity-sensitive transitions,
database-time reservation expiry, late-success compensation handoff, and
saved-payment-method operation reconciliation.

`WS05-02` does not close final worker hosting, Stripe sandbox/dashboard or
deployed webhook observations, broad scheduled reconciliation, actual refund or
credit-restoration execution, dispute handling, production observability,
alerts, runbooks, or other final infrastructure evidence. Those obligations
remain deferred exactly as declared by `WS05-02-R8` to `WS05-01B`, `WS05-03`,
`WS05-04`, `WS09`, and `WS10`.

## 8. Remaining Parent Passes And Progression

A parent that has not yet received Stage 0 intake requires Stage 0 before its
first-time Gate A when that parent becomes the deterministic next unit.

This register participates in progression but does not act as the sole selector.

For an in-progress decomposed parent:

1. use the accepted intake/dependency graph;
2. find incomplete current children whose prerequisites are accepted;
3. if exactly one child is the deterministic next executable unit, begin that
   child at fresh Gate A from current accepted `develop`;
4. if multiple children are simultaneously eligible and the accepted
   dependency/order does not choose between them, stop for owner selection.

A structurally approved deferred follow-up with an unmet external trigger is not
a current executable child merely because it has been named for future work. It
must have an exact owner/pass, trigger, preserved obligation set, and latest
required completion boundary. The program may continue only when current
downstream work does not depend on the deferred facts. Deferred evidence never
counts as proof or control closure.

This rule applies program-wide, not only to `WS04-01`. Stage 0 for later parents
must use the master blueprint's infrastructure-timing map to identify work that
requires final hosting, database, edge, worker, storage, monitoring, backup, DNS,
or other provider/runtime choices. Such work must not be satisfied with
temporary demo/prototype configuration merely to keep the sequence moving.

Before `CLOSE-01`, reconcile all mandatory deferred follow-ups and stop if any
required follow-up, including `WS04-01D`, remains incomplete.

For a completed parent:

1. reconcile the master blueprint, final remediation plan, this register,
   accepted prerequisites, and current repository truth;
2. if exactly one next parent is determined, begin that parent at Stage 0;
3. if durable authority leaves multiple equally valid next parents, stop for
   owner selection.

The exact remaining executable-unit count is intentionally unknown because
future Stage 0 decompositions may create additional child passes.

## 9. Parent Completion And Consistency Rules

Maintain these invariants:

- each child has one parent;
- every parent obligation is allocated;
- a decomposed parent completes its current executable child set only when all
  accepted current children complete;
- a deferred follow-up may preserve later provider/runtime proof only when the
  exact later pass, trigger, obligations, and latest completion boundary are
  recorded;
- deferred or covered-elsewhere evidence does not close the underlying control;
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
- a register entry is found stale during intake or Gate A.

Register updates normally travel with the substantive pass PR that makes the
new state true.

Every substantive first-time executable pass must update this register when
the pass merge changes accepted execution state. That register update is
justified by the frozen pass scope and reviewed as part of the actual
changed-file set. Program/documentation maintenance and historical rechecks
remain outside this automatic first-time-pass rule unless their explicit scope
says otherwise.

For a first child PR, include the frozen intake/decomposition reference,
accepted first-child state, remaining current-child state, and the parent's
remaining obligations. For later child PRs, update the register for that child's
accepted state and the remaining parent obligations. Acceptance of the final
currently executable child completes only the current executable child set when a
mandatory deferred follow-up remains outstanding; it must not mark the parent
fully complete or the deferred controls proven. Mark a decomposed parent complete
only when every accepted child obligation and every mandatory deferred follow-up
has been accepted or otherwise truthfully resolved under durable authority. If a
parent is kept whole and has no outstanding deferred obligation, update the
register for direct parent completion in that substantive pass. Gate D never
authors or semantically edits register content. Do not create routine tracker-only
PRs.

Do not update this register to:

- claim control closure without reassessment;
- store exact pytest node IDs;
- replace requirement declarations;
- replace `TESTING_RECORD.md`;
- document secret, provider-private, or personal evidence;
- act as the sole source for selecting the next pass.
