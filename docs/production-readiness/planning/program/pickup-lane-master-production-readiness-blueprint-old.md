# Pickup Lane Master Production-Readiness Blueprint

**Status:** Durable master execution blueprint

**Original planning date:** August 3, 2026

**Implementation authorization:** None. This document plans the work. It does not authorize code, Git, provider, deployment, migration, database, worker, storage, monitoring, backup, restore, or CI changes.

## 1. Program status routing

This blueprint is durable program authority for planned parent-pass scope, ordering,
dependencies, infrastructure timing, and completion expectations. It does not maintain
mutable branch, SHA, PR, or current-pass state.

Determine current execution state from current accepted repository truth and
`docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md`, using the
startup and authority rules in `docs/production-readiness/00-READ-ME-FIRST.md`. Do not
use the original August 3 planning snapshot, historical branch/merge notes, or old
prompts as current execution state.

The durable planning baseline remains:

- the locked audit contains **163 controls**, including **117 unresolved P0 controls**
  and **29 confirmed P0 failures** at the time of the original audit;
- the finalized remediation plan organizes the work into **WS01 through WS10** and
  requires phased implementation, current tests, provider evidence, runtime
  verification, and recovery evidence;
- all **27 owner decisions are approved**, with **0 open owner decisions**;
- implementation progress is tracked outside this section and may advance without
  rewriting the blueprint's historical planning counts.

## 2. Authority order

When two artifacts disagree, stop and apply this order:

1. Current accepted repository truth and the trusted baseline identified by
   `00-READ-ME-FIRST.md`, the execution register, and the applicable workflow.
2. The six locked audit reports and the 163-control manifest.
3. The finalized production-readiness remediation plan.
4. The approved foundation and Decision Packets 2 through 4.
5. This master blueprint.
6. The accepted Stage 0 intake and frozen Gate A plan for the current executable
   pass when they apply.
7. The current run instruction within its authorized scope.

A lower item cannot silently override a higher item. A discovered conflict produces a documented blueprint correction or a superseding owner decision before implementation continues.

## 3. Fixed decisions versus later technical values

The architectural and product direction is settled. The following items remain later **technical design or evidence-based values**, not reopened owner decisions:

| Area | Approved direction | Still selected later from evidence | First pass that must account for it |
|---|---|---|---|
| Security headers | Ownership split by response class and layer | Exact header values, CSP directives, HSTS behavior, staging/production differences | WS02-03 |
| Hosting/runtime topology | Keep application lifecycle and deployment contracts portable until final hosting is chosen | Final hosting provider, instance/process topology, autoscaling ceiling, rolling overlap, platform-specific hardening, provider runtime settings | WS02-02 |
| Edge/origin/TLS topology | Keep app-owned proxy, host, CORS, and response-class rules portable | Final public domains, direct-origin exposure, proxy/CDN behavior, TLS/HSTS/redirect settings, provider edge configuration | WS02-03 |
| Limits and timeouts | Use documented evidence and boundary tests | Request/header/body limits, timeouts, rate values, pagination limits | WS02-04 |
| PostgreSQL connections | One deployment-wide budget with reserve | Provider limit, instances, workers, pool, overflow, wait timeout, pooler/proxy mode, concrete production role/grant evidence | WS04-01 |
| Payment model | Separate payment, booking, refund, and compensation states | Exact enums, transitions, reservation duration, repair rules | WS05-02 |
| Venue images | Admin-only uploads; initials for users; sanitize before publication | Formats, bytes, pixels, derivative sizes, processing limits | WS06-02 |
| R2 lifecycle | Controlled deletion, recovery, reconciliation, and fallback | Cache TTL, recovery window, cleanup interval, production bucket/account/CORS/token/cache/provider settings | WS06-03 |
| Frontend hosting/public binding | Keep the production build and public-configuration contract portable | Final hosting project, domain, environment bindings, edge behavior, and source-map delivery/access settings | WS07-01 |
| Browser/performance | Modern browser policy and measured budgets | Exact device/browser matrix and measured performance thresholds | WS07-05 |
| Test artifacts | Sanitized, attributable, risk-based | Storage system and retention duration | WS08-03 |
| Observability infrastructure | Keep telemetry schemas, correlation, redaction, and signal requirements provider-neutral | Final logging/metrics provider, ingestion/delivery configuration, retention/access settings, dashboards, alert routing, provider capacity/cost values | WS09-01 / WS09-03 |
| Service objectives | Measure critical availability, correctness, payments, jobs, and freshness | Numeric objectives, launch thresholds, error budgets | WS09-03 |
| Privacy/retention | Purpose-based and table-by-table lifecycle | Exact durations and legally reviewed exceptions | WS10-01 |
| Recovery | Tiered protection and tested restore | RPO, RTO, PITR window, backup retention, recurring exercise schedule | WS10-04 |

No exact value may be invented merely to complete a pass.


### 3.1 Final infrastructure timing and provider-neutrality rule

Final production hosting and database-hosting infrastructure is intentionally
late-bound. The current Vercel, Render, and Neon setup is prototype/demo
infrastructure and is not a permanent production-architecture decision.
Temporary free-tier, preview, local, demo, or example settings must never be
promoted into final production assumptions merely because a pass needs a value.

This rule applies to any final production fact that materially depends on the
selected hosting, database host, edge/network topology, worker platform,
observability platform, backup platform, provider account, provider plan, or
provider-side configuration. Examples include:

- provider/project/account selection;
- public domains, origins, edge/proxy/CDN/TLS topology, and direct-origin exposure;
- instance/process counts, autoscaling, rolling overlap, runtime resource limits,
  and platform-specific hardening;
- database provider capacity, pooler/proxy mode, final pool/overflow values,
  production database roles/grants, and provider-side backup/PITR settings;
- final provider URLs/endpoints, environment bindings, secret-injection locations,
  production CORS/allowlists, bucket/account settings, and control-plane values;
- final logging/metrics provider configuration, dashboards, alert delivery,
  provider capacity/cost limits, and recovery/runtime evidence.

Before final infrastructure is selected, passes may still implement and verify
provider-independent work: interfaces, configuration names and validation,
source-owned security behavior, formulas, evidence schemas, portability
contracts, deterministic local/synthetic tests, and provider-neutral failure
handling. A value that is genuinely application-owned and can be justified from
provider-independent evidence does not need to wait merely because it is numeric.
The late-bound rule applies when the value or proof materially depends on final
production infrastructure.

When a parent pass contains both kinds of work, Stage 0 must not force an early
provider choice and must not block the entire parent solely because the final
infrastructure trigger is false. Stage 0 must separate:

1. the coherent provider-independent work that is executable now; and
2. a mandatory deferred verification unit for the final provider-specific
   configuration, values, topology, and runtime/provider evidence.

Every deferred unit must record its owning pass, exact obligation set,
prerequisites, activation trigger, and latest required completion boundary.
Temporary provider values are not substitutes. Deferred evidence is not proof and
does not close the underlying control.

Final-infrastructure-dependent verification must run after the relevant permanent
provider/topology is selected and the launch deployment shape is sufficiently
stable to produce honest evidence. It may run as soon as that trigger is true,
but every mandatory deferred infrastructure unit must be complete before
`CLOSE-01`. If an earlier pass genuinely requires one of those final facts, that
earlier pass waits only on the specific missing fact rather than causing unrelated
provider-independent work to stop.

This timing rule does not undo provider choices that higher authority has actually
locked as product architecture, such as an approved external service integration.
Even for a selected service, however, concrete production accounts, plans,
regions, quotas, domains, credentials, roles, provider settings, and runtime
observations remain unproven until the appropriate late-bound evidence exists.

## 4. Repository baseline and Git workflow

This section records durable repository-safety expectations and historical setup
structure. It does not maintain current branch, SHA, PR, worktree, or pass
state. Current execution-state verification is owned by
`00-READ-ME-FIRST.md`, `PASS-EXECUTION-REGISTER.md`, and the applicable workflow.

### 4.1 Baseline verification

Before an authorized pass mutates files, use the applicable workflow to verify
the current accepted baseline, branch, worktree/index state, remote relationship,
and changed-file scope. Historical `BASE-00` records remain program provenance;
they are not instructions to restart the current program from an old `main`
merge state.

The baseline verification must establish:

- the current branch and exact accepted baseline
- a clean or explicitly understood working tree
- all worktrees and their owners
- all stashes and whether they contain intended work
- recent branch/merge history
- remote tracking and whether local `develop` is current when the workflow
  requires it
- that production-readiness documents are included only when the current pass or
  correction scope authorizes them

No exact branch-creation or worktree-creation command is prescribed by this
blueprint. Use the current workflow and run instruction.

### 4.2 Intended isolation model

The historical preferred model, subject to baseline verification, was:

```text
pickup-lane/                         trusted current development checkout
pickup-lane-production-readiness/    isolated remediation worktree
```

Current workflows may use the active checkout or a separate worktree, but every
pass still uses an explicit branch and one narrow reviewable change set. A
separate child branch or pull request may be used per pass where practical;
otherwise each accepted pass must still remain an independently revertible
commit.

### 4.3 Git rules

1. Start every pass from the accepted baseline required by the applicable
   workflow.
2. Do not mix unrelated feature work with production-readiness remediation.
3. Include the pass ID in the branch, commit, pull request, evidence record, and review notes.
4. One pass may be split after inspection; it may not be broadened or silently combined with another pass.
5. Do not begin the next pass until the current pass is accepted, corrected, or reverted.
6. Database migrations, provider changes, and destructive operations require explicit rollback or forward-fix plans before execution.
7. Sensitive provider evidence is not committed to normal source control. The repository stores only sanitized records or references approved by the evidence policy.
8. Codex never invents the next pass, owner policy, architecture, or exception.
   Automated progression may select the next unit only when durable authority
   determines exactly one valid route.

## 5. Program gates

The table below records durable high-level program gates and historical setup
state. It is not the current per-pass execution workflow. Current production-
readiness work routes through `PASS-IMPLEMENTATION-WORKFLOW.md` or
`PASS-RECHECK-WORKFLOW.md`.

| Gate | Required result | Work allowed after gate |
|---|---|---|
| G0: Historical baseline ready | Historical intended work merged and baseline understood | Historical BASE-00 provenance; current sessions use workflow preflight |
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

This blueprint contains the original **42 parent-level planned passes**. Stage 0 may decompose them into additional executable children or mandatory deferred follow-ups. Pass IDs define order and scope, not calendar estimates.

| Pass | Track | Type | Title | Primary control count | Dependencies |
|---|---|---|---|---:|---|
| BASE-00 | PROGRAM | Repository inspection | Repository baseline and isolation gate | 0 | Historical setup predecessor; not a current restart instruction |
| GOV-01 | WS01 | Decision and governance | Import and reconcile the approved governance package | 5 | Historical BASE-00 setup |
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
| WS04-01 | WS04 | Database foundation | Database engine/session lifecycle, connection budget, and least-privilege roles | 6 | WS02-02; DBP-01; actual PostgreSQL provider/topology only for the mandatory late-bound final verification portion |
| WS04-02 | WS04 | Database/domain/concurrency | Transactions, invariants, locks, and deterministic concurrency | 8 | Accepted provider-independent WS04-01 foundation; approved identity/payment/job/storage invariant inputs. WS04-01D is required only if this work genuinely consumes a D-owned final-production fact. |
| WS04-03 | WS04 | Schema and migration | Migration policy, compatibility, interruption, and production-like rehearsal | 3 | Accepted provider-independent WS04-01 foundation; WS04-02; stable required schema capabilities. Final provider/runtime rehearsal facts remain late-bound. |
| WS05-01 | WS05 | Schema, worker, and deployment | Durable job model, claim/lease lifecycle, and worker deployment | 8 | WS02-02; accepted provider-independent WS04-01 foundation; WS04-02 and WS04-03 source/schema contracts; EN-02. WS04-01D is not a blanket prerequisite and later final DB verification must account for the worker consumers that actually exist. |
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

### 8.1 Final-infrastructure timing map

The pass register above states parent-level ownership and dependency intent. It
must be read together with the final-infrastructure timing rule in Section 3.1.
A prerequisite that names actual provider/topology/runtime evidence blocks only
the portion that genuinely needs that evidence. It does not force permanent
provider selection early when a coherent provider-independent slice can proceed.

The following passes are known in advance to contain infrastructure-dependent
work that Stage 0 must classify, split, or defer when the final production
configuration is not yet available:

| Pass | Provider-independent work that may proceed before final infrastructure | Late-bound production work | Latest required boundary |
|---|---|---|---|
| `WS02-01` | Typed setting names, environment classes, validation, unsafe-default rejection, public/private configuration boundaries | Exact production provider bindings, production URLs/domains, provider secret-injection locations, provider-derived configuration values | Before the final deployed configuration is relied on for production evidence |
| `WS02-02` | Application lifecycle, readiness/liveness, graceful shutdown, release identity, portable runtime contract | Final host/platform, instance/process topology, autoscaling, rolling overlap, provider runtime settings, platform-specific hardening and rollback evidence | Before final runtime/topology proof and any later pass that consumes those facts |
| `WS02-03` | App-owned trusted-proxy/CORS/header ownership contract and provider-neutral tests | Final edge/origin topology, domains, direct-origin exposure, TLS/HSTS/redirect behavior, provider edge/proxy configuration | Before final browser/edge verification and `CLOSE-01` |
| `WS02-05` | HTTP/schema/media/cache/docs/compatibility contracts | Full deployed edge-to-origin chain and final host/runtime observations | Before final release/full-chain evidence and `CLOSE-01` |
| `WS03-03` | Source-owned step-up/recent-auth behavior, provider-failure contract, portable App Check/service-identity expectations | Concrete production Firebase/GCP project/account/IAM/workload-identity/App Check enforcement and provider evidence | Before final provider-access verification and `CLOSE-01` |
| `WS04-01` | Application DB lifecycle, query/access behavior, connection-budget formula/framework, role/grant verification contract | Final PostgreSQL provider/topology, provider capacity, pooler/proxy mode, deployed pool values, final numeric budget/headroom, concrete production roles/grants and runtime proof | Mandatory deferred final DB verification before `CLOSE-01`; earlier only when its trigger is satisfied |
| `WS04-03` | Migration policy, compatibility rules, graph/drift checks, local/controlled rehearsal design | Final provider/runtime-specific migration ceilings, production-like topology evidence, and provider-specific rehearsal facts | Before production migration sign-off and `CLOSE-01` |
| `WS05-01` | Durable job model, claim/lease/heartbeat/retry/crash semantics, worker command contract | Final worker hosting/platform, service topology, scaling/resource settings, provider deployment configuration and runtime proof | Before deployed-worker verification in `WS05-04` |
| `WS05-04` | Deterministic local/sandbox race, replay, crash, timeout and repair proof | Final staging/deployed-worker topology and provider/runtime evidence when that environment depends on the final platform | Before WS05 workstream exit evidence and `CLOSE-01` |
| `WS06-03` | Storage lifecycle/reconciliation state machine, repair behavior, provider-neutral cache/recovery contract | Final production R2 account/bucket/CORS/token/cache/provider settings and provider/runtime recovery evidence | Before final storage/recovery evidence and `CLOSE-01` |
| `WS07-01` | Portable production build, public-configuration interface, artifact/release identity, source-map packaging policy | Final frontend host project/domain/environment bindings, delivery behavior, provider access and source-map exposure proof | Before final release evidence and `CLOSE-01` |
| `WS07-04` | Third-party inventory, CSP/SRI policy, browser-provider failure isolation | Final production domain allowlists, edge/header/CSP bindings and deployed browser/provider evidence | Before final browser-security verification and `CLOSE-01` |
| `WS08-02` | Deterministic unit/service/API/PostgreSQL/browser suites and provider-neutral fixtures | Provider, restore, and full-environment suites that require selected final sandboxes or recovery environments | Before the affected workstream evidence is treated as complete |
| `WS08-03` | Reproducible CI, scans, SBOM/provenance and release-manifest contracts | Final deployment linkage and provider/release evidence that depends on the selected production delivery path | Before final release evidence and `CLOSE-01` |
| `WS09-01` | Structured logging/correlation/redaction code and signal catalog | Final log/observability provider, aggregation/injection/delivery configuration, access/retention settings and provider evidence | Before `WS09-03` final observability evidence |
| `WS09-03` | Metric/SLI definitions, telemetry hooks, provider-neutral capacity model structure | Final dashboards/alerts, delivery routing, exact SLO/launch values that require measurement, provider/storage/database capacity and cost values | After final infrastructure is stable; before `WS10-03` final runbooks and `CLOSE-01` |
| `WS10-02` | Only preparatory inventories/procedures that do not claim live provider state | Actual production provider accounts/topology, MFA/recovery, managed secret injection, rotation/revocation/offboarding and access evidence | Late operational phase; before `WS10-03`, `WS10-04` where consumed, and `CLOSE-01` |
| `WS10-03` | Generic incident roles/severity/process framework where useful | Provider-specific outage procedures, deployed-architecture runbooks and realistic tabletop evidence | After stable deployed architecture; before `CLOSE-01` |
| `WS10-04` | Recovery requirements, evidence schema and rehearsal design where useful | Actual backup/PITR/provider settings, isolated restore, measured RPO/RTO evidence and recovery exercises | Final operational phase; before `CLOSE-01` |
| `CLOSE-01` | None of the required late-bound evidence may be substituted with temporary/demo facts | Reconcile and require completion of every mandatory deferred infrastructure verification unit | Must not begin final evidence completeness with required deferred units still open |

For provider-backed product integrations that are already selected by higher
authority, such as Firebase, Stripe, or R2, this map does not remove the selected
integration. It separates source/application contracts from concrete production
account, plan, role, region, quota, domain, credential, control-plane, and runtime
settings that still require later evidence.

## 9. Detailed pass specifications

### BASE-00: Historical repository baseline and isolation gate

- **Track:** PROGRAM
- **Pass type:** Repository inspection
- **Primary controls:** Program gate; no primary control reassessment
- **Prerequisites:** Historical setup predecessor; current execution-state
  preflight is owned by the read-first document and applicable workflow.
- **Maximum scope:** Historical read-only inspection of branch, status,
  worktrees, stashes, recent history, remotes, and the exact trusted baseline.
  Decide the isolated remediation branch/worktree only after inspection.
- **Required output:** Recorded baseline commit, clean-tree confirmation, protected unrelated work, chosen isolation strategy, and rollback anchor.
- **Proof before acceptance:** Read-only Git output reviewed; no repository mutation before approval.
- **Stop condition:** Stop on a dirty or ambiguous baseline, missing intended merge, unresolved stash/worktree ownership, or uncertainty about the correct source branch.

### GOV-01: Import and reconcile the approved governance package

- **Track:** WS01
- **Pass type:** Decision and governance
- **Primary controls:** GOV-001, GOV-004, GOV-005, GOV-006, GOV-007
- **Prerequisites:** Historical BASE-00 setup result
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

- **Infrastructure timing:** Provider-neutral setting names, validation, environment classes, and safety boundaries may be completed before final hosting is selected. Exact production provider bindings, URLs/domains, secret-injection locations, and provider-derived values remain late-bound.

- **Track:** WS02
- **Pass type:** Domain implementation
- **Primary controls:** GOV-002, API-M01, API-M02
- **Prerequisites:** EN-01, EN-02, EN-03
- **Maximum scope:** Inspect and then implement typed settings, environment bindings, unsafe-default rejection, import/startup behavior, and explicit local/CI/staging/production separation.
- **Required output:** Settings/config changes, current unit/config tests, environment matrix updates, and compatibility notes.
- **Proof before acceptance:** Invalid production configuration fails before readiness; no secret values enter source or artifacts.
- **Stop condition:** Stop if provider topology is unknown, configuration changes alter process/connection counts, or unrelated deployment code is required.

### WS02-02: Runtime process, lifecycle, health, and deployability

- **Infrastructure timing:** Application lifecycle, health, shutdown, release-identity, and portable runtime contracts may proceed without a permanent host. Final provider choice, process/instance topology, autoscaling, rolling overlap, platform-specific hardening, and provider runtime settings are late-bound and must be split/deferred when unavailable.

- **Track:** WS02
- **Pass type:** Deployment foundation
- **Primary controls:** API-M03, API-M17, OPS-001, OPS-002, OPS-003, OPS-004
- **Prerequisites:** WS02-01; DBP-01 policy. Preliminary/final provider topology is required only for the topology-specific verification portion; it does not block a coherent provider-independent child.
- **Maximum scope:** Define runtime command, supervision, worker/instance topology, container/platform hardening, startup/readiness/liveness, graceful shutdown, release identity, rolling overlap, rollback and forward-fix behavior.
- **Required output:** Versioned deployment/runtime configuration, health contract, shutdown handling, deployment tests, and release/rollback record template.
- **Proof before acceptance:** Local or staging-safe lifecycle tests; readiness gates traffic only after dependencies are ready; shutdown releases resources.
- **Stop condition:** Stop if a provider-specific runtime value would be guessed, temporary hosting would be treated as permanent, or a release change cannot be rolled back or forward-fixed. An undecided final runtime provider routes the provider-specific portion to deferred verification rather than blocking portable lifecycle work.

### WS02-03: Proxy, host, TLS, CORS, and response-class security headers

- **Infrastructure timing:** App-owned proxy/CORS/header contracts may proceed provider-independently. Final public domains, edge/origin topology, TLS/HSTS/redirect behavior, direct-origin exposure, and provider edge settings are late-bound.

- **Track:** WS02
- **Pass type:** Configuration and provider verification
- **Primary controls:** API-M04, API-M05, API-M06, API-M07, API-M08
- **Prerequisites:** WS02-01, WS02-02; FDN-02. Actual edge/origin topology is required only for late-bound edge/provider verification.
- **Maximum scope:** Assign edge versus app ownership and implement trusted-proxy, canonical host, TLS redirect/HSTS, CORS, framing, content-sniffing, cache, and response-class header behavior.
- **Required output:** Edge ownership matrix, app/edge configuration, unit/integration tests, and provider-evidence checklist.
- **Proof before acceptance:** Staging header captures, redirect traces, direct-origin behavior, disallowed-origin tests, and proxy-spoof tests.
- **Stop condition:** Stop on conflicting duplicated headers or redirect loops. If direct-origin exposure or provider settings are unknown because final hosting is not selected, keep those facts deferred; do not invent them or treat temporary hosting as final verification.

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

- **Infrastructure timing:** Source-owned HTTP/schema/cache/docs behavior may proceed before permanent hosting is selected. Full deployed edge-to-origin verification and host-specific observations are late-bound.

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

- **Infrastructure timing:** Source-owned authentication and provider-failure contracts may proceed before concrete production provider settings are available. Final production project/account/IAM/workload-identity/App Check settings and provider evidence are late-bound even when the service integration itself is already selected.

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

- **Infrastructure timing:** Provider-independent database lifecycle, access behavior, budget methodology, and role/grant verification framework may proceed before final database hosting is selected. Final PostgreSQL provider/topology, capacity, pooler/proxy mode, deployed pool values, numeric budget/headroom, concrete production roles/grants, and runtime proof are mandatory late-bound verification. Temporary Neon/Render facts are not substitutes.

- **Track:** WS04
- **Pass type:** Database foundation
- **Primary controls:** DB-001, DB-002, DB-003, DB-012, DB-013, DB-015
- **Prerequisites:** WS02-02; DBP-01. Actual PostgreSQL provider/topology is required only for the mandatory late-bound final verification portion.
- **Maximum scope:** Inspect and define engine/session lifecycle, transaction defaults, deployment-wide pool/overflow/wait budget, worker/migration reserve, provider roles/grants, and operational access.
- **Required output:** Provider-independent configuration/code and database-access contracts, connection-budget methodology/framework, role/grant verification plan, current PostgreSQL tests, and provider-evidence contract/checklist; plus the mandatory late-bound final verification unit when its trigger becomes true.
- **Proof before provider-independent acceptance:** Repository-owned lifecycle/access behavior, bounded waits/timeouts, deterministic budget arithmetic with synthetic inputs, and the least-privilege verification contract are proven without inventing final provider values.
- **Proof before full parent verification:** `WS04-01D` proves the actual deployment-wide maximum against final provider capacity/headroom and verifies concrete application/migration/support roles and grants using accepted sanitized provider/runtime evidence.
- **Stop condition:** Do not invent provider limits/process counts or change final pool/provider settings without topology evidence. If final infrastructure is still unselected, Stage 0 must split/defer the provider-specific verification rather than blocking coherent provider-independent work. Stop on routine superuser requirements or any attempt to treat temporary/demo infrastructure as final evidence.

### WS04-02: Transactions, invariants, locks, and deterministic concurrency

- **Track:** WS04
- **Pass type:** Database/domain/concurrency
- **Primary controls:** DB-004, DB-005, DB-006, DB-007, DB-008, DB-009, DB-010, DB-014
- **Prerequisites:** Accepted provider-independent `WS04-01` foundation; approved identity/payment/job/storage invariant inputs. `WS04-01D` is not a blanket prerequisite. If this pass genuinely requires a D-owned final-production fact, stop on that specific prerequisite until D's trigger is satisfied.
- **Maximum scope:** Define transaction and external-side-effect boundaries; add database constraints or deliberate serialization; handle duplicate, winner/loser, retry, deadlock, timeout, and unknown-outcome cases.
- **Required output:** Narrow models/constraints/services, deterministic independent-session tests, and invariant catalog.
- **Proof before acceptance:** Barrier-driven concurrency tests assert final database and external-intent states, cleanup, and retry behavior.
- **Stop condition:** Stop on nondeterministic tests, ambiguous source of truth, external calls inside unsafe transactions, or a required destructive constraint/backfill without migration design.

### WS04-03: Migration policy, compatibility, interruption, and production-like rehearsal

- **Infrastructure timing:** Migration policy, compatibility rules, graph/drift checks, and controlled rehearsal design may proceed provider-independently. Final provider/runtime-specific migration ceilings and production-like topology evidence are late-bound.

- **Track:** WS04
- **Pass type:** Schema and migration
- **Primary controls:** DB-016, DB-017, DB-018
- **Prerequisites:** Accepted provider-independent `WS04-01` foundation; `WS04-02`; stable required schema capabilities. Final provider/runtime-specific rehearsal facts remain late-bound and must not block provider-independent migration policy, compatibility, graph/drift, or controlled-rehearsal work.
- **Maximum scope:** Establish expand-and-contract rules, graph/drift checks, empty/prior-schema upgrades, online-index strategy, timeouts, interruption/resume, old/new compatibility, rollback versus forward-fix, and production-like rehearsal.
- **Required output:** Migration changes and tests, compatibility window, rehearsal plan/results, and forward-fix notes.
- **Proof before acceptance:** Empty and prior-schema upgrades pass; lock/duration/interruption behavior is measured on representative volume.
- **Stop condition:** Stop on blocking/destructive behavior without approval, downgrade assumptions that risk data, or inability to keep old/new versions compatible.

### WS05-01: Durable job model, claim/lease lifecycle, and worker deployment

- **Infrastructure timing:** Durable job semantics and a portable worker command/runtime contract may proceed before final worker hosting is selected. Final worker platform, deployment topology, scaling/resource settings, provider configuration, and runtime proof are late-bound and must be complete before deployed-worker verification.

- **Track:** WS05
- **Pass type:** Schema, worker, and deployment
- **Primary controls:** JOB-M01, JOB-M02, JOB-M03, JOB-M04, JOB-M05, JOB-M06, JOB-M07, JOB-M08
- **Prerequisites:** `WS02-02`; accepted provider-independent `WS04-01` foundation; `WS04-02` and `WS04-03` source/schema contracts; `EN-02`. `WS04-01D` is not a blanket prerequisite for durable-job source/schema work; later final database verification must include the worker connection demand that exists at that time.
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

- **Infrastructure timing:** Deterministic local/sandbox proof may proceed when safe. Any deployed-worker or staging evidence that depends on the final worker platform is late-bound until that environment exists.

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

- **Infrastructure timing:** Storage lifecycle/reconciliation behavior may proceed from the selected storage contract without assuming final production settings. Concrete production account/bucket/CORS/token/cache/provider values and runtime/recovery evidence are late-bound.

- **Track:** WS06
- **Pass type:** Storage lifecycle/provider/runtime
- **Primary controls:** STO-008, STO-009
- **Prerequisites:** WS06-01, WS06-02; DBP-04; OPP-05; WS05-01
- **Maximum scope:** Implement replacement/deletion state, public removal, temporary-original cleanup, abandoned-upload sweep, missing/orphan/divergence reconciliation, safe repair, default-image fallback, usage monitoring, token/CORS/public-access controls, and cache invalidation/expiry strategy.
- **Required output:** Lifecycle/reconciliation jobs, admin repair paths, tests, R2 evidence, and recovery documentation.
- **Proof before acceptance:** Missing object, orphan object, failed deletion, cache stale copy, abandoned upload, and derivative regeneration scenarios are verified.
- **Stop condition:** Stop if automatic deletion is not safely bounded, provider token scope/public access is unknown, or database/object authority is ambiguous.

### WS07-01: Production frontend build, public configuration, artifact identity, and source maps

- **Infrastructure timing:** Build inputs, public-configuration boundaries, artifact identity, and source-map packaging rules may proceed provider-independently. Final hosting project/domain/environment bindings, provider delivery behavior, access, and source-map exposure evidence are late-bound.

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

- **Infrastructure timing:** Third-party inventory, CSP/SRI policy, and failure-isolation behavior may proceed before final hosting/edge selection. Final production domain allowlists, edge/header bindings, and deployed provider/browser evidence are late-bound.

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

- **Infrastructure timing:** Repository/local/sandbox suites may proceed when their environments are honest substitutes for the behavior under test. Provider/restore/full-environment suites that require final selected infrastructure remain late-bound and must not be replaced with temporary demo-provider evidence.

- **Track:** WS08
- **Pass type:** Current tests
- **Primary controls:** TST-005, TST-006, TST-007, TST-008, TST-009
- **Prerequisites:** WS08-01; stable domain implementations; sandbox/restore environments
- **Maximum scope:** Complete risk-based current coverage for auth/admin, payments/jobs, venue storage, database races, migrations, provider boundaries, privacy workflows, and restore verification.
- **Required output:** Layered unit/service/API/PostgreSQL/browser/provider/migration/failure suites and evidence mapping.
- **Proof before acceptance:** Critical races use barriers/independent sessions; provider tests are sandboxed; migration/restore tests use controlled fixtures.
- **Stop condition:** Stop on nondeterminism, production provider use, giant unowned end-to-end tests, or unverified cleanup.

### WS08-03: Reproducible CI, scans, branch protection, SBOM, provenance, and release evidence

- **Infrastructure timing:** CI, scan, SBOM, provenance, and release-manifest contracts may proceed before final hosting selection. Deployment linkage and release/provider evidence that depends on the final delivery path is late-bound.

- **Track:** WS08
- **Pass type:** CI/supply chain/provider
- **Primary controls:** TST-012, TST-013, TST-014, TST-015, TST-016, TST-017
- **Prerequisites:** WS08-01, WS08-02; stable job names and release artifacts; EN-03
- **Maximum scope:** Pin tools/dependencies, validate clean installs, gate suites/build/migrations/security scans, protect secrets/forks, create aggregate required check, generate sanitized artifacts/SBOM/provenance, and verify GitHub branch rules/deployment linkage.
- **Required output:** CI workflows/checkers, scan policy, artifact/release manifest, redacted branch-protection evidence, and sample release package.
- **Proof before acceptance:** Actual CI run records; skipped/failed/canceled/provider-unavailable behavior is explicit; required checks cannot be bypassed silently.
- **Stop condition:** Stop if CI needs production credentials, gates can be skipped without visibility, artifacts leak data, or release identity cannot be tied to source/deployment.

### WS09-01: Structured request/event logging, correlation, redaction, and log aggregation

- **Infrastructure timing:** Logging schemas, correlation, redaction, and signal contracts may proceed provider-independently. Final central logging/observability provider selection, ingestion/delivery configuration, access/retention settings, and provider evidence are late-bound.

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

- **Infrastructure timing:** Signal definitions and provider-neutral capacity-model structure may proceed earlier. Final dashboards/alerts, delivery routing, exact measured objectives, provider/storage/database capacity, cost values, and provider-limit evidence require the final deployment and are late-bound.

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

- **Infrastructure timing:** This is intentionally a late operational/provider pass. It must use the actual selected production providers/accounts/topology and must not treat prototype Vercel/Render/Neon or other temporary environments as final evidence.

- **Track:** WS10
- **Pass type:** Operational/provider
- **Primary controls:** OPS-005, OPS-006, OPS-007, OPS-025
- **Prerequisites:** EN-03; actual provider accounts and hosting topology
- **Maximum scope:** Finalize least-privilege users/roles/service identities, MFA/recovery ownership, managed secret injection, rotation overlap, revocation, break-glass, offboarding, monitoring, and dated redacted evidence across hosting, Firebase/GCP, Stripe, R2, PostgreSQL, DNS, GitHub, monitoring, and backups.
- **Required output:** Completed inventories, procedures, redacted evidence packages, discrepancies, and exercises.
- **Proof before acceptance:** Access review and rotation/revocation/offboarding/lost-factor exercises succeed without exposing secrets.
- **Stop condition:** Stop on missing recovery owner, shared/unattributed privileged access, long-lived unmanaged credentials, or unsafe evidence.

### WS10-03: Incident response, provider-outage handling, and operational runbooks

- **Infrastructure timing:** Generic incident roles/process may be prepared earlier, but final provider-outage runbooks and tabletop evidence must match the stable deployed production architecture and are therefore late-bound.

- **Track:** WS10
- **Pass type:** Operational process/exercise
- **Primary controls:** OPS-013, OPS-014, OPS-015
- **Prerequisites:** WS09-03; stable deployed architecture; named owners
- **Maximum scope:** Define severity, roles, containment, evidence, reconciliation, communication, post-incident actions, and runbooks for API/DB/connection exhaustion/release/migration/jobs/Stripe/R2/Firebase/secrets/certificates/backups/control planes.
- **Required output:** Incident plan, provider-outage matrix, service runbooks, communication templates, and tabletop results.
- **Proof before acceptance:** Tabletops expose alert, access, decision, communication, reconciliation, and recovery gaps; actions have owners/retests.
- **Stop condition:** Stop if runbooks do not match deployed architecture, emergency steps bypass financial/data safeguards, or on-call/decision authority is undefined.

### WS10-04: Backup/PITR evidence, isolated restore, recovery validation, and exercises

- **Infrastructure timing:** Recovery requirements and rehearsal design may be prepared earlier, but actual backup/PITR configuration, restore proof, measured recovery results, and provider-specific exercises are late-bound until final production infrastructure exists.

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

## 11. Current pass workflow routing

Current pass execution is owned by the durable workflow documents, not by the
historical inspection-to-prompt lifecycle that produced the original blueprint.
Use this blueprint for parent-pass scope, sequencing, dependencies,
infrastructure timing, and completion expectations, then route execution through:

```text
Stage 0
-> Gate A planning
-> Gate A review
-> Gate B
-> Gate C review
-> Gate D
-> open PR for manual merge
```

Use `PASS-IMPLEMENTATION-WORKFLOW.md` for first-time implementation and
`PASS-RECHECK-WORKFLOW.md` for accepted or historical-pass rechecks. Do not
duplicate the full gate mechanics here.

The durable engineering requirements from the historical lifecycle remain
binding through those workflows:

- verify dependencies, accepted decisions, Git state, evidence availability,
  rollback/abort criteria, exact control IDs, and the infrastructure-timing
  classification from Sections 3.1 and 8.1 before implementation;
- inspect current repository truth and affected files before editing;
- keep the scope narrow to the selected parent/child pass and its frozen Gate A
  design;
- identify provider-independent work, final-infrastructure-dependent work, and
  any mandatory deferred follow-up with owner, trigger, preserved obligations,
  dependencies, and latest completion boundary;
- stop rather than guess on unresolved authority, unsafe provider/runtime/data
  actions, sensitive evidence, destructive migrations, ambiguous source of
  truth, or any attempt to choose final infrastructure prematurely;
- review the actual diff and relevant full files against authority, privacy,
  security, evidence, migration, compatibility, and no-unrelated-cleanup
  requirements;
- record commits, changed files, validation, migration head where applicable,
  provider/runtime evidence still outstanding, known limitations, and
  rollback/forward-fix instructions only through the workflow stage that owns
  publication;
- remember that control status remains unresolved until formal reassessment.

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
- Do not make permanent provider-specific configuration changes until the relevant final provider/topology is selected and the late-bound trigger is satisfied. Temporary Vercel/Render/Neon or other demo infrastructure does not satisfy that trigger.
- A provider integration already selected by higher authority may keep its source/application contract, but concrete production account, plan, region, quota, domain, credential, role, and control-plane settings remain evidence-bound.
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

1. The current accepted baseline cannot be verified or the active source branch
   is not the trusted intended baseline required by the workflow.
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
16. A pass attempts to select final production infrastructure merely to satisfy its own completion criteria.
17. Temporary/demo/free-tier/local/example provider values are being treated as final production configuration or evidence.
18. A final-infrastructure-dependent obligation has no named deferred owner, activation trigger, or latest required completion boundary.

## 15. Final closure sequence

1. Complete provider-independent repository, database, migration, configuration, and operational-document work.
2. Select and freeze the final production hosting/database/edge/worker/observability/recovery topology when the application and launch architecture are stable enough to make that decision honestly.
3. Activate and complete every mandatory deferred infrastructure/provider verification unit, including final production settings, numeric values, roles/grants, provider evidence, and runtime observations.
4. Execute applicable current non-legacy unit, service, API, PostgreSQL, concurrency, browser, provider, migration, failure, privacy, and recovery tests against the correct evidence layers.
5. Enforce reproducible CI, scans, required checks, artifacts, and supply-chain gates.
6. Collect redacted provider and repository-protection evidence.
7. Perform staged runtime verification against the final selected topology.
8. Rehearse migrations and deterministic concurrency.
9. Prove backup/PITR access and isolated restore.
10. Complete incident and recovery exercises.
11. Run `CLOSE-01` only after the mandatory deferred-infrastructure sweep confirms no required late-bound unit remains open.
12. Reassess all 163 controls from fresh evidence.
13. Issue production-readiness sign-off only when every applicable P0 is closed or governed by an approved time-bound exception and all launch conditions are satisfied.

## 16. Current execution entry

Do not restart the current program from historical `BASE-00` or `GOV-01`
instructions in this blueprint. Those entries remain provenance and parent-pass
structure.

For current work, determine execution state from current accepted repository
truth, `00-READ-ME-FIRST.md`, `PASS-EXECUTION-REGISTER.md`, and the current run
instruction. Then use the applicable workflow:

- first-time implementation routes through Stage 0, Gate A planning/review, Gate
  B, Gate C review, Gate D, and an open PR for manual merge;
- accepted or historical implementation rechecks route through the recheck
  workflow;
- mutable current state, branches, SHAs, PRs, and resume position belong in the
  execution register, frozen pass artifacts, local handoff when used, and
  current workflow state, not in this blueprint.
