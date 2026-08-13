# WS02-04B2A1 Request Body Limits Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS02-04B2A1` |
| Trusted test scope | `backend/tests/platform/request_body_limits/` |
| Requirement declaration | `backend/tests/support/requirements/ws02_04b2a1.json` |
| Authoritative sources | Frozen WS02-04B2A1 plan, B2A1 owner decision, GOV-006/FDN-04 method, limits register, current request-body middleware source, WS02-04A, WS02-03, EN-02, WS02-04B1, WS02-04B2A2C, WS02-05A |
| Evidence layers | Direct ASGI pytest, FastAPI/TestClient integration, settings/static review, source review, deferred external evidence |

## 1. Scope

This record covers source-owned FastAPI request-body limit evidence for
WS02-04B2A1: the Platform Notice create special class, the signed Stripe webhook
special class, actual ASGI-byte enforcement, advisory `Content-Length`
behavior, B2A1 route selection, non-identity `Content-Encoding` rejection,
stable public B2A1 errors, and typed B2A1 settings.

This scope intentionally does not prove ordinary JSON body limits, explicit
non-JSON `Content-Type` behavior, `API.UNSUPPORTED_MEDIA_TYPE`, provider hard
limits, edge/ingress/process-server limits, permanent-host or staging
precedence, R2 object-byte limits, runtime telemetry, dashboards, alerts, or
live Stripe behavior.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS02-04B2A1-R1` | Platform Notice create uses only the approved 160 KiB special request-body class. | pytest |
| `WS02-04B2A1-R2` | Signed Stripe webhook requests use only the approved 64 KiB special request-body class and preserve exact raw bytes. | pytest |
| `WS02-04B2A1-R3` | Actual ASGI bytes, not trusted length metadata, determine B2A1 body acceptance. | pytest |
| `WS02-04B2A1-R4` | Non-identity `Content-Encoding` is rejected for B2A1 classes without decompression. | pytest |
| `WS02-04B2A1-R5` | B2A1 rejections use stable safe public 413/unsupported-content-encoding 415 errors with inherited correlation/security/CORS behavior. | pytest |
| `WS02-04B2A1-R6` | B2A1 limit settings are typed, positive, documented, and distinct from ordinary JSON settings. | pytest/static |
| `WS02-04B2A1-R7` | A single middleware owner selects B2A1 classes without duplicate body-limit ownership or raw-body bypass. | pytest/static |
| `WS02-04B2A1-R8` | Later/external body, media-type, provider, runtime, and observability gaps remain explicit. | deferred |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| `R1`, `R7` | Only `POST /admin/platform-notices` receives the Platform Notice special limit. | Nearby Platform Notice list/recipient/cancel routes are treated as create, or create bypasses the special class. | Wrong route class is protected or unprotected. | Method/path special-class selection before downstream body reads. | platform |
| `R2`, `R7` | Only signed `POST /stripe/webhook` receives the signed-webhook special limit. | Missing-signature requests become false evidence, signed bytes are altered, or over-limit signed requests reach Stripe/provider processing. | Signature verification breaks or unsafe payloads reach mutation seams. | Signature-header class selection, byte preservation, and early rejection. | platform |
| `R3` | Actual ASGI bytes govern acceptance. | `Content-Length` lies, multi-message delivery, missing length, malformed length, or exact boundaries bypass enforcement. | Oversized bodies reach app processing. | Counting receive wrapper with early length rejection only when safe. | platform/direct ASGI |
| `R4` | Non-identity `Content-Encoding` is rejected without decompression. | Compressed bodies bypass byte limits or decoded bytes are implicitly trusted. | Resource abuse and ambiguous size semantics. | Encoding rejection before body processing. | platform/direct ASGI |
| `R5` | B2A1 rejections are stable, correlated, and safe. | Body, signature, private header, provider value, or internals leak in errors. | Privacy/security exposure and broken client contract. | Public error helpers plus inherited middleware. | platform/TestClient |
| `R6` | B2A1 settings are typed positive integers and documented. | Defaults drift, invalid values boot, duplicate owners appear, or ordinary JSON is mislabeled B2A1. | Unreviewed thresholds or confused ownership. | Settings parser, env registry, `.env.example`, and static ownership checks. | platform/settings |
| `R8` | Later and external gaps remain non-executable. | Local tests claim provider, edge, media-type, ordinary JSON, R2, or telemetry closure. | False production-readiness closure. | Deferred declaration and testing-record boundary. | governance |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | Admin source route, Stripe provider webhook, application middleware | grouped | B2A1 owns request classes, not authorization roles. |
| States / lifecycle | exact limit, under limit, over limit, missing signature, signed request, unsupported encoding | covered | These states control body-limit selection and failure behavior. |
| Actions | create Platform Notice, receive Stripe webhook, read ASGI body, parse settings | covered | These are the source-owned actions that can cross the body boundary. |
| Inputs / boundaries | missing/misleading/malformed/duplicate `Content-Length`, multi-message body, zero bytes, non-identity encoding, sensitive markers | covered | They represent material body-size, encoding, and leakage risks. |
| Time | Not applicable | not applicable | B2A1 owns no time-boundary behavior. |
| Dependencies | Stripe construction seam, webhook business seam, database dependency, settings env, source files | covered/grouped | Fakes are placed at application-owned seams to prove prohibited downstream work without live providers or DB mutation. |
| Concurrency / idempotency | Stripe duplicate/idempotent processing | deferred | WS05 owns broader webhook lifecycle; B2A1 only proves pre-processing body limits. |
| Authorization / privacy / security | safe error payload, private header/body/signature exclusion, CORS/security headers | covered | B2A1 errors inherit WS02-04A/WS02-03/EN-02 safety contracts. |
| Persistence / rollback | prohibited downstream mutation after B2A1 rejection | covered through fakes | B2A1 rejection must prevent mutation seams; persisted effects remain other passes. |
| Recovery | Smaller valid body can retry; provider/runtime failures external | grouped/deferred | Local source proves stable failure only. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | Missing `Content-Length`, absent `Content-Encoding`, missing Stripe signature | pytest; missing signature is route-owned |
| empty | yes | Zero-byte ASGI messages | pytest |
| corrupt | yes | Malformed `Content-Length`, non-identity encoding, secret-like payload markers | pytest |
| exceed | yes | limit plus one, declared length above limit | pytest |
| duplicate | yes | duplicate/conflicting `Content-Length` | pytest |
| delay | no | No timeout owned by B2A1 | not applicable |
| reorder | yes | multi-message ASGI sequencing | pytest |
| interrupt | yes | `http.disconnect` and non-request message pass-through | pytest |
| race | no | No concurrency contract owned by B2A1 | not applicable |
| expire / revoke | no | No expiry contract owned by B2A1 | not applicable |
| tamper | yes | misleading `Content-Length`, altered body bytes | pytest |
| retry | no | Retrying smaller bodies is client behavior; no retry policy owned | not applicable |
| recover | no | No runtime recovery contract owned | later evidence |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| `R1`, `R7` | Platform Notice special-class selection and nearby-route exclusion | TestClient/direct middleware | `test_request_body_limit_route_selection.py` | Adequate for source route class and early rejection; not B1 persistence proof. |
| `R2`, `R7` | Signed Stripe class selection, raw bytes, and pre-processing rejection | TestClient with app-owned fakes | `test_request_body_limit_route_selection.py` | Adequate for app-owned Stripe seam; not live Stripe/provider limit proof. |
| `R3` | actual bytes, `Content-Length`, multi-message, cutoff, non-HTTP/disconnect | Direct ASGI | `test_request_body_limit_asgi_contract.py` | Adequate for middleware byte semantics; transport before ASGI remains external. |
| `R4` | content-encoding acceptance/rejection and no decompression | Direct ASGI | `test_request_body_limit_asgi_contract.py` | Adequate for B2A1 encoding rule; no global content policy claimed. |
| `R5` | 413/unsupported-content-encoding 415 error safety and inherited headers | TestClient | `test_request_body_limit_error_contract.py` | Adequate for app-owned error envelope; provider/edge errors external. |
| `R6` | defaults, env parsing, `.env.example`, config ownership | pytest/static | `test_request_body_limit_settings_contract.py` | Adequate for repository settings; runtime provider config external. |
| `R8` | non-closure boundaries | declaration/record/static review | this record and `ws02_04b2a1.json` | Adequate to prevent fake local closure; later evidence still required. |

### Evidence Quality Checks

- Boundary tests use controlled byte payloads and exact byte counts.
- Accepted-body tests prove byte-for-byte downstream delivery.
- Rejected-body tests prove protected downstream seams were not called.
- `Content-Length` tests prove actual bytes still govern acceptance.
- Stripe/provider seams are faked at application-owned boundaries.
- No PostgreSQL race, mutation, idempotency, controlled time, browser, or
  migration proof is manufactured for this pass.
- Database-constraint proof is not applicable because B2A1 rejection occurs
  before database mutation.

## 7. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| Platform Notice create body reaches limit boundary | Under-limit body reaches normal downstream processing. | Over-limit body must not reach protected body/dependency/handler work. | No B2A1 persistence claim. |
| Signed Stripe webhook body reaches limit boundary | Under-limit signed raw bytes reach Stripe construction unchanged. | Over-limit signed body must not call Stripe construction, webhook processing, or business mutation seam. | Provider redelivery/idempotency remains WS05. |
| B2A1 error response | Stable public response with safe details and correlation/security/CORS behavior. | No body, signature, private header, provider value, or debug leak. | Client may retry with smaller valid body. |
| B2A1 settings parsing | Valid positive values configure app source boundaries. | Zero, negative, malformed values must fail settings construction. | Numeric changes require owner decision. |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| `WS02-04B2A1-R8` | deferred | Ordinary JSON body limits and route metadata are owned elsewhere; JSON media type is owned elsewhere; provider/runtime/edge evidence cannot be proven locally. | WS02-04B2A2C, WS02-05A, WS02-04B2B/B2C, WS05, WS09 |
| Ordinary JSON request bodies | covered elsewhere | Same middleware currently handles them, but ownership is B2A2C. | WS02-04B2A2C |
| Explicit non-JSON `Content-Type` / `API.UNSUPPORTED_MEDIA_TYPE` | covered elsewhere | Current middleware contains this behavior, but B2A1 must not tag it as evidence. | WS02-05A |
| Stripe provider payload limits and dashboard state | deferred | Local fakes prove source orchestration only. | WS05 / provider evidence |
| Edge, ingress, process-server, permanent-host, staging precedence | deferred | These occur before or around FastAPI and require runtime/provider evidence. | WS02-04B2B / WS02-04B2C |
| R2 object bytes | deferred | Direct object upload bypasses FastAPI request bodies. | WS06 / storage evidence |
| Runtime telemetry, dashboards, alerts | deferred | Local tests do not prove production observability. | WS09 |

## 9. Adequacy Conclusion

The selected evidence is adequate for WS02-04B2A1 when the request-body-limit
pytest scope passes, checker file/domain/suite scopes pass, generated
traceability maps R1-R7 to genuine executable tests, R8 remains unmapped and
deferred, adjacent API error/settings/Platform Notice trusted regressions pass,
the full current trusted backend regression passes, and final review confirms
the six-file Gate B evidence scope did not modify production/configuration or
claim later provider/runtime work.

Checker `PASS` is structural compliance only. Human Gate C review remains
responsible for judging semantic adequacy.
