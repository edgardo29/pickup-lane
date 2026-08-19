# WS02-04C3B - Provider-Cost Rate Limit Deferral

## At A Glance

| Field | Value |
|---|---|
| Pass | `WS02-04C3B` |
| Track | `WS02` |
| Type | API / governance and evidence-deferral |
| Primary controls | `API-M11`, `GOV-006` / `FDN-04` |
| Authority basis | Current accepted repository tree; `API-M11`; `GOV-006` / `FDN-04`; `limits-and-thresholds-register.md`; WS02-04 source-owned closeout; accepted `WS02-04C1`, `WS02-04C2`, `WS02-04C3A`, and `WS02-04B2A2B2` |
| Depends on | EN-01, EN-02, WS02-04A, WS02-04C1, WS02-04C2, WS02-04C3A, WS02-04B2A2B2 |
| Trusted test scope | `backend/tests/platform/provider_cost_rate_limits` |

## 1. Purpose

WS02-04C3B decides what Pickup Lane can honestly say today about
source-owned rate limits for provider-cost and financial-action workflows.

Some workflows can create or mutate Stripe objects, read Firebase or R2
provider state, or perform financial repair work. Those operations can matter
for abuse, provider quota, provider cost, and recovery. A rate limit would be a
real product and operations policy, not just a code pattern, because it must
choose who is limited, what counts as an attempt, which provider or local
resource is protected, how legitimate retries recover, and what happens when
the limiter cannot read or write its state.

The current authoritative conclusion is that C3B does not approve any new
source-owned provider-cost/action limiter. The pass preserves that decision,
updates the current inventory, and creates trusted repository evidence proving
the deferral and boundary are truthful.

## 2. Why This Matters

Provider-cost and financial actions sit between two risks:

- repeated calls can create unwanted provider load, cost, quota pressure, or
  financial-support noise;
- blunt throttles can break legitimate payment recovery, card setup sync,
  refund repair, account cleanup, provider redelivery, or administrator
  remediation after an unknown outcome.

`GOV-006` / `FDN-04` requires evidence before Pickup Lane approves numeric
limits. A safe C3B result is therefore not "add a limiter somewhere." It is:

- inventory current provider-cost/action surfaces;
- distinguish rate controls from primary correctness and recovery safeguards;
- confirm whether any current evidence justifies a max/window/key/storage
  policy;
- if not, preserve the evidence-dependent deferral and exact future evidence
  needed before a limiter can be authorized.

## 3. Requirements

| ID | Requirement | What it means | Why it matters |
|---|---|---|---|
| `WS02-04C3B-R1` | The current provider-cost/action inventory is complete for this pass. | C3B must account for current authenticated, privileged, provider-cost, provider-read, provider-mutation, financial repair, webhook/redelivery, and storage-provider surfaces that materially interact with rate/abuse ownership. | A stale candidate list can hide a real abuse surface or route work to the wrong owner. |
| `WS02-04C3B-R2` | No numeric rate policy is approved without `GOV-006` / `FDN-04` evidence. | C3B must not invent a maximum, window, limiter key, rate-limit `Retry-After`, storage, retention, telemetry, rollout, rollback, or cross-instance policy from source shape, plausible abuse, current provider objects, product caps, or conventional values. | Unjustified limits can block legitimate users, disrupt recovery, or create false control closure. |
| `WS02-04C3B-R3` | Every material candidate has an explicit current disposition. | The plan and evidence must say whether each workflow is evidence-dependent, explicit no-additional-C3B-limiter, external/later-owned, retired, local-only, or outside C3B scope. | Reviewers need to know whether C3B intentionally deferred work or missed it. |
| `WS02-04C3B-R4` | Rate limiting stays separate from primary correctness and recovery safeguards. | Authentication, authorization, state validation, row locks, product caps, idempotency keys, provider reads, webhook signatures, request-size limits, C1 timeouts, and C2 retry/reconciliation are not mislabeled as C3B rate controls. | Existing safeguards protect correctness; they do not automatically prove provider-cost abuse controls. |
| `WS02-04C3B-R5` | Limiter state, storage, and migrations remain unapproved until a future policy exists. | C3B must not add a generic PostgreSQL limiter table, Redis/shared limiter, migration, retention rule, failure policy, or durable attempt model without an approved workflow-specific numeric policy. | Limiter state design depends on what counts as an attempt and how false positives/recovery behave. |
| `WS02-04C3B-R6` | Current source-owned non-chat rate-control negative space is truthful. | C3B must prove that accepted source currently has no C3B-owned non-chat limiter, no generic rate middleware, no alternate non-chat `API.RATE_LIMITED` producer, and no hidden source-owned provider-cost limiter. C3A chat limiting must remain the only approved source-owned rate limit. | Prevents accidental, unsupported rate policy from appearing outside the approved C3A boundary. |
| `WS02-04C3B-R7` | Cross-pass boundaries and tracked artifacts remain consistent. | C3B must preserve C1 timeout ownership, C2 retry/reconciliation/backpressure ownership, C3A chat-rate ownership, B2A2B2 provider/payment input ownership, WS05 durable financial/reconciliation handoffs, WS09 observability/capacity handoffs, and the limits register/source-owned closeout boundary. | API-M11 remains broader than C3B; ownership must stay explicit after this pass. |
| `WS02-04C3B-R8` | External/runtime/provider/API-M11 gaps remain open and not falsely closed. | Provider dashboards, real provider quotas/costs, production request volume, abuse signals, trusted client IP, forwarded-header trust, edge/WAF/CAPTCHA/auth-provider controls, runtime/load behavior, and monitoring/alert thresholds require later or external evidence. | Local source review cannot prove deployed abuse-control or provider-control-plane facts. |

## 4. Technical Design / Contracts

### 4.1 Authority For Numeric Rate Decisions

**What this is**

C3B uses the approved `GOV-006` / `FDN-04` evidence method for rate-limit
decisions. That method permits a value only when the protected resource,
failure mode, enforcing layers, owner, provider/platform constraints, expected
workload, abuse risk, failure cost, recovery behavior, configurability,
boundary tests, multi-instance behavior, telemetry, rollback behavior, and
reassessment triggers are documented.

**Contract / required behavior**

C3B must not approve or implement any of the following without that evidence:

- a maximum request or action count;
- a time window;
- a limiter key, scope, actor, token, user, resource, provider-object, IP, or
  admin boundary;
- rate-limit `Retry-After` semantics;
- limiter failure behavior;
- PostgreSQL, Redis, in-memory, provider-dashboard, edge, or auth-provider
  limiter state;
- limiter-state retention;
- telemetry or alert thresholds;
- rollout, rollback, or safe-adjustment procedure.

These are not adequate numeric authority by themselves:

- the current source implementation;
- existing database capacity;
- product collection caps;
- frontend pending or disabled buttons;
- timeout values;
- provider object shape;
- provider idempotency keys;
- SDK defaults;
- uniqueness constraints;
- plausible abuse;
- conventional rate-limit values.

**Why**

Provider-cost limiter values affect product access, payment recovery, support
repair, and provider behavior. Guessing values would close an audit box while
creating a real production policy without evidence.

### 4.2 Current Provider-Cost / Action Inventory

| Workflow group | Current entry point / actor | Provider work | Existing primary safeguards | C2 class / owner | C3B disposition |
|---|---|---|---|---|---|
| Checkout PaymentIntent create/confirm | `POST /checkout/games/{game_id}/payment-intent`; authenticated verified user | Stripe PaymentIntent create and confirm; provider read before confirmation decisions | game lock, capacity validation, pending checkout reuse, server-owned amounts, credit reservation, payment-row/provider checkpoint, C1 timeouts, B2A2B2 return-url/input ownership | create before checkpoint is `NO_AUTOMATIC_RETRY`; confirm after checkpoint is `RECONCILE_BEFORE_RETRY`; WS05 owns durable post-expiry reconciliation | Evidence-dependent future candidate; no current max/window/key/storage policy approved. |
| Saved-card customer/setup/sync | `/user-payment-methods/setup-intent` and `/user-payment-methods/sync`; authenticated active user | Stripe customer create, SetupIntent create, SetupIntent retrieve, PaymentMethod retrieve, best-effort detach, possible default update | active user, local active-card cap, provider/customer ownership checks, duplicate/fingerprint handling, B2A2B2 opaque SetupIntent bounds, C1 timeouts | customer create is idempotent; setup create is `NO_AUTOMATIC_RETRY`; sync reads are safe; cleanup/default updates are recovery-sensitive | Setup is a strong future candidate, but pre-persistence attempts are not durably represented. Sync/default/detach need recovery-safe treatment. No current limiter approved. |
| Community-game publish fee | `POST /community-games/publish`; authenticated host | Stripe PaymentIntent create and confirm | host/game state checks, paid-attempt uniqueness, server-owned fee, attempt/payment rows, idempotency key, C1 timeout handling | create is `NO_AUTOMATIC_RETRY`; confirm is `RECONCILE_BEFORE_RETRY`; WS05 owns durable financial reconciliation | Evidence-dependent future candidate; no host/user max or window approved. |
| Waitlist auto-promotion payment | internal waitlist promotion service; system/admin-triggered through game state | Stripe PaymentIntent create and confirm for paid promotion | ordered waitlist state, game/capacity checks, processing state, payment row, idempotency key, sequential locked workflow | `RECONCILE_BEFORE_RETRY`; WS05 durable payment reconciliation | Explicit no-additional-C3B-limiter. Not a direct user retry loop; blunt throttling could interfere with legitimate promotion/recovery. |
| Refund retry/reconcile and financial repair | `/admin/money/...`; recent active admin | Stripe refund create/retrieve; local credit retry has no provider mutation | recent admin authorization, money-issue state gates, admin action/idempotency keys, refund/payment state, C1 timeout handling | manual repair / reconcile-before-retry; WS05 durable financial reconciliation | Explicit no-additional-C3B-limiter. Rate controls are not the primary safeguard for operator repair. |
| Official-game cancellation and player-removal refunds | `/admin/official-games/{game_id}/cancel` and `/participants/{participant_id}/remove`; admin | Stripe refund create per eligible payment | recent/admin authorization, preview/execute flow, state gates, deterministic refund idempotency, money issue follow-up, sequential refund loop | `RECONCILE_BEFORE_RETRY`; WS05 durable financial reconciliation | Explicit no-additional-C3B-limiter. Future durable worker/concurrency policy belongs outside C3B. |
| Account deletion cleanup | `/auth/account`, `/auth/unfinished-account`, admin delete workflow; user or admin | Firebase delete; Stripe saved-card detach loop | recent user/admin gates, pending deletion state, active-admin preservation, support/partial-failure records, saved-card row locks | `RECONCILE_BEFORE_RETRY`; WS05 durable account-cleanup recovery | Explicit no-additional-C3B-limiter. Recovery and support visibility are primary. Broader auth-abuse controls remain later. |
| Firebase identity and email checks | normal authenticated dependencies, `/auth/sync-user`, `/auth/email-availability` | Firebase token verification and user/email lookups | authentication dependency, local user sync/state checks, C1 timeout handling | safe reads; identity/abuse ownership later with WS03/WS09/provider evidence | Outside C3B source-limiter approval. Anonymous/public and auth-provider abuse controls remain API-M11/later evidence. |
| Venue-image upload authorization/completion/read URL signing | admin venue-image routes and read builders | R2 metadata `HEAD` on completion; presigned upload/read URL generation is local signing, and direct browser-to-R2 upload is outside local backend provider proof | admin authorization, content type and size checks, selected-image cap, venue/image state, R2 metadata timeout handling, source-owned route/schema bounds | R2 metadata read is safe read; storage lifecycle/reconciliation later with WS06 | Explicit no-additional-C3B-limiter. Upload size/type/count protect the product surface; direct browser-to-R2 upload and R2 provider quota/evidence remain external/later. |
| Stripe webhook processing | `POST /stripe/webhook`; provider-originated | Stripe signature construction; provider redelivery; local event processing | signed webhook, raw body limit, provider event ID dedupe, local idempotent processing | `PROVIDER_REDELIVERY`; provider dashboard/redelivery settings external | Explicit no-additional-C3B-limiter. Do not block provider redelivery with an app-source user/admin throttle. |
| Game-credit issue/reverse | `/admin/game-credits/...`; recent active admin | No provider mutation; local ledger mutation | recent admin authorization, source-owned eligibility, idempotency key, server-owned amount, ledger state | local manual repair / ledger ownership | Local-only for C3B; not a provider-cost rate candidate. |
| Retired generic payment/refund/payment-event/host-publish-fee/image routes | tombstone routes | None | route retired with stable error behavior | Not applicable | Retired; not a current provider-cost/action candidate except where replacement workflows above own behavior. |

### 4.3 Candidate Disposition Rules

C3B classifies a workflow as an evidence-dependent future rate candidate only
when all of these are true:

- the current source can materially cause repeated provider cost, quota
  pressure, provider object creation, financial provider work, or provider
  read load;
- existing correctness safeguards do not address the distinct abuse/cost risk;
- legitimate recovery would not be harmed by a limiter, or a future policy can
  explicitly handle that harm;
- an approved evidence package can define max/window/key/failure/storage/
  retention/telemetry/rollout values.

C3B classifies a workflow as explicit no-additional-C3B-limiter when the
current source-owned safeguards, C1/C2 recovery model, route ownership, or
provider-redelivery model makes a C3B source limiter unsupported or harmful
without new owner evidence.

C3B classifies a workflow as outside C3B when it is anonymous/public abuse,
auth-provider policy, edge/WAF/CAPTCHA, provider-dashboard configuration,
runtime/load/capacity, monitoring/alerts, or another pass-owned control.

### 4.4 Attempt State And Limiter State

The current domain records do not represent every possible attempt for the
evidence-dependent candidates:

- saved-card SetupIntent creation uses a request-local idempotency key, and a
  pre-response timeout does not create a durable local setup-attempt record;
- checkout and community publish create-timeout paths can roll back local
  rows before a provider object identity is checkpointed;
- sync, provider reads, and cleanup attempts are recovery operations and not
  all attempted reads or failed attempts are durable rate-limit counters;
- admin repair and refund attempts are represented by domain/support state,
  but that state is for financial correctness, not a general rate window.

Therefore C3B does not approve a generic limiter table, Redis/shared limiter,
or migration. Future limiter state requires an approved workflow-specific
policy first.

### 4.5 Cross-Pass Boundaries

- C1 owns current source-configured operation timeouts and timeout failure
  classification. C3B does not change timeout values.
- C2 owns retry/reconciliation/backpressure classification. C3B must not add a
  blunt throttle that contradicts reconcile-before-retry, manual repair,
  provider redelivery, or WS05 durable handoff contracts.
- C3A owns the approved source-owned authenticated chat limiter only: five
  visible text messages per sender per chat per rolling 60-second window for
  game chat and Need-a-Sub chat. C3B must not reuse that value elsewhere.
- B2A2B2 owns provider/payment input ownership and server-owned financial
  source validation. C3B does not reopen those contracts.
- WS05 owns durable jobs, provider unknown-outcome reconciliation, durable
  financial repair, and account-cleanup recovery.
- WS06 owns later storage/R2 object lifecycle and reconciliation.
- WS09 owns monitoring, metrics, dashboards, alerts, capacity, cost model, and
  operational telemetry thresholds.
- WS03 owns broader identity/auth-provider evidence where API-M11 depends on
  account, token, recovery, App Check, MFA, or auth-provider controls.

## 5. Implementation Scope

### Production correction set

NONE.

Gate B must not modify production application behavior, provider clients,
route behavior, retry policy implementation, limiter middleware, settings,
schemas, migrations, or frontend behavior.

### Configuration correction set

NONE.

Gate B must not add rate-limit settings, environment variables, provider
dashboard configuration, Redis configuration, or deployment configuration.

### Gate A canonical plan artifact

- `docs/production-readiness/planning/passes/ws02/ws02-04c3b-provider-cost-rate-limit-deferral.md`

This canonical plan is the Gate A plan artifact. After human approval, it is
frozen and is not a Gate B editable file.

The limits register and WS02-04 source-owned closeout already preserve the
material C3B deferral/API-M11 partial boundary. Gate B may not edit them unless
a future Gate A re-entry authorizes a correction.

### Exact Gate B editable set

- `backend/tests/support/requirements/ws02_04c3b.json`
- `backend/tests/platform/provider_cost_rate_limits/TESTING_RECORD.md`
- `backend/tests/platform/provider_cost_rate_limits/test_provider_cost_inventory_contract.py`
- `backend/tests/platform/provider_cost_rate_limits/test_provider_cost_rate_limit_deferral_contract.py`
- `backend/tests/platform/provider_cost_rate_limits/test_non_chat_rate_limit_negative_space_contract.py`
- `backend/tests/platform/provider_cost_rate_limits/test_c3b_boundary_and_handoff_contract.py`

### Complete expected pass change set

The complete expected pass change set is exactly seven files: this frozen
canonical plan artifact plus the six Gate B editable files listed above.

## 6. Testing And Evidence

### Requirement declarations

Gate B must create `backend/tests/support/requirements/ws02_04c3b.json` with
these declarations:

| ID | State | Scope | Source controls | Reason |
|---|---|---|---|---|
| `WS02-04C3B-R1` | `required` | `platform/provider_cost_rate_limits` | `["API-M11", "GOV-006", "FDN-04", "WS02-04C3B", "WS02-04C2"]` | Not required. |
| `WS02-04C3B-R2` | `required` | `platform/provider_cost_rate_limits` | `["API-M11", "GOV-006", "FDN-04", "WS02-04C3B"]` | Not required. |
| `WS02-04C3B-R3` | `required` | `platform/provider_cost_rate_limits` | `["API-M11", "GOV-006", "FDN-04", "WS02-04C3B", "WS02-04C2", "WS02-04C3A"]` | Not required. |
| `WS02-04C3B-R4` | `required` | `platform/provider_cost_rate_limits` | `["API-M11", "API-M10", "GOV-006", "FDN-04", "WS02-04C1", "WS02-04C2", "WS02-04B2A2B2", "WS02-04C3B"]` | Not required. |
| `WS02-04C3B-R5` | `required` | `platform/provider_cost_rate_limits` | `["API-M11", "GOV-006", "FDN-04", "WS02-04C3B", "WS04", "WS05"]` | Not required. |
| `WS02-04C3B-R6` | `required` | `platform/provider_cost_rate_limits` | `["API-M11", "GOV-006", "FDN-04", "WS02-04C3A", "WS02-04C3B"]` | Not required. |
| `WS02-04C3B-R7` | `required` | `platform/provider_cost_rate_limits` | `["API-M11", "API-M10", "API-M12", "GOV-006", "FDN-04", "WS02-04C1", "WS02-04C2", "WS02-04C3A", "WS02-04B2A2B2", "WS05", "WS06", "WS09"]` | Not required. |
| `WS02-04C3B-R8` | `deferred` | `governance` | `["API-M11", "API-M19", "GOV-006", "FDN-04", "OPS-010", "OPS-011", "OPS-016", "WS02-03", "WS02-04C3B", "WS03", "WS05", "WS06", "WS09", "WS10"]` | `Provider dashboards, real provider quotas and cost pressure, production request volume, abuse signals, trusted client-IP identity, forwarded-header trust, edge/WAF/CAPTCHA/auth-provider controls, runtime/load behavior, monitoring, alert thresholds, and full API-M11 closure remain later or external responsibilities and cannot be closed by local C3B source tests.` |

### Trusted evidence files

| Evidence file | Required proof |
|---|---|
| `test_provider_cost_inventory_contract.py` | Current C2 provider-operation registry and relevant source entry points cover the material C3B inventory; historical candidates, newly identified provider surfaces, retired generic routes, and local-only credit paths are classified truthfully. |
| `test_provider_cost_rate_limit_deferral_contract.py` | C3B documentation, the limits register, and WS02-04 closeout agree that provider-cost/action values are not approved, API-M11 remains partial, no numeric C3B policy exists, and no limiter state/migration is approved. |
| `test_non_chat_rate_limit_negative_space_contract.py` | Current accepted source has no C3B-owned non-chat limiter, generic rate-limit middleware, Redis/in-memory/provider-cost counter, alternate non-chat `API.RATE_LIMITED` producer, or non-chat rate-limit `Retry-After` producer; C3A chat remains the only approved source-owned rate limiter. |
| `test_c3b_boundary_and_handoff_contract.py` | C1, C2, C3A, B2A2B2, WS05, WS06, WS09, and external/provider evidence boundaries remain preserved; C3B does not claim provider dashboards, edge/runtime controls, or full API-M11 closure. |

`TESTING_RECORD.md` must explain the evidence quality and the non-executable
facts: absence of accepted external evidence, provider dashboard state,
production traffic, runtime/load behavior, and future owner decisions.

### Validation frozen for Gate B

Gate B must run:

```bash
APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest -q backend/tests/platform/provider_cost_rate_limits
```

```bash
APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest -q backend/tests/checker
```

```bash
DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/platform/provider_cost_rate_limits
```

```bash
DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python backend/tests/check_backend_tests.py --scope suite
```

Gate B must also run Python syntax/compile validation for the new Python test
files and `git diff --check`.

### Proof-layer decisions

| Proof layer | Decision |
|---|---|
| PostgreSQL behavioral evidence | Not required. C3B makes no production data-path or concurrency change; it proves static/source inventory and governance boundaries. |
| Genuine concurrency | Not required. No limiter algorithm, row-lock behavior, or cross-instance rate counter is approved in C3B. |
| Controlled time | Not required. No rolling window, expiration, or rate-limit `Retry-After` calculation is implemented by C3B. |
| Backend HTTP/API evidence | Not required for C3B. Existing routes are inventoried statically; no HTTP behavior changes. |
| Provider/network evidence | Not required and not allowed as local proof. Provider quota/cost/dashboard facts remain external evidence. |
| Browser/Playwright | Not required. C3B does not change frontend behavior. |
| Migration/schema-history evidence | Not required. No schema or migration change is approved. |

## 7. Integration / Operational Expectations

C3B integrates with later production-readiness work by preserving a truthful
handoff:

- later C3B-like or API-M11 work may add a source limiter only after an
  approved evidence package selects values and state ownership;
- WS05 must preserve recovery-safe payment/refund/account-cleanup behavior
  before introducing durable retry or worker limits;
- WS06 must own storage/R2 object lifecycle, reconciliation, and provider
  evidence;
- WS09 must own telemetry, dashboards, alerts, capacity/cost modeling, and
  operational thresholds;
- WS03 and provider/security work must own auth-provider, anonymous/public,
  IP, App Check, MFA, and recovery-abuse controls;
- WS02-03 and runtime/provider work must own trusted client-IP, forwarded
  headers, edge/WAF/CAPTCHA, permanent-host, and deployed topology evidence.

## 8. Not Part Of This Pass

C3B does not:

- implement a rate limiter;
- approve provider-cost/action max/window/key values;
- generalize C3A's chat value to other workflows;
- add rate-limit `Retry-After` behavior outside C3A or prohibit unrelated
  legitimate HTTP `Retry-After` semantics owned by another accepted pass;
- add a generic PostgreSQL, Redis, in-memory, provider-dashboard, edge, or
  auth-provider limiter;
- add migrations or limiter-state retention policy;
- change Stripe, Firebase, R2, checkout, saved-card, refund, account-deletion,
  venue-image, webhook, or game-credit production behavior;
- run provider/network/browser evidence;
- claim API-M11 is closed;
- close anonymous/public abuse controls, trusted client IP, forwarded-header
  trust, edge/WAF/CAPTCHA, auth-provider controls, provider dashboards,
  runtime/load behavior, monitoring, alerts, or capacity/cost modeling.

## 9. Related Controls And Remaining Evidence

| Control / Decision | What this pass establishes | What remains later |
|---|---|---|
| `API-M11` | C3B preserves the current provider-cost/action inventory, confirms no source-owned non-chat provider-cost limiter is currently approved, and keeps API-M11 partial. | Authenticated non-chat limits where justified, anonymous/public controls, IP/token/resource/admin scopes, edge/WAF/CAPTCHA, auth-provider/provider-dashboard controls, multi-instance runtime behavior, monitoring, alerts, and load evidence. |
| `GOV-006` / `FDN-04` | C3B applies the approved evidence method and refuses to invent numeric rate values, limiter state, or operational thresholds. | Future owner-approved evidence packages for any workflow-specific limiter values and operating model. |
| `WS02-04C1` | C3B preserves C1 timeout ownership and does not reinterpret timeout values as rate controls. | Later runtime/provider timeout evidence and global request/response deadline work. |
| `WS02-04C2` | C3B preserves retry/reconciliation/backpressure ownership and uses the C2 provider-operation registry for inventory truth. | Durable workers, live provider retry evidence, provider dashboard settings, worker retry/concurrency values, and WS05 reconciliation implementation. |
| `WS02-04C3A` | C3B preserves the narrow authenticated chat limiter boundary. | No unrelated source-owned rate values are approved by C3A. Broader API-M11 work remains open. |
| `WS02-04B2A2B2` | C3B preserves provider/payment input ownership and source-derived financial validation as primary safeguards, not rate limits. | Full payment/refund/provider lifecycle, dashboard evidence, durable reconciliation, monitoring, and later financial controls. |
| `WS05` / `WS06` / `WS09` | C3B documents durable payment/account/storage/reconciliation and observability/capacity handoffs. | Actual durable jobs, storage/provider reconciliation, runtime metrics, dashboards, alerts, capacity and cost model, and operational exercises. |

### Supporting relationships

The limits register and WS02-04 source-owned closeout remain the companion
governance artifacts for this pass. They continue to record C3A as the only
approved source-owned rate limit and C3B provider-cost/action values as not
approved.

## 10. Completion Criteria

- [ ] `docs/production-readiness/planning/passes/ws02/ws02-04c3b-provider-cost-rate-limit-deferral.md` matches current authority and repository truth.
- [ ] `backend/tests/support/requirements/ws02_04c3b.json` declares R1-R8 with stable IDs, valid states, correct scopes, source controls, and a reason for the deferred requirement.
- [ ] Trusted C3B static/source evidence exists under `backend/tests/platform/provider_cost_rate_limits`.
- [ ] R1-R7 have truthful pytest mappings; R8 remains deferred with zero pytest mappings.
- [ ] The C3B `TESTING_RECORD.md` explains evidence quality and external/non-executable boundaries without overclaiming.
- [ ] Focused C3B tests pass.
- [ ] EN-01 checker/foundation tests pass.
- [ ] C3B domain checker and suite checker pass.
- [ ] Python syntax/compile validation passes for the new Python test files.
- [ ] `git diff --check` passes.
- [ ] No production code, configuration, migration, provider setting, browser behavior, or unrelated documentation is changed.
- [ ] No API-M11 full-closure, provider-dashboard, runtime/load, monitoring/alert, or edge-control claim is made.
