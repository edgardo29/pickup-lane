# WS02-04C3A - Authenticated Chat Rate Limiting

## At A Glance

| Field | Value |
|---|---|
| Pass | `WS02-04C3A` |
| Track | `WS02` |
| Type | `API / Platform source-owned implementation and evidence` |
| Primary controls | `API-M11`, `GOV-006` |
| Authority basis | Master production-readiness blueprint, finalized remediation plan, `FDN-04`, `limits-and-thresholds-register.md`, WS02-04 source-owned closeout, WS02-04C3B deferral record |
| Depends on | `EN-01`, `EN-02`, `WS02-03`, `WS02-04A`, `WS02-04B1`, `WS02-04C1`, `WS02-04C2` |
| Trusted test scope | `backend/tests/platform/chat_rate_limits` |

## 1. Purpose

WS02-04C3A protects Pickup Lane's authenticated chat-send endpoints from a
single signed-in user rapidly posting visible text messages into one chat. It
does this for the two current chat families:

- game chat message creation through `POST /chat-messages`
- Need-a-Sub chat message creation through
  `POST /need-a-sub/{sub_post_id}/chat/messages`

The pass-owned product rule is:

```text
An authenticated sender may create at most 5 visible text messages per chat,
per chat family, in a rolling 60-second window.
```

C3A is source-owned. The current application implements this rule with
PostgreSQL-backed committed chat-message rows plus a deterministic
transaction-scoped PostgreSQL advisory lock. The pass also owns the stable local
429 response for this reliable rolling-window limiter, including `Retry-After`.

This pass does not select general application rate limits. It does not approve
provider-cost action limits, anonymous/public-IP throttles, trusted proxy or
forwarded-header identity, edge/WAF limits, CAPTCHA, provider dashboards, or
runtime/load claims.

## 2. Why This Matters

Chat spam can flood participants, create noisy notifications, and amplify
moderation work. A limit that is only in one process, only in the browser, or
only approximate would not protect a multi-instance backend. A limit that runs
before authorization could leak private chat existence or activity. A limit that
rejects after creating messages, notifications, read-state changes, or
moderation side effects would still allow abuse damage.

C3A therefore needs a small but exact backend-owned contract:

- the approved 5-per-60-second value has a current governance source;
- the limiter state is shared through PostgreSQL, not memory or browser state;
- same sender/chat requests serialize before the rolling-window read;
- unrelated users, chats, and chat families do not share one limiter key;
- rejected requests do not create prohibited chat side effects;
- clients receive a stable 429 with a safe retry interval when the limit is
  actually proven exceeded;
- the pass does not pretend to close broader abuse-control work that belongs to
  C3B, later runtime/provider evidence, or permanent infrastructure.

## 3. Requirements

| ID | Requirement | What it means | Why it matters |
|---|---|---|---|
| `WS02-04C3A-R1` | The approved authenticated chat product rule is enforced on both current chat-send families. | A verified authenticated user may create at most 5 visible text messages for the same sender, chat, and chat family in a rolling 60-second window for game chat and Need-a-Sub chat. | Protects the current source-owned chat surfaces without inventing broader rate policy. |
| `WS02-04C3A-R2` | Limiter identity and state are source-owned by PostgreSQL chat rows. | The limiter identity is authenticated internal user ID, chat ID, and chat family. Committed chat-message rows are the shared limiter state. IP address, forwarded headers, browser identity, route parameter values in output, provider metadata, Redis, process memory, and a generic limiter table are not limiter state. | Keeps the limit cross-instance and avoids unstable or privacy-sensitive identity inputs. |
| `WS02-04C3A-R3` | Rolling-window and `Retry-After` semantics are exact and controlled. | Qualifying rows are text messages with current visible status and `created_at >= current_time - 60 seconds`, ordered by `created_at` then `id`, bounded to the approved count. `Retry-After` is derived from the oldest contributing row and rounded up to at least 1 second for rejected requests. | Prevents off-by-one, clock-boundary, and early-retry errors. |
| `WS02-04C3A-R4` | Same sender/chat/family requests serialize through deterministic PostgreSQL advisory locks. | The service takes a transaction-scoped PostgreSQL advisory lock before the rolling-window read. The lock key is deterministic across processes and separates limiter category, chat ID, and sender ID. | Prevents concurrent requests from both observing allowance and exceeding the approved count. |
| `WS02-04C3A-R5` | Authorization and chat-write checks happen before limiter disclosure. | Authentication, chat existence, membership, active/write eligibility, and payload/chat ownership checks run before rate-limit state can produce a 429. | Prevents using the limiter to infer private chat existence, membership, activity, or counts. |
| `WS02-04C3A-R6` | Rejected and failed limiter paths do not create prohibited durable chat side effects. | Rate-limited requests do not insert a message, create notifications, update read state, create moderation findings, refresh chat summaries, or surface moderation text. Database lock/read failures do not fail open and are not mislabeled as proven rate-limit rejections. | Rejection must prevent the abusive effect rather than only change the response. |
| `WS02-04C3A-R7` | C3A rejections use the stable safe 429 contract. | Proven chat rate-limit rejections return HTTP 429, stable public code `API.RATE_LIMITED`, safe public detail/message, correlation ID, existing CORS/security-header behavior, and the approved `Retry-After` header. | Lets clients respond safely and keeps API errors non-disclosing. |
| `WS02-04C3A-R8` | Visible-text and moderation semantics are truthful. | Only currently visible text messages count. Removed/non-visible rows do not count while removed. Non-text/system rows are outside the C3A count. Current user-facing send paths create visible text rows; admin moderation changes visibility but does not create an alternate sender chat-write path. | The phrase "visible text messages" must match actual source behavior and not hide a reachable bypass. |
| `WS02-04C3A-R9` | C3A has one production limiter owner and no current bypass. | Both chat-send services use the shared limiter. There is no duplicate route-local count, middleware throttle, frontend-only throttle, in-memory fallback, Redis limiter, generic limiter table, or alternate production message insert path for authenticated user chat sends. | Competing mechanisms or direct inserts would make evidence misleading. |
| `WS02-04C3A-R10` | C3A telemetry and diagnostics remain EN-02 safe. | Any emitted C3A event uses bounded labels such as outcome, route template, actor class, limiter category, and stable error code. It must not include user IDs, chat IDs, game IDs, sub-post IDs, IPs, emails, route parameter values, message bodies, tokens, provider identifiers, raw SQL, or raw exception text. | Prevents the abuse-control path from leaking sensitive chat or identity data. |
| `WS02-04C3A-R11` | Later and external rate/abuse-control work remains explicit and unclosed. | Provider-cost/action limits stay with C3B or later evidence; anonymous/public-IP throttling, trusted proxy/client-IP ownership, forwarded-header trust, edge/WAF, CAPTCHA, auth-provider/provider-dashboard controls, runtime/load validation, monitoring, alerts, and permanent-host evidence remain later or external responsibilities. | Prevents a narrow local source pass from falsely closing broader `API-M11` obligations. |

## 4. Technical Design / Contracts

### 4.1 Authority And Numeric Rule

**What this is**

C3A contains a real product limit. The number is not chosen from code alone.
The current `limits-and-thresholds-register.md` records that WS02-04C3A
approves source-owned authenticated chat limits of 5 visible text messages per
sender per chat per rolling 60-second window for game chat and Need-a-Sub chat
only.

**Contract / required behavior**

- `5` is the approved maximum visible text message count.
- `60 seconds` is the approved rolling-window length.
- The protected resource is one chat within one chat family.
- The actor is the authenticated internal sender.
- The rule applies to message creation, not reads, read-state updates,
  moderation actions, provider calls, or frontend-only state.
- `FDN-04` supplies the evidence-based method for selecting limits, but it does
  not independently approve numeric thresholds.

**Why**

`GOV-006` forbids inventing universal limit values. C3A can keep the 5/60
contract only because the current limits register explicitly approves it for
the two chat families.

### 4.2 Runtime Surface And Limiter Identity

**What this is**

Current production chat-send entry points are:

- `backend/routes/chat_message_routes.py` -> `create_chat_message_record`
- `backend/routes/sub_post_routes.py` -> `create_sub_post_chat_message_workflow`

Both production services call `enforce_visible_text_chat_rate_limit` through
their local `validate_sender_rate_limit` helpers.

**Contract / required behavior**

- Game chat uses limiter category `game_chat`.
- Need-a-Sub chat uses limiter category `need_a_sub_chat`.
- The limiter key is built from limiter category, chat ID, and sender user ID.
- The public response must not expose the key, IDs, message counts, SQL details,
  or timestamps.
- Admin moderation routes may list, review, remove, or restore chat messages;
  they must not become alternate authenticated user-visible text creation
  paths.
- Seed/dev scripts are not C3A production runtime surfaces.

**Why**

The chat family belongs in the limiter identity so two unrelated chats with the
same UUID in different tables cannot share one throttle. The authenticated user
and chat ID keep the rule narrow enough for normal independent chat activity.

### 4.3 PostgreSQL Limiter State And Rolling Window

**What this is**

The authoritative limiter state is committed rows in the current chat-message
tables. The limiter reads rows matching:

- same `chat_id`
- same `sender_user_id`
- `message_type == "text"`
- current visible status
- `created_at >= current_time - 60 seconds`

**Contract / required behavior**

- Exactly 4 qualifying rows in the current window allow the next message.
- Exactly 5 qualifying rows in the current window reject the next message.
- A sixth qualifying create attempt in the same window is rejected.
- A row exactly at `current_time - 60 seconds` still contributes to the current
  window under the current inclusive boundary.
- Rows are ordered by `created_at ASC, id ASC`.
- The query is bounded to the approved maximum count.
- `current_time` is application-supplied aware UTC for the limiter call.
- User input must not control `created_at`.
- Runtime host clock correctness remains external/runtime evidence, not local
  C3A proof.

**Why**

The inclusive boundary and deterministic ordering make the current source
contract precise enough to test without uncontrolled sleeps. Counting committed
rows makes the limiter cross-instance as long as application instances share
the same PostgreSQL database.

### 4.4 PostgreSQL Advisory-Lock Serialization

**What this is**

Before reading the rolling window, the limiter calls
`pg_advisory_xact_lock(:lock_key)`.

**Contract / required behavior**

- The lock is transaction-scoped, not a manually released session lock.
- The lock key is derived with BLAKE2b over stable UTF-8 key material containing
  the pass-owned limiter category, chat UUID, and sender UUID.
- The implementation must not use Python's randomized `hash()` or any
  process-local value.
- Same sender/chat/family requests must serialize before their rolling-window
  reads.
- The C3A advisory-lock key includes limiter category, chat ID, and sender ID.
- Different C3A limiter identities produce different advisory-lock keys.
- C3A itself must not intentionally collapse unrelated sender, chat, or family
  identities onto one advisory-lock key.
- A lock or query failure must not be treated as allowance.

**Why**

Without serialization, two concurrent requests could both see fewer than 5
messages and both insert. The advisory lock supplies the current source-owned
cross-process serialization mechanism without adding a new table or Redis.
C3A's key-independence claim is limited to the C3A advisory-lock layer. It does
not claim the complete application workflow can never serialize different
senders for other accepted domain reasons; for example, the current Need-a-Sub
send workflow obtains an existing `SubPost` row lock before the C3A limiter.
Gate B evidence must not use full-workflow elapsed-time assertions to prove
absence of those non-C3A locks.

### 4.5 `Retry-After`

**What this is**

When the limit is proven exceeded, C3A tells the client when retrying becomes
safe for this rolling-window decision.

**Contract / required behavior**

- `Retry-After` is an integer number of seconds.
- It is calculated from the oldest row still contributing to the current
  5-message window.
- It is rounded up so the client is not told to retry too early.
- It is never zero or negative on a rejected request.
- It does not expose timestamps, IDs, row counts beyond the public policy, SQL
  details, or limiter internals.
- It is emitted only by the proven C3A rolling-window rejection path and then
  preserved by the stable HTTP error layer.

**Why**

`API-M11` requires `Retry-After` behavior to be explicit when a retry interval
is known. C3A has a known interval because the state is local PostgreSQL rows in
a rolling window.

### 4.6 Stable 429 Error Contract

**What this is**

C3A relies on the accepted WS02-04A stable error machinery and the accepted
WS02-03 CORS/security-header behavior.

**Contract / required behavior**

- Proven C3A rate-limit rejections raise HTTP 429.
- The stable public code is `API.RATE_LIMITED`.
- The detail/message is safe public text.
- The response includes a safe correlation ID.
- The `Retry-After` header survives the HTTPException handler.
- CORS and response-security headers remain owned by their prerequisite passes.
- Other HTTPException headers are not made public merely because C3A needs
  `Retry-After`.

**Why**

Clients need a predictable machine-readable response, but stable errors must
not leak limiter internals or accidentally broaden unrelated header exposure.

### 4.7 Authorization, Side Effects, And Failure Behavior

**What this is**

The limiter must run only after the caller is allowed to write to the chat, and
before the new message and downstream effects are created.

**Contract / required behavior**

- Game chat validates chat existence and membership/write authority before
  enforcing the limiter.
- Need-a-Sub chat validates the locked post, chat existence, write authority,
  and request `chat_id` ownership before enforcing the limiter.
- A rate-limited request does not insert a message row.
- A rate-limited request does not create notifications, read-state changes,
  moderation findings, summary refreshes, or moderation surfacing.
- Advisory-lock or rolling-window query failure is not fail-open and is not
  labeled as a proven rate-limit rejection.
- If message insertion or commit fails after an allowed decision, normal
  database rollback/error behavior applies.
- Post-commit moderation surfacing is not part of rejected-path side effects.

**Why**

The limiter should reduce abusive durable effects and must not become a private
chat oracle for unauthorized callers.

### 4.8 Visibility, Message Type, And Moderation

**What this is**

The approved rule is for visible text messages. Current chat tables distinguish
message type and visibility state.

**Contract / required behavior**

- Newly created user chat messages are text and visible.
- Removed/non-visible messages do not contribute while removed.
- Restored visible text messages contribute again if still inside the rolling
  window.
- Game-chat system or pinned-update rows are outside the C3A count.
- Need-a-Sub chat is text-only in current schema.
- Admin moderation may alter visibility but does not create an alternate
  user-send path.
- C3A does not change B1's separate message-body, page-size, or total visible
  history caps.

**Why**

The word "visible" is not decorative. The source query filters on current
visibility, so evidence must prove that current behavior and confirm it does not
give ordinary senders a self-service limiter bypass.

### 4.9 Privacy-Safe Telemetry

**What this is**

The current limiter emits an EN-02 event envelope for allowed, rejected, and
store-error outcomes.

**Contract / required behavior**

Allowed runtime labels include only bounded, low-cardinality classes such as:

- route template
- outcome class
- limiter category or resource kind
- authenticated actor class
- operation class
- stable error code on rejection

Runtime labels and logs must not include:

- user ID
- chat ID
- game ID
- Need-a-Sub post ID
- IP address
- email
- route parameter value
- message body
- auth token
- provider/private identifier
- raw SQL
- raw exception text

**Why**

Rate-limit diagnostics are security-relevant, but logging private chat or
identity values would violate EN-02's observability/privacy foundation.

### 4.10 Schema And Index Boundary

**What this is**

C3A currently uses existing chat-message tables and indexes. No migration is
approved by this plan.

**Contract / required behavior**

- Existing indexes materially support filtering by chat and creation time and
  by chat and visibility for both chat families.
- The current source does not require a new table, Redis, cache, or migration.
- Source inspection can prove repository schema/index presence.
- Production query-plan, load, and provider/runtime performance evidence remain
  later evidence and must not be inferred from local source alone.

**Why**

The current query is narrow and bounded. A theoretically more specialized index
is not by itself a C3A production correction unless current repository truth
shows the approved source-owned query can no longer be supported.

## 5. Implementation Scope

C3A Gate A owns this canonical planning document.

Gate B is authorized to add fresh EN-01 trusted evidence and requirement
traceability for the current source-owned behavior. Gate B is not authorized to
redesign the product rule or broaden C3A into general rate limiting.

### Production Correction Set

No production source correction is frozen by Gate A.

Current source already contains:

- `backend/services/chat_rate_limit_service.py`
- the game-chat integration in `backend/services/game_chat_service.py`
- the Need-a-Sub chat integration in `backend/services/sub_post_chat_service.py`
- 429 header preservation in `backend/observability/http_errors.py`

Gate B must return to Gate A if fresh trusted evidence proves a production
behavior defect that cannot be corrected inside the frozen scope.

### Configuration Correction Set

None.

C3A does not introduce an environment variable, runtime setting, edge setting,
provider setting, Redis configuration, middleware configuration, or deployment
configuration.

### Governance / Document Correction Set

None in Gate B.

The current limits register and C3B deferral record already carry the
authoritative numeric and boundary decisions. If a later correction to those
records becomes necessary, Gate B must stop and return to Gate A.

### Requirement / Evidence Set

Gate B may create exactly:

- `backend/tests/support/requirements/ws02_04c3a.json`
- `backend/tests/platform/chat_rate_limits/TESTING_RECORD.md`
- `backend/tests/platform/chat_rate_limits/test_chat_rate_limit_service_contract.py`
- `backend/tests/platform/chat_rate_limits/test_game_chat_rate_limit_contract.py`
- `backend/tests/platform/chat_rate_limits/test_need_a_sub_chat_rate_limit_contract.py`
- `backend/tests/platform/chat_rate_limits/test_chat_rate_limit_concurrency_contract.py`
- `backend/tests/platform/chat_rate_limits/test_chat_rate_limit_error_contract.py`
- `backend/tests/platform/chat_rate_limits/test_chat_rate_limit_negative_space_contract.py`

If any other file becomes necessary, the pass must return to Gate A before that
file is edited.

## 6. Testing And Evidence

C3A evidence uses the EN-01 architecture:

```text
Pass
-> Requirement
-> Risk / Scenario / Edge Case
-> Trusted Test
-> Generated Traceability
```

Detailed scenario inventories and adequacy reasoning belong in
`backend/tests/platform/chat_rate_limits/TESTING_RECORD.md`, not in this
planning document.

### Requirement Declaration Design

Gate B must create `backend/tests/support/requirements/ws02_04c3a.json` with
the following declaration design:

| ID | State | Scope | Source controls | Reason, if applicable |
|---|---|---|---|---|
| `WS02-04C3A-R1` | `required` | `platform/chat_rate_limits` | `["API-M11", "GOV-006", "FDN-04", "WS02-04C3A", "WS02-04B1"]` | Not required. |
| `WS02-04C3A-R2` | `required` | `platform/chat_rate_limits` | `["API-M11", "GOV-006", "FDN-04", "WS02-04C3A"]` | Not required. |
| `WS02-04C3A-R3` | `required` | `platform/chat_rate_limits` | `["API-M11", "GOV-006", "FDN-04", "WS02-04C3A"]` | Not required. |
| `WS02-04C3A-R4` | `required` | `platform/chat_rate_limits` | `["API-M11", "GOV-006", "FDN-04", "WS02-04C3A", "DB-002"]` | Not required. |
| `WS02-04C3A-R5` | `required` | `platform/chat_rate_limits` | `["API-M11", "AUTHZ-011", "WS02-04C3A", "WS03"]` | Not required. |
| `WS02-04C3A-R6` | `required` | `platform/chat_rate_limits` | `["API-M11", "API-M12", "GOV-006", "WS02-04C3A", "WS02-04A", "WS02-04C2"]` | Not required. |
| `WS02-04C3A-R7` | `required` | `platform/chat_rate_limits` | `["API-M11", "API-M12", "API-M15", "EN-02", "WS02-03", "WS02-04A", "WS02-04C3A"]` | Not required. |
| `WS02-04C3A-R8` | `required` | `platform/chat_rate_limits` | `["API-M11", "WS02-04C3A", "WS02-04B1", "WS03"]` | Not required. |
| `WS02-04C3A-R9` | `required` | `platform/chat_rate_limits` | `["API-M11", "GOV-006", "FDN-04", "WS02-04C3A", "WS02-04C3B"]` | Not required. |
| `WS02-04C3A-R10` | `required` | `platform/chat_rate_limits` | `["API-M11", "API-M15", "EN-02", "OPS-010", "WS02-04C3A"]` | Not required. |
| `WS02-04C3A-R11` | `deferred` | `governance` | `["API-M11", "API-M19", "GOV-006", "FDN-04", "WS02-04C3A", "WS02-04C3B", "WS02-03", "WS05", "WS08", "WS09", "WS10"]` | `Provider-cost/action rate values, authenticated non-chat throttles, anonymous/public abuse controls, trusted client-IP identity, forwarded-header trust, edge/WAF/CAPTCHA/auth-provider/provider-dashboard controls, permanent hosting/provider evidence, runtime/load validation, monitoring, alerts, and full API-M11 closure remain later or external responsibilities and cannot be closed by local C3A source tests.` |

Expected generated traceability after Gate B:

- `WS02-04C3A-R1` through `WS02-04C3A-R10`: at least one trusted pytest
  mapping each.
- `WS02-04C3A-R11`: zero pytest mappings by design, with the declaration
  reason and testing record explaining the deferral.

### Trusted Test Modules

Gate B evidence must be owned by `backend/tests/platform/chat_rate_limits`.
The trusted tests should group equivalent risks at the lowest reliable proof
layer:

| File | Primary proof |
|---|---|
| `test_chat_rate_limit_service_contract.py` | Approved constants, deterministic lock-key construction, UTC normalization, rolling-window query shape, controlled-time boundary behavior, `Retry-After` rounding, advisory-lock failure, rolling-window read failure, and bounded telemetry for `allowed`, `rejected`, and `store_error`. |
| `test_game_chat_rate_limit_contract.py` | Game-chat allowed/rejected behavior, auth/write ordering, visible text qualification, removed/restored/non-text behavior where game-chat owns it, rejected side-effect safety, limiter-store-failure side-effect ordering, and B1 total-cap interaction. |
| `test_need_a_sub_chat_rate_limit_contract.py` | Need-a-Sub allowed/rejected behavior, post/chat ownership ordering, visible text qualification, removed/restored behavior, text-only schema boundary, rejected side-effect safety, limiter-store-failure side-effect ordering, and post-lock interaction. |
| `test_chat_rate_limit_concurrency_contract.py` | Real PostgreSQL same sender/chat/family serialization with independent sessions/connections and deterministic barriers, plus C3A advisory-key independence at the advisory-lock layer for unrelated limiter identities. |
| `test_chat_rate_limit_error_contract.py` | Stable 429 response, `API.RATE_LIMITED`, safe detail/message, correlation ID, `Retry-After` preservation, and prerequisite CORS/security-header compatibility at backend API level. |
| `test_chat_rate_limit_negative_space_contract.py` | No duplicate production limiter owner, no alternate production chat insert path, no ordinary authenticated self-remove/self-restore visibility bypass, no in-memory/Redis/generic limiter state, no frontend-only or middleware-only throttle, no provider-cost/action limiter introduced by C3A, and no sensitive runtime telemetry labels. |

### Required Evidence Details

#### R6 Limiter-Store Failure Evidence

`test_chat_rate_limit_service_contract.py` must prove both current limiter-store
failure seams:

- advisory-lock acquisition failure at the actual lock-acquisition seam;
- rolling-window qualifying-row read failure after the lock stage.

For each seam, Gate B must prove:

- allowance is not returned;
- HTTP 429 is not fabricated;
- `API.RATE_LIMITED` is not claimed;
- `Retry-After` is not fabricated;
- the database/store failure propagates through the normal database/error
  boundary;
- limiter telemetry records only the bounded `store_error` outcome appropriate
  to the current source contract;
- no additional `allowed` or `rejected` limiter outcome is emitted for the
  failed decision.

`test_game_chat_rate_limit_contract.py` and
`test_need_a_sub_chat_rate_limit_contract.py` must prove that a representative
limiter-store failure happens before durable send side effects. For each chat
family, the attempted send must not create or mutate:

- a new chat-message row;
- notification creation or reopening;
- sender read state;
- chat summary state;
- chat-message moderation detections or findings;
- post-commit moderation surfacing.

The service-level limiter test owns the meaning of store failure. The workflow
tests own ordering and absence of downstream send side effects. Gate B must not
mock away both layers in one test and call that full proof.

#### R4 Same-Identity Concurrency And Advisory-Key Independence

`test_chat_rate_limit_concurrency_contract.py` must use real PostgreSQL and at
least two independent database sessions/connections. It must use one
representative current chat family for the full race because the serialization
mechanism is shared. The game-chat and Need-a-Sub modules separately prove that
each production caller uses the shared limiter with its correct category.

The same-identity race setup must include:

- one sender;
- one chat;
- one limiter family;
- exactly 4 committed qualifying visible text messages inside the controlled
  60-second window.

The test must coordinate two concurrent send attempts for that same
sender/chat/family and prove:

- both attempts genuinely contend for the production C3A limiter identity;
- the first transaction obtains the production transaction-scoped advisory lock;
- the second attempt reaches the production lock path while the first
  transaction still owns that lock;
- the first request observes 4 qualifying rows and may create exactly one
  additional qualifying message;
- that message and transaction complete before the second limiter decision can
  proceed;
- after serialization releases, the second request observes the updated
  committed state containing 5 qualifying messages;
- the second request receives the C3A rate-limit rejection;
- final qualifying message count is exactly 5, never 6;
- the rejected concurrent request produces no prohibited downstream send side
  effects.

The proof must use deterministic barriers, events, or equivalent
synchronization. It must not use arbitrary sleeps to establish race ordering.
A bounded test-harness timeout used only to prevent a hung test is test
mechanics, not C3A production policy.

The proof must depend on PostgreSQL's production `pg_advisory_xact_lock`
behavior. It must not let a Python mutex, one shared SQLAlchemy Session, one
shared connection, the test harness itself, or a mocked lock implementation
become the actual serialization mechanism. The design should be such that
removing or bypassing the production advisory-lock safeguard would allow the
race invariant to fail rather than letting the test remain green for an
unrelated reason.

Unrelated-identity evidence belongs at the C3A advisory-lock layer. Gate B must
prove deterministic lock-key separation for:

- different sender, same chat and family;
- different chat, same sender and family;
- different family with otherwise equivalent identity components.

PostgreSQL advisory-lock evidence may confirm distinct C3A keys do not contend
with one another. Gate B must not use elapsed-time assertions against the full
Need-a-Sub workflow for this claim because an accepted `SubPost` domain row lock
may legitimately serialize that workflow for reasons outside C3A.

#### R8 Visibility And Moderation Evidence

Gate B must prove that only currently visible text messages count:

- a recent persisted text row whose current visibility is `removed` does not
  contribute to the C3A count;
- a removed recent text row restored to `visible` contributes again if its
  original `created_at` remains inside the controlled rolling window;
- restoration does not create a new chat message or reset `created_at`;
- current game-chat non-user-send message types such as `system` and
  `pinned_update` do not contribute to the text-message count;
- current Need-a-Sub chat-message schema is text-only, using repository/model
  metadata for that schema fact rather than inventing a database-invalid
  non-text row.

`test_chat_rate_limit_negative_space_contract.py` must prove that current
ordinary authenticated chat-send surfaces do not expose a self-remove,
self-restore, or alternate visibility mutation that lets a sender hide recent
messages solely to reset the C3A count. Current admin moderation may remove or
restore existing messages and is not an alternate ordinary user-send path. The
database model's historical ability to represent `removed_source = "sender"` is
not proof that a current sender removal route exists.

#### R10 Telemetry Evidence

`test_chat_rate_limit_service_contract.py` must prove bounded EN-02-safe
runtime telemetry for every current limiter outcome:

- `allowed`;
- `rejected`;
- `store_error`.

For each outcome, emitted runtime fields must stay within approved bounded
classes and must not contain user ID, chat ID, game ID, Need-a-Sub post ID, IP,
email, route parameter values, message body, token, provider identifier, raw
SQL, or raw exception text. For `store_error`, Gate B must specifically prove
the raw database exception text is not placed into event fields.

This is evidence for current behavior only. Gate B must not add new telemetry.

### Evidence Quality Decisions

PostgreSQL is required for:

- committed-row rolling-window semantics;
- advisory-lock behavior;
- transaction rollback and rejected-side-effect proof where persisted state is
  material;
- same sender/chat/family concurrency proof.

Repository model, metadata, and source inspection are sufficient to prove that
repository-owned chat-message schema and index definitions exist. PostgreSQL is
required for C3A database behavior claims such as committed-row rolling-window
behavior, transaction behavior, rejected persisted effects, and genuine
advisory-lock concurrency. Local C3A evidence does not prove production query
plans, production index usage, production load performance, or deployed
database topology.

Genuine concurrency evidence is required. C3A's race-safety claim is a
production claim, so Gate B must include a deterministic PostgreSQL concurrency
test using independent sessions/connections. Source inspection alone is not
adequate for this claim.

Controlled time is required for exact rolling-window and `Retry-After`
boundaries. Gate B must use controlled inserted timestamps and/or injected
limiter time. It must not rely on uncontrolled sleeps for exact boundary proof.

Provider and live network evidence are not required. C3A has no provider call
and must not use provider/network tests to prove local chat limiting. C3B and
later provider/runtime owners keep those gaps.

Browser/Playwright evidence is not required. The lowest reliable owner for the
C3A response contract is backend HTTP/API evidence. Existing frontend behavior
may display the returned error, but browser proof would not add authority for
the server-side limiter.

Migration evidence is not required. No schema change or data migration is
authorized for C3A. Gate B may inspect current model/index definitions and
metadata but must not add or alter migrations.

### Gate B Validation Commands

Gate B must run the focused and regression evidence appropriate to the final
change set:

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/platform/chat_rate_limits
```

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/platform/api_errors backend/tests/workflows/source_owned_boundaries
```

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/checker backend/tests/workflows backend/tests/platform
```

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/checker
```

```bash
DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/platform/chat_rate_limits
```

```bash
DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/platform/api_errors
```

```bash
DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/workflows/source_owned_boundaries
```

```bash
DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python backend/tests/check_backend_tests.py --scope suite
```

Gate B must also:

- generate and inspect requirement traceability;
- compile/syntax-check changed Python files;
- run `git diff --check`;
- confirm no current trusted non-legacy code imports from excluded historical
  test architecture;
- confirm R1-R10 are mapped and R11 remains zero mapped.

## 7. Integration / Operational Expectations

C3A integrates with:

- WS02-04A for stable public error normalization and preservation of
  `Retry-After` on 429;
- WS02-03 for current CORS and response-security header behavior;
- EN-02 for safe correlation, public error descriptors, event envelopes,
  telemetry label validation, and redaction;
- WS02-04B1 for separate chat content, page-size, and total visible-history
  limits;
- WS02-04C1 for database timeout behavior that may affect limiter failure
  outcomes;
- WS02-04C2 for retry/backpressure ownership and current synchronous
  notification fanout inventory;
- WS02-04C3B for provider-cost/action rate-limit deferrals;
- WS05, WS08, WS09, and WS10 for later durable work, release/testing,
  observability, incident, provider, and runtime evidence.

Operationally, C3A assumes application instances that need a shared limiter
state connect to the same PostgreSQL database. It does not prove permanent
hosting topology, edge behavior, trusted proxy configuration, load behavior, or
deployed monitoring.

## 8. Not Part Of This Pass

C3A does not own:

- new provider-cost or financial-action rate limits;
- checkout/payment-intent, saved-card setup/sync, community publish fee, venue
  upload authorization, webhook, refund, game-credit, or admin-financial rate
  values;
- generic rate-limit tables, Redis, cache-based limiter state, middleware
  limiter state, or edge-provider limiter configuration;
- anonymous/public-IP throttling;
- trusted client-IP or forwarded-header ownership;
- WAF, CAPTCHA, auth-provider, provider-dashboard, or permanent-host controls;
- runtime/load/staging evidence for the entire API-M11 control;
- frontend/browser proof of the backend 429 contract;
- new migrations or schema changes;
- B1-owned message length, page-size, or total visible-history caps;
- broad logging, metrics, dashboards, alert thresholds, or operational
  runbooks.

## 9. Related Controls And Remaining Evidence

| Control / Decision | What this pass establishes | What remains later |
|---|---|---|
| `API-M11` | Source-owned authenticated chat throttling for game chat and Need-a-Sub chat, including PostgreSQL-backed shared limiter state, same sender/chat/family serialization, stable 429, `Retry-After`, failure behavior, and local trusted evidence. | Provider-cost/action values, authenticated non-chat throttles, anonymous/public abuse controls, trusted client IP, forwarded headers, edge/WAF/provider/auth-provider controls, runtime/load validation, monitoring, and full API-M11 closure. |
| `GOV-006` / `FDN-04` | Uses the current evidence-based limits method and the limits register's explicit approval for the 5/60 authenticated chat rule. | Future rate, capacity, alert, retention, provider, worker, and runtime values require their own evidence-backed approvals. |
| `API-M12` / `WS02-04A` | Consumes the accepted stable HTTP error contract for C3A 429 responses and `Retry-After` preservation. | Provider/edge/staging-generated errors and external precedence evidence remain outside C3A. |
| `API-M15` / `EN-02` / `OPS-010` | Keeps C3A diagnostics within bounded event-envelope, public-error, correlation, and redaction contracts. | Broad access logging, metrics, dashboards, tracing, and alerting remain WS09/later evidence. |
| `DB-002` | Uses PostgreSQL as the shared limiter state and serialization layer for this source-owned pass. | Deployment-wide DB connection budget, production pool behavior, load, and permanent topology remain later database/runtime evidence. |
| `WS02-04C3B` | Records that provider-cost/action rate limits are not C3A and remain evidence-dependent. | C3B and later owners must decide any workflow-specific provider-cost values and proof layers. |

### Supporting Relationships

- WS02-04B1 chat boundary evidence must preserve C3A ordering before the total
  visible-history cap, but B1 does not own the C3A rate value.
- WS02-04C2 documents current chat notification fanout as synchronous and
  sequential; C3A does not add worker/concurrency numbers.
- Runtime host clock correctness is an external runtime concern. C3A local
  evidence uses controlled timestamps to prove source semantics.

## 10. Completion Criteria

- [ ] Every C3A requirement is declared in
  `backend/tests/support/requirements/ws02_04c3a.json`.
- [ ] R1 through R10 have generated trusted pytest traceability.
- [ ] R11 remains zero mapped by design with a truthful deferred reason.
- [ ] `backend/tests/platform/chat_rate_limits/TESTING_RECORD.md` records the
  authoritative rule, risks, proof layers, PostgreSQL/concurrency/time
  decisions, side-effect evidence, privacy boundary, C3B split, and external
  gaps without overclaiming runtime/provider/edge closure.
- [ ] Focused C3A trusted tests pass.
- [ ] Relevant adjacent API-error and source-owned-boundary regressions pass.
- [ ] Full current trusted backend regression passes.
- [ ] Checker domain scopes for C3A and adjacent prerequisite evidence pass.
- [ ] Checker suite scope passes.
- [ ] Changed Python files compile.
- [ ] `git diff --check` passes.
- [ ] The final changed-file set matches the frozen Gate A scope.
- [ ] No production, configuration, governance, migration, provider, frontend,
  or browser work is introduced without returning to Gate A.
- [ ] Pass documentation matches current repository truth and authoritative
  scope.
- [ ] No unresolved blocker remains.

Pass completion does not close all of API-M11. It completes the source-owned
authenticated chat limiter slice while preserving explicit later and external
evidence boundaries.
