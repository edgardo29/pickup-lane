# WS02-04B2A2B2 - Provider And Payment Input Ownership

## At A Glance

| Field | Value |
|---|---|
| Pass | `WS02-04B2A2B2` |
| Track | `WS02` |
| Type | API / provider-payment request ownership recheck |
| Plain-English purpose | Preserve source-owned guards around opaque provider identifiers, checkout return URLs, payment-event repair, and game-credit source eligibility without pretending local tests prove provider/runtime payment readiness. |
| Primary controls | `API-M09`, `GOV-006` |
| Supporting / downstream controls | `FDN-04`, `PAY-004`, `PAY-005`, `PAY-006`, `PAY-008`, `PAY-009`, `PAY-010` |
| Authority basis | Current accepted repository tree; `docs/production-readiness/decisions/ws02-04b2a2b2-provider-payment-input-rules-approved.md`; `docs/production-readiness/governance/limits-and-thresholds-register.md` as recording artifact only; accepted WS02-04 source-owned closeout; accepted remediation plan, blueprint, and cross-pass ownership records. |
| Depends on | `EN-01`; `EN-02`; `EN-03`; `WS02-04A`; `WS02-04B1`; `WS02-04B2A1`; `WS02-04B2A2A`; `WS02-04B2A2B1` |
| Trusted test scope | `backend/tests/workflows/provider_payment_input_ownership` |
| Implementation type | One production service correction, one non-production script correction, trusted evidence, and traceability. |
| Production application correction set | `backend/services/game_credit_admin_service.py` |
| Frontend correction set | None. |

WS02-04B2A2B2 is the B2 slice for opaque provider/payment inputs and
source-derived financial request ownership. It does not own generic product
limits, ordinary JSON body-size limits, HTTP representation, response
minimization, deployed provider evidence, payment reconciliation, or durable
financial workflow closure.

## 1. Purpose

This pass proves that Pickup Lane's current source-owned provider/payment
input boundaries are deliberate, bounded, and assigned to the right owners.

The pass covers retained request surfaces where client input still touches
provider-adjacent or financial-adjacent workflows:

- saved-card SetupIntent sync;
- inbox global-seen token submission;
- checkout return URL selection;
- retired generic payment/refund/payment-event mutations;
- retained payment-event repair;
- game-credit issue/reverse operational text and source-derived eligibility.

The core rule is simple: local request parsing may reject blank, oversized, or
structurally unsafe input, but it must not pretend to prove provider facts or
financial entitlement facts that belong to provider services, signed webhooks,
server-owned rows, or later payment/reconciliation evidence.

The pass does not redesign checkout, Stripe, inbox, game credits, admin money,
or frontend payment flows. It preserves the approved source behavior, tightens
one current game-credit source-linkage gap, removes one stale non-production
script instruction that still advertises a retired provider-event write, and
creates fresh trusted evidence under the EN-01 architecture.

## 2. Why This Matters

Provider/payment-adjacent inputs are easy places to create false confidence.
An input can look like a Stripe identifier, a signed token, a return URL, or a
credit request, but the string itself is not the authority.

If B2A2B2 is wrong, these failures become possible:

- a blank or oversized SetupIntent ID reaches saved-card sync and creates
  misleading local evidence before provider validation;
- local code treats a Stripe prefix as proof that a SetupIntent or PaymentMethod
  is legitimate;
- an inbox global-seen request mutates state from an untrusted or wrong-user
  token;
- checkout sends an arbitrary external, credential-bearing, query-bearing, or
  wrong-path return URL to the provider;
- generic payment/refund/payment-event mutation routes become alternate write
  paths for provider-owned state;
- a repair route lets callers rewrite raw provider event identity or payloads;
- game-credit issuance fabricates source-less or excessive monetary value;
- a payment with no authoritative game or booking-derived game context supplies
  credit eligibility after the caller provides an unrelated official game ID;
- local tests claim provider dashboards, reconciliation, runtime deployment, or
  durable financial workflow readiness that they cannot honestly prove.

This pass keeps local proof honest: test what the source owns, document the
dynamic service checks that source can enforce, and explicitly leave external
payment/provider/runtime evidence with later owners.

## 3. Requirements

| ID | Requirement | What it means | Why it matters |
|---|---|---|---|
| `WS02-04B2A2B2-R1` | Saved payment-method sync treats `setup_intent_id` as bounded opaque provider input. | `POST /user-payment-methods/sync` requires `setup_intent_id`, trims surrounding whitespace, rejects blank input, caps it at 255 characters, accepts opaque values without local prefix legitimacy checks, and relies on provider-backed service validation for SetupIntent existence, ownership, status, customer association, and PaymentMethod legitimacy. | Prevents local schema code from either accepting unsafe raw input or falsely treating string shape as provider proof. |
| `WS02-04B2A2B2-R2` | Inbox global-seen uses bounded opaque token input and service-owned token validation. | `PUT /inbox/app-updates/global-seen` requires `seen_token`, trims surrounding whitespace, rejects blank input, caps it at 512 characters, treats it as an opaque server-issued request value, and leaves signature, kind, version, user, sequence, and payload checks in the inbox service. | Prevents oversized or wrong-user tokens from mutating inbox state while preserving EN-03 secret ownership and service-owned token semantics. |
| `WS02-04B2A2B2-R3` | Checkout return URLs are same-app, same-game, parameter-free return destinations. | Optional `return_url` is trimmed when supplied, must be absolute `http` or `https`, must not include embedded credentials, query strings, or fragments, must exactly match a configured Pickup Lane application/CORS origin, and must use `/games/{game_id}/checkout`. It is validated before game lookup, database mutation, or provider work. | Prevents arbitrary redirect targets or parameter-bearing URLs from becoming provider return destinations. |
| `WS02-04B2A2B2-R4` | Generic payment/refund/payment-event write surfaces remain retired. | Generic `POST /payments`, `PATCH /payments/{payment_id}`, `POST /refunds`, `PATCH /refunds/{refund_id}`, and `POST /payment-events` cannot be used as generic body-bearing payment/provider writes. Active writes remain owned by checkout, signed webhook processing, admin-money, refund/retry/reconcile, official-game, and later WS05 workflows. | Prevents obsolete generic write surfaces from bypassing workflow-owned payment/provider rules. |
| `WS02-04B2A2B2-R5` | Payment-event repair cannot rewrite provider-owned event metadata. | The retained repair surface accepts only `payment_id`, `processing_status`, and optional trimmed `processing_error` capped at 1000 characters. Provider identity, provider event ID, event type, raw payload, provider timestamps, and other provider-owned metadata are not request-writable through repair. | Allows narrow operational repair without turning repair into a raw provider-event mutation API. |
| `WS02-04B2A2B2-R6` | Game-credit issue/reverse requests use B2A2B2-owned operational text bounds and source-derived monetary eligibility. | Optional issue/reverse `idempotency_key` is trimmed and capped at 160 characters. Optional issue/reverse `note` is trimmed and capped at 1000 characters, with blank optional text allowed to normalize absent/null at the service layer. Generic issue requires a source booking and/or source payment that supplies server-owned monetary eligibility. `source_game_id` may confirm official in-app context but supplies no monetary ceiling alone and cannot manufacture game context for an unlinked payment. A source payment used for eligibility must establish authoritative official in-app game context through its own `game_id` or its associated booking's game. Payment game, payment booking game, and caller-supplied `source_game_id` must agree when present. Payment and booking references that resolve to the same underlying booking/payment source must share one remaining eligibility budget, including payment-only then booking-only issuance, booking-only then payment-linked issuance, and multiple payments for the same booking. Supplied or derived source booking/payment/game references must belong to the credited user and agree. The ceiling is the minimum applicable server-owned booking/payment amount, reduced by existing non-reversed credits sharing the relevant source. Existing reversed credits remain excluded. Requested credit must be positive and no more than the remaining eligible amount. Source-less discretionary issuance remains disabled, and reversal accepts no client-supplied reversal amount. | Prevents generic admin credit requests from fabricating source-less, unlinked, duplicate-source, or excessive monetary value while preserving narrow source-linked support paths. |
| `WS02-04B2A2B2-R7` | Current source and caller inventory has no active bypass for B2A2B2-owned provider/payment input ownership. | Current production frontend callers use retained supported flows, not retired generic payment/refund/payment-event writes. Current active backend routes and repository guidance must not create a second active write contract that contradicts B2A2B2. | Prevents tests from proving only the intended path while another current path or instruction undermines it. |
| `WS02-04B2A2B2-R8` | Later-owner evidence remains explicit and is not falsely closed by B2A2B2. | Whole-request body limits, HTTP/OpenAPI/cache/tombstone representation, request/response ownership, permanent URL/header/edge/runtime evidence, EN-03 secret lifecycle, Stripe/provider dashboards, payment/refund/reconciliation lifecycle, durable financial workflows, telemetry/metrics/dashboards/alerts, genuine financial-credit concurrency closure, and future source-less discretionary credit capability remain with their owners. | Keeps source-owned proof from overstating payment/provider/runtime readiness or full control closure. |

### Exact Requirement Declaration Metadata

Pass implementation must add one stable declaration file:

- `backend/tests/support/requirements/ws02_04b2a2b2.json`

The exact declaration metadata is frozen as follows:

| ID | State | Scope | `source_controls` | Reason |
|---|---|---|---|---|
| `WS02-04B2A2B2-R1` | `required` | `workflows/provider_payment_input_ownership` | `["API-M09", "GOV-006", "FDN-04", "PAY-008", "WS02-04B2A2B2"]` | Not required. |
| `WS02-04B2A2B2-R2` | `required` | `workflows/provider_payment_input_ownership` | `["API-M09", "GOV-006", "FDN-04", "EN-03", "WS02-04B2A2B2"]` | Not required. |
| `WS02-04B2A2B2-R3` | `required` | `workflows/provider_payment_input_ownership` | `["API-M09", "GOV-006", "FDN-04", "PAY-004", "WS02-04B2A2B2"]` | Not required. |
| `WS02-04B2A2B2-R4` | `required` | `workflows/provider_payment_input_ownership` | `["API-M09", "PAY-004", "PAY-005", "PAY-006", "PAY-009", "WS02-04B2A2B1", "WS02-04B2A2B2"]` | Not required. |
| `WS02-04B2A2B2-R5` | `required` | `workflows/provider_payment_input_ownership` | `["API-M09", "PAY-004", "PAY-005", "PAY-006", "WS02-04B2A2B2", "WS05"]` | Not required. |
| `WS02-04B2A2B2-R6` | `required` | `workflows/provider_payment_input_ownership` | `["API-M09", "GOV-006", "FDN-04", "PAY-010", "WS02-04B2A2B2", "WS05"]` | Not required. |
| `WS02-04B2A2B2-R7` | `required` | `workflows/provider_payment_input_ownership` | `["API-M09", "WS02-04B2A2B2", "WS02-05B1", "WS05"]` | Not required. |
| `WS02-04B2A2B2-R8` | `deferred` | `governance` | `["API-M09", "API-M13", "API-M14", "API-M18", "GOV-006", "PAY-004", "PAY-005", "PAY-006", "PAY-008", "PAY-009", "PAY-010", "EN-03", "WS02-04B2A1", "WS02-04B2A2C", "WS02-05A", "WS02-05B1", "WS02-05B2", "WS03", "WS04", "WS05", "WS09", "WS10"]` | `Whole-request body limits, HTTP/OpenAPI/cache/tombstone representation, request and response ownership, permanent URL/header/edge/runtime evidence, inbox secret lifecycle, Stripe/provider dashboards, payment/refund/reconciliation lifecycle, durable financial workflows, telemetry/metrics/dashboards/alerts, genuine financial-credit concurrency closure, and any future source-less discretionary credit capability remain with their owners and cannot be closed by B2A2B2 local source-owned evidence.` |

`WS02-04B2A2B2-R8` is non-executable and must have zero pytest mappings.

## 4. Technical Design / Contracts

### 4.1 Authority Split

**What this is**

B2A2B2 separates local request ownership from provider/payment authority. The
repository may enforce local input bounds, route retirement, current caller
compatibility, and server-owned source eligibility. Provider dashboards,
deployed provider behavior, Stripe object truth, durable reconciliation, and
external runtime behavior remain outside this local source-owned pass.

**Contract / required behavior**

The decision record
`docs/production-readiness/decisions/ws02-04b2a2b2-provider-payment-input-rules-approved.md`
is the approving source for B2A2B2 numeric and policy values. The limits and
thresholds register records the decision; it does not approve the values by
itself. Current source is implementation truth and evidence target, not its own
authority.

**Why**

Without the decision record, B2A2B2 would be preserving arbitrary current
values such as 255, 512, 1000, and 160 without owner approval. With the
decision record, those values are durable B2A2B2 policy and can be tested
honestly.

### 4.2 Saved Payment-Method SetupIntent Sync

**What this is**

`POST /user-payment-methods/sync` links a saved payment method after the
frontend completes the provider SetupIntent flow.

**Contract / required behavior**

- `setup_intent_id` is required when the sync request is used.
- Surrounding whitespace is trimmed.
- Blank input rejects.
- Maximum length is 255 characters.
- The schema treats the value as an opaque provider identifier.
- The schema must not infer legitimacy from `seti_` or any other provider
  prefix.
- Provider-backed service validation remains authoritative for SetupIntent
  existence, user/customer ownership, status, customer association, and
  PaymentMethod legitimacy.

**Why**

The local backend can prove that the request body is finite and non-blank. It
cannot prove that a provider object exists or belongs to the user without using
the provider-backed service boundary.

### 4.3 Inbox Global-Seen Token

**What this is**

`PUT /inbox/app-updates/global-seen` marks global platform notices seen using a
server-issued token from the inbox response.

**Contract / required behavior**

- `seen_token` is required.
- Surrounding whitespace is trimmed.
- Blank input rejects.
- Maximum length is 512 characters.
- The request schema treats the value as opaque server-issued input.
- Signature, kind, version, user, sequence, and payload validation remain in
  the inbox service.
- The 512-character bound is application-specific headroom for the current
  signed-token design, not a universal token-format maximum.

**Why**

The token is not a generic client value. Local schema parsing keeps the request
bounded, while the inbox service protects identity, sequence, signature, and
payload semantics.

### 4.4 Checkout Return URL

**What this is**

Checkout may pass a return URL to the payment provider so the browser can
return to Pickup Lane after provider-controlled confirmation steps.

**Contract / required behavior**

- `return_url` is optional.
- When supplied, surrounding whitespace is trimmed.
- It must be an absolute `http` or `https` URL.
- Embedded username/password credentials reject.
- Query strings reject.
- Fragments reject.
- The origin must exactly match a configured Pickup Lane application/CORS
  origin.
- The path must be exactly `/games/{game_id}/checkout`.
- Arbitrary external origins and alternate paths reject.
- Temporary Render, Vercel, or other deployment hostnames must not be
  hard-coded as permanent policy.
- Validation occurs before game lookup, database mutation, or provider work.

**Why**

The return URL is provider-adjacent. It must not become an open redirect,
parameter smuggling path, or deployment-host shortcut. At the same time,
B2A2B2 does not approve permanent HTTPS, canonical-domain, edge, URL-size, or
provider-precedence behavior.

### 4.5 Generic Payment, Refund, And Event Mutation Retirement

**What this is**

Generic payment/refund/event CRUD-style writes are not active product workflows.
They are replaced by checkout, signed webhooks, admin-money, refund/retry,
reconcile, official-game, and later payment-provider flows.

**Contract / required behavior**

These generic writes remain retired or unavailable as generic body-bearing
mutation surfaces:

- `POST /payments`
- `PATCH /payments/{payment_id}`
- `POST /refunds`
- `PATCH /refunds/{refund_id}`
- `POST /payment-events`

Read routes may remain available where current source supports them. Supported
writes must remain owned by their current workflow-specific routes and later
WS05 payment/provider lifecycle work.

**Why**

Provider-owned facts and payment lifecycle state cannot safely be authored by
generic request bodies.

### 4.6 Retained Payment-Event Repair

**What this is**

The retained payment-event repair surface supports narrow admin/backend repair
of linkage or processing state, not raw provider event authoring.

**Contract / required behavior**

The retained repair request-writable fields are exactly:

- `payment_id`
- `processing_status`
- `processing_error`

Optional `processing_error` is trimmed when supplied and capped at 1000
characters.

The repair surface must not make these provider-owned fields request-writable:

- provider identity;
- provider event ID;
- event type;
- raw provider payload;
- provider timestamps;
- receipt/provider metadata;
- other provider-owned event facts.

**Why**

Operational repair needs a narrow path to fix processing/linkage state, but it
must not become a replacement for signed webhook ingestion or provider API
truth.

### 4.7 Game-Credit Issue And Reverse

**What this is**

Game-credit issue and reverse are financial-adjacent admin workflows. B2A2B2
owns the current source-derived eligibility boundary for the generic issue
route and the request text bounds for issue/reverse.

**Contract / required behavior**

Operational text:

- optional `idempotency_key` trims surrounding whitespace and is capped at 160
  characters on issue and reverse;
- optional `note` trims surrounding whitespace and is capped at 1000
  characters on issue and reverse;
- blank optional operational text may normalize to absent/null at the service
  layer.

Issue eligibility:

- generic admin issuance must include a source booking and/or source payment
  that supplies server-owned monetary eligibility;
- a source payment used for eligibility must establish authoritative official
  in-app game context through its own `game_id` or through its associated
  booking's game;
- if both payment `game_id` and payment booking game exist, they must agree;
- `source_game_id` may confirm the authoritative source game but cannot
  manufacture game association for a payment that has neither game nor booking
  context;
- if `source_game_id` is supplied, it must agree with the authoritative game
  derived from payment/booking context;
- a payment with neither game nor booking-derived game context cannot supply
  monetary eligibility;
- valid booking-only sources and properly linked payment sources remain
  supported;
- payment and booking references that resolve to the same underlying
  booking/payment source must share one remaining eligibility budget;
- a prior non-reversed credit linked through a payment must reduce later
  eligibility when the same source is addressed through that payment's booking;
- a prior booking-linked credit must reduce later eligibility when addressed
  through a payment belonging to that booking;
- multiple payments belonging to the same booking must not create independent
  credit ceilings for that booking;
- existing reversed credits remain excluded from the used-source total;
- supplied or derived source booking, source payment, and source game
  references must belong to the credited user and agree with each other;
- eligible source games must be official in-app games;
- the monetary ceiling is the minimum applicable server-owned booking/payment
  amount from the validated source context;
- existing non-reversed credits for the credited user sharing the relevant
  source reduce remaining eligible amount;
- requested credit must be positive and no more than the remaining eligible
  amount;
- no universal monetary ceiling is introduced;
- source-less discretionary support/admin credit through the generic route
  remains disabled.

Reverse behavior:

- reversal remains bounded by the existing credit record and current eligible
  unused amount;
- the request does not supply a reversal amount.

**Why**

Source-derived credit issuance lets support/admin workflows correct or account
for known in-app payment/booking context. It must not become a generic money
creation endpoint. A future source-less discretionary capability needs its own
authorization, limit, audit, idempotency, and operational decision.

### 4.8 Error, Ordering, And Redaction Expectations

**What this is**

B2A2B2 relies on stable, safe request rejection and service-owned dynamic
validation without exposing sensitive or provider-owned input.

**Contract / required behavior**

- Static request-shape checks run before provider lookup, source eligibility,
  database mutation, audit writes, notification/background work, or provider
  work where applicable.
- Invalid tokens, URLs, provider identifiers, raw provider payloads, and
  internal details must not be echoed in public errors.
- B2A2B2 preserves the existing EN-02 safe public error/redaction foundation
  and WS02-04A stable API error contract instead of redefining it.

**Why**

The pass should reject unsafe input before side effects, but it should not
create new sensitive-output paths or duplicate existing error-contract owners.

### 4.9 Current Caller And Negative-Space Contract

**What this is**

B2A2B2 must prove that current callers and current repository artifacts do not
provide a bypass around the intended source-owned boundaries.

**Contract / required behavior**

- Current production frontend saved-card sync calls the retained sync endpoint
  with `setup_intent_id`.
- Current checkout calls send optional return URL only through the retained
  checkout payment-intent flow.
- Current inbox callers send the server-provided global-seen token to the
  retained inbox endpoint.
- Current production frontend code does not call retired generic
  payment/refund/payment-event mutation endpoints.
- Current source guidance must not advertise retired generic provider-event
  creation as active. Gate B must preserve the existing
  `backend/scripts/seed_payment_event_scenario.py` seed-data creation and ID
  output, remove the printed manual `POST /payment-events` request body and raw
  provider-event payload authoring example, and replace it with a concise
  message that generic payment-event creation is retired and payment-event
  creation is owned by signed Stripe webhook processing.
- Current route and service inventories must preserve downstream owner
  boundaries for WS02-05A, WS02-05B1, WS02-05B2, WS03, WS05, EN-03, and later
  runtime/provider evidence.

**Why**

Testing only the intended function is not enough if another current caller,
script, or route still tells developers to use the retired path.

## 5. Implementation Scope

### Pass-Owned Governance And Planning Artifacts

The Gate A governance and planning artifacts are:

- `docs/production-readiness/decisions/ws02-04b2a2b2-provider-payment-input-rules-approved.md`
- `docs/production-readiness/governance/limits-and-thresholds-register.md`
- `docs/production-readiness/planning/passes/ws02/ws02-04b2a2b2-opaque-provider-payment-inputs.md`

The decision record is the approving source for B2A2B2 numeric and policy
values. The limits register records selected approved values and open handoffs.
The plan translates authority into implementable requirements and evidence.

### Production Application Correction Set

Exactly one production application file requires correction:

- `backend/services/game_credit_admin_service.py`

Gate B must preserve the already-correct behavior for SetupIntent input, inbox
global-seen token input, checkout return URL validation, generic
payment/refund/event mutation retirement, and payment-event repair field
ownership.

Gate B must tighten game-credit source-derived eligibility so that:

- a source payment used for credit eligibility establishes authoritative
  official in-app game context through its own `game_id` or its associated
  booking's game;
- if both payment game and payment booking game exist, they agree;
- caller-supplied `source_game_id` may confirm the authoritative source game
  but may not manufacture a game association for a payment with neither game
  nor booking context;
- supplied `source_game_id` agrees with the authoritative game derived from the
  payment/booking context;
- a payment with neither game nor booking-derived game context cannot supply
  monetary eligibility;
- valid booking-only and properly linked payment flows remain valid;
- payment and booking references that resolve to the same underlying
  booking/payment source share one remaining eligibility budget;
- prior non-reversed credits linked through a payment reduce later eligibility
  when the same source is addressed through that payment's booking;
- prior non-reversed booking-linked credits reduce later eligibility when
  addressed through a payment belonging to that booking;
- multiple payments belonging to the same booking cannot independently obtain
  the full booking-derived credit ceiling;
- existing reversed credits remain excluded according to current approved
  behavior;
- no new payment-status, payment-type, or provider rules are introduced.
- no migration or new storage field is required by the frozen Gate A design; if
  implementation proves one unavoidable, Gate B must stop and return to Gate A.

### Backend Non-Production Correction Set

Exactly one current non-production source artifact requires correction:

- `backend/scripts/seed_payment_event_scenario.py`

That script currently prints a manual `POST /payment-events` body containing
raw provider fields. Gate B must preserve the existing seed-data creation and
ID output, remove the printed manual `POST /payment-events` request body,
remove the raw provider-event payload authoring example, and replace it with a
concise message that generic payment-event creation is retired and
payment-event creation is owned by signed Stripe webhook processing. The
correction must not add another manual or generic provider-event creation path.

### Frontend Correction Set

None.

Current production frontend callers are compatible with the approved source
rules and do not call retired generic payment/refund/payment-event mutation
surfaces.

### Pass-Owned Test And Evidence Artifacts

Gate B must create exactly these pass-owned trusted evidence artifacts:

- `backend/tests/support/requirements/ws02_04b2a2b2.json`
- `backend/tests/workflows/provider_payment_input_ownership/TESTING_RECORD.md`
- `backend/tests/workflows/provider_payment_input_ownership/test_setup_intent_input_contract.py`
- `backend/tests/workflows/provider_payment_input_ownership/test_inbox_seen_token_input_contract.py`
- `backend/tests/workflows/provider_payment_input_ownership/test_checkout_return_url_contract.py`
- `backend/tests/workflows/provider_payment_input_ownership/test_payment_mutation_retirement_contract.py`
- `backend/tests/workflows/provider_payment_input_ownership/test_payment_event_repair_contract.py`
- `backend/tests/workflows/provider_payment_input_ownership/test_game_credit_source_contract.py`
- `backend/tests/workflows/provider_payment_input_ownership/test_current_caller_negative_space_contract.py`

The test directory must follow current trusted `workflows/` conventions.

### Shared Test-Isolation Compatibility Correction

Gate B may also correct one pre-existing shared trusted-test infrastructure
isolation defect in `backend/tests/conftest.py`. The root `client` fixture
currently uses `@pytest.fixture(scope="session")` around `TestClient(app)`,
which can keep the canonical FastAPI application lifespan active across
independent trusted tests. EN-01 requires trusted tests to remain isolated and
order-independent, and the required full trusted regression has shown this
shared fixture state can leak into
`backend/tests/platform/runtime/test_runtime_lifecycle_and_health_contract.py::test_backend_main_is_the_single_canonical_app_and_health_owner`.

The frozen correction is only to make the root `client` fixture function-scoped
by removing `scope="session"` from its fixture decorator, so each consuming
test enters and exits the canonical application lifespan independently. This
does not change B2A2B2 requirements R1-R8, owner-approved provider/payment
policy, proof layers, production/frontend behavior, or test scenarios. If that
exact correction proves unsafe or insufficient, Gate B must stop and return to
Gate A instead of broadening the shared fixture change.

### Exact Gate B Editable File Set

Gate B may edit exactly these 12 files:

- `backend/services/game_credit_admin_service.py`
- `backend/scripts/seed_payment_event_scenario.py`
- `backend/tests/conftest.py`
- `backend/tests/support/requirements/ws02_04b2a2b2.json`
- `backend/tests/workflows/provider_payment_input_ownership/TESTING_RECORD.md`
- `backend/tests/workflows/provider_payment_input_ownership/test_setup_intent_input_contract.py`
- `backend/tests/workflows/provider_payment_input_ownership/test_inbox_seen_token_input_contract.py`
- `backend/tests/workflows/provider_payment_input_ownership/test_checkout_return_url_contract.py`
- `backend/tests/workflows/provider_payment_input_ownership/test_payment_mutation_retirement_contract.py`
- `backend/tests/workflows/provider_payment_input_ownership/test_payment_event_repair_contract.py`
- `backend/tests/workflows/provider_payment_input_ownership/test_game_credit_source_contract.py`
- `backend/tests/workflows/provider_payment_input_ownership/test_current_caller_negative_space_contract.py`

Gate B must not edit production application code outside the approved
game-credit service correction, frontend code, migrations, provider
configuration, or unrelated planning and governance documents. If Gate B
discovers that another production file, requirement, proof layer, or broader
scope is needed, it must stop and return to Gate A. A new owner decision is
required only when the problem is an actual unresolved authority or policy
decision.

## 6. Testing And Evidence

### Evidence Model

Trusted B2A2B2 evidence must use the EN-01 relationship:

```text
Pass
-> Requirement
-> Risk / Scenario / Edge Case
-> Trusted Test
-> Generated Traceability
```

Exact pytest node IDs are generated from collection and requirement metadata.
The plan freezes stable requirement IDs and trusted scopes; the testing record
must hold detailed risk, scenario, edge-case, and adequacy reasoning.

### Requirement Declaration

Gate B must create:

- `backend/tests/support/requirements/ws02_04b2a2b2.json`

The JSON must use the exact IDs, states, scopes, `source_controls`, and
deferred reason frozen in this plan. Required requirements map to trusted tests
under `workflows/provider_payment_input_ownership`. Deferred requirement
`WS02-04B2A2B2-R8` maps to governance only and must have zero pytest mappings.

### Human Testing Record

Gate B must create:

- `backend/tests/workflows/provider_payment_input_ownership/TESTING_RECORD.md`

The record must use
`docs/production-readiness/planning/templates/TESTING-RECORD-TEMPLATE.md`, summarize
risks and evidence quality, and explicitly describe why local tests can prove
source-owned behavior but cannot close provider dashboards, runtime deployment,
durable reconciliation, or broader PAY controls.

### Trusted Test Modules

Gate B must create the focused modules listed in the pass-owned evidence set.
The expected proof responsibilities are:

| Module | Requirement coverage | Required proof |
|---|---|---|
| `test_setup_intent_input_contract.py` | `WS02-04B2A2B2-R1` | Required/blank/trim/max/max+1 behavior, opaque ID acceptance until provider service validation, no prefix-based local legitimacy, and provider-owned validation boundary using fakes at the application-owned service boundary. |
| `test_inbox_seen_token_input_contract.py` | `WS02-04B2A2B2-R2` | Required/blank/trim/max/max+1 behavior, signed token kind/version/user/sequence validation, invalid-token rejection without unsafe echoed token values, and no prohibited global-seen mutation for invalid tokens. |
| `test_checkout_return_url_contract.py` | `WS02-04B2A2B2-R3` | Omitted/null acceptance, trim behavior, allowed configured origin, disallowed scheme, credentials, query, fragment, external origin, alternate path, wrong game path, no temporary hard-coded deployment hosts, and validation before game lookup/provider work. |
| `test_payment_mutation_retirement_contract.py` | `WS02-04B2A2B2-R4` | Generic payment/refund/payment-event write routes remain retired/unavailable as body-bearing mutation surfaces, and supported replacement workflow routes remain discoverable. |
| `test_payment_event_repair_contract.py` | `WS02-04B2A2B2-R5` | Only repair fields are writable, extra provider-owned fields reject, `processing_error` trim/max/max+1 behavior, meaningful persisted repair effects occur, and provider identity/event type/raw payload/provider metadata remain unchanged. |
| `test_game_credit_source_contract.py` | `WS02-04B2A2B2-R6` | Operational text trim/max/blank normalization, source booking/payment/user/game agreement, source payment with neither `game_id` nor booking context rejects, that same unlinked payment still rejects when caller supplies an unrelated valid official `source_game_id`, payment with authoritative official-game linkage succeeds when all other requirements are valid, payment with booking-derived official-game linkage succeeds when valid, supplied `source_game_id` conflicting with payment or booking game rejects, booking-only source behavior remains valid, payment-only issuance followed by booking-only issuance cannot reset the ceiling, booking-only issuance followed by payment-linked issuance cannot reset the ceiling, two payments for the same booking cannot independently obtain the full booking-derived credit ceiling, reversed prior credit remains excluded according to current approved behavior, source_game_id without monetary source rejection, official in-app eligibility, min booking/payment ceiling, existing non-reversed source credit deduction, positive amount and remaining-eligible bound, source-less discretionary rejection, and reversal bounded by existing unused credit with no client-supplied amount. |
| `test_current_caller_negative_space_contract.py` | `WS02-04B2A2B2-R7` | Current production frontend callers use retained supported flows; no current production frontend caller uses retired generic payment/refund/payment-event writes; no current non-production guidance advertises retired generic provider-event creation after the seed-script correction. |

### Proof-Layer Decisions

| Layer | Required for B2A2B2? | Decision |
|---|---|---|
| PostgreSQL | Yes for dynamic persisted service behavior. | Required for inbox global-seen mutation/no-mutation checks, payment-event repair persistence and provider-field preservation, and game-credit source-derived eligibility/reversal checks, including source-payment authoritative-game-linkage and same-underlying-source budget sharing. Static schema and source-inventory tests may avoid database access. |
| Provider/network | No live provider/network required. | Stripe/provider behavior must be faked at the application-owned service boundary. Local tests may verify that provider validation is delegated, but must not claim live Stripe dashboard, live provider ownership, or deployed provider behavior. |
| Browser/Playwright | No. | Current frontend caller compatibility is proven by source inspection/static tests. Browser runtime behavior remains outside B2A2B2. |
| Migration | No. | B2A2B2 changes no database schema and requires no Alembic migration evidence. |
| Genuine concurrency/race | No for pass closure. | Serial PostgreSQL service tests are required where source-owned persisted effects matter. Genuine concurrent credit/provider-event race closure remains with WS05/database/payment lifecycle owners. |
| Controlled time | Not generally required. | If a test asserts timestamp or sequence behavior, it must use a controlled/frozen/injected baseline. B2A2B2 should not introduce uncontrolled wall-clock assertions. |
| External runtime/provider evidence | No. | Runtime deployment, provider dashboards, staging behavior, permanent host, edge, telemetry, and alert evidence remain later-owner evidence. |

### Required Validation Commands

Gate B must run these focused, adjacent, regression, checker, and traceability
validations from the repository root:

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/workflows/provider_payment_input_ownership
```

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/workflows/route_lifecycle_cleanup backend/tests/workflows/active_request_schema_bounds backend/tests/platform/request_body_limits backend/tests/platform/secrets
```

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/workflows backend/tests/platform/runtime/test_runtime_lifecycle_and_health_contract.py::test_backend_main_is_the_single_canonical_app_and_health_owner
```

This proves the shared TestClient isolation correction against the previously
failing trusted-test order.

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/checker backend/tests/workflows backend/tests/platform
```

This is the full current trusted backend regression across the trusted
executable roots that actually exist at this baseline.

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/checker
```

```bash
backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/workflows/provider_payment_input_ownership
```

```bash
backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/workflows/route_lifecycle_cleanup
```

```bash
backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/workflows/active_request_schema_bounds
```

```bash
backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/platform/request_body_limits
```

```bash
backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/platform/secrets
```

```bash
backend/.venv/bin/python backend/tests/check_backend_tests.py --scope suite
```

```bash
git diff --check
```

Gate B must also confirm:

- all required B2A2B2 declarations have trusted mappings;
- deferred `WS02-04B2A2B2-R8` has zero pytest mappings and a required reason;
- no real provider payloads, production tokens, credentials, production
  database URLs, private keys, or real user/payment/provider data appear in new
  evidence artifacts.

## 7. Integration / Operational Expectations

B2A2B2 integrates with existing source-owned workflows while preserving current
supported behavior and tightening the approved game-credit source authority
where current source is too permissive:

- saved-card sync continues to call provider-backed SetupIntent validation;
- inbox global-seen continues to rely on signed-token service validation and
  EN-03-owned secret independence;
- checkout continues to send only same-app, same-game return destinations to
  the provider;
- generic payment/refund/payment-event writes remain unavailable while active
  workflow-specific writes stay preserved;
- payment-event repair remains a narrow operational surface;
- game-credit issue/reverse remains bounded by authoritative official in-app
  source context, server-owned monetary sources, and existing credit records.

Later payment/provider work may consume B2A2B2 as a source-owned prerequisite,
but must not treat it as proof of deployed provider configuration, provider
dashboard state, durable reconciliation, full credit ledger correctness,
runtime host behavior, or production telemetry.

## 8. Not Part Of This Pass

B2A2B2 does not own:

- ordinary JSON whole-request byte limits, owned by `WS02-04B2A2C`;
- special request-body classes, owned by `WS02-04B2A1`;
- generic route-lifecycle cleanup outside provider/payment inputs, owned by
  `WS02-04B2A2B1`;
- policy/legal request ownership, owned by `WS02-04B2A2B3`;
- HTTP media type, OpenAPI, cache, tombstone representation, or error-envelope
  representation, owned by `WS02-05A` and `WS02-04A`;
- broad request ownership/mass-assignment cleanup and response minimization,
  owned by `WS02-05B1` and `WS02-05B2`;
- identity/profile authority, owned by `WS03`;
- `INBOX_TOKEN_SECRET` independence and broader secret lifecycle, owned by
  `EN-03`;
- Stripe dashboard settings, provider runtime evidence, payment/refund
  lifecycle, reconciliation, durable jobs, and financial worker behavior,
  owned by `WS05` and later provider/payment owners;
- genuine database concurrency closure and financial-credit race proof, owned
  by `WS04` with payment lifecycle handoff to `WS05`;
- permanent HTTPS/canonical-domain/edge/provider-precedence/staging evidence;
- telemetry, metrics, dashboards, and alert thresholds owned by `WS09`;
- rate limits and abuse controls outside already accepted source-owned owners;
- future source-less discretionary support/admin credit capability;
- Playwright/browser runtime evidence;
- database schema changes or migrations.

## 9. Related Controls And Remaining Evidence

| Control / Decision | What this pass establishes | What remains later |
|---|---|---|
| `API-M09` | Advances source-owned request limits and ownership for opaque provider/payment inputs, checkout return URL shape, retired generic payment/provider writes, payment-event repair fields, and game-credit source-derived eligibility. | Broader ordinary JSON body limits, header/URL size, request-line, external ingress/process/provider/runtime limits, and other request families remain with their owners. |
| `GOV-006` / `FDN-04` | Provides an approved decision record for B2A2B2 numeric/policy values and records those values in the limits register without making the register the approving source. | Provider/runtime thresholds, telemetry/alert thresholds, capacity/cost limits, and future source-less credit values require separate owner decisions and evidence. |
| `PAY-004` | Preserves same-app checkout return URL validation and prevents generic payment-route writes from becoming payment lifecycle authority. | Provider confirmation behavior, webhook ordering, entitlement correctness, payment lifecycle, reconciliation, and runtime evidence remain WS05/later-owner work. |
| `PAY-005` | Preserves signed webhook processing as the owner of provider payment-event creation and prevents generic request bodies or repair requests from authoring raw provider event identity or payloads. | Stripe endpoint dashboard evidence, signature retry behavior, provider delivery timing, and deployed webhook runtime evidence remain WS05/later-owner work. |
| `PAY-006` | Preserves local source boundaries for payment-event processing and narrow repair without claiming complete event ordering, missing-event recovery, stale-event handling, or provider-state reconciliation. | Duplicate, stale, delayed, missing, out-of-order, and provider-current-state recovery evidence remains WS05/later-owner work. |
| `PAY-008` | Preserves SetupIntent sync as opaque provider input with provider-backed service validation. | Stripe dashboard, live provider, saved-card lifecycle, and deployed provider evidence remain WS05/later-owner work. |
| `PAY-009` | Keeps generic refund writes retired so refund behavior stays with supported refund, retry, reconcile, and later payment/provider workflows. | Refund lifecycle, provider synchronization, scheduled reconciliation, runtime success/failure/processing/unknown cases, and provider dashboard proof remain WS05/later-owner work. |
| `PAY-010` | Preserves and tightens source-derived game-credit issuance and reversal bounds for current generic admin credit routes. | Full refund/credit lifecycle, ledger concurrency, provider reconciliation, durable workflow evidence, and any future source-less discretionary credit feature remain later-owner work. |
| `WS04` | Leaves genuine database concurrency and financial-credit race closure outside B2A2B2 local serial service evidence. | Transaction, locking, race, and concurrent credit ledger proof remains WS04/database-owned with WS05 payment lifecycle handoff. |
| `WS09` | Leaves telemetry, metrics, dashboards, and alert thresholds outside B2A2B2 local source evidence. | Observability pipelines, dashboard evidence, alert thresholds, and operational telemetry remain WS09-owned. |

### Supporting Relationships

- `EN-01` supplies the trusted testing architecture, requirement declaration
  model, checker, and traceability expectations.
- `EN-02` supplies safe observability, redaction, and public-error foundations.
- `EN-03` supplies the secret/control-plane/provider-evidence boundary that
  keeps inbox token secret proof separate from local token-shape tests.
- `WS02-04B2A2B1` preserves the route-lifecycle tombstone pattern B2A2B2 relies
  on for generic payment/refund/payment-event mutation retirement.
- `WS02-04B2A2A` owns unrelated active request-schema bounds and must not be
  used as authority for B2A2B2-specific operational text values.

## 10. Completion Criteria

- [ ] The B2A2B2 decision record exists and approves the exact source-owned
  values and policy rules used by the pass.
- [ ] The limits and thresholds register records only B2A2B2 values that belong
  there and clearly states the decision record is the approving source.
- [ ] The stale non-production payment-event seed-script guidance no longer
  advertises retired generic `POST /payment-events` creation or raw provider
  payload authoring as an active manual workflow.
- [ ] The approved production game-credit service correction rejects unlinked
  source payments as monetary eligibility and preserves valid booking-only and
  properly linked payment flows.
- [ ] Payment and booking references that resolve to the same underlying
  booking/payment source share one remaining eligibility budget, with reversed
  prior credits still excluded.
- [ ] `backend/tests/support/requirements/ws02_04b2a2b2.json` exists with the
  exact frozen IDs, states, scopes, `source_controls`, and deferred reason in
  this plan.
- [ ] `backend/tests/workflows/provider_payment_input_ownership/TESTING_RECORD.md`
  exists and honestly records risks, evidence quality, proof layers, and
  remaining provider/runtime gaps.
- [ ] Trusted B2A2B2 tests exist in
  `backend/tests/workflows/provider_payment_input_ownership` and map to every
  required B2A2B2 requirement.
- [ ] Deferred `WS02-04B2A2B2-R8` has zero pytest mappings and a required
  governance reason.
- [ ] Focused B2A2B2 pytest validation passes.
- [ ] Required adjacent workflow/platform regressions pass.
- [ ] The previously failing workflow-to-runtime test order passes after the
  shared root `client` fixture is made function-scoped.
- [ ] EN-01 checker/foundation tests pass.
- [ ] Checker domain scopes for B2A2B2, adjacent workflow roots, request body
  limits, and secrets pass.
- [ ] Checker suite scope passes.
- [ ] Requirement traceability is complete for required B2A2B2 requirements.
- [ ] No current production frontend caller uses retired generic
  payment/refund/payment-event mutation routes.
- [ ] `git diff --check` passes.
- [ ] No production application code outside
  `backend/services/game_credit_admin_service.py`, no test code outside the
  approved `backend/tests/conftest.py` isolation correction and B2A2B2 trusted
  evidence files, and no frontend code, migrations, provider configuration,
  unrelated docs, or unrelated tests were changed.
- [ ] No real provider payloads, production credentials, production tokens,
  production database URLs, private keys, or real user/payment/provider data
  were introduced.
- [ ] B2A2B2 boundaries remain intact and no unresolved blocker remains.
