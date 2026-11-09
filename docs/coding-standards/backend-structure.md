# Backend Structure

This document defines the repository rules for backend file placement,
responsibility, dependency direction, architectural ownership, and API design
in Pickup Lane.

Read `backend-standards.md` alongside this guide for general backend
engineering requirements. Both documents apply to backend work; this guide
owns Pickup Lane's paths, service boundaries, and API contracts.

Read it before creating, moving, splitting, renaming, or substantially changing
backend files.

Also read:

* the relevant feature documentation before changing product behavior
* `database.md` before changing models, migrations, constraints, indexes, or
  database commands

This document does not own feature behavior, migration history, database rebuild
commands, or detailed test commands.

When existing code conflicts with these rules, do not silently copy or expand
the conflict. Keep the requested change focused and identify the inconsistency
unless the task explicitly includes correcting it.

## Existing Structure

The backend currently uses:

* `backend/routes/`: FastAPI endpoints and HTTP concerns
* `backend/services/`: business logic, queries, workflows, and orchestration
* `backend/models/`: SQLAlchemy ORM models
* `backend/schemas/`: Pydantic request and response models
* `backend/alembic/versions/`: Alembic migration revisions
* `backend/scripts/`: explicit local mock/demo-data utilities
* `backend/tests/`: backend tests

Continue using these locations.

Do not create a new top-level backend directory or architectural layer unless
none of the existing locations can clearly own the responsibility.

Do not introduce repository, manager, controller, use-case, handler, command,
or similar parallel layers as part of an ordinary feature change.

A new architectural layer requires an explicit owner decision.

## Placement Decision Order

Use the narrowest correct owner:

1. HTTP-specific behavior belongs in the route.
2. Request and response contracts belong in schemas.
3. Database definitions and database-enforced invariants belong in models and
   migrations.
4. Business rules, queries, state transitions, and workflows belong in
   services.
5. Reusable pure domain rules may belong in a focused rule or policy module.
6. External protocol communication belongs in the existing client or
   infrastructure owner.
7. Genuinely domain-independent behavior belongs in existing shared
   infrastructure.
8. Create a new file or directory only when no existing owner is appropriate.

Do not make code shared in anticipation of future reuse. Promote it when there
is a real second caller or when one canonical owner is needed to prevent
behavioral drift.

## Routes

Routes own:

* endpoint paths and methods
* request parsing
* path and query parameters
* dependency injection
* authentication and route-level access dependencies
* response models and status codes
* HTTP error translation to shared application exceptions
* conversion of service results into endpoint responses

Routes must call services for domain queries and business workflows.

Routes must not own:

* reusable business rules
* reusable database queries
* multi-step workflows
* commits or rollbacks
* row locking
* idempotency
* cross-model state changes
* external-system workflows
* audit, notification, or support orchestration

Endpoint-specific parameter normalization may remain in the route.

Reusable validation belongs in the owning schema, rule, policy, or service.

Services and lower-level modules must never import route modules.

## Services

Services own:

* business and domain validation
* state transitions
* reusable database queries
* transaction boundaries
* row locking
* idempotency and replay behavior
* orchestration across models
* cross-domain workflows
* audit writes
* notification behavior
* support follow-up behavior
* external-system coordination
* reconciliation and partial-failure handling

Prefer one service owning a complete cohesive workflow over splitting every
internal step into a separate file.

Split a service when it contains independent workflows with different callers,
rules, dependencies, or change patterns.

A service may call another service when the called service clearly owns a
lower-level capability, complete domain operation, canonical query, or policy.

Do not create service chains that only pass arguments through additional
layers.

Do not import another service only to reuse a private helper. Move genuinely
shared behavior to the domain that owns its meaning.

Cross-domain workflows must have one explicit orchestration owner. Each domain
service remains responsible for its own invariants and state changes.

Avoid circular dependencies. Local imports must not be used as a permanent
workaround for unclear ownership.

## Models And Migrations

Models own:

* tables and columns
* relationships
* indexes
* unique and check constraints
* foreign-key configuration
* ORM configuration
* appropriate database defaults

Models must not contain:

* route or authentication logic
* request or response behavior
* database queries
* transaction orchestration
* external-system calls
* multi-step domain workflows

Model changes must remain aligned with migrations, schemas, services, tests,
and the relevant feature requirements.

Migration style, revision history, database commands, and rebuild rules belong
in `database.md`.

## Schemas

Schemas own:

* request and response shapes
* field types and nullability
* request defaults
* serialization configuration
* simple request-shape normalization
* validation that depends only on submitted data

Schemas must not contain:

* database queries
* permission decisions
* current-state validation
* transactions
* domain workflows
* external-system calls

Services must validate rules that depend on database state, actor identity,
ownership, permissions, prior workflow state, or external-system state.

Routes may import schemas through the intentional `backend.schemas` export
surface.

Services should normally import the owning schema module directly.

Schemas must not import routes or services.

## Domain Rules And Policies

A focused rule or policy module is appropriate when one domain has a meaningful
set of reusable:

* constants
* status sets
* invariants
* normalization
* pure validation
* permission rules
* transition rules
* sensitivity or target requirements

Rule and policy modules must have one clear domain owner and should normally be
deterministic and free of database, network, and framework side effects.

Do not create generic validation, policy, rule, or constants dumping grounds.

Database-dependent validation belongs in services.

## Queries

Reusable domain queries belong below the route layer.

Queries used by one workflow may remain private to its service.

Queries shared across related workflows may be exposed by the domain that owns
the returned data.

Read-only database work belongs in a service when it represents:

* domain filtering
* visibility
* authorization scope
* ownership
* search
* pagination
* response construction
* derived domain state

Do not duplicate complex queries.

Do not place domain queries in generic database utilities.

Do not introduce a repository layer merely to wrap SQLAlchemy calls.

A focused domain query module is justified only when several real callers share
a substantial, cohesive set of complex read operations.

## Authentication And Authorization

Derive the acting user from verified authentication.

Do not trust request-supplied actor, sender, host, owner, user, or admin
identifiers for authenticated actions.

Use the existing authenticated-user and active-user dependencies.

Admin routes must use `require_active_admin`.

Frontend visibility is not authorization. The backend must enforce access.

Route dependencies may enforce broad access requirements. Services own
authorization that depends on the target record, ownership, workflow state,
action type, or domain policy.

Do not reimplement authentication or active-admin checks across domain
services. Use the existing shared dependencies and service-callable assertions.

## Transactions And External Services

The service that owns a state-changing workflow also owns:

* transaction ordering
* row locks
* commits and rollbacks
* idempotency
* replay and conflict behavior
* audit coordination
* notification coordination
* support follow-up coordination
* external-system coordination

Routes must not commit or roll back business workflows.

Do not split one atomic state transition across unrelated transaction owners.

Within Pickup Lane, the service owning an atomic workflow owns its commit or
rollback. Called services participating in that workflow must not commit or
roll back independently; a separate durable stage must be intentional.

The owning service implements the product's durability and reconciliation
requirements for external work. Follow the reliability and transaction-duration
rules in `backend-standards.md` without adding a queue or outbox for effects
that do not require durable delivery.

High-risk workflows may use separate preview and execution operations.
Execution must recalculate, authorize, and lock current state rather than
trusting the preview response.

External client modules own protocol-level concerns such as:

* client initialization
* external-service authentication
* request construction
* response parsing
* timeouts
* transport errors
* external-service identifiers
* provider-documented webhook authentication, such as signature verification
  or HTTP Basic Authentication

Domain services own decisions based on external responses.

External clients must not decide application permissions, state transitions,
audit behavior, notifications, or support outcomes.

Firebase Admin JSON and service-account key files are local secret material.
They must remain ignored and uncommitted; backend code should load any required
credential material through the configured credential path rather than
hardcoding it in source.

Use existing shared clients and external-service initialization. Do not create wrappers
that merely rename one existing call.

## Infrastructure And Dependencies

Use existing owners for:

* configuration and environment loading
* database engine and session setup
* FastAPI dependencies
* application startup and shutdown
* logging
* shared exception types
* external client initialization

FastAPI dependencies may resolve authenticated users, database sessions,
route-level access, and shared request context.

Dependencies must not become hidden service layers or own complete business
workflows.

Worker and scheduled-job entry points use the existing infrastructure owners
for any sessions and shutdown handling they need; their business workflows
remain service-owned.

Before creating new infrastructure, inspect the backend for the established
owner.

## API Design Standards

These rules define the external behavior of Pickup Lane HTTP endpoints. The
sections above remain authoritative for who owns routes, schemas, services,
authorization, transactions, idempotency, and external clients; this section
does not restate them.

Apply these rules to new endpoints and to endpoints whose contract is already
being changed. Do not reshape an existing endpoint merely to conform; doing so
is a contract change governed by Compatibility below.

Production requirement identifiers such as P06.R05 refer to
`docs/production-readiness/production-launch/production-launch-requirements.md`.

### Resources, Paths, And Methods

Model endpoints on domain resources, not on tables, ORM models, or internal
workflow steps.

* Use plural nouns for collections and one path segment per identifier, such
  as `/games/{game_id}`. Nest a resource only when the parent is part of its
  identity.
* Follow the project's existing path-naming conventions, including in new
  routers. Do not introduce a competing style.
* Path parameters identify the resource. Query parameters filter, sort,
  search, or paginate.

Methods must keep their HTTP (RFC 9110) meaning:

| Method | Use | Safe | Idempotent |
|---|---|---|---|
| `GET` | Read a representation | Yes | Yes |
| `POST` | Create a subordinate resource or run a domain command | No | No |
| `PUT` | Replace the client-editable representation at a known URI | No | Yes |
| `PATCH` | Partially modify a resource | No | Not inherently |
| `DELETE` | Remove the resource | No | Yes |

* `GET` must not intentionally change business state or initiate a business
  operation, including through query parameters. Incidental effects such as
  request logging, metrics, and access auditing are permitted; they do not
  relax the safe and idempotent meaning shown in the table.
* `PUT` replaces every client-writable field of the target resource. Clients
  do not supply server-managed fields such as identifiers, timestamps, or
  calculated values; the server preserves or derives them. A writable field
  omitted from a `PUT` body is rejected or reset to its documented default,
  never left unchanged. Use `PATCH` when only some writable fields change.
* `DELETE` must have the same intended effect when repeated, although a
  repeated request may receive a different status.
* Use ordinary resource methods when they naturally express the operation.
  An operation that does not fit creation, replacement, partial modification,
  or deletion, such as cancel, approve, restore, or retry, is an explicit
  `POST` domain command. `POST /{collection}/{id}/{action}` is the
  recommended form; another resource shape is acceptable when it expresses
  the operation more clearly. Do not hide a domain command inside a generic
  `PATCH` or `PUT` field edit.
* Do not create RPC-style paths, such as `/getGame` or `/updateGame`, for
  operations a standard method already expresses.
* A non-idempotent `POST` whose duplicate execution would cause harm needs
  service-owned replay protection, as defined under Services.

### Request Contracts

* Every request body uses an explicit Pydantic request schema. Read the raw
  `Request` only for a documented need, such as verifying a provider signature
  over the raw body.
* Clients cannot arbitrarily set server-controlled values, including
  identifiers, actor and owner fields, status and lifecycle fields,
  server-calculated amounts, permissions, and timestamps. Generic create and
  update schemas must not include them.
* An explicitly authorized action may change a protected value, such as a
  status, lifecycle state, or role, through its own narrowly defined request
  schema that accepts only the inputs that action needs. The owning service
  still authorizes the actor and validates current state, as defined under
  Schemas and Services.
* Write schemas reject unknown fields rather than silently ignoring them.
  Rejecting a field that clients previously sent successfully may be a
  breaking change and follows Compatibility.
* Use separate create, update, and response schemas when their fields or
  permissions differ. Do not use one model for every purpose.
* Constrain each field to its meaningful domain: precise types, enumerations
  or literals for finite values, standard formats, numeric ranges, and maximum
  lengths for strings and lists.
* Limit values must come from the applicable requirement or from the database
  constraint the value is stored under. When neither defines a needed limit,
  report the gap instead of inventing a value.
* Request bodies have a maximum size, enforced by counting the bytes actually
  received, regardless of a missing or incorrect length header, before the
  body is parsed or any business change occurs; an oversized body returns
  `413`. P06.R13 and P06.R14 define the enforcement points, and P06.R14 fixes
  the ordinary JSON, platform-notice, and Stripe-webhook limits. Any other
  value must come from an applicable requirement, an infrastructure
  constraint, or a documented operational need, not an invented number.
* Normalize input only where it is harmless and documented, such as trimming
  surrounding whitespace. Do not coerce clearly invalid input into a valid
  value so that a request succeeds.

### Partial Updates

`PATCH` bodies are partial objects with these meanings:

* An omitted field is unchanged.
* An explicit `null` clears the field and is accepted only when the schema
  declares the field clearable.
* Schema defaults are never applied as changes.

Services must apply only the fields actually sent, using the fields Pydantic
reports as set (for example, `model_dump(exclude_unset=True)`). They must not
apply the full model.

### Responses

* Ordinary JSON endpoints declare an explicit response schema and success
  status code.
* Response schemas are explicit and specific to the caller. Never expose an
  ORM model's full column set, and do not reuse one response schema across
  audiences whose readable fields differ.
* Return the resource or result directly; no response wrapper is required.
* A collection that is paginated, or is expected to need pagination, returns
  an object containing its items and pagination fields from the start,
  because converting a bare array later is a breaking change.
* An empty collection is a successful response with no items, not `404`.
* Responses containing private, sensitive, user-specific, or administrative
  information send `Cache-Control: no-store`. `no-cache` still permits
  storage and is not a substitute when storage must be prevented. Genuinely
  public responses may use caching appropriate to their content.
* Use `200` for a successful response with a body, `201` for a created
  resource, `202` only when accepted work is not yet complete, and `204` for
  intentional success without a body.
* Responses without a body, redirects, file downloads, streams, and
  external-provider-required formats may use an appropriate alternative
  response type instead of a JSON response schema. Each such exception must
  be intentional and documented at the route, and any JSON it returns still
  follows the field-exposure rules above.

### Error Status Codes

| Status | Use |
|---|---|
| `400` | The request is malformed or cannot be interpreted, and the problem is not reported by ordinary FastAPI request validation, such as an invalid or mismatched pagination cursor |
| `401` | Authentication is missing, invalid, or expired; the response includes a `WWW-Authenticate` challenge |
| `403` | The caller lacks permission for the action or resource; or, when App Check is enforced, a classified browser API request has missing or invalid App Check proof, including on a route that does not require user authentication (P10.R02, P10.R04) |
| `404` | The resource does not exist, or the applicable visibility policy requires concealing it from this caller |
| `405` | The route does not support the request method; the response identifies the methods the route accepts (P06.R05) |
| `409` | The request conflicts with the resource's current state, including an invalid state transition, exhausted capacity, or a conflicting duplicate. A recognized retry of the same operation follows that operation's idempotency or replay contract instead |
| `413` | The request body exceeds its maximum size |
| `415` | The request uses a content type the route does not accept (P06.R05) |
| `422` | The request fails validation, including FastAPI `RequestValidationError` for body, query, and path input, and, where appropriate, a well-formed submitted value that is semantically invalid. An unsupported content type returns `415`, not `422` |
| `429` | The caller exceeded an applicable rate limit; include `Retry-After` when known |
| `5xx` | A server or dependency failure; include `Retry-After` with `503` when known. When App Check is enforced, Firebase App Check verification unavailability returns `503` (P10.R04) |

When a request has more than one fault, return the first applicable result in
the response precedence defined by P06.R05. Stripe webhooks, non-browser
callbacks, and direct signed R2 requests keep their own credential rules and
are not subject to App Check.

Choose the status from the reason for the rejection. Do not map unrelated
business-rule failures to one universal status. A submitted value that can be
interpreted but violates a rule usually returns `422`, one that depends on the
resource's current state returns `409`, and one that depends on the actor's
permission returns `403`, or `404` when concealment applies.

Never return a success status for a failure or a `5xx` status for a
caller-correctable error.

### Error Responses

The target format for Pickup Lane HTTP API errors is RFC 9457 Problem
Details, served as `application/problem+json`. Once adopted, the same
structure applies to ordinary errors, validation errors, and unexpected
failures. Adoption follows the transition rule at the end of this section.

| Member | Content |
|---|---|
| `type` | Identifies the problem class; a stable absolute URI is preferred, and `about:blank` is permitted when the HTTP status alone describes the problem, in which case `title` is the status's standard reason phrase |
| `title` | Short, safe description of the problem type |
| `status` | The HTTP status code, equal to the response status |
| `detail` | Safe, human-readable string explaining this specific failure |
| `code` | Pickup Lane extension: stable machine-readable error identifier |
| `correlation_id` | Pickup Lane extension: the server-generated internal request identifier defined in Request Correlation |
| `errors` | Pickup Lane extension, optional: one entry per validation failure, each with the field `location`, the violated rule's `code`, and a safe `message`. `location` is always an array of path segments beginning with the input source, such as `["body", "guest_count"]` |

* Every error response uses the HTTP status that matches the failure, as
  defined in Error Status Codes.
* `type` and `code` values do not change meaning once published. Clients use
  them, not `title`, `detail`, or `message` text, to decide behavior.
* Each `code` always appears with the same `type`; several codes may share
  one `type`.
* Validation errors identify the field and violated rule without including
  submitted values.
* Unexpected failures return a generic `detail` with no exception
  information.
* No member may contain stack traces, raw exception text, SQL, request
  bodies, internal hostnames or paths, credentials, tokens, or provider
  diagnostics.
* The central exception handlers in application infrastructure own this
  format. Routes and services raise exceptions; they do not build error
  bodies or register their own handlers.

This is the target format for Pickup Lane endpoints. Changing an existing
endpoint's error responses to it is a contract change and follows
Compatibility.

Adopt Problem Details only through one explicitly planned change to the
central exception handlers, reviewed under Compatibility for every existing
endpoint and caller whose error responses it changes. Until that change is
approved and made, new and changed endpoints use the established central error
format. Routes and services must not build their own error bodies or register
their own handlers to reach the target format early. In either format, error
responses must meet P06.R02, including a stable error identifier, a safe
message, the HTTP status, and the server-generated request identifier from
Request Correlation, and must follow the content restrictions above.

### Request Correlation

* Every inbound request receives a new server-generated internal request
  identifier, whether or not the caller supplies `X-Request-ID`. A
  caller-supplied value never replaces it.
* The internal request identifier is the authoritative request-tracing
  identifier. The same value appears in the response `X-Request-ID` header,
  in an error body's `correlation_id`, and in the related server logs.
* Request identifiers are canonical UUIDv4 values: exactly 36 lowercase
  characters with hyphens, version `4`, and an RFC 9562 variant, matching
  `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`.
  This format applies to the server-generated identifier and to any retained
  caller value.
* An incoming `X-Request-ID` may be retained only when it matches that format.
  A retained value is a separate caller-correlation value linked to the
  internal request identifier. It is never returned as the response
  `X-Request-ID` or used as `correlation_id`.
* A missing, malformed, oversized, or otherwise invalid incoming value is not
  retained, never replaces the internal identifier, and is never reflected in
  a response.
* Request identifiers and caller-correlation values are for request tracing
  only. They never authenticate a caller or grant authorization.

### Collections: Pagination, Filtering, And Sorting

* Every endpoint that returns a list must enforce a maximum page size and
  reject or cap a larger request according to its contract, without returning
  an unbounded table (P05.R17). A collection that can grow with user or data
  volume also has a default page size. Enforce page size through request
  validation. Page-size values follow the limit-source rule in Request
  Contracts and are chosen under Section 3.3 of the production launch
  requirements, as P05.R17 requires.
* Choose offset or cursor pagination per endpoint. Offset suits small or
  administrative lists that need page-number navigation. Cursor pagination
  suits large or frequently changing collections read sequentially. Neither
  is mandatory.
* Ordering must be deterministic, supported by an index, and end with a unique
  tie-breaker, such as the primary key (P05.R17).
* Cursors are opaque: clients must not construct or interpret them. A cursor
  must also be protected against modification and bound to the endpoint, sort
  direction, filter values, and authorization context that created it, and
  its contract must state the ordering and change-visibility behavior required
  by P05.R27.
* Filter parameters and sort keys are explicit, typed allowlists. Do not
  accept free-form field names, expressions, or query languages.
* Add filtering, sorting, and totals only when a client needs them.

### Compatibility

Old and new clients can be active at the same time during a deployment and
while a browser keeps an older frontend loaded. A backend change must work
with both the deployed frontend and the frontend being deployed.

Because write schemas reject unknown fields, a frontend may begin sending a
new request field only after every backend instance that could receive it
accepts that field.

Usually compatible:

* adding an endpoint
* adding an optional request field whose absence preserves existing behavior
* adding a response field that clients do not need

Breaking:

* removing or renaming an endpoint, field, or enumeration value
* making an optional request field required, or no longer accepting a field
  that clients still send
* changing a field's type, format, units, nullability, default, or meaning
* changing the status, error `type`, or error `code` clients rely on for an
  outcome
* adding a response enumeration value that clients interpret exhaustively

A breaking change requires identifying every caller and sequencing the change:

1. add the new contract alongside the old one
2. move every caller to the new contract
3. remove the old contract only after no active client uses it

Do not introduce API version identifiers preemptively. A versioned path or
header requires an explicit owner decision.

### Synchronous And Asynchronous Routes

* Declare a route or dependency with `def` when it calls blocking code, such
  as a synchronous database session, a synchronous SDK, or file I/O. FastAPI
  runs `def` routes in a worker thread.
* Use `async def` only when every operation on its execution path is
  non-blocking or awaited.
* An `async def` route or dependency must not call blocking database,
  network, file, or CPU-heavy code directly. When that cannot be avoided,
  move the call off the event loop explicitly.
* Do not convert a route to `async def` as a performance change without
  confirming the whole call path is non-blocking.

### OpenAPI

FastAPI's generated OpenAPI schema is the authoritative endpoint reference. Do
not maintain separate documents that repeat endpoint paths, fields, schemas,
or status codes.

Keep the generated schema accurate:

* Declare response schemas, success status codes, field types, and
  constraints in code so they appear in the schema.
* Document intentional error statuses through shared response definitions
  instead of copying error schemas onto individual routes.
* Describe error responses with the shared schema of the central error format
  in effect: `application/problem+json` with the shared Problem Details schema
  once that format is adopted. Do not advertise FastAPI's default
  validation-error response shape or any other shape the application does not
  return.
* Add summaries or descriptions only where behavior is not evident from the
  declaration.

Written documentation covers workflows, rules, and rationale, not field
listings. A generated schema does not prove runtime behavior; testing
standards own that verification.

## Files, Folders, And Helpers

Every backend file must have a purpose that can be described in one short
sentence.

Use lowercase `snake_case` for Python files and directories.

Name files by domain and responsibility, such as:

* `<domain>_service.py`
* `<domain>_routes.py`
* `<domain>_schemas.py`
* `<domain>_rules.py`
* `<domain>_policy.py`
* `<service>_client.py`
* `<domain>_queries.py`
* `test_<domain>_<responsibility>.py`

Avoid vague names such as:

* `utils.py`
* `helpers.py`
* `common.py`
* `misc.py`
* `manager.py`
* `processor.py`

Domain-specific helpers belong near the service, rule, policy, client, or
schema that owns their meaning.

Generic helpers must be genuinely domain-independent.

Create or split a file when it establishes a meaningful responsibility or
separates workflows that have different callers, dependencies, or reasons to
change.

Do not split a file merely because it is long.

Do not create:

* speculative abstractions
* one-function wrapper modules without a meaningful boundary
* files that only rename another function call
* tiny files that make a cohesive workflow harder to follow
* global helper or constants dumping grounds

Create a subdirectory only when a domain has several cohesive files and the
folder provides a clear ownership or navigation benefit.

Do not create a directory for one file or because a feature may grow later.

For a non-trivial new file or directory, identify:

1. its path
2. its responsibility
3. why an existing file is insufficient
4. which modules may import it
5. which modules it may import

## Imports And Dependency Direction

Required direction:

* application bootstrap registers routes and infrastructure
* routes import schemas, dependencies, and services
* services import models, domain schemas, clients, rules, policies, and
  lower-level services
* schemas import only shared types and pure domain definitions
* models import only model-level types and database infrastructure
* clients import external-service and infrastructure utilities

Required restrictions:

* services must not import routes
* schemas must not import routes or services
* models must not import routes or services
* clients must not import routes
* lower-level services must not import higher-level orchestration services
* generic utilities must not import domain workflows

Avoid wildcard imports, circular imports, hidden side effects, and permanent
local-import workarounds.

Use package exports deliberately:

* `backend.routes` may expose routers for application registration
* `backend.models` may expose ORM models for application and Alembic loading
* `backend.schemas` may provide a route-facing schema API

Within services, prefer direct imports from the owning module so dependencies
remain visible.

## Scripts And Tests

`backend/scripts/` owns explicit local mock/demo-data utilities only. Keep
test infrastructure, administrator tools, and worker runtime entry points out
of this directory. The existing non-demo command entry points live in focused
modules at the `backend/` package root.

Demo-data scripts must have a narrow purpose, use existing services for domain
behavior, make destructive operations explicit, and refuse production use.
They are not a substitute for a missing service.

Tests belong under `backend/tests/` and should follow the domain or workflow
being tested.

Route tests cover HTTP behavior, authentication, authorization, validation,
status codes, and response contracts.

Service tests cover business rules, state transitions, transaction behavior,
idempotency, auditing, side effects, and partial failures.

Do not place production helpers in the test package or introduce a new test
framework as part of an unrelated task.

Exact test commands and execution rules belong in the relevant testing
documentation or current task instruction.

## Scope Discipline

Keep each implementation limited to the current instruction.

Do not mix unrelated:

* cleanup
* renaming
* file moves
* architecture changes
* formatting
* feature work
* migration cleanup
* test-tooling changes

Do not refactor nearby legacy structure merely because a file is being touched.

A structural correction is appropriate when it is necessary to implement the
requested behavior safely and correctly.

## Before Backend Changes

Before editing backend code:

1. Read this document and `backend-standards.md`.
2. Read the relevant feature documentation.
3. Read `database.md` when persistent data may change.
4. Read `backend-testing.md` when backend tests or validation are in scope.
5. Identify the current owner of the behavior.
6. State which files will change.
7. Explain any non-trivial new file, directory, or moved responsibility.
8. Confirm the dependency direction.
9. Confirm the focused validation for the change.
10. Keep unrelated cleanup outside the task.

Before considering the structural portion complete, confirm:

* every changed file has one clear responsibility
* routes remain limited to HTTP concerns
* new or changed endpoints follow the API Design Standards, and breaking
  contract changes are sequenced for every caller
* business behavior remains in services
* reusable queries and rules have one owner
* models and migrations remain aligned
* actor identity comes from verified authentication and backend authorization
  remains enforced
* transaction ownership is explicit
* dependencies do not form cycles
* tests and imports reflect file movement
