# Testing Record: WS03-04A Authorization Matrix Foundation

## At A Glance

| Field | Value |
|---|---|
| Pass | `WS03-04A - Authorization matrix foundation and route drift guard` |
| Parent | `WS03-04 - Complete authorization matrix and negative proof` |
| Trusted scope | `backend/tests/workflows/authorization_matrix_foundation` |
| Requirement declaration | `backend/tests/support/requirements/ws03_04a.json` |
| Canonical matrix artifact | `backend/tests/workflows/authorization_matrix_foundation/authorization_matrix.json` |
| Contract test | `test_authorization_matrix_foundation_contract.py` |
| Gate | `B - implementation and trusted evidence` |

## Scope

This record covers only the WS03-04A matrix foundation, route inventory, source/gap traceability, child-owner partition, deterministic backend authorization-dependency serialization, and route drift guard.

This record does not claim final behavioral authorization closure for self-owned, relationship, admin/high-risk, provider/runtime, database-concurrency, export, unmask, read-audit, or parent-gap disposition work. Those remain downstream under `WS03-04B`, `WS03-04C`, `WS03-04D`, `WS05`, `WS08`, `WS09`, `WS10`, or later governance as applicable.

## Requirements

| Requirement | State In This Scope |
|---|---|
| `WS03-04A-R1` | Covered by current FastAPI route-key enumeration and matrix route-set equality. |
| `WS03-04A-R2` | Covered by structured matrix schema checks for route identity, source metadata, dispositions, owners, auth dimensions, concealment, and gaps. |
| `WS03-04A-R3` | Covered by homogeneous family ownership, valid owner vocabulary, no `WS03-04A` behavioral owner, and no route overlap. |
| `WS03-04A-R4` | Covered by backend dependency/source-based disposition checks and explicit reasons for protected and non-protected routes. |
| `WS03-04A-R5` | Covered by required route authorization-dimension and negative-proof fields. |
| `WS03-04A-R6` | Covered by fail-closed route and auth-dependency drift checks. |
| `WS03-04A-R7` | Covered by requirement declaration, pytest markers, source classification, accepted predecessor repository evidence classification, and trusted non-legacy scope. |
| `WS03-04A-R8` | Covered by negative-space checks preventing frontend-only, provider/runtime, App Check, recent-auth, broad admin, OpenAPI-only, or deferred/governance false closure. |
| `WS03-04A-R9` | Deferred/governance with zero pytest mappings in this pass. |

## Invariants And Risks

The primary invariant is that every current registered FastAPI `APIRoute` method/path pair, excluding implicit `HEAD` and `OPTIONS`, appears exactly once in the matrix with one valid behavioral owner or explicit non-WS03-04 disposition.

The risk model covers skipped routes, stale routes, duplicate routes, owner overlap, broad prefix-only allocation, route/family ownership mismatch, unnamed covered-elsewhere or blocked owner, negative-proof owner drift, canonical gap/reference corruption, one-sided gap references, ambiguous authorization dependency identity, undefined policy, frontend-only guard substitution, App Check or recent-auth overclaim, false provider/runtime closure, and sibling-child overclaim between `WS03-04B` and `WS03-04C`.

## Scenario Discovery

Scenario discovery used the current `backend.main.app` route table as derived current truth. The matrix enumerates 289 current route keys across 70 homogeneous families. Each route records registered method, FastAPI path format, route name, tags, endpoint module, backend auth-service dependency identities, route disposition, owner/disposition reasons, authorization dimensions, concealment posture, negative-proof owner/detail/reason, source references, and canonical gap references.

Mixed high-level prefixes were split by route behavior and owner. Examples include `/auth/*` predecessor-owned account lifecycle versus B-owned self-account routes, `/users/*` self versus target/admin routes, `/venues/*` public discovery versus retired/admin operations, and `/admin/*` high-risk/admin families.

## Authoritative Sources Read

WS03-04A validation read the production-readiness read-first document, program context, implementation workflow, frozen WS03-04 intake, frozen WS03-04A Gate A plan, execution register, master blueprint, final remediation plan, accepted WS03 predecessor plans/evidence records, current `backend.main.app` route registration, current route modules, and `backend/services/auth_service.py`.

## Failure Transformations

The contract is designed to fail closed when:

- a current FastAPI route is missing from the matrix;
- a stale matrix route is no longer registered;
- a matrix route key appears more than once;
- a route's serialized backend authorization dependencies drift;
- an auth dependency cannot be represented as a stable `module:qualname` identity;
- a protected route lacks backend auth dependency classification;
- a route or family uses `WS03-04A` as behavioral owner;
- a covered-elsewhere or blocked owner leaves the actual owner unnamed;
- a gap reference is stale, orphaned, one-sided, or contradicts route/family ownership;
- a deferred/provider/runtime/governance fact is mapped to local pytest evidence.

## Selected Evidence

Selected executable evidence is the trusted ordinary pytest contract in `test_authorization_matrix_foundation_contract.py`. It imports current `backend.main.app`, flattens the current route table, traverses nested FastAPI dependency trees, serializes backend auth dependencies with the frozen algorithm, loads `authorization_matrix.json`, and compares the matrix to repository truth.

Selected human evidence is this record plus the matrix source registry. Accepted predecessor evidence from `WS03-01`, `WS03-02`, `WS03-03A`, and `WS03-03B` is classified as accepted repository source/test evidence, not external evidence.

## Validation Execution Notes

The initial focused pytest attempt stopped before execution because the ambient local `DATABASE_URL` pointed at `pickup_lane_db_dev`. That stop was the repository's intended backend database safety behavior: the harness requires the dedicated `pickup_lane_test_db` database name before backend tests run.

The successful focused pytest rerun used the legitimate dedicated test database boundary `postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db` and passed 11 tests. No database or test safety mechanism was disabled, weakened, or bypassed.

## Important Side Effects

No application source, frontend source, migrations, provider configuration, runtime configuration, or production behavior changed. The added route drift guard will require deliberate matrix review whenever a route key or backend auth-service dependency changes.

The execution-register edit is a proposed accepted-state update for `WS03-04A` that becomes true atomically only when the substantive PR merges into `develop`. Human Gate B or Gate C approval alone does not make the pass accepted.

## Gaps

Canonical matrix gap `WS03-04A-G001` records `/stripe/webhook` payment/webhook lifecycle proof as covered elsewhere by `WS05`, tied to PAY-005/PAY-006 authority. WS03-04A does not claim WS05 completion.

`WS03-04A-R9` remains deferred/governance with zero pytest mappings. Final behavioral closure remains with:

- `WS03-04B` for self-owned account, notification, inbox, saved-card, credit, payment, refund, and host-fee surfaces;
- `WS03-04C` for games, community games, checkout, bookings, participants, waitlists, chats/messages, My Games, and Need-a-Sub relationship surfaces;
- `WS03-04D` for admin/high-risk routes, final matrix review, and parent-gap disposition;
- later named owners for provider/runtime, database-concurrency, export/unmask/read-audit, and governance facts.

No `blocked` owner or `blocked_owner_decision` is present in the ready-for-review WS03-04A evidence.

## Adequacy

The evidence is adequate for WS03-04A because it proves the matrix foundation is complete against current repository route truth, validates source and gap integrity, prevents unsupported owner overlap, records downstream owners without overclaiming behavioral closure, and fails closed on route or backend authorization-dependency drift.

The evidence is intentionally not adequate for final WS03-04 parent closure. Gate B stops before Gate C, and later children must consume this matrix rather than treating it as completed authorization behavior proof.
