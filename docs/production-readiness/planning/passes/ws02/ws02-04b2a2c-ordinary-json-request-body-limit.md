# WS02-04B2A2C - Ordinary JSON Request Body Limit

## At A Glance

| Field | Value |
|---|---|
| Pass | `WS02-04B2A2C` |
| Track | `WS02` |
| Type | API/platform request-body limit recheck, configuration reconciliation, and trusted evidence reconstruction |
| Primary controls | `API-M09`, `GOV-006` |
| Authority basis | Current accepted repository tree; `API-M09`; `GOV-006` / `FDN-04`; `docs/production-readiness/governance/limits-and-thresholds-register.md`; `docs/production-readiness/planning/passes/ws02/ws02-04-source-owned-closeout.md`; `docs/production-readiness/planning/passes/ws02/ws02-04b2a1-portable-request-boundaries.md`; accepted adjacent `WS02-04B2A2A`, `WS02-04B2A2B1`, `WS02-04B2A2B2`, `WS02-04B2A2B3`, and `WS02-05A` plans |
| Depends on | `EN-01`; `EN-02`; `WS02-03`; `WS02-04A`; `WS02-04B2A1`; `WS02-04B2A2A`; `WS02-04B2A2B1`; `WS02-04B2A2B2`; `WS02-04B2A2B3`; `WS02-05A` |
| Trusted test scope | `backend/tests/platform/request_body_limits/` |

## 1. Purpose

WS02-04B2A2C establishes the source-owned ordinary JSON request-body byte
limit for Pickup Lane's retained FastAPI JSON request routes.

An ordinary JSON route is a normal application route whose final FastAPI body
metadata declares a request body and that is not one of the approved special
request-body classes. The pass makes those ordinary request bodies finite
before route parsing, authentication work, database work, provider work, or
business mutation can process an oversized body.

The ordinary JSON limit is 64 KiB / 65,536 bytes. That value is already recorded
in the current accepted repository as the A2C-owned ordinary JSON body limit in
the GOV-006 limits register and WS02-04 source-owned closeout. This recheck does
not invent, widen, or reopen the value.

A2C does not complete all request-size, HTTP, provider, edge, browser, staging,
or observability work. It proves the local FastAPI source boundary for ordinary
JSON request bodies and preserves the handoffs to the passes that own special
body classes, field-level schema bounds, HTTP media behavior, external ingress,
provider limits, and runtime evidence.

## 2. Why This Matters

Without a finite ordinary JSON body limit, a normal API caller can send a large
JSON request body to a retained application route and force the backend to spend
memory and parser work before the application rejects the request. That creates
a resource-exhaustion risk and can let unsafe payloads reach dependency,
database, provider, or mutation seams that should never see over-limit input.

The limit must be source-owned because permanent ingress, process-server,
provider, and staging evidence remains outside this pass. FastAPI can still
enforce a real application-owned boundary now. Later edge or provider limits may
reject earlier, but they do not replace the local source contract.

The route selection also matters. A body limit that is maintained as a manual
route list can drift when routes are added, retired, or converted to bodyless
tombstones. A2C therefore relies on FastAPI route body metadata so retained
ordinary JSON routes are selected by the current application structure, while
bodyless routes and approved special classes stay out of the ordinary class.

## 3. Requirements

| ID | Requirement | What it means | Why it matters |
|---|---|---|---|
| `WS02-04B2A2C-R1` | Ordinary JSON route classification is metadata-derived and current. | The application selects ordinary routes from FastAPI `APIRoute` final body metadata with non-bodyless methods and `route.body_field is not None`, excluding approved special classes. The current accepted baseline has 81 ordinary JSON routes, and direct endpoint body parameters currently match the final body-field inventory. | Prevents stale manual inventories and makes future retained JSON body routes inherit the ordinary class unless explicitly reviewed as special. |
| `WS02-04B2A2C-R2` | The ordinary JSON limit is the approved typed backend setting. | Ordinary JSON request bodies use the 64 KiB / 65,536-byte default, parse `ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES` as a positive integer, keep the setting backend-only, and keep it distinct from Platform Notice and signed Stripe webhook limits. | Prevents unreviewed numeric drift, invalid boot configuration, frontend exposure, or accidental coupling between request classes. |
| `WS02-04B2A2C-R3` | Actual received ASGI bytes are authoritative for ordinary JSON requests. | Exact-limit bodies are accepted, limit-plus-one bodies are rejected, valid oversized `Content-Length` may reject early, and missing, malformed, duplicate, or underdeclared `Content-Length` cannot bypass actual-byte counting across multi-message ASGI delivery. | Prevents callers from using misleading metadata or chunked delivery to move oversized bodies into parsing or business logic. |
| `WS02-04B2A2C-R4` | Accepted ordinary bytes are preserved and rejected ordinary bodies do not reach protected downstream work. | Under-limit ordinary bodies reach downstream parsing unchanged. Over-limit ordinary bodies are rejected before the relevant downstream route/dependency/body/business seam can process the payload. | Proves the body limiter protects the application rather than merely returning a status after work already happened. |
| `WS02-04B2A2C-R5` | Special and bodyless route boundaries remain separate from ordinary JSON. | Platform Notice create keeps its 160 KiB special class, signed Stripe webhook requests keep their raw-body 64 KiB special class, bodyless routes and tombstones are excluded, and no policy/payment/legal route invents a pass-specific body-limit class. | Preserves B2A1, B1, B2, B3, and WS02-05A ownership instead of blending unrelated request classes into ordinary JSON. |
| `WS02-04B2A2C-R6` | Ordinary JSON body-limit failures use safe app-owned behavior without claiming the whole HTTP media contract. | Ordinary oversized requests use stable safe 413 behavior, non-identity content encoding is rejected for limited ordinary routes, accepted JSON media behavior remains compatible, and explicit non-JSON media-type policy remains WS02-05A-owned. | Keeps size-limit errors safe and correlated while avoiding false closure of media/OpenAPI/cache work. |
| `WS02-04B2A2C-R7` | Later and external request-limit evidence remains explicit. | External ingress, edge, process-server, provider hard limits, request-line/header limits, form/multipart/file upload limits, R2 object-byte limits, permanent-host/staging precedence, runtime/load evidence, telemetry, dashboards, alerts, and broader request/response ownership are not closed by A2C local source evidence. | Prevents the local FastAPI proof from being mistaken for full production infrastructure or provider closure. |

### Requirement Declaration Design

Gate B must create `backend/tests/support/requirements/ws02_04b2a2c.json` with
this exact machine declaration design:

| Requirement ID | State | Scope | `source_controls` | Reason |
|---|---|---|---|---|
| `WS02-04B2A2C-R1` | `required` | `platform/request_body_limits` | `["API-M09", "GOV-006", "WS02-04B2A1", "WS02-04B2A2C", "WS02-04B2A2B1", "WS02-04B2A2B2", "WS02-04B2A2B3"]` | Not required. |
| `WS02-04B2A2C-R2` | `required` | `platform/request_body_limits` | `["API-M09", "GOV-006", "FDN-04", "WS02-04B2A2C", "WS02-01"]` | Not required. |
| `WS02-04B2A2C-R3` | `required` | `platform/request_body_limits` | `["API-M09", "GOV-006", "FDN-04", "WS02-04B2A1", "WS02-04B2A2C"]` | Not required. |
| `WS02-04B2A2C-R4` | `required` | `platform/request_body_limits` | `["API-M09", "WS02-04B2A2C", "WS02-04B2A2A", "WS02-04B2A2B1", "WS02-04B2A2B2", "WS02-04B2A2B3"]` | Not required. |
| `WS02-04B2A2C-R5` | `required` | `platform/request_body_limits` | `["API-M09", "GOV-006", "WS02-04B2A1", "WS02-04B2A2C", "WS05"]` | Not required. |
| `WS02-04B2A2C-R6` | `required` | `platform/request_body_limits` | `["API-M09", "API-M12", "API-M13", "WS02-04A", "WS02-05A", "WS02-03", "EN-02", "WS02-04B2A2C"]` | Not required. |
| `WS02-04B2A2C-R7` | `deferred` | `governance` | `["API-M09", "API-M13", "API-M14", "API-M18", "GOV-006", "FDN-04", "WS02-04B2A1", "WS02-04B2A2C", "WS02-05A", "WS02-05B1", "WS02-05B2", "WS05", "WS06", "WS09"]` | `External ingress, edge, process-server, provider hard limits, request-line and header limits, form/multipart/file upload limits, direct R2 object-byte limits, permanent-host and staging precedence, runtime/load evidence, telemetry, dashboards, alerts, Stripe/provider dashboard proof, broad request/response ownership, and OpenAPI/cache/media contracts beyond the source-owned ordinary JSON boundary remain with their listed owners and cannot be closed by A2C local source tests.` |

`WS02-04B2A2C-R7` must have zero pytest mappings.

## 4. Technical Design / Contracts

### 4.1 Numeric Value And Authority

**What this is**

The ordinary JSON body limit is the finite byte budget for normal FastAPI JSON
request bodies that do not belong to an approved special class.

**Contract / required behavior**

- Ordinary JSON request bodies use 64 KiB / 65,536 bytes.
- The current approved basis is the accepted A2C source-owned limit recorded in
  the current repository, including the GOV-006 limits register and
  WS02-04 source-owned closeout.
- The current evidence basis preserved in the accepted A2C planning record is
  that the largest deterministic ordinary route family measured during
  readiness was Need-a-Sub at 29,042 compact JSON bytes using escaped non-BMP
  worst-case text, leaving 36,494 bytes below the 65,536-byte ordinary JSON
  limit.
- The value remains source-owned FastAPI application enforcement only.
- A later numeric change requires a superseding approved owner decision or
  accepted later-owner authority.

**Why**

`GOV-006` and `FDN-04` require documented bases and boundary tests for numeric
limits. A2C preserves the approved ordinary JSON value and supplies fresh
trusted evidence under EN-01. It does not treat the historical implementation
PR as authority.

### 4.2 Route Selection And Current Inventory

**What this is**

Ordinary JSON selection is the source rule that decides which FastAPI routes
receive the ordinary byte limit.

**Contract / required behavior**

The current application builds ordinary JSON routes from FastAPI metadata:

- inspect each `APIRoute`;
- require final FastAPI request-body metadata: `route.body_field is not None`;
- ignore bodyless methods `GET`, `HEAD`, and `OPTIONS`;
- exclude approved special body-route keys;
- preserve FastAPI path regex matching for templated paths;
- match trailing-slash request paths through the middleware's normalized path
  behavior.

Gate A compared the current direct endpoint-body predicate
`route.dependant.body_params` with the final FastAPI body metadata predicate
`route.body_field is not None`. At the accepted baseline they produce the same
inventory: 82 non-bodyless FastAPI body routes before special-class exclusion
and 81 ordinary routes after excluding Platform Notice create. There is no
current route-membership change, but Gate B must harden production selection to
use `route.body_field` so future dependency-body routes cannot bypass the
ordinary class.

The freshly derived current accepted-baseline inventory is:

| Route class | Current count | Current source truth |
|---|---:|---|
| Ordinary JSON FastAPI routes | 81 | `APIRoute` entries with non-bodyless methods and final FastAPI body metadata, excluding special classes |
| Platform Notice special route | 1 | `POST /admin/platform-notices`, with FastAPI body parameter `payload` |
| Signed Stripe webhook special route | 1 | signed `POST /stripe/webhook`, raw-body route with no FastAPI body parameter |
| FastAPI routes with non-bodyless final body metadata before special exclusion | 82 | 81 ordinary plus Platform Notice create |
| Non-bodyless routes with no final FastAPI body metadata | 63 | excluded from ordinary body-route selection |
| Bodyless 410 tombstones among those no-body routes | 44 | excluded from ordinary body-route selection |

The retained body-bearing route inventory for request-limit classification is
therefore 83 route classes: 81 ordinary JSON classes, one Platform Notice
special class, and one signed Stripe raw-body special class.

The full application has 45 HTTP 410 tombstones. The additional tombstone is
the bodyless-method `GET /notifications` route, which is outside the
non-bodyless ordinary body-route selection inventory.

Current source inspection found no `UploadFile`, FastAPI `File`, FastAPI `Form`,
or multipart consumers outside excluded historical tests. Direct R2 object
bytes remain outside FastAPI request-body limiting because uploads use
provider-owned direct upload URLs.

**Why**

The count is a current Gate A fact, not a copied historical claim. Gate B tests
must derive this inventory from the real app and fail on material route drift.

### 4.3 Special-Class Precedence

**What this is**

Special classes are routes whose body limit is not the ordinary JSON class.

**Contract / required behavior**

Selection order is:

1. signed `POST /stripe/webhook` with a present `Stripe-Signature` header;
2. `POST /admin/platform-notices`;
3. retained ordinary JSON body routes;
4. no source-owned body limit for routes outside those classes.

Special classes stay distinct:

- Platform Notice create uses 160 KiB / 163,840 bytes and remains B2A1-owned.
- Signed Stripe webhook uses 64 KiB / 65,536 bytes, preserves exact raw bytes
  for signature verification, and remains B2A1/WS05-owned for its special
  provider lifecycle boundary.
- Missing-signature Stripe requests remain route-owned failures, not signed
  webhook body-limit proof.
- Bodyless tombstones remain bodyless even if a stale caller submits a body.
- B1/B2/B3-retired route surfaces do not create policy, legal, provider,
  payment, refund, payment-event, or generic lifecycle body-limit subclasses.

**Why**

A2C owns the general ordinary class only. Treating every request body as
ordinary would erase deliberate special boundaries and could turn retired
tombstones back into active body surfaces.

### 4.4 Actual Bytes And Content-Length

**What this is**

The middleware must decide acceptance from the bytes the application actually
receives, not from caller-supplied length metadata alone.

**Contract / required behavior**

For ordinary JSON limited requests:

- exact-limit bodies are accepted;
- limit-plus-one bodies are rejected;
- actual ASGI `http.request` body bytes are counted cumulatively;
- multi-message and chunked delivery that reaches ASGI is enforced by the same
  byte counter;
- accepted bytes are delivered downstream unchanged;
- one syntactically valid `Content-Length` above the selected limit may reject
  before the body is read;
- `Content-Length` at or below the limit is not proof that the body is safe;
- missing, malformed, duplicate, conflicting, or underdeclared
  `Content-Length` values cannot bypass actual-byte enforcement;
- empty zero-byte messages do not count against the limit;
- non-HTTP scopes pass through without body-limit behavior.

**Why**

`Content-Length` is advisory. If the backend trusted it for approval, a caller
could underdeclare a body and still force oversized payloads into parsing or
route work.

### 4.5 Downstream Protection

**What this is**

The body limit must protect the application before meaningful downstream work
happens.

**Contract / required behavior**

For over-limit ordinary JSON requests, source-owned rejection must occur before
the protected downstream route/dependency/body/business seam processes the
payload. Gate B evidence should use the lowest reliable layer:

- direct ASGI proof for byte counting and receive behavior;
- FastAPI/TestClient proof for actual app route selection and stable responses;
- fakes or dependency overrides at application-owned seams when proving that a
  representative downstream handler or dependency was not reached.

For accepted ordinary requests, tests must prove byte-for-byte downstream
delivery rather than only a successful status.

**Why**

A body limit that rejects after parsing, dependency work, provider calls, or
business mutation does not satisfy the protected-resource purpose of `API-M09`.

### 4.6 Content-Encoding And JSON Media Boundary

**What this is**

Body size, content encoding, and JSON media type are related but not identical
contracts.

**Contract / required behavior**

For A2C ordinary limited classes:

- absent `Content-Encoding` and identity-only encodings are accepted for size
  evaluation;
- non-identity `Content-Encoding` values, including comma-separated values with
  any non-identity token, are rejected before body processing;
- the application does not decompress request bodies;
- oversized request-body rejection remains independent from JSON parsing;
- missing `Content-Type` remains compatible under the WS02-05A media decision;
- explicit non-JSON `Content-Type` rejection and `API.UNSUPPORTED_MEDIA_TYPE`
  remain WS02-05A-owned HTTP/media behavior.

A2C evidence may check that ordinary size enforcement and WS02-05A media
behavior coexist, but it must not claim the whole media/OpenAPI/cache contract.

**Why**

Compressed request bodies make the size boundary ambiguous if the application
does not own decompression. Media-type behavior is a neighboring HTTP contract
and stays with WS02-05A.

### 4.7 Stable App-Owned Errors

**What this is**

Application-owned A2C failures must use safe public error behavior.

**Contract / required behavior**

Oversized ordinary JSON requests use:

- HTTP 413;
- stable `API.REQUEST_BODY_TOO_LARGE` code;
- safe public message and detail;
- correlation ID body/header behavior where applicable;
- compatible CORS and response-security headers where applicable;
- no submitted body, field value, provider data, token, credential, database
  URL, private header, internal diagnostic, traceback, or implementation detail
  leakage.

Unsupported non-identity content encoding uses the existing app-owned 415
`API.UNSUPPORTED_CONTENT_ENCODING` behavior for limited classes. Explicit
non-JSON media-type 415 behavior remains WS02-05A-owned.

**Why**

A2C must not create a body-limit control that leaks sensitive submitted content
or breaks the stable error/correlation foundation supplied by WS02-04A, WS02-03,
and EN-02.

### 4.8 Typed Configuration

**What this is**

The ordinary JSON limit is backend configuration, not a frontend or product
field maximum.

**Contract / required behavior**

Current source uses:

- setting name: `ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES`;
- `BackendSettings.ordinary_json_request_body_limit_bytes`;
- default constant:
  `DEFAULT_ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES = 64 * 1024`;
- positive integer parsing through the settings owner;
- independent Platform Notice and signed Stripe webhook settings.

Gate A found the runtime setting already exists and is used by app construction,
but tracked environment vocabulary is stale:

- `BACKEND_ENVIRONMENT_VARIABLES` does not list
  `ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES`.
- `backend/.env.example` does not document
  `ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES=65536`.

Gate B must correct that settings/configuration documentation gap and the
route-metadata selector described in section 4.2. The settings/config
correction must not change the approved value or middleware behavior.

**Why**

The setting is already functional, but the repository's declared environment
surface and example configuration should match the typed settings contract.

## 5. Implementation Scope

### Current Implementation Surfaces

The current A2C source contract is implemented through:

- `backend/observability/request_body_limits.py`
- `backend/main.py`
- `backend/settings.py`
- `backend/.env.example`
- `backend/observability/http_errors.py`
- current FastAPI route modules included by `backend/main.py`

### Correction Sets

Production behavior correction set:

- `backend/main.py` - harden ordinary route candidate detection to use final
  FastAPI body metadata, `route.body_field is not None`, instead of direct
  endpoint body parameters from `route.dependant.body_params`. The current
  accepted baseline route membership remains unchanged, but the source rule
  becomes dependency-body safe.

Settings/config correction set:

- `backend/settings.py` - add `ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES` to the
  declared backend environment variable vocabulary.
- `backend/.env.example` - document
  `ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES=65536`.

Governance/document correction set: none beyond this canonical plan. The
limits register already records A2C's 64 KiB ordinary JSON value and external
deferrals.

Frontend correction set: none.

Database, migration, provider, deployment, CI, and operational correction set:
none.

### Authorized Gate B Editable Set

Gate B may edit exactly these files:

1. `backend/main.py`
2. `backend/settings.py`
3. `backend/.env.example`
4. `backend/tests/support/requirements/ws02_04b2a2c.json`
5. `backend/tests/platform/request_body_limits/TESTING_RECORD.md`
6. `backend/tests/platform/request_body_limits/test_ordinary_json_route_inventory_contract.py`
7. `backend/tests/platform/request_body_limits/test_ordinary_json_request_body_limit_contract.py`
8. `backend/tests/platform/request_body_limits/test_request_body_limit_settings_contract.py`
9. `backend/tests/platform/request_body_limits/test_request_body_limit_error_contract.py`

If Gate B finds that the request-body-limit middleware, app construction beyond
the approved `backend/main.py` route-selector hardening, route modules,
governance register, frontend, database, migration, provider, deployment, or CI
behavior must change, it must return to Gate A instead of broadening the edit
set.

### Complete Expected Pass Change Set

The complete pass change set is expected to be exactly the Gate A plan plus the
Gate B editable files:

1. `docs/production-readiness/planning/passes/ws02/ws02-04b2a2c-ordinary-json-request-body-limit.md`
2. `backend/main.py`
3. `backend/settings.py`
4. `backend/.env.example`
5. `backend/tests/support/requirements/ws02_04b2a2c.json`
6. `backend/tests/platform/request_body_limits/TESTING_RECORD.md`
7. `backend/tests/platform/request_body_limits/test_ordinary_json_route_inventory_contract.py`
8. `backend/tests/platform/request_body_limits/test_ordinary_json_request_body_limit_contract.py`
9. `backend/tests/platform/request_body_limits/test_request_body_limit_settings_contract.py`
10. `backend/tests/platform/request_body_limits/test_request_body_limit_error_contract.py`

## 6. Testing And Evidence

### Trusted Test Scope

A2C uses the existing trusted platform scope:

```text
backend/tests/platform/request_body_limits/
```

This is the correct EN-01 owner because the behavior is global FastAPI
middleware and route metadata, not a single business domain workflow. A2C must
extend the existing current trusted request-body-limit domain instead of
creating a duplicate pass-specific root.

The existing `TESTING_RECORD.md` in that scope must be reconciled to cover both
B2A1 special classes and A2C ordinary JSON evidence without manually
maintaining exact pytest node IDs.

### Planned Evidence Modules

| Test module | Evidence responsibility |
|---|---|
| `test_ordinary_json_route_inventory_contract.py` | Derive the current route inventory from the real FastAPI app without merely reproducing production classifier logic; independently compare final FastAPI `route.body_field` metadata against ordinary selection; prove direct endpoint body parameters are covered; prove a synthetic dependency-body route is selected ordinary after the `backend/main.py` correction; prove Platform Notice create is special and not ordinary; prove signed Stripe webhook is the only approved raw-body special route; prove bodyless routes and tombstones remain excluded; prove no body-bearing `GET`, `HEAD`, or `OPTIONS` route is silently excluded; inspect production route/dependency source for manual raw-body consumers such as `Request.body()`, `Request.json()`, `Request.form()`, or `Request.stream()`; prove no current policy/payment/legal-specific body-limit class exists; prove no current `UploadFile`, FastAPI `File`, FastAPI `Form`, or multipart ownerless body class exists. |
| `test_ordinary_json_request_body_limit_contract.py` | Use direct ASGI and small synthetic routes to prove ordinary exact-limit success, limit-plus-one rejection, valid oversized `Content-Length` early rejection, missing/malformed/duplicate/underdeclared `Content-Length` actual-byte enforcement, multi-message delivery, downstream byte preservation, and protected downstream cutoff on rejection. |
| `test_request_body_limit_settings_contract.py` | Extend current settings evidence to prove ordinary default 65,536 bytes, custom positive integer acceptance, zero/negative/malformed rejection, environment registry entry, `.env.example` documentation, no frontend exposure, and separation from Platform Notice/Stripe settings. |
| `test_request_body_limit_error_contract.py` | Extend current safe-error evidence to prove ordinary oversized and non-identity content-encoding failures use safe stable public behavior without leaking submitted body, credentials, headers, provider-like data, database URLs, traceback, or internal diagnostics. |
| `TESTING_RECORD.md` | Explain the combined request-body-limit risk model, A2C scenario selection, evidence quality, covered-elsewhere WS02-05A media behavior, and R7 deferrals. |

### Proof-Layer Decisions

- Direct ASGI proof is required for byte counting because it proves the
  middleware behavior without depending on a particular application route.
- FastAPI route-table proof is required for ordinary route classification and
  negative space because A2C selects routes from real app metadata.
- Route-inventory proof must independently verify final FastAPI `body_field`
  metadata, direct endpoint body parameters, dependency-body selection,
  bodyless method exclusion, special-class exclusion, and manual raw-body
  consumers instead of only calling the production classifier.
- FastAPI/TestClient proof is required for app-owned stable errors and
  middleware integration.
- Static settings/config proof is required for typed configuration,
  `.env.example`, backend environment vocabulary, and no frontend exposure.
- PostgreSQL is not required for A2C because the pass must prove rejection
  happens before database work; representative downstream seams can be faked or
  observed at the application boundary.
- Live provider/network evidence is not required and must not be used.
- Playwright/browser evidence is not required.
- Migration-history proof is not required.
- Genuine concurrency proof is not required.
- Controlled time proof is not required.
- Historical and out-of-scope tests are not evidence.
- Gate B must preserve existing B2A1 evidence in the shared
  `platform/request_body_limits` scope and must not weaken, remove, or remap
  B2A1 special-class proof while adding A2C.

### Evidence Quality Rules

Gate B tests must prove the safeguards that matter:

- size-boundary tests use controlled byte payloads and exact byte counts;
- accepted-body tests prove byte-for-byte downstream delivery;
- rejected-body tests prove protected downstream processing did not occur;
- `Content-Length` tests prove actual bytes still govern acceptance;
- route-inventory tests derive from current FastAPI metadata rather than a
  hand-copied historical list;
- route-inventory tests prove the only current manual raw-body consumer is the
  approved signed Stripe webhook special class;
- static settings checks distinguish backend-private configuration from
  frontend-public configuration;
- tests do not use provider/network access, production credentials, or old
  application tests;
- media-type checks do not duplicate or overclaim WS02-05A.

### Required Validation

Gate B must run:

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/platform/request_body_limits
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/platform/settings backend/tests/platform/http_security backend/tests/platform/api_errors backend/tests/workflows/route_lifecycle_cleanup backend/tests/workflows/provider_payment_input_ownership backend/tests/workflows/policy_legal_request_ownership
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/checker backend/tests/workflows backend/tests/platform
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/checker
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/platform/request_body_limits
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python backend/tests/check_backend_tests.py --scope suite
```

Gate B must also run:

```bash
backend/.venv/bin/python -m py_compile backend/main.py backend/settings.py backend/tests/platform/request_body_limits/test_ordinary_json_route_inventory_contract.py backend/tests/platform/request_body_limits/test_ordinary_json_request_body_limit_contract.py backend/tests/platform/request_body_limits/test_request_body_limit_settings_contract.py backend/tests/platform/request_body_limits/test_request_body_limit_error_contract.py
git diff --check
```

Generated traceability must show `WS02-04B2A2C-R1` through
`WS02-04B2A2C-R6` mapped to current trusted pytest evidence and
`WS02-04B2A2C-R7` with zero pytest mappings and an explicit deferred reason.
Because A2C extends the shared request-body-limit scope, generated traceability
must also confirm existing B2A1 requirements R1 through R7 remain mapped and
B2A1 R8 remains zero-mapped/deferred.

## 7. Integration / Operational Expectations

A2C integrates with:

- `WS02-04B2A1`, which owns the portable middleware foundation and the Platform
  Notice and signed Stripe special request-body classes.
- `WS02-04B2A2A`, which owns field-level active request schema bounds.
- `WS02-04B2A2B1`, which retires obsolete mutation routes as bodyless
  tombstones and leaves downstream body-limit work a cleaner active surface.
- `WS02-04B2A2B2`, which owns provider/payment input boundaries and prevents
  generic payment/provider bodies from becoming ordinary A2C blockers.
- `WS02-04B2A2B3`, which owns policy/legal request ownership and keeps
  policy/legal write tombstones bodyless.
- `WS02-05A`, which owns JSON media-type behavior, OpenAPI representation,
  cache policy, method behavior, and tombstone representation.
- `WS02-04A`, `WS02-03`, and `EN-02`, which supply stable error, CORS,
  response-security, correlation, and safe public-error foundations.

Future route additions must preserve the metadata-derived classification rule:
retained FastAPI routes with final FastAPI body metadata become ordinary JSON
unless an approved special class and evidence explicitly says otherwise.

## 8. Not Part Of This Pass

A2C does not implement or close:

- Platform Notice or signed Stripe special-class numeric authority, owned by
  `WS02-04B2A1`;
- field-level request schema bounds, owned by `WS02-04B2A2A` and neighboring
  workflow owners;
- retired route lifecycle, provider/payment input ownership, or policy/legal
  request ownership, owned by B1/B2/B3;
- explicit non-JSON media-type policy, OpenAPI, cache, method handling, or
  tombstone representation, owned by `WS02-05A`;
- broad request/response ownership and response minimization, owned by
  `WS02-05B1` and `WS02-05B2`;
- form, multipart, file-upload, streaming, direct R2 object-byte, or storage
  provider limits;
- header, URL, request-line, edge, ingress, process-server, permanent-host, or
  staging precedence evidence;
- Stripe/provider dashboard settings, provider payload hard limits, delivery
  records, event subscriptions, replay/idempotency, refunds, disputes, or live
  provider evidence;
- runtime telemetry, metrics, dashboards, alerts, load evidence, rate limits,
  retries, timeouts, cancellation, worker concurrency, durable jobs, backups,
  recovery, or launch sign-off;
- frontend behavior, Playwright/browser evidence, database schema changes,
  migrations, or production data changes.

## 9. Related Controls And Remaining Evidence

| Control / Decision | What this pass establishes | What remains later |
|---|---|---|
| `API-M09` | Establishes source-owned ordinary JSON whole-request byte limiting for retained FastAPI JSON body routes and preserves special/bodyless boundaries. | Header, URL, request-line, form/multipart/file, streaming, provider, ingress, process-server, permanent-host, staging, runtime/load, and external precedence evidence remains outside A2C. |
| `GOV-006` / `FDN-04` | Preserves the accepted 64 KiB ordinary JSON value, documents its current basis, and requires fresh boundary evidence. | Future numeric changes and unrelated thresholds require their own approved basis, tests, and evidence. |
| `WS02-04B2A1` | Supplies shared middleware foundation and special request-body classes that A2C must not re-own. | B2A1 remains the owner for Platform Notice and signed Stripe special-class proof. |
| `WS02-05A` | Owns JSON media-type/OpenAPI/cache behavior that must coexist with A2C body-size enforcement. | Full HTTP/media/OpenAPI/cache and external HTTP-chain evidence remains outside A2C. |
| `WS02-05B1` / `WS02-05B2` | Receive broader request/response ownership and minimization boundaries after source-owned body limits are established. | Payload separation and response minimization remain their work. |
| Later provider, storage, telemetry, runtime, ingress, permanent-host, and staging owners | Receive provider, storage, telemetry, runtime, ingress, permanent-host, staging, and external precedence evidence. | Those owners must supply evidence before broader production-readiness control closure. |

### Supporting Relationships

- `EN-01` supplies requirement declarations, trusted test roots, checker, and
  generated traceability.
- `EN-02` supplies safe public error and observability primitives.
- `WS02-03` supplies CORS, host, response-security, and edge-boundary source
  behavior inherited by application-owned errors.
- `WS02-04A` supplies stable app-owned API error contracts.

## 10. Completion Criteria

A2C is complete when:

- the canonical A2C plan is reconciled to current authority and current route
  inventory;
- the ordinary JSON source limit remains 64 KiB / 65,536 bytes;
- `backend/main.py` selects ordinary routes with `route.body_field is not None`
  while preserving the current accepted-baseline route membership;
- `backend/settings.py` declares `ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES` in the
  backend environment vocabulary;
- `backend/.env.example` documents
  `ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES=65536`;
- `backend/tests/support/requirements/ws02_04b2a2c.json` declares R1 through R7
  with the exact metadata in this plan;
- `backend/tests/platform/request_body_limits/TESTING_RECORD.md` explains the
  combined B2A1/A2C request-body-limit risk model, A2C evidence, and R7
  deferrals;
- fresh trusted tests under `backend/tests/platform/request_body_limits/` prove
  R1 through R6 without relying on historical tests;
- R7 remains deferred with zero pytest mappings;
- existing B2A1 R1 through R7 request-body-limit mappings remain intact, and
  B2A1 R8 remains zero-mapped/deferred;
- focused request-body-limit tests pass;
- adjacent B2A1, B1, B2, B3, WS02-05A/API-error evidence remains compatible;
- the full current trusted backend regression passes;
- checker domain scope for `backend/tests/platform/request_body_limits` passes;
- checker suite scope passes;
- generated traceability is complete and truthful;
- compile/static validation for changed Python files passes;
- `git diff --check` passes;
- no frontend, database, migration, provider, deployment, CI, or unrelated
  production behavior change is introduced;
- no unresolved blocker remains.

Pass completion does not mean full `API-M09` or `GOV-006` closure. External
ingress, provider, runtime, staging, telemetry, header/URL, form/multipart,
file/object-byte, and broader request/response evidence remains with later
owners.
