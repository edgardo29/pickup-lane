# Pickup Lane Production-Readiness Blueprint

**Status:** Corrected master production-readiness authority
**Scope:** Existing-product production hardening, necessary internal infrastructure, and explicitly approved product exceptions only
**Implementation authorization:** None by itself. This document defines scope, sequencing, and completion requirements. Destructive database, provider, credential, deployment, production-data, or irreversible operations still require explicit execution authority.

---

## 1. Mission

Pickup Lane was already substantially built before the production-readiness program began.

The purpose of this program is to make the existing application safe for real production use. It is not a product-development roadmap and is not an enterprise-platform program.

Production readiness means making Pickup Lane:

- secure;
- correct;
- reliable;
- concurrency-safe;
- privacy-safe;
- scalable to its expected workload;
- observable;
- maintainable;
- deployable;
- recoverable;
- operationally safe.

New internal machinery is allowed only when it is genuinely required to make existing functionality production-safe.

New user or administrator functionality is not a production-readiness requirement merely because it is useful, convenient, sophisticated, or common in larger systems.

---

## 2. Governing scope rule

Every current or future production-readiness change must satisfy one of these two conditions:

1. it directly hardens existing Pickup Lane behavior; or
2. it is necessary internal infrastructure for that hardening.

A third category may exist only when the owner explicitly chooses to keep a product capability that is not required for production readiness.

The corrected program therefore uses this practical rule:

- **NEED**: required for responsible production operation of Pickup Lane as actually designed.
- **DO NOT NEED**: not required for production readiness and must not remain a launch blocker.

A mechanism does not become necessary merely because it already exists, appears in an old audit, appears in an old plan, has tests, or has supporting infrastructure.

---

## 3. Explicit boundaries

### 3.1 Production-readiness work may include

- authentication and authorization hardening;
- server-side ownership and permission enforcement;
- mass-assignment prevention;
- request, input, body, upload, query, pagination and resource bounds;
- abuse and rate controls;
- safe errors;
- privacy and sensitive-data protection;
- database transactions, constraints and concurrency controls;
- idempotency and duplicate-delivery handling;
- safe provider retry and unknown-outcome recovery;
- payment reconciliation;
- durable work where accepted work must survive request or process failure;
- upload validation, sanitization and object-storage lifecycle;
- secure frontend and runtime configuration;
- logging, metrics and actionable alerting;
- administrative auditability;
- secrets and provider-access hardening;
- deployment and migration safety;
- capacity safeguards;
- backups and tested recovery;
- targeted testing and CI safeguards;
- correctness repairs in existing workflows.

### 3.2 Production readiness does not automatically justify

- new user workflows;
- new administrator workflows;
- convenience-only lifecycle states;
- broad administrator workspaces;
- speculative future-product support;
- duplicate state machines;
- duplicate policy registries;
- generalized repair platforms;
- generalized evidence/compliance systems;
- custom test-management platforms;
- custom AI-agent orchestration systems;
- formal enterprise SRE or incident bureaucracy;
- microservices;
- Kafka or another queue;
- event sourcing;
- sharding;
- service meshes;
- custom identity systems;
- custom IAM systems;
- custom compliance platforms.

---

## 4. Minimum-sufficient architecture

Pickup Lane should remain a straightforward PostgreSQL-centered web application unless measured evidence later proves a specific limitation.

The intended production shape is:

- React/Vite frontend;
- FastAPI backend;
- PostgreSQL as transactional source of truth;
- Firebase Authentication as identity provider;
- Stripe as processor-side payment authority;
- PostgreSQL-backed durable jobs for asynchronous/reconciliation work;
- Cloudflare R2 for venue-image storage;
- provider-native or lightweight managed deployment, logging, metrics, secrets and backup capabilities.

The safety goal is not to add infrastructure. It is to make the boundaries between these systems explicit about authenticity, authorization, idempotency, bounded resource use, concurrency, failure handling and recovery.

---

## 5. Core production-readiness requirements

### 5.1 Application security

Pickup Lane must have:

- server-side authorization for every protected read and mutation;
- request schemas that expose only client-mutable fields;
- type, range, length and format validation;
- bounded request bodies, uploads, queries and pagination;
- abuse controls for expensive and sensitive endpoints;
- HTTPS in production;
- safe browser security headers;
- deliberate CORS behavior when cross-origin;
- sanitized production errors;
- no debug/internal/provider/SQL detail exposed to clients.

### 5.2 Identity

Pickup Lane must:

- verify Firebase ID tokens on the backend;
- derive identity from verified token claims, never from client-supplied UID;
- enforce current local account state for privileged and monetary operations;
- prevent suspended, deleted or demoted users from retaining sensitive authority indefinitely;
- treat Firebase as identity authority, not as a replacement for Pickup Lane authorization;
- clear identity-scoped frontend state on logout, user switch and relevant account-state changes;
- use recent authentication for sensitive identity/admin actions where appropriate.

### 5.3 Database

Pickup Lane must use PostgreSQL for real transactional guarantees:

- explicit transactional boundaries;
- PK/FK/NOT NULL/CHECK/UNIQUE constraints for genuine invariants;
- unique/idempotency constraints where duplicate logical operations must be impossible;
- deliberate row locking, conditional writes or equivalent concurrency control where races matter;
- real PostgreSQL tests for concurrency-sensitive behavior;
- bounded connection demand;
- least-privilege runtime roles;
- reviewed and tested Alembic migrations;
- rollout-compatible migration behavior when old/new versions can overlap.

Do not duplicate the application business state machine inside PL/pgSQL when compact database-native constraints are sufficient.

### 5.4 Payments

Stripe remains authoritative for Stripe-side monetary state.

Pickup Lane must have:

- one logical PaymentIntent per purchase/order attempt lifecycle;
- server-calculated monetary authority;
- signed webhook verification using the raw request body;
- duplicate and out-of-order webhook tolerance;
- idempotent Stripe writes;
- safe handling of provider timeout/unknown outcomes;
- reconciliation independent of webhook delivery;
- refund/credit invariants that prevent duplicate value creation;
- safe saved-payment-method handling using Stripe-hosted mechanisms;
- restricted live credentials.

A browser callback is never payment authority.

### 5.5 Durable background work

The existing PostgreSQL queue is sufficient.

Required behavior includes:

- atomic local state plus enqueue where both must agree;
- exclusive bounded claims;
- lease/fencing semantics where external side effects occur;
- at-least-once-safe handlers;
- bounded retry and exhaustion;
- crash recovery;
- graceful worker shutdown;
- visible failed/exhausted jobs;
- provider backoff for throttling/transient failure.

Heartbeats are needed only when real job duration requires them.

Permanent append-only event history for every heartbeat is not required.

A speculative priority/fairness scheduler is not required.

### 5.6 R2 and venue images

Before issuing an upload capability, the backend must authorize the actor and target.

Required behavior includes:

- server-generated object keys;
- short-lived operation-specific presigned URLs;
- private staging/raw uploads;
- actual-byte validation after upload;
- image decode and resource bounds;
- supported-format enforcement;
- metadata stripping;
- safe re-encoding before publication;
- abandoned-upload cleanup;
- missing/orphan detection for actual Pickup Lane-owned objects;
- idempotent deletion/replacement;
- least-privilege R2 credentials;
- narrow production CORS.

Do not build a generalized storage-management platform.

### 5.7 Frontend

The production frontend must have:

- a real production Vite build;
- no secrets in browser-visible configuration;
- identity-scoped cache/storage cleanup;
- retry-safe mutations;
- valid SPA deep links on the final host;
- explicit pending/success/retryable/terminal/unknown failure states where relevant;
- restrictive CSP compatible with actual Firebase/Stripe dependencies;
- restricted or non-public production source maps;
- a declared supported-browser policy;
- reasonable accessibility on core workflows.

### 5.8 Testing

Testing must be risk-based and prove real safeguards.

Required evidence includes, where relevant:

- unit/service tests;
- API authorization and contract tests;
- real PostgreSQL integration tests;
- deterministic concurrency tests;
- migration tests;
- Stripe sandbox/provider tests;
- critical browser E2E tests;
- restore/recovery proof;
- launch-scale capacity smoke/load proof.

Do not build a custom test-management or compliance platform around pytest.

Do not classify tests as trustworthy merely because they live in a special directory.

Existing useful regression tests should remain active unless individually shown to be obsolete or invalid.

### 5.9 CI and supply chain

Pickup Lane must have:

- deterministic dependency resolution;
- required CI before release/merge;
- protected release/default branch behavior appropriate to the repository;
- least-privilege GitHub Actions permissions;
- third-party actions pinned to full commit SHAs;
- one useful dependency/secret scanning path;
- one maintained SAST/code-scanning path;
- source/build/release identity.

A mandatory SBOM program is not required unless a real consumer, customer, platform or legal requirement later creates that need.

Formal artifact signing/provenance infrastructure is not required for this application by default.

### 5.10 Logging and observability

Pickup Lane must have:

- structured application logs;
- request/job/payment/storage/admin correlation where useful;
- release identity;
- secret, token, PII and payment-data redaction;
- centralized retained API and worker logs;
- a small actionable metric/alert set.

Critical launch signals should include, as applicable:

- API availability/error rate/latency;
- DB connection pressure/timeouts;
- worker backlog, age, retry and exhaustion;
- Stripe/provider failures;
- financial reconciliation discrepancies;
- storage failures;
- resource saturation.

Do not duplicate every durable domain transition into central logs.

Do not build a giant event taxonomy.

Do not require formal SLO/error-budget bureaucracy unless the service later has a real operational need for it.

### 5.11 Administrative auditability

Privileged mutations must be attributable.

Keep:

- actor;
- action;
- target;
- time;
- outcome;
- reason/context where needed;
- correlation/reference identifiers;
- append-only or tamper-resistant behavior.

Audit especially sensitive staff reads where private messages or detailed financial data are exposed outside ordinary user flows.

Do not build a new audit investigation/search/export product as a production-readiness requirement.

### 5.12 Privacy

Pickup Lane must:

- know what personal/sensitive data it actually stores;
- minimize unnecessary copies;
- define purpose-based retention/deletion behavior for material data classes;
- preserve required financial/audit integrity when accounts are deleted;
- harden the existing account-deletion/anonymization workflow;
- handle provider-side copies correctly;
- prevent restore from silently resurrecting deleted/anonymized identities or data;
- test deletion/provider-failure/retry/restore edge cases.

A general personal-data export feature is not required unless later demanded by law, contract or explicit product scope.

A generic legal-hold platform is not required.

### 5.13 Secrets and provider access

Production must have:

- separate dev/test/staging/production credentials and data boundaries;
- no production secrets in Git or frontend bundles;
- provider-native secret storage/injection;
- least-privilege runtime identities;
- MFA for human production control-plane access;
- individual attributable accounts;
- tested rotation, revocation and offboarding;
- short-lived CI/cloud identity such as OIDC when supported by the selected provider;
- a narrow emergency-access path where needed.

Do not build a custom cross-provider IAM system.

### 5.14 Deployment

Production deployment must include:

- startup validation of critical configuration;
- liveness/readiness behavior;
- graceful API shutdown;
- graceful worker shutdown;
- release identity;
- migration-compatible rollout;
- an understood rollback or forward-fix path.

Exact hosting, process count, replica count, autoscaling and rollout values remain late-bound until final infrastructure is selected.

### 5.15 Capacity

Pickup Lane must have explicit finite budgets for:

- API concurrency;
- worker concurrency;
- PostgreSQL connections;
- expensive request/query dimensions;
- retry volume;
- provider throttling.

Expected launch load should be exercised with reasonable headroom.

Autoscaling and multiple replicas are situational.

Sharding, microservices and distributed schedulers are not currently justified.

### 5.16 Backup and recovery

Pickup Lane must define acceptable:

- **RPO**: maximum tolerable data loss;
- **RTO**: maximum tolerable recovery time.

The final PostgreSQL platform must provide a backup/recovery mechanism that meets those values.

Before launch:

- automated backups must exist;
- PITR or an equivalent low-loss recovery mechanism should be used when needed to meet the accepted RPO;
- an actual isolated restore must succeed;
- critical application integrity checks must pass after restore;
- outbound provider side effects must remain disabled during initial restore validation;
- local payment/job state must be reconciled before provider-mutating workers are re-enabled;
- completed deletion/anonymization must not silently return.

### 5.17 Incident readiness

Pickup Lane must have:

- a named production owner;
- a backup/escalation path;
- concise runbooks for real critical failure modes;
- known access to Stripe, PostgreSQL, R2, Firebase and deployment systems;
- a secret-compromise revoke/rotate procedure.

Runbooks should cover the actual selected stack and real risks, not hypothetical infrastructure.

---

## 6. Current program state

The historical master blueprint contained 42 parent-level planned entries.

Implementation later decomposed several parents into child passes, so implemented-pass count and parent-pass count are different measurements.

Current authoritative audit status:

- 40 implemented passes were audited;
- 39 are merged/accepted;
- `WS03-05B` is implemented in open PR #176 but unmerged;
- the remaining roadmap contains 27 genuinely unimplemented executable/deferred/parent units;
- none of the 27 remaining units should be deleted wholesale because each still contains legitimate production-readiness work;
- substantial unnecessary scope must be removed from inside many of those units.

This corrected blueprint is the roadmap authority for what survives.

Historical control counts, historical P0/P1/P2 labels and historical pass wording are not automatic launch blockers.

---

## 7. Implemented-work correction program

Already-implemented legitimate hardening stays.

Cleanup must target only unnecessary product expansion, process machinery and internal architecture.

### 7.1 Product decisions

| Capability | Final decision |
|---|---|
| Platform Notice selected-user cap of 500 | **KEEP** |
| Review-case assignment/reassignment/unassignment | **REMOVE** |
| Reopen closed review cases | **REMOVE** |
| Merge historical review cases | **REMOVE** |
| Formal note-correction relationships | **REMOVE** |
| Chat cases in the Review Cases admin UI | **KEEP** |
| Expanded lifecycle/history inspection UI | **REMOVE extra UI** |
| Necessary backend case history for correctness/auditability | **KEEP minimal necessary history** |
| Admin-facing R2/storage repair controls | **REMOVE** |
| General personal-data export | **REMOVE from production-readiness scope** |

### 7.2 PR #176 corrected target

`WS03-05B / PR #176` must not merge as currently implemented.

Keep:

- chat cases in Review Cases;
- expected-case-version conflict protection;
- deterministic locking;
- idempotency;
- one-open-case uniqueness where genuinely required;
- actor/timestamp/action/outcome history;
- immutable ordered history needed for correctness/auditability;
- compact FKs, unique constraints, checks and concurrency-critical database safeguards;
- stale UI reload/conflict handling;
- legitimate finding/chat-signal/enforcement references.

Remove:

- assignment state, APIs, filters, UI and history;
- reopen state, APIs, UI and history;
- merge state, APIs, UI, linked-case navigation and history;
- `corrects_note_id` and correction-specific relationships/UI;
- expanded lifecycle/history explorer;
- history/metadata whose only purpose is a rejected feature;
- the comprehensive PL/pgSQL duplicate review-workflow state machine.

Immutable notes remain append-only. A later clarification/correction can be represented by another immutable note without a formal correction relationship.

### 7.3 Merged process/testing/governance machinery to remove

Remove as production-readiness infrastructure:

- custom requirement-to-pytest compliance framework;
- trusted-root / zero-trust directory hierarchy;
- reusable pass-planning framework;
- broad backend test-suite archival/reset;
- reusable testing-record framework;
- generalized repository-topology scanner;
- custom production-readiness Gate workflow;
- generic release/rollback record template;
- reusable production-readiness PR-description framework;
- broad program-wide engineering/process framework;
- global Gate-review-completion rule;
- reviewer-language/PR-writing frameworks;
- repository-local Codex orchestration/custom-agent/handoff framework.

Ordinary useful engineering practices remain:

- focused planning where a change needs it;
- normal pytest;
- active regression tests;
- targeted runtime/config checks;
- concise validation results;
- ordinary PR review;
- simple repository instructions for Codex;
- normal Git/PR usage.

### 7.4 Merged internal architecture to remove or simplify

Remove:

- declarative `provider_retry_policy.py` registry;
- permanent pagination-contract/handoff inventory;
- declarative migration-policy mirror;
- speculative priority/fairness scheduler;
- permanent heartbeat-event rows.

Simplify:

- scanner latency observability should use normal metrics/logging instead of persisting execution duration on every moderation record;
- review-case DB protection should use compact database-native invariants rather than a duplicate PL/pgSQL application state machine.

---

## 8. Remaining production-readiness roadmap

All 27 remaining units stay as work items, but only the corrected scope below survives.

### 8.1 Moderation

#### WS03-05C — Moderation enforcement and safe notices

Need:

- action/state preconditions;
- idempotency and conflict behavior;
- reversal/restoration correctness;
- truthful safe notices;
- only concrete notice-delay/suppression behavior actually required by real actions.

Do not build:

- a second moderation permission hierarchy;
- a generalized notice lifecycle engine.

#### WS03-05D — Minimum-necessary admin data and sensitive-read auditing

Need:

- minimum-necessary admin responses;
- excerpt-first sensitive content;
- controlled full-content reveal where existing admin behavior truly requires it;
- no-store/private cache behavior;
- sensitive-read auditing.

### 8.2 Database and migrations

#### WS04-01D — Final PostgreSQL topology, connection budget and roles

Need final-provider proof of:

- selected PostgreSQL platform/topology;
- provider connection limit;
- maximum API/worker process demand;
- real pool settings;
- safe headroom/reserve;
- migration/operational reserve;
- least-privilege runtime role;
- separate migration/schema-change authority where appropriate.

No final numeric values may be invented before the provider/topology is selected.

#### WS04-03B — Final migration/runtime rehearsal

Need:

- actual migration runner;
- actual provider/runtime permissions;
- representative migration path;
- lock/runtime behavior for real risky operations;
- rollout compatibility;
- final-environment rehearsal proportionate to actual migration risk.

Do not build a permanent production-scale migration laboratory.

### 8.3 Durable work and payments

#### WS05-01B — Final worker deployment/runtime proof

Need:

- actual worker hosting;
- process/concurrency topology;
- release identity;
- graceful shutdown;
- real claim/lease/fencing behavior;
- crash recovery;
- bounded retries/exhaustion;
- DB connection demand;
- real job-registry proof.

Do not preserve the rejected fairness scheduler or per-heartbeat event history.

#### WS05-03 — Refunds, credits, notices and reconciliation

Need:

- correct refund/credit/compensation invariants;
- durable jobs only where work must survive request/process/provider failure;
- idempotent provider operations;
- unresolved/unknown-outcome recovery;
- reuse of existing `MoneyIssue` and existing repair/reconciliation mechanisms;
- periodic bounded reconciliation of unresolved/recent monetary state against Stripe;
- provider throttling/backoff.

Do not:

- move every synchronous financial mutation behind the queue;
- queue ordinary DB-local notice creation without a real out-of-transaction delivery need;
- build a generic all-history financial synchronization system;
- create a second generic financial repair platform.

#### WS05-04 — Failure/concurrency/provider verification

Need focused proof for real high-risk transitions:

- deterministic concurrency races;
- duplicate/replay behavior;
- process crash;
- timeout;
- unknown provider outcome;
- bounded retries;
- Stripe sandbox scenarios;
- deployed-worker behavior;
- reconciliation behavior.

Do not build:

- a generic fault-injection DSL/platform;
- exhaustive Cartesian failure matrices;
- tests for rejected speculative worker features.

### 8.4 Venue images and R2

#### WS06-01 — Admin upload authority and initiation

Need:

- only the approved active-admin path may initiate venue-image uploads;
- server-owned object identity;
- actor/venue/object binding;
- short-lived operation-specific R2 presigned URLs;
- replay/expiry protection appropriate to the existing workflow.

Do not create a second generic upload-intent subsystem if the existing pending venue-image record can safely own the intent.

#### WS06-02 — Image validation and sanitization

Need:

- actual-byte validation;
- byte limits;
- decoded dimension/pixel/decompression limits;
- supported image formats only;
- metadata removal;
- safe re-encoding;
- publication only after sanitization;
- raw staging kept only as long as needed.

Derivatives are optional unless a real product/performance requirement needs them.

Asynchronous processing is optional unless actual processing cost/failure characteristics require durable work.

#### WS06-03 — R2 lifecycle and repair

Need:

- truthful replacement/deletion behavior;
- abandoned-upload cleanup;
- orphan/missing-object detection scoped to Pickup Lane-owned objects;
- idempotent cleanup;
- safe automatic repair for unambiguous cases;
- narrow internal/operator mechanism for rare ambiguous cases;
- final R2 token/CORS/access proof;
- cache/removal behavior appropriate to the selected final delivery path.

Do not build:

- admin-facing repair controls;
- a storage-management dashboard;
- a universal R2 reconciliation platform;
- derivative repair if derivatives are not actually retained;
- speculative CDN purge architecture before final delivery topology requires it.

### 8.5 Frontend

#### WS07-01 — Production build and public configuration

Need:

- real production Vite build;
- no secrets in browser-visible config;
- environment separation;
- release/build identity;
- restricted/non-public production source maps;
- final-host verification later.

#### WS07-02 — Identity-scoped state and safe retries

Need:

- deliberate Firebase persistence;
- cleanup on logout/account switch/account-state change;
- identity-scoped caches/storage;
- no stale admin/private state after identity change;
- bounded safe read/token retries;
- no blind mutation replay.

#### WS07-03 — Routes, forms and resilient UI state

Need:

- deep-link correctness;
- route/query parsing;
- loading/empty/error states;
- provider/network failure states;
- form failure behavior;
- safe API error handling;
- small shared primitives only where duplication is real.

Do not recreate identity/retry ownership already handled by WS07-02.

#### WS07-04 — Browser security and third-party code

Need:

- inventory of actual Firebase/Stripe browser dependencies;
- CSP compatible with required providers;
- framing and browser security headers;
- failure isolation;
- minimal third-party browser code;
- final deployed-domain/header proof later.

SRI is only needed where the actual loading model supports it and the asset bytes are stable.

#### WS07-05 — Accessibility, browser support and performance

Need:

- usable keyboard/focus/form/error behavior on core flows;
- intended browser compatibility;
- production-build performance measurement;
- correction of material bundle/image/runtime problems.

Do not invent performance budgets without measurement.

### 8.6 Testing and CI

#### WS08-01 — Current test inventory and gap cleanup

Need:

- reactivate useful regression tests;
- remove/replace only tests individually shown to be obsolete or invalid;
- safe reusable DB/browser/provider/auth fixtures;
- identify critical coverage gaps;
- lightweight mapping from important invariants to proof only where useful.

Do not recreate:

- trusted-root/legacy hierarchy;
- custom requirement declaration/checker platform;
- universal suite declarations;
- permanent control-to-test compliance mapping.

#### WS08-02 — Critical risk-based suites

Need targeted coverage at the right layer for:

- authorization;
- financial correctness;
- durable jobs;
- deterministic PostgreSQL concurrency;
- migrations;
- provider boundaries;
- account deletion/privacy;
- critical frontend journeys;
- recovery/restore.

#### WS08-03 — CI and supply-chain hardening

Need:

- deterministic Python/JS dependency resolution;
- production build in CI;
- required critical test gates;
- migration checks;
- protected release/default branch behavior;
- explicit minimum GitHub Actions permissions;
- third-party actions pinned to full commit SHAs;
- one useful dependency/secret scanning path;
- one maintained SAST/code-scanning path;
- simple source/build/deployment identity.

Do not require:

- a formal SBOM program by default;
- custom provenance/signing infrastructure;
- another compliance/release-evidence framework.

### 8.7 Observability and audit

#### WS09-01 — Structured logging

Need:

- structured API and worker logs;
- correlation identifiers;
- release identity;
- bounded fields;
- redaction;
- central retained searchable logs;
- final-provider delivery/access/retention proof.

Do not duplicate full durable domain histories into logs.

#### WS09-02 — Administrative auditability

Need to harden the existing `AdminAction`/audit behavior:

- append-only/tamper-resistant records;
- actor/action/target/time/outcome;
- atomic/durable recording where appropriate;
- important privileged-action coverage;
- sensitive-read auditing where appropriate;
- restricted audit access.

Do not create:

- a second universal audit store;
- duplicate durable rows for every denial/provider failure already truthfully represented elsewhere;
- a broad new audit investigation/search/export product.

#### WS09-03 — Metrics, alerts and capacity

Need a small critical signal set and actionable alerts for:

- API failures/latency;
- DB exhaustion/timeouts;
- worker backlog/retry/exhaustion;
- payment/reconciliation failure;
- provider throttling/failure;
- storage failure;
- resource saturation.

Need targeted capacity proof for:

- DB connection budget;
- API concurrency;
- worker throughput/backlog;
- provider limits.

Do not create:

- formal SLO/error-budget bureaucracy;
- dashboard/alert proliferation;
- generic cost-governance systems;
- generic load-testing platforms.

### 8.8 Privacy, secrets and operations

#### WS10-01 — Privacy/data lifecycle

Need:

- bounded inventory of material personal/sensitive/provider-copy data;
- minimization;
- purpose-based retention;
- existing account deletion/anonymization hardening;
- idempotent provider cleanup;
- retry/reconciliation for partial or unknown cleanup outcomes;
- safe Firebase/Stripe/R2 cleanup where applicable;
- preservation of necessary financial/audit truth;
- restore-time deletion/anonymization correctness;
- privacy edge-case tests.

Do not build:

- a general personal-data export product;
- a generic legal-hold platform;
- a universal data-governance registry;
- arbitrary invented retention schedules;
- a universal tombstone/replay framework.

#### WS10-02 — Secrets and control-plane access

Need:

- actual selected-provider access inventory;
- attributable human accounts;
- MFA/recovery;
- least privilege;
- provider-native secret injection;
- runtime credential scope;
- tested rotation/revocation/offboarding;
- narrow emergency access;
- OIDC/short-lived CI identity where the selected provider supports it.

Do not build a cross-provider IAM/governance platform.

#### WS10-03 — Incident readiness

Need:

- named owner/escalation;
- concise procedures for actual critical failure modes;
- provider-specific steps only for selected providers;
- secret-compromise handling;
- representative exercises.

Do not build:

- a generic incident-management platform;
- exhaustive runbook catalogs;
- enterprise severity/postmortem bureaucracy.

#### WS10-04 — Backup and recovery

Need:

- explicit accepted RPO;
- explicit accepted RTO;
- final provider backup configuration meeting those objectives;
- PITR or equivalent low-loss mechanism where required by the accepted RPO;
- isolated real restore;
- integrity/application checks;
- provider-mutating workers disabled during initial restore validation;
- Stripe/payment/job reconciliation before effects resume;
- deletion/anonymization resurrection protection;
- one real successful recovery proof and targeted reruns after recovery-relevant changes or failed proof.

Do not build:

- a permanent recovery laboratory;
- clones of every provider for every restore;
- exhaustive table-by-table recovery framework;
- a recovery evidence-management platform.

### 8.9 Final closure

#### CLOSE-01 — Final discrepancy/completeness sweep

Need one small final check that:

- every surviving required obligation is complete;
- triggered final-provider evidence exists;
- real contradictions are resolved;
- genuine exceptions/open risks are explicit;
- no rejected C/D item remains a hidden blocker.

Do not create:

- a universal evidence index;
- a dossier for every historical control;
- a new exception/evidence governance framework.

#### CLOSE-02 — Final readiness decision

Need one independent sign-off/no-sign-off decision against:

- corrected current production-safety requirements;
- real final repository state;
- final provider/runtime evidence;
- testing results;
- recovery proof;
- unresolved material risk.

The historical 163-control checklist may be used only as a completeness cross-check.

It must not resurrect rejected product features, unnecessary process systems, speculative architecture or obsolete historical remedies.

---

## 9. Provider-neutral versus late-bound work

The final production infrastructure is intentionally not selected yet.

Current demo/prototype use of Vercel, Render and Neon does not establish the final production topology.

### 9.1 Work that can be completed before final provider selection

Examples:

- application authorization and validation;
- request/query bounds;
- error behavior;
- database constraints and concurrency behavior;
- provider-neutral connection-budget formulas;
- durable-job semantics;
- Stripe reconciliation logic;
- R2 upload/sanitization lifecycle logic;
- frontend state cleanup;
- CI configuration;
- logging/redaction implementation;
- privacy/deletion behavior;
- provider-independent recovery design.

### 9.2 Work that remains late-bound

Examples:

- final hosting provider;
- production domains;
- edge/proxy/TLS/HSTS configuration;
- API/worker process and instance counts;
- autoscaling;
- actual PostgreSQL provider limit;
- final pool sizes;
- final DB roles/grants;
- final R2 account/token/CORS settings;
- final logging/metrics provider;
- final alert delivery;
- production IAM/secret bindings;
- backup/PITR implementation;
- actual RPO/RTO proof;
- actual isolated restore;
- production capacity measurements.

Do not invent late-bound values to complete a pass.

---

## 10. Execution model

The old Stage 0 / Gate A / Gate B / Gate C / Gate D program is not required.

Use a normal engineering workflow:

1. **Scope**
   - identify the selected roadmap unit;
   - inspect current repository truth;
   - state the actual remaining problem;
   - remove historical C/D scope from consideration.

2. **Plan when necessary**
   - write a concise implementation plan only when the change is complex enough to need one;
   - define expected behavior, important invariants, implementation approach and validation;
   - do not create planning artifacts merely because the old process expected them.

3. **Implement and test**
   - make one coherent reviewable change;
   - use the smallest mechanism that solves the real problem;
   - test realistic failure and race conditions at the correct layer.

4. **Independent review**
   - inspect the actual diff and relevant surrounding code;
   - verify that the change solves the intended production-safety problem;
   - verify that it did not introduce unnecessary product or architecture expansion.

5. **PR**
   - use the normal repository PR flow;
   - PR description uses:
     - Summary
     - Changes
     - Validation
   - merge remains a deliberate repository action.

Codex may be used throughout this workflow.

Codex does not require duplicated handoff bundles, custom repository-local agents, frozen planning SHAs, custom multi-gate orchestration or custom compliance-checker routing.

Repository instructions should be concise, current and directly useful to a competent developer or coding agent.

---

## 11. Testing philosophy

Pickup Lane should test real failure modes aggressively without turning testing into a separate platform.

Examples of important edge cases include:

- concurrent first login;
- duplicate admin mutations;
- stale review-case writes;
- double refund/credit attempts;
- Stripe timeout after provider acceptance;
- duplicate/out-of-order webhooks;
- worker crash after provider side effect;
- expired/reclaimed job lease;
- provider 429/throttling;
- malformed or oversized upload;
- decompression-bomb-style image;
- R2 upload succeeds but DB finalize fails;
- DB update succeeds but provider cleanup fails;
- account deletion partially completes;
- provider timeout leaves deletion outcome unknown;
- deletion job is retried;
- same cleanup runs twice;
- backup restore contains state deleted after the backup;
- restored worker tries to replay stale provider work.

Use:

- unit/service tests;
- API tests;
- real PostgreSQL integration/concurrency tests;
- provider sandbox/emulator/mocked-failure tests where appropriate;
- browser E2E for critical user journeys;
- actual restore exercises when recovery is the behavior being proved.

Do not create giant generic frameworks to enumerate every theoretical combination.

---

## 12. Codex and repository organization

The repository should remain easy for a developer or Codex session to understand.

Keep only durable instructions that answer real questions such as:

- where backend code belongs;
- where frontend code belongs;
- database/migration rules;
- how to run relevant tests;
- production-readiness scope;
- what work is currently being executed;
- what final-provider facts remain intentionally unknown.

Avoid:

- duplicated copies of the same instruction files;
- multiple competing authority chains;
- large routing documents;
- local-chat history in tracked files;
- AI-specific orchestration frameworks;
- permanent handoff packages that duplicate canonical repository files.

One authoritative source per concern is preferred.

---

## 13. Explicit do-not-build list

The following are not launch requirements unless a future independent real requirement appears:

- Kafka;
- second durable queue;
- microservice decomposition;
- sharding;
- service mesh;
- event sourcing;
- custom identity platform;
- custom IAM platform;
- custom compliance platform;
- custom test-management platform;
- requirement-to-pytest compliance system;
- trusted-root/zero-trust test hierarchy;
- generic topology scanner;
- generic fault-injection platform;
- universal repair framework;
- generalized storage-management dashboard;
- generic audit investigation product;
- formal SLO/error-budget program;
- giant dashboard/alert catalog;
- SBOM governance program;
- formal artifact-signing/provenance infrastructure;
- enterprise incident-management platform;
- generic legal-hold system;
- general personal-data export product;
- admin-facing R2 repair product;
- moderation assignment workflow;
- moderation reopen workflow;
- moderation merge workflow;
- formal note-correction relationship;
- expanded moderation lifecycle/history explorer;
- speculative priority/fairness scheduler;
- permanent durable heartbeat-event history;
- duplicate application business state machines in PL/pgSQL.

---

## 14. Production-readiness completion criteria

Pickup Lane is ready for production only when all applicable items below are true.

### Security and identity

- protected actions authorize the current verified actor server-side;
- mass assignment is blocked;
- sensitive/expensive inputs are bounded;
- suspended/deleted/demoted identities cannot retain sensitive authority;
- production errors do not expose internal secrets/details.

### Database and concurrency

- critical invariants are transactionally and/or database enforced;
- money, booking, admin and job races have deterministic protection;
- connection demand fits the final provider budget;
- migrations are reviewed, compatible and rehearsed.

### Payments

- Stripe is processor-side authority;
- webhook verification is correct;
- duplicate/out-of-order events are safe;
- provider writes are idempotent;
- unknown outcomes are recoverable;
- bounded periodic reconciliation exists.

### Jobs

- enqueue/claim/lease/retry/exhaustion/recovery behavior is correct;
- handlers are safe under at-least-once execution;
- worker shutdown is safe;
- final worker deployment has been proven.

### Storage

- only authorized admins can initiate venue-image uploads;
- presigns are short-lived and operation-specific;
- raw bytes are private until validated;
- publication is sanitized/re-encoded;
- abandoned/orphan/missing/deletion failures are handled safely.

### Frontend

- production build is correct;
- browser configuration contains no secrets;
- identity state does not leak across users;
- critical mutations are retry-safe;
- deep links work;
- failure states are understandable;
- browser security policy is deployed.

### Testing and CI

- critical safeguards have adequate tests at the correct layer;
- real PostgreSQL race-sensitive paths are tested;
- Stripe sandbox/provider behavior is covered where needed;
- critical browser journeys are exercised;
- CI is deterministic and required;
- GitHub Actions are least privilege and pinned safely;
- security scanning is present without redundant noise.

### Observability and audit

- API and worker logs are structured, redacted, correlated and centralized;
- critical failure conditions have actionable alerts;
- privileged actions are auditable;
- sensitive staff reads are auditable where applicable.

### Privacy and access

- personal data is minimized;
- existing deletion/anonymization is resilient and idempotent;
- provider copies are handled appropriately;
- restore does not silently resurrect deleted identities/data;
- production provider access is attributable, least privilege and MFA-protected;
- rotation/revocation/offboarding works.

### Deployment, capacity and recovery

- startup validation, readiness and graceful shutdown work;
- real launch capacity has reasonable headroom;
- provider throttling is handled;
- acceptable RPO and RTO are explicitly stated;
- automated backup meets those objectives;
- isolated restore has succeeded;
- provider-mutating work is controlled during recovery;
- payment/job reconciliation succeeds before restored production effects resume.

### Operations

- a production owner and escalation path exist;
- concise critical runbooks match the final selected stack;
- credential compromise has a known revoke/rotate path.

---

## 15. Final rule

Production-readiness completion is determined by whether the actual Pickup Lane system is safe to operate.

It is not determined by:

- finishing every historical document;
- satisfying every historical control label mechanically;
- preserving every old pass mechanism;
- completing every old evidence template;
- keeping every previously implemented internal framework;
- building rejected optional product features.

The program ends when the corrected required production-safety obligations are implemented, tested, verified in the final environment where necessary, and no material unresolved launch risk remains.
