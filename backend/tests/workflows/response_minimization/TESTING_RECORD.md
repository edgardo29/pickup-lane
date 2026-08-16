# WS02-05B2 Response Minimization Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS02-05B2` |
| Trusted test scope | `backend/tests/workflows/response_minimization` |
| Requirement declaration | `backend/tests/support/requirements/ws02_05b2.json` |
| Authoritative sources | Canonical WS02-05B2 plan; current accepted repository truth; EN-01 trusted evidence architecture |
| Evidence layers | pytest; Pydantic schema inspection; generated OpenAPI response-schema inspection; dynamic FastAPI route-table inventory; PostgreSQL-backed API behavior; production frontend/source inventory; governance deferral for R10 |

## 1. Scope

This record covers local trusted evidence for B2-owned response minimization and
audience-specific response contracts. The scope includes public/ordinary game
responses, My Games and current-user participant responses, explicit host/admin
richness, self/user/admin identity responses, ordinary financial summaries,
checkout payment-intent/status responses, saved-card setup/sync/default/detach
responses, public/admin image responses, participant/admin chat response
boundaries, public policy reads, OpenAPI response truth, current frontend
compatibility, dynamic route-table discovery for missing/raw response
contracts, and negative-space classification of nearby response families.

This record does not claim request ownership, mass-assignment closure,
provider/payment/refund correctness, storage processing/lifecycle, policy/legal
authoring, cache/docs/tombstone ownership, permanent deployed HTTP-chain proof,
browser/e2e behavior, migrations, concurrency, observability, privacy/retention,
or public API versioning.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS02-05B2-R1` | Public and ordinary game responses expose only audience-appropriate game, roster, capacity, schedule, location, price, cancellation, chat, and compatibility fields. | pytest |
| `WS02-05B2-R2` | Host/admin game richness is explicit and restricted to host/admin response contexts. | pytest |
| `WS02-05B2-R3` | Self/account responses expose current product-required self fields while admin user routes retain operational fields only behind admin authorization. | pytest |
| `WS02-05B2-R4` | Ordinary financial responses exclude provider/internal details while admin financial surfaces remain explicit admin-only exceptions. | pytest |
| `WS02-05B2-R5` | Public image responses exclude storage/provider/upload metadata while admin/upload responses retain operational metadata. | pytest |
| `WS02-05B2-R6` | Participant chat responses exclude moderation/admin evidence while admin moderation schemas retain review fields. | pytest |
| `WS02-05B2-R7` | Public policy/legal reads expose only display/version fields. | pytest |
| `WS02-05B2-R8` | Response models, generated OpenAPI schemas, and current negative-space classifications do not bypass B2 minimization. | pytest |
| `WS02-05B2-R9` | Current frontend callers remain compatible with retained temporary response fields and public image ordering fields. | pytest |
| `WS02-05B2-R10` | Later-owner and external-evidence boundaries remain explicit. | deferred |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| R1, R2 | Game responses are audience-specific at HTTP serialization time. | Public/detail/list/My Games/current-user participant responses leak broad `GameRead` or participant actor, lifecycle, policy, audit, or internal request fields. | Public or ordinary callers receive operational game or participant state. | Runtime public/non-host/host/admin/My Games/current-user participant API assertions and route/model checks. | workflow/API/PostgreSQL |
| R3 | Self and admin user responses are split by audience. | Ordinary users receive Firebase/provider UID, audit/deletion fields, or admin-only state. | Identity and admin state leak outside the authorized context. | Runtime self/admin API assertions plus route response-model checks. | workflow/API/PostgreSQL |
| R4 | Ordinary financial reads are summaries, not provider records. | Ordinary payment/refund/card/event/checkout/status/saved-card action responses expose provider IDs, idempotency, raw payloads, failure diagnostics, or metadata. | Payment/provider internals leak to ordinary users. | Runtime ordinary financial API assertions, synthetic provider-boundary serialization checks, and admin-only route classification. | workflow/API/PostgreSQL |
| R5 | Public image reads expose display data only. | Public image responses expose R2 object keys, buckets, account IDs, upload status, uploader, content type, size, ETag, or audit timestamps. | Storage topology and upload lifecycle leak publicly. | Runtime public/admin image API assertions and schema checks. | workflow/API/PostgreSQL |
| R6 | Participant chat reads are conversation display contracts. | Participant responses expose review status, visibility workflow, detections, reviewer/admin IDs, removal/restoration actors, or moderation source. | Moderation workflow evidence leaks to participants. | Runtime participant chat API assertions and admin moderation schema checks. | workflow/API/PostgreSQL |
| R7 | Public policy reads expose renderable policy content, not management state. | Public legal endpoints expose active/retired/audit fields. | Management lifecycle leaks through public legal pages. | Runtime public policy API assertions and schema checks. | workflow/API/PostgreSQL |
| R8 | OpenAPI and response-model boundaries match runtime minimization. | A B2 route uses raw dict, `Any`, missing response model, broad ORM/table-shaped schema, or unclassified exception. | Runtime filtering and generated docs drift from the intended contract. | Dynamic FastAPI route-table discovery, suspicious-candidate classification, schema/OpenAPI checks, and fail-closed unclassified-route assertions. | workflow/source/OpenAPI |
| R9 | Current frontend callers still use retained fields and no removed public/internal fields. | Response minimization silently breaks current UI or leaves stale dependencies on fields B2 must not expose. | Product workflows fail or unsafe fields stay public for compatibility by accident. | Current frontend source inventory. | workflow/source |
| R10 | Later-owner and external gaps remain open. | Local B2 tests claim provider, storage runtime, request ownership, browser, concurrency, legal/privacy, or operational proof. | Production-readiness status becomes misleading. | Deferred declaration and explicit record boundary. | governance |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | signed-out public caller, ordinary user, self/account caller, host, participant, admin | covered | Response minimization is audience-sensitive. |
| States / lifecycle | visible published games, host-edit/cancel responses, active users, payment/refund states, active images, visible chat/policy records | covered | These are the current B2-owned response surfaces. |
| Actions | list/detail/read, My Games, current-user participant reads, host edit, cancel, self profile update, checkout payment-intent/status, payment/refund/card/event reads, saved-card setup/sync/default/detach, image reads, chat message reads, policy reads | covered | They exercise runtime HTTP serialization where response filtering matters. |
| Inputs / boundaries | generated OpenAPI response schemas, live FastAPI `APIRoute` entries, route `response_model`s, broad `dict`/`Any` contracts, missing response models, Pydantic fields, current frontend field use | covered | B2 must prove both runtime and documented response truth, and R8 must discover suspicious response surfaces even when they were not manually preselected. |
| Dependencies | FastAPI, Pydantic, PostgreSQL, production services/serializers, synthetic provider-boundary mocks for checkout/setup-intent serialization, frontend source files | covered for local response shape | These are the local proof layers for B2; synthetic provider data reaches HTTP serialization without claiming provider correctness. |
| Provider/storage runtime | Stripe/Firebase/R2 network behavior, webhook/provider dashboards, upload object lifecycle | deferred | Those are later-owner/external evidence and not B2 response minimization. |
| Authorization / privacy | audience-specific field exposure; admin-only richness | covered for response shape | Full identity authority and privacy/retention policy remain later owners. |
| Concurrency / rollback | race behavior, retries, idempotency, durable jobs | deferred/not applicable | Response shape is not a race/concurrency invariant. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | required display fields accidentally removed from current response contracts | pytest/API/source |
| corrupt | yes | broad internal/protected fields appear in ordinary/public responses | pytest/API/OpenAPI |
| tamper | no | request-body ownership is B1/B3/A2 scope | covered elsewhere |
| exceed | no | request-size and field-bound limits are A2 scope | covered elsewhere |
| duplicate | no | no B2 duplicate/idempotency claim | not applicable |
| delay | no | no timing SLA claim | not applicable |
| reorder | partial | public image ordering must use public fields, not internal timestamps | source inventory |
| interrupt | no | no B2 rollback claim | covered elsewhere |
| race | no | concurrency proof is later-owner | deferred |
| expire / revoke | no | auth/provider lifecycle is outside B2 | deferred |
| recover | no | provider/storage recovery is outside B2 | deferred |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| R1, R2 | Game detail/list/browse/My Games/current-user participant/roster/count, host/admin visibility, cancel/host-edit returns, generic admin `GameRead` reservation. | API, PostgreSQL, route/schema inspection | `test_game_response_audience_contract.py` | Enough for current local game response exposure; not browser/e2e or request ownership. |
| R3 | Self/auth/account/user response split and admin user operational route split. | API, PostgreSQL, route/schema inspection | `test_user_response_audience_contract.py` | Enough for local response shape; WS03 still owns identity authority. |
| R4 | Ordinary payment/refund/event/card reads, checkout payment-intent/status projections, saved-card setup/sync/default/detach responses, and admin financial exception classification. | API, PostgreSQL, route/schema inspection, synthetic provider-boundary mocks | `test_financial_response_minimization_contract.py` | Enough for HTTP field minimization and action response shape; not provider correctness or Stripe lifecycle. |
| R5 | Public game/venue images and admin image/upload metadata. | API, PostgreSQL, schema inspection | `test_image_response_minimization_contract.py` | Enough for HTTP representation; WS06 owns storage runtime and image processing. |
| R6, R7 | Participant game/Need-a-Sub chat, admin moderation schemas, and public policy reads. | API, PostgreSQL, schema inspection | `test_chat_policy_response_minimization_contract.py` | Enough for current local response minimization; not moderation process adequacy or legal review. |
| R8 | Response-model/OpenAPI truth, dynamic suspicious-route discovery from the current FastAPI route table, and nearby response-family classification, including My Games, current-user participant, checkout, and saved-card action routes. | Source/static and OpenAPI | `test_response_model_openapi_negative_space_contract.py` | Enough to catch current local response-model omissions, raw/generic response contracts, stale exception records, and undocumented B2-owned bypasses; not 05A HTTP/cache/docs policy closure or proof that later-owner/admin/provider routes are otherwise complete. |
| R9 | Current frontend compatibility and temporary field dependence. | Source/static | `test_current_frontend_response_compatibility_contract.py` | Enough for current source compatibility; not browser runtime proof. |
| R10 | Later-owner non-closure. | Governance declaration | Requirement JSON and this record | Correctly has no executable pytest mapping. |

### Evidence Quality Checks

- Runtime tests assert actual HTTP JSON keys, not only Pydantic class fields.
- Schema and OpenAPI checks are used where the approved plan requires response
  model truth and negative-space classification.
- R8 enumerates the current registered `APIRoute` table and discovers
  suspicious candidates from route metadata rather than relying on a manually
  complete route list.
- Every discovered route with a missing response model or broad `dict`/`Any`
  response contract must have an explicit classification. Unclassified
  candidates, stale classifications, and B2-owned contradictions fail the test.
- Current exception classes include retired 410 mutation tombstones, no-content
  cleanup responses, platform/runtime probes, active-admin operational
  dictionaries, and provider webhook acknowledgements. Classification records
  ownership/negative space; it does not close those other owners' requirements.
- Synthetic checkout/setup-intent provider results are used only to reach HTTP
  serialization and are not provider lifecycle proof.
- Current frontend inventory reads production frontend source and does not rely
  on historical PR text.
- Admin/provider/internal response richness is classified explicitly rather than
  treated as an ordinary/public contract.
- R10 has zero pytest mappings.

## 7. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects / Non-Claims |
|---|---|---|
| Public/ordinary reads | Return product-required display fields for the caller audience. | Must not expose broad table/internal/provider/moderation/storage fields. |
| Host/admin reads | Retain fields needed by host/admin workflows behind the corresponding audience boundary. | Must not make host/admin richness public by accident. |
| Checkout and saved-card actions | Return action-specific client-facing checkout/card projections, including intentionally returned synthetic client secrets where the current product contract requires them. | Must not expose broad provider objects, raw payloads, idempotency keys, provider bookkeeping, diagnostics, or arbitrary metadata; does not prove provider lifecycle correctness. |
| Static source inventory | Documents current frontend and nearby response-family dependencies. | Does not modify frontend or production source. |
| Dynamic route-table inventory | Discovers current missing-response-model and broad/raw response candidates from the registered FastAPI app and requires explicit classifications. | Classification does not prove later-owner/provider/admin behavior safe; it records why the candidate is not a B2 ordinary/public leak. |
| Generated OpenAPI checks | Confirms documented response schemas match minimized contracts and that classified tombstone/no-content/dict exceptions are represented consistently with their response shape. | Does not claim 05A docs exposure/cache/media closure. |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| `WS02-05B2-R10` | deferred | Request ownership, mass assignment, provider correctness, storage lifecycle, policy/legal authoring, cache/docs/tombstones, permanent HTTP-chain evidence, browser/e2e, migrations, concurrency, observability, privacy/retention, and API versioning cannot be closed by B2 local tests. | Listed downstream owners |
| Request-body ownership | covered elsewhere | B2 is response minimization only. | `WS02-05B1`, A2/B3 owners |
| Provider/payment correctness | covered elsewhere/deferred | B2 proves response fields only; synthetic provider-boundary data in checkout/setup-intent tests is serialization reachability evidence only. | `WS02-04B2A2B2`, `WS05` |
| Storage runtime/lifecycle | covered elsewhere/deferred | B2 proves HTTP image representation only. | `WS06` |
| Browser/e2e behavior | deferred | No frontend correction is approved in B2. | Frontend/e2e owner |
| Full semantic record adequacy | manual | Checker and generated traceability are structural; this record requires human review. | Gate C/human review |

## 9. Adequacy Conclusion

This evidence is adequate for Gate B when focused B2 pytest, checker domain and
suite scopes, generated traceability through the checker, full trusted backend
regression, syntax/compile validation, and diff/integrity checks pass.

Requirements R1 through R9 have executable trusted evidence. R10 is intentionally
deferred with zero pytest mappings. Checker `PASS` is structural compliance
evidence only; this record supplies the human adequacy boundary and keeps
later-owner gaps explicit.
