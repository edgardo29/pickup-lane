# WS02-04B2A1 - Portable Request Body Boundaries

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS02-04B2A1` |
| Primary controls | `API-M09`, `GOV-006` |
| Numeric authority | `docs/production-readiness/decisions/ws02-04b2a1-request-body-limits-approved.md` |
| Current closure type | Source-owned FastAPI request-body enforcement for two approved special request classes only |
| Approved B2A1 values | 160 KiB / 163,840 bytes for Platform Notice create; 64 KiB / 65,536 bytes for signed Stripe webhook requests |
| Requirement declaration | `backend/tests/support/requirements/ws02_04b2a1.json` |
| Trusted test scope | `backend/tests/platform/request_body_limits/` |
| Testing record | `backend/tests/platform/request_body_limits/TESTING_RECORD.md` |
| Evidence boundary | Local repository source, trusted pytest, direct ASGI harnesses, FastAPI/TestClient integration, settings/static review |
| Explicit non-closure | Ordinary JSON body limits, JSON media-type policy, form/multipart/file-upload limits, R2 object bytes, headers, URLs, ingress, process-server behavior, provider limits, permanent-host alignment, staging/provider precedence, runtime telemetry, dashboards, alerts, and live Stripe evidence |

## 1. Purpose

WS02-04B2A1 establishes portable, application-owned request-body boundaries for
the current repository surfaces that have explicit owner-approved FDN-04 /
GOV-006 numeric values and can be enforced honestly inside FastAPI source.

This pass owns two request classes:

- Platform Notice create requests: `POST /admin/platform-notices`, approved at
  160 KiB / 163,840 bytes.
- Signed Stripe webhook requests: signed `POST /stripe/webhook`, approved at
  64 KiB / 65,536 bytes.

The pass does not approve a universal request-size policy. It does not claim
that provider, edge, process-server, permanent-host, staging, ordinary JSON, or
JSON media-type behavior is complete.

## 2. Why This Matters

The backend has routes that can receive materially large request bodies before
business validation, database work, or provider verification. Without a
source-owned request-body limit for the approved classes, expensive or unsafe
payloads can reach JSON parsing, Stripe webhook verification, or application
handlers before the backend applies a bounded failure.

The control needs to be portable because permanent public-edge and provider
topology is not finalized. The FastAPI layer can provide a real repository-owned
safeguard now, while preserving the evidence boundary for later ingress,
process-server, provider, media-type, ordinary JSON, and staging work.

## 3. Requirements

| Requirement ID | Requirement | Authority Class | Evidence State |
|---|---|---|---|
| `WS02-04B2A1-R1` | Platform Notice create uses the approved 160 KiB source-owned request-body limit for `POST /admin/platform-notices` only, without redefining WS02-04B1 field, recipient, audience, audit, or persistence rules. | B2A1-owned approved value and route class | required |
| `WS02-04B2A1-R2` | Signed Stripe webhook requests use the approved 64 KiB source-owned request-body limit for signed `POST /stripe/webhook` only; accepted bytes remain exact for signature verification; missing-signature requests remain route-owned and are not promoted into the signed-webhook limit class. | B2A1-owned approved value and route class; Stripe provider behavior remains external | required |
| `WS02-04B2A1-R3` | The limiter enforces actual ASGI `http.request` bytes, treats `Content-Length` as advisory, accepts exactly-at-limit bodies, rejects limit-plus-one bodies, supports missing length metadata and multi-message delivery, ignores malformed or duplicate length metadata for early approval, and does not parse, reconstruct, or mutate accepted bodies. | B2A1 source contract | required |
| `WS02-04B2A1-R4` | Non-identity `Content-Encoding` is rejected for the B2A1 limited classes before body processing; the application performs no decompression and does not create a global content-encoding policy for unrelated routes. | B2A1 source contract | required |
| `WS02-04B2A1-R5` | Application-owned B2A1 413 and unsupported-content-encoding 415 rejections use stable, safe public responses with correlation behavior and compatible security/CORS/header handling where applicable, without leaking submitted bodies, signatures, headers, provider data, or internals. | Inherited error, correlation, CORS, and security-header contracts applied to B2A1 errors | required |
| `WS02-04B2A1-R6` | The two B2A1 limits are owned through typed backend settings, safe defaults, positive integer parsing, and `.env.example` documentation; ordinary JSON body-limit settings remain WS02-04B2A2C-owned. | B2A1 for Platform Notice and Stripe values; WS02-04B2A2C for ordinary JSON | required |
| `WS02-04B2A1-R7` | One application-owned middleware path selects B2A1 route classes by HTTP method and normalized path before downstream body reads; there is no duplicate repository-owned request-body limiter or raw-body bypass for the two B2A1 classes. | B2A1 source contract and current repository inventory | required |
| `WS02-04B2A1-R8` | Remaining request-size, ingress, provider, process-server, staging, R2, form/multipart, header, URL, media-type, telemetry, and runtime evidence gaps stay explicit and are not represented as closed by local B2A1 source tests. | Later/external responsibility preserved by GOV-006 and WS02 handoffs | deferred |

### Requirement Declaration Design

Gate B must create `backend/tests/support/requirements/ws02_04b2a1.json` with
this exact machine declaration design:

| Requirement ID | State | Scope | `source_controls` | Reason |
|---|---|---|---|---|
| `WS02-04B2A1-R1` | `required` | `platform/request_body_limits` | `["API-M09", "GOV-006", "FDN-04", "WS02-04B2A1", "WS02-04B1"]` | none |
| `WS02-04B2A1-R2` | `required` | `platform/request_body_limits` | `["API-M09", "GOV-006", "FDN-04", "WS02-04B2A1", "WS05"]` | none |
| `WS02-04B2A1-R3` | `required` | `platform/request_body_limits` | `["API-M09", "GOV-006", "FDN-04", "WS02-04B2A1"]` | none |
| `WS02-04B2A1-R4` | `required` | `platform/request_body_limits` | `["API-M09", "GOV-006", "FDN-04", "WS02-04B2A1"]` | none |
| `WS02-04B2A1-R5` | `required` | `platform/request_body_limits` | `["API-M09", "API-M12", "WS02-04B2A1", "WS02-04A", "WS02-03", "EN-02"]` | none |
| `WS02-04B2A1-R6` | `required` | `platform/request_body_limits` | `["API-M09", "GOV-006", "FDN-04", "WS02-04B2A1", "WS02-01", "WS02-04B2A2C"]` | none |
| `WS02-04B2A1-R7` | `required` | `platform/request_body_limits` | `["API-M09", "GOV-006", "FDN-04", "WS02-04B2A1", "WS02-04B2A2C"]` | none |
| `WS02-04B2A1-R8` | `deferred` | `governance` | `["API-M09", "GOV-006", "FDN-04", "WS02-04B2A1", "WS02-04B2A2C", "WS02-05A", "WS02-04B2B", "WS02-04B2C", "WS05", "WS09"]` | `Ordinary JSON body limits and route metadata are owned by WS02-04B2A2C; JSON media-type behavior is owned by WS02-05A; provider, edge, ingress, process-server, permanent-host, staging, R2 object-byte, telemetry, dashboard, alert, and live Stripe evidence remain later or external responsibilities and cannot be closed by local B2A1 source tests.` |

R8 must have no pytest mapping.

## 4. Technical Design / Contracts

### Approved Values

The direct durable authority for the B2A1 numeric values is
`docs/production-readiness/decisions/ws02-04b2a1-request-body-limits-approved.md`.
The GOV-006 limits register records those approved values, but it is not their
self-approving source.

Approved B2A1 values:

- 160 KiB / 163,840 bytes for the Platform Notice create route class.
- 64 KiB / 65,536 bytes for signed Stripe webhook requests.

The evidence basis preserved in the decision record is:

- Current Platform Notice source bounds `idempotency_key` to 160 characters,
  `title` to 150 characters, `message` to 4,000 characters, and selected users
  to 500 IDs. A compact synthetic request at those valid selected-user bounds
  is 23,911 bytes; an impossible combined all-eligible-plus-selected shape is
  23,915 bytes.
- Current signed Stripe webhook source consumes a raw provider payload and then
  processes supported payment-intent and refund event classes. A representative
  safe synthetic supported payment-intent event containing the current fields
  consumed by source is about 1 KiB.

The Stripe value is not a Stripe provider hard-limit claim.

### Route Selection

The request-body limiter is a pure ASGI middleware installed in the FastAPI
application middleware stack. It selects a limit before downstream body
processing:

| Class | Selection Rule | Limit |
|---|---|---:|
| Signed Stripe webhook | `POST` plus normalized path `/stripe/webhook` plus a present `Stripe-Signature` header | 65,536 bytes |
| Platform Notice create | `POST` plus normalized path `/admin/platform-notices` | 163,840 bytes |

Path matching strips trailing slashes except for root. The B2A1 route classes
must remain distinct from ordinary JSON selection, and signed Stripe webhook
selection must preserve the current missing-signature boundary.

Ordinary JSON 65,536-byte limiting and ordinary JSON route-metadata selection
are owned by WS02-04B2A2C, even though current source uses the same middleware.

### Actual Bytes And Content-Length

For B2A1 limited classes:

- actual bytes are counted from ASGI `http.request` messages;
- non-HTTP ASGI scopes pass through untouched;
- empty and zero-byte messages are allowed;
- accepted bytes are delivered downstream unchanged;
- exact-limit bodies are allowed;
- bodies exceeding the limit are rejected;
- one syntactically valid `Content-Length` above the selected limit may reject
  before the body is read;
- a declared length within the limit is never trusted for acceptance;
- missing, malformed, duplicate, or conflicting `Content-Length` metadata does
  not create early approval;
- chunked or multi-message bodies that reach ASGI are enforced by actual-byte
  counting;
- the middleware does not parse JSON, reconstruct the body, call providers, use
  the database, or buffer accepted content for later replay.

Transport, ingress, or process-server rejection before FastAPI is outside this
source contract and may not use the application error envelope.

### Platform Notice Contract

The 160 KiB limit applies only to the Platform Notice create route class. It
protects the request-body boundary before JSON parsing and downstream
application work. The pass must not duplicate or re-own WS02-04B1 behavior for
selected-user counts, field lengths, list pagination, recipient pagination,
audit policy, or persisted side effects.

Recipient routes, list/history routes, worker batching, direct R2 object bytes,
and unrelated admin routes are outside the B2A1 Platform Notice limit.

### Stripe Webhook Contract

The 64 KiB limit applies only to signed Stripe webhook requests. Oversized
signed requests must be rejected before Stripe event construction, provider
verification, database mutation, or business mutation.

Accepted signed webhook requests must preserve exact raw bytes for Stripe
signature verification. B2A1 does not own duplicate-event handling, idempotency,
ignored-event behavior, refund/payment reconciliation, provider dashboard
configuration, Stripe event-size limits, endpoint registration, delivery
records, or live provider evidence.

Requests missing `Stripe-Signature` are intentionally not classified as signed
Stripe webhook requests by the limiter. They remain route-owned failures and
must not be used as proof of signed-webhook body-limit behavior.

### Content-Encoding And Media Type

For B2A1 limited classes, no request decompression is supported. Non-identity
`Content-Encoding` values, including comma-separated values containing any
non-identity token, are rejected before body processing. Empty values and
identity-only values do not trigger this rejection. Matching must be
case-insensitive and whitespace-tolerant.

B2A1 owns 415 `API.UNSUPPORTED_CONTENT_ENCODING` for non-identity
`Content-Encoding` on its two special classes.

WS02-05A owns explicit non-JSON `Content-Type` rejection,
`API.UNSUPPORTED_MEDIA_TYPE`, and JSON media-type behavior. B2A1 tests must not
tag those media-type behaviors as B2A1 evidence merely because the current
implementation shares middleware.

### Error And Middleware Integration

Application-owned B2A1 rejections use stable public error helpers inherited from
the WS02-04A and EN-02 error/observability foundation:

- oversized body: HTTP 413 with `API.REQUEST_BODY_TOO_LARGE`;
- unsupported content encoding: HTTP 415 with
  `API.UNSUPPORTED_CONTENT_ENCODING`;
- safe message and detail only;
- correlation ID in safe error output and response headers where applicable;
- compatible response-security, CORS, and host behavior according to middleware
  ownership;
- no echoing of request bodies, signatures, secrets, provider diagnostics,
  internal exceptions, paths, database URLs, or private headers.

`API.UNSUPPORTED_MEDIA_TYPE` is not B2A1 evidence.

### Settings

B2A1 owns:

- `PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES`
- `STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES`

The fields are typed backend settings with safe defaults and positive integer
parsing. `.env.example` documents the approved values. The ordinary JSON
setting and route metadata discovery are WS02-04B2A2C-owned current behavior,
not B2A1 closure.

## 5. Implementation Scope

### Current Implementation Surfaces

The B2A1 source contract is currently implemented through these source and
configuration surfaces:

- `backend/observability/request_body_limits.py`
- `backend/main.py`
- `backend/settings.py`
- `backend/.env.example`
- `backend/observability/http_errors.py`
- `backend/routes/platform_notice_routes.py`
- `backend/routes/stripe_webhook_routes.py`

These files are evidence targets for B2A1. They are not authorized Gate B edit
targets.

### Final Evidence Artifacts

Gate B must create exactly these B2A1 evidence artifacts:

1. `backend/tests/support/requirements/ws02_04b2a1.json`
2. `backend/tests/platform/request_body_limits/TESTING_RECORD.md`
3. `backend/tests/platform/request_body_limits/test_request_body_limit_asgi_contract.py`
4. `backend/tests/platform/request_body_limits/test_request_body_limit_route_selection.py`
5. `backend/tests/platform/request_body_limits/test_request_body_limit_error_contract.py`
6. `backend/tests/platform/request_body_limits/test_request_body_limit_settings_contract.py`

### Authorized Gate B Editable Set

Gate B may edit only the six evidence files listed above.

Production corrections: none approved.

Configuration corrections: none approved.

Governance corrections after the B2A1 owner-decision and limits-register
reconciliation: none approved.

If Gate B finds that current production or configuration contradicts this
frozen plan, it must return to Gate A rather than modify another file.

## 6. Testing And Evidence

The trusted test scope is `platform/request_body_limits` because B2A1 owns a
platform HTTP middleware contract rather than a product workflow service.

Expected proof layers:

| Requirement(s) | Proof Layer | Required Evidence |
|---|---|---|
| `WS02-04B2A1-R1`, `WS02-04B2A1-R7` | FastAPI/TestClient plus static route inventory | Actual Platform Notice create path is selected; nearby list/recipient/history/admin routes are not selected; rejection happens before handler/dependency body processing. |
| `WS02-04B2A1-R2`, `WS02-04B2A1-R7` | FastAPI/TestClient with provider and database fakes at application-owned seams | Signed webhook over-limit rejection precedes Stripe event construction and business mutation; accepted signed bodies preserve exact raw bytes; missing signature remains route-owned and does not become a signed-webhook limit proof. |
| `WS02-04B2A1-R3` | Direct ASGI harness around the middleware | Exact limit, limit-plus-one, missing length, misleading length, malformed/duplicate length, multi-message delivery, `more_body`, zero-byte messages, disconnect/non-HTTP pass-through, downstream read cutoff, and accepted-byte preservation. |
| `WS02-04B2A1-R4` | Direct ASGI harness plus TestClient where useful | Non-identity, case/whitespace, and comma-separated content-encoding behavior; no decompression; route outside all request-body-limited classes unaffected. |
| `WS02-04B2A1-R5` | FastAPI/TestClient | Stable public 413 and unsupported-content-encoding 415 payloads, safe detail, correlation/header behavior, compatible CORS/security headers, and no sensitive body/header/provider leakage. |
| `WS02-04B2A1-R6` | Settings pytest/static config review | Defaults, env var names, positive integer parsing, `.env.example` values, no duplicate B2A1 configuration owner, and ordinary JSON ownership separation. |
| `WS02-04B2A1-R8` | Requirement declaration, TESTING_RECORD, static repository review | Explicit deferred/non-closure state for ordinary JSON, media type, form/multipart, R2 object bytes, headers, URLs, ingress, process-server, provider, staging, runtime telemetry, and live Stripe evidence. |

No PostgreSQL proof is required for B2A1 if tests prove rejection occurs before
downstream application work and provider/database seams are faked at
application-owned boundaries. PostgreSQL-backed persistence remains owned by
WS02-04B1 and later workflow/payment passes.

No Playwright, browser, migration-history, genuine concurrency, controlled
time, live network, or live provider proof is required for B2A1.

### Evidence Quality Rules

Gate B tests must prove the safeguard that matters:

- size-boundary tests use controlled byte payloads rather than incidental JSON
  lengths;
- accepted-body tests prove exact downstream bytes, not only a successful
  response;
- rejected-body tests prove the relevant downstream read, provider call, or
  business mutation did not occur;
- `Content-Length` tests prove actual bytes still govern acceptance;
- Stripe fakes sit at the application-owned Stripe construction and webhook
  service seams, not inside the body-limit rule itself;
- static checks distinguish tracked source from provider/runtime claims;
- routes described as unaffected must be outside all currently applicable
  request-body-limited classes, not ordinary JSON routes owned by WS02-04B2A2C;
- no historical or legacy tests are evidence inputs;
- `API.UNSUPPORTED_MEDIA_TYPE` and explicit non-JSON `Content-Type` rejection
  are not B2A1 evidence.

## 7. Integration / Operational Expectations

B2A1 must remain compatible with:

- WS02-04B1 source-owned Platform Notice workflow boundaries;
- WS02-04B2A2C ordinary JSON body-limit ownership;
- WS02-05A JSON media-type ownership;
- WS02-04A stable public error contracts;
- WS02-03 host, CORS, response-security, and edge-boundary ownership;
- EN-02 safe observability/error metadata;
- WS05 payment/provider lifecycle and Stripe webhook idempotency/reconciliation
  ownership;
- WS09 future telemetry/dashboard/alert work;
- WS02-04B2B/B2C ingress, provider, process-server, permanent-host, and staging
  verification.

The B2A1 owner decision requires reassessment when source routes or schemas
change, provider/platform constraints change, a permanent host is selected,
workload or abuse signals appear, an incident occurs, boundary tests reveal
drift, telemetry reveals a limit problem, or a superseding owner decision
changes the approved values.

## 8. Not Part Of This Pass

B2A1 does not close:

- ordinary JSON request-body limits or schema bounds beyond the two B2A1
  special classes;
- explicit non-JSON `Content-Type` rejection, `API.UNSUPPORTED_MEDIA_TYPE`, or
  JSON media-type behavior;
- form, multipart, or FastAPI file-upload request consumers;
- direct R2 object byte limits or storage-provider upload behavior;
- headers, URLs, redirect precedence, proxy metadata, ingress limits, edge
  limits, process-server limits, permanent-hosting limits, or staging
  precedence;
- Stripe provider hard limits, dashboard settings, endpoint registration,
  event subscriptions, delivery records, API version, provider alerts, replay,
  idempotency, refund, dispute, reconciliation, or live provider proof;
- request timeouts, retries, cancellation, backpressure, rate limiting, worker
  concurrency, durable jobs, dashboards, alert thresholds, runtime telemetry, or
  launch-load evidence.

Current repository searches find no FastAPI `UploadFile`, `File`, `Form`, or
multipart consumers outside the excluded historical test tree. If such consumers
are introduced later, they require a new owner decision and evidence before
being claimed by any request-size pass.

## 9. Related Controls And Remaining Evidence

| Control / Pass | Relationship |
|---|---|
| `API-M09` | B2A1 advances request-body limits for two source-owned classes only; API-M09 remains partial. |
| `GOV-006` / `FDN-04` | Supplies the evidence-based method; the pass-specific B2A1 decision record supplies the approved numbers. |
| `WS02-04B1` | Owns source-owned product, collection, pagination, and selected Platform Notice recipient boundaries. |
| `WS02-04B2A2A/B1/B2/B3/C` | Own ordinary JSON schema bounds, ordinary JSON request-body limit activation, and related retained JSON classes. |
| `WS02-05A` | Owns explicit non-JSON `Content-Type` rejection, `API.UNSUPPORTED_MEDIA_TYPE`, and JSON media-type behavior. |
| `WS02-04A` | Owns stable public error shape used by B2A1 413 and unsupported-content-encoding 415 rejections. |
| `WS02-03` | Owns host, CORS, security-header, and edge-boundary behavior inherited by app-owned rejections. |
| `EN-02` | Owns safe observability, redaction, correlation, and public error descriptor foundations. |
| `WS05` | Owns broader Stripe/payment provider lifecycle, webhook idempotency, reconciliation, refunds, disputes, and provider evidence. |
| `WS02-04B2B/B2C` | Own hosting/ingress/process-server/provider alignment and permanent staging/precedence verification. |
| `WS09` | Owns production telemetry, dashboards, alerts, and operational observability closure. |

## 10. Completion Criteria

WS02-04B2A1 is complete when:

- the approved Platform Notice and signed Stripe webhook numeric values have
  durable owner authority in
  `docs/production-readiness/decisions/ws02-04b2a1-request-body-limits-approved.md`;
- the GOV-006 limits register records those values without presenting itself as
  the approving source;
- current source enforcement remains correct for the two B2A1 special classes;
- `backend/tests/support/requirements/ws02_04b2a1.json` declares R1-R8 with the
  exact metadata in this plan;
- `backend/tests/platform/request_body_limits/TESTING_RECORD.md` explains the
  selected scenarios, risks, proof layers, evidence limits, and handoffs;
- trusted tests under `backend/tests/platform/request_body_limits/` cover R1
  through R7 without relying on historical or legacy tests;
- R8 remains explicit deferred/non-executable evidence rather than fake pytest
  closure;
- checker file/domain scope passes for the new trusted scope;
- checker suite scope passes;
- requirement traceability is complete and truthful;
- B2A1 trusted tests pass without PostgreSQL, Playwright, live provider access,
  external network, migration proof, concurrency proof, controlled time, or
  invented provider evidence;
- JSON media-type and ordinary JSON behavior are not tagged as B2A1 evidence;
- final review confirms no unrelated files, secrets, provider-private data, or
  later-pass responsibilities were introduced.
