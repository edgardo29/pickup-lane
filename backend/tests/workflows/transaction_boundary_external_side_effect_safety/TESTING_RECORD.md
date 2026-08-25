# Testing Record: WS04-02A - Transaction Boundary And External-Side-Effect Safety

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS04-02A` |
| Trusted test scope | `backend/tests/workflows/transaction_boundary_external_side_effect_safety/` |
| Requirement declaration | `backend/tests/support/requirements/ws04_02a.json` |
| Authoritative sources | Frozen WS04-02 intake, frozen WS04-02A canonical plan, accepted WS04-01A/B/C database foundation, accepted WS02-04C1/C2 timeout and retry records, current backend source |
| Evidence layers | pytest, static source-policy checks, provider fakes, compatibility regression |

## 1. Scope

This record covers current source-owned transaction boundaries for workflows
that combine database mutation with Stripe, Firebase, R2 metadata, webhook,
notification, platform-notice, support, or admin-visible effects.

The scope proves local checkpoint ordering, honest unknown-outcome handling,
retry-policy reconciliation, user-visible/admin-visible local-state boundaries,
and preservation of accepted database and retry foundations. It does not prove
live Stripe/Firebase/R2 provider behavior, durable worker execution, full
payment lifecycle redesign, final production infrastructure, migration
compatibility, dashboards, alert thresholds, or deployed runtime evidence.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS04-02A-R1` | Material current side-effecting workflows are inventoried with local unit of work, external effect, checkpoint, timeout behavior, and downstream owner. | pytest/static |
| `WS04-02A-R2` | Provider mutations that need local recovery have a committed checkpoint or durable idempotency identity before the provider call. | pytest/provider fakes/static |
| `WS04-02A-R3` | Checkout create/re-entry/confirm preserves accepted serialization and avoids duplicate create or confirm decisions. | pytest/provider fakes plus WS02-04C2 compatibility |
| `WS04-02A-R4` | Unknown provider outcomes do not produce blind automatic replay or ordinary success. | pytest/provider fakes/static |
| `WS04-02A-R5` | Provider outcomes and post-provider persistence failures are recorded or surfaced through recoverable states. | pytest/static plus compatibility |
| `WS04-02A-R6` | User-visible, admin-visible, notification, platform-notice, and support effects are tied to committed local state. | pytest/static |
| `WS04-02A-R7` | Provider retry classifications and durable-work handoffs stay consistent with the transaction-boundary policy. | pytest/static |
| `WS04-02A-R8` | Accepted database lifecycle, timeout, rollback, pool, role, and query-access foundations remain intact. | compatibility pytest/checker |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| `R1`, `R7` | Every current material side-effecting workflow has one source-owned boundary policy and matching retry contexts where provider-backed. | A new provider mutation or visible effect is omitted from policy. | Recovery and downstream passes reason from an incomplete contract. | Declarative registry plus retry-policy consistency checks. | workflows |
| `R2`, `R4` | Risky provider mutations have durable local identity before the call and do not replay blindly after timeout. | Stripe creates an object while local rows roll back, or the app retries with only request-local identity. | Duplicate provider work, unrecoverable split-brain state, or false success. | Checkpoint-before-provider source behavior and timeout tests with provider fakes. | workflows |
| `R3` | Checkout re-entry reacquires game serialization and rereads provider state before confirm decisions. | A duplicate request creates another PaymentIntent, reserves credits again, or confirms from a stale view. | Capacity, credit, and payment corruption. | Existing WS02-04C2 PostgreSQL serialization tests remain current with the checkpoint change. | platform/workflows |
| `R5`, `R6` | Provider and visible outcomes are not claimed until owning local state is durable. | A response, admin action, notice, or notification claims success before commit, or provider success is erased after local failure. | Misleading users/admins and lost repair evidence. | Separate recording transactions, local visible-effect policy, support/money issue handoffs. | workflows |
| `R8` | Database lifecycle and timeout foundations remain intact. | Checkpoint changes weaken request rollback/close behavior, retry policy, or database access contracts. | Regression in accepted WS04-01 and WS02-04 controls. | Focused compatibility validation for operation timeouts, retry reconciliation, database lifecycle, and query access. | platform/workflows |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | caller, user, admin, provider, webhook, support/system | grouped | The pass owns transaction/side-effect boundaries, not full authorization matrices. |
| States / lifecycle | pending, requires action, processing, failed, cancelled, succeeded, expired, unknown | covered/grouped | These are the material states for checkout, publish, refund, cleanup, and visible local rows. |
| Actions | create, confirm, retrieve, retry, reconcile, delete, publish, notify, support/admin record | covered/grouped | Current source surfaces are inventoried and representative risky mutations are exercised. |
| Inputs / boundaries | idempotency keys, provider IDs, committed row IDs, support metadata | covered | Boundary safety depends on durable identity and safe metadata. |
| Time | checkout hold, publish attempt expiry, timeout/unknown provider outcome | covered/grouped | Tests use provider fakes and existing explicit-time checkout coverage. |
| Dependencies | PostgreSQL session, Stripe, Firebase, R2 metadata, webhook redelivery | covered/deferred | Local proof fakes providers at app-owned boundaries; live provider behavior remains later-owned. |
| Concurrency / idempotency | duplicate checkout, duplicate retry, provider redelivery, no blind replay | covered/grouped | Existing WS02-04C2 compatibility plus policy tests protect current source behavior. |
| Authorization / privacy / security | admin/support visibility, safe policy prose, no secret/provider-private evidence | covered/grouped | Tests inspect declarative policy and no live provider evidence is stored. |
| Persistence / rollback | committed checkpoints, short recording transactions, no success before commit | covered | Provider checkpoint tests prove commit ordering for key risky workflows. |
| Recovery | pending/reconcile/manual repair/support follow-up, later durable work | covered/deferred | Current recoverable state is source-owned; durable execution remains WS05. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | missing workflow or retry context in boundary registry | pytest/static |
| empty | yes | missing checkpoint, post-effect record, or recovery path | pytest/static |
| corrupt | yes | mismatched provider retry context or unsafe policy prose | pytest/static |
| exceed | no | no numeric retry/concurrency threshold is approved by this pass | not applicable |
| duplicate | yes | duplicate checkout create/re-entry or refund retry idempotency | pytest/compatibility |
| delay | yes | provider timeout or unknown outcome | pytest with provider fakes |
| reorder | yes | provider call before local checkpoint | pytest with provider fakes |
| interrupt | yes | provider mutation timeout between checkpoint and outcome recording | pytest with provider fakes |
| race | yes, narrowly | checkout/game serialization after provider create | WS02-04C2 compatibility |
| expire / revoke | yes | stale checkout and publish attempt expiry | compatibility/local policy |
| tamper | yes | request-local identity substituted for durable identity | pytest/static |
| retry | yes | no blind replay unless retry policy explicitly permits it | pytest/static |
| recover | yes | pending/support/reconcile states and later owner handoff | pytest/static |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| `R1`, `R6`, `R7`, `R8` | policy inventory, required fields, retry-context reconciliation, sensitive/runtime negative space | pytest/static | `test_transaction_boundary_policy_contract.py` | Adequate for source-owned registry completeness and drift checks; does not prove live provider behavior. |
| `R2`, `R3`, `R4`, `R5` | checkout provider create timeout after checkpoint | pytest with provider fake | `test_provider_checkpoint_ordering_contract.py` | Proves the provider call observes a prior local commit and no confirmation/success follows an unknown create outcome. |
| `R3`, `R5`, `R6` | checkout provider success followed by local recording failure | pytest with provider fake | `test_provider_checkpoint_ordering_contract.py` | Proves provider success is surfaced as recoverable local-recording failure instead of mislabeled as provider-create failure. |
| `R2`, `R4`, `R5` | community publish fee create timeout after checkpoint | pytest with provider fake | `test_provider_checkpoint_ordering_contract.py` | Proves publish attempt/payment identity survives create timeout without claiming a published game or provider ID. |
| `R5`, `R6` | community publish provider success followed by local recording failure | pytest with provider fake | `test_provider_checkpoint_ordering_contract.py` | Proves provider success is not erased by generic create-failure wording when local publish fee recording fails. |
| `R2`, `R4`, `R5` | paid waitlist auto-promotion create/confirm boundary | pytest with provider fake | `test_provider_checkpoint_ordering_contract.py` | Proves the waitlist promotion/payment checkpoint commits before Stripe create, provider result records before confirm, and unknown create outcomes stay processing without blind replay. |
| `R5`, `R6` | saved-card sync/default/detach provider success followed by local recording failure | pytest with provider fake | `test_provider_checkpoint_ordering_contract.py` | Proves provider-visible saved-card/default/detach mutations surface local persistence failure as recoverable card-state reconciliation instead of provider failure. |
| `R2`, `R4`, `R5` | admin refund retry timeout after retry-intent checkpoint | pytest with provider fake | `test_provider_checkpoint_ordering_contract.py` | Proves the admin retry identity commits before Stripe refund create and timeout does not erase that identity. |
| `R5`, `R6` | admin refund provider success followed by local result-recording failure | pytest with provider fake | `test_provider_checkpoint_ordering_contract.py` | Proves provider refund metadata is durably checkpointed on the admin action before broader local result recording can fail. |
| `R2`, `R4`, `R5` | unfinished-account Firebase cleanup config failure, timeout/unknown outcome, provider-success/local-commit failure, and duplicate cleanup | pytest with provider fake | `test_provider_checkpoint_ordering_contract.py` | Proves Firebase cleanup does not claim success on unknown outcome, records support follow-up after provider success plus local commit failure, and allows already-absent local duplicate cleanup to complete safely. |
| `R3`, `R4`, `R7`, `R8` | accepted checkout serialization and retry compatibility | pytest/PostgreSQL/static | `backend/tests/platform/retry_reconciliation/`, `backend/tests/platform/operation_timeouts/` | Preserves accepted WS02-04C2 behavior while updating old rollback expectations to the new checkpoint semantics. |
| `R8` | database lifecycle and query-access compatibility | pytest/checker | `backend/tests/workflows/application_database_lifecycle_pool_settings_role_credential_boundaries/`, `backend/tests/workflows/query_cursor_database_access_behavior/` | Required compatibility proof for accepted database foundations; does not claim final production topology or roles. |

### Evidence Quality Checks

- Provider effects are faked at the application-owned service boundary.
- Timeout tests prove prohibited effects: no checkout confirmation after create
  timeout, no provider ID claim after create timeout, and no rollback of the
  committed recovery checkpoint.
- Post-provider-success failure tests prove provider success is recorded or
  honestly surfaced as a recoverable local-recording conflict instead of being
  mislabeled as provider-create failure.
- Source-policy tests compare finite workflow and retry-context sets instead of
  relying on prose-only review.
- Existing PostgreSQL checkout serialization evidence remains the proof layer
  for independent-session duplicate checkout/re-entry behavior.
- Checker `PASS` is structural traceability evidence only; semantic adequacy
  comes from the focused assertions and this record.

## 7. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| Checkout PaymentIntent create | Pending booking, payment idempotency key, participants, and credit reservation commit before Stripe create; provider ID/status record in a later short transaction. | No confirmation, success response, provider ID claim, or duplicate PaymentIntent after create timeout; no provider-create failure wording after provider success. | Committed local identity survives; app blind replay remains prohibited. |
| Checkout PaymentIntent confirm/re-entry | Existing provider PaymentIntent is reread while checkout/game serialization is owned; local payment status records before response. | No stale pre-lock confirm decision, duplicate credit reservation, or second create. | Existing pending checkout identity drives re-entry. |
| Community publish fee create/confirm | Attempt/payment checkpoint commits before Stripe create; provider result and confirmation state record before publish response. | No published game or provider ID claim after create timeout; no provider-create failure wording after provider success. | Attempt status endpoint and later WS05 reconciliation consume durable identity. |
| Paid waitlist auto-promotion | Promotion/payment checkpoint commits before Stripe create; provider PaymentIntent identity records before confirm; final promotion/payment status records before visible success. | No confirmation, accepted promotion, or blind replay after create/confirm timeout; no provider-failure wording after provider success. | Processing state and durable payment identity feed later WS05 reconciliation. |
| Saved-card sync/default/detach | Provider-visible default/detach mutations are followed by local state recording or recoverable local-recording failure. | No ordinary success or misleading provider-failure response when Stripe changed state but local persistence failed. | User refresh/support repair reconciles card state before another unsafe mutation. |
| Admin refund retry | AdminAction retry intent commits before Stripe refund create; provider result checkpoint records on the admin action before later refund event/money issue metadata. | No duplicate retry from the same idempotency key or success/failure claim after timeout alone; no erase of provider refund metadata on local result-recording conflict. | Admin reconciliation and WS05 consume durable retry identity. |
| Unfinished Firebase cleanup | Firebase delete outcome either commits local hard delete or records support partial failure if local commit fails. | No ordinary success when Firebase succeeds but local cleanup cannot be persisted; no local commit after config failure or unknown provider outcome. | Duplicate/retry behavior uses Firebase identity and support follow-up state. |
| Notifications, platform notices, support/admin effects | Committed local rows are the visible source of truth. | No claim of external delivery or provider-side fanout. | Future external delivery remains WS05-owned. |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| Durable worker execution, leases, retries, poison/dead-letter behavior | deferred | The frozen plan forbids implementing a general durable worker system in WS04-02A. | `WS05` |
| Full payment state machine, Stripe sandbox lifecycle, provider reconciliation | deferred | This pass creates current-source transaction boundaries only. | `WS05-02` through `WS05-04` |
| Final production database topology, role/grant proof, provider capacity | deferred | Final infrastructure remains intentionally unselected. | `WS04-01D` |
| Database-enforced invariants and deterministic domain concurrency | deferred | Stage 0 assigns this to the next child. | `WS04-02B` |
| Database values/defaults and SQL/logging safety | deferred | Stage 0 assigns this to the final child. | `WS04-02C` |
| Migration compatibility and production-like rehearsal | deferred | Parent authority assigns this outside WS04-02. | `WS04-03` |
| External notification delivery, dashboards, alert thresholds, provider logs | deferred | Current source creates local rows only and does not provide deployed operational evidence. | `WS05`, `WS09`, `WS10` |

## 9. Validation Results

- Focused WS04-02A workflow evidence: `20 passed`.
- Affected operation-timeout compatibility scope: `95 passed`.
- Affected retry/reconciliation compatibility scope: `36 passed`.
- Affected provider-cost/rate inventory scope: `15 passed`.
- Saved-card source-owned limit regression: `1 passed`.
- Saved-card setup-intent input regression: `2 passed`.
- Financial response-minimization saved-card/payment regression: `5 passed`.
- Self-owned account/payment authorization regression: `7 passed`.
- Accepted WS04-01A database lifecycle compatibility scope: `29 passed`.
- Accepted WS04-01B query/cursor compatibility scope: `15 passed`.
- Accepted WS04-01C production database verification compatibility scope:
  `25 passed`.
- WS04-02A focused checker: `PASS`.
- Repository suite checker: `PASS`.

## 10. Adequacy Conclusion

The selected evidence is adequate for Gate B when focused WS04-02A tests,
affected timeout/retry/database-foundation compatibility tests, focused checker,
suite checker, `git diff --check`, and final scope/security review pass.

All eight WS04-02A requirements are required and have executable or static
trusted evidence in the focused workflow scope, supplemented by compatibility
evidence from accepted WS02-04C1/C2 and WS04-01A/B/C foundations. No requirement
is marked covered elsewhere or deferred in the declaration. Later provider,
worker, migration, runtime, final-infrastructure, and observability proof remain
explicit gaps owned by later passes. Checker `PASS` is structural compliance
only, not human adequacy by itself. This record contains no literal credentials,
credential-bearing URLs, raw sensitive logs or unredacted errors,
provider-private values, personal or payment data, local machine paths,
usernames, session state, internal chat material, or other prohibited sensitive
values.
