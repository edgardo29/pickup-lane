# WS09-01 Intake - Structured Logging

## 1. What Needs To Be Decided

This intake decides how the remaining **WS09-01 - Structured Logging** work should be divided so implementation can proceed without pretending that final production logging infrastructure already exists.

The parent combines two different engineering conditions: source-level logging behavior that can be completed against the current application and worker code now, and centralized production logging work that depends on a selected final provider, final API/worker runtime topology, and approved operational inputs. The execution shape must preserve both without blocking the provider-neutral work or treating deferred production proof as complete.

## 2. What We Know

The facts below are limited to items that materially affect whether WS09-01 should execute as one unit or be split.

| Topic | Current fact or constraint | Why it affects execution |
|---|---|---|
| Parent requirement | WS09-01 requires structured API and worker logs, correlation identifiers, release identity, bounded fields, redaction, centrally retained searchable logs, and final-provider delivery/access/retention proof. | Source behavior and final provider activation are both required; neither may disappear during decomposition. |
| Existing observability primitives | Accepted EN-02 provides reusable correlation, event-envelope, redaction, public-error, and telemetry primitives, but it is not a complete structured-logging implementation. In particular, its event envelope does not by itself bound every release/source identity input. | The current source foundation should be reused and hardened where necessary rather than treated as turnkey or replaced with a second observability framework. |
| Correlation mismatch | HTTP correlation uses canonical UUIDv4 values. Current durable-job correlation accepts a broader format and may generate `job-...` identifiers, and current payment-job enqueue paths do not establish end-to-end request-to-job correlation. | The provider-neutral logging work must own compatibility and propagation across request, job, and worker boundaries. The exact design belongs in engineering planning. |
| Current logging surface | Current application logging uses multiple shapes across middleware, services, global error handling, framework/access output, and the durable worker; worker operational output remains plain text in places. | The source-level unit must cover normalization of the existing application/API/runtime/worker logging surface, not merely add a few new structured events. |
| Existing logging-safety contract | Accepted WS04-02C already prohibits unsafe logging of raw SQL values, raw provider payloads, credentials, payment data, personal data, and unbounded text while allowing safe bounded operational metadata. | WS09-01 must preserve this accepted safety boundary while normalizing logging. |
| Provider-control-plane and evidence contract | Accepted EN-03 defines the current provider inventory, unresolved monitoring/logging-provider state, ownership expectations, and sanitized external-evidence boundary. | The final-provider unit must consume that foundation rather than invent a second evidence system or treat provider facts as repository-proven. |
| Release identity | Current backend settings already provide a bounded application release identity, but final deployed identity values remain runtime facts. | Source-level support can be completed now; final-provider/runtime verification remains later. |
| Final production infrastructure | Final production API hosting, worker hosting, centralized logging provider/sink, ingestion topology, provider access model, and concrete retention configuration are intentionally not selected or approved yet. | Central logging activation and verification cannot honestly complete now and must remain a mandatory deferred unit. |
| Worker runtime dependency | WS05-01B owns final worker deployment/runtime proof and remains late-bound. | Final centralized worker-log activation and proof cannot complete before an accepted final worker runtime exists. |
| Retention and access inputs | WS10-01 owns broader purpose-based retention decisions; WS10-02 owns broader selected-provider access/control governance. | The deferred logging unit may apply and verify logging-specific settings, but it must not invent retention policy or duplicate broader IAM governance. |
| Scanner-latency correction | The corrected master requires scanner latency observability to stop persisting execution duration on every moderation record and instead use normal metrics/logging. Current source still persists that duration. | This correction must have one owner. It is assigned to WS09-03, which owns the replacement observability signal and retirement of the per-record persisted duration path; WS09-01A must not duplicate it. |

## 3. Execution Decision

The parent should be **split into two executable units**.

This split is required because provider-neutral logging can be implemented and accepted against current source now, while centralized production logging requires a different prerequisite state, different operational environment, and provider/runtime configuration that does not yet exist.

| Order | Work | Depends on |
|---|---|---|
| 1 | **WS09-01A - Provider-Independent Structured API and Worker Logging** | Accepted current observability, logging-safety, API runtime, and durable-worker source contracts |
| 2 | **WS09-01B - Final Centralized Logging Activation and Verification** | Accepted WS09-01A plus the selected final API/worker/logging topology and approved retention/access inputs |

**WS09-01A** leaves a coherent result on its own: Pickup Lane's repository-owned API/runtime/worker logging surface follows one provider-neutral structured logging contract with compatible correlation, bounded/redacted fields, and release identity suitable for later collection.

**WS09-01B** leaves a separate coherent result: the selected production logging system is actually configured to receive the API and worker logs, preserve the required searchable fields, restrict access appropriately, retain logs according to approved requirements, and provide runtime verification that the path works.

Keeping the parent whole would force currently executable source work to wait for intentionally unselected infrastructure. Splitting API and worker logging into separate children is not justified because they share the same structured-logging contract and can be reviewed as one provider-neutral outcome.

## 4. Where The Parent Work Goes

This allocation accounts for the complete WS09-01 parent scope and the adjacent corrected-master obligations that intersect it. The purpose is to avoid hidden gaps, duplicated ownership, or premature provider assumptions.

| Parent work | Goes to | Remaining boundary |
|---|---|---|
| Structured application/API/runtime logging | `WS09-01A` | Covers normalization of repository-owned application, error, middleware, access/framework, and related runtime logging surfaces without selecting a final logging vendor. |
| Structured durable-worker logging | `WS09-01A` | Covers the worker's operational logging contract without duplicating the durable-job history as a second event store. |
| Request/job/worker correlation | `WS09-01A` | Reconciles current correlation-contract incompatibility and establishes meaningful propagation while preserving accepted HTTP compatibility. Detailed mechanics are deferred to engineering planning. |
| Payment/storage/admin correlation where useful | `WS09-01A` | Covers bounded operational correlation and summaries for meaningful payment, provider-storage, and administrative logging paths without duplicating payment histories, storage state, or administrative audit truth. |
| Release identity and bounded structured fields | `WS09-01A` | Reuses current foundations and owns any logging-specific hardening required for a safe bounded source contract. |
| Redaction and logging safety | `WS09-01A` | Preserves EN-02 and WS04-02C safety boundaries; no raw secrets, provider payloads, payment data, PII, SQL values, or unbounded text become logging content. |
| Central API and worker log delivery/ingestion | `WS09-01B` | Owns selected-provider activation/configuration after the final production topology exists. Provider selection itself is an external prerequisite, not work invented by A. |
| Central searchability and field preservation | `WS09-01B` | Owns configuration and verification that the final logging system preserves the structured fields needed for operations. |
| Logging-specific provider access application/proof | `WS09-01B` | Applies and verifies approved access requirements for the logging system; broader provider IAM/MFA/recovery/offboarding governance remains `WS10-02`. |
| Logging retention application/proof | `WS09-01B` | Applies and verifies an approved logging-retention requirement; broader retention policy remains `WS10-01`, and B may not invent an arbitrary schedule. |
| Scanner latency persistence cleanup and replacement signal | `WS09-03` | Assigned once to the metrics/alerts/capacity owner; excluded from WS09-01A to avoid duplicate observability and schema cleanup. |
| Broader metrics, alerts, dashboards, and capacity | `WS09-03` | Outside WS09-01. WS09-03 may consume structured-log signals but owns its own metric/alert design. |
| Administrative audit truth | Accepted `WS09-02` | Logs must not become a second administrative audit store. |
| Durable domain/job/payment histories | Existing owning domain/workflow stores | WS09-01 may summarize operational events but must not duplicate full durable histories. |

No WS09-01 obligation is dropped: source behavior is owned by A, and final centralized activation/configuration plus verification is owned by B.

## 5. What Happens Next

**WS09-01A - Provider-Independent Structured API and Worker Logging** is the next executable engineering work.

Its required source foundations are already present: the application has accepted observability/redaction primitives, current API request correlation, release-identity support, accepted logging-safety rules, and an accepted durable-worker foundation. The remaining incompatibilities and heterogeneous logging surfaces are source problems that A can reconcile without selecting a final production provider.

There is no technical blocker to beginning engineering planning for A.

WS09-01B is intentionally not executable yet. It becomes executable only when its final infrastructure and policy prerequisites described in the Internal Record are satisfied.

## 6. Internal Record

| Detail | Value |
|---|---|
| Parent pass | `WS09-01 - Structured Logging` |
| Intake outcome | Split into current provider-independent work plus mandatory deferred final-infrastructure work |
| Accepted baseline | Current accepted `develop`; no baseline hash is frozen by this intake |
| Intake path | `docs/production-readiness/planning/passes/ws09/ws09-01-intake.md` |
| Authority sources | `docs/production-readiness/00-READ-ME-FIRST.md`; `docs/production-readiness/01-PROGRAM-CONTEXT.md`; corrected master sections 5.10, 7.4, 8.3, 8.7, and 8.8; current `PASS-EXECUTION-REGISTER.md`; current implementation workflow Stage 0; current intake template |
| Execution-register state | `WS09-01` remains unimplemented; current post-WS09-02C register state records 45 accepted executable passes and 24 remaining units |
| Applicable accepted prerequisites | EN-02 observability primitives; EN-03 provider-control-plane and sanitized-evidence foundation; WS04-02C logging-safety contract; current API correlation/runtime behavior; current release-identity settings; accepted WS05-01A portable durable-worker/job source behavior |
| Applicable engineering guidance | Program Context-routed `docs/agent-notes/` backend and testing guidance, applied where relevant without treating it as corrected-master scope authority |
| Child order | `WS09-01A -> WS09-01B` |
| Selected first executable unit | `WS09-01A - Provider-Independent Structured API and Worker Logging` |
| Mandatory deferred unit | `WS09-01B - Final Centralized Logging Activation and Verification` |
| Proposed canonical plan path | Not fixed by Stage 0; if Gate A creates a durable plan, use the current planning template under the WS09 pass-family path |
| Proposed requirement declaration | Not applicable - Stage 0 does not create a new mandatory requirement-declaration/compliance framework |
| Proposed trusted test or verification location | Not fixed by Stage 0; Gate A must use current applicable backend/application testing guidance and the lowest reliable proof layer |
| Blockers | None for `WS09-01A`; `WS09-01B` remains prerequisite-blocked while final infrastructure and policy/control inputs are unresolved |
| Exact next allowed action | Perform a fresh independent Stage 0 review of this corrected intake. Gate A must not begin until the intake is approved. |

### Cohesion Record

The parent cannot execute as one unit because it fails the **single prerequisite state** and **single verification/forward-fix unit** tests: provider-neutral source work is executable now, while final centralized logging activation depends on intentionally unselected infrastructure and separate operational inputs.

`WS09-01A` is cohesive because its API/runtime/worker surfaces share one structured-logging contract, one current source prerequisite state, and one provider-neutral acceptance boundary.

`WS09-01B` is cohesive once triggered because its work is confined to the selected final logging path: activation/configuration plus runtime verification of delivery, searchable field preservation, access, and retention.

No additional API-versus-worker split is justified.

### Evidence-Class Record

`WS09-01A` is expected to be proved primarily through current source behavior and focused repository-level integration evidence for the complete structured logging contract. Exact tests and validation scope belong to Gate A.

`WS09-01B` requires sanitized provider/runtime evidence from the selected final production logging path. Repository source alone cannot prove its completion.

### Deferred Follow-Up Record - `WS09-01B`

**Owner:** `WS09-01B - Final Centralized Logging Activation and Verification`

**Preserved obligations:** central retained searchable API and worker logs; final-provider delivery/ingestion; preservation of required searchable structured fields; logging-specific access application/proof; logging-retention application/proof; final confirmation that correlation/release identity remain operationally useful and sensitive-data protections survive ingestion.

**Exact trigger:** all of the following are true:

1. `WS09-01A` is accepted.
2. The final production API hosting/runtime and centralized logging provider/sink plus ingestion topology are selected, approved by the accountable platform/observability owner under the current ownership record, and available.
3. Final worker hosting/runtime is available through accepted `WS05-01B`.
4. An owner-approved logging-retention requirement exists through `WS10-01` or an explicit owner decision.
5. Applicable selected-provider logging access/control requirements exist through `WS10-02` or an explicit owner decision.
6. The accepted EN-03 provider-control-plane inventory and sanitized-evidence rules are available for the selected provider.
7. A safe final environment is available where API and worker delivery, ingestion, searchability, access, and retention can be configured and verified honestly.

**Downstream consumers:**

- `WS10-01` consumes B's applied logging-retention configuration and provider proof for its broader privacy/retention closure. Its approved logging-retention input is a prerequisite to B; B's resulting proof is the return handoff.
- `WS10-02` consumes B's logging-specific provider-access configuration and proof for its broader selected-provider access closure. Its approved access/control input is a prerequisite to B; B's resulting proof is the return handoff.
- `WS10-03` consumes B for provider-specific incident diagnostics and centralized-log retrieval procedures once the final provider exists.
- `CLOSE-01` requires B to be resolved before the final discrepancy/completeness sweep can truthfully close WS09-01.
- `WS09-03` is a conditional consumer only if its selected alert/signal design depends on centralized log-derived signals; it may otherwise proceed while B's trigger is false.

**Latest required completion boundary:** execute B as soon as its trigger becomes true and no later than the earliest downstream consumer that actually requires the centralized-log facts or `CLOSE-01`, whichever comes first.

**Execution-register visibility:** when A is eventually accepted, the register must keep B visible as an incomplete mandatory deferred unit and must keep parent `WS09-01` incomplete until B is accepted or otherwise truthfully resolved under current authority.

Deferred status is not proof of completion.

### External Boundaries And Non-Goals

WS09-01 does not own provider selection, broader metrics/alert/capacity design, a second audit or event-history store, duplication of complete durable domain histories, broad retention-policy design, broad provider IAM governance, final worker deployment, or a new compliance/testing framework. It must not create a giant or exhaustive event taxonomy; structured events remain bounded and operationally useful. Provider-neutral A must not promote temporary Vercel, Render, Neon, local, CI, README, or framework defaults into permanent production assumptions.
