# WS02-04B1 - Source-Owned Boundaries

## At A Glance

| Field | Value |
|---|---|
| Pass | `WS02-04B1` |
| Track | `WS02` |
| Type | Domain/API source-boundary recheck |
| Primary controls | `API-M09`, `GOV-006` |
| Authority basis | Accepted WS02-04B1 source-owned selection, WS02-04 source-owned closeout, current repository truth, and the evidence-based limit method from `FDN-04` |
| Depends on | EN-01, EN-02, WS02-03, WS02-04A |
| Trusted test scope | `backend/tests/workflows/source_owned_boundaries` |

WS02-04B1 owns only source-defined product and API boundaries that can be
implemented and proven inside the repository without provider, edge, staging,
deployment, or permanent runtime evidence.

This pass does not make every current numeric value a final production policy.
It freezes the B1-approved source-owned values for selected Platform Notice
audiences, Platform Notice field/list boundaries, public card pagination, Need a
Sub serial collection limits, saved-card serial local active count, chat serial
content/list/history limits, and the selected venue-photo product-flow count.
It also records current source behavior for venue-image declared/stored metadata
checks without treating current byte/type defaults as final image-safety policy.

Gate B must implement only the narrow correction and fresh trusted evidence
defined here. Database concurrency, payment/provider lifecycle, storage
sanitization/publication, body/header/URL, rate, timeout, retry, and runtime
evidence remain with their downstream owners.

## 1. Purpose

Pickup Lane has workflows where repository source already owns finite limits:
admin Platform Notices, public card lists, Need a Sub posts and requests, saved
cards, chats, and venue-image upload initiation. WS02-04B1 turns the approved
source-owned portions of those limits into a durable contract that can be
implemented and tested under EN-01.

The pass answers:

- which source-owned values are B1-approved;
- which values are inherited shared contracts or current implementation only;
- which local serial side effects must be proven;
- which provider, runtime, concurrency, payment, database, and storage risks are
  real but owned by later passes.

## 2. Why This Matters

Unbounded source-owned workflows can produce oversized requests, expensive
queries, partial local state, uncontrolled admin fanout, or oversized user
content before broader provider and runtime protections exist. The opposite
failure is just as risky: a local source pass can falsely claim that provider,
database-concurrency, storage-publication, or runtime facts are production-ready
when no local test can honestly prove them.

WS02-04B1 keeps the two sides separate. It proves the repository-owned serial
contracts that are real today and leaves explicit handoffs for WS04 database
invariants, WS05 payment/provider lifecycle, WS06 storage/image safety, B2
request/provider boundaries, C timeout/retry/rate behavior, and WS02-05 HTTP
contract work.

## 3. Requirements

| ID | Requirement | What it means | Why it matters |
|---|---|---|---|
| WS02-04B1-R1 | Platform Notice selected publish boundaries are finite and sparse. | A selected Platform Notice may target at most 500 unique selected users. Duplicate IDs are deduped before the cap. Over-cap, missing, or ineligible selected users reject before notice rows, recipient rows, admin audit action rows, or commit. Global notices create no selected-recipient membership rows; selected notices create one membership row per unique selected user. Platform Notices do not create ordinary notification rows in the current workflow. | Prevents oversized admin fanout and false notice state while preserving the sparse notice model. |
| WS02-04B1-R2 | Platform Notice field, search, cursor, and list boundaries are source-owned. | Title is 150 characters, message is 4000 characters, cancellation reason is 1000 characters, campaign-history search is 200 characters with at least 3 meaningful letters/numbers, campaign-history pages are max 30, recipient pages default to 50 and max at 100, and recipient cursors must have a route-level encoded length bound of 2000 characters. Selected-user lookup consumes the shared admin lookup route and is not a separate B1-approved numeric policy. | Keeps admin notice input, lookup, and list work finite without inventing wider Platform Notice lookup policy. |
| WS02-04B1-R3 | Public card pagination is source-bounded and deterministic. | Browse Games, My Games, My Need a Sub, and Need a Sub cards default to 40 items, reject limits below 1 at the route layer, clamp limits above 100 at the service layer, bound cursor strings to 2000 characters, reject malformed or foreign-context cursors, and query at most one page plus one extra row. | Prevents unbounded public/user card queries and preserves stable list navigation. |
| WS02-04B1-R4 | Need a Sub post collection limits are enforced before serial persistence. | A Need a Sub post can include at most 6 position rows and 11 total requested substitutes. Duplicate position/group rows, incompatible group combinations, and position totals that do not equal `subs_needed` reject before prohibited post/position persistence. | Prevents oversized or internally inconsistent substitute requests. |
| WS02-04B1-R5 | Need a Sub waitlist cap is enforced for the serial source-owned workflow. | Each post can have at most 25 waitlisted requests. The next serial waitlist request rejects without creating a request row, status-history row, notification, promotion, or other prohibited side effect. Current source locks the post and position during request classification, but B1 does not close broader database-concurrency controls. | Prevents source-owned waitlist growth beyond the product cap while keeping DB race closure with WS04. |
| WS02-04B1-R6 | Saved-card serial local active count is capped. | A user can have at most 5 active local saved cards. Detached or inactive local rows do not count. The fifth serial active card is allowed; the sixth serial active card rejects without persisting a prohibited sixth active local row. Stripe provider state, cleanup, ordering, retries, and concurrency remain outside B1. | Protects the local saved-card product boundary without claiming final payment-provider readiness. |
| WS02-04B1-R7 | Chat serial content, list, and visible-history caps are source-owned. | Game chat and Need a Sub chat text messages are capped at 300 characters after whitespace normalization; participant page reads return at most 50 visible messages; each chat allows at most 200 visible text messages in the serial workflow. Removed/non-visible/non-text rows do not count. Current C3A rate limits remain separate. | Prevents oversized chat content and unbounded visible chat histories without approving rate or cross-sender race behavior. |
| WS02-04B1-R8 | Venue-image source-owned initiation and metadata gates are honestly bounded. | The official-game create flow has a B1-selected product count of at most 3 selected venue photos. Current source also has configured declared size/type checks before upload authorization and stored size/content-type metadata checks before local completion, but current 8 MiB and JPEG/PNG/WebP defaults are current implementation and later WS06 policy inputs, not final B1-approved image-security values. Missing provider content-type metadata does not currently reject completion. | Keeps local venue-image initiation finite while preventing metadata-only checks from being mistaken for safe production image publication. |
| WS02-04B1-R9 | B1 must preserve downstream and external non-closure. | Database-concurrency races, payment/provider lifecycle and cleanup, storage content validation/sanitization/publication, final image byte/type/pixel policy, body/header/URL/ingress/provider limits, timeout/retry/rate controls, staging captures, deployment topology, and provider evidence remain with later owners. | Prevents this source-only pass from falsely closing broader production-readiness controls. |

## 4. Technical Design / Contracts

### 4.1 Authority Classes

Every material value is classified before Gate B:

| Boundary | Value | Authority class | Basis |
|---|---:|---|---|
| Platform Notice selected audience | 500 unique users | B1-owned approved value | Accepted WS02-04B1 source-owned selection and WS02-04 source-owned closeout |
| Platform Notice title | 150 characters | B1-owned approved value | Accepted B1 field/list boundary |
| Platform Notice message | 4000 characters | B1-owned approved value | Accepted B1 field/list boundary |
| Platform Notice cancellation reason | 1000 characters | B1-owned approved value | Accepted B1 field/list boundary |
| Selected-user lookup query max | 120 characters | Inherited/current shared admin lookup contract | Current `GET /admin/lookups/users` route; not separately approved by B1 |
| Selected-user lookup useful term minimum | 3 characters | Inherited/current shared admin lookup contract | Current admin lookup service; not separately approved by B1 |
| Selected-user lookup max terms | 3 terms | Inherited/current shared admin lookup contract | Current admin lookup service; not separately approved by B1 |
| Selected-user lookup result limit | 10 users | Inherited/current shared admin lookup contract | Current admin lookup route/service; not separately approved by B1 |
| Campaign history search | 200 characters | B1-owned approved value | Accepted B1 field/list boundary |
| Campaign history useful-character minimum | 3 letters/numbers | B1-owned approved value | Accepted B1 field/list boundary |
| Campaign history page max | 30 notices | B1-owned approved value | Accepted B1 field/list boundary |
| Recipient page default/max | 50 default, 100 max | B1-owned approved value | Accepted B1 field/list boundary |
| Recipient cursor max | 2000 encoded characters | B1-owned approved value | Accepted B1 field/list boundary and current history/list cursor convention |
| Public card page default/max | 40 default, 100 max | B1-owned approved value | Accepted B1 public pagination boundary |
| Public card minimum | route rejects below 1 | B1-owned approved semantics | Accepted B1 public pagination boundary and current route validation |
| Public card cursor max | 2000 encoded characters | B1-owned approved value | Accepted B1 public pagination boundary |
| Need a Sub position rows | 6 rows | B1-owned approved value | Accepted B1 collection boundary |
| Need a Sub total substitutes | 11 substitutes | B1-owned approved value | Accepted B1 collection boundary |
| Need a Sub waitlist | 25 waitlisted requests | B1-owned approved value | Accepted B1 collection boundary |
| Saved-card active local rows | 5 active cards | B1-owned approved value | Accepted B1 saved-card boundary |
| Chat message body | 300 characters | B1-owned approved value | Accepted B1 chat boundary |
| Chat page size | 50 visible messages | B1-owned approved value | Accepted B1 chat boundary |
| Chat visible history | 200 visible text messages | B1-owned approved value | Accepted B1 chat boundary |
| Venue selected-photo count | 3 selected photos | B1-owned approved value | Accepted B1 venue-image product-flow boundary |
| Venue image byte default | 8 MiB | Current implementation only / later WS06 input | Current R2 settings default; exact production file-size policy remains WS06 |
| Venue image declared types | JPEG, PNG, WebP | Current implementation only / later WS06 input | Current R2 settings default; final production format policy remains WS06 |
| Pixel, decoding, sanitization, metadata stripping, derivatives | Not implemented by B1 | Later-pass/external value | DBP-03, WS06-02, WS06-03 |

### 4.2 Platform Notice

The Platform Notice service is authoritative for selected publish semantics.
`selected_user_ids` are normalized to a unique UUID list sorted by string value
before the 500-user cap is applied. More than 500 unique IDs raises a service
owned 400 response before eligibility checks, notice insertion, recipient
insertion, admin-action insertion, or commit.

For selected notices, every selected user must exist and be currently eligible
before the notice is persisted. Missing or ineligible users reject before notice
persistence. Global notices receive a global sequence and no selected-recipient
membership rows. Selected notices receive no global sequence and one membership
row per unique selected user. The current Platform Notice workflow does not
create ordinary notification rows or provider delivery work.

Field and list contracts:

| Boundary | Current contract |
|---|---|
| Title | Backend schema/service normalize and trim single-line text; blank, control-character, and over-150-character values reject. |
| Message | Backend schema/service normalize line endings and trim; blank, control-character, and over-4000-character values reject. |
| Cancellation reason | Backend schema/service trim/collapse whitespace; blank, control-character, and over-1000-character values reject. |
| Campaign-history search | Route and service bound normalized search to 200 characters; active search requires at least 3 alphanumeric meaningful characters. |
| Campaign-history page | Route rejects outside 1 through 30; service keeps an internal max of 30 and uses `limit + 1`. |
| Recipient page | Route rejects outside 1 through 100; service keeps an internal max of 100 and uses `limit + 1`. |
| Recipient cursor | Gate B must add the missing route-level `max_length=2000` encoded cursor bound while preserving malformed-cursor 400 behavior. |
| Selected-user lookup | Platform Notices consume the shared admin user lookup route. B1 does not approve separate lookup values or require frontend parity beyond the already B1-owned selected-audience cap. |

FastAPI/Pydantic validation errors are inherited from WS02-04A as stable 422
validation envelopes. Service-owned boundary failures remain service-owned HTTP
errors with stable normalization from WS02-04A. Gate B must not redesign error
codes, status classes, correlation behavior, authorization, or response shape.

### 4.3 Public Card Pagination

The B1 public card surfaces are:

| Surface | Default | Minimum | Maximum | Cursor |
|---|---:|---|---:|---|
| Browse Games | 40 | route rejects below 1 | service clamps above 100 | max 2000 characters |
| My Games | 40 | route rejects below 1 | service clamps above 100 | max 2000 characters |
| My Need a Sub | 40 | route rejects below 1 | service clamps above 100 | max 2000 characters |
| Need a Sub cards | 40 | route rejects below 1 | service clamps above 100 | max 2000 characters |

Malformed cursor payloads and cursor/query-context mismatches raise
service-owned 400 responses. All four services order by complete deterministic
tuples that include row identity and request `limit + 1` rows to determine
`has_more`.

B1 does not close the broader `DB-013` concerns of concurrent insert/update/delete
stability, stale-sort-key behavior beyond the current source contract,
production query plans, or database-provider performance evidence.

### 4.4 Need a Sub

Post create/update schemas reject more than 6 position rows and
`subs_needed` above 11. Service validation rechecks the same caps, requires
position spots to sum exactly to `subs_needed`, rejects duplicate
position/group rows, rejects `open` mixed with men/women rows for the same
position, and rejects player groups incompatible with the post group. These
checks happen before prohibited post/position persistence in the serial
workflow.

Request creation locks the post and requested position rows in current source
before queue/waitlist classification. The waitlist cap counts active
`sub_waitlist` request rows for the post. If the post already has 25
waitlisted requests, the next serial waitlist request raises a service-owned
400 response before request insertion, status-history insertion, notification,
promotion, or commit.

B1 may record the current lock context because it affects current source
behavior. It must not claim final `DB-007` or deterministic concurrency closure.
Broader database invariant proof remains with WS04 and later current-test
coverage.

### 4.5 Saved Cards

The saved-card cap counts local rows with `method_status == "active"`.
Detached and expired/inactive rows do not count. In the serial local workflow,
the fifth active card is allowed and the sixth active card raises a
service-owned 400 response before a prohibited sixth active local row is
persisted.

Current sync retrieves Stripe SetupIntent and PaymentMethod state before the
local cap check, may detach an unpersisted Stripe payment method when the cap
is exceeded, and may set a Stripe default before local persistence when the new
card should be default. Those provider/local ordering, cleanup, retry,
divergence, and concurrency concerns are real handoffs to WS05/PAY-008 with
WS04 database-transaction dependencies and provider evidence. B1 tests must
fake Stripe at the application-owned boundary and must not contact Stripe.

### 4.6 Chat

Game chat and Need a Sub chat share these B1 serial values:

| Surface | Message body | Page size | Visible text history cap |
|---|---:|---:|---:|
| Game chat | 300 characters | 50 visible messages | 200 visible text messages |
| Need a Sub chat | 300 characters | 50 visible messages | 200 visible text messages |

Message bodies are whitespace-normalized and blank messages reject with
service-owned 400 responses. Page reads clamp to 50 and lower values to 1 in
service code. The 200-message cap counts visible text messages only; removed,
non-visible, and non-text rows do not count.

Game-chat sends execute the C3A sender/chat rate limiter before the total
history cap. That rate limiter is sender-specific and does not prove
cross-sender serialization of the 200-message cap. B1 evidence for the
game-chat history cap must avoid accidentally hitting the 429 rate limit and
must prove the serial B1 invariant. Cross-sender race closure remains with WS04
and later current-test coverage.

Need a Sub chat currently locks the owning post before message classification
and the total cap check. B1 may record that current source context, but still
does not close broader database-concurrency controls.

### 4.7 Venue Images

B1 owns the selected-photo product-flow count: the current official-game create
flow selects at most 3 venue photos. Backend upload authorization also has
source-owned metadata gates that currently validate declared role, declared
content type, and declared size before issuing an upload URL. Completion checks
stored object size before local activation and checks stored object content
type only when the provider returns non-empty content-type metadata.

The current defaults for the metadata gates are:

- max image bytes: 8 MiB;
- declared image types: `image/jpeg`, `image/png`, `image/webp`.

Those defaults are current implementation and configuration evidence only.
They are not final B1-approved production image security policy. DBP-03 and
WS06 retain final ownership for actual file-content validation, magic-byte or
decode checks, byte/pixel/decompression limits, sanitization, metadata
stripping, re-encoding, derivatives, safe publication state, provider
lifecycle, reconciliation, and R2/runtime evidence.

Current source can mark an image `active` after metadata-only completion.
That is current truth and a WS06 production-readiness gap, not a B1 closure.
Gate B must not modify venue image production/frontend source solely to create
a test hook.

## 5. Implementation Scope

Gate B may modify or create only the files listed here unless human review
returns the pass to Gate A.

Production/backend correction:

- `backend/routes/platform_notice_routes.py`: add only the missing route-level
  `max_length=2000` encoded cursor bound to
  `GET /admin/platform-notices/{notice_id}/recipients`.

Frontend corrections:

- None. Current Platform Notice selected-audience frontend behavior is already
  present. Shared admin lookup values are not separate B1-approved frontend
  policy. Venue-photo frontend source must not be refactored solely for
  testability.

Testing/evidence artifacts to create:

- `backend/tests/support/requirements/ws02_04b1.json`
- `backend/tests/workflows/source_owned_boundaries/TESTING_RECORD.md`
- `backend/tests/workflows/source_owned_boundaries/test_platform_notice_boundaries.py`
- `backend/tests/workflows/source_owned_boundaries/test_public_card_pagination_contract.py`
- `backend/tests/workflows/source_owned_boundaries/test_need_a_sub_collection_limits.py`
- `backend/tests/workflows/source_owned_boundaries/test_saved_card_limit_contract.py`
- `backend/tests/workflows/source_owned_boundaries/test_chat_boundary_contract.py`
- `backend/tests/workflows/source_owned_boundaries/test_venue_image_upload_boundaries.py`

Gate B must not modify:

- `backend/services/game_chat_service.py`
- `backend/services/payment_method_service.py`
- `backend/services/venue_image_service.py`
- `frontend/src/pages/admin/platform-notices/adminPlatformNoticeData.js`
- `frontend/src/pages/admin/platform-notices/AdminPlatformNoticesPage.jsx`
- `frontend/src/pages/admin/official-games/create/adminCreateOfficialGameData.js`
- `frontend/src/pages/admin/official-games/create/AdminCreateOfficialGamePage.jsx`
- program context, limits register, templates, unrelated governance, or any
  downstream WS04/WS05/WS06 implementation file.

No model, migration, provider, network, worker, deployment, or frontend
production refactor is approved by this pass.

## 6. Testing And Evidence

Fresh backend evidence belongs under
`backend/tests/workflows/source_owned_boundaries/`, a trusted EN-01 root because
B1 spans cross-domain workflow behavior rather than one platform primitive.
Tests must use stable requirement markers from `ws02_04b1.json`.

Backend proof layers:

- FastAPI/TestClient for route query/schema behavior, HTTP status class, and
  stable WS02-04A validation/error normalization.
- Service/domain proof where the service owns normalization, deduplication,
  clamping, or cap behavior.
- PostgreSQL-backed serial-state proof where B1 must prove accepted persisted
  state, rejected prohibited state, rollback/no partial write, active/inactive
  saved-card counting, sparse Platform Notice state, Need a Sub serial
  persisted limits, chat serial visible-history limits, or venue local metadata
  state.
- Provider fakes at Stripe/R2 application-owned boundaries. Tests must not
  contact real Stripe, R2, Firebase, email, hosting, or other providers.
- Source/static review in the testing record where executable proof would
  require a production refactor solely for testability or would overclaim a
  provider/runtime fact.

Concurrency evidence:

- B1 does not require deterministic concurrent-session tests to prove WS04,
  WS05, or WS06 race closure.
- The TESTING_RECORD must record discovered race and provider/local ordering
  gaps with their downstream owners.
- B1 serial PostgreSQL evidence remains required where persisted local effects
  are part of the B1 source contract.

Frontend evidence:

- No new frontend executable artifact is required by Gate B.
- Existing Platform Notice frontend unit coverage may be rerun as supporting UX
  evidence for the selected-audience cap, but backend/source evidence remains
  authoritative for server protection.
- Venue-photo frontend preflight is supporting source-review evidence only for
  B1. Do not refactor production frontend code solely to call the helper from a
  test.
- Playwright is not required because no browser-only B1 invariant is selected.

Controlled time:

- Use one controlled baseline where future dates, pagination order, chat setup,
  or Need a Sub eligibility depend on time.

Non-executable evidence:

- The testing record must explain why local B1 evidence does not prove
  provider/runtime behavior, DBP-03 image safety, WS04 concurrency invariants,
  WS05 payment/provider lifecycle, WS06 storage publication, B2/C boundaries,
  or WS02-05 HTTP contract closure.

## 7. Integration / Operational Expectations

WS02-04B1 depends on:

- EN-01 trusted test taxonomy, PostgreSQL safety, requirement metadata, and
  checker scope policy;
- EN-02 safe correlation, public error, redaction, event, and telemetry
  primitives;
- WS02-03 API response security/header foundations where applicable;
- WS02-04A stable application error envelopes and safe validation handling;
- WS02-04C3A chat rate-limit behavior, which B1 must preserve but not own;
- WS02-04B2/B2A/B2C request/provider/body/header/URL ownership;
- WS02-05 request/response/OpenAPI/cache compatibility work;
- downstream WS04/WS05/WS06 work for the discovered database, payment, and
  storage gaps.

The pass must preserve current authorization, stable error normalization,
correlation behavior, idempotency behavior, provider boundary fakes in tests,
and production source behavior outside the single approved recipient-cursor
correction.

## 8. Not Part Of This Pass

WS02-04B1 does not implement or prove:

- global request-body, multipart, header, URL, export, or bulk-operation limits;
- process-server, ingress, CDN, WAF, edge, proxy, or provider precedence;
- timeout, retry, cancellation, backpressure, durable worker, queue, delivery
  concurrency, or batch-size policy;
- new rate limits, abuse thresholds, or the C3A 5-per-60-second chat policy;
- database-enforced serialization for saved cards, game chat, venue image
  selected-count, public cursor race behavior, or broader Need a Sub invariants;
- Stripe dashboard settings, provider state equivalence, provider retries,
  provider cleanup, or payment lifecycle closure;
- final venue image byte/type/pixel policy, actual content validation,
  magic-byte/decode checks, sanitization, metadata stripping, re-encoding,
  derivatives, safe publication lifecycle, R2 retention, CDN behavior, direct
  upload runtime enforcement, or provider metadata reliability;
- production/staging/runtime captures, provider dashboards, or permanent
  hosting evidence;
- response minimization, OpenAPI/media/cache contracts, browser route guards, or
  unrelated frontend behavior;
- program-context, workflow-template, limits-register, or unrelated governance
  maintenance during Gate B.

## 9. Related Controls And Remaining Evidence

B1 advances:

- `API-M09` for the approved source-owned request, query, pagination, search,
  collection, and local metadata boundaries listed in this plan.
- `GOV-006` through a bounded B1 value record that must not be broadened beyond
  the source-owned values.

B1 depends on but does not close:

- `DB-005`, `DB-006`, `DB-007`, and `DB-013` for persisted effects,
  transaction/side-effect classification, serialization, and pagination
  concerns. WS04 is the primary owner for database invariant and deterministic
  concurrency closure.
- `PAY-008` for saved-payment metadata and Stripe ownership. WS05 is the
  primary owner for provider lifecycle, reconciliation, retries, cleanup, and
  payment concurrency.
- `STO-005`, `STO-006`, `STO-009`, `DBP-03`, and `DBP-04` for venue-image and
  R2 storage safety. WS06 is the primary owner for file validation,
  sanitization, safe publication, lifecycle, reconciliation, and provider
  evidence.
- `API-M10` and `API-M11` for timeouts, retry/backpressure, rate, and abuse
  controls owned by C passes.
- `API-M13`, `API-M14`, `API-M16`, `API-M18`, and `API-M19` where WS02-05 owns
  HTTP contract, schema, cache, and edge-to-origin compatibility evidence.

Remaining evidence after B1:

- B2 owns body/header/URL/ingress/provider/staging request-boundary evidence
  outside the source-owned B1 values.
- C owns timeout, retry, backpressure, rate, and provider-cost controls outside
  B1 serial local boundaries.
- WS04 owns database constraints, locks, independent-session race proof, and
  invariant catalog closure.
- WS05 owns payment/saved-card provider lifecycle, reconciliation, Stripe
  sandbox/deployed evidence, and durable financial workflow closure.
- WS06 owns venue-image processing, publication, R2 lifecycle, cleanup,
  reconciliation, recovery, and storage provider evidence.
- Provider/runtime/staging/deployment owners must provide sanitized evidence
  for facts not provable from local source.

## 10. Completion Criteria

- [ ] Canonical WS02-04B1 plan uses the reusable pass-planning structure and
  contains no implementation diary, branch/PR/SHA history, historical-test
  narrative, unrelated workflow maintenance, or unrelated governance cleanup.
- [ ] `backend/tests/support/requirements/ws02_04b1.json` declares the final
  WS02-04B1 requirements with stable IDs, truthful `source_controls`, states,
  scopes, and reasons for deferred/later obligations.
- [ ] Platform Notice selected audience, deduplication, eligibility,
  pre-mutation rejection, sparse persistence, field/search/list pagination, and
  recipient cursor bounds are corrected or proven within the B1 source scope.
- [ ] Public Browse Games, My Games, My Need a Sub, and Need a Sub card
  pagination defaults, minimums, maximums, cursor bounds, malformed/context
  failures, deterministic ordering, and `limit + 1` query shape are proven for
  the current source contract.
- [ ] Need a Sub post position-row, total-substitute, duplicate/incompatible
  row, total-sum, pre-persistence rejection, and waitlist serial cap behavior
  are proven without claiming broad DB concurrency closure.
- [ ] Saved-card serial local active-cap behavior is proven for active versus
  detached/inactive rows, fifth accepted card, sixth serial rejection, and no
  prohibited local sixth active row, while provider/local ordering and
  concurrency gaps remain deferred.
- [ ] Game chat and Need a Sub chat serial message-body, page-size, visible
  history, removed/non-visible/non-text counting, and rate-limit interaction
  boundaries are proven without claiming cross-sender race closure.
- [ ] Venue image selected-count and current source metadata gates are proven or
  source-reviewed only to the extent B1 owns them; final image content safety,
  byte/type/pixel policy, publication, and R2/provider behavior remain WS06.
- [ ] `backend/tests/workflows/source_owned_boundaries/TESTING_RECORD.md`
  records requirement/risk groups, scenario selection, serial persisted-state
  proof, PostgreSQL decisions, provider fakes, frontend boundaries, and
  downstream DB/payment/storage/runtime gaps.
- [ ] Checker domain scope for
  `backend/tests/workflows/source_owned_boundaries`, checker suite scope,
  relevant backend pytest, requirement traceability, and `git diff --check`
  pass during Gate B.
- [ ] No deterministic concurrency proof, provider/network proof, Playwright
  proof, migration proof, production data, provider secrets, or legacy/untrusted
  test evidence is used to close B1.
