# Testing Record: WS04-01B - Query, Cursor, And Database-Access Behavior

## Scope

This record covers trusted local evidence for `WS04-01B`, the second child of
`WS04-01`. The evidence proves that current API collection routes have explicit
database-access contracts, bounded `limit` and `offset` behavior where this pass
added offset pages, stable ordering metadata, cursor context rejection for admin
money lists, user/parent scope binding in representative service reads, and a
batched list-serialization contract for Need-a-Sub and notifications whose
material related-record reads remain page-bounded.

This pass does not prove production query plans, production row counts, real
provider latency, provider connection limits, index selectivity under production
data, or deployment-wide database capacity.

## Requirement Mapping

| Requirement | Evidence |
| --- | --- |
| `WS04-01B-R1` | Inventory tests prove all `77` current collection routes are represented as explicit contracts and `PAGINATION_HANDOFFS` is empty. |
| `WS04-01B-R2` | Contract tests prove each newly bounded offset route exposes `limit` and `offset` parameters with the registered default, maximum, and deterministic-order metadata. Focused API evidence proves mixed self/admin `/bookings`, `/payments`, `/refunds`, and `/game-credits` routes expose one shared effective maximum. Source review confirms service queries include ID or stable unique tie-breakers where row ordering needs one. |
| `WS04-01B-R3` | PostgreSQL-backed cursor tests prove the changed admin money payment, refund, refund-event, credit, and money-issue cursor families provide first-page and next-page behavior, `has_more` / `next_cursor`, stable malformed-cursor rejection, and stable query-context mismatch rejection. |
| `WS04-01B-R4` | Service-source tests prove representative private and parent-scoped lists keep user or parent binding in the database query before applying offset and limit. |
| `WS04-01B-R5` | Source checks assert the current model index support used by reviewed changed query families, including user, game, payment, refund, refund-event, credit, money-issue, notification, policy, payment-event, image, booking, waitlist, and Need-a-Sub reads. No speculative index was added for future workload assumptions. |
| `WS04-01B-R6` | PostgreSQL-backed tests prove Need-a-Sub request waitlist-ahead counts remain correct when off-page waitlist rows exist and the material waitlist-count rows are limited to the returned page. Additional PostgreSQL-backed tests prove `/need-a-sub/posts`, `/need-a-sub/posts/mine`, and `/notifications/me` batch related records once per page instead of doing avoidable per-row related reads. |
| `WS04-01B-R7` | Testing-record evidence states the local proof boundary and does not claim production query plans, provider latency, production row counts, or deployed workload behavior. |

## Evidence Quality Notes

- Tests use synthetic data in the dedicated local test database and do not
  contact production infrastructure.
- The pagination inventory test compares registered contracts with the live
  FastAPI route table.
- Cursor tests exercise service-owned helper behavior directly so malformed and
  mismatched cursor handling remains stable without relying on raw database
  exceptions.
- PostgreSQL-backed cursor tests cover every admin money cursor family changed
  by this pass: payments, refunds, refund events, credits, and money issues.
- Index source checks intentionally verify model metadata and current query
  support. They do not claim production selectivity or production query-plan
  quality.
- Need-a-Sub request-list evidence counts only the material list serializer
  query pattern: one requester lookup and one page-row waitlist-ahead aggregate
  for a multi-row page that has off-page waitlist rows ahead of it.
- Need-a-Sub post-list evidence proves public and owner list responses batch
  request counts, positions, and position request counts once per returned
  page.
- Notification-list evidence proves game actions, Need-a-Sub post actions, and
  Need-a-Sub chat-access checks batch related rows once per returned page.
- Mixed self/admin route evidence proves `/bookings`, `/payments`, `/refunds`,
  and `/game-credits` reject limits above the shared route/service maximum.
- The focused workflow suite proves source-level API and service behavior. It
  does not claim production provider capacity or production query-plan evidence.
- Checker `PASS` results are structural and traceability checks; semantic
  adequacy comes from the focused behavior assertions and this record.

## Validation Results

- Focused WS04-01B evidence and pagination inventory compatibility:
  `18 passed`.
- WS04-01B requirement mapping/domain checker: `PASS`.
- Repository suite checker: `PASS`.

## Boundaries

- Production query-plan thresholds, provider-specific performance targets,
  telemetry alerts, production row counts, and deployment-wide database capacity
  remain later or external evidence responsibilities.
- This pass does not define production PostgreSQL topology, pooler/proxy mode,
  deployed process counts, or concrete production role grants.

## Final Self-Review

- This record contains no literal credentials, credential-bearing URLs, private
  keys, tokens, personal/payment data, provider-private values, raw sensitive
  logs, local machine paths, usernames, session state, or internal chat
  material.
- Requirement IDs preserve the meanings frozen in the approved WS04-01B plan.
- Remaining boundaries are concrete and do not overclaim local pytest evidence.
