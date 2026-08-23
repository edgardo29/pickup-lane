# WS04-01B - Query, Cursor, And Database-Access Behavior

This pass makes current API collection queries bounded, deterministic, and
honest about the database access they perform.

## 1. What This Work Does

This section explains the database-access surface covered by this pass and the
result the implementation must produce.

Pickup Lane already has several deliberate pagination contracts. Public game
cards, My Games cards, Need-a-Sub cards, inbox feeds, admin money lists, admin
game lists, admin user lists, admin review cases, platform notices, and selected
chat-message views use route limits, cursor values, offsets, or parent-scoped
limits.

The repository also still contains current collection routes whose database
access is only recorded as unresolved. Some are generic unbounded lists. Some
are child collections under a parent object but lack an explicit page contract.
Some use search, filters, relationship checks, or sorted database reads without
current tests proving the route's limit, ordering, cursor context, and index
support.

This pass turns that mixed state into a current database-access contract:

- every current collection route is bounded, parent-scoped with a clear finite
  shape, or removed from the live API if it is not a valid current route;
- cursor pagination uses deterministic ordering and rejects malformed or
  mismatched cursors;
- list queries keep their authorization, parent-object, filter, and search
  constraints inside the database query;
- indexes and query shapes are reviewed against the current source rather than
  guessed from future workload assumptions;
- obvious avoidable N+1 list behavior is removed where current list responses
  serialize related records.

This pass does not choose production query-plan thresholds, provider-specific
performance targets, production data-volume assumptions, telemetry alerts,
transaction-locking rules, or the production database connection budget. Those
facts require production or later database work.

## 2. What Must Be True

This section defines the engineering outcomes that make the pass complete. The
requirements are about the behavior of current database reads, not about future
provider capacity or speculative optimization.

### 2.1 Current Collection Routes Are Bounded

Every current live collection route must have one deliberate database-access
shape:

- a limit-based page;
- a cursor-based page;
- an offset-based page with an explicit maximum page size;
- a parent-scoped child list whose maximum result size is controlled by the
  parent object or by an explicit limit;
- or a clear removal/tombstone path if current source proves the route should no
  longer behave as a live collection route.

Generic collection routes must not execute an unbounded table read.

A route that accepts `limit` must enforce a minimum and maximum before the
database query runs. A service may clamp a limit only when the route and tests
make the effective maximum observable and deliberate.

New numeric limits must have a current source or approved product basis. This
pass must not invent arbitrary values only to make a route look bounded.

### 2.2 Pagination Order Is Stable

Every paginated query must use a deterministic order.

The order must include enough columns to make page boundaries stable when
multiple rows share the same primary sort value. In practice that means the
query order and cursor payload include the same tie-breaker, usually the row
identifier.

The database query must fetch one extra row when that is how the route computes
`has_more` and `next_cursor`.

Offset-based pages may remain only when they are explicitly bounded and ordered.

### 2.3 Cursors Match The Query That Created Them

A cursor must not be accepted for a different query context.

For a cursor route, the cursor validation must account for the fields that
change the result set, such as:

- view or status;
- search text or normalized search context;
- date or time window;
- sort direction;
- parent route object;
- feed name;
- current-user scope when the cursor is for a private user-specific feed.

Malformed cursors and cursors from the wrong context must fail with a stable
client error and must not expose raw database errors.

A cursor may be opaque and signed when the route needs tamper detection, as the
inbox feed already does. A cursor may also be decoded and validated when the
query itself still enforces all authorization and parent-object scope. In both
cases, cursor tampering must not widen the result set or bypass authorization.

### 2.4 Query Filters Stay Inside The Authorized Database Scope

List and search routes must apply authorization and object-binding constraints
before returning rows.

Private current-user lists must filter by the current user or by an equivalent
authorized relationship in the query. Admin lists must still require active
admin access and must not let path IDs, cursors, filters, or search parameters
escape the intended admin scope. Parent-scoped child lists must bind every row
to the parent object named in the route.

Unsupported filters, malformed filter values, invalid cursors, and missing
parent objects must have deliberate response behavior.

### 2.5 Current Query Shapes Match Current Indexes

The source must be reviewed so indexes match the actual database reads that the
current application performs.

The review must cover:

- list filters and parent foreign keys;
- sort columns used for pagination;
- cursor tie-breakers;
- prefix or case-insensitive searches;
- relationship `exists` predicates;
- status, lifecycle, and visibility filters;
- admin money, notice, review, user, game, Need-a-Sub, chat, image, policy, and
  history reads that remain live.

Index changes are allowed only when they support a current query. Do not add
speculative indexes for possible future searches or production workloads.

When an index is added, changed, or removed, the SQLAlchemy model and Alembic
migration state must remain aligned.

### 2.6 List Serialization Avoids Avoidable N+1 Reads

A bounded database query can still be unsafe if serializing each row performs
avoidable per-row related queries.

For list responses that include related users, games, venues, payments,
messages, audit records, or review targets, implementation must batch related
record loading when current source shows repeated per-row database access that
can be replaced with a page-level lookup.

This pass does not require a new generic data-loader abstraction. It requires
focused fixes where the current list response actually performs avoidable
repeated database reads.

### 2.7 Production Performance Claims Stay Out Of Source-Level Proof

This pass can prove repository behavior against PostgreSQL tests and source
inspection.

It cannot prove production row counts, query plans, lock observations, index
selectivity, autovacuum behavior, real provider latency, or deployed workload.

Tests and documentation must state that boundary honestly. They may verify the
query shape, ordering, cursor behavior, source indexes, and regression behavior
that are available from the repository.

## 3. Design

This section explains how the implementation should make the requirements true
using the current application shape. The design starts from the existing
pagination inventory, route source, service queries, models, and migrations.

### 3.1 Reconcile The Current Collection Inventory

The current inventory records 77 relevant collection routes: 34 with explicit
contracts and 43 still listed as unresolved collection-route entries.

Implementation should rebuild that inventory from current route source and
compare it to the registered contract inventory. Every current collection route
must end in one of these states:

1. it has an explicit contract with method, path, style, limit behavior,
   ordering, and cursor or offset behavior where applicable;
2. it is parent-scoped and finite for a current domain reason that is tested and
   documented in the contract;
3. it is not a live collection route and is removed or represented by the
   current API's tombstone behavior;
4. it cannot be made honest without a new owner/product decision, in which case
   implementation must stop rather than invent a value.

The old unresolved category should not remain a parking lot for database-access
work that this pass owns.

### 3.2 Keep Existing Good Contracts And Correct The Incomplete Ones

Existing contracts should be preserved when current source proves they are
accurate.

Examples include the current keyset-style public card lists, My Games card
lists, Need-a-Sub card lists, inbox feeds, admin money lists, admin user list,
admin game lists, review-case list, platform-notice lists, and selected chat
message pages.

For each route, implementation must check that the route, service, schema, and
tests agree on:

- accepted query parameters;
- effective limit;
- maximum limit;
- ordering;
- cursor or offset behavior;
- response fields such as `has_more` and `next_cursor`;
- authorization and parent-object binding.

When the inventory is wrong, the route/service contract should be corrected.
When the route is wrong, the route or service should be corrected.

### 3.3 Treat Generic Lists Differently From Parent-Scoped Child Lists

Generic lists and parent-scoped child lists have different database risks.

Generic lists such as all users, venues, bookings, payments, refunds, policy
records, notifications, game credits, game chats, and provider events must not
read the whole table. They need a deliberate page contract or a current API
decision that the route is no longer live.

Parent-scoped child lists such as game participants, official-game bookings,
waitlists, Need-a-Sub positions, Need-a-Sub requests, and status-history records
may be acceptable without cursor pagination only when the parent object and
current domain rules bound the result size clearly enough for this API. If that
is not true, they need an explicit limit or page contract.

This distinction prevents the implementation from adding unnecessary cursor
machinery to small parent-scoped collections while still forbidding broad
unbounded table reads.

### 3.4 Validate Cursor Context At The Service Boundary

Cursor decoding and validation should live close to the service query that uses
the cursor.

Each cursor family must define the payload values it needs to continue the same
query. The validation should reject:

- invalid encoding;
- missing required payload fields;
- wrong data types;
- cursor values that do not parse as the expected UUID, timestamp, integer, or
  enum-like value;
- query-context mismatch.

For public date-scoped card lists, the cursor context includes the date window
and the ordered row values.

For current-user lists, the query must still bind the rows to the current user.
If the cursor payload carries user-specific context, that context must match the
current user.

For admin search and filter lists, the cursor context must include enough
normalized filter state that a cursor generated for one filter cannot be reused
under another filter.

For inbox feeds, the existing signed cursor behavior should remain because
those cursors carry feed state and read-state behavior.

### 3.5 Align Indexes With Real Queries

Index review should start from the current queries, not from a generic list of
tables.

For each live list/search/cursor route, implementation should identify the
columns used for:

- filtering;
- parent binding;
- lifecycle/status visibility;
- ordering;
- cursor tie-breaks;
- joins or relationship existence checks.

If the existing model and migrations already support the query, tests should
prove the support rather than adding a duplicate index.

If a current query lacks source-level index support, the smallest useful model
and migration change should be made. For case-insensitive or prefix search,
implementation should choose only indexes that match the actual PostgreSQL
expression or operator used by the current query.

This pass does not run production `EXPLAIN` plans or choose indexes based on
unknown production cardinality. It establishes that repository-defined queries
and indexes are coherent for the current application behavior.

### 3.6 Batch Related Data Where The Current List Needs It

Several list responses serialize data from more than one table. The preferred
shape is:

1. query the bounded page of primary rows;
2. collect the related identifiers from that page;
3. load each related table once for the page;
4. serialize from the loaded maps.

This keeps query count bounded by page shape instead of page size.

Implementation should apply that shape to current list serializers only where
source inspection shows repeated per-row related reads. It should not introduce
a new framework-wide loading abstraction unless the current duplication
requires one.

## 4. Failures And Edge Cases

This section defines the abnormal cases that matter for this pass. Correct
handling protects the database from unbounded reads and protects clients from
ambiguous pagination behavior.

1. **Unbounded collection route**
   - **Condition:** A live collection route can read a whole table or an
     unbounded relationship collection.
   - **Required behavior:** The route is given a deliberate page contract,
     constrained by a real parent-scoped bound, or removed/tombstoned if it is
     not a valid current collection route.

2. **Unsupported or too-large limit**
   - **Condition:** A request supplies a missing, zero, negative, too-large, or
     otherwise unsupported page-size value.
   - **Required behavior:** The route either rejects the request through route
     validation or clamps it through a documented service maximum that tests can
     observe.

3. **Malformed cursor**
   - **Condition:** The cursor cannot be decoded, is missing required fields, or
     contains values of the wrong type.
   - **Required behavior:** The request fails with a stable client error and no
     raw database or internal parsing detail is exposed.

4. **Cursor from a different query**
   - **Condition:** A cursor generated under one view, search, date, status,
     parent, feed, sort direction, or private user context is reused under a
     different context.
   - **Required behavior:** The request fails as a cursor mismatch or otherwise
     cannot widen the authorized result set.

5. **Cursor anchor row changed or disappeared**
   - **Condition:** The row represented by a cursor was deleted or changed after
     the cursor was issued.
   - **Required behavior:** The next page remains deterministic for the query's
     current data and does not crash or leak rows outside the authorized scope.

6. **Duplicate primary sort values**
   - **Condition:** Multiple rows have the same timestamp, status rank, score,
     or other primary sort value.
   - **Required behavior:** The query uses a tie-breaker so rows are not
     duplicated or skipped at page boundaries.

7. **Missing parent object**
   - **Condition:** A parent-scoped child-list route names a game, Need-a-Sub
     post, notice, request, refund, user, or other parent record that does not
     exist or is not visible to the actor.
   - **Required behavior:** The response follows the current route's deliberate
     missing-object or concealment behavior and does not return unrelated child
     rows.

8. **Unsupported filter or search value**
   - **Condition:** A request supplies a filter, status, sort, search, or view
     value outside the current route contract.
   - **Required behavior:** The request is rejected or normalized exactly as the
     route contract defines before the database query runs.

9. **Query/index mismatch**
   - **Condition:** A current list or search query relies on a filter, parent
     key, sort, or expression that the schema does not support in source.
   - **Required behavior:** The schema is corrected when source-level support is
     required, or the implementation records why the current route does not
     require an index change.

10. **Avoidable per-row related queries**
    - **Condition:** Serializing one page performs repeated database reads for
      related records that could be loaded once for the page.
    - **Required behavior:** The serializer uses page-level related-data
      loading and tests prove query count remains bounded for the representative
      list.

## 5. Testing

This section explains what the tests must prove. The tests should focus on
database-access behavior that the repository can verify with PostgreSQL and
current source.

### 5.1 Inventory And Route Contract Tests

Tests must prove that the live route inventory and pagination contract
inventory agree.

They should verify that every current collection route is classified as a
bounded contract, a deliberately finite parent-scoped list, or a non-live
route. No current collection route should disappear from the inventory.

The tests should also prove that route-level query parameters and service-level
effective limits agree for the routes changed by this pass.

### 5.2 Cursor And Pagination Behavior Tests

PostgreSQL-backed tests must cover representative cursor families and every
changed cursor family.

The tests should prove:

- first page and next page behavior;
- `has_more` and `next_cursor` behavior;
- deterministic ordering with duplicate primary sort values;
- invalid cursor rejection;
- context mismatch rejection;
- stale or deleted cursor anchor behavior where current source can make that
  deterministic.

For offset routes that remain, tests must prove the page size is bounded and the
ordering is deliberate.

### 5.3 Authorization And Parent-Binding Tests

Tests must prove that list and search routes do not escape their intended scope.

That includes current-user lists, admin lists, parent-scoped child lists, and
routes whose cursors or filters could otherwise be reused across contexts.

The tests should focus on behavior that changed or was previously unresolved.
They should reuse accepted authorization evidence where the only question is
database access, not re-prove every unrelated authorization case.

### 5.4 Query And Index Alignment Tests

Tests or source checks must prove that changed query shapes have matching
schema support.

When the pass adds, changes, or removes an index, tests must verify the model
and migration state agree.

When no index change is made for a reviewed query, the testing record should
explain the source-level reason concisely, such as an already matching index,
an existing parent-bound small collection, or a route removal.

### 5.5 Bounded Serialization Tests

For list serializers changed to avoid repeated related-record reads, tests must
prove the response remains correct and the number of relevant database reads is
bounded for the page.

The test should measure the material query pattern, not incidental framework
queries that are unrelated to the list behavior.

### 5.6 Validation Limits

The repository can prove source behavior, PostgreSQL-backed cursor behavior,
schema/index alignment, and route contract consistency.

It cannot prove production query-plan quality, production row estimates,
provider latency, autovacuum behavior, real workload distribution, or live
concurrent page races. Those claims must not be made by this pass.

## 6. Done When

This section defines the engineering completion bar. The pass is complete only
when the current application has an honest database-access contract for its
collection routes.

- [ ] Every current collection route is bounded, deliberately parent-scoped, or
  no longer live.
- [ ] The pagination inventory has no unresolved database-access entry for
  work owned by this pass.
- [ ] Every cursor route uses deterministic ordering and validates the query
  context needed for that route.
- [ ] Invalid, mismatched, and stale cursors have stable tested behavior.
- [ ] Current-user, admin, and parent-scoped list queries keep authorization and
  object binding inside the database query.
- [ ] Current list/search query shapes and schema indexes are aligned without
  speculative index additions.
- [ ] Changed list serializers avoid material per-row related-record query
  growth.
- [ ] Tests cover the changed inventory, route contracts, cursor behavior,
  parent binding, index alignment, and bounded serialization behavior.
- [ ] Documentation and test records make no production performance,
  provider-runtime, or workload claims that the repository cannot prove.
