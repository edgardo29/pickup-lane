# Pickup Lane Master Production-Readiness Blueprint

**Status:** Proposed execution blueprint for owner review

**Planning date:** August 3, 2026

**Implementation authorization:** None. This document plans the work. It does not authorize code, Git, provider, deployment, migration, database, worker, storage, monitoring, backup, restore, or CI changes.

## 1. Current program status

- The locked audit contains **163 controls**, including **117 unresolved P0 controls** and **29 confirmed P0 failures**.
- The finalized remediation plan organizes the work into **WS01 through WS10** and requires phased implementation, current tests, provider evidence, runtime verification, and recovery evidence.
- All **27 owner decisions are approved**. There are **0 open owner decisions**.
- WS01 governance documents and decision records have been prepared and reviewed outside the repository.
- The user is finishing the merge of intended previous application work into `main`. The new production-readiness documents are intentionally excluded from that old-work merge.
- No production-readiness application implementation has started.
- The previously generated WS02 Codex prompt and package are withdrawn and must not be used.

## 2. Authority order

When two artifacts disagree, stop and apply this order:

1. The current repository tree after the user finishes and verifies the merge into `main`.
2. The six locked audit reports and the 163-control manifest.
3. The finalized production-readiness remediation plan.
4. The approved foundation and Decision Packets 2 through 4.
5. This master blueprint.
6. The approved pass-specific inspection record.
7. The pass-specific Codex prompt.

A lower item cannot silently override a higher item. A discovered conflict produces a documented blueprint correction or a superseding owner decision before implementation continues.

## 3. Fixed decisions versus later technical values

The architectural and product direction is settled. The following items remain later **technical design or evidence-based values**, not reopened owner decisions:

| Area | Approved direction | Still selected later from evidence | First blocking pass |
|---|---|---|---|
| Security headers | Ownership split by response class and layer | Exact header values, CSP directives, HSTS behavior, staging/production differences | WS02-03 |
| Limits and timeouts | Use documented evidence and boundary tests | Request/header/body limits, timeouts, rate values, pagination limits | WS02-04 |
| PostgreSQL connections | One deployment-wide budget with reserve | Provider limit, instances, workers, pool, overflow, wait timeout | WS04-01 |
| Payment model | Separate payment, booking, refund, and compensation states | Exact enums, transitions, reservation duration, repair rules | WS05-02 |
| Venue images | Admin-only uploads; initials for users; sanitize before publication | Formats, bytes, pixels, derivative sizes, processing limits | WS06-02 |
| R2 lifecycle | Controlled deletion, recovery, reconciliation, and fallback | Cache TTL, recovery window, cleanup interval, provider settings | WS06-03 |
| Browser/performance | Modern browser policy and measured budgets | Exact device/browser matrix and measured performance thresholds | WS07-05 |
| Test artifacts | Sanitized, attributable, risk-based | Storage system and retention duration | WS08-03 |
| Service objectives | Measure critical availability, correctness, payments, jobs, and freshness | Numeric objectives, launch thresholds, error budgets | WS09-03 |
| Privacy/retention | Purpose-based and table-by-table lifecycle | Exact durations and legally reviewed exceptions | WS10-01 |
| Recovery | Tiered protection and tested restore | RPO, RTO, PITR window, backup retention, recurring exercise schedule | WS10-04 |

No exact value may be invented merely to complete a prompt.

## 4. Repository baseline and Git workflow

### 4.1 Hard baseline gate

Implementation starts only after the user confirms the intended previous work is merged into `main`. The first execution step is `BASE-00`, a read-only repository inspection.

The baseline inspection must establish:

- the current branch and exact `main` commit
- a clean or explicitly understood working tree
- all worktrees and their owners
- all stashes and whether they contain intended work
- recent branch/merge history
- remote tracking and whether local `main` is current
- that the approved production-readiness documents were not accidentally included in the old-work merge

No exact branch-creation or worktree-creation command is prescribed until that inspection is reviewed.

### 4.2 Intended isolation model

The preferred model, subject to the baseline inspection, is:

```text
pickup-lane/                         trusted current development checkout
pickup-lane-production-readiness/    isolated remediation worktree
```

The remediation worktree uses a dedicated integration branch. Each pass is completed as one narrow reviewable change set. A separate child branch or pull request may be used per pass where practical; otherwise each accepted pass must still remain an independently revertible commit.

### 4.3 Git rules

1. Start every pass from a clean accepted commit.
2. Do not mix unrelated feature work with production-readiness remediation.
3. Include the pass ID in the branch, commit, pull request, evidence record, and review notes.
4. One pass may be split after inspection; it may not be broadened or silently combined with another pass.
5. Do not begin the next pass until the current pass is accepted, corrected, or reverted.
6. Database migrations, provider changes, and destructive operations require explicit rollback or forward-fix plans before execution.
7. Sensitive provider evidence is not committed to normal source control. The repository stores only sanitized records or references approved by the evidence policy.
8. Codex never decides the next pass, owner policy, architecture, or exception.

## 5. Program gates

| Gate | Required result | Work allowed after gate |
|---|---|---|
| G0: Main ready | Intended previous work merged; user confirms merge complete | Read-only baseline inspection |
| G1: Baseline trusted | Exact commit, clean state, worktrees/stashes understood, isolation approved | Governance import only |
| G2: Governance versioned | Approved WS01 package in remediation branch; 27 decisions reconciled | Early test, telemetry, and control-plane enablers |
| G3: Foundation enablers | Current-test taxonomy, correlation/redaction contract, safe evidence process | WS02 production foundation |
| G4: Deployable foundation | Typed configuration, runtime lifecycle, edge/HTTP chain, staged proof | WS03 and WS04 controlled implementation |
| G5: Identity and database foundation | Identity/authorization and database/migration invariants proven | Durable jobs, payments, storage |
| G6: Durable provider workflows | Jobs, payments, refunds, storage lifecycle and reconciliation proven | Stable frontend completion |
| G7: Frontend production evidence | State isolation, routes, browser security, accessibility, performance proven | Final CI and observability gates |
| G8: Release and observability evidence | CI, scans, branch protection, logs, audit, metrics, alerts, capacity proven | Privacy, runbooks, restore and exercises |
| G9: Operational readiness | Secrets/access, privacy/retention, runbooks, restore and exercises proven | Final evidence sweep |
| G10: Reassessment complete | Fresh 163-control assessment and P0 disposition | Sign-off or explicit no-sign-off |

## 6. Approved decision register

All owner decisions are locked. A change requires a new superseding decision record.

| Audit ID | Approved record | Decision | Earliest workstream |
|---|---|---|---|
| API-M18 | FDN-03 | Decide OpenAPI/docs exposure, inventory, versioning, compatibility, and deprecation policy. | WS01 |
| GOV-004 | FDN-01 | Assign named production owners across core systems and provider accounts. | WS01 |
| GOV-006 | FDN-04 | Decide documented bases for limits, thresholds, pools, retries, retention, RPO, RTO, and alerts. | WS01 |
| TST-011 | FDN-05 | Decide retry, flake, artifact retention, and risk-based coverage policy. | WS01 |
| API-M08 | FDN-02 | Assign security-header ownership between app and edge. | WS02 |
| TST-017 | FDN-06 | Decide artifact identity, SBOM, provenance, signing, and release-evidence policy. | WS02 |
| OPS-010 | FDN-07 | Decide telemetry label bounds, privacy review, and correlation/tracing posture. | WS08 |
| DB-002 | DBP-01 | Decide deployment-wide DB connection budget. | WS02 |
| FE-M09 | IDB-05 | Decide third-party browser-code inventory, data-sharing, CSP/SRI, and provider-failure posture. | WS02 |
| FE-M12 | OPP-01 | Decide WCAG target and accessibility verification scope. | WS02 |
| FE-M13 | OPP-02 | Decide browser support, performance budgets, source-map policy, and telemetry/performance measurement. | WS02 |
| IAM-003 | IDB-01 | Decide Firebase browser persistence and retry/replay behavior. | WS02 |
| IAM-010 | IDB-04 | Decide whether Firebase App Check applies. | WS02 |
| STO-009 | DBP-04 | Decide deletion, lifecycle, retention, recovery, monitoring, and R2 controls. | WS02 |
| ADM-014 | OPP-03 | Decide enforcement notice timing, suppression, appeal, and safe-content rules. | WS03 |
| IAM-006 | IDB-02 | Decide source-of-truth matrix for identity, profile, role, account state, ownership, and permissions. | WS03 |
| IAM-007 | IDB-03 | Decide verified-email policy and administrator verified-identifier requirement. | WS03 |
| PAY-007 | DBP-02 | Decide canonical financial state mapping. | WS03 |
| OPS-018 | OPP-04 | Decide RPO, RTO, PITR, backup/WAL window, and restore dependencies. | WS04 |
| OPS-020 | OPP-05 | Decide R2 loss tolerance and recovery protection. | WS04 |
| OPS-021 | OPP-06 | Decide tabletop and technical recovery exercise cadence and scope. | WS04 |
| OPS-022 | OPP-07 | Decide data-purpose and retention schedules. | WS04 |
| STO-006 | DBP-03 | Decide image sanitization, re-encoding, derivative, metadata, and processing requirements. | WS05 |
| OPS-012 | OPP-09 | Decide service indicators, objectives, launch thresholds, and error-budget posture. | WS08 |
| OPS-016 | OPP-10 | Decide capacity and cost model across API, DB, workers, providers, logs, CI, and backups. | WS08 |
| ADM-008 | OPP-11 | Decide audit review, alerting, retention, archive, deletion, legal hold, and export handling. | WS10 |
| DB-011 | OPP-08 | Decide per-table lifecycle, deletion, anonymization, retention, restoration, and backup-retention policy. | WS10 |

## 7. Workstream order

The phase order is dependency-based, not a simple WS02, WS03, WS04 sequence:

1. **WS01** governance is versioned first.
2. Early **WS08**, **WS09**, and **WS10** enabling slices establish test isolation, correlation/redaction, and safe provider-evidence handling.
3. **WS02** establishes the production configuration and deployment foundation.
4. **WS03** identity/authorization and **WS04** database/concurrency may proceed in controlled parallel slices after their dependencies are stable.
5. **WS05** implements the shared durable-job foundation before payment and other consumers.
6. **WS06** follows the database/job foundation for admin venue-image processing and R2 reconciliation.
7. **WS07** validates the frontend against stable API and identity contracts.
8. **WS08** and **WS09** finish their CI/release and production-observability gates.
9. **WS10** completes privacy, secrets, incident response, restore, and recovery exercises.
10. A fresh control reassessment follows. Implementation alone never equals closure.

## 8. Planned implementation-pass register

This blueprint contains **42 planned passes**. Pass IDs define order and scope, not calendar estimates.

| Pass | Track | Type | Title | Primary control count | Dependencies |
|---|---|---|---|---:|---|
| BASE-00 | PROGRAM | Repository inspection | Repository baseline and isolation gate | 0 | User finishes merging intended previous work into main |
| GOV-01 | WS01 | Decision and governance | Import and reconcile the approved governance package | 5 | BASE-00 |
| EN-01 | WS08 | Test infrastructure | Early current-test taxonomy and isolation baseline | 5 | GOV-01 |
| EN-02 | WS09 | Architecture contract | Early correlation, event-envelope, and redaction contract | 2 | GOV-01 |
| EN-03 | WS10 | Operational/provider foundation | Early secrets, control-plane access, and evidence-handling foundation | 4 | GOV-01 |
| WS02-01 | WS02 | Domain implementation | Typed settings and environment isolation | 3 | EN-01, EN-02, EN-03 |
| WS02-02 | WS02 | Deployment foundation | Runtime process, lifecycle, health, and deployability | 6 | WS02-01; DBP-01 policy; preliminary provider topology |
| WS02-03 | WS02 | Configuration and provider verification | Proxy, host, TLS, CORS, and response-class security headers | 5 | WS02-01, WS02-02; FDN-02; actual edge/origin topology |
| WS02-04 | WS02 | Domain implementation | Request limits, timeouts, rate controls, and stable errors | 4 | WS02-01, EN-02; evidence-based limit method |
| WS02-05 | WS02 | Domain implementation and runtime verification | HTTP contracts, schemas, docs, cache, and end-to-end chain | 5 | WS02-03, WS02-04; FDN-03 |
| WS03-01 | WS03 | Domain implementation | Identity authority and verifier-controlled field protection | 7 | WS02-01, WS02-05; IDB-01, IDB-02, IDB-03 |
| WS03-02 | WS03 | Schema, migration, and domain implementation | Provisioning, account-state lifecycle, and concurrent first login | 3 | WS03-01; WS04-01 and WS04-02 design inputs |
| WS03-03 | WS03 | Provider/security implementation | High-risk authentication and Firebase control verification | 3 | WS03-01; EN-03; IDB-04 |
| WS03-04 | WS03 | Domain implementation and current tests | Complete authorization matrix and negative proof | 5 | WS03-01, WS03-02; stable resource and state models |
| WS03-05 | WS03 | Schema/domain/privacy implementation | Moderation states, safe notices, and minimum-necessary admin data | 7 | WS03-04; WS04-02; WS05 durable notice path design; OPP-03; WS09-02 audit contract |
| WS04-01 | WS04 | Database foundation | Database engine/session lifecycle, connection budget, and least-privilege roles | 6 | WS02-02; DBP-01; actual PostgreSQL provider/topology |
| WS04-02 | WS04 | Database/domain/concurrency | Transactions, invariants, locks, and deterministic concurrency | 8 | WS04-01; approved identity/payment/job/storage invariant inputs |
| WS04-03 | WS04 | Schema and migration | Migration policy, compatibility, interruption, and production-like rehearsal | 3 | WS04-01, WS04-02; stable required schema capabilities |
| WS05-01 | WS05 | Schema, worker, and deployment | Durable job model, claim/lease lifecycle, and worker deployment | 8 | WS02-02; WS04-01 through WS04-03; EN-02 |
| WS05-02 | WS05 | Financial domain implementation | Payment and booking state machines with webhook authority | 8 | WS05-01; WS04-02; DBP-02; WS03-04 |
| WS05-03 | WS05 | Durable financial/notification workflows | Refunds, credits, notices, moderation delivery, and reconciliation | 7 | WS05-01, WS05-02; WS03-05 |
| WS05-04 | WS05 | Concurrency/failure/provider/runtime verification | Deterministic failure, replay, sandbox, and deployed-worker verification | 23 | WS05-01 through WS05-03; Stripe sandbox; staging worker |
| WS06-01 | WS06 | Storage domain implementation | Admin-only venue-image authority and upload initiation | 3 | WS02 foundation; WS03 active-admin gate; DBP-03 |
| WS06-02 | WS06 | Storage processing implementation | Venue-image validation, sanitization, re-encoding, and derivatives | 4 | WS06-01; WS05-01 durable jobs if asynchronous; evidence-based file limits |
| WS06-03 | WS06 | Storage lifecycle/provider/runtime | R2 lifecycle, deletion, cache behavior, reconciliation, and recovery | 2 | WS06-01, WS06-02; DBP-04; OPP-05; WS05-01 |
| WS07-01 | WS07 | Frontend/build/release | Production frontend build, public configuration, artifact identity, and source maps | 2 | WS02-02, WS02-05; FDN-06; OPP-02 |
| WS07-02 | WS07 | Frontend/browser | Authentication persistence, identity-scoped state, logout, switch, and safe retries | 3 | WS03-01 through WS03-03; IDB-01 |
| WS07-03 | WS07 | Frontend/browser | Routes, API errors, forms, URLs, browser storage, and resilient UI state | 4 | WS02-04, WS02-05; stable backend authorization/error contracts |
| WS07-04 | WS07 | Frontend security/provider | Third-party browser code, CSP/SRI posture, headers, and provider failure isolation | 2 | WS02-03; IDB-05; actual Firebase/Stripe/browser dependency inventory |
| WS07-05 | WS07 | Frontend/accessibility/performance | WCAG 2.2 AA, browser support, and performance verification | 2 | WS07-01 through WS07-04; EN-01; OPP-01, OPP-02 |
| WS08-01 | WS08 | Test infrastructure | Complete current-test inventory, fixtures, and control mapping | 6 | EN-01; stable outputs from WS02 through WS07 |
| WS08-02 | WS08 | Current tests | Critical workflow, deterministic concurrency, migration, provider, privacy, and recovery suites | 5 | WS08-01; stable domain implementations; sandbox/restore environments |
| WS08-03 | WS08 | CI/supply chain/provider | Reproducible CI, scans, branch protection, SBOM, provenance, and release evidence | 6 | WS08-01, WS08-02; stable job names and release artifacts; EN-03 |
| WS09-01 | WS09 | Observability implementation | Structured request/event logging, correlation, redaction, and log aggregation | 3 | EN-02; stable release/environment context and event models |
| WS09-02 | WS09 | Database/domain/privacy | Append-only administrative audit trail and sensitive-access controls | 6 | WS03-04, WS03-05; WS04-02; OPP-11 |
| WS09-03 | WS09 | Observability/operations | Metrics, service objectives, dashboards, alerts, capacity, and cost evidence | 4 | WS09-01, WS09-02; stable WS02-WS06 workflows; OPP-09, OPP-10 |
| WS10-01 | WS10 | Privacy/retention/schema | Data classification, table lifecycle, retention, privacy, and audit lifecycle | 6 | Stable data models from WS03-WS06; OPP-07, OPP-08, OPP-11 |
| WS10-02 | WS10 | Operational/provider | Secrets, provider control-plane access, MFA, rotation, revocation, and offboarding | 4 | EN-03; actual provider accounts and hosting topology |
| WS10-03 | WS10 | Operational process/exercise | Incident response, provider-outage handling, and operational runbooks | 3 | WS09-03; stable deployed architecture; named owners |
| WS10-04 | WS10 | Recovery/provider/runtime | Backup/PITR evidence, isolated restore, recovery validation, and exercises | 5 | WS10-01 through WS10-03; stable application release; WS09 observability; OPP-04, OPP-05, OPP-06 |
| CLOSE-01 | PROGRAM | Audit preparation | Cross-workstream evidence completeness and discrepancy sweep | 0 | All workstream exit gates |
| CLOSE-02 | PROGRAM | Independent reassessment | Fresh 163-control reassessment and production-readiness decision | 0 | CLOSE-01; all correction/retest passes complete |

## 9. Detailed pass specifications

### BASE-00: Repository baseline and isolation gate

- **Track:** PROGRAM
- **Pass type:** Repository inspection
- **Primary controls:** Program gate; no primary control reassessment
- **Prerequisites:** User finishes merging intended previous work into main
- **Maximum scope:** Read-only inspection of branch, status, worktrees, stashes, recent history, remotes, and the exact main commit. Decide the isolated remediation branch/worktree only after inspection.
- **Required output:** Recorded baseline commit, clean-tree confirmation, protected unrelated work, chosen isolation strategy, and rollback anchor.
- **Proof before acceptance:** Read-only Git output reviewed; no repository mutation before approval.
- **Stop condition:** Stop on a dirty or ambiguous baseline, missing intended merge, unresolved stash/worktree ownership, or uncertainty about the correct source branch.

### GOV-01: Import and reconcile the approved governance package

- **Track:** WS01
- **Pass type:** Decision and governance
- **Primary controls:** GOV-001, GOV-004, GOV-005, GOV-006, GOV-007
- **Prerequisites:** BASE-00
- **Maximum scope:** Add only the approved WS01 governance documents and root README linkage to the isolated remediation branch. Reconcile the 27 approved decisions and 0 open decisions without changing locked audit findings.
- **Required output:** Versioned governance package, decision registers, ownership, limits method, audit process, risk/exception process, and source links.
- **Proof before acceptance:** Document review, control-ID reconciliation, no code/config/provider changes.
- **Stop condition:** Stop if the repository version differs from the approved documents, a decision appears reopened, or the change includes unrelated files.

### EN-01: Early current-test taxonomy and isolation baseline

- **Track:** WS08
- **Pass type:** Test infrastructure
- **Primary controls:** TST-001, TST-003, TST-004, TST-010, TST-011
- **Prerequisites:** GOV-01
- **Maximum scope:** Define current non-legacy suite categories, environment boundaries, synthetic-data rules, fixture cleanup, DB-name guards, provider-sandbox separation, flake handling, and artifact sanitization. Do not add broad domain coverage yet.
- **Required output:** Test taxonomy, directory/tag/config convention, fixture-safety checks, and self-tests.
- **Proof before acceptance:** Checker/self-tests demonstrate correct suite discovery, wrong-DB rejection, cleanup, and artifact sanitization.
- **Stop condition:** Stop if the harness would use production resources, count legacy tests as current evidence, or require unstable domain interfaces.

### EN-02: Early correlation, event-envelope, and redaction contract

- **Track:** WS09
- **Pass type:** Architecture contract
- **Primary controls:** API-M15, OPS-010
- **Prerequisites:** GOV-01
- **Maximum scope:** Specify request, job, payment, storage, admin-action, and release correlation fields; accepted identifier rules; safe error exposure; bounded telemetry labels; redaction and prohibited data. Limit implementation to shared primitives only if current-tree inspection supports it.
- **Required output:** Approved correlation/redaction contract and narrowly scoped shared interfaces/tests.
- **Proof before acceptance:** Unit tests for identifier validation, context separation, encoding, and redaction where implementation occurs.
- **Stop condition:** Stop if fields require unstable payment/job schemas, introduce sensitive or unbounded labels, or expand into full observability.

### EN-03: Early secrets, control-plane access, and evidence-handling foundation

- **Track:** WS10
- **Pass type:** Operational/provider foundation
- **Primary controls:** OPS-005, OPS-006, OPS-007, OPS-025
- **Prerequisites:** GOV-01
- **Maximum scope:** Create redacted inventories and procedures for provider owners, roles, MFA/recovery, secret storage/injection, rotation, revocation, offboarding, emergency access, and safe evidence handling. No secret values or provider mutations.
- **Required output:** Control-plane register, secret-lifecycle register, evidence checklist, redaction rules, and unresolved provider-access log.
- **Proof before acceptance:** Owner review; evidence templates contain no secrets or personal data.
- **Stop condition:** Stop immediately if credentials, private keys, tokens, recovery codes, personal data, or unapproved provider access would be exposed.

### WS02-01: Typed settings and environment isolation

- **Track:** WS02
- **Pass type:** Domain implementation
- **Primary controls:** GOV-002, API-M01, API-M02
- **Prerequisites:** EN-01, EN-02, EN-03
- **Maximum scope:** Inspect and then implement typed settings, environment bindings, unsafe-default rejection, import/startup behavior, and explicit local/CI/staging/production separation.
- **Required output:** Settings/config changes, current unit/config tests, environment matrix updates, and compatibility notes.
- **Proof before acceptance:** Invalid production configuration fails before readiness; no secret values enter source or artifacts.
- **Stop condition:** Stop if provider topology is unknown, configuration changes alter process/connection counts, or unrelated deployment code is required.

### WS02-02: Runtime process, lifecycle, health, and deployability

- **Track:** WS02
- **Pass type:** Deployment foundation
- **Primary controls:** API-M03, API-M17, OPS-001, OPS-002, OPS-003, OPS-004
- **Prerequisites:** WS02-01; DBP-01 policy; preliminary provider topology
- **Maximum scope:** Define runtime command, supervision, worker/instance topology, container/platform hardening, startup/readiness/liveness, graceful shutdown, release identity, rolling overlap, rollback and forward-fix behavior.
- **Required output:** Versioned deployment/runtime configuration, health contract, shutdown handling, deployment tests, and release/rollback record template.
- **Proof before acceptance:** Local or staging-safe lifecycle tests; readiness gates traffic only after dependencies are ready; shutdown releases resources.
- **Stop condition:** Stop if connection budget cannot be calculated, runtime provider is undecided, or a release change cannot be rolled back or forward-fixed.

### WS02-03: Proxy, host, TLS, CORS, and response-class security headers

- **Track:** WS02
- **Pass type:** Configuration and provider verification
- **Primary controls:** API-M04, API-M05, API-M06, API-M07, API-M08
- **Prerequisites:** WS02-01, WS02-02; FDN-02; actual edge/origin topology
- **Maximum scope:** Assign edge versus app ownership and implement trusted-proxy, canonical host, TLS redirect/HSTS, CORS, framing, content-sniffing, cache, and response-class header behavior.
- **Required output:** Edge ownership matrix, app/edge configuration, unit/integration tests, and provider-evidence checklist.
- **Proof before acceptance:** Staging header captures, redirect traces, direct-origin behavior, disallowed-origin tests, and proxy-spoof tests.
- **Stop condition:** Stop on unknown direct-origin exposure, conflicting duplicated headers, redirect loops, or provider settings that cannot be safely verified.

### WS02-04: Request limits, timeouts, rate controls, and stable errors

- **Track:** WS02
- **Pass type:** Domain implementation
- **Primary controls:** API-M09, API-M10, API-M11, API-M12
- **Prerequisites:** WS02-01, EN-02; evidence-based limit method
- **Maximum scope:** Implement bounded work before expensive operations, layered request/header/body/URL limits, timeouts/cancellation, rate controls, resource release, and privacy-safe stable error envelopes.
- **Required output:** Configuration/code, boundary tests, timeout/cancellation tests, rate-limit tests, and telemetry hooks.
- **Proof before acceptance:** Approved values have documented bases; 413/429/timeout/error behavior is repeatable and correlated.
- **Stop condition:** Stop if a numeric value lacks evidence, retries could repeat non-idempotent work, or limits conflict across edge and app.

### WS02-05: HTTP contracts, schemas, docs, cache, and end-to-end chain

- **Track:** WS02
- **Pass type:** Domain implementation and runtime verification
- **Primary controls:** API-M13, API-M14, API-M16, API-M18, API-M19
- **Prerequisites:** WS02-03, WS02-04; FDN-03
- **Maximum scope:** Separate request/response schemas, enforce methods/media types/pagination, apply docs/OpenAPI policy, protect private caching, preserve rolling compatibility, and verify the full edge-to-origin chain.
- **Required output:** API/schema changes, current API tests, OpenAPI inventory checks, cache tests, compatibility notes, and staged chain report.
- **Proof before acceptance:** Unsupported media/methods fail correctly; private data is not cacheable; old/new frontend/API compatibility is exercised.
- **Stop condition:** Stop if a breaking contract lacks a compatibility plan, frontend changes are required outside scope, or configured behavior cannot be proven at runtime.

### WS03-01: Identity authority and verifier-controlled field protection

- **Track:** WS03
- **Pass type:** Domain implementation
- **Primary controls:** IAM-001, IAM-002, IAM-003, IAM-004, IAM-006, IAM-007, IAM-014
- **Prerequisites:** WS02-01, WS02-05; IDB-01, IDB-02, IDB-03
- **Maximum scope:** Implement the Firebase/PostgreSQL authority matrix, token/local-user checks, verified-email gates, safe retry/persistence assumptions, and removal of ordinary-user write access to verifier/admin-controlled fields.
- **Required output:** Schemas/services/dependencies, field-write restrictions, route policy matrix, and current negative tests.
- **Proof before acceptance:** Revoked/disabled/unverified/stale/user-written verifier scenarios are denied as designed.
- **Stop condition:** Stop if a field has two authorities, provider state is unavailable without a fail-safe rule, or changes require broad account-lifecycle redesign.

### WS03-02: Provisioning, account-state lifecycle, and concurrent first login

- **Track:** WS03
- **Pass type:** Schema, migration, and domain implementation
- **Primary controls:** IAM-005, IAM-009, IAM-018
- **Prerequisites:** WS03-01; WS04-01 and WS04-02 design inputs
- **Maximum scope:** Make first login, account linking, recovery, suspension, disablement, deletion, and cross-instance state changes conflict-safe while preserving stable identifiers.
- **Required output:** Narrow schema/migration if required, services, deterministic PostgreSQL concurrency tests, and lifecycle documentation.
- **Proof before acceptance:** Concurrent first login creates one user; open sessions and routes respond to state changes as designed.
- **Stop condition:** Stop on ambiguous merge/link behavior, destructive identity migration, or missing provider revocation/recovery evidence.

### WS03-03: High-risk authentication and Firebase control verification

- **Track:** WS03
- **Pass type:** Provider/security implementation
- **Primary controls:** IAM-008, IAM-010, IAM-011
- **Prerequisites:** WS03-01; EN-03; IDB-04
- **Maximum scope:** Define and implement recent-authentication/step-up requirements for high-risk actions, stage App Check, and verify service-account/workload identity scope, revocation, and emergency procedures.
- **Required output:** High-risk action matrix, enforcement code/tests, staged App Check evidence, and redacted Firebase/GCP evidence.
- **Proof before acceptance:** Missing/stale step-up is denied; App Check valid/missing/invalid/provider-unavailable cases are tested; credentials remain least privilege.
- **Stop condition:** Stop if production enforcement risks locking out valid users, provider tier/capability is unknown, or long-lived credentials cannot be safely governed.

### WS03-04: Complete authorization matrix and negative proof

- **Track:** WS03
- **Pass type:** Domain implementation and current tests
- **Primary controls:** IAM-012, IAM-013, IAM-015, IAM-016, IAM-017
- **Prerequisites:** WS03-01, WS03-02; stable resource and state models
- **Maximum scope:** Inventory every protected route/action and enforce object, relationship, workflow-state, list/query, field, function, role, and concealment boundaries.
- **Required output:** Authorization matrix, narrowly required code corrections, exhaustive current negative tests, and uncovered-gap register.
- **Proof before acceptance:** Cross-user, cross-role, stale-state, mass-assignment, list/search/export, and 401/403/404 substitutions are tested.
- **Stop condition:** Stop if resource policy is undefined, a route family cannot be inventoried, or frontend route guards are being used as backend authorization.

### WS03-05: Moderation states, safe notices, and minimum-necessary admin data

- **Track:** WS03
- **Pass type:** Schema/domain/privacy implementation
- **Primary controls:** ADM-007, ADM-009, ADM-010, ADM-012, ADM-013, ADM-014, ADM-015
- **Prerequisites:** WS03-04; WS04-02; WS05 durable notice path design; OPP-03; WS09-02 audit contract
- **Maximum scope:** Stabilize moderation taxonomy/evidence/review/enforcement states; implement safe notice rules; replace default full-sensitive-data exposure with excerpt-first, controlled unmask, anti-cache, and read auditing.
- **Required output:** Models/migration if required, services/APIs/admin UI contracts, notice policy implementation, and current authorization/privacy tests.
- **Proof before acceptance:** Stale evidence, conflicting actions, suppressed notices, unmask, sensitive reads, and denied exports are covered.
- **Stop condition:** Stop if full private content remains the default, audit atomicity is unresolved, or enforcement requires an undefined durable workflow.

### WS04-01: Database engine/session lifecycle, connection budget, and least-privilege roles

- **Track:** WS04
- **Pass type:** Database foundation
- **Primary controls:** DB-001, DB-002, DB-003, DB-012, DB-013, DB-015
- **Prerequisites:** WS02-02; DBP-01; actual PostgreSQL provider/topology
- **Maximum scope:** Inspect and define engine/session lifecycle, transaction defaults, deployment-wide pool/overflow/wait budget, worker/migration reserve, provider roles/grants, and operational access.
- **Required output:** Configuration/code, connection-budget record, role/grant plan, current PostgreSQL tests, and provider-evidence checklist.
- **Proof before acceptance:** Multi-process maximum stays within provider budget; waits/timeouts are bounded; application/migration/support roles are least privilege.
- **Stop condition:** Stop if provider limits or process counts are unknown, routine superuser access is required, or pool changes precede topology evidence.

### WS04-02: Transactions, invariants, locks, and deterministic concurrency

- **Track:** WS04
- **Pass type:** Database/domain/concurrency
- **Primary controls:** DB-004, DB-005, DB-006, DB-007, DB-008, DB-009, DB-010, DB-014
- **Prerequisites:** WS04-01; approved identity/payment/job/storage invariant inputs
- **Maximum scope:** Define transaction and external-side-effect boundaries; add database constraints or deliberate serialization; handle duplicate, winner/loser, retry, deadlock, timeout, and unknown-outcome cases.
- **Required output:** Narrow models/constraints/services, deterministic independent-session tests, and invariant catalog.
- **Proof before acceptance:** Barrier-driven concurrency tests assert final database and external-intent states, cleanup, and retry behavior.
- **Stop condition:** Stop on nondeterministic tests, ambiguous source of truth, external calls inside unsafe transactions, or a required destructive constraint/backfill without migration design.

### WS04-03: Migration policy, compatibility, interruption, and production-like rehearsal

- **Track:** WS04
- **Pass type:** Schema and migration
- **Primary controls:** DB-016, DB-017, DB-018
- **Prerequisites:** WS04-01, WS04-02; stable required schema capabilities
- **Maximum scope:** Establish expand-and-contract rules, graph/drift checks, empty/prior-schema upgrades, online-index strategy, timeouts, interruption/resume, old/new compatibility, rollback versus forward-fix, and production-like rehearsal.
- **Required output:** Migration changes and tests, compatibility window, rehearsal plan/results, and forward-fix notes.
- **Proof before acceptance:** Empty and prior-schema upgrades pass; lock/duration/interruption behavior is measured on representative volume.
- **Stop condition:** Stop on blocking/destructive behavior without approval, downgrade assumptions that risk data, or inability to keep old/new versions compatible.

### WS05-01: Durable job model, claim/lease lifecycle, and worker deployment

- **Track:** WS05
- **Pass type:** Schema, worker, and deployment
- **Primary controls:** JOB-M01, JOB-M02, JOB-M03, JOB-M04, JOB-M05, JOB-M06, JOB-M07, JOB-M08
- **Prerequisites:** WS02-02; WS04-01 through WS04-03; EN-02
- **Maximum scope:** Implement durable job state, transactional handoff/outbox where required, claim/lease/heartbeat, bounded retry, crash recovery, exhaustion/dead-letter/repair, version compatibility, graceful shutdown, worker command, and job observability.
- **Required output:** Models/migration, worker/service implementation, operator interfaces, deployment config, current tests, and runbook draft.
- **Proof before acceptance:** Crash/restart, stale lease, duplicate delivery, multi-worker claim, unsupported version, shutdown, and backlog behavior are deterministic.
- **Stop condition:** Stop if jobs can be lost between transaction and enqueue, ownership is ambiguous, or worker deployment/monitoring cannot be defined.

### WS05-02: Payment and booking state machines with webhook authority

- **Track:** WS05
- **Pass type:** Financial domain implementation
- **Primary controls:** PAY-001, PAY-002, PAY-003, PAY-004, PAY-005, PAY-006, PAY-007, PAY-008
- **Prerequisites:** WS05-01; WS04-02; DBP-02; WS03-04
- **Maximum scope:** Implement separate coordinated payment, booking, reservation, capacity-conflict, and compensation states; trusted amount calculation; PaymentIntent lifecycle; signed webhook ingestion and idempotent transition rules.
- **Required output:** Models/migration if required, services/routes/webhook handlers, transition catalog, current API/PostgreSQL tests, and frontend contract notes.
- **Proof before acceptance:** Duplicate/out-of-order/delayed webhooks, browser abandonment, requires-action/processing/failure/success, capacity conflict, and server authority are verified.
- **Stop condition:** Stop if frontend callback is treated as final authority, money and booking use one ambiguous status, or transition/compensation rules are incomplete.

### WS05-03: Refunds, credits, notices, moderation delivery, and reconciliation

- **Track:** WS05
- **Pass type:** Durable financial/notification workflows
- **Primary controls:** ADM-011, ADM-016, PAY-009, PAY-010, PAY-011, PAY-012, PAY-013
- **Prerequisites:** WS05-01, WS05-02; WS03-05
- **Maximum scope:** Apply durable jobs to refunds, credits, administrative notices, moderation delivery, provider synchronization, mismatch classification, repair controls, and recurring reconciliation.
- **Required output:** Durable workflows, schemas/migrations if needed, operator procedures, reconciliation reports, and current tests.
- **Proof before acceptance:** Duplicate requests, provider timeout/unknown outcome, partial failure, retry, capacity compensation, and repair are idempotent and auditable.
- **Stop condition:** Stop if a financial repair can double-spend/credit/refund, provider truth is overwritten, or manual repair lacks guardrails and audit.

### WS05-04: Deterministic failure, replay, sandbox, and deployed-worker verification

- **Track:** WS05
- **Pass type:** Concurrency/failure/provider/runtime verification
- **Primary controls:** ADM-011, ADM-016, PAY-001, PAY-002, PAY-003, PAY-004, PAY-005, PAY-006, PAY-007, PAY-008, PAY-009, PAY-010, PAY-011, PAY-012, PAY-013, JOB-M01, JOB-M02, JOB-M03, JOB-M04, JOB-M05, JOB-M06, JOB-M07, JOB-M08
- **Prerequisites:** WS05-01 through WS05-03; Stripe sandbox; staging worker
- **Maximum scope:** Run the focused race/replay/crash/timeout/unknown-outcome families and collect Stripe sandbox, worker deployment, reconciliation, and operator evidence. Correct only narrowly proven defects.
- **Required output:** Sanitized test and runtime evidence package, defect log, follow-up passes, and workstream closure assessment.
- **Proof before acceptance:** Repeated deterministic results, final-state verification, no production data/credentials, and provider/environment attribution.
- **Stop condition:** Stop on nondeterminism, unbounded financial impact, unsafe provider mode, missing rollback/repair path, or secrets in evidence.

### WS06-01: Admin-only venue-image authority and upload initiation

- **Track:** WS06
- **Pass type:** Storage domain implementation
- **Primary controls:** STO-001, STO-002, STO-003
- **Prerequisites:** WS02 foundation; WS03 active-admin gate; DBP-03
- **Maximum scope:** Remove or deny all player/community-host image upload paths, preserve initials-only avatars, enforce active-admin venue-image authority, bind upload intent to venue/admin/file constraints, and prevent arbitrary URLs/keys.
- **Required output:** Routes/services/frontend admin contract, authorization tests, upload-intent records if required, and product-scope documentation.
- **Proof before acceptance:** Player/host/cross-venue/expired/replayed upload attempts are denied; only approved admin workflow can initiate.
- **Stop condition:** Stop if user uploads remain reachable, client claims control object identity/type, or admin authorization relies only on frontend UI.

### WS06-02: Venue-image validation, sanitization, re-encoding, and derivatives

- **Track:** WS06
- **Pass type:** Storage processing implementation
- **Primary controls:** STO-004, STO-005, STO-006, STO-007
- **Prerequisites:** WS06-01; WS05-01 durable jobs if asynchronous; evidence-based file limits
- **Maximum scope:** Treat admin files as untrusted; verify bytes, size/pixel/decompression limits, isolate processing, strip metadata, re-encode approved formats, create idempotent sanitized masters/derivatives, and publish only after success.
- **Required output:** Processing code/job, explicit states, tests with malformed/bomb/metadata cases, and safe failure behavior.
- **Proof before acceptance:** Invalid/corrupt/oversized/mismatched files are rejected; metadata is removed; repeated processing does not duplicate assets.
- **Stop condition:** Stop if raw uploads become public, processing resource bounds are unproven, or original retention is undefined.

### WS06-03: R2 lifecycle, deletion, cache behavior, reconciliation, and recovery

- **Track:** WS06
- **Pass type:** Storage lifecycle/provider/runtime
- **Primary controls:** STO-008, STO-009
- **Prerequisites:** WS06-01, WS06-02; DBP-04; OPP-05; WS05-01
- **Maximum scope:** Implement replacement/deletion state, public removal, temporary-original cleanup, abandoned-upload sweep, missing/orphan/divergence reconciliation, safe repair, default-image fallback, usage monitoring, token/CORS/public-access controls, and cache invalidation/expiry strategy.
- **Required output:** Lifecycle/reconciliation jobs, admin repair paths, tests, R2 evidence, and recovery documentation.
- **Proof before acceptance:** Missing object, orphan object, failed deletion, cache stale copy, abandoned upload, and derivative regeneration scenarios are verified.
- **Stop condition:** Stop if automatic deletion is not safely bounded, provider token scope/public access is unknown, or database/object authority is ambiguous.

### WS07-01: Production frontend build, public configuration, artifact identity, and source maps

- **Track:** WS07
- **Pass type:** Frontend/build/release
- **Primary controls:** FE-M01, FE-M02
- **Prerequisites:** WS02-02, WS02-05; FDN-06; OPP-02
- **Maximum scope:** Define production build inputs, public environment variables, artifact/release identity, dependency output, and private source-map handling.
- **Required output:** Build configuration/checks, bundle/public-variable scan, release linkage, unit tests, and documentation.
- **Proof before acceptance:** Production artifact contains only approved public values; source maps are not publicly accessible and are release-linked.
- **Stop condition:** Stop if secrets exist in frontend inputs, artifact identity cannot be preserved, or hosting behavior is unknown.

### WS07-02: Authentication persistence, identity-scoped state, logout, switch, and safe retries

- **Track:** WS07
- **Pass type:** Frontend/browser
- **Primary controls:** FE-M05, FE-M06, FE-M10
- **Prerequisites:** WS03-01 through WS03-03; IDB-01
- **Maximum scope:** Make Firebase persistence explicit; clear profile, booking, chat, notification, admin, query, local/session/IndexedDB state on logout/switch/state change; bound token/read retries; prohibit blind mutation replay.
- **Required output:** Frontend state contract, code, unit tests, Playwright identity-switch tests, and storage inventory.
- **Proof before acceptance:** No prior-user data appears after logout/switch/suspension/deletion/role change; sensitive mutations are not replayed.
- **Stop condition:** Stop if backend session/authorization behavior is unclear, global keys persist user data, or a generic retry interceptor affects mutations.

### WS07-03: Routes, API errors, forms, URLs, browser storage, and resilient UI state

- **Track:** WS07
- **Pass type:** Frontend/browser
- **Primary controls:** FE-M03, FE-M04, FE-M07, FE-M11
- **Prerequisites:** WS02-04, WS02-05; stable backend authorization/error contracts
- **Maximum scope:** Harden route transitions, deep links, history, error boundaries, forms/status messages, URL/query handling, storage use, loading/empty/failure states, and safe API response handling.
- **Required output:** Frontend changes, unit tests, focused Playwright scenarios, and route/error inventory.
- **Proof before acceptance:** Malformed/expired/deep-link/offline/provider/error states remain understandable and do not expose private data.
- **Stop condition:** Stop if a UI workaround masks a backend contract/authorization defect or the pass requires redesigning unrelated pages.

### WS07-04: Third-party browser code, CSP/SRI posture, headers, and provider failure isolation

- **Track:** WS07
- **Pass type:** Frontend security/provider
- **Primary controls:** FE-M08, FE-M09
- **Prerequisites:** WS02-03; IDB-05; actual Firebase/Stripe/browser dependency inventory
- **Maximum scope:** Inventory approved browser code/domains/data, enforce CSP and related browser controls, use SRI where compatible, minimize third-party data sharing, and isolate provider failure.
- **Required output:** Inventory, CSP/header configuration, frontend failure handling, tests, and staged browser evidence.
- **Proof before acceptance:** Unapproved domains/scripts are blocked; Firebase/Stripe failure does not expose secrets, corrupt state, or duplicate payment actions.
- **Stop condition:** Stop if CSP requires unsafe broad allowances without justification, third-party data flows are unknown, or provider scripts become single points of failure.

### WS07-05: WCAG 2.2 AA, browser support, and performance verification

- **Track:** WS07
- **Pass type:** Frontend/accessibility/performance
- **Primary controls:** FE-M12, FE-M13
- **Prerequisites:** WS07-01 through WS07-04; EN-01; OPP-01, OPP-02
- **Maximum scope:** Apply and verify keyboard/focus/dialog/form/status/contrast/reflow/zoom/reduced-motion/screen-reader behavior, supported modern browser/device matrix, production-build performance, bundle/image behavior, and governed exceptions.
- **Required output:** Code corrections, automated tests, manual audit record, browser matrix results, performance baseline/budgets, and exceptions.
- **Proof before acceptance:** Critical end-to-end processes pass defined accessibility/browser checks; performance values come from realistic measurements.
- **Stop condition:** Stop if only automated accessibility evidence exists, exact budgets are invented, or browser tests use development builds.

### WS08-01: Complete current-test inventory, fixtures, and control mapping

- **Track:** WS08
- **Pass type:** Test infrastructure
- **Primary controls:** TST-001, TST-002, TST-003, TST-004, TST-010, TST-011
- **Prerequisites:** EN-01; stable outputs from WS02 through WS07
- **Maximum scope:** Finalize suite discovery/classification, synthetic fixtures, isolated PostgreSQL/browser/provider environments, cleanup, auth-state generation, artifact policy, and control-to-evidence mapping.
- **Required output:** Current-suite inventory, checker updates, fixture documentation, gap list, and self-tests.
- **Proof before acceptance:** No legacy test is counted; every suite declares environment/data/cleanup; missing required suites fail the checker.
- **Stop condition:** Stop if fixtures share production resources, test ordering is required, or classification overstates provider/full-stack coverage.

### WS08-02: Critical workflow, deterministic concurrency, migration, provider, privacy, and recovery suites

- **Track:** WS08
- **Pass type:** Current tests
- **Primary controls:** TST-005, TST-006, TST-007, TST-008, TST-009
- **Prerequisites:** WS08-01; stable domain implementations; sandbox/restore environments
- **Maximum scope:** Complete risk-based current coverage for auth/admin, payments/jobs, venue storage, database races, migrations, provider boundaries, privacy workflows, and restore verification.
- **Required output:** Layered unit/service/API/PostgreSQL/browser/provider/migration/failure suites and evidence mapping.
- **Proof before acceptance:** Critical races use barriers/independent sessions; provider tests are sandboxed; migration/restore tests use controlled fixtures.
- **Stop condition:** Stop on nondeterminism, production provider use, giant unowned end-to-end tests, or unverified cleanup.

### WS08-03: Reproducible CI, scans, branch protection, SBOM, provenance, and release evidence

- **Track:** WS08
- **Pass type:** CI/supply chain/provider
- **Primary controls:** TST-012, TST-013, TST-014, TST-015, TST-016, TST-017
- **Prerequisites:** WS08-01, WS08-02; stable job names and release artifacts; EN-03
- **Maximum scope:** Pin tools/dependencies, validate clean installs, gate suites/build/migrations/security scans, protect secrets/forks, create aggregate required check, generate sanitized artifacts/SBOM/provenance, and verify GitHub branch rules/deployment linkage.
- **Required output:** CI workflows/checkers, scan policy, artifact/release manifest, redacted branch-protection evidence, and sample release package.
- **Proof before acceptance:** Actual CI run records; skipped/failed/canceled/provider-unavailable behavior is explicit; required checks cannot be bypassed silently.
- **Stop condition:** Stop if CI needs production credentials, gates can be skipped without visibility, artifacts leak data, or release identity cannot be tied to source/deployment.

### WS09-01: Structured request/event logging, correlation, redaction, and log aggregation

- **Track:** WS09
- **Pass type:** Observability implementation
- **Primary controls:** API-M15, OPS-008, OPS-010
- **Prerequisites:** EN-02; stable release/environment context and event models
- **Maximum scope:** Implement bounded request/job/payment/storage/admin/release context, structured logging, route templates, error categories, redaction, access/retention hooks, central aggregation, and log-loss detection.
- **Required output:** Shared logging/correlation code, tests, provider configuration/evidence, and log-field catalog.
- **Proof before acceptance:** Concurrent context isolation; injection-safe encoding; no tokens/private messages/card data/full signed URLs; samples from every component.
- **Stop condition:** Stop if high-cardinality or sensitive fields are required, central provider access is unsafe, or logs cannot be tied to environment/release.

### WS09-02: Append-only administrative audit trail and sensitive-access controls

- **Track:** WS09
- **Pass type:** Database/domain/privacy
- **Primary controls:** ADM-001, ADM-002, ADM-003, ADM-004, ADM-005, ADM-006
- **Prerequisites:** WS03-04, WS03-05; WS04-02; OPP-11
- **Maximum scope:** Implement required audit event catalog, atomic or durable recording, before/after-safe fields, outcomes, denial/conflict/provider failure, append-only permissions, restricted lookup, sensitive-read/unmask/export auditing, and correction records.
- **Required output:** Schema/migration, services, admin access contract, PostgreSQL tests, and audit policy linkage.
- **Proof before acceptance:** Normal update/delete is denied; audit write failure behavior is explicit; duplicate/concurrent privileged actions remain attributable.
- **Stop condition:** Stop if audit contains excessive sensitive content, privileged actions can succeed without designed audit behavior, or normal admins can alter history.

### WS09-03: Metrics, service objectives, dashboards, alerts, capacity, and cost evidence

- **Track:** WS09
- **Pass type:** Observability/operations
- **Primary controls:** OPS-009, OPS-011, OPS-012, OPS-016
- **Prerequisites:** WS09-01, WS09-02; stable WS02-WS06 workflows; OPP-09, OPP-10
- **Maximum scope:** Define measured indicators and evidence-based targets for availability, latency, correctness, payments, job delay, data freshness, provider/storage/database limits, cost, and launch blockers; implement dashboards/alerts and synthetic delivery tests.
- **Required output:** Metric catalog, SLI/SLO record, dashboards, alert/runbook links, capacity/cost model, load tests, and delivery evidence.
- **Proof before acceptance:** Alerts are symptom/outcome based, bounded, delivered and acknowledged; load warns before provider limits; exact values have evidence.
- **Stop condition:** Stop if targets are invented, labels are unbounded, alert routing has no owner, or capacity tests risk production.

### WS10-01: Data classification, table lifecycle, retention, privacy, and audit lifecycle

- **Track:** WS10
- **Pass type:** Privacy/retention/schema
- **Primary controls:** GOV-003, ADM-008, DB-011, OPS-022, OPS-023, OPS-024
- **Prerequisites:** Stable data models from WS03-WS06; OPP-07, OPP-08, OPP-11
- **Maximum scope:** Create data inventory/classification and table/provider-copy lifecycle matrix; implement approved hard delete/anonymize/restricted/soft-delete behavior, export/correction/deletion workflows, durable retries, backup treatment, legal holds, and restore-time deletion reapplication.
- **Required output:** Policies/matrices, narrow migrations/jobs/APIs, synthetic privacy tests, audit evidence, and exception process.
- **Proof before acceptance:** Cross-user denial, partial provider failure, replay, concurrent use/deletion, restored-deleted-user, export protection, and legal-hold scoping are verified.
- **Stop condition:** Stop on unreviewed destructive changes, invented legal periods, incomplete provider-copy inventory, or inability to reapply deletion after restore.

### WS10-02: Secrets, provider control-plane access, MFA, rotation, revocation, and offboarding

- **Track:** WS10
- **Pass type:** Operational/provider
- **Primary controls:** OPS-005, OPS-006, OPS-007, OPS-025
- **Prerequisites:** EN-03; actual provider accounts and hosting topology
- **Maximum scope:** Finalize least-privilege users/roles/service identities, MFA/recovery ownership, managed secret injection, rotation overlap, revocation, break-glass, offboarding, monitoring, and dated redacted evidence across hosting, Firebase/GCP, Stripe, R2, PostgreSQL, DNS, GitHub, monitoring, and backups.
- **Required output:** Completed inventories, procedures, redacted evidence packages, discrepancies, and exercises.
- **Proof before acceptance:** Access review and rotation/revocation/offboarding/lost-factor exercises succeed without exposing secrets.
- **Stop condition:** Stop on missing recovery owner, shared/unattributed privileged access, long-lived unmanaged credentials, or unsafe evidence.

### WS10-03: Incident response, provider-outage handling, and operational runbooks

- **Track:** WS10
- **Pass type:** Operational process/exercise
- **Primary controls:** OPS-013, OPS-014, OPS-015
- **Prerequisites:** WS09-03; stable deployed architecture; named owners
- **Maximum scope:** Define severity, roles, containment, evidence, reconciliation, communication, post-incident actions, and runbooks for API/DB/connection exhaustion/release/migration/jobs/Stripe/R2/Firebase/secrets/certificates/backups/control planes.
- **Required output:** Incident plan, provider-outage matrix, service runbooks, communication templates, and tabletop results.
- **Proof before acceptance:** Tabletops expose alert, access, decision, communication, reconciliation, and recovery gaps; actions have owners/retests.
- **Stop condition:** Stop if runbooks do not match deployed architecture, emergency steps bypass financial/data safeguards, or on-call/decision authority is undefined.

### WS10-04: Backup/PITR evidence, isolated restore, recovery validation, and exercises

- **Track:** WS10
- **Pass type:** Recovery/provider/runtime
- **Primary controls:** OPS-017, OPS-018, OPS-019, OPS-020, OPS-021
- **Prerequisites:** WS10-01 through WS10-03; stable application release; WS09 observability; OPP-04, OPP-05, OPP-06
- **Maximum scope:** Verify provider backup/PITR/encryption/access/monitoring; restore into isolation; validate integrity/startup/Firebase mappings/roles/bookings/Stripe/R2/jobs/migrations/deletion replay; execute required technical and tabletop recovery scenarios.
- **Required output:** Redacted provider evidence, measured restore report, reconciliation results, exercise reports, defects, owners, and retest plan.
- **Proof before acceptance:** Backups are actually readable; restored system passes critical checks; deleted/anonymized data does not silently return; job/payment replay is controlled.
- **Stop condition:** Stop if isolation, credentials, synthetic data, recovery objectives, version compatibility, or safe abort/cleanup are not proven.

### CLOSE-01: Cross-workstream evidence completeness and discrepancy sweep

- **Track:** PROGRAM
- **Pass type:** Audit preparation
- **Primary controls:** Program gate; no primary control reassessment
- **Prerequisites:** All workstream exit gates
- **Maximum scope:** Reconcile repository changes, current tests, CI, provider evidence, runtime observations, migration/concurrency rehearsals, operational records, and exercises against every control and identify remaining gaps without changing locked findings.
- **Required output:** Complete evidence index, missing/contradictory evidence log, exception candidates, and required correction passes.
- **Proof before acceptance:** Every evidence item is dated, environment-attributed, redacted, and linked to exact controls; every control has an assessor-ready record.
- **Stop condition:** Stop if evidence is stale, unattributed, secret-bearing, contradictory, or based only on configuration intent.

### CLOSE-02: Fresh 163-control reassessment and production-readiness decision

- **Track:** PROGRAM
- **Pass type:** Independent reassessment
- **Primary controls:** Program gate; no primary control reassessment
- **Prerequisites:** CLOSE-01; all correction/retest passes complete
- **Maximum scope:** Reassess all 163 controls from current repository, runtime, provider, operational, and exercise evidence. Do not carry forward old statuses or infer closure from implementation alone.
- **Required output:** New control-by-control assessment, P0/P1/P2 disposition, approved time-bound exceptions if any, and explicit sign-off or no-sign-off decision.
- **Proof before acceptance:** Independent reconciliation finds no missing/duplicate controls; every applicable P0 is closed or formally resolved under policy.
- **Stop condition:** No sign-off if any applicable P0 lacks required evidence, an exception is informal/open-ended, or production behavior remains unverified.

## 10. Control-coverage validation

The planned pass decomposition was mechanically checked against the finalized workstream register.

| Workstream | Expected primary controls | Covered by planned passes | Missing | Unexpected |
|---|---:|---:|---|---|
| WS01 | 5 | 5 | None | None |
| WS02 | 23 | 23 | None | None |
| WS03 | 25 | 25 | None | None |
| WS04 | 17 | 17 | None | None |
| WS05 | 23 | 23 | None | None |
| WS06 | 9 | 9 | None | None |
| WS07 | 13 | 13 | None | None |
| WS08 | 17 | 17 | None | None |
| WS09 | 13 | 13 | None | None |
| WS10 | 18 | 18 | None | None |

**Validation result:** PASS. Every primary control assigned to WS01 through WS10 appears in at least one planned pass for its owning workstream, with no unexpected primary control assigned to the wrong workstream.

This does not close any control. It only verifies blueprint coverage.

## 11. Mandatory lifecycle for every implementation pass

### Step 1: Entry-gate check

Confirm dependencies, approved decisions, clean Git state, provider access, test environment, rollback/abort criteria, and exact control IDs.

### Step 2: Read-only repository inspection

Inspect only the narrow subsystem. Produce:

- current files and behavior
- stale audit assumptions, if any
- proposed allowed files
- prohibited files and unrelated areas
- schema/migration impact
- exact tests and evidence
- unresolved blockers

No edits occur during inspection.

### Step 3: Pass-specific Codex prompt

The assistant prepares the prompt only after reviewing the inspection. The prompt must include:

1. pass ID and workstream
2. exact audit control IDs
3. objective and approved decision inputs
4. current-tree findings
5. allowed files or subsystem
6. explicitly prohibited scope
7. required implementation behavior
8. required current tests
9. database and migration implications
10. provider/runtime evidence that is not part of Codex's repository task
11. required output format
12. stop conditions

### Step 4: Codex execution

Codex performs only the approved pass. It must stop rather than guess when it discovers:

- an unmade or conflicting decision
- a required file outside allowed scope
- a destructive migration not covered by the pass
- a production credential or personal-data requirement
- an ambiguous source of truth
- a need to redesign another workstream

### Step 5: Actual review

Review the actual diff and relevant full files, not only Codex's summary. Verify:

- scope discipline
- correctness against approved decisions
- security and privacy boundaries
- migrations and compatibility
- current non-legacy tests
- failure and concurrency behavior
- documentation and evidence updates
- no unrelated cleanup

### Step 6: Accept, correct, or reject

- **Accept:** all entry, implementation, test, and evidence requirements pass.
- **Correct:** issue a narrowly scoped correction prompt for the same pass.
- **Reject:** revert the pass or discard the branch when its approach is unsafe or outside the blueprint.

### Step 7: Commit and evidence

Commit the accepted pass independently and update the pass record with:

- source commit
- changed files
- tests executed and results
- migration head where applicable
- provider/runtime evidence still outstanding
- known limitations
- rollback or forward-fix instructions
- control status remains unresolved until formal reassessment

## 12. Commit, merge, and rollback protocol

### Repository changes

- One coherent pass per commit or pull request.
- No unrelated formatting, renaming, dependency upgrade, or refactor.
- Commit messages begin with the pass ID.
- A failed or partially accepted pass is not stacked under later work.

### Database migrations

- Prefer expand-and-contract and forward-fix compatibility.
- Do not depend on destructive downgrade scripts as the primary recovery strategy.
- Backfills require batching, interruption, resume, and evidence appropriate to volume.
- A migration does not merge until empty-schema, prior-schema, compatibility, and rehearsal requirements for that pass are satisfied.

### Provider changes

- Separate repository implementation from provider mutation and provider evidence.
- Record prior setting, intended setting, owner, environment, validation, and reversal procedure.
- Never place secrets or unrestricted provider screenshots in the repository.

### Rollback hierarchy

1. Revert an isolated repository pass when it has no irreversible data/provider effect.
2. Use a planned forward-fix for schema changes where downgrade risks data.
3. Restore the prior immutable deployment artifact when deployment compatibility permits.
4. Use controlled provider rollback only with an owner, evidence, and verification.
5. Trigger incident/recovery procedures when state is uncertain.

## 13. Evidence protocol

A control may require several evidence classes. A code change or test alone cannot substitute for provider, runtime, operational, or recovery proof.

Every evidence record must include:

- control IDs
- environment
- source revision or release identity
- date and reviewer
- exact scenario or setting
- redaction status
- observed result
- unresolved discrepancy
- follow-up owner

Evidence must never contain raw tokens, passwords, private keys, recovery codes, unrestricted signed URLs, card data, private-message bodies, or unnecessary personal information.

## 14. Global stop conditions

Stop the program or current pass when any of these occurs:

1. `main` is not the trusted intended baseline.
2. The working tree contains unrelated or unexplained changes.
3. The pass requires an unapproved architecture or product decision.
4. Current repository behavior contradicts the locked audit and the conflict has not been reviewed.
5. Scope expands beyond the named controls or subsystem.
6. A migration may be destructive, blocking, or incompatible without an approved strategy.
7. A test is nondeterministic or depends on execution order.
8. A provider test would touch production data, credentials, payments, users, or objects.
9. A retry could duplicate a non-idempotent mutation.
10. A financial, booking, job, or object workflow has an ambiguous source of truth or unknown final state without repair logic.
11. Sensitive information would enter source, logs, metrics, artifacts, screenshots, or evidence.
12. Rollback, forward-fix, abort, or cleanup is unavailable.
13. Required tests fail or were not executed.
14. Codex reports success but the actual diff or files cannot be reviewed.
15. A later pass is being used to hide an unresolved earlier-pass defect.

## 15. Final closure sequence

1. Complete controlled repository, database, migration, configuration, and operational-document passes.
2. Execute applicable current non-legacy unit, service, API, PostgreSQL, concurrency, browser, provider, migration, failure, privacy, and recovery tests.
3. Enforce reproducible CI, scans, required checks, artifacts, and supply-chain gates.
4. Collect redacted provider and repository-protection evidence.
5. Perform staged runtime verification.
6. Rehearse migrations and deterministic concurrency.
7. Prove backup/PITR access and isolated restore.
8. Complete incident and recovery exercises.
9. Reassess all 163 controls from fresh evidence.
10. Issue production-readiness sign-off only when every applicable P0 is closed or governed by an approved time-bound exception and all launch conditions are satisfied.

## 16. Immediate execution point

While the user finishes the old-work merge, this blueprint is the active planning artifact.

After the user confirms the merge is complete:

1. Run `BASE-00` only.
2. Review the read-only Git baseline.
3. Approve the exact remediation branch/worktree setup.
4. Run `GOV-01` to place the already approved governance package into the isolated remediation branch.
5. Do not begin WS02 code before `EN-01`, `EN-02`, and `EN-03` satisfy their entry gates.

No previously generated WS02 prompt is valid under this blueprint.