# WS02-04C3A Chat Rate Limits Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS02-04C3A` |
| Trusted test scope | `backend/tests/platform/chat_rate_limits` |
| Requirement declaration | `backend/tests/support/requirements/ws02_04c3a.json` |
| Authoritative sources | Canonical WS02-04C3A plan, `limits-and-thresholds-register.md`, EN-01, EN-02, WS02-03, WS02-04A, WS02-04B1, WS02-04C2 |
| Evidence layers | pytest, PostgreSQL, backend HTTP/API, source/AST/model metadata, governance deferral |

## 1. Scope

This record covers the local trusted evidence for Pickup Lane's source-owned
authenticated chat-send rate limit: at most 5 visible text messages per
authenticated sender, per chat, per chat family, in a rolling 60-second window.
The covered chat families are game chat and Need-a-Sub chat.

The record does not cover provider-cost/action throttles, anonymous/public
abuse controls, trusted client-IP ownership, forwarded-header trust, edge/WAF,
CAPTCHA, provider dashboards, deployed topology, production load, monitoring,
alerts, or full API-M11 closure. Those remain with C3B, later passes, or
external/runtime evidence.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS02-04C3A-R1` | Approved 5 visible text messages per 60 seconds rule applies to both chat families. | pytest |
| `WS02-04C3A-R2` | Limiter identity is sender, chat, and family; state is committed PostgreSQL chat rows. | pytest |
| `WS02-04C3A-R3` | Rolling-window and `Retry-After` semantics are exact and controlled. | pytest |
| `WS02-04C3A-R4` | Same sender/chat/family decisions serialize through PostgreSQL advisory locks. | pytest |
| `WS02-04C3A-R5` | Authorization, existence, ownership, and payload checks precede limiter disclosure. | pytest |
| `WS02-04C3A-R6` | Rejected and store-failure limiter paths do not create prohibited chat side effects. | pytest |
| `WS02-04C3A-R7` | Proven C3A rejections use the stable safe 429 API contract. | pytest |
| `WS02-04C3A-R8` | Visible-text, removal, restoration, and non-text boundaries are truthful. | pytest |
| `WS02-04C3A-R9` | One shared limiter owner protects current send paths without alternate bypasses. | pytest |
| `WS02-04C3A-R10` | C3A telemetry remains EN-02 safe and low cardinality. | pytest |
| `WS02-04C3A-R11` | Broader rate/abuse controls remain explicit later/external work. | deferred |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| R1-R3 | The 5/60 rule counts only current visible text rows for the same sender/chat/family. | Off-by-one, wrong identity, wrong row type, or wrong time boundary. | Users can spam or get blocked incorrectly. | Shared limiter query, deterministic ordering, bounded count, controlled time. | platform |
| R4 | Same identity checks serialize before the rolling-window read. | Two concurrent requests both see 4 rows and both insert. | The approved maximum can be exceeded. | Transaction-scoped `pg_advisory_xact_lock`. | platform |
| R5-R6 | Write eligibility precedes limiter disclosure and rejection precedes send side effects. | Private chat activity leaks, or rejected sends still create messages/notifications/read state/moderation effects. | Privacy leak or abuse damage despite a 429. | Service ordering and rollback/no-mutation assertions. | platform |
| R7 | Proven rejections emit the accepted safe 429 response shape. | `Retry-After` is dropped or unsafe headers/details leak. | Clients cannot respond safely, or internals leak. | WS02-04A/WS02-03 HTTP layer evidence through the real route. | platform |
| R8-R9 | Current source has one limiter owner and no ordinary-user visibility bypass. | Duplicate limiters or alternate message/visibility paths make evidence false. | Unprotected writes or count reset bypasses. | Source/AST/model/router inspection plus persisted visibility tests. | platform |
| R10 | Limiter diagnostics use bounded event metadata only. | IDs, message text, route params, SQL, or exception details enter logs. | Privacy/security leak in abuse-control path. | EN-02 `EventEnvelope` and runtime log payload assertions. | platform |
| R11 | Later/external abuse controls remain unclosed. | Local source tests are overstated as broad API-M11 closure. | False production-readiness signal. | Requirement declaration deferral and testing-record boundary. | governance |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | authenticated sender, non-member, write-ineligible user, admin moderator | covered/grouped | Senders are executable; admin moderation is allowed but not a send bypass. |
| States / lifecycle | visible, removed, restored, system, pinned update, text-only Need-a-Sub rows | covered | These define "visible text" truthfulness. |
| Actions | create chat message, reject chat message, remove/restore visibility, read HTTP error | covered | Current C3A behavior is create/reject plus safe response. |
| Inputs / boundaries | 4 rows, 5 rows, exact 60-second boundary, outside boundary, other sender/chat/family | covered | These are the approved numeric and identity boundaries. |
| Time | controlled UTC baseline and rolling-window boundary | covered | Exact boundary evidence avoids wall-clock ambiguity. |
| Dependencies | PostgreSQL, FastAPI HTTP stack | covered | Committed-row and response-normalization claims require these layers. |
| Concurrency / idempotency | same sender/chat/family race; unrelated advisory keys | covered | Genuine independent sessions/connections prove the lock safeguard. |
| Authorization / privacy / security | auth-before-limiter, safe error, safe telemetry | covered | Limiter must not become a disclosure channel. |
| Persistence / rollback | no message, notification, read state, summary, detection, or surfacing effect on rejection/failure | covered | Rejection must prevent the abusive durable effect. |
| Recovery | lock/read store failure propagates as store error, not fake allowance or fake 429 | covered | Fail-closed behavior prevents silent bypass. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | missing auth or missing/mismatched chat ownership | pytest |
| empty | yes | empty message remains existing message-body validation, not C3A | covered elsewhere by B1 |
| corrupt | yes | unrelated HTTPException headers and unsafe telemetry fields | pytest |
| exceed | yes | 6th visible text message in the current window | pytest |
| duplicate | yes | concurrent same-identity send attempts | pytest |
| delay | yes | `Retry-After` from oldest qualifying row | pytest |
| reorder | yes | `created_at ASC, id ASC` deterministic row ordering | pytest |
| interrupt | yes | advisory lock and rolling-window read failures | pytest |
| race | yes | independent PostgreSQL sessions/connections | pytest |
| expire / revoke | no | runtime clock and deployment state | deferred |
| tamper | yes | ordinary-user visibility bypass negative space | pytest |
| retry | yes | safe retry interval only, not global retry policy | pytest |
| recover | yes | failed store operations do not fabricate C3A rejection | pytest |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| R1-R4, R6, R10 | Shared limiter constants, identity, rolling-window query, store failure, telemetry | pytest + PostgreSQL | `test_chat_rate_limit_service_contract.py` | Proves the common source-owned limiter without duplicating each workflow. |
| R1, R5, R6, R8 | Game chat workflow integration and side effects | pytest + PostgreSQL | `test_game_chat_rate_limit_contract.py` | Exercises the production send owner, allowed message persistence/count behavior, and rejected side-effect safety. |
| R1, R5, R6, R8 | Need-a-Sub workflow integration and side effects | pytest + PostgreSQL | `test_need_a_sub_chat_rate_limit_contract.py` | Exercises the production send owner, allowed message persistence/count behavior, rejected side-effect safety, and its separate post row lock. |
| R4, R6 | Same-identity race and key-layer independence | pytest + PostgreSQL | `test_chat_rate_limit_concurrency_contract.py` | Uses independent sessions/connections and observes the real advisory-lock SQL. |
| R7 | Stable API 429 shape and prerequisite headers | backend HTTP/API | `test_chat_rate_limit_error_contract.py` | Proves a real C3A rejection through the application response stack. |
| R8-R10 | Ownership and bypass negative space | source/AST/model metadata | `test_chat_rate_limit_negative_space_contract.py` | Static evidence is the lowest reliable layer for route/source ownership. |
| R11 | Broader rate/abuse controls | governance deferral | Requirement JSON and this record | Local C3A tests cannot honestly prove external/runtime controls. |

### Evidence Quality Checks

- Exact time-boundary tests use controlled UTC baselines in service-level
  PostgreSQL evidence.
- Successful send tests assert shared limiter integration and persisted visible
  message/count behavior; they do not independently assert positive summary,
  read-state, or notification effects.
- Rejected mutations prove prohibited message, notification, read-state,
  summary, detection, and surfacing effects do not occur.
- Genuine PostgreSQL race behavior uses independent sessions and independent
  database connections.
- Store-failure tests inject at the actual advisory-lock and rolling-window
  read seams rather than replacing the business rule.
- Backend HTTP evidence uses the application route and error middleware, not a
  browser or a synthetic response.
- Source/static tests are limited to ownership and negative-space claims that
  are better proven by current repository structure than by runtime examples.

## 7. Important Side Effects

| Operation / Scenario | Successful Effects / Evidence Context | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| Allowed game chat send | C3A tests assert one additional visible text message and the expected persisted count. Current source normally performs downstream summary, sender read-state, notification, and moderation work, but C3A does not independently assert those positive effects. | Not applicable. | One durable send effect asserted by C3A evidence. |
| Rejected game chat send | None. | No new message, notification, sender read state, summary update, detection, or moderation surfacing. | No prohibited durable effect. |
| Allowed Need-a-Sub chat send | C3A tests assert one additional visible text message and the expected persisted count. Current source normally performs downstream summary, sender read-state, notification, and moderation work, but C3A does not independently assert those positive effects. | Not applicable. | One durable send effect asserted by C3A evidence. |
| Rejected Need-a-Sub chat send | None. | No new sub-chat message, notification, sender read state, summary update, detection, or moderation surfacing. | No prohibited durable effect. |
| Limiter store failure | None. | No fake allowance, no fake 429, no `Retry-After`, no send side effects. | Database/store failure propagates. |
| Same-identity concurrent game chat sends | Exactly one of two competing sends creates the fifth qualifying row. | The second request must not create a sixth row or downstream effects. | Final qualifying count is 5, never 6. |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| Provider-cost/action rate values | deferred | C3A covers authenticated chat-send only. | C3B / later passes |
| Authenticated non-chat throttles | deferred | Not a chat-send source-owned rule. | C3B / later passes |
| Anonymous/public abuse controls | deferred | Requires trusted client identity and edge/runtime policy. | C3B / WS08 / WS09 / WS10 |
| Trusted client-IP and forwarded-header ownership | deferred | Requires deployed ingress/topology proof. | WS02-03 / WS10 |
| Edge/WAF/CAPTCHA/auth-provider/provider dashboard controls | deferred | External provider/runtime evidence, not local source tests. | later evidence |
| Runtime/load validation, monitoring, alerts | deferred | Requires deployed/runtime observation. | OPS / later passes |
| Migration/schema-history proof | not applicable | C3A makes no migration change; model/index inspection proves current source definitions only. | migrations if later changed |

## 9. Adequacy Conclusion

The selected evidence is adequate for the local C3A source-owned contract when
the focused tests, adjacent regressions, full trusted backend regression,
checker/domain/suite checks, traceability generation, compile validation, and
`git diff --check` pass.

R1-R10 have trusted executable mappings in `backend/tests/platform/chat_rate_limits`.
R11 is intentionally deferred and must have zero pytest mappings. Checker
`PASS` remains structural compliance evidence only; semantic adequacy depends
on this record, the tests, and independent human review.
