# WS02-04B2A2A Active Request Schema Bounds Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS02-04B2A2A` |
| Trusted test scope | `backend/tests/workflows/active_request_schema_bounds` |
| Requirement declaration | `backend/tests/support/requirements/ws02_04b2a2a.json` |
| Authoritative sources | Canonical WS02-04B2A2A plan, A2A owner decision, limits register, EN-01 trusted evidence architecture, TESTING_RECORD template |
| Evidence layers | pytest, Pydantic schema validation, PostgreSQL-backed service validation for R6 only, source review, governance deferral |

## 1. Scope

This record covers active workflow request-schema bounds and the narrow
admin-money service target comparison approved for WS02-04B2A2A.

The approved owner decision is policy authority for the field values. Current
accepted source and supported callers are implementation truth and
compatibility evidence; they do not independently approve policy values.

This scope intentionally does not cover whole-request byte limits, B1 product
collection limits, provider or runtime evidence, storage safety, response
minimization, media-type behavior, identity authority, migrations, browser
behavior, controlled-time proof, or genuine concurrency proof.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS02-04B2A2A-R1` | Profile, settings, and self-delete request fields preserve approved static bounds without reclaiming identity authority. | pytest |
| `WS02-04B2A2A-R2` | Game, guest, cancellation, consent-version, and price request fields preserve approved static bounds. | pytest |
| `WS02-04B2A2A-R3` | Community payment snapshot requests stay small, typed, duplicate-safe, and bounded. | pytest |
| `WS02-04B2A2A-R4` | Admin request literals and operational text stay within approved active request bounds. | pytest |
| `WS02-04B2A2A-R5` | Venue-image request metadata has approved request-shape bounds only. | pytest |
| `WS02-04B2A2A-R6` | Admin-money client amounts are non-negative and cannot exceed server-owned eligible target state. | pytest with PostgreSQL-backed service proof |
| `WS02-04B2A2A-R7` | Later-pass and external evidence remains deferred and non-executable. | deferred/governance |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| R1 | Ordinary profile/settings/delete requests accept only approved finite text, literals, and confirmation forms. | Oversized or arbitrary profile/settings/delete input reaches service code. | Profile/account requests carry unintended state or ambiguous deletion intent. | Pydantic field bounds, literal validation, trimming, unknown-field rejection. | workflow/schema |
| R2 | Active game, guest, cancellation, consent, and price request values stay at approved boundaries. | Impossible capacity, unsupported party size, unbounded cents, or oversized text reaches workflow/payment-adjacent code. | Invalid source request state or false readiness claims. | Pydantic bounds/defaults on active request models. | workflow/schema |
| R3 | Community payment snapshots are finite, typed, trimmed, and duplicate-safe. | Arbitrary or oversized payment display data persists. | Unbounded payment text or ambiguous display methods. | Nested Pydantic schemas and duplicate validators. | workflow/schema |
| R4 | Admin action literals and operational text are known and bounded. | Arbitrary outcome classes or oversized internal text reaches admin workflows. | Misclassified admin actions or oversized audit/review/support text. | Pydantic literal and text bounds. | workflow/schema |
| R5 | Venue-image metadata is finite without claiming file/storage safety. | Arbitrary image roles, statuses, or display slots enter metadata. | Misleading storage readiness or malformed admin metadata. | Pydantic literal and numeric bounds. | workflow/schema |
| R6 | Client money amount cannot be negative or exceed server-owned eligible target. | Client input creates source-less or excessive financial outcome. | Unsafe admin financial state. | Pydantic non-negative parsing plus PostgreSQL-backed service target comparison. | workflow/service/PostgreSQL |
| R7 | Later-owner work remains outside A2A closure. | A2A tests falsely claim provider, runtime, identity, storage, response, or concurrency proof. | Misleading production-readiness evidence. | Deferred requirement state and explicit non-closure record. | governance |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | ordinary caller, host, admin, provider, runtime | grouped/deferred | Request schemas are actor-neutral; provider/runtime actors are later evidence. |
| States / lifecycle | omitted, explicit null, accepted literals, unsupported literals, positive/zero/negative money targets | covered | These classes materially change accepted or rejected request behavior. |
| Actions | create, update, join, checkout, add/remove guests, delete account, admin resolve/close/outcome, venue-image upload/update | covered | These are the active A2A request families. |
| Inputs / boundaries | min, min-1, max, max+1, blank, whitespace, duplicate, unknown key, non-string | covered | Boundary and malformed inputs are the core A2A risk. |
| Time | ordinary deterministic fixture timestamps only | not applicable | A2A does not prove time-boundary behavior. |
| Dependencies | Pydantic; PostgreSQL for R6 target state only | covered | Static rules require schema proof; R6 requires real persisted server state. |
| Concurrency / idempotency | genuine races and duplicate provider effects | deferred | WS04/WS05 own those proof layers. |
| Authorization / privacy / security | unknown-field rejection; identity/writable-field authority | grouped/deferred | A2A proves unexpected-key rejection only for included schemas; WS02-05B1/WS03 own writable-field authority. |
| Persistence / rollback | prohibited financial outcome rows after rejected R6 input | covered | Rejected dynamic money input must not create financial outcome rows. |
| Recovery | provider/runtime recovery | deferred | Not provable by local A2A tests. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | optional/null fields and defaulted lists/counts | pytest |
| empty | yes | blank confirmation/reasons/trimmed payment value | pytest |
| corrupt | yes | invalid literals and non-string payment values | pytest |
| exceed | yes | max+1 text/list/numeric and amount-over-target cases | pytest |
| duplicate | yes | duplicate community payment method type | pytest |
| delay | no | no timing invariant | not applicable |
| reorder | no | ordering is not A2A policy | not applicable |
| interrupt | yes | rejected R6 input leaves no prohibited financial outcome | pytest |
| race | no | genuine concurrency remains WS04 | deferred |
| expire / revoke | no | provider/runtime lifecycle is outside A2A | deferred |
| tamper | yes | unknown field rejection in included request schemas | pytest |
| retry | no | idempotency/provider retry is outside A2A | deferred |
| recover | no | provider/runtime recovery is outside A2A | deferred |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| R1 | Profile/settings/delete max, null/omit, literal, trim, wrong/blank, unknown key | pytest/Pydantic | `test_profile_settings_account_bounds.py` | Enough for static request parsing; not WS03 identity authority. |
| R2 | Capacity, price, guest, cancellation, consent, Need-a-Sub price boundaries | pytest/Pydantic | `test_game_request_schema_bounds.py` | Enough for request-shape bounds; not availability, payment totals, refund, provider, or concurrency proof. |
| R3 | Payment snapshot count, literal, strict string/trim, duplicate, instruction null-only, unknown nested key | pytest/Pydantic | `test_community_payment_schema_bounds.py` | Enough for bounded display snapshot shape; not provider payment or saved-card lifecycle. |
| R4 | Admin official-game, money, review, and support literals/text bounds | pytest/Pydantic | `test_admin_request_schema_bounds.py` | Enough for request parsing; not provider/payment execution, moderation lifecycle, idempotency, or durable jobs. |
| R5 | Venue-image role/status/sort-order metadata and unknown keys | pytest/Pydantic | `test_venue_image_schema_bounds.py` | Enough for metadata request shape; not file content, R2, publication, or storage concurrency. |
| R6 | Static non-negative amount and server-owned eligible target comparison | pytest/PostgreSQL/service | `test_admin_money_dynamic_bounds.py` | Enough for target comparison and no prohibited outcome persistence; not WS05 provider lifecycle or genuine concurrency. |
| R7 | Deferred later-owner handoffs | governance | requirement declaration and this record | Correctly unmapped; no executable pytest evidence. |

### Evidence Quality Checks

- Time-boundary proof is not part of A2A; deterministic timestamps are setup
  data only.
- Successful static parsing proves validated model values, defaults, and
  trimming where material.
- Rejected static parsing proves the request does not pass Pydantic validation.
- Rejected R6 service inputs prove no prohibited `AdminFinancialOutcome` row is
  persisted.
- Idempotency and external provider effects are not claimed by this scope.
- No external provider is mocked because R6 uses the target-comparison service
  boundary before provider mutation paths.
- No database-constraint attribution is used as the A2A proof layer.

## 7. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| Static request parsing | Validated model stores accepted values, defaults, nulls, and trimmed values. | Invalid values do not create a valid request model. | No persistence involved. |
| Admin-money target comparison | Equal or zero permitted target cases pass the source target-comparison boundary. | Over-target and no-target positive requests persist no `AdminFinancialOutcome`. | No provider or idempotency proof claimed. |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| B1 product and collection limits | deferred | A2A inherits or references these but does not prove them. | WS02-04B1 |
| Whole-request body limits | deferred | A2A covers field/schema bounds only. | WS02-04B2A1 / WS02-04B2A2C |
| Retired/provider/payment/policy request families | deferred | Those surfaces are not active A2A-owned request shapes. | WS02-04B2A2B1/B2/B3 |
| HTTP/media/OpenAPI/cache/request ownership/response minimization | deferred | Unknown-field proof is narrower than write-ownership policy. | WS02-05A/B1/B2 |
| Identity/profile authority | deferred | R1 preserves the split but does not own verifier/provider/admin identity facts. | WS03 |
| Database concurrency | deferred | Serial PostgreSQL state for R6 is not genuine race proof. | WS04 |
| Payment/provider lifecycle | deferred | R6 does not contact providers or prove refunds/credits/reconciliation. | WS05 |
| Storage/provider behavior | deferred | R5 covers metadata only. | WS06 |
| External runtime/provider evidence | deferred | Not honestly provable by local A2A pytest. | Later provider/runtime owners |

## 9. Adequacy Conclusion

This evidence is adequate for Gate B when the requirement declaration, this
record, six trusted pytest modules, focused A2A pytest, relevant adjacent
trusted regression, full trusted backend regression, checker file/domain/suite
scopes, generated traceability, diff/whitespace checks, frozen Gate A hash
verification, and secret review pass.

R1 through R6 require executable trusted evidence. R7 is intentionally
deferred/governance and must have no pytest mapping. Checker `PASS` remains
machine-compliance evidence only; this record supplies the human adequacy
boundary and keeps later-owner/provider/runtime gaps explicit.
