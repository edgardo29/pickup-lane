# WS02-04B1 Source-Owned Boundaries Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS02-04B1` |
| Trusted test scope | `backend/tests/workflows/source_owned_boundaries` |
| Requirement declaration | `backend/tests/support/requirements/ws02_04b1.json` |
| Authoritative sources | Canonical WS02-04B1 plan, WS02-04 source-owned closeout, EN-01 trusted evidence architecture, WS02-04A stable error contract, approved production-readiness controls and decisions |
| Evidence layers | pytest, FastAPI/TestClient, service checks, PostgreSQL-backed serial-state proof, Stripe/R2 fakes, source review, governance deferral |

## 1. Scope

This record covers WS02-04B1 source-owned repository boundaries for Platform
Notices, public card pagination, Need a Sub collection limits, saved-card local
active count, chat content/list/history caps, and venue-image upload initiation
metadata gates.

It intentionally does not cover provider dashboards, runtime ingress, staging
captures, browser behavior, Playwright, migrations, broad database
serialization, payment-provider lifecycle, final venue-image content safety,
or R2 lifecycle evidence.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS02-04B1-R1` | Platform Notice selected publish boundaries are finite and sparse. | pytest |
| `WS02-04B1-R2` | Platform Notice field, search, cursor, and list boundaries are source-owned. | pytest |
| `WS02-04B1-R3` | Public card pagination is source-bounded and deterministic. | pytest |
| `WS02-04B1-R4` | Need a Sub post schema and service collection limits reject invalid serial inputs before persistence. | pytest |
| `WS02-04B1-R5` | Need a Sub waitlist cap rejects the next serial request without prohibited side effects. | pytest |
| `WS02-04B1-R6` | Saved-card serial local active count is capped without live Stripe calls. | pytest |
| `WS02-04B1-R7` | Game chat and Need a Sub chat serial content/list/history caps are source-owned. | pytest |
| `WS02-04B1-R8` | Venue-image selected-count and current metadata gates are source-owned within B1 limits. | pytest plus source review |
| `WS02-04B1-R9` | Later/provider/runtime non-closure is preserved. | deferred/governance |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| R1/R2 | Platform Notice selection, text, search, and recipient pagination stay finite and sparse. | Oversized fanout, invalid users, unbounded cursors, or partial rows could persist. | Admin notices could become expensive or false. | Route validation, service normalization, eligibility checks, transaction rollback. | workflow/API/service/PostgreSQL |
| R3 | Public card endpoints bound limits, cursors, ordering, and `limit + 1` behavior. | Queries could become unbounded or cursors could be reused in the wrong context. | Public/user card lists could be expensive or inconsistent. | FastAPI query validation and source cursor contracts. | workflow/API/service/source |
| R4/R5 | Need a Sub post and waitlist caps reject invalid serial mutations before prohibited rows or notifications. | Invalid post shapes or over-cap requests could persist partial state. | Overgrown posts, false requests, or noisy notifications. | Schema/service validation, PostgreSQL serial-state proof, rollback checks. | workflow/schema/service/PostgreSQL |
| R6 | Saved-card cap counts only active local rows and fakes Stripe. | Sixth active card or live provider call could slip in. | Payment-method state could exceed product limits or depend on live Stripe. | Service cap, Stripe boundary fakes, persisted-row assertions. | workflow/service/PostgreSQL/provider fake |
| R7 | Chat body, page, and serial visible-text history caps remain finite. | Oversized messages or over-cap visible histories could persist. | Chat storage and moderation surfaces could grow beyond source bounds. | Service normalization, history-count checks, PostgreSQL rows. | workflow/service/PostgreSQL |
| R8 | Venue-image selected count and metadata gates are finite without claiming image safety. | Over-selected images or metadata mismatches could activate rows. | Admin media workflow could overrun source caps or misstate storage safety. | Service count checks, R2 fakes, persisted-state assertions. | workflow/service/PostgreSQL/provider fake |
| R9 | Later-owner obligations stay deferred. | B1 could falsely claim provider/runtime/concurrency closure. | Production-readiness evidence would be misleading. | Requirement state and this record's gap table. | governance |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | admin, selected user, ordinary user, owner, requester, chat participant, provider fake | covered/grouped | Each surface uses the lowest actor model needed to prove the source boundary. |
| States / lifecycle | active/ineligible users, selected/global notices, active/inactive cards, visible/removed chat rows, pending/active venue images | covered/grouped | Material states affect counting, rejection, or sparse persistence. |
| Actions | publish, cancel validation, list, create post/request, sync card, send/list chat, create/complete upload | covered | These actions own the B1 mutations and queries. |
| Inputs / boundaries | exact limit, over limit, duplicates, malformed cursors, context mismatch, unsupported metadata | covered | Boundary inputs are the core B1 risk. |
| Time | future posts/games and ordered rows | covered | Tests use controlled timestamps or source/static checks where ordering is the invariant. |
| Dependencies | PostgreSQL, Stripe fake, R2 fake | covered | Real provider/network access is deliberately excluded. |
| Concurrency / idempotency | serial caps, idempotent notice replay, race gaps | grouped/deferred | Serial effects are executable B1 proof; deterministic races remain WS04/WS05/WS06. |
| Authorization / privacy / security | admin-only notices/images, selected-user eligibility, provider fake boundary | covered/grouped | Route tests preserve validation/error behavior; server-side source remains authoritative. |
| Persistence / rollback | accepted rows and prohibited rows/effects | covered | Rejected mutations assert no relevant prohibited side effects. |
| Recovery | provider/runtime recovery | deferred | Later provider/runtime owners must supply evidence. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | missing selected users, missing/blank chat body | pytest |
| empty | yes | blank Platform Notice and chat fields | pytest grouped with normalization |
| corrupt | yes | malformed cursors, mismatched R2 metadata | pytest |
| exceed | yes | all numeric caps | pytest |
| duplicate | yes | selected IDs and Need a Sub rows | pytest |
| delay | no | runtime delay is outside B1 | deferred |
| reorder | yes | deterministic cursor tie-breaks | source/static pytest |
| interrupt | yes | rejected mutation rollback/no side effect | pytest |
| race | yes | DB/provider races discovered but not B1 proof | deferred to WS04/WS05/WS06 |
| expire / revoke | limited | ineligible selected user and future Need a Sub/game setup | pytest |
| tamper | yes | foreign-context cursors | pytest |
| retry | limited | provider retries are outside B1 | deferred |
| recover | no | provider/runtime recovery is outside B1 | deferred |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| R1/R2 | Platform Notice fanout, text/list bounds, cursor validation, sparse rows | pytest, API, service, PostgreSQL | `test_platform_notice_boundaries.py` | Enough for local source contract; provider/runtime is not involved. |
| R3 | Public card limit/cursor/order contracts across four surfaces | pytest, API/source/service | `test_public_card_pagination_contract.py` | Enough for route/source bounds; not DB runtime/concurrency proof. |
| R4/R5 | Need a Sub post caps and serial waitlist side effects | pytest, schema, service, PostgreSQL | `test_need_a_sub_collection_limits.py` | Enough for serial B1 effects; the six-row position maximum and over-11 substitute rejection are schema-owned request-shape proof, while 11 accepted substitutes, duplicate/incompatible rows, total-sum rejection, and waitlist side effects are service/PostgreSQL proof. Not DB-007 race closure. |
| R6 | Saved-card active local cap with Stripe fakes | pytest, service, PostgreSQL, provider fake | `test_saved_card_limit_contract.py` | Enough for serial local cap; not PAY-008 provider lifecycle. |
| R7 | Chat body/page/history caps | pytest, service, PostgreSQL | `test_chat_boundary_contract.py` | Enough for serial source caps; not C3A rate-policy or cross-sender race closure. |
| R8 | Venue selected count and metadata gates | pytest, service, PostgreSQL, R2 fake, source review | `test_venue_image_upload_boundaries.py` | Enough for current metadata gates; not WS06 image safety or R2 reliability. |
| R9 | Later-owner non-closure | governance | requirement declaration and this record | Correctly deferred; no pytest mapping. |

### Evidence Quality Checks

- Time-sensitive setup uses controlled future timestamps rather than wall-clock
  boundaries as the assertion.
- Successful mutations prove persisted rows or returned bounded page state.
- Rejected mutations prove relevant prohibited rows, status history,
  notifications, admin actions, or active images/cards were not created.
- Idempotency/provider retry closure is not claimed by B1.
- Genuine PostgreSQL race proof is deferred to later owners rather than faked
  with serial tests.
- Stripe and R2 are faked at service-owned boundaries, not by bypassing the
  business rule under test.
- Database-constraint attribution is not the B1 proof layer; service/source
  safeguards are asserted directly.

## 7. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| Selected Platform Notice publish | one notice and one recipient per unique selected user plus one admin action | over-cap/missing/ineligible cases create no notice, recipient, admin action, or notification rows | rollback/no partial state |
| Global Platform Notice publish | one global notice and admin action | no selected-recipient rows and no ordinary notification rows | sparse global state |
| Need a Sub post create | valid 11-sub post and positions persist | schema rejects over-row or over-total inputs before service work; service rejects duplicate, incompatible, or mismatched position input before post/position rows | rollback/no partial state |
| Need a Sub waitlist request | accepted waitlist rows and status histories persist | over-cap request creates no request, status-history, notification, or promotion effect | rollback/no partial state |
| Saved-card sync | active local card persists when under cap | sixth active local card does not persist | Stripe fake records boundary calls only |
| Chat message/list | accepted source-count rows are visible and bounded | over-cap or invalid body does not create an extra visible text row | serial source cap |
| Venue image upload/complete | pending/active local rows change only through accepted metadata gates | over-selected, size mismatch, and content-type mismatch do not activate rows | R2 fake, rollback/no activation |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| R3 cursor races and production query plans | deferred | Local B1 proves source bounds only. | WS04 / DB-013 |
| R5 waitlist concurrency | deferred | Serial proof does not close database race policy. | WS04 / DB-007 |
| R6 Stripe lifecycle, cleanup, retry, reconciliation, provider state equivalence | deferred | B1 fakes Stripe and proves only local serial cap. | WS05 / PAY-008 with provider evidence |
| R7 C3A rate policy and cross-sender race closure | deferred | B1 preserves rate behavior but does not own it. | WS02-04C3A and WS04 |
| R8 image content validation, decoding, sanitization, metadata stripping, re-encoding, derivatives, pixel/resource policy, safe publication, R2 lifecycle | deferred | Current B1 source performs metadata checks only, including acceptance when provider content-type metadata is empty. | WS06 / STO-005 / STO-006 / STO-009 / DBP-03 / DBP-04 |
| Body/header/URL/ingress/provider limits | deferred | B1 owns only selected source-owned values. | B2 |
| Timeout, retry, backpressure, rate, abuse controls | deferred | Outside the source-owned B1 contract. | C passes |
| HTTP/OpenAPI/cache compatibility | deferred | B1 route correction must preserve existing error middleware but does not close HTTP contract. | WS02-05 |
| Staging, deployment, provider, runtime evidence | deferred | Not provable by local pytest. | Provider/runtime owners |

## 9. Adequacy Conclusion

The selected evidence is adequate for WS02-04B1 when the requirement
declaration, this record, six trusted pytest modules, focused workflow pytest
scope, checker file/domain/suite scopes, generated traceability, adjacent
API-error/HTTP-security regression, full trusted backend regression, and
diff/whitespace checks pass.

R1 through R8 require executable trusted evidence. R9 is intentionally
deferred/governance and must have no pytest mapping. Checker `PASS` remains
machine-compliance evidence only; this record supplies the human adequacy
boundary and keeps downstream/provider/runtime gaps explicit.
