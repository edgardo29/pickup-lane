# Pickup Lane Production-Readiness Static Audit — Part 5

## Corrected Part 5 Summary

Read-only static correction pass covering GOV-001 through GOV-007 and OPS-001 through OPS-025. No repository files were modified, and no tests, services, providers, dashboards, builds, deployments, backups, restores, or exercises were run. Legacy tests were treated as historical only. GOV-005 is assessed as FAIL because the current repository does not maintain a repeatable, owner-governed production-readiness audit process.

## Complete Corrected Part 5 Control Table

| ID | Domain | Class | Priority | Final status | Evidence classes | Current evidence | Missing evidence or gap | Next verification |
|---|---|---|---|---|---|---|---|---|
| GOV-001 | Governance | MUST | P0 | PARTIAL | SOURCE CODE, STATIC CONFIGURATION, CI CONFIGURATION, DEPLOYMENT CONFIGURATION, PROVIDER DASHBOARD REQUIRED, RUNTIME REQUIRED, OPERATIONAL PROCESS REQUIRED | README.md:11-16 names Vercel, Render, Neon, Firebase, R2, and Stripe. backend/main.py:100-176 wires middleware, health endpoints, and routers. backend/database.py:14-31 defines database access. backend/services/r2_storage_service.py:83-130 defines R2 client setup. backend/services/stripe_service.py:56-97 defines Stripe setup. .github/workflows/ci.yml:63-145 defines CI jobs. | No authoritative architecture inventory covering workers, scheduler, monitoring, backups, DNS/CDN, regions, public and private services, or single points of failure. Search scope is detailed in GOV-001 appendix. | Later architecture inventory, topology, provider settings, and approval evidence. |
| GOV-002 | Governance | MUST | P0 | PARTIAL | SOURCE CODE, STATIC CONFIGURATION, CI CONFIGURATION, DEPLOYMENT CONFIGURATION, PROVIDER DASHBOARD REQUIRED, RUNTIME REQUIRED, OPERATIONAL PROCESS REQUIRED | README.md:18-64 lists backend and frontend deployment variables. backend/.env.example:1-23 and frontend/.env.example:1-9 provide local example variables. .github/workflows/ci.yml:93-145 uses a CI PostgreSQL service. backend/tests/conftest.py:71-95 rejects unsafe test database names. frontend/playwright.config.js:10-17 uses localhost for browser tests. | No complete environment matrix for local, automated test, browser test, provider sandbox, staging, and production across Firebase, Stripe, R2, PostgreSQL, domains, webhooks, secrets, logs, and CI credentials. | Later environment matrix and provider/runtime isolation evidence. |
| GOV-003 | Governance | MUST | P1 | PARTIAL | SOURCE CODE, DATABASE SCHEMA, STATIC CONFIGURATION, OPERATIONAL PROCESS REQUIRED, RUNTIME REQUIRED | Fragmented handling signals exist. README.md:5-7 says fake/demo data and no committed secrets. backend/models/payment_model.py:22-23 says raw card data is not stored. backend/models/user_model.py:116-154 stores profile and identity fields. backend/models/chat_message_model.py:20-193 and backend/models/sub_post_chat_message_model.py:19-182 store chat content and review state. backend/models/admin_action_model.py:11-180 stores admin audit records. frontend/src/features/legal/legalPolicies.js:40-54 is placeholder privacy text. | No formal classification and handling policy for public, internal, personal, private-message, financial, moderation, audit, authentication, or secret data across access, display, logging, caching, retention, backup, export, and deletion. | Later approved classification and handling evidence. |
| GOV-004 | Governance | MUST DECIDE | P1 | NEEDS DECISION | OWNER DECISION REQUIRED, OPERATIONAL PROCESS REQUIRED, PROVIDER DASHBOARD REQUIRED | Code and test ownership notes exist in AGENTS.md:8-13, docs/agent-notes/database.md:3-12, and backend/tests/README.md:16-18. backend/tests/compliance/contracts.py:668-681 validates backend test-contract ownership entries. | No named production owners for authentication, authorization, payments, database, storage, workers, release, secrets, monitoring, backups, incident response, privacy operations, or provider accounts. Search scope is detailed in GOV-004 appendix. | Later named-owner and provider-access evidence. |
| GOV-005 | Governance | MUST | P1 | FAIL | STATIC CONFIGURATION, OPERATIONAL PROCESS REQUIRED | backend/tests/README.md:14-18 and 111-161 define a backend test-compliance workflow, not a production-readiness audit process. Static review of README.md, AGENTS.md, docs/agent-notes, .github, backend/tests, and backend/tests/compliance found no repeatable owner-governed production-readiness audit process. | No cadence, approval, versioning, exception handling, preserved production-readiness results, reassessment triggers, or stable source-revision linkage. This one-time static audit and prior generated reports are not repository evidence. | Later repeatable audit-process records with cadence, approval, result preservation, reassessment triggers, and stable source-revision linkage. |
| GOV-006 | Governance | MUST DECIDE | P1 | NEEDS DECISION | SOURCE CODE, STATIC CONFIGURATION, OWNER DECISION REQUIRED, OPERATIONAL PROCESS REQUIRED, RUNTIME REQUIRED | Local limits exist in backend/.env.example:20-23, backend/services/r2_storage_service.py:111-114, backend/services/game_chat_service.py:48-51, and backend/services/sub_post_chat_service.py:46-50. | No documented basis and boundary-test evidence for universal request size, timeout, rate, worker count, pool size, indexes, retries, retention, RPO, RTO, or alert thresholds. Search scope is detailed in GOV-006 appendix. | Later owner basis for limits and boundary-test evidence. |
| GOV-007 | Governance | MUST | P1 | FAIL | STATIC CONFIGURATION, OPERATIONAL PROCESS REQUIRED | App-owned filename and term searches found no risk register, accepted-risk register, exception register, waiver process, owner approval, expiry, or verification record. Search scope is detailed in GOV-007 appendix. | No repository-verifiable risk acceptance or exception-management process. | Later risk and exception records with owner, justification, compensating control, expiry, and verification evidence. |
| OPS-001 | Operations | MUST | P0 | PARTIAL | SOURCE CODE, STATIC CONFIGURATION, CI CONFIGURATION, DEPLOYMENT CONFIGURATION, PROVIDER DASHBOARD REQUIRED, RUNTIME REQUIRED, OPERATIONAL PROCESS REQUIRED | README.md:11-16 identifies intended services. README.md:18-64 lists release settings and variables. frontend/vercel.json:1-8 defines SPA routing. backend/main.py:109-118 exposes root and DB-health endpoints. | Frontend and API are described, but workers and scheduler are not deployed as explicit responsibilities. No statelessness proof, scaling evidence, region evidence, durable shared-service topology, or runtime proof. | Later production topology and runtime state evidence. |
| OPS-002 | Operations | MUST | P0 | FAIL | STATIC CONFIGURATION, CI CONFIGURATION, DEPLOYMENT CONFIGURATION, PROVIDER DASHBOARD REQUIRED, OPERATIONAL PROCESS REQUIRED, RUNTIME REQUIRED | .github/workflows/ci.yml:63-145 builds frontend and backend. README.md:18-26 gives a Render backend command. App-owned deployment search found frontend/vercel.json only, with no Dockerfile, Procfile, render.yaml, fly.toml, railway config, compose file, or equivalent backend runtime artifact. | No trusted maintained runtime image, separated build/runtime stages, artifact exclusion strategy, image scan, rebuild evidence, or versioned platform-native runtime strategy. Search scope is detailed in OPS-002 appendix. | Later runtime-image or platform-native runtime evidence. |
| OPS-003 | Operations | MUST | P0 | FAIL | STATIC CONFIGURATION, DEPLOYMENT CONFIGURATION, PROVIDER DASHBOARD REQUIRED, RUNTIME REQUIRED, OPERATIONAL PROCESS REQUIRED | Deployment/runtime search inspected README.md, .github/workflows, frontend/vercel.json, frontend/package.json, frontend/playwright.config.js, backend app files, and app-owned deployment filenames. Actual hardening configuration found: none for non-root identity, capabilities, privileged mode, Docker socket, writable paths, CPU limits, memory limits, process limits, file-descriptor limits, read-only filesystem, or platform sandboxing. | No container or platform-runtime hardening evidence. Database-pool and API-docs claims are excluded from this control. Search scope is detailed in OPS-003 appendix. | Later platform hardening, limits, and sandbox evidence. |
| OPS-004 | Operations | MUST | P0 | PARTIAL | SOURCE CODE, MIGRATION, CI CONFIGURATION, DEPLOYMENT CONFIGURATION, RUNTIME REQUIRED, OPERATIONAL PROCESS REQUIRED | .github/workflows/ci.yml:63-145 defines build, migration, and test jobs. README.md:18-67 gives basic release notes. .github/workflows/ci.yml:141-145 runs alembic upgrade head and pytest. backend/main.py:109-118 exposes health endpoints. | No health-gated rolling release proof, immutable artifact evidence, tested rollback/forward-fix plans, old/new frontend/API/worker/webhook/job/schema compatibility evidence, or release rehearsal. | Later health-gated release, rollback, artifact, compatibility, and rehearsal evidence. |
| OPS-005 | Operations | MUST | P0 | EXTERNAL EVIDENCE REQUIRED | STATIC CONFIGURATION, PROVIDER DASHBOARD REQUIRED, OPERATIONAL PROCESS REQUIRED | README.md:11-16 names Vercel, Render, Neon, Firebase, R2, and Stripe. Repository and CI control plane is represented by .github/workflows/ci.yml:1-178. | Domain registrar, DNS, CDN, hosting, database, Firebase, Stripe, Cloudflare, repository, monitoring, and backup control-plane users, MFA, least privilege, recovery ownership, and offboarding are external. | Later provider account, MFA, role, recovery-owner, offboarding, and access-review evidence. |
| OPS-006 | Operations | MUST | P0 | PARTIAL | SOURCE CODE, STATIC CONFIGURATION, DEPLOYMENT CONFIGURATION, PROVIDER DASHBOARD REQUIRED, OPERATIONAL PROCESS REQUIRED, RUNTIME REQUIRED | .gitignore:10-17 ignores .env files and Firebase admin JSON patterns. README.md:5-7 warns against committed secrets. backend/.env.example:1-23 and frontend/.env.example:1-9 are placeholders. backend/firebase_admin_client.py:26-49, backend/services/stripe_service.py:56-85, and backend/services/r2_storage_service.py:83-115 read secrets from environment. | Repo hygiene and runtime env loading exist, but managed secret store, runtime injection, access controls, rotation, revocation, and provider-side secret evidence are missing. | Later secret-store, injection, access, and rotation evidence. |
| OPS-007 | Operations | MUST | P0 | FAIL | STATIC CONFIGURATION, PROVIDER DASHBOARD REQUIRED, OPERATIONAL PROCESS REQUIRED | README.md:28-64, backend/.env.example:1-23, and frontend/.env.example:1-9 list variables, but they are not an inventory. Search scope for secret inventory used README.md, AGENTS.md, docs, backend, frontend, .github, root config, excluding dependency folders and backend/tests/legacy, with terms secret inventory, secret owner, rotation, revocation, workload identity, OIDC, short-lived, secret store, password manager, Vault, Doppler, MFA, least privilege, offboarding. | No secret inventory with owner, scope, dependent systems, storage, rotation/revocation procedure, emergency response, safe overlap, or short-lived identity decision. | Later secret-inventory and rotation/revocation evidence. |
| OPS-008 | Operations | MUST | P0 | FAIL | SOURCE CODE, DATABASE SCHEMA, PROVIDER DASHBOARD REQUIRED, RUNTIME REQUIRED, OPERATIONAL PROCESS REQUIRED | Application logger usage exists in backend/services/moderation_surfacing_service.py:50 and 145-224, backend/services/game_chat_service.py:43 and 970-973, backend/services/sub_post_chat_service.py:44 and 372-375, backend/services/moderation_signal_service.py:21 and 289, and backend/services/content_moderation_finding_service.py:36 and 332. Admin audit records exist in backend/models/admin_action_model.py:11-180. | No centralized structured frontend, API, worker, database, provider, or edge logs with release, environment, request, job, or event context, restricted access, redaction, loss detection, or policy-driven retention. Search scope is detailed in OPS-008 appendix. | Later centralized log pipeline, retention, access-control, redaction, and loss-detection evidence. |
| OPS-009 | Operations | MUST | P0 | FAIL | SOURCE CODE, CI CONFIGURATION, PROVIDER DASHBOARD REQUIRED, RUNTIME REQUIRED, OPERATIONAL PROCESS REQUIRED | backend/main.py:109-118 exposes health endpoints. .github/workflows/ci.yml:63-145 defines CI jobs. backend/models/payment_event_model.py:20-91 stores Stripe webhook/event processing records. | No operational metrics for API traffic/errors/latency, database pool/query/lock/storage, worker backlog, payment/webhook/refund/reconciliation outcomes, upload/storage divergence, auth failures, release health, backup success, or provider quotas. Search scope is detailed in OPS-009 appendix. | Later metrics pipeline, dashboards, and runtime measurement evidence. |
| OPS-010 | Operations | MUST DECIDE | P1 | NEEDS DECISION | SOURCE CODE, DATABASE SCHEMA, OWNER DECISION REQUIRED, OPERATIONAL PROCESS REQUIRED, RUNTIME REQUIRED | Provider IDs and timestamps exist in backend/models/payment_model.py:120-145, backend/models/refund_model.py:140-189, and backend/models/payment_event_model.py:73-91. Admin audit IDs exist in backend/models/admin_action_model.py:84-136. | No bounded metric-label policy, telemetry attribute policy, privacy review, request/job/payment correlation standard, or tracing decision. | Later owner decision on labels/tracing and correlation evidence. |
| OPS-011 | Operations | MUST | P0 | FAIL | SOURCE CODE, STATIC CONFIGURATION, PROVIDER DASHBOARD REQUIRED, RUNTIME REQUIRED, OPERATIONAL PROCESS REQUIRED | backend/main.py:109-118 has health endpoints. Search of README.md, AGENTS.md, docs, backend, frontend, .github, and root config for dashboard, alert, monitor, SLI, SLO, metrics, pager, and on-call terms found no production dashboard or alert configuration. | No symptom-based dashboards, alerts tied to user/financial/data outcomes, threshold basis, alert delivery evidence, or maintenance-suppression controls. | Later dashboard, alert, delivery proof, maintenance-suppression, and threshold evidence. |
| OPS-012 | Operations | MUST DECIDE | P1 | NEEDS DECISION | OWNER DECISION REQUIRED, OPERATIONAL PROCESS REQUIRED, RUNTIME REQUIRED, PROVIDER DASHBOARD REQUIRED | Search of README.md, AGENTS.md, docs, backend, frontend, .github, and root config for SLI, SLO, SLA, availability, latency, correctness, reliability, worker delay, data freshness, error budget, and launch threshold found no service objective record. | No selected indicators or objectives for availability, latency, correctness, payment reliability, worker delay, or data freshness. | Later SLI, SLO, error-budget, and launch-threshold decision evidence. |
| OPS-013 | Operations | MUST | P1 | FAIL | SOURCE CODE, PROVIDER DASHBOARD REQUIRED, RUNTIME REQUIRED, OPERATIONAL PROCESS REQUIRED | Local provider-error paths exist for Stripe in backend/services/stripe_service.py:173-332, R2 in backend/services/r2_storage_service.py:145-220, Firebase in backend/firebase_admin_client.py:52-77, and Stripe webhooks in backend/routes/stripe_webhook_routes.py:13-39. | No provider-status notification evidence, internal correlation evidence, degraded behavior for Firebase, Stripe, R2, PostgreSQL, hosting, DNS, or CDN, or outage exercise. Search scope is detailed in OPS-013 appendix. | Later provider-notification, internal-correlation, degraded-behavior, and exercise evidence. |
| OPS-014 | Operations | MUST | P0 | FAIL | STATIC CONFIGURATION, OPERATIONAL PROCESS REQUIRED | Search scope used README.md, AGENTS.md, docs, backend, frontend, .github, root config, excluding dependencies and backend/tests/legacy, with terms incident, severity, SEV, on-call, oncall, pager, postmortem, post-incident, containment, evidence preservation, recovery, reconciliation, communication, tracked actions. | No incident-response process with severity, roles, containment, evidence preservation, recovery, reconciliation, communication, post-incident review, owners, or tracked actions. | Later incident-response process and exercise evidence. |
| OPS-015 | Operations | MUST | P0 | FAIL | STATIC CONFIGURATION, OPERATIONAL PROCESS REQUIRED, RUNTIME REQUIRED | README.md:18-67 has basic release notes only. Search scope used README.md, AGENTS.md, docs, backend, frontend, .github, root config, excluding dependencies and backend/tests/legacy, with terms runbook, playbook, outage, connection exhaustion, failed release, migration, worker backlog, dead letter, webhook mismatch, payment mismatch, R2 failure, credential failure, Firebase outage, secret compromise, certificate expiry, backup failure, restore. | No runbooks for API/DB outage, connection exhaustion, failed release/migration, worker backlog/dead letters, Stripe mismatch, R2 failure, Firebase outage, secret compromise, certificate expiry, backup failure, or restore. | Later runbook evidence for each listed scenario. |
| OPS-016 | Operations | MUST DECIDE | P1 | NEEDS DECISION | SOURCE CODE, STATIC CONFIGURATION, OWNER DECISION REQUIRED, PROVIDER DASHBOARD REQUIRED, OPERATIONAL PROCESS REQUIRED, RUNTIME REQUIRED | Fragmented limits appear in backend/.env.example:20-23, backend/services/r2_storage_service.py:111-114, backend/services/game_chat_service.py:48-51, backend/services/sub_post_chat_service.py:46-50, and backend/database.py:27. | No capacity or cost model across API, database connections/storage, workers, provider quotas, R2 requests/storage, logs/metrics, CI, or backups. No load evidence or alert-before-limit evidence. | Later capacity, load, quota, and cost evidence. |
| OPS-017 | Operations | MUST | P0 | EXTERNAL EVIDENCE REQUIRED | STATIC CONFIGURATION, PROVIDER DASHBOARD REQUIRED, OPERATIONAL PROCESS REQUIRED, RUNTIME REQUIRED | README.md:11-16 identifies Neon Postgres. backend/database.py:14-31 uses DATABASE_URL. Search of repo docs/config/source for backup, PITR, WAL, snapshot, retention, restore, encryption, backup credentials, and monitored completion found no repository-managed PostgreSQL backup proof. | Production PostgreSQL backup enablement, encryption, access restriction, monitoring, retention, and credentials are provider/runtime evidence outside the repo. | Later PostgreSQL backup settings, retention, success, access, and PITR evidence. |
| OPS-018 | Operations | MUST DECIDE | P0 | NEEDS DECISION | OWNER DECISION REQUIRED, PROVIDER DASHBOARD REQUIRED, OPERATIONAL PROCESS REQUIRED, RUNTIME REQUIRED, STATIC CONFIGURATION | Search of README.md, AGENTS.md, docs, backend, frontend, .github, and root config for RPO, RTO, PITR, WAL, restore window, backup window, business impact, recovery objective, and restore dependency found no decision record. | No RPO/RTO selection or verification for backup/WAL window, versions, roles, extensions, configuration, or restore dependencies. | Later RPO/RTO decision, PITR-window, version, role, extension, and dependency evidence. |
| OPS-019 | Operations | MUST | P0 | FAIL | PROVIDER DASHBOARD REQUIRED, OPERATIONAL PROCESS REQUIRED, RUNTIME REQUIRED | .github/workflows/ci.yml:141-145 runs migrations and tests, but this is not restore evidence. Search scope used README.md, AGENTS.md, docs, backend, frontend, .github, root config, excluding dependencies and backend/tests/legacy, with terms restore, backup restore, isolated restore, decryption, integrity, application startup, identity mapping, Stripe reference, R2 reference, deletion tombstone, restore validation. | No isolated restore evidence covering decryption, integrity, application startup, identity mapping, Stripe/R2 references, jobs, or deletion tombstones. | Later isolated restore proof covering integrity, startup, mappings, references, jobs, and tombstones. |
| OPS-020 | Operations | MUST DECIDE | P1 | NEEDS DECISION | SOURCE CODE, DATABASE SCHEMA, STATIC CONFIGURATION, OWNER DECISION REQUIRED, PROVIDER DASHBOARD REQUIRED, OPERATIONAL PROCESS REQUIRED, RUNTIME REQUIRED | R2 setup appears in backend/services/r2_storage_service.py:83-130. Venue-image object metadata appears in backend/models/venue_image_model.py:100-108. R2 example variables appear in backend/.env.example:14-23. | No loss-tolerance classification for R2 originals/derivatives, bucket recovery protection, lifecycle/versioning evidence, provider settings recovery, DNS recovery, monitoring recovery, infrastructure recovery, or secret recreation procedure. | Later R2 recovery, provider settings, secret recreation, DNS, and monitoring evidence. |
| OPS-021 | Operations | MUST DECIDE | P1 | NEEDS DECISION | OWNER DECISION REQUIRED, OPERATIONAL PROCESS REQUIRED, RUNTIME REQUIRED | Search scope used README.md, AGENTS.md, docs, backend, frontend, .github, root config, excluding dependencies and backend/tests/legacy, with terms tabletop, recovery exercise, disaster recovery, restore exercise, rollback exercise, secret compromise, webhook outage, worker backlog, provider outage, user-deletion failure, domain recovery, control-plane recovery. | No tabletop or technical recovery exercise evidence for restore, rollback, secret compromise, webhook outage, worker backlog, provider outage, user-deletion failure, or domain/control-plane recovery. | Later tabletop and technical recovery exercise evidence. |
| OPS-022 | Operations | MUST DECIDE | P1 | NEEDS DECISION | SOURCE CODE, DATABASE SCHEMA, STATIC CONFIGURATION, OWNER DECISION REQUIRED, PROVIDER DASHBOARD REQUIRED, OPERATIONAL PROCESS REQUIRED, RUNTIME REQUIRED | Account anonymization appears in backend/services/account_deletion_service.py:930-945. Policy-document versioning appears in backend/models/policy_document_model.py:20-94. Venue image deleted_at and object metadata appear in backend/models/venue_image_model.py:100-140. | No approved retention schedule for accounts, profiles, games, bookings, messages, notices, payments, images, moderation, audit, logs, metrics, backups, exports, or test data. | Later approved retention schedule and runtime/provider retention evidence. |
| OPS-023 | Operations | MUST | P0 | PARTIAL | SOURCE CODE, DATABASE SCHEMA, STATIC CONFIGURATION, PROVIDER DASHBOARD REQUIRED, OPERATIONAL PROCESS REQUIRED, RUNTIME REQUIRED | Self-delete route exists at backend/routes/auth_routes.py:60-66. Self-delete workflow locks users and active admins at backend/services/account_deletion_service.py:87-143, records partial failures at 145-207, detaches saved methods at 210-259, clears host assignments at 300-328, and anonymizes users at 930-945. Admin-delete preview and execution exist in backend/services/admin_user_delete_service.py:475-620, 756-840, and 904-1044. Placeholder privacy text is frontend/src/features/legal/legalPolicies.js:40-54. | Deletion exists, but no complete access, correction, export, durable retry, R2 handling, logs handling, backups handling, restore-time reapplication, or legal approval evidence. | Later privacy workflow evidence for deletion, access, correction, export, R2, logs, backups, and restore-time reapplication. |
| OPS-024 | Operations | MUST | P0 | PARTIAL | STATIC CONFIGURATION, CI CONFIGURATION, CURRENT TEST SOURCE, PROVIDER DASHBOARD REQUIRED, OPERATIONAL PROCESS REQUIRED, RUNTIME REQUIRED | README.md:5-7 says the prototype uses fake/demo data. backend/tests/README.md:60 says not to use development, staging, or production databases. backend/tests/conftest.py:71-95 rejects unsafe test DB names. backend/tests/conftest.py:102-143 truncates test tables with an advisory lock. .github/workflows/ci.yml:93-145 uses a CI PostgreSQL service and test database URL. | Synthetic/test isolation exists, but no approved production-data handling process, minimization/anonymization rules, restricted dump policy, provider export rules, production access controls, backup-data rules, or retention evidence. | Later production-data handling, minimization, anonymization, restricted dump, cleanup, retention, and access evidence. |
| OPS-025 | Operations | MUST | P0 | EXTERNAL EVIDENCE REQUIRED | STATIC CONFIGURATION, DEPLOYMENT CONFIGURATION, PROVIDER DASHBOARD REQUIRED, OPERATIONAL PROCESS REQUIRED | README.md:11-64 names providers and env settings. frontend/vercel.json:1-8 provides frontend routing. Search of app-owned repo files for provider dashboard exports, hosting settings, Firebase settings, Stripe dashboard evidence, Cloudflare/R2 settings, PostgreSQL backup settings, DNS records, repository settings, monitoring settings, and backup settings found no safe provider evidence records. | Hosting, Firebase/Google Cloud, Stripe, Cloudflare/R2, PostgreSQL, DNS, repository, monitoring, and backup dashboard verification are external. | Later provider-dashboard evidence without secret values. |

## Governance Appendices


### GOV-001 architecture/trust-boundary matrix

| Component | Repo evidence | Boundary status | Missing evidence |
|---|---|---|---|
| Frontend | README.md:11 and 47-51, frontend/vercel.json:1-8 | Public browser entry point implied | Domain, CDN, region, environment, cache, access-log, and provider settings proof |
| Backend API | README.md:12 and 18-26, backend/main.py:100-176 | Public API entry point implied | Runtime topology, region, instance count, scaling, ingress, egress, and private network proof |
| Workers | Search terms BackgroundTasks, Celery, RQ, dramatiq, APScheduler, cron, scheduler, worker, queue across backend, frontend, .github, README.md excluding legacy found no worker runtime | Required component absent | Worker responsibility and topology evidence |
| Scheduler | Status enums mention scheduled_job in status-history code, but no scheduler runtime config found | Data value only, not scheduler architecture | Scheduler ownership, trigger, runtime, and failure model |
| PostgreSQL | README.md:13, backend/database.py:14-31 | Durable database dependency | Provider project, region, backup, pool, and access evidence |
| Firebase | README.md:14, backend/firebase_admin_client.py:26-77, frontend/src/lib/firebase.js:4-15 | Authentication provider boundary | Project separation, auth settings, MFA/admin access, and provider logs |
| Stripe | README.md:16, backend/services/stripe_service.py:56-97, backend/routes/stripe_webhook_routes.py:13-39 | Payment provider and webhook boundary | Dashboard settings, webhook endpoint config, mode separation, and alert evidence |
| R2 | README.md:15, backend/services/r2_storage_service.py:83-220 | Object-storage provider boundary | Bucket settings, versioning, lifecycle, access, and recovery evidence |
| DNS/CDN | README.md names Vercel and R2 but no DNS files found | External only | Registrar, DNS records, CDN behavior, certificate, and ownership evidence |
| CI | .github/workflows/ci.yml:1-178 | GitHub Actions CI boundary | Branch protection and provider access settings evidence |
| Monitoring | Search terms logging, metrics, dashboard, alert, monitor, trace across app-owned files found no production monitoring config | Not evidenced | Monitoring topology and owner evidence |
| Backups | Search terms backup, PITR, restore, WAL, snapshot across app-owned files found no production backup config | External only | Backup provider settings and restore evidence |
| Public entry points | backend/main.py:109-118, backend/routes/stripe_webhook_routes.py:13-39, frontend/vercel.json:1-8 | Frontend, API, webhook, and static route surfaces exist | Complete public route inventory and edge controls |
| Private services | Database, Firebase Admin, Stripe, and R2 are referenced from backend source | Private dependencies implied | Network isolation and credential boundary proof |
| Regions | No region setting found in README.md, .github, backend env examples, frontend config, or provider docs | Not evidenced | Provider-region evidence |
| Single points of failure | No SPOF register or dependency risk matrix found | Not evidenced | SPOF analysis and acceptance evidence |

### GOV-002 environment-isolation matrix

| Environment | Repo evidence | Coverage | Missing evidence |
|---|---|---|---|
| Local | backend/.env.example:1-23, frontend/.env.example:1-9, README.md:28-64 | Local examples exist | No formal local isolation matrix across every provider |
| Automated backend test | .github/workflows/ci.yml:93-145, backend/tests/conftest.py:71-95 | CI test DB and unsafe-DB guard exist | No provider sandbox matrix for Firebase, Stripe, R2 |
| Browser test | frontend/playwright.config.js:10-17 | Local browser server target exists | No browser-test provider isolation proof |
| Provider sandbox | README.md:5-7 and 16 says fake/demo data and Stripe test mode | Stripe test-mode intent exists | Firebase project, R2 bucket, Neon DB, domains, and webhooks not proven isolated |
| Staging | Search of README.md, .github, backend/.env.example, frontend/.env.example, frontend config, backend config, and docs for staging found no staging matrix | Not evidenced | Staging provider and data separation evidence |
| Production | README.md:18-64 lists intended release variables | Deployment notes only | Production provider/project/bucket/database/domain/log separation evidence |
| CI credentials | .github/workflows/ci.yml:114-116 sets DATABASE_URL and PYTHONPATH | CI database URL explicit | No CI secret scope or provider credential separation evidence |
| Logs | Search terms log, logging, retention, central, provider log across app-owned files found no environment log matrix | Not evidenced | Per-environment logging isolation evidence |

### GOV-003 classification/handling matrix

| Data class | Repo evidence | Handling signals | Missing dimensions |
|---|---|---|---|
| Public | Game, venue, and image public routes exist through backend/main.py:123-176 and venue image public route backend/routes/venue_image_routes.py:29-34 | Public read surface exists | Classification, caching, logging, retention, and backup rules |
| Internal | Admin actions in backend/models/admin_action_model.py:11-180 and support flags in backend/models/support_flag_model.py:11-125 | Internal admin/support records exist | Formal access/display/logging/export/deletion rules |
| Personal | User fields in backend/models/user_model.py:116-154 | Identity and profile data modeled | Classification, export, backup, log handling, and retention schedule |
| Private-message | Game chat model backend/models/chat_message_model.py:20-193 and Need a Sub chat model backend/models/sub_post_chat_message_model.py:19-182 | Messages have visibility and review state | Private-message classification, export, backup, retention, and deletion rules |
| Financial | Payment model backend/models/payment_model.py:22-145, refund model backend/models/refund_model.py:20-189, payment event model backend/models/payment_event_model.py:20-91 | Stripe references and webhook records exist, raw card storage avoided | Financial data display, retention, logging, backup, and export policy |
| Moderation | Scanner fields backend/services/content_moderation_scanner_service.py:10-180 and findings backend/models/admin_content_moderation_finding_model.py:11-130 | Moderation categories and evidence records exist | Moderation retention, appeal, export, display, and access policy |
| Audit | Admin actions backend/models/admin_action_model.py:11-180 | Admin action audit table exists | Audit-log retention, central log correlation, access review, and backup policy |
| Authentication | Firebase admin backend/firebase_admin_client.py:26-77 and frontend Firebase config frontend/src/lib/firebase.js:4-15 | Firebase auth boundary exists | Auth data classification, provider logs, export, and deletion policy |
| Secrets | .gitignore:10-17, README.md:5-7, backend/.env.example:1-23 | Commit hygiene and placeholder variables exist | Secret classification, inventory, storage, rotation, and access policy |

### GOV-004 ownership matrix

| Ownership area | Repo evidence | Current result |
|---|---|---|
| Authentication | docs/agent-notes/auth.md describes product behavior, but no named owner | Owner decision missing |
| Authorization | docs/agent-notes/admin/phase-1-foundation/access.md and permissions docs describe behavior, but no named owner | Owner decision missing |
| Payments | README.md:16 and payment docs describe Stripe use, but no named owner | Owner decision missing |
| Database | docs/agent-notes/database.md:3-12 describes schema ownership rules, not production owner | Owner decision missing |
| Storage | R2 docs and code exist, but no named storage owner | Owner decision missing |
| Workers | No worker runtime found | Owner decision missing |
| Release | README.md:18-67 has release notes, no release owner | Owner decision missing |
| Secrets | README.md:5-7 and .gitignore:10-17 cover hygiene, no secret owner | Owner decision missing |
| Monitoring | No monitoring config or owner found | Owner decision missing |
| Backups | No backup owner found | Owner decision missing |
| Incident response | No incident owner found | Owner decision missing |
| Privacy operations | Placeholder privacy text exists, no privacy owner | Owner decision missing |
| Provider accounts | Providers named in README.md:11-16, no account owners | Owner decision missing |
| Search scope | App-owned filename search excluded .git, frontend/node_modules, backend/.venv, backend/tests/legacy and looked for CODEOWNERS, owner, runbook, incident, backup, restore, retention, risk, exception, SLO, SLI, monitor, alert, dashboard, capacity, cost, secret. Term search covered README.md, AGENTS.md, docs, backend, frontend, .github. | Only code/test ownership references and unrelated UI filenames were found |

### GOV-005 audit-process assessment

| Required process element | Repo evidence | Result |
|---|---|---|
| Normalized statuses | No maintained production-readiness audit process found in repo | Missing |
| Evidence per result | backend/tests/README.md:14-18 has backend test-contract evidence concepts only | Not sufficient |
| Source-control reference | No stable production-readiness audit result record with source-revision linkage found | Missing |
| Cadence | Search terms cadence, audit process, production-readiness, reassessment across README.md, AGENTS.md, docs, backend/tests, backend/tests/compliance, .github | Missing |
| Approval | backend/tests/README.md:62 mentions approval for DB-changing commands, not audit approval | Missing |
| Versioning | Policy documents have product-policy versioning in backend/models/policy_document_model.py:20-94, not audit-process versioning | Missing |
| Exception handling | backend/tests/compliance/contracts.py:878-881 validates accepted backend-test gaps, not production audit exceptions | Missing |
| Preserved results | No repo-governed production-readiness result store found | Missing |
| Reassessment triggers | No production-readiness reassessment trigger found | Missing |
| Status conclusion | Current repo evidence does not support meaningful portions of the required production-readiness audit process | FAIL |

### GOV-006 limits/decision matrix

| Limit family | Repo evidence | Decision status |
|---|---|---|
| Request size | No global request-size policy found | Needs decision |
| Timeout | No timeout policy found | Needs decision |
| Rate | Chat rate examples in backend/services/game_chat_service.py:48-51 and backend/services/sub_post_chat_service.py:46-50 | Fragmented |
| Worker count | Worker runtime not found | Needs decision |
| Pool size | backend/database.py:27 uses create_engine without explicit app pool settings | Needs decision |
| Indexes | Many model indexes exist, but no documented basis matrix | Fragmented |
| Retries | No global retry policy found | Needs decision |
| Retention | No approved retention schedule found | Needs decision |
| RPO/RTO | No recovery-objective record found | Needs decision |
| Alert thresholds | No alert config found | Needs decision |
| Boundary tests | Current backend test framework exists, but no universal limit-boundary evidence for these categories | Incomplete |
| Search scope | README.md, AGENTS.md, docs, backend routes/services/models/schemas/alembic/tests excluding legacy, frontend src/tests/config, .github, and root config searched for MAX, MIN, LIMIT, TIMEOUT, TTL, RETRY, rate, pool, worker, retention, RPO, RTO, alert, threshold, quota. | Fragmented local limits only |

### GOV-007 risk/exception search summary

| Search item | Scope | Result |
|---|---|---|
| File names | App-owned files excluding .git, frontend/node_modules, backend/.venv, backend/tests/legacy searched for risk, exception, waiver, incident, runbook, SLO, SLI, monitor, alert, dashboard, backup, restore, owner, secret | No risk or exception register file found |
| Terms | README.md, AGENTS.md, docs, backend, frontend, .github searched for risk register, accepted risk, exception register, waiver, compensating control, expiry, review date, verification evidence | No production risk process found |
| Related findings | backend/tests/compliance has accepted-gap logic for test contracts | Historical/test-process only for this control |
| Why absence matters | GOV-007 requires explicit owner, justification, compensating controls, expiry or review date, and verification evidence | FAIL |

## Operations Appendices


### OPS-001 runtime-topology matrix

| Responsibility | Repo evidence | Runtime status |
|---|---|---|
| Frontend | README.md:11 and 47-51, frontend/vercel.json:1-8 | Intended Vercel frontend, runtime external |
| API | README.md:12 and 18-26, backend/main.py:123-176 | Intended Render web service, runtime external |
| Workers | Worker search terms across app-owned source found no worker process | Missing |
| Scheduler | scheduled_job appears as status-history value, no scheduler runtime | Missing |
| Stateless API | backend/database.py:42-49 yields per-request sessions | Partial code signal only |
| Shared durable sessions/state | Firebase auth and PostgreSQL implied by README.md:13-14 and backend/database.py:14-31 | External verification required |
| Uploads | R2 service in backend/services/r2_storage_service.py:83-220 | External bucket proof required |
| User data | PostgreSQL models under backend/models | Runtime and provider proof required |

### OPS-002 build/runtime-image matrix

| Artifact family | Inspected files | Found | Gap |
|---|---|---|---|
| Frontend build | frontend/package.json:6-14, .github/workflows/ci.yml:63-91 | npm build and lint in CI | No runtime image strategy |
| Backend build | README.md:18-26, .github/workflows/ci.yml:93-145 | pip install and uvicorn command guidance | No backend runtime artifact |
| Container files | App-owned filename search for Dockerfile, docker, compose, Procfile, render.yaml, fly.toml, railway, k8s, kubernetes | frontend/vercel.json only | No image or platform-native backend runtime file |
| Secret exclusion | .gitignore:10-17 | Env and Firebase key ignore patterns | No image or bundle scan evidence |
| Security rebuild/scan | .github/workflows/ci.yml:63-145 | CI build and tests | No scan or rebuild policy |

### OPS-003 runtime-hardening matrix

| Hardening item | Search scope | Evidence found |
|---|---|---|
| Non-root identity | README.md, .github, frontend config, backend config, app-owned deployment filenames, backend source | None |
| Capabilities | Same scope, terms capabilities, cap_add, cap_drop | None |
| Privileged mode | Same scope, terms privileged, security_opt, no-new-privileges | None |
| Docker socket | Same scope, terms docker.sock, Docker socket | None |
| Writable paths | Same scope, terms read-only, readonly, writable paths | None |
| CPU limits | Same scope, terms CPU, limits, resources | None |
| Memory limits | Same scope, terms memory, limits, resources | None |
| Process limits | Same scope, terms pids, process limits | None |
| File-descriptor limits | Same scope, terms ulimit, file descriptor | None |
| Read-only filesystem | Same scope, terms read-only filesystem, readonly | None |
| Platform sandboxing | Same scope, terms sandbox, runtime, container, platform | None |
| Adjacent issue excluded | backend/main.py:91-97 defaults API docs on | Not counted for OPS-003 |

### OPS-004 deployment/rollback matrix

| Required area | Repo evidence | Missing |
|---|---|---|
| Frontend release | README.md:47-51 and .github/workflows/ci.yml:63-91 | Release proof, rollback artifact |
| API release | README.md:18-26 and .github/workflows/ci.yml:93-145 | Health-gated rollout proof |
| Worker release | Worker runtime not found | Worker compatibility and rollback |
| Webhook compatibility | backend/routes/stripe_webhook_routes.py:13-39 | Old/new webhook compatibility evidence |
| Job compatibility | scheduled_job data values only | Job runtime and compatibility evidence |
| Schema compatibility | Alembic run in .github/workflows/ci.yml:141-142 | Rolling migration policy and rehearsal |
| Prior artifacts | No artifact retention config found | Immutable prior artifact evidence |
| Rollback/forward-fix | Search terms rollback, forward-fix, release, artifact, compatibility across app-owned files | Missing |

### OPS-005 control-plane access register

| Control plane | Repo evidence | Required external evidence |
|---|---|---|
| Domain registrar | No repo evidence | Accounts, MFA, owner, recovery, offboarding |
| DNS | No repo evidence | DNS roles, records, audit, recovery |
| CDN | Vercel/R2 implied by README.md:11-16 | CDN settings and access |
| Hosting frontend | README.md:11, frontend/vercel.json:1-8 | Vercel team roles and logs |
| Hosting API | README.md:12 and 18-26 | Render roles and runtime access |
| Database | README.md:13 | Neon users, roles, backups, audit |
| Firebase | README.md:14 | Firebase/Google roles and auth settings |
| Stripe | README.md:16 | Stripe team roles, mode, webhooks, logs |
| Cloudflare/R2 | README.md:15 | Cloudflare users, R2 access keys, bucket roles |
| Repository | .github/workflows/ci.yml:1-178 | GitHub org/repo settings and branch protections |
| Monitoring | No repo evidence | Monitoring provider access |
| Backups | No repo evidence | Backup owner and access |

### OPS-006 secret-storage matrix

| Secret family | Repo evidence | Current result |
|---|---|---|
| Backend database URL | backend/.env.example:1, backend/database.py:14-17 | Env-based loading, store external |
| Firebase admin | backend/.env.example:2-5, backend/firebase_admin_client.py:26-49 | Env or local file path, store external |
| Stripe | backend/.env.example:9-12, backend/services/stripe_service.py:56-85 | Env-based loading, store external |
| R2 | backend/.env.example:14-23, backend/services/r2_storage_service.py:83-115 | Env-based loading, store external |
| Frontend public vars | frontend/.env.example:1-9, frontend/src/lib/firebase.js:4-15 | Public bundle vars expected |
| Repo hygiene | .gitignore:10-17, README.md:5-7 | Local secret files ignored |
| Missing | Provider secret store, runtime injection, access review, rotation, revocation | Partial |

### OPS-008 logging matrix

| Log category | Repo evidence | Current result |
|---|---|---|
| Application logs | logging.getLogger usage in five backend services | Local logger calls only |
| Audit records | backend/models/admin_action_model.py:11-180 | Admin action table, not central logs |
| Provider logs | Stripe/R2/Firebase integrations exist | Provider logs external |
| Access logs | No API access-log middleware found in backend/main.py:100-176 | Missing |
| Worker logs | Worker runtime not found | Missing |
| Database logs | No DB log settings found in backend/database.py:14-31 or config files | Missing |
| Frontend logs | Search of frontend/src for Sentry, PostHog, OpenTelemetry, logging found no production logging client | Missing |
| Central aggregation | Search of README.md, AGENTS.md, docs, backend, frontend, .github for structlog, loguru, Sentry, PostHog, OpenTelemetry, Prometheus, StatsD, Datadog, dashboard, alert, monitor | Missing |
| Retention/access/redaction | No log policy found | Missing |

### OPS-009 operational-measurement matrix

| Measurement area | Repo evidence | Current result |
|---|---|---|
| API traffic/errors/latency | backend/main.py:109-118 health endpoints only | Missing metrics |
| Database pool/query/lock/storage | backend/database.py:27 engine only | Missing metrics |
| Workers | Worker runtime not found | Missing |
| Payments | backend/models/payment_model.py:22-145 and payment events backend/models/payment_event_model.py:20-91 | Data records, not metrics |
| Webhooks | backend/routes/stripe_webhook_routes.py:13-39 and backend/models/payment_event_model.py:20-91 | Processing records, not operational metrics |
| Refunds | backend/models/refund_model.py:20-189 | Data records, not metrics |
| Reconciliation | Money issues backend/models/money_issue_model.py:22-127 | Queue rows, not metrics |
| Uploads | backend/services/venue_image_service.py:145-164 validates upload request | No divergence metrics |
| Authentication | Firebase auth code exists | No auth failure metrics |
| Releases | .github/workflows/ci.yml:63-145 | CI config, no production release metrics |
| Backups | README.md:13 names Neon | Backup success external |
| Provider quotas | Providers named in README.md:11-16 | Quota evidence external |
| Search scope | README.md, AGENTS.md, docs, backend, frontend, .github searched for metrics, Prometheus, StatsD, Datadog, OpenTelemetry, dashboard, alert, monitor, latency, error rate, quota, backup success | No production measurement system found |

### OPS-010 telemetry/correlation matrix

| Correlation area | Repo evidence | Current result |
|---|---|---|
| Request correlation | Search terms request id, request_id, X-Request-ID, correlation across backend/main.py, routes, services, frontend, .github | No standard found |
| Job correlation | No worker/job runtime found | Missing |
| Payment correlation | backend/models/payment_model.py:120-138 and backend/models/payment_event_model.py:73-91 | Provider IDs exist |
| Refund correlation | backend/models/refund_model.py:140-155 | Provider refund IDs exist |
| Admin action correlation | backend/models/admin_action_model.py:84-136 and idempotency indexes | Partial internal IDs |
| Privacy-safe labels | No telemetry-label policy found | Needs decision |
| Bounded attributes | No metrics/telemetry config found | Needs decision |
| Tracing | frontend/playwright.config.js:11 is test tracing only, not distributed tracing | Not applicable as production evidence |

### OPS-011 dashboard/alert matrix

| Alert/dashboard area | Search scope | Current result |
|---|---|---|
| User outcomes | README.md, AGENTS.md, docs, backend, frontend, .github searched for dashboard, alert, monitor, SLO, SLI, metrics, pager, on-call | Missing |
| Financial outcomes | Same scope, plus payment/refund/money source files | Missing dashboards and alerts |
| Data outcomes | Same scope, plus R2 and backup terms | Missing |
| Threshold basis | Search terms threshold, normal behavior, capacity, quota, recovery | Missing |
| Delivery proof | Search terms alert delivery, pager, notification, on-call | Missing |
| Maintenance suppression | Search terms maintenance, suppression, mute, silence | Missing |

### OPS-012 SLI/SLO decision summary

| Objective area | Search terms | Result |
|---|---|---|
| Availability | SLI, SLO, SLA, availability, uptime | No objective |
| Latency | latency, p95, p99, response time | No objective |
| Correctness | correctness, error budget, data freshness | No objective |
| Payment reliability | payment reliability, webhook reliability, refund reliability | No objective |
| Worker delay | worker delay, backlog, queue age | No worker objective |
| Data freshness | freshness, staleness, lag | No objective |
| Public SLA | SLA | No decision |

### OPS-013 provider-outage matrix

| Provider | Local evidence | Missing outage evidence |
|---|---|---|
| Firebase | backend/firebase_admin_client.py:52-77 | Status notifications, degraded auth behavior, provider correlation |
| Stripe | backend/services/stripe_service.py:173-332 and backend/routes/stripe_webhook_routes.py:13-39 | Status notifications, degraded payment/refund behavior, reconciliation procedure |
| R2 | backend/services/r2_storage_service.py:145-220 | Status notifications, degraded upload/read behavior |
| PostgreSQL | backend/database.py:14-49 | Provider status and DB outage procedure |
| Hosting frontend | README.md:11, frontend/vercel.json:1-8 | Vercel outage behavior |
| Hosting API | README.md:12 and 18-26 | Render outage behavior |
| DNS/CDN | No DNS config found | DNS/CDN outage behavior |
| Search scope | README.md, AGENTS.md, docs, backend, frontend, .github searched for provider status, status page, outage, degraded, failover, incident, Firebase, Stripe, R2, PostgreSQL, hosting, DNS, CDN | No operational outage process found |

### OPS-015 runbook coverage matrix

| Scenario | Evidence found | Result |
|---|---|---|
| API outage | backend/main.py:109-118 health endpoints only | No runbook |
| DB outage | backend/database.py:34-39 health check only | No runbook |
| Connection exhaustion | No pool/runbook terms found | No runbook |
| Failed release | README.md:18-67 release notes only | No runbook |
| Failed migration | .github/workflows/ci.yml:141-142 migration command only | No runbook |
| Worker backlog | No worker runtime | No runbook |
| Dead letters | No dead-letter terms found | No runbook |
| Stripe webhook/payment mismatch | Stripe webhook code exists | No runbook |
| R2 upload failure | backend/services/venue_image_service.py:60-80 handles storage errors | No runbook |
| R2 credential failure | backend/services/r2_storage_service.py:83-115 raises config errors | No runbook |
| Firebase outage | backend/firebase_admin_client.py:52-77 provider calls | No runbook |
| Secret compromise | No process found | No runbook |
| Certificate expiry | No certificate terms found | No runbook |
| Backup failure | No backup process found | No runbook |
| Restore | No restore process found | No runbook |

### OPS-016 capacity/cost matrix

| Area | Repo evidence | Missing |
|---|---|---|
| API | backend/main.py:123-176 routers | Capacity model and runtime limits |
| Database connections/storage | backend/database.py:27 engine | Pool, storage, and query capacity |
| Worker throughput | No worker runtime found | Worker capacity |
| Provider quotas | Providers named in README.md:11-16 | Quota and plan evidence |
| R2 requests/storage | backend/.env.example:14-23 and R2 service | Request/storage budget |
| Logs/metrics | No central logging/metrics | Ingestion and retention cost |
| CI | .github/workflows/ci.yml:63-145 | CI minute/cache budget |
| Backups | Neon named in README.md:13 | Backup storage budget |
| Load evidence | No load-test evidence found outside testing guidance docs | Runtime capacity proof missing |

### OPS-018 recovery-objective matrix

| Recovery element | Search scope | Result |
|---|---|---|
| RPO | README.md, AGENTS.md, docs, backend, frontend, .github searched for RPO | Missing |
| RTO | Same scope searched for RTO | Missing |
| PITR need | Same scope searched for PITR and WAL | Missing |
| Backup/WAL window | Same scope searched for backup window, WAL window | Missing |
| Version/role/extension dependencies | backend/alembic and database docs inspected | No recovery objective proof |
| Business impact | Same scope searched for business impact, criticality, recovery priority | Missing |

### OPS-020 R2/configuration-recovery matrix

| Recovery area | Repo evidence | Missing |
|---|---|---|
| R2 originals | backend/models/venue_image_model.py:100-108 object metadata | Loss tolerance undecided |
| R2 derivatives | No derivative model or policy found | Loss tolerance undecided |
| Bucket recovery | backend/.env.example:14-23 names bucket settings | Provider recovery evidence missing |
| Object versioning/lifecycle | No repo config found | Provider evidence missing |
| Metadata reconciliation | Venue image metadata exists | No reconciliation process |
| DNS recovery | No DNS config found | Missing |
| Provider settings recovery | README.md:11-16 provider list only | Missing |
| Monitoring recovery | No monitoring config found | Missing |
| Secret recreation | Secret env names exist | Procedure missing |

### OPS-022 retention matrix

| Data category | Repo evidence | Retention status |
|---|---|---|
| Accounts | backend/services/account_deletion_service.py:930-945 anonymizes users | No approved schedule |
| Profiles | backend/models/user_model.py:121-154 | No approved schedule |
| Games | Game models exist, no retention policy found | No approved schedule |
| Bookings | Booking models exist, no retention policy found | No approved schedule |
| Messages | backend/models/chat_message_model.py:20-193 and backend/models/sub_post_chat_message_model.py:19-182 | No approved schedule |
| Notices | Notification and platform notice models exist | No approved schedule |
| Payments | backend/models/payment_model.py:22-145 | No approved schedule |
| Images | backend/models/venue_image_model.py:100-140 | No approved schedule |
| Moderation | backend/models/admin_content_moderation_finding_model.py:11-130 | No approved schedule |
| Audit | backend/models/admin_action_model.py:11-180 | No approved schedule |
| Logs | Local logger calls only | No approved schedule |
| Metrics | No metrics system found | No approved schedule |
| Backups | No backup config found | No approved schedule |
| Exports | No export workflow found | No approved schedule |
| Test data | backend/tests/conftest.py:102-143 truncates test tables | No approved retention policy |

### OPS-023 privacy-workflow matrix

| Privacy workflow | Repo evidence | Current result |
|---|---|---|
| Authenticated deletion | backend/routes/auth_routes.py:60-66 | Present |
| Deletion durability | backend/services/account_deletion_service.py:145-207 and admin_user_delete_service.py:756-778 record partial failures | Partial |
| Firebase deletion | backend/firebase_admin_client.py:71-77 | Present, provider runtime unverified |
| PostgreSQL anonymization | backend/services/account_deletion_service.py:930-945 | Present |
| Stripe references | backend/services/account_deletion_service.py:210-259 detaches saved methods | Partial |
| R2 handling | Venue images store uploaded_by_user_id with SET NULL in backend/models/venue_image_model.py:94-108 | No privacy-specific object workflow |
| Jobs | No worker/job runtime found | Missing |
| Logs | No central log policy found | Missing |
| Backups | No restore-time reapplication proof | Missing |
| Access | No authenticated data-access export route found in privacy search | Missing |
| Correction | Profile/edit flows exist, but no formal correction workflow evidence | Incomplete |
| Export | No user-data export workflow found | Missing |
| Cross-user export prevention | No export feature found | Not evidenced |

### OPS-024 production-data handling matrix

| Data handling area | Repo evidence | Current result |
|---|---|---|
| Synthetic data | README.md:5-7 says fake/demo data | Partial |
| Separate test DB | backend/tests/README.md:60 and backend/tests/conftest.py:71-95 | Partial |
| Test cleanup | backend/tests/conftest.py:102-143 | Partial |
| CI test database | .github/workflows/ci.yml:93-145 | Partial |
| Provider modes | README.md:16 says Stripe test mode | Stripe only |
| Production dump restrictions | Search terms production data, dump, anonymization, minimization, synthetic, fake data across app-owned files | Missing |
| Provider exports | No provider export handling found | Missing |
| Backup handling | No backup data process found | Missing |
| Access controls | Provider/dashboard evidence external | Missing |

### OPS-025 provider-evidence register

| Provider/control plane | Repo evidence | External evidence still required |
|---|---|---|
| Vercel | README.md:11 and 47-51, frontend/vercel.json:1-8 | Project settings, domains, env vars, access, logs |
| Render | README.md:12 and 18-26 | Service settings, env vars, runtime, access, logs |
| Neon/PostgreSQL | README.md:13, backend/database.py:14-31 | Backups, roles, PITR, access, monitoring |
| Firebase/Google Cloud | README.md:14, backend/firebase_admin_client.py:26-77, frontend/src/lib/firebase.js:4-15 | Project settings, auth providers, roles, logs |
| Stripe | README.md:16, backend/services/stripe_service.py:56-97 | Mode, webhooks, events, roles, alerts |
| Cloudflare/R2 | README.md:15, backend/services/r2_storage_service.py:83-220 | Bucket settings, access keys, lifecycle, logs |
| DNS | No repo evidence | Registrar and DNS records |
| Repository | .github/workflows/ci.yml:1-178 | Branch protection, required checks, admins |
| Monitoring | No repo evidence | Dashboard and alert settings |
| Backups | No repo evidence | Backup settings and restore records |
| Search scope | README.md, AGENTS.md, docs, backend, frontend, .github, root config searched for provider dashboard, hosting settings, Firebase settings, Stripe dashboard, Cloudflare, R2, PostgreSQL backup, DNS, repository settings, monitoring, backup | No safe provider evidence records found |

### OPS-007 secret-inventory search summary

| Search dimension | Scope or evidence | Result |
|---|---|---|
| Repository scope | `README.md`, `AGENTS.md`, `docs/`, `backend/`, `frontend/`, `.github/`, and root configuration; dependency directories and `backend/tests/legacy/` excluded | App-owned source and governance material inspected |
| Terms | secret inventory, secret owner, rotation, revocation, emergency response, safe overlap, workload identity, OIDC, short-lived credential, secret store, password manager, Vault, Doppler, MFA, least privilege, offboarding | No maintained secret-inventory record found |
| Existing clues | Backend and frontend environment examples and README deployment variables | Variable names only; no ownership or lifecycle metadata |
| Missing required fields | Owner, scope, dependent systems, storage location, environment, rotation and revocation procedures, emergency response, overlap strategy, and short-lived identity decision | Control remains FAIL |

### OPS-014 incident-response search summary

| Search dimension | Scope or terms | Result |
|---|---|---|
| Repository scope | `README.md`, `AGENTS.md`, `docs/`, `backend/`, `frontend/`, `.github/`, and root configuration; dependency directories and `backend/tests/legacy/` excluded | Operational documentation and source inspected |
| Terms | incident, severity, SEV, on-call, oncall, pager, containment, evidence preservation, recovery, reconciliation, communication, postmortem, post-incident, tracked actions | No incident-response process found |
| Missing clauses | Severity model, assigned roles, containment, evidence preservation, recovery, financial and data reconciliation, communication, post-incident review, owners, and tracked actions | Control remains FAIL |

### OPS-017 PostgreSQL backup evidence summary

| Evidence area | Repository result | External evidence required |
|---|---|---|
| Provider identity | README identifies Neon PostgreSQL; `backend/database.py:14-31` consumes `DATABASE_URL` | Active production project and backup capability |
| Search scope | Repository docs, configuration, and source searched for backup, PITR, WAL, snapshot, retention, restore, encryption, backup credential, and monitored completion | Provider configuration cannot be established statically |
| Backup controls | No repository-managed schedule, encryption setting, access restriction, retention, monitoring, or separately protected backup credential evidence | Provider dashboard and operational records |
| Status basis | Application source cannot prove production backup enablement | EXTERNAL EVIDENCE REQUIRED remains controlling |

### OPS-019 restore-evidence summary

| Search dimension | Scope or evidence | Result |
|---|---|---|
| Non-restore evidence | `.github/workflows/ci.yml:141-145` runs migrations and tests | Does not demonstrate backup restoration |
| Repository scope | `README.md`, `AGENTS.md`, `docs/`, `backend/`, `frontend/`, `.github/`, and root configuration; dependency directories and `backend/tests/legacy/` excluded | Restore-related material inspected |
| Terms | restore, backup restore, isolated restore, decryption, integrity, application startup, identity mapping, Stripe reference, R2 reference, deletion tombstone, restore validation | No isolated restore record found |
| Missing validation | Decryption, database integrity, application startup, Firebase identity mapping, Stripe and R2 references, jobs, deletion tombstones, duration, owner, and follow-up record | Control remains FAIL |

### OPS-021 exercise-evidence summary

| Search dimension | Scope or terms | Result |
|---|---|---|
| Repository scope | `README.md`, `AGENTS.md`, `docs/`, `backend/`, `frontend/`, `.github/`, and root configuration; dependency directories and `backend/tests/legacy/` excluded | Recovery and incident exercise material inspected |
| Terms | tabletop, recovery exercise, disaster recovery, restore exercise, rollback exercise, secret compromise, webhook outage, worker backlog, provider outage, user-deletion failure, domain recovery, control-plane recovery | No exercise record found |
| Missing evidence | Date, scope, participants, scenario, expected and actual results, gaps, actions, owner, due date, and retest | Exercise scope and cadence remain an owner decision; status remains NEEDS DECISION |

## Part 5 Corrections Made

### Corrected priorities

- GOV-003 P1, GOV-004 P1, GOV-006 P1, GOV-007 P1, OPS-010 P1, OPS-012 P1, OPS-013 P1, OPS-016 P1, OPS-020 P1, OPS-021 P1, OPS-022 P1.

### Status changes

- GOV-005 changed from PARTIAL to FAIL. No other status changed.

### GOV-005 evidence correction

- removed CURRENT TEST SOURCE. backend/tests/README.md is treated as documentation for the backend test checker, not production-readiness audit evidence. The current audit and prior generated reports were not used as positive repository evidence.

### OPS-003 scope correction

- removed database-pool and API-docs reasoning from OPS-003. The corrected row evaluates only container or platform-runtime hardening controls.

### Evidence-class corrections

- all evidence classes were normalized to the allowed list only. CURRENT TEST SOURCE is used only where actual current test source supports the row, notably OPS-024.

### Negative-search corrections

- added auditable search scope for GOV-004, GOV-007, OPS-002, OPS-003, OPS-007, OPS-008, OPS-009, OPS-011, OPS-012, OPS-014, OPS-015, OPS-017, OPS-019, OPS-021, and OPS-025.

### Appendix expansions

- expanded the governance and operations appendices into compact matrices covering required components, environments, data classes, providers, runtime hardening, logging categories, metrics categories, runbook scenarios, retention categories, privacy workflows, production-data handling, and provider evidence.

### Controls reassessed but retained

- GOV-001 through GOV-004, GOV-006, GOV-007, and OPS-001 through OPS-025 retained their corrected final statuses. GOV-005 changed from PARTIAL to FAIL.

### Final report-only consolidation

- Added the five required standalone appendices omitted from the Codex response: OPS-007, OPS-014, OPS-017, OPS-019, and OPS-021.
- Verified that all 32 control IDs are present in exact order.
- Verified every Class and Priority against the master checklist.
- Verified that all statuses and evidence classes use the allowed audit vocabulary.
- Normalized the report into one complete Markdown artifact without changing the corrected control findings.