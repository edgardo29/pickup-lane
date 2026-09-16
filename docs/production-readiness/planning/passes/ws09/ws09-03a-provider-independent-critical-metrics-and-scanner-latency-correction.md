# WS09-03A - Provider-independent critical metrics and scanner-latency correction

This work gives Pickup Lane a bounded, privacy-safe application metrics surface for its current critical operational signals and moves moderation scan duration out of durable domain records into operational telemetry.

This document is the engineering blueprint for this work.

## 1. What This Work Does

This section defines the result of the work and its engineering boundary. The application already has bounded telemetry-label validation and structured API/worker logging, but it does not yet have a provider-independent metrics recorder or a correct operational home for moderation scan duration.

The finished system has a small direct-metrics contract for the current critical application signals: API traffic/error/latency and in-flight pressure, database pool pressure/timeouts, durable-worker backlog/retry/exhaustion, payment and reconciliation execution/results and open financial discrepancies, provider/storage operation failures and throttling, and moderation scan latency.

Metrics are operational summaries only. Existing durable job, payment, reconciliation, moderation, audit, and storage records remain authoritative for domain history and must not be duplicated into a second metrics history.

Moderation scan duration is removed from saved-content moderation findings, both chat-detection record families, and derived review-signal metadata. The scanner still preserves the provenance required to reproduce and interpret a moderation result: scanner identity/version, taxonomy/configuration, canonicalization/evidence format, target context, declared limits, scan time, content hashes, rule versions, and evidence.

The metrics implementation remains independent of any final monitoring provider. It does not select or configure a metrics vendor, create production alert thresholds or routes, add provider-native resource-utilization monitoring, expose a public metrics endpoint, establish retention policy, or claim launch-capacity proof.

## 2. What Must Be True

These requirements define the observable behavior and safety properties that must hold when the work is complete. They intentionally describe a small metrics surface rather than a general telemetry platform.

### 2.1 The metrics contract is bounded and provider-independent

- The application has one canonical runtime metrics contract shared by API and worker code.
- Metric names, kinds, units, and allowed dimensions are declared from a finite application-owned inventory. Runtime callers cannot invent metric names or arbitrary label keys.
- Metric dimensions reuse the existing telemetry-label safety rules. Correlation IDs, request IDs, user IDs, payment IDs, booking IDs, provider object IDs, object keys, URLs, email addresses, phone numbers, exception text, free text, and other high-cardinality or sensitive values are never metric dimensions.
- `environment`, `release`, and process source identity are immutable recorder metadata. They are not caller-controlled labels.
- Runtime observations are direct metrics. They do not depend on centralized log ingestion or parsing.
- Each validated observation can be delivered through a provider-neutral sink interface so distributions retain per-observation semantics without binding the application to a monitoring vendor.
- Recording a metric must never change an API response, provider call result, transaction outcome, job lifecycle, retry decision, or moderation decision.
- No configured metrics sink may make a network call as part of this work.

### 2.2 API request signals are complete and single-owned

- Every completed HTTP request produces exactly one request-count observation and one latency observation.
- API latency uses a monotonic clock and spans the same request lifecycle that owns the final observable response status.
- The request result is classified as `success` for status 100-399, `client_error` for 400-499, and `server_error` for 500-599.
- The route dimension is the validated framework route template after routing or the existing fixed `/{unmatched}` fallback. Raw paths and query strings are never metric data.
- The HTTP method is converted to a fixed operation token. The supported methods are `http.get`, `http.post`, `http.put`, `http.patch`, `http.delete`, `http.head`, and `http.options`; any other method becomes `http.other`.
- An in-flight gauge increases once when an HTTP request enters the application request-lifecycle owner and returns to its prior value on every completion or failure path.
- Handled errors, dependency/database timeouts, unexpected exceptions, and exceptions after response start do not create duplicate request observations.

### 2.3 Database pressure and timeout signals reflect application-controlled state

- The application exposes the number of currently checked-out SQLAlchemy pool connections as a gauge when the configured engine uses a pool that can report that value.
- The application exposes the configured per-process application pool ceiling as `pool_size + max_overflow` when those settings are configured. This is an application pool value, not a claim about final database-provider capacity.
- Database timeout observations use the existing timeout classifications: `database.pool_wait`, `database.statement`, and `database.lock`.
- Connection identities, SQL text, statement parameters, database URLs, and provider-private values never enter metrics.
- Pool observations do not add connection acquisition, alter checkout/check-in behavior, or introduce an independent connection-budget formula.

### 2.4 Worker and payment/reconciliation health comes from authoritative durable state

- Durable-job state outcomes are recorded after the authoritative transition commits; existing missing/unsupported/lease-lost diagnostics retain their distinct non-transition meaning.
- The worker result dimension uses the current bounded lifecycle outcomes emitted by the runner, including `succeeded`, `retry_waiting`, `exhausted`, `lease_lost`, `missing`, and `unsupported` where those paths occur.
- Idle polling and ordinary shutdown do not increment job-outcome metrics.
- Backlog gauges report pending, retry-waiting, leased, and exhausted durable work by a fixed `job_type` vocabulary. Exhausted work remains observable after process restart. Oldest-age gauges distinguish executable ready work from unsupported ready work.
- Backlog observation is derived from database aggregate queries over authoritative durable-job rows; it does not load payloads, protected identity, result metadata, correlations, or complete job histories into metric state.
- Durable-job outcomes describe execution, not the success of the underlying payment or reconciliation result. A separate bounded reconciliation-result observation distinguishes an authoritative failed payment-method operation from a successfully completed reconciliation job; it is emitted only after the owning transaction commits.
- Unresolved financial discrepancies are exposed as a gauge derived from authoritative open `MoneyIssue` rows, partitioned only by the existing fixed issue-type taxonomy. Amounts, currencies, payment/refund IDs, users, summaries, and operation keys are not dimensions.

### 2.5 Provider and storage outcomes use stable classifications

- Current external-provider operations record bounded outcome observations at the application boundary where success or failure is known.
- `provider_kind` is limited to `stripe`, `firebase`, and `r2`. Operations and applicable outcomes are defined by the current client-boundary matrix in Section 3.7, independently of the declarative retry-policy registry. Metrics neither import nor extend that registry; its removal is not part of this work.
- Provider outcomes use fixed result classes: `succeeded`, `timed_out`, `unknown_outcome`, `rate_limited`, `failed`, `configuration_error`, `not_found`, and `rejected`, only where the corresponding application path actually has that meaning. Expected credential and payment rejection is never reported as an operational provider failure.
- A provider operation is `rate_limited` only when a typed SDK/provider error or explicit provider status/code establishes throttling. Exception-message parsing is never used.
- Read timeouts and mutation timeouts preserve their existing distinction; mutation timeout remains an unknown provider outcome where the existing contract says so.
- R2 object-not-found remains distinct from storage failure.
- Adding metrics does not add retries, alter retry ownership, or change existing provider exception translation.

### 2.6 Scanner latency becomes operational telemetry instead of domain history

- Saved-content moderation and both chat moderation paths observe scan duration as `moderation.scan.duration_seconds` using a monotonic clock.
- The metric operation identifies only the fixed moderation target context. Scanner version, taxonomy version, configuration hash, content identity, message/game/post identity, and matched evidence are not metric dimensions.
- The existing chat timing boundary is preserved: where chat workflows start the timer before repeated-message context evaluation and pass that start time into scanning, the replacement metric uses that same start point.
- `execution_duration_us` is removed from `ScanProvenance`.
- `execution_duration_us` is removed from saved-content moderation finding persistence and from both chat-detection persistence families.
- The nonnegative duration check constraints associated with those columns are removed from the canonical table definitions.
- Chat detection aggregation no longer requires duration equality and no longer reconstructs duration into scan provenance.
- `scan_execution_duration_us` is removed from derived administrative review-signal metadata.
- No replacement duration field is added to another database column, JSON metadata field, durable event, or audit record.
- Removing duration does not change moderation finding identity, detection identity, scan timestamps, scanner/taxonomy/configuration provenance, evidence fingerprints, declared limits, content hashes, rule versions, or moderation decisions.

### 2.7 Metrics failures are isolated from product behavior

- Invalid runtime metric data is rejected without raising into business logic.
- A metric observation containing an unsupported name, unsupported dimension, unsafe dimension value, non-finite numeric value, negative duration, or invalid counter delta is not recorded.
- Static metric-definition mistakes are configuration/programming errors and fail metrics initialization before the affected API or worker process begins normal work.
- Failures while collecting an observable gauge produce a partial metric snapshot rather than mutating product state or failing a request/job.
- Each collection replaces the complete series population of each observable family; absent or failed families never retain a previous collection's values. Counts explicitly return zero, while an unavailable age or unsupported pool observation is absent.
- All declared gauges are nonnegative. Matching API entry/exit accounting remains balanced even when an optional sink fails.
- Metric storage remains bounded by the finite descriptor and dimension population. Distribution aggregation does not retain an unbounded list of raw observations.

## 3. Design

The design adds a small metrics layer under the existing observability ownership, instruments the current canonical lifecycle owners, and treats database-backed gauges as read-only views of authoritative state. It reuses existing safety contracts instead of creating a second label or redaction system.

### 3.1 Runtime metrics recorder and metric definitions

Add a focused metrics module under the existing backend observability package. It owns metric definitions, validation, recording, aggregation, observable-gauge registration, and deterministic snapshots. It does not own domain rules, provider retries, database transitions, or alert policy.

Each metric is declared by an immutable descriptor with:

- canonical metric name;
- metric kind: `counter`, `gauge`, or `distribution`;
- unit;
- exact allowed dimension names;
- exact fixed result/operation/job-type vocabulary when the metric requires one;
- numeric domain: nonnegative finite numbers for durations and gauges, nonnegative integers for counts and counter increments. Booleans are not numeric observations.

The recorder is constructed with the same validated process identity used by structured logging:

- `source_identity`: `api` or `worker`;
- `environment`: the existing validated application environment;
- `release`: the existing release identity.

Callers provide only the metric's declared dimensions and numeric value. The recorder validates dimensions through the existing telemetry validators before changing metric state.

Every validated observation is represented by an immutable metric observation containing the descriptor, numeric value, validated dimensions, and recorder identity. Event observations also carry a monotonically increasing recorder-local event sequence assigned atomically with canonical state mutation. The recorder owns canonical thread-safe in-memory state and can dispatch validated observations to an optional `MetricSink`. The sink has two operations: record one event observation, and replace one complete observable-family batch for a collection cycle. The batch contains recorder identity, a fixed family name, a process-local collection sequence number, and validated observations; a failed family is explicitly marked unavailable. Event and collection sequences are separate protocol fields, never dimensions. This preserves distribution observations and observable disappearance without choosing a transport.

Canonical in-memory state aggregates event observations by descriptor plus sorted validated dimensions:

- counters store a nonnegative monotonically increasing total;
- event gauges store the latest nonnegative finite value; the API in-flight gauge uses the dedicated atomic entry/exit accounting described below;
- distributions store `count`, `sum`, `min`, and `max` and never retain an unbounded observation list.

Validation and canonical state mutation are atomic and precede optional sink delivery. Each distribution observation is still delivered individually, not reduced to its aggregate. A record method's boolean result means the observation was accepted into canonical state, not that the optional sink delivered it: sink failure is contained and does not change an already-true acceptance result, roll back state, or alter lifecycle ownership. No network-backed sink is configured. Do not invoke sink code while holding the canonical-state lock, and do not retry failed delivery. A sink must not recursively invoke recorder collection or recording.

Sink operations must be safe under concurrent calls. Event delivery may arrive out of canonical mutation order. For each event-gauge series, the sink atomically applies a value only when its event sequence is newer than the last applied sequence; retain only that sequence and current value, not event history. Counter increments and distribution samples remain additive observations and must all be applied when delivered, even out of sequence. Sequence comparison is scoped to the attached recorder's lifetime, not merged using environment/release/source metadata as an instance identifier. A new recorder uses a fresh sink binding or resets that binding's state. Thus concurrent exits that canonically change in-flight pressure from `2 -> 1 -> 0` cannot leave the sink at `1` when delivery arrives as `0` then `1`. Failed delivery remains best-effort and does not change canonical acceptance or introduce retries.

A deterministic snapshot returns recorder identity, sorted metric series, and the fixed unavailable-family names for that collection. It is an application interface for testing and local inspection, not an HTTP endpoint or background exporter. It performs no provider-network I/O; explicitly requested database-backed collections do perform the bounded read-only queries below.

Observable callbacks own three disjoint fixed families: `database_pool`, `durable_backlog`, and `financial_discrepancy`. A callback returns the complete family batch when an explicit collection is requested. Collection cycles are serialized per recorder; callbacks run outside the event-state lock. Validate the entire batch before publishing it. Duplicate series or any invalid observation invalidate that family, not merely one row. On successful collection, replace the prior family atomically, including removal of series not returned. On callback/query/validation failure, publish an empty unavailable family and discard its previous series. The other families and event aggregates remain valid. Never retain cached values as if they were current. Optional sink failure does not undo the local replacement. Empty count populations yield the explicit fixed zero series below; empty oldest-age populations yield no series.

Process ownership is fixed rather than chosen by deployment topology:

| Family or observations | API recorder | Worker recorder |
|---|---|---|
| HTTP events/in-flight | Yes | No |
| Local database pool and timeout events | Yes | Yes |
| Provider and scanner events | Within API execution | Within worker execution |
| Job and reconciliation-result events | No | Yes |
| Global durable-backlog and MoneyIssue observables | Yes | No |

The API is the only process category collecting global database state. Multiple API instances observe the same global gauges; these are replicated snapshots, not additive per-instance counts. Recorder metadata does not pretend to identify final instances. Provider adapters must preserve gauge semantics rather than sum replicas; final topology binding remains outside this work. Register pool callbacks on both process recorders, and global callbacks only on API app construction. Each database callback opens its own `SessionLocal` context, executes only aggregate SELECTs, and closes/rolls back its read transaction on success or failure. It never uses a request or job session, commits domain work, or adds rows. No scheduler, polling task, or collector starts at import or app construction.

Runtime record methods are non-throwing and return success/failure. Descriptor registration and process initialization are strict because an invalid static metric definition means the application cannot truthfully expose its declared metrics contract.

Use the same active/process ownership pattern already used by structured runtime events:

- API request execution activates the API recorder for downstream provider/service instrumentation.
- The portable worker command activates its recorder around startup readiness, status inspection, claiming, handler execution, outcome commits, heartbeat, and shutdown database work. The runner also activates its supplied recorder when invoked directly. The lease-renewer thread explicitly activates that same recorder; context variables do not implicitly cross threads.
- A caller outside an active supported runtime context receives a no-op recording result rather than creating an unconfigured recorder.
- Repeated application construction in tests replaces or resets the intended process recorder rather than stacking collectors or leaking metric state between app instances.

### 3.2 Critical metric inventory

The following inventory is the complete metric surface established by this work. Metric names and dimension sets are fixed; implementation may not add neighboring metrics merely because a call site is convenient.

| Metric | Kind | Unit | Dimensions | Meaning |
|---|---|---|---|---|
| `api.request.total` | counter | requests | `operation`, `route_template`, `result` | Completed HTTP requests by fixed method operation, validated route template, and status class. |
| `api.request.duration_seconds` | distribution | seconds | `operation`, `route_template`, `result` | Monotonic request duration for the same completed request population. |
| `api.request.in_flight` | gauge | requests | none | Requests currently inside the API request-lifecycle owner for this process. |
| `database.pool.checked_out` | gauge | connections | none | Current checked-out application-pool connections when available from the active SQLAlchemy pool. |
| `database.pool.capacity` | gauge | connections | none | Configured per-process application ceiling `pool_size + max_overflow` when those settings are configured. |
| `database.timeout.total` | counter | timeouts | `operation`, `result` | Classified pool-wait, statement, and lock timeouts; `result` is `timed_out`. |
| `worker.job.outcome.total` | counter | jobs | `job_type`, `result` | Post-commit durable-job state outcomes and existing missing/unsupported/lease-lost diagnostics; measures execution, not underlying payment success. |
| `worker.backlog.count` | gauge | jobs | `job_type`, `result` | Current backlog count by job type and bounded queue state. |
| `worker.backlog.oldest_age_seconds` | gauge | seconds | `job_type` | Age since availability of the oldest executable ready job, or unsupported ready work; absent when the corresponding population is empty. |
| `payment.reconciliation.outcome.total` | counter | operations | `job_type`, `result` | Committed domain reconciliation result, distinct from whether the job successfully ran; fixed mapping in Section 3.6. |
| `financial.discrepancy.open` | gauge | issues | `operation`, `result` | Count of authoritative open money issues; `operation` is `money_issue.<fixed_issue_type>` and `result` is `open`. |
| `provider.operation.outcome.total` | counter | operations | `provider_kind`, `operation`, `result` | Stable success/failure/timeout/throttle outcomes for current Stripe, Firebase, and R2 boundaries. |
| `moderation.scan.duration_seconds` | distribution | seconds | `operation` | Monotonic scan latency by fixed moderation target context. |

No correlation dimension is present. Release and environment are recorder metadata. The metric inventory intentionally does not create separate counters for every durable domain transition.

### 3.3 API request timing and in-flight pressure

Extend the existing correlation/request middleware rather than adding a second request-observability middleware.

At HTTP entry:

1. take a monotonic start timestamp;
2. increment `api.request.in_flight`;
3. retain the canonical entry-acceptance boolean plus separate metric-completed/in-flight-released booleans in the safe scope state used by the existing completion/error path. These flags are request-local bookkeeping, not observations or labels.

At the single request-completion owner:

1. determine the final observable status;
2. resolve the matched route template or `/{unmatched}`;
3. normalize the method to the fixed operation vocabulary;
4. derive the result status class;
5. increment `api.request.total`;
6. observe monotonic elapsed seconds in `api.request.duration_seconds`;
7. run the shared release helper in a `finally` path. It atomically decrements the canonical gauge only when this request's entry was accepted and its release flag is still false, then marks it released. Also invoke this helper in middleware's exit `finally`, so a failed/late outer-completion path cannot strand the gauge. Duplicate invocation is a no-op.

The recorder exposes dedicated non-throwing enter/exit operations for this gauge; callers cannot pass arbitrary signed gauge deltas. Canonical entry acceptance is independent of optional sink delivery. If entry itself is unavailable, mark it unaccepted and never decrement on exit. Completion claims its flag once before recording count/duration, so error handling cannot duplicate them. Middleware exit releases in-flight accounting even when the outer error handler supplies classification after the inner middleware unwinds; the outer helper cannot release it again. Sink failures during entry, count/duration delivery, or exit cannot produce negative or stranded in-flight values. No global request-token set or durable request history is needed.

The existing unexpected-error path must call the same completion helper used by ordinary completion so a request cannot emit two count or duration observations. If an exception occurs after response start, use the already captured status exactly as the current logging path does. If no response status was started, classify the unexpected response as 500.

The metric path must not inspect or store the raw request target, query, body, headers, cookies, client address, user agent, response body, exception text, or correlation ID.

### 3.4 Database pool pressure and timeout instrumentation

Database pool pressure is read from the current SQLAlchemy engine rather than maintained as a second independent checkout counter.

Register observable gauges that:

- return the pool's current checked-out count when the active pool supports that query;
- return the configured application pool ceiling from validated application settings when `pool_size` and `max_overflow` are configured;
- omit an unavailable observation instead of guessing a value for an alternate/test pool implementation.

The ceiling is strictly the per-process application pool configuration. It is not compared with a provider connection cap inside this work.

Observe database exceptions below service/HTTP translation so caught readiness failures, handler retries, and internally suppressed exceptions remain visible. `backend.database` owns two passive observation hooks on the shared application engine:

1. A minimal `QueuePool` subclass overrides the public `connect()` boundary only to catch, observe, and re-raise connection-acquisition/checkout exceptions. It delegates all acquisition, timeout, recycling, and checkout behavior unchanged to `QueuePool`; no custom queue or connection counter is added. SQLAlchemy pool-wait `TimeoutError` is observed here because it does not reach engine `handle_error`.
2. An engine `handle_error` listener observes classified DBAPI execution errors, using `ExceptionContext.original_exception` as the failure origin alongside `ExceptionContext.sqlalchemy_exception`. It returns no replacement exception, performs no queries, and changes neither rollback nor invalidation behavior.

Reuse the existing safe database classification. Where checkout's direct DBAPI timeout-setting calls expose an unwrapped driver exception, recognize the same typed psycopg `LockNotAvailable` and `QueryCanceled` causes without changing their public translation. Map only the three existing database timeout kinds:

- `pool_wait` -> `database.pool_wait`;
- `statement` -> `database.statement`;
- `lock` -> `database.lock`.

Do not parse arbitrary database exception strings and do not expose SQL or connection details.

The shared observation helper classifies and deduplicates the current failure by its originating pool/DBAPI exception. Use the explicitly supplied `ExceptionContext.original_exception` when present; otherwise follow the current SQLAlchemy exception's `.orig` links to the originating driver exception, or use the current exception itself for an unwrapped driver error or pool-wait `TimeoutError`. This traversal is identity-cycle-safe. The engine wrapper's `__cause__` may not yet be attached when `handle_error` runs, so cause/context traversal is not required to recover its supplied original. Classify only this origin using the existing pool-wait/statement/lock meanings; a non-timeout origin must not inherit timeout classification from an earlier handled exception.

Place one private observed boolean on the classified origin before recorder delivery. The pool hook and any engine wrapper/rethrow exposing that same origin see the same mark and do not record twice. Do not mark or inspect unrelated implicit `__context__` exceptions for deduplication: new database work inside an exception handler can fail independently while Python links it to the previous failure. Distinct driver origins count separately even in that context. Marks are not retained in a process collection, persisted, or sent to the sink. The entire observation helper, including classification/marking, is non-throwing; it cannot mask the original database exception. No API exception handler, session rollback handler, durable-handler catch block, or query collector adds another observation. Public timeout translation remains unchanged.

| Current database population | Observation owner | Recorder context |
|---|---|---|
| API dependency/session acquisition, execution, flush, and commit, including exceptions caught inside services | Shared pool/engine hooks | Active API request |
| Readiness `check_database_connection()` and API lifecycle connectivity work | Shared pool/engine hooks | API recorder explicitly activated around lifecycle/readiness work |
| Worker startup/status, claim, handler, transition commits, heartbeat, and shutdown | Shared pool/engine hooks | Worker command/runner context |
| Lease renewal in its background thread | Shared pool/engine hooks | Explicit worker recorder context in that thread |
| Backlog/MoneyIssue observable SELECTs | Shared pool/engine hooks | API recorder explicitly activated for collection |
| Alembic, unrelated maintenance engines, unsupported runtime calls, and test-only engines without instrumentation | Not application metric producers | No recorder is created implicitly |

Register hooks once per engine rather than per app instance. Shared pool options and the existing timeout-setting checkout callback remain intact. If a supported test engine is constructed for hook proof, use the same instrumentation helper. No raw exception object, connection, statement, parameters, or `ExceptionContext` enters metric observations; only the fixed classified operation and `timed_out` result do.

### 3.5 Durable-worker backlog and outcome instrumentation

The durable runner already owns authoritative post-commit job outcomes. Add the metric observation to that same outcome-emission boundary after the durable state transition has committed.

Use the actual event result rather than the return string when they differ. In particular, a final transient failure that commits exhaustion must be observed as `exhausted`, matching the durable event/state rather than the runner's compatibility return value.

Do not emit a job metric for `idle` or normal `shutdown`.

Expose backlog through aggregate database queries rather than the existing operator summary's all-row materialization. The metric query returns only bounded aggregates:

- counts grouped by current `job_type` and queue state;
- oldest available/claimable job age grouped by `job_type`.

The job-type vocabulary is exactly `stripe_webhook_event`, `stripe_payment_intent_reconcile`, `stripe_payment_method_operation_reconcile`, and the fixed fallback `unsupported`. Map each row using the production registry's supported `(job_type, payload_version)` pairs, not a regex alone: an unknown type or unsupported version maps to `unsupported`, never its stored arbitrary string. The same fallback applies to event observations from generic runner/test definitions outside the production inventory.

The complete queue-state allocation is:

| Durable status | `worker.backlog.count` | Oldest-age membership |
|---|---|---|
| `pending` | Included, regardless of future `available_at` | Ready only when `available_at <= database_now` and `attempt_count < maximum_attempts` |
| `retry_waiting` | Included, including delayed retry | Same ready predicate as pending |
| `leased` | Included; both live and expired leases | Not included: expired-lease recovery is distinct from ready pending work |
| `exhausted` | Included as durable unresolved repair pressure, including rows predating process startup | Not included |
| `succeeded` | Excluded completed history | Not included |
| `cancelled` | Excluded cancelled history | Not included |

For supported rows, oldest age is `max(0, (database_now - min(available_at)).total_seconds())` under the exact ready predicate above and supported-pair membership. For unsupported rows, the same status/availability/remaining-attempt predicate yields the `unsupported` age series; it means ready work that this production registry cannot execute, not a claim that it is executable. Return all 16 job-type/state count series explicitly, including zero; return age only for nonempty corresponding populations. Use database time, as claiming does, rather than a process wall clock. Aggregate with SQL CASE/grouping and MIN/COUNT; do not first materialize distinct arbitrary job types into Python or metric dimensions.

The outcome result vocabulary is exactly `succeeded`, `retry_waiting`, `exhausted`, `lease_lost`, `missing`, and `unsupported`. Existing runner outcome diagnostics without a successful state transition (missing, unsupported, lease-lost) remain diagnostic observations, not claims of a committed transition. Claim-time expired-lease exhaustion uses the existing post-commit outcome owner too. Do not add counters for enqueue, lease acquisition, idle, heartbeat, shutdown, or operator requeue. Existing operator diagnostics, including expired leases and heartbeat age, remain unchanged; this metric surface does not duplicate every diagnostic field.

The aggregate query does not select job payloads, protected identities, result metadata, lease tokens, correlations, or origin identifiers.

For `stripe_webhook_event`, `stripe_payment_intent_reconcile`, and `stripe_payment_method_operation_reconcile`, `worker.job.outcome.total` is the current payment/reconciliation execution metric. The `job_type` dimension distinguishes those workflows without adding payment identifiers or a duplicate domain counter.

### 3.6 Payment, reconciliation, and financial discrepancy health

Job execution and domain resolution are different facts: a reconciliation job can correctly finish by establishing that the underlying payment-method operation failed. Keep `worker.job.outcome.total` unchanged and add `payment.reconciliation.outcome.total` with only the two reconciliation job types and results `succeeded`, `failed`, `pending`, or `already_terminal`. The finite source-result mapping is:

| Current producer | Source result | Domain metric result |
|---|---|---|
| Stripe webhook handler | `processed`, `ignored`, `failed`, retry | No reconciliation-result metric; runner success/retry/exhaustion measures ingestion/processing, not the customer's payment outcome |
| PaymentIntent reconcile | `processed` | `succeeded`: reconciliation applied its authoritative observation; not a claim the customer paid |
| PaymentIntent reconcile | `already_terminal` | `already_terminal` |
| PaymentIntent reconcile | `permanent_failure` | `failed` |
| PaymentIntent reconcile | `retry` | `pending` |
| Payment-method operation reconcile | `succeeded` | `succeeded` |
| Payment-method operation reconcile | `failed`, including an already-failed or missing operation | `failed`, even though the compatible handler/runner result is success |
| Payment-method operation reconcile | `provider_unknown` | `pending` |

The payment consumer maps its returned scalar outcome to an immutable bounded observation staged in the runner's current attempt context. The generic runner does not inspect provider results, ORM rows, arbitrary result metadata, or payloads to infer domain outcome. Staged observations are transient telemetry data and are not added to `HandlerResult.result_metadata`, durable job rows, or event history. Emit at most one staged reconciliation result per attempt only after the runner commits its successful completion/retry/exhaustion transition; discard on rollback, failed commit, or lease loss. A handler exception before a scalar domain result is obtained produces only the normal worker retry/exhaustion signal. This adds no retry, transaction, reconciliation, or payment-state behavior. Repeated legitimate attempts are separate operational observations, not exactly-once financial history.

Expected customer payment states (`requires_payment_method`, `requires_confirmation`, `requires_action`, `processing`, `requires_capture`, `succeeded`, `canceled`, and the existing unknown fallback), full-credit checkout, and ordinary user cancellation are not infrastructure failures. They remain authoritative domain state and are not copied into a second payment-transition counter. Operational Stripe SDK failures are observed through provider outcomes; webhook processing and reconciliation failures through worker/domain-result outcomes; refund/credit discrepancies through MoneyIssue pressure. Later refund/credit workflows not registered as current durable consumers are not invented here.

Open `MoneyIssue` rows already represent unresolved financial discrepancies and repair obligations. Expose them as an observable gauge rather than creating metrics at every money-issue event.

The query groups only rows with `status = "open"` by `issue_type`. Each authoritative issue type from the current fixed `ISSUE_DEFAULTS` taxonomy maps to:

- `operation = "money_issue.<issue_type>"`;
- `result = "open"`;
- gauge value = current row count.

This keeps the metric synchronized with durable truth after reopen/resolution and avoids overcounting rolled-back attempts or duplicating money-issue event history.

Return an explicit count, including zero, for all seven current issue types: `refund_missing_provider_reference`, `refund_processing_overdue`, `refund_failed`, `refund_cancelled`, `refund_outcome_unknown`, `credit_restore_failed`, and `credit_release_failed`. Tests reconcile this population with `ISSUE_DEFAULTS` and the model's issue-type constraint. Resolved rows are excluded; no current payment-method operation failure is silently assumed to create a MoneyIssue.

### 3.7 Provider and storage operation outcomes

Provider metrics are recorded at the existing shared boundaries where the application already decides whether an external operation succeeded or how an exception is translated.

The following matrix is the complete population, derived from the actual client calls rather than a retry-policy inventory. Provider kind must match the operation prefix, and result must belong to that operation's declared vocabulary. Callers cannot supply new strings. In this matrix, **read outcomes** mean `succeeded`, `timed_out`, `rate_limited`, `failed`, and `configuration_error`; **mutation outcomes** mean `succeeded`, `unknown_outcome`, `rate_limited`, `failed`, and `configuration_error`. Local presigning has no remote mutation-unknown outcome.

| Operation | Exact current client owner/call | Applicable outcomes |
|---|---|---|
| `stripe.customer.create` | `stripe_service.create_customer` / customers.create | Mutation outcomes |
| `stripe.setup_intent.create` | `create_setup_intent` / setup_intents.create | Mutation outcomes |
| `stripe.setup_intent.retrieve` | `retrieve_setup_intent` / setup_intents.retrieve | Read outcomes |
| `stripe.payment_method.retrieve` | `retrieve_payment_method` / payment_methods.retrieve | Read outcomes |
| `stripe.payment_method.detach` | `detach_payment_method` / payment_methods.detach | Mutation outcomes |
| `stripe.customer.default_payment_method.set` | `set_customer_default_payment_method` / customers.update | Mutation outcomes |
| `stripe.customer.default_payment_method.clear` | `clear_customer_default_payment_method` / customers.update | Mutation outcomes |
| `stripe.payment_intent.create` | `create_payment_intent` / payment_intents.create | Mutation outcomes plus `rejected` for typed CardError |
| `stripe.payment_intent.confirm` | `confirm_payment_intent` / payment_intents.confirm | Mutation outcomes plus `rejected` for typed CardError |
| `stripe.payment_intent.retrieve` | `retrieve_payment_intent` / payment_intents.retrieve | Read outcomes |
| `stripe.refund.create` | `create_refund` / refunds.create | Mutation outcomes |
| `stripe.refund.retrieve` | `retrieve_refund` / refunds.retrieve | Read outcomes |
| `firebase.token.verify` | `firebase_admin_client.verify_firebase_token` / auth.verify_id_token and decoded UID validation | Read outcomes plus `rejected` for invalid/expired/revoked/disabled token, ValueError, or UserNotFoundError from the SDK's revoked-token user check |
| `firebase.user.lookup` | `verify_firebase_token` / auth.get_user and disabled-user validation | Read outcomes plus `not_found` for UserNotFoundError and `rejected` for UserDisabledError |
| `firebase.user.lookup` | `firebase_email_exists` / auth.get_user_by_email | Read outcomes plus `not_found`; preserve the current False return |
| `firebase.app_check.verify` | `verify_firebase_app_check_token` / app_check.verify_token | Read outcomes plus `rejected` for ValueError |
| `firebase.user.delete` | `delete_firebase_user` / auth.delete_user | Mutation outcomes; absent user is `succeeded` because deletion is idempotently complete |
| `r2.upload_url.create` | `r2_storage_service.create_object_upload_url` / generate_presigned_url(put_object) | `succeeded`, `timed_out`, `rate_limited`, `failed`, `configuration_error` |
| `r2.read_url.create` | `create_object_read_url` / generate_presigned_url(get_object) | Same local-presigning outcomes |
| `r2.metadata.head` | `get_object_properties` / head_object | Read outcomes plus `not_found` |
| `r2.upload.validate` | `venue_image_service.validate_upload_request` / its configuration preflight | `configuration_error` only; no success or ordinary request-validation observation |
| `r2.readiness.check` | `check_venue_image_upload_readiness` / its configuration preflight | `configuration_error` only; its database failure belongs to database metrics |

The two R2 preflights are included because configuration can fail before the lower storage call is reached. Successful preflights do not duplicate the lower operation. For upload construction's separate `get_r2_storage_config()` before presigning, emit `r2.upload_url.create/configuration_error` only when that preflight raises; otherwise the storage client owns the observation. Do not instrument existing higher-level storage error logging as a second generic metric owner. Game/official-game read-URL callers are covered by the shared storage client, including their fallback paths.

Stripe webhook signature verification (`construct_webhook_event`) is local inbound validation, not an external provider operation; its invalid-request/configuration response is covered by API outcomes and valid stored-event execution by worker outcomes. Inbound `stripe.webhook.delivery` and application repair operations from the old registry are excluded from this provider counter. No new webhook, financial-repair, or retry framework is introduced.

Outcome classification is:

- `succeeded`: the provider boundary returned the result expected by the application;
- `timed_out`: an existing read-timeout contract establishes a known failed read;
- `unknown_outcome`: an existing mutation-timeout contract says the remote mutation may have happened;
- `rate_limited`: the provider SDK exposes a typed throttling/resource-exhaustion error or explicit throttling status/code;
- `not_found`: an existing provider boundary explicitly treats absence as a distinct expected result;
- `configuration_error`: required safe provider configuration is unavailable before a remote call;
- `rejected`: the operation's typed expected credential/payment rejection described in the matrix; not an outage or provider failure;
- `failed`: another provider error is translated or propagated without a more specific safe classification.

Do not classify throttling by matching exception text. Do not change exception types, public error mappings, retry ownership, idempotency, or reconciliation behavior.

For each Stripe operation, move client/configuration acquisition inside its existing shared read/mutation call scope using the existing callable boundary; do not call the SDK twice. Its scope includes configuration, one SDK call, and existing result extraction, so malformed required provider results are not reported as successful. Classify missing SDK/credentials/disabled integration and the current refund-currency configuration guards as `configuration_error` before remote invocation. A `StripeConfigError` raised by response extraction after invocation is `failed`, not missing configuration. Typed Stripe `RateLimitError` or explicit SDK HTTP 429 is `rate_limited`; typed CardError is `rejected` only for the two PaymentIntent operations above. Other SDK errors remain `failed` rather than guessing a resource's domain meaning. Keep the existing timeout translation confined to the SDK-call phase; adding the metric scope must not newly translate configuration/extraction exceptions into dependency timeouts. Catch, observe once, and preserve the original translated exception and result shape.

Firebase initialization belongs to the named operation scope, not outside it. A failed initialization records only the operation that was about to run; token verification initialization failure does not also invent a failed lookup. Token verification and the following user lookup are separate scopes: successful verify records once even if lookup subsequently fails. Classify original typed exceptions before the existing public translation, so ResourceExhaustedError remains `rate_limited` even when translated to unavailable. Existing timeout-like read exceptions are `timed_out`; App Check's explicitly caught provider-unavailable classes continue their existing translation, with ResourceExhaustedError as `rate_limited` and the remaining unavailable classes as `failed` unless the existing timeout contract establishes a timeout. Certificate-fetch/JWK failures are `failed`, not invalid-token rejection. Initialization/credentials/project failures are `configuration_error`; token parsing/verification ValueError is `rejected`. Never change disabled-user, unavailable, token rejection, or user-not-found product behavior to fit the metric.

The existing `auth.verify_id_token(check_revoked=True)` performs an SDK-internal user lookup. If that check raises typed `UserNotFoundError` for a deleted account, record one `firebase.token.verify/rejected` observation and preserve the existing authentication denial. The later explicit `auth.get_user` has not run and receives no observation; SDK-internal calls are not separately instrumented. Absence from the explicit user lookup remains `firebase.user.lookup/not_found`.

R2 lower-operation scopes include configuration/client construction, one presign/HEAD call, and existing result conversion. Classify before wrapping Botocore errors into `R2StorageError`. Explicit ClientError HTTP 429 or fixed error codes `SlowDown`, `Throttling`, `ThrottlingException`, and `TooManyRequestsException` yield `rate_limited`; fixed HEAD absence codes `404`, `NoSuchKey`, and `NotFound` yield `not_found`. ConnectTimeoutError/ReadTimeoutError yield `timed_out`; other provider/SDK failures yield `failed`. No endpoint, bucket, object key, response mapping, or exception message is copied into dimensions. Preserve original exception wrapping and absence behavior.

All scopes choose exactly one result. Configuration errors precede invocation; explicit typed throttling, expected rejection/absence, and existing timeout classification precede generic failure. Do not use a second outer metric catch to observe the same exception again. Sink rejection/failure never becomes another provider failure observation.

R2 upload-URL and read-URL generation are included as storage operations even when the SDK operation is local, because configuration/SDK failures are current storage failures. R2 metadata `not_found` remains a non-failure result and metadata timeout remains `timed_out`.

### 3.8 Moderation scan latency

Move performance timing out of `ScanProvenance`. Scanner provenance should describe what was scanned and under which reproducible scanner contract, not how long one execution happened to take.

For saved-content moderation:

- retain the existing monotonic timing around `build_content_moderation_findings`;
- after the scan result is determined, observe elapsed seconds once under the fixed operation derived from its current target context;
- metric-recording failure does not invalidate the scan result.

For game-chat and Need-a-Sub chat moderation:

- preserve the existing workflow start timestamp taken before repeated-message context evaluation;
- pass that start point through the scan call as today so the measured interval retains the current meaning;
- observe one duration at completed detection using the fixed chat target context;
- do not persist the elapsed value in the detection records.

The operation vocabulary is derived from the existing finite moderation target-context contract and represented as `moderation.scan.<target_context>`. An unknown or invalid target context is rejected rather than becoming a new cardinality dimension.

### 3.9 Retiring duration persistence without changing moderation identity

Because Pickup Lane still uses editable pre-production canonical migration history, remove the obsolete duration columns and their duration-specific nonnegative checks from the canonical migrations that own:

- saved-content moderation findings;
- game-chat message detections;
- Need-a-Sub chat message detections.

Do not add a later patch migration solely to drop these pre-production columns.

Keep SQLAlchemy models aligned with those canonical migration definitions. Remove duration from record-construction helpers and persistence calls.

Remove duration from:

- `ScanProvenance`;
- scan-result validators that currently require it;
- chat-detection provenance equality/aggregation;
- reconstructed chat scan provenance;
- review-signal metadata key `scan_execution_duration_us`.

The clean schema after base-to-head migration must not contain the three duration columns or their duration-specific check constraints.

No data-conversion migration is required for preserved production history because the project is still operating under its clean-rebuild pre-production migration policy. The migration change does not authorize destructive work against a development or real-data database.

Update the active `docs/production-readiness/governance/moderation-taxonomy-register.md` contract with the same correction: persisted reproducibility provenance excludes execution duration, and scan duration is operational telemetry only. Scanner version `3`, taxonomy version `1`, evidence format `1`, canonicalization version, rule versions, and profile configuration hashes remain unchanged. Duration is performance provenance outside the behavior-bearing profile serialization and matched-evidence interpretation; removing it changes neither scanner evaluation nor evidence discriminator/content/validation semantics. Removing the duration-only scan-result validation is not a change to matched-evidence format. Keep historical accepted plans as historical records rather than rewriting their descriptions of former storage behavior.

### 3.10 Compatibility and privacy boundaries

Metric instrumentation is observational. Existing API payloads, response codes, request correlation, health responses, logging records, durable-job transitions, worker status output, payment/reconciliation decisions, provider error translation, moderation evidence, and administrative review behavior remain unchanged except for removal of the obsolete persisted duration fields from internal moderation storage.

Metric recording occurs after the application knows the safe classification it intends to record. It must never capture arbitrary ORM objects, request objects, response objects, provider responses, exception objects, payloads, metadata dictionaries, SQL, or durable result metadata.

All runtime series are bounded by the fixed metric inventory plus existing finite route templates, job types, issue types, provider kinds, provider operations, moderation target contexts, and result vocabularies.

## 4. Failures And Edge Cases

This section defines abnormal situations where observability code could otherwise corrupt product behavior, leak sensitive data, double-count operations, or misrepresent durable state.

1. **Unsupported or unsafe metric dimension**
   - **Condition:** A caller supplies an undeclared label key, identifier, unsafe string, raw path, URL, contact value, provider object ID, or another value rejected by the existing telemetry rules.
   - **Required behavior:** Reject that observation without emitting the unsafe value and without raising into the owning request, job, provider call, or moderation flow.

2. **Invalid numeric observation**
   - **Condition:** A caller supplies NaN, infinity, a negative duration, an invalid counter delta, or another value incompatible with the metric kind.
   - **Required behavior:** Do not mutate metric state. Product behavior continues unchanged.

3. **Invalid static metric definition**
   - **Condition:** A duplicate/conflicting descriptor or invalid fixed metric definition is discovered while the API or worker metrics recorder is initialized.
   - **Required behavior:** Fail that process initialization before normal serving or job claiming instead of silently exposing an ambiguous metric contract.

4. **HTTP exception before response start**
   - **Condition:** A request leaves the normal middleware path through an unexpected exception before `http.response.start`.
   - **Required behavior:** The existing outer error handling produces the public 500 behavior, and the shared metric completion owner records exactly one server-error request and duration, then restores the in-flight gauge.

5. **HTTP exception after response start**
   - **Condition:** Downstream code raises after the response status has already been observed.
   - **Required behavior:** Use the captured status for the single request metric, do not invent a second 500 response, and restore the in-flight gauge exactly once.

6. **Unmatched or malformed request target**
   - **Condition:** No validated framework route template is available.
   - **Required behavior:** Use the fixed `/{unmatched}` route dimension and never inspect or emit the raw target.

7. **Pool implementation cannot report pressure**
   - **Condition:** A test or alternate SQLAlchemy pool does not expose the checked-out state required by the observable gauge.
   - **Required behavior:** Omit the unavailable gauge observation. Do not substitute zero, create a connection, or fail product work.

8. **Database-backed observable query fails**
   - **Condition:** Backlog or money-issue gauge collection cannot query the database.
   - **Required behavior:** Replace that complete family with an empty unavailable batch, remove its previous series, and return the other valid families/event aggregates. Close its independent read session, never alter jobs/issues or retry business work, and never embed the exception in metric data. Its safely classified database timeout is still counted once by the shared hooks.

9. **Durable transition loses its lease or fails to commit**
   - **Condition:** A runner attempt does not own the final durable transition or the transition does not commit.
   - **Required behavior:** Record only the post-commit bounded outcome that the existing runner establishes. Never record a successful/retry/exhausted state before it becomes authoritative.

10. **Provider mutation times out**
    - **Condition:** An existing provider mutation boundary raises the application's unknown-outcome timeout contract.
    - **Required behavior:** Record `unknown_outcome`; preserve the existing reconciliation/idempotency behavior and do not treat the operation as an ordinary known failure or retry it from the metrics layer.

11. **Provider throttling cannot be established safely**
    - **Condition:** A provider failure has no typed throttling/resource-exhaustion classification or explicit provider status/code.
    - **Required behavior:** Record the applicable generic failure classification rather than inferring `rate_limited` from exception text.

12. **R2 object is absent**
    - **Condition:** The current metadata lookup establishes object-not-found.
    - **Required behavior:** Record `not_found`, preserve the existing object-not-found product behavior, and do not count it as a storage/provider failure.

13. **Metrics recording fails during moderation**
    - **Condition:** The recorder rejects or fails an observation after a moderation scan completes.
    - **Required behavior:** Preserve the moderation result and its reproducible provenance. Never restore duration persistence as a fallback.

14. **Legacy local database still has duration columns**
    - **Condition:** A local pre-production database was built from the previous canonical migration definitions.
    - **Required behavior:** Treat the database as stale under the existing clean-rebuild policy. Do not add compatibility writes or a patch migration merely to support that historical local shape.

15. **Concurrent observations hit the same series**
    - **Condition:** Multiple API requests or worker operations update the same counter, gauge, or distribution concurrently.
    - **Required behavior:** Updates are atomic with respect to the in-process metric state; no count is lost, distributions remain internally consistent, and in-flight gauges cannot become negative through a valid lifecycle.

16. **An observable population becomes empty**
    - **Condition:** Jobs complete, exhausted work is requeued/cancelled, issues resolve, or no ready job remains after a previous nonempty collection.
    - **Required behavior:** The next successful family replacement contains the fixed zero count series and removes unavailable age series. No prior age/count survives as current state.

17. **Optional sink fails during API entry or completion**
    - **Condition:** Sink delivery raises before or after another observation has been delivered.
    - **Required behavior:** Canonical entry acceptance, count/distribution aggregates, and observable replacement remain independent of sink success. Release each accepted entry once; never apply an unmatched decrement or retry delivery. The public response and existing logging remain unchanged.

18. **A payment-method reconciliation establishes failure**
    - **Condition:** The consumer returns `failed` and the compatible durable handler completes the job successfully.
    - **Required behavior:** After the owning final commit, observe job `succeeded` and reconciliation `failed` as distinct facts. Discard staged reconciliation data on lease loss/rollback/failed commit; do not change the accepted handler result or create a MoneyIssue to manufacture coverage.

19. **A database exception is handled before reaching HTTP error translation**
    - **Condition:** Readiness returns false, a service handles an execution timeout, or a worker converts it into retry/exhaustion.
    - **Required behavior:** Shared pool/engine hooks observe the timeout once before translation. Exception propagation, rollback, job transitions, and public health/error behavior remain unchanged; a duplicate exception hook/rethrow does not count it again.

20. **An expected credential/payment rejection occurs**
    - **Condition:** The operation's matrix establishes invalid credentials, a disabled user, a deleted user during token verification's SDK revoked-user check, or typed PaymentIntent CardError.
    - **Required behavior:** Observe `rejected`, never `failed`/`rate_limited`, and preserve the current product rejection. Deleted-user token verification does not invent a subsequent explicit lookup observation. Explicit Firebase user lookup absence is `not_found`; deleting an already absent Firebase user is `succeeded`.

## 5. Testing

Testing must prove that the metric surface is bounded and non-disruptive, that each critical source emits the intended operational signal, and that moderation duration has been removed from every durable representation without changing moderation behavior. Provider-independent tests must not depend on public network access or production credentials.

### 5.1 Metrics contract and privacy tests

Verify the complete fixed descriptor inventory, metric kinds, units, numeric domains, exact cross-dimension vocabularies, and process identity. Pure recorder/privacy tests belong with current platform observability coverage; PostgreSQL domain aggregates and consumer integration use their existing domain/workflow layers. Schema proof uses migration-safe infrastructure. No real-provider network verification is required for these observational changes.

Prove:

- valid counters, gauges, and distributions produce deterministic snapshots;
- concurrent updates do not lose observations;
- event sequences follow canonical mutation order, concurrent sink calls are safe, and a barrier-controlled test delivering two in-flight exits as `0` then `1` leaves both canonical and sink gauges at zero;
- reordered counter/distribution delivery retains every increment/sample, and a fresh recorder binding does not inherit gauge sequence state from a prior recorder lifetime;
- the sink interface receives each validated distribution observation while the in-memory sink aggregates count/sum/min/max without retaining an unbounded sample list;
- canonical event state updates independently of injected sink failure, with no retries or recursive sink calls;
- observable batches atomically replace prior populations, present-to-absent ages disappear, and all declared count combinations explicitly transition to zero;
- invalid/duplicate-series/callback-failed families become unavailable without stale series, while other families/event counters survive;
- concurrent collections are serialized, callbacks/sinks execute without the canonical-state lock, and distributions still deliver individual observations;
- API alone registers global backlog/MoneyIssue callbacks; worker and API expose their own local pool values without duplicate registrations or automatic polling;
- repeated API/worker recorder initialization does not leak or duplicate prior metric state;
- unsupported metric names or dimensions are rejected;
- correlation/request/user/payment/booking/provider IDs, object keys, URLs, raw routes, contact values, exception text, free text, secrets, and arbitrary mappings cannot enter metric dimensions;
- invalid/non-finite numeric values, negative gauges/durations, fractional count values, and booleans do not mutate metric state;
- a runtime recording failure does not raise into its caller.

### 5.2 API lifecycle tests

Exercise the current request-lifecycle owner with:

- successful responses;
- redirects;
- handled client errors;
- handled server errors;
- database/dependency timeout responses;
- unexpected exceptions before response start;
- exceptions after response start;
- matched parameterized routes;
- unmatched routes;
- supported and unsupported HTTP methods;
- concurrent requests.

Inject sink failures independently at entry, request-count delivery, duration delivery, and exit, including concurrent/error paths. Assert the canonical in-flight gauge balances and duplicate completion/release is harmless. Recorder entry rejection must never cause a later decrement. Exercise the real outer-error/middleware integration so completion after middleware unwinding is not hidden by a mocked helper.

For every completed path, assert exactly one request counter and one duration observation and verify that the in-flight gauge returns to its previous value. Confirm status-class mapping, route-template use, fixed method-operation mapping, and absence of raw path/query/correlation data.

Existing correlation headers, public error bodies, response status, and structured request logging must remain unchanged.

### 5.3 Database metrics tests

Use controlled SQLAlchemy/PostgreSQL test behavior to prove:

- checked-out pool gauge changes when a connection is checked out and restored after check-in;
- configured pool-capacity gauge equals the validated per-process pool configuration and does not imply provider capacity;
- pool-wait, statement, and lock timeout paths increment only their corresponding timeout classification;
- SQL text, parameters, connection URLs, and connection identities never enter observations;
- an unsupported pool implementation results in an omitted gauge rather than a fabricated value.

Exercise shared instrumented QueuePool acquisition and engine execution hooks, not merely calls to a recording helper. Cover each of the three timeout classes through API/session and worker paths, direct readiness, caught service exceptions, commit/flush, collector SELECT failure, and explicit lease-renewer thread context. Establish SQLAlchemy pool-wait exhaustion with a controlled small test pool; establish statement/lock timeouts against PostgreSQL with deterministic coordination. Include the direct checkout timeout-setting path and a driver exception wrapped/rethrown by the engine to prove one observation for the same origin. Distinct repeated statement exceptions count separately. Exercise a handled database timeout followed by independent recovery-query timeout through the hooks: the new driver origin counts even when its implicit context contains the observed first error. Also prove a recovery-query non-timeout error does not inherit the earlier timeout classification, while repeated hooks/wrappers for the original failure still count once. Non-timeout failures, uninstrumented maintenance engines, and unsupported runtime contexts do not create metrics. Assert unchanged pool settings, listener count, transaction rollback/invalidation, health/public responses, and retry behavior.

### 5.4 Durable worker and backlog tests

Use the existing PostgreSQL-backed durable-job test layer to verify:

- successful, retry-waiting, exhausted, lease-lost, missing, and unsupported paths record the same bounded result established by the authoritative post-commit event path;
- final transient exhaustion is observed as `exhausted` even where the runner keeps an existing compatibility return value;
- idle/shutdown do not create job-outcome observations;
- Stripe webhook/payment/payment-method reconciliation jobs are distinguishable through `job_type` without payment/provider identifiers;
- all six authoritative durable statuses have the exact inclusion/exclusion in Section 3.5, and all 16 declared count series are present even when zero;
- oldest claimable age is correct per job type and absent when no claimable job exists;
- future availability, remaining-attempt limits, supported-pair membership, expired leases, and unsupported type/version combinations have the specified count/age meanings;
- exhausted rows created before recorder startup remain visible and resolve correctly after requeue/cancellation;
- arbitrary stored job-type values never become metric dimensions or Python-materialized unbounded grouping state;
- backlog collection does not deserialize or expose job payload/protected identity/result metadata.

Assert the state matrix's included/excluded union equals current authoritative statuses and is disjoint. Verify the three production type/version pairs against the production registry. Collection opens/closes an independent read session and never commits or modifies jobs/history; inspect query projection so safe output is not achieved by first loading prohibited rows.

### 5.5 Reconciliation and financial discrepancy tests

Against PostgreSQL-backed money-issue rows, verify that the observable gauge:

- counts only `open` issues;
- groups by every authoritative current issue type;
- updates correctly after issue creation, reopen, and resolution;
- emits only the fixed operation token and `open` result;
- never includes amount, currency, IDs, summaries, external references, or operation keys.

The tests must show that metric collection does not modify money-issue state or append money-issue events.

Reconcile the seven issue types with both source taxonomy and the model constraint; assert explicit zero series after resolving the last issue of a type and a failed query removes that whole observable family rather than retaining its prior nonzero values.

For domain reconciliation outcomes, cover every scalar result in Section 3.6 for both reconciliation consumers and verify webhook results do not create this metric. In particular, run payment-method `failed` through the real consumer/runner integration and assert committed job `succeeded` plus reconciliation `failed`. Cover pending and repeated attempts, already-terminal/missing operation, failed final commit, rollback, lease loss, and handler exception before a domain result. Assert staged telemetry never enters durable result metadata, job/event rows, or payment-method state. Existing payment state, idempotency, provider-unknown recovery, and retry schedules remain unchanged.

### 5.6 Provider and storage boundary tests

At application-owned provider boundaries, use deterministic SDK fakes/mocks to exercise every matrix row and every applicable outcome in Section 3.7. Fake the SDK/client boundary, not the whole application owner. Reconcile the explicit operation inventory with all current Stripe read/mutation call sites, both Firebase lookup sites plus verify/App Check/delete, all three R2 SDK operations, and both preflight-only R2 configuration paths. This is a finite source-boundary coverage check, not a production retry registry. Prove:

- success records `succeeded`;
- read timeout records `timed_out`;
- mutation timeout records `unknown_outcome`;
- explicit typed/status throttling records `rate_limited`;
- an ordinary provider failure records `failed`;
- configuration failure records `configuration_error` where that operation requires configuration;
- R2 object absence records `not_found`;
- expected Firebase credential rejection/disabled user and typed PaymentIntent CardError record `rejected`, not operational failure;
- absent Firebase lookup records `not_found`, while idempotent absent-user deletion records `succeeded`;
- typed UserNotFoundError raised by token verification's SDK revoked-user check records exactly one `firebase.token.verify/rejected`; assert the later explicit lookup is not called or observed and the existing authentication denial is unchanged;
- token verification followed by failed lookup records exactly one observation for each operation actually attempted; failed initialization does not invent downstream operations;
- configuration/client acquisition is inside the observed scope, response-extraction failure is not `succeeded`, and higher-level logging/preflights do not duplicate lower observations;
- typed ResourceExhausted/RateLimit/ClientError codes are classified before wrapping, without changing current unavailable/unknown-outcome exception translation;
- successful local presigning is not proof of successful upload/object availability; inbound webhook validation and application repair registry entries are excluded;
- current Stripe, Firebase, and R2 operations use only the fixed provider and operation vocabularies.

Assert that provider metrics do not expose request payloads, provider responses, IDs, credentials, bucket/object details, exception messages, or tracebacks, and that metric failures do not change provider exception/retry/reconciliation behavior.

### 5.7 Scanner latency and provenance tests

Cover saved-content, game-chat, and Need-a-Sub chat scanning.

Verify:

- one `moderation.scan.duration_seconds` observation occurs for each completed scan;
- elapsed time is derived from a controlled monotonic clock and converted correctly to seconds;
- chat timing preserves the existing start point before repeated-message context evaluation;
- the operation dimension uses only the fixed target-context vocabulary;
- metric recording failure leaves the moderation result unchanged;
- `ScanProvenance` no longer carries execution duration;
- all remaining scanner/taxonomy/configuration/canonicalization/evidence provenance remains unchanged;
- finding/detection identity and evidence fingerprints do not depend on duration.

Verify the active moderation taxonomy register describes duration as operational telemetry and its persisted provenance list matches the resulting contract. Keep scanner/taxonomy/evidence/canonicalization/rule versions and profile configuration hashes unchanged; compare remaining reproducibility/evidence behavior to controlled prior fixtures rather than rewriting expectations to whatever the new implementation returns.

### 5.8 Schema and persistence tests

Use the migration-safe PostgreSQL test environment to prove the canonical clean schema.

Verify:

- base-to-head migrations create the saved-content finding and both chat-detection tables without `execution_duration_us`;
- the three duration-specific nonnegative check constraints are absent;
- SQLAlchemy model metadata matches the canonical migration definitions;
- persistence helpers no longer attempt to write duration;
- chat aggregation/reconstruction does not require duration;
- administrative review-signal metadata does not contain `scan_execution_duration_us`;
- no other durable moderation JSON/metadata path receives a replacement execution-duration value.

Keep all unrelated moderation columns, constraints, indexes, identities, and provenance behavior intact.

### 5.9 Affected regression coverage

Run focused regressions for request/error handling, database timeout behavior, durable workers/payment reconciliation, provider/storage boundaries, saved-content moderation, both chat moderation families, moderation surfacing/review signals, and existing structured logging/correlation behavior.

Because the metrics recorder touches shared API/worker observability and database/runtime instrumentation, run the broader backend regression suite after focused coverage. Static Python checks should also confirm the modified code remains importable, lint-clean, and consistently formatted.

## 6. Done When

This checklist is the engineering completion bar for the work.

- [ ] A single provider-independent runtime metrics contract exists for API and worker processes without a monitoring-vendor dependency or network transport.
- [ ] The fixed critical metric inventory covers API request/error/latency/in-flight pressure, database pool pressure/timeouts, worker backlog/retry/exhaustion, current payment/reconciliation execution, unresolved financial discrepancies, provider/storage outcomes, and moderation scan latency.
- [ ] Every metric dimension is bounded by the existing telemetry safety rules and no sensitive or high-cardinality identifier can become a metric label.
- [ ] API requests produce exactly one count and latency observation on every completion/error path and the in-flight gauge is balanced.
- [ ] Database pool and timeout metrics reflect only application-controlled state and do not invent provider capacity.
- [ ] Durable-job outcome and backlog metrics agree with authoritative committed job state, and open financial-discrepancy gauges agree with authoritative `MoneyIssue` state.
- [ ] Current reconciliation results are distinguished from job execution, including committed payment-method failure under successful job completion; no staged telemetry is persisted or emitted for failed final transitions.
- [ ] Observable batches have exact zero/removal/unavailable semantics, fixed process ownership, and independent read-session lifecycle; current exhausted work survives process restart and unsupported work cannot introduce arbitrary labels.
- [ ] Provider and R2 outcomes preserve current timeout, unknown-outcome, throttling, not-found, retry, and exception behavior while exposing only fixed safe classifications.
- [ ] Moderation scan latency is emitted as operational telemetry for saved-content and both chat families using the existing timing boundaries.
- [ ] `execution_duration_us` and `scan_execution_duration_us` are absent from scan provenance, moderation models, canonical migrations, persistence helpers, chat aggregation, and review-signal metadata, with no replacement durable duration field.
- [ ] All reproducibility-relevant moderation provenance, evidence, identities, and product decisions remain intact.
- [ ] The active moderation taxonomy contract matches the duration-free persisted provenance without unnecessary version/configuration changes.
- [ ] Invalid static definitions fail initialization before serving/claiming; runtime recording and collection failures preserve product behavior and cannot corrupt in-flight accounting or present stale gauges as current.
- [ ] Focused PostgreSQL/integration tests and the broader affected backend regression suite pass for the resulting design.
