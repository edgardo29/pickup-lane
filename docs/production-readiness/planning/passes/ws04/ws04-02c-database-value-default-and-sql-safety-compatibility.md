# WS04-02C - Database Value, Default, And SQL-Safety Compatibility

This pass makes the current database value, default, and SQL-construction surface explicit and testable after the accepted WS04-02A transaction-boundary work and WS04-02B concurrency-invariant work.

This document is the engineering blueprint for the pass.

## 1. What This Work Does

This pass covers the database value layer that remains after the transaction and concurrency children are accepted. It verifies and corrects how the current backend represents time, money, statuses, JSON values, database defaults, update timestamps, raw SQL, and SQL-related logging across SQLAlchemy models, canonical migrations, services, schemas, and focused tests.

The result should be a settled current-source database compatibility contract:

- timestamps stored through PostgreSQL and SQLAlchemy remain timezone-aware and serialize safely through the API;
- money and provider-facing amounts remain integer cents with explicit USD currency handling;
- status and default values created by PostgreSQL match the values accepted by services and response schemas;
- JSON columns and JSON defaults do not share mutable Python state or silently change shape between model, migration, and API behavior;
- raw SQL usage is fixed, parameterized, or explicitly allowlisted;
- application and SQL logging do not expose raw SQL parameter values, provider payloads, personal data, payment details, credentials, or other sensitive database values;
- the accepted WS04-02A transaction-boundary contracts and WS04-02B invariant/concurrency contracts remain intact.

This pass may make narrow source or migration corrections when current repository truth shows a value/default/SQL-safety mismatch. It does not redesign the payment lifecycle, create durable workers, select final production infrastructure, prove provider/database logs from a deployed environment, rehearse production-like migrations, or define the broader migration compatibility program.

## 2. What Must Be True

The requirements below define the finished behavior for this pass. They focus on current repository-owned database values and SQL safety, not on final provider/runtime evidence or later payment, job, migration, and observability programs.

### 2.1 The Current Value And SQL Surface Is Cataloged

The backend must contain a compact contract at `backend/services/database_value_sql_safety_policy.py` that names the current database value and SQL-safety surface this pass protects.

The contract must cover at least:

- timestamp and update-timestamp ownership;
- money, currency, and amount fields;
- status fields, status defaults, and service-accepted status values;
- JSON/JSONB columns and payload defaults;
- database server defaults and ORM-side defaults;
- raw SQL expressions used by production source;
- raw SQL expressions used by migrations where they affect SQL/value safety;
- SQL/logging safety rules for the current backend database surface;
- later owners for deployed provider/database logs, broader observability, migration rehearsal, durable workers, and final production infrastructure facts.

The contract must be deterministic and side-effect free. It is a current-source design and test target, not a runtime policy engine.

### 2.2 Time And Update Timestamps Are Timezone-Aware And Deliberate

Persisted datetime values must use timezone-aware SQLAlchemy/PostgreSQL types and timezone-aware Python values.

Database defaults may initialize `created_at`, `updated_at`, and event timestamps when the model and canonical migration agree. Service code may set `updated_at` or lifecycle timestamps when a workflow makes a deliberate state transition, but it must use timezone-aware values and must not rely on `datetime.utcnow()`, naive `datetime.now()`, `DateTime(timezone=False)`, bare `DateTime()`, or implicit ORM `onupdate` behavior.

Tests must prove representative database default round trips and API serialization for timezone-aware datetime fields. If current source uses both database initialization and service-owned update timestamps for the same row family, the behavior must be intentional, documented in the contract, and covered by focused tests.

### 2.3 Money And Currency Values Stay Exact

Money-bearing database fields must stay represented as integer cents, with explicit currency fields or constraints where the value crosses payment, refund, credit, booking, host-publish, admin-money, or provider-facing boundaries.

The current USD-only contract must remain explicit:

- database constraints and migrations must reject unsupported currencies where the table owns money;
- service-level validation must continue to reject unsupported currency input before provider calls;
- provider-facing Stripe operations must send and receive integer cents without float conversion;
- API schemas must expose money as integer cents, not formatted floating-point values, when the field is programmatic data rather than display text.

Tests must prove representative database constraints, service validation, provider adapter behavior with fake/local inputs, and API serialization boundaries without contacting Stripe or relying on final production provider evidence.

### 2.4 Status Defaults Match The Current State Machines

Every database status default that can create a row without an explicit application value must be a status that current service code and response schemas accept.

Status compatibility must be checked across:

- SQLAlchemy model check constraints and defaults;
- canonical migration check constraints and defaults;
- service constants and validation helpers;
- request and response schemas;
- accepted transaction and concurrency state transitions from WS04-02A and WS04-02B.

The pass must correct any current mismatch where PostgreSQL can create a status value that application code treats as invalid, or where application code can persist a status that the database rejects. It must not create new product states or redesign payment, refund, booking, moderation, notice, or job state machines.

### 2.5 JSON Defaults And Payloads Are Safe

JSON and JSONB columns must have safe default behavior and stable shapes where the application depends on them.

The pass must verify that:

- server-side JSON defaults use explicit PostgreSQL expressions when a database default is required;
- Python model or schema defaults do not share mutable state between requests or rows;
- required JSON payload fields round-trip through PostgreSQL without shape changes that break current services;
- raw provider payload storage remains limited to the accepted current event surfaces and is not logged or exposed through unrelated validation.

Tests must include representative row creation and mutation cases for current JSON/JSONB columns that have defaults or application-dependent shapes.

### 2.6 Raw SQL Is Fixed, Parameterized, Or Allowlisted

Production raw SQL must remain small and safe.

The current production raw SQL surface includes fixed health-check SQL, fixed platform-notice search/sequence SQL, and SQLAlchemy model/migration expressions such as partial indexes, check constraints, extension setup, and sequence setup. Those uses are acceptable only when they are fixed strings, parameterized expressions, or allowlisted fixed identifiers.

The pass must reject or correct:

- f-string SQL;
- `.format()` SQL;
- string-concatenated SQL;
- `exec_driver_sql()` in production source;
- `from_statement()` for production dynamic statements;
- dynamic table, column, sort, operator, or schema identifiers without an explicit allowlist;
- unreviewed `search_path` mutation;
- SQLAlchemy `echo=True` or statement-logging configuration in production settings;
- migration SQL expressions that interpolate untrusted values or hide value/default behavior that belongs in an ordinary Alembic/SQLAlchemy construct.

Migration SQL is in scope only for value/default/SQL-safety review. Expand/contract policy, migration graph correctness, drift detection, interruption behavior, and production-like migration rehearsal belong to WS04-03.

### 2.7 SQL And Value Logging Does Not Leak Sensitive Data

The backend must not intentionally log raw SQL with bound parameter values, full provider payloads, credentials, payment card data, personal data, or other sensitive database values.

The pass must inspect current application logging around database, provider, admin, payment, refund, credit, notification, platform notice, support, moderation, and account-deletion flows where SQL or database values could be emitted. It must preserve useful operational logs while preventing value leakage.

Repository-owned static and local runtime checks can prove application-source logging behavior. Deployed database logs, provider control-plane logs, centralized log aggregation, dashboards, alert thresholds, and operational log-access evidence remain later-owned by WS09 and WS10.

### 2.8 Accepted Database Contracts Remain Intact

The pass must preserve the accepted database foundation, transaction-boundary, and invariant/concurrency behavior from WS04-01A, WS04-01B, WS04-01C, WS04-02A, and WS04-02B.

It must not:

- remove or weaken request-session rollback/close behavior, pool settings, timeout settings, role/credential boundaries, query/cursor behavior, transaction checkpoints, provider unknown-outcome handling, database invariants, row locks, or deterministic concurrency proof;
- use temporary Neon, Render, Vercel, local, CI, README, free-tier, or framework-default values as final production facts;
- require final production PostgreSQL topology, numeric connection budget, role/grant evidence, deployed SQL logs, provider logs, dashboards, alerts, or runtime operations evidence before this provider-independent child can complete;
- absorb WS04-03 migration policy/rehearsal, WS05 durable job/payment lifecycle, WS09/WS10 deployed observability/operations, or WS04-01D final production database verification work.

## 3. Design

The design starts by making the current value and SQL surface explicit, then proves representative behavior with focused PostgreSQL and static-source tests. Gate B should make narrow corrections only when current repository truth violates the contract below.

### 3.1 Add A Database Value And SQL-Safety Contract

Introduce `backend/services/database_value_sql_safety_policy.py` for the current value/default/SQL-safety surface.

The contract should be readable by tests and humans. It should identify each protected family, the accepted mechanism, and the later owner when the proof needs deployed provider/runtime evidence.

At minimum, include these families:

| Family | Accepted current mechanism |
|---|---|
| Timestamps and update timestamps | `DateTime(timezone=True)`, PostgreSQL `now()` defaults where appropriate, timezone-aware service-set timestamps for deliberate transitions. |
| Money and currency | Integer cents, explicit USD constraints or validation, provider adapter behavior that sends cents without float conversion. |
| Status defaults | Database defaults and check constraints aligned with service constants and schema-visible states. |
| JSON/JSONB values | Explicit server-side defaults or safe Python/schema defaults, stable payload shapes, no shared mutable defaults. |
| Production raw SQL | Fixed or parameterized SQL only; fixed literal SQL expressions may be listed when they have no user-controlled identifier or value input. |
| Migration SQL expressions | Fixed extension, sequence, index, and constraint expressions reviewed for value/default/SQL-safety only. |
| SQL and value logging | No production SQL echo or intentional logging of bound SQL values, raw provider payloads, secrets, personal data, or payment details. |

The contract must not open database connections, call providers, read environment-specific provider settings, or depend on final production infrastructure.

### 3.2 Reconcile Models, Migrations, Services, And Schemas

Gate B must inspect the current repository surface rather than rely on the old audit snapshot.

The reconciliation must include:

- SQLAlchemy model columns and constraints under `backend/models/`;
- canonical Alembic migrations under `backend/alembic/versions/`;
- services and adapters under `backend/services/` that create or mutate timestamp, status, money, currency, JSON, or provider-facing values;
- route/schema boundaries under `backend/routes/` and `backend/schemas/` where these values enter or leave the API;
- current trusted tests and accepted compatibility records for WS04-01A/B/C, WS04-02A, and WS04-02B.

For each mismatch found, Gate B should choose the narrowest correction that makes the current behavior coherent. Examples include fixing a service-set timestamp to use timezone-aware UTC, aligning a model default with its canonical migration, making an allowlist explicit around a fixed SQL expression, or adding a missing test for an already-correct contract.

Gate B must return to Gate A if the correct fix requires a new product state, a broad payment/provider redesign, a durable worker, final infrastructure evidence, or a migration compatibility policy that belongs to WS04-03.

### 3.3 Prove Database Defaults With PostgreSQL, Not Static Inspection Alone

Static inspection can show that a model or migration declares `server_default`, `DateTime(timezone=True)`, `CHAR(3)`, `Integer`, `JSONB`, or a check constraint. It cannot prove that PostgreSQL produces the expected values at runtime.

Focused PostgreSQL tests should create representative rows through SQLAlchemy while intentionally allowing PostgreSQL defaults to populate the relevant fields. Those tests should refresh the rows and assert:

- timestamps are populated, timezone-aware, and serializable;
- `created_at` and `updated_at` initialization behaves as intended;
- service-owned update timestamp changes remain timezone-aware;
- status defaults are values accepted by current service/schema logic;
- money defaults and amount constraints preserve integer cents and USD-only behavior;
- JSON defaults create independent row values and do not share mutable Python state.

Do not create exhaustive table-by-table tests when a representative family test plus static inventory proves the same contract. Add targeted tests for tables whose current defaults are materially different or high risk.

### 3.4 Keep SQL Construction Small And Explicit

Gate B must build a current raw-SQL inventory for production source and migration SQL expressions relevant to value/default/SQL safety.

Production source should stay within these accepted patterns:

- fixed health-check SQL such as `SELECT 1`;
- fixed advisory-lock or sequence calls that use bound parameters or fixed identifiers;
- fixed full-text/search expressions exposed through `literal_column()` only when the expression is constant and not built from user input;
- SQLAlchemy expression APIs for predicates, sorting, partial indexes, and constraints.

If a dynamic identifier is genuinely needed, it must use an explicit allowlist that maps external choices to known SQLAlchemy columns or fixed SQL fragments. Do not pass user input into raw SQL text.

Migration SQL expressions should remain fixed schema expressions. If a migration expression is better expressed through Alembic or SQLAlchemy operations, Gate B may narrow it when doing so is part of SQL/value safety and does not become WS04-03 migration-policy work.

### 3.5 Keep Logging Useful But Value-Safe

Gate B must inspect logging statements and logging configuration that could expose database values.

The pass should preserve logs that communicate bounded operational facts such as workflow identifiers, safe IDs, state categories, retry classes, and sanitized error categories. It must prevent logs that include:

- raw SQL with bound parameter values;
- raw request, provider, webhook, or database payloads;
- secrets, tokens, credentials, or connection strings;
- payment method details or card data;
- unbounded personal text or profile data;
- sensitive moderation, support, or admin review content.

Tests may combine static source assertions with local logging-capture tests around representative workflows. Provider and deployed database log evidence remains outside this pass.

### 3.6 Preserve Accepted A/B Contracts While Closing The C Surface

WS04-02C runs after accepted WS04-02A and WS04-02B because its tests should cover the settled database surface. Gate B must keep the A and B source contracts as compatibility boundaries.

Required preservation includes:

- transaction-boundary policy classifications and provider checkpoint behavior from WS04-02A;
- game-first locking, paid waitlist hold behavior, account-deletion roster cleanup order, and credit concurrency behavior from WS04-02B;
- accepted database lifecycle, query/cursor, production-database verification framework, and final-infrastructure deferral from WS04-01A/B/C.

The execution-register update for this pass should record WS04-02C as accepted on merge and mark the current WS04-02 executable child set complete. It must keep later-owned work with WS04-03, WS05, WS09, WS10, and WS04-01D rather than claiming those facts as proven by WS04-02.

## 4. Failures And Edge Cases

These cases define the boundaries that matter for database values and SQL safety. They are the situations most likely to produce incorrect persisted values, unsafe SQL, or false completion claims.

1. **Database default creates an application-invalid value**
   - **Condition:** PostgreSQL creates a status, currency, JSON value, timestamp, or numeric default that service code or response schemas reject.
   - **Required behavior:** Align the model, canonical migration, service validation, or schema boundary so database-created rows remain valid current application rows.

2. **Service code creates a database-invalid value**
   - **Condition:** Current service code can set a status, currency, amount, JSON shape, or timestamp that violates a database check constraint or accepted schema contract.
   - **Required behavior:** Correct the service validation or value mapping without inventing a new product state or broad lifecycle redesign.

3. **Naive or mixed timezone values appear**
   - **Condition:** Source uses naive datetimes, `datetime.utcnow()`, bare `datetime.now()`, non-timezone SQLAlchemy datetime columns, or ambiguous timestamp serialization.
   - **Required behavior:** Use timezone-aware values and prove representative database/API round trips.

4. **Money crosses a boundary as a float or unsupported currency**
   - **Condition:** Money-bearing source converts cents through floating-point math, omits required USD validation, or can send unsupported currency to provider-facing code.
   - **Required behavior:** Preserve integer cents and explicit currency validation through database, service, provider-adapter, and API boundaries.

5. **JSON defaults share mutable state or change shape**
   - **Condition:** A JSON field uses a mutable Python default, a database default that does not match service expectations, or a payload shape that changes when round-tripped through PostgreSQL.
   - **Required behavior:** Use safe defaults and verify independent row values and stable application-visible shape.

6. **Raw SQL accepts user-controlled identifiers or values**
   - **Condition:** Source builds SQL text through f-strings, `.format()`, concatenation, unallowlisted dynamic identifiers, `exec_driver_sql()`, unreviewed `search_path`, or equivalent unsafe construction.
   - **Required behavior:** Replace it with SQLAlchemy expressions, bound parameters, or explicit allowlists. If the needed fix is a broader migration-policy change, return to Gate A or route to WS04-03.

7. **Logs expose database or provider values**
   - **Condition:** Logging captures raw SQL with parameters, raw provider payloads, personal data, payment data, credentials, or unbounded user/admin text.
   - **Required behavior:** Sanitize or narrow the log while preserving safe operational context. Deployed provider/database log access remains later-owned.

8. **A required correction would cross this pass boundary**
   - **Condition:** Correct completion requires final production provider facts, migration rehearsal policy, durable job execution, full payment/provider reconciliation, deployed logging, dashboards, alert thresholds, or operational evidence.
   - **Required behavior:** Stop and route to the owning pass instead of expanding WS04-02C.

## 5. Testing

Testing must prove that the current database value and SQL-safety surface works against PostgreSQL and current source, not merely that source files contain expected strings.

### 5.1 Focused PostgreSQL Value And Default Tests

Create a focused trusted test scope for this pass. The tests should use the existing PostgreSQL test database rules and should prove representative runtime behavior for:

- timezone-aware server defaults and API serialization;
- deliberate service-owned `updated_at` changes;
- money/currency constraints and integer-cent round trips;
- status defaults that match service/schema-accepted values;
- JSON/JSONB defaults and independent row mutation;
- representative model/migration consistency for the database value families this pass owns.

Tests should cover the highest-risk current families rather than every column mechanically. High-risk families include bookings, payments, refunds, game credits, game-credit usage, host publish fees, money issues, platform notices, notifications, participants, waitlist entries, and current admin/support/review records where database defaults or payloads affect visible behavior.

### 5.2 SQL Construction And Logging Tests

Static source tests must verify the current production raw-SQL inventory and reject unsafe construction patterns in production source.

The tests should prove:

- production raw SQL remains fixed, parameterized, or explicitly allowlisted;
- migration SQL expressions in this pass's scope are fixed and value-safe;
- SQLAlchemy `echo=True`, SQL statement logging, and connection-string logging are not enabled in production code/configuration;
- representative application logs do not include raw SQL parameter values, raw provider payloads, credentials, payment data, personal data, or other sensitive database values.

If runtime log capture is used, it should execute only local deterministic code paths and must not require provider network access or deployed logging infrastructure.

### 5.3 Compatibility Tests

Run the accepted compatibility scopes that could realistically regress from this pass:

- WS04-01A database lifecycle, pool, session, timeout, and credential-boundary tests;
- WS04-01B query/cursor and database-access behavior tests;
- WS04-01C provider-independent production database verification framework tests;
- WS04-02A transaction-boundary and provider-checkpoint tests;
- WS04-02B database-invariant and concurrency tests;
- any focused route/schema tests affected by value/default/SQL corrections.

Gate B may add a narrower compatibility run when the actual implementation touches a more specific service or route.

### 5.4 Requirement Declaration And Testing Record

Gate B must add the stable requirement declaration and human testing record for this focused scope.

The requirement declaration belongs at `backend/tests/support/requirements/ws04_02c.json`. Focused tests and the testing record belong under `backend/tests/workflows/database_value_default_sql_safety_compatibility/`.

The requirement declaration should map the current requirements in this plan to stable `WS04-02C` requirement IDs. The testing record should explain the value/default/SQL risks, selected scenarios, proof layers, gaps, deferrals, and why the validation is adequate.

The testing record must not claim final provider/database log evidence, production runtime behavior, migration rehearsal, durable worker behavior, full payment reconciliation, dashboards, alerts, or final infrastructure facts.

## 6. Done When

This checklist defines the engineering completion bar for WS04-02C.

- [ ] The current database value/default/SQL-safety contract exists and covers timestamps, money, statuses, JSON, defaults, raw SQL, migration SQL expressions, logging safety, and later-owned boundaries.
- [ ] SQLAlchemy models, canonical migrations, services, schemas, and accepted A/B artifacts have been reconciled for this pass's value/default/SQL-safety scope.
- [ ] Any current source mismatch in timestamp, money/currency, status, JSON default, raw SQL, or logging behavior has been corrected narrowly within this pass.
- [ ] PostgreSQL tests prove representative database defaults, timezone-aware timestamp round trips, integer-cent/currency behavior, status-default compatibility, and JSON default behavior.
- [ ] Static or local runtime tests prove production raw SQL remains fixed, parameterized, or allowlisted and that repository-owned logging does not expose sensitive database values.
- [ ] Accepted WS04-01A/B/C, WS04-02A, and WS04-02B contracts continue to pass where this pass could affect them.
- [ ] The stable requirement declaration and testing record for WS04-02C are present and match the implemented proof.
- [ ] The execution register records that WS04-02C becomes accepted on merge, marks the current WS04-02 executable child set complete, and preserves later-owned WS04-03, WS05, WS09, WS10, and WS04-01D work without claiming it as complete.
- [ ] No final production infrastructure, deployed provider log, database log, dashboard, alert, migration rehearsal, durable-worker, or full payment/provider reconciliation fact is claimed by this pass.
