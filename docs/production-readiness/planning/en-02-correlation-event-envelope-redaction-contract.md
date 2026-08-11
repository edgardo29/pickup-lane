# EN-02 Correlation, Event-Envelope, And Redaction Contract

## Scope

EN-02 defines the shared backend platform foundation for privacy-safe
correlation, event metadata, redaction, public error descriptors, and telemetry
labels.

EN-02 owns these stable requirements:

| Requirement | Contract |
|---|---|
| `EN02-CORR-001` | Safe UUIDv4 correlation ID generation and validation. |
| `EN02-CORR-002` | Context-local correlation lifecycle with reset/isolation semantics. |
| `EN02-EVENT-001` | Bounded privacy-safe event envelope whose validated values cannot be made unsafe after construction. |
| `EN02-REDACT-001` | Recursive, non-mutating sensitive-data redaction. |
| `EN02-PUBLIC-001` | Privacy-safe public error descriptor. |
| `EN02-TEL-001` | Bounded privacy-safe telemetry labels. |
| `EN02-SCOPE-001` | Later-scope observability boundaries remain explicit and are not absorbed into EN-02. |

Primary controls are API-M15 and OPS-010. Supporting decisions and nearby
controls include FDN-07, ADM-006, OPS-008, and API-M12 where public error
semantics are relevant.

EN-02 does not implement full observability. It does not add FastAPI request
middleware, structured access logs, log aggregation, metrics exporters,
dashboards, alerting, SLOs, tracing, provider telemetry integrations, retention
systems, route-by-route error conversion, durable job schema fields, operational
CI/release gates, migrations, or production runtime evidence.

## Trusted Ownership And Evidence

EN-02 trusted tests live under:

```text
backend/tests/platform/observability/
```

That location owns EN-02 because these are global backend/platform/security
primitives rather than a domain, workflow, migration, provider, or page/API
behavior.

Requirement declarations live in:

```text
backend/tests/support/requirements/en02.json
```

The declarations store stable requirement identity, owning pass, source
controls, current machine-readable state, and scope. They do not store pytest
node IDs, product specifications, scenarios, or assertion text. Exact test
references are generated from pytest collection and `pytest.mark.requirement`
metadata.

The human testing/risk record lives in:

```text
backend/tests/platform/observability/TESTING_RECORD.md
```

`EN02-SCOPE-001` is documentation and diff-review evidence. It is declared with
a supported non-executable state because no product-runtime pytest node should
pretend to prove that later-scope work was not implemented.

## Risk Model

EN-02 protects against these foundational risks:

- Caller-supplied request IDs, domain IDs, provider IDs, or secrets becoming
  trusted correlation IDs.
- Correlation context leaking across nested operations, failed paths, or async
  tasks.
- Event envelopes carrying raw payloads, free text, object keys, provider
  payloads, exception text, personal data, credentials, or arbitrary labels.
- Validated event labels, telemetry labels, or public error details being
  mutated after validation.
- Redaction missing equivalent sensitive key spellings such as authorization,
  proxy authorization, x-api-key, API-key credentials, and provider credential
  variants.
- Public error descriptors exposing exception objects, stack traces, SQL/DB
  errors, provider responses, secrets, unsafe messages, or mutable details.
- Telemetry labels carrying high-cardinality or identifying values such as
  user IDs, payment IDs, booking IDs, provider event IDs, correlation IDs,
  idempotency keys, email addresses, phone numbers, URLs, object keys,
  exception messages, route parameters, or free text.
- EN-02 being misread as completion of later observability systems.

## Correlation Contract

Server-generated correlation IDs are canonical UUIDv4 strings.

Accepted correlation IDs must:

- be strings
- be exactly canonical lowercase UUIDv4 text
- be 36 characters long
- have no padding
- have no control characters
- parse back to the same canonical string
- be UUID version 4

Missing or empty incoming request IDs are replaced with generated server-owned
UUIDv4 values. Malformed, non-v4, uppercase, padded, control-containing, or
domain/provider-shaped values are rejected.

Correlation IDs must not be derived from email addresses, user IDs, payment
IDs, booking IDs, provider event IDs, object keys, URLs, idempotency keys, or
free text. A UUID-shaped external value is only a syntactic candidate; EN-02
does not create trust in arbitrary upstream identifiers.

## Context Lifecycle

Backend correlation context uses `contextvars`.

The lifecycle contract is:

- set only a validated correlation ID
- read the current correlation ID
- reset using the returned token
- restore the prior value after nested context
- preserve independent values across async tasks
- reset through failure/finally paths
- return `None` when no context is set
- avoid global mutable request objects

Future middleware must set context at request entry, reset it in a `finally`
path, and pass only the safe correlation ID into public errors and structured
diagnostics.

## Event Envelope Contract

The event envelope contains bounded operational metadata only.

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

Serialization returns plain JSON-safe structures while preserving the immutable
validated internals.

## Redaction Contract

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

At minimum, redaction protects:

- Authorization and Proxy-Authorization headers
- Cookie and Set-Cookie headers
- x-api-key and x_api_key spellings
- access, refresh, ID, bearer, and auth tokens
- API keys and API-secret style credential keys
- provider credential variants for Stripe, Firebase, Cloudflare, R2, and AWS
- passwords, secrets, private keys, and client secrets
- database URLs
- Stripe signatures and webhook secrets
- signed URLs, presigned URLs, and sensitive URL query parameters
- recovery codes
- email addresses
- phone numbers
- names and guest contact information
- street addresses
- message bodies, admin free text, and user-generated content
- raw webhook payloads
- card fingerprints
- storage object keys
- stack traces, SQL/database errors, and raw exception strings

EN-02 does not redact every identifier by default. Safe structural identifiers
that are not sensitive by key or value can remain available for bounded
diagnostic shape.

## Public Error Contract

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
JSON-safe dictionaries and lists for accepted consumers.

EN-02 does not replace existing route exceptions or implement broad API error
normalization. Future API error-envelope work must adopt these primitives
route-by-route or through a carefully reviewed middleware/exception-handler
pass.

## Telemetry Label Contract

Metric and telemetry labels are only for bounded low-cardinality values.

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

Approved environment values are `ci`, `development`, `local`, `preview`,
`production`, `staging`, and `test`.

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

## Current Production Corrections

The EN-02 implementation includes these scoped production corrections:

- `EventEnvelope.labels` and `validate_telemetry_labels(...)` now store
  validated mappings immutably after defensive copying.
- `PublicErrorDescriptor.details` now stores validated details immutably,
  including nested mappings and sequences, while preserving plain JSON
  serialization.
- Redaction key normalization now covers audited authorization,
  proxy-authorization/proxy_authorization, x-api-key/x_api_key, API-key style,
  and provider credential variants without redacting every safe identifier.

Correlation generation, validation, context set/read/reset, and context-manager
cleanup remain the established EN-02 behavior.

## Later Accepted Consumers

Later accepted code may consume EN-02 primitives, but EN-02 does not claim the
later systems as complete. Current consumers include:

- public error helper code that builds safe descriptors from existing exception
  flows
- timeout classification that uses bounded telemetry labels and public timeout
  details
- chat rate-limit diagnostics that serialize safe event envelopes
- settings validation that uses sensitive-text detection

These consumers must preserve EN-02 boundaries: pass only validated/bounded
metadata, serialize through safe public methods, and avoid raw payloads,
secrets, provider responses, route parameters, or free text.

## Explicit Later-Scope Boundaries

EN-02 deliberately defers:

- FastAPI request/correlation middleware
- global exception handlers
- structured access logging
- log aggregation
- metrics exporters
- dashboards
- alerting
- SLOs
- distributed tracing
- provider-specific telemetry integrations
- retention and audit-evidence systems
- CI artifact and release identity gates
- durable job schema fields
- payment/refund schema changes
- storage lifecycle changes
- admin audit schema changes
- notification schema changes
- route-by-route safe error conversion
- production operational evidence

Release and deployment identity wiring remains deferred. A future release pass
must connect immutable source revision, deployment artifact identity,
environment, migration/schema reference, and CI evidence.

## Control Mapping

API-M15 is partially satisfied by shared request/correlation ID validation,
ContextVar isolation, safe envelope restrictions, privacy-safe public error
descriptors, redaction primitives, and trusted tests. It is not fully closed
because runtime request middleware, access logs, route-template logging, broad
route error conversion, and production runtime evidence remain deferred.

OPS-010 is partially satisfied by the bounded telemetry-label contract,
prohibited-label rules, post-validation immutability, redaction requirements,
and context foundation. It is not fully closed because metrics, dashboards,
tracing posture, provider samples, retention, alerting, SLOs, and production
runtime evidence remain deferred.

FDN-07 remains the decision source for the early shared foundation. EN-02
implements only the foundation described here and does not claim complete logs,
metrics, dashboards, tracing, or runtime correlation rollout.
