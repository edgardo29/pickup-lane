# WS02-05A HTTP Contracts Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS02-05A` |
| Trusted test scope | `backend/tests/platform/http_contracts/` |
| Requirement declaration | `backend/tests/support/requirements/ws02_05a.json` |
| Authoritative sources | Canonical WS02-05A plan, `FDN-03`, `FDN-04`, `API-M13`, `API-M14`, `API-M16`, `API-M18`, `API-M19`, accepted WS02-03/WS02-04/WS02-05B1/WS02-05B2 plans |
| Evidence layers | pytest, backend HTTP/API, generated OpenAPI inspection, source route metadata, governance deferral |

## 1. Scope

This record covers WS02-05A's local trusted evidence for source-owned backend
HTTP contracts: ordinary JSON media-type behavior, framework-owned method
stability, generated OpenAPI public error documentation, source-owned cache
classification, docs/OpenAPI exposure policy, compatibility tombstone
representation, and pagination inventory ownership truth.

This record does not cover live edge/CDN/shared-cache behavior, deployed
docs access, proxy/TLS/HSTS/direct-origin behavior, runtime/process-server
behavior, provider behavior, frontend/browser behavior, database query plans,
stale-cursor concurrency, bulk/export design, public API versioning, or
unapproved pagination numeric values.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS02-05A-R1` | JSON request-body media behavior is explicit and compatibility-preserving. | pytest |
| `WS02-05A-R2` | Unsupported methods remain framework-owned but stable. | pytest |
| `WS02-05A-R3` | OpenAPI documents stable public error contracts truthfully. | pytest |
| `WS02-05A-R4` | Source-owned API cache classification is safe. | pytest |
| `WS02-05A-R5` | Docs/OpenAPI exposure and compatibility follow `FDN-03`. | pytest |
| `WS02-05A-R6` | Compatibility tombstones remain visible and bodyless while registered. | pytest |
| `WS02-05A-R7` | Pagination inventory is complete and ownership-truthful. | pytest |
| `WS02-05A-R8` | Repository-only evidence boundaries are explicit. | deferred with zero pytest mappings |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| `R1` | Ordinary JSON routes accept JSON-compatible media and reject explicit non-JSON media before route work. | Ambiguous or wrong media reaches route code, or missing content type is rejected without approved compatibility evidence. | Callers break or route logic processes unexpected input. | Request-body middleware media gate and raw-webhook exclusion. | platform |
| `R2` | Method routing remains framework-owned and the stable envelope preserves `Allow`. | Pickup Lane adds aliases or loses method metadata. | Callers receive inconsistent failures or lose compatibility metadata. | Starlette routing plus application error normalization. | platform |
| `R3` | OpenAPI error schemas and route-derived responses match current source behavior without sensitive fields. | Docs understate failures, overstate provider behavior, or expose internal data. | Reviewers and callers trust incorrect API contracts. | OpenAPI contract augmentation. | platform |
| `R4` | Private, authenticated, and admin API responses are private no-store; public API responses remain no-store. | Sensitive responses become cacheable or route-specific stricter policies are weakened. | Private user, admin, chat, payment, or profile data can be cached. | Response security header middleware and route classification. | platform |
| `R5` | Docs/OpenAPI exposure follows `FDN-03` and does not replace authorization. | Production-like docs are enabled by accident, or hiding docs is mistaken for security. | API inventory or authorization posture is misrepresented. | Typed settings validation and route authorization independence. | platform |
| `R6` | Retired compatibility tombstones stay visible, deprecated, 410-documented, and bodyless. | Tombstones disappear from docs or advertise retired request bodies. | Compatibility cleanup becomes invisible or obsolete input appears supported. | Tombstone route metadata and OpenAPI augmentation. | platform |
| `R7` | Pagination inventory accounts for every current live collection route as approved contract or unresolved handoff with truthful owner metadata. | A route drops from both inventories, stale B1/B2 ownership remains, or tests invent limits. | API-M14/API-M09/DB-013 risk falsely appears closed. | Pagination source inventory and route metadata checks. | platform |
| `R8` | Local evidence stays inside repository-owned proof boundaries. | Local tests are treated as CDN, proxy, provider, runtime, DB-performance, or full-chain proof. | Production readiness is overstated. | Deferred declaration and explicit testing-record gaps. | governance |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | anonymous callers, authenticated/private/admin route classes, provider webhook sender | grouped | WS02-05A proves HTTP classification and docs, not user authorization rules. |
| States / lifecycle | active routes, compatibility tombstones, docs enabled/disabled, production-like settings | covered | These states define current source-owned HTTP contract behavior. |
| Actions | JSON mutation, unsupported method, OpenAPI generation, cache header application, docs access, tombstone inspection, pagination inventory review | covered | Each action maps directly to a frozen WS02-05A requirement. |
| Inputs / boundaries | `application/json`, charset, `+json`, missing content type, non-JSON, malformed JSON, content encoding, oversized body | covered/grouped | Material media boundaries are executable without database proof. |
| Time | not applicable | not applicable | WS02-05A owns no time-boundary behavior. |
| Dependencies | FastAPI, OpenAPI generation, settings, route metadata | covered | These are source-owned dependencies for this pass. |
| Concurrency / idempotency | stale cursors, pagination races, API idempotency | deferred/covered elsewhere | WS02-05A does not approve numeric values or DB concurrency proof. |
| Authorization / privacy / security | cache classification, docs not authorization, sensitive OpenAPI content | covered | These are platform HTTP privacy/security boundaries. |
| Persistence / rollback | not applicable | not applicable | Focused WS02-05A evidence adds no database mutation. |
| Recovery | runtime/edge/provider recovery | deferred | These are later or external evidence classes. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | route missing from pagination contract or handoff inventory | pytest/source metadata |
| empty | yes | missing `Content-Type` on JSON body | pytest/API |
| corrupt | yes | malformed JSON under accepted media type | pytest/API |
| exceed | yes | body-size rejection remains distinct from media-type rejection | pytest/API |
| duplicate | yes | duplicate inventory ownership through contract/handoff overlap | pytest/source metadata |
| delay | no | no timeout or retry timing owned by WS02-05A | deferred |
| reorder | no | no ordering behavior owned except later pagination database proof | deferred |
| interrupt | no | no recovery or partial-failure mutation owned by WS02-05A | not applicable |
| race | no | stale-cursor and DB concurrency proof remains later | deferred |
| expire / revoke | no | no expiration or revocation contract owned by WS02-05A | not applicable |
| tamper | yes | unsafe OpenAPI schema text or stale pagination owner metadata | pytest/static |
| retry | no | retry/idempotency ownership remains broader API-M13/later work | deferred |
| recover | no | provider/runtime recovery is outside local WS02-05A evidence | deferred |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| `R1` | JSON-compatible media acceptance, explicit non-JSON rejection, missing content-type validation compatibility, malformed JSON, raw webhook exclusion, tombstone/bodyless exclusion, prerequisite body-limit/encoding distinction | pytest + backend HTTP/API | `test_json_media_type_contract.py` | Adequate for source-owned FastAPI behavior; does not claim provider or database proof. |
| `R2`, `R3` | 405 stable envelope, `Allow`, route-derived OpenAPI error responses, provider webhook 405 exclusion, public error schema sensitivity | pytest + generated OpenAPI | `test_method_openapi_error_contract.py` | Adequate for generated schema and current route metadata; does not claim every hypothetical runtime failure. |
| `R4`, `R5`, `R6` | private/public cache classes, docs/OpenAPI exposure, route authorization independence, tombstone OpenAPI representation | pytest + backend HTTP/API + settings inspection | `test_cache_docs_tombstone_contract.py` | Adequate for repository source; CDN/shared-cache/deployed provider behavior remains deferred. |
| `R7` | pagination contract/handoff completeness, live route agreement, owner metadata correction, no fake numeric limits | pytest + source route metadata | `test_pagination_inventory_contract.py` | Adequate for current repository inventory truth; DB query plans and stale-cursor behavior remain later. |
| `R8` | external/runtime/provider/full-chain and unapproved numeric pagination values | deferred | `ws02_05a.json`, this record | Correctly zero-mapped because local pytest cannot honestly prove these facts. |

### Evidence Quality Checks

- Exact time-boundary tests are not applicable because WS02-05A owns no timing
  rule.
- Successful mutations are not applicable because focused WS02-05A tests do
  not create durable application records.
- Rejected media and body-limit paths prove route-owned business/dependency
  behavior is not reached where that distinction is material.
- Idempotency tests are not applicable because WS02-05A does not approve retry
  or idempotency behavior.
- Genuine PostgreSQL race/concurrency behavior is not applicable to focused
  WS02-05A evidence; pagination DB behavior remains later.
- Provider calls are not mocked or contacted; Stripe webhook tests stop at the
  application-owned route boundary.
- Database-constraint tests are not applicable because WS02-05A changes no
  schema or constraint.

## 7. Important Side Effects

WS02-05A focused evidence is source-owned HTTP/API and static metadata proof.
It adds no database rows, migrations, provider objects, frontend state,
deployment resources, CDN settings, or runtime configuration.

Rejected media/body-limit tests assert prohibited dependency or service calls
do not occur where materially relevant. Pagination tests assert unresolved
handoffs remain unresolved rather than converting open risk into fake approved
contracts.

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| `WS02-05A-R8` | deferred | Permanent edge, CDN, proxy, TLS/HSTS, direct-origin, shared-cache, deployed docs access, process-server, staging/runtime, public-versioning, provider, DB query-plan/runtime, stale-cursor concurrency, bulk/export, telemetry/dashboard/alert, and unapproved numeric pagination values cannot be closed by local source tests. | WS03, WS04, WS07, WS08, WS09, WS10, provider/runtime evidence, future owner decisions |
| Request ownership and mass assignment | covered elsewhere | Accepted WS02-05B1 owns request ownership and request-schema cleanup. | WS02-05B1 |
| Response minimization and audience-specific reads | covered elsewhere | Accepted WS02-05B2 owns response minimization and audience separation. | WS02-05B2 |
| Request-body byte values and route classes | covered elsewhere | Accepted B2A1/B2A2C own current source body byte limits. | WS02-04B2A1, WS02-04B2A2C |
| Chat rate-limit 429 behavior | covered elsewhere | Accepted C3A owns chat limiter values and runtime 429 behavior; WS02-05A only documents route-derived OpenAPI metadata. | WS02-04C3A |
| Non-chat/provider-cost rate limits | covered elsewhere/deferred | Accepted C3B records no approved non-chat/provider-cost limiter values. | WS02-04C3B / later evidence |
| Cache at CDN/shared-cache layers | deferred | App headers cannot prove edge or shared-cache behavior. | WS08 / runtime/provider evidence |
| Pagination numeric values | deferred | FDN-04 requires workflow-specific evidence and approval before values are selected. | API owner / later owner decision |

## 9. Adequacy Conclusion

The selected evidence is adequate for the local WS02-05A Gate B scope when the
focused WS02-05A tests, adjacent platform regressions, full trusted backend
regression, checker/domain/suite checks, generated traceability, compile
validation, and `git diff --check` pass.

`WS02-05A-R1` through `WS02-05A-R7` must have trusted executable mappings under
`backend/tests/platform/http_contracts/`. `WS02-05A-R8` must remain deferred and
zero-mapped. Checker `PASS` remains structural compliance evidence only; Gate C
must still independently review semantic adequacy and confirm WS02-05A does not
overclaim API-M13, API-M14, API-M16, API-M18, API-M19, provider/runtime, CDN,
database-performance, or full HTTP-chain closure.
