# WS02-05B1 Game Request Ownership Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS02-05B1` |
| Trusted test scope | `backend/tests/workflows/request_ownership` |
| Requirement declaration | `backend/tests/support/requirements/ws02_05b1.json` |
| Authoritative sources | Canonical WS02-05B1 plan; current accepted repository truth; EN-01 trusted evidence architecture |
| Evidence layers | pytest; Pydantic schema inspection; generated OpenAPI request-schema inspection; PostgreSQL-backed API behavior; production source/static caller inventory; governance deferral for R7 |

## 1. Scope

This record covers the local trusted evidence for game request ownership in
WS02-05B1. The scope is the generic game create/update request boundary,
server-derived protected game fields, dedicated game mutation authorities, and
current caller/helper negative space.

This record does not claim response minimization, HTTP cache/media/tombstone
representation, ordinary request body limits, provider/payment/refund behavior,
storage provider evidence, DB race/concurrency closure, deployed runtime proof,
telemetry, legal/privacy review, or future API versioning.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS02-05B1-R1` | Generic game create exposes only caller-owned fields and rejects protected over-posting before persistence. | pytest |
| `WS02-05B1-R2` | Generic game create derives protected persisted values from auth, venue, lifecycle, invariant, and DB/server sources. | pytest with PostgreSQL-backed API proof |
| `WS02-05B1-R3` | Generic game update exposes only generic admin-editable fields and rejects protected over-posting before mutation. | pytest |
| `WS02-05B1-R4` | Generic game update preserves protected fields and applies only allowed or service-derived changes. | pytest with PostgreSQL-backed API proof |
| `WS02-05B1-R5` | Specialized game mutation paths use dedicated schemas and actor boundaries rather than broad game-row request bodies. | pytest/source/OpenAPI |
| `WS02-05B1-R6` | Current callers, trusted helpers/support, and generic game services remain compatible with the narrowed request contract. | pytest/source-static |
| `WS02-05B1-R7` | Later-owner and external-evidence boundaries remain explicit. | deferred |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| R1 | Generic create request fields are an allowlist, not the `games` table shape. | Caller can submit lifecycle, snapshot, payment, policy, actor, or timestamp fields. | Client over-posting could forge authoritative game state. | `GameCreate` extra-forbid plus generated OpenAPI request schema and API rejection. | workflow/schema/API |
| R2 | Generic create protected values come from trusted workflow sources. | Admin request body decides actor, snapshots, lifecycle, payment mode, official invariants, or local date. | Persisted rows could contradict source-owned policy or identity. | PostgreSQL-backed create scenarios over community and official rows. | workflow/API/PostgreSQL |
| R3 | Generic update request fields are an admin-edit allowlist. | Caller can patch protected row fields such as host, status, venue snapshots, payment mode, policy, or timestamps. | Generic update becomes a game-row patch bypass. | `GameUpdate` extra-forbid plus generated OpenAPI request schema and API rejection. | workflow/schema/API |
| R4 | Successful generic updates change only allowed fields and service-derived fields. | Allowed edits accidentally rewrite protected identity, lifecycle, snapshots, payment, or official invariant fields. | Admin edits could silently corrupt game authority boundaries. | PostgreSQL-backed allowed update and rejected no-side-effect scenarios. | workflow/API/PostgreSQL |
| R5 | Dedicated game workflows keep their own purpose schemas and actor checks. | A specialized path exposes generic protected game fields without a purpose-specific owner. | Dedicated flows become another over-posting bypass. | Route-table, schema, dependency, and OpenAPI request-schema inventory. | workflow/source/OpenAPI |
| R6 | Current callers and trusted helpers do not depend on generic protected over-posting. | Frontend or setup helpers still call generic `POST /games` or `PATCH /games/{id}` with removed fields, or service code spreads request data into ORM rows. | The narrowed contract would be incompatible or bypassed internally. | Source-static caller inventory, trusted helper scan, and service mapping inspection. | workflow/source |
| R7 | Later-owner evidence stays open. | B1 overclaims HTTP, response, provider, DB race, runtime, or legal closure. | Production-readiness status becomes misleading. | Deferred declaration and explicit record boundary. | governance |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | active admin, verified host/user, current frontend caller, trusted helper/setup caller | covered | B1 request ownership depends on admin generic routes, verified specialized routes, and current caller compatibility. |
| States / lifecycle | published active rows, official/community type, lifecycle/cancellation/completion fields, official forced fields | covered | These are the protected game state classes that over-posting would corrupt. |
| Actions | generic create, generic update, community publish, host edit, official create/update/actions, roster actions, cancellation, community detail, enforcement | covered | These are the frozen B1 mutation surfaces. |
| Inputs / boundaries | allowed fields, unknown/protected fields, generated request schemas, source payload builders | covered | B1 owns whether the fields are writable at all. |
| Time | fixed future schedules and derived local date | covered in scope | Tests need future games for valid edits and prove local-date derivation; wall-clock transition behavior is not B1-owned. |
| Dependencies | Pydantic, FastAPI OpenAPI, PostgreSQL, production source files | covered | These are the local proof layers for request ownership. |
| Concurrency / idempotency | genuine races, payment/booking capacity races, idempotency keys | deferred/not applicable | These belong to DB/workflow/payment owners, not B1 generic request ownership. |
| Authorization / privacy / security | admin and verified-user route dependencies; response minimization | partial/deferred | Actor dependency shape is covered; response audience minimization stays WS02-05B2. |
| Persistence / rollback | successful create/update effects and rejected no-side-effect behavior | covered | Rejected mutations must prove no prohibited persisted effect. |
| Recovery | provider reconciliation, runtime replay, deployed edge behavior | deferred | Not local B1 request-ownership evidence. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | optional allowed fields and absent protected fields | pytest/API |
| empty | partial | bodyless or empty purpose schemas such as leave/cancel defaults | pytest/schema/OpenAPI |
| corrupt | yes | protected/unknown fields in generic create/update bodies | pytest/API |
| exceed | partial | numeric/text bounds belong to adjacent A2A owners | covered elsewhere |
| duplicate | no | no B1 duplicate/idempotency claim | not applicable |
| delay | no | no time-expiry claim | not applicable |
| reorder | no | no ordering claim | not applicable |
| interrupt | yes | rejected over-posting leaves no persisted create/update side effect | pytest/PostgreSQL |
| race | no | DB race/concurrency proof belongs to later owners | deferred |
| expire / revoke | no | auth/session/provider lifecycle is outside B1 | deferred |
| tamper | yes | request body tries to tamper with protected game fields | pytest/API |
| retry | no | generic create/update idempotency is not claimed | not applicable |
| recover | no | recovery workflows are outside B1 | deferred |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| R1, R2 | Generic create schema/OpenAPI allowlist, protected over-post rejection, community/official persisted derivation. | Pydantic, OpenAPI, API, PostgreSQL | `test_game_create_request_ownership_contract.py` | Enough for local generic create ownership; not response minimization or external runtime proof. |
| R3, R4 | Generic update schema/OpenAPI allowlist, protected over-post no-side-effect, allowed update preservation, derived local date, host guest max, and official forced fields. | Pydantic, OpenAPI, API, PostgreSQL | `test_game_update_request_ownership_contract.py` | Enough for local generic update ownership; not full game lifecycle behavior. |
| R5 | Dedicated schema, route, dependency, and OpenAPI request-body inventory for specialized game workflows. | Source/static and OpenAPI | `test_game_specialized_mutation_authority_contract.py` | Enough to prove no specialized path exposes broad protected game-row writes; adjacent owners still test their domain behavior. |
| R6 | Current frontend callers, generic game service mapping, and trusted helper/setup negative space. | Source/static | `test_game_request_negative_space_contract.py` | Enough for current source compatibility and no request-shaped bypass; not browser runtime proof. |
| R7 | Later-owner non-closure. | Governance declaration | Requirement JSON and this record | Correctly has no executable pytest mapping. |

### Evidence Quality Checks

- Successful generic create and update tests assert persisted database state, not
  only successful HTTP responses.
- Rejected generic create and update tests assert prohibited persisted effects
  did not occur.
- OpenAPI checks inspect generated request schemas only; response minimization
  and HTTP representation are not claimed.
- Source inventory checks current production caller and service files without
  relying on historical evidence.
- B1 does not claim genuine concurrent database behavior, provider behavior, or
  deployed ingress behavior.

## 7. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| Generic game create | Creates a game row with server-derived actor, snapshots, lifecycle, payment, policy, invariant, local-date, and timestamp values. | Protected over-post body must not create any game row. | No idempotency claim. |
| Generic game update | Mutates allowed fields and server-derived local-date/host-guest/official-forced fields as appropriate. | Protected over-post body must not mutate existing protected or allowed row values. | No idempotency claim. |
| Specialized mutation inventory | Keeps dedicated route bodies and actor dependencies purpose-specific. | Specialized paths must not expose broad protected game-row fields except fields deliberately owned by that action. | Behavioral idempotency remains with adjacent workflow owners. |
| Caller/helper negative space | Current callers use dedicated routes and trusted helpers do not require unsafe generic over-posting. | No current source should rely on generic protected `GameCreate`/`GameUpdate` fields or request-shaped ORM writes. | Not applicable. |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| `WS02-05B1-R7` | deferred | Response minimization, HTTP media/cache/tombstone representation, ordinary body limits, identity/account authority, provider/payment/refund correctness, storage evidence, DB race/concurrency proof, deployed/runtime evidence, telemetry, legal/privacy review, and future versioning are not local B1 proof. | Listed downstream owners |
| Numeric/text bounds | covered elsewhere | A2A owns active request bounds where a field is exposed. | `WS02-04B2A2A` |
| Current response audiences | covered elsewhere | B1 owns request fields, not response minimization. | `WS02-05B2` |
| Payment/provider correctness | covered elsewhere/deferred | B1 only checks game request ownership boundaries. | `WS02-04B2A2B2`, `WS05` |
| Browser/e2e behavior | deferred | No frontend behavior change is approved in B1. | Frontend/e2e owner |
| Full semantic record adequacy | manual | Checker and generated traceability are structural; this record requires human review. | Gate C/human review |

## 9. Adequacy Conclusion

This evidence is adequate for Gate B when focused B1 pytest, checker domain and
suite scopes, generated traceability through the checker, full trusted backend
regression, syntax/compile validation, and diff/integrity checks pass.

Requirements R1 through R6 have executable trusted evidence. R7 is intentionally
deferred with zero pytest mappings. Checker `PASS` is structural compliance
evidence only; this record supplies the human adequacy boundary and keeps
later-owner gaps explicit.
