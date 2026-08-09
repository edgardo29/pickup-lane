# Rate Limit Tests

These tests protect source-owned rate and abuse-control behavior for
production-readiness pass WS02-04C3A.

Covered boundaries:

- authenticated game chat visible-text message rate limits
- authenticated Need-a-Sub chat visible-text message rate limits
- PostgreSQL-backed sender/chat serialization
- stable `API.RATE_LIMITED` responses with reliable `Retry-After`
- fail-closed limiter behavior without adding generic limiter storage

C3A does not cover checkout, saved-card, upload authorization, anonymous/IP,
edge/WAF, CAPTCHA, or provider-dashboard limits.
