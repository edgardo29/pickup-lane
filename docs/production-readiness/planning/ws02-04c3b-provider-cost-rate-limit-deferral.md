# WS02-04C3B Provider-Cost Rate Limit Deferral

Pass: WS02-04C3B

Status: evidence-deferred; no source implementation approved.

Scope: authenticated provider-cost and financial-action workflows considered
after C3A completed source-owned chat throttling.

## Decision

Do not implement additional source-owned application rate limits in C3B.

The inspected workflows may benefit from defense-in-depth throttling, but no
workflow has an evidence-backed maximum, window, scope, persistence rule,
failure policy, or retention rule sufficient to satisfy FDN-04. Existing domain
rows do not represent every attempted action for the C3B candidates, and moving
to a generic limiter table or Redis/shared limiter without approved values would
invent policy.

C3B therefore records the current decision only. No rate value, retry value,
setting, provider configuration, table, migration, or edge control is approved.

## FDN-04 Basis

Operational limits must be selected from evidence. Current code behavior,
storage capacity, existing provider object shape, or plausible abuse risk is
not enough to approve a numeric rate policy.

Future C3B implementation requires workflow-specific evidence for legitimate
frequency, legitimate short bursts, retry and recovery behavior,
false-positive tolerance, provider cost or quota impact, limiter scope/key,
cross-instance state, maximum/window, Retry-After behavior, failure policy,
storage and retention, telemetry, rollout, rollback, and reassessment trigger.

No numeric placeholders are approved by this record.

## Candidate Dispositions

| Candidate | Status | Current protections | C3B decision |
|---|---|---|---|
| Checkout payment-intent creation | EVIDENCE-DEPENDENT RATE-LIMIT CANDIDATE | Authenticated user, database locking, pending checkout reuse, payment-row and provider idempotency, capacity and state validation, frontend duplicate-submit prevention. | Rate limiting may reduce provider-cost abuse, but no defensible count/window currently exists. Do not implement a rate limit. |
| Saved-card setup | EVIDENCE-DEPENDENT RATE-LIMIT CANDIDATE | Authenticated user, saved-card product cap, frontend pending and duplicate-submit behavior, provider/customer ownership. | Repeated setup calls can create provider objects, making this a strong future candidate. Failed or pre-persistence attempts are not represented by durable local rows, so a strict future limiter may require dedicated shared limiter state. Do not introduce table/state until rate values and retention semantics are approved. |
| Saved-card sync | EVIDENCE-DEPENDENT RATE-LIMIT CANDIDATE | Authenticated user, provider ownership checks, provider reads, possible cleanup/default behavior, retry/reconcile ownership from C2. | Sync is recovery-sensitive. Legitimate re-sync after provider, browser, or local failure must remain possible, and a low blunt limit could damage recovery. Current rows do not represent every attempted sync. Do not implement a rate limit. |
| Community publish fee | EVIDENCE-DEPENDENT RATE-LIMIT CANDIDATE | Authenticated host, active paid-attempt uniqueness, host/date state ownership, provider/payment idempotency, frontend publishing state. | Broader provider-cost abuse is possible in theory, but no evidence-backed host rate exists. Do not implement a rate limit. |

## Explicit No Application Rate Limit Decisions

| Workflow | Current decision | Reason |
|---|---|---|
| Saved-card default | No additional source-owned C3B limiter. | Lifecycle and reconcile-before-retry semantics are more important than blunt throttling. |
| Saved-card detach | No additional source-owned C3B limiter. | Lifecycle and reconcile-before-retry semantics are more important than blunt throttling. |
| Venue-image upload authorization | No additional source-owned C3B limiter. | Presigning is local, and image count, type, and size rules already protect the product surface. |
| Venue-image completion | No additional source-owned C3B limiter. | Current lifecycle/idempotency plus R2 timeout behavior is the appropriate current control; repeated metadata-read abuse is not evidenced. |
| Waitlist payment or promotion | No additional source-owned C3B limiter. | This is an internal state-machine flow, not a direct user route. |
| Refund retry or reconcile | No additional source-owned C3B limiter. | Authorization, idempotency, state gates, row locks, confirmation, and reconciliation are primary; blunt throttling could block legitimate financial repair. |
| Game-credit issue or reverse | No additional source-owned C3B limiter. | Authorization, source ownership, state gates, row locks, confirmation, and reconciliation are primary; blunt throttling could block legitimate financial repair. |
| Admin financial repair | No additional source-owned C3B limiter. | Authorization, idempotency, state gates, row locks, confirmation, and reconciliation are primary; blunt throttling could block legitimate financial repair. |
| Official-game financial repair | No additional source-owned C3B limiter. | Authorization, idempotency, state gates, row locks, confirmation, and reconciliation are primary; blunt throttling could block legitimate financial repair. |
| Stripe webhook | No additional source-owned C3B limiter. | Body limit, signature verification, provider event dedupe, and provider redelivery are the current correct controls. |

## Reassessment Triggers

Reconsider C3B source-owned limits only when concrete evidence or architecture
change exists, including:

- observed provider-cost abuse
- repeated provider-object creation
- real production request-volume telemetry
- high repeated-attempt rates from authenticated users
- provider quota or cost pressure
- support incidents involving repeated action spam
- permanent hosting/runtime selection
- introduction of a shared durable limiter store for another justified workflow
- material workflow redesign
- provider SDK or API behavior changes

No time-based reassessment date is created by this record.

## Limiter-State And Migration Decision

No generic PostgreSQL rate-limit table is approved.

No Redis/shared limiter is approved.

No migration is required for the current C3B disposition.

Future dedicated limiter state must be justified by an approved workflow,
numeric policy, durable scope/key, failure policy, storage and retention rule,
telemetry plan, rollout plan, rollback plan, and cross-instance evidence before
implementation.

This record does not design a future schema.

## API-M11 Status

API-M11 remains partial.

Source-owned completed evidence includes:

- authenticated chat limiting
- cross-instance PostgreSQL chat serialization
- stable `API.RATE_LIMITED` 429 responses
- reliable chat `Retry-After`
- limiter failure behavior
- bounded limiter telemetry policy

Still open or evidence-deferred:

- provider-cost action rate values
- authenticated non-chat throttles where future evidence justifies them
- anonymous/public abuse controls
- trusted client-IP identity
- forwarded-header trust
- edge, WAF, provider-dashboard, and auth-provider rate controls
- permanent hosting/provider evidence
- runtime/load validation

## Source Impact

C3B is documentation/governance only. It requires no source implementation and
does not alter previously completed C1, C2, C3A, WS02-04A, or WS02-04B source
controls.
