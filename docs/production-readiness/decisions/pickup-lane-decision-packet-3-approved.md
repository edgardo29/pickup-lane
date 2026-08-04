# Pickup Lane Decision Packet 3: Approved Record

## Status

**APPROVED**

Approval date: August 3, 2026

This record locks four decisions covering database capacity, financial state modeling, venue-image processing, and Cloudflare R2 lifecycle management.

It records product, policy, and architecture direction only. It does not claim implementation, tests, provider configuration, runtime evidence, migration completion, or production readiness.

## Approved decisions

### DBP-01 / DB-002: Deployment-wide PostgreSQL connection budget

Approved direction:

- Pickup Lane will maintain one deployment-wide PostgreSQL connection budget.
- The budget must include API instances, process workers, per-process pools, overflow, background workers, migrations, monitoring, autoscaling, rolling-deployment overlap, and operational reserve.
- Pool growth and connection wait behavior must be bounded.
- The application may not independently size every service without accounting for the deployment-wide maximum.
- Exact numeric values will be selected only after the PostgreSQL provider limit and deployment topology are confirmed.
- The final values require boundary testing, telemetry, and safe-adjustment behavior under the approved limits method.

Still requires later technical design:

- provider connection limit
- deployment instance and worker topology
- pool size and overflow values
- connection wait timeout
- rolling-deployment reserve
- monitoring and alert signals
- whether a connection pooler is justified

### DBP-02 / PAY-007: Canonical payment, booking, refund, and compensation states

Approved direction:

- Pickup Lane will use separate but coordinated state machines for payment, booking, refund, and compensation behavior.
- Stripe is authoritative for provider payment outcomes.
- Pickup Lane is authoritative for booking, participation, capacity, and application compensation outcomes.
- The frontend is not the final authority for payment completion.
- Signed Stripe webhooks and server-side reconciliation determine final financial state.
- State transitions must be explicit, validated, idempotent, auditable, and safe under duplicate, delayed, or out-of-order events.
- A successful payment with a capacity conflict must be represented truthfully and trigger an explicit compensation or refund path rather than being mislabeled as a failed payment.

Still requires later technical design:

- exact states and enum names
- transition matrix
- reservation duration and expiry behavior
- database constraints
- webhook event mapping
- worker and reconciliation behavior
- refund initiation and completion rules
- user-facing status language

### DBP-03 / STO-006: Image-upload scope and admin venue-image processing

Approved direction:

- Players cannot upload profile images or other images.
- Community hosts cannot upload images.
- Player avatars use generated initials only.
- No preset-avatar feature is included in current production-readiness implementation.
- Only active administrators may upload and manage venue images.
- Admin-uploaded venue images must be treated as untrusted files despite the trusted role.
- Venue images must be validated by actual file content, processed within bounded resource limits, stripped of unnecessary metadata, re-encoded into approved formats, and converted into controlled display derivatives before publication.
- Venue-image upload, replacement, publication, and removal actions require admin audit records.
- Any future user-upload feature requires a new product, moderation, privacy, and security decision.

Still requires later technical design:

- allowed image formats
- file-size and pixel-dimension limits
- processing library and isolation model
- derivative sizes and quality settings
- temporary upload state
- failure states
- exact admin authorization and audit fields

### DBP-04 / STO-009: Venue-image lifecycle, deletion, recovery, monitoring, and R2 controls

Approved direction:

- Admin-controlled venue images follow a documented Cloudflare R2 lifecycle.
- Replaced or deleted images are removed from public application use immediately.
- Database state must record replacement or deletion before permanent cleanup.
- Cached copies must be invalidated or allowed to expire through a documented strategy.
- A limited recovery period may be used where justified; permanent deletion follows through controlled cleanup.
- Temporary originals remain private.
- Public application pages use sanitized derivatives.
- Temporary originals are deleted after successful processing unless an approved recovery reason justifies retention.
- The system must detect and handle abandoned uploads, failed processing, missing objects, orphaned objects, failed deletions, and storage usage approaching provider limits.
- Venue-image loss must not break the venue or game record; the application falls back to a default venue presentation and permits admin replacement.
- Exact lifecycle, retention, monitoring, cache, recovery, and provider-control values require later evidence and testing.

Still requires later technical design:

- deletion recovery period
- abandoned-upload expiry
- original-retention rule
- R2 lifecycle-rule values
- cache invalidation and TTL design
- reconciliation job design
- usage and failure alerts
- versioning or recovery settings
- provider token scope and CORS settings

## Approval impact

Decision count after this approval:

- Total owner-decision register entries: **27**
- Approved: **16**
- Open: **11**

Previously approved decisions remain unchanged:

- FDN-01 through FDN-07
- IDB-01 through IDB-05

Newly approved decisions:

- DBP-01 through DBP-04

## Supersession rule

A later change to any decision in this record requires a new superseding decision record. This approved record remains preserved.

## Implementation restriction

This approval does not authorize application code changes, Git branch changes, worktree creation, provider configuration, deployment changes, migrations, worker changes, storage mutations, or CI changes.
