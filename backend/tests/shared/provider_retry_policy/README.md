# Provider Retry Policy Tests

These tests are current non-legacy production-readiness evidence for WS02-04C2.

Owning rule area: provider retry ownership, provider mutation unknown-outcome
reconciliation, webhook redelivery ownership, and current sequential fanout
policy.

Affected features: Stripe checkout and saved payment methods, admin refund and
money repair, Stripe webhooks, Firebase account deletion, R2 venue-image
metadata verification, Platform Notice recipient creation, game chat,
Need-a-Sub chat, waitlist promotion, and account cleanup.

Page/API integration coverage lives in the relevant current page/API leaves and
the full non-legacy backend suite. Legacy tests remain historical evidence only.

They verify source-owned retry-safety classifications, dependency-owned provider
retry behavior, and backpressure/fanout boundaries without calling live Stripe,
Firebase, R2, email, or other providers.

This leaf does not approve retry counts, backoff values, worker concurrency,
leases, queues, schedulers, rate limiting, or provider retry configuration.
Those values remain outside WS02-04C2 unless a later pass approves them with
evidence.
