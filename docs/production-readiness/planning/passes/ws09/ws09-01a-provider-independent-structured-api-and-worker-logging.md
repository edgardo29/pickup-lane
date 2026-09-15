# WS09-01A - Provider-Independent Structured API and Worker Logging

WS09-01A establishes one safe, bounded, provider-independent structured logging contract for Pickup Lane's production API/runtime and durable worker surfaces while preserving existing request, job, payment, storage, administrative, and durable-history behavior.

This document is the engineering blueprint for this pass.

## 1. What This Work Does

This pass normalizes the production API/runtime and durable-worker logging surfaces that currently emit a mixture of JSON message strings, logging `extra` dictionaries, plain diagnostic messages, raw Uvicorn access/runtime output, moderation messages containing identifiers, and worker `print()` output. The finished system emits bounded JSON operational records through one application-owned path and keeps request/job correlation intact across API and worker execution.

The in-scope runtime population is finite: request correlation/completion and application error handling; App Check; chat rate limiting; the current moderation reconciliation/surfacing logging sites; venue-image/R2 operational failures; Uvicorn access/runtime logging; durable-job processing; the durable-worker command; and its explicit status/job-inspection output. One-off administrative, bootstrap, seed, migration, development, and maintenance scripts such as `bootstrap_admin.py` and `seed_demo_browse.py` are outside this runtime contract unless they execute through one of those listed production surfaces.

The implementation extends the accepted EN-02 `EventEnvelope` rather than introducing a parallel observability model. Durable job rows/events, payment records, administrative audit records, and domain state remain authoritative. Logs are bounded operational summaries, not another history or audit database.

Centralized provider ingestion, retained search, provider access/retention configuration, and deployed delivery proof are outside this source-level work. Scanner-latency persistence cleanup and its replacement signal are also outside this pass.

## 2. What Must Be True

These requirements define the source behavior that must exist when this pass is complete. They are intentionally limited to the production API/runtime and durable-worker surfaces listed above so implementation has a closed population rather than a repository-wide logging mandate.

### 2.1 One Bounded Structured Event Contract

- Each in-scope operational event is emitted as one parseable JSON object rather than a plain message, pre-serialized application message, arbitrary `extra` dictionary, traceback, or dumped `LogRecord`.
- Every application event contains `schema_version`, `event_name`, `occurred_at`, `severity`, `source_identity`, `environment`, and `release`.
- Optional correlation, HTTP, job, provider, resource, result, and label fields use the exact typed and bounded contract in Section 3.1.
- The general emitter accepts a controlled field mapping and validates every key and value inside its non-throwing boundary. `correlation_id`, `request_id`, and `resource_id` are context/owner-controlled rather than caller-supplied fields. Unsupported keys never escape as Python call-signature errors and never appear in output.
- The structured contract contains no final logging-provider transport, index, account, project, region, retention, or access value.

### 2.2 Request Correlation Preserves Existing Behavior

- A valid externally supplied `X-Request-ID` remains accepted only when it is canonical lowercase UUIDv4.
- A missing, empty, or invalid external value is discarded and replaced with a generated canonical UUIDv4. The request continues normally, and the invalid value is neither reflected nor logged.
- The selected safe correlation ID is used by the existing response-header and public-error contracts and by structured events emitted during that request.
- Request/task correlation and emitter context are reset on every normal and exceptional path and cannot leak between concurrent requests or tasks.

### 2.3 Request Completion Preserves Timeout And Error Semantics

- Every completed HTTP request produces exactly one `http.request` event using the final observable HTTP status and the selected safe correlation ID.
- Recognized dependency/database timeouts keep the existing timeout classification and safe public timeout response, including the existing timeout status/code contract; they do not become `application.unexpected_error` events.
- Only non-timeout unhandled exceptions emit `application.unexpected_error` and use the existing safe 500 contract.
- Handled responses, recognized timeout responses, ordinary unhandled 500 responses, and failures after response start cannot create duplicate completion records.
- Raw paths, query strings, bodies, headers, cookies, client addresses, user agents, and request/response objects are never event fields.

### 2.4 Durable Job Correlation Is Forward-Compatible

- An enqueue call that explicitly supplies a correlation value keeps the accepted broader durable-job validation behavior.
- Otherwise, work enqueued in an active request stores that request's canonical correlation ID.
- Otherwise, newly enqueued background work receives a generated canonical UUIDv4 correlation ID.
- Historical broader values such as `job-...` remain processable without migration or rewrite.
- A worker activates canonical job correlation for the complete handler/transition/logging scope. A legacy non-UUID job executes with an explicitly empty correlation context and does not inherit stale context from earlier work.
- Existing `DurableJobRunner.process_once() -> str` outcomes and durable claim/lease/retry/exhaustion semantics remain compatible.

### 2.5 The Existing Runtime Event Population Is Fully Allocated

- App Check preserves its existing `valid`, `missing`, `invalid`, and `provider_unavailable` outcomes and existing App Check stable codes.
- Chat rate limiting covers `allowed`, `rejected`, and database `store_error` branches.
- The current moderation reconciliation/surfacing error call sites are replaced individually with fixed structured mappings rather than collapsed into an ambiguous generic event.
- Venue-image/R2 configuration and provider failures are logged at the request-facing service points that know the operation being attempted, including best-effort game-card image reads; the low-level storage adapter does not produce duplicate events.
- Every durable-runner result that can represent processed work has a fixed committed-state result/severity/error-code rule, including final-attempt exhaustion, expired-lease exhaustion, and translation from current lowercase durable error codes to EN-02-compatible uppercase event codes.
- The worker's unexpected command/runtime failure has one fixed event contract.

### 2.6 Worker Output Preserves Operator Compatibility Without Raw Tracebacks

- Normal durable-job loop output comes from structured runner events; routine idle polling emits no informational event.
- After worker logging initialization succeeds, an unexpected top-level worker failure emits exactly one fixed safe event and exits with code `1` without re-raising into Python's default traceback printer.
- `--status` and optional `--job-id` remain on-demand operator interfaces and emit the exact deterministic JSON schemas in Section 3.8.
- Operator output preserves the accepted backlog, heartbeat, attempt, unsupported-version, and bounded recent-event information while excluding payloads, protected identity, correlation values, lease tokens, raw result metadata, provider payloads, and complete history.

### 2.7 Identifier And Sensitive-Data Safety Is Structural

- The general application emitter does not accept `resource_id` at all.
- The general application emitter also does not accept `correlation_id` or `request_id`; runtime correlation comes only from the active request/job context or the private validated outer-error path.
- Only the durable-runner-owned emission wrapper may construct the pair `resource_kind="durable_job"` plus the job's internal UUID as `resource_id`.
- No logging path performs database lookups to infer what an arbitrary UUID identifies.
- User, administrator, actor, booking, participant, payment, payment-event, refund, chat/message, provider, idempotency, and storage-object identifiers do not enter the structured resource-ID field.
- Raw SQL values, provider payloads, credentials, tokens, secrets, payment/card data, personal data, object keys/URLs, free-form text, raw exceptions, tracebacks, and arbitrary metadata never enter the structured event contract.

### 2.8 Logging Failure Isolation Has A Defined Bootstrap Boundary

- The application-owned structured logging guarantee begins only after the repository's safe logging bootstrap has successfully installed its handlers. Failures in the Python interpreter, module loader, or code required to establish that bootstrap are outside this application's structured-log guarantee and must not be described as protected by it.
- For the normal Uvicorn API entrypoint, the earliest application bootstrap runs before importing database/routes that can fail during application import.
- For the worker entrypoint, database-dependent and job-service imports occur only after the worker logging bootstrap succeeds.
- Once structured logging is active, event validation, serialization, formatting, handler, and output-stream failures do not change API responses, database transactions, provider operations, authorization/audit decisions, durable-job transitions, payment/storage state, or worker exit decisions.
- Application-owned handlers suppress Python logging's default `handleError()` traceback/message/argument diagnostics.

## 3. Design

The design keeps `EventEnvelope` as the bounded data contract, adds a controlled non-throwing emitter around it, and installs application-owned handlers that write only validated JSON. Request middleware and the durable runner own correlation lifecycle. The design also defines an early bootstrap boundary so raw Uvicorn/Python logging behavior is not confused with the guarantees that apply after application logging is active.

### 3.1 Exact Event Record Shape

Keep `EVENT_SCHEMA_VERSION="1"`. New fields are additive and omitted when unused so existing EN-02 envelopes retain their existing serialized shape when the new fields are absent.

Every runtime application event contains:

| Field | Contract |
|---|---|
| `schema_version` | Exact existing value `1`. |
| `event_name` | Existing bounded lowercase event token, maximum 80 characters. |
| `occurred_at` | Timezone-aware timestamp serialized in canonical UTC form. |
| `severity` | `debug`, `info`, `warning`, `error`, or `critical`. |
| `source_identity` | Exact process category `api` or `worker`. |
| `environment` | Current validated `BackendSettings.app_env.value`. |
| `release` | Current validated `BackendSettings.release_identity`. |

Add these optional fields to `EventEnvelope` alongside its existing correlation, request, actor, operation, resource, result, provider, error-code, and labels fields:

| Field | Contract |
|---|---|
| `severity` | Optional for direct compatibility construction but required by the runtime emitter; one of the five fixed severity values. |
| `resource_id` | Canonical lowercase UUID text. Envelope validation requires `resource_kind="durable_job"` whenever present, but production provenance is enforced by the runner-only wrapper described below. |
| `http_method` | `delete`, `get`, `head`, `options`, `patch`, `post`, `put`, or fixed `other`. |
| `http_status_code` | Integer 100 through 599. |
| `attempt_count` | Integer 0 through 2,147,483,647. |
| `maximum_attempts` | Integer 1 through 2,147,483,647; if both attempt fields exist, `attempt_count <= maximum_attempts`. |

Harden `release` and `source_identity` with a 120-character ceiling while retaining trimming, control-character, and sensitive-text checks. Current settings continue to apply their narrower release validation before events are constructed. Labels retain the existing EN-02 allowlist and low-cardinality rules. High-cardinality IDs never move into labels.

### 3.2 Non-Throwing Emitter And JSON Transport

The general application emitter has a narrow shape equivalent to:

```text
emit_event(event_name, severity, fields: Mapping[str, object]) -> bool
```

`fields` is accepted as one mapping so unknown keys are discovered inside the function's `try` boundary rather than by Python argument binding. The emitter allowlist contains only the documented caller-supplied `EventEnvelope` runtime fields and explicitly excludes `correlation_id`, `request_id`, and `resource_id`. The emitter reads canonical correlation only from the active context, validates the event name, severity, every mapping key/value, constructs the envelope, serializes deterministic JSON, and submits it to the dedicated event logger inside one non-throwing boundary.

A separate private runner helper equivalent to `emit_durable_job_event(job_id, ...)` is the only production interface that can populate `resource_id`. It receives the job UUID from the claimed `DurableJob`, hardcodes `resource_kind="durable_job"`, reads correlation from the runner-owned active context, and delegates the remaining validated facts to the same serializer. No other production caller is given a resource-ID or correlation parameter.

The outer request-error handler is the only path that must emit after ordinary request middleware has unwound. It uses a private helper that accepts only the already-validated correlation value stored in ASGI request state, activates that value in a temporary correlation context for the diagnostic and completion emissions, and resets the context in `finally`. The helper does not accept arbitrary `request_id` or other caller-controlled identifiers.

Validation rejection has one deterministic fallback rule: the emitter always attempts exactly one fixed `logging.event_rejected` record using only static event identity, `warning` severity, current safe process identity/environment/release, timestamp, and active canonical correlation when available. The fallback contains **no rejected event name, rejected key name, rejected value, exception type/text, or validation message**. If fallback construction/submission fails, it is dropped without another attempt.

Serialization, handler, or stream-write failure does **not** attempt the rejection fallback because that could recurse through the same failed transport. Those failures are swallowed after initialization and return `False` to the caller.

Application operational records are transported through a dedicated non-propagating logger with exactly one tagged custom handler. The emitter passes one already-validated JSON string as `LogRecord.msg`, with empty `args`, no `exc_info`, and no arbitrary `extra`. The handler does not invoke a generic formatter; under its internal lock it writes exactly `validated_json + "\n"` to `sys.stdout` and flushes. Its `emit()` catches write failures, and its `handleError()` is a no-op, so the standard logging traceback/message/argument diagnostic path cannot expose the record on `stderr`.

### 3.3 Logging Bootstrap And Initialization Boundary

API startup uses two phases so application-controlled logging starts before database and route imports can fail:

1. `backend.main` initially imports only the standard library plus the import-safe settings/logging bootstrap modules.
2. An import-safe preparation step disables `uvicorn.access` and replaces Uvicorn runtime handlers with application-owned handlers that never reproduce the original record message, arguments, or traceback.
3. Settings are resolved and the API logging configuration is activated with validated source/environment/release metadata.
4. Only then are database, routes, and other database-dependent application modules imported and the normal app assembled.
5. `create_app(settings)` builds the request emitter from the exact supplied settings object and configures/reuses the tagged handler idempotently; repeated app construction does not stack handlers or share mutable per-app metadata.

The implementation may move current top-level imports to satisfy this ordering. It must not import database-dependent modules merely to configure logging.

Worker startup follows the same principle. The worker module's top-level imports remain limited to standard-library code plus import-safe settings/logging bootstrap code. `main()` establishes worker logging, resolves settings, and only then imports/initializes `SessionLocal`, database checks, the durable runner, and the production job registry.

There is a deliberate limit to this guarantee: a failure before the bootstrap code itself can execute—for example interpreter startup, loading the bootstrap module, or a direct raw Python import failure that occurs before that code—may still be rendered by the host interpreter/runtime. The application must not claim that such pre-bootstrap output is structured or redacted. For the normal API/worker entrypoints, database and business-module imports are deliberately moved behind the safe bootstrap so they fall inside the controlled runtime boundary.

If safe logging activation cannot be established, startup stops before the API serves requests or the worker claims jobs. Application code raises only a fixed safe bootstrap error without chaining sensitive source exceptions. External runtime behavior before the bootstrap boundary remains outside the application's guarantee.

### 3.4 Request Correlation, Completion, Timeout, And Unexpected Errors

Extend the existing correlation middleware rather than creating a second correlation owner. At HTTP request entry it:

1. validates the supplied request ID when present;
2. replaces missing, empty, or invalid input with a generated UUIDv4;
3. stores the safe ID and API emitter in request/task `ContextVar` state;
4. stores the same safe ID plus already-validated source/environment/release data in ASGI `scope["state"]` so the outer exception path can reuse it after user middleware unwinds;
5. captures the first `http.response.start` status and whether response start occurred.

For ordinary and handled-error responses, the middleware emits `http.request` after downstream execution returns and before context reset. The route field comes from the matched framework route template after routing; unavailable/invalid route metadata becomes exact fallback `/{unmatched}`. Status classification is `success` for 100-399, `client_error` for 400-499, and `server_error` for 500-599. Severity is `info`, `warning`, and `error` respectively.

When an exception escapes user middleware, the correlation middleware records that fact and does **not** emit completion. It re-raises so the existing outer exception handling path remains authoritative. The outer handler reads safe request state and first applies the existing `public_timeout_contract(exc)` classification:

- If the exception is a recognized timeout, emit exactly one `application.timeout` event using the existing timeout contract's bounded provider/operation/result/error-code facts, build the existing safe timeout response (currently 503 where that contract specifies 503), and emit exactly one `http.request` completion with that actual final status. No `application.unexpected_error` is emitted.
- Otherwise, emit exactly one `application.unexpected_error` with stable error code `API.UNEXPECTED`, build the existing safe 500 response, and emit exactly one `http.request` completion with status 500.

Both branches reuse the correlation ID stored in safe request state; they do not generate a second ID. Direct calls to the public error helper without request state retain the existing generated-correlation fallback and do not pretend to represent a completed routed request.

If an exception occurs after `http.response.start`, the exception is still classified as timeout versus unexpected for its diagnostic event, but no second HTTP response is attempted. The one completion event uses the captured already-started status, and the server's existing post-start failure behavior is preserved.

### 3.5 Exact API/Runtime Event Inventory

The following tables are the complete in-scope application/runtime emission population. Existing plain logging at these sites is replaced rather than left in parallel.

#### Request, security, and error events

| Existing/runtime branch | Event | Severity | Fixed/allowed facts |
|---|---|---:|---|
| HTTP completion 100-399 | `http.request` | `info` | method; validated route-template label; status; `result="success"`; correlation. |
| HTTP completion 400-499 | `http.request` | `warning` | method; route template; status; `result="client_error"`; correlation. |
| HTTP completion 500-599 | `http.request` | `error` | method; route template; status; `result="server_error"`; correlation. |
| App Check `valid` | existing `app_check.request` | `info` | `provider_kind="firebase"`; existing `app_check.observe`/`app_check.enforce`; route family/template; `result="valid"`; no error code. |
| App Check `missing` | existing `app_check.request` | `warning` | same bounded App Check fields; `result="missing"`; `APP_CHECK.REQUIRED`. |
| App Check `invalid` | existing `app_check.request` | `warning` | same bounded fields; `result="invalid"`; `APP_CHECK.INVALID`. |
| App Check `provider_unavailable` | existing `app_check.request` | `warning` | same bounded fields; `result="provider_unavailable"`; `APP_CHECK.UNAVAILABLE`. |
| Chat allowed | existing `chat.rate_limit` | `info` | `operation="chat_rate_limit.check"`; existing bounded limiter category/route; `result="allowed"`; no error code. |
| Chat rejected | existing `chat.rate_limit` | `warning` | same bounded fields; `result="rejected"`; `API.RATE_LIMITED`. |
| Chat database error | existing `chat.rate_limit` | `error` | same bounded fields; `result="store_error"`; `CHAT.RATE_LIMIT_STORE_ERROR`; original `SQLAlchemyError` still re-raises. |
| Recognized dependency/database timeout | `application.timeout` | `warning` | existing `public_timeout_contract` provider/operation/result/code facts plus correlation; no raw exception. |
| Non-timeout unhandled application exception | `application.unexpected_error` | `error` | `operation="http.request"`; `result="failed"`; `API.UNEXPECTED`; correlation only. |
| Uvicorn runtime warning/error | `runtime.framework` | normalized original warning/error/critical level | fixed `operation="uvicorn.runtime"`; `result="runtime_record"`; no original message/args/traceback/attributes. |

#### Moderation failure events

| Existing call site / branch | Event | Severity | Fixed mapping |
|---|---|---:|---|
| `run_content_moderation_finding_reconciliation_safely` catch-all | `moderation.finding_reconciliation_failed` | `error` | `operation="moderation.finding.reconcile"`; `resource_kind="moderation_finding"`; `result="failed"`; `MODERATION.FINDING_RECONCILIATION_FAILED`; no target data/ID or exception type. |
| `run_moderation_surfacing_safely` `IntegrityError` | `moderation.surfacing_failed` | `error` | `operation="moderation.surfacing.persist"`; `resource_kind="moderation_signal"`; `result="integrity_error"`; `MODERATION.SURFACING_INTEGRITY`. |
| `run_moderation_surfacing_safely` other exception | `moderation.surfacing_failed` | `error` | same operation/resource; `result="failed"`; `MODERATION.SURFACING_FAILED`. |
| `surface_community_game_text` catch-all | `moderation.reconciliation_failed` | `error` | `operation="moderation.community_game.reconcile"`; `resource_kind="community_game"`; `result="failed"`; `MODERATION.COMMUNITY_GAME_RECONCILIATION_FAILED`; no game ID. |
| `surface_need_a_sub_post_text` catch-all | `moderation.reconciliation_failed` | `error` | `operation="moderation.need_a_sub.reconcile"`; `resource_kind="need_a_sub"`; `result="failed"`; `MODERATION.NEED_A_SUB_RECONCILIATION_FAILED`; no post ID. |

Chat-message moderation uses `run_moderation_surfacing_safely`, so its integrity/generic failures use the two surfacing mappings above. These mappings preserve each existing rollback/fail-safe branch; logging occurs only after the branch has performed the same rollback it performs today.

#### Venue-image/R2 failure events

Storage failures are emitted at the request-facing service points in `venue_image_service`, `official_game_query_service`, and `game_service` rather than from both callers and `r2_storage_service`. That gives each failure one operation name and avoids duplicates.

| Entry path / failure | Event mapping |
|---|---|
| `validate_upload_request()` direct `get_r2_storage_config()` failure | `storage.operation_failed`, `error`, `provider_kind="r2"`, `operation="r2.upload.validate"`, `result="configuration_error"`, `STORAGE.CONFIG_UNAVAILABLE`. |
| `check_venue_image_upload_readiness()` config failure | same event/severity/provider, `operation="r2.readiness.check"`, `result="configuration_error"`, `STORAGE.CONFIG_UNAVAILABLE`. |
| `create_venue_image_upload()` direct config failure or upload-ticket config failure | `operation="r2.upload_url.create"`, `result="configuration_error"`, `STORAGE.CONFIG_UNAVAILABLE`. |
| `create_venue_image_upload()` upload-ticket provider failure | `operation="r2.upload_url.create"`, `result="provider_error"`, `STORAGE.UPLOAD_URL_FAILED`. |
| admin/public image read URL config failure | `operation="r2.read_url.create"`, `result="configuration_error"`, `STORAGE.CONFIG_UNAVAILABLE`. |
| admin/public image read URL provider failure | `operation="r2.read_url.create"`, `result="provider_error"`, `STORAGE.READ_URL_FAILED`. |
| `official_game_query_service.build_primary_venue_image_url()` best-effort config failure | Emit the same read-URL configuration event, then preserve the current `None` fallback. |
| `official_game_query_service.build_primary_venue_image_url()` best-effort provider failure | Emit the same read-URL provider event, then preserve the current `None` fallback. |
| `game_service.build_game_card_read()` best-effort config failure | Emit the same read-URL configuration event, then preserve the current missing-image fallback. |
| `game_service.build_game_card_read()` best-effort provider failure | Emit the same read-URL provider event, then preserve the current missing-image fallback. |
| `complete_venue_image_upload()` metadata config failure | `operation="r2.metadata.head"`, `result="configuration_error"`, `STORAGE.CONFIG_UNAVAILABLE`. |
| metadata non-timeout provider failure | `operation="r2.metadata.head"`, `result="provider_error"`, `STORAGE.METADATA_LOOKUP_FAILED`. |
| metadata `DependencyReadTimeoutError` | no storage-failure duplicate; use the single shared `application.timeout` event. |
| expected `R2ObjectNotFoundError` | no provider-failure event; preserve the existing domain 400 behavior and request completion record. |

Every storage event includes active canonical request correlation when available and contains no account, bucket, endpoint, object key, file name, URL, ETag, credentials, provider response, or venue/image/user identifier.

### 3.6 Durable Job Result Mapping And Error-Code Translation

The runner remains the sole owner of `durable_job.processed`. It emits after the applicable durable transition commit so logging failure cannot alter the transition. Event result classification comes from the authoritative committed job state, not blindly from the compatibility string returned by `process_once()`.

The fixed runner mapping is:

| Observed condition and committed state | Existing `process_once()` result | Emit job event? | Severity | Event result | Stable event code |
|---|---|---:|---:|---|---|
| Handler succeeds and commits `succeeded` | `succeeded` | yes | `info` | `succeeded` | omitted |
| Transient failure commits `retry_waiting` | `retry_waiting` | yes | `warning` | `retry_waiting` | translated committed/retry error code; fallback `JOB.TRANSIENT_FAILURE`. |
| Transient failure at the final allowed attempt commits `exhausted` | preserve current `retry_waiting` compatibility result | yes | `error` | `exhausted` | translated committed error code; fallback `JOB.TRANSIENT_FAILURE`. |
| Permanent failure commits `exhausted` | `exhausted` | yes | `error` | `exhausted` | translated committed error code; fallback `JOB.PERMANENT_FAILURE`. |
| Expired lease at maximum attempts commits `exhausted` during claim/recovery | preserve current claim/`process_once()` behavior | yes, as its own job event after the claim transaction commits | `error` | `exhausted` | `JOB.LEASE_EXPIRED_MAX_ATTEMPTS`. |
| Handler/transition reports `lease_lost` without a new terminal commit | `lease_lost` | yes | `warning` | `lease_lost` | `JOB.LEASE_LOST`. |
| Claimed job is missing before handler execution | `missing` | yes | `error` | `missing` | `JOB.MISSING`. |
| Claimed definition becomes unsupported before execution | `unsupported` | yes | `error` | `unsupported` | `JOB.UNSUPPORTED_DEFINITION`. |
| No claimable work | `idle` | no | — | — | — |
| Requested shutdown without a claimed job | `shutdown` | no job-result event | — | — | — |

The runner-owned claim/recovery path collects a bounded safe summary whenever it commits an expired-lease exhaustion. After the claim transaction commits, the runner emits that job's exhaustion event even if the same iteration also claims and processes another job. Existing `claim_job()` callers and return behavior remain compatible; the summary collection is an optional/private runner concern, not a replacement durable history.

Current durable error codes are lowercase safe storage codes. Before an error code is placed in the EN-02 uppercase `stable_error_code` field, use this exact translation table:

| Durable code | Structured event code |
|---|---|
| `malformed_payload` | `JOB.MALFORMED_PAYLOAD` |
| `handler_transient_failure` | `JOB.HANDLER_TRANSIENT_FAILURE` |
| `handler_permanent_failure` | `JOB.HANDLER_PERMANENT_FAILURE` |
| `transient_failure` | `JOB.TRANSIENT_FAILURE` |
| `permanent_failure` | `JOB.PERMANENT_FAILURE` |
| `invalid_provider_event` | `JOB.INVALID_PROVIDER_EVENT` |
| `provider_event_retry` | `JOB.PROVIDER_EVENT_RETRY` |
| `payment_reconcile_invalid` | `JOB.PAYMENT_RECONCILE_INVALID` |
| `payment_reconcile_retry` | `JOB.PAYMENT_RECONCILE_RETRY` |
| `payment_method_reconcile_retry` | `JOB.PAYMENT_METHOD_RECONCILE_RETRY` |
| `lease_expired_max_attempts` | `JOB.LEASE_EXPIRED_MAX_ATTEMPTS` |

The current production registry is completely covered by this table. If a future registered handler supplies another safe durable error code before this logging contract is deliberately extended, the structured event uses fixed `JOB.UNMAPPED_ERROR` rather than echoing or algorithmically transforming the unknown value. The durable row retains its original code unchanged.

Each job event contains only the durable job UUID through the runner-only resource wrapper, canonical correlation when available, bounded `job_type` label, attempt/max-attempt integers, fixed result/severity/code, and `provider_kind="stripe"` for the three current Stripe job types. It never includes payload, protected identity, result metadata, origin reference, lease token/owner, payment/provider identifiers, or durable event history.

### 3.7 Durable Job Correlation Lifecycle

Change only the default correlation selected by `enqueue_job`:

1. Preserve an explicitly supplied value after the current broad safe-string validation.
2. Otherwise use the active canonical request correlation when present.
3. Otherwise generate a canonical UUIDv4.

The database column, accepted historical validation range, and idempotent-return behavior remain unchanged.

After a job is claimed, the runner loads the authoritative job and validates its stored correlation with the strict EN-02 UUIDv4 validator. It opens a scoped context that sets the canonical value when valid or explicitly clears correlation for a legacy value. The scope covers payload validation, handler execution, durable transition, and the post-commit job event and always restores the previous context in `finally`.

The runner captures only the safe facts needed for the post-commit event: job ID, job type, attempt/max-attempt values, outcome, and the current finite durable error code. It does not derive logging metadata by dumping the job model.

### 3.8 Worker Command, Failure Exit, And Exact Operator JSON

The worker command removes per-iteration `print()` output for normal processing. Runner events are the operational record; `idle` remains silent.

After worker logging activation, the command wraps database initialization, registry construction, runner construction, status mode, and the processing loop in a top-level safe failure boundary. An unexpected exception that reaches that boundary emits exactly:

- `event_name="durable_worker.failure"`
- `severity="error"`
- `operation="durable_worker.run"`
- `result="failed"`
- `stable_error_code="WORKER.UNEXPECTED_FAILURE"`

It then returns exit code `1` and does not re-raise. `if __name__ == "__main__": raise SystemExit(main())` therefore exits nonzero without Python printing the original traceback. Normal `--once`, status inspection, clean shutdown, and requested shutdown continue to use their current successful exit behavior.

Failures that occur before the worker bootstrap itself can execute remain outside this guarantee, as described in Section 3.3.

`--status` output is deterministic JSON Lines. The first object is exactly this shape:

```json
{
  "record_type": "durable_job_status",
  "schema_version": 1,
  "by_status": [{"status": "...", "count": 0}],
  "by_type_version": [{"job_type": "...", "payload_version": 1, "count": 0}],
  "attempt_counts_by_status": [
    {
      "status": "...",
      "attempt_counts": [{"attempt_count": 0, "count": 0}]
    }
  ],
  "unsupported_type_versions": [{"job_type": "...", "payload_version": 1}],
  "expired_leases": 0,
  "exhausted_jobs": 0,
  "retry_waiting_jobs": 0,
  "oldest_pending_age_seconds": null,
  "fairness_protected_jobs": 0,
  "worker_heartbeats": [
    {
      "worker_identity": "...",
      "worker_version": "...",
      "status": "running",
      "heartbeat_age_seconds": 0,
      "has_current_job": false
    }
  ]
}
```

Tuple-keyed backlog mappings are therefore encoded as sorted arrays of objects rather than JSON object keys. `by_status`, type/version entries, unsupported pairs, status groups, attempt-count entries, and heartbeat entries are deterministically sorted by their natural keys.

When `--job-id` is supplied and the job exists, the second line is exactly:

```json
{
  "record_type": "durable_job_details",
  "schema_version": 1,
  "missing": false,
  "job_type": "...",
  "payload_version": 1,
  "status": "...",
  "attempt_count": 0,
  "maximum_attempts": 1,
  "last_safe_error_code": null,
  "recent_events": [
    {
      "occurred_at": "2026-01-01T00:00:00Z",
      "event_type": "...",
      "previous_status": null,
      "new_status": null,
      "attempt_count": null,
      "lease_owner": null,
      "safe_error_code": null,
      "event_metadata": {}
    }
  ]
}
```

A missing job emits only:

```json
{"record_type":"durable_job_details","schema_version":1,"missing":true}
```

The submitted job ID itself is not echoed.

Operator strings that are not already finite status/job-type codes—`worker_identity`, `worker_version`, and `lease_owner`—are projected through one output-only safety helper using the existing field-specific storage bounds: 120 characters for worker identity, 80 for worker version, and 120 for lease owner. A value is preserved only when it is a string of 1 through its field's maximum characters, equals its stripped form, contains no control characters, and passes the existing sensitive-text detector; otherwise output is fixed `"redacted"` (or `null` when the source field is null). This output sanitization does not change the persisted heartbeat or event row.

Recent-event `event_metadata` is revalidated/projected through the durable-job diagnostic-metadata safety rules before JSON serialization. Mapping keys are sorted; only already-supported JSON-safe bounded values are retained. If revalidation fails for any stored metadata object, the operator report substitutes `{}` rather than exposing raw metadata or raising. Recent events retain the existing inspection limit and are emitted in the order returned by the accepted inspection service; timestamps use canonical UTC `Z` form. No correlation ID, payload, protected identity, raw `result_metadata`, provider payload, current job ID, lease token, or complete history is added.

### 3.9 Payment And Administrative Correlation Boundaries

The three current Stripe durable job types receive `provider_kind="stripe"` on `durable_job.processed`. Their request-originated enqueues inherit request correlation through the central `enqueue_job` rule. The job UUID is the only resource ID; payment, payment-event, payment-method-operation, customer, charge, PaymentIntent, and other provider/domain IDs never become log resource IDs.

Synchronous payment timeouts remain represented by the shared timeout event. No payment-success event or duplicate financial history is added.

Administrative success and denial behavior remains represented by `AdminAction`. Unexpected administrative runtime failures use the ordinary request/error records. Their correlation ID remains the same request correlation available to the existing audit writer; no audit reason, note, actor/user data, sensitive-read content, or audit metadata object is copied into operational logs.

### 3.10 Uvicorn And Other Logger Handling

The safe API logging setup explicitly disables `uvicorn.access` after Uvicorn has installed its defaults. The application-owned `http.request` event is the only request-access record in this contract.

`uvicorn` and `uvicorn.error` at `WARNING` and above use a dedicated application handler that **ignores** the original `LogRecord.msg`, `args`, `exc_info`, `stack_info`, and arbitrary attributes. For each accepted warning/error/critical record it emits only the fixed `runtime.framework` structured event described in Section 3.5 with normalized severity and validated API source/environment/release metadata. It never attempts to sanitize arbitrary framework text into the event.

That handler uses the same no-op `handleError()` and safe stdout transport rules as application events. Other third-party loggers are not attached to the application structured handler merely to make them appear structured. SQLAlchemy statement/parameter logging remains disabled.

## 4. Failures And Edge Cases

These cases cover the abnormal paths most likely to break correlation, leak sensitive information, or cause logging itself to change application behavior.

1. **Invalid external request ID**
   - **Condition:** `X-Request-ID` is malformed, non-v4, uppercase, padded, control-containing, or otherwise invalid.
   - **Required behavior:** Discard it, generate a canonical UUIDv4, continue the request, and use only the generated value in response and event contracts.

2. **Recognized timeout escapes user middleware**
   - **Condition:** An exception reaching the outer application exception handler matches the existing public timeout contract.
   - **Required behavior:** Emit `application.timeout`, preserve the existing safe timeout response/status/code, emit one completion event with the actual final status, and do not emit `application.unexpected_error`.

3. **Non-timeout exception escapes user middleware**
   - **Condition:** The escaped exception is not a recognized timeout.
   - **Required behavior:** Emit `application.unexpected_error`, preserve the safe 500 response, emit one 500 completion record, and reuse the request's safe correlation ID.

4. **Exception occurs after response start**
   - **Condition:** `http.response.start` was already observed before a timeout or other exception escapes.
   - **Required behavior:** Classify and emit the diagnostic event, emit one completion using the captured status, do not attempt another response, and preserve server failure behavior.

5. **Legacy durable-job correlation**
   - **Condition:** A stored job has an accepted broader correlation such as `job-...`.
   - **Required behavior:** Process normally under an explicitly empty correlation context, omit the legacy value from events, identify only the durable job UUID, and restore prior context afterward.

6. **Durable job produces an unknown safe lowercase error code**
   - **Condition:** A future/changed handler returns a code not present in the finite translation table.
   - **Required behavior:** Keep the original code in durable state, emit fixed `JOB.UNMAPPED_ERROR`, and never transform/echo the unknown value into the structured error-code field.

7. **Unsupported event key or invalid event value**
   - **Condition:** The controlled event mapping contains an unknown key or any value violates type/range/token/length/sensitive-data rules.
   - **Required behavior:** Drop the attempted event and attempt exactly one fixed `logging.event_rejected` record containing none of the rejected input or validation detail.

8. **General caller attempts to supply `resource_id`**
   - **Condition:** `resource_id` appears in a general emitter field mapping.
   - **Required behavior:** Treat it as an unsupported key inside the emitter boundary; only the runner-owned job wrapper can create a resource ID. No lookup is performed to infer UUID semantics.

9. **General caller attempts to override correlation**
   - **Condition:** `correlation_id` or `request_id` appears in a general emitter field mapping.
   - **Required behavior:** Treat it as an unsupported key inside the emitter boundary and use only the active trusted request/job context. The outer error helper may temporarily activate only the already-validated value retained in ASGI request state.

10. **Formatter, handler, or stdout write fails after activation**
   - **Condition:** Serialization or output fails after safe logging is active.
   - **Required behavior:** Swallow the logging failure, do not invoke default `handleError()`, do not recurse into rejection logging for transport failure, and do not alter product behavior.

11. **Safe logging bootstrap cannot be established**
    - **Condition:** The application reaches its logging bootstrap but cannot install the required handlers or safe Uvicorn configuration.
    - **Required behavior:** Stop startup before serving requests or claiming jobs and raise only a fixed bootstrap failure. Do not claim guarantees for interpreter/module-loader failures that occur before bootstrap code executes.

12. **Worker fails after logging activation**
    - **Condition:** Database initialization, registry/runner setup, status mode, or the worker processing loop raises unexpectedly after bootstrap.
    - **Required behavior:** Emit one `durable_worker.failure`, return exit code `1`, and do not re-raise or print a raw traceback.

13. **Operator identity or metadata is unsafe**
    - **Condition:** Worker identity/version/lease owner is oversized, control-containing, sensitive, or stored event metadata fails output revalidation.
    - **Required behavior:** Replace the unsafe identity with fixed `redacted` (or null when originally null) and replace unsafe metadata with `{}`; never emit the rejected source value.

14. **Repeated application construction**
    - **Condition:** Tests/tooling create multiple app instances with different validated settings.
    - **Required behavior:** Tagged handlers are reused/replaced idempotently, each request uses its app's supplied metadata, and no duplicate records or stale cross-app metadata occur.

15. **Missing job in operator inspection**
    - **Condition:** `--status --job-id` names a syntactically valid UUID with no durable job.
    - **Required behavior:** Emit the fixed minimal missing-details JSON object, return the normal successful inspection exit status, and do not echo the submitted identifier.

## 5. Testing

Testing must prove the exact event mappings, correlation lifecycles, bootstrap/failure boundaries, sensitive-data exclusions, worker compatibility, deterministic operator JSON, and effective Uvicorn configuration. Tests should use the lowest reliable layer for each contract and must exercise the finite populations defined in the design.

### 5.1 Envelope, Emitter, And Transport Tests

Verify the additive envelope fields, required runtime fields, deterministic JSON, normalized severity, UTC timestamps, source/environment/release values, and omission of unused optional fields. Existing EN-02 serialization must remain unchanged when new fields are absent.

Exercise every new type/range rule, including HTTP method/status, attempt relationships, release/source ceilings, and structural `resource_kind="durable_job"`/UUID pairing.

Call the general mapping-based emitter with unknown keys—including `correlation_id`, `request_id`, and `resource_id`—and invalid/sensitive values. Assert that the call does not raise, the source value/key/event name does not appear in output, and exactly one fixed `logging.event_rejected` record is attempted for validation rejection. Prove correlation comes only from active trusted context and the runner-specific wrapper is the only production interface that can populate `resource_id`.

Inject JSON serialization, custom-handler, flush/write, and handler-internal failures. Capture both stdout and stderr and prove that no raw event data, exception traceback, logging call stack, original message, or arguments appear; business callers receive only the emitter's failure result.

### 5.2 Request, Timeout, Error, And Concurrency Integration Tests

Exercise 2xx, redirect, handled 4xx/5xx, recognized dependency timeout, ordinary unhandled 500, and exception-after-response-start behavior. Assert exactly one `http.request` event for each completed request and the correct final status/result/severity.

For the timeout branch, assert the existing timeout status/code/body behavior remains intact, `application.timeout` is emitted once, and `application.unexpected_error` is absent. For the ordinary unhandled branch, assert the inverse and preserve the existing safe 500 contract.

Cover caller-supplied valid UUIDv4, missing, empty, and representative invalid IDs. Invalid values must continue processing under a newly generated UUID and the rejected input must be absent from all records.

Run concurrent requests/tasks with distinct request IDs, including at least one timeout/error path. Assert per-task correlation isolation and verify a subsequent request/background task has no leaked prior correlation or emitter context.

Use sensitive raw paths and queries for matched and unmatched requests and verify output contains only the matched route template or `/{unmatched}`. Bodies, headers, cookies, addresses, user agents, and raw targets must be absent.

### 5.3 Exhaustive Current API/Runtime Event-Site Tests

Exercise every row in Section 3.5 and assert its exact event name, severity, operation, result, provider/resource classification, stable error code, and allowed/prohibited fields.

Specifically cover all three chat results (`allowed`, `rejected`, `store_error`); the content-moderation finding reconciliation catch; moderation surfacing integrity and generic catches; community-game and Need-a-Sub reconciliation catches; every listed venue-image/R2 configuration/provider path, including the two best-effort game-card read paths; timeout/non-timeout storage distinction; and expected R2 object-not-found behavior.

Retain a narrow structural source assertion over the enumerated in-scope modules so the old plain/moderation/message-plus-`extra` emission sites do not remain in parallel. The assertion is limited to this finite runtime population and is not a repository-wide compliance framework or a mandate for one-off scripts.

### 5.4 Durable Job Correlation, Outcome, And Code-Translation Tests

Using the existing PostgreSQL-backed durable-job coverage, prove:

- explicit broader correlation remains accepted;
- request-context enqueue stores the request UUID;
- no-context enqueue generates UUIDv4;
- canonical correlation is active throughout handler execution and reset afterward;
- legacy correlation is omitted and cannot inherit prior context;
- `process_once()` retains `shutdown`, `idle`, `missing`, `unsupported`, `succeeded`, `retry_waiting`, `exhausted`, and `lease_lost` compatibility where those paths are exercised;
- idle/shutdown do not create duplicate job-result events;
- each processed outcome uses the exact severity/result/code mapping in Section 3.6;
- a final-attempt transient failure preserves the current `process_once()` result while emitting committed result `exhausted` rather than `retry_waiting`;
- expired-lease exhaustion emits its own post-commit `JOB.LEASE_EXPIRED_MAX_ATTEMPTS` event, including when another job is claimed in the same iteration;
- every current lowercase durable code in the translation table produces its exact uppercase event code;
- an otherwise safe unmapped lowercase code produces `JOB.UNMAPPED_ERROR` without exposing the source code in the event;
- each job event is emitted after the durable transition commit and logging failure cannot change durable state.

### 5.5 Worker Failure And Exact Operator JSON Tests

Run the worker command in a subprocess or equivalent boundary that captures stdout, stderr, and exit code after safe bootstrap. Force a post-bootstrap unexpected failure and assert exactly one `durable_worker.failure` JSON record, exit code `1`, and no Python traceback or raw exception text on either stream.

Exercise clean `--once`, shutdown, idle, and normal processed outcomes to verify accepted success exit behavior and absence of per-iteration plain output.

For `--status`, parse each line as JSON and compare it to the exact schemas in Section 3.8. Cover multiple statuses/types/versions/attempt counts to prove tuple-keyed mappings are encoded as deterministically sorted arrays rather than invalid JSON object keys.

For `--status --job-id`, verify timestamps, null/empty fields, recent-event ordering, missing-job shape, safe metadata projection, and deterministic encoding. Prove valid worker identity and lease-owner values from 81 through 120 characters remain visible, while worker version remains bounded at 80. Seed values over their field-specific bounds plus control-containing/sensitive worker identity, version, lease owner, and event metadata values at the appropriate test boundary and assert redaction/empty metadata without raw leakage.

### 5.6 Bootstrap And Effective Uvicorn Configuration Tests

Exercise the import/startup arrangement used by the normal API entrypoint. Prove safe logging preparation occurs before database/routes are imported, `uvicorn.access` is disabled after Uvicorn's defaults are present, and Uvicorn warning/error records containing sensitive message text, arguments, and traceback information produce only the fixed `runtime.framework` JSON shape.

Inject a database/business-module import failure **after** bootstrap and verify the application does not expose that exception through an application-owned Uvicorn handler. Separately document/test the pre-bootstrap limit by forcing failure before application bootstrap in a subprocess: the process may be controlled by the host interpreter/runtime, and the test must not assert that such output is an application structured event.

Repeat API configuration/app construction and prove exactly one tagged application handler is effective, no duplicate output occurs, and request events use the settings supplied to their own app instance.

### 5.7 Payment, Storage, And Administrative Compatibility

Verify request-originated Stripe jobs carry request correlation into worker events without exposing payment/provider IDs. Exercise current payment-job success/retry/permanent-failure code translation and preserve payment durable-state behavior.

Verify all R2 mappings through the request-facing venue-image and best-effort game-card boundaries with provider calls mocked locally. No account, bucket, endpoint, object key, URL, ETag, file name, credential, provider response, or raw exception may appear.

Verify administrative request/error correlation remains compatible with `AdminAction.correlation_id`, while successful/denied audit metadata, reasons, notes, actor/user information, and sensitive-read content are not copied into logs. Existing audit authorization and transaction atomicity remain unchanged.

### 5.8 Regression Scope

Run the focused observability, request/error, App Check, chat-rate-limit, moderation, durable-job/worker, payment-job, R2-storage, and administrative-audit coverage. Because this work changes shared logging configuration and request middleware used across the API, the normal backend regression suite is required in addition to the focused tests.

No source-level test in this pass establishes centralized provider delivery, retained search, provider access, retention, or deployed production-runtime proof.

## 6. Done When

This section defines the engineering completion bar for WS09-01A.

- [ ] The enumerated production API/runtime and durable-worker surfaces use one bounded JSON event contract, with one-off administrative/development scripts explicitly outside that runtime population.
- [ ] Request IDs preserve current replacement behavior, remain isolated per task, and use one safe correlation across completion, recognized timeout, and unexpected-error paths.
- [ ] Recognized dependency timeouts retain their existing public timeout contract and are never misclassified as unexpected 500 errors.
- [ ] Every in-scope current event/failure site has the exact finite event mapping defined in this plan, including chat `store_error`, all listed moderation branches, venue-image/R2 entry paths, and durable-runner outcomes.
- [ ] The general emitter validates a controlled mapping inside its non-throwing boundary, emits no rejected input in its fixed rejection event, cannot accept correlation/request/resource IDs, and obtains correlation only from trusted request/job context or the private validated outer-error path.
- [ ] Only the durable-runner wrapper can emit a durable-job UUID as `resource_id`; no semantic UUID lookup or other domain identifier logging is introduced.
- [ ] Durable jobs preserve explicit/historical correlation compatibility, inherit request correlation by default where applicable, generate UUIDv4 for new context-free work, classify structured events from committed state, cover final-attempt and expired-lease exhaustion, and translate current lowercase durable error codes with the fixed mapping.
- [ ] Safe logging bootstrap occurs before normal API database/route imports and before worker database/job imports, with pre-bootstrap limitations stated accurately rather than hidden by an impossible no-leak guarantee.
- [ ] Application-owned handlers write only validated JSON to stdout, suppress default `handleError()` diagnostics, disable raw Uvicorn access output, and never reproduce arbitrary framework messages/tracebacks.
- [ ] Post-bootstrap worker failures emit one fixed event, exit `1`, and do not re-raise into a raw traceback.
- [ ] Worker status/job inspection emits the exact deterministic JSON Lines schemas, safely projects operator-controlled identities/metadata using the existing 120/80/120 field bounds, and preserves the accepted bounded operator information.
- [ ] Payment, storage, moderation, and administrative behavior remains compatible with existing durable state, rollback, authorization, audit, and public-error contracts.
- [ ] Focused proof plus the required backend regression suite passes without adding final-provider ingestion, search, access, retention, or deployment assumptions.
