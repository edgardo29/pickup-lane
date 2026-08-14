# WS02-04B2A2A - Active Request Schema Bounds

## At A Glance

| Field | Value |
|---|---|
| Pass | `WS02-04B2A2A` |
| Track | `WS02` |
| Type | API request-schema and source-owned service-boundary recheck |
| Primary controls | `API-M09`, `GOV-006` |
| Policy / rule authority | `docs/production-readiness/decisions/ws02-04b2a2a-active-request-rules-approved.md`, `FDN-04`, `GOV-006`, and relevant accepted cross-pass ownership records |
| Implementation truth | Current accepted repository source and current supported callers |
| Depends on | EN-01, EN-02, WS02-04A, WS02-04B1, WS02-04B2A1, WS02-04B2A2B1/B2/B3, WS02-04B2A2C, WS02-05A/B1/B2, WS03-01 |
| Trusted test scope | `backend/tests/workflows/active_request_schema_bounds` |

WS02-04B2A2A owns the active workflow request-field bounds and narrow
source-owned dynamic service checks approved in the A2A owner decision. It does
not own whole-request byte limits, product collection limits, provider/payment
lifecycle, storage safety, response minimization, media-type behavior, or
identity authority.

## 1. Purpose

This pass makes Pickup Lane's active request bodies honest and bounded where
the repository source can enforce that boundary directly. It covers current
Pydantic request schemas and the small set of service checks where a request
value must be compared with server-owned state.

The pass answers:

- which active request-field values are approved A2A source policy;
- which current schema rules are inherited from or owned by other passes;
- which production behavior is already correct and must remain unchanged;
- which fresh trusted evidence is required under the EN-01 architecture.

The pass does not redesign the product API, select new limits, change current
frontend callers, or broaden historical scope.

## 2. Why This Matters

Unbounded or ambiguous request fields can let oversized text, unsupported
literal values, impossible game capacities, unsupported party sizes, arbitrary
payment-display data, or excessive admin-money amounts reach service, database,
or provider-adjacent code. The opposite failure is also risky: a local
request-schema pass can falsely claim broader provider, storage, response,
runtime, or concurrency readiness.

WS02-04B2A2A keeps those concerns separate. It proves the source-owned request
guards that are real today and records handoffs for later owners where local
tests cannot honestly close the risk.

## 3. Requirements

| ID | Requirement | What it means | Why it matters |
|---|---|---|---|
| `WS02-04B2A2A-R1` | Profile, settings, and account-delete requests use approved active bounds. | Profile update text, settings locality text, settings location-permission status, and self-delete confirmation must follow the exact A2A-approved schema rules. Profile email, verifier-controlled fields, provider identity, role, account state, and profile photo URL remain WS03-owned. | Prevents ordinary account/profile requests from carrying oversized or unauthorized state while preserving the identity authority split. |
| `WS02-04B2A2A-R2` | Game, guest, cancellation, consent, and price request values stay within approved A2A bounds. | Active game/community/admin create/edit, join, checkout, booking guest add, host guest add, guest removal, game cancellation, consent-version, and Need-a-Sub price fields must enforce the approved source bounds. | Prevents impossible capacity, unsupported party-size, unbounded cents, no-op guest mutations, and oversized cancellation/consent text before workflow or payment work. |
| `WS02-04B2A2A-R3` | Community payment snapshot requests remain small, typed, and duplicate-safe. | Community payment method snapshots must keep the approved count, type set, value trimming/min/max, duplicate-type rejection, and absent/null instructions behavior. | Prevents arbitrary or oversized community payment display data from becoming persisted request state. |
| `WS02-04B2A2A-R4` | Admin workflow request literals and operational text are bounded. | A2A-owned admin official-game, admin-money, review-case, and support-flag request literals and reason/note text must follow the approved current schemas. | Prevents arbitrary admin outcome classes and oversized operational text from reaching audit, review, support, or financial workflow code. |
| `WS02-04B2A2A-R5` | Venue-image request metadata has approved request-shape bounds only. | Venue-image request role/status literals and `sort_order` must follow the A2A-approved schema rules. | Keeps admin venue-image metadata finite without claiming storage publication or file-safety readiness. |
| `WS02-04B2A2A-R6` | Admin-money client amounts cannot exceed server-owned eligibility. | `amount_cents` must be non-negative; a supplied amount must not exceed the eligible server-calculated target; without an eligible positive target, positive client amount rejects. | Prevents request input from creating source-less or excessive financial outcomes. |
| `WS02-04B2A2A-R7` | Later-pass ownership remains explicit and is not pulled back into A2A. | B1, B2A1, B2A2B, B2A2C, WS02-05, WS03, WS04, WS05, and WS06-owned behavior must remain inherited, deferred, or outside scope as appropriate. | Prevents this source pass from falsely closing product collection, transport, provider, storage, identity, response, database, or runtime controls. |

## 4. Technical Design / Contracts

### 4.1 Authority Classes

Every current request rule is classified before evidence is written:

| Class | Meaning | A2A treatment |
|---|---|---|
| A2A-approved source rule | The exact current rule is listed in `ws02-04b2a2a-active-request-rules-approved.md`. | Preserve and test it in implementation evidence. |
| Later-pass owned rule | A later accepted pass owns the behavior even if the current schema or route still contains it. | Do not claim it as A2A evidence. Reference the owner only where needed for boundaries. |
| Current implementation only | Source contains a rule, but A2A authority does not select it as current pass policy. | Do not turn it into an A2A requirement. |
| External/provider/runtime evidence | The fact cannot be proven honestly by local repository tests. | Record a handoff; do not fake proof. |

The exhaustive approved A2A rule table lives in the decision record. The
planning summary below groups those rules by behavior so implementation
evidence can stay focused without copying the decision record into tests.

### 4.2 Profile, Settings, And Account Delete

A2A owns only current active request bounds for:

- `UserUpdate.phone` max 30;
- `UserUpdate.first_name` and `last_name` max 100;
- `UserUpdate.home_city` and `home_state` max 120;
- `UserSettingsUpdate.location_permission_status` literal set:
  `unknown`, `allowed`, `denied`, `skipped`;
- `UserSettingsUpdate.selected_city` and `selected_state` max 120;
- `AuthDeleteAccountRequest.confirmation` must equal `DELETE` after trimming,
  case-insensitively.

Unknown fields reject through the current request model configuration.
Ordinary profile email mutation, `email_verified_at`, provider UID, role,
account state, admin authority, provider timestamps, and profile-photo URL are
not A2A. WS03-01 owns those identity and verifier-controlled boundaries.

### 4.3 Game, Guest, And Price Requests

A2A owns these active request-field bounds:

- `total_spots` 6 through 99 where exposed on active game/community/admin
  create and update schemas;
- `price_per_player_cents` 0 through 99,900 where exposed on active
  game/community/admin create and update schemas;
- `max_guests_per_booking` 0 through 2 where exposed on active game/admin
  create and update schemas;
- player join and checkout `guest_count` 0 through 2;
- booking guest-add `guest_count` 1 through 2;
- host guest-add `guest_count` at least 1, with no A2A-approved upper bound;
- guest `remove_count` at least 1;
- ordinary game `cancel_reason` max 500;
- join `auto_charge_consent_version` max 50;
- Need-a-Sub `price_due_at_venue_cents` 0 through 99,900.

These are static request-schema bounds. They do not prove capacity
serialization, oversell prevention, payment totals, refunds, provider behavior,
or database-concurrency invariants.

`host_guest_max` is no longer an A2A request-owned field. WS02-05B1 removed it
from generic game requests and current active host/admin request schemas do not
expose it as an A2A field.

### 4.4 Community Payment Snapshots

A2A owns the current active community payment snapshot request shape:

- at most 2 payment-method snapshot entries;
- method type literal set: `venmo`, `zelle`, `cash_app`, `paypal`,
  `apple_cash`, `cash`, `other`;
- method value is a strict string, trimmed before validation, min 1 and max 255;
- duplicate method types reject;
- `payment_instructions_snapshot` must be absent or JSON null.

These rules protect bounded community payment display data only. They do not
prove provider payment behavior, saved-card lifecycle, moderation workflow, or
payment settlement.

### 4.5 Admin Requests

A2A owns current request literals and operational text bounds for these active
admin surfaces:

- admin official-game operational reason fields approved at max 1000 where
  exposed on create/update, host assignment/removal execution, player add, and
  player removal execution;
- admin official-game player-removal outcome literal set;
- admin-money financial outcome literal set;
- admin-money reason min 3/max 1000 and internal note max 1000;
- admin-review close outcome literal set;
- admin-review close reason min 1/max 1000 and note body max 1000;
- support-flag resolve outcome literal set;
- support-flag resolve reason min 1/max 1000.

Admin user action schemas, admin community enforcement schemas, admin
Need-a-Sub enforcement schemas, game-credit request ownership, idempotency
policy, provider mutations, and broader moderation lifecycle are not approved
merely because they are current body-bearing routes. They remain outside A2A
unless a listed A2A rule directly applies.

### 4.6 Admin-Money Dynamic Safeguards

Static schema validation rejects negative `amount_cents`.

Service validation must also preserve the current source behavior:

- when a host publish fee is supplied, the requested amount cannot exceed the
  host publish fee amount;
- when no eligible positive target exists, a positive client-supplied amount
  rejects;
- these rejections must occur before a prohibited financial outcome is
  persisted.

Trusted evidence may use PostgreSQL-backed service tests for these dynamic
state-dependent checks. It must not contact Stripe or treat provider state as
proven.

### 4.7 Venue Image Request Metadata

A2A owns only request-shape metadata bounds:

- upload/update `image_role` is `card` or `gallery`;
- update `image_status` is `pending_upload`, `active`, `hidden`, or `removed`;
- upload/update `sort_order` is 0 through 2.

B1 owns selected-photo product count. WS06 owns final file byte/type/pixel
policy, content validation, image processing, safe publication, R2 lifecycle,
cleanup, and provider/runtime evidence.

### 4.8 Later-Owned Boundaries

A2A must not reclaim:

- B1 product and collection limits, including Platform Notice boundaries, Need
  a Sub collection limits, saved-card count, chat content/list/history, and
  selected venue-photo count;
- B2A1 and B2A2C whole-request body byte limits;
- B2A2B1/B2/B3 retired, provider/payment, inbox, checkout URL, game-credit,
  policy/legal, and acceptance request ownership;
- WS02-05A media type, OpenAPI, cache, and HTTP representation;
- WS02-05B1 request ownership and over-posting cleanup;
- WS02-05B2 response minimization;
- WS03 identity/profile authority;
- WS05 payment/provider lifecycle;
- WS06 storage/provider behavior.

## 5. Implementation Scope

Production/schema/service/frontend corrections:

- None. The owner decision approves preserving the current A2A-owned behavior,
  and current source already matches the approved rules.

Pass-owned governance artifacts:

- `docs/production-readiness/decisions/ws02-04b2a2a-active-request-rules-approved.md`
- `docs/production-readiness/governance/limits-and-thresholds-register.md`
- `docs/production-readiness/planning/ws02-04b2a2a-active-workflow-schema-bounds.md`

The editable evidence set for implementation is limited to:

- `backend/tests/support/requirements/ws02_04b2a2a.json`
- `backend/tests/workflows/active_request_schema_bounds/TESTING_RECORD.md`
- `backend/tests/workflows/active_request_schema_bounds/test_profile_settings_account_bounds.py`
- `backend/tests/workflows/active_request_schema_bounds/test_game_request_schema_bounds.py`
- `backend/tests/workflows/active_request_schema_bounds/test_community_payment_schema_bounds.py`
- `backend/tests/workflows/active_request_schema_bounds/test_admin_request_schema_bounds.py`
- `backend/tests/workflows/active_request_schema_bounds/test_venue_image_schema_bounds.py`
- `backend/tests/workflows/active_request_schema_bounds/test_admin_money_dynamic_bounds.py`

Implementation must not modify production source, frontend source, migrations,
provider configuration, CI, unrelated docs, or later-pass artifacts unless a
new design review expands the approved scope.

## 6. Testing And Evidence

Trusted evidence belongs under
`backend/tests/workflows/active_request_schema_bounds/`, a trusted EN-01
workflow scope.

Requirement declarations belong in:

`backend/tests/support/requirements/ws02_04b2a2a.json`

Testing record belongs in:

`backend/tests/workflows/active_request_schema_bounds/TESTING_RECORD.md`

### 6.1 Requirement Declaration Design

The requirement declaration must be created at:

`backend/tests/support/requirements/ws02_04b2a2a.json`

The exact metadata is:

| ID | state | scope | source_controls | reason |
|---|---|---|---|---|
| `WS02-04B2A2A-R1` | `required` | `workflows/active_request_schema_bounds` | `["API-M09", "GOV-006", "FDN-04", "WS02-04B2A2A", "WS03-01"]` | Not required. |
| `WS02-04B2A2A-R2` | `required` | `workflows/active_request_schema_bounds` | `["API-M09", "GOV-006", "FDN-04", "WS02-04B2A2A"]` | Not required. |
| `WS02-04B2A2A-R3` | `required` | `workflows/active_request_schema_bounds` | `["API-M09", "GOV-006", "FDN-04", "WS02-04B2A2A"]` | Not required. |
| `WS02-04B2A2A-R4` | `required` | `workflows/active_request_schema_bounds` | `["API-M09", "GOV-006", "FDN-04", "WS02-04B2A2A"]` | Not required. |
| `WS02-04B2A2A-R5` | `required` | `workflows/active_request_schema_bounds` | `["API-M09", "GOV-006", "FDN-04", "WS02-04B2A2A", "WS06"]` | Not required. |
| `WS02-04B2A2A-R6` | `required` | `workflows/active_request_schema_bounds` | `["API-M09", "GOV-006", "FDN-04", "WS02-04B2A2A", "WS05"]` | Not required. |
| `WS02-04B2A2A-R7` | `deferred` | `governance` | `["API-M09", "API-M10", "API-M11", "API-M12", "API-M13", "API-M14", "API-M16", "API-M18", "API-M19", "GOV-006", "DB-005", "DB-006", "DB-007", "DB-013", "PAY-008", "STO-005", "STO-006", "STO-009", "DBP-03", "DBP-04", "WS02-04B1", "WS02-04B2A1", "WS02-04B2A2B1", "WS02-04B2A2B2", "WS02-04B2A2B3", "WS02-04B2A2C", "WS02-05A", "WS02-05B1", "WS02-05B2", "WS03-01", "WS04", "WS05", "WS06"]` | B1 product and collection limits, whole-request body limits, retired/provider/payment/policy request ownership, HTTP/media/OpenAPI/cache behavior, writable-field/request-ownership boundaries, response minimization, identity/profile authority, payment/provider lifecycle, storage/provider behavior, database concurrency, and external runtime evidence remain with their later owners and cannot be closed by local A2A request-schema tests. |

`WS02-04B2A2A-R7` must have no pytest mapping.

Proof layers:

- Pydantic/schema tests for static field bounds, literal sets, trimming,
  duplicates, omitted/null behavior, create/update differences, and unknown
  field rejection.
- Service tests for admin-money dynamic amount eligibility and no prohibited
  persisted financial outcome.
- PostgreSQL only for the admin-money dynamic service checks where persisted
  source state is needed.
- Source review in the testing record for current frontend caller
  compatibility and cross-pass handoffs.

Unknown-field rejection evidence may prove only that the included A2A request
schemas reject unexpected keys through their current request model
configuration. It must not claim ownership over which business fields are
client-writable, later field-removal or mass-assignment policy, or WS02-05B1
and WS03-owned field authority.

Not required for A2A evidence:

- provider or live network access;
- Playwright/browser tests;
- migration proof;
- genuine concurrency proof;
- controlled-time proof.

Tests may use ordinary deterministic fixture values or timestamps as setup
data. That setup does not create a controlled-time proof layer or expand the
implementation scope.

The evidence must not duplicate B1, B2A1, B2A2C, WS02-05, WS03, WS05, or WS06
tests simply to inflate coverage.

## 7. Integration / Operational Expectations

A2A relies on:

- EN-01 trusted test taxonomy, requirement metadata, generated traceability,
  and checker scope policy;
- EN-02 safe error, redaction, event, and telemetry primitives where errors or
  logs are observed;
- WS02-04A stable validation and public error behavior;
- B1, B2A1, B2A2B, B2A2C, WS02-05, WS03, WS05, and WS06 ownership records for
  non-A2A behavior.

The pass must preserve current supported frontend callers. If a future
correction requires caller changes, a new design review must decide whether
A2A or a later compatibility owner should make that change.

## 8. Not Part Of This Pass

WS02-04B2A2A does not implement or prove:

- broad request-body, multipart, header, URL, edge, provider, process-server,
  or runtime limits;
- B1 product/collection limits;
- provider/payment lifecycle, Stripe dashboard state, retries,
  reconciliation, or cleanup;
- storage content safety, actual file validation, image processing, safe
  publication, R2 lifecycle, or provider metadata reliability;
- database-enforced capacity, participation, cursor, financial, or storage
  concurrency invariants;
- media-type policy, OpenAPI, cache, tombstone representation, response
  minimization, or public/internal API versioning;
- identity provider authority, verified-email policy, profile email mutation,
  role/account/admin fields, or profile-photo ownership;
- frontend browser behavior, Playwright evidence, deployment evidence,
  telemetry dashboards, alert thresholds, provider evidence, or permanent-host
  evidence;
- unrelated current request schema constraints not listed in the owner
  decision.

## 9. Related Controls And Remaining Evidence

A2A advances:

- `API-M09` for approved active request-field/schema bounds and the
  source-owned admin-money dynamic amount guard.
- `GOV-006` and `FDN-04` through the pass-specific owner decision and limits
  register reconciliation.

A2A depends on but does not close:

- B1 for Platform Notice, Need a Sub collection, saved-card, chat, pagination,
  and selected venue-photo product/source boundaries;
- B2A1 and B2A2C for whole-request body byte limits;
- B2A2B1/B2/B3 for retired routes, provider/payment/inbox/checkout URL,
  game-credit, policy/legal, and acceptance request ownership;
- WS02-05A/B1/B2 for HTTP/media/OpenAPI/cache, request ownership, and response
  minimization;
- WS03 for identity/profile authority and verifier-controlled fields;
- WS05 for payment/provider lifecycle and financial provider evidence;
- WS06 for image/storage provider safety;
- WS04 and later database work for deterministic concurrency and persisted
  invariant closure.

Provider/runtime/staging/deployment owners must provide sanitized evidence for
facts not provable from local source.

## 10. Completion Criteria

- [ ] `backend/tests/support/requirements/ws02_04b2a2a.json` declares the final
  A2A requirements with stable IDs, states, scopes, `source_controls`, and a
  truthful reason for deferred ownership handoffs.
- [ ] Profile, settings, and account-delete request bounds are proven without
  reclaiming WS03-owned identity/profile authority.
- [ ] Game, guest, cancellation, consent-version, and pricing request bounds
  are proven without claiming capacity serialization, payment/provider
  lifecycle, or database concurrency closure.
- [ ] Community payment snapshot count, literal, value trimming/min/max,
  duplicate rejection, null instructions, and unknown-field behavior are
  proven.
- [ ] Admin official-game, admin-money, admin-review, and support request
  literals/text bounds are proven only for the A2A-owned fields listed in the
  decision record.
- [ ] Admin-money dynamic target checks are proven with source-owned database
  state and no prohibited financial outcome persistence.
- [ ] Venue-image role/status/sort-order request metadata bounds are proven
  without claiming selected-photo count, file safety, R2, or storage provider
  readiness.
- [ ] `backend/tests/workflows/active_request_schema_bounds/TESTING_RECORD.md`
  records scenario selection, proof layers, caller compatibility, side-effect
  boundaries, inherited/later ownership, and evidence adequacy.
- [ ] Checker domain scope for
  `backend/tests/workflows/active_request_schema_bounds`, checker suite scope,
  relevant pytest, requirement traceability, and `git diff --check`.
- [ ] No provider/network, Playwright, migration, genuine-concurrency,
  historical/pre-reset evidence, production-data, or provider-secret evidence
  is used to close A2A.
