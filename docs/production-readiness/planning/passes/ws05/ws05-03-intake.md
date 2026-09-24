# WS05-03 — Refunds, credits, notices and reconciliation intake

## 1. What Needs To Be Decided

This intake decides how to finish the financial obligations left by the accepted
payment and booking lifecycle. The execution boundary matters because completing
a known refund or credit obligation and periodically finding unresolved monetary
state are independently useful outcomes with different failure and review paths.

## 2. What We Know

These facts determine the split. They describe current accepted source and the
surviving requirements, not a new financial product design.

| Topic | Current fact or constraint | Why it affects execution |
|---|---|---|
| Accepted foundation | The PostgreSQL durable-job runtime and the payment, booking, webhook, and compensation state model are accepted. A late successful payment without entitlement creates an active `PaymentCompensation` obligation, but no refund is executed there. | The financial obligation can be consumed without redesigning checkout or webhook payment authority. |
| Existing money workflows | Refund records and events, game-credit grants and usage, admin refund retry/reconcile, and `MoneyIssue` repair paths already exist. Official-game cancellation, player removal, community publish-fee and direct/admin financial outcomes have separate provider and credit paths. | Completion must reconcile all real producers and consumers against one value-preserving contract, while reusing existing repair ownership. |
| Existing notices | Financial workflows can create in-app notification rows from committed outcomes. Moderation already creates local safe notices. | Notices belong with the truth-producing financial transition; ordinary database-local notice creation needs no separate delivery queue. |
| Existing reconciliation | Targeted PaymentIntent and saved-method jobs and manual refund reconciliation exist. There is no bounded periodic discovery of unresolved or recent monetary state. | Targeted recovery and periodic discovery are different outcomes. The latter must consume the former and the completed refund/credit paths. |
| Historical handoff | The older WS05-02 intake also named disputes and broad moderation delivery for WS05-03. The corrected master limits this unit to real refund, credit, notice, and reconciliation obligations. | The older wording does not create a dispute feature, external notice channel, or generalized delivery engine. |
| Provider and runtime boundary | Stripe is the fixed payment integration. Final worker hosting and deployed behavior are not yet proven; temporary hosting and database services do not select final production topology. | Portable source behavior can proceed now. Final worker deployment and provider/runtime verification retain their existing later owners. |

## 3. Execution Decision

This section selects the smallest independently acceptable engineering results.
The refund and credit work must be correct together where a booking used both,
while periodic discovery can follow after the individual obligation paths are
safe.

**Outcome: split WS05-03 into two ordered executable children.**

| Order | Work | Depends on |
|---|---|---|
| 1 | `WS05-03A — Financial obligation fulfillment and truthful notices` | Accepted durable-job and payment/booking foundations |
| 2 | `WS05-03B — Bounded periodic monetary reconciliation` | Accepted `WS05-03A` and existing targeted reconciliation |

`WS05-03A` leaves refund, credit, and compensation obligations recoverable at
their individual operation boundaries, with notices tied to actual committed
outcomes. That is a coherent result even before a periodic sweep is added.
`WS05-03B` then adds bounded discovery and provider comparison for unresolved
or recent state, including cases no path explicitly handed to repair. It uses
existing targeted paths and has a separate scheduling and rate-control review
boundary. The children share accepted financial models but do not independently
implement the same transition.

## 4. Where The Parent Work Goes

This allocation preserves each surviving parent responsibility once. Shared
compatibility checks may cross both children, but each behavior has one primary
implementing owner.

| Parent work | Goes to | Remaining boundary |
|---|---|---|
| Refund, credit, and compensation value invariants across known obligations | `WS05-03A` | Includes compensation after paid checkout without entitlement, official-game cancellation, player removal, community publish-fee and direct/admin outcomes, and failed credit release or restore. Preserve separate Stripe payment truth and booking entitlement; do not create duplicate refunds or credit value. |
| Durable handling for operations that must survive request, process, or provider failure; stable Stripe mutation identity; unknown-outcome recovery | `WS05-03A` | Keep synchronous local financial mutations when they are already transactionally safe. Targeted recovery belongs with the obligation it repairs. |
| Reuse of `MoneyIssue`, refund events, credit usage, and existing admin repair/reconciliation | `WS05-03A` | No second generic repair platform or all-history ledger. |
| Truthful financial user notices and any concrete notice delivery need | `WS05-03A` | Local notices follow committed outcomes; existing moderation notices remain accepted. No generalized notice lifecycle or queue for ordinary local rows. |
| Portable periodic trigger, bounded discovery, and Stripe comparison for unresolved/recent monetary state | `WS05-03B` | Reuse targeted transitions and repair paths from A; avoid all-history synchronization. |
| Provider throttling and backoff | `WS05-03A` for individual provider work; `WS05-03B` for periodic scan/provider-read pacing | Each owner limits its own calls; neither installs a generic retry platform. |
| Final worker platform, deployment topology, and real execution of the portable worker and periodic trigger | Existing mandatory `WS05-01B` | Trigger remains selection and evidence of the final worker platform, service/process topology, scaling/resource settings, deployment path, and safe runtime verification environment. Its proof must include applicable WS05-03 consumers when available. |
| Stripe sandbox, deployed-worker, replay, crash, timeout, and reconciliation-behavior verification | Existing `WS05-04` | This later verification consumes the finished source paths; local tests in A/B are not provider or deployed-runtime proof. |
| Deployed monitoring, runbooks, and restore-before-effects reconciliation | Existing `WS09` and `WS10` owners | These consume safe outcomes and source signals without changing A/B financial ownership. |

There is no new WS05-03 final-infrastructure child. The final production worker
activation and runtime proof are already mandatory under `WS05-01B`; the
Stripe/deployed reconciliation exercises are already assigned to `WS05-04`.
Those obligations remain incomplete. Run them when their final platform and
verification environments are selected and evidenced, and no later than the
first downstream work requiring those facts or `CLOSE-01`. In particular,
production restore must reconcile local payment and job state before
provider-mutating effects resume.

## 5. What Happens Next

This section identifies the next engineering result. `WS05-03A` is ready to
plan because the accepted durable-job and payment/booking contracts, existing
refund and credit records, Stripe integration, and MoneyIssue repair paths are
available. No final hosting choice is required for its source-owned result.
`WS05-03B` follows only after A is accepted so its periodic discovery uses the
current financial transition contract.

## 6. Internal Record

| Detail | Value |
|---|---|
| Parent pass | `WS05-03 — Refunds, credits, notices and reconciliation` |
| Stage 0 outcome | Decompose into `WS05-03A -> WS05-03B`; no new mandatory deferred child |
| Starting-state rule | Use current accepted `origin/develop` when later execution begins; do not treat this intake as a frozen Git baseline |
| Intake path | `docs/production-readiness/planning/passes/ws05/ws05-03-intake.md` |
| Authority | Corrected master blueprint sections 5.4, 5.5, 8.3, and 14; read-first and Program Context; implementation workflow section 6 |
| Factual state | Execution register records `WS05-01A` and `WS05-02` accepted, `WS05-01B` deferred, and `WS05-03` unimplemented |
| Register update | Record the accepted A/B decomposition with the first substantive child PR; this local Stage 0 intake does not mark either child accepted |
| Later obligations | `WS05-01B` final worker proof; `WS05-04` provider/failure and deployed reconciliation proof; applicable `WS09` and `WS10` operations |
| Blockers for A | None identified from current repository truth |
| Exact next allowed action | Under a new instruction, perform Gate A engineering planning and plan review for `WS05-03A` against then-current `develop`; do not begin Gate B from this intake |

The section 6.5 cohesion test supports the split. Each verdict applies to the
proposed child as an independently acceptable result.

| Question | A verdict and basis | B verdict and basis | Split implication |
|---|---|---|---|
| One primary outcome | Yes: fulfill known monetary obligations truthfully. | Yes: discover and compare bounded unresolved/recent state. | Distinct outcomes support separate acceptance. |
| One invariant family | Yes: preserve value and outcome truth across refunds, credits, compensation, and notices. | Yes: bounded discovery, provider comparison, and safe handoff. | Cross-child financial models are shared prerequisites, not duplicated implementation. |
| One prerequisite state | Yes: accepted durable jobs, payment state, and existing money records. | Yes: accepted A plus existing targeted reconciliation. | B has a later prerequisite, so the parent is not one prerequisite state. |
| One safe merge or forward-fix unit | Yes: mixed-value dispositions and their notices must stay consistent. | Yes: a periodic scan can be added after safe individual paths exist. | A is a safe intermediate state; a scan need not merge with A. |
| One evidence model | Yes: local transactional, provider-boundary, and value-invariant proof. | Yes: bounded scheduling/discovery, provider-read pacing, and reconciliation proof. | The evidence questions differ. |
| One semantic review model | Yes: every disposition is authorized, idempotent, and truthful. | Yes: discovery neither misses eligible recent work nor produces duplicate or unbounded effects. | Separate reviews can cover each full invariant family. |
| Safe and useful intermediate state | Yes: individual obligations can complete and recover without periodic discovery. | Yes: B closes the remaining source-owned periodic requirement. | The order preserves a useful A result while the parent remains incomplete. |
