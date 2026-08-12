# HTTP Security Shared Tests

Owner: Proxy, host, CORS, and FastAPI-owned response-header contracts.

Affected areas:

- Typed backend host and CORS settings.
- Application Host validation.
- FastAPI-owned response security headers.
- API documentation response protections.
- Health and diagnostic response boundaries.

Rules covered here:

- Application source validates only configured Host names and does not trust
  forwarded host values.
- CORS remains exact-origin and credential-aware without allowing wildcard,
  suffix, prefix, path, case-confusion, lookalike, or null-origin bypasses.
- FastAPI-owned JSON, health, error, documentation, and schema responses carry
  the source-owned security headers for their response class.
- Source-only controls do not implement TLS, HSTS, canonical redirects, trusted
  proxy expansion, frontend edge headers, or provider direct-origin policy.

Provider, DNS, TLS, CDN, Render, Vercel, and direct-origin behavior require
external evidence and staging response captures.
