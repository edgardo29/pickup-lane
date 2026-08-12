# Request Body Limit Tests

These tests protect the WS02-04B2A1 portable request body boundary.

Covered boundaries:

- Ordinary JSON route request byte counting for retained FastAPI routes with
  request-body parameters.
- Platform Notice create-route request byte counting for the approved
  application body budget.
- Signed Stripe webhook request byte counting without changing raw webhook
  bytes, body-read timing, or route-owned signature behavior.
- Application-owned oversized-body and unsupported-content-encoding error
  responses.
- Regression coverage that bodyless routes, tombstones, WebSocket, and lifespan
  scopes remain outside request-body limiting.

This folder uses direct ASGI calls for missing `Content-Length`, chunked body,
and misleading declared-length cases because `TestClient` cannot represent all
transport shapes that can reach an ASGI application.
