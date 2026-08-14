# Request Body Limits Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS02-04B2A1` and `WS02-04B2A2C` |
| Trusted test scope | `backend/tests/platform/request_body_limits/` |
| Requirement declaration | `backend/tests/support/requirements/ws02_04b2a1.json`; `backend/tests/support/requirements/ws02_04b2a2c.json` |
| Authoritative sources | Frozen B2A1 plan; frozen A2C plan; B2A1 owner decision; GOV-006/FDN-04 method; limits register; current request-body middleware source; WS02-04A; WS02-03; EN-02; WS02-04B1; WS02-04B2A2A/B1/B2/B3; WS02-05A |
| Evidence layers | Direct ASGI pytest, FastAPI/TestClient integration, route/static source review, settings/static review, deferred external evidence |

## 1. Scope

This record covers the shared source-owned FastAPI request-body limit evidence
for:

- B2A1 Platform Notice create special class;
- B2A1 signed Stripe webhook raw-body special class;
- A2C ordinary JSON route classification and 64 KiB body enforcement;
- actual ASGI-byte authority versus advisory `Content-Length`;
- non-identity `Content-Encoding` rejection for limited classes;
- stable public 413 and unsupported-content-encoding 415 behavior;
- typed backend settings and tracked `.env.example` documentation;
- source/static negative space for manual raw-body consumers, ownerless
  file/form/multipart request bodies, and duplicate body-limit classes.

This scope intentionally does not prove external ingress, edge,
process-server, permanent-host, staging, provider hard limits, live Stripe
behavior, R2 object-byte enforcement, explicit non-JSON media closure,
OpenAPI/cache behavior, telemetry, dashboards, alerts, load evidence,
frontend behavior, or broader request/response ownership.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS02-04B2A1-R1` | Platform Notice create uses only the approved 160 KiB special request-body class. | pytest |
| `WS02-04B2A1-R2` | Signed Stripe webhook requests use only the approved 64 KiB raw-body special class and preserve exact raw bytes. | pytest |
| `WS02-04B2A1-R3` | Actual ASGI bytes, not trusted length metadata, determine B2A1 body acceptance. | pytest |
| `WS02-04B2A1-R4` | Non-identity `Content-Encoding` is rejected for B2A1 classes without decompression. | pytest |
| `WS02-04B2A1-R5` | B2A1 rejections use stable safe public 413/415 errors with inherited correlation/security/CORS behavior. | pytest |
| `WS02-04B2A1-R6` | B2A1 limit settings are typed, positive, documented, and distinct from ordinary JSON settings. | pytest/static |
| `WS02-04B2A1-R7` | A single middleware owner selects B2A1 classes without duplicate body-limit ownership or raw-body bypass. | pytest/static |
| `WS02-04B2A1-R8` | Later/external body, media-type, provider, runtime, and observability gaps remain explicit. | deferred |
| `WS02-04B2A2C-R1` | Ordinary JSON route classification is derived from current FastAPI final body metadata and remains current. | pytest/static |
| `WS02-04B2A2C-R2` | Ordinary JSON limit configuration is typed, positive, documented, backend-only, and independent. | pytest/static |
| `WS02-04B2A2C-R3` | Actual received ASGI bytes are authoritative for ordinary JSON requests. | pytest |
| `WS02-04B2A2C-R4` | Accepted ordinary bytes are preserved, and rejected ordinary bodies do not reach protected downstream seams. | pytest |
| `WS02-04B2A2C-R5` | Special and bodyless route boundaries remain separate from ordinary JSON. | pytest/static |
| `WS02-04B2A2C-R6` | Ordinary body-limit failures use safe app-owned behavior without claiming full HTTP media closure. | pytest |
| `WS02-04B2A2C-R7` | Later/external request-limit evidence remains explicit. | deferred |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| `B2A1-R1`, `B2A1-R7` | Only `POST /admin/platform-notices` receives the Platform Notice special limit. | Nearby Platform Notice routes are treated as create, or create bypasses the special class. | Wrong route class is protected or unprotected. | Method/path special-class selection before downstream body reads. | platform |
| `B2A1-R2`, `B2A1-R7` | Only signed `POST /stripe/webhook` receives the signed raw-body special limit. | Missing-signature requests become false evidence, raw bytes are altered, or over-limit signed requests reach provider processing. | Signature verification breaks or unsafe payloads reach mutation seams. | Signature-header class selection, byte preservation, and early rejection. | platform |
| `B2A1-R3`, `A2C-R3` | Actual ASGI bytes govern acceptance for limited classes. | Missing, malformed, duplicate, or underdeclared `Content-Length` bypasses enforcement. | Oversized bodies reach parser, dependency, database, provider, or business work. | Counting receive wrapper with early length rejection only when safe. | platform/direct ASGI |
| `B2A1-R4`, `A2C-R6` | Non-identity encoding is rejected without decompression. | Compressed bodies bypass byte limits or decoded bytes are implicitly trusted. | Resource abuse and ambiguous size semantics. | Encoding rejection before body processing. | platform |
| `B2A1-R5`, `A2C-R6` | Limited-class failures are stable, correlated where applicable, and safe. | Body, private header, provider data, database URL, credential, traceback, or internal diagnostic leaks. | Privacy/security exposure and broken client contract. | Public error helpers plus inherited middleware. | platform/TestClient |
| `A2C-R1`, `A2C-R5` | Ordinary routes are selected from final FastAPI body metadata, not a stale manual list. | Dependency-body routes, future retained routes, or manual raw-body consumers bypass all approved classes. | Ordinary JSON bodies may become unbounded. | Route-table/static proof against current app metadata and source. | platform/static |
| `A2C-R4` | Rejected ordinary bodies do not reach protected downstream seams. | The app parses or runs dependency/business work before rejecting. | The size limit would not protect application resources. | Direct ASGI and FastAPI dependency/handler cutoff proof. | platform |
| `B2A1-R6`, `A2C-R2` | Limits are typed positive backend settings and documented once. | Defaults drift, invalid values boot, duplicate env owners appear, or frontend reads backend-private limits. | Unreviewed thresholds or confused ownership. | Settings parser, env registry, `.env.example`, static ownership, and frontend non-exposure checks. | platform/settings |
| `B2A1-R8`, `A2C-R7` | Later and external gaps remain non-executable. | Local tests claim provider, edge, media, R2, runtime, or broader request/response closure. | False production-readiness closure. | Deferred declarations and testing-record boundaries. | governance |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | Admin source route, Stripe provider webhook, ordinary API caller, application middleware | grouped | This scope owns request classes, not user-role policy. |
| States / lifecycle | exact limit, under limit, over limit, missing signature, signed request, unsupported encoding, bodyless tombstone | covered/grouped | These states control source-owned body-limit selection and failure behavior. |
| Actions | create Platform Notice, receive Stripe webhook, ordinary JSON body route, read ASGI body, parse settings | covered | These are the source-owned actions that can cross the body boundary. |
| Inputs / boundaries | missing/misleading/malformed/duplicate `Content-Length`, exact boundary, multi-message body, non-identity encoding, sensitive markers, missing content type | covered/grouped | They represent material size, encoding, route-classification, and leakage risks. |
| Time | Not applicable | not applicable | No time-boundary behavior is owned here. |
| Dependencies | Stripe construction seam, FastAPI body dependency, route metadata, settings env, source files | covered/grouped | Fakes and synthetic routes are placed at application-owned seams; no live provider or DB mutation is required. |
| Concurrency / idempotency | Stripe duplicate/idempotent processing; broader body-limit races | deferred/not applicable | WS05 owns webhook lifecycle; this scope proves pre-processing source limits only. |
| Authorization / privacy / security | safe error payload, private header/body/signature exclusion, CORS/security headers | covered | Errors inherit WS02-04A/WS02-03/EN-02 safety contracts. |
| Persistence / rollback | prohibited downstream mutation after rejection | covered through fakes/static | Rejection occurs before DB/provider/business work; no persistence is owned here. |
| Recovery | Smaller valid body can retry; stale tombstones remain bodyless; provider/runtime failures external | grouped/deferred | Local source proves stable failure and classification only. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | Missing `Content-Length`, absent `Content-Encoding`, missing Stripe signature, missing `Content-Type` | pytest; missing signature/media details are route or WS02-05A-owned |
| empty | yes | Zero-byte ASGI messages | B2A1 direct ASGI pytest |
| corrupt | yes | Malformed `Content-Length`, non-identity encoding, secret-like payload markers | pytest |
| exceed | yes | limit plus one, declared length above limit | pytest |
| duplicate | yes | duplicate/conflicting `Content-Length` | pytest |
| delay | no | No timeout owned by this scope | not applicable |
| reorder | yes | multi-message ASGI sequencing | pytest |
| interrupt | yes | `http.disconnect` and non-request message pass-through | B2A1 direct ASGI pytest |
| race | no | No concurrency contract owned here | not applicable |
| expire / revoke | no | No expiry contract owned here | not applicable |
| tamper | yes | misleading `Content-Length`, altered body bytes, body on tombstone | pytest |
| retry | no | Retrying smaller bodies is client behavior; no retry policy owned | not applicable |
| recover | no | No runtime recovery contract owned | later evidence |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| `B2A1-R1`, `B2A1-R7` | Platform Notice special-class selection and nearby-route exclusion | TestClient/direct middleware | `test_request_body_limit_route_selection.py` | Adequate for source route class and early rejection; not B1 persistence proof. |
| `B2A1-R2`, `B2A1-R7` | Signed Stripe class selection, raw bytes, and pre-processing rejection | TestClient with app-owned fakes | `test_request_body_limit_route_selection.py` | Adequate for app-owned Stripe seam; not live Stripe/provider limit proof. |
| `B2A1-R3`, `B2A1-R4` | actual bytes, `Content-Length`, multi-message, cutoff, non-HTTP/disconnect, encoding | Direct ASGI | `test_request_body_limit_asgi_contract.py` | Adequate for B2A1 middleware byte semantics; transport before ASGI remains external. |
| `B2A1-R5` | B2A1 413/unsupported-content-encoding 415 safety and inherited headers | TestClient | `test_request_body_limit_error_contract.py` | Adequate for app-owned error envelope; provider/edge errors external. |
| `B2A1-R6` | B2A1 defaults, env parsing, `.env.example`, config ownership | pytest/static | `test_request_body_limit_settings_contract.py` | Adequate for repository settings; runtime provider config external. |
| `A2C-R1`, `A2C-R5` | final-body route inventory, direct-vs-final metadata, dependency-body inheritance, special/bodyless/tombstone negative space, manual raw-body/source negative space | FastAPI route/static pytest | `test_ordinary_json_route_inventory_contract.py` | Adequate for current source-owned route classification; future route drift must update evidence. |
| `A2C-R2` | ordinary default, positive parsing, invalid rejection, env registry, `.env.example`, backend-only ownership, no frontend exposure | pytest/static | `test_request_body_limit_settings_contract.py` | Adequate for typed source configuration; deployed env injection evidence remains external. |
| `A2C-R3`, `A2C-R4` | exact ordinary boundary, limit plus one, `Content-Length`, missing/malformed/duplicate/underdeclared length, multi-message counting, downstream cutoff, path regex/trailing slash | Direct ASGI and synthetic FastAPI pytest | `test_ordinary_json_request_body_limit_contract.py` | Adequate for source-owned ordinary byte semantics; ingress/process-server limits remain external. |
| `A2C-R6` | ordinary safe 413/415 behavior, sensitive-data non-leakage, supported JSON compatibility, missing-content-type non-closure | TestClient and synthetic FastAPI pytest | `test_request_body_limit_error_contract.py` | Adequate for A2C stable error interaction; explicit non-JSON media behavior remains WS02-05A-owned. |
| `B2A1-R8`, `A2C-R7` | non-closure boundaries | declarations/record/static review | this record and requirement declarations | Adequate to prevent fake local closure; later evidence still required. |

### Evidence Quality Checks

- Boundary tests use controlled byte payloads and exact byte counts.
- Accepted-body tests prove byte-for-byte downstream delivery.
- Rejected-body tests prove protected downstream seams were not called or did
  not receive the rejected payload.
- `Content-Length` tests prove actual bytes still govern acceptance.
- Route-inventory tests derive from current FastAPI metadata rather than a
  hand-copied historical list.
- Static source tests prove signed Stripe is the only current manual raw-body
  consumer and that file/form/multipart request bodies are not introduced.
- Settings tests distinguish backend-private configuration from frontend-public
  configuration.
- Stripe/provider seams are faked at application-owned boundaries.
- No PostgreSQL race, mutation, idempotency, controlled time, browser,
  migration, live provider, or runtime proof is manufactured for this scope.
- Database-constraint proof is not applicable because rejection occurs before
  database mutation.

## 7. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| Platform Notice create body reaches limit boundary | Under-limit body reaches normal downstream processing. | Over-limit body must not reach protected body/dependency/handler work. | No B2A1 persistence claim. |
| Signed Stripe webhook body reaches limit boundary | Under-limit signed raw bytes reach Stripe construction unchanged. | Over-limit signed body must not call Stripe construction, webhook processing, or business mutation seam. | Provider redelivery/idempotency remains WS05. |
| Ordinary JSON body reaches limit boundary | Exact-limit and under-limit bytes reach downstream unchanged. | Over-limit ordinary bodies must not reach protected route/dependency/body/business work. | No A2C persistence claim. |
| Limited-class error response | Stable public response with safe details and correlation/security/CORS behavior where applicable. | No body, signature, private header, provider value, database URL, credential, or debug leak. | Client may retry with a smaller valid body. |
| Settings parsing | Valid positive values configure app source boundaries. | Zero, negative, malformed values must fail settings construction. | Numeric changes require owner decision. |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| `WS02-04B2A1-R8` | deferred | Ordinary JSON body limits are A2C-owned; media/provider/runtime/edge evidence cannot be proven locally. | WS02-04B2A2C, WS02-05A, WS02-04B2B/B2C, WS05, WS09 |
| `WS02-04B2A2C-R7` | deferred | External ingress, edge, process-server, provider hard limits, request-line/header limits, form/multipart/file upload limits, R2 object-byte limits, permanent-host/staging precedence, runtime/load evidence, telemetry, dashboards, alerts, provider proof, broad request/response ownership, and OpenAPI/cache/media contracts are outside local A2C source tests. | Listed downstream owners |
| Explicit non-JSON `Content-Type` / `API.UNSUPPORTED_MEDIA_TYPE` | covered elsewhere | The middleware contains media behavior, but A2C must not claim full HTTP/media closure. | WS02-05A |
| Stripe provider payload limits and dashboard state | deferred | Local fakes prove source orchestration only. | WS05 / provider evidence |
| Edge, ingress, process-server, permanent-host, staging precedence | deferred | These occur before or around FastAPI and require runtime/provider evidence. | WS02-04B2B / WS02-04B2C |
| R2 object bytes | deferred | Direct object upload bytes bypass FastAPI request bodies. | WS06 / storage evidence |
| Runtime telemetry, dashboards, alerts | deferred | Local tests do not prove production observability. | WS09 |

## 9. Adequacy Conclusion

The selected evidence is adequate for the shared B2A1/A2C request-body-limit
scope when:

- focused `backend/tests/platform/request_body_limits` pytest passes;
- targeted adjacent settings, HTTP-security, API-error, B1, B2, and B3
  regressions pass;
- the full current trusted backend regression passes;
- checker domain and suite scopes pass;
- generated traceability maps B2A1 R1-R7 and A2C R1-R6 to current trusted
  executable evidence;
- B2A1 R8 and A2C R7 remain zero-mapped and deferred;
- compile/static validation and `git diff --check` pass.

Checker `PASS` is structural compliance only. Human Gate C review remains
responsible for judging semantic adequacy and confirming that no later/provider
closure is overclaimed.
