# WS02-04C3A Chat Rate Limit Contract

Pass: WS02-04C3A

Scope: portable, source-owned rate limiting for existing authenticated chat
message creation.

API-M11 remains partial after this pass. C3A protects the two active chat write
paths only; it does not select permanent anonymous, provider-cost, edge, or
public-IP controls.

## C3A And C3B Split

C3A owns:

- authenticated game chat visible-text message creation
- authenticated Need-a-Sub chat visible-text message creation
- stable 429 behavior for those chat limiters
- reliable `Retry-After` for those rolling-window decisions
- PostgreSQL-backed race safety for sender/chat limiter identity

C3B remains separate for authenticated provider-cost workflows that still need
numeric decisions, including checkout/payment-intent creation, saved-card
setup/sync, venue upload authorization, and any similar future provider-cost
action identified during inspection.

## Approved Product Rule

An authenticated sender may create at most 5 visible text messages per chat in a
rolling 60-second window.

The identity is:

- the authenticated internal user
- the chat identity
- the chat family, separating game chat from Need-a-Sub chat

The rule does not use IP address, forwarded headers, browser identity, route
parameters in public output, or provider metadata.

## PostgreSQL Ownership

Committed chat-message rows remain the authoritative shared limiter state.

The limiter does not add Redis, in-memory counters, a generic rate-limit table,
or a migration. The rolling-window query is bounded by chat, sender, message
type, visibility state, timestamp, ordering, and the approved count.

Existing indexes support the query shape without a schema change:

- `ix_chat_messages_chat_id_created_at`
- `ix_chat_messages_chat_id_visibility_status`
- `ix_sub_post_chat_messages_chat_id_created_at`
- `ix_sub_post_chat_messages_chat_id_visibility_status`

## Race Safety

Before the rolling-window read, the service acquires a deterministic PostgreSQL
transaction-scoped advisory lock for the limiter category, chat ID, and sender
user ID.

The lock is:

- cross-process and cross-instance while all instances share PostgreSQL
- released automatically by normal transaction completion
- scoped so unrelated chats, users, and chat families use different keys

The protected order is:

1. request schema validation
2. authentication
3. chat membership and write authorization
4. transaction-scoped limiter serialization
5. rolling-window read
6. message insert
7. commit
8. existing notification, read-state, moderation surfacing, and follow-up work

Rejected messages are not inserted and do not create downstream notifications.

## Retry-After

When the approved count is already present, the limiter selects the oldest
message still contributing to the current 5-message window. It calculates when
that row exits the 60-second window and returns a rounded-up `Retry-After`
second value so clients are not told to retry before eligibility returns.

The response does not expose internal timestamps, message IDs, sender IDs, chat
IDs, counts beyond the public policy, SQL details, or limiter internals.

## Stable 429 Contract

Rate-limit rejections use:

- HTTP status `429`
- stable code `API.RATE_LIMITED`
- safe public detail/message
- correlation identifier
- existing CORS behavior
- existing response-security headers
- `Retry-After` for this reliable chat rolling-window limiter

Game chat and Need-a-Sub chat share the same public code.

## Limiter Failure Behavior

The limiter must not fail open.

If PostgreSQL lock acquisition or the rolling-window read fails, the service
does not assume allowance and does not write the message. Normal safe database
failure behavior applies, and the error must not be mislabeled as a rate-limit
rejection unless the limit was actually proven exceeded.

No fallback in-memory limiter is approved.

## Telemetry And Redaction

C3A may emit existing EN-02 event-envelope telemetry with only bounded,
low-cardinality labels:

- limiter category
- route template
- authenticated actor class
- allow/reject/store-error result
- rolling-window algorithm class
- stable error code when rejected

Telemetry must not include user ID, chat ID, game ID, sub-post ID, IP address,
email, route parameter values, message body, tokens, provider identifiers, raw
SQL, or raw exception text.

## Deferred To C3B

| Workflow | Current protection | Why rate limiting may help | Evidence still required | C3A enforcement |
|---|---|---|---|---|
| Checkout/payment-intent creation | Existing auth, schema validation, payment workflow state, idempotency, timeout, and reconciliation rules. | Provider-cost abuse and duplicate payment pressure. | Approved burst/sustained numbers, retry interaction, provider limits, user impact, and payment-state evidence. | None |
| Saved-card setup/sync | Existing auth, schema validation, provider timeout classification, duplicate-card handling, and no automatic retry policy. | Provider-cost abuse and repeated SetupIntent/sync attempts. | Approved numbers, durable identity expectations, provider limits, and recovery behavior. | None |
| Venue upload authorization | Existing admin authorization, declared size/type validation, signed URL expiration, and R2 metadata verification. | Storage/request abuse and signed-upload churn. | Approved request frequency, upload lifecycle evidence, R2/provider constraints, and UI retry expectations. | None |
| Other provider-cost authenticated actions | Existing per-workflow validation and provider wrapper behavior. | Cost, fraud, or side-effect amplification. | Endpoint-specific product decision and runtime/provider evidence. | None |

## Permanent Infrastructure Deferrals

The following remain outside C3A and C3B source-owned authenticated controls
until permanent infrastructure is selected and evidenced:

- trusted client IP
- anonymous/public throttling
- forwarded-header identity
- edge/WAF limits
- CAPTCHA/bot controls
- provider-dashboard limits

These deferrals do not block source-owned chat protection.
