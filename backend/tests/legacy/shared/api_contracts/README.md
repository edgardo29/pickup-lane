# API Contract Shared Tests

Owner: Source-owned HTTP, OpenAPI, cache, media-type, pagination, and rolling
compatibility contract foundations.

Covered boundaries:

- Ordinary JSON request-body routes reject explicitly non-JSON media types with
  a stable 415 envelope while preserving missing `Content-Type` compatibility.
- Framework-owned 405 responses keep the stable public error envelope and
  `Allow` header behavior.
- Authenticated and admin JSON responses use the private no-store cache policy
  when route ownership is known, while public JSON remains conservatively
  no-store.
- Generated OpenAPI includes shared stable error schemas, bodyless deprecated
  tombstones, important runtime statuses, and correct request-body media
  ownership.
- Current collection-route pagination contracts are inventoried, with known
  unbounded or compatibility-sensitive collection routes handed off instead of
  receiving invented numeric limits.

This folder does not own request-schema tightening, response minimization,
public/admin/internal response redesign, API versioning, CDN caching,
permanent hosting-edge behavior, migrations, provider configuration, or
frontend rewrites.
