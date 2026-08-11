# EN-02 Observability Foundation Testing Record

## Scope

This record covers the EN-02 platform observability foundation: correlation ID
generation and validation, correlation context lifecycle, safe event-envelope
metadata, redaction, public error descriptors, telemetry labels, and explicit
later-scope boundaries.

EN-02 is a pure platform/security primitive pass. It does not cover FastAPI
middleware wiring, route-by-route error conversion, structured logging rollout,
metrics exporters, dashboards, tracing, provider observability, durable job
schema fields, CI/release gates, or production runtime evidence.

## Requirements And Risks

| Requirement | Authoritative Source | Invariant | Important Risk | Owning Layer | Current Evidence |
|---|---|---|---|---|---|
| `EN02-CORR-001` | API-M15, FDN-07 | Correlation IDs are server-safe canonical UUIDv4 values, and untrusted caller IDs are validated or replaced when absent. | Domain IDs, provider IDs, secrets, padded values, controls, or noncanonical UUIDs become trusted request correlation. | Pure platform unit/policy tests. | Covered by fresh correlation contract tests for generation, validation, unsafe forms, and untrusted input handling. |
| `EN02-CORR-002` | API-M15, FDN-07 | Correlation context is request/task local and restored through reset/finally behavior. | Correlation leaks across nested operations, failed paths, or concurrent async tasks. | Pure context/concurrency tests. | Covered by fresh ContextVar tests for set/get/reset, nested contexts, failure cleanup, and async isolation. |
| `EN02-EVENT-001` | API-M15, OPS-010 | Event envelopes contain only bounded metadata, serialize safely, and cannot be made unsafe after validation. | Raw payloads, free text, unsafe labels, mutable validated labels, or unsafe release data enters operational events. | Pure platform unit/policy tests. | Covered by fresh event-envelope tests for bounded fields, timestamps, correlation association, serialization, unsafe label rejection, defensive copying, and immutable labels. |
| `EN02-REDACT-001` | API-M15, OPS-010 | Redaction is recursive, non-mutating, shape-preserving where practical, and recognizes sensitive key/value variants. | Authorization, proxy authorization, x-api-key, provider credentials, signed URLs, database URLs, tokens, or unsafe object reprs leak into diagnostics. | Pure platform unit/policy tests. | Covered by fresh redaction tests for key normalization, embedded sensitive strings, nested mappings/sequences, recursion, unknown objects, non-mutation, and safe structural metadata. |
| `EN02-PUBLIC-001` | API-M15, API-M12, OPS-010 | Public error descriptors expose only stable safe fields and immutable validated details. | Exception objects, provider/DB internals, stack traces, sensitive keys, or post-validation nested mutation leak to clients. | Pure platform unit/policy tests. | Covered by fresh public-error tests for safe serialization, unsafe detail rejection, defensive copying, nested immutability, and unsafe top-level fields. |
| `EN02-TEL-001` | API-M15, OPS-010 | Telemetry labels use approved low-cardinality names and safe bounded values, and validated mappings are immutable. | User IDs, correlation IDs, provider IDs, email, phone, URLs, object keys, free text, or post-validation mutation enters labels. | Pure platform unit/policy tests. | Covered by fresh telemetry tests for approved labels, prohibited names/values, route-template bounds, redaction interaction, defensive copying, and immutable mappings. |
| `EN02-SCOPE-001` | FDN-07, ADM-006, OPS-008, OPS-010 | Later-scope observability and operational systems remain explicit deferrals. | EN-02 falsely claims middleware, logging, metrics, dashboards, tracing, provider monitoring, or release/runtime evidence. | Canonical plan and diff review. | Covered elsewhere by the canonical EN-02 planning document and final diff review; no product-runtime pytest node is appropriate. |

## Adequacy Conclusion

EN-02 is adequately tested for the foundational platform scope when the fresh
platform observability pytest suite passes, the checker domain and suite scopes
pass, generated traceability maps the six executable EN-02 requirements to
current pytest nodes, and the final diff review confirms no later-scope
observability rollout or sensitive material was introduced.
