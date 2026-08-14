# WS02-04C1 - Operation Timeouts And Cancellation

## At A Glance

| Field | Value |
|---|---|
| Pass | `WS02-04C1` |
| Track | `WS02-04` source-owned API boundary recheck |
| Type | Backend provider, database, configuration, and evidence pass |
| Primary controls | `API-M10`, `GOV-006` |
| Supporting controls | `API-M12`, `API-M19`, `DB-002`, `DB-004`, `DB-008`, `JOB-M05`, `PAY-002` |
| Authority basis | Current accepted repository tree; `GOV-006` / `FDN-04` evidence-based limit method; limits-and-thresholds register; WS02-04 source-owned closeout; WS02-04C2 retry/reconciliation policy; current backend timeout implementation |
| Depends on | `EN-01`, `EN-02`, `WS02-01`, `WS02-04A` |
| Trusted test scope | `backend/tests/platform/operation_timeouts/` |

## 1. Purpose

WS02-04C1 defines Pickup Lane's portable, source-owned timeout contract for the
backend operations that currently call private dependencies or hold database
resources during request handling.

In plain terms, this pass makes sure the backend does not wait forever for
Stripe, Firebase Admin, Cloudflare R2 metadata checks, SQLAlchemy pool
checkout, or PostgreSQL statements and locks. It also defines what the backend
may safely tell callers when a timeout happens.

C1 is intentionally operation-specific. It does not create a global request
deadline, route-family deadline, retry policy, rate limit, worker timeout,
provider dashboard setting, process-server setting, or permanent hosting
configuration. Those require later runtime, provider, or owner evidence.

The current production implementation for the C1 timeout contract already
exists in source. This recheck's pass-owned output is the reconciled canonical
plan plus fresh EN-01 trusted evidence and traceability proving the current
contract.

## 2. Why This Matters

Timeout behavior protects reliability and user trust. Without clear operation
bounds, a slow dependency can tie up API workers, hold database connections,
leave callers waiting with unclear results, or produce misleading local state.

The most important failure mode is an external mutation timing out after the
request was sent. For example, a Stripe refund creation timeout does not prove
the refund failed. The provider might still create it. Pickup Lane must not
blindly retry or record a definite provider failure from that local timeout
alone.

Database timeouts have a different risk profile. Pool wait, statement timeout,
and lock timeout protect backend resources from unbounded waits, but they do
not prove full database connection budgeting, transaction-duration policy,
deadlock recovery, or production-provider capacity. Those stay open for later
database and runtime evidence.

Cancellation is also different from timeout. A client disconnect or task
cancellation is not a proof that synchronous provider work stopped. C1 therefore
keeps cancellation as an internal classification and avoids claiming a public
client response for a request that is already gone.

## 3. Requirements

| ID | Requirement | What it means | Why it matters |
|---|---|---|---|
| `WS02-04C1-R1` | Timeout values are typed, positive, documented, and authority-aligned. | The eight C1 timeout settings must use the approved values from the limits register, be configurable through backend settings, reject invalid values, and be documented in tracked backend environment configuration. | Prevents undocumented or accidental timeout values and keeps `GOV-006` / `FDN-04` evidence discipline intact. |
| `WS02-04C1-R2` | Stripe read and mutation operations use separate timeout-owned clients and distinct timeout outcomes. | Stripe read/query calls use the read timeout and map timeout to dependency-read semantics. Stripe provider mutations use the mutation timeout and map timeout to unknown-outcome semantics. | Prevents slow reads from blocking indefinitely and prevents mutation timeouts from being treated as definite provider failure. |
| `WS02-04C1-R3` | Firebase Admin reads and deletion use the approved Admin HTTP timeout and correct outcome classes. | Token verification, user lookup, and email lookup use dependency-read timeout semantics. User deletion timeout is an unknown external mutation outcome. | Protects authentication/account flows without pretending an external deletion definitely succeeded or failed after timeout. |
| `WS02-04C1-R4` | R2 scope is metadata timeout ownership only. | R2 metadata `HEAD` checks use approved connect/read timeouts and dependency-read timeout semantics. Presigned URL generation is local signing, and browser direct upload behavior is not treated as backend network timeout evidence. | Prevents source evidence from falsely claiming direct object-upload or provider-runtime behavior. |
| `WS02-04C1-R5` | Database wait, statement, and lock timeout settings are installed at the source-owned database layer. | SQLAlchemy pool wait uses the approved pool timeout. Checked-out PostgreSQL sessions receive approved `statement_timeout` and `lock_timeout`, with lock timeout lower than statement timeout. Database timeout exceptions classify safely and request sessions close or roll back as owned by the current dependency behavior. | Bounds local database waits while preserving later evidence for full database capacity, topology, and concurrency closure. |
| `WS02-04C1-R6` | Public timeout responses use stable safe contracts. | Dependency-read, dependency-mutation-unknown, and database timeout categories produce stable safe public error contracts through the existing API error boundary, correlation, and EN-02 redaction/label primitives. | Prevents leaking provider IDs, database URLs, object keys, request content, credentials, stack traces, or arbitrary exception strings during timeout failures. |
| `WS02-04C1-R7` | Cancellation remains distinct from timeout and is not swallowed by C1 helpers. | C1 helpers classify `asyncio.CancelledError` separately, do not catch `BaseException`, and do not turn cancellation into a fake public timeout response. | Prevents misleading responses and avoids hiding client disconnect or task-cancellation behavior. |
| `WS02-04C1-R8` | Outcome-sensitive side effects preserve existing safe ordering and no-blind-replay behavior. | Provider mutation timeouts must not create local definite-success or definite-failure state solely from timeout. Existing idempotency, pending/processing, support-follow-up, rollback, reconciliation, and best-effort cleanup boundaries must remain explicit. | Prevents duplicate payment/refund/account side effects and preserves C2 retry/reconciliation ownership. |
| `WS02-04C1-R9` | Current provider and outbound operation inventory is complete for C1 scope. | Current production backend source must not contain another provider/network operation that bypasses C1-owned timeout taxonomy, or any such operation must be explicitly classified as local, out of scope, or later-owned. | Prevents a hidden outbound path from escaping timeout ownership. |
| `WS02-04C1-R10` | Later/runtime timeout obligations remain explicit and unclosed by local source tests. | Global request/response deadlines, DB connect timeout, pool sizing/overflow, deployment-wide connection budget, transaction duration, idle-session timeout, process-server and proxy timeouts, provider dashboard settings, live network behavior, retries, rate controls, worker shutdown, telemetry dashboards, alerts, and permanent-host alignment remain later or external evidence. | Prevents false closure of broader `API-M10`, `API-M19`, `GOV-006`, database, provider, job, and runtime obligations. |

### Requirement Declaration Design

Gate B must add `backend/tests/support/requirements/ws02_04c1.json` with these
stable declarations:

| Requirement ID | State | Scope | Source controls | Reason |
|---|---|---|---|---|
| `WS02-04C1-R1` | `required` | `platform/operation_timeouts` | `["API-M10", "GOV-006", "FDN-04", "WS02-04C1", "WS02-01"]` | none |
| `WS02-04C1-R2` | `required` | `platform/operation_timeouts` | `["API-M10", "GOV-006", "FDN-04", "WS02-04C1", "WS02-04C2", "PAY-002", "JOB-M05"]` | none |
| `WS02-04C1-R3` | `required` | `platform/operation_timeouts` | `["API-M10", "GOV-006", "FDN-04", "WS02-04C1", "WS03-02"]` | none |
| `WS02-04C1-R4` | `required` | `platform/operation_timeouts` | `["API-M10", "GOV-006", "FDN-04", "WS02-04C1", "WS06"]` | none |
| `WS02-04C1-R5` | `required` | `platform/operation_timeouts` | `["API-M10", "DB-004", "DB-008", "GOV-006", "FDN-04", "WS02-04C1"]` | none |
| `WS02-04C1-R6` | `required` | `platform/operation_timeouts` | `["API-M10", "API-M12", "EN-02", "WS02-04A", "WS02-04C1"]` | none |
| `WS02-04C1-R7` | `required` | `platform/operation_timeouts` | `["API-M10", "API-M19", "WS02-04C1", "WS02-04C2"]` | none |
| `WS02-04C1-R8` | `required` | `platform/operation_timeouts` | `["API-M10", "JOB-M05", "PAY-002", "GOV-006", "WS02-04C1", "WS02-04C2", "WS03-02", "WS05"]` | none |
| `WS02-04C1-R9` | `required` | `platform/operation_timeouts` | `["API-M10", "GOV-006", "WS02-04C1", "WS02-04C2", "WS02-04B1", "WS02-04B2A1", "WS02-04B2A2C"]` | none |
| `WS02-04C1-R10` | `deferred` | `governance` | `["API-M10", "API-M19", "DB-002", "GOV-006", "FDN-04", "WS02-04C1", "WS02-04C2", "WS02-04C3A", "WS02-04C3B", "WS04", "WS05", "WS06", "WS09", "WS10"]` | `Global request and response deadlines, DB connect timeout, pool size and overflow, deployment-wide connection budget, transaction duration, idle-session timeout, process-server and proxy behavior, provider dashboards, live network behavior, retries, rate controls, durable workers, shutdown, telemetry dashboards, alerts, and permanent-host/runtime evidence remain later or external responsibilities and cannot be closed by local C1 source tests. DB connect timeout, pool sizing, overflow, provider connection caps, and deployment instance/process connection consumption are DB-002 / WS04-owned later database evidence.` |

## 4. Technical Design / Contracts

### 4.1 Approved Timeout Values

The current approved C1 timeout values are:

| Operation class | Approved value | Current owner |
|---|---:|---|
| Stripe read/query operation | 6 seconds | backend typed setting |
| Stripe mutation operation | 15 seconds | backend typed setting |
| Firebase Admin HTTP operation | 8 seconds | backend typed setting |
| R2 metadata/HEAD connect | 2 seconds | backend typed setting |
| R2 metadata/HEAD read | 6 seconds | backend typed setting |
| SQLAlchemy pool wait | 2 seconds | backend typed setting |
| PostgreSQL statement timeout | 12000 milliseconds | backend typed setting applied to checked-out sessions |
| PostgreSQL lock timeout | 2000 milliseconds | backend typed setting applied to checked-out sessions |

These values are initial portable application policy values. They are
configurable and must be reassessed after real telemetry, load and failure
evidence, permanent runtime selection, provider evidence, or a superseding owner
decision.

The limits register is the current durable authority that records these
approved values. `FDN-04` supplies the method for approving numeric limits; it
does not approve numeric values by itself.

### 4.2 Typed Configuration Contract

The backend settings owner must expose the eight C1 timeout values as typed
backend settings. The settings parser must:

- use the approved defaults;
- accept positive integer overrides;
- reject zero, negative, and non-integer values;
- require `DB_LOCK_TIMEOUT_MILLISECONDS` to be lower than
  `DB_STATEMENT_TIMEOUT_MILLISECONDS`;
- register the environment variable names in the backend settings inventory;
- document the values in `backend/.env.example`;
- avoid frontend-public ownership or duplicate ad hoc environment parsing.

No Gate B production or tracked configuration correction is currently planned.
Current source already contains these settings, default values, registry
entries, validation behavior, and `.env.example` documentation.

### 4.3 Public Timeout Taxonomy

C1 has three public timeout categories:

| Category | Public meaning | Required public behavior |
|---|---|---|
| `API.DEPENDENCY_READ_TIMEOUT` | A required dependency read/query did not complete within the configured operation timeout. | HTTP 503 retry-later semantics with safe details only. |
| `API.DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN` | A provider mutation did not confirm its final provider outcome before timeout. | HTTP 503 semantics that do not claim the provider operation definitely failed. |
| `API.DATABASE_TIMEOUT` | A database pool wait, statement, or lock operation reached the configured bound. | HTTP 503 retry-later semantics with safe details only. |

The public error contract must integrate with the existing WS02-04A stable API
error boundary and EN-02 safe public-error/telemetry primitives. Public payloads
and labels must not include user IDs, provider IDs, payment IDs, object keys,
URLs, emails, tokens, request content, raw exception strings, database URLs,
credentials, private headers, or arbitrary text.

### 4.4 Stripe Contract

Stripe calls are split by operation class:

| Operation | Class | Timeout owner | Outcome on timeout |
|---|---|---|---|
| `stripe.setup_intent.retrieve` | read/query | Stripe read client | dependency-read timeout |
| `stripe.payment_method.retrieve` | read/query | Stripe read client | dependency-read timeout |
| `stripe.payment_intent.retrieve` | read/query | Stripe read client | dependency-read timeout |
| `stripe.refund.retrieve` | read/query | Stripe read client | dependency-read timeout |
| `stripe.customer.create` | mutation | Stripe mutation client | mutation unknown outcome |
| `stripe.setup_intent.create` | mutation | Stripe mutation client | mutation unknown outcome |
| `stripe.payment_intent.create` | mutation | Stripe mutation client | mutation unknown outcome |
| `stripe.payment_intent.confirm` | mutation | Stripe mutation client | mutation unknown outcome |
| `stripe.refund.create` | mutation | Stripe mutation client | mutation unknown outcome |
| `stripe.payment_method.detach` | mutation | Stripe mutation client | mutation unknown outcome |
| `stripe.customer.default_payment_method.set` | mutation | Stripe mutation client | mutation unknown outcome |
| `stripe.customer.default_payment_method.clear` | mutation | Stripe mutation client | mutation unknown outcome |

Stripe webhook event construction is local signature/body verification and not a
C1 provider network timeout path. Provider redelivery, webhook retry behavior,
and durable reconciliation are not C1 closure.

Stripe mutation timeouts must preserve C2 no-blind-replay ownership. C1 tests
should prove representative side-effect behavior, not every payment workflow in
the product. Required representative proofs include:

- local success state is not committed solely because a provider mutation timed
  out;
- local definite provider-failure state is not recorded solely because a
  provider mutation timed out;
- timeout-unknown flows preserve existing pending, processing,
  support-follow-up, rollback, idempotency, or reconciliation boundaries;
- the saved-card `detach_unpersisted_payment_method` path is classified as
  best-effort cleanup of an unpersisted provider object after a local rejection,
  not as a user-visible successful detach or reconciliation proof.

### 4.5 Firebase Admin Contract

Firebase Admin app initialization must set the configured Admin HTTP timeout.
The current C1 owned operation classes are:

| Operation | Class | Outcome on timeout |
|---|---|---|
| `firebase.token.verify` | read/query | dependency-read timeout |
| `firebase.user.lookup` | read/query | dependency-read timeout |
| `firebase.user.delete` | mutation | mutation unknown outcome |

Token verification includes both `verify_id_token` and the subsequent
`get_user` lookup. Email availability lookup uses `get_user_by_email`.

User deletion timeout must leave account deletion outcome uncertain and rely on
the existing pending/support/recovery state. C1 must not restore, finalize, or
claim provider deletion outcome from timeout alone.

Firebase credential loading, app reuse, and configuration errors are not
provider network timeout evidence.

### 4.6 R2 Metadata Contract

C1 owns only backend R2 metadata timeout behavior:

- the backend R2 client must use the approved metadata connect and read
  timeouts;
- `head_object` metadata verification timeout must map to
  dependency-read semantics;
- object-not-found and other storage errors remain distinct from timeout;
- presigned upload/read URL generation is local signing work and must not be
  represented as provider network timeout evidence.

Browser direct upload bytes, R2 object-byte limits, R2 dashboard/account
configuration, object lifecycle, malware scanning, and storage reconciliation
remain later storage/provider evidence.

### 4.7 Database Timeout Contract

C1 owns source-level database timeout installation and classification:

- the SQLAlchemy engine must use the approved pool acquisition wait timeout;
- checked-out PostgreSQL sessions must receive `statement_timeout` and
  `lock_timeout`;
- lock timeout must remain lower than statement timeout;
- SQLAlchemy pool timeout must classify as database pool wait timeout;
- PostgreSQL lock and statement timeout exceptions must classify as database
  timeout types;
- request-owned database sessions must roll back on ordinary exceptions and
  close in all cases.

C1 owns the current 2-second SQLAlchemy pool acquisition wait. C1 does not own
DB connect timeout, pool size, maximum overflow, recycle, pre-ping, provider
pooler settings, provider connection limits, API process count, worker count,
deployment-wide connection budgeting, transaction-duration limits,
idle-session limits, migration timeout policy, deadlock/serialization retry,
unknown-commit handling, or production concurrency evidence. Those
connection-budget items are DB-002 / WS04-owned later database evidence.

### 4.8 Cancellation Contract

Cancellation is not a public C1 timeout category. The timeout helpers must keep
`asyncio.CancelledError` distinct and must not catch `BaseException`.

The current runtime uses ordinary `except Exception` handling in timeout helper
call sites, so `asyncio.CancelledError` is not swallowed by those call sites.
Database session finalization still closes the session in `finally`.

C1 tests may inspect classification and exception handling, but they must not
claim process-server, ASGI server, proxy, browser, or deployed cancellation
behavior.

### 4.9 Provider Inventory And Negative Space

Current production backend source uses these private dependency SDK boundaries:

- Stripe through `backend/services/stripe_service.py`;
- Firebase Admin through `backend/firebase_admin_client.py`;
- Cloudflare R2/S3-compatible metadata and presigned URL helpers through
  `backend/services/r2_storage_service.py`;
- PostgreSQL through SQLAlchemy in `backend/database.py`.

Current production source search did not identify another direct `requests`,
`httpx`, `aiohttp`, `urllib.request`, raw socket, SendGrid, Twilio, SMTP,
Google, or Cloudflare API client path outside those boundaries. Manual seed and
bootstrap scripts are not production request-path timeout closure evidence.

Gate B evidence must include static inventory protection so a future production
provider/network path cannot silently bypass C1 classification.

## 5. Implementation Scope

### Pass-Owned Outputs

C1 owns these outputs for the current recheck:

- this canonical planning document;
- `backend/tests/support/requirements/ws02_04c1.json`;
- `backend/tests/platform/operation_timeouts/TESTING_RECORD.md`;
- fresh trusted tests under `backend/tests/platform/operation_timeouts/`.

### Production And Configuration Corrections

No production source or tracked configuration correction is currently approved
for Gate B. Current repository truth already includes:

- `backend/observability/timeouts.py` timeout taxonomy and helpers;
- `backend/observability/http_errors.py` public timeout integration;
- `backend/settings.py` C1 settings, defaults, validation, and registry;
- `backend/.env.example` C1 environment documentation;
- `backend/database.py` SQLAlchemy pool wait and checked-out PostgreSQL timeout
  settings;
- `backend/services/stripe_service.py` split Stripe read/mutation clients;
- `backend/firebase_admin_client.py` Firebase Admin HTTP timeout and timeout
  classification;
- `backend/services/r2_storage_service.py` R2 metadata timeout configuration
  and timeout classification.

Gate B must not change production behavior unless implementation evidence
proves this plan is wrong. If a production change becomes necessary, the pass
must return to Gate A for owner approval.

### Historical Provenance

The original implementation provenance is:

- original PR: `#119`, `WS02-04C1 add operation timeout semantics`;
- original branch: `pr/WS02-04C1`;
- original base: `a1fe08976a7f5d21aa3cea0e835e4fd067175fe0`;
- original head: `b088b00b54c8b2dea800fe2795e86b6ed19016e6`;
- original merge: `3ebdb50ae1dd73bbd971b59f05e65fb4f5e3af56`.

The original pass changed production/configuration timeout files and created
old tests under a pre-EN-01 testing architecture. Historical/pre-EN-01 tests are
provenance only and are not current trusted C1 evidence.

Material later evolution preserved the source-owned C1 contract and added
supporting adjacent contracts, especially C2 retry/reconciliation policy,
EN-02 observability safety, WS02-04A error behavior, and later WS02-04
request-boundary passes.

## 6. Testing And Evidence

### Trusted Evidence Scope

Gate B must create fresh trusted evidence under:

```text
backend/tests/platform/operation_timeouts/
```

This is an ordinary trusted platform scope. It must not use old `shared/` tests,
historical/pre-EN-01 tests, real provider network calls, production resources,
browser tests, or Playwright.

### Required Evidence Files

Gate B must add:

- `backend/tests/platform/operation_timeouts/TESTING_RECORD.md`;
- `backend/tests/platform/operation_timeouts/test_timeout_settings_contract.py`;
- `backend/tests/platform/operation_timeouts/test_stripe_timeout_contract.py`;
- `backend/tests/platform/operation_timeouts/test_firebase_timeout_contract.py`;
- `backend/tests/platform/operation_timeouts/test_r2_metadata_timeout_contract.py`;
- `backend/tests/platform/operation_timeouts/test_database_timeout_contract.py`;
- `backend/tests/platform/operation_timeouts/test_public_timeout_contract.py`;
- `backend/tests/platform/operation_timeouts/test_provider_operation_inventory_contract.py`;
- `backend/tests/platform/operation_timeouts/test_timeout_side_effect_ordering_contract.py`.

### Evidence Design

| Requirement(s) | Scenario group | Proof layer | Required evidence |
|---|---|---|---|
| `WS02-04C1-R1` | approved defaults, positive overrides, invalid values, lock lower than statement, env registry, `.env.example`, backend-only ownership | settings/static pytest | Build settings from controlled env dictionaries; inspect backend config and repository text. |
| `WS02-04C1-R2` | Stripe read/mutation client timeout selection and timeout translation | unit/static pytest with provider fakes | Patch Stripe client construction and operation calls at the app-owned wrapper boundary; do not call Stripe. |
| `WS02-04C1-R3` | Firebase Admin HTTP timeout, read timeout mapping, deletion unknown mapping | unit pytest with Firebase Admin fakes | Patch Firebase Admin app/auth boundary; do not call Firebase. |
| `WS02-04C1-R4` | R2 metadata connect/read settings, HEAD timeout mapping, presigned URL local-signing boundary | unit/static pytest with R2 fakes | Patch boto3/botocore boundary; do not call R2. |
| `WS02-04C1-R5` | SQLAlchemy pool timeout setting, PostgreSQL checked-out `SET` calls, timeout classification, rollback/close behavior | narrow PostgreSQL integration plus unit/static pytest | Use the dedicated local PostgreSQL test database to prove a real checked-out application connection receives the configured `statement_timeout` and `lock_timeout` values. Use lower-layer unit/synthetic exception-chain proof for pool wait, statement-timeout, lock-timeout, and rollback/close classification where the real database is not necessary. |
| `WS02-04C1-R6` | public timeout error payloads, safe detail/details, correlation, telemetry labels, no sensitive leakage | TestClient/unit pytest | Exercise public error boundary with synthetic timeout exceptions and sensitive markers. |
| `WS02-04C1-R7` | cancellation distinct from timeout, helpers do not swallow cancellation, ordinary C1 call-site catches do not catch `BaseException` | unit/static pytest | Inspect helper behavior and representative call-site exception boundaries. |
| `WS02-04C1-R8` | representative provider mutation timeout side effects, no local definite failure/success from timeout, existing pending/support/recovery behavior | unit/service pytest with fakes and database where needed | Verify representative checkout/payment/refund/Firebase/saved-card boundaries without broad payment-system reimplementation. |
| `WS02-04C1-R9` | production outbound/provider operation inventory and bypass search | static pytest | Search production backend source for direct network/provider SDK paths and classify allowed boundaries. |
| `WS02-04C1-R10` | later/runtime/provider gaps remain explicit | requirement declaration and testing record | Deferred zero-mapped requirement plus testing record non-closure. |

### Evidence Quality Rules

Gate B proof-layer decisions are frozen as:

- PostgreSQL is required for R5, but only for the smallest database integration
  proof that cannot be established as confidently through static or unit
  evidence.
- `test_database_timeout_contract.py` must use the dedicated local PostgreSQL
  test database to prove a real checked-out application connection receives the
  configured source-owned values: `statement_timeout` resolves to
  12000 milliseconds / 12 seconds, `lock_timeout` resolves to
  2000 milliseconds / 2 seconds, and both values are actually present on a real
  checked-out connection.
- The PostgreSQL proof must not use a 12-second sleep or an artificial 2-second
  lock wait.
- SQLAlchemy pool wait timeout classification, psycopg/SQLAlchemy
  statement-timeout exception classification, psycopg/SQLAlchemy lock-timeout
  exception classification, and request-owned rollback/close behavior should use
  lower-layer unit/static or synthetic exception-chain proof where the real
  database is not necessary.
- Live provider or network access is not required and is prohibited for
  ordinary trusted C1 evidence.
- Browser and Playwright proof are not required.
- Migration or schema-history proof is not required.
- Genuine concurrency or race proof is not required.
- Controlled-time proof is not required.

Gate B tests must:

- fake external providers at Pickup Lane's wrapper boundary, not by mocking away
  the C1 business rule being proven;
- avoid real provider network calls and production resources;
- use PostgreSQL only for the frozen narrow R5 integration proof;
- prove rejected-side-effect behavior where a timeout could otherwise create
  misleading state;
- avoid uncontrolled sleeps or flaky timing;
- generate exact pytest traceability from requirement markers, not manually
  maintained node lists.

### Required Validation

Gate B validation must include:

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/platform/operation_timeouts
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/platform/operation_timeouts backend/tests/platform/observability backend/tests/platform/api_errors backend/tests/platform/settings backend/tests/platform/runtime
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/checker backend/tests/workflows backend/tests/platform
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/checker
DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/platform/operation_timeouts
DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python backend/tests/check_backend_tests.py --scope suite
backend/.venv/bin/python -m py_compile backend/observability/timeouts.py backend/observability/http_errors.py backend/settings.py backend/database.py backend/firebase_admin_client.py backend/services/stripe_service.py backend/services/r2_storage_service.py backend/tests/platform/operation_timeouts/test_timeout_settings_contract.py backend/tests/platform/operation_timeouts/test_stripe_timeout_contract.py backend/tests/platform/operation_timeouts/test_firebase_timeout_contract.py backend/tests/platform/operation_timeouts/test_r2_metadata_timeout_contract.py backend/tests/platform/operation_timeouts/test_database_timeout_contract.py backend/tests/platform/operation_timeouts/test_public_timeout_contract.py backend/tests/platform/operation_timeouts/test_provider_operation_inventory_contract.py backend/tests/platform/operation_timeouts/test_timeout_side_effect_ordering_contract.py
git diff --check
```

The full current trusted backend regression is the current executable trusted
roots that exist at this baseline: `backend/tests/checker`,
`backend/tests/workflows`, and `backend/tests/platform`.

Gate B must confirm generated traceability maps `WS02-04C1-R1` through
`WS02-04C1-R9` to trusted executable evidence and leaves `WS02-04C1-R10`
zero-mapped and deferred.

## 7. Integration / Operational Expectations

C1 integrates with:

- WS02-04A stable API error contracts, because timeout failures become safe
  public API errors;
- EN-02 observability/privacy primitives, because timeout labels and public
  error details must remain bounded and redacted;
- WS02-04C2 retry/reconciliation policy, because C1 timeout outcomes feed the
  later no-blind-replay and durable-repair model;
- account deletion and payment/refund workflows, because Firebase and Stripe
  mutation timeouts can create unknown external outcomes;
- R2 venue-image workflows, because metadata verification is the only backend
  R2 network timeout path in C1 scope;
- later runtime, database, job, storage, telemetry, and provider-evidence
  passes, because C1 intentionally does not close those layers.

Future code that adds a new backend provider/network operation must either use
an existing C1-classified boundary or explicitly assign ownership in a later
approved pass.

## 8. Not Part Of This Pass

C1 does not implement or prove:

- a global API request deadline;
- a response deadline;
- route-family deadlines;
- process-server, proxy, ingress, edge, or permanent-host timeout settings;
- DB connect timeout;
- DB pool size, maximum overflow, provider connection budget, deployment-wide
  connection budget, or instance/process connection consumption, which remain
  DB-002 / WS04-owned later database evidence;
- transaction-duration timeout, idle-in-transaction timeout, deadlock retry,
  serialization retry, or unknown-commit recovery;
- migration timeout policy;
- provider dashboard settings or live provider behavior;
- Stripe, Firebase, or R2 retry counts, backoff, jitter, or SDK retry mode;
- durable workers, queues, leases, shutdown, or background recovery;
- rate limits, abuse controls, concurrency caps, or provider-cost controls;
- dashboards, alerts, telemetry retention, SLOs, or production monitoring;
- browser cancellation, frontend request cancellation, or Playwright evidence;
- direct R2 object-byte enforcement or storage lifecycle evidence.

## 9. Related Controls And Remaining Evidence

| Control / Decision | What this pass establishes | What remains later |
|---|---|---|
| `API-M10` | Source-owned operation timeout categories, eight approved timeout values, provider/database timeout classification, cancellation distinction, and safe local outcome semantics. | Layered connection, global request/response, proxy/process-server, runtime, worker, provider-dashboard, telemetry, and permanent-host timeout evidence. |
| `GOV-006` / `FDN-04` | Uses the approved evidence-based method and the limits register's C1 numeric values without inventing new values. | Reassessment after telemetry, load/failure evidence, runtime selection, provider evidence, or superseding owner decision. |
| `API-M12` / `WS02-04A` | Timeout failures integrate with safe stable API error contracts. | Broader API error and HTTP behavior remains with its owning passes. |
| `EN-02` | Timeout labels and public error details use bounded safe observability primitives. | Production dashboards, alerts, and runtime observability remain later evidence. |
| `DB-002` / `WS04` | C1 explicitly preserves the handoff for DB connect timeout, pool sizing, maximum overflow, provider connection caps, process counts, and deployment-wide connection budgeting. | Later database work must decide and prove the deployment-wide connection budget and provider/runtime capacity. |
| `DB-004` / `DB-008` | Local database pool wait, statement timeout, lock timeout, classification, rollback, and close behavior are source-owned. | Full database topology, concurrency, deadlock/serialization, unknown-commit, migration, and provider evidence remains open. |
| `PAY-002` / `JOB-M05` | Provider mutation timeout unknown-outcome semantics avoid definite local failure/success and preserve no-blind-replay boundaries. | Full payment, webhook, reconciliation, durable retry, Stripe test-mode, and provider evidence remain later. |

### Supporting Relationships

WS02-04C2 owns retry/reconciliation/backpressure classifications and must not
be silently replaced by C1. WS02-04C3A and WS02-04C3B own rate and provider-cost
controls. DB-002 / WS04 own the later deployment-wide database connection
budget, including connect timeout, pool sizing, maximum overflow, provider
connection caps, and instance/process connection consumption. WS05 owns durable
work and job recovery. WS06 owns storage provider evidence beyond metadata HEAD.
WS09 owns production observability evidence. WS10 owns release and operational
proof where applicable.

## 10. Completion Criteria

- [ ] This canonical plan matches current authority and repository truth.
- [ ] No unresolved owner decision is required for C1.
- [ ] No production or tracked configuration correction is required; if evidence
  disproves this, the pass returns to Gate A.
- [ ] `backend/tests/support/requirements/ws02_04c1.json` exists and declares
  `WS02-04C1-R1` through `WS02-04C1-R10` with the states/scopes/source controls
  defined here.
- [ ] `backend/tests/platform/operation_timeouts/TESTING_RECORD.md` explains
  risks, scenario groups, evidence layers, side effects, and non-closure without
  duplicating every pytest node ID.
- [ ] Fresh trusted tests under `backend/tests/platform/operation_timeouts/`
  prove `WS02-04C1-R1` through `WS02-04C1-R9`.
- [ ] `WS02-04C1-R10` remains zero-mapped and deferred.
- [ ] Focused C1 tests pass.
- [ ] Adjacent platform regressions pass.
- [ ] Full current trusted backend regression passes across `checker`,
  `workflows`, and `platform`.
- [ ] Checker domain scope for `backend/tests/platform/operation_timeouts`
  passes.
- [ ] Checker suite scope passes.
- [ ] Generated traceability is complete and current.
- [ ] Python syntax/compile validation for changed Python files passes.
- [ ] `git diff --check` passes.
- [ ] No provider/runtime/later-pass closure is overclaimed.
- [ ] Gate B verifies this approved canonical plan's SHA-256 remains unchanged.

## Gate B Frozen Editable Set

Gate B may edit exactly these files:

1. `backend/tests/support/requirements/ws02_04c1.json`
2. `backend/tests/platform/operation_timeouts/TESTING_RECORD.md`
3. `backend/tests/platform/operation_timeouts/test_timeout_settings_contract.py`
4. `backend/tests/platform/operation_timeouts/test_stripe_timeout_contract.py`
5. `backend/tests/platform/operation_timeouts/test_firebase_timeout_contract.py`
6. `backend/tests/platform/operation_timeouts/test_r2_metadata_timeout_contract.py`
7. `backend/tests/platform/operation_timeouts/test_database_timeout_contract.py`
8. `backend/tests/platform/operation_timeouts/test_public_timeout_contract.py`
9. `backend/tests/platform/operation_timeouts/test_provider_operation_inventory_contract.py`
10. `backend/tests/platform/operation_timeouts/test_timeout_side_effect_ordering_contract.py`

Gate B must not modify production source, tracked configuration, governance
registers, provider/runtime artifacts, or unrelated tests unless Gate B evidence
proves this frozen design is wrong and the pass returns to Gate A for approval.

Gate B must verify this approved canonical plan's SHA-256 remains unchanged.

The complete expected pass change set is exactly 11 files:

1. `docs/production-readiness/planning/ws02-04c1-operation-timeouts-cancellation.md`
2. `backend/tests/support/requirements/ws02_04c1.json`
3. `backend/tests/platform/operation_timeouts/TESTING_RECORD.md`
4. `backend/tests/platform/operation_timeouts/test_timeout_settings_contract.py`
5. `backend/tests/platform/operation_timeouts/test_stripe_timeout_contract.py`
6. `backend/tests/platform/operation_timeouts/test_firebase_timeout_contract.py`
7. `backend/tests/platform/operation_timeouts/test_r2_metadata_timeout_contract.py`
8. `backend/tests/platform/operation_timeouts/test_database_timeout_contract.py`
9. `backend/tests/platform/operation_timeouts/test_public_timeout_contract.py`
10. `backend/tests/platform/operation_timeouts/test_provider_operation_inventory_contract.py`
11. `backend/tests/platform/operation_timeouts/test_timeout_side_effect_ordering_contract.py`
