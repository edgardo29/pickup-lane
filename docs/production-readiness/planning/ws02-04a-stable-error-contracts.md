# WS02-04A - Stable Backend Error Contracts

## At A Glance

| Field | Value |
|---|---|
| Pass | `WS02-04A` |
| Track | `WS02` |
| Type | `API / Domain implementation` |
| Primary controls | `API-M12`; supporting intersections with `API-M09`, `API-M10`, `API-M11`, `API-M13`, `API-M15`, `API-M19`, `OPS-010` |
| Authority basis | Locked `API-M12` requirement; final remediation plan; `FDN-04`; `FDN-07`; EN-02 correlation, redaction, and public-error primitives; WS02-01 settings; WS02-02 app construction and health; WS02-03 HTTP security; WS02-04 source-owned closeout; WS02-05A OpenAPI/cache compatibility |
| Depends on | `EN-02`, `WS02-01`, `WS02-02`, `WS02-03` |
| Trusted test scope | `backend/tests/platform/api_errors/` |

## 1. Purpose

WS02-04A defines the stable backend error contract for application-owned FastAPI
errors.

The pass requires backend error responses that are predictable for callers,
safe for users, and useful for operations without exposing implementation
details. Application-owned JSON errors must carry a stable machine-readable
code, safe public message, HTTP status, request correlation ID, and a
frontend-compatible top-level `detail` field.

The pass uses the EN-02 correlation, public error descriptor, redaction, and
telemetry-label primitives. It does not create a second observability schema and
does not complete the broader WS02-04 request-limit, timeout, or rate-control
program.

## 2. Why This Matters

Unstable or over-detailed backend errors create production risk:

- clients may parse framework defaults that change under dependency upgrades;
- users may see stack traces, SQL details, provider messages, paths, tokens, or
  submitted private values;
- operators may receive an error report without a request correlation ID;
- browser callers may break if `detail` disappears before frontend compatibility
  work is complete;
- the current protocol-important headers `Allow`, `Retry-After`, and
  `WWW-Authenticate` may be lost;
- arbitrary exception headers may leak unsafe data if they are copied into
  public responses without an allowlist.

WS02-04A prevents those failures for the repository-owned application error
surface while keeping provider, edge, and deployed HTTP-chain evidence explicit.

## 3. Requirements

| ID | Requirement | What it means | Why it matters |
|---|---|---|---|
| `WS02-04A-R1` | Canonical public error envelope | Application-owned JSON errors expose `detail`, `code`, `message`, `correlation_id`, and optional `details` using EN-02 public-error rules. | Callers get a stable shape without internal exception data. |
| `WS02-04A-R2` | Validation and malformed JSON safety | Request validation and malformed JSON failures return stable 422 envelopes without submitted values, request bodies, unsafe context, secrets, SQL/provider diagnostics, or raw parser internals. | User input failures are common and must not become data leaks. |
| `WS02-04A-R3` | HTTPException status and code normalization | Route, framework, middleware, timeout, body-limit, media-type, and rate-limit HTTP failures keep the correct HTTP status and receive the approved stable public code or safe fallback. | API clients need machine-readable failures without every route hand-building envelopes. |
| `WS02-04A-R4` | Correlation and safe protocol headers | Every application-owned error response has matching body/header correlation. Valid incoming UUIDv4 `X-Request-ID` values are accepted, invalid values are replaced, and only exact approved HTTPException protocol-header/status pairs are preserved. | Operators can correlate failures while public responses do not reflect attacker-controlled IDs or arbitrary headers. |
| `WS02-04A-R5` | Unexpected-error and timeout redaction | Unexpected exceptions and public timeout exceptions never expose raw exception text, stack traces, SQL/provider data, filesystem paths, configuration values, credentials, tokens, cookies, signed URLs, or arbitrary object reprs. | The fallback path is where disclosure risk is highest. |
| `WS02-04A-R6` | Response ownership boundaries | The plan and tests distinguish application-owned JSON errors from middleware-owned, health, docs/OpenAPI, mounted static, redirect, no-content, and provider/edge surfaces. | A stable error contract must not falsely claim ownership of responses the app cannot or should not normalize. |
| `WS02-04A-R7` | Single owner and bypass resistance | The canonical handlers, middleware, and public-error helper are the only source-owned error-envelope path; there are no competing handlers, duplicate correlation injectors, or raw exception serialization paths. | Duplicate owners drift and can bypass redaction, correlation, or compatibility rules. |
| `WS02-04A-R8` | External evidence boundary | Provider-generated errors, edge/CDN/WAF errors, deployed precedence, public staging captures, provider timeout payloads, and sanitized provider/runtime evidence remain external or later-pass proof. | Local pytest must not certify facts that only deployment/provider evidence can prove. |

## 4. Technical Design / Contracts

### 4.1 Public Error Envelope

Application-owned JSON errors use this body shape:

```json
{
  "detail": "safe client-compatible detail",
  "code": "API.STABLE_CODE",
  "message": "Safe public message.",
  "correlation_id": "canonical-uuidv4",
  "details": {}
}
```

`details` is optional. All other fields are required for application-owned JSON
errors. The HTTP status remains the actual response status, not a body-only
field.

`detail` remains top-level for existing frontend compatibility. Current
frontend code reads top-level `detail`, formats validation lists, and reads
top-level `code` before falling back to `detail.code`. WS02-04A therefore keeps
`detail` stable while allowing `message`, `code`, `correlation_id`, and
`details` to support newer clients and operational tooling.

The envelope must be built through the EN-02 `PublicErrorDescriptor` and
correlation/redaction helpers. It must not use raw `str(exc)`, exception
objects, stack traces, database diagnostics, provider payloads, secrets, signed
URLs, cookies, request bodies, or arbitrary object reprs as public data.

### 4.2 Current Status And Code Inventory

| Error class | Owner | Status | Public code | Message source | `detail` / `details` | Header behavior |
|---|---|---:|---|---|---|---|
| Request validation | Application validation handler | 422 | `API.VALIDATION_FAILED` | Stable validation message | `detail` is a sanitized validation-error list; `details.field_errors` mirrors safe field summaries. | `X-Request-ID`; CORS/security headers where WS02-03 owns them |
| Malformed JSON | Application validation handler | 422 | `API.MALFORMED_JSON` | Stable malformed-JSON message | Same sanitized list/field-error shape; submitted body and parser internals excluded. | `X-Request-ID`; CORS/security headers where WS02-03 owns them |
| Bad request | HTTPException handler | 400 | `API.BAD_REQUEST` | Safe exception detail or status fallback | Sanitized detail; no `details` unless a future safe descriptor explicitly supplies it. | No HTTPException-provided headers preserved |
| Unauthenticated | HTTPException handler | 401 | `AUTH.UNAUTHENTICATED` | Safe exception detail or status fallback | Sanitized detail. | Preserve only `WWW-Authenticate` from HTTPException headers, using case-insensitive name matching |
| Forbidden | HTTPException handler | 403 | `AUTH.FORBIDDEN` | Safe exception detail or status fallback | Sanitized detail. | No HTTPException-provided headers preserved |
| Not found | HTTPException handler | 404 | `API.NOT_FOUND` | Safe route/framework detail or status fallback | Sanitized detail. | No HTTPException-provided headers preserved |
| Method not allowed | HTTPException handler | 405 | `API.METHOD_NOT_ALLOWED` | Safe framework detail or status fallback | Sanitized detail. | Preserve only `Allow` from HTTPException headers, using case-insensitive name matching |
| Conflict | HTTPException handler | 409 | `API.CONFLICT` | Safe route detail or status fallback | Sanitized detail; unsafe database/provider text redacted. | No HTTPException-provided headers preserved |
| Retired compatibility route | HTTPException handler | 410 | Valid route-provided `detail.code` when it satisfies EN-02 code rules; otherwise `API.HTTP_ERROR` | Safe `detail.message` or status fallback | Sanitized route detail. Current lowercase tombstone helper codes do not become top-level canonical codes. | No HTTPException-provided headers preserved |
| Request body too large | Request-body middleware / HTTPException handler | 413 | `API.REQUEST_BODY_TOO_LARGE` | Stable body-limit message or safe status fallback | Safe public detail; no body/header/provider leakage. | `X-Request-ID`; CORS/security headers where applicable |
| Unsupported content encoding | Request-body middleware | 415 | `API.UNSUPPORTED_CONTENT_ENCODING` | Stable content-encoding message | Safe public detail. | `X-Request-ID`; CORS/security headers where applicable |
| Unsupported media type | Request-body middleware / HTTPException handler | 415 | `API.UNSUPPORTED_MEDIA_TYPE` | Stable media-type message or safe status fallback | Safe public detail. | `X-Request-ID`; CORS/security headers where applicable |
| Rate limited | HTTPException handler | 429 | `API.RATE_LIMITED` | Safe route detail or status fallback | Safe public detail. | Preserve only `Retry-After` from HTTPException headers, using case-insensitive name matching |
| Public timeout | Unexpected-exception handler via timeout classifier | 503 | `API.DEPENDENCY_READ_TIMEOUT`, `API.DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN`, or `API.DATABASE_TIMEOUT` | Timeout contract | Safe timeout detail and bounded timeout `details`. | `X-Request-ID`; no provider payload |
| Service unavailable | HTTPException handler | 503 | `API.SERVICE_UNAVAILABLE` | Safe route detail or status fallback | Sanitized detail; provider/config values redacted if unsafe. | No HTTPException-provided headers preserved; no current source-approved 503 `Retry-After` |
| Other HTTPException | HTTPException handler | Original status | Valid `detail.code` when EN-02-safe; otherwise `API.HTTP_ERROR` | Safe detail/message or HTTP status phrase fallback | Sanitized detail. | No HTTPException-provided headers preserved unless the status/header pair is one of the exact approved pairs in Section 4.4 |
| Unexpected exception | Unexpected-exception handler | 500 | `API.UNEXPECTED` | Stable generic message | Stable generic detail; no raw exception data. | `X-Request-ID`; safe redacted log context |

### 4.3 Validation And Malformed JSON Details

Validation responses must remove submitted values and unsafe context. Safe
validation entries may include:

- `loc`;
- `msg`;
- `type`;
- safe Pydantic documentation `url` values when present.

The supplemental `details.field_errors` list may include only safe field
locations, descriptions, and error types. It must not include submitted values,
request bodies, secrets, tokens, cookies, private URLs, provider payloads,
database diagnostics, raw parser exceptions, or arbitrary object reprs.

Malformed JSON is classified from the current FastAPI/Pydantic validation error
surface and keeps status 422 with code `API.MALFORMED_JSON`.

### 4.4 Correlation And Header Contract

`X-Request-ID` is the response correlation header. The value in the public error
body must equal the response header.

Incoming `X-Request-ID` is accepted only when it is a canonical UUIDv4 value
validated by EN-02. Missing or invalid incoming values are replaced by a
server-generated canonical UUIDv4 and are not reflected.

HTTPException headers are untrusted input unless explicitly approved. The
implementation must filter only headers supplied through the HTTPException path
before they enter the public error response. The filter belongs in, or directly
for, `handle_http_exception()` before calling `_public_error_response(...)`.

The approved HTTPException-provided header preservation contract is exactly:

| Status | Preserved HTTPException header | Value ownership |
|---:|---|---|
| 401 | `WWW-Authenticate` | No current source producer was found. The contract preserves a source/framework-owned authentication challenge if one is supplied by an approved 401 HTTPException path. |
| 405 | `Allow` | Current Starlette/FastAPI routing generates the method list for framework-owned method-not-allowed responses. |
| 429 | `Retry-After` | Current chat rate-limit source generates an integer-second retry delay from the approved rolling-window limiter. |

No other HTTPException-provided header is preserved by WS02-04A. Current source
does not supply, require, or approve 503 `Retry-After`.

Header-name comparison is case-insensitive. The implementation may emit
canonical spelling, but allowlist membership must treat `WWW-Authenticate`,
`www-authenticate`, and other casing variants as the same header name.

Preservation is restricted to the exact status/header pairs above. Values for
those pairs are preserved as supplied because the current approved producers
are framework-owned or source-owned protocol values. WS02-04A does not create a
new generic header-value sanitizer. A future producer that derives one of these
header values from user input, provider payloads, secrets, or free text requires
a separate review before it can rely on this contract.

`X-Request-ID` is never preserved from HTTPException headers, with any casing.
It is owned exclusively by the canonical EN-02 correlation path. The public
body `correlation_id` must equal the final response `X-Request-ID` even when
`exc.headers` attempts to supply `X-Request-ID`, `x-request-id`, or another
casing variant.

Representative rejected HTTPException-provided headers are `X-Request-ID`,
`X-Internal`, `Set-Cookie`, `Location`, `Access-Control-Allow-Origin`, and
`Cache-Control`.

WS02-03-owned CORS and response-security headers continue to be applied by the
middleware stack where that stack owns the response class.

### 4.5 Unexpected Exceptions And Logging

Unhandled ordinary exceptions return:

- status `500`;
- code `API.UNEXPECTED`;
- message `Something went wrong. Please try again.`;
- detail `An unexpected error occurred.`;
- body/header correlation.

The log record for unexpected exceptions may include only a redacted bounded
event context with the stable error code and correlation ID. It must not include
raw exception text, traceback text, SQL/provider diagnostics, credentials,
tokens, cookies, signed URLs, request bodies, submitted private values, file
paths, or arbitrary object reprs.

Timeout exceptions recognized by the source-owned timeout classifier return the
approved timeout contract instead of the generic 500. Timeout logging uses
bounded timeout telemetry labels and the safe correlation ID.

### 4.6 Current Response Ownership Matrix

| Surface | Current ownership model | WS02-04A contract |
|---|---|---|
| Application-owned JSON errors | FastAPI exception handlers plus EN-02 public-error primitives. | Stable envelope required. |
| Validation and malformed JSON | FastAPI `RequestValidationError` routed to application handler. | Stable 422 envelope and sanitized validation details required. |
| Authentication and authorization errors | Route/dependency `HTTPException` routed to application handler. | Stable 401/403 envelope required; no sensitive auth/provider data. |
| Framework 404 and 405 | Starlette/FastAPI HTTPException routed to application handler. | Stable envelope required; 405 preserves `Allow`. |
| Body-limit and media-type middleware errors | Application-owned request-body middleware uses `public_error_response`. | Stable 413/415 envelope required. |
| Rate-limit errors | Source-owned chat limiter raises 429 `HTTPException` with `Retry-After`. | Stable 429 envelope required; preserve safe `Retry-After`. |
| Public timeout errors | Timeout classifier maps approved timeout exception classes. | Stable 503 timeout envelopes required. |
| Unexpected exceptions | Application unexpected-exception handler. | Stable 500 envelope and safe log context required. |
| Invalid Host | `TrustedHostMiddleware`; not converted to JSON envelope. | Remains middleware-owned text response with response correlation and WS02-03 security/cache headers when the app stack observes it. |
| Health and diagnostics | `/live`, `/ready`, and conditional `/db-health` use WS02-02 health/diagnostic response contracts. | Health 503 responses are not the public error envelope. |
| Docs and OpenAPI | FastAPI docs/OpenAPI routes controlled by settings and WS02-05A policy. | Successful docs/OpenAPI responses are not error envelopes; disabled/missing docs route failures use ordinary 404 behavior. |
| Mounted static | Current source mounts `backend/static` at `/static`. | Successful static/file responses stay outside generic API header policy; missing static assets currently route through stable JSON 404 with correlation but keep static-path security-header exclusion. |
| Framework slash redirects | Current FastAPI/Starlette routing redirects alternate slash forms with 307. | Redirect responses are not error envelopes and are excluded from generic API response-security headers, while correlation still applies when the app stack observes them. |
| No-content response | Current source has one 204 auth cleanup route. | Successful 204 responses have no error body; response-security/correlation may still apply as response headers. |
| File, streaming, WebSocket | Current source has no app-owned `FileResponse`, `StreamingResponse`, or WebSocket route beyond mounted static. | No additional error-envelope ownership is invented. |
| Provider, edge, CDN, WAF, deployed proxy | External runtime/provider layers. | Not repository-proven by WS02-04A local tests. |

### 4.7 Single-Owner Rules

The canonical error-envelope owners are:

- `backend/observability/http_errors.py` for correlation middleware, exception
  handlers, sanitizer logic, timeout classification, and `public_error_response`;
- `backend/main.py` for one canonical FastAPI app construction path and
  middleware installation;
- EN-02 modules for correlation ID validation/generation, redaction, public
  descriptor validation, and telemetry-label safety.

Route code may raise `HTTPException` with safe detail, but routes must not build
a competing public error envelope, register route-local exception handlers,
inject duplicate correlation headers, or serialize raw exceptions directly to
clients.

## 5. Implementation Scope

WS02-04A owns:

- the canonical pass plan at
  `docs/production-readiness/planning/ws02-04a-stable-error-contracts.md`;
- the stable error contract implementation in `backend/observability/http_errors.py`;
- interaction with canonical app construction in `backend/main.py`;
- source-owned body-limit, media-type, timeout, and rate-limit error classes
  only where they flow through the stable error contract;
- requirement declarations in `backend/tests/support/requirements/ws02_04a.json`;
- a human testing/risk record in `backend/tests/platform/api_errors/TESTING_RECORD.md`;
- fresh trusted tests in `backend/tests/platform/api_errors/`.

The only production correction authorized by this plan is in
`backend/observability/http_errors.py`. The current source defect is that
arbitrary HTTPException-provided headers flow through `handle_http_exception()`
into `_public_error_response(...)`, where the whole supplied mapping is copied
before canonical correlation is added with `setdefault`.

The correction must filter only `exc.headers` in, or directly for,
`handle_http_exception()`. It must not add a response-wide header filter and
must not broaden filtering to unrelated `public_error_response(...)` callers.
The exact approved HTTPException-provided headers are:

- status 401: `WWW-Authenticate`;
- status 405: `Allow`;
- status 429: `Retry-After`.

Header-name matching must be case-insensitive. `X-Request-ID` from
HTTPException headers must always be rejected, regardless of casing, so the
canonical EN-02 correlation ID wins.

The implementation must preserve:

- the existing public envelope field names;
- top-level `detail` compatibility;
- EN-02 descriptor/redaction/correlation ownership;
- FastAPI/Starlette status behavior;
- WS02-03 CORS and response-security middleware ownership;
- cache-header ownership;
- WS02-02 health/diagnostic response contracts;
- WS02-05A OpenAPI/cache/docs policy;
- source-owned 413, 415, timeout 503, and chat 429 contracts from adjacent
  accepted WS02-04 slices;
- existing `public_error_response(...)` callers outside the HTTPException path.

Gate B is authorized to modify exactly these WS02-04A implementation/evidence
files:

1. `backend/observability/http_errors.py`
2. `backend/tests/support/requirements/ws02_04a.json`
3. `backend/tests/platform/api_errors/TESTING_RECORD.md`
4. `backend/tests/platform/api_errors/test_public_error_envelope_contract.py`
5. `backend/tests/platform/api_errors/test_validation_and_malformed_json_contract.py`
6. `backend/tests/platform/api_errors/test_http_exception_status_contract.py`
7. `backend/tests/platform/api_errors/test_correlation_and_safe_headers_contract.py`
8. `backend/tests/platform/api_errors/test_unexpected_error_redaction_contract.py`
9. `backend/tests/platform/api_errors/test_error_boundary_static_contract.py`

The canonical WS02-04A plan has already been modified during Gate A and becomes
frozen after human approval. Gate B must not modify or redesign it.

## 6. Testing And Evidence

### 6.1 Requirement Declaration Design

The pass must create `backend/tests/support/requirements/ws02_04a.json` with
this machine-readable requirement model:

| ID | Owning pass | Source controls | State | Scope | Reason when needed |
|---|---|---|---|---|---|
| `WS02-04A-R1` | `WS02-04A` | `API-M12`, `API-M15`, `EN-02`, `FE-M04` | `required` | `platform/api_errors` | Not applicable |
| `WS02-04A-R2` | `WS02-04A` | `API-M12`, `API-M09`, `EN-02` | `required` | `platform/api_errors` | Not applicable |
| `WS02-04A-R3` | `WS02-04A` | `API-M12`, `API-M09`, `API-M10`, `API-M11`, `EN-02`, `WS02-04B2A1`, `WS02-04C1`, `WS02-04C3A`, `WS02-05A` | `required` | `platform/api_errors` | Not applicable |
| `WS02-04A-R4` | `WS02-04A` | `API-M12`, `API-M13`, `API-M15`, `FDN-07`, `EN-02` | `required` | `platform/api_errors` | Not applicable |
| `WS02-04A-R5` | `WS02-04A` | `API-M12`, `API-M15`, `OPS-010`, `EN-02`, `WS02-04C1` | `required` | `platform/api_errors` | Not applicable |
| `WS02-04A-R6` | `WS02-04A` | `API-M12`, `API-M08`, `API-M16`, `API-M17`, `API-M18`, `API-M19`, `WS02-02`, `WS02-03`, `WS02-05A` | `required` | `platform/api_errors` | Not applicable |
| `WS02-04A-R7` | `WS02-04A` | `API-M12`, `API-M15`, `EN-02`, `WS02-02` | `required` | `platform/api_errors` | Not applicable |
| `WS02-04A-R8` | `WS02-04A` | `API-M12`, `API-M15`, `API-M19`, `OPS-010`, `OPS-025`, `WS10-02` | `deferred` | `governance` | Provider-generated errors, edge/CDN/WAF errors, deployed error/header precedence, public staging captures, provider timeout payloads, and sanitized provider/runtime evidence cannot be proven by local repository tests and remain external evidence. |

### 6.2 Trusted Test Modules

The pass must create these trusted test modules:

| Test module | Primary proof |
|---|---|
| `backend/tests/platform/api_errors/test_public_error_envelope_contract.py` | Envelope fields, top-level `detail`, EN-02 descriptor integration, frontend-compatible static contract, and safe detail shapes. |
| `backend/tests/platform/api_errors/test_validation_and_malformed_json_contract.py` | Validation and malformed JSON 422 classification, sanitized validation list, field-error details, and submitted-value exclusion. |
| `backend/tests/platform/api_errors/test_http_exception_status_contract.py` | Status/code normalization for 400, 401, 403, 404, 405, 409, 410, 413, 415, 429, 503, timeout, and other HTTPException classes. |
| `backend/tests/platform/api_errors/test_correlation_and_safe_headers_contract.py` | Valid incoming request-ID acceptance, invalid request-ID replacement, body/header equality, context cleanup, exact HTTPException header filtering, case-insensitive header-name matching, CORS/security/cache preservation, and canonical middleware ownership. |
| `backend/tests/platform/api_errors/test_unexpected_error_redaction_contract.py` | Generic 500 response, timeout-specific 503 response, nested redaction, public/log leakage prevention, and no raw exception text. |
| `backend/tests/platform/api_errors/test_error_boundary_static_contract.py` | Canonical app registration, middleware order, invalid Host boundary, health/docs/OpenAPI/static/redirect/no-content ownership, absence of app-owned file/streaming/WebSocket surfaces, and no duplicate error owners. |

The pass must create `backend/tests/platform/api_errors/TESTING_RECORD.md`
using the canonical testing-record template. The record should explain risk
groups, scenario selection, proof layers, remaining external gaps, and adequacy
conclusions without duplicating every pytest node ID.

### 6.3 Proof Layer Decisions

Executable WS02-04A proof uses:

- FastAPI `TestClient` for application, middleware, framework, CORS, security,
  validation, malformed JSON, and routing behavior;
- direct helper/handler proof where lower-level sanitization or timeout
  classification is the owned behavior;
- static source checks for duplicate handlers, duplicate middleware,
  unsupported response classes, frontend compatibility, and absence of
  alternate public error owners.

Executable WS02-04A proof does not require:

- PostgreSQL;
- database migrations or schema-history tests;
- external network access;
- provider sandbox/dashboard access;
- browser/Playwright;
- concurrency;
- controlled time;
- subprocesses or a live server.

Synthetic values must be used. Provider, token, database URL, cookie, signed URL,
email, phone, and private-object examples must be fake and intentionally safe.

### 6.4 Adequacy Safeguards

The tests must fail for the right reason. They must check combinations of:

- exact status;
- exact stable code;
- public message source;
- `detail` type and shape;
- optional `details` and `field_errors` shape;
- body/header correlation equality;
- valid and invalid incoming `X-Request-ID`;
- preservation of `WWW-Authenticate` only for 401, `Allow` only for 405, and
  `Retry-After` only for 429 when supplied through HTTPException headers;
- case-insensitive input-name matching for approved HTTPException headers;
- rejection of HTTPException-supplied `X-Request-ID` casing variants,
  `X-Internal`, `Set-Cookie`, `Location`, `Access-Control-Allow-Origin`, and
  `Cache-Control`;
- proof that rejected HTTPException headers are not forwarded merely because a
  route or framework HTTPException supplied them;
- proof that canonical CORS, response-security, cache, and correlation headers
  added by outer accepted layers still survive on final responses where
  applicable;
- submitted-value exclusion;
- nested mapping/list redaction;
- raw exception and logging redaction;
- CORS and response-security preservation where WS02-03 owns those headers;
- invalid Host remaining middleware-owned;
- frontend compatibility;
- duplicate/alternate owner absence.

The test set should group equivalent classes rather than creating a Cartesian
explosion of every route.

## 7. Integration / Operational Expectations

WS02-04A integrates with:

- EN-02 for correlation ID validation/generation, request-local correlation,
  safe public error descriptors, redaction, and bounded telemetry labels;
- WS02-01 for environment/settings safety and production-like defaults;
- WS02-02 for canonical app construction, lifecycle, health, readiness, and
  diagnostic response ownership;
- WS02-03 for Host enforcement, CORS, response-security headers, redirect/static
  exclusions, and deployed HTTP-chain evidence boundaries;
- WS02-04B/C slices for source-owned 413, 415, timeout, and 429 error classes;
- WS02-05A for OpenAPI error schemas, 405 documentation, cache policy, docs
  exposure, tombstone representation, and rolling compatibility;
- WS07/FE-M04 because the current frontend API client still consumes top-level
  `detail` and top-level `code`.

Operationally, accepting WS02-04A means the repository-owned backend error
contract is ready for review. It does not mean provider, edge, WAF, production
logging, staging, or full HTTP-chain evidence is closed.

## 8. Not Part Of This Pass

WS02-04A does not implement or close:

- numeric request-size, header, URL, pagination, timeout, retry, rate, worker,
  pool, or alert values;
- global request deadlines, response deadlines, process-server timeouts,
  keep-alive, graceful shutdown, or durable-worker policy;
- broad logging, access logs, metrics, dashboards, alerting, tracing, SLOs, or
  retention;
- provider dashboard configuration or provider-generated error payload control;
- edge/CDN/WAF generated errors or public-host precedence;
- staging/production HTTP captures;
- frontend API-client redesign;
- OpenAPI/schema/cache work beyond preserving existing WS02-05A contracts;
- authentication, authorization, payment, domain, database, migration, or
  business-rule redesign;
- Playwright/browser evidence;
- historical evidence as the current executable contract.

## 9. Related Controls And Remaining Evidence

| Control / Decision | WS02-04A relationship | Remaining evidence boundary |
|---|---|---|
| `API-M12` | Primary control. WS02-04A owns stable source-level JSON errors for application-owned backend failures. | Full closure still needs provider, edge, staging, and deployed precedence evidence. |
| `API-M09` | Body-limit and media-type errors that reach FastAPI must use stable public errors. | Header, URL, ingress, process-server, provider, edge, upload, staging, and precedence evidence remain outside WS02-04A. |
| `API-M10` | Source-owned timeout classes must map to safe stable 503 errors. | Global request/runtime deadlines, cancellation behavior across deployment, provider dashboards, durable recovery, and load evidence remain outside WS02-04A. |
| `API-M11` | Source-owned chat 429 responses must keep stable code/correlation and safe `Retry-After`. | Anonymous/IP, edge/WAF/provider, non-chat, multi-instance/load, monitoring, and provider-cost rate evidence remain later. |
| `API-M13` | WS02-04A preserves protocol-relevant headers on error responses. | Broader content negotiation, idempotency semantics, and API compatibility remain WS02-05 and later work. |
| `API-M15` / `FDN-07` / `OPS-010` | Error responses and timeout/unexpected logging must use safe correlation and privacy-bounded fields. | Structured access logs, metrics, dashboards, tracing, alerting, and production log samples remain WS09/WS10 evidence. |
| `API-M08` / `API-M16` / `API-M17` / `API-M18` / `API-M19` | Error-contract evidence must preserve response-security, cache, health, docs/OpenAPI, and HTTP-chain ownership boundaries. | Provider-added headers, deployed cache/header behavior, public docs exposure, release-linked staging captures, and full HTTP-chain evidence remain external/later. |
| `OPS-025` / `WS10-02` | External provider/runtime evidence must be sanitized and handled through accepted evidence processes. | Provider account settings, access, MFA, DNS/TLS, deployments, logs, secret-store, and sanitized evidence packages remain provider/control-plane work. |

## 10. Completion Criteria

- [ ] The canonical WS02-04A plan uses the reusable planning-document structure
  and contains current requirements, contracts, scope, evidence design, and
  external boundaries.
- [ ] `backend/observability/http_errors.py` filters only HTTPException-provided
  headers before public error response construction, preserving only
  case-insensitive `WWW-Authenticate` on 401, `Allow` on 405, and
  `Retry-After` on 429.
- [ ] `backend/tests/support/requirements/ws02_04a.json` declares all final
  WS02-04A requirements with valid IDs, source controls, states, scopes, and
  reasons where required.
- [ ] `backend/tests/platform/api_errors/TESTING_RECORD.md` records the trusted
  evidence reasoning and remaining external gaps from current authority under
  the accepted EN-01 architecture.
- [ ] Trusted tests under `backend/tests/platform/api_errors/` prove the
  application-owned error contract, redaction, correlation, header, ownership,
  frontend-compatibility, and bypass-resistance requirements.
- [ ] Focused WS02-04A tests pass.
- [ ] Relevant EN-02, WS02-02, WS02-03, WS02-04B/C, and WS02-05A regression
  checks required by the implemented change set pass.
- [ ] Checker file/domain/suite scopes and generated traceability pass for the
  final WS02-04A state.
- [ ] `git diff --check` passes.
- [ ] Trusted WS02-04A evidence is derived from current authority under the
  accepted EN-01 architecture; historical evidence does not define the current
  executable contract.
- [ ] No provider, edge, staging, logging/metrics, frontend redesign, database,
  migration, browser, or later-pass evidence is falsely claimed as closed.
