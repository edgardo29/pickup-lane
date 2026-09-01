# Pickup Lane Master Production-Readiness Blueprint

**Status:** Durable master execution blueprint

**Original planning date:** August 3, 2026

**Implementation authorization:** None. This document plans the work. It does not authorize code, Git, provider, deployment, migration, database, worker, storage, monitoring, backup, restore, or CI changes.

## 1. Program status routing

This blueprint is durable program authority for planned parent-pass scope, ordering,
dependencies, infrastructure timing, and completion expectations. It does not maintain
mutable branch, SHA, PR, current-pass, worktree, or trigger state.

Determine current execution state from current accepted repository truth and
`docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md`, using the
startup and authority rules in `docs/production-readiness/00-READ-ME-FIRST.md`. Do not
use the original August 3 planning snapshot, historical branch/merge notes, old
prompts, alphabetical order, or filename order as current execution state.

The durable planning baseline remains:

- the locked audit contains **163 controls**, including **117 unresolved P0 controls**
  and **29 confirmed P0 failures** at the time of the original audit;
- the finalized remediation plan organizes the work into **WS01 through WS10** and
  requires phased implementation, current tests, provider evidence, runtime
  verification, and recovery evidence;
- all **27 owner decisions are approved**, with **0 open owner decisions**;
- implementation progress is tracked outside this section and may advance without
  rewriting the blueprint's historical planning counts.

This document defines parent-level responsibilities and dependency intent. It does not
predefine future executable children. For every parent not already decomposed in an
accepted intake, Stage 0 remains the sole process that decides whether the parent
executes whole, is divided into executable children, has a mandatory deferred
follow-up, or must stop on a real prerequisite or owner decision.

## 2. Authority order

Use the authority model in `docs/production-readiness/00-READ-ME-FIRST.md`.

Requirement authority is, in order:

1. the six locked audit reports and the 163-control checklist;
2. the finalized production-readiness remediation plan;
3. approved decision records and the final decision inventory;
4. this master blueprint;
5. the accepted Stage 0 intake and frozen Gate A plan for the current executable pass,
   within their authorized scope;
6. the current run instruction, within the scope authorized by higher authority.

Current accepted source, configuration, schemas, migrations, tests, and tracked
artifacts establish what currently exists and how the implementation currently
behaves. They do not become product or production-readiness requirement authority
merely because they are present in the repository.

The execution register is accepted-state navigation and dependency bookkeeping. It is
not product authority. Current branch, baseline, worktree, staged state, PR state, and
trigger state must be verified from current repository truth and the active run.

When current implementation conflicts with authoritative requirements, treat that as
an implementation mismatch to reconcile. Do not rewrite the requirement to match the
existing implementation unless higher authority explicitly changes it.

Stop when two authoritative records conflict. Do not guess, silently reinterpret one
as lower priority, or use current code to resolve a requirement conflict.

## 3. Fixed decisions versus later technical values

The architectural and product direction is settled. The following items remain later
**technical design or evidence-based values**, not reopened owner decisions:

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
late-bound. Current Vercel, Render, and Neon usage is prototype/demo infrastructure,
not a permanent production-architecture decision. Temporary free-tier, preview,
local, demo, or example settings must never be promoted into final production
assumptions merely because a pass needs a value.

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
source-owned security behavior, formulas, evidence schemas, portability contracts,
deterministic local/synthetic tests, and provider-neutral failure handling. A value
that is genuinely application-owned and justified from provider-independent evidence
does not need to wait merely because it is numeric.

When a parent contains both provider-independent and final-infrastructure-dependent
work, Stage 0 must determine the executable boundary under the implementation
workflow. It must not force an early provider choice, treat temporary infrastructure
as final evidence, or block unrelated provider-independent work.

Every mandatory deferred follow-up created by Stage 0 must record:

- one owning executable unit;
- the exact preserved controls, requirements, and evidence obligations;
- its prerequisites;
- the exact activation trigger;
- downstream consumers;
- the latest required completion boundary.

Temporary provider values are not substitutes. Deferred work is not proof and does
not close the underlying control. Run it as soon as its trigger is satisfied and no
later than the first downstream consumer that genuinely requires it or `CLOSE-01`,
whichever comes first.

### 3.2 Dependency interpretation and Stage 0 ownership

Parent-level prerequisite text can describe several different engineering
relationships. Stage 0 must distinguish them before deciding the executable shape:

- a completed pass or child required by all of the proposed executable work;
- an accepted contract, invariant, decision, or design input that does not require
  the producing parent to be complete;
- a prerequisite that applies to only one responsibility inside the parent;
- a dependency that exists only if a particular implementation approach is selected;
- a final-provider, runtime, sandbox, restore, or other evidence prerequisite that
  applies only to the work claiming that evidence.

A parent-level dependency must not be applied as a blanket blocker when it applies
only to part of the parent. A broad phrase such as `WS02 foundation`, `stable event
models`, `WS05 durable notice path design`, or `WS09 observability` must be resolved
during Stage 0 to the exact accepted contract or missing capability that the proposed
executable work consumes.

The blueprint may identify a known dependency distinction or an apparent
cross-workstream conflict so Stage 0 does not miss it. It must not invent future child
IDs, freeze a future decomposition, or replace the intake decision. Exact child
structure, ordering, no-gap/no-overlap allocation, and deferred follow-up creation
remain Stage 0 responsibilities.

Before accepting an intake, Stage 0 must verify that the proposed executable
dependency graph has no unresolved direct or indirect cycle. When two parent rows
appear circular, Stage 0 must determine whether the relationship is actually
contract-only, responsibility-specific, conditional, or late-bound. If durable
authority does not resolve that distinction, stop for a program-document correction
or owner decision rather than guessing.

## 4. Repository baseline and Git workflow

This section records durable repository-safety expectations and historical setup
structure. It does not maintain current branch, SHA, PR, worktree, or pass state.
Current execution-state verification is owned by `00-READ-ME-FIRST.md`,
`PASS-EXECUTION-REGISTER.md`, and the applicable workflow.

### 4.1 Baseline verification

Before an authorized pass mutates files, use the applicable workflow to verify the
current accepted baseline, branch, worktree/index state, remote relationship, and
changed-file scope.

The baseline verification must establish:

- the current branch and exact accepted baseline;
- a clean or explicitly understood working tree and index;
- all worktrees and their owners;
- all stashes and whether they contain intended work;
- recent branch/merge history;
- remote tracking and whether local `develop` is current when the workflow requires
  it;
- frozen artifact paths and SHAs when applicable;
- that production-readiness documents are included only when the current scope
  authorizes them.

Unexpected local work, divergence, or branch ambiguity causes a stop. Do not
automatically reset, rebase, merge, stash, restore, clean, or delete anything.

### 4.2 Intended isolation model

The historical preferred layout was:

```text
pickup-lane/                         trusted current development checkout
pickup-lane-production-readiness/    isolated remediation worktree
```

Current workflows may use the active checkout or a separate worktree, but every
executable pass still uses an explicit branch and one narrow reviewable change set.
A later child starts from current accepted `develop` after required earlier children
merge.

### 4.3 Git rules

1. Start every pass from the accepted baseline required by the applicable workflow.
2. Do not mix unrelated feature, documentation, process, dependency, or cleanup work
   with production-readiness remediation.
3. Include the pass ID in the branch, commit, pull request, evidence record, and
   review notes.
4. A parent may be divided only through Stage 0 or an explicit structural correction;
   it may not be broadened or silently combined with another parent.
5. Do not begin a dependent executable unit until the current unit is accepted,
   corrected, or reverted.
6. Database migrations, provider changes, and destructive operations require explicit
   rollback or forward-fix plans before execution.
7. Sensitive provider evidence is not committed to normal source control.
8. Gate D must exclude unrelated carryover and follow the changed-file boundary
   approved by Gate C.
9. Automated progression may select the next unit only when durable authority,
   accepted dependency state, trigger state, and current repository truth determine
   exactly one safe route.

## 5. Program gates

The table below records durable high-level program gates and historical setup state.
It is not the current per-pass execution workflow. Current production-readiness work
routes through `PASS-IMPLEMENTATION-WORKFLOW.md` or `PASS-RECHECK-WORKFLOW.md`.

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

These are workstream-level sequencing gates. They do not convert every named
workstream into a blanket whole-parent prerequisite. Stage 0 must resolve the exact
contract and responsibility needed by the selected parent.

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

The phase order is dependency-based, not a simple WS02, WS03, WS04 sequence and not a
rule that one entire workstream must finish before another begins:

1. **WS01** governance is versioned first.
2. Early **WS08**, **WS09**, and **WS10** enabling work establishes test isolation,
   correlation/redaction, and safe provider-evidence handling.
3. **WS02** establishes the production configuration and deployment foundation.
4. **WS03** identity/authorization and **WS04** database/concurrency may proceed in
   controlled parallel work after the contracts needed by each executable unit are
   stable.
5. **WS05** implements the shared durable-job foundation before payment and other
   durable consumers.
6. **WS06** follows the applicable database, job, and admin-authority contracts for
   venue-image processing and R2 lifecycle work.
7. **WS07** validates the frontend against stable API and identity contracts.
8. **WS08** and **WS09** finish their current-test, CI/release, audit, and production-
   observability gates when the implementations and evidence environments they verify
   are stable.
9. **WS10** completes privacy, secrets, incident response, restore, and recovery work
   when its source and final-provider prerequisites are satisfied.
10. A fresh control reassessment follows. Implementation alone never equals closure.

Parent numbering expresses program organization, not an automatic serial execution
order. Cross-workstream design inputs and reusable contracts may be needed before a
later parent is complete. Responsibility-specific or late-bound dependencies must not
be converted into whole-parent blockers.

Stage 0 uses this ordering, the parent register below, the remediation plan, accepted
intakes and plans, the execution register, and current repository truth to decide the
actual executable boundary. This section does not preapprove future child IDs or
decompositions.

## 8. Planned implementation-pass register

This blueprint contains the original **42 parent-level planned passes**. Stage 0 may
decompose a selected parent into executable children or mandatory deferred
follow-ups after inspecting current repository truth and the applicable
prerequisites. Nothing in this parent register preapproves a future child ID or
decomposition.

The dependency column records parent-level intent. Stage 0 must apply Section 3.2
before treating any item as a whole-parent blocker.

| Pass | Track | Type | Title | Primary control count | Dependencies and Stage 0 interpretation |
|---|---|---|---|---:|---|
| BASE-00 | PROGRAM | Repository inspection | Repository baseline and isolation gate | 0 | Historical setup predecessor only. Current execution-state preflight is owned by `00-READ-ME-FIRST.md` and the applicable workflow. |
| GOV-01 | WS01 | Decision and governance | Import and reconcile the approved governance package | 5 | Historical `BASE-00` setup result. |
| EN-01 | WS08 | Test infrastructure | Early current-test taxonomy and isolation baseline | 5 | `GOV-01`. |
| EN-02 | WS09 | Architecture contract | Early correlation, event-envelope, and redaction contract | 2 | `GOV-01`. |
| EN-03 | WS10 | Operational/provider foundation | Early secrets, control-plane access, and evidence-handling foundation | 4 | `GOV-01`. |
| WS02-01 | WS02 | Domain implementation | Typed settings and environment isolation | 3 | `EN-01`, `EN-02`, and `EN-03`. |
| WS02-02 | WS02 | Deployment foundation | Runtime process, lifecycle, health, and deployability | 6 | `WS02-01` and DBP-01. Final provider/topology facts apply only to work that claims final topology or runtime evidence; Stage 0 must not treat them as a blanket blocker for portable lifecycle work. |
| WS02-03 | WS02 | Configuration and provider verification | Proxy, host, TLS, CORS, and response-class security headers | 5 | `WS02-01`, the applicable source-owned runtime contract from `WS02-02`, and FDN-02. Final edge/origin facts apply only to final provider verification. |
| WS02-04 | WS02 | Domain implementation | Request limits, timeouts, rate controls, and stable errors | 4 | `WS02-01`, `EN-02`, and the approved evidence-based limit method. |
| WS02-05 | WS02 | Domain implementation and runtime verification | HTTP contracts, schemas, docs, cache, and end-to-end chain | 5 | The applicable source contracts from `WS02-03`, `WS02-04`, and FDN-03. Final edge-to-origin topology applies only to full deployed-chain evidence. |
| WS03-01 | WS03 | Domain implementation | Identity authority and verifier-controlled field protection | 7 | `WS02-01`, the applicable source-owned HTTP contract from `WS02-05`, and IDB-01 through IDB-03. |
| WS03-02 | WS03 | Schema, migration, and domain implementation | Provisioning, account-state lifecycle, and concurrent first login | 3 | `WS03-01` plus the accepted WS04 database-lifecycle, transaction, and invariant design inputs required by the selected scope. This does not require the entire WS04 parents or late-bound provider proof to be complete. |
| WS03-03 | WS03 | Provider/security implementation | High-risk authentication and Firebase control verification | 3 | `WS03-01`, `EN-03`, and IDB-04. Concrete production Firebase/GCP settings and evidence apply only to the final provider-dependent scope. |
| WS03-04 | WS03 | Domain implementation and current tests | Complete authorization matrix and negative proof | 5 | `WS03-01`, `WS03-02`, and stable resource/state contracts for the surfaces being reviewed. |
| WS03-05 | WS03 | Schema/domain/privacy implementation | Moderation states, safe notices, and minimum-necessary admin data | 7 | `WS03-04`, the applicable `WS04-02` transaction/invariant contracts, and OPP-03. Durable notice work may consume the accepted provider-independent job/handoff contract from `WS05-01`. Audited moderation or sensitive-read responsibilities may require an append-only audit capability from `WS09-02`, but `WS09-02` parent completion is not a blanket prerequisite for the whole parent. Stage 0 must resolve the exact responsibility-level dependencies without creating a cycle. |
| WS04-01 | WS04 | Database foundation | Database engine/session lifecycle, connection budget, and least-privilege roles | 6 | The applicable portable runtime contract from `WS02-02` and DBP-01. Actual PostgreSQL provider/topology facts apply only to final verification. |
| WS04-02 | WS04 | Database/domain/concurrency | Transactions, invariants, locks, and deterministic concurrency | 8 | The accepted provider-independent `WS04-01` foundation plus approved identity, payment, job, and storage invariant inputs. A `WS04-01D` fact is required only when the selected scope genuinely consumes that final-production fact. |
| WS04-03 | WS04 | Schema and migration | Migration policy, compatibility, interruption, and production-like rehearsal | 3 | The accepted provider-independent `WS04-01` foundation, `WS04-02`, and stable required schema capabilities. Final provider/runtime rehearsal facts apply only to final production-like evidence. |
| WS05-01 | WS05 | Schema, worker, and deployment | Durable job model, claim/lease lifecycle, and worker deployment | 8 | The applicable portable runtime contract from `WS02-02`, accepted provider-independent `WS04-01`, `WS04-02` and `WS04-03` source/schema contracts, and `EN-02`. Final worker hosting/topology applies only to final deployment and runtime proof. Applicable WS09/WS10 centralized observability and operations contracts are responsibility-specific inputs only to final verification that claims them, not prerequisites for provider-independent source observability or repair/operator work. |
| WS05-02 | WS05 | Financial domain implementation | Payment and booking state machines with webhook authority | 8 | The provider-independent durable-job foundation from `WS05-01`, `WS04-02`, DBP-02, and `WS03-04`. |
| WS05-03 | WS05 | Durable financial/notification workflows | Refunds, credits, notices, moderation delivery, and reconciliation | 7 | The provider-independent `WS05-01` foundation and `WS05-02` apply to the financial workflow responsibilities. The accepted `WS03-05` moderation/safe-notice contract applies only to moderation and administrative-notice delivery responsibilities. Append-only audit capability applies to the privileged actions that require it. Stage 0 must not treat `WS03-05` as a blanket prerequisite for unrelated financial work. |
| WS05-04 | WS05 | Concurrency/failure/provider/runtime verification | Deterministic failure, replay, sandbox, and deployed-worker verification | 23 | The applicable completed WS05 source responsibilities for each scenario. Stripe sandbox availability is required only for sandbox evidence. Final worker hosting and a deployed worker environment are required only for deployed-runtime evidence. Applicable WS09/WS10 contracts or evidence apply only to selected final JOB-M08 verification that claims centralized operational surfaces. Stage 0 must decide the executable shape from the evidence environments actually available. |
| WS06-01 | WS06 | Storage domain implementation | Admin-only venue-image authority and upload initiation | 3 | The applicable accepted WS02 source foundation, the active-admin authorization contract, and DBP-03. Final R2 account or public-access evidence is not a prerequisite for source-owned upload authority unless the selected scope claims that provider behavior. |
| WS06-02 | WS06 | Storage processing implementation | Venue-image validation, sanitization, re-encoding, and derivatives | 4 | `WS06-01`, DBP-03, and evidence-based file limits. The provider-independent durable-job foundation from `WS05-01` is required only if Stage 0 or Gate A selects asynchronous processing. |
| WS06-03 | WS06 | Storage lifecycle/provider/runtime | R2 lifecycle, deletion, cache behavior, reconciliation, and recovery | 2 | `WS06-01`, `WS06-02`, DBP-04, OPP-05, and the provider-independent durable-job contract when required by the selected design. Final R2 configuration and runtime/recovery evidence apply only to the scope that claims those facts. |
| WS07-01 | WS07 | Frontend/build/release | Production frontend build, public configuration, artifact identity, and source maps | 2 | The applicable source-owned `WS02-02` and `WS02-05` contracts, FDN-06, and OPP-02. Final hosting project/domain/delivery facts apply only to final binding and exposure evidence. |
| WS07-02 | WS07 | Frontend/browser | Authentication persistence, identity-scoped state, logout, switch, and safe retries | 3 | The source-owned `WS03-01` through `WS03-03` contracts and IDB-01. |
| WS07-03 | WS07 | Frontend/browser | Routes, API errors, forms, URLs, browser storage, and resilient UI state | 4 | `WS02-04`, the source-owned `WS02-05` contracts, stable backend authorization/error contracts, and the applicable identity-scoped storage/retry contract from `WS07-02`. Stage 0 must allocate overlapping browser-state responsibilities without duplication. |
| WS07-04 | WS07 | Frontend security/provider | Third-party browser code, CSP/SRI posture, headers, and provider failure isolation | 2 | The applicable source-owned `WS02-03` contract, IDB-05, and the actual Firebase/Stripe browser dependency inventory. Final domains and edge/header behavior apply only to final deployed evidence. |
| WS07-05 | WS07 | Frontend/accessibility/performance | WCAG 2.2 AA, browser support, and performance verification | 2 | The applicable accepted source contracts from `WS07-01` through `WS07-04`, `EN-01`, OPP-01, and OPP-02. Final-host measurements apply only to performance claims that require that environment. Stage 0 decides whether the outcomes form one safe executable unit. |
| WS08-01 | WS08 | Test infrastructure | Complete current-test inventory, fixtures, and control mapping | 6 | `EN-01` and stable outputs from the specific WS02 through WS07 surfaces being inventoried; not blanket completion of every parent in those workstreams. |
| WS08-02 | WS08 | Current tests | Critical workflow, deterministic concurrency, migration, provider, privacy, and recovery suites | 5 | `WS08-01` and the applicable stable domain implementation. Provider sandbox, restore, or full-environment availability applies only to the evidence family that uses it. Stage 0 must not let one unavailable evidence environment block independently valid evidence work. |
| WS08-03 | WS08 | CI/supply chain/provider | Reproducible CI, scans, branch protection, SBOM, provenance, and release evidence | 6 | The applicable `WS08-01`/`WS08-02` outputs, stable job names and release artifacts, and `EN-03`. Final deployment linkage and repository/provider settings apply only to the evidence that claims them. |
| WS09-01 | WS09 | Observability implementation | Structured request/event logging, correlation, redaction, and log aggregation | 3 | `EN-02` and stable event/release context for the sources being instrumented. Applicable data-classification, minimization, and retention contracts must be consumed when configuring final access/retention behavior. Final logging-provider facts apply only to provider/runtime proof. |
| WS09-02 | WS09 | Database/domain/privacy | Append-only administrative audit trail and sensitive-access controls | 6 | `WS03-04`, `WS04-02`, and OPP-11 are prerequisites for reusable append-only audit behavior. Domain-specific audit catalog entries and sensitive-read/unmask/export coverage may consume accepted contracts from `WS03-05` and privileged actions from `WS05-03`. Those downstream domain contracts are responsibility-specific inputs, not blanket prerequisites for all WS09-02 work. Stage 0 must resolve the boundary without creating a `WS03-05`/`WS09-02` cycle. |
| WS09-03 | WS09 | Observability/operations | Metrics, service objectives, dashboards, alerts, capacity, and cost evidence | 4 | The applicable accepted `WS09-01` and `WS09-02` contracts, stable signal producers from the relevant WS02 through WS06 areas, OPP-09, and OPP-10. Provider-neutral WS10-03 incident ownership, escalation, and runbook-link conventions apply only to alert-delivery responsibilities that consume them and do not require WS10-03 parent completion. Final observability provider, measurements, alert delivery, capacity, and cost facts apply only to final evidence. |
| WS10-01 | WS10 | Privacy/retention/schema | Data classification, table lifecycle, retention, privacy, and audit lifecycle | 6 | Stable applicable data models from WS03 through WS06 and OPP-07, OPP-08, and OPP-11. Logging, audit, and recovery consumers may depend on this pass's outputs, but those downstream uses must not be turned into a circular blanket prerequisite on this whole parent. Actual provider-backed restore and restored-system deletion/anonymization proof remain owned by WS10-04. |
| WS10-02 | WS10 | Operational/provider | Secrets, provider control-plane access, MFA, rotation, revocation, and offboarding | 4 | `EN-03` plus actual selected production provider accounts/topology for claims about live access, MFA, rotation, revocation, and offboarding. Preparatory records may proceed only when they are independently useful and do not claim live provider state. |
| WS10-03 | WS10 | Operational process/exercise | Incident response, provider-outage handling, and operational runbooks | 3 | Named owners and stable source workflow contracts are required for provider-neutral planning. Applicable accepted WS09-03 dashboard, alert-definition, routing, and delivery contracts, stable deployed architecture, and actual provider topology apply only to final provider-specific runbooks and exercises that consume them; WS09-03 parent completion is not a prerequisite for provider-neutral WS10-03 work. Stage 0 must distinguish those prerequisite states. |
| WS10-04 | WS10 | Recovery/provider/runtime | Backup/PITR evidence, isolated restore, recovery validation, and exercises | 5 | OPP-04 through OPP-06 and stable data/workflow requirements are required for recovery design. The applicable accepted WS10-01 lifecycle/deletion/replay contract, rather than WS10-01 whole-parent completion, plus applicable accepted WS10-02/WS10-03 outputs, a stable release, final observability, final provider configuration, and an isolated restore environment apply to actual recovery proof. Stage 0 must distinguish those prerequisite states. |
| CLOSE-01 | PROGRAM | Audit preparation | Cross-workstream evidence completeness and discrepancy sweep | 0 | All workstream exit gates and every mandatory deferred obligation must be complete or truthfully resolved. |
| CLOSE-02 | PROGRAM | Independent reassessment | Fresh 163-control reassessment and production-readiness decision | 0 | `CLOSE-01` and all correction/retest passes. |

### 8.1 Final-infrastructure timing map

The parent register above must be read together with the final-infrastructure rule in
Section 3.1. The entries below identify work that may proceed before final infrastructure and
work that requires final provider/runtime facts so Stage 0 does not discover the
distinction only after Gate B begins.

This table does not prescribe a child structure. Stage 0 must still decide whether the
parent remains one executable pass, needs executable children, needs a mandatory
deferred follow-up, or is blocked. The decision must be based on current repository
truth, prerequisite state, rollback safety, evidence environment, and the intake
template.

| Pass | Work that may proceed before final infrastructure | Late-bound work | Latest required boundary |
|---|---|---|---|
| WS02-01 | Typed settings, environment classes, validation, unsafe-default rejection, public/private configuration boundaries | Exact production provider bindings, URLs/domains, secret-injection locations, provider-derived values | Before final deployed configuration is relied on for production evidence |
| WS02-02 | Application lifecycle, readiness/liveness, graceful shutdown, release identity, portable runtime contract | Final host/platform, instance/process topology, autoscaling, rolling overlap, provider runtime settings, platform hardening and rollback evidence | Before final runtime/topology proof and any consumer that requires those facts |
| WS02-03 | App-owned trusted-proxy/CORS/header ownership and source behavior | Final edge/origin topology, domains, direct-origin exposure, TLS/HSTS/redirect behavior, provider edge/proxy configuration | Before final browser/edge verification and `CLOSE-01` |
| WS02-05 | HTTP/schema/media/cache/docs/compatibility contracts | Full deployed edge-to-origin chain and final host/runtime observations | Before final release/full-chain evidence and `CLOSE-01` |
| WS03-03 | Source-owned step-up/recent-auth behavior, provider-failure contract, portable App Check/service-identity expectations | Concrete production Firebase/GCP project/account/IAM/workload-identity/App Check enforcement and evidence | Before final provider-access verification and `CLOSE-01` |
| WS04-01 | Application DB lifecycle, query/access behavior, connection-budget method, role/grant verification contract | Final PostgreSQL provider/topology/capacity/pooler, deployed values, numeric budget/headroom, concrete roles/grants, runtime proof | Mandatory final DB verification before `CLOSE-01`, or earlier when consumed |
| WS04-03 | Migration policy, compatibility, graph/drift checks, controlled rehearsal design | Final provider/runtime ceilings, production-like topology evidence, final rollout rehearsal | Before production migration sign-off and `CLOSE-01` |
| WS05-01 | Durable job model, claim/lease/heartbeat/retry/crash semantics, source-owned job signals and repair/operator visibility, portable worker command | Final worker host/platform/topology/scaling/resources/provider deployment and runtime proof; centralized log aggregation, dashboards, alert delivery, and operational runbooks owned by applicable WS09/WS10 work | Before deployed-worker or final JOB-M08 verification in WS05-04 that requires those facts |
| WS05-04 | Deterministic local and safe sandbox verification | Final staging/deployed-worker topology and runtime evidence | Before WS05 workstream exit and `CLOSE-01` |
| WS06-03 | Storage lifecycle/reconciliation/repair and provider-neutral cache/recovery contract | Final R2 account/bucket/CORS/token/cache/provider settings and runtime/recovery evidence | Before final storage/recovery evidence and `CLOSE-01` |
| WS07-01 | Portable production build, public-config interface, artifact identity, source-map packaging | Final frontend host/domain/environment bindings, delivery behavior, provider access and source-map exposure proof | Before final release evidence and `CLOSE-01` |
| WS07-04 | Third-party inventory, CSP/SRI policy, browser-provider failure isolation | Final production domain allowlists, edge/header/CSP bindings and deployed evidence | Before final browser-security verification and `CLOSE-01` |
| WS08-02 | Deterministic repository/PostgreSQL/browser suites and provider-neutral fixtures | Provider, restore, and full-environment suites requiring selected safe environments | Before affected evidence is treated as complete |
| WS08-03 | Reproducible CI, scans, SBOM/provenance and release-manifest contracts | Final deployment linkage, branch-protection, and provider/release evidence | Before final release evidence and `CLOSE-01` |
| WS09-01 | Structured logging/correlation/redaction code and signal catalog | Final logging provider, aggregation/delivery configuration, access/retention, log-loss proof | Before WS09-03 final observability evidence |
| WS09-03 | Metric/SLI definitions, instrumentation, provider-neutral capacity model | Final dashboards/alerts/routing, measured objectives, provider limits, capacity and cost values | After final infrastructure is stable; before WS10-03 final runbooks and `CLOSE-01` |
| WS10-01 | Data lifecycle and deletion/anonymization requirements, provider-copy lifecycle rules, tombstone/replay/reapplication behavior, and source-level or synthetic proof | Actual final-provider lifecycle evidence where provider behavior is claimed; actual provider-backed restore and restored-system deletion/anonymization proof remain owned by WS10-04 | Before the affected provider-lifecycle or recovery evidence is treated as complete and `CLOSE-01` |
| WS10-02 | Preparatory inventories/procedures that do not claim live provider state | Actual production provider accounts/topology, MFA/recovery, secret injection, rotation/revocation/offboarding evidence | Late operational phase; before consumers and `CLOSE-01` |
| WS10-03 | Generic incident roles/severity/process, escalation behavior, runbook-link conventions, and scenario catalog | Provider-specific outage runbooks, on-call routing, deployed-architecture tabletops consuming applicable accepted WS09-03 contracts | After stable deployed architecture; before `CLOSE-01` |
| WS10-04 | Recovery requirements, evidence schema, rehearsal design | Actual backup/PITR settings, isolated restore, measured recovery results and exercises | Final operational phase; before `CLOSE-01` |
| CLOSE-01 | No required late-bound evidence can be substituted | Reconcile and require every mandatory deferred unit | Must not start with required deferred units open |

## 9. Detailed pass specifications

### BASE-00: Repository baseline and isolation gate

- **Track:** PROGRAM
- **Pass type:** Repository inspection
- **Primary controls:** Program gate; no primary control reassessment
- **Prerequisites:** Historical setup predecessor only. Current execution-state preflight is owned by `00-READ-ME-FIRST.md` and the applicable workflow.
- **Maximum scope:** Historical read-only inspection of branch, status, worktrees, stashes, recent history, remotes, and the exact trusted baseline. Decide the isolated remediation branch/worktree only after inspection.
- **Required output:** Recorded baseline commit, clean-tree confirmation, protected unrelated work, chosen isolation strategy, and rollback anchor.
- **Proof before acceptance:** Read-only Git output reviewed; no repository mutation before approval.
- **Stop condition:** Stop on a dirty or ambiguous baseline, missing intended merge, unresolved stash/worktree ownership, or uncertainty about the correct source branch.

### GOV-01: Import and reconcile the approved governance package

- **Track:** WS01
- **Pass type:** Decision and governance
- **Primary controls:** GOV-001, GOV-004, GOV-005, GOV-006, GOV-007
- **Prerequisites:** Historical `BASE-00` setup result.
- **Maximum scope:** Add only the approved WS01 governance documents and root README linkage to the isolated remediation branch. Reconcile the 27 approved decisions and 0 open decisions without changing locked audit findings.
- **Required output:** Versioned governance package, decision registers, ownership, limits method, audit process, risk/exception process, and source links.
- **Proof before acceptance:** Document review, control-ID reconciliation, and no code/config/provider changes.
- **Stop condition:** Stop if the repository version differs from the approved documents, a decision appears reopened, or the change includes unrelated files.

### EN-01: Early current-test taxonomy and isolation baseline

- **Track:** WS08
- **Pass type:** Test infrastructure
- **Primary controls:** TST-001, TST-003, TST-004, TST-010, TST-011
- **Prerequisites:** `GOV-01`.
- **Maximum scope:** Define current non-legacy suite categories, environment boundaries, synthetic-data rules, fixture cleanup, DB-name guards, provider-sandbox separation, flake handling, and artifact sanitization. Do not add broad domain coverage yet.
- **Required output:** Test taxonomy, directory/tag/config convention, fixture-safety checks, and self-tests.
- **Proof before acceptance:** Checker/self-tests demonstrate correct suite discovery, wrong-DB rejection, cleanup, and artifact sanitization.
- **Stop condition:** Stop if the harness would use production resources, count legacy tests as current evidence, or require unstable domain interfaces.

### EN-02: Early correlation, event-envelope, and redaction contract

- **Track:** WS09
- **Pass type:** Architecture contract
- **Primary controls:** API-M15, OPS-010
- **Prerequisites:** `GOV-01`.
- **Maximum scope:** Specify request, job, payment, storage, admin-action, and release correlation fields; accepted identifier rules; safe error exposure; bounded telemetry labels; redaction; and prohibited data. Limit implementation to shared primitives only if current-tree inspection supports it.
- **Required output:** Approved correlation/redaction contract and narrowly scoped shared interfaces/tests.
- **Proof before acceptance:** Unit tests for identifier validation, context separation, encoding, and redaction where implementation occurs.
- **Stop condition:** Stop if fields require unstable payment/job schemas, introduce sensitive or unbounded labels, or expand into full observability.

### EN-03: Early secrets, control-plane access, and evidence-handling foundation

- **Track:** WS10
- **Pass type:** Operational/provider foundation
- **Primary controls:** OPS-005, OPS-006, OPS-007, OPS-025
- **Prerequisites:** `GOV-01`.
- **Maximum scope:** Create redacted inventories and procedures for provider owners, roles, MFA/recovery, secret storage/injection, rotation, revocation, offboarding, emergency access, and safe evidence handling. No secret values or provider mutations.
- **Required output:** Control-plane register, secret-lifecycle register, evidence checklist, redaction rules, and unresolved provider-access log.
- **Proof before acceptance:** Owner review; evidence templates contain no secrets or unnecessary personal data.
- **Stop condition:** Stop immediately if credentials, private keys, tokens, recovery codes, personal data, or unapproved provider access would be exposed.

### WS02-01: Typed settings and environment isolation

- **Infrastructure timing:** Provider-neutral setting names, validation, environment classes, and safety boundaries may be completed before final hosting is selected. Exact production provider bindings, URLs/domains, secret-injection locations, and provider-derived values are late-bound work.
- **Track:** WS02
- **Pass type:** Domain implementation
- **Primary controls:** GOV-002, API-M01, API-M02
- **Prerequisites:** `EN-01`, `EN-02`, and `EN-03`.
- **Maximum scope:** Inspect and implement typed settings, environment bindings, unsafe-default rejection, import/startup behavior, and explicit local/CI/staging/production separation.
- **Required output:** Settings/config changes, current unit/config tests, environment matrix updates, and compatibility notes.
- **Proof before acceptance:** Invalid production configuration fails before readiness; no secret values enter source or artifacts.
- **Stop condition:** Stop if an implementation decision requires unknown final topology, if configuration changes alter process/connection counts without authority, or if unrelated deployment code is required.

### WS02-02: Runtime process, lifecycle, health, and deployability

- **Infrastructure timing:** Application lifecycle, health, shutdown, release-identity, and portable runtime contracts may proceed without a permanent host. Final provider choice, process/instance topology, autoscaling, rolling overlap, platform-specific hardening, and provider runtime settings are late-bound and must be evaluated by Stage 0 when unavailable.
- **Track:** WS02
- **Pass type:** Deployment foundation
- **Primary controls:** API-M03, API-M17, OPS-001, OPS-002, OPS-003, OPS-004
- **Prerequisites:** `WS02-01` and DBP-01. Final provider/topology facts apply only to work that claims final topology or runtime evidence; Stage 0 must not treat them as a blanket blocker for portable lifecycle work.
- **Maximum scope:** Define runtime command, supervision, worker/instance topology, container/platform hardening, startup/readiness/liveness, graceful shutdown, release identity, rolling overlap, rollback, and forward-fix behavior.
- **Required output:** Versioned deployment/runtime configuration, health contract, shutdown handling, deployment tests, and release/rollback record template.
- **Proof before acceptance:** Local or staging-safe lifecycle tests; readiness gates traffic only after dependencies are ready; shutdown releases resources.
- **Stop condition:** Stop if a provider-specific runtime value would be guessed, temporary hosting would be treated as permanent, or a release change cannot be rolled back or forward-fixed.

### WS02-03: Proxy, host, TLS, CORS, and response-class security headers

- **Infrastructure timing:** App-owned proxy/CORS/header contracts may proceed provider-independently. Final public domains, edge/origin topology, TLS/HSTS/redirect behavior, direct-origin exposure, and provider edge settings are late-bound.
- **Track:** WS02
- **Pass type:** Configuration and provider verification
- **Primary controls:** API-M04, API-M05, API-M06, API-M07, API-M08
- **Prerequisites:** `WS02-01`, the applicable source-owned runtime contract from `WS02-02`, and FDN-02. Final edge/origin facts apply only to final provider verification.
- **Maximum scope:** Assign edge versus app ownership and implement trusted-proxy, canonical host, TLS redirect/HSTS, CORS, framing, content-sniffing, cache, and response-class header behavior.
- **Required output:** Edge ownership matrix, app/edge configuration, unit/integration tests, and provider-evidence checklist.
- **Proof before acceptance:** Staging header captures, redirect traces, direct-origin behavior, disallowed-origin tests, and proxy-spoof tests.
- **Stop condition:** Stop on conflicting duplicated headers or redirect loops. If direct-origin exposure or provider settings are unknown because final hosting is not selected, preserve those facts for later verification rather than guessing.

### WS02-04: Request limits, timeouts, rate controls, and stable errors

- **Track:** WS02
- **Pass type:** Domain implementation
- **Primary controls:** API-M09, API-M10, API-M11, API-M12
- **Prerequisites:** `WS02-01`, `EN-02`, and the approved evidence-based limit method.
- **Maximum scope:** Implement bounded work before expensive operations, layered request/header/body/URL limits, timeouts/cancellation, rate controls, resource release, and privacy-safe stable error envelopes.
- **Required output:** Configuration/code, boundary tests, timeout/cancellation tests, rate-limit tests, and telemetry hooks.
- **Proof before acceptance:** Approved values have documented bases; 413/429/timeout/error behavior is repeatable and correlated.
- **Stop condition:** Stop if a numeric value lacks evidence, retries could repeat non-idempotent work, or limits conflict across edge and app.

### WS02-05: HTTP contracts, schemas, docs, cache, and end-to-end chain

- **Infrastructure timing:** Source-owned HTTP/schema/cache/docs behavior may proceed before permanent hosting is selected. Full deployed edge-to-origin verification and host-specific observations are late-bound.
- **Track:** WS02
- **Pass type:** Domain implementation and runtime verification
- **Primary controls:** API-M13, API-M14, API-M16, API-M18, API-M19
- **Prerequisites:** The applicable source contracts from `WS02-03`, `WS02-04`, and FDN-03. Final edge-to-origin topology applies only to full deployed-chain evidence.
- **Maximum scope:** Separate request/response schemas, enforce methods/media types/pagination, apply docs/OpenAPI policy, protect private caching, preserve rolling compatibility, and verify the full edge-to-origin chain.
- **Required output:** API/schema changes, current API tests, OpenAPI inventory checks, cache tests, compatibility notes, and staged chain report.
- **Proof before acceptance:** Unsupported media/methods fail correctly; private data is not cacheable; old/new frontend/API compatibility is exercised.
- **Stop condition:** Stop if a breaking contract lacks a compatibility plan, frontend changes are required outside scope, or configured behavior cannot be proven at the evidence layer being claimed.

### WS03-01: Identity authority and verifier-controlled field protection

- **Track:** WS03
- **Pass type:** Domain implementation
- **Primary controls:** IAM-001, IAM-002, IAM-003, IAM-004, IAM-006, IAM-007, IAM-014
- **Prerequisites:** `WS02-01`, the applicable source-owned HTTP contract from `WS02-05`, and IDB-01 through IDB-03.
- **Maximum scope:** Implement the Firebase/PostgreSQL authority matrix, token/local-user checks, verified-email gates, safe retry/persistence assumptions, and removal of ordinary-user write access to verifier/admin-controlled fields.
- **Required output:** Schemas/services/dependencies, field-write restrictions, route policy matrix, and current negative tests.
- **Proof before acceptance:** Revoked, disabled, unverified, stale, and user-written verifier scenarios are denied as designed.
- **Stop condition:** Stop if a field has two authorities, provider state is unavailable without a fail-safe rule, or changes require broad account-lifecycle redesign.

### WS03-02: Provisioning, account-state lifecycle, and concurrent first login

- **Track:** WS03
- **Pass type:** Schema, migration, and domain implementation
- **Primary controls:** IAM-005, IAM-009, IAM-018
- **Prerequisites:** `WS03-01` plus the accepted WS04 database-lifecycle, transaction, and invariant design inputs required by the selected scope. This does not require the entire WS04 parents or late-bound provider proof to be complete.
- **Stage 0 dependency note:** The WS04 references are design inputs. Stage 0 must identify the exact accepted contract consumed by the proposed work rather than requiring full completion of the WS04 parents.
- **Maximum scope:** Make first login, account linking, recovery, suspension, disablement, deletion, and cross-instance state changes conflict-safe while preserving stable identifiers.
- **Required output:** Narrow schema/migration if required, services, deterministic PostgreSQL concurrency tests, and lifecycle documentation.
- **Proof before acceptance:** Concurrent first login creates one user; open sessions and routes respond to state changes as designed.
- **Stop condition:** Stop on ambiguous merge/link behavior or destructive identity migration. Missing provider revocation/recovery evidence stops only the responsibility claiming actual provider/runtime revocation or recovery proof; it does not block provider-independent provisioning, account-lifecycle, database, or concurrency work whose own prerequisites are satisfied.

### WS03-03: High-risk authentication and Firebase control verification

- **Infrastructure timing:** Source-owned authentication and provider-failure contracts may proceed before concrete production provider settings are available. Final production project/account/IAM/workload-identity/App Check settings and provider evidence are late-bound even when the service integration itself is selected.
- **Track:** WS03
- **Pass type:** Provider/security implementation
- **Primary controls:** IAM-008, IAM-010, IAM-011
- **Prerequisites:** `WS03-01`, `EN-03`, and IDB-04. Concrete production Firebase/GCP settings and evidence apply only to the final provider-dependent scope.
- **Maximum scope:** Define and implement recent-authentication/step-up requirements for high-risk actions, stage App Check, and verify service-account/workload identity scope, revocation, and emergency procedures.
- **Required output:** High-risk action matrix, enforcement code/tests, staged App Check evidence, and redacted Firebase/GCP evidence.
- **Proof before acceptance:** Missing/stale step-up is denied; App Check valid/missing/invalid/provider-unavailable cases are tested; credentials remain least privilege.
- **Stop condition:** Stop if production enforcement risks locking out valid users, provider tier/capability is unknown, or long-lived credentials cannot be safely governed.

### WS03-04: Complete authorization matrix and negative proof

- **Track:** WS03
- **Pass type:** Domain implementation and current tests
- **Primary controls:** IAM-012, IAM-013, IAM-015, IAM-016, IAM-017
- **Prerequisites:** `WS03-01`, `WS03-02`, and stable resource/state contracts for the surfaces being reviewed.
- **Maximum scope:** Inventory every protected route/action and enforce object, relationship, workflow-state, list/query, field, function, role, and concealment boundaries.
- **Required output:** Authorization matrix, narrowly required code corrections, exhaustive current negative tests, and uncovered-gap register.
- **Proof before acceptance:** Cross-user, cross-role, stale-state, mass-assignment, list/search/export, and 401/403/404 substitutions are tested.
- **Stop condition:** Stop if resource policy is undefined, a route family cannot be inventoried, or frontend route guards are being used as backend authorization.

### WS03-05: Moderation states, safe notices, and minimum-necessary admin data

- **Track:** WS03
- **Pass type:** Schema/domain/privacy implementation
- **Primary controls:** ADM-007, ADM-009, ADM-010, ADM-012, ADM-013, ADM-014, ADM-015
- **Prerequisites:** `WS03-04`, the applicable `WS04-02` transaction/invariant contracts, and OPP-03. Durable notice work may consume the accepted provider-independent job/handoff contract from `WS05-01`. Audited moderation or sensitive-read responsibilities may require an append-only audit capability from `WS09-02`, but `WS09-02` parent completion is not a blanket prerequisite for the whole parent. Stage 0 must resolve the exact responsibility-level dependencies without creating a cycle.
- **Stage 0 dependency note:** Do not interpret `WS09-02` parent completion or `WS05-03` parent completion as blanket prerequisites. Stage 0 must identify the exact audit and durable-notice capabilities required by each responsibility and must reject a circular executable graph.
- **Maximum scope:** Stabilize moderation taxonomy/evidence/review/enforcement states; implement safe notice rules; replace default full-sensitive-data exposure with excerpt-first, controlled unmask, anti-cache, and read auditing.
- **Required output:** Models/migration if required, services/APIs/admin UI contracts, notice policy implementation, and current authorization/privacy tests.
- **Proof before acceptance:** Stale evidence, conflicting actions, suppressed notices, unmask, sensitive reads, and denied exports are covered.
- **Stop condition:** Stop if full private content remains the default, audit behavior required by the selected scope is unresolved, or enforcement requires an undefined durable workflow.

### WS04-01: Database engine/session lifecycle, connection budget, and least-privilege roles

- **Infrastructure timing:** Provider-independent database lifecycle, access behavior, budget methodology, and role/grant verification framework may proceed before final database hosting is selected. Final PostgreSQL provider/topology, capacity, pooler/proxy mode, deployed values, concrete production roles/grants, and runtime proof are late-bound.
- **Track:** WS04
- **Pass type:** Database foundation
- **Primary controls:** DB-001, DB-002, DB-003, DB-012, DB-013, DB-015
- **Prerequisites:** The applicable portable runtime contract from `WS02-02` and DBP-01. Actual PostgreSQL provider/topology facts apply only to final verification.
- **Maximum scope:** Inspect and define engine/session lifecycle, transaction defaults, deployment-wide pool/overflow/wait budget, worker/migration reserve, provider roles/grants, and operational access.
- **Required output:** Provider-independent configuration/code and database-access contracts, connection-budget methodology, role/grant verification plan, current PostgreSQL tests, and provider-evidence contract/checklist.
- **Proof before acceptance:** Repository-owned lifecycle/access behavior, bounded waits/timeouts, deterministic budget arithmetic with synthetic inputs, and the least-privilege verification contract are proven without inventing final provider values.
- **Stop condition:** Do not invent provider limits/process counts or change final pool/provider settings without topology evidence. Stop on routine superuser requirements or any attempt to treat temporary infrastructure as final evidence.

### WS04-02: Transactions, invariants, locks, and deterministic concurrency

- **Track:** WS04
- **Pass type:** Database/domain/concurrency
- **Primary controls:** DB-004, DB-005, DB-006, DB-007, DB-008, DB-009, DB-010, DB-014
- **Prerequisites:** The accepted provider-independent `WS04-01` foundation plus approved identity, payment, job, and storage invariant inputs. A `WS04-01D` fact is required only when the selected scope genuinely consumes that final-production fact.
- **Maximum scope:** Define transaction and external-side-effect boundaries; add database constraints or deliberate serialization; handle duplicate, winner/loser, retry, deadlock, timeout, and unknown-outcome cases.
- **Required output:** Narrow models/constraints/services, deterministic independent-session tests, and invariant catalog.
- **Proof before acceptance:** Barrier-driven concurrency tests assert final database and external-intent states, cleanup, and retry behavior.
- **Stop condition:** Stop on nondeterministic tests, ambiguous source of truth, external calls inside unsafe transactions, or a required destructive constraint/backfill without migration design.

### WS04-03: Migration policy, compatibility, interruption, and production-like rehearsal

- **Infrastructure timing:** Migration policy, compatibility rules, graph/drift checks, and controlled rehearsal design may proceed provider-independently. Final provider/runtime-specific ceilings and production-like topology evidence are late-bound.
- **Track:** WS04
- **Pass type:** Schema and migration
- **Primary controls:** DB-016, DB-017, DB-018
- **Prerequisites:** The accepted provider-independent `WS04-01` foundation, `WS04-02`, and stable required schema capabilities. Final provider/runtime rehearsal facts apply only to final production-like evidence.
- **Maximum scope:** Establish expand-and-contract rules, graph/drift checks, empty/prior-schema upgrades, online-index strategy, timeouts, interruption/resume, old/new compatibility, rollback versus forward-fix, and final production-like rehearsal.
- **Required output:** Migration changes/tests, compatibility window, controlled rehearsal results, forward-fix notes, and mandatory final provider/runtime rehearsal.
- **Proof before acceptance:** Empty/prior-schema upgrades and interruption/resume proof now; provider/runtime lock and duration behavior only from the final rehearsal environment.
- **Stop condition:** Stop on blocking/destructive behavior without approval, downgrade assumptions that risk data, or inability to keep old/new versions compatible.

### WS05-01: Durable job model, claim/lease lifecycle, and worker deployment

- **Infrastructure timing:** Durable job semantics, source-owned job signals, repair state, operator visibility, and a portable worker command/runtime contract may proceed before final worker hosting is selected. Final worker platform, deployment topology, scaling/resource settings, provider configuration, and runtime proof are late-bound. Centralized log aggregation, dashboards, alert delivery, and operational runbooks remain responsibility-specific later contracts and evidence owned by the applicable WS09 and WS10 work.
- **Track:** WS05
- **Pass type:** Schema, worker, and deployment
- **Primary controls:** JOB-M01, JOB-M02, JOB-M03, JOB-M04, JOB-M05, JOB-M06, JOB-M07, JOB-M08
- **Prerequisites:** The applicable portable runtime contract from `WS02-02`, accepted provider-independent `WS04-01`, `WS04-02` and `WS04-03` source/schema contracts, and `EN-02`. Final worker hosting/topology applies only to final deployment and runtime proof. Applicable accepted WS09/WS10 contracts or evidence are responsibility-specific inputs only when the selected final verification scope claims centralized logging, dashboards, alert delivery, or operational runbooks; they are not prerequisites for provider-independent WS05-01 work.
- **Maximum scope:** Implement durable job state, transactional handoff/outbox where required, claim/lease/heartbeat, bounded retry, crash recovery, exhaustion/dead-letter/repair, source-level job observability, operator visibility, repair state, durable-job signals, version compatibility, graceful shutdown, portable worker command, and final deployed worker proof.
- **Required output:** Models/migration, worker/service implementation, source-owned observability and repair/operator interfaces, durable-job signal contract, portable deployment contract, current tests, runbook draft, and mandatory final worker-hosting/runtime verification.
- **Proof before acceptance:** Crash/restart, stale lease, duplicate delivery, multi-worker claim, unsupported version, shutdown, backlog, signal visibility, and repair behavior are deterministic; deployed claims require final runtime evidence, and claims about centralized operational surfaces require the applicable WS09/WS10 evidence.
- **Stop condition:** Stop if jobs can be lost between transaction and enqueue, ownership is ambiguous, or final worker deployment/monitoring is guessed.

### WS05-02: Payment and booking state machines with webhook authority

- **Track:** WS05
- **Pass type:** Financial domain implementation
- **Primary controls:** PAY-001, PAY-002, PAY-003, PAY-004, PAY-005, PAY-006, PAY-007, PAY-008
- **Prerequisites:** The provider-independent durable-job foundation from `WS05-01`, `WS04-02`, DBP-02, and `WS03-04`.
- **Maximum scope:** Implement separate coordinated payment, booking, reservation, capacity-conflict, and compensation states; trusted amount calculation; PaymentIntent lifecycle; signed webhook ingestion; saved-payment-method lifecycle; and idempotent transition rules.
- **Required output:** Models/migration if required, services/routes/webhook handlers, transition catalog, current API/PostgreSQL tests, saved-method/frontend contracts, and explicit later-owner handoffs.
- **Proof before acceptance:** Duplicate/out-of-order/delayed webhooks, browser abandonment, requires-action/processing/failure/success, saved-method ownership/recovery, capacity conflict, and server authority are verified.
- **Stop condition:** Stop if frontend callback is treated as final authority, money and booking use one ambiguous status, or transition/compensation rules are incomplete.

### WS05-03: Refunds, credits, notices, moderation delivery, and reconciliation

- **Track:** WS05
- **Pass type:** Durable financial and notification workflows
- **Primary controls:** ADM-011, ADM-016, PAY-009, PAY-010, PAY-011, PAY-012, PAY-013
- **Prerequisites:** The provider-independent `WS05-01` foundation and `WS05-02` apply to the financial workflow responsibilities. The accepted `WS03-05` moderation/safe-notice contract applies only to moderation and administrative-notice delivery responsibilities. Append-only audit capability applies to the privileged actions that require it. Stage 0 must not treat `WS03-05` as a blanket prerequisite for unrelated financial work.
- **Stage 0 dependency note:** `WS03-05` applies only to moderation and administrative-notice responsibilities. Stage 0 must evaluate the complete parent and choose the executable shape without blocking unrelated refund, credit, compensation, or reconciliation work solely on `WS03-05`.
- **Maximum scope:** Apply durable jobs to refunds, credits, administrative notices, moderation delivery, provider synchronization, mismatch classification, repair controls, and recurring reconciliation.
- **Required output:** Durable workflows, schemas/migrations if needed, operator procedures, reconciliation reports, and current tests.
- **Proof before acceptance:** Duplicate requests, provider timeout/unknown outcome, partial failure, retry, capacity compensation, and repair are idempotent and auditable.
- **Stop condition:** Stop if a financial repair can double-spend/credit/refund, provider truth is overwritten, manual repair lacks guardrails and audit, or notice delivery invents policy not owned by the accepted moderation/notice contract.

### WS05-04: Deterministic failure, replay, sandbox, and deployed-worker verification

- **Infrastructure timing:** Deterministic local proof, Stripe sandbox proof, and deployed-worker/runtime proof depend on different evidence environments. Stage 0 must evaluate those prerequisites without substituting one evidence layer for another.
- **Track:** WS05
- **Pass type:** Concurrency/failure/provider/runtime verification
- **Primary controls:** ADM-011, ADM-016, PAY-001, PAY-002, PAY-003, PAY-004, PAY-005, PAY-006, PAY-007, PAY-008, PAY-009, PAY-010, PAY-011, PAY-012, PAY-013, JOB-M01, JOB-M02, JOB-M03, JOB-M04, JOB-M05, JOB-M06, JOB-M07, JOB-M08
- **Prerequisites:** The applicable completed WS05 source responsibilities for each scenario. Stripe sandbox availability is required only for sandbox evidence. Final worker hosting and a deployed worker environment are required only for deployed-runtime evidence. Applicable accepted WS09/WS10 contracts or evidence are required only when the selected final JOB-M08 verification scope claims centralized log aggregation, dashboards, alert delivery, or operational runbooks. Stage 0 must decide the executable shape from the evidence environments actually available.
- **Stage 0 dependency note:** Local deterministic proof, Stripe sandbox proof, deployed-worker proof, and final JOB-M08 operational proof have different responsibility and environment prerequisites. Stage 0 decides whether they form one honest executable result or require separate execution and identifies any applicable WS09/WS10 inputs without treating those later parents as blanket blockers; this blueprint does not predefine the answer.
- **Maximum scope:** Run focused race/replay/crash/timeout/unknown-outcome families and collect Stripe sandbox, worker deployment, reconciliation, and operator evidence. Correct only narrowly proven defects.
- **Required output:** Sanitized test and runtime evidence package, defect log, follow-up passes, and workstream closure assessment.
- **Proof before acceptance:** Repeated deterministic results, final-state verification, no production data/credentials, and provider/environment attribution.
- **Stop condition:** Stop on nondeterminism, unbounded financial impact, unsafe provider mode, missing rollback/repair path, unavailable required evidence environment, or secrets in evidence.

### WS06-01: Admin-only venue-image authority and upload initiation

- **Track:** WS06
- **Pass type:** Storage domain implementation
- **Primary controls:** STO-001, STO-002, STO-003
- **Prerequisites:** The applicable accepted WS02 source foundation, the active-admin authorization contract, and DBP-03. Final R2 account or public-access evidence is not a prerequisite for source-owned upload authority unless the selected scope claims that provider behavior.
- **Maximum scope:** Remove or deny all player/community-host image upload paths, preserve initials-only avatars, enforce active-admin venue-image authority, bind upload intent to venue/admin/file constraints, and prevent arbitrary URLs/keys.
- **Required output:** Routes/services/frontend admin contract, authorization tests, upload-intent records if required, and product-scope documentation.
- **Proof before acceptance:** Player, host, cross-venue, expired, and replayed upload attempts are denied; only the approved admin workflow can initiate.
- **Stop condition:** Stop if user uploads remain reachable, the client controls object identity/type, admin authorization relies only on frontend UI, or final provider facts are guessed.

### WS06-02: Venue-image validation, sanitization, re-encoding, and derivatives

- **Track:** WS06
- **Pass type:** Storage processing implementation
- **Primary controls:** STO-004, STO-005, STO-006, STO-007
- **Prerequisites:** `WS06-01`, DBP-03, and evidence-based file limits. The provider-independent durable-job foundation from `WS05-01` is required only if Stage 0 or Gate A selects asynchronous processing.
- **Stage 0 dependency note:** The durable-job dependency is conditional on asynchronous processing. Stage 0 or Gate A must not apply it when the selected implementation is synchronous and still satisfies authority.
- **Maximum scope:** Treat admin files as untrusted; verify bytes, size/pixel/decompression limits; isolate processing; strip metadata; re-encode approved formats; create idempotent sanitized masters/derivatives; and publish only after success.
- **Required output:** Processing code or durable job, explicit states, tests with malformed/bomb/metadata cases, and safe failure behavior.
- **Proof before acceptance:** Invalid, corrupt, oversized, mismatched, and decompression-danger inputs are rejected; metadata is removed; repeated processing does not duplicate assets.
- **Stop condition:** Stop if raw uploads become public, processing resource bounds are unproven, original retention is undefined, or a conditional job dependency is treated as unconditional.

### WS06-03: R2 lifecycle, deletion, cache behavior, reconciliation, and recovery

- **Infrastructure timing:** Storage lifecycle/reconciliation behavior may proceed from the selected storage contract without assuming final production settings. Concrete production account/bucket/CORS/token/cache/provider values and runtime/recovery evidence are late-bound.
- **Track:** WS06
- **Pass type:** Storage lifecycle/provider/runtime
- **Primary controls:** STO-008, STO-009
- **Prerequisites:** `WS06-01`, `WS06-02`, DBP-04, OPP-05, and the provider-independent durable-job contract when required by the selected design. Final R2 configuration and runtime/recovery evidence apply only to the scope that claims those facts.
- **Maximum scope:** Implement replacement/deletion state, public removal, temporary-original cleanup, abandoned-upload sweep, missing/orphan/divergence reconciliation, safe repair, default-image fallback, usage monitoring, token/CORS/public-access controls, and cache invalidation/expiry strategy.
- **Required output:** Lifecycle/reconciliation jobs, admin repair paths, tests, R2 evidence, and recovery documentation.
- **Proof before acceptance:** Missing object, orphan object, failed deletion, cache stale copy, abandoned upload, and derivative regeneration scenarios are verified.
- **Stop condition:** Stop if automatic deletion is not safely bounded, provider token scope/public access is unknown for the evidence being claimed, or database/object authority is ambiguous.

### WS07-01: Production frontend build, public configuration, artifact identity, and source maps

- **Infrastructure timing:** Build inputs, public-configuration boundaries, artifact identity, and source-map packaging rules may proceed provider-independently. Final hosting project/domain/environment bindings, provider delivery behavior, access, and source-map exposure evidence are late-bound.
- **Track:** WS07
- **Pass type:** Frontend/build/release
- **Primary controls:** FE-M01, FE-M02
- **Prerequisites:** The applicable source-owned `WS02-02` and `WS02-05` contracts, FDN-06, and OPP-02. Final hosting project/domain/delivery facts apply only to final binding and exposure evidence.
- **Maximum scope:** Define production build inputs, public environment variables, artifact/release identity, dependency output, and private source-map handling.
- **Required output:** Build configuration/checks, bundle/public-variable scan, release linkage, unit tests, and documentation.
- **Proof before acceptance:** Production artifact contains only approved public values; source maps are not publicly accessible and are release-linked at the evidence layer being claimed.
- **Stop condition:** Stop if secrets exist in frontend inputs, artifact identity cannot be preserved, or final hosting behavior is unknown for a claim that requires it.

### WS07-02: Authentication persistence, identity-scoped state, logout, switch, and safe retries

- **Track:** WS07
- **Pass type:** Frontend/browser
- **Primary controls:** FE-M05, FE-M06, FE-M10
- **Prerequisites:** The source-owned `WS03-01` through `WS03-03` contracts and IDB-01.
- **Maximum scope:** Make Firebase persistence explicit; clear profile, booking, chat, notification, admin, query, local/session/IndexedDB state on logout/switch/state change; bound token/read retries; prohibit blind mutation replay.
- **Required output:** Frontend state contract, code, unit tests, focused Playwright identity-switch tests, and storage inventory.
- **Proof before acceptance:** No prior-user data appears after logout, switch, suspension, deletion, or role change; sensitive mutations are not blindly replayed.
- **Stop condition:** Stop if backend session/authorization behavior is unclear, global keys persist user data, or a generic retry interceptor affects mutations.

### WS07-03: Routes, API errors, forms, URLs, browser storage, and resilient UI state

- **Track:** WS07
- **Pass type:** Frontend/browser
- **Primary controls:** FE-M03, FE-M04, FE-M07, FE-M11
- **Prerequisites:** `WS02-04`, the source-owned `WS02-05` contracts, stable backend authorization/error contracts, and the applicable identity-scoped storage/retry contract from `WS07-02`. Stage 0 must allocate overlapping browser-state responsibilities without duplication.
- **Stage 0 dependency note:** Stage 0 must allocate overlap with `WS07-02` for identity-scoped storage, logout/switch cleanup, and mutation retry behavior without duplicating ownership.
- **Maximum scope:** Harden route transitions, deep links, history, error boundaries, forms/status messages, URL/query handling, non-identity-specific storage use, loading/empty/failure states, and safe API response handling.
- **Required output:** Frontend changes, unit tests, focused Playwright scenarios, and route/error/storage ownership inventory.
- **Proof before acceptance:** Malformed, expired, deep-link, offline, provider, and API-error states remain understandable and do not expose private data or bypass the WS07-02 identity contract.
- **Stop condition:** Stop if a UI workaround masks a backend defect or if storage/retry behavior duplicates or conflicts with WS07-02.

### WS07-04: Third-party browser code, CSP/SRI posture, headers, and provider failure isolation

- **Infrastructure timing:** Third-party inventory, CSP/SRI policy, and failure-isolation behavior may proceed before final hosting/edge selection. Final production domain allowlists, edge/header bindings, and deployed provider/browser evidence are late-bound.
- **Track:** WS07
- **Pass type:** Frontend security/provider
- **Primary controls:** FE-M08, FE-M09
- **Prerequisites:** The applicable source-owned `WS02-03` contract, IDB-05, and the actual Firebase/Stripe browser dependency inventory. Final domains and edge/header behavior apply only to final deployed evidence.
- **Maximum scope:** Inventory approved browser code/domains/data, enforce CSP and related browser controls, use SRI where compatible, minimize third-party data sharing, and isolate provider failure.
- **Required output:** Inventory, CSP/header configuration, frontend failure handling, tests, and staged browser evidence.
- **Proof before acceptance:** Unapproved domains/scripts are blocked; Firebase/Stripe failure does not expose secrets, corrupt state, or duplicate payment actions.
- **Stop condition:** Stop if CSP requires unsafe broad allowances without justification, third-party data flows are unknown, or provider scripts become single points of failure.

### WS07-05: WCAG 2.2 AA, browser support, and performance verification

- **Track:** WS07
- **Pass type:** Frontend/accessibility/performance
- **Primary controls:** FE-M12, FE-M13
- **Prerequisites:** The applicable accepted source contracts from `WS07-01` through `WS07-04`, `EN-01`, OPP-01, and OPP-02. Final-host measurements apply only to performance claims that require that environment. Stage 0 decides whether the outcomes form one safe executable unit.
- **Stage 0 dependency note:** Accessibility, browser compatibility, and performance use different proof methods. Stage 0 must apply the normal cohesion test but this blueprint does not require a predetermined split.
- **Maximum scope:** Apply and verify keyboard/focus/dialog/form/status/contrast/reflow/zoom/reduced-motion/screen-reader behavior, supported modern browser/device matrix, production-build performance, bundle/image behavior, and governed exceptions.
- **Required output:** Code corrections, automated tests, manual audit record, browser matrix results, performance baseline/budgets, and exceptions.
- **Proof before acceptance:** Critical end-to-end processes pass defined accessibility/browser checks; performance values come from realistic measurements.
- **Stop condition:** Stop if only automated accessibility evidence exists, exact budgets are invented, or browser tests use development builds.

### WS08-01: Complete current-test inventory, fixtures, and control mapping

- **Track:** WS08
- **Pass type:** Test infrastructure
- **Primary controls:** TST-001, TST-002, TST-003, TST-004, TST-010, TST-011
- **Prerequisites:** `EN-01` and stable outputs from the specific WS02 through WS07 surfaces being inventoried; not blanket completion of every parent in those workstreams.
- **Maximum scope:** Finalize suite discovery/classification, synthetic fixtures, isolated PostgreSQL/browser/provider environments, cleanup, auth-state generation, artifact policy, and control-to-evidence mapping.
- **Required output:** Current-suite inventory, checker updates, fixture documentation, gap list, and self-tests.
- **Proof before acceptance:** No legacy test is counted; every suite declares environment/data/cleanup; missing required suites fail the checker.
- **Stop condition:** Stop if fixtures share production resources, test ordering is required, or classification overstates provider/full-stack coverage.

### WS08-02: Critical workflow, deterministic concurrency, migration, provider, privacy, and recovery suites

- **Infrastructure timing:** Repository/local/sandbox suites may proceed when their environments are honest substitutes for the behavior under test. Provider, restore, or full-environment suites that require selected final infrastructure remain late-bound.
- **Track:** WS08
- **Pass type:** Current tests
- **Primary controls:** TST-005, TST-006, TST-007, TST-008, TST-009
- **Prerequisites:** `WS08-01` and the applicable stable domain implementation. Provider sandbox, restore, or full-environment availability applies only to the evidence family that uses it. Stage 0 must not let one unavailable evidence environment block independently valid evidence work.
- **Stage 0 dependency note:** Provider sandbox, restore, and full-environment availability apply only to the evidence families that use them. Stage 0 must not substitute one evidence layer for another or turn an unavailable layer into a blanket blocker.
- **Maximum scope:** Complete risk-based current coverage for auth/admin, payments/jobs, venue storage, database races, migrations, provider boundaries, privacy workflows, and restore verification.
- **Required output:** Layered unit/service/API/PostgreSQL/browser/provider/migration/failure suites and evidence mapping.
- **Proof before acceptance:** Critical races use barriers/independent sessions; provider tests are sandboxed; migration/restore tests use controlled fixtures.
- **Stop condition:** Stop on nondeterminism, production provider use, giant unowned end-to-end tests, unverified cleanup, or evidence-layer substitution.

### WS08-03: Reproducible CI, scans, branch protection, SBOM, provenance, and release evidence

- **Infrastructure timing:** CI, scan, SBOM, provenance, and release-manifest contracts may proceed before final hosting selection. Deployment linkage and release/provider evidence that depends on the final delivery path is late-bound.
- **Track:** WS08
- **Pass type:** CI/supply chain/provider
- **Primary controls:** TST-012, TST-013, TST-014, TST-015, TST-016, TST-017
- **Prerequisites:** The applicable `WS08-01`/`WS08-02` outputs, stable job names and release artifacts, and `EN-03`. Final deployment linkage and repository/provider settings apply only to the evidence that claims them.
- **Maximum scope:** Pin tools/dependencies, validate clean installs, gate suites/build/migrations/security scans, protect secrets/forks, create aggregate required check, generate sanitized artifacts/SBOM/provenance, and verify GitHub branch rules/deployment linkage.
- **Required output:** CI workflows/checkers, scan policy, artifact/release manifest, redacted branch-protection evidence, and sample release package.
- **Proof before acceptance:** Actual CI run records; skipped/failed/canceled/provider-unavailable behavior is explicit; required checks cannot be bypassed silently.
- **Stop condition:** Stop if CI needs production credentials, gates can be skipped without visibility, artifacts leak data, or release identity cannot be tied to source/deployment.

### WS09-01: Structured request/event logging, correlation, redaction, and log aggregation

- **Infrastructure timing:** Logging schemas, correlation, redaction, and signal contracts may proceed provider-independently. Final central logging/observability provider selection, ingestion/delivery configuration, access/retention settings, and provider evidence are late-bound.
- **Track:** WS09
- **Pass type:** Observability implementation
- **Primary controls:** API-M15, OPS-008, OPS-010
- **Prerequisites:** `EN-02` and stable event/release context for the sources being instrumented. Applicable data-classification, minimization, and retention contracts must be consumed when configuring final access/retention behavior. Final logging-provider facts apply only to provider/runtime proof.
- **Stage 0 dependency note:** Final logging access and retention behavior must consume the applicable approved data-lifecycle contract rather than inventing it. This relationship is a contract dependency, not a requirement that all of `WS10-01` finish before source logging can begin.
- **Maximum scope:** Implement bounded request/job/payment/storage/admin/release context, structured logging, route templates, error categories, redaction, access/retention hooks, central aggregation, and log-loss detection.
- **Required output:** Shared logging/correlation code, tests, provider configuration/evidence, and log-field catalog.
- **Proof before acceptance:** Concurrent context isolation; injection-safe encoding; no tokens/private messages/card data/full signed URLs; samples from every component at the evidence layer being claimed.
- **Stop condition:** Stop if high-cardinality or sensitive fields are required, central provider access is unsafe, retention is invented, or logs cannot be tied to environment/release.

### WS09-02: Append-only administrative audit trail and sensitive-access controls

- **Track:** WS09
- **Pass type:** Database/domain/privacy
- **Primary controls:** ADM-001, ADM-002, ADM-003, ADM-004, ADM-005, ADM-006
- **Prerequisites:** `WS03-04`, `WS04-02`, and OPP-11 are prerequisites for reusable append-only audit behavior. Domain-specific audit catalog entries and sensitive-read/unmask/export coverage may consume accepted contracts from `WS03-05` and privileged actions from `WS05-03`. Those downstream domain contracts are responsibility-specific inputs, not blanket prerequisites for all WS09-02 work. Stage 0 must resolve the boundary without creating a `WS03-05`/`WS09-02` cycle.
- **Stage 0 dependency note:** Reusable append-only audit capability must not be blanket-blocked by `WS03-05`. Conversely, domain-specific moderation, unmask, sensitive-read, or privileged-repair audit coverage may require accepted domain contracts. Stage 0 must resolve the responsibility boundary without a `WS03-05`/`WS09-02` cycle.
- **Maximum scope:** Implement the required append-only administrative audit event catalog, atomic or durable recording, safe before/after fields, outcomes, denial/conflict/provider failure, append-only permissions, restricted lookup, sensitive-read/unmask/export auditing, and correction records.
- **Required output:** Schema/migration, services, admin access contract, PostgreSQL tests, and audit policy linkage.
- **Proof before acceptance:** Normal update/delete is denied; audit write-failure behavior is explicit; duplicate/concurrent privileged actions remain attributable.
- **Stop condition:** Stop if audit contains excessive sensitive content, privileged actions can succeed without designed audit behavior, normal admins can alter history, or the proposed executable dependency graph is circular.

### WS09-03: Metrics, service objectives, dashboards, alerts, capacity, and cost evidence

- **Infrastructure timing:** Signal definitions and provider-neutral capacity-model structure may proceed earlier. Final dashboards/alerts, delivery routing, exact measured objectives, provider/storage/database capacity, cost values, and provider-limit evidence require the final deployment and are late-bound.
- **Track:** WS09
- **Pass type:** Observability/operations
- **Primary controls:** OPS-009, OPS-011, OPS-012, OPS-016
- **Prerequisites:** The applicable accepted `WS09-01` and `WS09-02` contracts, stable signal producers from the relevant WS02 through WS06 areas, OPP-09, and OPP-10. Accepted provider-neutral incident ownership, escalation behavior, and runbook-link conventions from `WS10-03` are responsibility-specific inputs only to the WS09-03 alert-delivery work that needs them; they do not require `WS10-03` parent completion or block unrelated WS09-03 signal, metric, objective, capacity, or cost work. Final observability provider, measurements, alert delivery, capacity, and cost facts apply only to final evidence.
- **Stage 0 dependency note:** Stage 0 must identify the exact provider-neutral WS10-03 incident contract consumed by applicable alert-delivery responsibilities without making `WS10-03` a blanket prerequisite. Final provider-specific WS10-03 runbooks and exercises may consume applicable accepted WS09-03 dashboard, alert-definition, routing, and delivery contracts without making either parent circularly dependent on whole-parent completion.
- **Maximum scope:** Define measured indicators and evidence-based targets for availability, latency, correctness, payments, job delay, data freshness, provider/storage/database limits, cost, and launch blockers; implement dashboards/alerts and synthetic delivery tests.
- **Required output:** Metric catalog, SLI/SLO record, dashboards, alert/runbook links, capacity/cost model, load tests, and delivery evidence.
- **Proof before acceptance:** Alerts are symptom/outcome based, bounded, delivered and acknowledged; load warns before provider limits; exact values have evidence.
- **Stop condition:** Stop if targets are invented, labels are unbounded, alert routing has no owner, or capacity tests risk production.

### WS10-01: Data classification, table lifecycle, retention, privacy, and audit lifecycle

- **Infrastructure timing:** Data lifecycle and deletion/anonymization requirements, provider-copy lifecycle rules, tombstone/replay/reapplication behavior, and source-level or synthetic proof may proceed before a final restore environment exists. Actual provider-backed restore execution, restored-system verification, and actual recovery-environment evidence are late-bound responsibilities owned by `WS10-04`.
- **Track:** WS10
- **Pass type:** Privacy/retention/schema
- **Primary controls:** GOV-003, ADM-008, DB-011, OPS-022, OPS-023, OPS-024
- **Prerequisites:** Stable applicable data models from WS03 through WS06 and OPP-07, OPP-08, and OPP-11. Logging, audit, and recovery consumers may depend on this pass's outputs, but those downstream uses must not be turned into a circular blanket prerequisite on this whole parent.
- **Stage 0 dependency note:** Stage 0 must allocate overlap with logging, audit, provider-copy, legal-hold, and restore-time deletion responsibilities without making downstream consumers blanket prerequisites of this parent. It must preserve WS10-01 ownership of the lifecycle/deletion contract and source-level or synthetic reapplication proof while preserving WS10-04 ownership of actual provider-backed restore and restored-system evidence.
- **Maximum scope:** Create data inventory/classification and table/provider-copy lifecycle matrix; implement approved hard delete/anonymize/restricted/soft-delete behavior, export/correction/deletion workflows, durable retries, backup treatment, legal holds, and restore-time deletion reapplication.
- **Required output:** Policies/matrices, provider-copy lifecycle and tombstone/replay/reapplication contract, narrow migrations/jobs/APIs, synthetic privacy tests, audit evidence, and exception process.
- **Proof before acceptance:** Cross-user denial, partial provider failure, replay, concurrent use/deletion, export protection, and legal-hold scoping are verified; source-level and synthetic proof demonstrates that deletion/anonymization state can be preserved or reapplied. Actual restored-system verification is owned by `WS10-04`.
- **Stop condition:** Stop on unreviewed destructive changes, invented legal periods, incomplete provider-copy inventory, or inability to define and prove source-level or synthetic deletion reapplication behavior. Missing actual final-provider restore evidence stops only the WS10-04 recovery responsibility that claims it; it does not block provider-independent WS10-01 work whose own prerequisites are satisfied.

### WS10-02: Secrets, provider control-plane access, MFA, rotation, revocation, and offboarding

- **Infrastructure timing:** This is intentionally late operational/provider work. Preparatory inventories may exist earlier, but live claims must use the actual selected production providers/accounts/topology and never temporary Vercel/Render/Neon as final evidence.
- **Track:** WS10
- **Pass type:** Operational/provider
- **Primary controls:** OPS-005, OPS-006, OPS-007, OPS-025
- **Prerequisites:** `EN-03` plus actual selected production provider accounts/topology for claims about live access, MFA, rotation, revocation, and offboarding. Preparatory records may proceed only when they are independently useful and do not claim live provider state.
- **Maximum scope:** Finalize least-privilege users/roles/service identities, MFA/recovery ownership, managed secret injection, rotation overlap, revocation, break-glass, offboarding, monitoring, and dated redacted evidence across hosting, Firebase/GCP, Stripe, R2, PostgreSQL, DNS, GitHub, monitoring, and backups.
- **Required output:** Completed inventories, procedures, redacted evidence packages, discrepancies, and exercises.
- **Proof before acceptance:** Access review and rotation/revocation/offboarding/lost-factor exercises succeed without exposing secrets.
- **Stop condition:** Stop on missing recovery owner, shared/unattributed privileged access, long-lived unmanaged credentials, unsafe evidence, or unselected final providers.

### WS10-03: Incident response, provider-outage handling, and operational runbooks

- **Infrastructure timing:** Generic incident roles/process may be prepared earlier, but final provider-outage runbooks and tabletop evidence must match the stable deployed production architecture and are therefore late-bound.
- **Track:** WS10
- **Pass type:** Operational process/exercise
- **Primary controls:** OPS-013, OPS-014, OPS-015
- **Prerequisites:** Named owners and stable source workflow contracts are required for provider-neutral incident ownership, escalation behavior, and runbook-link conventions. Applicable accepted `WS09-03` dashboard, alert-definition, routing, and delivery contracts, stable deployed architecture, and actual provider topology apply only to final provider-specific runbooks and exercises that consume them; `WS09-03` parent completion is not a prerequisite for provider-neutral WS10-03 planning.
- **Stage 0 dependency note:** Provider-neutral incident planning and final provider-specific runbooks/exercises have different prerequisite states. Stage 0 must order only the applicable responsibility-level contract exchanges, must not make either parent a blanket prerequisite for the other, and decides the executable shape without this blueprint predefining children.
- **Maximum scope:** Define severity, roles, containment, evidence, reconciliation, communication, post-incident actions, and runbooks for API/DB/connection exhaustion/release/migration/jobs/Stripe/R2/Firebase/secrets/certificates/backups/control planes.
- **Required output:** Incident plan, provider-outage matrix, service runbooks, communication templates, and tabletop results.
- **Proof before acceptance:** Tabletops expose alert, access, decision, communication, reconciliation, and recovery gaps; actions have owners/retests.
- **Stop condition:** Stop if runbooks do not match deployed architecture, emergency steps bypass financial/data safeguards, or on-call/decision authority is undefined.

### WS10-04: Backup/PITR evidence, isolated restore, recovery validation, and exercises

- **Infrastructure timing:** Recovery requirements and rehearsal design may be prepared earlier, but actual backup/PITR configuration, restore proof, measured recovery results, and provider-specific exercises are late-bound until final production infrastructure exists.
- **Track:** WS10
- **Pass type:** Recovery/provider/runtime
- **Primary controls:** OPS-017, OPS-018, OPS-019, OPS-020, OPS-021
- **Prerequisites:** OPP-04 through OPP-06 and stable data/workflow requirements are required for recovery design. The applicable accepted `WS10-01` lifecycle/deletion/replay contract, rather than WS10-01 whole-parent completion, plus applicable accepted WS10-02/WS10-03 outputs, a stable release, final observability, final provider configuration, and an isolated restore environment apply to actual recovery proof. Stage 0 must distinguish those prerequisite states.
- **Stage 0 dependency note:** Recovery design and actual provider-backed restore proof have different prerequisite states. Stage 0 must preserve WS10-01 ownership of lifecycle/deletion rules and source-level or synthetic reapplication proof while preserving WS10-04 ownership of actual provider-backed restore and restored-system evidence; Stage 0 decides the executable shape without this blueprint predefining children.
- **Maximum scope:** Verify provider backup/PITR/encryption/access/monitoring; execute the actual provider-backed restore into isolation; validate integrity/startup/Firebase mappings/roles/bookings/Stripe/R2/jobs/migrations/deletion replay; execute required technical and tabletop recovery scenarios.
- **Required output:** Redacted provider and actual recovery-environment evidence, measured restore report, reconciliation results, exercise reports, defects, owners, and retest plan.
- **Proof before acceptance:** Backups are actually readable; restored system passes critical checks; deleted/anonymized data does not silently return; job/payment replay is controlled.
- **Stop condition:** Stop if isolation, credentials, synthetic data, recovery objectives, version compatibility, or safe abort/cleanup are not proven.

### CLOSE-01: Cross-workstream evidence completeness and discrepancy sweep

- **Track:** PROGRAM
- **Pass type:** Audit preparation
- **Primary controls:** Program gate; no primary control reassessment
- **Prerequisites:** All workstream exit gates and every mandatory deferred obligation must be complete or truthfully resolved.
- **Maximum scope:** Reconcile repository changes, current tests, CI, provider evidence, runtime observations, migration/concurrency rehearsals, operational records, and exercises against every control and identify remaining gaps without changing locked findings.
- **Required output:** Complete evidence index, missing/contradictory evidence log, exception candidates, and required correction passes.
- **Proof before acceptance:** Every evidence item is dated, environment-attributed, redacted, linked to exact controls, and reconciled to one owner; every control has an assessor-ready record.
- **Stop condition:** Stop if evidence is stale, unattributed, secret-bearing, contradictory, based only on configuration intent, a control lacks an assessor-ready record, or a mandatory deferred obligation remains open.

### CLOSE-02: Fresh 163-control reassessment and production-readiness decision

- **Track:** PROGRAM
- **Pass type:** Independent reassessment
- **Primary controls:** Program gate; no primary control reassessment
- **Prerequisites:** `CLOSE-01` and all correction/retest passes.
- **Maximum scope:** Reassess all 163 controls from current repository, runtime, provider, operational, and exercise evidence. Do not carry forward old statuses or infer closure from implementation alone.
- **Required output:** New control-by-control assessment, P0/P1/P2 disposition, approved time-bound exceptions if any, and explicit sign-off or no-sign-off decision.
- **Proof before acceptance:** Independent reconciliation finds no missing/duplicate controls; every applicable P0 is closed or formally resolved under policy.
- **Stop condition:** No sign-off if any applicable P0 lacks required evidence, an exception is informal/open-ended, or production behavior remains unverified.

## 10. Program integrity validation

### 10.1 Control-coverage validation

The planned parent-pass decomposition was mechanically checked against the finalized
workstream register:

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

**Validation result:** PASS. Every primary control assigned to WS01 through WS10
appears in at least one planned parent pass, with no unexpected primary control
assigned to the wrong workstream.

This does not close any control. It also does not prove that a future executable
dependency graph is acyclic, that a parent should remain whole, or that every
responsibility has the same prerequisite state.

### 10.2 Dependency-integrity review

Before Stage 0 accepts a parent intake, it must verify:

- every parent responsibility has been identified;
- each prerequisite is interpreted as either a completed-pass prerequisite, an
  accepted contract/design input, responsibility-specific, conditional, or
  late-bound;
- no responsibility-specific, conditional, or late-bound prerequisite is applied as
  a blanket blocker to unrelated parent work;
- broad dependency phrases are resolved to the exact capability or evidence needed;
- the proposed executable graph contains no unresolved direct or indirect cycle;
- every responsibility has one destination and no implementation responsibility is
  duplicated;
- every deferred follow-up has an owner, trigger, preserved obligations,
  prerequisites, downstream consumers, and latest completion boundary;
- the proposed executable result is independently safe, useful, reviewable, and
  reversible or forward-fixable.

This review does not predetermine whether the parent must split. Stage 0 applies the
intake template and current repository truth to decide whether the parent remains one
pass, is divided into executable children, has a mandatory deferred follow-up, or must
stop.

The `WS03-05`, `WS05-03`, and `WS09-02` parent rows require particular care because
their moderation, notice, financial-repair, sensitive-read, and audit responsibilities
do not all consume the same contracts. The corrected prerequisite wording in this
blueprint removes the prior whole-parent circular interpretation; Stage 0 must still
determine the actual executable boundaries when those parents are selected.

## 11. Current pass workflow routing

Current pass execution is owned by the durable workflow documents. Use this blueprint
for parent-pass scope, dependency intent, infrastructure timing, and completion
expectations, then route first-time work through:

```text
Stage 0
-> Gate A planning
-> independent Gate A review / correction cycle
-> Gate B implementation and trusted evidence
-> independent Gate C review / correction cycle
-> Gate D Git and PR finalization
-> open PR for manual merge
```

Use `PASS-IMPLEMENTATION-WORKFLOW.md` for first-time implementation and correction
rounds on the same unmerged pass. Use `PASS-RECHECK-WORKFLOW.md` for accepted or
historical implementation being revalidated or repaired.

The durable engineering requirements from the historical lifecycle remain binding:

- verify prerequisites, accepted decisions, Git state, evidence availability,
  rollback/abort criteria, exact control IDs, and infrastructure timing before
  implementation;
- inspect current repository truth and affected files before editing;
- keep scope narrow to the selected executable pass and frozen Gate A design;
- let Stage 0, not this blueprint or a prompt, decide future decomposition;
- distinguish repository, provider, runtime, operational, privacy, and recovery
  evidence;
- stop rather than guess through unresolved authority, ownership, dependency,
  provider/runtime facts, destructive migrations, or sensitive evidence;
- review the actual diff and relevant full files, including negative space and bypass
  paths;
- preserve later provider/runtime evidence as explicit deferred work when Stage 0
  creates such a follow-up;
- remember that implementation and tests do not close controls without the required
  evidence and reassessment.

## 12. Commit, merge, and rollback protocol

### Repository changes

- One coherent executable pass per commit or pull request.
- No unrelated formatting, renaming, dependency upgrade, process edit, or refactor.
- Commit messages begin with the executable pass ID.
- A failed or partially accepted pass is not stacked under dependent work.
- Gate D must exclude unrelated carryover and finalize only the pass state approved
  by Gate C.

### Database migrations

- Prefer expand-and-contract and forward-fix compatibility.
- Do not depend on destructive downgrade scripts as the primary recovery strategy.
- Backfills require batching, interruption, resume, and evidence appropriate to
  volume.
- A migration does not merge until the empty-schema, prior-schema, compatibility, and
  rehearsal requirements for the executable pass are satisfied.

### Provider changes

- Separate repository implementation from provider mutation and provider evidence.
- Do not make permanent provider-specific configuration changes until the relevant
  final-provider trigger is satisfied.
- A selected product integration may keep its source/application contract, but
  concrete production accounts, plans, regions, quotas, domains, credentials, roles,
  settings, and runtime observations remain evidence-bound.
- Record prior setting, intended setting, owner, environment, validation, and
  reversal procedure.
- Never place secrets or unrestricted provider screenshots in the repository.

### Rollback hierarchy

1. Revert an isolated repository pass when it has no irreversible data/provider
   effect.
2. Use a planned forward fix for schema changes where downgrade risks data.
3. Restore the prior immutable deployment artifact when compatibility permits.
4. Use controlled provider rollback only with an owner, evidence, and verification.
5. Trigger incident/recovery procedures when state is uncertain.

## 13. Evidence protocol

A control may require several evidence classes. A code change or test alone cannot
substitute for provider, runtime, operational, privacy, or recovery proof when the
control requires those layers.

Every accepted evidence record must identify:

- control IDs;
- environment;
- source revision or release identity;
- date and reviewer;
- exact scenario or setting;
- redaction status;
- observed result;
- unresolved discrepancy;
- follow-up owner.

Evidence must never contain raw tokens, passwords, private keys, recovery codes,
unrestricted signed URLs, card data, private-message bodies, or unnecessary personal
information.

## 14. Global stop conditions

Stop the program or current executable pass when any of these occurs:

1. the accepted baseline or active source branch cannot be verified;
2. the worktree contains unrelated or unexplained changes;
3. a material prerequisite is unresolved, circular, or cannot be tied to an exact
   accepted capability;
4. the work requires an unapproved architecture, product, security, technical-policy,
   or operational decision;
5. current implementation contradicts higher authority and the conflict is not
   reconciled;
6. scope expands beyond the selected parent or executable-pass responsibility;
7. Stage 0 is applying a responsibility-specific, conditional, or late-bound
   prerequisite as a blanket blocker without justification;
8. a migration may be destructive, blocking, or incompatible without an approved
   strategy;
9. a test is nondeterministic or depends on execution order;
10. a provider test would touch production data, credentials, payments, users, or
    objects;
11. a retry could duplicate a non-idempotent mutation;
12. a financial, booking, job, moderation, notice, audit, or storage workflow has an
    ambiguous source of truth or unknown final state without repair logic;
13. sensitive information would enter source, logs, metrics, artifacts, screenshots,
    or evidence;
14. rollback, forward-fix, abort, or cleanup is unavailable;
15. required tests fail or were not executed;
16. reported success cannot be verified from the actual diff, files, or evidence;
17. a later pass is being used to hide an unresolved earlier-pass defect;
18. final production infrastructure is being selected merely to satisfy one pass;
19. temporary/demo/free-tier/local/example values are being treated as final
    production configuration or evidence;
20. a final-infrastructure-dependent obligation has no named owner, trigger,
    prerequisites, downstream consumers, or latest boundary;
21. a parent is represented as complete while a mandatory deferred obligation
    remains open;
22. Gate D includes unrelated work outside the Gate C-approved pass state.

## 15. Final closure sequence

1. Complete provider-independent repository, database, migration, configuration, and
   operational-document work.
2. Select and freeze final production hosting, database, edge, worker, observability,
   and recovery topology when the application and launch architecture are stable
   enough to make that decision honestly.
3. Activate and complete every mandatory deferred provider/infrastructure follow-up,
   including final settings, values, roles/grants, provider evidence, and runtime
   observations.
4. Execute applicable current unit, service, API, PostgreSQL, concurrency, browser,
   provider, migration, failure, privacy, and recovery tests at the correct evidence
   layers.
5. Enforce reproducible CI, scans, required checks, artifacts, and supply-chain gates.
6. Collect redacted provider and repository-protection evidence.
7. Perform staged runtime verification against the final selected topology.
8. Rehearse migrations and deterministic concurrency.
9. Prove backup/PITR access and isolated restore.
10. Complete incident and recovery exercises.
11. Run `CLOSE-01` only after the mandatory deferred sweep confirms no required
    follow-up remains open or unowned.
12. Reassess all 163 controls from fresh evidence.
13. Issue production-readiness sign-off only when every applicable P0 is closed or
    governed by an approved time-bound exception and all launch conditions are
    satisfied.

## 16. Current execution entry

Do not restart the program from historical `BASE-00` or `GOV-01` instructions. Those
entries remain provenance and parent-pass structure.

For current work:

1. determine current accepted repository state;
2. read `00-READ-ME-FIRST.md`, Program Context, this blueprint, and the execution
   register;
3. identify the selected parent's actual prerequisite and trigger state;
4. use the correct first-time or recheck workflow;
5. when a new parent is selected, run Stage 0 before Gate A;
6. let Stage 0 decide whole-parent execution, child structure, deferred follow-ups,
   or blockers;
7. when an accepted parent has remaining children, use its accepted intake graph;
8. when exactly one executable unit is eligible, proceed at its required stage;
9. when multiple units are equally eligible or authority remains ambiguous, stop for
   owner selection;
10. never infer progression from numbering alone;
11. never treat a deferred follow-up with an unmet trigger as the next executable
    unit.

The execution register records accepted decomposition, current completion state, and
deferred follow-up state. Frozen pass artifacts contain the current assignment. No
single one of those sources replaces the others.
