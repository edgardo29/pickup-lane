# WS03-03B App Check Provider Security Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS03-03B` |
| Trusted test scope | `backend/tests/workflows/app_check_provider_security` |
| Requirement declaration | `backend/tests/support/requirements/ws03_03b.json` |
| Authoritative sources | Frozen WS03-03B canonical plan; `IAM-008`; `IAM-010`; `IAM-011`; `IDB-04`; accepted EN-02, EN-03, WS03-01, WS03-02, and WS03-03A boundaries |
| Evidence layers | pytest, frontend unit, source review, checker traceability, governance deferral |

## 1. Scope

This record covers repository-owned Firebase App Check source behavior: backend
mode parsing, supported web-app App ID binding, frontend token acquisition and
transport, backend use of the centralized Firebase provider-verification
boundary, route classification,
observe/enforced middleware behavior, safe denial contracts, bounded event
recording, and negative-space source checks.

It does not prove live Firebase App Check registration, reCAPTCHA Enterprise
domain configuration, deployed observe/enforced rollout, administrator MFA
enrollment, Firebase/GCP IAM, key inventory, secret-store injection, rotation,
revocation, monitoring, or production owner approval.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS03-03B-R1` | Backend and frontend App Check configuration is bounded and explicit where required. | pytest |
| `WS03-03B-R2` | Frontend App Check helper and API transport are centralized and non-leaking. | pytest and frontend unit |
| `WS03-03B-R3` | Backend verification uses the centralized Firebase App Check wrapper plus exact verified App ID comparison. | pytest |
| `WS03-03B-R4` | Disabled, observe, and enforced middleware behavior preserves HTTP contracts. | pytest |
| `WS03-03B-R5` | Route and caller policy is classified and fails closed for drift. | pytest |
| `WS03-03B-R6` | App Check remains defense in depth and preserves identity, authz, recent-auth, and replay safeguards. | pytest and frontend unit |
| `WS03-03B-R7` | Negative-space checks prevent bypasses, unsafe telemetry/storage, and false closure. | pytest |
| `WS03-03B-R8` | Administrator MFA is provider/governance evidence. | deferred |
| `WS03-03B-R9` | Firebase/GCP credential governance is provider/operations evidence. | deferred |
| `WS03-03B-R10` | Production App Check rollout requires provider/runtime evidence and owner approval. | deferred |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| R1 | Only disabled, observe, and enforced modes are accepted; production-like mode is explicit; observe/enforced require App ID. | Production silently defaults disabled or enforces with no supported app identity. | Rollout confusion or unsafe enforcement. | Typed settings parser and finite env contracts. | workflow/platform |
| R2 | Only normal Pickup Lane API requests receive `X-Firebase-AppCheck`. | Token leaks to provider uploads, URLs, bodies, cookies, or arbitrary absolute URLs. | Provider-token exposure and cross-origin leakage. | Central frontend helper and API-client source/unit tests. | workflow/frontend unit |
| R3 | The centralized Firebase provider wrapper verifies the token and the WS03 layer inspects only the verified App ID. | Source manually decodes JWTs, trusts client App ID, creates a second Firebase boundary, or treats ID tokens as App Check. | Forged source authenticity or duplicated provider ownership. | Narrow verifier boundary and negative-space scans. | workflow/C1 |
| R4 | Observe records and continues; enforced denies before endpoint side effects for missing/invalid/unavailable. | App Check fails open in enforced mode or breaks CORS/security/correlation. | Protected routes execute without source proof or public contract drifts. | Middleware behavior tests with injected verifier/recorder. | workflow |
| R5 | Registered API routes are classified from current routes and unclassified drift fails. | New API families silently bypass or provider callbacks are gated. | Coverage gap or provider outage. | Precomputed policy and route inventory tests. | workflow |
| R6 | App Check does not replace auth, authorization, recent-auth, rate limits, request limits, payment, or idempotency safeguards. | App Check token becomes identity or a replay/retry trigger. | Weaker security source. | Source negative-space and WS03 prerequisite regressions. | workflow |
| R7 | Evidence does not overclaim provider/governance closure. | Deferred facts get pytest mappings or raw provider/App ID material leaks. | False production-readiness closure or confidential data exposure. | Requirement states, zero mappings, and source inventory. | checker/workflow |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | anonymous, authenticated user, admin, provider callback, infrastructure probe | covered/grouped | App Check is route-source defense in depth and is independent of actor identity. |
| States / lifecycle | disabled, observe, enforced; valid, missing, invalid, unavailable | covered | These are the finite source-owned modes/outcomes. |
| Actions | request, preflight, provider upload, route construction, event recording | covered | Each action can bypass or break the App Check boundary. |
| Inputs / boundaries | missing/blank token, wrong header, wrong App ID, invalid mode, placeholder App ID | covered | These are the material source/config failure boundaries. |
| Time | token expiry and revocation | deferred | Firebase provider verification owns live expiry/revocation proof; local code classifies provider rejection. |
| Dependencies | Firebase Admin SDK, centralized `firebase.app_check.verify` wrapper, frontend Firebase SDK, CORS, public errors, EventEnvelope | covered/deferred | Local tests prove boundary use and fakes; live provider facts remain external. |
| Concurrency / idempotency | retry/replay | covered | Low-level API client must not add blind retry or mutation replay. |
| Authorization / privacy / security | auth separation, App ID non-disclosure, telemetry bounds | covered | Negative-space checks protect against App Check becoming identity or leaking provider detail. |
| Persistence / rollback | token persistence and endpoint side effects on denial | covered | Frontend tests/source scans block persistence; backend tests prove denial before endpoint execution. |
| Recovery | provider unavailable and rollout approval | covered/deferred | Source returns safe 503; production rollout/recovery evidence is external. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | missing mode/token/App ID | pytest |
| empty | yes | blank token/App ID/frontend site key | pytest and unit |
| corrupt | yes | invalid token/mode/manual JWT path | pytest and source scan |
| exceed | no | no App Check-owned length boundary | not applicable |
| duplicate | no | duplicate headers are framework-normalized | grouped through header-only behavior |
| delay | yes | provider unavailable | pytest with fake verifier |
| reorder | yes | middleware ordering and CORS preflight | pytest |
| interrupt | yes | recorder failure | pytest |
| race | no | no App Check persistence or shared mutable business state | not applicable |
| expire / revoke | yes | provider rejected token | provider-owned classification exercised as invalid |
| tamper | yes | query/body/client App ID/app-owned validity flags | source scan |
| retry | yes | frontend global retry/replay | source/unit |
| recover | yes | disabled/observe rollout and provider unavailable | pytest plus deferred rollout evidence |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| R1, R6, R7 | Settings modes, App ID, placeholders, finite config names | pytest | `test_app_check_settings_contract.py` plus compatibility tests | Enough for repository settings behavior; not provider registration. |
| R3, R4, R5, R6 | Verifier outcomes, middleware denials, events, HTTP contracts | pytest | `test_app_check_backend_contract.py` | Uses injected verifier/recorder at the owned boundary and proves invalid, timeout, and unavailable mapping; live Firebase remains external. |
| R4, R5, R6, R7 | Current route policy and unmatched 404/405/preflight behavior | pytest | `test_app_check_route_policy_contract.py` | Enough for current registered routes and fail-closed drift. |
| R2, R5, R6, R7 | API-client and provider-upload negative space | pytest/source | `test_app_check_frontend_transport_contract.py` | Enough for source ownership; real browser App Check remains external. |
| R1, R2, R3, R6, R7 | Bypass, logging, storage, telemetry, false closure inventory | pytest/source | `test_app_check_negative_space_contract.py` | Enough for local negative-space evidence, including no direct Firebase Admin SDK call in the App Check service. |
| R3, R4, R6, R7 | Firebase App Check timeout and retry ownership compatibility | C1/C2 pytest/source | `test_firebase_timeout_contract.py`; `test_c2_provider_operation_inventory_contract.py`; `provider_retry_policy.py` | C1 owns timeout classification for `firebase.app_check.verify`; C2 records it as a safe read with no application automatic retry. |
| R2, R6 | Token helper and transport behavior | frontend unit | `frontend/tests/unit/appCheckApiClient.test.js` | Enough for deterministic browser-source logic, not live provider behavior. |
| R8, R9, R10 | MFA, Firebase/GCP governance, production rollout | governance/provider | requirement JSON and this record | Local pytest cannot close these facts. |

## 7. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| Enforced valid App Check | Request continues to endpoint and one bounded event may be recorded. | App Check must not authenticate, authorize, or mutate business state. | Not applicable. |
| Enforced missing/invalid/unavailable | Safe 403/503 response before endpoint execution and one bounded event attempt. | No endpoint side effects; no raw token/App ID/provider exception exposure; no application retry or request replay. | Caller behavior remains outside this App Check proof layer. |
| Observe outcome | Endpoint behavior is unchanged and one bounded observation event may be recorded. | Recorder failure must not change the route result. | Best-effort event only. |
| Frontend token acquisition | Existing API request receives `X-Firebase-AppCheck` only when a token exists. | No URL/body/cookie/storage/log token persistence and no blind retry. | Acquisition failure returns no token and lets backend mode decide. |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| `WS03-03B-R8` | deferred | Administrator MFA is a Firebase/Identity Platform provider and governance fact. | WS03-03B/WS10 sanitized provider-governance evidence. |
| `WS03-03B-R9` | deferred | Firebase/GCP service-account mechanism, IAM, key inventory, rotation, revocation, and monitoring require provider/operations evidence. | EN-03/WS03-03B/WS10 sanitized provider-governance evidence. |
| `WS03-03B-R10` | deferred | Production App Check enforcement requires staged runtime proof, false-positive review, rollback, and owner approval. | WS03-03B/WS10 runtime/provider evidence. |
| Live App Check token verification | deferred | Local pytest uses fakes at the centralized Firebase Admin boundary and does not call provider network. | Provider sandbox/staging evidence. |

## 9. Adequacy Conclusion

This scope is adequate when focused App Check pytest, frontend unit tests,
compatibility tests, WS03 prerequisite regressions, domain/suite checker,
generated traceability, full backend regression, lint/build, and final
security-diff review pass.

R1 through R7 have executable repository evidence. R8 through R10 are
intentionally deferred/governance with zero pytest mappings. Checker `PASS` is
machine-compliance evidence only; human Gate C review must still judge semantic
adequacy and the explicit external evidence gaps.
