# Pickup Lane Master Production-Readiness Checklist

**Version:** Draft 1, consolidated August 2, 2026  
**Basis:** Seven completed Deep Research reports plus their requirement and verification matrices.  
**Assessment state:** No repository or runtime compliance judgment is made in this file. Every control begins as `NOT ASSESSED`.

## How to use this checklist

Use one status per control: `PASS`, `PARTIAL`, `FAIL`, `NEEDS DECISION`, `NOT APPLICABLE`, or `EXTERNAL EVIDENCE REQUIRED`. A status without concrete evidence is not valid. The detailed 575-row research register is retained separately for traceability.

### Normalized classifications

| Classification | Meaning |
|---|---|
| `MUST` | Required for the stated architecture or for safe/correct production operation. |
| `MUST DECIDE` | The project must make, document, and test a decision; no universal setting is asserted. |
| `SHOULD` | Strong production hardening whose exact form may vary. |
| `CONDITIONAL` | Applies only when the referenced feature or risk exists. |

### Priority

| Priority | Meaning |
|---|---|
| `P0` | Launch blocker or critical correctness/security/recovery control. |
| `P1` | Required before a responsible production launch unless a documented exception exists. |
| `P2` | Hardening or scale-dependent maturity control. |

## Control summary

This checklist contains **163 consolidated controls**. The source register contains **575 primary research requirements** and **270 supporting verification/configuration rows**.

| Domain | Consolidated controls |
|---|---:|
| Governance | 7 |
| API and HTTP | 19 |
| Identity and access | 18 |
| Audit and moderation | 16 |
| Database | 18 |
| Payments | 13 |
| Storage and uploads | 9 |
| Background jobs | 8 |
| Frontend | 13 |
| Testing and CI | 17 |
| Operations | 25 |

## Governance

| ID | Requirement | Class | Priority | Evidence types | Source requirement IDs | Status | Notes |
|---|---|---|---|---|---|---|---|
| GOV-001 | Maintain an authoritative production architecture and trust-boundary inventory covering frontend, API, workers, scheduler, PostgreSQL, Firebase, Stripe, R2, DNS/CDN, CI, monitoring, backups, public entry points, private services, regions, and single points of failure. | MUST | P0 | PROCESS; CONFIG; PROVIDER | DEPLOY-001; API-043; EXT-001–012 | NOT ASSESSED |  |
| GOV-002 | Maintain a complete environment matrix for local, test, staging, and production. Firebase projects, Stripe modes, R2 buckets, PostgreSQL databases, domains, webhooks, secrets, logs, and CI credentials must not cross environments accidentally. | MUST | P0 | CONFIG; PROVIDER; RUNTIME | FBAUTH-028–030; FE-002–003; STRIPE-006; STORAGE-001–004; DEPLOY-004; EXT-001–012 | NOT ASSESSED |  |
| GOV-003 | Define data classifications and handling rules for public, internal, personal, private-message, financial, moderation, audit, authentication, and secret data. Classification must drive access, display, logging, caching, retention, backup, export, and deletion. | MUST | P1 | PROCESS; CODE; PROVIDER | SENS-001–012; DATA-001–004; AUDIT-007; API-033–034 | NOT ASSESSED |  |
| GOV-004 | Assign named owners for authentication, authorization, payments, database, storage, workers, deployment, secrets, monitoring, backups, incident response, privacy operations, and provider accounts. | MUST DECIDE | P1 | PROCESS; PROVIDER | AUDIT-002; SECRET-001–010; IR-001–012; EXT-001–012 | NOT ASSESSED |  |
| GOV-005 | Use the normalized audit statuses PASS, PARTIAL, FAIL, NEEDS DECISION, NOT APPLICABLE, and EXTERNAL EVIDENCE REQUIRED. Every result must include evidence and a source-control reference. | MUST | P1 | PROCESS | All seven reports; consolidated checklist method | NOT ASSESSED |  |
| GOV-006 | Do not invent universal limits for request size, timeout, rate, worker count, pool size, indexes, retries, retention, RPO, RTO, or alert thresholds. Each value must have a documented basis and boundary test. | MUST DECIDE | P1 | PROCESS; RUNTIME; LOAD | API-006–007, 016–021; DBCONN-002–004; QUERY-001–010; JOB-005–007; RECOVERY-001–014 | NOT ASSESSED |  |
| GOV-007 | Record risk acceptance and exceptions with owner, justification, compensating controls, expiry or review date, and verification evidence. | MUST | P1 | PROCESS; REPO/CI | CI-005–014; SUPPLY-001–013; IR-001–012 | NOT ASSESSED |  |

## API and HTTP

| ID | Requirement | Class | Priority | Evidence types | Source requirement IDs | Status | Notes |
|---|---|---|---|---|---|---|---|
| API-M01 | Initialize shared process-scoped resources through a controlled application lifecycle and close them during graceful teardown. Avoid unsafe import-time network or migration side effects. | SHOULD | P1 | CODE; RUNTIME | API-001; DBCONN-005 | NOT ASSESSED |  |
| API-M02 | Parse production configuration through typed validation. Missing, malformed, unsafe, or cross-environment values must prevent readiness rather than silently use development defaults. | MUST | P0 | CODE; CONFIG; RUNTIME | API-002–003; DEPLOY-004; FE-002 | NOT ASSESSED |  |
| API-M03 | Run Uvicorn without reload under reliable supervision. Worker count, concurrency, keep-alive, recycling, shutdown, and instance count must be deliberate and compatible with database/provider limits. | MUST | P0 | CONFIG; RUNTIME; LOAD | API-004–007; DEPLOY-006–007; DBCONN-002 | NOT ASSESSED |  |
| API-M04 | Trust forwarded scheme, host, and client-address metadata only from known immediate proxies. Define multi-hop normalization and prevent direct-origin bypass. | MUST | P0 | CONFIG; RUNTIME; PROVIDER | API-008–009, 045–046 | NOT ASSESSED |  |
| API-M05 | Enforce an explicit host allowlist and canonical domain policy, including deliberate preview-domain handling. | MUST | P1 | CONFIG; RUNTIME; PROVIDER | API-010; DEPLOY-011 | NOT ASSESSED |  |
| API-M06 | Serve public traffic only over HTTPS. Assign one layer to redirects and HSTS, verify external TLS behavior, and avoid redirect loops behind proxies. | MUST | P0 | PROVIDER; RUNTIME; CONFIG | API-011, 014; DEPLOY-011 | NOT ASSESSED |  |
| API-M07 | Use an exact reviewed CORS origin allowlist and explicitly required methods/headers. Treat CORS as a browser policy, not authentication or authorization. | MUST | P0 | CODE; CONFIG; RUNTIME | API-012–013 | NOT ASSESSED |  |
| API-M08 | Apply security headers by response class and owning layer. Browser-document controls belong primarily on frontend HTML and interactive docs; JSON responses still require content-sniffing, cache, transport, and framing review. | MUST DECIDE | P1 | CONFIG; RUNTIME | API-014; FESEC-012; DEPLOY-011 | NOT ASSESSED |  |
| API-M09 | Apply finite body, multipart, file, header, URL, query, pagination, search, export, and bulk-operation limits before expensive work. Effective limits across edge, server, parser, and application must be documented and tested. | MUST | P0 | CODE; CONFIG; RUNTIME; LOAD | API-015–017; STORAGE-013–020 | NOT ASSESSED |  |
| API-M10 | Define layered connection, body-read, application, database, provider, and proxy timeout budgets. Handle cancellation and release resources; move long-running durable work out of request processes. | MUST | P0 | CODE; CONFIG; RUNTIME | API-018–019; JOB-001–028; DEPLOY-006 | NOT ASSESSED |  |
| API-M11 | Use endpoint-aware abuse controls with appropriate IP, user, token, resource, and administrative scopes. Multi-instance behavior, Retry-After, failure mode, and monitoring must be explicit. | MUST | P0 | CODE; CONFIG; RUNTIME; PROVIDER | API-020–021, 044; FBAUTH-018; OBS-005 | NOT ASSESSED |  |
| API-M12 | Return a stable, non-disclosing JSON error contract with machine code, safe message, HTTP status, and request ID. Global handling must cover validation, malformed JSON, provider/database failures, timeouts, and unexpected exceptions without exposing internals. | MUST | P0 | CODE; RUNTIME | API-022–024; FE-010–012 | NOT ASSESSED |  |
| API-M13 | Use documented HTTP methods, status codes, content types, authentication challenges, retry semantics, and idempotent behavior. Do not mutate through safe methods or silently accept unsupported media types. | MUST | P1 | CODE; RUNTIME; CONTRACT TEST | API-024–027 | NOT ASSESSED |  |
| API-M14 | Use separate request, internal, public, and administrative schemas. Filter responses, define timestamp/UUID/money/null semantics, and paginate or stream large results deliberately. | MUST | P0 | CODE; RUNTIME; CONTRACT TEST | API-027–029; AUTHZ-011–014; SCHEMA-005–007 | NOT ASSESSED |  |
| API-M15 | Generate or validate request IDs, propagate safe correlation context, and emit structured access logs using route templates. Never log credentials, client secrets, presigned URLs, private messages, full payment data, or unnecessary personal data. | MUST | P0 | CODE; CONFIG; RUNTIME; PROVIDER | API-030–033; FBAUTH-005; AUDIT-015–016; OBS-001–004 | NOT ASSESSED |  |
| API-M16 | Define cache behavior for every response class. Prevent shared-cache leakage of authenticated, administrative, inbox, messaging, payment, or private data; use validators only for intentionally cacheable public resources. | MUST | P0 | CODE; CONFIG; RUNTIME | API-034–035; SENS-008; FESEC-009–010 | NOT ASSESSED |  |
| API-M17 | Provide distinct startup, liveness, and readiness semantics, minimal uncached health responses, and a non-sensitive release identifier. Detailed diagnostics must be restricted. | MUST | P1 | CODE; CONFIG; RUNTIME; PROVIDER | API-036–038; DEPLOY-005 | NOT ASSESSED |  |
| API-M18 | Choose and verify OpenAPI/docs exposure, maintain endpoint inventory, and manage compatibility, deprecation, and versioning deliberately. Hiding documentation must not substitute for authorization. | MUST DECIDE | P1 | CODE; CONFIG; RUNTIME; CONTRACT TEST | API-039–043 | NOT ASSESSED |  |
| API-M19 | Keep the complete HTTP chain current and aligned on message framing. Authorized end-to-end tests must cover proxy spoofing, ambiguous framing, CORS, limits, caching, errors, timeouts, and graceful shutdown. | MUST | P1 | RUNTIME; SECURITY TEST; PROVIDER | API-045–046 | NOT ASSESSED |  |

## Identity and access

| ID | Requirement | Class | Priority | Evidence types | Source requirement IDs | Status | Notes |
|---|---|---|---|---|---|---|---|
| IAM-001 | Verify every protected request with the maintained Firebase Admin SDK for the explicitly configured project. Accept only Firebase ID tokens and validate signature, issuer, audience, time, subject, and syntax. | MUST | P0 | CODE; RUNTIME; PROVIDER | FBAUTH-001–003 | NOT ASSESSED |  |
| IAM-002 | Transmit bearer tokens only through HTTPS Authorization headers. Do not accept them from URLs or forms, duplicate them in browser storage, forward them unnecessarily, or expose them to logs and telemetry. | MUST | P0 | CODE; RUNTIME; BUNDLE/LOG SCAN | FBAUTH-004–006, 015; API-033; FESEC-008, 013 | NOT ASSESSED |  |
| IAM-003 | Make browser Firebase persistence an explicit risk decision. Token refresh and retry must be bounded and must not replay non-idempotent mutations blindly. | MUST DECIDE | P1 | CODE; RUNTIME | FBAUTH-007–008; FE-011; FESEC-008 | NOT ASSESSED |  |
| IAM-004 | Distinguish cryptographic token validity, Firebase account validity, local account state, and current authorization. Suspension, deletion, disablement, role removal, or revocation must take effect within a documented interval across instances and caches. | MUST | P0 | CODE; RUNTIME; PROVIDER | FBAUTH-009–014; ACCOUNT-001–016; AUTHZ-019 | NOT ASSESSED |  |
| IAM-005 | Provision local users idempotently by Firebase UID with uniqueness and concurrent-first-login protection. Never attach a new UID to an old account merely because an email matches. | MUST | P0 | CODE; SCHEMA; CONCURRENCY TEST | FBAUTH-019–025; ACCOUNT-001–004; SCHEMA-002 | NOT ASSESSED |  |
| IAM-006 | Document the source of truth and synchronization policy for UID, email, verification status, display name, phone, provider links, role, account status, ownership, and permissions. | MUST DECIDE | P1 | PROCESS; CODE; RUNTIME | FBAUTH-019–025; AUTHZ-001; ACCOUNT-001–016 | NOT ASSESSED |  |
| IAM-007 | Define operation-specific verified-email policy. Administrator identity must use a verified, currently controlled identifier; other requirements depend on abuse and recovery risk. | MUST DECIDE | P1 | CODE; RUNTIME; PROVIDER | FBAUTH-016 | NOT ASSESSED |  |
| IAM-008 | Require recent authentication or step-up controls for Firebase-sensitive account changes and other approved high-risk actions. Administrator MFA is required unless a documented provider limitation and compensating control exists. | MUST | P0 | CODE; RUNTIME; PROVIDER; PROCESS | FBAUTH-017, 029–030; ADMIN-004–008 | NOT ASSESSED |  |
| IAM-009 | Keep account recovery and sign-in responses enumeration-resistant and abuse-controlled. Preserve recovery ownership, factor reset, and emergency revocation procedures. | MUST | P0 | CODE; RUNTIME; PROVIDER; PROCESS | FBAUTH-018; ADMIN-006–008 | NOT ASSESSED |  |
| IAM-010 | Treat Firebase App Check as optional defense in depth for supported clients. It must not replace authentication, authorization, rate limiting, or replay-safe business operations. | CONDITIONAL | P2 | CODE; RUNTIME; PROVIDER | FBAUTH-027 | NOT ASSESSED |  |
| IAM-011 | Use managed identity, ADC, or workload-identity federation for Firebase Admin access where supported. Long-lived service-account keys require least privilege, restricted storage, inventory, rotation, monitoring, and emergency revocation. | MUST | P0 | CONFIG; PROVIDER; PROCESS | FBAUTH-026, 028; SECRET-001–006; EXT-003 | NOT ASSESSED |  |
| IAM-012 | Deny authorization by default on every request. A valid token is insufficient without a current local user, permitted account state, function permission, resource relationship, and valid workflow state. | MUST | P0 | CODE; RUNTIME | AUTHZ-001–003 | NOT ASSESSED |  |
| IAM-013 | Enforce object, nested-resource, relationship, state, and function authorization server-side for every identifier and operation. UUID opacity, hidden routes, and frontend guards are not security controls. | MUST | P0 | CODE; RUNTIME; SECURITY TEST | AUTHZ-004–008 | NOT ASSESSED |  |
| IAM-014 | Enforce field-level authorization with purpose-specific schemas and explicit field mapping. Reject mass assignment of roles, ownership, account state, payment state, provider IDs, timestamps, and administrative fields. | MUST | P0 | CODE; RUNTIME | AUTHZ-009–014; API-M14 | NOT ASSESSED |  |
| IAM-015 | Scope list, search, aggregate, cursor, bulk, and export queries to the current actor and visibility state. Decide when 403 or 404 concealment is appropriate and apply it consistently. | MUST | P0 | CODE; RUNTIME | AUTHZ-015–018 | NOT ASSESSED |  |
| IAM-016 | Use a current backend administrator gate that requires a valid identity, existing local user, active state, non-deleted state, and current administrator permission on every request. | MUST | P0 | CODE; RUNTIME | ADMIN-001–003 | NOT ASSESSED |  |
| IAM-017 | Protect role grants/removals, account suspension/deletion/restoration, financial mutations, private-message access, exports, and platform notices with action-specific permission, recent authentication, confirmation, idempotency, current-state checks, and auditability. | MUST | P0 | CODE; RUNTIME; AUDIT | ADMIN-004–012; ENF-001–008 | NOT ASSESSED |  |
| IAM-018 | Use named administrator accounts, controlled bootstrap and offboarding, and prevent unsafe removal of the final recoverable administrator. Shared accounts are prohibited. Impersonation and break-glass features are conditional and tightly controlled if implemented. | MUST | P1 | PROVIDER; PROCESS; RUNTIME | ADMIN-009–015; SECRET-007–010 | NOT ASSESSED |  |

## Audit and moderation

| ID | Requirement | Class | Priority | Evidence types | Source requirement IDs | Status | Notes |
|---|---|---|---|---|---|---|---|
| ADM-001 | Maintain a distinct authoritative administrative audit trail separate from access logs, application logs, moderation findings, case history, financial ledgers, and business status history. | MUST | P0 | CODE; SCHEMA; PROCESS | AUDIT-001–002 | NOT ASSESSED |  |
| ADM-002 | Audit consequential privileged successes, sensitive reads, significant failures, authorization denials, conflicts, duplicate/replay outcomes, provider failures, and security/access configuration changes. | MUST | P0 | CODE; RUNTIME | AUDIT-003–005 | NOT ASSESSED |  |
| ADM-003 | Use structured minimized audit records with immutable ID, authoritative time, actor, role context, target, action, outcome, stable failure code, request ID, environment/release, and linked domain identifiers. Store selected changes, not unrestricted snapshots. | MUST | P0 | SCHEMA; CODE; RUNTIME | AUDIT-006–009, 014 | NOT ASSESSED |  |
| ADM-004 | Make the normal audit-writing path append-only and tightly permissioned. Corrections must be new linked events. Direct update/delete must not be available to ordinary application or administrator roles. | MUST | P0 | SCHEMA; DB PRIVILEGE; RUNTIME | AUDIT-010–013 | NOT ASSESSED |  |
| ADM-005 | Define transaction and failure behavior for audit writes. A privileged mutation must not silently succeed without its required audit record; external copies or forwarding must tolerate retry and duplication. | MUST | P0 | CODE; SCHEMA; FAILURE TEST | AUDIT-011–013; ENF-005 | NOT ASSESSED |  |
| ADM-006 | Redact secrets and unnecessary personal data before emission at every logging boundary. Encode untrusted fields to prevent newline, terminal, HTML, JSON, and spreadsheet injection. | MUST | P0 | CODE; CONFIG; RUNTIME | AUDIT-015–016; SENS-006–007; API-033 | NOT ASSESSED |  |
| ADM-007 | Restrict audit search, sensitive reads, unmasking, and exports by task and permission. Log access to private messages, payment context, moderation evidence, audit records, and exports. | MUST | P0 | CODE; UI; RUNTIME; ACCESS REVIEW | AUDIT-017–020; SENS-001–011 | NOT ASSESSED |  |
| ADM-008 | Define audit review, alerting, retention, archive, deletion/anonymization, legal-hold, and export handling by data category. No universal retention period is assumed. | MUST DECIDE | P1 | PROCESS; CONFIG; PROVIDER | AUDIT-018–020; DATA-003–004 | NOT ASSESSED |  |
| ADM-009 | Maintain a versioned moderation taxonomy and record the rule, scanner or model identity, version, configuration, language/context limits, and execution time for every finding. Machine learning is not required. | MUST | P1 | CODE; SCHEMA; PROCESS | MOD-001–003, 012 | NOT ASSESSED |  |
| ADM-010 | Bind findings to a specific target field and content version/hash. Preserve minimal evidence and offsets safely, deduplicate repeated scans, and mark earlier findings historical or stale after edits. | MUST | P0 | CODE; SCHEMA; RUNTIME | MOD-004–010 | NOT ASSESSED |  |
| ADM-011 | Represent scanner timeout, outage, partial result, queue failure, and evidence-write failure as explicit non-clean states. Retry idempotently and expose exhausted work and backlog to operators. | MUST | P0 | CODE; JOB; RUNTIME; MONITORING | MOD-011; JOB-001–028; OBS-007 | NOT ASSESSED |  |
| ADM-012 | Use explicit server-enforced review-case state transitions, links, assignments, outcomes, notes, and append-only event history. Case creation, merging, automatic resolution, and concurrent review must be idempotent and conflict-safe. | MUST | P0 | CODE; SCHEMA; RUNTIME | CASE-001–009 | NOT ASSESSED |  |
| ADM-013 | Apply enforcement through action-specific permissions, required target/action/reason/current-state inputs, scoped idempotency, preconditions, explicit external-side-effect states, and separate reversal/restoration records. | MUST | P0 | CODE; SCHEMA; RUNTIME | ENF-001–008 | NOT ASSESSED |  |
| ADM-014 | Generate user-safe enforcement notices according to documented policy. Delayed or suppressed notice requires a structured reason; internal detection, fraud, reporter, or security details must not leak. Appeals remain a product/legal decision. | MUST DECIDE | P1 | CODE; PROCESS; RUNTIME | ENF-009–011 | NOT ASSESSED |  |
| ADM-015 | Return minimum-necessary administrative data from the backend. Default to excerpt-first private-message and moderation-evidence views, controlled unmasking, anti-caching, and restricted export. Frontend masking alone is insufficient. | MUST | P0 | CODE; UI; RUNTIME | SENS-001–012 | NOT ASSESSED |  |
| ADM-016 | Model notice campaign, immutable content version, audience definition/snapshot, recipient record, and delivery attempt separately. Creation, recipient delivery, cancellation, correction, retry, and large-audience processing must be idempotent and observable. | MUST | P0 | CODE; SCHEMA; JOB; RUNTIME | NOTICE-001–010 | NOT ASSESSED |  |

## Database

| ID | Requirement | Class | Priority | Evidence types | Source requirement IDs | Status | Notes |
|---|---|---|---|---|---|---|---|
| DB-001 | Use one safe engine/pool per process model, never reuse inherited live connections after fork, and dispose pools during shutdown. | MUST | P0 | CODE; RUNTIME | DBCONN-001, 005–006 | NOT ASSESSED |  |
| DB-002 | Maintain a deployment-wide connection budget including API workers, instances, overflow, background workers, migrations, monitoring, autoscaling, rolling overlap, and operational reserve. Bound pool growth and wait time. | MUST DECIDE | P0 | CONFIG; RUNTIME; LOAD | DBCONN-002–004; OBS-006 | NOT ASSESSED |  |
| DB-003 | Use a separate Session or AsyncSession per request, job attempt, webhook attempt, and administrative operation. Never share sessions concurrently or reuse request sessions after completion. | MUST | P0 | CODE; RUNTIME | DBCONN-006–007 | NOT ASSESSED |  |
| DB-004 | Commit only after a unit of work succeeds; roll back on every failure including failed flush; close sessions deterministically; avoid provider calls and streaming while holding unnecessary transactions. | MUST | P0 | CODE; FAILURE TEST | DBCONN-008–012; TXN-001–004 | NOT ASSESSED |  |
| DB-005 | Define explicit transaction boundaries for booking, capacity, waitlists, Need a Sub, payments, refunds, credits, audit, notices, webhooks, and jobs. User-visible success must not precede durable commit. | MUST | P0 | CODE; SCHEMA; RUNTIME | TXN-001–006 | NOT ASSESSED |  |
| DB-006 | Coordinate database commits with external side effects using durable operation states, outbox/inbox or equivalent patterns, idempotency, compensation, and reconciliation. Never assume cross-provider atomicity. | MUST | P0 | CODE; SCHEMA; FAILURE TEST | TXN-005–008; FIN-001–025; JOB-001–028 | NOT ASSESSED |  |
| DB-007 | Use database-enforced serialization points for capacity, one-active-record, duplicate webhook, credit/refund, notice delivery, job claim, and concurrent administrative workflows. Prefer constraints, atomic conditional updates, or row/version controls over process-local locks. | MUST | P0 | CODE; SCHEMA; CONCURRENCY TEST | TXN-009–015; SCHEMA-001–004 | NOT ASSESSED |  |
| DB-008 | Choose isolation, row locking, optimistic versioning, NOWAIT/SKIP LOCKED, or serializable transactions by invariant. Handle deadlocks, serialization failures, lock timeouts, and unknown commit outcomes with whole-transaction retry only when safe. | MUST | P0 | CODE; CONFIG; CONCURRENCY TEST | TXN-009–015 | NOT ASSESSED |  |
| DB-009 | Enforce primary keys, foreign keys, unique/partial unique, check, exclusion, non-null, and conditional integrity rules in PostgreSQL whenever application validation alone cannot protect concurrent or direct writes. | MUST | P0 | SCHEMA; MIGRATION; RUNTIME | SCHEMA-001–005 | NOT ASSESSED |  |
| DB-010 | Use exact monetary types with explicit currency and rounding contracts; use timezone-aware timestamps and explicit UTC/offset serialization; define database versus ORM defaults deliberately. | MUST | P0 | SCHEMA; CODE; RUNTIME | SCHEMA-005–007; FIN-017; API-027 | NOT ASSESSED |  |
| DB-011 | Choose hard deletion, soft deletion, anonymization, or restricted retention per table. Soft-deleted rows must be consistently filtered and compatible with uniqueness, foreign keys, restoration, and historical records. | MUST DECIDE | P1 | SCHEMA; CODE; RUNTIME | SCHEMA-004, 008; DATA-005–007 | NOT ASSESSED |  |
| DB-012 | Base indexes on real query patterns, ordering, cardinality, and plans. Review foreign-key indexes, partial/composite/expression indexes, N+1 loading, statistics, autovacuum, redundant indexes, and write cost. | MUST | P1 | SCHEMA; QUERY PLAN; LOAD | QUERY-001–007; OBS-006 | NOT ASSESSED |  |
| DB-013 | Use stable deterministic pagination with complete ordering and tie-breakers. Protect cursor integrity and authorization context; test concurrent inserts, updates, and deletion. | MUST | P1 | CODE; SCHEMA; RUNTIME | QUERY-008–009; AUTHZ-015 | NOT ASSESSED |  |
| DB-014 | Use parameterized SQL and allowlist dynamic identifiers, sort columns, operators, and table/column names. Restrict unsafe raw SQL and prevent secret/query data leakage in logs. | MUST | P0 | CODE; STATIC ANALYSIS; RUNTIME | DBSEC-001–002; API-033 | NOT ASSESSED |  |
| DB-015 | Use separate least-privilege application, migration, read-only/reporting, worker, and backup roles where justified. The application must not run as owner or superuser; secure schema ownership, search_path, default privileges, and direct human access. | MUST | P0 | DB CONFIG; PROVIDER; ACCESS REVIEW | DBSEC-003–009; SECRET-007–010 | NOT ASSESSED |  |
| DB-016 | Maintain a single understood Alembic migration graph, review autogenerated migrations manually, verify model/schema drift, and manage extensions explicitly. | MUST | P1 | REPO; MIGRATION; SCHEMA | MIG-001–002, 011, 013–014 | NOT ASSESSED |  |
| DB-017 | Use expand-and-contract, backward-compatible migrations for rolling deployments. Avoid unbounded table rewrites and blocking DDL; add constraints/indexes and remove old columns only after compatibility windows. | MUST | P0 | MIGRATION REHEARSAL; RUNTIME | MIG-003–006, 012; DEPLOY-008–009 | NOT ASSESSED |  |
| DB-018 | Make large data migrations resumable, batched, observable, and independently recoverable where one Alembic transaction is unsafe. Test upgrade from empty and production-like schemas, interruption, old/new compatibility, and rollback or forward-fix plans. | MUST | P0 | CI; MIGRATION REHEARSAL; RESTORE | MIG-007–010; TEST-016 | NOT ASSESSED |  |

## Payments

| ID | Requirement | Class | Priority | Evidence types | Source requirement IDs | Status | Notes |
|---|---|---|---|---|---|---|---|
| PAY-001 | Derive amount and currency from trusted server-side booking, pricing, and credit data. Bind every checkout to an authenticated user and durable local operation identity. | MUST | P0 | CODE; SCHEMA; RUNTIME | STRIPE-001–002 | NOT ASSESSED |  |
| PAY-002 | Use stable Stripe idempotency keys plus local uniqueness and operation-state controls for PaymentIntent, refund, and other financial mutations. Same-key payload changes must conflict. | MUST | P0 | CODE; SCHEMA; RUNTIME | STRIPE-003–004; FIN-003–005 | NOT ASSESSED |  |
| PAY-003 | Expose PaymentIntent client secrets only to the authorized checkout user and never through URLs, logs, analytics, support artifacts, or cross-user responses. Keep publishable, secret, restricted, and webhook keys separated. | MUST | P0 | CODE; RUNTIME; LOG/BUNDLE SCAN | STRIPE-005–006; FESEC-002; SECRET-001–006 | NOT ASSESSED |  |
| PAY-004 | Treat PaymentIntent as provider payment-lifecycle authority and PostgreSQL as application-business authority. Client callbacks and return URLs must not create paid entitlements by themselves. | MUST | P0 | CODE; RUNTIME | STRIPE-007–012; FIN-001–002 | NOT ASSESSED |  |
| PAY-005 | Verify Stripe webhook signatures against the unmodified body with the correct environment and endpoint secret. Acknowledge promptly, record event IDs, and process durably. | MUST | P0 | CODE; CONFIG; RUNTIME; PROVIDER | STRIPE-013–017 | NOT ASSESSED |  |
| PAY-006 | Handle duplicate, delayed, missing, and out-of-order webhook events. Preserve event processing state, retrieve current provider state when needed, and never regress terminal local state from stale events. | MUST | P0 | CODE; SCHEMA; FAILURE TEST | STRIPE-014–019; FIN-001–008 | NOT ASSESSED |  |
| PAY-007 | Model booking and payment as an explicit state machine covering pending, action-required, processing, succeeded, failed, canceled, unknown, refunded, and capacity-conflict outcomes. Define reservation and compensation policy. | MUST DECIDE | P0 | CODE; SCHEMA; RUNTIME | FIN-001–012 | NOT ASSESSED |  |
| PAY-008 | Store only necessary saved-payment metadata and provider identifiers. Enforce Stripe Customer and PaymentMethod ownership, consent, attach/detach behavior, stale metadata refresh, and cross-user isolation. | MUST | P0 | CODE; SCHEMA; RUNTIME | STRIPE-020–024 | NOT ASSESSED |  |
| PAY-009 | Represent refunds as durable operations with amount/currency validation, remaining refundable amount, idempotency, provider/local states, unknown outcome handling, user notice, and reconciliation. | MUST | P0 | CODE; SCHEMA; RUNTIME; PROVIDER | FIN-009–016 | NOT ASSESSED |  |
| PAY-010 | Use an append-only or equivalently auditable credit ledger with exact amounts, current derived balance, concurrency-safe spend, idempotent issuance/reversal, and clear linkage to booking/refund/admin causes. | MUST | P0 | CODE; SCHEMA; CONCURRENCY TEST | FIN-017–021 | NOT ASSESSED |  |
| PAY-011 | Protect high-risk financial administration with action-specific permission, reauthentication/MFA, reason, preview/confirmation, current-state checks, idempotency, audit, and risk-based dual approval. | MUST | P0 | CODE; RUNTIME; PROCESS | FIN-022–025; ADMIN-010–012; ENF-008 | NOT ASSESSED |  |
| PAY-012 | Track disputes and asynchronous reversals, and reconcile Stripe PaymentIntents, charges, refunds, disputes, local payments, bookings, and credits on a risk-based schedule and on demand. | MUST | P0 | JOB; PROVIDER; PROCESS | STRIPE-018–019; FIN-006–008, 023–025; OBS-008 | NOT ASSESSED |  |
| PAY-013 | Pin and verify Stripe API/webhook versions, separate test/live settings and keys, restrict Dashboard access with MFA, monitor failed delivery and key use, and maintain emergency rotation procedures. | MUST | P0 | PROVIDER; CONFIG; PROCESS | STRIPE-006, 016–024; EXT-004; SECRET-001–010 | NOT ASSESSED |  |

## Storage and uploads

| ID | Requirement | Class | Priority | Evidence types | Source requirement IDs | Status | Notes |
|---|---|---|---|---|---|---|---|
| STO-001 | Separate production and non-production R2 buckets and credentials. Use bucket-scoped least-privilege tokens, protected account access, rotation, and no frontend exposure. | MUST | P0 | CONFIG; PROVIDER; PROCESS | STORAGE-001–004; EXT-005; SECRET-001–010 | NOT ASSESSED |  |
| STO-002 | Generate opaque server-controlled object keys without user path control or unnecessary personal data. Define immutable/versioned replacement behavior and prevent collisions or overwrites. | MUST | P0 | CODE; RUNTIME | STORAGE-005–008 | NOT ASSESSED |  |
| STO-003 | Issue presigned URLs only after authorization, bind them to method/key/operation, keep expiry short enough for the workflow, prevent logging, and treat them as reusable bearer credentials until expiry. | MUST | P0 | CODE; CONFIG; RUNTIME | STORAGE-009–012; SENS-006 | NOT ASSESSED |  |
| STO-004 | Use a staged upload workflow: authorize, create pending metadata, upload, confirm with object metadata, validate/process, then publish. Client claims alone must not activate an object. | MUST | P0 | CODE; SCHEMA; RUNTIME | STORAGE-013–018 | NOT ASSESSED |  |
| STO-005 | Validate declared type, extension, magic bytes, successful image decode, size, dimensions/pixel count, decompression risk, animation/SVG policy, and metadata exposure before publication. | MUST | P0 | CODE; RUNTIME; SECURITY TEST | STORAGE-019–023 | NOT ASSESSED |  |
| STO-006 | Isolate and bound image processing. Re-encode or sanitize when required, strip sensitive metadata according to policy, create derived assets idempotently, and expose explicit processing failures. | MUST DECIDE | P1 | JOB; RUNTIME | STORAGE-021–024 | NOT ASSESSED |  |
| STO-007 | Classify objects as public or private. Private moderation evidence and attachments must require authorized signed access; public images need safe content type, disposition, cache, and non-guessable keys. | MUST | P0 | CODE; CONFIG; RUNTIME | STORAGE-025–027 | NOT ASSESSED |  |
| STO-008 | Keep database metadata and R2 objects reconciled. Detect missing objects, orphan objects, failed derivatives, replacements, deleted owners, and status mismatches without unsafe automatic deletion. | MUST | P0 | JOB; SCHEMA; PROVIDER | STORAGE-028–031; OBS-009 | NOT ASSESSED |  |
| STO-009 | Define deletion, cache invalidation, abandoned-upload cleanup, lifecycle rules, and recovery for originals versus replaceable derivatives. Verify public access, custom domains, CORS, token scope, usage, and deletion controls in Cloudflare. | MUST DECIDE | P1 | CODE; JOB; PROVIDER; RECOVERY TEST | STORAGE-029–032; RECOVERY-007–009; EXT-005 | NOT ASSESSED |  |

## Background jobs

| ID | Requirement | Class | Priority | Evidence types | Source requirement IDs | Status | Notes |
|---|---|---|---|---|---|---|---|
| JOB-M01 | Use a durable database-backed or managed queue for financial, webhook, notice, image, deletion, reconciliation, and other work that must survive process loss. In-process tasks are only for disposable work. | MUST | P0 | CODE; SCHEMA; RUNTIME | JOB-001–004; FIN-001–025 | NOT ASSESSED |  |
| JOB-M02 | Persist job identity, type/version, safe payload/reference, status, priority, availability, attempts, lease/claim, timestamps, idempotency/correlation, and normalized failure data. | MUST | P0 | SCHEMA; CODE | JOB-005–008 | NOT ASSESSED |  |
| JOB-M03 | Claim work atomically using row locks/skip-locked or equivalent lease semantics. Handle worker crash, lease expiry, long jobs, heartbeats, batch fairness, and duplicate execution. | MUST | P0 | CODE; SCHEMA; CONCURRENCY TEST | JOB-009–013; TXN-009–015 | NOT ASSESSED |  |
| JOB-M04 | Design handlers for at-least-once execution with local/provider idempotency, partial-completion markers, safe resume, and duplicate side-effect prevention. | MUST | P0 | CODE; SCHEMA; FAILURE TEST | JOB-014–016 | NOT ASSESSED |  |
| JOB-M05 | Classify retryable versus permanent failures, use bounded backoff with jitter and Retry-After where applicable, and treat network timeout with unknown provider outcome as reconciliation work rather than blind replay. | MUST | P0 | CODE; CONFIG; FAILURE TEST | JOB-017–020 | NOT ASSESSED |  |
| JOB-M06 | Move exhausted, invalid, poison, or unsupported-version work into an operator-visible dead-letter state with safe repair and replay controls. | MUST | P1 | CODE; UI; PROCESS | JOB-021–023 | NOT ASSESSED |  |
| JOB-M07 | Define execution timeout, cancellation, deployment shutdown, lease release, scheduled-job singleton/duplicate-safe behavior, and version compatibility across rolling deployments. | MUST | P0 | CODE; CONFIG; RUNTIME | JOB-024–026; DEPLOY-002, 006, 008 | NOT ASSESSED |  |
| JOB-M08 | Monitor pending count, oldest age, throughput, attempts, failures, dead letters, active workers, expired leases, and worker version. Alert on user/financial impact and maintain repair runbooks. | MUST | P0 | MONITORING; RUNTIME; PROCESS | JOB-027–028; OBS-007; IR-001–012 | NOT ASSESSED |  |

## Frontend

| ID | Requirement | Class | Priority | Evidence types | Source requirement IDs | Status | Notes |
|---|---|---|---|---|---|---|---|
| FE-M01 | Produce deployable artifacts only with a verified Vite production build. Record mode, environment, API base URL, feature flags, base path, browser target, and release identity; never serve production with development or preview servers. | MUST | P0 | CI; BUILD; RUNTIME | FE-001–005 | NOT ASSESSED |  |
| FE-M02 | Treat all VITE-prefixed/build-time values as public. Maintain a frontend configuration allowlist and scan the built bundle and source maps for secrets, localhost, wrong environment, and live/test provider mismatches. | MUST | P0 | BUILD SCAN; CI | FE-002–003; FESEC-001–002; CI-005 | NOT ASSESSED |  |
| FE-M03 | Keep React effects and subscriptions cleanup-safe, use stable keys and state identity, and prevent state updates from stale or unmounted work. | MUST | P1 | CODE; UNIT/COMPONENT TEST | FE-006–009 | NOT ASSESSED |  |
| FE-M04 | Use a central API-client policy for current tokens, request IDs, timeout/cancellation, safe retries, JSON/error handling, empty responses, and non-idempotent mutation protection. | MUST | P0 | CODE; UNIT/INTEGRATION TEST | FE-010–012; FBAUTH-008; API-M12 | NOT ASSESSED |  |
| FE-M05 | Prevent stale and cross-user results through aborting/ignoring obsolete requests, identity-scoped cache keys, invalidation on logout/role/account changes, and guarded optimistic updates. | MUST | P0 | CODE; BROWSER TEST | FE-007, 011–014; FESEC-009–010 | NOT ASSESSED |  |
| FE-M06 | Treat client route guards and hidden controls as navigation only. Direct URL refresh, unknown routes, role changes, suspension, deletion, and redirect destinations must fail safely while backend authorization remains authoritative. | MUST | P0 | CODE; BROWSER TEST | FE-015–016; AUTHZ-008 | NOT ASSESSED |  |
| FE-M07 | Use server validation as authoritative. Forms must handle accessible field/form errors, unknown fields, double submission, unsaved changes, date/time, files, and sensitive actions without trusting hidden or disabled fields. | MUST | P1 | CODE; COMPONENT/BROWSER TEST | FE-017–018; FESEC-006 | NOT ASSESSED |  |
| FE-M08 | Render untrusted content as escaped text by default. Any HTML/Markdown/rich text requires a reviewed sanitizer; dangerous DOM sinks, scriptable URL schemes, open redirects, and unsafe external-link behavior must be blocked. | MUST | P0 | CODE; SECURITY TEST | FESEC-003–007 | NOT ASSESSED |  |
| FE-M09 | Inventory and approve third-party JavaScript, pin and monitor dependencies, minimize data collection, and apply CSP/SRI or other controls where compatible. A provider script failure must not expose secrets or corrupt state. | MUST DECIDE | P1 | CODE; CONFIG; SUPPLY CHAIN | FESEC-011–012; SUPPLY-001–013 | NOT ASSESSED |  |
| FE-M10 | Minimize browser persistence of tokens, private messages, administrative data, payment client secrets, and presigned URLs. Clear identity-specific state on logout and user switch; use no-store for sensitive responses. | MUST | P0 | CODE; BROWSER TEST | FESEC-008–010, 013–014; SENS-008 | NOT ASSESSED |  |
| FE-M11 | Provide explicit loading, empty, stale, offline/network, unauthorized, deleted, processing, retryable-failure, and permanent-failure states. Avoid indefinite spinners and destructive retries. | MUST | P1 | COMPONENT/BROWSER TEST | FE-010–014; UX-001 | NOT ASSESSED |  |
| FE-M12 | Adopt a documented accessibility target based on WCAG 2.2, normally AA unless a justified policy says otherwise. Verify semantic structure, keyboard operation, focus, dialogs, forms, status messages, contrast, reflow, zoom, reduced motion, and screen-reader behavior. | MUST DECIDE | P1 | AUTOMATED + MANUAL ACCESSIBILITY TEST | UX-001–008 | NOT ASSESSED |  |
| FE-M13 | Define supported browsers and responsive behavior. Measure Core Web Vitals and route-specific performance using production builds, realistic devices/networks, image sizing, code splitting, and controlled third-party scripts. Source-map and telemetry exposure must be deliberate. | MUST DECIDE | P1 | BUILD; LAB/FIELD PERFORMANCE; BROWSER TEST | UX-009–012; FESEC-013–014 | NOT ASSESSED |  |

## Testing and CI

| ID | Requirement | Class | Priority | Evidence types | Source requirement IDs | Status | Notes |
|---|---|---|---|---|---|---|---|
| TST-001 | Maintain an explicit test taxonomy: unit, component, backend service, API integration, PostgreSQL integration, mocked browser, full-stack browser, provider sandbox/emulator, migration, concurrency, security, and production smoke tests. | MUST | P1 | REPO; CI; PROCESS | TEST-001–004 | NOT ASSESSED |  |
| TST-002 | Test user-visible behavior and domain invariants at the lowest useful layer without replacing integration coverage. Backend database tests must use PostgreSQL when PostgreSQL behavior matters. | MUST | P1 | TEST CODE; CI | TEST-005–010 | NOT ASSESSED |  |
| TST-003 | Use Playwright semantic locators, web-first assertions, isolated contexts, deterministic state, controlled time, and useful traces/screenshots on failure. Avoid arbitrary sleeps and brittle CSS/XPath selectors. | MUST | P1 | TEST CODE; CI ARTIFACTS | TEST-011–014 | NOT ASSESSED |  |
| TST-004 | Separate mocked browser, full-stack, and provider-integration projects so their dependencies and guarantees are unmistakable. Provider tests must use emulator/test/sandbox resources and never production data or live charges. | MUST | P0 | TEST CONFIG; CI; PROVIDER | TEST-012–014; CI-013 | NOT ASSESSED |  |
| TST-005 | Cover authentication, revocation, account state, object/function/field authorization, cross-user substitution, stale roles, admin privilege removal, and direct API access. | MUST | P0 | API/BROWSER TEST | TEST-015; FBAUTH runtime matrices; AUTHZ-001–020 | NOT ASSESSED |  |
| TST-006 | Cover payment success/failure/action/processing, duplicate checkout, webhook signature/replay/order, refund, credit, provider timeout, local/provider partial failure, and reconciliation using Stripe test mode. | MUST | P0 | INTEGRATION/PROVIDER TEST | TEST-015; STRIPE/FIN runtime matrices | NOT ASSESSED |  |
| TST-007 | Cover upload authorization, wrong type/size, malformed or decompression-heavy image, expired URL, wrong key, confirmation replay, processing failure, missing/orphan/deleted object, and cache behavior. | MUST | P0 | INTEGRATION/PROVIDER TEST | TEST-015; STORAGE runtime matrix | NOT ASSESSED |  |
| TST-008 | Use deterministic concurrency tests for capacity, waitlists, duplicate provisioning, webhooks, refunds, credits, administrative actions, and job claiming. | MUST | P0 | CONCURRENCY TEST | TEST-015; TXN-009–015; JOB-009–016 | NOT ASSESSED |  |
| TST-009 | Test the full migration chain from empty and production-like schemas, schema drift, data preservation, interruption/resume, old/new application overlap, and rollback/forward-fix behavior. | MUST | P0 | CI; MIGRATION REHEARSAL | TEST-016; MIG-001–014 | NOT ASSESSED |  |
| TST-010 | Use synthetic, non-production test data; isolate database, browser, auth, storage, provider objects, time, environment, and background workers. Tests must be order-independent and clean up after failure. | MUST | P1 | TEST CONFIG; CI | TEST-017–019 | NOT ASSESSED |  |
| TST-011 | Treat retries as diagnostic aids, not defect masking. Track flaky tests with owner and expiry; retain sanitized artifacts and root-cause recurring failures. Use risk-based coverage rather than a universal percentage. | MUST DECIDE | P1 | CI; PROCESS | TEST-020–022 | NOT ASSESSED |  |
| TST-012 | Run CI from a clean reviewed revision with explicit Node/npm/Python/tool versions and frozen dependency resolution. Lockfile or dependency-manifest mismatch must fail. | MUST | P0 | CI CONFIG | CI-001–003 | NOT ASSESSED |  |
| TST-013 | Run noninteractive formatting, linting, type checks, secret scanning, dependency review, vulnerability analysis, tests, migration checks, production frontend build, and backend/container build. Required failures must block merge or release. | MUST | P0 | CI CONFIG; REPORTS | CI-004–011 | NOT ASSESSED |  |
| TST-014 | Protect default/release branches with pull requests, required checks, review, controlled bypass, and workflow-change ownership. Untrusted forks must not receive protected secrets or deployment authority. | MUST | P0 | REPO SETTINGS; CI SECURITY TEST | CI-012–014; SUPPLY-004–008 | NOT ASSESSED |  |
| TST-015 | Use least-privilege workflow permissions, safe event choice, no untrusted expression-to-shell interpolation, SHA-pinned third-party actions, protected environments, and short-lived OIDC credentials where supported. | MUST | P0 | CI CONFIG; REPO SETTINGS | SUPPLY-004–009 | NOT ASSESSED |  |
| TST-016 | Inventory dependencies and build inputs, review updates and suppressions, scan source/container/OS packages, and revoke any exposed secret rather than merely delete it from the latest revision. | MUST | P0 | CI; PROCESS | SUPPLY-001–003; CI-005–007 | NOT ASSESSED |  |
| TST-017 | Identify immutable release artifacts by digest/version and retain evidence linking source, dependencies, SBOM/provenance where adopted, test results, approvals, and deployment. Signing and higher SLSA targets are risk-based. | MUST DECIDE | P1 | CI; ARTIFACT REGISTRY; PROCESS | SUPPLY-010–013; DEPLOY-010 | NOT ASSESSED |  |

## Operations

| ID | Requirement | Class | Priority | Evidence types | Source requirement IDs | Status | Notes |
|---|---|---|---|---|---|---|---|
| OPS-001 | Deploy frontend, API, workers, and scheduler as explicit responsibilities. API instances must be stateless for authoritative sessions, jobs, locks, uploads, and user data; shared durable services must hold cross-instance state. | MUST | P0 | ARCHITECTURE; CONFIG; RUNTIME | DEPLOY-002–003 | NOT ASSESSED |  |
| OPS-002 | Build runtime images from trusted maintained bases using separated build/runtime stages where practical. Exclude source-control secrets, service-account files, caches, tests, and unnecessary build tools; scan and rebuild for security updates. | MUST | P0 | CONTAINER IMAGE; CI | CONTAINER-001–004 | NOT ASSESSED |  |
| OPS-003 | Run containers with non-root identity, least capabilities, no privileged mode or Docker socket, controlled writable paths, and CPU/memory/process limits where the platform supports them. | MUST | P0 | RUNTIME CONFIG; SECURITY TEST | CONTAINER-005–010 | NOT ASSESSED |  |
| OPS-004 | Use health-gated rolling deployment with old/new frontend, API, worker, webhook, job, and schema compatibility. Retain immutable prior artifacts and maintain tested rollback/forward-fix plans. | MUST | P0 | DEPLOY CONFIG; RUNTIME; EXERCISE | DEPLOY-005–010; DB-017–018 | NOT ASSESSED |  |
| OPS-005 | Protect domain registrar, DNS, CDN, hosting, database, Firebase, Stripe, Cloudflare, repository, monitoring, and backup control planes with named accounts, MFA, least privilege, recovery ownership, and offboarding. | MUST | P0 | PROVIDER; ACCESS REVIEW | DEPLOY-011; SECRET-007–010; EXT-001–012 | NOT ASSESSED |  |
| OPS-006 | Store production secrets in a managed/platform secret store or equivalently controlled runtime injection. Never use source control, frontend bundles, Docker ARG/ENV build layers, logs, tickets, or shared files as secret stores. | MUST | P0 | CONFIG; IMAGE/BUNDLE SCAN; PROVIDER | SECRET-001–003; FESEC-001–002; CONTAINER-003 | NOT ASSESSED |  |
| OPS-007 | Maintain a secret inventory with owner, scope, dependent systems, storage, rotation/revocation procedure, emergency response, and safe overlap where supported. Prefer short-lived workload identity and OIDC over long-lived keys. | MUST | P0 | PROCESS; PROVIDER; EXERCISE | SECRET-004–010; FBAUTH-026; TST-015 | NOT ASSESSED |  |
| OPS-008 | Centralize structured frontend, API, worker, database, provider, and edge logs with release/environment/request/job/event context, restricted access, redaction, loss detection, and policy-driven retention. | MUST | P0 | CONFIG; PROVIDER; RUNTIME | OBS-001–004; API-M15; ADM-006 | NOT ASSESSED |  |
| OPS-009 | Measure API traffic/errors/latency, database pool/query/lock/storage health, worker backlog, payment/webhook/refund/reconciliation outcomes, upload/storage divergence, authentication failures, deployment health, and backup success. | MUST | P0 | METRICS; DASHBOARD; RUNTIME | OBS-005–010 | NOT ASSESSED |  |
| OPS-010 | Keep metric labels and telemetry attributes bounded and privacy-safe. Full distributed tracing is conditional, but request/job/payment correlation must be possible without raw credentials or high-cardinality personal data. | MUST DECIDE | P1 | CONFIG; TELEMETRY REVIEW | OBS-011–013; API-030–033 | NOT ASSESSED |  |
| OPS-011 | Create dashboards and symptom-based alerts tied to user, financial, and data outcomes. Derive thresholds from normal behavior, capacity, provider quotas, and recovery needs; test alert delivery and control maintenance suppression. | MUST | P0 | DASHBOARD; ALERT TEST; PROCESS | OBS-014–018 | NOT ASSESSED |  |
| OPS-012 | Define service indicators and internal objectives for availability, latency, correctness, payment reliability, worker delay, and data freshness. Formal public SLA, tracing, and complex synthetic journeys are context-dependent. | MUST DECIDE | P1 | PROCESS; METRICS | OBS-014–018 | NOT ASSESSED |  |
| OPS-013 | Subscribe to provider status and security notifications and correlate them with internal signals. Define degraded behavior for Firebase, Stripe, R2, PostgreSQL, hosting, DNS, and CDN outages. | MUST | P1 | PROVIDER; RUNBOOK; EXERCISE | IR-004–008; EXT-001–012 | NOT ASSESSED |  |
| OPS-014 | Maintain scaled incident response with severity, roles, containment, evidence preservation, recovery, reconciliation, communication, post-incident review, owners, and tracked actions. | MUST | P0 | PROCESS; EXERCISE | IR-001–003, 009–012 | NOT ASSESSED |  |
| OPS-015 | Maintain runbooks for API/DB outage, connection exhaustion, failed deployment/migration, worker backlog/dead letters, Stripe webhook/payment mismatch, R2 upload/credential failure, Firebase outage, secret compromise, certificate expiry, backup failure, and restore. | MUST | P0 | PROCESS; EXERCISE | IR-004–012 | NOT ASSESSED |  |
| OPS-016 | Model capacity and cost across API, database connections/storage, worker throughput, provider quotas, R2 requests/storage, logs/metrics, CI, and backups. Load-test critical peaks and alert before hard limits or budget surprises. | MUST DECIDE | P1 | LOAD TEST; PROVIDER; PROCESS | DEPLOY-012; OBS-005–010 | NOT ASSESSED |  |
| OPS-017 | Enable protected automated PostgreSQL backups with encryption, access restriction, monitored completion, retention decision, and separately protected backup credentials. | MUST | P0 | PROVIDER; CONFIG | RECOVERY-001–004 | NOT ASSESSED |  |
| OPS-018 | Select RPO and RTO by business impact. Enable PITR when required by the selected RPO, and verify actual backup/WAL window, version, roles, extensions, configuration, and restore dependencies. | MUST DECIDE | P0 | PROCESS; PROVIDER; RESTORE TEST | RECOVERY-001–004 | NOT ASSESSED |  |
| OPS-019 | Treat backup success as unproven until an isolated restore validates decryption, database integrity, application startup, identity mapping, Stripe/R2 references, jobs, and deletion tombstones. Repeat after material backup, version, extension, or key changes. | MUST | P0 | RESTORE TEST; PROCESS | RECOVERY-005–006 | NOT ASSESSED |  |
| OPS-020 | Classify R2 originals and derivatives by loss tolerance and implement recovery protection for irreplaceable objects. Preserve recoverable configuration, DNS, provider settings, monitoring, infrastructure, and secret recreation procedures. | MUST DECIDE | P1 | PROVIDER; BACKUP; EXERCISE | RECOVERY-007–012 | NOT ASSESSED |  |
| OPS-021 | Run tabletop and technical recovery exercises for restore, deployment rollback, secret compromise, webhook outage, worker backlog, provider outage, user-deletion failure, and domain/control-plane recovery. | MUST DECIDE | P1 | EXERCISE; PROCESS | RECOVERY-013–014; IR-001–012 | NOT ASSESSED |  |
| OPS-022 | Approve data-purpose and retention schedules for accounts, profiles, games, bookings, messages, notices, payments, images, moderation, audit, logs, metrics, backups, exports, and test data. Do not retain indefinitely by default. | MUST DECIDE | P1 | PROCESS; CONFIG | DATA-001–004; ADM-008 | NOT ASSESSED |  |
| OPS-023 | Implement account deletion, data access, correction, and export as authenticated, durable, retryable workflows across Firebase, PostgreSQL, Stripe references, R2, jobs, logs, and backups. Prevent cross-user exports and reapply deletion/anonymization after restore. | MUST | P0 | CODE; JOB; RUNTIME; RESTORE TEST | DATA-005–010; ACCOUNT-009–016 | NOT ASSESSED |  |
| OPS-024 | Do not copy production data into development or test without approved minimization/anonymization. Use synthetic data, separate provider modes, restricted dumps, cleanup, retention, and access controls. | MUST | P0 | PROCESS; ACCESS REVIEW; TEST CONFIG | DATA-011–012; TEST-017–019 | NOT ASSESSED |  |
| OPS-025 | Complete provider-dashboard verification for hosting, Firebase/Google Cloud, Stripe, Cloudflare/R2, PostgreSQL, DNS, repository, monitoring, and backups. Record safe configuration evidence without secret values. | MUST | P0 | PROVIDER; CONFIG | EXT-001–012; source reports dashboard matrices | NOT ASSESSED |  |

## Decision register

These decisions cannot be resolved from technology documentation alone. They must be answered before related controls can receive a final status.

| ID | Decision required | Status | Owner | Evidence |
|---|---|---|---|---|
| DEC-001 | Production hosting, edge, proxy, worker, scheduler, queue, secret-manager, monitoring, and managed PostgreSQL products. | OPEN |  |  |
| DEC-002 | API worker/instance count, connection budget, concurrency, keep-alive, timeout, and shutdown values. | OPEN |  |  |
| DEC-003 | Request, upload, pagination, search, bulk, rate-limit, and retry thresholds by endpoint and identity. | OPEN |  |  |
| DEC-004 | Firebase browser persistence, revocation-check strategy, email-verification gates, App Check, and ordinary-user MFA. | OPEN |  |  |
| DEC-005 | Administrator MFA factor, recent-authentication policy, privilege granularity, dual control, break-glass, and impersonation. | OPEN |  |  |
| DEC-006 | Account suspension and deletion behavior, grace period, restoration, retained/anonymized records, and provider ordering. | OPEN |  |  |
| DEC-007 | Moderation policy taxonomy, synchronous/asynchronous scanning, fail-open/closed rules, case states, notices, and appeals. | OPEN |  |  |
| DEC-008 | Audit, moderation, financial, message, telemetry, backup, export, and test-data retention periods. | OPEN |  |  |
| DEC-009 | Capacity representation and concurrency strategy for game spots, waitlists, bookings, and Need a Sub positions. | OPEN |  |  |
| DEC-010 | Booking/payment reservation model, pending states, expiration, capacity conflict, compensation, refund versus credit policy. | OPEN |  |  |
| DEC-011 | Credit ledger rules, expiration, transferability, mixed payment, negative balances, and administrative limits. | OPEN |  |  |
| DEC-012 | Public/private object classes, SVG/animation policy, re-encoding, metadata removal, malware scanning, and original retention. | OPEN |  |  |
| DEC-013 | Database pool/timeout/isolation choices, RLS value, PostgreSQL enums, soft deletion, and cursor snapshot semantics. | OPEN |  |  |
| DEC-014 | Migration deployment sequence, online DDL capabilities, production-size rehearsal, rollback versus forward-fix policy. | OPEN |  |  |
| DEC-015 | Browser support, WCAG conformance target, performance budgets, source-map policy, service workers, and analytics/session replay. | OPEN |  |  |
| DEC-016 | Coverage gates, provider tests in pull requests, browser-test parallelism, mutation testing, and flaky-test policy. | OPEN |  |  |
| DEC-017 | SBOM, signing, provenance, SLSA target, artifact promotion, and production approval policy. | OPEN |  |  |
| DEC-018 | SLIs/SLOs, alert thresholds, synthetic monitoring, on-call/escalation, maintenance, and incident severity model. | OPEN |  |  |
| DEC-019 | RPO, RTO, PITR window, backup retention, restore-test cadence, R2 recovery, and disaster-exercise frequency. | OPEN |  |  |
| DEC-020 | Data classifications, collection purposes, retention schedules, deletion/anonymization, backup disclosure, and privacy request process. | OPEN |  |  |

## Evidence package categories

| Category | Examples |
|---|---|
| Code | Routes, dependencies, services, schemas, exception handlers, redaction helpers, workers. |
| Static configuration | Environment schemas, Uvicorn/container commands, CORS, proxy trust, CI workflow, migration config. |
| Database/schema | Constraints, indexes, roles, privileges, migration graph, job/audit/payment state. |
| Runtime | Negative requests, concurrency, failure injection, cache isolation, graceful shutdown, provider timeout. |
| Provider dashboard | Firebase, Google IAM, Stripe, Cloudflare, hosting, PostgreSQL, DNS, repository, monitoring, backups. |
| Process | Access review, key rotation, incident response, retention, releases, reconciliation, exception handling. |
| Recovery/exercise | Database restore, deletion-after-restore, rollback, credential compromise, provider outage. |
