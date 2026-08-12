# Observability Shared Tests

Owner: Shared observability, correlation, redaction, and safe-error contracts

Affected pages/features:

- Future API request middleware and safe error envelopes.
- Future structured request/event logging.
- Future provider, payment, storage, job, admin-action, and release evidence.

Rules covered here:

- Correlation identifiers are canonical server-generated UUIDv4 values.
- Request/event correlation context is isolated by `contextvars`.
- Structured event envelopes contain only bounded, privacy-safe metadata.
- Redaction protects nested sensitive values without mutating original inputs.
- Telemetry labels are limited to approved low-cardinality fields.
- Public error descriptors cannot serialize exceptions, stack traces, provider
  responses, database errors, tokens, or secrets.

This folder does not wire middleware, logging aggregation, metrics, tracing,
provider calls, or route-level error conversion.
