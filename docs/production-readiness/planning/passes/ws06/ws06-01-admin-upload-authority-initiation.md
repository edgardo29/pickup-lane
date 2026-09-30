# WS06-01 - Admin upload authority and initiation

This pass makes venue-image upload initiation an expiry-bound, server-owned workflow that only an active administrator can start and that can be completed exactly once at the application layer without allowing another API path to bypass the upload intent.

This document is the engineering blueprint for this pass.

## 1. What This Work Does

Venue photos already use a direct-to-R2 upload flow. An active administrator asks the backend for an upload URL, the backend chooses the venue-image ID and R2 object key, the browser uploads directly to the returned presigned `PUT` URL, and the browser then calls the backend completion endpoint. The backend already stores the initiating administrator, venue, object key, bucket/account identity, declared content type and size, and current image state.

The current flow does not persist the expiry of the issued upload capability. The completion endpoint therefore cannot determine whether the specific upload intent is still valid. It also accepts any non-removed image row, so an already active or hidden row can be sent through completion again. In addition, the general venue-image update path can currently move rows into or out of `pending_upload`, which lets an ordinary metadata/status update bypass the intended creation-and-completion lifecycle. Two concurrent completion requests can also observe the same pending row before either commits and both attempt the same state/audit effects.

After this pass:

- initiation remains restricted to the existing active-admin route;
- the venue must be active when the intent is created;
- the backend remains the only authority for image identity, venue binding, object key, storage target, and initiating actor attribution;
- every newly created `pending_upload` row carries the exact expiry returned by the R2 upload-ticket signer;
- the existing three-selected-photo limit is serialized per venue across upload initiation and `hidden -> active` reactivation, including races between those operations;
- an upload can become active only through the completion endpoint while that persisted intent is pending, unconsumed, and unexpired;
- completion is a single durable application transition even when requests race;
- the general update endpoint cannot manufacture a new pending intent or activate an uncompleted pending upload;
- repeated initiation requests remain separate upload intents because the API has no idempotency identity for initiation;
- the existing browser sequence and upload response shape remain compatible.

This pass does not perform image decoding, pixel/resource validation, metadata stripping, safe re-encoding, or publication sanitization. It also does not add abandoned-upload cleanup, object repair, production R2 credential/CORS proof, a second upload-intent table, or a generalized storage-management system.

## 2. What Must Be True

These requirements define the upload-intent contract that must hold after the pass. They focus on who may issue a capability, what that capability is bound to, when it remains valid, and how the application prevents stale or repeated completion from changing state again.

### 2.1 Only the approved administrator path can create an upload intent

The upload-URL endpoint must continue to require the existing `require_active_admin` dependency. Anonymous users, ordinary users, inactive administrators, suspended/deleted accounts, and any other actor rejected by that dependency must be denied before the venue-image service can create a row or ask the R2 signing adapter for an upload capability.

The service must continue to resolve the target venue from the path-owned venue ID and reject a missing, deleted, or inactive venue before signing an upload URL. The client must not be able to supply an actor ID, object key, bucket, account ID, or alternate target venue through the upload request.

### 2.2 Identity and storage binding are server-owned

For each successful initiation, the backend must generate a new venue-image UUID and derive the R2 object key from server-controlled values. The persisted row must bind that UUID to:

- the target venue;
- the authenticated administrator that initiated the upload, subject to the existing user-deletion foreign-key behavior;
- storage provider `r2`;
- the configured bucket/account identity used for the ticket;
- the exact generated object key;
- the normalized declared content type and declared size;
- the existing image-role, primary, ordering, alt-text, and caption fields.

None of those actor/venue/object identity fields may become mutable through the completion or general update request schemas. A different active administrator may complete or administratively manage an existing intent under the existing admin authorization model, but doing so must not rewrite who originally initiated the upload or which venue/object the intent targets. Audit records continue to identify the administrator performing each administrative action.

### 2.3 Every pending intent has an exact persisted expiry

The existing R2 upload-ticket signer remains responsible for choosing the upload capability lifetime from the configured `R2_UPLOAD_URL_MINUTES` value and for returning the resulting timezone-aware `expires_at` value.

The venue-image row must persist that exact `expires_at` as `upload_expires_at` when the intent is created. The application must not recompute an old intent's deadline from the current setting later. Changing `R2_UPLOAD_URL_MINUTES` therefore affects only subsequently issued capabilities; each existing intent is governed by its own persisted deadline.

No new numeric lifetime is introduced by this pass. The existing configured value remains the source for newly signed URLs.

The presigned URL itself, its signature/query parameters, and any credential-bearing representation must not be persisted in the venue-image row, audit metadata, or application logs. The API continues to return the presigned URL only to the authorized caller that created the intent.

### 2.4 `pending_upload` represents one unconsumed, expiry-bound intent

A row in `pending_upload` must satisfy both of these conditions:

- `upload_expires_at` is present;
- `upload_completed_at` is null.

The database must enforce that invariant so a future caller cannot persist a malformed pending intent even if service validation is bypassed.

`upload_expires_at` may remain nullable for non-pending rows. This preserves compatibility with existing non-pending data/setup patterns that may not have originated from a newly issued upload ticket while still making every actual pending intent complete and enforceable.

Expiration does not automatically mutate the row. An expired row remains `pending_upload` until an explicit administrative removal or lifecycle cleanup changes it, and it continues to participate in the existing selected-photo count while it remains pending. This pass must not introduce a scheduler, time-triggered state mutation, or new cleanup mechanism.

### 2.5 Completion is legal only for a live pending intent

The completion endpoint may transition a venue image to `active` only when all of the following are true at the point of the final database transition:

- the row still exists and is not soft-deleted;
- `image_status == "pending_upload"`;
- `upload_completed_at` is null;
- `upload_expires_at` is present;
- the current UTC time is strictly earlier than `upload_expires_at`;
- the R2 metadata lookup for the persisted object key succeeds;
- the existing declared-size check succeeds;
- the existing content-type comparison succeeds when R2 supplies a content type.

`now >= upload_expires_at` is expired. An expired intent must not be completed merely because an object happens to exist at its key.

A serial completion request for an expired intent or an already active/hidden intent must be rejected before another R2 metadata lookup. It must not change the venue-image row, primary-image state, audit history, or completion timestamp.

A soft-deleted removed image keeps the existing not-found behavior. If a row is ever observed with `image_status == "removed"` but without the normal soft-delete marker, the existing removed-image rejection remains safe and non-mutating.

### 2.6 Completion must be single-consumption under concurrency

Two completion requests for the same pending intent must not both commit success.

The workflow must avoid holding a database row lock across the R2 metadata request. It may perform an initial local eligibility check and the provider `HEAD` first, but immediately before changing local state it must lock and reload the venue-image row from PostgreSQL and repeat all state/consumption/expiry checks against that fresh locked row.

Exactly one contender may then perform the `pending_upload -> active` transition, set `upload_completed_at`, apply the existing primary-image behavior, write the success audit action, and commit. A contender that reaches the lock after the row was already consumed must receive a conflict response and must not write a second success audit action or repeat primary-image side effects.

The existing unique partial index for one active primary image per venue remains the database backstop for primary-image uniqueness. This pass does not replace that constraint with a new mechanism.

### 2.7 General updates cannot bypass the intent lifecycle

The general venue-image update endpoint may continue to edit the fields it already owns, including supported administrative visibility/removal behavior, but status changes must obey this lifecycle:

| Current status | Requested status through PATCH | Required behavior |
|---|---|---|
| `pending_upload` | `pending_upload` | Allowed as a same-state update; the existing intent and expiry are unchanged. |
| `pending_upload` | `active` | Reject. Activation must go through upload completion. |
| `pending_upload` | `hidden` | Reject. A not-yet-completed upload cannot be hidden as if it were completed media. |
| `pending_upload` | `removed` | Allowed under the existing removal/audit-reason rules. |
| `active` | `active` | Allowed as a same-state update. |
| `active` | `hidden` | Allowed; preserve existing hide behavior. |
| `active` | `removed` | Allowed under the existing removal rules. |
| `active` | `pending_upload` | Reject. An existing image cannot be turned into a new upload intent. |
| `hidden` | `hidden` | Allowed as a same-state update. |
| `hidden` | `active` | Allowed only while the venue remains below the three-selected-photo limit; otherwise return the existing selected-photo capacity rejection. |
| `hidden` | `removed` | Allowed under the existing removal rules. |
| `hidden` | `pending_upload` | Reject. An existing image cannot be turned into a new upload intent. |
| `removed` | any | Preserve the existing deleted/not-found boundary; no new transition is introduced. |

When `image_status` is omitted, the update remains a metadata update and must not alter upload expiry or completion state.

Invalid lifecycle requests must fail before the service writes an audit success record or mutates image/primary state.

### 2.8 Repeated initiation is not idempotent, and selected-photo capacity is serialized

The initiation request has no request ID or idempotency key in its public contract. Two otherwise identical valid `POST /admin/venues/{venue_id}/images/upload-url` requests are therefore two distinct upload intents, each with a new server-generated image ID, object key, and expiry.

This pass must not infer duplicate identity from file name, content type, size, venue, or image metadata, and it must not introduce a generic idempotency subsystem merely to collapse repeated clicks.

The accepted venue limit remains three non-deleted images whose status is `pending_upload` or `active`. Two operations can increase membership in that selected set:

- creation of a new `pending_upload` intent;
- reactivation of a `hidden` image through `hidden -> active`.

Both producers must serialize on the same venue row before counting selected images and must hold that venue lock through their local mutation and commit. The count must be repeated while the lock is held. This common lock makes two initiations, two reactivations, and an initiation racing a reactivation observe one ordered capacity decision. At most one contender may take the final available selected-photo slot. A loser receives the existing client-safe `400` selected-photo capacity response and must not persist its state change or success audit. A losing initiation must be rejected before an upload or read capability is signed.

Completion does not increase selected-set membership because `pending_upload` and `active` are both already selected. It therefore continues to use the image-row completion lock rather than acquiring the venue capacity lock solely for counting.

### 2.9 R2 capability scope and observable behavior remain truthful

The generated capability must remain a presigned `PUT` for exactly the server-generated object key and configured bucket, with the existing signed content-type requirement and returned upload headers. The browser continues to send only those upload headers to R2 and must not send Firebase credentials or other application authentication to the storage endpoint.

The application-level single-consumption guarantee does not claim that an R2 presigned `PUT` URL is cryptographically one-use. A holder of a still-valid URL may be able to reuse that provider capability until its expiry according to provider behavior. This pass bounds that capability by the exact persisted expiry and prevents repeated backend completion/state effects; it does not invent unsupported provider revocation or conditional-write behavior.

Provider operation metrics and storage-failure logging must continue to use the existing R2 operation/result vocabulary. Presigned URLs, signatures, credentials, and raw provider-private values must not be added to those events.

### 2.10 Existing API and product behavior remains compatible

The existing upload response continues to contain `image`, `upload_url`, `upload_headers`, and `expires_at`. The `expires_at` returned to the browser must be the same value persisted for that intent.

`upload_expires_at` is internal lifecycle state and does not need to be added to the ordinary `VenueImageRead`/admin-list response. The current browser flow remains:

1. request an upload ticket;
2. `PUT` the file directly to the returned R2 URL;
3. call the completion endpoint using the returned image ID.

The current three-selected-photo boundary, declared content-type/size checks, object metadata checks, public visibility filtering, primary-image behavior, and safe admin audit attribution remain in force. Missing R2 content-type metadata continues to follow the current accepted behavior; this pass does not turn metadata-only checks into image-content validation.

## 3. Design

The design uses the existing `venue_images` row as the upload intent. One persisted expiry field and one compact database check make the intent enforceable without introducing a second table or workflow. Service-level lifecycle checks then make completion time-aware and single-consumption while preserving the existing direct browser-to-R2 transport.

### 3.1 Persist the signer-issued expiry on `venue_images`

Add a timezone-aware nullable `upload_expires_at` column to the `VenueImage` model and to the existing canonical `venue_images` migration. Do not create a patch migration: the repository's current pre-production migration policy requires changes to an existing table to be made in that table's canonical migration and validated through a clean rebuild.

The column has no server default. Its value must come from the exact `R2ObjectUploadTicket.expires_at` returned for the intent being persisted.

Add one database check constraint equivalent to:

```sql
image_status <> 'pending_upload'
OR (
    upload_expires_at IS NOT NULL
    AND upload_completed_at IS NULL
)
```

The model and canonical migration must use the same named constraint. The constraint exists because `pending_upload` is no longer merely a display status; it denotes a real unconsumed capability with a known deadline.

No index on `upload_expires_at` is required by this pass because no WS06-01 query discovers rows by expiry. Adding a speculative expiry index for future cleanup would exceed the current need.

The conflict-detail mapping must recognize the new named constraint so an unexpected database-enforced rejection does not fall through to raw PostgreSQL error text. Normal service validation should reject invalid transitions before the constraint is reached.

### 3.2 Serialize capacity, then create and commit an intent without persisting capability secrets

The initiation workflow keeps its existing transaction owner, records the ticket expiry, and closes the accepted selected-photo race before issuing a capability.

The sequence is:

1. the route establishes an active administrator through the existing dependency;
2. the service verifies that the target venue exists and is active before any capability is signed;
3. the service applies the existing request and declared type/size checks;
4. the service acquires a PostgreSQL `FOR UPDATE` lock on the target venue row and revalidates that the venue still exists, is not deleted, and is active;
5. while holding that lock, the service repeats the selected-photo count and rejects at three before signing;
6. the service resolves the configured R2 storage identity and generates a new image UUID and object key;
7. the R2 signer creates the object-specific `PUT` ticket and returns its exact expiry;
8. the service constructs the `pending_upload` row with `upload_expires_at = upload_ticket.expires_at`;
9. the row and existing create audit action are flushed together;
10. before committing, the service signs the read URL required by the unchanged nested admin image response and retains it only in the in-memory response;
11. the row and audit action commit while the venue lock is still held;
12. only after successful local persistence does the route return the already-constructed response containing the upload ticket and read URL.

Upload- and read-URL generation are local signing operations, not provider network mutations, so holding the venue lock across those bounded calls does not hold a database lock across external I/O. Any validation, signing, flush, or commit failure after lock acquisition rolls back the transaction and releases the venue lock. A failed transaction must never return either capability to the caller. The presigned URLs and signatures are transient response data only.

The existing create audit remains attributable to the authenticated administrator and target venue/image. The row's `uploaded_by_user_id` remains the immutable initiation provenance; normal account-deletion `SET NULL` behavior is not changed.

### 3.3 Validate completion before provider work, then lock and revalidate before commit

Completion uses two local validation points around the provider metadata request.

First, load the current row without a write lock and reject obvious non-completable cases before contacting R2:

- deleted/not found;
- removed;
- status other than `pending_upload`;
- already populated `upload_completed_at`;
- missing expiry;
- `now >= upload_expires_at`.

If the intent is locally eligible, perform the existing R2 `HEAD` against the persisted object key and preserve the existing provider-result, size, and content-type handling.

After the provider checks succeed, acquire a PostgreSQL row lock for the same venue-image ID and force a fresh database read rather than relying on a previously cached SQLAlchemy object. Under that lock, repeat the deleted/status/completed/expiry checks using a newly captured UTC time. This second check handles:

- another completion that committed while the provider request was in flight;
- an administrator that removed or changed the image while the provider request was in flight;
- an intent that crossed its expiry while the provider request was in flight.

Only the fresh locked `pending_upload` row may transition to `active`. Set `upload_completed_at` once. Preserve the current ETag precedence exactly: a non-empty ETag supplied by the completion request wins; otherwise use the ETag returned by R2 metadata lookup; otherwise retain the row's existing ETag. Then perform the existing primary-image clearing/assignment, write and flush the success audit action, and sign the read URL required by the admin response before committing the transition. After commit, construct or return the response with that already-signed URL; do not perform another failure-prone signing operation after the durable state change.

If response read-URL signing fails, roll back the image transition, completion timestamp, primary-image changes, and success audit together. The intent remains pending and unconsumed and may be retried only while it remains unexpired. A read URL generated for a transaction that later fails is never returned or persisted.

A lifecycle rejection uses a stable client-safe conflict response. In particular, an active/hidden replay and an expired pending intent return `409 Conflict` rather than being treated as another successful completion. Existing not-found, removed-image, provider-configuration, provider-failure, object-not-found, size-mismatch, and content-type-mismatch response classes remain unchanged.

### 3.4 Make the general update path obey the status matrix

Keep lifecycle validation in the existing venue-image service because it depends on current persisted state. A PATCH that requests a status must lock and freshly reload the target image before comparing its current status with the allowed transition table in Section 2.7.

For `hidden -> active`, acquire and hold the same venue-row capacity lock used by initiation, repeat the count of non-deleted `pending_upload` and `active` rows, and reject with the existing `400` capacity response when three already exist. Only a reactivation that owns the venue lock and observes an available slot may update the image and write its success audit. Holding the common venue lock through commit serializes reactivation with every initiation and other reactivation for the venue.

Do not add another state-machine module or database trigger. The service is already the owner of venue-image transitions, and the database pending-intent constraint remains the compact final backstop.

The update path must never alter `upload_expires_at` or `upload_completed_at` as a side effect of an ordinary PATCH. A same-state `pending_upload` update preserves the original ticket and deadline; it does not refresh, extend, or reissue the capability. Creating a new capability requires a new initiation request and therefore a new image ID/object key.

For every successful PATCH, flush the image and audit changes, sign the read URL needed by the unchanged admin response before commit, and then commit. A read-URL configuration or signing failure rolls back the PATCH and its audit action, so an error response never conceals an already-committed administrative update.

### 3.5 Preserve the existing R2 signing and browser contract

`create_object_upload_url` continues to sign `put_object` using the configured bucket, generated key, normalized content type, and existing `R2_UPLOAD_URL_MINUTES`. Its returned `expires_at` remains the authoritative per-ticket deadline.

No setting, provider client, transport wrapper, retry layer, or frontend API abstraction is added. The frontend upload helper can continue consuming the existing response fields and performing direct `PUT` followed by completion without modification to the request/response shape.

If the direct `PUT` itself fails because the provider capability is expired or rejected, the browser continues to treat that as an upload failure and does not call completion. A later retry of the whole upload flow obtains a new server-owned intent rather than extending the old one.

### 3.6 Define the complete provider and metadata outcome handling

The affected provider-operation family is `r2.upload.validate`, `r2.upload_url.create`, `r2.metadata.head`, and `r2.read_url.create`. Preserve those exact operation names and the accepted provider-result vocabulary rather than introducing endpoint-specific aliases.

| Operation | Provider result or local outcome | Required API and transaction behavior |
|---|---|---|
| `r2.upload.validate` | request/configuration validation succeeds | Continue. This validation-only operation does not emit a synthetic `succeeded` provider result because its accepted metric vocabulary contains only `configuration_error`. |
| `r2.upload.validate` | `configuration_error` | Emit the existing configuration result and safe storage failure event, return the existing `503` service-unavailable response, and perform no signing, capacity mutation, row write, or success audit. |
| `r2.upload.validate` | unsupported type, size, role, or other client input | Return the existing `400` client rejection without recording a provider result; no provider operation has failed. |
| `r2.upload_url.create` | `succeeded` | Retain the ticket in memory, persist its exact expiry, and return it only after the intent and audit commit. |
| `r2.upload_url.create` | `configuration_error` | Return the existing `503` service-unavailable response and roll back/no-op the local transaction. |
| `r2.upload_url.create` | `failed`, `rate_limited`, or `timed_out` | Preserve the existing safe `502` signing/provider-failure response and matching storage failure event; persist no intent or success audit and return no capability. |
| `r2.upload_url.create` | empty or malformed signing output | Validate the ticket inside the observed adapter before it records success, emit only `failed`, return the same safe `502` class, and do not expose or persist partial capability material. |
| `r2.metadata.head` | `succeeded` with usable metadata | Apply the existing size/type rules, then continue to final locked revalidation and at most one activation. |
| `r2.metadata.head` | `not_found` | Preserve the current `400` client response; leave the intent pending and unconsumed. The adapter-owned `not_found` result is sufficient; do not emit a duplicate generic storage-failure event. |
| `r2.metadata.head` | `configuration_error` | Preserve the current `503` service-unavailable response and configuration storage event; leave the intent pending and unconsumed. |
| `r2.metadata.head` | `timed_out` | Preserve `DependencyReadTimeoutError` and its distinct public `503`/`retry_later` contract; leave the intent pending and unconsumed and do not replace it with the generic `502` path or emit a duplicate storage-failure event. |
| `r2.metadata.head` | `rate_limited` or `failed` | Preserve the current safe `502` provider-failure response and storage failure event; leave the intent pending and unconsumed. |
| `r2.metadata.head` | malformed/unusable provider response | Classify it as `failed`, return the same safe `502` class without leaking provider data, and leave the intent pending and unconsumed. |
| completion metadata checks | matching size and matching/present type | Continue. |
| completion metadata checks | size mismatch or present content-type mismatch | Preserve the current `400` client rejection; leave the intent pending and unconsumed. |
| completion metadata checks | content type absent | Preserve the currently accepted behavior; do not invent byte/content validation here. |
| `r2.read_url.create` for initiation, completion, or PATCH | `succeeded` | Keep the signed URL transiently in the response being constructed; commit the associated mutation only after signing succeeds. |
| `r2.read_url.create` for initiation, completion, or PATCH | `configuration_error` | Return the existing `503` service-unavailable response and roll back the associated image/audit/primary mutation. No upload or read capability is returned. |
| `r2.read_url.create` for initiation, completion, or PATCH | `failed`, `rate_limited`, `timed_out`, or malformed/empty output | Validate signing output inside the observed adapter before it records success, emit only `failed` for malformed output, return the existing safe `502` read-URL/provider-failure response, and roll back the associated image/audit/primary mutation. No upload or read capability is returned. |

These are read or local-signing operations, not uncertain provider mutations, so this pass introduces no `pending` or `unknown_outcome` result. Cancellation must propagate rather than be converted into a provider result; if it occurs before commit, normal transaction cleanup must roll back and no capability may be returned. None of the failures above extends an intent deadline. A caller may retry completion only while the same persisted intent remains pending and unexpired.

### 3.7 Compatibility and migration behavior

The model and canonical migration must remain aligned. Because the canonical migration changes, clean test databases must be rebuilt before affected backend and migration tests are treated as valid. Migration validation must prove that a clean database reaches the current head with the new column and check constraint and that model/migration comparison does not show drift.

The schema change is deliberately compatible with non-pending rows that have no recorded upload expiry. Only `pending_upload` requires a non-null expiry and null completion timestamp. This avoids inventing a historical deadline for rows that did not originate under the new intent contract.

The public/admin read response does not grow a new field. The upload-ticket response already exposes `expires_at`, so the frontend contract remains stable while the backend gains the persisted value it needs for enforcement.

## 4. Failures And Edge Cases

The important abnormal cases are those that could otherwise issue an unauthorized capability, complete a stale intent, repeat durable effects, or leave the API claiming more provider certainty than it has.

1. **Unauthorized actor attempts initiation or completion**
   - **Condition:** Authentication or `require_active_admin` rejects the caller.
   - **Required behavior:** Reject before the venue-image workflow performs storage signing, metadata lookup, row mutation, or success auditing.

2. **Target venue is missing, deleted, or inactive at initiation**
   - **Condition:** The path venue ID does not resolve to an active venue.
   - **Required behavior:** Preserve the existing not-found response; do not sign an upload URL and do not create an intent.

3. **Declared upload request is outside current accepted bounds**
   - **Condition:** Unsupported image role/type, invalid size/order, or the selected-photo limit is already full when counted under the venue capacity lock.
   - **Required behavior:** Reject before signing/persistence according to the existing validation contract. Do not broaden current type/byte defaults into a new final image-security policy.

4. **Upload-ticket signing cannot run**
   - **Condition:** R2 configuration is unavailable or the signing adapter raises its provider/signing error.
   - **Required behavior:** Return the existing safe 503/502 class as applicable; create no venue-image row and no success audit.

5. **Local persistence fails after a ticket was generated**
   - **Condition:** Flush/commit fails because of schema readiness, integrity, or another local transaction error.
   - **Required behavior:** Roll back the local row/audit. Do not return the generated capability to the caller. Map known database constraints to safe details rather than exposing raw SQL errors.

6. **Intent expires before completion starts**
   - **Condition:** `now >= upload_expires_at` during the first local completion check.
   - **Required behavior:** Return `409 Conflict` before R2 metadata lookup. Leave the row pending/unconsumed and write no success audit.

7. **Intent expires while R2 metadata is being checked**
   - **Condition:** The first check passes but the deadline is reached before the final locked revalidation.
   - **Required behavior:** Reject at locked revalidation with `409 Conflict`; do not activate the image or write completion audit effects.

8. **Serial completion replay**
   - **Condition:** The same image is already active/hidden or otherwise no longer pending when completion is called again.
   - **Required behavior:** Return `409 Conflict` before another provider metadata request when the current local state already proves replay. Do not alter `upload_completed_at`, ETag, primary state, or audit history.

9. **Concurrent completion replay**
   - **Condition:** Two requests both pass initial eligibility/provider checks for the same pending image.
   - **Required behavior:** Final row locking/revalidation permits only one commit. The loser returns a conflict after acquiring the fresh row and writes no second completion audit or primary-image effect.

10. **Administrative PATCH attempts to bypass completion**
    - **Condition:** PATCH requests `pending_upload -> active`, `pending_upload -> hidden`, or any `active/hidden -> pending_upload` transition.
    - **Required behavior:** Return `409 Conflict` before mutation/audit. Existing allowed visibility/removal transitions continue to work.

11. **Uploaded object does not satisfy current metadata checks**
    - **Condition:** R2 cannot find the object, declared size differs, or a supplied provider content type differs from the stored declaration.
    - **Required behavior:** Preserve the current client rejection. Leave the intent pending, unconsumed, and subject to its original deadline.

12. **R2 metadata lookup is unavailable**
    - **Condition:** Configuration, timeout, rate limit, provider/transport failure, or malformed metadata prevents `HEAD` from producing usable metadata.
    - **Required behavior:** Preserve the distinct contracts in Section 3.6: configuration and read timeout return their `503` classes, with timeout retaining `retry_later`; rate-limit/provider/malformed failure returns the safe `502` class. Do not consume the intent, extend its deadline, duplicate adapter-owned timeout/not-found events, or leak provider details.

13. **Configuration changes after an intent is created**
    - **Condition:** `R2_UPLOAD_URL_MINUTES` changes between initiation and completion.
    - **Required behavior:** The existing intent continues to use its persisted `upload_expires_at`; the new configuration applies only to subsequently generated tickets.

14. **Repeated initiation with identical request metadata**
    - **Condition:** An administrator repeats the same valid initiation request.
    - **Required behavior:** Treat it as a new intent with a new image ID/key/expiry, subject to the existing selected-photo cap. Do not silently deduplicate it by file metadata.

15. **Provider URL is reused before its deadline**
    - **Condition:** A holder reuses the same presigned `PUT` URL while R2 still considers it valid.
    - **Required behavior:** Do not claim provider-enforced one-time capability semantics. Application completion remains single-consumption and expiry-bound; no second local completion/state/audit effect is permitted.

16. **Selected-photo producers race for the final slot**
    - **Condition:** Two initiations, two `hidden -> active` PATCH requests, or one of each concurrently observe a venue with only one selected-photo slot available.
    - **Required behavior:** Both operations serialize on the venue row and recount under that lock. At most one commits selected-set membership. The loser receives the existing `400` capacity response, writes no image/status/audit change, and, when the loser is initiation, signs and returns no capability.

17. **Read-URL signing fails while constructing a mutation response**
    - **Condition:** `r2.read_url.create` fails for initiation, completion, or PATCH after local changes have been staged but before commit.
    - **Required behavior:** Return the safe `503` configuration or `502` provider response from Section 3.6 and roll back all staged image, completion, primary-image, and success-audit effects. There is no post-commit read-signing step that can return an error after durable success.

18. **Request cancellation interrupts an uncommitted operation**
    - **Condition:** Cancellation occurs during validation, local signing, provider metadata lookup, lock acquisition, or other work before commit.
    - **Required behavior:** Propagate cancellation, allow transaction cleanup to roll back, and return no capability. Do not invent a provider result or success audit for an operation that did not commit.

## 5. Testing

Testing must prove that the new intent lifecycle is enforced at the API, service, PostgreSQL, and provider-adapter boundaries without relying on real production R2 configuration. Existing useful venue-image regression coverage should be preserved where it still represents current behavior, while new proof should be placed according to current behavior ownership rather than legacy location.

### 5.1 Authorization and initiation

Prove that:

- an active administrator can create an intent for an active venue;
- unauthorized/non-admin/inactive privileged actors are rejected before the R2 signer is invoked and before a venue-image/audit row is created;
- missing/deleted/inactive venue targets reject before signing;
- the generated image ID and object key are server-owned and the persisted actor/venue/object binding matches the authenticated request context;
- the exact fake signer `expires_at` value is persisted as `upload_expires_at` and returned unchanged in the API response;
- the presigned URL is not persisted in the venue-image row or audit payload;
- upload validation and upload-ticket configuration/provider failures use the exact operation/result contracts in Section 3.6 and leave no intent/success audit;
- initiation read-URL configuration/provider failure rolls back the image and create audit and returns neither the upload nor read capability;
- two identical successful initiation requests create distinct IDs/keys rather than being treated as idempotent replays;
- the accepted three-selected-photo limit continues to count non-deleted pending/active images as it does today.

### 5.2 Pending-intent persistence and migration

Using real PostgreSQL/migration validation, prove that:

- the canonical `venue_images` migration creates `upload_expires_at` with timezone support and the model matches it;
- a `pending_upload` row without `upload_expires_at` violates the named pending-intent check;
- a `pending_upload` row with a non-null `upload_completed_at` violates the same invariant;
- a valid pending row with expiry and null completion succeeds;
- non-pending rows are permitted to have a null expiry for compatibility;
- a clean rebuild reaches the current Alembic head and model/migration drift checks remain clean.

Because the canonical migration is edited, affected test databases must be rebuilt from the updated migration history before ordinary/migration results are accepted.

### 5.3 Lifecycle and replay matrix

Exercise the complete authoritative status set: `pending_upload`, `active`, `hidden`, and `removed`.

Prove the PATCH transition matrix in Section 2.7, including all transitions that are deliberately rejected. For every rejected mutation, verify both the response and the absence of prohibited persistence/audit/primary-image changes.

For completion, prove that:

- valid pending/unconsumed/unexpired transitions to active once;
- `upload_completed_at` is set once and the original `upload_expires_at` remains unchanged;
- active/hidden completion replay returns conflict and does not call R2 again in the serial case;
- expired pending completion returns conflict before R2 lookup;
- equality at the deadline is expired;
- changing the configured TTL after creation does not change an existing intent's deadline;
- removed/deleted behavior remains consistent with the existing not-found/removed boundary.

### 5.4 Concurrent completion

Use independent PostgreSQL sessions and deterministic synchronization around the final completion transition so two completion attempts act on the same pending intent.

The proof must establish that:

- only one request commits `pending_upload -> active`;
- only one completion success audit action is persisted;
- `upload_completed_at` represents the single committed consumption;
- primary-image changes are applied once and the existing one-active-primary database constraint remains satisfied;
- the losing request observes the fresh locked state and returns a conflict rather than reporting success.

The provider metadata call may be faked at the existing application-owned R2 boundary; this test is proving local concurrency semantics, not Cloudflare behavior.

### 5.5 Concurrent selected-photo capacity

Use independent PostgreSQL sessions and deterministic synchronization around the common venue-row lock. Begin with exactly two selected images, so only one selected-photo slot remains, and prove all three producer pairings:

- initiation racing initiation;
- `hidden -> active` racing `hidden -> active` for two different hidden images;
- initiation racing `hidden -> active`.

For each pairing, prove that at most one contender commits, the final non-deleted `pending_upload`/`active` count is at most three, and the loser receives the existing `400` capacity response. Also prove that the losing operation writes no success audit or prohibited image/status state and that a losing initiation never calls the upload-ticket or read-URL signer. A non-racing `hidden -> active` at capacity must receive the same rejection, while reactivation below capacity remains allowed.

### 5.6 Provider and metadata failures

Cover the complete affected R2 operation/result family from Section 3.6, asserting both public behavior and exact observability tokens:

- `r2.upload.validate`: configuration failure, plus successful and client-invalid validation paths that must not invent a `succeeded`/provider-failure result;
- `r2.upload_url.create`: `succeeded`, `configuration_error`, `failed`, `rate_limited`, `timed_out`, and malformed output;
- `r2.metadata.head`: `succeeded`, `not_found`, `configuration_error`, distinct `timed_out`, `rate_limited`, `failed`, and malformed response;
- completion metadata checks: size mismatch, content type present and mismatched, and content type absent under the existing accepted behavior;
- `r2.read_url.create`: success and configuration/provider failures for each mutation-producing caller—initiation, completion, and PATCH;
- successful metadata lookup followed by a local expiry/state change before final locking;
- cancellation before commit without a synthesized provider result or durable mutation.

Metadata timeout tests must prove that `DependencyReadTimeoutError` retains its `503`/`retry_later` public contract and `timed_out` metric classification rather than becoming the generic `502`, and that timeout and not-found do not produce a duplicate generic storage-failure event. Each rejected completion case must prove that the row remains unconsumed and that no completion success audit or prohibited primary-image mutation occurs.

For read-URL failure after staged local mutation, prove separately that initiation leaves no new row/create audit, completion remains pending with no completion/primary/audit effects, and PATCH leaves the prior image/primary state and audit history unchanged. Successful mutation responses must prove that read signing occurred before commit and that response construction performs no second post-commit signing call.

### 5.7 API and frontend compatibility

Backend API tests must prove that the initiation response retains the existing `image`, `upload_url`, `upload_headers`, and `expires_at` fields and that completion still returns the ordinary admin venue-image representation.

No new frontend logic or component-test framework is required because the browser request/response contract and direct `PUT` algorithm do not change. Any existing runnable frontend/browser regression that exercises the official-game photo upload flow must continue to pass; WS06-01 must not require a new client-side transport abstraction.

## 6. Done When

This checklist defines the engineering completion bar for WS06-01.

- [ ] Only the existing active-admin path can create a venue-image upload intent, and invalid venue/actor requests cannot reach R2 signing or persist intent state.
- [ ] Each new upload intent has a server-generated image/object identity, immutable actor/venue/object binding, and the exact signer-issued expiry persisted without storing the presigned URL.
- [ ] PostgreSQL enforces that every `pending_upload` row is expiry-bound and unconsumed, with the SQLAlchemy model and canonical `venue_images` migration in sync.
- [ ] Completion rejects expired, consumed, or non-pending intents and performs one final locked revalidation before committing state.
- [ ] Concurrent completion attempts can produce only one successful state transition, completion audit, and set of primary-image effects.
- [ ] The general update endpoint cannot manufacture a new pending intent or activate/hide an uncompleted pending upload, while existing legitimate active/hidden/removal behavior remains intact.
- [ ] Initiation and `hidden -> active` use the same per-venue capacity lock and recount under that lock, so every producer race preserves at most three non-deleted pending/active images and the loser has no success side effects.
- [ ] Repeated initiation remains explicitly non-idempotent and bounded by the serialized selected-photo contract; no duplicate-detection or generic upload-intent subsystem is added.
- [ ] The full `r2.upload.validate`, `r2.upload_url.create`, `r2.metadata.head`, and `r2.read_url.create` operation/result family preserves its exact metrics, safe error classes, timeout distinction, and no-secret observability behavior.
- [ ] Initiation, completion, and PATCH obtain any required response read URL before commit, and read-signing failure rolls back their entire local mutation/audit unit rather than returning an error after durable success.
- [ ] Existing R2 signing configuration, response shapes, and browser direct-upload flow remain compatible.
- [ ] Focused API/service/PostgreSQL/concurrency/migration tests prove the complete lifecycle, failure, replay, capacity-race, provider-result, rollback, and compatibility behavior described in this plan.
