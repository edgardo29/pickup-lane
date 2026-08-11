# EN-02 - Safe Observability Privacy Foundation

## 1. Purpose

EN-02 establishes the backend foundation for recording and connecting
operational information safely. When a request fails, a job times out, or a
diagnostic event is emitted, the backend needs enough context for developers and
operators to understand what happened without exposing secrets, personal data,
provider payloads, payment data, object keys, or uncontrolled free text.

This pass provides safe primitives for six common needs:

- identifying one request or operation while debugging
- keeping that identifier isolated to the current request/task
- recording small structured operational events
- removing sensitive material before diagnostic use
- returning safe client-facing error information
- attaching bounded labels to telemetry

The core idea is simple: diagnostic data should be useful, but it must be
bounded, privacy-safe, and hard to corrupt after validation. EN-02 therefore
defines exact contracts for correlation IDs, correlation context, event
envelopes, redaction, public error descriptors, and telemetry labels.

EN-02 is not a full observability rollout. It does not add request middleware,
structured access logging, metrics exporters, dashboards, alerts, SLOs, tracing,
provider telemetry integrations, retention systems, route-by-route error
conversion, CI/release gates, schema changes, or production runtime evidence.
Those later systems may consume EN-02 primitives, but they are not completed by
this pass.

## 2. Why This Matters

Observability and error handling are easy places to leak information because
they sit near failures, provider responses, request bodies, and exception text.
EN-02 protects against practical backend failure modes such as:

- an authorization token, cookie, API key, signed URL, database URL, or provider
  credential appearing in logs or diagnostics
- one request inheriting another request's correlation ID because context was
  stored globally or not reset on failure
- a provider response, database error, stack trace, or raw `str(exc)` being sent
  back to a client
- a metadata dictionary being validated once and later mutated to contain an
  email address, token, object key, raw route parameter, or free-form message
- user IDs, booking IDs, payment IDs, provider event IDs, or correlation IDs
  being used as metric labels and creating unbounded/high-cardinality telemetry
- free-form route paths, messages, exception strings, or provider payload fields
  entering event metadata where only bounded operational tokens are allowed

The security and reliability rule is that diagnostic context must be safe at
the moment it is accepted and must remain safe after that. Defensive copying and
immutable validated storage are part of the contract because otherwise a caller
could pass validation, keep a reference to the original object, and later insert
unsafe data.

## 3. Requirements

Primary authoritative controls are API-M15 and OPS-010. FDN-07 is the decision
source for this early shared foundation. ADM-006, OPS-008, and API-M12 are
supporting nearby controls where admin/operations boundaries and public error
semantics intersect this pass.

| ID | Requirement | What it means | Why it matters |
|---|---|---|---|
| `EN02-CORR-001` | Safe UUIDv4 correlation ID generation and validation. | The backend generates canonical UUIDv4 IDs and accepts only canonical UUIDv4 caller IDs. Missing IDs are replaced; unsafe IDs are rejected. | Debugging can connect related diagnostics without reusing user, payment, provider, URL, object-key, or secret-derived identifiers. |
| `EN02-CORR-002` | Context-local correlation lifecycle. | The current correlation ID is stored in request/task-local context, can be set/read/reset, restores nested values, and is cleaned up after failures. | One request or async task must not leak its identifier into another operation. |
| `EN02-EVENT-001` | Bounded privacy-safe event envelope. | Operational events contain a small approved set of metadata fields, validated labels, and immutable validated state. | Events remain useful for diagnostics without carrying raw payloads, exception details, personal data, secrets, or mutable unsafe metadata. |
| `EN02-REDACT-001` | Recursive non-mutating sensitive-data redaction. | Redaction returns a sanitized copy, walks nested structures, recognizes sensitive key/value variants, and preserves safe shape where practical. | Diagnostics can remove secrets and private data without damaging the caller's original object or erasing safe structural context. |
| `EN02-PUBLIC-001` | Safe public error descriptor. | Client-facing errors expose only stable codes, safe messages, safe correlation IDs, and optional validated safe details. | Internal exception/provider/database/configuration information must not leak to clients. |
| `EN02-TEL-001` | Bounded privacy-safe telemetry labels. | Telemetry labels use only approved low-cardinality names and bounded values; validated mappings are immutable. | Monitoring systems must not receive personal identifiers, free text, URLs, object keys, provider IDs, or per-request values as labels. |
| `EN02-SCOPE-001` | Explicit later-scope boundaries. | EN-02 documents what it does not implement and keeps later observability work separate. | The foundation should not be mistaken for a complete logging, metrics, tracing, release, or runtime evidence program. |

## 4. Technical Design / Contracts

### 4.1 Correlation IDs

A correlation ID is a safe random identifier used to follow one request or
operation through backend diagnostics. It is deliberately not a user ID, booking
ID, payment ID, provider event ID, object key, URL, idempotency key, email
address, or secret-derived value.

Server-generated correlation IDs are canonical UUIDv4 strings. UUIDv4 gives the
backend a random identifier that is useful for diagnostics without encoding
domain meaning or private data.

Accepted correlation IDs must:

- be strings
- be exactly canonical lowercase UUIDv4 text
- be 36 characters long
- have no padding
- have no control characters
- parse back to the same canonical string
- be UUID version 4

Incoming request IDs are untrusted input. Missing or empty incoming values are
replaced with generated server-owned UUIDv4 values. Malformed, non-v4,
uppercase, padded, control-containing, or domain/provider-shaped values are
rejected.

These restrictions exist so that correlation can support debugging without
becoming an accidental channel for user data, provider identifiers, secrets,
free text, object keys, or arbitrary external request-ID formats.

### 4.2 Correlation Context Lifecycle

Correlation context is how backend code knows "which request or operation am I
currently handling?" without passing the correlation ID through every function
argument. EN-02 uses Python `ContextVar` storage because it is local to the
current execution context and preserves isolation across async tasks better than
global variables.

The lifecycle contract is:

- set only a validated correlation ID
- read the current correlation ID
- reset using the token returned by the set operation
- restore the prior value after nested context
- preserve independent values across async tasks
- reset through failure/finally paths
- return `None` when no context is set
- avoid global mutable request objects

Future request middleware must set context at request entry, reset it in a
`finally` path, and pass only the safe correlation ID into public errors and
structured diagnostics.

### 4.3 Event Envelope

An event envelope is a small structured record describing what happened
operationally. It is not the underlying request body, response body, provider
payload, exception, or message text. Its job is to provide bounded metadata that
can be logged or passed to later observability systems safely.

Supported fields are:

- schema version
- event name
- occurred-at timestamp
- environment
- release identity
- source identity
- correlation ID
- request ID when distinct
- actor kind
- operation
- resource kind
- result
- stable error code
- provider kind
- approved low-cardinality labels

The current schema version is `1`.

Event names and enum-like fields are bounded code tokens. Timestamps must be
timezone-aware. Correlation and request IDs must satisfy the EN-02 correlation
contract. Label mappings are validated, defensively copied, and stored as
immutable mappings so callers cannot add unsafe labels after construction.

Event-envelope serialization returns plain JSON-safe structures while
preserving the immutable validated internals. Callers can serialize the
envelope without receiving direct access to mutable validated state.

Event envelopes must not contain:

- raw request bodies
- raw response bodies
- raw webhook payloads
- arbitrary provider responses
- exception objects
- stack traces
- raw `str(exc)` output
- tokens, cookies, passwords, client secrets, or private keys
- signed URLs
- private-message bodies
- personal data
- card data
- object keys
- arbitrary telemetry labels
- free-form text

### 4.4 Redaction

Redaction replaces sensitive information with a single marker before diagnostic
use. It is a safety primitive for logs, error context, test artifacts, and other
places where structured data may be inspected.

Redaction uses one marker:

```text
[REDACTED]
```

The redaction primitive:

- returns a redacted copy without mutating the input
- preserves mapping and sequence shape where practical
- handles nested dictionaries, lists, and tuples
- handles recursive structures safely
- treats key spellings case-insensitively after normalization
- recognizes equivalent hyphen, underscore, and camel-case sensitive keys
- handles unexpected objects without using unsafe `repr`
- preserves safe structural metadata when not otherwise sensitive

Protected categories include:

Credentials and secrets:

- Authorization and Proxy-Authorization headers
- Cookie and Set-Cookie headers
- x-api-key and x_api_key spellings
- access, refresh, ID, bearer, and auth tokens
- API keys and API-secret style credential keys
- provider credential variants for Stripe, Firebase, Cloudflare, R2, and AWS
- passwords, secrets, private keys, and client secrets
- database URLs
- Stripe signatures and webhook secrets
- recovery codes

URLs and storage:

- signed URLs and presigned URLs
- sensitive URL query parameters
- storage object keys

Personal and payment-related data:

- email addresses
- phone numbers
- names and guest contact information
- street addresses
- card fingerprints

Free-form and internal diagnostic data:

- message bodies
- admin free text
- user-generated content
- raw webhook payloads
- stack traces
- SQL/database errors
- raw exception strings

EN-02 does not redact every identifier by default. Safe structural identifiers
that are not sensitive by key or value can remain available for bounded
diagnostic shape.

### 4.5 Public Errors

Internal error information is for developers and operators. Client-facing error
information is for users and API callers. EN-02 keeps those two categories
separate by defining a public error descriptor that can expose stable, safe
fields without leaking internal failure details.

The shared public error descriptor may expose:

- stable machine error code
- safe public message
- safe correlation ID
- optional safe details

It must not expose:

- exception objects
- stack traces
- SQL or database errors
- provider responses
- raw configuration errors
- internal file paths
- tokens or secrets
- raw `str(exc)` output by default
- sensitive detail keys
- unsafe nested detail values

Public error details are validated recursively, defensively copied, and stored
immutably, including nested mappings and sequences. Serialization returns plain
JSON-safe dictionaries and lists for accepted consumers rather than leaking
mapping proxies, tuples, or mutable internal state.

EN-02 does not replace existing route exceptions or implement broad API error
normalization. Future API error-envelope work must adopt these primitives
route-by-route or through a carefully reviewed middleware/exception-handler
pass.

### 4.6 Telemetry Labels

Telemetry labels are name/value attributes attached to metrics or operational
signals so monitoring systems can group and filter data. Labels must be low
cardinality: they should come from a small predictable set of values, not from a
unique value per user, request, payment, booking, provider event, object, URL, or
exception.

Approved label names are:

- `actor_kind`
- `environment`
- `error_code`
- `job_type`
- `operation`
- `outcome`
- `provider_kind`
- `resource_kind`
- `result`
- `route_template`

Approved environment values are:

- `ci`
- `development`
- `local`
- `preview`
- `production`
- `staging`
- `test`

Prohibited labels and values include:

- request IDs
- correlation IDs
- user IDs
- payment IDs
- booking IDs
- provider event IDs
- idempotency keys
- email addresses
- phone numbers
- URLs
- object keys
- exception messages
- free-form text
- raw route parameters
- UUID-shaped identifiers
- provider-shaped identifiers
- values containing sensitive text

Validated label mappings are deterministic, defensively copied, and immutable
after validation. Callers that need serialization can convert the mapping to a
plain dictionary at the edge.

## 5. Implementation Scope

EN-02 owns the production primitives that enforce the contracts above. The
implementation provides:

- correlation ID generation, validation, set/read/reset, context manager
  cleanup, and async-safe request/task-local behavior
- event-envelope validation and serialization for bounded operational metadata
- redaction helpers for sensitive fields and sensitive text
- public error descriptors for safe client-facing error information
- telemetry-label validation for bounded low-cardinality labels

Required production behavior includes:

- immutable event/telemetry labels: `EventEnvelope.labels` and
  `validate_telemetry_labels(...)` store validated mappings immutably after
  defensive copying
- immutable public-error details: `PublicErrorDescriptor.details` stores
  validated details immutably, including nested mappings and sequences, while
  preserving plain JSON serialization
- stronger sensitive-key normalization/redaction: redaction recognizes audited
  authorization, proxy-authorization/proxy_authorization, x-api-key/x_api_key,
  API-key style, and provider credential variants without redacting every safe
  identifier

Correlation behavior already matches the EN-02 contract and does not require a
broad rewrite. It remains responsible for canonical UUIDv4 generation,
canonical validation, invalid caller ID rejection, replacement of missing IDs,
ContextVar set/read/reset, reset-token behavior, and context-manager cleanup.

Relevant production modules and concepts include:

- `backend.observability.correlation`
- `backend.observability.events`
- `backend.observability.redaction`
- `backend.observability.errors`
- `backend.observability.telemetry`
- timeout/public-error consumers that use these primitives through safe mapping
  and serialization behavior

## 6. Testing And Evidence

EN-02 evidence follows the EN-01 testing architecture:

```text
authoritative requirement
-> invariant / risk
-> meaningful scenario / edge case
-> trusted pytest test
-> generated traceability
```

Trusted EN-02 tests live in:

```text
backend/tests/platform/observability/
```

This scope is correct because EN-02 defines global backend/platform/security
behavior rather than a domain, workflow, migration, provider, or page/API
feature.

Requirement declarations live in:

```text
backend/tests/support/requirements/en02.json
```

The human testing/risk record lives in:

```text
backend/tests/platform/observability/TESTING_RECORD.md
```

The declaration file stores stable requirement identity, owning pass, source
controls, current machine-readable state, and scope. It does not store product
specifications, scenario details, assertions, or exact pytest node IDs. Exact
current pytest references are generated from pytest collection and
`pytest.mark.requirement` metadata.

The trusted tests cover the important risk categories:

- safe correlation ID generation and rejection of unsafe incoming values
- ContextVar set/read/reset, nested restoration, failure cleanup, and async
  isolation
- event-envelope bounded fields, timestamp requirements, correlation
  association, safe serialization, unsafe label rejection, and post-validation
  immutability
- recursive, non-mutating redaction of sensitive keys and values while
  preserving safe structural metadata
- public error validation, nested immutable details, safe serialization, and
  internal-leak prevention
- telemetry label allowlists, prohibited high-cardinality/private values,
  route-template bounds, defensive copying, and immutable validated mappings

`EN02-SCOPE-001` is documented and reviewed rather than forced into a fake
runtime test. Its evidence is the canonical plan, the testing/risk record, and
diff review confirming that EN-02 did not absorb later-scope work.

## 7. Current Consumers / Integration Expectations

Later accepted code may consume EN-02 primitives, but it must preserve EN-02
boundaries. Current examples include:

- public error helper code that builds safe descriptors from existing exception
  flows
- timeout classification that uses bounded telemetry labels and public timeout
  details
- chat rate-limit diagnostics that serialize safe event envelopes
- settings validation that uses sensitive-text detection

These consumers must pass only validated and bounded metadata. They should
serialize through safe public methods and avoid raw payloads, secrets, provider
responses, route parameters, object keys, exception text, and free-form user or
admin text.

Future consumers must treat EN-02 primitives as foundation contracts, not as
permission to add broad observability systems inside this pass.

## 8. Not Part Of EN-02

This section exists to prevent scope creep. EN-02 deliberately excludes the
systems below even though later work may build on EN-02 primitives.

Runtime request/error integration:

- FastAPI request/correlation middleware
- global exception handlers
- route-by-route safe error conversion
- broad API error normalization
- production runtime evidence

Logging and observability rollout:

- structured access logging
- log aggregation
- metrics exporters
- dashboards
- alerting
- SLOs
- distributed tracing
- provider-specific telemetry integrations
- retention and audit-evidence systems

Release and platform gates:

- CI artifact gates
- release identity gates
- full source/deployment evidence wiring
- migration/schema reference wiring

Schema and domain changes:

- durable job schema fields
- payment/refund schema changes
- storage lifecycle changes
- admin audit schema changes
- notification schema changes

Release and deployment identity wiring remains deferred. A future release pass
must connect immutable source revision, deployment artifact identity,
environment, migration/schema reference, and CI evidence.

## 9. Related Controls And Remaining Evidence

| Control / Decision | What EN-02 establishes | What remains later |
|---|---|---|
| API-M15 | API-M15 is the primary API/error-safety control related to request correlation, safe public error information, and diagnostic boundaries. EN-02 advances it by establishing safe correlation IDs, isolated context, privacy-safe public error descriptors, safe event metadata, redaction primitives, trusted tests, and generated traceability. | Full closure still requires request middleware, access logs, route-template logging, route/error integration, and production runtime evidence proving the primitives are wired correctly. |
| OPS-010 | OPS-010 is the primary operations/observability control related to safe operational diagnostics. EN-02 advances it by defining bounded telemetry labels, prohibited label/value classes, post-validation immutability, redaction, context foundation, and trusted platform evidence. | Full closure still requires metrics exporters, dashboards, tracing posture/decisions, provider samples, retention, alerting, SLOs, and production runtime evidence. |
| FDN-07 | FDN-07 is the decision source for the approved early shared observability foundation. EN-02 implements that foundation: correlation, context, redaction, bounded event metadata, safe public descriptors, telemetry-label validation, and trusted evidence. | Complete logging, metrics, dashboards, tracing, runtime correlation rollout, and production operational evidence remain later work. |

Supporting relationships:

- API-M12 is relevant where public error semantics intersect API response
  behavior.
- ADM-006 is relevant where admin operational text and audit-like data must not
  become unsafe labels or public details.
- OPS-008 is relevant where operational evidence and diagnostics must remain
  bounded and safe.

## 10. Completion Criteria

EN-02 is complete when:

- all seven EN-02 requirements are accounted for
- required production primitives match the contracts in this document
- trusted EN-02 tests pass under `backend/tests/platform/observability/`
- EN-01 checker domain/subtree scope passes for the EN-02 trusted scope
- EN-01 checker suite scope remains consistent
- generated traceability maps executable EN-02 requirements to current pytest
  tests
- `EN02-SCOPE-001` is documented with supported non-executable evidence
- the EN-02 testing/risk record is complete
- no unresolved EN-02 blocker remains
- no sensitive data is introduced
- later-scope boundaries remain intact
- documentation matches implementation

Completion of EN-02 does not mean API-M15 or OPS-010 are fully closed. Later
runtime evidence and broader observability work remain outside this pass.
