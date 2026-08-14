# WS02-04C1 Operation Timeouts And Cancellation Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS02-04C1` |
| Trusted test scope | `backend/tests/platform/operation_timeouts/` |
| Requirement declaration | `backend/tests/support/requirements/ws02_04c1.json` |
| Authoritative sources | Canonical WS02-04C1 plan, limits-and-thresholds register, `GOV-006`, `FDN-04`, WS02-04C2 retry/reconciliation policy, current backend timeout implementation |
| Evidence layers | pytest, narrow PostgreSQL integration, provider fakes, static source inventory |

## 1. Scope

This record covers Pickup Lane's source-owned operation timeout contract for
backend provider/database calls: configured timeout values, provider timeout
classification, public timeout responses, cancellation distinction, representative
side-effect ordering, and current outbound/provider inventory.

It intentionally does not close provider dashboards or live network behavior,
proxy/process-server/runtime timeouts, global request/response deadlines,
database connect timeout, pool sizing or overflow, deployment-wide connection
budgeting, worker/shutdown behavior, retries/backoff/rate controls, telemetry
dashboards or alerts, provider contract suites, browser behavior, or permanent
host evidence.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS02-04C1-R1` | The eight approved timeout values are typed, positive, registered, documented, and backend-owned. | pytest |
| `WS02-04C1-R2` | Stripe reads and mutations use separate timeout clients and map timeout outcomes differently. | pytest |
| `WS02-04C1-R3` | Firebase Admin HTTP timeout and read/delete timeout outcomes are classified safely. | pytest |
| `WS02-04C1-R4` | R2 metadata `HEAD` timeout behavior is bounded without claiming browser upload or live provider proof. | pytest |
| `WS02-04C1-R5` | Database pool wait, checked-out statement/lock settings, exception classification, rollback, and close behavior are bounded. | pytest and PostgreSQL |
| `WS02-04C1-R6` | Timeout categories produce stable safe public 503 contracts with bounded labels and correlation. | pytest |
| `WS02-04C1-R7` | Cancellation remains distinct from timeout and is not swallowed by C1 helpers. | pytest |
| `WS02-04C1-R8` | Representative provider mutation timeout paths preserve unknown-outcome and no-blind-replay boundaries. | pytest |
| `WS02-04C1-R9` | Current production outbound/provider operations are inventoried and C1-owned boundaries are explicit. | pytest |
| `WS02-04C1-R10` | Runtime, deployment, provider, worker, retry, and broader database timeout obligations remain deferred. | deferred with zero pytest mappings |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| `WS02-04C1-R1` | Timeout values are configured through the backend settings owner and reject invalid values. | A zero, negative, undocumented, or duplicate timeout owner bypasses the approved source. | Operations can wait indefinitely or silently drift from approved limits. | Typed settings parsing, registry entries, `.env.example`, backend-only ownership scan. | platform |
| `WS02-04C1-R2` | Stripe reads produce retry-later timeout semantics; Stripe mutations produce unknown-outcome semantics. | A mutation timeout is treated as provider failure or retried blindly. | Duplicate charges/refunds or incorrect local state. | Separate fake read/mutation clients and wrapper translation tests. | platform |
| `WS02-04C1-R3` | Firebase reads and deletion use the Admin timeout while deletion timeout remains unknown. | Firebase deletion timeout is recorded as definite success or failure, or ordinary auth/user-not-found outcomes are mislabeled as timeouts. | Account cleanup can be misrepresented, support recovery can be lost, or validation failures can receive misleading timeout semantics. | Firebase boundary fakes prove timeout translation and representative non-timeout distinction. | platform |
| `WS02-04C1-R4` | R2 evidence is limited to backend metadata checks. | Local presign/browser upload behavior is mistaken for provider network proof, or non-timeout storage errors are mislabeled as timeouts. | False closure of R2 runtime/storage obligations or misleading retry behavior. | boto3/botocore fakes, non-timeout ClientError coverage, cancellation propagation, and presign/static boundary checks. | platform |
| `WS02-04C1-R5` | Real checked-out DB sessions receive statement and lock timeouts; exception types classify correctly; sessions roll back/close. | DB waits remain unbounded, realistic psycopg/SQLAlchemy timeout shapes are missed, or failed/cancelled requests leak sessions. | Resource exhaustion or misleading public errors. | Narrow PostgreSQL `SHOW` proof, realistic psycopg/SQLAlchemy exception-chain tests, and `get_db` fake-session rollback/close tests. | platform |
| `WS02-04C1-R6` | Public timeout responses expose only stable safe semantics. | Provider IDs, URLs, DB strings, submitted values, private headers, tracebacks, or raw exception text leak. | Privacy/security incident and unstable API behavior. | Public error handler tests assert exact timeout payloads and sensitive-marker absence. | platform |
| `WS02-04C1-R7` | Cancellation is not a timeout category and is not caught as ordinary timeout/failure. | Client disconnects or task cancellation are hidden as provider/database timeouts. | Misleading responses and masked runtime behavior. | Helper behavior, representative Stripe/R2/database cancellation tests, and AST catch-boundary tests. | platform |
| `WS02-04C1-R8` | Timeout alone does not create definite provider success/failure or automatic replay. | Checkout, Firebase deletion, or saved-card cleanup writes incorrect final state after timeout. | Duplicate provider mutations, incorrect local outcome state, or lost recovery. | Representative executable service-boundary tests, supporting source checks, and C2 retry-policy assertions. | platform |
| `WS02-04C1-R9` | Current provider/network boundaries are classified. | A new direct network client bypasses C1 timeout taxonomy. | Hidden unbounded external call. | Static AST import/call inventory over production backend source. | platform |
| `WS02-04C1-R10` | Later/runtime obligations remain explicit and unclaimed. | Local source tests are treated as deployed runtime, provider-dashboard, or capacity proof. | False production-readiness closure. | Deferred declaration plus this record's gaps table. | governance |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | caller, backend service, provider, database, support/admin recovery | grouped | C1 owns backend behavior at dependency boundaries, not actor authorization. |
| States / lifecycle | read timeout, mutation timeout unknown, database pool/statement/lock timeout, cancellation, non-timeout failure | covered | These are the material timeout outcome classes. |
| Actions | Stripe read/mutation, Firebase token/user read/deletion, R2 metadata read/presign, DB session checkout/exception handling | covered | Current production inventory shows these are the C1-owned external/database paths. |
| Inputs / boundaries | timeout env values, public error payloads, sensitive strings, provider identifiers, DB URLs | covered | Misconfiguration and leakage are central C1 risks. |
| Time | timeout configuration values, delayed provider/database calls | grouped | Tests prove configuration and classification without real sleeps. |
| Dependencies | Stripe, Firebase Admin, R2 metadata, PostgreSQL/SQLAlchemy | covered | Provider fakes are used at app-owned boundaries; PostgreSQL is used only for checked-out session settings. |
| Concurrency / idempotency | no blind replay, unknown outcome, C2 retry ownership | covered by representative executable service evidence plus policy checks | C1 does not implement retry/reconciliation. |
| Authorization / privacy / security | redaction, bounded telemetry labels, safe correlation | covered | EN-02 primitives are exercised through public timeout contracts. |
| Persistence / rollback | DB rollback/close; representative provider timeout side effects | covered | C1 proves side-effect ordering where timeout could misstate outcomes, without claiming full provider reconciliation. |
| Recovery | pending/processing/support/reconcile/manual repair | grouped | Recovery implementation remains C2/later owned; C1 preserves safe handoff states. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | missing timeout env values | Defaults are asserted. |
| empty | yes | blank/non-integer timeout values | Invalid setting tests reject them. |
| corrupt | yes | non-timeout provider/storage/database exceptions | Distinct exceptions remain distinct. |
| exceed | yes | zero/negative or lock >= statement settings | Settings validation rejects them. |
| duplicate | yes | blind replay and duplicate provider mutation | Retry policy and wrapper call-count evidence cover this. |
| delay | yes | provider/database timeout classes | Fakes and synthetic exception chains cover classification. |
| reorder | no | no ordered event stream owned by C1 | Not applicable. |
| interrupt | yes | `asyncio.CancelledError` | Cancellation tests cover helper/call-site behavior. |
| race | no | no genuine C1 race proof required | Later database/concurrency passes own this. |
| expire / revoke | no | not a C1 timeout boundary | Not applicable. |
| tamper | yes | public error sensitive content and labels | Public error tests assert safe output. |
| retry | yes | C2 retry/no-blind-replay policy | Static policy checks preserve C2 ownership. |
| recover | yes | unknown-outcome recovery handoffs | Representative source checks cover pending/support/reconcile states. |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| `WS02-04C1-R1` | approved values, positive overrides, invalid values, registry/docs, backend-only owner | pytest/static | `test_timeout_settings_contract.py` | Proves current typed configuration and catches duplicate/ad hoc env ownership. |
| `WS02-04C1-R2` | Stripe client timeouts and read/mutation translation | pytest with fakes | `test_stripe_timeout_contract.py` | Uses provider fakes at the Stripe wrapper boundary and proves no app replay from one timeout call. |
| `WS02-04C1-R3` | Firebase Admin timeout and timeout/non-timeout classification | pytest with fakes | `test_firebase_timeout_contract.py` | Exercises app-owned Firebase boundary without live Firebase, including user-not-found and validation/auth failures that must not become timeouts. |
| `WS02-04C1-R4` | R2 metadata timeout, non-timeout storage errors, cancellation, and presign boundary | pytest with fakes/static | `test_r2_metadata_timeout_contract.py` | Covers metadata `HEAD` only, proves ordinary storage failures and cancellation stay distinct, and explicitly avoids browser/upload/provider-runtime claims. |
| `WS02-04C1-R5` | DB checked-out session settings, pool timeout setting, realistic exception classification, rollback/close/cancellation close | PostgreSQL plus unit fakes | `test_database_timeout_contract.py` | PostgreSQL proves installed session settings; realistic SQLAlchemy/psycopg exception chains avoid slow sleeps and artificial locks. |
| `WS02-04C1-R6`, `WS02-04C1-R7` | public timeout responses, safe labels, cancellation distinction | pytest/unit/static | `test_public_timeout_contract.py`, `test_r2_metadata_timeout_contract.py`, `test_database_timeout_contract.py` | Exercises public boundary and helper behavior directly, including representative provider/database cancellation paths. |
| `WS02-04C1-R8` | representative unknown-outcome side-effect ordering | pytest with fakes and PostgreSQL where persisted rejection effects matter | `test_timeout_side_effect_ordering_contract.py` | Confirms checkout rollback, Firebase deletion support metadata, saved-card unpersisted cleanup behavior, and no blind application retry without broad payment/account-system reimplementation. |
| `WS02-04C1-R9` | outbound/provider operation inventory | pytest/static | `test_provider_operation_inventory_contract.py` | Scans current production source and fails on unclassified new network/provider boundaries. |
| `WS02-04C1-R10` | later/runtime/provider gaps | declaration and record | `ws02_04c1.json`, this record | Correctly remains zero-mapped because local C1 tests cannot prove deployed runtime/provider/dashboard/capacity behavior. |

### Evidence Quality Checks

- C1 does not rely on uncontrolled wall-clock sleeps; timeout behavior is proved
  through settings, fakes, synthetic exceptions, and real PostgreSQL session
  settings.
- The pass has no approved production mutation changes. Representative
  side-effect evidence verifies existing safe ordering instead of manufacturing
  new business mutations.
- Rejected/timeout paths prove relevant prohibited effects through executable
  checkout rollback, one-call provider-boundary assertions, Firebase unknown
  support metadata, saved-card cap rejection without a local row, and no
  automatic replay assertions.
- Idempotency/retry evidence proves C1 preserves C2 no-blind-replay ownership
  rather than implementing new retry behavior.
- PostgreSQL is used only where the database itself must prove checked-out
  session timeout settings.
- External providers are faked at Stripe, Firebase Admin, and R2 application
  boundaries.
- Database exception classification uses realistic SQLAlchemy/psycopg cause
  chains because the frozen plan prohibits slow statement sleeps and artificial
  lock waits.

## 7. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| Stripe checkout/payment timeout | none beyond propagating timeout | no definite local provider success or failure solely from timeout | request transaction rolls back and provider mutation is not replayed by C1 |
| Stripe refund timeout | refund remains processing/unknown where current workflows create records | no failed/succeeded final state solely from timeout | C2/later reconciliation or support owns recovery |
| Firebase deletion timeout | partial failure/support metadata records unknown provider outcome | no definite auth deletion success/failure solely from timeout | support follow-up preserves recovery |
| Saved-card provider cleanup timeout | best-effort cleanup failure is swallowed only for unpersisted cleanup after the owning save rejection | no local saved-card row is created because cleanup failed after a rejected save | duplicate/cap rejection remains the owning outcome; cleanup is not user-visible detach or reconciliation proof |
| Database request exception/cancellation | rollback on ordinary exception and close in all cases | leaked open session, swallowed cancellation, or timeout relabeling | `get_db` dependency handles rollback/close; cancellation closes without rollback under current production behavior |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| `WS02-04C1-R10` global request/response deadlines | deferred | C1 local source tests do not prove deployed request lifecycle bounds. | WS02-04C3A/B, runtime/deployment evidence |
| DB connect timeout, pool size/overflow, provider connection caps, deployment-wide connection budget | deferred | C1 owns pool wait and checked-out session settings only. | DB-002 / WS04 |
| transaction-duration, idle-session, deadlock/serialization, migration timeout policy | deferred | Requires database/concurrency/migration evidence outside C1. | DB-004 / DB-008 / later database work |
| provider dashboards, live networks, SDK retry modes, backoff/jitter | deferred | C1 uses fakes and static policy; live provider behavior is not local trusted proof. | provider evidence / WS02-04C2 / later operations |
| process-server, proxy, ingress, permanent-host timeout settings | deferred | Not represented by repository source tests. | runtime/hosting evidence |
| workers, shutdown, durable reconciliation | deferred | C1 preserves handoff states but does not implement durable jobs. | WS05 / WS06 / WS09 / WS10 |
| telemetry dashboards and alerts | deferred | C1 verifies safe labels and public contracts only. | observability operations |

## 9. Adequacy Conclusion

The selected evidence is adequate for the frozen WS02-04C1 Gate B scope when
focused C1, adjacent platform, full trusted backend, checker/domain/suite,
traceability, compile, and diff checks pass.

`WS02-04C1-R1` through `WS02-04C1-R9` have executable trusted evidence under
`backend/tests/platform/operation_timeouts/`. `WS02-04C1-R10` is intentionally
deferred and must remain zero-mapped. Checker `PASS` is structural compliance
evidence only; human review must still confirm the tests match the frozen risk
model and do not overclaim external/runtime closure.
