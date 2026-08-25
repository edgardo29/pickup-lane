# WS04-02C Database Value, Default, And SQL-Safety Compatibility Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS04-02C` |
| Trusted test scope | `backend/tests/workflows/database_value_default_sql_safety_compatibility` |
| Requirement declaration | `backend/tests/support/requirements/ws04_02c.json` |
| Authoritative sources | `docs/production-readiness/planning/passes/ws04/ws04-02c-database-value-default-and-sql-safety-compatibility.md`, accepted `WS04-02` intake, accepted WS04-01A/B/C and WS04-02A/B artifacts |
| Evidence layers | PostgreSQL pytest, static source pytest, source-owned policy contract, compatibility pytest |

## 1. Scope

This record covers the provider-independent WS04-02C database value/default and
SQL-safety surface for current repository-owned source. The scope includes
timestamps, service-owned update timestamps, integer-cent money and USD currency
handling, status/default compatibility, JSON/JSONB default behavior, production
raw SQL construction, migration SQL expressions as they affect value safety, and
repository-owned SQL/value logging safety.

This record does not claim final production PostgreSQL provider/topology facts,
numeric production connection budgets, concrete production database roles or
grants, production-like migration rehearsal, durable job/payment lifecycle
reconciliation, deployed provider/database logs, centralized dashboards, alerts,
or operational log-access evidence.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS04-02C-R1` | Current database value/default/SQL-safety surface is cataloged in one deterministic source contract. | pytest |
| `WS04-02C-R2` | Persisted timestamps and deliberate update timestamps are timezone-aware and avoid naive update mechanisms. | pytest |
| `WS04-02C-R3` | Money values remain integer cents with explicit current USD-only handling across database and provider-adapter boundaries. | pytest |
| `WS04-02C-R4` | Database defaults and current status state machines remain compatible. | pytest |
| `WS04-02C-R5` | JSON defaults and payload shapes avoid shared mutable defaults and round-trip safely. | pytest |
| `WS04-02C-R6` | Production raw SQL and migration SQL expressions are fixed, parameterized, or allowlisted. | pytest |
| `WS04-02C-R7` | Repository-owned logging does not intentionally expose SQL values, provider payloads, credentials, payment data, or personal data. | pytest |
| `WS04-02C-R8` | Accepted WS04-01A/B/C and WS04-02A/B contracts remain intact while later-owned evidence remains outside this pass. | pytest plus compatibility |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| `WS04-02C-R1` | One source-owned contract names the current protected value and SQL families. | The pass silently proves only scattered examples and loses ownership boundaries. | False closure or later regression. | Declarative policy and requirement declaration. | workflow |
| `WS04-02C-R2` | Persisted datetimes are timezone-aware and update timestamps are deliberate. | Naive datetimes, bare `DateTime()`, `datetime.utcnow()`, or implicit `onupdate` create ambiguous persisted values. | Incorrect ordering, expiry, reconciliation, or API serialization. | Model metadata scan and PostgreSQL round trip. | workflow |
| `WS04-02C-R3` | Money uses integer cents and current USD constraints. | Float conversion, unsupported currency, or mismatched provider payloads reach the database/provider boundary. | Ledger inconsistency or payment mismatch. | DB constraint proof and fake Stripe adapter proof. | workflow |
| `WS04-02C-R4` | Database-created defaults are application-accepted states. | PostgreSQL creates a status the app rejects, or app code persists a state the DB rejects. | Runtime failures and invalid rows. | Model/default assertions and runtime row creation. | workflow |
| `WS04-02C-R5` | JSON defaults are independent and shape-stable. | Mutable defaults bleed between requests/rows or PostgreSQL defaults produce unexpected shapes. | Broken payment-display or event payload behavior. | Pydantic default-factory check and PostgreSQL JSONB round trip. | workflow |
| `WS04-02C-R6` | Raw SQL remains small, fixed, parameterized, or allowlisted. | Dynamic SQL, f-string SQL, unsafe identifiers, or hidden migration SQL expands the attack surface. | Injection risk or unreviewed value/default behavior. | AST inventory and unsafe-pattern checks. | workflow |
| `WS04-02C-R7` | Logs avoid sensitive SQL/provider/payment/personal values. | Logs include raw payloads, card details, credentials, or bound SQL values. | Privacy and credential exposure. | Static logging-source check and redaction boundary preservation. | workflow |
| `WS04-02C-R8` | Accepted database/transaction/concurrency contracts keep passing. | C changes weaken pool/session, query, transaction, lock, or invariant behavior. | Regression in already accepted foundations. | Compatibility test runs for accepted scopes. | workflow/platform |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | user, admin, system/provider-adapter | grouped | Value/default and SQL-safety behavior is shared by database/source boundaries rather than route identity. |
| States / lifecycle | role/account/booking/payment/community-detail/credit statuses | covered | Representative defaults and model constraints prove current state compatibility without redesigning state machines. |
| Actions | create, update, provider-adapter payload, static SQL/log review | covered | These are the actions where values can be created, changed, sent, or leaked. |
| Inputs / boundaries | unsupported currency, mutable JSON defaults, SQL construction | covered | Each is a high-risk value/SQL boundary in the frozen plan. |
| Time | server default creation, deliberate update timestamp, API serialization | covered | Tests use PostgreSQL defaults and timezone-aware service-set values. |
| Dependencies | PostgreSQL, local source, fake Stripe client | covered | No real provider or final production infrastructure is required. |
| Concurrency / idempotency | accepted WS04-02B locks/invariants | covered elsewhere plus compatibility | WS04-02B owns concurrency; WS04-02C verifies it is preserved. |
| Authorization / privacy / security | logging redaction and SQL construction | covered | Static tests reject unsafe source patterns and sensitive log arguments. |
| Persistence / rollback | successful defaults, rejected bad currency | covered | Runtime tests prove persisted values and database rejection. |
| Recovery | final provider/runtime/log evidence | deferred | Owned by WS04-01D, WS05, WS09, and WS10. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | omit database default values on representative rows | PostgreSQL default round trip |
| empty | yes | empty JSON payment method snapshot | PostgreSQL and schema default proof |
| corrupt | yes | unsupported currency | database constraint rejection |
| exceed | no | size limits outside value/default/SQL-safety focus | covered by source-owned request/schema passes |
| duplicate | no | duplicate/idempotency behavior owned by WS04-02B and WS05 | compatibility/deferred |
| delay | yes | service-owned update timestamp | timezone-aware update proof |
| reorder | no | lock ordering owned by WS04-02B | compatibility |
| interrupt | no | migration interruption owned by WS04-03 | deferred |
| race | no | deterministic contention owned by WS04-02B | compatibility |
| expire / revoke | no | lifecycle expiry/revoke flows owned by domain/payment passes | covered elsewhere/deferred |
| tamper | yes | raw SQL construction and unsafe logging | static source proof |
| retry | no | provider retry/reconciliation owned by WS04-02A/WS05 | compatibility/deferred |
| recover | no | deployed operations evidence owned by WS09/WS10 | deferred |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| `WS04-02C-R1`, `R8` | Source-owned contract and requirement declaration | pytest/static | `test_database_value_sql_safety_policy_contract.py` | Proves one deterministic contract covers all frozen requirement families and later owners. |
| `WS04-02C-R2`, `R4` | PostgreSQL/default timestamp and status behavior | pytest/PostgreSQL/API schema | `test_database_value_defaults_contract.py` | Proves representative server defaults, aware timestamps, deliberate update timestamp, and schema serialization. |
| `WS04-02C-R3` | Money/currency DB and Stripe-adapter boundaries | pytest/PostgreSQL/fake provider boundary | `test_database_value_defaults_contract.py` | Proves unsupported currency rejection and integer-cent Stripe payload construction without contacting Stripe. |
| `WS04-02C-R5` | JSON defaults and shape stability | pytest/PostgreSQL/schema | `test_database_value_defaults_contract.py` | Proves Pydantic mutable defaults are isolated and PostgreSQL JSONB default rows stay independent. |
| `WS04-02C-R6`, `R7` | Raw SQL and logging safety | pytest/static | `test_sql_construction_and_logging_contract.py` | Proves current raw SQL inventory matches allowlists and rejects unsafe SQL/logging patterns in repository source. |
| `WS04-02C-R8` | Accepted compatibility boundaries | pytest | WS04-01A/B/C and WS04-02A/B compatibility scopes | Proves C changes did not break accepted database, transaction, and invariant contracts. |

## 7. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| Representative row creation | PostgreSQL fills safe defaults and timestamp values. | Unsupported currency must not persist. | Integrity failure rolls back the rejected row. |
| JSON default mutation | One row can store a new JSON value. | Another row's default value must not change. | Independent PostgreSQL row values remain isolated. |
| Stripe adapter fake call | Payload uses integer cents and current currency value. | No real Stripe network call and no float conversion. | Not applicable - fake local boundary only. |
| Raw SQL/logging checks | Current source inventory stays explicit. | Dynamic raw SQL and sensitive log fields fail the test. | Not applicable - static proof. |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| Final production PostgreSQL topology, connection budget, roles, grants, and provider/runtime proof | deferred | Final infrastructure is intentionally unselected. | `WS04-01D` |
| Migration graph, drift, interruption, expand/contract policy, and production-like rehearsal | deferred | WS04-02C reviews only value/default/SQL-safety expressions. | `WS04-03` |
| Durable jobs, full payment lifecycle, provider reconciliation, and worker execution | deferred | WS04-02C does not redesign WS05 provider/job ownership. | `WS05` |
| Deployed database/provider logs, dashboards, alerts, and operational log access | deferred | This pass owns repository source logging only. | `WS09`, `WS10` |
| Deterministic database contention and lock ordering | covered_elsewhere | Accepted WS04-02B owns the direct concurrency proof. | WS04-02B compatibility scope |

## 9. Adequacy Conclusion

The selected evidence is adequate for WS04-02C when the focused PostgreSQL/static
tests, backend checker scope, compatibility scopes, and `git diff --check` pass.
All eight WS04-02C requirements have executable evidence in this trusted scope.
Later provider, final infrastructure, migration rehearsal, durable-worker, and
deployed observability evidence remains explicitly deferred to its owning passes
and is not claimed here.

Checker `PASS` is structural compliance only, not human adequacy by itself. This
record contains no literal credentials, credential-bearing URLs, raw sensitive
logs, unredacted errors, provider-private values, personal or payment data, local
machine paths, usernames, session state, internal chat material, or other
prohibited sensitive values.

## 10. Gate B Validation Results

| Validation | Result |
|---|---|
| Focused WS04-02C PostgreSQL/static pytest scope | `12 passed` |
| Backend test checker for `workflows/database_value_default_sql_safety_compatibility` | `PASS`; 12 collected pytest nodes; all 8 WS04-02C requirements mapped |
| Accepted WS04-01A/B/C and WS04-02A/B compatibility scopes | `116 passed` |

The compatibility run included database lifecycle/pool/role boundaries,
query/cursor database access behavior, production database verification,
transaction-boundary external side-effect safety, database invariants/locks/
deterministic concurrency, and operation-timeout contracts. The only correction
needed during compatibility validation was a test-harness class-identity fix for
WS04-02A fake-session assertions after another compatibility test reloads
`backend.models`; no transaction-boundary behavior was changed.
