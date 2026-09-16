# WS09-03 Intake - Metrics, Alerts, And Capacity

## 1. What Needs To Be Decided

This intake decides how the metrics, alerts, and capacity parent should execute.
The decision matters because Pickup Lane can add bounded application metrics and
correct the current scanner-latency persistence now, while operational alerts
and credible launch-capacity proof require final provider, topology, workload,
and threshold facts that do not yet exist.

The parent engineering work is `WS09-03 - Metrics, alerts and capacity`. It
covers a small critical signal set for API, database, worker, payment,
reconciliation, provider, storage, and resource pressure; actionable alerting;
and targeted capacity proof for database connections, API concurrency, worker
throughput/backlog, and provider limits.

The execution shape must produce useful provider-independent instrumentation
without inventing final infrastructure facts or treating deferred operational
verification as complete.

## 2. What We Know

This section lists the technical facts and dependencies that determine whether
the parent can execute now or must wait. These facts define the execution
boundary; they do not prescribe the implementation.

| Topic | Current fact or constraint | Why it affects execution |
|---|---|---|
| Corrected parent scope | Current authority requires a small critical metric and alert set for API failures/latency, database exhaustion/timeouts, worker backlog/retry/exhaustion, payment/reconciliation failure, provider throttling/failure, storage failure, and resource saturation. It also requires targeted proof for database, API, worker, and provider capacity. | All of these obligations need a destination, but the corrected scope rejects formal SLO/error-budget bureaucracy, dashboard or alert proliferation, generic cost governance, and a generic load-testing platform. Broader historical WS09-03 wording does not restore those rejected systems. |
| Accepted telemetry and logging foundations | `EN-02` provides correlation, redaction, event-envelope, and bounded low-cardinality telemetry-label contracts. `WS09-01A`, accepted through PR #184, now provides structured API and worker logging with environment and release context. `WS09-02A/B/C` provide accepted administrative-audit behavior. | Provider-independent metrics can reuse these safety and runtime contracts. Central log ingestion and retained search remain mandatory under `WS09-01B`, but direct metric instrumentation does not require that deferred log-provider work. |
| Current metrics state | The repository has safe telemetry-label primitives and structured operational events, but no application metrics registry/export path, selected metrics provider, production signal view, or alert delivery. | The source-owned metric foundation is real implementation work that can proceed now. Provider activation and operational proof cannot be inferred from the existing logging layer. |
| Current signal sources | Current source exposes API request outcomes through structured middleware, database pool and timeout behavior, durable-job state and backlog summaries, payment and reconciliation states, provider timeout/failure classifications, and storage operations. It does not yet record API latency as a metric. | The current finite application population is sufficiently concrete to design and implement a bounded critical metric set, including the missing latency observation. New signal-producing behavior introduced by later payment, reconciliation, storage, or runtime work must preserve the accepted metric contract, and final verification must cover the then-current launch population. |
| Scanner-latency correction | Current moderation source measures scan duration and persists it on saved-content findings, both chat-detection record families, and derived review-signal metadata. The corrected master requires normal metrics/logging instead of a duration value on every moderation record, and the approved `WS09-01` intake assigns this correction to `WS09-03`. | The replacement latency signal and retirement of per-record duration persistence must travel together in the provider-independent child. Splitting them would either lose the signal or temporarily duplicate it, and leaving them unassigned would orphan an explicit correction. |
| Database capacity contract | Accepted `WS04-01A/C` provide application pool settings, a provider-independent deployment-wide connection-budget model, required consumer categories, telemetry inputs, and later-verification rules. `WS04-01D` remains mandatory for the actual provider, topology, pool values, consumers, headroom, and production role/budget evidence. | `WS09-03` should implement the database-pressure signals and later consume the accepted budget evidence; it must not duplicate the budget formula or invent final values. |
| Worker capacity contract | Accepted `WS05-01A` provides durable job states, backlog age/counts, retry/exhaustion state, worker diagnostics, and a portable worker. `WS05-01B` remains mandatory for final worker hosting and runtime proof. | Source metrics can be built from accepted worker state now. Actual worker count, concurrency, throughput, resource sizing, and launch headroom remain final-runtime evidence. |
| Threshold and capacity decisions | The approved evidence-based limits method requires accountable ownership, provider/platform constraints, workload and failure-cost evidence, telemetry, adjustment/rollback behavior, and reassessment triggers. It explicitly approves no alert threshold, capacity value, or launch objective by itself. | The current child must not invent production thresholds or capacity numbers. Those values and their operational behavior belong to the final verification child after evidence and owner approval exist. |
| Final observability and runtime infrastructure | The monitoring/metrics provider, alert destinations, final API and worker topology, final PostgreSQL provider/capacity, final provider quotas, and production launch workload remain unselected or unevidenced. Temporary Vercel, Render, Neon, local, and CI facts are not final production evidence. | Metrics-provider binding, operational signal visibility, alert routing/delivery, provider-native resource saturation, and real launch-capacity measurements are mandatory deferred work with a different prerequisite state and evidence environment. |
| Later consumers | Incident response needs trustworthy alerts and escalation paths, while final readiness needs actual capacity and provider-limit evidence. | The deferred result must complete before final incident procedures rely on its alert routes and no later than final completeness review. |

The expected proof also follows this boundary. The provider-independent child
can be proved from source, deterministic metric observations, focused API and
service behavior, PostgreSQL-backed schema compatibility where the scanner
correction requires it, and affected regressions. The deferred child requires
sanitized provider/configuration evidence, controlled runtime observations,
targeted load or saturation exercises, and end-to-end alert delivery and
acknowledgement evidence.

## 3. Execution Decision

This section states the selected execution shape and why it matches the two
different engineering and verification boundaries. The parent should be split
into one provider-independent executable child and one mandatory deferred
operational child.

Outcome: split current work from mandatory final-infrastructure work.

| Order | Work | Depends on |
|---|---|---|
| `1` | `WS09-03A - Provider-independent critical metrics and scanner-latency correction` | Accepted `EN-02`, `WS02-04C1`, `WS04-01A/C`, `WS05-01A`, `WS05-02`, `WS09-01A`, `WS09-02`, and the current source-owned storage contract |
| `2` | `WS09-03B - Final metrics activation, actionable alerts, and launch-capacity verification` | Accepted `WS09-03A`; stable launch signal producers; selected final monitoring and runtime infrastructure; evidence-backed owner decisions for thresholds, routing, workload, headroom, and provider limits; applicable final database and worker evidence |

`WS09-03A` is an independently acceptable engineering result: it gives the
current application a bounded, privacy-safe critical metric surface and moves
scanner latency from repeated durable records to operational telemetry. It does
not need final provider identity, alert destinations, instance counts, or
production threshold values.

`WS09-03B` is a separate operational result because it binds the final metric
pipeline, small actionable alert set, delivery routes, and measured capacity
evidence to the actual launch environment. Its alerts and capacity findings
must agree: thresholds that warn before hard limits cannot be accepted before
the relevant provider limits, topology, workload, and measurements are known.
That shared final environment makes B one coherent result rather than separate
dashboard, alert, and load-testing children.

The selected design uses direct metrics for WS09-03 signals. Neither child
depends on `WS09-01B` merely because centralized logs remain incomplete. If a
future B plan proposes a genuinely log-derived signal, that specific design
would first have to establish `WS09-01B` as a prerequisite rather than silently
assuming centralized log delivery.

The following cohesion check explains why the parent is split only once.

| Cohesion question | `WS09-03A` | `WS09-03B` | Split implication |
|---|---|---|---|
| One primary outcome | Pass - bounded source metrics plus the inseparable scanner correction form one provider-independent telemetry result. | Pass - final operational monitoring and capacity readiness form one launch verification result. | No additional child is needed. |
| One requirement family | Pass - current metric production, privacy bounds, and replacement of wrongly persisted latency are one source-observability family. | Pass - provider activation, actionable alerting, and capacity proof are one final operational family. | Keep source production separate from final activation. |
| One prerequisite state | Pass - all required source and accepted contracts exist. | Pass - all work waits on the same final-provider, topology, workload, threshold, and evidence state. | The parent cannot safely execute whole. |
| One safe merge or forward-fix unit | Pass - instrumentation and removal of per-record duration persistence can be merged and corrected without final-provider mutation. | Pass - final provider bindings, alerts, and capacity evidence can be activated, adjusted, or rolled back against the selected environment. | Do not mix source migration work with late provider activation. |
| One evidence model | Pass - repository, deterministic application, and focused database evidence. | Pass - provider, configuration, runtime, delivery, and controlled load evidence. | Different evidence environments require the split. |
| One semantic review model | Pass - completeness, label safety, metric behavior, compatibility, and scanner persistence. | Pass - signal delivery, alert actionability/noise, capacity headroom, and provider-limit truth. | Each child can receive a coherent independent review. |
| Safe and useful intermediate state | Pass - direct metrics are usable by local, CI, staging, or any later compatible collector without claiming production activation. | Pass - closes the remaining operational obligations once its trigger is true. | A may complete while B remains visibly incomplete. |

## 4. Where The Parent Work Goes

This section accounts for the complete corrected parent scope. Each row gives a
major responsibility one primary destination so the split does not lose work,
duplicate another pass, or treat deferred evidence as complete.

| Parent work | Goes to | Remaining boundary |
|---|---|---|
| Bounded, privacy-safe source metrics for current API traffic/failure/latency, database pressure/timeouts, worker backlog/retry/exhaustion, payment/reconciliation outcomes, provider throttling/failure, and storage failure | `WS09-03A` | Instrument the complete current finite source population. Later feature passes that add signal-producing paths must preserve the accepted shared contract; `WS09-03B` verifies the final launch population rather than reimplementing source metrics. |
| Provider-independent metric exposure and safe environment/release/outcome dimensions | `WS09-03A` | Final collector/provider binding, provider access, and retention are not claimed. Correlation identifiers and other high-cardinality or sensitive values remain out of metric labels. |
| Scanner latency replacement signal and retirement of execution-duration persistence from all current moderation record and derived metadata paths | `WS09-03A` | Version, taxonomy, and evidence provenance needed for reproducibility remains intact; per-execution performance duration is removed from durable domain history rather than moved into another durable record. |
| Preservation of accepted domain truth | `WS09-03A` | Metrics summarize operational behavior; durable job, payment, reconciliation, audit, moderation, and storage records remain authoritative and are not duplicated into a metrics history. |
| Selected production metrics ingestion and usable operational visibility for the small critical signal set | `WS09-03B` | This does not require a broad dashboard system. Central retained log ingestion remains `WS09-01B`. Monitoring-provider IAM, MFA, access review, and offboarding remain `WS10-02`; metric retention policy remains `WS10-01`. |
| Evidence-based actionable alert conditions, thresholds, routing, maintenance/noise behavior, delivery, acknowledgement, and recovery verification | `WS09-03B` | No value or route may be copied from temporary infrastructure, examples, framework defaults, or unevidenced assumptions. Incident procedures consume these results under `WS10-03`. |
| Final API availability plus provider-native API/worker/database/resource saturation signals not observable truthfully from portable application source | `WS09-03B` | Application-controlled request, health, pressure, and failure signals remain in A; actual external availability, infrastructure utilization, and saturation require the selected final runtime and provider evidence. |
| Targeted production database connection-budget and headroom proof | `WS09-03B` | Consume the canonical `WS04-01C` model and applicable `WS04-01D` facts; do not create another connection-budget formula or role-verification system. |
| Targeted API concurrency and worker throughput/backlog proof at expected launch load | `WS09-03B` | Consume final API/worker topology and applicable `WS05-01B` runtime evidence. Do not create a generic load-testing platform. |
| Provider throttling/limit capacity proof and alert-before-limit behavior | `WS09-03B` | Provider-specific limits require sanitized final-provider evidence. Application retry, idempotency, and reconciliation behavior remain with their accepted or later domain owners. |
| Evidence-based threshold, workload, headroom, and provider-limit decisions | Observability and reliability owner with the applicable platform, database, durable-jobs, payment, storage, and incident-response role hats | The project owner currently holds these role hats on an interim basis. No numeric value is approved until the evidence-based decision method is satisfied. |
| Formal SLO/error-budget machinery, broad service-objective bureaucracy, dashboard/alert proliferation, generic cost governance, and a generic load-testing platform | Not part of the corrected parent | Historical documents may be used as provenance only and cannot restore these rejected outcomes. A provider's ordinary signal view may be used when needed, but building dashboards is not itself a completion requirement. |

## 5. What Happens Next

This section identifies the engineering work that can proceed now and separates
it from the facts that genuinely remain unavailable.

`WS09-03A - Provider-independent critical metrics and scanner-latency
correction` is the next executable work.

Its technical prerequisites are satisfied: the accepted telemetry/privacy,
structured logging, administrative audit, database-budget, durable-job, and
current domain contracts exist in current source. The finite current emitters
and all current scanner-duration persistence paths can be inspected. Final
monitoring-provider selection, alert thresholds, destinations, runtime
topology, provider limits, and launch-load values are not required to implement
or prove this source-owned result.

There is no blocker to `WS09-03A`. The missing final facts block only
`WS09-03B`, whose deferred status remains an incomplete parent obligation rather
than evidence of production readiness.

## 6. Internal Record

| Detail | Value |
|---|---|
| Parent pass | `WS09-03 - Metrics, alerts and capacity` |
| Intake outcome | Decompose current provider-independent work plus a mandatory deferred final-infrastructure follow-up |
| Accepted baseline | Current accepted `origin/develop`, including merged PR #184 for `WS09-01A` |
| Intake path | `docs/production-readiness/planning/passes/ws09/ws09-03-intake.md` |
| Authority sources | `docs/production-readiness/00-READ-ME-FIRST.md`; `docs/production-readiness/01-PROGRAM-CONTEXT.md`; corrected master Sections 5.10, 5.15, 7.4, 8.7, 9, and 14; current implementation workflow Stage 0; current intake template; current source and applicable engineering/testing guidance |
| Execution-register state | The register still uses pre-PR-184 wording for current `WS09-01A` state. Current `develop` proves PR #184 is merged and accepted. Per owner instruction, no standalone register-cleanup edit is made in Stage 0; the substantive WS09-03 PR must reconcile the register with then-current truth. |
| Approved decisions and prerequisites | `FDN-04` evidence-based limit/threshold method; `FDN-07` bounded telemetry/correlation/privacy contract; accepted `EN-02`; accepted `WS02-04C1`; accepted `WS04-01A/C`; accepted `WS05-01A`; accepted `WS05-02`; accepted `WS09-01A`; accepted `WS09-02A/B/C`; current source-owned storage behavior |
| Child order | `WS09-03A -> WS09-03B` after B's deferred trigger is satisfied |
| Current executable child | `WS09-03A - Provider-independent critical metrics and scanner-latency correction` |
| Proposed canonical plan path | `docs/production-readiness/planning/passes/ws09/ws09-03a-provider-independent-critical-metrics-and-scanner-latency-correction.md` |
| Proposed requirement declaration | Not applicable at Stage 0 - Gate A determines whether a separate declaration is genuinely useful under the current workflow. |
| Proposed trusted test or verification location | Not applicable at Stage 0 - Gate A selects proportionate locations from the current backend test structure. |
| Deferred owner | `WS09-03B - Final metrics activation, actionable alerts, and launch-capacity verification`; accountable observability and reliability owner, currently the project owner on an interim basis |
| Preserved deferred obligations | Final metrics-provider ingestion and usable operational signal visibility; evidence-based actionable alert thresholds and routing; delivery, acknowledgement, suppression/noise, and recovery proof; provider-native resource saturation; actual database/API/worker/provider capacity and reasonable launch headroom; alert-before-hard-limit behavior |
| Deferred trigger | `WS09-03A` accepted; final monitoring provider and safe metrics-ingestion path selected; approved metrics-retention and provider-access inputs available; final API, worker, and PostgreSQL topology/capacity inputs evidenced; launch signal producers stable; provider limits and expected launch workload available; owners approve evidence-based thresholds, routing/escalation, and headroom criteria; safe controlled runtime/load and alert-delivery verification can be performed |
| Deferred prerequisites and handoffs | Consumes `WS09-03A`, applicable `WS04-01D` connection-budget facts, applicable `WS05-01B` worker-runtime facts, applicable `WS10-01/02` retention and provider-access decisions/evidence, final provider/runtime evidence, and stable then-current WS05/WS06 signal producers. It does not depend on `WS09-01B` unless a later approved B design genuinely selects a centralized log-derived signal. It supplies alert and capacity facts to `WS10-03` and final readiness review. |
| Latest deferred completion boundary | Run as soon as the trigger is satisfied and before `WS10-03` completes incident procedures that rely on final alert routing, and no later than `CLOSE-01`, whichever first requires these facts. |
| Deferred visibility | Mandatory and incomplete. The execution register must add `WS09-03A` and keep `WS09-03B` visible when reconciled with the eventual substantive PR. Deferred status does not complete `WS09-03` or any B-owned requirement. |
| Blockers | None for `WS09-03A`; `WS09-03B` is not executable while its final-infrastructure trigger is false. |
| Exact next allowed action | With explicit owner authorization, perform Gate A engineering planning and plan review for `WS09-03A`; do not begin Gate B or any provider/configuration work. |
