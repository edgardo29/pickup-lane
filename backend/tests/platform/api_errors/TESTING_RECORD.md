# WS02-04A Stable Backend Error Contracts Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS02-04A` |
| Trusted test scope | `backend/tests/platform/api_errors/` |
| Requirement declaration | `backend/tests/support/requirements/ws02_04a.json` |
| Authoritative sources | Canonical WS02-04A plan; `API-M12`; `API-M09`; `API-M10`; `API-M11`; `API-M13`; `API-M15`; `API-M19`; `OPS-010`; EN-02; WS02-02; WS02-03; WS02-05A |
| Evidence layers | Trusted platform pytest, FastAPI `TestClient`, direct handler/helper proof, static source review, governance deferral |

## 1. Scope

This record covers repository-owned backend API error contracts for
application-owned FastAPI errors. The scope includes public error envelope
shape, frontend-compatible top-level `detail`, validation and malformed JSON
sanitization, HTTPException status/code normalization, correlation behavior,
narrow HTTPException header preservation, unexpected-error and timeout
redaction, response ownership boundaries, and single-owner/bypass resistance.

This record does not cover provider-generated errors, edge/CDN/WAF error
bodies, deployed proxy precedence, public staging captures, production logging
samples, provider timeout payloads, or sanitized external evidence packages.
Those remain external or later evidence under `WS02-04A-R8`.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS02-04A-R1` | Application-owned JSON errors expose the stable public envelope and current frontend-compatible top-level `detail`. | pytest |
| `WS02-04A-R2` | Validation and malformed JSON failures return safe 422 envelopes without submitted private values or parser internals. | pytest |
| `WS02-04A-R3` | HTTPException, request-body, media-type, rate-limit, timeout, and fallback classes normalize to approved status/code behavior. | pytest |
| `WS02-04A-R4` | Correlation is canonical and only exact approved HTTPException status/header pairs are preserved. | pytest |
| `WS02-04A-R5` | Unexpected exceptions and public timeout errors do not expose raw exception, provider, SQL, path, cookie, signed URL, submitted private value, or object repr data. | pytest |
| `WS02-04A-R6` | Application-owned errors are distinguished from middleware, health, docs/OpenAPI, static, redirect, no-content, provider, and edge surfaces. | pytest/static |
| `WS02-04A-R7` | Canonical handlers/middleware remain the only source-owned error-envelope path with no duplicate owner or bypass path. | pytest/static |
| `WS02-04A-R8` | Provider, edge, deployed precedence, staging, provider timeout, and sanitized runtime evidence remain external. | deferred |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| `WS02-04A-R1` | Public JSON errors have required stable fields and safe descriptor semantics. | A response drops `detail`, omits `correlation_id`, or changes stable `code`. | Frontend breakage and poor operational correlation. | Central public-error response builder and EN-02 descriptor. | platform |
| `WS02-04A-R2` | Validation detail includes only bounded safe fields. | Submitted token, database URL, request body, or parser context appears in 422 output. | User/private data disclosure. | Validation-error sanitizer. | platform |
| `WS02-04A-R3` | Material status classes map to approved stable codes. | Framework defaults or route detail codes become unstable public contracts. | Client handling drift and false OpenAPI/runtime expectations. | HTTPException handler and source-owned request-body middleware. | platform |
| `WS02-04A-R4` | Correlation is owned by EN-02 and exception headers are allowlisted by exact status/header pair. | Caller-supplied exception headers leak cookies, redirects, CORS grants, cache policy, internal IDs, or fake request IDs. | Header injection, tracking confusion, and unsafe public response metadata. | HTTPException-header filter before public response construction. | platform |
| `WS02-04A-R5` | Fallback and timeout paths remain generic, bounded, and redacted. | Raw exception text, SQL/provider details, paths, tokens, cookies, or arbitrary reprs reach response or logs. | High-risk disclosure at failure time. | Unexpected-exception handler, timeout classifier, and EN-02 redaction. | platform |
| `WS02-04A-R6` | The error contract claims only surfaces Pickup Lane owns. | Tests normalize Host, docs, static, redirects, health, or provider/edge surfaces that belong elsewhere. | False production-readiness closure and broken middleware behavior. | Response ownership matrix and runtime/static boundary checks. | platform |
| `WS02-04A-R7` | One canonical owner controls error envelopes and correlation injection. | A route-local handler, alternate app factory, duplicate middleware, or helper bypasses sanitizer/correlation. | Drift and inconsistent public errors. | Static owner/bypass checks over current source. | platform |
| `WS02-04A-R8` | External evidence is not converted into fake local pytest claims. | Provider/deployed behavior is marked closed because local source tests pass. | False release confidence. | Deferred governance declaration and explicit testing-record boundary. | governance |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | Anonymous callers, authenticated dependency failures, framework/middleware, operators reviewing logs | grouped | Error contract is actor-neutral except auth status classes; representative classes cover the owned behavior. |
| States / lifecycle | 400, 401, 403, 404, 405, 409, 410, 413, 415, 422, 429, 500, 503, unknown HTTP status | covered/grouped | Status/code equivalence classes are tested without a route-by-route Cartesian explosion. |
| Actions | GET, POST, PATCH, body parsing, framework routing, handler/helper execution | covered | Runtime tests exercise framework behavior where material; direct helper proof covers lower-level owner behavior. |
| Inputs / boundaries | Missing/invalid/valid request IDs, unsafe validation values, malformed JSON, approved/rejected headers, wrong header/status pairs | covered | These are the material disclosure and correlation boundaries for WS02-04A. |
| Time | Timeout exception classes | covered without controlled time | No time-boundary calculation is implemented here; timeout classification uses explicit exception classes. |
| Dependencies | Database, providers, network, browser, live server | not applicable/deferred | The executable scope uses no PostgreSQL, migrations, external network, provider access, browser, subprocess, concurrency, controlled time, or live server proof. |
| Concurrency / idempotency | Request-local correlation cleanup | grouped | EN-02 owns broad async context proof; WS02-04A checks request cleanup/interoperation. |
| Authorization / privacy / security | Auth status codes, public redaction, sensitive headers, logs | covered | Synthetic sensitive sentinels make leakage checks meaningful. |
| Persistence / rollback | Not applicable | not applicable | WS02-04A does not mutate persistence. |
| Recovery | Unexpected failure and timeout response/log behavior | covered/deferred | Local fallback behavior is covered; production runtime evidence remains external. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | Missing request ID and missing optional details | pytest |
| empty | yes | Empty/missing correlation behavior is covered by generated request IDs; empty submitted values are not a distinct WS02-04A rule. | grouped |
| corrupt | yes | Malformed JSON, invalid request ID, unsafe detail/header values | pytest |
| exceed | yes | Request body over source-owned limit and too-long validation field | pytest |
| duplicate | yes | Duplicate/alternate owner and duplicate correlation-injector risk | static pytest |
| delay | yes | Public timeout exception classes | pytest |
| reorder | no | No ordered event or mutation sequence in this pass. | not applicable |
| interrupt | yes | Unexpected exception fallback | pytest |
| race | no | No PostgreSQL or concurrency contract in this pass. | not applicable |
| expire / revoke | no | No lifecycle expiry/revocation behavior in this pass. | not applicable |
| tamper | yes | HTTPException-provided headers and request IDs | pytest |
| retry | yes | `Retry-After` preservation only for source-approved 429 | pytest |
| recover | yes | Generic safe fallback and timeout-specific fallback | pytest |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| `WS02-04A-R1` | Public envelope and frontend compatibility | TestClient, direct helper, static frontend source | `test_public_error_envelope_contract.py` | Adequate for repository-owned response shape and current client expectations; no browser proof is needed for this backend contract. |
| `WS02-04A-R2` | Validation and malformed JSON sanitization | TestClient | `test_validation_and_malformed_json_contract.py` | Adequate for FastAPI/Pydantic validation surface and submitted-value exclusion. |
| `WS02-04A-R3` | Status/code normalization and source-owned 413/415 behavior | Direct handler and TestClient | `test_http_exception_status_contract.py` | Adequate for current equivalence classes; not every route is enumerated. |
| `WS02-04A-R4` | Correlation and exact HTTPException header filtering | TestClient and direct handler | `test_correlation_and_safe_headers_contract.py` | Adequate for the production correction and middleware interoperability; EN-02 owns deeper correlation primitives. |
| `WS02-04A-R5` | Unexpected error and timeout disclosure prevention | TestClient, direct handler, caplog | `test_unexpected_error_redaction_contract.py` | Adequate for repository-owned public/log behavior with synthetic sensitive sentinels. |
| `WS02-04A-R6`, `WS02-04A-R7` | Response ownership and single-owner/bypass resistance | TestClient and static source review | `test_error_boundary_static_contract.py` | Adequate for current source ownership; external provider/edge behavior remains outside pytest. |
| `WS02-04A-R8` | External provider/deployment evidence boundary | Governance/deferred | Canonical plan and requirement declaration | Local pytest cannot honestly prove this evidence. |

### Evidence Quality Checks

- Time-boundary quality: not applicable to executable WS02-04A tests; timeout
  proof uses explicit exception classes rather than wall-clock timing.
- Successful mutation effects: not applicable; WS02-04A has no persistence
  mutation.
- Rejected mutation side effects: not applicable; WS02-04A rejects response
  disclosure/header propagation rather than data mutations.
- Idempotency effects: not applicable; no persisted or external side effects.
- PostgreSQL concurrency: not applicable; the pass requires no database or race
  proof.
- External provider mocking: not applicable; provider behavior is not exercised
  or mocked as a fake proof.
- Database-constraint attribution: not applicable; no database constraints are
  under test.

## 7. Important Side Effects

WS02-04A has no database writes, provider calls, network calls, migrations, or
durable side effects. The important prohibited effects are public response and
log disclosure. Tests therefore assert rejected headers are not forwarded,
invalid request IDs are not reflected, and synthetic sensitive values do not
appear in public responses or captured logs.

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| `WS02-04A-R8` | deferred | Provider-generated errors, edge/CDN/WAF errors, deployed error/header precedence, public staging captures, provider timeout payloads, and sanitized provider/runtime evidence cannot be proven by local repository tests. | Provider/control-plane/runtime evidence packages and later WS/OPS work. |
| EN-02 correlation/redaction primitives | covered_elsewhere | WS02-04A consumes these primitives and tests integration; EN-02 owns primitive-level exhaustive proof. | `backend/tests/platform/observability/` |
| WS02-02 health/lifecycle behavior | covered_elsewhere | WS02-04A proves health responses are not public error envelopes; WS02-02 owns health semantics. | `backend/tests/platform/runtime/` |
| WS02-03 HTTP security/CORS behavior | covered_elsewhere | WS02-04A proves the exception-header filter does not strip outer middleware-owned headers; WS02-03 owns full policy. | `backend/tests/platform/http_security/` |
| WS02-05A OpenAPI/docs/cache compatibility | covered_elsewhere | WS02-04A checks relevant docs/OpenAPI boundaries and schema compatibility; full WS02-05A closure remains with that pass. | Later WS02-05A evidence |

## 9. Adequacy Conclusion

The selected evidence is adequate for the repository-owned WS02-04A scope when
the trusted `platform/api_errors` pytest scope passes, checker file/domain/suite
scopes pass, generated traceability maps `WS02-04A-R1` through `WS02-04A-R7` to
trusted pytest nodes, `WS02-04A-R8` remains deferred without pytest nodes, and
final review confirms no external provider/deployment evidence is falsely
claimed.

Checker `PASS` is structural compliance only. Human Gate C review must still
judge semantic adequacy, scope honesty, and whether the executable evidence
matches the frozen WS02-04A plan.
