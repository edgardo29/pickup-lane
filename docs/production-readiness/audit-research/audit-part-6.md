# Pickup Lane Production-Readiness Static Audit — Part 6: Consolidated Synthesis

## 1. Synthesis metadata

| Field | Value |
|---|---|
| Synthesis date | August 3, 2026 |
| Input filenames read | audit-part-1.md; audit-part-2.md; audit-part-3.md; audit-part-4.md; audit-part-5.md; pickup-lane-master-production-readiness-checklist.md; pickup-lane-static-inventory-crosswalk.md; pickup-lane-research-consolidation-review.md |
| Finalized parts used | All five finalized parts were used |
| Control reconciliation | All 163 controls reconciled successfully |
| Finding changes | No locked control finding, Class, Priority, status, or evidence class was changed |
| Prohibited execution | No tests, builds, migrations, databases, services, workers, containers, provider tools, networks, backups, restores, or exercises were run |
| Files not readable | None |

## 2. Reconciliation result

| Check | Result |
|---|---|
| Expected control count | 163 |
| Actual unique control count | 163 |
| Duplicate count | 0 |
| Missing count | 0 |
| Unexpected count | 0 |
| Class mismatches | 0 |
| Priority mismatches | 0 |
| Status-vocabulary errors | 0 |
| Evidence-class errors | 0 |
| Assigned-Part errors | 0 |
| Final reconciliation result | PASS |

## 3. Executive readiness conclusion

The locked static audit supports that Pickup Lane has substantial repository-visible implementation across API, identity, payments, storage metadata, database models, frontend flows, and some current non-legacy test infrastructure. It does not support production-readiness sign-off because every P0 control remains unresolved.
P0 unresolved controls: 117. P0 confirmed FAIL controls: 29. P0 PARTIAL controls: 77. P0 NEEDS DECISION controls: 3. P0 EXTERNAL EVIDENCE REQUIRED controls: 8.
Dominant cross-domain reasons are missing runtime verification, missing provider-dashboard evidence, incomplete deployment and operational-process evidence, no durable background-job foundation, incomplete current test coverage for critical flows, incomplete observability and recovery evidence, and open owner decisions for key thresholds and policies.
## 4. Consolidated status counts

### 4.1 Counts by final status

| Final status | Count | Percentage of 163 |
|---|---|---|
| PASS | 0 | 0.0% |
| PARTIAL | 93 | 57.1% |
| FAIL | 36 | 22.1% |
| NEEDS DECISION | 26 | 16.0% |
| NOT APPLICABLE | 0 | 0.0% |
| EXTERNAL EVIDENCE REQUIRED | 8 | 4.9% |

### 4.2 Counts by Priority and final status

| Priority | PASS | PARTIAL | FAIL | NEEDS DECISION | NOT APPLICABLE | EXTERNAL EVIDENCE REQUIRED | Total |
|---|---|---|---|---|---|---|---|
| P0 | 0 | 77 | 29 | 3 | 0 | 8 | 117 |
| P1 | 0 | 16 | 7 | 22 | 0 | 0 | 45 |
| P2 | 0 | 0 | 0 | 1 | 0 | 0 | 1 |

### 4.3 Counts by Part and final status

| Part | Domains | PASS | PARTIAL | FAIL | NEEDS DECISION | NOT APPLICABLE | EXTERNAL EVIDENCE REQUIRED | Total |
|---|---|---|---|---|---|---|---|---|
| 1 | API and HTTP; Identity and access | 0 | 21 | 9 | 5 | 0 | 2 | 37 |
| 2 | Audit and moderation; Database | 0 | 27 | 2 | 4 | 0 | 1 | 34 |
| 3 | Payments; Storage and uploads; Background jobs | 0 | 16 | 10 | 3 | 0 | 1 | 30 |
| 4 | Frontend; Testing and CI | 0 | 21 | 3 | 5 | 0 | 1 | 30 |
| 5 | Governance; Operations | 0 | 8 | 12 | 9 | 0 | 3 | 32 |

### 4.4 Counts by Domain and final status

| Domain | PASS | PARTIAL | FAIL | NEEDS DECISION | NOT APPLICABLE | EXTERNAL EVIDENCE REQUIRED | Total |
|---|---|---|---|---|---|---|---|
| Governance | 0 | 3 | 2 | 2 | 0 | 0 | 7 |
| API and HTTP | 0 | 10 | 6 | 2 | 0 | 1 | 19 |
| Identity and access | 0 | 11 | 3 | 3 | 0 | 1 | 18 |
| Audit and moderation | 0 | 12 | 2 | 2 | 0 | 0 | 16 |
| Database | 0 | 15 | 0 | 2 | 0 | 1 | 18 |
| Payments | 0 | 11 | 1 | 1 | 0 | 0 | 13 |
| Storage and uploads | 0 | 5 | 1 | 2 | 0 | 1 | 9 |
| Background jobs | 0 | 0 | 8 | 0 | 0 | 0 | 8 |
| Frontend | 0 | 10 | 0 | 3 | 0 | 0 | 13 |
| Testing and CI | 0 | 11 | 3 | 2 | 0 | 1 | 17 |
| Operations | 0 | 5 | 10 | 7 | 0 | 3 | 25 |

## 5. Complete P0 unresolved-control index

| ID | Part | Domain | Class | Final status | Locked gap summary | Required evidence category |
|---|---|---|---|---|---|---|
| GOV-001 | 5 | Governance | MUST | PARTIAL | No authoritative architecture inventory covering workers, scheduler, monitoring, backups, DNS/CDN, regions, public and private services, or single points of failure. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; operational-process evidence; recovery/exercise evidence |
| GOV-002 | 5 | Governance | MUST | PARTIAL | No complete environment matrix across local, test, browser test, provider sandbox, staging, production, providers, secrets, logs, and CI credentials. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; operational-process evidence; current-test evidence |
| API-M02 | 1 | API and HTTP | MUST | PARTIAL | Development defaults remain for local CORS, API docs, DB health, and frontend API fallback; no central typed production-mode validation. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence |
| API-M03 | 1 | API and HTTP | MUST | FAIL | No backend process-supervision configuration for worker count, concurrency, keep-alive, recycling, shutdown, or instance count. | repository remediation later; runtime verification; deployment evidence; operational-process evidence |
| API-M04 | 1 | API and HTTP | MUST | FAIL | No trusted-proxy or multi-hop forwarded-header normalization configuration. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence |
| API-M06 | 1 | API and HTTP | MUST | EXTERNAL EVIDENCE REQUIRED | No repo-managed TLS redirect, HTTPS redirect middleware, HSTS, or security-header configuration; public HTTPS posture is provider-dependent. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence |
| API-M07 | 1 | API and HTTP | MUST | PARTIAL | Production origins are configurable, but methods and headers remain wildcard with credentials; runtime allow and deny behavior was not verified. | repository remediation later; runtime verification; current-test evidence |
| API-M09 | 1 | API and HTTP | MUST | PARTIAL | Limits are uneven and no global body, multipart, header, URL, export, or bulk enforcement appears before expensive work. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; current-test evidence |
| API-M10 | 1 | API and HTTP | MUST | FAIL | No production request-budget evidence for server, DB, provider, proxy, body-read, cancellation, keep-alive, or graceful timeout settings. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; current-test evidence |
| API-M11 | 1 | API and HTTP | MUST | PARTIAL | Only chat-scoped DB-count throttles were found; no broad endpoint-aware abuse-control policy or monitoring evidence. | repository remediation later; runtime verification; operational-process evidence; current-test evidence |
| API-M12 | 1 | API and HTTP | MUST | PARTIAL | No global stable error contract covering validation, malformed JSON, machine codes, request IDs, provider/database failures, timeouts, and unexpected exceptions. | repository remediation later; runtime verification; provider-dashboard evidence; current-test evidence |
| API-M14 | 1 | API and HTTP | MUST | PARTIAL | Request and response separation is incomplete by audience; serialization contract coverage is incomplete. | repository remediation later; runtime verification; current-test evidence |
| API-M15 | 1 | API and HTTP | MUST | FAIL | No production access-log, request-correlation, structured logging, centralized redaction, or safe logging policy. | repository remediation later; runtime verification; deployment evidence; operational-process evidence |
| API-M16 | 1 | API and HTTP | MUST | PARTIAL | Cache-Control evidence exists only for route-specific cases, not all private, admin, inbox, chat, payment, or profile responses. | repository remediation later; runtime verification; operational-process evidence; current-test evidence |
| IAM-001 | 1 | Identity and access | MUST | PARTIAL | Project/audience binding is implicit in SDK credentials, and token revocation checking is not explicit. | repository remediation later; runtime verification; provider-dashboard evidence; current-test evidence |
| IAM-002 | 1 | Identity and access | MUST | PARTIAL | Header transport is visible, but HTTPS, logs, bundle, telemetry, and complete exposure proof were not collected. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence |
| IAM-004 | 1 | Identity and access | MUST | PARTIAL | Firebase disabled/revoked behavior and cross-instance account-state timing are not proven. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence; current-test evidence |
| IAM-005 | 1 | Identity and access | MUST | PARTIAL | UID uniqueness exists, but simultaneous first-login concurrency proof was not collected. | repository remediation later; runtime verification; current-test evidence |
| IAM-008 | 1 | Identity and access | MUST | FAIL | No enforced recent-authentication, step-up, MFA, or compensating-control policy for high-risk account and admin actions. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence |
| IAM-009 | 1 | Identity and access | MUST | PARTIAL | Recovery abuse controls, Firebase dashboard settings, factor reset, and emergency revocation procedures remain external or operational. | runtime verification; provider-dashboard evidence; operational-process evidence; recovery/exercise evidence |
| IAM-011 | 1 | Identity and access | MUST | EXTERNAL EVIDENCE REQUIRED | Managed identity, service-account scope, restricted storage, inventory, rotation, monitoring, and emergency revocation cannot be proven statically. | runtime verification; provider-dashboard evidence; operational-process evidence |
| IAM-012 | 1 | Identity and access | MUST | PARTIAL | Broader authenticated-user dependencies may be intentional, but the route-family authorization matrix and tests are incomplete. | runtime verification; current-test evidence |
| IAM-013 | 1 | Identity and access | MUST | PARTIAL | Static review found no confirmed object, nested-resource, relationship, state, or function authorization gap, but evidence is representative rather than exhaustive. | repository remediation later; runtime verification; current-test evidence |
| IAM-014 | 1 | Identity and access | MUST | FAIL | Ordinary authenticated users can write a verifier-controlled email_verified_at timestamp through profile update. | repository remediation later; runtime verification; current-test evidence |
| IAM-015 | 1 | Identity and access | MUST | PARTIAL | List, search, aggregate, cursor, bulk, export scoping and 403/404 concealment are not fully proven. | repository remediation later; runtime verification; operational-process evidence; current-test evidence |
| IAM-016 | 1 | Identity and access | MUST | PARTIAL | Static admin-route inspection found gates, but runtime negative matrix coverage is incomplete. | repository remediation later; runtime verification; current-test evidence |
| IAM-017 | 1 | Identity and access | MUST | PARTIAL | Privileged operations rely mostly on broad active-admin gates, not named action-specific permissions, recent auth, or dual control evidence. | runtime verification; provider-dashboard evidence; operational-process evidence; current-test evidence |
| ADM-001 | 2 | Audit and moderation | MUST | PARTIAL | Several durable domain records exist, but access and application logs are not modeled as a distinct durable audit store. | runtime verification; operational-process evidence |
| ADM-002 | 2 | Audit and moderation | MUST | PARTIAL | Privileged success auditing is broad but not universal, and sensitive reads, denials, provider failures, and duplicate outcomes are incomplete. | runtime verification; provider-dashboard evidence; current-test evidence |
| ADM-003 | 2 | Audit and moderation | MUST | PARTIAL | Audit records do not consistently show request ID, environment, release, stable failure code, or actor role context snapshots. | runtime verification; current-test evidence |
| ADM-004 | 2 | Audit and moderation | MUST | PARTIAL | No database trigger, RLS, privilege separation, or append-only database enforcement was found. | repository remediation later; runtime verification; provider-dashboard evidence |
| ADM-005 | 2 | Audit and moderation | MUST | PARTIAL | Audit atomicity is inconsistent around external providers and failure paths. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; operational-process evidence; current-test evidence; recovery/exercise evidence |
| ADM-006 | 2 | Audit and moderation | MUST | PARTIAL | Redaction exists for admin metadata but is not proven as a repository-wide logging boundary. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence |
| ADM-007 | 2 | Audit and moderation | MUST | PARTIAL | Sensitive admin access uses broad active-admin gates, not task-specific permissions, unmasking controls, or complete read-audit proof. | runtime verification; operational-process evidence |
| ADM-010 | 2 | Audit and moderation | MUST | PARTIAL | Moderation findings bind content, but canonicalization version and stale-finding behavior remain incomplete. | runtime verification |
| ADM-011 | 2 | Audit and moderation | MUST | FAIL | No durable scanner timeout, outage, partial-result, queue-failure, evidence-write-failure, retry, backlog, or operator-visible exhausted state. | repository remediation later; runtime verification; operational-process evidence |
| ADM-012 | 2 | Audit and moderation | MUST | PARTIAL | Review-case state is modeled, but assignment, reopen, merge, and concurrent-review behavior are incomplete. | repository remediation later; runtime verification; recovery/exercise evidence |
| ADM-013 | 2 | Audit and moderation | MUST | PARTIAL | Enforcement has idempotency and audit patterns, but authorization is mostly broad active-admin and external side-effect states are incomplete. | runtime verification; recovery/exercise evidence |
| ADM-015 | 2 | Audit and moderation | MUST | FAIL | Full private chat message bodies are exposed by default without excerpt-first, controlled-unmask, or read-audit pattern. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence |
| ADM-016 | 2 | Audit and moderation | MUST | PARTIAL | Notice architecture lacks separate immutable content versions, complete audience snapshots, delivery attempts, retry/backoff state, worker processing, and delivery observability. | repository remediation later; runtime verification; deployment evidence; operational-process evidence |
| DB-001 | 2 | Database | MUST | PARTIAL | Static engine setup exists, but deployed topology, fork/reload behavior, and shutdown disposal are unproven. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; operational-process evidence |
| DB-002 | 2 | Database | MUST DECIDE | NEEDS DECISION | No owner-approved deployment-wide database connection budget. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; operational-process evidence; owner decision |
| DB-003 | 2 | Database | MUST | PARTIAL | Per-request sessions are visible, but callback lifetime and runtime exception behavior are not proven. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; operational-process evidence; current-test evidence |
| DB-004 | 2 | Database | MUST | PARTIAL | Provider calls still occur inside request workflows after local flush and before final durable commit. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence; recovery/exercise evidence |
| DB-005 | 2 | Database | MUST | PARTIAL | Transaction boundaries are uneven; some invariants are app-only and durable background-job boundaries are absent. | repository remediation later; runtime verification; provider-dashboard evidence; recovery/exercise evidence |
| DB-006 | 2 | Database | MUST | PARTIAL | No general transactional outbox, provider-operation inbox, delivery-attempt table, pending-operation table, or durable worker equivalent. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; operational-process evidence |
| DB-007 | 2 | Database | MUST | PARTIAL | Several critical invariants are app-only or partially database-enforced, including capacity, active booking, credits, and durable job-claiming. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; current-test evidence; recovery/exercise evidence |
| DB-008 | 2 | Database | MUST | PARTIAL | No production source evidence for explicit isolation, lock timeout, statement timeout, deadlock handling, serialization retry, optimistic versioning, or unknown-commit handling. | repository remediation later; runtime verification; provider-dashboard evidence |
| DB-009 | 2 | Database | MUST | PARTIAL | Schema is broad but incomplete for all business invariants; some UUID references and workflow-state rules remain application-only. | runtime verification; deployment evidence; current-test evidence |
| DB-010 | 2 | Database | MUST | PARTIAL | Static evidence does not prove runtime DB defaults, provider amount and currency round trips, DB timezone settings, or API serialization behavior. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence |
| DB-014 | 2 | Database | MUST | PARTIAL | Static SQL review is favorable, but production log redaction, provider logs, database logs, query-data exposure, and runtime SQL text behavior are unproven. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; operational-process evidence; current-test evidence |
| DB-015 | 2 | Database | MUST | EXTERNAL EVIDENCE REQUIRED | Production roles, grants, ownership, search path, human access, application and migration credentials, and credential rotation are outside repo evidence. | repository remediation later; provider-dashboard evidence; deployment evidence; operational-process evidence; current-test evidence; recovery/exercise evidence |
| DB-017 | 2 | Database | MUST | PARTIAL | Upgrade migrations are predominantly additive, but no expand-and-contract policy, online-index strategy, release sequencing, migration timeout, rollback, forward-fix, or rehearsal evidence. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence; recovery/exercise evidence |
| DB-018 | 2 | Database | MUST | PARTIAL | No large data migration is currently triggered, but upgrade, interruption, old/new compatibility, rollback, forward-fix, backup/restore integration, and observability evidence are absent. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence; recovery/exercise evidence |
| PAY-001 | 3 | Payments | MUST | PARTIAL | Trusted amount derivation exists for ordinary checkout and publish fees, but privileged repair flows can set amounts and need separate controls. | repository remediation later; runtime verification; provider-dashboard evidence |
| PAY-002 | 3 | Payments | MUST | PARTIAL | Idempotency exists in places, but same-key different-payload conflict handling is uneven. | repository remediation later; runtime verification; provider-dashboard evidence |
| PAY-003 | 3 | Payments | MUST | PARTIAL | Client-secret paths lack bundle, runtime-log, exception-log, analytics, and telemetry evidence. | runtime verification; provider-dashboard evidence; current-test evidence |
| PAY-004 | 3 | Payments | MUST | PARTIAL | Client callback does not grant entitlement statically, but return-url abuse, webhook ordering, and capacity-conflict behavior are unverified. | runtime verification; provider-dashboard evidence; operational-process evidence; current-test evidence |
| PAY-005 | 3 | Payments | MUST | PARTIAL | Webhook signature verification exists, but endpoint business logic runs before acknowledgment and retry/order behavior is unverified. | runtime verification; provider-dashboard evidence; operational-process evidence; current-test evidence |
| PAY-006 | 3 | Payments | MUST | PARTIAL | Webhook events exist, but dispute events and complete unknown-outcome/reconciliation behavior are missing. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence; recovery/exercise evidence |
| PAY-007 | 3 | Payments | MUST DECIDE | NEEDS DECISION | Canonical cross-object financial state policy is unresolved across payment, booking, dispute, capacity conflict, refund, credit, and money-issue states. | repository remediation later; operational-process evidence; owner decision |
| PAY-008 | 3 | Payments | MUST | PARTIAL | Stripe SetupIntent usage exists, but provider/dashboard and operational consent evidence were not inspected. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence |
| PAY-009 | 3 | Payments | MUST | PARTIAL | Admin refund record creation is local and does not call Stripe; refund lifecycle and provider sync are incomplete. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence |
| PAY-010 | 3 | Payments | MUST | PARTIAL | Credit ledgers exist, but current non-legacy credit concurrency tests were not found. | repository remediation later; runtime verification; deployment evidence; current-test evidence; recovery/exercise evidence |
| PAY-011 | 3 | Payments | MUST | PARTIAL | Admin money gates are broad active admin, not action-specific financial permissions. | repository remediation later; runtime verification; operational-process evidence |
| PAY-012 | 3 | Payments | MUST | FAIL | No scheduled or on-demand Stripe/local dispute, charge, refund, payment, credit, or reconciliation processor evidence. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; operational-process evidence; current-test evidence; recovery/exercise evidence |
| PAY-013 | 3 | Payments | MUST | PARTIAL | Stripe SDK is installed, but API-version pinning, webhook-event inventory, mode separation, dashboard event config, and sandbox evidence are incomplete. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence; current-test evidence |
| STO-001 | 3 | Storage and uploads | MUST | EXTERNAL EVIDENCE REQUIRED | Production bucket ownership, token scope, CORS, public access, rotation, environment separation, and human access require Cloudflare/provider evidence. | provider-dashboard evidence; operational-process evidence |
| STO-002 | 3 | Storage and uploads | MUST | PARTIAL | Object-key design avoids direct personal data but does not fully establish privacy, scope, or provider access behavior. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence |
| STO-003 | 3 | Storage and uploads | MUST | PARTIAL | Signed URLs can be reused until expiry; no revocation, runtime log proof, provider CORS/header proof, or expiry-range validation. | repository remediation later; runtime verification; provider-dashboard evidence |
| STO-004 | 3 | Storage and uploads | MUST | PARTIAL | Venue upload confirmation exists, but game image URL import lacks upload confirmation and equivalent object verification. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence |
| STO-005 | 3 | Storage and uploads | MUST | PARTIAL | No image decode, magic-byte validation, dimension/pixel checks, decompression protection, EXIF stripping, animation policy, or malformed-image parser. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence; current-test evidence |
| STO-007 | 3 | Storage and uploads | MUST | PARTIAL | Public/private classification is implicit; authorization, cache, deleted-owner, and signed-URL behavior remain incomplete. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence |
| STO-008 | 3 | Storage and uploads | MUST | FAIL | No R2 object reconciliation, orphan detection, lifecycle cleanup, safe object deletion, or storage divergence processor evidence. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence; current-test evidence |
| JOB-M01 | 3 | Background jobs | MUST | FAIL | No durable queue or worker runner for financial, webhook, notice, image, deletion, or reconciliation work. | repository remediation later; provider-dashboard evidence; deployment evidence; operational-process evidence; current-test evidence |
| JOB-M02 | 3 | Background jobs | MUST | FAIL | No general job identity, version, payload, priority, availability, attempts, lease, correlation, normalized error, or result-reference schema. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence |
| JOB-M03 | 3 | Background jobs | MUST | FAIL | No atomic job claim, lease, heartbeat, visibility timeout, crash recovery, fairness, duplicate-execution control, or expired-lease recovery. | repository remediation later; runtime verification; deployment evidence; recovery/exercise evidence |
| JOB-M04 | 3 | Background jobs | MUST | FAIL | No at-least-once handler framework, versioned handler contract, resume marker, completed-step tracking, replay path, or duplicate side-effect framework. | repository remediation later; runtime verification |
| JOB-M05 | 3 | Background jobs | MUST | FAIL | No queued retry classification, bounded backoff, jitter, Retry-After handling, timeout-to-reconciliation handoff, or durable job retry policy. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence |
| JOB-M07 | 3 | Background jobs | MUST | FAIL | No job timeout, cancellation, graceful shutdown, lease release, singleton scheduling, duplicate-safe scheduling, or rolling worker-version compatibility. | repository remediation later; runtime verification; deployment evidence; operational-process evidence |
| JOB-M08 | 3 | Background jobs | MUST | FAIL | No worker backlog, age, throughput, attempts, failures, dead letters, active worker, expired-lease, version, impact metrics, dashboards, alerts, or repair runbooks. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; operational-process evidence; current-test evidence |
| FE-M01 | 4 | Frontend | MUST | PARTIAL | No explicit Vite mode, browser target, base path, source-map setting, artifact retention, release identifier, or deployed artifact identity. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; operational-process evidence; current-test evidence |
| FE-M02 | 4 | Frontend | MUST | PARTIAL | No public frontend variable allowlist, bundle/source-map scan, environment/provider mismatch evidence, and localhost fallback remains source-visible. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence |
| FE-M04 | 4 | Frontend | MUST | PARTIAL | No central token, request ID, timeout, credentials mode, cache mode, retry matrix, or cancellation policy. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence |
| FE-M05 | 4 | Frontend | MUST | PARTIAL | No global identity-scoped cache policy; user-switch, logout, role-change, suspension, and deletion runtime behavior are unverified. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence; current-test evidence |
| FE-M06 | 4 | Frontend | MUST | PARTIAL | No catch-all route and no browser proof for deleted, suspended, stale-admin, direct refresh, hidden controls, or unknown paths. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence |
| FE-M08 | 4 | Frontend | MUST | PARTIAL | React escapes text, but unsafe URL schemes, CSP, Trusted Types, sanitizer policy, and stored-media runtime evidence are incomplete. | repository remediation later; runtime verification; deployment evidence; operational-process evidence; current-test evidence |
| FE-M10 | 4 | Frontend | MUST | PARTIAL | Firebase persistence is not explicit; browser cache, history, logout cleanup, signed URL, and client-secret exposure are unverified. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; current-test evidence |
| TST-004 | 4 | Testing and CI | MUST | PARTIAL | Test project names exist, but mocked browser, full-stack browser, provider integration, sandbox, emulator, and production-smoke separation are incomplete. | runtime verification; provider-dashboard evidence; current-test evidence |
| TST-005 | 4 | Testing and CI | MUST | PARTIAL | Current tests miss broad email verification, stale role, admin privilege removal, object/function/field authorization, mass assignment, and frontend guard coverage. | repository remediation later; runtime verification; operational-process evidence; current-test evidence |
| TST-006 | 4 | Testing and CI | MUST | FAIL | No current non-legacy direct tests for critical Stripe payment, webhook, refund, credit, timeout, partial-failure, reconciliation, or sandbox scenarios. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence; current-test evidence |
| TST-007 | 4 | Testing and CI | MUST | FAIL | No current non-legacy direct tests for critical upload authorization, validation, signed URL, confirmation replay, processing failure, missing/orphan/deleted object, cache, or R2 sandbox scenarios. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence; current-test evidence |
| TST-008 | 4 | Testing and CI | MUST | FAIL | No deterministic current concurrency tests with simultaneous sessions, barriers, winner/loser assertions, cleanup, and reproducible DB behavior. | repository remediation later; runtime verification; current-test evidence |
| TST-009 | 4 | Testing and CI | MUST | PARTIAL | CI intent covers empty-database upgrade only, not production-like schemas, drift, interruption, old/new overlap, rollback, or forward-fix. | repository remediation later; runtime verification; operational-process evidence; current-test evidence; recovery/exercise evidence |
| TST-012 | 4 | Testing and CI | MUST | PARTIAL | Dependency locks and CI exist, but npm and pip versions are inherited and clean reviewed revision execution was not verified. | repository remediation later; runtime verification; current-test evidence |
| TST-013 | 4 | Testing and CI | MUST | PARTIAL | CI lacks many gates: frontend unit, Playwright, format, type check, secret scan, dependency review, vulnerability scan, provider tests, concurrency tests, migration drift, backend artifact, container build, and artifact upload. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; current-test evidence; recovery/exercise evidence |
| TST-014 | 4 | Testing and CI | MUST | EXTERNAL EVIDENCE REQUIRED | GitHub branch protection, rulesets, required checks, reviews, bypass, fork policy, workflow ownership, and aggregator status require external evidence. | repository remediation later; provider-dashboard evidence; deployment evidence; operational-process evidence |
| TST-015 | 4 | Testing and CI | MUST | PARTIAL | Workflow permissions are limited, but third-party actions are tag-pinned rather than full SHA-pinned, and OIDC/environments were not proven. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; operational-process evidence |
| TST-016 | 4 | Testing and CI | MUST | PARTIAL | No dependency review, vulnerability scanning, source/bundle/container scan, SBOM, suppression ownership, provenance, secret-history scan, or revocation process. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; operational-process evidence; current-test evidence |
| OPS-001 | 5 | Operations | MUST | PARTIAL | Frontend and API are described, but workers and scheduler are not deployed as explicit responsibilities. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; operational-process evidence |
| OPS-002 | 5 | Operations | MUST | FAIL | No trusted runtime image, separated build/runtime stage, artifact exclusion, image scan, rebuild evidence, or platform-native runtime strategy. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; operational-process evidence |
| OPS-003 | 5 | Operations | MUST | FAIL | No container or platform-runtime hardening evidence. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; operational-process evidence; current-test evidence |
| OPS-004 | 5 | Operations | MUST | PARTIAL | No health-gated rolling release proof, immutable artifact evidence, rollback/forward-fix plan, old/new compatibility evidence, or release rehearsal. | repository remediation later; runtime verification; deployment evidence; operational-process evidence; current-test evidence; recovery/exercise evidence |
| OPS-005 | 5 | Operations | MUST | EXTERNAL EVIDENCE REQUIRED | Provider control-plane users, MFA, least privilege, recovery ownership, and offboarding are external. | provider-dashboard evidence; deployment evidence; operational-process evidence; recovery/exercise evidence |
| OPS-006 | 5 | Operations | MUST | PARTIAL | Repo hygiene and env loading exist, but managed secret store, injection, access control, rotation, revocation, and provider-side evidence are missing. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; operational-process evidence |
| OPS-007 | 5 | Operations | MUST | FAIL | No secret inventory with owner, scope, dependent systems, storage, rotation/revocation, emergency response, safe overlap, or short-lived identity decision. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence; current-test evidence |
| OPS-008 | 5 | Operations | MUST | FAIL | No centralized structured frontend, API, worker, database, provider, or edge logs with context, access restriction, redaction, loss detection, or retention. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; operational-process evidence |
| OPS-009 | 5 | Operations | MUST | FAIL | No operational metrics for API, DB, workers, payments, uploads, auth, deployments, backups, or provider quotas. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; operational-process evidence; recovery/exercise evidence |
| OPS-011 | 5 | Operations | MUST | FAIL | No symptom-based dashboards, user/financial/data alerts, threshold basis, alert-delivery evidence, or maintenance-suppression controls. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence |
| OPS-014 | 5 | Operations | MUST | FAIL | No incident-response process with severity, roles, containment, evidence preservation, recovery, reconciliation, communication, review, owners, or tracked actions. | repository remediation later; operational-process evidence; current-test evidence; recovery/exercise evidence |
| OPS-015 | 5 | Operations | MUST | FAIL | No runbooks for API/DB outage, connection exhaustion, failed release/migration, worker backlog, Stripe mismatch, R2 failure, Firebase outage, secret compromise, certificate expiry, backup failure, or restore. | repository remediation later; runtime verification; provider-dashboard evidence; deployment evidence; operational-process evidence; current-test evidence; recovery/exercise evidence |
| OPS-017 | 5 | Operations | MUST | EXTERNAL EVIDENCE REQUIRED | PostgreSQL backup enablement, encryption, access restriction, monitoring, retention, and credentials are provider/runtime evidence. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence; recovery/exercise evidence |
| OPS-018 | 5 | Operations | MUST DECIDE | NEEDS DECISION | No RPO/RTO selection or verification for backup/WAL window, versions, roles, extensions, configuration, or restore dependencies. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence; owner decision; recovery/exercise evidence |
| OPS-019 | 5 | Operations | MUST | FAIL | No isolated restore evidence covering decryption, integrity, app startup, identity mapping, Stripe/R2 references, jobs, or deletion tombstones. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence; current-test evidence; recovery/exercise evidence |
| OPS-023 | 5 | Operations | MUST | PARTIAL | Deletion exists, but access, correction, export, durable retry, R2, logs, backups, restore-time reapplication, and legal approval evidence are incomplete. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence; recovery/exercise evidence |
| OPS-024 | 5 | Operations | MUST | PARTIAL | Synthetic/test isolation exists, but production-data handling, minimization, anonymization, dump, provider export, access, backup-data, and retention evidence are incomplete. | repository remediation later; runtime verification; provider-dashboard evidence; operational-process evidence; current-test evidence; recovery/exercise evidence |
| OPS-025 | 5 | Operations | MUST | EXTERNAL EVIDENCE REQUIRED | Hosting, Firebase/Google Cloud, Stripe, Cloudflare/R2, PostgreSQL, DNS, repository, monitoring, and backup dashboard verification are external. | repository remediation later; provider-dashboard evidence; deployment evidence; operational-process evidence; recovery/exercise evidence |

Exact P0 unresolved total: 117. This reconciles to the executive summary: 77 PARTIAL plus 29 FAIL plus 3 NEEDS DECISION plus 8 EXTERNAL EVIDENCE REQUIRED equals 117.
## 6. P0 confirmed-failure index

| ID | Part | Domain | Locked failure summary | Main dependency or affected outcome |
|---|---|---|---|---|
| API-M03 | 1 | API and HTTP | No backend process-supervision configuration for worker count, concurrency, keep-alive, recycling, shutdown, or instance count. | HTTP production runtime safety |
| API-M04 | 1 | API and HTTP | No trusted-proxy or forwarded-header normalization configuration. | Edge and origin request integrity |
| API-M10 | 1 | API and HTTP | No production timeout budget for server, DB, provider, proxy, body-read, cancellation, keep-alive, or graceful shutdown behavior. | Request resource exhaustion and cancellation safety |
| API-M15 | 1 | API and HTTP | No production access-log, request-correlation, structured logging, centralized redaction, or safe logging policy. | Observability and sensitive-log control |
| IAM-008 | 1 | Identity and access | No enforced recent-authentication, step-up, MFA, or compensating-control policy. | High-risk account and admin action protection |
| IAM-014 | 1 | Identity and access | Ordinary users can write email_verified_at. | Field-level authorization |
| ADM-011 | 2 | Audit and moderation | No durable scanner timeout, outage, partial-result, queue-failure, evidence-write-failure, retry, backlog, or exhausted-state model. | Moderation failure handling |
| ADM-015 | 2 | Audit and moderation | Private chat bodies are exposed by default without excerpt-first, controlled-unmask, or read-audit pattern. | Sensitive admin-data exposure |
| PAY-012 | 3 | Payments | No scheduled or on-demand Stripe/local reconciliation processor evidence. | Financial reconciliation |
| STO-008 | 3 | Storage and uploads | No R2 object reconciliation, orphan detection, lifecycle cleanup, safe object deletion, or storage divergence processor evidence. | Storage metadata consistency |
| JOB-M01 | 3 | Background jobs | No durable queue or worker runner. | Durable background work |
| JOB-M02 | 3 | Background jobs | No general job schema for identity, attempts, lease, correlation, errors, or result references. | Durable job state |
| JOB-M03 | 3 | Background jobs | No atomic claim, lease, heartbeat, visibility timeout, crash recovery, fairness, or duplicate-execution control. | Worker concurrency and crash safety |
| JOB-M04 | 3 | Background jobs | No at-least-once handler framework, resume marker, replay path, or duplicate side-effect framework. | Idempotent durable handlers |
| JOB-M05 | 3 | Background jobs | No queued retry classification, backoff, jitter, Retry-After handling, or timeout-to-reconciliation handoff. | Failure retry safety |
| JOB-M07 | 3 | Background jobs | No job timeout, cancellation, graceful shutdown, lease release, singleton scheduling, or rolling worker compatibility. | Worker deployment safety |
| JOB-M08 | 3 | Background jobs | No worker backlog metrics, alerts, dashboards, impact metrics, or repair runbooks. | Worker observability |
| TST-006 | 4 | Testing and CI | No current non-legacy direct tests for critical Stripe payment and reconciliation scenarios. | Payment assurance |
| TST-007 | 4 | Testing and CI | No current non-legacy direct tests for critical upload, signed URL, object, cache, or R2 scenarios. | Upload and storage assurance |
| TST-008 | 4 | Testing and CI | No deterministic current concurrency tests. | Concurrency assurance |
| OPS-002 | 5 | Operations | No trusted runtime image or equivalent platform-native runtime strategy. | Runtime supply-chain evidence |
| OPS-003 | 5 | Operations | No container or platform-runtime hardening evidence. | Runtime hardening |
| OPS-007 | 5 | Operations | No secret inventory with ownership, scope, rotation, revocation, emergency response, or identity decision. | Secret operations |
| OPS-008 | 5 | Operations | No centralized structured logs with context, restricted access, redaction, loss detection, or retention. | Operational logging |
| OPS-009 | 5 | Operations | No operational metrics for critical API, DB, worker, payment, upload, auth, deployment, backup, or provider outcomes. | Metrics and observability |
| OPS-011 | 5 | Operations | No symptom-based dashboards or alerts. | Alerting |
| OPS-014 | 5 | Operations | No incident-response process. | Incident response |
| OPS-015 | 5 | Operations | No operational runbooks for required outage, migration, worker, provider, secret, certificate, backup, or restore scenarios. | Runbooks |
| OPS-019 | 5 | Operations | No isolated restore evidence. | Recovery confidence |

## 7. Owner-decision register

| ID | Part | Domain | Class | Final status | Decision required | Current locked evidence | Suggested owner role | Evidence required after decision |
|---|---|---|---|---|---|---|---|---|
| API-M08 | 1 | API and HTTP | MUST DECIDE | NEEDS DECISION | Assign security-header ownership between app and edge. | CORS middleware and frontend rewrite exist; no security-header policy. | Platform or security owner | Approved ownership decision plus deployed header evidence. |
| API-M18 | 1 | API and HTTP | MUST DECIDE | NEEDS DECISION | Decide OpenAPI/docs exposure, inventory, versioning, compatibility, and deprecation policy. | Docs exposure is env-driven but default enabled; no complete inventory or policy. | API owner | Approved API docs/version policy plus runtime exposure evidence. |
| IAM-003 | 1 | Identity and access | MUST DECIDE | NEEDS DECISION | Decide Firebase browser persistence and retry/replay behavior. | Firebase auth initializes without explicit persistence; retry policy is limited. | Auth and frontend owner | Approved persistence/retry policy plus browser runtime evidence. |
| IAM-006 | 1 | Identity and access | MUST DECIDE | NEEDS DECISION | Decide source-of-truth matrix for identity, profile, role, account state, ownership, and permissions. | Docs and code split Firebase and app profile fields, but sync policy is incomplete. | Auth and data owner | Approved field ownership and sync-conflict evidence. |
| IAM-007 | 1 | Identity and access | MUST DECIDE | FAIL | Decide verified-email policy and administrator verified-identifier requirement. | Firebase token can set verification, but ordinary user profile update can also write email_verified_at. | Auth and security owner | Approved policy plus denial tests for user-controlled verifier fields. |
| IAM-010 | 1 | Identity and access | CONDITIONAL | NEEDS DECISION | Decide whether Firebase App Check applies. | No App Check implementation or documented exclusion. | Security owner | Applicability decision and, if selected, provider/runtime evidence. |
| ADM-008 | 2 | Audit and moderation | MUST DECIDE | NEEDS DECISION | Decide audit review, alerting, retention, archive, deletion, legal hold, and export handling. | Durable audit-like tables exist, but lifecycle policy is missing. | Compliance or operations owner | Approved audit lifecycle policy and operational records. |
| ADM-014 | 2 | Audit and moderation | MUST DECIDE | NEEDS DECISION | Decide enforcement notice timing, suppression, appeal, and safe-content rules. | Multiple notice paths exist, but no complete notice policy. | Trust and safety, product, or legal owner | Approved notice policy plus runtime notice evidence. |
| DB-002 | 2 | Database | MUST DECIDE | NEEDS DECISION | Decide deployment-wide DB connection budget. | Engine uses implicit pool behavior; deployment counts and provider limits are not known. | Backend platform or database owner | Budget document plus provider/deployment/runtime evidence. |
| DB-011 | 2 | Database | MUST DECIDE | NEEDS DECISION | Decide per-table lifecycle, deletion, anonymization, retention, restoration, and backup-retention policy. | Account deletion behavior exists, but no formal lifecycle policy. | Privacy and data owner | Approved lifecycle matrix plus enforcement evidence. |
| PAY-007 | 3 | Payments | MUST DECIDE | NEEDS DECISION | Decide canonical financial state mapping. | Payment, booking, refund, credit, and money-issue states exist but cross-object policy is unresolved. | Payments and finance owner | Approved state map plus tests/runtime observations. |
| STO-006 | 3 | Storage and uploads | MUST DECIDE | NEEDS DECISION | Decide image sanitization, re-encoding, derivative, metadata, and processing requirements. | Upload path exists, but no processing pipeline. | Storage and security owner | Approved image-processing policy plus runtime evidence if selected. |
| STO-009 | 3 | Storage and uploads | MUST DECIDE | NEEDS DECISION | Decide deletion, lifecycle, retention, recovery, monitoring, and R2 controls. | Soft-delete metadata exists; object deletion and lifecycle evidence are missing. | Storage and operations owner | Approved lifecycle/recovery policy plus provider evidence. |
| FE-M09 | 4 | Frontend | MUST DECIDE | NEEDS DECISION | Decide third-party browser-code inventory, data-sharing, CSP/SRI, and provider-failure posture. | Dependencies are listed and locked; no approved third-party policy. | Frontend security and privacy owner | Approved inventory/policy plus bundle/provider evidence. |
| FE-M12 | 4 | Frontend | MUST DECIDE | NEEDS DECISION | Decide WCAG target and accessibility verification scope. | Some accessible patterns exist; no approved target or audit evidence. | Product/design accessibility owner | WCAG target plus automated/manual accessibility evidence. |
| FE-M13 | 4 | Frontend | MUST DECIDE | NEEDS DECISION | Decide browser support, performance budgets, source-map policy, and telemetry/performance measurement. | One Chromium Playwright project; no browser matrix or performance policy. | Frontend platform owner | Approved browser/performance policy plus build/browser evidence. |
| TST-011 | 4 | Testing and CI | MUST DECIDE | NEEDS DECISION | Decide retry, flake, artifact retention, and risk-based coverage policy. | CI retries exist; no owner-approved flaky-test or artifact policy. | QA or engineering owner | Approved test policy plus CI artifact evidence. |
| TST-017 | 4 | Testing and CI | MUST DECIDE | NEEDS DECISION | Decide artifact identity, SBOM, provenance, signing, and release-evidence policy. | Lockfiles and CI jobs exist; no artifact registry, signing, provenance, or deployment linkage. | Release and supply-chain owner | Approved release-evidence policy plus artifact records. |
| GOV-004 | 5 | Governance | MUST DECIDE | NEEDS DECISION | Assign named production owners across core systems and provider accounts. | Code/test ownership notes exist, but no production owner matrix. | Engineering leadership | Owner matrix plus provider-access records. |
| GOV-006 | 5 | Governance | MUST DECIDE | NEEDS DECISION | Decide documented bases for limits, thresholds, pools, retries, retention, RPO, RTO, and alerts. | Some local limits exist; no documented basis or boundary-test evidence. | Engineering, product, and platform owners | Approved limit basis plus boundary-test evidence. |
| OPS-010 | 5 | Operations | MUST DECIDE | NEEDS DECISION | Decide telemetry label bounds, privacy review, and correlation/tracing posture. | Provider IDs and audit IDs exist; no telemetry policy. | Observability and privacy owner | Approved telemetry policy plus dashboard/sample evidence. |
| OPS-012 | 5 | Operations | MUST DECIDE | NEEDS DECISION | Decide service indicators, objectives, launch thresholds, and error-budget posture. | No SLI/SLO/SLA or objective record found. | Operations and business owner | Approved objectives plus metric evidence. |
| OPS-016 | 5 | Operations | MUST DECIDE | NEEDS DECISION | Decide capacity and cost model across API, DB, workers, providers, logs, CI, and backups. | Fragmented limits exist; no capacity, load, quota, or cost model. | Platform and finance owner | Capacity model plus load/provider evidence. |
| OPS-018 | 5 | Operations | MUST DECIDE | NEEDS DECISION | Decide RPO, RTO, PITR, backup/WAL window, and restore dependencies. | No RPO/RTO decision or verification evidence. | Business, operations, and database owner | Approved RPO/RTO plus backup/PITR/restore evidence. |
| OPS-020 | 5 | Operations | MUST DECIDE | NEEDS DECISION | Decide R2 loss tolerance and recovery protection. | R2 config and metadata exist; no recovery classification or provider settings evidence. | Storage and operations owner | Approved classification plus R2 recovery evidence. |
| OPS-021 | 5 | Operations | MUST DECIDE | NEEDS DECISION | Decide tabletop and technical recovery exercise cadence and scope. | No recovery exercise evidence. | Incident-response owner | Exercise records and outcomes. |
| OPS-022 | 5 | Operations | MUST DECIDE | NEEDS DECISION | Decide data-purpose and retention schedules. | Account anonymization and policy versioning exist; no approved retention schedule. | Privacy/legal/data owner | Retention schedule plus runtime/provider enforcement evidence. |

Register entries: 27 total. MUST DECIDE controls: 26. Additional decision-blocked controls: 1, IAM-010.
## 8. Runtime and failure-verification register

| Related control IDs | Scenario | Locked static conclusion | Why static evidence is insufficient | Required environment | Safe evidence to collect |
|---|---|---|---|---|---|
| API-M04, API-M05, API-M06, API-M07, API-M08, API-M16, OPS-005, OPS-025 | Proxy, forwarded-header, host, HTTPS, HSTS, CORS, and cache behavior | Repository evidence is partial or external; trusted-proxy, host, HTTPS, HSTS, and complete cache policy are not proven. | Edge/provider behavior cannot be inferred from app source. | Staging or production-equivalent edge plus API | Redacted request/response samples, header captures, provider settings screenshots without secrets. |
| API-M09, API-M10, API-M11, DB-002, DB-008, GOV-006, OPS-016 | Request limits, timeouts, rate limiting, pool limits, and load boundaries | Local limits exist in pockets; production budgets and abuse controls are incomplete. | Static source cannot prove effective layered limits under load or multi-instance conditions. | Staging with production-like routing and safe synthetic load | Boundary-test results, timeout observations, rate-limit responses, pool metrics. |
| API-M12, API-M15, ADM-006, OPS-008, OPS-010 | Error handling, request correlation, structured logging, and redaction | No global stable error contract or production correlation system. | Logs and unexpected error behavior require runtime observation. | Staging API with sanitized log access | Error-response samples, redacted log excerpts, correlation propagation examples. |
| IAM-001, IAM-004, IAM-006, IAM-007, IAM-008, IAM-009, IAM-010, IAM-011 | Firebase token revocation, disabled users, email verification, persistence, App Check, recent auth, and account state | Some backend checks exist, but provider/runtime behavior and policies are incomplete. | Firebase project configuration and token lifecycle cannot be proven statically. | Firebase test project plus staging backend | Redacted token test matrix, provider settings screenshots, account-state transition observations. |
| IAM-012, IAM-013, IAM-014, IAM-015, IAM-016, IAM-017, ADM-007, ADM-013, ADM-015, TST-005 | Object, relationship, function, field, list, and admin authorization | Representative server checks exist; one field-level gap is confirmed; tests are incomplete. | Static review is not exhaustive and cannot prove IDOR or stale-role behavior. | Staging API with synthetic users and roles | Negative authorization matrix, cross-user substitution results, stale-role and field-update samples. |
| DB-004, DB-005, DB-006, DB-007, DB-008, DB-017, DB-018, TST-008 | Transactions, concurrency, lock ordering, retries, and unknown outcomes | Important locks and constraints exist, but retries, isolation, unknown commits, and concurrency tests are incomplete. | Race behavior requires controlled concurrent execution. | PostgreSQL integration or staging database with synthetic data | Deterministic race results, deadlock/timeout observations, transaction logs with sensitive values removed. |
| PAY-001, PAY-002, PAY-003, PAY-004, PAY-005, PAY-006, PAY-007, PAY-008, PAY-009, PAY-010, PAY-011, PAY-012, PAY-013, TST-006 | Stripe checkout, webhooks, refunds, credits, unknown outcomes, and reconciliation | Payment source code exists, but reconciliation and provider-sandbox verification are incomplete. | Stripe dashboard, webhook ordering, provider failures, and sandbox behavior are external/runtime. | Stripe test mode plus staging backend | Webhook delivery records, idempotency outcomes, refund/credit cases, reconciliation samples without secrets. |
| STO-001, STO-002, STO-003, STO-004, STO-005, STO-006, STO-007, STO-008, STO-009, TST-007 | R2 signed URLs, upload validation, cleanup, lifecycle, and reconciliation | Upload metadata and signing exist; image validation, object reconciliation, and provider controls are incomplete. | R2 bucket policy, CORS, object state, and signed URL behavior are external/runtime. | Cloudflare R2 test bucket plus staging API | Redacted bucket settings, signed URL tests, object existence checks, orphan/missing-object reconciliation samples. |
| JOB-M01, JOB-M02, JOB-M03, JOB-M04, JOB-M05, JOB-M06, JOB-M07, JOB-M08, ADM-011, ADM-016, OPS-001 | Durable job claim, retry, crash, replay, monitoring, and repair | No general durable job foundation exists. | Static source cannot show worker crash/replay behavior where no worker framework exists. | Future staging worker/queue environment | Job state samples, claim/retry/crash tests, backlog metrics, repair-run evidence. |
| FE-M01, FE-M02, FE-M03, FE-M04, FE-M05, FE-M06, FE-M07, FE-M08, FE-M10, FE-M11, FE-M12, FE-M13, TST-003 | Frontend identity changes, cache, persistence, routes, accessibility, performance, and browser behavior | Source patterns exist, but browser/runtime evidence is incomplete. | Browser state, cache, focus, route, accessibility, and performance behavior need execution. | Production build served in staging plus supported browser matrix | Browser test results, accessibility reports, performance measurements, source-map and bundle scans. |
| API-M01, API-M03, API-M17, DB-001, DB-017, DB-018, JOB-M07, OPS-001, OPS-004 | Deployment startup/shutdown, health, rolling compatibility, and migration safety | Health endpoints and migration chain exist, but deployment, rolling release, and shutdown behavior are unverified. | Process manager, release flow, and production-size migration behavior are outside static source. | Staging deployment and production-like database copy or synthetic volume | Startup/shutdown logs, health-gate evidence, migration timing, old/new compatibility checks. |
| OPS-017, OPS-018, OPS-019, OPS-020, OPS-021, OPS-023, OPS-024, OPS-025, DB-011, GOV-003 | Backups, restore, deletion-after-restore, retention, privacy, and recovery exercises | Account deletion exists partially; backup, restore, retention, and recovery evidence are absent or external. | Restore confidence requires exercise evidence and provider backup settings. | Isolated restore environment with synthetic data | Restore exercise report, backup/PITR settings, deletion-after-restore check, privacy request evidence. |

## 9. External-dashboard and operational-evidence register

| Related control IDs | Provider or process | Evidence required | Why locked repository evidence is insufficient | Safe evidence format | Secret-handling restriction |
|---|---|---|---|---|---|
| FE-M01, FE-M02, API-M06, API-M08, OPS-001, OPS-004, OPS-025 | Vercel/frontend hosting | Build mode, env bindings, redirects/headers, artifact identity, preview policy. | Repo has config/docs but no deployed provider state. | Redacted deployment settings and response headers. | Do not expose env values, tokens, or private deployment logs. |
| API-M03, API-M04, API-M06, API-M09, API-M10, API-M17, OPS-001, OPS-004 | API hosting | Runtime command, workers, instances, proxy headers, TLS redirect ownership, health gates, shutdown. | README command is not provider configuration. | Provider settings screenshots and sanitized runtime observations. | Do not expose full DATABASE_URL or runtime secrets. |
| API-M05, API-M06, OPS-005, OPS-013, OPS-025 | DNS, TLS, registrar, CDN | Domain ownership, TLS, HSTS, canonical host, CDN/proxy behavior, account protection. | DNS/CDN/registrar are not represented in repo. | Redacted DNS/TLS/CDN settings and certificate status. | Do not expose registrar recovery codes or account tokens. |
| IAM-001, IAM-004, IAM-007, IAM-008, IAM-009, IAM-010, IAM-011, OPS-005, OPS-025 | Firebase and Google Cloud | Project binding, auth providers, disabled/revoked behavior, MFA, App Check, service-account scope, key handling. | SDK calls do not prove provider configuration. | Redacted Firebase/GCP settings and test-matrix results. | Do not expose private keys, service-account JSON, tokens, or user PII. |
| PAY-001, PAY-002, PAY-003, PAY-005, PAY-006, PAY-008, PAY-009, PAY-012, PAY-013, OPS-025 | Stripe | Mode separation, webhook endpoint/events, API version, idempotency behavior, disputes/refunds, reconciliation evidence. | Provider dashboard and sandbox outcomes are external. | Stripe test-mode screenshots and redacted event IDs. | Do not expose secret keys, webhook secrets, card data, or customer PII. |
| STO-001, STO-003, STO-007, STO-008, STO-009, OPS-020, OPS-025 | Cloudflare R2 | Bucket access, CORS, lifecycle, retention, object recovery, token scope, human access. | Repo only shows SDK configuration and metadata. | Redacted bucket settings and object-state samples. | Do not expose access keys, secret keys, signed URLs, or full object lists with personal data. |
| DB-002, DB-015, OPS-017, OPS-018, OPS-019, OPS-025 | PostgreSQL hosting, backups, PITR | Roles, grants, search path, pool limits, backups, PITR, restore, retention, human access. | Runtime database/provider state is absent from repo. | Redacted role/grant summaries and restore exercise reports. | Do not expose full URLs, passwords, connection strings, dumps, or raw data. |
| TST-014, TST-015, TST-016, TST-017, OPS-005, OPS-025 | GitHub settings and branch protection | Required checks, branch rules, reviews, bypasses, workflow ownership, secret policies. | Workflow YAML cannot prove repository settings. | Ruleset screenshots and settings export with sensitive fields redacted. | Do not expose GitHub tokens, secret names tied to values, or bypass credentials. |
| OPS-006, OPS-007, IAM-011, GOV-002 | Runtime secret storage and provider access | Secret inventory, store, rotation, revocation, owners, access reviews, emergency response. | Env examples list variables but are not production evidence. | Redacted inventory and access-review records. | Never disclose secret values, private keys, tokens, or passwords. |
| API-M15, ADM-006, OPS-008, OPS-009, OPS-010, OPS-011, OPS-012 | Monitoring, logging, dashboards, alerting | Central logs, metrics, dashboards, alert delivery, labels, retention, SLOs. | Scattered source logging and health endpoints do not prove observability. | Redacted dashboard screenshots and alert-test records. | Do not expose raw logs containing tokens, private messages, payment data, or PII. |
| ADM-008, OPS-014, OPS-015, OPS-021 | Incident response and runbooks | Severity, roles, runbooks, communication, evidence preservation, exercises. | Operational process documents were not found. | Approved runbooks and exercise summaries. | Do not expose incident-sensitive details beyond sanitized summaries. |
| GOV-004, OPS-005, OPS-007 | Access reviews and offboarding | Named owners, MFA, least privilege, recovery ownership, offboarding records. | Provider control-plane access is external. | Redacted access review and ownership matrix. | Do not expose account recovery materials or personal credentials. |
| GOV-003, DB-011, OPS-022, OPS-023, OPS-024 | Retention and privacy operations | Data classification, retention schedules, deletion/export/correction workflows, production-data handling. | Placeholder/legal and code behavior do not prove approved privacy operations. | Approved policy records and redacted workflow evidence. | Do not expose user data, exports, backups, or unredacted deletion records. |
| OPS-017, OPS-018, OPS-019, OPS-020, OPS-021, OPS-023 | Restore and recovery exercises | Backup success, PITR, restore integrity, deletion-after-restore, R2 recovery, disaster exercises. | Backup success is unproven without restore exercise evidence. | Isolated restore report and recovery-exercise summary. | Do not expose database dumps, keys, full user records, or raw provider exports. |

## 10. Cross-domain dependency synthesis

| Dependency cluster | Related control IDs | Domains involved | Locked finding pattern | Why controls depend on one another | Evidence gate before closure |
|---|---|---|---|---|---|
| Production configuration and deployment foundation | GOV-001, GOV-002, API-M02, API-M03, API-M04, API-M05, API-M06, API-M17, OPS-001, OPS-004, OPS-025 | Governance, API and HTTP, Operations | Partial or failing deployment evidence with provider gaps. | Runtime safety depends on deployment topology, env isolation, proxy/TLS behavior, and health gates. | Deployment and provider-dashboard evidence plus runtime observations. |
| Identity, account state, and authorization | IAM-001, IAM-004, IAM-006, IAM-007, IAM-008, IAM-012, IAM-013, IAM-014, IAM-015, IAM-016, IAM-017, TST-005 | Identity and access, Testing and CI | Representative checks exist, one field-level FAIL, broad missing runtime tests. | Authorization correctness depends on Firebase state, local account state, roles, field mapping, and tests. | Owner decisions, runtime auth matrix, and current negative tests. |
| Payment authority, reconciliation, and durable work | PAY-001, PAY-002, PAY-004, PAY-005, PAY-006, PAY-007, PAY-009, PAY-010, PAY-012, JOB-M01, JOB-M02, JOB-M04, TST-006 | Payments, Background jobs, Testing and CI | Payment source exists, but reconciliation and durable background execution are missing. | Financial correctness needs idempotent requests, webhook order handling, refund/credit policy, and durable retries. | Stripe sandbox/provider evidence, durable job evidence, and current payment tests. |
| Storage lifecycle and background processing | STO-001, STO-003, STO-004, STO-005, STO-008, STO-009, JOB-M01, JOB-M03, JOB-M05, JOB-M08, TST-007, OPS-020 | Storage and uploads, Background jobs, Testing and CI, Operations | Signed upload paths exist, but processing, cleanup, lifecycle, and reconciliation are incomplete. | Storage correctness depends on provider bucket settings, object validation, metadata reconciliation, and durable cleanup jobs. | R2 dashboard evidence, upload runtime evidence, worker evidence, and current tests. |
| Database concurrency and migration safety | DB-002, DB-004, DB-005, DB-006, DB-007, DB-008, DB-015, DB-017, DB-018, TST-008, TST-009, OPS-004 | Database, Testing and CI, Operations | Schema and locks exist, but connection budgets, retries, privileges, and migration rehearsal are incomplete. | Correctness under production load depends on DB roles, transaction boundaries, concurrency tests, and deploy sequencing. | Provider DB evidence, runtime concurrency tests, migration rehearsal, and release compatibility evidence. |
| Frontend state and browser security | FE-M01, FE-M02, FE-M04, FE-M05, FE-M06, FE-M08, FE-M09, FE-M10, FE-M12, FE-M13, API-M08, API-M16 | Frontend, API and HTTP | Source patterns exist but browser, bundle, header, persistence, accessibility, and performance evidence are incomplete. | Browser safety depends on deployed headers, API cache behavior, state isolation, CSP decisions, and supported-browser proof. | Production-build browser tests, bundle scans, owner decisions, and deployed-header evidence. |
| Current testing, CI, and release evidence | TST-001, TST-002, TST-003, TST-004, TST-005, TST-006, TST-007, TST-008, TST-009, TST-012, TST-013, TST-014, TST-015, TST-016, TST-017, GOV-005 | Testing and CI, Governance | Current tests exist but are uneven; CI config is intent, not executed evidence. | Production sign-off depends on current tests, required checks, artifact identity, and repeatable audit process. | CI run records, branch protection evidence, artifact records, and expanded current tests. |
| Observability, incident response, and operational ownership | GOV-004, OPS-007, OPS-008, OPS-009, OPS-010, OPS-011, OPS-012, OPS-013, OPS-014, OPS-015, OPS-016 | Governance, Operations | Many operations controls are FAIL or NEEDS DECISION. | Incident handling depends on owners, metrics, logs, dashboards, alerts, runbooks, and capacity decisions. | Owner matrix, monitoring evidence, alert tests, runbooks, and exercises. |
| Backup, restore, privacy, and retention | GOV-003, ADM-008, DB-011, OPS-017, OPS-018, OPS-019, OPS-020, OPS-021, OPS-022, OPS-023, OPS-024, OPS-025 | Governance, Audit and moderation, Database, Operations | Code has partial deletion behavior, but backup, restore, retention, and privacy operations remain incomplete or external. | Recovery and privacy correctness require retention decisions, provider backup settings, restore tests, and deletion reapplication. | Approved policies, provider backup evidence, restore exercise, and privacy workflow evidence. |

## 11. Testing and assurance synthesis

Current non-legacy backend test evidence exists for shared authentication dependency behavior, Browse Games hidden access, My Games API contracts, My Games Need a Sub eligibility, selected booking constraints, and the backend test-compliance checker. Related controls include IAM-001, IAM-004, IAM-013, API-M13, API-M16, TST-002, and TST-005.
Current frontend unit evidence exists for selected Browse Games selectors, inbox state/model behavior, and admin platform-notice data helpers. Related controls include FE-M03, FE-M05, FE-M07, FE-M11, TST-002, and TST-003.
Current Playwright evidence is limited to configuration and one landing spec. It is not a broad full-stack browser assurance suite and is not shown as a CI gate. Related controls include FE-M12, FE-M13, TST-003, and TST-004.
Current CI configuration represents frontend npm install/lint/build intent and backend compile, Alembic upgrade-head, and pytest intent. No execution was performed in this synthesis. Related controls include FE-M01, TST-012, TST-013, DB-016, DB-018, and OPS-004.
Current PostgreSQL integration evidence includes a CI Postgres service and backend test fixtures that guard test DB naming and cleanup. It does not prove production PostgreSQL behavior, query plans, concurrency, privileges, or migration rehearsal. Related controls include DB-002, DB-003, DB-007, DB-008, DB-015, TST-002, TST-008, and TST-009.
Critical workflows with no current direct test source include Stripe payment success/failure/action/processing/reconciliation, R2 upload validation/object lifecycle, deterministic concurrency, broad admin authorization, mass assignment denial, frontend route-guard runtime behavior, provider sandbox boundaries, restore/deletion-after-restore, and worker crash/retry behavior. Related controls include IAM-014, PAY-012, STO-008, JOB-M01 through JOB-M08, TST-006, TST-007, TST-008, OPS-019, and OPS-023.
Deterministic concurrency coverage is a confirmed gap under TST-008. Migration coverage is partial under TST-009, DB-016, DB-017, and DB-018. Provider-sandbox coverage is incomplete under TST-004, TST-006, TST-007, PAY-013, STO-001, and OPS-025. Legacy tests remain historical only and do not satisfy current coverage. Outcomes that remain unverified because execution was prohibited include all runtime, CI, provider, database, deployment, backup, restore, worker, and exercise behavior.
## 12. Final 163-control manifest

| ID | Part | Domain | Class | Priority | Final status |
|---|---|---|---|---|---|
| GOV-001 | 5 | Governance | MUST | P0 | PARTIAL |
| GOV-002 | 5 | Governance | MUST | P0 | PARTIAL |
| GOV-003 | 5 | Governance | MUST | P1 | PARTIAL |
| GOV-004 | 5 | Governance | MUST DECIDE | P1 | NEEDS DECISION |
| GOV-005 | 5 | Governance | MUST | P1 | FAIL |
| GOV-006 | 5 | Governance | MUST DECIDE | P1 | NEEDS DECISION |
| GOV-007 | 5 | Governance | MUST | P1 | FAIL |
| API-M01 | 1 | API and HTTP | SHOULD | P1 | PARTIAL |
| API-M02 | 1 | API and HTTP | MUST | P0 | PARTIAL |
| API-M03 | 1 | API and HTTP | MUST | P0 | FAIL |
| API-M04 | 1 | API and HTTP | MUST | P0 | FAIL |
| API-M05 | 1 | API and HTTP | MUST | P1 | FAIL |
| API-M06 | 1 | API and HTTP | MUST | P0 | EXTERNAL EVIDENCE REQUIRED |
| API-M07 | 1 | API and HTTP | MUST | P0 | PARTIAL |
| API-M08 | 1 | API and HTTP | MUST DECIDE | P1 | NEEDS DECISION |
| API-M09 | 1 | API and HTTP | MUST | P0 | PARTIAL |
| API-M10 | 1 | API and HTTP | MUST | P0 | FAIL |
| API-M11 | 1 | API and HTTP | MUST | P0 | PARTIAL |
| API-M12 | 1 | API and HTTP | MUST | P0 | PARTIAL |
| API-M13 | 1 | API and HTTP | MUST | P1 | PARTIAL |
| API-M14 | 1 | API and HTTP | MUST | P0 | PARTIAL |
| API-M15 | 1 | API and HTTP | MUST | P0 | FAIL |
| API-M16 | 1 | API and HTTP | MUST | P0 | PARTIAL |
| API-M17 | 1 | API and HTTP | MUST | P1 | PARTIAL |
| API-M18 | 1 | API and HTTP | MUST DECIDE | P1 | NEEDS DECISION |
| API-M19 | 1 | API and HTTP | MUST | P1 | FAIL |
| IAM-001 | 1 | Identity and access | MUST | P0 | PARTIAL |
| IAM-002 | 1 | Identity and access | MUST | P0 | PARTIAL |
| IAM-003 | 1 | Identity and access | MUST DECIDE | P1 | NEEDS DECISION |
| IAM-004 | 1 | Identity and access | MUST | P0 | PARTIAL |
| IAM-005 | 1 | Identity and access | MUST | P0 | PARTIAL |
| IAM-006 | 1 | Identity and access | MUST DECIDE | P1 | NEEDS DECISION |
| IAM-007 | 1 | Identity and access | MUST DECIDE | P1 | FAIL |
| IAM-008 | 1 | Identity and access | MUST | P0 | FAIL |
| IAM-009 | 1 | Identity and access | MUST | P0 | PARTIAL |
| IAM-010 | 1 | Identity and access | CONDITIONAL | P2 | NEEDS DECISION |
| IAM-011 | 1 | Identity and access | MUST | P0 | EXTERNAL EVIDENCE REQUIRED |
| IAM-012 | 1 | Identity and access | MUST | P0 | PARTIAL |
| IAM-013 | 1 | Identity and access | MUST | P0 | PARTIAL |
| IAM-014 | 1 | Identity and access | MUST | P0 | FAIL |
| IAM-015 | 1 | Identity and access | MUST | P0 | PARTIAL |
| IAM-016 | 1 | Identity and access | MUST | P0 | PARTIAL |
| IAM-017 | 1 | Identity and access | MUST | P0 | PARTIAL |
| IAM-018 | 1 | Identity and access | MUST | P1 | PARTIAL |
| ADM-001 | 2 | Audit and moderation | MUST | P0 | PARTIAL |
| ADM-002 | 2 | Audit and moderation | MUST | P0 | PARTIAL |
| ADM-003 | 2 | Audit and moderation | MUST | P0 | PARTIAL |
| ADM-004 | 2 | Audit and moderation | MUST | P0 | PARTIAL |
| ADM-005 | 2 | Audit and moderation | MUST | P0 | PARTIAL |
| ADM-006 | 2 | Audit and moderation | MUST | P0 | PARTIAL |
| ADM-007 | 2 | Audit and moderation | MUST | P0 | PARTIAL |
| ADM-008 | 2 | Audit and moderation | MUST DECIDE | P1 | NEEDS DECISION |
| ADM-009 | 2 | Audit and moderation | MUST | P1 | PARTIAL |
| ADM-010 | 2 | Audit and moderation | MUST | P0 | PARTIAL |
| ADM-011 | 2 | Audit and moderation | MUST | P0 | FAIL |
| ADM-012 | 2 | Audit and moderation | MUST | P0 | PARTIAL |
| ADM-013 | 2 | Audit and moderation | MUST | P0 | PARTIAL |
| ADM-014 | 2 | Audit and moderation | MUST DECIDE | P1 | NEEDS DECISION |
| ADM-015 | 2 | Audit and moderation | MUST | P0 | FAIL |
| ADM-016 | 2 | Audit and moderation | MUST | P0 | PARTIAL |
| DB-001 | 2 | Database | MUST | P0 | PARTIAL |
| DB-002 | 2 | Database | MUST DECIDE | P0 | NEEDS DECISION |
| DB-003 | 2 | Database | MUST | P0 | PARTIAL |
| DB-004 | 2 | Database | MUST | P0 | PARTIAL |
| DB-005 | 2 | Database | MUST | P0 | PARTIAL |
| DB-006 | 2 | Database | MUST | P0 | PARTIAL |
| DB-007 | 2 | Database | MUST | P0 | PARTIAL |
| DB-008 | 2 | Database | MUST | P0 | PARTIAL |
| DB-009 | 2 | Database | MUST | P0 | PARTIAL |
| DB-010 | 2 | Database | MUST | P0 | PARTIAL |
| DB-011 | 2 | Database | MUST DECIDE | P1 | NEEDS DECISION |
| DB-012 | 2 | Database | MUST | P1 | PARTIAL |
| DB-013 | 2 | Database | MUST | P1 | PARTIAL |
| DB-014 | 2 | Database | MUST | P0 | PARTIAL |
| DB-015 | 2 | Database | MUST | P0 | EXTERNAL EVIDENCE REQUIRED |
| DB-016 | 2 | Database | MUST | P1 | PARTIAL |
| DB-017 | 2 | Database | MUST | P0 | PARTIAL |
| DB-018 | 2 | Database | MUST | P0 | PARTIAL |
| PAY-001 | 3 | Payments | MUST | P0 | PARTIAL |
| PAY-002 | 3 | Payments | MUST | P0 | PARTIAL |
| PAY-003 | 3 | Payments | MUST | P0 | PARTIAL |
| PAY-004 | 3 | Payments | MUST | P0 | PARTIAL |
| PAY-005 | 3 | Payments | MUST | P0 | PARTIAL |
| PAY-006 | 3 | Payments | MUST | P0 | PARTIAL |
| PAY-007 | 3 | Payments | MUST DECIDE | P0 | NEEDS DECISION |
| PAY-008 | 3 | Payments | MUST | P0 | PARTIAL |
| PAY-009 | 3 | Payments | MUST | P0 | PARTIAL |
| PAY-010 | 3 | Payments | MUST | P0 | PARTIAL |
| PAY-011 | 3 | Payments | MUST | P0 | PARTIAL |
| PAY-012 | 3 | Payments | MUST | P0 | FAIL |
| PAY-013 | 3 | Payments | MUST | P0 | PARTIAL |
| STO-001 | 3 | Storage and uploads | MUST | P0 | EXTERNAL EVIDENCE REQUIRED |
| STO-002 | 3 | Storage and uploads | MUST | P0 | PARTIAL |
| STO-003 | 3 | Storage and uploads | MUST | P0 | PARTIAL |
| STO-004 | 3 | Storage and uploads | MUST | P0 | PARTIAL |
| STO-005 | 3 | Storage and uploads | MUST | P0 | PARTIAL |
| STO-006 | 3 | Storage and uploads | MUST DECIDE | P1 | NEEDS DECISION |
| STO-007 | 3 | Storage and uploads | MUST | P0 | PARTIAL |
| STO-008 | 3 | Storage and uploads | MUST | P0 | FAIL |
| STO-009 | 3 | Storage and uploads | MUST DECIDE | P1 | NEEDS DECISION |
| JOB-M01 | 3 | Background jobs | MUST | P0 | FAIL |
| JOB-M02 | 3 | Background jobs | MUST | P0 | FAIL |
| JOB-M03 | 3 | Background jobs | MUST | P0 | FAIL |
| JOB-M04 | 3 | Background jobs | MUST | P0 | FAIL |
| JOB-M05 | 3 | Background jobs | MUST | P0 | FAIL |
| JOB-M06 | 3 | Background jobs | MUST | P1 | FAIL |
| JOB-M07 | 3 | Background jobs | MUST | P0 | FAIL |
| JOB-M08 | 3 | Background jobs | MUST | P0 | FAIL |
| FE-M01 | 4 | Frontend | MUST | P0 | PARTIAL |
| FE-M02 | 4 | Frontend | MUST | P0 | PARTIAL |
| FE-M03 | 4 | Frontend | MUST | P1 | PARTIAL |
| FE-M04 | 4 | Frontend | MUST | P0 | PARTIAL |
| FE-M05 | 4 | Frontend | MUST | P0 | PARTIAL |
| FE-M06 | 4 | Frontend | MUST | P0 | PARTIAL |
| FE-M07 | 4 | Frontend | MUST | P1 | PARTIAL |
| FE-M08 | 4 | Frontend | MUST | P0 | PARTIAL |
| FE-M09 | 4 | Frontend | MUST DECIDE | P1 | NEEDS DECISION |
| FE-M10 | 4 | Frontend | MUST | P0 | PARTIAL |
| FE-M11 | 4 | Frontend | MUST | P1 | PARTIAL |
| FE-M12 | 4 | Frontend | MUST DECIDE | P1 | NEEDS DECISION |
| FE-M13 | 4 | Frontend | MUST DECIDE | P1 | NEEDS DECISION |
| TST-001 | 4 | Testing and CI | MUST | P1 | PARTIAL |
| TST-002 | 4 | Testing and CI | MUST | P1 | PARTIAL |
| TST-003 | 4 | Testing and CI | MUST | P1 | PARTIAL |
| TST-004 | 4 | Testing and CI | MUST | P0 | PARTIAL |
| TST-005 | 4 | Testing and CI | MUST | P0 | PARTIAL |
| TST-006 | 4 | Testing and CI | MUST | P0 | FAIL |
| TST-007 | 4 | Testing and CI | MUST | P0 | FAIL |
| TST-008 | 4 | Testing and CI | MUST | P0 | FAIL |
| TST-009 | 4 | Testing and CI | MUST | P0 | PARTIAL |
| TST-010 | 4 | Testing and CI | MUST | P1 | PARTIAL |
| TST-011 | 4 | Testing and CI | MUST DECIDE | P1 | NEEDS DECISION |
| TST-012 | 4 | Testing and CI | MUST | P0 | PARTIAL |
| TST-013 | 4 | Testing and CI | MUST | P0 | PARTIAL |
| TST-014 | 4 | Testing and CI | MUST | P0 | EXTERNAL EVIDENCE REQUIRED |
| TST-015 | 4 | Testing and CI | MUST | P0 | PARTIAL |
| TST-016 | 4 | Testing and CI | MUST | P0 | PARTIAL |
| TST-017 | 4 | Testing and CI | MUST DECIDE | P1 | NEEDS DECISION |
| OPS-001 | 5 | Operations | MUST | P0 | PARTIAL |
| OPS-002 | 5 | Operations | MUST | P0 | FAIL |
| OPS-003 | 5 | Operations | MUST | P0 | FAIL |
| OPS-004 | 5 | Operations | MUST | P0 | PARTIAL |
| OPS-005 | 5 | Operations | MUST | P0 | EXTERNAL EVIDENCE REQUIRED |
| OPS-006 | 5 | Operations | MUST | P0 | PARTIAL |
| OPS-007 | 5 | Operations | MUST | P0 | FAIL |
| OPS-008 | 5 | Operations | MUST | P0 | FAIL |
| OPS-009 | 5 | Operations | MUST | P0 | FAIL |
| OPS-010 | 5 | Operations | MUST DECIDE | P1 | NEEDS DECISION |
| OPS-011 | 5 | Operations | MUST | P0 | FAIL |
| OPS-012 | 5 | Operations | MUST DECIDE | P1 | NEEDS DECISION |
| OPS-013 | 5 | Operations | MUST | P1 | FAIL |
| OPS-014 | 5 | Operations | MUST | P0 | FAIL |
| OPS-015 | 5 | Operations | MUST | P0 | FAIL |
| OPS-016 | 5 | Operations | MUST DECIDE | P1 | NEEDS DECISION |
| OPS-017 | 5 | Operations | MUST | P0 | EXTERNAL EVIDENCE REQUIRED |
| OPS-018 | 5 | Operations | MUST DECIDE | P0 | NEEDS DECISION |
| OPS-019 | 5 | Operations | MUST | P0 | FAIL |
| OPS-020 | 5 | Operations | MUST DECIDE | P1 | NEEDS DECISION |
| OPS-021 | 5 | Operations | MUST DECIDE | P1 | NEEDS DECISION |
| OPS-022 | 5 | Operations | MUST DECIDE | P1 | NEEDS DECISION |
| OPS-023 | 5 | Operations | MUST | P0 | PARTIAL |
| OPS-024 | 5 | Operations | MUST | P0 | PARTIAL |
| OPS-025 | 5 | Operations | MUST | P0 | EXTERNAL EVIDENCE REQUIRED |

## 13. Conflicts, unknowns, and limitations

This was a static-only synthesis of locked reports. No repository re-audit, test execution, build execution, migration execution, runtime inspection, provider inspection, database connection, network access, backup, restore, or exercise occurred.
The findings depend on the five finalized audit reports and current packaged input files, not on an immutable source revision. Branch names and commit hashes were not used. Provider-dashboard and operational-process evidence remains absent for many controls. Owner decisions remain open for 26 MUST DECIDE controls plus IAM-010 as an additional conditional decision-blocked control. No remediation was performed.
No synthesis ambiguity blocked reconciliation. The 163-control manifest reconciled successfully without changing locked findings.
## 14. Readiness gate statement

Production-readiness approval is not supported by the locked findings. The evidence still required spans repository remediation later, runtime verification, provider-dashboard evidence, deployment evidence, operational-process evidence, owner decisions, current-test evidence, and recovery/exercise evidence.
All unresolved P0 controls must be addressed, externally evidenced, or formally resolved before sign-off. The next separate phase is remediation planning; this Part 6 report does not include the remediation plan.
## 15. Completion statement

> Pickup Lane Part 6 consolidated synthesis completed from the five finalized static-audit reports. All 163 controls were reconciled without changing locked findings. No files were modified and no tests, builds, migrations, databases, servers, workers, containers, networks, providers, backups, restores, or exercises were run. Remediation planning remains a separate next phase.
