# WS02-04B2A2B3 - Policy/Legal Request Ownership

## At A Glance

| Field | Value |
|---|---|
| Pass | `WS02-04B2A2B3` |
| Track | `WS02` |
| Type | API source-owned request-ownership recheck |
| Primary controls | `API-M09` |
| Authority basis | Current accepted repository tree; `WS02-04` source-owned closeout; master production-readiness blueprint `WS02-04`; final remediation plan `API-M09`; accepted adjacent pass boundaries for `WS02-04B2A2B1`, `WS02-04B2A2B2`, `WS02-04B2A2C`, `WS02-05A`, `WS02-05B1`, and `WS02-05B2` |
| Depends on | `EN-01`; `WS02-04B2A2B1` |
| Trusted test scope | `backend/tests/workflows/policy_legal_request_ownership` |

## 1. Purpose

WS02-04B2A2B3 makes the policy/legal request boundary explicit and testable.
The pass requires generic policy document authoring and generic policy
acceptance mutation routes to stay retired as bodyless compatibility
tombstones, while preserving legitimate read behavior and internal setup paths.

In plain English: clients and generic admin request bodies must not be able to
author legal text, submit arbitrary legal-content URLs, fabricate policy
acceptance evidence, or rewrite acceptance metadata through broad policy/legal
CRUD routes. Policy/legal display can still exist, policy records can still be
read where authorized, and controlled internal setup can still seed records for
local development and tests.

This pass does not make legal language production-final, create a new policy
editor, create a product acceptance workflow, close privacy/retention/legal
compliance, or activate ordinary JSON request-body byte limits. Those are
separate owners or later evidence boundaries.

## 2. Why This Matters

Policy/legal request bodies carry unusually sensitive authority. If generic
write routes remain active, a caller could try to:

- publish arbitrary terms, privacy, cancellation, or refund text through a broad
  request body;
- attach an unreviewed or external `content_url` as if it were approved legal
  content;
- fabricate acceptance records for another user;
- rewrite acceptance time, policy identity, IP metadata, or user-agent metadata;
- force broad body-limit work to special-case unbounded policy text instead of
  retiring the unsupported write surface.

B3 keeps those risks out of public/admin request bodies. It also avoids the
opposite mistake: preserved reads, internal setup services, and source-managed
frontend legal presentation are not evidence of a still-active generic write
API.

## 3. Requirements

| ID | Requirement | What it means | Why it matters |
|---|---|---|---|
| `WS02-04B2A2B3-R1` | Generic policy document mutations are retired as bodyless tombstones. | `POST /policy-documents` and `PATCH /policy-documents/{policy_document_id}` must remain registered only as authenticated/admin-gated 410 mutation tombstones with no request body model, no route-owned JSON parsing, and no policy-document row mutation. | Prevents broad request bodies from authoring legal content, arbitrary content URLs, or policy lifecycle fields. |
| `WS02-04B2A2B3-R2` | Generic policy acceptance mutations are retired as bodyless tombstones. | `POST /policy-acceptances` and `PATCH /policy-acceptances/{policy_acceptance_id}` must remain registered only as authenticated/admin-gated 410 mutation tombstones with no request body model, no route-owned JSON parsing, and no policy-acceptance row mutation. | Prevents callers from fabricating or rewriting acceptance evidence and request metadata. |
| `WS02-04B2A2B3-R3` | Legitimate reads and controlled internal setup remain available. | Public policy-document reads, admin policy-acceptance reads, retained models, retained schemas, and retained service/setup primitives may continue where they are not exposed as generic HTTP write contracts. | Prevents B3 from breaking current display, admin evidence review, development setup, or future server-owned workflows. |
| `WS02-04B2A2B3-R4` | Current callers and scripts do not bypass the retired route boundary. | Current frontend behavior remains compatible, no current frontend caller uses generic policy/legal write routes, and future frontend code may consume retained policy-document reads without violating B3. Current seed/bootstrap scripts touching policy documents or acceptances must use internal setup and must not advertise retired write-route request bodies as active workflows. | Prevents an obsolete caller, helper, or script from reintroducing the unsafe write contract outside route files while preserving legitimate read integration. |
| `WS02-04B2A2B3-R5` | B3 leaves no policy/legal blocker for ordinary JSON body-limit ownership. | No retained public/admin policy/legal write route may require a special large policy-text body class, arbitrary URL body class, or fabricated acceptance body class. Bodyless tombstones remain outside ordinary JSON request-body ownership. | Keeps B3 aligned with `WS02-04B2A2C`, which owns ordinary JSON byte-limit activation instead of policy/legal product semantics. |
| `WS02-04B2A2B3-R6` | Later-owner and external-evidence boundaries remain explicit. | B3 must not claim closure for booking-policy acceptance lifecycle, HTTP/OpenAPI/cache/tombstone representation, broader request ownership, response minimization, legal-compliance review, privacy/retention, final acceptance product workflows, provider/runtime evidence, or external ingress limits. | Prevents a narrow request-ownership pass from becoming a false legal, privacy, HTTP, deployment, or product-workflow signoff. |

### Requirement Declaration Metadata

Gate B must create `backend/tests/support/requirements/ws02_04b2a2b3.json`
with exactly these declaration states and scopes:

```json
{
  "schema_version": 1,
  "requirements": [
    {
      "id": "WS02-04B2A2B3-R1",
      "owning_pass": "WS02-04B2A2B3",
      "source_controls": ["API-M09", "WS02-04B2A2B3"],
      "state": "required",
      "scope": "workflows/policy_legal_request_ownership"
    },
    {
      "id": "WS02-04B2A2B3-R2",
      "owning_pass": "WS02-04B2A2B3",
      "source_controls": ["API-M09", "WS02-04B2A2B3"],
      "state": "required",
      "scope": "workflows/policy_legal_request_ownership"
    },
    {
      "id": "WS02-04B2A2B3-R3",
      "owning_pass": "WS02-04B2A2B3",
      "source_controls": ["API-M09", "API-M14", "WS02-04B2A2B3", "WS02-05B2"],
      "state": "required",
      "scope": "workflows/policy_legal_request_ownership"
    },
    {
      "id": "WS02-04B2A2B3-R4",
      "owning_pass": "WS02-04B2A2B3",
      "source_controls": ["API-M09", "WS02-04B2A2B3"],
      "state": "required",
      "scope": "workflows/policy_legal_request_ownership"
    },
    {
      "id": "WS02-04B2A2B3-R5",
      "owning_pass": "WS02-04B2A2B3",
      "source_controls": ["API-M09", "GOV-006", "WS02-04B2A1", "WS02-04B2A2B3", "WS02-04B2A2C"],
      "state": "required",
      "scope": "workflows/policy_legal_request_ownership"
    },
    {
      "id": "WS02-04B2A2B3-R6",
      "owning_pass": "WS02-04B2A2B3",
      "source_controls": [
        "API-M09",
        "API-M13",
        "API-M14",
        "API-M18",
        "GOV-006",
        "WS02-04B2A2B1",
        "WS02-04B2A2C",
        "WS02-05A",
        "WS02-05B1",
        "WS02-05B2",
        "WS03",
        "WS10"
      ],
      "state": "deferred",
      "scope": "governance",
      "reason": "Booking-policy acceptance lifecycle, ordinary JSON byte limits, HTTP/media/OpenAPI/cache/tombstone representation, broad request ownership, response minimization, identity/account authority, final legal/privacy/retention policy, product acceptance workflows, external ingress limits, and provider/runtime evidence remain with their owners and cannot be closed by local B3 request-ownership evidence."
    }
  ]
}
```

`R1` through `R5` require trusted executable evidence. `R6` is intentionally
deferred/governance and must have zero pytest mappings.

## 4. Technical Design / Contracts

### 4.1 Generic Policy Document Mutation Boundary

**What this is**

The policy document table and service can still support controlled internal
setup, but generic HTTP callers must not author or update policy/legal content
through broad policy-document mutation routes.

**Contract / required behavior**

- `POST /policy-documents` remains registered as a 410 compatibility
  tombstone.
- `PATCH /policy-documents/{policy_document_id}` remains registered as a 410
  compatibility tombstone.
- Both routes require the current active admin dependency before their
  tombstone response.
- Neither route declares a request body model or a request body field.
- Submitted JSON or malformed JSON must not activate route-owned policy
  document request validation.
- Neither route depends on `get_db` or calls policy-document create/update
  service functions.
- Policy-document list/detail reads remain available for public active,
  non-retired, effective documents through the current read service.

**Why**

Legal content must not become a generic client/admin payload. If future product
work needs a policy authoring workflow, it must be separately approved and
source-owned rather than revived through these retired routes.

### 4.2 Generic Policy Acceptance Mutation Boundary

**What this is**

Policy acceptance evidence can be stored and read, but generic request bodies
must not be treated as authority for who accepted which policy, when, or with
what request metadata.

**Contract / required behavior**

- `POST /policy-acceptances` remains registered as a 410 compatibility
  tombstone.
- `PATCH /policy-acceptances/{policy_acceptance_id}` remains registered as a
  410 compatibility tombstone.
- Both routes require the current active admin dependency before their
  tombstone response.
- Neither route declares a request body model or a request body field.
- Submitted JSON or malformed JSON must not activate route-owned policy
  acceptance request validation.
- Neither route depends on `get_db` or calls policy-acceptance create/update
  service functions.
- Policy-acceptance list/detail reads remain available for admin evidence
  review through the current read service.

**Why**

Acceptance evidence is only trustworthy when derived from an approved
server-owned workflow. A generic request body for `user_id`, `accepted_at`,
`ip_address`, or `user_agent` would make acceptance evidence caller-owned.

### 4.3 Preserved Read, Model, Schema, Service, And Setup Boundary

**What this is**

B3 retires generic write request surfaces. It does not delete the underlying
policy/legal data model or every internal function that can create setup data.

**Contract / required behavior**

- `PolicyDocument` and `PolicyAcceptance` models remain valid persisted
  structures.
- Read schemas may remain exported for active API reads.
- Create/update schemas and services may remain available for controlled
  internal setup, seed, bootstrap, and future server-owned workflows.
- Seed/bootstrap scripts may write directly through internal setup paths, but
  they must not present retired HTTP write bodies as active manual API flows.
- Internal setup capabilities are not a public/admin request contract.

**Why**

Production-readiness work should remove unsafe caller authority without
destroying legitimate setup or future implementation primitives. The ownership
line is the HTTP request surface, not the mere existence of a model or service
function.

### 4.4 Current Caller And Frontend Boundary

**What this is**

Current user-facing legal presentation is compatible with the B3 boundary
because it does not call generic policy/legal write APIs. The current frontend
uses source-owned legal content for pages, modals, and agreement presentation,
but B3 does not require legal presentation to remain permanently static.

**Contract / required behavior**

- Current frontend code must not call generic `POST` or `PATCH`
  `/policy-documents` or `/policy-acceptances` endpoints.
- Current legal pages and modals may render source-owned policy text.
- Future frontend code may legitimately consume retained policy-document `GET`
  read APIs without violating B3.
- Future frontend code must not revive generic caller-owned legal authoring or
  policy-acceptance mutation through the retired `POST` or `PATCH` routes.
- Checkout/signup agreement UI may require user interaction, but B3 does not
  claim it persists authoritative legal acceptance evidence.
- Any future acceptance workflow must derive actor, policy reference, time, and
  request metadata from server-owned context and must receive separate approval.

**Why**

B3 must not confuse display text, read integration, or UI agreement controls
with durable legal acceptance evidence. It also must not turn current static
presentation into a permanent product constraint.

### 4.5 Ordinary JSON And HTTP Representation Boundary

**What this is**

B3 removes policy/legal write bodies as a blocker for request-body limit work.
It does not own whole-request byte limits or the exact public shape of 410
responses.

**Contract / required behavior**

- No retained policy/legal write route requires a special large policy-text,
  URL, or acceptance-evidence request body class.
- Bodyless policy/legal tombstones remain outside ordinary JSON request-body
  ownership.
- `WS02-04B2A2C` owns ordinary JSON body-size activation.
- `WS02-05A` owns HTTP media-type behavior, OpenAPI/tombstone representation,
  cache behavior, and method/compatibility foundations.
- `WS02-05B1` and `WS02-05B2` own broader request ownership and response
  minimization outside B3's narrow retired-write boundary.

**Why**

Keeping these boundaries separate prevents B3 from inventing numeric body
limits, HTTP representation policy, or legal/product workflows that belong to
other passes.

## 5. Implementation Scope

Current repository truth at the accepted baseline already satisfies the
pass-owned production behavior:

- `backend/routes/policy_document_routes.py` exposes public reads and bodyless
  admin-gated 410 tombstones for generic document mutations.
- `backend/routes/policy_acceptance_routes.py` exposes admin reads and
  bodyless admin-gated 410 tombstones for generic acceptance mutations.
- `backend/services/policy_document_service.py` and
  `backend/services/policy_acceptance_service.py` retain internal create/update
  primitives without route-owned generic write exposure.
- `backend/scripts/seed_policy_document_scenario.py` and
  `backend/scripts/seed_policy_acceptance_scenario.py` seed local scenario data
  through internal setup and explicitly state the generic API writes are
  retired.
- Current frontend legal pages, modals, signup links, checkout agreement UI,
  and profile links use source-owned legal content and do not call generic
  policy/legal write APIs.

Therefore Gate B has no approved production source correction, no
non-production/script correction, and no frontend correction unless a new
contradiction is discovered that requires returning to Gate A.

Gate B must create fresh trusted evidence only:

- `backend/tests/support/requirements/ws02_04b2a2b3.json`
- `backend/tests/workflows/policy_legal_request_ownership/TESTING_RECORD.md`
- `backend/tests/workflows/policy_legal_request_ownership/test_policy_document_request_ownership_contract.py`
- `backend/tests/workflows/policy_legal_request_ownership/test_policy_acceptance_request_ownership_contract.py`
- `backend/tests/workflows/policy_legal_request_ownership/test_policy_legal_caller_negative_space_contract.py`

The complete expected pass change set after Gate B is this canonical plan plus
the five Gate B evidence artifacts above.

## 6. Testing And Evidence

Gate B must create a new trusted workflow scope:

`backend/tests/workflows/policy_legal_request_ownership`

The scope must use the current EN-01 testing architecture:

```text
Pass
-> Requirement
-> Risk / Scenario / Edge Case
-> Trusted Test
-> Generated Traceability
```

Exact pytest node IDs must be generated from collection and checker output, not
hand-maintained in this plan.

### Planned Evidence Modules

`test_policy_document_request_ownership_contract.py`

- Proves `POST /policy-documents` and
  `PATCH /policy-documents/{policy_document_id}` are each registered only as
  the intended policy-document mutation tombstone.
- Proves the active-admin authentication dependency remains in front of
  tombstone behavior.
- Proves a rejected or non-admin authentication path does not fall through to
  the authenticated 410 lifecycle behavior.
- Proves the tombstone routes expose no FastAPI request-body parameter.
- Proves the tombstone handlers perform no route-owned manual body parsing.
- Proves the tombstone handlers have no `get_db` dependency and do not call
  policy-document create/update mutation-service functions.
- Proves authenticated no-body requests receive the intended 410 lifecycle
  behavior without asserting `WS02-05A`-owned response wording, media type,
  cache, or OpenAPI details.
- Proves submitted JSON does not become an accepted policy-document contract.
- Proves malformed JSON does not revive body parsing or request-model
  validation.
- Uses PostgreSQL where needed to prove body-bearing attempts do not create or
  alter a `PolicyDocument` row. For `PATCH`, use an existing synthetic policy
  record where useful and prove rejected caller content does not alter it.
- Proves a synthetic policy document can be created through a current
  controlled internal service/setup primitive rather than through the retired
  HTTP write API.
- Proves an eligible active, non-retired, already-effective synthetic policy
  document remains available through the current public read path.
- Proves an inactive document is not returned as an eligible public policy
  document.
- Proves a retired document is not returned as an eligible public policy
  document.
- Proves a future-effective document is not returned as an eligible public
  policy document.
- Uses the current public read contract for those predicates without expanding
  into `WS02-05B2` response-field minimization.

`test_policy_acceptance_request_ownership_contract.py`

- Proves `POST /policy-acceptances` and
  `PATCH /policy-acceptances/{policy_acceptance_id}` are each registered only
  as the intended policy-acceptance mutation tombstone.
- Proves the active-admin authentication dependency remains in front of
  tombstone behavior.
- Proves a rejected or non-admin authentication path does not fall through to
  the authenticated 410 lifecycle behavior.
- Proves the tombstone routes expose no FastAPI request-body parameter.
- Proves the tombstone handlers perform no route-owned manual body parsing.
- Proves the tombstone handlers have no `get_db` dependency and do not call
  policy-acceptance create/update mutation-service functions.
- Proves authenticated no-body requests receive the intended 410 lifecycle
  behavior without asserting `WS02-05A`-owned response wording, media type,
  cache, or OpenAPI details.
- Proves submitted JSON and malformed JSON do not revive policy-acceptance body
  validation.
- Proves submitted actor, policy, accepted-time, IP, user-agent, and other
  sentinel evidence is not accepted or reflected as a writable contract.
- Uses PostgreSQL where needed to prove body-bearing `POST` and `PATCH`
  attempts do not create or mutate `PolicyAcceptance` rows.
- Proves a synthetic acceptance can be created through a current controlled
  internal service/setup primitive rather than through the retired HTTP write
  API.
- Proves an active admin can retrieve the acceptance through both retained list
  and detail read paths.
- Proves a rejected or non-admin path cannot use those admin read surfaces.
- Proves the admin read boundary remains intact.

`test_policy_legal_caller_negative_space_contract.py`

- Proves the complete current frontend application source and caller surface
  does not use the retired generic policy/legal write endpoints:
  `POST /policy-documents`,
  `PATCH /policy-documents/{policy_document_id}`,
  `POST /policy-acceptances`, or
  `PATCH /policy-acceptances/{policy_acceptance_id}`.
- Allows harmless current or future `GET`/read integration with retained
  policy-document read APIs.
- Proves current policy/legal seed scripts use internal setup and do not print
  retired HTTP write bodies as active manual API workflows.
- Reviews current policy/legal seed/setup scripts relevant to this boundary.
  `seed_booking_policy_acceptance_scenario.py` may be inspected only as current
  negative-space/setup guidance where relevant; B3 must not reassign
  booking-policy-acceptance lifecycle ownership away from `WS02-04B2A2B1`.
- Proves current repository truth has no alternate active HTTP route accepting
  `PolicyDocumentCreate`, `PolicyDocumentUpdate`, or equivalent generic
  legal-authoring bodies.
- Proves current repository truth has no alternate active HTTP route accepting
  `PolicyAcceptanceCreate`, `PolicyAcceptanceUpdate`, or equivalent
  caller-owned acceptance evidence.
- Proves current active route handlers do not call generic policy-document
  create/update mutation-service functions from another active route.
- Proves current active route handlers do not call generic policy-acceptance
  create/update mutation-service functions from another active route.
- Proves current route inventory contains no same-method duplicate or slash
  alias that bypasses any of the four B3 tombstones.
- Proves from current route/application metadata that the four B3 mutation
  tombstones have no body parameters and therefore are not classified as
  retained ordinary JSON body routes.
- Proves there is no B3-specific large policy-text, arbitrary-policy-URL, or
  acceptance-evidence body-limit class.
- Proves current special body classes remain owned elsewhere and B3 does not
  invent a numeric policy/legal request-body value.

### Required Validation Commands

Gate B must run the focused B3 suite:

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/workflows/policy_legal_request_ownership
```

Gate B must run adjacent trusted regressions:

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/workflows/route_lifecycle_cleanup backend/tests/workflows/active_request_schema_bounds backend/tests/platform/request_body_limits
```

Gate B must run the full current trusted backend regression across executable
trusted roots that exist:

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/checker backend/tests/workflows backend/tests/platform
```

Gate B must run checker/foundation regression:

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/checker
```

Gate B must run domain and suite checker scopes:

```bash
backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/workflows/policy_legal_request_ownership
```

```bash
backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/workflows/route_lifecycle_cleanup
```

```bash
backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/platform/request_body_limits
```

```bash
backend/.venv/bin/python backend/tests/check_backend_tests.py --scope suite
```

Gate B must confirm generated traceability maps `R1` through `R5` and maps
`R6` to zero pytest nodes with the deferred reason above.

Gate B must run syntax validation for changed Python test files and:

```bash
git diff --check
```

### Evidence Quality Rules

The `TESTING_RECORD.md` must explain why the selected proof layer is adequate.
Where applicable, it must cover:

- route metadata and HTTP behavior rather than only static text;
- submitted-body and malformed-body negative cases;
- persisted read/setup proof for preserved read paths;
- caller/script negative space;
- rejected-side-effect proof where route/service calls could otherwise mutate
  state;
- no provider, browser, deployed/external runtime, legal-compliance,
  privacy-retention, or external-ingress overclaim.

## 7. Integration / Operational Expectations

B3 integrates with current source-owned WS02-04 work by keeping policy/legal
request bodies out of the ordinary mutation surface:

- `WS02-04B2A2B1` owns broad route-lifecycle cleanup and booking-policy
  acceptance tombstones. B3 does not absorb booking-policy acceptance merely
  because the name contains "policy".
- `WS02-04B2A2B2` owns provider/payment input ownership and does not own B3's
  policy/legal surfaces.
- `WS02-04B2A2C` can treat policy/legal write tombstones as bodyless and does
  not need a special policy-text body class from B3.
- `WS02-05A` may represent tombstones in OpenAPI and stable HTTP behavior
  without changing B3's retired-write authority.
- `WS02-05B1` and `WS02-05B2` may further refine request/response ownership
  without reviving B3's generic policy/legal write bodies.

Future policy/legal or acceptance workflows must preserve B3's ownership rule:
caller request bodies cannot be the sole authority for legal content,
acceptance actor, acceptance time, policy version, IP metadata, or user-agent
metadata.

## 8. Not Part Of This Pass

B3 does not own:

- booking-policy acceptance route lifecycle or evidence, owned by
  `WS02-04B2A2B1`;
- provider/payment input ownership, owned by `WS02-04B2A2B2`;
- ordinary JSON whole-request byte limits, owned by `WS02-04B2A2C`;
- special request-body classes, owned by `WS02-04B2A1`;
- HTTP media type, OpenAPI, cache policy, method handling, tombstone
  representation, and compatibility representation, owned by `WS02-05A`;
- broader request ownership, mass-assignment cleanup, or response minimization,
  owned by `WS02-05B1` and `WS02-05B2`;
- final legal text, legal review, privacy policy approval, retention rules,
  account deletion/privacy operations, or backup/restore privacy evidence;
- a new policy editor, CMS, admin authoring UI, or legal content publishing
  process;
- a new durable product acceptance workflow;
- provider dashboard, runtime, staging, edge, ingress, header, request-line,
  multipart, streaming, load, or browser/Playwright evidence;
- database migrations or schema redesign.

## 9. Related Controls And Remaining Evidence

| Control / Decision | What this pass establishes | What remains later |
|---|---|---|
| `API-M09` | Advances source-owned request limits by retiring generic policy/legal write bodies and proving no special policy/legal request-body class is required. | B3 does not re-prove or claim `WS02-04B2A2C` ordinary JSON body-limit ownership; the current source-owned ordinary JSON limit remains `WS02-04B2A2C`-owned. External ingress, process/server limits, headers/request-line limits, multipart/streaming, provider/edge precedence, staging captures, load, and deployed/external evidence remain outside B3. |
| `API-M13` / `WS02-05A` | Preserves the fact that policy/legal tombstones are bodyless compatibility routes without re-proving `WS02-05A`-owned HTTP media, OpenAPI, cache, and tombstone representation. | Current source-owned HTTP/media/OpenAPI/cache/tombstone representation remains `WS02-05A`-owned. Permanent/deployed HTTP-chain evidence remains outside B3. |
| `API-M14` / `WS02-05B2` | Preserves public policy-document reads and admin policy-acceptance reads while keeping response minimization outside B3. | Current policy-document public-read minimization is already `WS02-05B2`-owned and is not re-proven by B3. Future redesign or additional audience-specific policy/legal response work remains with `WS02-05B2` or a later appropriate owner. |
| `GOV-006` | Avoids inventing a numeric policy-text body limit or URL/body threshold for retired write routes. | Approved values and boundary tests remain required for any future body, URL, rate, timeout, retention, or alert threshold. |
| `WS10` | Keeps later privacy, retention, privacy-process, and related operational evidence outside B3. | Privacy/retention/deletion evidence and incident/privacy process evidence require later `WS10` or privacy/operations owners. Final legal-text/legal-review approval remains outside B3 and is not assigned by this pass. |

### Supporting Relationships

- `EN-01` supplies the trusted testing architecture, requirement declaration
  model, checker, and generated traceability.
- `EN-02` supplies the safe public-error and redaction foundation, but B3 does
  not redesign error envelopes.
- `EN-03` supplies repository/provider evidence-boundary discipline, but B3
  does not handle secrets or provider access.

## 10. Completion Criteria

- [ ] `backend/tests/support/requirements/ws02_04b2a2b3.json` exists with the
  exact frozen IDs, states, scopes, `source_controls`, and deferred reason in
  this plan.
- [ ] `backend/tests/workflows/policy_legal_request_ownership/TESTING_RECORD.md`
  exists and honestly records risks, evidence quality, proof layers, and
  remaining legal/privacy/runtime/provider gaps.
- [ ] Trusted B3 tests exist only under
  `backend/tests/workflows/policy_legal_request_ownership`.
- [ ] The four generic policy/legal mutation routes remain admin-gated,
  bodyless 410 tombstones.
- [ ] Public policy-document reads and admin policy-acceptance reads remain
  preserved.
- [ ] Internal setup, seed, and service primitives are not misclassified as
  prohibited public/admin HTTP writes.
- [ ] Current frontend callers and seed scripts do not advertise or use retired
  generic policy/legal write routes, while retained policy-document reads remain
  available for legitimate current or future read integration.
- [ ] No production, frontend, script, governance, or configuration correction
  is introduced unless Gate A is reopened and explicitly approves it.
- [ ] Focused, adjacent, full trusted backend, checker/domain/suite,
  generated-traceability, syntax, and `git diff --check` validation all pass.
- [ ] `R1` through `R5` are mapped to trusted evidence, and `R6` remains
  deferred with zero pytest mappings.
- [ ] Pass documentation and evidence do not claim legal-compliance,
  privacy-retention, provider/runtime, HTTP/OpenAPI/cache, broad request
  ownership, or ordinary body-limit closure.
- [ ] No unresolved owner decision or blocker remains.
