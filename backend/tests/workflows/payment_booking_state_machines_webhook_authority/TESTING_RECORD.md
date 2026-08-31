# WS05-02 Payment Booking State Machines Webhook Authority Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS05-02` |
| Trusted test scope | `backend/tests/workflows/payment_booking_state_machines_webhook_authority` |
| Requirement declaration | `backend/tests/support/requirements/ws05_02.json` |
| Authoritative sources | Frozen WS05-02 plan; accepted WS02-04B2A2B2, WS02-04C2, WS04-02A/B/C, WS04-03A, WS05-01A artifacts; payment, checkout, webhook, credit, waitlist, and durable-job source |
| Evidence layers | PostgreSQL-backed service transitions; deterministic provider-boundary fakes; source/response contracts; model and migration constraints; governance deferral for later runtime/provider evidence |

## 1. Scope

This record covers the source-owned trusted evidence for the WS05-02 payment,
booking, reservation, webhook, compensation, and saved-payment-method state
machines.

It proves repository-owned lifecycle shape, durable local identities, bounded
event envelopes, provider-call ordering, exact local expiry behavior,
compensation handoffs, and saved-card unknown-outcome handoffs. Deterministic
PostgreSQL service tests exercise the state transitions, fresh post-provider
database-time decisions, saved-method concurrency, and transaction visibility
directly; source inspection is retained only for negative-space and finite
ownership contracts. It intentionally does not
prove live Stripe delivery, Stripe dashboard settings, deployed worker hosting,
actual compensation/refund execution, disputes, broad scheduled reconciliation,
production alerts, or operational runbooks.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS05-02-R1` | Checkout identity, amount, reservation, PaymentIntent creation, and confirmation decisions are server-owned, checkpointed, and free of DB locks during provider calls. | pytest/source |
| `WS05-02-R2` | Payment, provider, booking, reservation, participant, credit, and history states are explicit and separate. | PostgreSQL service tests, source contracts, and model constraints |
| `WS05-02-R3` | Late success and capacity conflict preserve succeeded payment truth and create one active compensation obligation without webhook-time refunds. | PostgreSQL service tests, source contracts, and model constraints |
| `WS05-02-R4` | Signed webhook ingestion persists a bounded event envelope and enqueues durable internal work before acknowledgment. | PostgreSQL service tests and source contracts |
| `WS05-02-R5` | Duplicate, delayed, missing, out-of-order, nonterminal, unknown, failed, canceled, and succeeded PaymentIntent observations use one canonical transition rule for webhook and reconciliation. | PostgreSQL service tests and source contracts |
| `WS05-02-R6` | Saved payment methods are user-owned, provider-verified, idempotent, safe-metadata-only, and durable across unknown outcomes. | PostgreSQL service tests, deterministic provider fakes, frontend unit tests, and model constraints |
| `WS05-02-R7` | Accepted provider-input, transaction, invariant, migration, authorization, response, durable-job, community-publish, waitlist, credit, and full-credit checkout contracts remain compatible. | pytest/source plus covered elsewhere |
| `WS05-02-R8` | Later provider, runtime, refund/credit execution, dispute, reconciliation, observability, and operations evidence stays deferred. | deferred |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| R1 | Provider mutations occur only after durable local identity exists and no DB lock is held. | Checkout verifies saved cards or calls Stripe while owning game/booking locks. | Deadlocks, stale entitlement decisions, or duplicate provider work. | Re-entry gate, committed checkpoints, and source ordering contracts. | workflow/source |
| R2 | Provider payment truth and booking/reservation truth remain separate. | Browser or PaymentIntent status directly grants entitlement or active holds survive expiry. | Users can receive false roster entitlement or capacity can be stranded. | Explicit status sets, booking matrix constraints, and local expiry path. | workflow/source/model |
| R3 | A successful charge without entitlement creates one compensation obligation. | Webhook marks payment failed, confirms participants, or creates duplicate/ad hoc refunds. | Financial records become false or refund obligations duplicate. | Compensation table active uniqueness and webhook negative-space tests. | workflow/source/model |
| R4 | Webhook HTTP acknowledgment follows committed durable event/job state. | The route processes effects inline, stores raw provider payload, or enqueues unsafe payloads. | Duplicate effects, leaked secrets, or lost events. | Bounded envelope and internal-ID-only durable job contracts. | workflow/source |
| R5 | Webhook and targeted reconciliation use identical PaymentIntent transition rules. | Reconciliation and webhook disagree after stale, unknown, or delayed provider observations. | State depends on delivery order rather than authoritative provider truth. | Shared transition entry and stale-expiry reuse. | workflow/source |
| R6 | Saved-card operations have durable identity and unknown handoffs. | Timeout after a provider action is treated as local success/failure or replayed with changed identity, or two unresolved operations become active concurrently. | Lost card/default/detach state or duplicate provider mutation. | Payment-method operation table, active-operation uniqueness, idempotency keys, and unknown reconcile jobs. | workflow/source/model |
| R7 | Existing accepted compatibility contracts remain intact. | This pass reopens retired routes, client authority, reverse lock order, unsafe responses, or old workflow behavior. | Previously accepted production-readiness evidence regresses. | Source contracts plus earlier accepted test scopes. | workflow/platform/covered_elsewhere |
| R8 | Source tests do not overclaim external/runtime proof. | Local fakes are mistaken for Stripe, worker-hosting, alerting, or runbook evidence. | Program status becomes dishonest. | Deferred requirement declaration and this record. | governance |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | authenticated user, admin read, provider webhook, durable worker, system reconciliation | grouped | WS05-02 owns source transitions; broader authorization is covered by accepted scopes. |
| States / lifecycle | payment states, provider states, booking states, reservation states, compensation states, operation states, event states | covered | These finite sets define the pass. |
| Actions | checkout create, checkout confirm/retry, status read, webhook ingest, webhook worker handling, payment reconciliation, saved-card setup/sync/default/detach | covered/grouped | Source contracts cover the material state-machine paths. |
| Inputs / boundaries | Stripe IDs, event envelopes, idempotency keys, payment method IDs, return URLs, metadata references | covered/grouped | Prior provider-input scopes remain prerequisites where exact parsing is already accepted. |
| Time | before expiry, exact expiry, after expiry, late success, provider call crossing expiry | covered/PostgreSQL service | Tests invoke the exact expiry boundary for every unresolved state, apply late success afterward, and prove checkout/waitlist final entitlement decisions use fresh DB time after provider work; deeper deployed timing remains later. |
| Dependencies | PostgreSQL, Stripe, durable jobs, browser polling | covered/deferred | Source-owned boundaries are covered; live provider/browser/runtime behavior is deferred. |
| Concurrency / idempotency | duplicate webhooks, repeated checkout create/confirm, compensation uniqueness, saved-card active-operation uniqueness, lock order | covered/grouped | PostgreSQL tests cover current source-owned uniqueness and contention behavior; crash/race replay remains WS05-04 where assigned. |
| Authorization / privacy / security | signed webhook, saved-card ownership, safe response/event/job metadata | grouped | This scope verifies no sensitive payload expansion; accepted auth scopes own role matrices. |
| Persistence / rollback | checkpoints, unknown handoffs, stale release, durable events/jobs | covered/grouped | Tests focus on durable source behavior and prohibited provider claims. |
| Recovery | webhook retry, payment reconcile, payment-method reconcile, compensation handoff | covered/deferred | Local handoffs are covered; refund execution and broad reconciliation remain later-owned. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | missing saved method, unsupported event payload fields | covered/grouped |
| empty | yes | safe labels and event/provider IDs from prior scopes | covered elsewhere |
| corrupt | yes | mismatched metadata or provider ownership | covered/grouped |
| exceed | partial | bounded event/job metadata and provider IDs | covered elsewhere/source |
| duplicate | yes | webhook event ID, compensation active uniqueness, creation/confirmation identities | pytest/source/model |
| delay | yes | delayed nonterminal, failed, canceled, or success provider observations | pytest/source |
| reorder | yes | out-of-order PaymentIntent events resolved by current provider observation | pytest/source |
| interrupt | yes | unknown provider outcomes and local recording failures | pytest/source plus prior timeout scopes |
| race | partial | lock order, re-entry contracts, and saved-card active-operation contention | PostgreSQL/source now; deeper crash/race proof deferred to WS05-04 |
| expire / revoke | yes | reservation expiry and expired saved cards | pytest/source |
| tamper | yes | webhook payloads and metadata references | covered/grouped |
| retry | yes | durable webhook/payment/payment-method reconcile jobs | pytest/source |
| recover | yes | targeted PaymentIntent and payment-method operation reconciliation handoffs | pytest/source |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| R1, R6, R7 | Checkout saved-card verification releases locks, then re-enters before reserving or confirming; provider mutations follow committed checkpoints. | pytest/source | `test_payment_booking_state_machines_contract.py` | Adequate for source-owned ordering; not a live deadlock/load proof. |
| R2, R5 | Exact unfamiliar provider status is retained separately from normalized `unknown`; ordinary cancellation fails and releases the booking. | PostgreSQL service | `test_payment_booking_transitions.py` | Commits the resulting rows so database constraints and service behavior are proved together. |
| R2, R5 | Every unresolved state expires at the exact boundary without rewriting provider truth. | PostgreSQL service | `test_payment_booking_transitions.py` | Parameterized over `requires_payment_method`, `requires_confirmation`, `requires_action`, `processing`, `requires_capture`, and `unknown`. |
| R3, R5 | Late success and real capacity conflict preserve succeeded payment truth and create one active compensation, while a valid held party still confirms. | PostgreSQL service/model | `test_payment_booking_transitions.py`; `test_payment_booking_state_machines_contract.py` | Proves positive, negative, and duplicate application behavior; actual refund execution remains WS05-03. |
| R4, R5 | Duplicate webhook ingest commits one bounded event and one internal-ID-only durable job. | PostgreSQL service/source | `test_payment_booking_transitions.py`; `test_payment_booking_state_machines_contract.py` | Proves repository-owned durable acknowledgment state; live Stripe delivery is deferred. |
| R1, R2, R5, R7 | Checkout and paid-waitlist provider boundaries reacquire database time before final reservation/entitlement decisions. | PostgreSQL service with provider fakes | `test_payment_booking_transitions.py`; `test_payment_booking_state_machines_contract.py` | Proves provider work crossing expiry becomes late success/expired state rather than stale entitlement. |
| R2, R5, R7 | Paid waitlist `requires_action` / `requires_payment_method` fail promotion, while `requires_confirmation` and `requires_capture` preserve exact provider truth without entitlement or false failure. | PostgreSQL service with provider fakes | `test_payment_booking_transitions.py`; `test_payment_booking_state_machines_contract.py` | Proves non-interactive failure cases and manual-capture/no-entitlement handling inside the canonical transition path. |
| R6, R7 | Paid waitlist provider ownership is reverified before charge, durable saved-method reconciliation leaves its final state uncommitted for the worker transaction, and unresolved saved-method operations are database-safe under contention. | PostgreSQL service with provider fakes | `test_payment_booking_transitions.py` | Proves rejection before mutation, transaction visibility, and active-operation uniqueness; live provider behavior is deferred. |
| R6 | One frontend saved-card action supplies an explicit operation identity and reuses it across step-up replay. | Node unit | `frontend/tests/unit/paymentMethodsApi.test.js` | Proves the API helper cannot silently mint a replacement identity during replay. |
| R8 | Later-owner non-closure. | governance | `ws05_02.json`; this record | Correctly has no executable pytest mapping. |

### Evidence Quality Checks

- Time-boundary evidence uses an exact timestamp argument through the DB-owned
  expiry path and no arbitrary sleeps.
- Successful and rejected transition proof commits against PostgreSQL, while
  provider behavior remains represented at the application wrapper boundary.
- Rejected/prohibited effects are proven with negative-space source checks for
  provider calls during local status reads, unsafe webhook payloads, inline
  webhook processing, and webhook-time refund mutation.
- Idempotency is represented by creation fingerprints, confirmation-attempt
  fingerprints, payment-method operation fingerprints, event uniqueness, and
  compensation active uniqueness.
- External providers are not contacted. Stripe behavior is represented only at
  the application-owned wrapper boundary.
- Database-constraint proof includes committed service outcomes after a full
  migration downgrade/upgrade rehearsal; broader migration policy remains in
  its dedicated validation scope.

## 7. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| Checkout PaymentIntent create | Pending booking, held reservation, participants, credits, and payment creation identity commit before Stripe create. | No provider call while holding game/booking locks; no client-owned amount/provider state. | Re-entry recomputes current DB state after provider verification and reacquires DB time after provider work. |
| Checkout confirmation | Confirmation attempt identity commits before Stripe confirm. | No reuse of a previous confirmation identity with a different PaymentMethod; no stale timestamp can grant entitlement after expiry. | Same protected inputs reuse the same confirmation idempotency key and final state uses fresh DB time. |
| Checkout status read | Expired unresolved holds release locally before response. | No provider polling, confirmation, create, or saved-card provider read from browser status polling. | Expiry does not falsify provider truth. |
| Webhook ingest | Unique event row and one durable job commit before acknowledgment. | No raw payload, client secret, card data, email, or provider event payload in durable job. | Duplicate provider event is acknowledged idempotently. |
| Webhook/reconcile transition | Current PaymentIntent observation applies through one transition service. | Delayed nonterminal/failure/cancel cannot regress local success; expired hold cannot be extended. | Retry works from internal payment/event identity. |
| Late success / capacity conflict | Payment stays succeeded, booking denies entitlement, active compensation exists. | No participant confirmation and no ad hoc webhook refund mutation. | Active compensation uniqueness is per payment and booking. |
| Saved-card operation | Operation identity and provider idempotency key exist before provider mutation. | Unknown provider result is not reported as success, failed replay, or a second active operation for the same user. | Unknown status enqueues operation reconciliation; PostgreSQL active-operation uniqueness blocks concurrent conflicts. |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| `WS05-02-R8` | deferred | Final worker hosting, Stripe sandbox/dashboard evidence, deployed webhook delivery, broad scheduled reconciliation, compensation/refund execution, credit-restoration execution, disputes, production alerts, and runbooks cannot be closed by local source contracts. | WS05-01B, WS05-03, WS05-04, WS09, WS10 |
| Migration execution against PostgreSQL | validated for this correction | The dedicated test database completed downgrade-to-base and upgrade-to-head before focused service tests. Broader migration policy remains separately owned. | WS04-03A validation layer |
| Full role/authorization matrix | covered elsewhere | WS05-02 preserves accepted boundaries but does not reopen every role-route proof. | WS03-04 and accepted auth scopes |
| Browser/e2e behavior | deferred | Frontend polling presentation is updated, but Playwright/browser proof is not required by this Gate B scope. | Frontend/e2e owner or explicit user request |
| Deployed provider crash/race/replay exercises | deferred | Local atomicity, duplicate delivery, and unknown-outcome handoffs are exercised here; deployed worker/provider interruption evidence remains later-owned. | WS05-04 |

## 9. Owner-Directed Gate B Correction Round 3 Validation

| Validation Layer | Result |
|---|---|
| Focused WS05-02 transition and source-contract scope | PASS: `35 passed` |
| Complete changed trusted backend test module scope | PASS: `141 passed`; warnings were limited to the existing Alembic `path_separator` deprecation |
| Frontend unit tests | PASS: `64 passed` |
| Frontend ESLint | PASS |
| Python compile checks over the changed backend ownership areas | PASS |
| Ruff | PASS over the changed Python correction scope with `ruff==0.16.5` from `backend/.venv` |
| Backend suite checker and generated traceability | PASS: `1,394` nodes collected; `WS05-02-R1` through `R7` mapped and `R8` intentionally zero-mapped |
| PostgreSQL migration lifecycle | PASS: downgrade from head to base and rebuild from base to the single `0065` head after adding the active saved-method operation index |
| Git diff whitespace check | PASS |
| Broad trusted backend suite | NOT RERUN in Correction Round 3; not required by the frozen scope and not claimed as passing |
| Browser or Stripe sandbox evidence | NOT RUN: not required by the frozen pass and not claimed |

## 10. Adequacy Conclusion

This evidence is adequate for the WS05-02 source-owned Gate B scope when the
focused WS05-02 tests, suite checker, syntax/compile checks, and changed trusted
regression scope agreed for the owner-directed Gate B Correction Round 3 result.

`WS05-02-R1` through `WS05-02-R7` have executable trusted evidence in this
scope or accepted prerequisite scopes. `WS05-02-R8` is intentionally deferred
and must remain zero-mapped. Checker `PASS` is structural compliance evidence
only; human review must still confirm semantic adequacy and that this pass does
not overclaim provider, runtime, refund-execution, observability, or operations
closure. This record contains no literal credentials, credential-bearing URLs,
raw sensitive logs, unredacted errors, provider-private values, personal or
payment data, local machine paths, usernames, session state, or internal chat
material.
