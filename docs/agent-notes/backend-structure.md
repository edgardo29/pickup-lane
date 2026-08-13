# Backend Structure

This document defines the authoritative rules for backend file placement,
responsibility, dependency direction, and architectural ownership in Pickup
Lane.

Read it before creating, moving, splitting, renaming, or substantially changing
backend files.

Also read:

* the relevant feature documentation before changing product behavior
* `database.md` before changing models, migrations, constraints, indexes, or
  database commands
* `global-rules.md` before running commands or broad repository changes

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
* `backend/scripts/`: explicit development or operational scripts
* `backend/tests/`: backend tests

Continue using these locations.

Do not create a new top-level backend directory or architectural layer unless
none of the existing locations can clearly own the responsibility.

Do not introduce repository, manager, controller, use-case, handler, command,
or similar parallel layers as part of an ordinary feature change.

A new architectural layer requires an explicit project-level decision.

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
* HTTP error translation
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
and the relevant feature contract.

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

Frontend visibility is not authorization. Backend checks remain authoritative.

Route dependencies may enforce broad access requirements. Services own
authorization that depends on the target record, ownership, workflow state,
action type, or domain policy.

Do not reimplement authentication or active-admin checks across domain
services. Use the existing shared dependencies and service-callable assertions.

## Transactions And External Systems

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

High-risk workflows may use separate preview and execution operations.
Execution must recalculate, authorize, and lock current state rather than
trusting the preview response.

External client modules own protocol-level concerns such as:

* client initialization
* provider authentication
* request construction
* response parsing
* timeouts
* transport errors
* provider identifiers
* webhook signature verification

Domain services own decisions based on external responses.

External clients must not decide application permissions, state transitions,
audit behavior, notifications, or support outcomes.

Use existing shared clients and provider initialization. Do not create wrappers
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

Before creating new infrastructure, inspect the backend for the established
owner.

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
* `<provider>_client.py`
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
* clients import provider and infrastructure utilities

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

`backend/scripts/` owns explicit development, maintenance, repair, or
operational commands.

Scripts must have a narrow purpose, use existing services for domain behavior,
and make destructive operations explicit.

A script is not a substitute for a missing service.

Tests belong under `backend/tests/` and should follow the domain or workflow
being tested.

Route tests cover HTTP behavior, authentication, authorization, validation,
status codes, and response contracts.

Service tests cover business rules, state transitions, transaction behavior,
idempotency, auditing, side effects, and partial failures.

Do not place production helpers in the test package or introduce a new test
framework as part of an unrelated task.

Exact test commands and execution rules belong in `global-rules.md` or the
relevant testing documentation.

## Scope Discipline

Keep each implementation limited to the approved task.

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

1. Read this document.
2. Read the relevant feature documentation.
3. Read `database.md` when persistent data may change.
4. Read `global-rules.md` for commands and testing requirements.
5. Identify the current owner of the behavior.
6. State which files will change.
7. Explain any non-trivial new file, directory, or moved responsibility.
8. Confirm the dependency direction.
9. Confirm the focused validation for the change.
10. Keep unrelated cleanup outside the task.

Before considering the structural portion complete, confirm:

* every changed file has one clear responsibility
* routes remain limited to HTTP concerns
* business behavior remains in services
* reusable queries and rules have one owner
* models and migrations remain aligned
* actor identity and authorization remain authoritative
* transaction ownership is explicit
* dependencies do not form cycles
* tests and imports reflect file movement
