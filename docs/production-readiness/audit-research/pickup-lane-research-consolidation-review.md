# Pickup Lane Research Consolidation Review

## Outcome

The seven reports were converted into a normalized master checklist containing **163 consolidated controls** and **20 explicit decision items**. A separate source register preserves all 575 primary requirement rows for traceability. No repository compliance status was assigned during consolidation.

## Report completeness

| Research report | Primary requirements | Supporting verification/configuration rows | Consolidation result |
|---|---:|---:|---|
| 1. FastAPI and HTTP/API | 46 | 55 | Included |
| 2. Firebase, accounts, authorization, admin access | 81 | 77 | Included |
| 3. Audit, moderation, sensitive admin data, notices | 76 | 11 | Included |
| 4. PostgreSQL, SQLAlchemy, Alembic | 70 | 36 | Included |
| 5. Stripe, finance, R2, durable jobs | 109 | 0 | Included |
| 6. React, testing, CI, supply chain | 93 | 53 | Included |
| 7. Deployment, secrets, observability, recovery, data lifecycle | 100 | 38 | Included |

## Major overlap groups merged

- Typed configuration and environment separation: API-002, DEPLOY-004, FE-002–003, Firebase/Stripe/R2 environment controls.
- Graceful shutdown and lifecycle: API-001/004, DBCONN-005, JOB-024–026, DEPLOY-006.
- HTTPS, proxy trust, host validation, and domains: API-008–011, DEPLOY-011, provider dashboard controls.
- Secret and token redaction: API-033, FBAUTH-005, AUDIT-015–016, FESEC-001–002/013, SECRET-001–010, OBS-002.
- Idempotency and partial failure: TXN, STRIPE, FIN, JOB, CASE, ENF, NOTICE, and account-deletion requirements.
- Exact money representation: API-027, SCHEMA-006, FIN-017.
- Health and worker observability: API-036–038, DEPLOY-005, JOB-027–028, OBS-005–010.
- R2 configuration and recovery: STORAGE-032, EXT-005, RECOVERY-007–009.
- CI artifact integrity and deployment promotion: CI/SUPPLY controls plus DEPLOY-008–010.
- Data classification, retention, deletion, exports, and backups: SENS, AUDIT, DATA, RECOVERY, and ACCOUNT requirements.

## Classification normalization

The source reports used `REQUIRED`, `STRONGLY RECOMMENDED`, and `CONTEXT-DEPENDENT` correctly in most cases, but they did not always use those labels with identical strictness. The master checklist uses four normalized labels: `MUST`, `MUST DECIDE`, `SHOULD`, and `CONDITIONAL`. This prevents a required decision from being mistaken for a universal technical setting.

Examples of normalization:
- Exact thresholds for limits, rates, timeouts, pools, retries, alerts, retention, RPO, and RTO are `MUST DECIDE`, not universal constants.
- ML moderation governance is `CONDITIONAL`; deterministic moderation does not require an ML program.
- App Check, tracing, DNSSEC, multi-region deployment, impersonation, break-glass accounts, dual approval, SBOM signing, and high SLSA levels remain conditional or risk-based.
- Restore testing, current authorization, webhook signature verification, database constraints for invariants, secret protection, and durable financial idempotency remain `MUST`.

## Genuine unresolved areas

- Production hosting, edge, proxy, worker, scheduler, queue, secret-manager, monitoring, and managed PostgreSQL products.
- API worker/instance count, connection budget, concurrency, keep-alive, timeout, and shutdown values.
- Request, upload, pagination, search, bulk, rate-limit, and retry thresholds by endpoint and identity.
- Firebase browser persistence, revocation-check strategy, email-verification gates, App Check, and ordinary-user MFA.
- Administrator MFA factor, recent-authentication policy, privilege granularity, dual control, break-glass, and impersonation.
- Account suspension and deletion behavior, grace period, restoration, retained/anonymized records, and provider ordering.
- Moderation policy taxonomy, synchronous/asynchronous scanning, fail-open/closed rules, case states, notices, and appeals.
- Audit, moderation, financial, message, telemetry, backup, export, and test-data retention periods.
- Capacity representation and concurrency strategy for game spots, waitlists, bookings, and Need a Sub positions.
- Booking/payment reservation model, pending states, expiration, capacity conflict, compensation, refund versus credit policy.
- Credit ledger rules, expiration, transferability, mixed payment, negative balances, and administrative limits.
- Public/private object classes, SVG/animation policy, re-encoding, metadata removal, malware scanning, and original retention.
- Database pool/timeout/isolation choices, RLS value, PostgreSQL enums, soft deletion, and cursor snapshot semantics.
- Migration deployment sequence, online DDL capabilities, production-size rehearsal, rollback versus forward-fix policy.
- Browser support, WCAG conformance target, performance budgets, source-map policy, service workers, and analytics/session replay.
- Coverage gates, provider tests in pull requests, browser-test parallelism, mutation testing, and flaky-test policy.
- SBOM, signing, provenance, SLSA target, artifact promotion, and production approval policy.
- SLIs/SLOs, alert thresholds, synthetic monitoring, on-call/escalation, maintenance, and incident severity model.
- RPO, RTO, PITR window, backup retention, restore-test cadence, R2 recovery, and disaster-exercise frequency.
- Data classifications, collection purposes, retention schedules, deletion/anonymization, backup disclosure, and privacy request process.

## Next controlled step

Compare this checklist against the completed Codex static inventories. That comparison should classify only repository-verifiable evidence. Runtime behavior, provider dashboards, production configuration, and operational processes must remain `EXTERNAL EVIDENCE REQUIRED` or `NOT ASSESSED` until separately verified. After the inventory crosswalk is complete, generate the controlled Codex audit prompt for the current working tree.
