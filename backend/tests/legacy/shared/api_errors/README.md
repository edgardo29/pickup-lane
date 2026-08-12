# API Error Contract Shared Tests

Owner: Shared backend API error contracts and FastAPI exception handling

Affected pages/features:

- All backend API routes that return application-owned JSON error responses.
- Authentication, authorization, validation, not-found, method, conflict, and
  unexpected-error paths.
- Frontend API compatibility that still depends on top-level `detail`.

Rules covered here:

- Application-owned errors include the EN-02 public error descriptor fields.
- Top-level `detail` remains present for frontend compatibility.
- Request validation details preserve safe field locations while removing
  submitted values and unsafe context.
- Unhandled exceptions never return raw exception, database, provider, or stack
  information.
- Error responses preserve correlation IDs and the `X-Request-ID` response
  header.
- Existing CORS, security-header, Host, health, docs, webhook raw-body, redirect,
  static/file, and no-content behavior remains outside the JSON error envelope
  where appropriate.

This folder does not implement request-size limits, pagination limits,
timeouts, cancellation budgets, provider retry policy, rate limits, proxy trust,
or hosting-edge error precedence.
