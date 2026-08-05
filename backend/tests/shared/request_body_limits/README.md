# Request Body Limit Tests

These tests protect the WS02-04B2A1 portable request body boundary.

Covered boundaries:

- Platform Notice create-route request byte counting for the approved
  application body budget.
- Signed Stripe webhook request byte counting without changing raw webhook
  bytes, body-read timing, or route-owned signature behavior.
- Application-owned oversized-body and unsupported-content-encoding error
  responses.
- Regression coverage that the limiter is route-class scoped and does not
  create a global ordinary JSON request limit.

This folder uses direct ASGI calls for missing `Content-Length`, chunked body,
and misleading declared-length cases because `TestClient` cannot represent all
transport shapes that can reach an ASGI application.
