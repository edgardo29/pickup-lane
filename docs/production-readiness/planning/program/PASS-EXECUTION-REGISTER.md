# Production-Readiness Pass Execution Register

This register records how Pickup Lane's original parent-level production
readiness blueprint has been translated into actual executable passes.

The master blueprint remains authoritative for the original 42 planned parent
passes. This register does not alter that blueprint, close controls, select the
next pass, or authorize implementation. It is a navigation and execution-state
record that must be updated only through an approved documentation or pass
scope.

## 1. Current Basis

| Field | Value |
|---|---|
| Register purpose | Distinguish original blueprint parent passes from actual executable passes. |
| Current reconciliation point | Proposed accepted `develop` state after the substantive `WS04-01B` PR merges. |
| Current accepted develop SHA at reconciliation | Merge SHA to be established by the substantive `WS04-01B` PR; accepted baseline before this pass was `f7545db6d7451e8cee5ddd53f74c175a8126ebff`. |
| Original blueprint register | 42 parent-level planned passes in `docs/production-readiness/planning/program/pickup-lane-master-production-readiness-blueprint.md`. |
| Accepted executable requirement declarations through this point | 31 files under `backend/tests/support/requirements/` once the substantive `WS04-01B` PR merges. |
| Next pass selected by this register? | No. The owner must explicitly select the next intake or pass. |

The recorded accepted `develop` SHA is a historical reconciliation basis for
this register version. It is not a mutable instruction and is not the
current-session source of truth. Current execution always comes from current
`origin/develop` plus the approved instruction.

## 2. Program Summary

| Metric | Count | Meaning |
|---|---:|---|
| Original blueprint parent-level entries | 42 | Parent-level entries mirrored from the master blueprint. |
| Accepted/completed parent-level entries | 14 | Includes `BASE-00` and `GOV-01` program predecessors plus accepted direct or decomposed parent entries through `WS03-04`. |
| Remaining parent-level entries | 28 | Parent-level entries not yet completed in this register; includes decomposed in-progress `WS04-01`. |
| Accepted executable passes with requirement declarations | 31 | Current accepted executable declaration files under `backend/tests/support/requirements/` once the substantive `WS04-01B` PR merges. |
| Remaining actual executable-pass count | Unknown | Future executable-unit count depends on owner selection and accepted decomposition. |

Count magnitude is not completion proof or control-closure proof. Controls
close only through accepted evidence and reassessment.

## 3. How To Use This Register

Before selecting or designing a future production-readiness pass:

1. Read the read-first document, program context, and applicable workflow.
2. Identify the relevant parent blueprint pass.
3. Check this register for accepted child passes and remaining parent scope.
4. Use `docs/production-readiness/planning/templates/PASS-INTAKE-TEMPLATE.md`
   when a parent pass needs decomposition or readiness review.
5. Do not infer the next pass from alphabetical order, filename order, or the
   last accepted PR.

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
| `WS03-05` | Moderation states, safe notices, and minimum-necessary admin data | Not yet selected in this register. Requires intake before implementation. |
| `WS04-01` | Database engine/session lifecycle, connection budget, and least-privilege roles | Decomposed by accepted Stage 0 intake into `WS04-01A`, `WS04-01B`, and `WS04-01C`; `WS04-01A` is accepted and `WS04-01B` is accepted after the substantive B PR merges; parent remains incomplete until C is accepted. |
| `WS04-02` | Transactions, invariants, locks, and deterministic concurrency | Not yet selected in this register. Requires intake before implementation. |
| `WS04-03` | Migration policy, compatibility, interruption, and production-like rehearsal | Not yet selected in this register. Requires intake before implementation. |
| `WS05-01` | Durable job model, claim/lease lifecycle, and worker deployment | Not yet selected in this register. Requires intake before implementation. |
| `WS05-02` | Payment and booking state machines with webhook authority | Not yet selected in this register. Requires intake before implementation. |
| `WS05-03` | Refunds, credits, notices, moderation delivery, and reconciliation | Not yet selected in this register. Requires intake before implementation. |
| `WS05-04` | Deterministic failure, replay, sandbox, and deployed-worker verification | Not yet selected in this register. Requires intake before implementation. |
| `WS06-01` | Admin-only venue-image authority and upload initiation | Not yet selected in this register. Requires intake before implementation. |
| `WS06-02` | Venue-image validation, sanitization, re-encoding, and derivatives | Not yet selected in this register. Requires intake before implementation. |
| `WS06-03` | R2 lifecycle, deletion, cache behavior, reconciliation, and recovery | Not yet selected in this register. Requires intake before implementation. |
| `WS07-01` | Production frontend build, public configuration, artifact identity, and source maps | Not yet selected in this register. Requires intake before implementation. |
| `WS07-02` | Authentication persistence, identity-scoped state, logout, switch, and safe retries | Not yet selected in this register. Requires intake before implementation. |
| `WS07-03` | Routes, API errors, forms, URLs, browser storage, and resilient UI state | Not yet selected in this register. Requires intake before implementation. |
| `WS07-04` | Third-party browser code, CSP/SRI posture, headers, and provider failure isolation | Not yet selected in this register. Requires intake before implementation. |
| `WS07-05` | WCAG 2.2 AA, browser support, and performance verification | Not yet selected in this register. Requires intake before implementation. |
| `WS08-01` | Complete current-test inventory, fixtures, and control mapping | Not yet selected in this register. Requires intake before implementation. |
| `WS08-02` | Critical workflow, deterministic concurrency, migration, provider, privacy, and recovery suites | Not yet selected in this register. Requires intake before implementation. |
| `WS08-03` | Reproducible CI, scans, branch protection, SBOM, provenance, and release evidence | Not yet selected in this register. Requires intake before implementation. |
| `WS09-01` | Structured request/event logging, correlation, redaction, and log aggregation | Not yet selected in this register. Requires intake before implementation. |
| `WS09-02` | Append-only administrative audit trail and sensitive-access controls | Not yet selected in this register. Requires intake before implementation. |
| `WS09-03` | Metrics, service objectives, dashboards, alerts, capacity, and cost evidence | Not yet selected in this register. Requires intake before implementation. |
| `WS10-01` | Data classification, table lifecycle, retention, privacy, and audit lifecycle | Not yet selected in this register. Requires intake before implementation. |
| `WS10-02` | Secrets, provider control-plane access, MFA, rotation, revocation, and offboarding | Not yet selected in this register. Requires intake before implementation. |
| `WS10-03` | Incident response, provider-outage handling, and operational runbooks | Not yet selected in this register. Requires intake before implementation. |
| `WS10-04` | Backup/PITR evidence, isolated restore, recovery validation, and exercises | Not yet selected in this register. Requires intake before implementation. |
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
| `WS04-01A` | `WS04-01` | `passes/ws04/ws04-01a-application-database-lifecycle-pool-settings-role-credential-boundaries.md` | `ws04_01a.json` | 7 | 7 | 0 | 0 | `workflows/application_database_lifecycle_pool_settings_role_credential_boundaries` |
| `WS04-01B` | `WS04-01` | `passes/ws04/ws04-01b-query-cursor-database-access-behavior.md` | `ws04_01b.json` | 7 | 7 | 0 | 0 | `workflows/query_cursor_database_access_behavior` |

## 6. Accepted Stage 0 Intake Records

| Parent pass | Intake record | SHA-256 | Accepted by executable pass | Accepted state |
|---|---|---|---|---|
| `WS03-04` | `docs/production-readiness/planning/passes/ws03/ws03-04-intake.md` | `e8dd5cda0aad2325df5c25d7d80f0e01a4849a9a1de205e91f0ac8d919869eb4` | `WS03-04A` | Accepted in `develop` through `WS03-04A`; reused by the remaining `WS03-04` children. |
| `WS04-01` | `docs/production-readiness/planning/passes/ws04/ws04-01-intake.md` | `39a43297ccabb2019987780e232aab384cb2f1e15b2d805daaa2da6a9ae2e2de` | `WS04-01A` | Accepted through `WS04-01A`; reused by `WS04-01B` and `WS04-01C`. |

Historical WS02-04, WS02-05, and WS03-03 decompositions remain accepted. Do
not fabricate retroactive intake records for them.

Future accepted intake records use:

```text
docs/production-readiness/planning/passes/<family>/<parent-id>-intake.md
```

Once owner-approved, an intake record is a frozen Stage 0 artifact identified by
path and SHA-256. It travels with the first substantive child pass or direct
parent pass that makes the structure accepted; it is not a Gate B-editable file.

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

The closeout records source-owned completion for the approved repository-owned
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

Approved Stage 0 intake:
`docs/production-readiness/planning/passes/ws03/ws03-04-intake.md`

Frozen intake SHA-256:
`e8dd5cda0aad2325df5c25d7d80f0e01a4849a9a1de205e91f0ac8d919869eb4`

Approved executable children:

1. `WS03-04A`
2. `WS03-04B`
3. `WS03-04C`
4. `WS03-04D`

Approved dependency graph:
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
lifecycle gap remains
`covered_elsewhere` by `WS05` and does not block WS03-04 completion because the
provider callback payment lifecycle belongs to later WS05 payment/webhook
evidence.

### WS04-01

Original parent: `WS04-01 - Database engine/session lifecycle, connection
budget, and least-privilege roles`.

Approved Stage 0 intake:
`docs/production-readiness/planning/passes/ws04/ws04-01-intake.md`

Frozen intake SHA-256:
`39a43297ccabb2019987780e232aab384cb2f1e15b2d805daaa2da6a9ae2e2de`

Approved executable children:

1. `WS04-01A`
2. `WS04-01B`
3. `WS04-01C`

Approved dependency graph:
`WS04-01A + WS04-01B -> WS04-01C`

`WS04-01A` owns application database lifecycle, pool settings, request-session
behavior, and application-versus-migration credential boundaries. It establishes
source-owned per-process application pool behavior without claiming final
production provider capacity, production role grants, or deployment topology.

`WS04-01B` owns query, cursor, pagination, and database-access behavior.

`WS04-01C` owns production PostgreSQL topology, deployment-wide connection
budget, provider limits, pooler/proxy mode, deployed process/instance facts,
rolling overlap, migration/monitoring allowance, reserve, and concrete
production database role and grant verification.

After the substantive `WS04-01B` PR merges, WS04-01 remains incomplete. The
accepted A and B evidence is a prerequisite for final production database
verification but does not close the parent connection-budget or
least-privilege-role obligations by itself.

## 8. Remaining Parent Passes

Every parent pass marked "not yet selected" requires explicit owner direction
and Stage 0 intake before Gate A according to blueprint dependencies.

This register does not decide whether the next work should be `WS04-01C`,
another parent intake, a correction, or a documentation task. The exact
remaining executable-unit count is intentionally unknown.

## 9. Parent Completion And Consistency Rules

Maintain these invariants:

- each child has one parent;
- every parent obligation is allocated;
- a decomposed parent completes only when all approved children complete;
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
accepted first-child state, remaining child state, and incomplete parent state
unless all children are complete. For later child PRs, update the register for
that child's accepted state and the remaining parent state. For the final child
PR, record final-child acceptance and mark the parent complete. If a parent is
kept whole, update the register for direct parent completion in that substantive
pass. Gate D never authors or semantically edits register content. Do not create
routine tracker-only PRs.

Do not update this register to:

- claim control closure without reassessment;
- store exact pytest node IDs;
- replace requirement declarations;
- replace `TESTING_RECORD.md`;
- document secret, provider-private, or personal evidence;
- select the next pass.
