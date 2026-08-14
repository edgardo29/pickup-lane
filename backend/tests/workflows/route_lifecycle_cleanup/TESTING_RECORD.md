# WS02-04B2A2B1 Route Lifecycle Cleanup Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS02-04B2A2B1` |
| Trusted test scope | `backend/tests/workflows/route_lifecycle_cleanup` |
| Requirement declaration | `backend/tests/support/requirements/ws02_04b2a2b1.json` |
| Authoritative sources | Canonical WS02-04B2A2B1 plan; applicable API/control requirements; accepted WS02-04 closeout and ownership records |
| Evidence layers | FastAPI route-table inspection; TestClient HTTP proof; handler-level source/AST proof; frontend production source/static proof; trusted backend support/setup static proof; governance deferral for R7 |

## 1. Scope

This record covers the trusted local evidence for the WS02-04B2A2B1 route
lifecycle cleanup pass. The executable scope is exactly the 35 B2A2B1-retired
mutation tombstones frozen by the canonical plan.

The record separates lifecycle policy from implementation truth. Policy comes
from the canonical pass plan and accepted production-readiness authority.
Current source proves what is implemented today.

`GET /notifications` is excluded. It is a current authenticated 410 tombstone,
but it is not a body-bearing mutation route, was not one of the B2A2B1
notification write paths, and is not B2A2B1 evidence.

This scope does not prove HTTP/OpenAPI/cache representation, ordinary JSON body
limits, provider/payment behavior, policy/legal ownership, identity/account
behavior, database concurrency, storage/provider evidence, tombstone removal
timing, or external runtime/provider evidence.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS02-04B2A2B1-R1` | The 35 retired mutation routes remain bodyless, authenticated, registered compatibility tombstones with no DB/session or retired mutation/provider work. | pytest |
| `WS02-04B2A2B1-R2` | Retired generic/scaffolded mutation surfaces cannot fabricate direct lifecycle state. | pytest |
| `WS02-04B2A2B1-R3` | Need-a-Sub duplicate removal is retired and the admin POST removal action remains canonical. | pytest |
| `WS02-04B2A2B1-R4` | Official-game player DELETE removal is retired and the POST preview/execute pair remains canonical. | pytest |
| `WS02-04B2A2B1-R5` | Official-game host DELETE removal is retired and POST host/remove remains canonical with a reason-bearing body shape. | pytest |
| `WS02-04B2A2B1-R6` | Production frontend callers and trusted backend support/setup helpers do not depend on retired B1 routes. | pytest |
| `WS02-04B2A2B1-R7` | Later-owner HTTP, provider/payment, policy/legal, identity, DB concurrency, storage, tombstone timing, and runtime evidence remains outside B1. | deferred |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| `R1`, `R2` | Retired mutation routes are registered only as bodyless, authenticated, non-mutating tombstones. | A route regains a body field, DB dependency, manual body reader, service call, provider call, or active alias. | Clients could revive generic lifecycle writes or treat stale JSON as supported input. | Route-table, HTTP, and handler-level source/AST evidence. | workflow |
| `R2` | Generic CRUD and server-derived state scaffolds cannot fabricate lifecycle state. | Direct booking, roster, waitlist, history, admin action, notification write, or similar state fabrication becomes reachable. | Audit/history, notification, roster, and booking state could bypass service-owned workflow rules. | 410 lifecycle proof and no mutation-service/DB proof. | workflow |
| `R3` | Need-a-Sub removal uses the canonical admin POST action. | A duplicate PATCH path removes posts or production callers use the stale path. | Moderation/review/audit/notification ownership could be bypassed. | Retired route and replacement/caller source checks. | workflow |
| `R4` | Official-game player removal uses POST preview/execute. | Stale DELETE path removes players or callers bypass preview/execute. | Payment, credit, waitlist, audit, and notification side effects could be skipped. | Retired route and replacement/caller source checks. | workflow |
| `R5` | Official-game host removal uses POST host/remove with a reason-bearing request body. | Stale DELETE path removes hosts or caller omits the canonical reason shape. | Host removal could bypass the service-owned action path. | Retired route, active route body-shape, and caller checks. | workflow |
| `R6` | Test setup and production callers do not rely on retired public routes. | Evidence or UI compatibility quietly depends on resurrecting retired routes. | Future cleanup could be blocked by hidden stale dependencies. | Targeted frontend and trusted support/setup static checks. | workflow |
| `R7` | Later-owner work remains explicit and non-executable in B1. | B1 tests overclaim representation, provider, payment, policy, identity, concurrency, storage, or runtime closure. | Production-readiness status becomes dishonest. | Deferred requirement declaration and testing-record boundary. | governance |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | Anonymous caller; controlled active admin. | Covered | Tests prove auth failure precedes representative tombstone handlers and controlled active admins receive lifecycle 410. |
| States / lifecycle | Retired mutation route; active replacement route; adjacent non-B1 tombstone. | Covered / excluded | The 35 retired mutation routes are covered. `GET /notifications` is explicitly excluded from B1. |
| Actions | POST, PATCH, DELETE retired mutations; canonical POST replacement actions. | Covered | Method/path registration and replacement route shape are central to B1. |
| Inputs / boundaries | No body; JSON body; sentinel body; malformed JSON. | Covered | Tests prove stale bodies do not create an active request contract. |
| Time | No time-sensitive behavior. | Not applicable | Route lifecycle retirement does not depend on wall-clock time. |
| Dependencies | FastAPI route table; source handlers; frontend source; backend support files. | Covered | These are the lowest honest proof layers for B1. |
| Concurrency / idempotency | No genuine concurrency or idempotency proof. | Deferred | B1 tombstones have no DB or provider state effects. |
| Authorization / privacy / security | Active-admin boundary and no submitted-body echo. | Covered | Auth order and sentinel non-reflection are tested without claiming exact error representation. |
| Persistence / rollback | Prohibited mutation only. | Covered | No DB dependency and no mutation-service calls are proved at route and source layers. |
| Recovery | Stale client compatibility tombstone. | Covered | HTTP 410 lifecycle behavior is tested without WS02-05A representation claims. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | Retired route called without a body. | HTTP 410 lifecycle proof. |
| empty | no | Empty body is equivalent to omitted for bodyless tombstones. | Covered by no-body requests. |
| corrupt | yes | Malformed JSON sent to a retired route. | Representative HTTP proof shows route-owned parsing is not revived. |
| exceed | no | Size limits are not owned by B1. | Deferred to ordinary JSON/provider limit owners. |
| duplicate | yes | Duplicate route registration or active alias. | Route-table negative-space proof. |
| delay | no | No time dependency. | Not applicable. |
| reorder | no | No ordering dependency. | Not applicable. |
| interrupt | no | No stateful operation. | Not applicable. |
| race | no | No DB mutation or concurrency path. | Deferred outside B1. |
| expire / revoke | no | No expiry semantics in this scope. | Not applicable. |
| tamper | yes | Submitted JSON tries to activate retired input. | Sentinel body and source/bodyless proof. |
| retry | no | Tombstones do not create idempotent state effects. | Not applicable. |
| recover | yes | Stale clients receive the compatibility tombstone. | HTTP 410 lifecycle proof. |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| `R1` | 35-route registration, auth dependency, no body field, no DB dependency, no active duplicate alias. | FastAPI route table | `test_retired_route_registration_contract.py` | The real route table is the authority for registered method/path/body/dependency shape. |
| `R1`, `R2` | No-body, JSON-body, sentinel, malformed JSON, and auth-order lifecycle behavior. | TestClient | `test_retired_route_http_contract.py` | Proves stale input reaches 410 behavior without becoming accepted request validation or mutation. |
| `R1`, `R2` | Handler source has no manual body readers, DB/session construction, service mutation calls, or provider/network work. | Handler AST/source | `test_retired_route_source_contract.py` | Directly targets retired handlers and helper wrapper chains without rejecting active read routes in the same modules. |
| `R3`, `R4`, `R5` | Canonical replacement route registration, active route shape, and frontend caller compatibility. | Route table and frontend source/static | `test_replacement_route_contract.py` | Proves replacement workflows remain the production path without retesting their full service behavior. |
| `R6` | Frontend callers and trusted backend setup/support helpers avoid retired routes. | Source/static | `test_replacement_route_contract.py` | Demonstrates current compatibility without letting tests define product API. |
| `R7` | Downstream non-closure. | Governance declaration | Requirement JSON and this record | Correctly has no executable pytest evidence. |

### Evidence Quality Checks

- Exact time-boundary tests are not applicable because the B1 lifecycle contract
  has no time dependency.
- Successful mutations are not applicable because B1 retired routes must not
  mutate.
- Rejected mutations prove prohibited effects through no body field, no DB
  dependency, no mutation service calls, no provider calls, and HTTP tombstone
  behavior.
- Idempotency tests are not applicable because tombstones have no persisted or
  external effects.
- Genuine PostgreSQL race or concurrency behavior is not applicable.
- External providers are not contacted or mocked because provider behavior is
  outside B1.
- Database-constraint tests are not applicable because no DB proof is required.

## 7. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| 35 retired mutation routes | Authenticated stale callers receive lifecycle HTTP 410. | No request-body binding, manual body parsing, database/session use, retired mutation-service call, provider call, or submitted-body acceptance. | No persisted effect; rollback/idempotency not applicable. |
| Need-a-Sub replacement route | Canonical POST route remains registered. | Retired PATCH must not be the active removal path. | Full service idempotency remains outside B1. |
| Official-game player replacement | POST preview/execute routes remain registered. | Retired DELETE must not be the active removal path. | Payment/credit/waitlist effects remain outside B1. |
| Official-game host replacement | POST host/remove remains registered with reason-bearing body shape. | Retired DELETE must not be the active removal path. | Reason field bounds remain A2A-owned. |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| `WS02-04B2A2B1-R7` | deferred | HTTP/OpenAPI/cache/tombstone representation, ordinary JSON body limits, provider/payment input ownership and provider evidence, policy/legal ownership, request/response ownership outside B1, identity/account ownership, database concurrency, storage/provider evidence, tombstone removal timing, and external runtime/provider evidence remain outside local B1 route-lifecycle evidence. | Downstream WS02/WS03/WS05/WS06 and runtime/provider owners |
| `GET /notifications` | not applicable | It is not one of the 35 B2A2B1-retired mutation routes. | Adjacent current source / later owner if policy changes |
| A2A reason-field bounds | covered elsewhere | B1 proves host replacement includes a reason-bearing shape but not numeric/text-field policy. | `WS02-04B2A2A` |
| WS02-05A tombstone representation | covered elsewhere | B1 proves lifecycle 410 only and not public envelope, media/cache/OpenAPI/405/removal timing. | `WS02-05A` |

## 9. Adequacy Conclusion

The selected evidence is adequate for Gate B when focused pytest, adjacent
trusted regression, full trusted backend regression, checker file/domain/suite
validation, requirement traceability, and diff/integrity checks pass.

Requirements `R1` through `R6` have executable evidence. `R7` is correctly
deferred with zero pytest mappings. Checker `PASS` is structural compliance
evidence only; adequacy also depends on this human risk record matching the
actual evidence boundaries.
