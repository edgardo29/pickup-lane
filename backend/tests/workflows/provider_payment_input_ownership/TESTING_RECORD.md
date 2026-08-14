# WS02-04B2A2B2 Provider / Payment Input Ownership Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS02-04B2A2B2` |
| Trusted test scope | `backend/tests/workflows/provider_payment_input_ownership` |
| Requirement declaration | `backend/tests/support/requirements/ws02_04b2a2b2.json` |
| Authoritative sources | Canonical WS02-04B2A2B2 plan; accepted B2A2B2 owner decision; limits register; EN-01 trusted evidence architecture |
| Evidence layers | pytest; Pydantic schema validation; FastAPI route-table proof; app-owned provider fakes; PostgreSQL-backed service proof; production source/static caller proof; governance deferral for R8 |

## 1. Scope

This record covers the local trusted evidence for provider-owned and
payment-source-owned input boundaries in WS02-04B2A2B2.

The pass proves only app-owned request parsing, route retirement, source-owned
service rules, and current production caller compatibility. It does not contact
Stripe, run browser tests, prove provider dashboards, close durable payment or
refund lifecycle work, prove genuine financial-credit concurrency, or claim
runtime/provider evidence.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS02-04B2A2B2-R1` | SetupIntent IDs are bounded, trimmed opaque provider tokens and app code delegates provider truth to the Stripe boundary. | pytest |
| `WS02-04B2A2B2-R2` | Inbox global seen tokens are bounded, signed, versioned, user-bound, and reject without persisted side effects. | pytest |
| `WS02-04B2A2B2-R3` | Checkout return URLs are optional/null, trimmed, exact-origin/path scoped, and validated before DB/provider work. | pytest |
| `WS02-04B2A2B2-R4` | Generic payment, refund, and payment-event mutation surfaces remain retired while supported payment workflows remain available. | pytest |
| `WS02-04B2A2B2-R5` | Payment event repair only updates allowed repair fields and keeps provider identity/payload immutable. | pytest |
| `WS02-04B2A2B2-R6` | Game-credit monetary eligibility comes from credited-user-owned official in-app payment/booking source context, uses the minimum applicable source ceiling, and shares budget across equivalent source references. | pytest with PostgreSQL-backed service proof |
| `WS02-04B2A2B2-R7` | Current production callers use supported flows and do not depend on generic payment-event creation. | pytest/source-static |
| `WS02-04B2A2B2-R8` | Later-owner provider, runtime, request/response, telemetry, concurrency, and durable payment evidence remains outside B2A2B2. | deferred |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| R1 | SetupIntent IDs are app-bounded opaque strings and provider validity is checked only at the Stripe boundary. | App code accepts unbounded text or assumes local ID semantics. | Provider-owned payment setup state could be spoofed or overclaimed. | Schema bounds plus app-owned fake proving delegation. | workflow/schema/service |
| R2 | Seen tokens are signed, versioned, user-bound, sequence-bearing strings. | Unsigned, wrong-user, wrong-kind, or malformed tokens update seen state. | Users could alter inbox read state. | Schema bounds, token decoding, and rejected side-effect proof. | workflow/service/PostgreSQL |
| R3 | Checkout return URLs are scoped to allowed origins and the exact game checkout path. | Arbitrary redirects reach DB/provider checkout work. | Unsafe redirect state or misleading payment return flow. | Pure URL validation and early-failure service proof. | workflow/service |
| R4 | Generic payment/refund/payment-event writes stay retired. | Direct financial/provider rows become client-writable again. | Source-owned payment lifecycle could be bypassed. | Route table checks and active supported workflow route checks. | workflow/route |
| R5 | Payment event repair cannot mutate provider identity, type, or raw payload. | Admin repair changes provider event facts after ingestion. | Audit evidence could be rewritten. | Schema extra rejection and PostgreSQL persisted repair proof. | workflow/service/PostgreSQL |
| R6 | Game-credit monetary eligibility is derived from credited-user-owned official in-app booking/payment context and consumed once per underlying source. | Caller-provided game IDs, wrong-user sources, non-official/non-in-app sources, or alternate same-booking references reset budget. | Duplicate/excess credits could be issued from the same payment source. | PostgreSQL-backed service scenarios over source linkage, eligibility, and budget. | workflow/service/PostgreSQL |
| R7 | Current callers use supported setup, checkout, inbox, admin-money, and webhook paths. | Frontend or seed guidance keeps constructing retired generic payment-event writes. | Stale clients or operator docs could revive unsupported provider input. | Production source/static checks. | workflow/source |
| R8 | Later-owner work stays explicitly open. | B2A2B2 overclaims provider dashboards, runtime proof, reconciliation, or concurrency closure. | Production-readiness status becomes dishonest. | Deferred declaration and explicit testing-record boundary. | governance |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | signed-in user, active admin, provider, runtime | covered/deferred | Local app-owned user/admin flows are covered; live provider/runtime evidence is deferred. |
| States / lifecycle | omitted/null, blank, trimmed, bounded, over-bound, signed, tampered, retired, repair-only, linked, unlinked, reversed | covered | These classes materially affect provider/payment ownership. |
| Actions | setup payment method, mark inbox seen, create checkout PaymentIntent, retire generic writes, repair payment events, issue credits | covered | These are the B2A2B2-owned local surfaces. |
| Inputs / boundaries | opaque IDs, seen tokens, URLs, provider metadata, payment/booking/source references, operational text | covered | These are the frozen ownership boundaries. |
| Time | controlled setup timestamps only | not applicable | B2A2B2 does not prove time-expiry behavior. |
| Dependencies | Pydantic, FastAPI route table, PostgreSQL, app-owned provider fakes | covered | These are honest local proof layers for app-owned behavior. |
| Concurrency / idempotency | same-source serial budget; genuine races | partial/deferred | Serial budget proof is covered; genuine concurrency remains WS04/WS05. |
| Authorization / privacy / security | route auth dependency, token user binding, no rejected secret echo | covered in scope | Exact public error representation and headers are later owners. |
| Persistence / rollback | rejected token/repair/credit scenarios leave no prohibited persisted effect | covered | PostgreSQL-backed service tests prove meaningful side effects. |
| Recovery | provider reconciliation, retries, dashboard repair | deferred | Durable financial/provider recovery is outside local B2A2B2. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | nullable return URL and optional repair/source fields | pytest |
| empty | yes | blank SetupIntent, seen token, return URL, operational text | pytest |
| corrupt | yes | malformed/tampered token, invalid URL, wrong source links | pytest |
| exceed | yes | max+1 SetupIntent/seen token/error text and over-budget credits | pytest |
| duplicate | yes | same booking/payment source budget reuse | pytest/PostgreSQL |
| delay | no | no time-expiry claim | not applicable |
| reorder | yes | booking-first/payment-first credit budget scenarios | pytest/PostgreSQL |
| interrupt | yes | rejected token/repair/credit leaves no prohibited rows/updates | pytest/PostgreSQL |
| race | no | genuine concurrent credit issuance remains outside B2A2B2 | deferred |
| expire / revoke | no | provider token/session lifecycle remains provider-owned | deferred |
| tamper | yes | token tamper, URL tamper, provider-field repair tamper | pytest |
| retry | partial | serial same-source budget cannot reset | pytest/PostgreSQL |
| recover | partial | payment-event repair fields only | pytest/PostgreSQL |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| R1 | SetupIntent trim/blank/255/256 and opaque provider delegation. | Pydantic and app-owned fake | `test_setup_intent_input_contract.py` | Enough for local app bounds and delegation; not live Stripe validation. |
| R2 | Seen token trim/blank/512/513, signature, version, kind, user, sequence, and rejected side effects. | Pydantic and PostgreSQL service | `test_inbox_seen_token_input_contract.py` | Enough for repository-owned token contract; not EN-03 secret lifecycle proof. |
| R3 | Return URL null/trim/allowed origin/path/rejection and early validation. | Pure service and monkeypatched guard | `test_checkout_return_url_contract.py` | Enough for app-owned URL scope; not deployed URL/provider evidence. |
| R4 | Generic payment/refund/payment-event writes retired; supported workflow routes available. | FastAPI route table | `test_payment_mutation_retirement_contract.py` | Enough for route lifecycle shape; not public representation or OpenAPI/cache proof. |
| R5 | Repair-only fields, provider metadata immutability, persisted repair effects. | Pydantic and PostgreSQL service | `test_payment_event_repair_contract.py` | Enough for local repair contract; not provider dashboard or reconciliation closure. |
| R6 | Source linkage, credited-user ownership, official in-app eligibility, minimum source ceiling, positive/source-bound amounts, same underlying source budget, source-less rejection, reversal exclusion, and current-unused-amount reversal. | PostgreSQL service | `test_game_credit_source_contract.py` | Enough for serial source-owned budget and reversal invariants; not genuine concurrency. |
| R7 | Current frontend callers and seed guidance use supported flows and no retired provider event body. | Source/static | `test_current_caller_negative_space_contract.py` | Enough for current caller compatibility; not browser behavior. |
| R8 | Later-owner non-closure. | Governance declaration | Requirement JSON and this record | Correctly has no executable pytest mapping. |

### Evidence Quality Checks

- Time-boundary tests are not applicable because this pass has no local expiry
  or wall-clock correctness claim.
- Successful mutations prove persisted effects for payment-event repair,
  game-credit issuance, and game-credit reversal.
- Rejected token, repair, and game-credit scenarios prove prohibited persisted
  side effects did not occur.
- Same-source budget tests prove serial persisted effects are not duplicated by
  alternate payment/booking references.
- Genuine PostgreSQL race behavior is not claimed by this pass.
- External provider behavior is faked only at the app-owned Stripe boundary,
  without mocking the business rules being tested.
- Database-constraint attribution is not the proof layer for this pass.

## 7. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| SetupIntent sync | App passes bounded opaque ID to provider boundary. | App must not infer local provider truth from ID shape. | No DB mutation in delegation rejection scenario. |
| Mark global seen | Valid signed token updates only the user's global seen sequence. | Invalid/wrong-user/wrong-kind tokens do not change existing state. | Upsert is monotonic for sequence; secret lifecycle is external. |
| Checkout return URL | Valid return URL is normalized before checkout work. | Invalid URL fails before DB/provider checkout work. | No DB/provider effect on validation failure. |
| Retired generic writes | Authenticated stale callers receive 410 tombstones. | No body contract or generic creation/update behavior is revived. | No persisted/provider effect. |
| Payment-event repair | `payment_id`, `processing_status`, and `processing_error` can update when valid. | Provider identity, event type, and raw payload cannot change. | Rejected repair leaves provider fields and state unchanged. |
| Game-credit source budget | Valid user-owned official in-app booking/payment source issues at most the remaining/minimum eligible amount. | Wrong-user, non-official/non-in-app, unlinked/source-less, non-positive, or over-budget inputs do not persist credits. | Equivalent source references share one serial budget. |
| Game-credit reversal | Valid reversal records the current unused amount, sets available value to zero, and marks the credit reversed. | Client-supplied reversal amount and missing required audit reason do not persist reversal usage or mutate the credit. | Blank idempotency keys normalize to server-owned generated keys; genuine concurrent reversal remains later-owner work. |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| `WS02-04B2A2B2-R8` | deferred | Whole-request body limits, HTTP/OpenAPI/cache/tombstone representation, request and response ownership, permanent URL/header/edge/runtime evidence, inbox secret lifecycle, Stripe/provider dashboards, payment/refund/reconciliation lifecycle, durable financial workflows, telemetry/metrics/dashboards/alerts, genuine financial-credit concurrency closure, and future source-less discretionary credits remain outside B2A2B2. | Listed downstream owners |
| Live Stripe validation | deferred | Local tests use app-owned fakes only. | WS05/provider evidence |
| Browser checkout behavior | deferred | B2A2B2 proves backend contract and caller source, not Playwright/browser runtime. | Frontend/e2e owner |
| Public error/header representation | deferred | These tests assert only local rejection and non-echo basics. | WS02-05A / API-error owners |
| Genuine credit issuance race closure | deferred | Serial PostgreSQL same-source proof is not concurrent locking proof. | WS04/WS05 |

## 9. Adequacy Conclusion

This evidence is adequate for Gate B when focused B2A2B2 pytest, adjacent
trusted regression, full trusted backend regression, checker regression,
checker domain/suite scopes, generated traceability, syntax/compile validation,
and diff/integrity checks pass.

Requirements R1 through R7 have executable trusted evidence. R8 is intentionally
deferred with zero pytest mappings. Checker `PASS` is structural compliance
evidence only; this record supplies the human adequacy boundary and keeps
provider/runtime/later-owner gaps explicit.
