# EN-02 Correlation, Event-Envelope, And Redaction Contract

Status: implemented foundation, ready for review

Branch: `pr/EN-02`

Baseline: `c1d68518c606f5b704b02bd9639fb76189c07a82`

Controls: API-M15, OPS-010

## Scope

EN-02 creates the narrow shared foundation for correlation identifiers,
isolated request/event context, safe event-envelope fields, redaction,
telemetry-label validation, and public error descriptors.

EN-02 does not implement full observability. It does not add middleware,
structured access logs, metrics, dashboards, tracing, aggregation, provider
integrations, route-by-route error conversion, migrations, or production
configuration.

## Identifier Rules

Server-generated correlation identifiers are canonical UUIDv4 strings.

Accepted identifiers must:

- be strings
- be exactly canonical lowercase UUIDv4 text
- have no padding
- have no control characters
- parse back to the same canonical string

Incoming identifiers are untrusted input. EN-02 does not accept arbitrary
external request-ID formats because the approved decisions do not define a
broader safe format. A later middleware pass may decide whether a trusted edge,
client, or provider can supply compatible IDs.

Correlation identifiers must not be derived from email addresses, user IDs,
payment IDs, booking IDs, provider event IDs, object keys, URLs, idempotency
keys, or free text. A UUID-shaped external value is still only a syntactic
correlation candidate; code must not intentionally reuse domain IDs as
correlation IDs.

## Context Lifecycle

Backend correlation context uses `contextvars`.

Required lifecycle:

- set a validated correlation ID
- read the current correlation ID
- reset using the returned token
- nested context restores the prior value
- async tasks keep independent values
- completed requests or tasks reset context
- missing context returns `None`
- no global mutable request object is used

EN-02 does not wire this into FastAPI middleware. Future request middleware must
set context at request entry, reset it in a `finally` path, and include the safe
request/correlation ID in public error envelopes and structured access logs.

## Event Envelope

The shared event envelope contains bounded operational metadata only.

Supported fields:

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

Event names and enum-like fields must be bounded code tokens. They are not raw
route paths, route parameters, exception messages, provider payload fields, or
free-form text.

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

Release and deployment identity wiring remains deferred. A future release pass
must connect immutable source revision, deployment artifact identity,
environment, migration/schema reference, and CI evidence.

## Telemetry Labels

Metric and telemetry labels are only for bounded low-cardinality values.

Approved label names:

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

Prohibited label names include:

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

Label values must be bounded code tokens or approved environment values.
Approved environment values are `ci`, `development`, `local`, `preview`,
`production`, `staging`, and `test`. Values that look like UUIDs, provider IDs,
emails, phone numbers, URLs, object keys, exception messages, or free text are
rejected.

## Redaction Rules

Redaction uses one marker: `[REDACTED]`.

The redaction primitive:

- does not mutate the original object
- preserves mapping and sequence shape where practical
- handles nested dictionaries and lists
- treats keys case-insensitively
- handles unexpected objects without using unsafe `repr`
- handles recursive structures safely

At minimum, redaction protects:

- Authorization headers
- Cookie and Set-Cookie headers
- access, refresh, and ID tokens
- API keys
- passwords
- secrets and private keys
- client secrets
- database URLs
- Stripe signatures
- Stripe client secrets
- Firebase credentials
- R2 credentials
- signed URLs and presigned URLs
- recovery codes
- email addresses
- phone numbers
- names
- street addresses
- guest contact information
- message bodies
- admin free text
- user-generated content
- raw webhook payloads
- card fingerprints
- storage object keys
- sensitive URL query parameters
- stack traces, SQL/database errors, and raw exception strings

## Public Error Information

The shared public error descriptor may expose:

- stable machine error code
- safe public message
- correlation ID
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

EN-02 does not replace existing route exceptions. Future API error-envelope work
must adopt these primitives route-by-route or through a carefully reviewed
middleware/exception-handler pass.

## Domain Correlation Expectations

HTTP requests:

- use a safe request/correlation ID
- propagate it to safe errors and structured logs in a later middleware pass

Durable jobs:

- require stable job ID, attempt ID, and originating request or event reference
- deferred until durable job schema and worker deployment exist

Payments and refunds:

- use internal payment, booking, refund, credit, or money-issue IDs as
  diagnostic context, not telemetry labels
- provider identifiers are redacted or access-controlled and used only where
  operationally necessary
- raw provider payloads remain outside event envelopes

Storage:

- use internal image/object record ID and non-sensitive storage context
- full signed URLs and object keys are prohibited from telemetry labels
- storage lifecycle behavior remains deferred

Admin actions:

- use admin action or audit record ID plus request correlation
- admin notes, reasons, and free-text metadata are not labels

Release:

- use environment and immutable release identity when available
- full source/deployment evidence wiring remains deferred

## Deferred Fields And Systems

EN-02 deliberately defers:

- FastAPI request middleware
- global exception handlers
- structured access logging
- log aggregation
- metrics exporters
- dashboards
- alerting
- distributed tracing
- provider-specific telemetry integrations
- CI artifact and release identity wiring
- durable job schema fields
- payment/refund schema changes
- storage lifecycle changes
- admin audit schema changes
- notification schema changes
- route-by-route safe error conversion

## Control Mapping

API-M15 is partially satisfied by shared request/correlation ID validation,
context isolation, safe envelope restrictions, redaction primitives, and tests.
It is not fully closed because runtime middleware, access logs, route-template
logging, and runtime evidence do not exist yet.

OPS-010 is partially satisfied by the implemented bounded telemetry-label
contract, prohibited-label rules, redaction requirements, and context
foundation. It is not fully closed because metrics, dashboards, tracing
posture, provider samples, and production runtime evidence do not exist yet.

FDN-07 remains the approved decision source. EN-02 implements its early shared
foundation but does not claim logs, metrics, dashboards, tracing, or runtime
correlation are complete.
