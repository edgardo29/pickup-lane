# WS02-05B1 - Request Ownership And Mass-Assignment Cleanup

## At A Glance

| Field | Value |
|---|---|
| Pass | `WS02-05B1` |
| Track | `WS02` |
| Type | API request-ownership / mass-assignment evidence reconstruction |
| Primary controls | `API-M14`, `IAM-014` |
| Supporting controls | `API-M09`, `API-M13`, `API-M18`, `GOV-006`, `PAY-008`, `PAY-009`, `PAY-010`, `DB-005`, `DB-006`, `STO-005`, `STO-006` |
| Gate A accepted baseline | `def991aed72927d58b5247463f7f84882351012e` |
| Historical PR provenance | PR `#124`, merge `6825e84`, head `eac0f5855d3f1a73343f10f5dc910a85aebd07d9`, baseline parent `f2a313aab194bd982aca55344ea5b7e578be2e82` |
| Depends on | `EN-01`; `WS02-04B1`; `WS02-04B2A1`; `WS02-04B2A2A`; `WS02-04B2A2B1`; `WS02-04B2A2B2`; `WS02-04B2A2B3`; `WS02-04B2A2C`; `WS02-05A`; accepted `WS02-05B2` and `WS03-01` boundaries |
| Trusted test scope | `backend/tests/workflows/request_ownership` |
| Production correction set | None approved |
| Frontend correction set | None approved |
| Gate B evidence type | Requirement declaration, testing record, focused trusted backend tests, generated OpenAPI/request-schema inspection, source/caller inventory, PostgreSQL-backed API behavior |
| Gate B test-infrastructure correction | `backend/tests/conftest.py` shared TestClient/global app isolation only |

## 1. Purpose

WS02-05B1 proves that game write requests cannot mass-assign server-owned game
state through generic or adjacent game mutation surfaces.

In plain English: callers may send the fields that a workflow truly owns, but
they must not be able to smuggle identity, lifecycle, venue snapshots, payment
mode, policy mode, provider IDs, audit timestamps, or administrative status into
persisted game rows. Those values must come from the authenticated actor,
selected server workflow, existing database rows, provider-owned workflows, or
dedicated admin actions.

The current accepted source already contains the narrowed generic game request
schemas and service derivation. Gate B is therefore an evidence reconstruction
pass unless a human reopens the production correction set.

## 2. Why This Matters

`API-M14` requires separate request, internal, public, and administrative
contracts. `IAM-014` requires field-level authorization and explicit mapping so
callers cannot assign roles, ownership, account state, payment state, provider
IDs, timestamps, or administrative fields.

Game rows are a high-risk request-ownership surface because the persisted model
contains many fields that should not be caller-authored:

- ownership and identity fields such as `created_by_user_id`, cancellation
  actors, completion actors, and most host assignment paths;
- lifecycle and visibility state such as `publish_status`, `game_status`,
  `public_visibility_status`, `join_enforcement_status`, `published_at`,
  `cancelled_at`, `completed_at`, `cancellation_source`, and `cancel_reason`;
- venue snapshot fields that should be copied from approved venue data or
  workflow-specific host/admin location handling;
- payment, policy, and invariant fields such as `payment_collection_type`,
  `currency`, `sport_type`, `policy_mode`, `minimum_age`, `host_guest_max`, and
  `custom_cancellation_text`;
- provider/payment-adjacent values that are owned by checkout, payment, refund,
  saved-card, webhook, and admin-money workflows.

B1 keeps those values out of broad request bodies and proves the remaining
specialized mutation paths are not generic bypasses.

## 3. Gate A Reconciliation Findings

### Current Source Truth

The Gate A baseline is current accepted `develop` at
`def991aed72927d58b5247463f7f84882351012e`. Current accepted `develop` is
repository truth for the current implementation state. Authoritative
production-readiness sources and this reconciled/frozen plan define what must
be true for Gate B. Historical PR `#124` remains provenance only.

Current generic game routes:

- `POST /games` is admin-only and accepts `GameCreate`.
- `PATCH /games/{game_id}` is admin-only and accepts `GameUpdate`.
- Current frontend product flows do not call generic `POST /games` or generic
  `PATCH /games/{game_id}`. Community create/edit and official admin create/edit
  use dedicated endpoints.

Current generic request schemas:

- `GameCreate` uses `extra="forbid"` and allows only the generic admin create
  inputs: `game_type`, `title`, `description`, `venue_id`, optional community
  `host_user_id`, schedule/timezone, format/group/skill/environment, capacity,
  price, guest flags, waitlist/chat flags, `custom_rules_text`, `game_notes`,
  and `parking_notes`.
- `GameUpdate` uses `extra="forbid"` and allows only partial generic admin edit
  inputs: title/description, schedule/timezone, format/group/skill/environment,
  capacity, price, guest flags, waitlist/chat flags, `custom_rules_text`,
  `game_notes`, and `parking_notes`.
- The schemas exclude identity, lifecycle, payment mode, visibility,
  enforcement, snapshots, sport, currency, policy, official forced fields,
  cancellation/completion actor fields, and timestamp fields.

Current generic service behavior:

- `build_game_create_data` maps a `GameCreate` request into an explicit game
  data dictionary and derives protected fields from the admin actor, venue row,
  selected game type, fixed product rules, and lifecycle normalization.
- Generic create validates referenced venue and any community host reference,
  applies official invariants, normalizes lifecycle fields, validates business
  rules, and persists `Game(id=uuid.uuid4(), **normalized_game_data)`.
- Generic update starts from `GameUpdate.model_dump(exclude_unset=True)`,
  rejects official location/host changes, requires the game not to have started,
  computes an effective full-game validation shape from the existing row plus
  allowed updates, normalizes lifecycle and official invariants, then applies
  only request-owned fields plus service-derived `starts_on_local`,
  lifecycle-maintenance fields, and `host_guest_max`/official forced fields when
  applicable.

Current specialized game mutation paths:

- Community publish uses `CommunityGamePublishCreate`, verified host identity,
  explicit `build_game_data`, server-owned lifecycle defaults, venue handling,
  and payment-owned publish-fee behavior.
- Community host edit uses `GameHostEdit`, verified host identity, ownership and
  pre-start checks, restricted host-editable fields, and server-owned protected
  field preservation.
- Admin official game create/update use `AdminOfficialGameCreate` and
  `AdminOfficialGameUpdate`, active admin identity, explicit official data
  derivation, and dedicated official host/cancel/player action schemas.
- Generic user mutations are disabled, `/users/me` exposes a narrow profile
  update schema, payment/provider inputs are owned by WS02-04B2A2B2 and WS05,
  policy/legal write retirement is owned by WS02-04B2A2B3, body sizes are owned
  by WS02-04B2A1/A2C, HTTP/OpenAPI/cache/tombstone representation is owned by
  WS02-05A, and response minimization is owned by WS02-05B2.

### Historical PR Provenance

Historical PR `#124` merged as `6825e84` from head
`eac0f5855d3f1a73343f10f5dc910a85aebd07d9`. Its production intent was to narrow
generic game create/update request schemas, pass the active admin to generic
game create, and derive protected game fields in the service.

The historical PR also changed prior-generation backend test helpers and shared
test files. Those files are provenance only. They are not current EN-01 trusted
B1 evidence and must not be used as authority for Gate B requirements.

### Later Accepted Changes

After historical B1, accepted work changed relevant boundaries:

- `WS02-05B2` added audience-specific response minimization, including
  `GameDetailRead` and `SelfUserRead`; response minimization stays out of B1.
- `WS03-01` tightened identity/profile authority, including generic user
  mutation retirement and narrower `UserUpdate`; profile/account authority stays
  with WS03.
- `WS02-04B2A2A` owns active request-field numeric bounds and unknown-field
  rejection for its approved active request families; B1 owns whether a field is
  writable at all for generic game request ownership.
- `WS02-04B2A2B1`, `WS02-04B2A2B2`, `WS02-04B2A2B3`, and `WS02-04B2A2C` already
  froze route-lifecycle, provider/payment input, policy/legal, and ordinary JSON
  body-size ownership boundaries that B1 must not re-open.

### Gate B Test-Isolation Scope Correction

Gate B focused B1 evidence passed, but the required full backend regression
exposed an order-dependent test-process isolation failure in the current suite:
`backend/tests/platform/chat_rate_limits/test_chat_rate_limit_error_contract.py::test_real_chat_rate_limit_rejection_uses_safe_429_contract`
fails after an earlier platform API-error test imports `backend.main` while
CORS settings are monkeypatched.

The failure is independently reproducible without B1 when
`backend/tests/platform/api_errors/test_correlation_and_safe_headers_contract.py::test_valid_incoming_request_id_is_accepted_and_mirrored`
runs before the chat-rate-limit test. The earlier test's `_create_app`
temporarily sets `CORS_ALLOWED_ORIGINS=https://app.example.invalid`, resets the
settings cache, and imports `backend.main`. If that is the first import in the
test process, `backend.main.app = create_app()` is built with the temporary
origin. Pytest restores the environment after the test, but the module-level
FastAPI app remains configured with the temporary CORS allowlist.

The later chat-rate-limit test uses the shared root `client` fixture, which
imports `backend.main.app`. If that cached app was created under the temporary
origin, the request from `Origin: http://localhost:5173` is no longer an allowed
CORS origin, so Starlette correctly omits `Access-Control-Allow-Origin` and the
chat test fails its current platform contract assertion.

This is a trusted backend test-process isolation defect only. It does not
change production behavior: production imports `backend.main` once under the
real runtime environment, not under a pytest monkeypatch. B1 exposed the defect
because the approved Gate B validation requires a full backend regression after
adding B1 trusted evidence; B1 does not cause the leak and does not own the
chat-rate-limit behavior.

The minimum correction owner is `backend/tests/conftest.py`. The root shared
fixture layer owns broadly shared `TestClient` acquisition, database cleanup,
network safety, and FastAPI dependency override cleanup. The correction must
ensure the shared `client` fixture cannot reuse a module-level `backend.main.app`
that was created under another test's temporary settings. Fixing only the
earlier platform test would leave the same order-dependent class open for other
current temporary-settings app-construction tests. Changing the chat test would
hide a shared fixture isolation defect. Changing production `backend/main.py`
would be outside this test-only correction.

## 4. Requirements

| ID | Requirement | What it means | Evidence state |
|---|---|---|---|
| `WS02-05B1-R1` | Generic game create exposes only caller-owned request fields and rejects protected over-posting. | `GameCreate`, `POST /games`, and generated OpenAPI must omit protected identity, lifecycle, payment, policy, provider, venue snapshot, invariant, cancellation/completion, and timestamp fields. Unknown/protected submitted fields fail before game persistence. | required |
| `WS02-05B1-R2` | Generic game create derives protected persisted fields from trusted sources. | Persisted generic-created games derive actor, venue snapshots, lifecycle/status/visibility/enforcement, payment collection, sport, currency, policy, official invariants, local date, and timestamps from server workflow, not the request body. | required |
| `WS02-05B1-R3` | Generic game update exposes only generic admin-editable fields and rejects protected over-posting. | `GameUpdate`, `PATCH /games/{game_id}`, and generated OpenAPI must omit protected persisted fields. Unknown/protected submitted fields fail before mutation. | required |
| `WS02-05B1-R4` | Generic game update preserves protected fields and applies only allowed or service-derived changes. | Successful generic updates may mutate allowed fields plus service-derived `starts_on_local`, lifecycle-maintenance fields, `host_guest_max` for format changes, and official forced fields. Rejected over-posting leaves existing protected persisted values unchanged. | required |
| `WS02-05B1-R5` | Specialized game mutation paths are dedicated authorities, not generic bypasses. | Community publish, community host edit, admin official create/update, official host assignment/removal, official cancellation/player actions, game join/leave/guest/cancel, community detail, and admin community enforcement each keep purpose-specific schemas and actor checks instead of broad game-row request bodies. | required |
| `WS02-05B1-R6` | Current caller and source negative space remains compatible and traceable. | Current frontend callers use dedicated routes, no current trusted helper/support file requires removed generic game fields, generated request schemas match the narrowed contract, and source inventory has no request-shaped generic game ORM write that bypasses B1 mapping. | required |
| `WS02-05B1-R7` | Later-owner and external-evidence boundaries remain explicit. | B1 does not close response minimization, HTTP media/cache/tombstone representation, ordinary body limits, identity/account authority, provider/payment/refund correctness, storage/provider proof, DB race/concurrency proof, deployed/runtime evidence, or legal/privacy review. | deferred |

### Requirement Declaration Metadata

Gate B must create `backend/tests/support/requirements/ws02_05b1.json` with
exactly these declaration states and scopes:

```json
{
  "schema_version": 1,
  "requirements": [
    {
      "id": "WS02-05B1-R1",
      "owning_pass": "WS02-05B1",
      "source_controls": ["API-M14", "IAM-014", "WS02-05B1"],
      "state": "required",
      "scope": "workflows/request_ownership"
    },
    {
      "id": "WS02-05B1-R2",
      "owning_pass": "WS02-05B1",
      "source_controls": ["API-M14", "IAM-014", "WS02-05B1"],
      "state": "required",
      "scope": "workflows/request_ownership"
    },
    {
      "id": "WS02-05B1-R3",
      "owning_pass": "WS02-05B1",
      "source_controls": ["API-M14", "IAM-014", "WS02-05B1"],
      "state": "required",
      "scope": "workflows/request_ownership"
    },
    {
      "id": "WS02-05B1-R4",
      "owning_pass": "WS02-05B1",
      "source_controls": ["API-M14", "IAM-014", "WS02-05B1"],
      "state": "required",
      "scope": "workflows/request_ownership"
    },
    {
      "id": "WS02-05B1-R5",
      "owning_pass": "WS02-05B1",
      "source_controls": [
        "API-M09",
        "API-M14",
        "IAM-014",
        "WS02-04B2A2A",
        "WS02-04B2A2B1",
        "WS02-04B2A2B2",
        "WS02-04B2A2B3",
        "WS02-05B1",
        "WS05"
      ],
      "state": "required",
      "scope": "workflows/request_ownership"
    },
    {
      "id": "WS02-05B1-R6",
      "owning_pass": "WS02-05B1",
      "source_controls": ["API-M14", "IAM-014", "WS02-05A", "WS02-05B1", "WS02-05B2", "WS03-01"],
      "state": "required",
      "scope": "workflows/request_ownership"
    },
    {
      "id": "WS02-05B1-R7",
      "owning_pass": "WS02-05B1",
      "source_controls": [
        "API-M09",
        "API-M13",
        "API-M14",
        "API-M18",
        "API-M19",
        "GOV-006",
        "PAY-008",
        "PAY-009",
        "PAY-010",
        "DB-005",
        "DB-006",
        "STO-005",
        "STO-006",
        "WS02-04B1",
        "WS02-04B2A1",
        "WS02-04B2A2A",
        "WS02-04B2A2B1",
        "WS02-04B2A2B2",
        "WS02-04B2A2B3",
        "WS02-04B2A2C",
        "WS02-05A",
        "WS02-05B1",
        "WS02-05B2",
        "WS03",
        "WS05",
        "WS06",
        "WS08",
        "WS09",
        "WS10"
      ],
      "state": "deferred",
      "scope": "governance",
      "reason": "Response minimization, HTTP media/cache/tombstone representation, ordinary request-body limits, identity/account authority, provider/payment/refund correctness, storage/provider evidence, DB race/concurrency proof, external ingress/runtime/deployment evidence, telemetry/dashboards/alerts, legal/privacy review, and future API versioning remain with their listed owners and cannot be closed by local B1 request-ownership evidence."
    }
  ]
}
```

`WS02-05B1-R1` through `WS02-05B1-R6` require trusted executable evidence.
`WS02-05B1-R7` must remain deferred/governance and must have zero pytest
mappings.

## 5. Technical Design / Contracts

### 5.1 Protected Game Fields

B1-protected fields are not generic game request-owned unless explicitly named
in a dedicated workflow contract:

| Category | Protected fields / examples |
|---|---|
| Identity and actor authority | `created_by_user_id`, cancellation actors, completion actors, generic update `host_user_id`, and official create host assignment |
| Lifecycle and visibility | `publish_status`, `game_status`, `public_visibility_status`, `join_enforcement_status`, `published_at`, `cancelled_at`, `completed_at`, `cancellation_source`, `cancel_reason` |
| Venue snapshots | `venue_name_snapshot`, `address_snapshot`, `city_snapshot`, `state_snapshot`, `neighborhood_snapshot` except dedicated workflow-generated snapshot updates |
| Product invariants | `sport_type`, `currency`, `minimum_age`, `policy_mode`, `host_guest_max`, `custom_cancellation_text` |
| Payment/provider state | `payment_collection_type` and provider/payment/refund IDs or statuses on adjacent payment models |
| Audit and persistence timestamps | `created_at`, `updated_at`, `deleted_at` and analogous system-maintained fields |

### 5.2 Generic Game Create Contract

`POST /games` is an admin-only compatibility surface for generic game creation.
It remains broader than current product UI because it can create either
`official` or `community` rows, but it must not expose the full `Game` row as a
request body.

Allowed request-owned fields:

- game selection and display: `game_type`, `title`, `description`;
- venue reference: `venue_id`;
- community host reference: optional `host_user_id`, ignored for official games
  and validated for community games;
- schedule and classification: `starts_at`, `ends_at`, `timezone`,
  `format_label`, `game_player_group`, `skill_level`, `environment_type`;
- approved numeric and feature flags: `total_spots`,
  `price_per_player_cents`, `allow_guests`, `max_guests_per_booking`,
  `waitlist_enabled`, `is_chat_enabled`;
- community/admin content fields: `custom_rules_text`, `game_notes`,
  `parking_notes`.

Server-derived create fields:

- `created_by_user_id` from the authenticated admin;
- venue snapshots from the active venue row;
- `payment_collection_type` from game type and price;
- `publish_status`, `game_status`, `public_visibility_status`, and
  `join_enforcement_status` from workflow defaults;
- `sport_type="soccer"` and `currency="USD"`;
- `policy_mode`, `minimum_age`, `host_guest_max`, and
  `custom_cancellation_text` from official/community invariant rules;
- `starts_on_local`, `published_at`, cancellation fields, and completion fields
  from lifecycle normalization;
- `id`, `created_at`, `updated_at`, and persistence timestamps from server/DB.

Gate B must prove both negative rejection and positive persistence derivation.
A generated OpenAPI request-schema check is required so the external contract
matches the Pydantic source.

### 5.3 Generic Game Update Contract

`PATCH /games/{game_id}` is an admin-only generic edit surface. It supports only
the fields listed in `GameUpdate`; it is not a game-row patch API.

Allowed request-owned fields:

- `title`, `description`;
- `starts_at`, `ends_at`, `timezone`;
- `format_label`, `game_player_group`, `skill_level`, `environment_type`;
- `total_spots`, `price_per_player_cents`;
- `allow_guests`, `max_guests_per_booking`, `waitlist_enabled`,
  `is_chat_enabled`;
- `custom_rules_text`, `game_notes`, `parking_notes`.

Required update behavior:

- protected submitted keys reject before mutation through `extra="forbid"` and
  generated OpenAPI must omit them;
- allowed updates validate against the effective row plus update data;
- official games keep official forced fields;
- `starts_on_local` is derived from the effective schedule/timezone;
- `host_guest_max` is derived only when a request-owned `format_label` change
  requires it;
- lifecycle-maintenance fields may be re-normalized by service code, but callers
  cannot set them directly;
- rejected over-posting must leave the existing row unchanged.

### 5.4 Specialized Game Mutation Contracts

Dedicated game workflows may expose fields that generic game update does not,
but only through their own actor and purpose boundary.

| Workflow | Contract |
|---|---|
| Community publish | Verified host request uses `CommunityGamePublishCreate`; host identity and venue/game lifecycle fields are server-derived; publish-fee payment behavior stays payment-owned. |
| Community host edit | Verified host request uses `GameHostEdit`; ownership, pre-start, roster, and paid-booking restrictions apply; location changes create/update snapshots only through host-edit logic. |
| Admin official create/update | Active admin request uses `AdminOfficialGameCreate` and `AdminOfficialGameUpdate`; official fields are explicitly derived and official host assignment uses a separate action. |
| Official roster/cancel actions | Dedicated preview/execute/action schemas own host assignment/removal, player add/removal, and cancellation decisions; they are not generic row update contracts. |
| Game join/leave/guest/cancel | Verified-user workflow schemas own roster and host cancellation behavior; payment/credit effects stay with their owning passes. |
| Community details and admin community enforcement | Purpose-specific schemas own community detail text and enforcement actions; they do not make generic game protected fields caller-owned. |

Gate B should use source/static and generated OpenAPI inspection for this
inventory, plus focused API tests only where a material bypass risk needs
runtime proof. B1 must not duplicate the full behavior tests from the adjacent
workflow owners.

### 5.5 Current Caller And OpenAPI Contract

Gate B must prove current callers remain compatible with the narrowed request
contract:

- create/edit community game UI calls `/community-games/publish`,
  `/games/{game_id}/host-edit`, and
  `/community-game-details/games/{game_id}/host-edit`;
- admin official game UI calls `/admin/official-games` and
  `/admin/official-games/{game_id}` plus dedicated official action routes;
- browse/details/checkout callers use read, join, leave, guest, cancel, and
  checkout endpoints rather than generic game create/update;
- no current frontend caller sends generic `POST /games` or generic
  `PATCH /games/{game_id}`.

Generated OpenAPI evidence is required for B1 because request ownership is an
external API contract. The evidence must inspect request schemas only; response
minimization and tombstone representation remain WS02-05B2 and WS02-05A work.

## 6. Implementation Scope

### Current Source Evidence Targets

Gate B may inspect these production files as evidence sources but has no
approval to edit them:

- `backend/routes/game_routes.py`
- `backend/schemas/game_schema.py`
- `backend/services/game_service.py`
- `backend/services/game_rules.py`
- `backend/schemas/community_game_publish_schema.py`
- `backend/services/community_game_publish_service.py`
- `backend/services/community_game_edit_service.py`
- `backend/routes/community_game_publish_routes.py`
- `backend/routes/community_game_detail_routes.py`
- `backend/schemas/admin_official_game_schema.py`
- `backend/routes/admin_official_game_routes.py`
- `backend/services/official_game_service.py`
- `backend/services/official_game_roster_service.py`
- current frontend API payload/caller files under `frontend/src/pages/create-game`,
  `frontend/src/pages/admin/official-games`, and `frontend/src/pages/browse-games`

### Authorized Gate B Editable Set

Gate B may create or edit only these artifacts unless a human reopens the plan:

1. `backend/tests/support/requirements/ws02_05b1.json`
2. `backend/tests/workflows/request_ownership/TESTING_RECORD.md`
3. `backend/tests/workflows/request_ownership/test_game_create_request_ownership_contract.py`
4. `backend/tests/workflows/request_ownership/test_game_update_request_ownership_contract.py`
5. `backend/tests/workflows/request_ownership/test_game_specialized_mutation_authority_contract.py`
6. `backend/tests/workflows/request_ownership/test_game_request_negative_space_contract.py`
7. `backend/tests/conftest.py`

The `backend/tests/conftest.py` authorization is limited to the shared
TestClient/global app isolation correction described in this plan. It must not
change production app construction, production routes, B1 requirements,
requirement metadata semantics, or B1 evidence scenarios. If the actual fix
requires any file outside this list, Gate B must stop and return to Gate A.

Production source corrections: none approved.

Frontend source corrections: none approved.

Database migrations: none approved.

If Gate B discovers that current production source contradicts the frozen B1
contract, stop and request human review before changing production code or
expanding this file set.

## 7. Testing And Evidence

### Trusted Test Root

Trusted B1 tests must live under:

- `backend/tests/workflows/request_ownership`

This is inside the current EN-01 trusted `workflows` root. Historical or
pre-reset tests are not evidence.

### Shared Test-Isolation Correction

Gate B must correct this trusted backend test-process invariant:

A backend test that temporarily changes settings and imports or rebuilds
`backend.main` must not leave a differently configured global FastAPI app for
later tests.

The correction must be implemented only in `backend/tests/conftest.py`. The
shared `client` fixture, or a helper inside the same file, must ensure DB-backed
tests using the shared client receive a FastAPI app built for the current normal
test environment after any prior monkeypatch-scoped settings have been restored.
It must preserve existing dedicated test database validation, network safety,
database cleanup, and dependency-override cleanup.

### Required Test Files

`test_game_create_request_ownership_contract.py`

- cover `WS02-05B1-R1` and `WS02-05B1-R2`;
- inspect `GameCreate` fields and generated OpenAPI for `POST /games`;
- API-test protected over-posting rejection for representative protected
  categories;
- API-test valid admin generic community/official create persistence using
  PostgreSQL and prove protected values are server-derived;
- prove venue snapshots come from the venue row, not request payload;
- prove official create ignores caller-supplied host intent and applies
  official invariants.

`test_game_update_request_ownership_contract.py`

- cover `WS02-05B1-R3` and `WS02-05B1-R4`;
- inspect `GameUpdate` fields and generated OpenAPI for `PATCH /games/{game_id}`;
- API-test protected over-posting rejection for representative protected
  categories;
- API-test rejected over-posting has no persisted side effect;
- API-test successful allowed updates mutate allowed fields and preserve
  protected fields;
- prove service-derived `starts_on_local`, lifecycle maintenance, and
  `host_guest_max`/official forced behavior for material update cases.

`test_game_specialized_mutation_authority_contract.py`

- cover `WS02-05B1-R5`;
- inspect purpose-specific schemas and route bindings for community publish,
  host edit, admin official create/update, official host/player/cancel actions,
  game join/leave/guest/cancel, community details, and admin community
  enforcement;
- prove those schemas use `extra="forbid"` where they accept JSON bodies;
- prove dedicated host/user IDs appear only in purpose-specific action schemas,
  not generic game update;
- prove generated OpenAPI request schemas do not expose generic protected game
  fields through specialized paths except for fields deliberately owned by that
  path.

`test_game_request_negative_space_contract.py`

- cover `WS02-05B1-R6`;
- source-inspect current frontend callers and payload builders for absence of
  generic `POST /games` and generic `PATCH /games/{game_id}` write callers;
- source-inspect generic game write services for explicit request mapping and
  absence of request-shaped `Game(**game.model_dump())` or equivalent bypasses;
- inspect current trusted backend test helpers/support utilities and current
  internal setup callers for any dependency on removed/protected generic
  `GameCreate` or `GameUpdate` fields;
- prove current trusted helpers/support do not require unsafe generic-game
  over-posting to set identity, lifecycle, snapshot, payment, policy, actor,
  timestamp, or other protected game fields.

Requirement declaration mapping and generated traceability remain Gate B
checker/traceability validation responsibilities outside B1 behavioral pytest.
Testing-record adequacy remains a human/Gate C review responsibility.

### Evidence Layer Decisions

| Evidence layer | Decision | Reason |
|---|---|---|
| PostgreSQL API behavior | Required | Create/update derivation, persistence, and rejected no-side-effect behavior are database facts, not just schema facts. |
| Pydantic schema inspection | Required | `extra="forbid"` and field allowlists are the first request-ownership boundary. |
| Generated OpenAPI inspection | Required | Request ownership is part of the external API contract and must not be hidden from docs/contracts. |
| Source/caller inventory | Required | B1 must prove there is no current generic game write caller or request-shaped service bypass. |
| Frontend unit tests | Not required | No frontend behavior changes are approved; source inventory is the lowest reliable compatibility proof. |
| Playwright/e2e | Not required | No browser workflow change is part of B1. |
| Provider/network evidence | Not required | Payment/provider correctness belongs to WS02-04B2A2B2 and WS05. |
| Database migration proof | Not required | B1 changes no database schema. |
| Concurrency/race proof | Not required | Capacity, booking, payment, and roster race behavior belongs to DB/workflow/payment owners. |
| Controlled time/freezing | Not generally required | Tests can use fixed future schedule inputs; exact wall-clock transitions are not B1-owned. |
| Full backend regression | Required after focused tests in Gate B | B1 touches API contracts and trusted requirement mapping; full backend regression is needed for Gate B closeout. |
| Shared backend test isolation | Required for the Gate B test-infrastructure correction | The full regression discovered a current order-dependent shared app leak; Gate B must prove the corrected final state no longer fails the independently reproducible sequence. |

### Suggested Gate B Validation Commands

After correcting `backend/tests/conftest.py`, first run the exact minimal
reproduction that previously failed:

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/platform/api_errors/test_correlation_and_safe_headers_contract.py::test_valid_incoming_request_id_is_accepted_and_mirrored backend/tests/platform/chat_rate_limits/test_chat_rate_limit_error_contract.py::test_real_chat_rate_limit_rejection_uses_safe_429_contract
```

Run the affected platform API-error module and chat-rate-limit module:

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/platform/api_errors/test_correlation_and_safe_headers_contract.py
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/platform/chat_rate_limits/test_chat_rate_limit_error_contract.py
```

Run focused B1 tests after creating the evidence artifacts:

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/workflows/request_ownership
```

Run structural compliance checks:

```bash
backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/workflows/request_ownership
backend/.venv/bin/python backend/tests/check_backend_tests.py --scope suite
```

The domain or suite checker output must include generated B1 traceability and
show mappings for R1 through R6 and zero mappings for deferred R7.

Run the backend regression required by the production-readiness workflow:

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests
```

Run static whitespace sanity:

```bash
git diff --check
```

Gate A does not run these tests and does not create these artifacts.

## 8. Integration And Cross-Pass Boundaries

| Area | B1 position |
|---|---|
| `API-M14` | B1 advances request/internal separation for game write contracts only. Response minimization, pagination, cache, and broader HTTP behavior stay with WS02-05A/B2 and later owners. |
| `IAM-014` | B1 advances field-level authorization for game write request fields. Identity/account authority remains WS03; payment/provider authority remains WS05 and WS02-04B2A2B2. |
| `WS02-04B2A2A` | A2A owns approved numeric/type bounds where a field is exposed. B1 owns whether generic game write exposes the field at all. |
| `WS02-04B2A2B1` | Route lifecycle/tombstone retirement remains B1-from-WS02-04 work, not this B1 request-ownership pass. |
| `WS02-04B2A2B2` | Provider/payment input ownership remains B2A2B2 and WS05. B1 must not re-own saved-card, checkout return URL, payment-event repair, refund, credit, or admin-money payment semantics. |
| `WS02-04B2A2B3` | Policy/legal authoring and acceptance mutation retirement remains B3. |
| `WS02-04B2A2C` | Ordinary JSON byte limits remain A2C. B1 may rely on oversized-body protection but must not claim it. |
| `WS02-05A` | HTTP media, OpenAPI error documentation, cache classification, docs exposure, tombstone representation, and pagination owner truth stay with 05A. B1 owns only request-schema field presence/absence for game write paths. |
| `WS02-05B2` | Response minimization and audience-specific read contracts stay with B2. B1 must not use response fields as request-ownership proof except to confirm it is not claiming them. |
| `WS03` | Profile, Firebase identity, verifier-controlled fields, role/account status, account deletion, and auth authority stay with WS03. |
| `WS05` | Stripe, provider-side lifecycle, refund correctness, payment reconciliation, dashboards, and financial runtime evidence stay with WS05. |
| `WS06` | Venue image upload/object provider behavior and R2 evidence stay with WS06. |

## 9. Non-Goals

B1 does not:

- alter production backend, frontend, database, provider, deployment, or CI
  code in Gate B unless the plan is reopened;
- add or change migrations;
- change `GameRead`, `GameDetailRead`, `SelfUserRead`, admin response models, or
  any response minimization behavior;
- change HTTP media-type handling, cache headers, docs exposure, 405 handling,
  tombstone representation, or pagination contracts;
- approve a universal body-size policy or route limit;
- validate Stripe/provider dashboards, live webhooks, saved-card provider
  behavior, refunds, or financial reconciliation;
- prove booking/roster/payment race safety or capacity concurrency;
- prove legal/privacy readiness;
- run Playwright/e2e or change browser UI behavior.

## 10. Gate B Completion Criteria

Gate B is complete only when all of the following are true:

- `backend/tests/support/requirements/ws02_05b1.json` exists with the frozen
  metadata above.
- `backend/tests/workflows/request_ownership/TESTING_RECORD.md` exists and
  explains scenario discovery, selected evidence, side effects, gaps, and
  adequacy for R1-R7.
- The four B1 test files listed in this plan exist under
  `backend/tests/workflows/request_ownership`.
- `backend/tests/conftest.py` contains only the approved shared
  TestClient/global app isolation correction.
- R1 through R6 have trusted pytest mappings and pass.
- R7 remains deferred/governance with zero pytest mappings.
- The exact minimal isolation reproduction and the affected platform API-error
  and chat-rate-limit modules pass after the correction.
- Focused B1 tests pass against PostgreSQL.
- Backend test checker domain and suite checks pass.
- Full trusted backend regression passes.
- `git diff --check` passes.
- No production, frontend, migration, provider, deployment, or CI file changed
  unless a human explicitly approved reopening the Gate A scope.
- The Gate B final report states exactly which evidence layers were used, which
  were intentionally not used, and why B1 remains partial for broader API-M14
  and IAM-014 closure.
