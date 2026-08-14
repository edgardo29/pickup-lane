# WS02-04B2A2B1 - Route Lifecycle Cleanup

## At A Glance

| Field | Value |
|---|---|
| Pass | `WS02-04B2A2B1` |
| Track | `WS02` |
| Type | API route-lifecycle / request-surface recheck |
| Plain-English purpose | Retire obsolete, duplicate, and scaffolded route surfaces while preserving active product workflows. |
| Primary controls | `API-M09` |
| Supporting / downstream controls | `API-M13`, `API-M18`, `GOV-006`, `ADM-001`, `ADM-004`, `IAM-017`, `DB-005`, `PAY-009`, `PAY-010` |
| Depends on | `EN-01`; `WS02-04B1`; `WS02-04B2A1`; `WS02-04B2A2A`; ownership handoffs to `WS02-04B2A2B2`, `WS02-04B2A2B3`, `WS02-04B2A2C`, `WS02-05A`, `WS02-05B1`, `WS02-05B2`, `WS03`, `WS05`, and `WS06`. |
| Policy / lifecycle authority | Applicable API/control requirements; accepted WS02-04 source-owned closeout; accepted remediation, blueprint, and decision records authorizing obsolete mutation cleanup; accepted later ownership records where they preserve tombstone or replacement boundaries. |
| Implementation truth | Current accepted repository route table, current backend implementation, and current frontend callers. |
| Trusted evidence scope | `backend/tests/workflows/route_lifecycle_cleanup` |
| Implementation type | Trusted evidence and traceability only, unless a human-approved correction changes the frozen scope. |
| Production/backend correction set | None. |
| Frontend correction set | None. |

## 1. Purpose

WS02-04B2A2B1 is the route-lifecycle cleanup slice of the WS02-04B2A2B split.
It proves that obsolete body-bearing mutation surfaces, duplicate action routes,
and scaffolded admin notification write routes are no longer usable public write
APIs, while keeping supported product flows available through canonical
service-owned routes.

The pass exists because a route should not continue accepting a public request
body merely because the model, service, or old scaffold still exists. When a
workflow is server-derived, internally owned, or replaced by a more specific
action endpoint, the obsolete route must become an authenticated, bodyless,
non-mutating compatibility tombstone instead of another place where clients can
attempt to write lifecycle state.

Current source establishes what is implemented. It does not independently
approve route-lifecycle policy. The policy authority for this pass comes from
the applicable controls, accepted WS02-04 closeout, and accepted ownership
records that assign route retirement and replacement-route preservation.

## 2. Why This Matters

Pickup Lane has several state transitions that must be owned by product
services instead of generic CRUD endpoints:

- bookings, participants, waitlists, host fees, venues, images, approvals,
  settings, stats, chats, status histories, admin actions, and booking-policy
  acceptances;
- admin notification creation and mutation scaffolds;
- Need-a-Sub admin enforcement removal;
- official-game player removal;
- official-game host removal.

If obsolete routes were still usable, a caller could bypass validation, audit
derivation, notification behavior, moderation review linkage, payment or credit
side effects, and other workflow-owned rules. Even if a route failed later,
accepting and parsing the request body would still make it part of the active
request surface and would leave WS02-04 ordinary JSON limits with more endpoints
to govern.

This pass reduces that surface honestly. It does not claim that every API
request-body concern is finished. Provider/payment metadata, policy/legal
ownership, ordinary JSON size limits, OpenAPI/cache representation, identity
ownership, storage/provider evidence, database concurrency, and broader
request/response minimization remain in their owning passes.

## 3. Requirements

| Requirement | State | Current contract | Evidence owner |
|---|---|---|---|
| `WS02-04B2A2B1-R1` | Required | The 35 B2A2B1-retired mutation routes are registered only as intended compatibility tombstones. Each route preserves the authentication boundary, returns HTTP 410 to authenticated callers as lifecycle behavior, has no FastAPI request-body field, has no manual body parsing, and has no database/session dependency or retired mutation-service/provider work. B1 does not own the exact public error envelope or representation. | `backend/tests/workflows/route_lifecycle_cleanup` |
| `WS02-04B2A2B1-R2` | Required | Generic CRUD, scaffolded lifecycle writes, and retired admin notification write scaffolds for bookings, participants, waitlists, host publish fees, venues, game images, venue approvals, user settings, user stats, game chats, admin actions, status histories, booking-policy acceptances, and admin notification POST/PATCH routes cannot be used to fabricate state. Supported reads and service-owned workflows remain outside the tombstone set. | `backend/tests/workflows/route_lifecycle_cleanup` |
| `WS02-04B2A2B1-R3` | Required | The duplicate Need-a-Sub removal route is retired, and the canonical admin removal action remains `POST /admin/need-a-sub/{post_id}/remove`. | `backend/tests/workflows/route_lifecycle_cleanup` |
| `WS02-04B2A2B1-R4` | Required | The retired official-game player `DELETE` route stays unavailable, and the canonical player removal flow remains the POST preview/execute pair. | `backend/tests/workflows/route_lifecycle_cleanup` |
| `WS02-04B2A2B1-R5` | Required | The retired official-game host `DELETE` route stays unavailable, and the canonical host removal action remains `POST /admin/official-games/{game_id}/host/remove` with a compatible reason-bearing body shape. A2A owns the reason-field bound; B1 owns only lifecycle and replacement-route shape. | `backend/tests/workflows/route_lifecycle_cleanup` |
| `WS02-04B2A2B1-R6` | Required | Current production frontend callers and current trusted backend support/setup helpers do not depend on retired B1 routes. Caller compatibility is preserved through canonical active routes. | `backend/tests/workflows/route_lifecycle_cleanup` |
| `WS02-04B2A2B1-R7` | Deferred | Broader HTTP/OpenAPI/cache/tombstone representation, ordinary JSON request limits, provider/payment input ownership and provider evidence, policy/legal ownership, request/response ownership outside B1, identity/account ownership, database concurrency, storage/provider evidence, tombstone removal timing, and external runtime/provider evidence are not closed by B1. | Governance / downstream owners |

### Exact Requirement Declaration Metadata

Pass implementation must add one stable declaration file:

- `backend/tests/support/requirements/ws02_04b2a2b1.json`

The exact declaration metadata is frozen as follows:

| ID | State | Scope | `source_controls` | Reason |
|---|---|---|---|---|
| `WS02-04B2A2B1-R1` | `required` | `workflows/route_lifecycle_cleanup` | `["API-M09", "WS02-04B2A2B1"]` | Not required. |
| `WS02-04B2A2B1-R2` | `required` | `workflows/route_lifecycle_cleanup` | `["API-M09", "ADM-001", "ADM-004", "DB-005", "WS02-04B2A2B1"]` | Not required. |
| `WS02-04B2A2B1-R3` | `required` | `workflows/route_lifecycle_cleanup` | `["API-M09", "IAM-017", "WS02-04B2A2B1"]` | Not required. |
| `WS02-04B2A2B1-R4` | `required` | `workflows/route_lifecycle_cleanup` | `["API-M09", "IAM-017", "WS02-04B2A2B1"]` | Not required. |
| `WS02-04B2A2B1-R5` | `required` | `workflows/route_lifecycle_cleanup` | `["API-M09", "IAM-017", "WS02-04B2A2A", "WS02-04B2A2B1"]` | Not required. |
| `WS02-04B2A2B1-R6` | `required` | `workflows/route_lifecycle_cleanup` | `["API-M09", "WS02-04B2A2B1"]` | Not required. |
| `WS02-04B2A2B1-R7` | `deferred` | `governance` | `["API-M09", "API-M13", "API-M14", "API-M18", "GOV-006", "DB-005", "PAY-009", "PAY-010", "WS02-04B2A2B2", "WS02-04B2A2B3", "WS02-04B2A2C", "WS02-05A", "WS02-05B1", "WS02-05B2", "WS03", "WS05", "WS06"]` | `HTTP/OpenAPI/cache/tombstone representation, ordinary JSON body limits, provider/payment input ownership and provider evidence, policy/legal ownership, request/response ownership outside B1, identity/account ownership, database concurrency, storage/provider evidence, tombstone removal timing, and external runtime/provider evidence remain with downstream owners and cannot be closed by local B1 route-lifecycle evidence.` |

`WS02-04B2A2B1-R7` is non-executable and must have zero pytest mappings.

## 4. Technical Design / Contracts

### B1 Tombstone Contract

Every B1-retired route must satisfy this lifecycle contract:

- The expected method/path remains registered as the intended compatibility
  tombstone.
- The route preserves the active-admin authentication boundary before returning
  the tombstone response.
- Authenticated callers receive HTTP 410.
- The route has no FastAPI request-body model or body field.
- The route does not manually read `Request.body()`, `Request.json()`,
  `Request.form()`, `Request.stream()`, or any equivalent body reader.
- The route does not acquire `get_db`, open a database session, call mutation
  services, or perform provider/network work.
- The route uses the current shared retired-route mechanism where applicable.
- Stale submitted JSON does not become an active request contract.

B1 does not own the exact public error-envelope representation, error-code or
message wording, media type, cache headers, OpenAPI schema/deprecation
representation, 405 behavior, or removal/deprecation timing. Those remain
WS02-05A or later-owner responsibilities. B1 owns only lifecycle retirement,
bodyless/no-retired-mutation behavior, and replacement-route preservation.

### Current B1 Retired Route Inventory

The current accepted route table contains exactly 35 B2A2B1-retired mutation
route registrations.

`GET /notifications` is a real current authenticated 410 tombstone, but it is
not a mutation route, is not body-bearing, and is outside B2A2B1 scope. Current
source establishes that route exists; it does not assign the route to this
pass.

| Route family | B1-retired routes | Count/classification |
|---|---|---|
| Bookings | `POST /bookings`; `PATCH /bookings/{booking_id}` | 2 mutation tombstones |
| Game participants | `POST /game-participants`; `PATCH /game-participants/{participant_id}` | 2 mutation tombstones |
| Waitlist entries | `POST /waitlist-entries`; `PATCH /waitlist-entries/{waitlist_entry_id}` | 2 mutation tombstones |
| Host publish fees | `POST /host-publish-fees`; `PATCH /host-publish-fees/{host_publish_fee_id}` | 2 mutation tombstones |
| Venues | `POST /venues`; `PATCH /venues/{venue_id}` | 2 mutation tombstones |
| Game images | `POST /game-images`; `PATCH /game-images/{game_image_id}` | 2 mutation tombstones |
| Venue approval requests | `POST /venue-approval-requests`; `PATCH /venue-approval-requests/{venue_approval_request_id}` | 2 mutation tombstones |
| User settings | `POST /user-settings`; `PATCH /user-settings/{user_id}` | 2 mutation tombstones |
| User stats | `POST /user-stats`; `PATCH /user-stats/{user_id}` | 2 mutation tombstones |
| Game chats | `POST /game-chats`; `PATCH /game-chats/{game_chat_id}` | 2 mutation tombstones |
| Admin actions | `POST /admin/actions`; `POST /admin/actions/{admin_action_id}/notes` | 2 mutation tombstones |
| Game status history | `POST /game-status-history`; `PATCH /game-status-history/{history_id}` | 2 mutation tombstones |
| Booking status history | `POST /booking-status-history`; `PATCH /booking-status-history/{history_id}` | 2 mutation tombstones |
| Participant status history | `POST /participant-status-history`; `PATCH /participant-status-history/{history_id}` | 2 mutation tombstones |
| Booking-policy acceptances | `POST /booking-policy-acceptances`; `PATCH /booking-policy-acceptances/{booking_policy_acceptance_id}` | 2 mutation tombstones |
| Admin notifications | `POST /notifications`; `PATCH /notifications/{notification_id}` | 2 mutation tombstones |
| Need-a-Sub duplicate removal | `PATCH /need-a-sub/posts/{sub_post_id}/remove` | 1 mutation tombstone |
| Official-game player retired removal | `DELETE /admin/official-games/{game_id}/participants/{participant_id}` | 1 mutation tombstone |
| Official-game host retired removal | `DELETE /admin/official-games/{game_id}/host` | 1 mutation tombstone |

### Preserved Active Workflows

B1 must not break or replace supported workflows. The preserved current active
surfaces include:

- booking, roster, waitlist, host-fee, venue, image, approval, stats, chat,
  audit, status-history, and booking-policy-acceptance reads;
- `/user-settings/me` and `/user-stats/me`;
- scoped game-chat and Need-a-Sub chat workflows;
- official-game create/update, roster, cancellation, preview, execute, and host
  removal actions;
- active admin notification lookup/read workflows;
- active admin venue-image upload, authorization, stored-object verification,
  moderation, and selected-image capacity behavior.

No database model or migration change is part of this pass.

### Canonical Replacement Routes

The following replacements are in scope for preservation evidence:

| Replaced route | Canonical active route |
|---|---|
| `PATCH /need-a-sub/posts/{sub_post_id}/remove` | `POST /admin/need-a-sub/{post_id}/remove` |
| `DELETE /admin/official-games/{game_id}/participants/{participant_id}` | `POST /admin/official-games/{game_id}/participants/{participant_id}/remove-preview`; `POST /admin/official-games/{game_id}/participants/{participant_id}/remove` |
| `DELETE /admin/official-games/{game_id}/host` | `POST /admin/official-games/{game_id}/host/remove` |

The active frontend callers must continue targeting the canonical POST actions,
not the retired DELETE or duplicate PATCH routes.

### Negative Space And Cross-Pass Ownership

B1 must not expand into adjacent ownership areas:

- WS02-04B2A2A owns active workflow request-field allowlists, type bounds, and
  selected request-shape rules, including the approved reason-field bound where
  a preserved replacement action uses one.
- WS02-04B2A2B2 owns provider, payment, opaque metadata, checkout return URL,
  and inbox-provider evidence boundaries.
- WS02-04B2A2B3 owns policy/legal authoring and policy-acceptance request
  ownership.
- WS02-04B2A2C owns ordinary JSON body-size policy after obsolete route cleanup
  is complete.
- WS02-05A owns HTTP/OpenAPI/cache/tombstone representation.
- WS02-05B1 owns request ownership and mass-assignment cleanup beyond this
  route-lifecycle slice.
- WS02-05B2 owns response minimization.
- WS03 owns identity and account-lifecycle behavior.
- WS05 owns payment/refund/provider-side correctness.
- WS06 owns storage and object-provider evidence.

Current generic `/users` mutation routes are disabled identity surfaces and do
not define B1 body-bearing lifecycle cleanup. The active `DELETE /venues/{venue_id}`
route is a bodyless admin mutation and is not a B1-retired route; any future
policy change for that route requires a separate owner decision.

## 5. Implementation Scope

### Pass-Owned Artifacts

The pass-owned implementation and evidence set is exactly:

- `backend/tests/support/requirements/ws02_04b2a2b1.json`
- `backend/tests/workflows/route_lifecycle_cleanup/TESTING_RECORD.md`
- `backend/tests/workflows/route_lifecycle_cleanup/test_retired_route_registration_contract.py`
- `backend/tests/workflows/route_lifecycle_cleanup/test_retired_route_http_contract.py`
- `backend/tests/workflows/route_lifecycle_cleanup/test_retired_route_source_contract.py`
- `backend/tests/workflows/route_lifecycle_cleanup/test_replacement_route_contract.py`

No production application code, frontend application code, database migrations,
provider integrations, CI configuration, or unrelated files are in the frozen
implementation/evidence set.

### Production Code Corrections

Production/backend correction set: none.

The current route table already presents the B1 tombstone shape that trusted
evidence must prove: bodyless, authenticated, non-mutating, and
replacement-preserving.

If implementation evidence discovers that a retired route still parses a body,
bypasses authentication, reaches a database/service mutation, or leaves a stale
active caller, the production correction set requires renewed human approval
before it can expand.

### Frontend Corrections

Frontend correction set: none.

Current production frontend callers target the canonical active routes. Caller
compatibility evidence belongs in the route-lifecycle evidence set rather than
new frontend source changes.

## 6. Testing And Evidence

### Trusted Test Root

Trusted tests live under:

- `backend/tests/workflows/route_lifecycle_cleanup`

This is a current EN-01 trusted backend test root. The tests must not derive
authority from historical or pre-reset test material.

### Required Trusted Test Modules

The required evidence modules are:

| Test module | Evidence responsibility |
|---|---|
| `test_retired_route_registration_contract.py` | Introspect the real FastAPI route table and prove all 35 B2A2B1-retired mutation routes are registered as expected, have no FastAPI body field, preserve the active-admin dependency, do not depend on `get_db`, and have no B2A2B1 bypass or duplicate active route alias. |
| `test_retired_route_http_contract.py` | Use `TestClient` with controlled active-admin dependency overrides to prove representative and grouped coverage for the 35 retired mutation routes: HTTP 410 for no-body and body-bearing requests, no body validation, and no submitted sentinel content reflected as an accepted request contract. Include representative unauthenticated checks proving the authentication boundary remains in front of the tombstone. Do not assert the exact public error-envelope wording, media type, cache headers, OpenAPI representation, or other WS02-05A-owned details. |
| `test_retired_route_source_contract.py` | Use static source/AST evidence over the 35 retired mutation handler functions themselves to prove they do not accept request-body parameters, do not manually read request bodies, do not call database/session dependencies, and do not call mutation services. The source proof must not fail merely because the same route module also contains active read routes that legitimately use `get_db`. |
| `test_replacement_route_contract.py` | Prove canonical replacement routes remain registered with the expected methods and body shape; prove current frontend production API helpers/callers use canonical active routes instead of retired B1 paths; and prove current trusted backend support/setup helpers do not invoke retired B1 routes as fixture/setup shortcuts. Backend-support inspection must use only current trusted EN-01 roots/support machinery and must not infer product requirements from tests. |

### Evidence-Layer Decisions

The tests should use the lowest honest layer that proves the contract:

- Route registration and dependency evidence uses the real FastAPI route table.
- HTTP evidence proves lifecycle behavior without taking ownership of
  WS02-05A's full response representation.
- Source/AST evidence inspects retired handler functions themselves rather than
  module-level imports.
- Frontend production caller compatibility uses source/static contract checks
  plus existing read-only unit coverage where materially useful.
- Backend trusted support dependency proof is executable/static evidence inside
  the existing route-lifecycle evidence set.
- PostgreSQL is not required because the retired route contract forbids `get_db`
  and mutation-service calls.
- Provider/network evidence is not required.
- Playwright/browser evidence is not required.
- Migrations are not required.
- Genuine concurrency evidence is not required.
- Controlled time evidence is not required.

### Required Validation

Required validation commands are:

```bash
backend/.venv/bin/python -m pytest -q backend/tests/workflows/route_lifecycle_cleanup
backend/.venv/bin/python -m pytest -q backend/tests/checker
backend/.venv/bin/python backend/tests/check_backend_tests.py --scope file backend/tests/workflows/route_lifecycle_cleanup/test_retired_route_registration_contract.py
backend/.venv/bin/python backend/tests/check_backend_tests.py --scope file backend/tests/workflows/route_lifecycle_cleanup/test_retired_route_http_contract.py
backend/.venv/bin/python backend/tests/check_backend_tests.py --scope file backend/tests/workflows/route_lifecycle_cleanup/test_retired_route_source_contract.py
backend/.venv/bin/python backend/tests/check_backend_tests.py --scope file backend/tests/workflows/route_lifecycle_cleanup/test_replacement_route_contract.py
backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/workflows/route_lifecycle_cleanup
backend/.venv/bin/python backend/tests/check_backend_tests.py --scope suite
git diff --check
```

If the exact local virtualenv path is unavailable, use the repository's active
backend Python environment and report the substitution.

## 7. Integration / Operational Expectations

B1 should leave active operations unchanged:

- supported product reads continue to route through existing service-owned
  behavior;
- canonical admin Need-a-Sub and official-game removal workflows remain the
  only active removal entry points in this slice;
- downstream request-body limit work can treat B1 tombstones as bodyless;
- downstream HTTP/OpenAPI work can represent tombstones consistently without
  re-deciding which B1 routes are retired.

Operationally, these tombstones are a compatibility bridge for stale clients.
They are not a promise that obsolete routes remain forever. Any future removal
date, deprecation policy, cache behavior, or OpenAPI representation belongs to
WS02-05A or a later owner decision.

## 8. Not Part Of This Pass

B1 does not implement or close:

- ordinary JSON request-size enforcement;
- multipart or raw-body provider limits;
- Stripe webhook authenticity, payload-size, or provider metadata policy;
- checkout return URL policy;
- payment/refund lifecycle correctness;
- policy/legal authoring or acceptance ownership;
- identity/account lifecycle behavior;
- database concurrency behavior;
- provider dashboard evidence;
- storage/object-provider evidence;
- OpenAPI/media/cache/405 representation;
- response minimization;
- tombstone removal dates;
- Playwright or browser-level evidence;
- historical test repair.

## 9. Related Controls And Remaining Evidence

`API-M09` advances because obsolete body-bearing mutation surfaces are removed
from the active request-body surface. It remains partial until ordinary JSON,
provider/payment, policy/legal, and infrastructure request-body work complete in
their owning passes.

`API-M13` is supported only for lifecycle method/status behavior: stale callers
receive HTTP 410 from the intended tombstone. Broader media negotiation,
unsupported-media behavior, retry semantics, and idempotency remain outside B1.

`API-M18` is supported by preserving explicit registered compatibility
tombstones for retired routes. OpenAPI exposure, deprecation representation,
cache behavior, and removal timing remain WS02-05A/later-owner work.

`GOV-006` is respected because B1 does not invent broad request limits or
provider thresholds. It proves lifecycle ownership and leaves threshold policy
to the limits register and downstream passes.

`ADM-*`, `IAM-*`, `DB-*`, and `PAY-*` controls are supported by preserving
canonical service-owned workflows and by preventing direct generic fabrication
paths, but their broader operational evidence remains in their owning passes.

## 10. Completion Criteria

This pass is complete only when all of the following are true:

- exact WS02-04B2A2B1 declaration metadata exists as frozen in this plan;
- `WS02-04B2A2B1-R7` is deferred, governance-scoped, non-executable, and has
  zero pytest mappings;
- the testing record explains the evidence boundary, what was proven, and what
  remains outside B1;
- trusted route-lifecycle tests prove the complete 35-route B2A2B1 retired
  mutation inventory;
- trusted route-lifecycle tests prove bodyless, authenticated, non-mutating
  lifecycle behavior without claiming WS02-05A response-representation closure;
- trusted route-lifecycle tests prove canonical replacement routes remain
  registered and compatible;
- trusted route-lifecycle tests prove frontend production caller compatibility;
- trusted route-lifecycle tests prove current trusted backend support/setup
  helpers do not depend on retired B1 routes;
- focused pytest for the route-lifecycle test root passes;
- checker file scope passes for all four frozen Python evidence modules;
- checker domain scope passes for `backend/tests/workflows/route_lifecycle_cleanup`;
- checker suite scope and requirement traceability pass;
- `git diff --check` passes;
- no false closure is claimed for HTTP/OpenAPI/cache representation,
  provider/payment correctness, identity/account behavior, database
  concurrency, storage/provider evidence, ordinary JSON limits, or external
  runtime/provider evidence;
- no production, frontend, migration, provider, CI, or unrelated files are
  changed unless explicitly approved after a new finding.
