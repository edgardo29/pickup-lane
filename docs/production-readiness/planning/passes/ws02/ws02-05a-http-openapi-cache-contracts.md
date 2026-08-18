# WS02-05A - HTTP, OpenAPI, Cache, And Compatibility Contracts

## At A Glance

| Field | Value |
|---|---|
| Pass | `WS02-05A` |
| Track | `WS02` |
| Type | API/platform HTTP contract recheck |
| Primary controls | `API-M13`, `API-M14`, `API-M16`, `API-M18`, `API-M19` |
| Authority basis | Current repository tree, final remediation plan, foundation decisions `FDN-03` and `FDN-04`, master blueprint `WS02-05`, accepted WS02-03/WS02-04/WS02-05B1/WS02-05B2 plans, limits register |
| Depends on | `WS02-03`, `WS02-04`, `FDN-03`, `FDN-04` |
| Trusted test scope | `backend/tests/platform/http_contracts/` |

## 1. Purpose

WS02-05A owns Pickup Lane's portable backend HTTP contract foundation. It makes
the current FastAPI API behavior deliberate and testable for media types,
unsupported methods, public error schema documentation, cache classification,
docs/OpenAPI exposure, tombstone representation, compatibility, and pagination
inventory truth.

This pass does not finish every API contract risk. Request ownership and
response minimization are owned by the accepted WS02-05B1 and WS02-05B2 passes.
Permanent edge, CDN, proxy, TLS, runtime, staging, query-plan, and public API
versioning evidence remain later or external proof. Open pagination numeric
values also remain unapproved until the evidence-based limit process in FDN-04
selects values for each affected workflow.

The immediate output of WS02-05A is a source-owned backend contract and fresh
trusted platform evidence that current repository behavior is explicit instead
of accidental.

## 2. Why This Matters

HTTP contract drift creates production risk even when individual route handlers
look correct. Examples include:

- accepting non-JSON payloads on JSON routes and letting route code see
  ambiguous input;
- returning framework-shaped 405 responses that bypass the stable public error
  envelope;
- documenting OpenAPI responses that do not match runtime public error shapes;
- allowing authenticated, admin, or private JSON responses to become cacheable;
- exposing local-only docs in production by configuration accident;
- hiding compatibility tombstones from OpenAPI before callers have migrated;
- recording stale pagination handoffs that point unresolved work to a pass that
  no longer owns it.

WS02-05A reduces those risks by centralizing the current contract and making
the remaining gaps explicit. It is especially important because later frontend,
identity, database, storage, and release work depends on stable API behavior.

## 3. Requirements

| ID | Requirement | What it means | Why it matters |
|---|---|---|---|
| `WS02-05A-R1` | JSON request-body media behavior is explicit and compatibility-preserving. | Source-owned JSON request-body routes accept `application/json` and compatible `+json` media types, reject explicit non-JSON media types with the stable 415 contract, preserve missing `Content-Type` compatibility, and leave signed raw-body webhook behavior outside the ordinary JSON contract. | Prevents ambiguous input handling without breaking current supported callers or Stripe webhook raw-body verification. |
| `WS02-05A-R2` | Unsupported methods remain framework-owned but stable. | FastAPI/Starlette continues to decide method-not-allowed routing, while Pickup Lane wraps the response in the stable public error envelope and preserves the `Allow` header. | Avoids method aliasing or route redesign while keeping public API failures predictable. |
| `WS02-05A-R3` | OpenAPI documents stable public error contracts truthfully. | The generated schema exposes reusable public error and validation-error response schemas and attaches route-derived error responses where current source supports them. | Reviewers and later callers need docs that match runtime behavior without leaking internal exceptions, provider diagnostics, SQL, or submitted sensitive values. |
| `WS02-05A-R4` | Source-owned API cache classification is safe. | Private, authenticated, and admin JSON API responses are marked `private, no-store`; public API JSON, docs/OpenAPI, health/readiness, and public errors remain `no-store`; stricter route-specific headers are preserved. | Prevents private API data from being stored by shared or browser caches while avoiding unsupported CDN/public-cache claims. |
| `WS02-05A-R5` | Docs/OpenAPI exposure and compatibility follow `FDN-03`. | Local and test environments may expose docs/OpenAPI; production-like environments disable docs and raw schema by default; docs visibility never substitutes for authorization; compatibility changes require deliberate sequencing. | Prevents accidental production documentation exposure and preserves rolling frontend/backend compatibility. |
| `WS02-05A-R6` | Compatibility tombstones remain visible and bodyless while registered. | Current 410 compatibility tombstone routes stay in OpenAPI, are deprecated, document 410, and do not advertise removed request bodies. | Keeps compatibility signals visible without reviving removed request contracts. |
| `WS02-05A-R7` | Pagination inventory is complete and ownership-truthful. | Every current live collection route is either registered with an approved current pagination contract or registered as an unresolved handoff with truthful current accountable ownership. No unresolved route is silently dropped, no unapproved numeric value is invented, and no stale B1/B2 owner remains. | Prevents false closure of `API-M14`, `API-M09`, and `DB-013` pagination risk while preserving evidence for later owner decisions. |
| `WS02-05A-R8` | Repository-only evidence boundaries are explicit. | Local source and trusted tests prove the source-owned HTTP contracts above; edge/CDN/proxy/TLS/runtime/query-plan/provider/staging/public-versioning evidence remains later or external. | Prevents local tests from overclaiming full production HTTP-chain closure. |

## 4. Technical Design / Contracts

### 4.1 JSON Media-Type Contract

**What this is**

Pickup Lane has ordinary JSON request-body routes and special raw-body routes.
The ordinary JSON contract is enforced by source-owned request-body middleware
and route classification.

**Contract / required behavior**

- `application/json` is accepted.
- Compatible JSON structured media types ending in `+json` are accepted.
- Explicit non-JSON media types are rejected before route code runs.
- Rejected ordinary JSON media types return the stable 415 public error
  contract.
- Missing `Content-Type` remains accepted for compatibility because current
  authority has not proven all supported callers can tolerate a blanket
  rejection.
- Malformed JSON with an accepted JSON media type remains a validation failure,
  not a media-type failure.
- Request-body byte limits and content-encoding rejection remain separate
  contracts owned by the existing request-body limit foundation.
- Signed Stripe webhook handling remains raw-body owned and is not reclassified
  as ordinary JSON.
- Bodyless routes and tombstones remain outside ordinary JSON parsing.

**Why**

This protects route code from explicit wrong-media input while preserving known
caller compatibility and provider raw-body verification.

### 4.2 Unsupported Method Contract

**What this is**

Unsupported methods are routing failures, not application-specific business
rules.

**Contract / required behavior**

- FastAPI/Starlette remains the method owner.
- Pickup Lane's exception handling normalizes the response into the stable
  public error envelope.
- The framework `Allow` header is preserved when present.
- WS02-05A does not add method aliases for obsolete or hypothetical clients.
- OpenAPI documents the method-not-allowed contract for applicable operations.

**Why**

This gives callers predictable failures without creating new route behavior.

### 4.3 OpenAPI Error Representation

**What this is**

OpenAPI must describe public error shapes that current runtime code can emit.

**Contract / required behavior**

The generated schema includes reusable schemas for:

- the stable public error envelope;
- the stable validation-error envelope.

Route-derived error responses are documented where current source supports
them, including:

- 401 and 403 for private/authenticated/admin routes;
- 404 for resource routes with path parameters;
- 409 for mutation routes with conflict risk;
- 410 for tombstones;
- 413, 415, and 422 for ordinary JSON request-body routes;
- 429 only for accepted chat rate-limit route families;
- 503 for database-backed or readiness routes;
- 405 for framework-owned method-not-allowed behavior except where an accepted
  provider raw-body route requires different treatment.

The schema must not expose internal exceptions, SQL, provider diagnostics,
configuration values, submitted sensitive values, raw request content, or
provider secrets.

**Why**

OpenAPI is part of API compatibility and review. It must help callers and
reviewers understand failures without becoming a sensitive-data leak or a false
promise.

### 4.4 Cache Classification

**What this is**

The API applies source-owned cache headers by response class.

**Contract / required behavior**

- Authenticated, admin, and private JSON API responses use
  `Cache-Control: private, no-store`.
- Public API JSON, public errors, health/readiness, docs, and OpenAPI use
  `Cache-Control: no-store`.
- Existing stricter route-specific headers are preserved.
- Redirect, static, and file responses remain outside this generic JSON API
  cache middleware.
- WS02-05A does not introduce public `max-age`, validators, CDN cache policy,
  stale revalidation, static asset cache behavior, or shared-cache proof.

**Why**

The source-owned contract prevents accidental caching of private API data while
avoiding claims that require edge/CDN/provider evidence.

### 4.5 Docs, OpenAPI, And Compatibility

**What this is**

`FDN-03` controls docs/OpenAPI exposure and compatibility posture.

**Contract / required behavior**

- Local development and controlled test environments may expose interactive
  docs and the raw OpenAPI schema.
- Production-like environments disable docs, Redoc, and raw OpenAPI by default.
- Enabling docs in production-like mode must fail fast or remain
  access-restricted by an approved future policy.
- Hiding docs never substitutes for route authorization.
- Pickup Lane remains an internal web-application API at this stage.
- Rolling frontend/backend compatibility must be preserved for active callers.
- Breaking request or response changes require caller audit, compatibility
  planning, and coordinated deployment.

**Why**

This makes docs exposure deliberate and keeps internal compatibility concerns
from turning into accidental public API versioning promises.

### 4.6 Tombstone Representation

**What this is**

Compatibility tombstones are route-level signals that an old path or method is
retired but still intentionally present.

**Contract / required behavior**

- Current 410 tombstone routes remain registered while their compatibility
  window exists.
- They remain visible in OpenAPI.
- They are marked deprecated.
- They document the 410 response.
- They do not advertise removed request bodies.
- WS02-05A does not invent removal dates and does not remove tombstone routes.

**Why**

Tombstones help rolling compatibility and caller cleanup without reviving
obsolete input contracts.

### 4.7 Pagination Inventory And Ownership

**What this is**

`backend/observability/pagination_contracts.py` is the source inventory for
current collection-route pagination status. It has two classes of entries:

- `PAGINATION_CONTRACTS`: current live routes with an accepted source-owned
  pagination contract or boundary.
- `PAGINATION_HANDOFFS`: current live routes that remain open because no
  approved explicit pagination limit or full pagination contract exists.

**Current repository truth**

The current route inventory has:

- 34 live contract entries;
- 43 live handoff entries;
- no overlap between contract and handoff keys;
- no missing live routes among the recorded contract entries;
- no missing live routes among the recorded handoff entries.

The handoff entries are therefore still-live unresolved routes, not stale dead
routes.

The defect is ownership metadata: each current handoff still uses
`recommended_owner="WS02-05B"`. Accepted `WS02-05B1` owns request ownership and
mass-assignment cleanup. Accepted `WS02-05B2` owns response minimization and
audience-specific response contracts. Neither accepted B1 nor B2 plan accepts
the remaining pagination-limit obligation.

Higher authority still assigns the obligation. The master blueprint says
parent `WS02-05` owns HTTP contracts, schemas, deliberate pagination,
docs/OpenAPI, cache, compatibility, and end-to-end chain responsibilities. The
limits register says source-owned route/schema/service enforcement belongs to
the API owner, while database/runtime behavior belongs to later database and
runtime owners. All such roles are held by the Project owner on an interim
basis until reassigned.

**Contract / required behavior**

- Every current live collection route must be accounted for in either
  `PAGINATION_CONTRACTS` or `PAGINATION_HANDOFFS`.
- A route with an accepted source-owned pagination contract remains in
  `PAGINATION_CONTRACTS`.
- A live route with no approved explicit value or complete pagination contract
  remains in `PAGINATION_HANDOFFS`.
- Handoff metadata must point only to an authority-backed current owner.
- Handoff metadata must not point unresolved pagination work to completed
  child passes that did not accept it.
- Numeric pagination limits must not be selected or inferred by WS02-05A unless
  there is workflow-specific evidence and approval under FDN-04.
- Database concurrency, stale cursor behavior, query plans, runtime/load
  behavior, bulk/export behavior, provider/ingress limits, and storage file
  policy remain later-owner evidence.

**Gate B source metadata correction**

`backend/observability/pagination_contracts.py` must update the
`PAGINATION_HANDOFFS` `recommended_owner` values from:

```python
recommended_owner="WS02-05B"
```

to the authority-backed current role:

```python
recommended_owner="API owner"
```

This is a metadata correction. It does not alter request handling, route
behavior, query limits, service limits, pagination numeric values, database
queries, frontend behavior, or runtime behavior. It stops the repository from
claiming that completed B1/B2 work owns unresolved pagination values.

**Why**

The inventory is valuable only if it is complete and honest. A stale future or
completed-pass owner can make unresolved pagination risk look closed when it is
not.

## 5. Implementation Scope

### 5.1 Production Source

WS02-05A Gate B may modify only this production/source file:

```text
backend/observability/pagination_contracts.py
```

The only planned production/source correction is the metadata-only
`recommended_owner` change described in section 4.7.

No production behavior change is authorized for pagination limits, route
handlers, service queries, database indexes, frontend callers, provider
integrations, deployment configuration, middleware ordering, docs exposure
settings, or cache policy beyond what the current source already implements.

### 5.2 Requirement Declarations

Gate B must create:

```text
backend/tests/support/requirements/ws02_05a.json
```

The declaration file must use stable IDs `WS02-05A-R1` through `WS02-05A-R8`.
It stores machine-readable identity, state, source controls, and scope only.
It must not duplicate the full pass plan, scenario inventory, or exact pytest
node IDs.

### 5.3 Trusted Evidence Scope

Gate B must create a real trusted platform scope:

```text
backend/tests/platform/http_contracts/
```

This directory is not a placeholder. It must contain the pass testing record
and executable trusted evidence for the current source-owned HTTP contracts.

### 5.4 Configuration, Database, Provider, Frontend, And Deployment

No configuration, database, migration, provider, frontend, deployment, CI, or
GitHub Actions change is authorized by WS02-05A Gate B.

## 6. Testing And Evidence

### 6.1 Requirement Declarations

| ID | Owning pass | State | Scope | Source controls |
|---|---|---|---|---|
| `WS02-05A-R1` | `WS02-05A` | `required` | `platform/http_contracts` | `API-M13`, `API-M09`, `WS02-05A`, `WS02-04B2A1`, `WS02-04B2A2C`, `WS02-04A` |
| `WS02-05A-R2` | `WS02-05A` | `required` | `platform/http_contracts` | `API-M13`, `API-M12`, `WS02-05A`, `WS02-04A` |
| `WS02-05A-R3` | `WS02-05A` | `required` | `platform/http_contracts` | `API-M18`, `API-M12`, `WS02-05A`, `WS02-04A` |
| `WS02-05A-R4` | `WS02-05A` | `required` | `platform/http_contracts` | `API-M16`, `API-M08`, `FDN-02`, `WS02-05A`, `WS02-03` |
| `WS02-05A-R5` | `WS02-05A` | `required` | `platform/http_contracts` | `API-M18`, `FDN-03`, `WS02-05A`, `WS02-01`, `WS02-03` |
| `WS02-05A-R6` | `WS02-05A` | `required` | `platform/http_contracts` | `API-M13`, `API-M18`, `WS02-05A`, `WS02-04B2A2B1` |
| `WS02-05A-R7` | `WS02-05A` | `required` | `platform/http_contracts` | `API-M14`, `API-M09`, `DB-013`, `GOV-006`, `FDN-04`, `WS02-05A`, `WS02-04B1` |
| `WS02-05A-R8` | `WS02-05A` | `deferred` | `governance` | `API-M13`, `API-M14`, `API-M16`, `API-M18`, `API-M19`, `GOV-006`, `FDN-03`, `FDN-04`, `WS02-05A`, `WS02-03`, `WS02-04`, `WS02-05B1`, `WS02-05B2`, `WS03`, `WS04`, `WS07`, `WS08`, `WS09`, `WS10` |

`WS02-05A-R8` reason:

```text
Permanent edge, CDN, proxy, TLS/HSTS, direct-origin, shared-cache, docs access,
process-server, staging/runtime, public-versioning, external-provider,
database query-plan/runtime, stale-cursor concurrency, bulk/export, broader
HTTP-chain, telemetry/dashboard/alert, and unapproved numeric pagination-value
evidence remain later or external responsibilities and cannot be closed by
local WS02-05A source tests.
```

### 6.2 Testing Record

Gate B must create:

```text
backend/tests/platform/http_contracts/TESTING_RECORD.md
```

The testing record must follow
`docs/production-readiness/planning/templates/TESTING-RECORD-TEMPLATE.md` and explain:

- scope and non-scope;
- requirement meanings;
- risk model;
- selected evidence;
- evidence quality decisions;
- repository-only proof boundaries;
- why checker `PASS` is structural compliance only.

### 6.3 Focused Trusted Tests

Gate B must create the following focused trusted test files:

```text
backend/tests/platform/http_contracts/test_json_media_type_contract.py
backend/tests/platform/http_contracts/test_method_openapi_error_contract.py
backend/tests/platform/http_contracts/test_cache_docs_tombstone_contract.py
backend/tests/platform/http_contracts/test_pagination_inventory_contract.py
```

Expected proof groups:

- JSON media tests prove accepted JSON and `+json`, explicit non-JSON 415,
  missing `Content-Type` compatibility, Stripe raw-body exclusion, and
  separation from size/content-encoding behavior where applicable.
- Method/OpenAPI/error tests prove stable 405 wrapping with `Allow`, reusable
  public error schemas, route-derived error documentation, and no sensitive
  schema content.
- Cache/docs/tombstone tests prove response-class cache headers, production-like
  docs disablement, local/test docs availability, tombstone visibility,
  deprecated marking, 410 documentation, and absence of removed request bodies.
- Pagination inventory tests prove contract/handoff completeness, current-live
  route agreement, no overlap, no missing route from both inventories, all 34
  approved contract entries remain live, all 43 handoff entries remain live,
  all unresolved handoff owners are `API owner`, no stale `WS02-05B` owner
  remains, and no test requires an unapproved numeric value.

### 6.4 Proof-Layer Decisions

| Area | Proof layer | Decision |
|---|---|---|
| JSON media behavior | FastAPI/TestClient source-owned API tests | Required because request parsing and middleware routing are HTTP/application behavior. |
| 405 behavior | FastAPI/TestClient source-owned API tests | Required because framework routing and exception wrapping must be observed together. |
| OpenAPI schema | Static generated schema inspection from the app | Required because the contract is the generated schema. |
| Cache headers | FastAPI/TestClient source-owned API tests | Required because middleware/header behavior is response behavior. |
| Docs exposure | Settings/app configuration inspection and API request checks | Required for local/test and production-like policy. |
| Tombstones | Generated OpenAPI and API behavior checks | Required to prove compatibility route representation. |
| Pagination inventory | Static app route inventory plus source metadata checks | Required to prove current truth without inventing values. |
| PostgreSQL | Not required for focused WS02-05A evidence | WS02-05A proves source-owned HTTP metadata/contracts; DB query plans and concurrency remain later. |
| Provider/network | Not required | No provider runtime behavior is closed by this pass. |
| Frontend/Playwright | Not required | No frontend behavior changes are authorized. |
| Controlled time | Not required | No time-boundary behavior is owned by this pass. |
| Concurrency/idempotency | Not required for focused tests | Pagination stale-cursor and DB concurrency evidence remains later. |

### 6.5 Gate B Validation Design

Gate B must validate the final state with:

1. Focused WS02-05A platform tests:

```bash
APP_ENV=test DATABASE_URL='[dedicated test database URL]' backend/.venv/bin/python -m pytest -q backend/tests/platform/http_contracts
```

2. Adjacent platform regressions for accepted HTTP/cache/error/limits behavior:

```bash
APP_ENV=test DATABASE_URL='[dedicated test database URL]' backend/.venv/bin/python -m pytest -q backend/tests/platform/http_security backend/tests/platform/api_errors backend/tests/platform/request_body_limits
```

3. Full current trusted backend regression across executable trusted roots that
   exist at this baseline:

```bash
APP_ENV=test DATABASE_URL='[dedicated test database URL]' backend/.venv/bin/python -m pytest -q backend/tests/checker backend/tests/workflows backend/tests/platform
```

4. Checker/foundation regression:

```bash
APP_ENV=test DATABASE_URL='[dedicated test database URL]' backend/.venv/bin/python -m pytest -q backend/tests/checker
```

5. Domain checker for the new trusted scope:

```bash
DATABASE_URL='[dedicated test database URL]' backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/platform/http_contracts
```

6. Domain checkers for adjacent trusted platform scopes:

```bash
DATABASE_URL='[dedicated test database URL]' backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/platform/http_security
DATABASE_URL='[dedicated test database URL]' backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/platform/api_errors
DATABASE_URL='[dedicated test database URL]' backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/platform/request_body_limits
```

7. Suite checker:

```bash
DATABASE_URL='[dedicated test database URL]' backend/.venv/bin/python backend/tests/check_backend_tests.py --scope suite
```

8. Generated traceability review confirming:

- `R1` through `R7` have mapped trusted pytest evidence;
- `R8` is deferred with zero mapped pytest evidence and an accurate reason.

9. Python syntax/compile validation for changed Python files.

10. Diff hygiene:

```bash
git diff --check
```

The full trusted backend regression is required because WS02-05A touches
cross-cutting HTTP metadata and route classification. A focused pass could pass
while another trusted platform or workflow scope observes a changed route,
middleware, error, cache, or docs/OpenAPI behavior.

## 7. Integration And Dependencies

WS02-05A depends on:

- `WS02-03` for app/edge header ownership boundaries and cache/security-header
  context;
- `WS02-04A` for stable public error envelope behavior;
- `WS02-04B1` and `WS02-04B2A2C` for accepted request-body special-class and
  ordinary JSON limit behavior;
- `WS02-04C3A` and `WS02-04C3B` for chat and non-chat rate-limit ownership;
- `WS02-05B1` for request ownership and mass-assignment cleanup;
- `WS02-05B2` for response minimization and audience-specific response
  contracts;
- `FDN-03` for docs/OpenAPI exposure and compatibility;
- `FDN-04` for evidence-based limit selection.

WS02-05A establishes a downstream source-owned foundation for:

- later frontend/API compatibility work;
- later identity and authorization passes that rely on stable public error and
  cache behavior;
- later database/query-plan pagination evidence;
- later runtime/edge HTTP-chain verification;
- later public API versioning or deprecation policy if Pickup Lane gains
  independent external clients.

## 8. Boundaries And Non-Goals

WS02-05A does not:

- select new pagination numeric values;
- implement query-plan, stale-cursor, or concurrent pagination proof;
- implement bulk/export limits;
- change request ownership or response minimization beyond accepted B1/B2 work;
- change frontend callers;
- introduce public API versioning;
- implement CDN/shared-cache/public max-age behavior;
- prove permanent TLS, HSTS, proxy, process-server, direct-origin, or edge
  behavior;
- prove provider runtime behavior;
- modify deployment, CI, GitHub Actions, migrations, database schema, or
  provider configuration;
- run or revive `backend/tests/legacy/`;
- create empty future trusted roots.

## 9. Controls And Remaining Evidence

| Control | WS02-05A outcome | Remaining evidence |
|---|---|---|
| `API-M13` | Advances for JSON media behavior, unsupported method stability, 415/405 contracts, tombstones, and documented error responses. | Full API media/idempotency/versioning review remains broader than this pass. |
| `API-M14` | Advances for pagination inventory truth and ownership correction; relies on accepted B1/B2 for request/response ownership and minimization. | Open numeric pagination values, DB stale-cursor/concurrency behavior, query plans, serialization completeness, and broader request/response compatibility remain later. |
| `API-M16` | Advances for source-owned API response cache classification. | CDN/shared-cache/static asset/permanent edge evidence remains later. |
| `API-M18` | Advances for docs/OpenAPI exposure policy, generated error schema representation, endpoint inventory support, tombstone visibility, and compatibility notes. | Public API versioning, long-term deprecation policy, production docs access if desired, and CI OpenAPI publication remain later. |
| `API-M19` | Records the repository/source boundary and does not claim full HTTP-chain closure. | Permanent edge, proxy, TLS/HSTS, direct-origin, staging/runtime, process-server, and deployment-chain evidence remains later. |

## 10. Completion Criteria

Gate A is complete when:

- the stale `WS02-05B` pagination handoff blocker is reclassified against
  higher authority;
- the canonical plan distinguishes approved pagination contracts from still-live
  unresolved handoffs;
- FDN-04 numeric-value limits remain unapproved unless separately approved by
  evidence;
- the exact source metadata correction is frozen;
- stable requirements and source controls are defined;
- proof layers and evidence boundaries are explicit;
- the Gate B editable set is exact;
- the complete expected pass change set is exact;
- feasibility checks and `git diff --check` pass.

Gate B may begin only after human approval of this corrected Gate A plan.

## Gate B Editable Set

Gate B may edit exactly these 7 files:

1. `backend/observability/pagination_contracts.py`
2. `backend/tests/support/requirements/ws02_05a.json`
3. `backend/tests/platform/http_contracts/TESTING_RECORD.md`
4. `backend/tests/platform/http_contracts/test_json_media_type_contract.py`
5. `backend/tests/platform/http_contracts/test_method_openapi_error_contract.py`
6. `backend/tests/platform/http_contracts/test_cache_docs_tombstone_contract.py`
7. `backend/tests/platform/http_contracts/test_pagination_inventory_contract.py`

## Complete Expected Pass Change Set

The complete WS02-05A recheck change set is expected to be exactly these 8
files:

1. `docs/production-readiness/planning/passes/ws02/ws02-05a-http-openapi-cache-contracts.md`
2. `backend/observability/pagination_contracts.py`
3. `backend/tests/support/requirements/ws02_05a.json`
4. `backend/tests/platform/http_contracts/TESTING_RECORD.md`
5. `backend/tests/platform/http_contracts/test_json_media_type_contract.py`
6. `backend/tests/platform/http_contracts/test_method_openapi_error_contract.py`
7. `backend/tests/platform/http_contracts/test_cache_docs_tombstone_contract.py`
8. `backend/tests/platform/http_contracts/test_pagination_inventory_contract.py`
