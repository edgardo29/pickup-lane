# WS06-02 - Image validation and sanitization

This pass turns each administrator-uploaded venue image into a bounded,
server-validated, metadata-free image stored under a publication-only object
key before the image can become active or appear in an application response.

This document is the engineering blueprint for this pass.

## 1. What This Work Does

Venue images currently use a direct browser-to-R2 upload. The backend creates a
pending upload intent, gives the active administrator a presigned `PUT` URL,
and later checks the object's declared size and provider content type before it
marks the row active. The backend does not read or decode the uploaded bytes,
and the same object key becomes readable after activation.

This work separates the browser-writable staging object from the object used by
application readers. Completion downloads a bounded object, identifies and
fully decodes its actual image content, enforces resource limits, applies image
orientation, discards supplied metadata, re-encodes the pixels with controlled
settings, writes the result to a server-only immutable publication candidate,
and atomically selects that candidate when it activates the database row. It
then makes a best-effort deletion of the private staging object. Every public,
game, and administrative read of a completed image uses only the publication
key committed by the winning completion.

The existing active-admin authorization, server-owned upload intent, upload
expiry, three-selected-image limit, completion replay protection, image roles,
primary-image behavior, and browser `upload -> complete` sequence remain in
force.

This pass does not create display derivatives, resize valid images, introduce a
background job, or add a storage-management interface. General abandoned-upload
cleanup, orphan and missing-object reconciliation, final R2 access/CORS proof,
and final cache/removal policy are outside this work.

## 2. What Must Be True

These requirements define the safety boundary for turning untrusted staged
bytes into a venue image that the application may publish.

### 2.1 Staging and publication are separate capabilities

- A browser upload URL may write only a server-generated staging key.
- Each completion attempt must use a different, server-generated publication
  candidate key. The key committed by the winning completion becomes the
  image's immutable publication key.
- The browser must never receive a write capability for a publication key.
- Pending rows must not expose a read URL for their staging object.
- Public venue-image lists, game summaries, game details, and administrative
  previews must never sign or return a staging key as a display URL.
- Reusing an unexpired staging upload URL after completion must not be able to
  replace or change the published image.
- A losing, stale, timed-out, or retried completion must not be able to replace
  or delete the publication object selected by the database winner.

### 2.2 Actual bytes and resource use are bounded

- The declared upload size and every downloaded byte count must each be greater
  than zero and must not exceed the configured byte limit. A staging download
  must also equal the declared size persisted on the upload intent. The
  configured byte limit may be narrowed but must never exceed the application
  hard ceiling of 8 MiB.
- A missing, non-integer, boolean, negative, or otherwise unusable provider
  `ContentLength` is malformed provider response metadata, not an upload-size
  mismatch. A well-formed nonnegative length outside the byte policy, unequal
  to bytes consumed, or unequal to the persisted declared size is an upload
  mismatch. A short, overlong, or unbounded body must be rejected.
- Only single-frame JPEG, PNG, and WebP images are supported. Before invoking a
  decoder, the processor must classify the bounded source by the canonical
  JPEG, PNG, or WebP signature rules in Section 3.5. A source with no approved
  signature is `unsupported_content`; this includes a valid image in any other
  format and bytes whose format is not recognizable. An approved signature
  different from the normalized content type persisted on the upload intent is
  `type_mismatch`. A source with the matching approved signature that otherwise
  fails restricted open, verification, or full decode is `corrupt_image`.
  Recognizing a signature is only rejection classification and never proves an
  image valid for publication.
- The request filename and extension have no format authority. A misleading
  filename does not reject otherwise valid bytes when the persisted declaration
  and actual approved format agree, and it cannot make unsupported, mismatched,
  or corrupt bytes acceptable.
- Provider content type, when present, must agree with the upload intent. A
  missing provider content type may not substitute for byte validation and
  does not by itself reject an otherwise valid decoded image.
- R2 response classification must use a coherent HTTP status and error code,
  not an error-code string alone. A contradictory, absent, or unusable status
  cannot establish that staging was absent or that a publication/deletion
  mutation definitely had no effect. Malformed download body types are provider
  failures, not client upload mismatches. For an invoked mutation, every `5xx`
  response remains outcome-unknown even when its error code suggests throttling
  or a missing object.
- Width and height must each be between 1 and 8,192 pixels, and total pixels
  must not exceed 20,000,000. The pixel ceiling also bounds normalized decoded
  pixel storage to at most 80,000,000 bytes for an RGBA image before encoder
  and library overhead.
- Animated or multi-frame files, truncated files, corrupt files, source modes
  that decode successfully but cannot be normalized safely, and decoder
  decompression-bomb warnings or errors must be rejected. A successfully
  decoded mode that cannot be normalized uses `unsupported_content`; a decoder
  or verification failure for a matching approved format uses `corrupt_image`,
  except that decompression-bomb and dimension/pixel-limit failures use
  `resource_limit`. For a matching signature, inspect bounded dimensions before
  verification/full first-frame decode, then classify a successfully verified
  and decoded first frame that declares animation or additional frames as
  `multi_frame` without decoding rejected later frames. A resource-bound failure
  therefore takes precedence over both corruption and frame-count rejection;
  verification or first-frame decode failure precedes `multi_frame`.
- Re-encoded output must also be non-empty and no larger than the configured
  byte limit.
- At most one venue image may occupy the decode/re-encode section in each API
  process. Excess concurrent completion requests must be rejected before an R2
  object download or image allocation begins; they must not queue without a
  bound.

### 2.3 Sanitized output contains controlled pixels and metadata

- Every publishable single-frame source must verify and fully decode; recognizing
  a header alone is insufficient. A source identified as multi-frame after
  container verification and complete first-frame decode is rejected without
  decoding additional frames, which cannot make it eligible for publication.
- EXIF orientation must be applied to the pixel matrix before metadata is
  discarded so the visible orientation remains correct.
- The processor must create a fresh RGB or RGBA pixel image and must not carry
  source `info`, EXIF, XMP, ICC profiles, comments, PNG text chunks, or other
  caller-supplied metadata into the output.
- Output must be encoded as the same approved format detected from the source,
  using explicit deterministic encoder options. The output must itself reopen,
  verify, fully decode, satisfy the same dimension and pixel bounds, and contain
  none of the prohibited metadata before it can be stored for publication.
- Encoder-generated structural data required by JPEG, PNG, or WebP remains
  allowed; arbitrary metadata supplied by the uploader does not.

### 2.4 Database state distinguishes uploaded and published objects

- The original staging key and its declared/uploaded metadata remain the
  immutable upload-intent binding established at initiation.
- An active or hidden image must have a non-empty publication key, publication
  content type, positive publication byte count, publication ETag, and upload
  completion timestamp.
- A pending image must not have publication metadata and must remain excluded
  from every public image query.
- Publication keys must be unique and must not collide with staging keys or
  with another venue image's publication key. Publication must atomically
  refuse to overwrite an existing object at a candidate key; a generated UUID
  and a database uniqueness constraint alone are not collision protection.
- Removed rows may retain publication metadata as history, but removal must
  continue to exclude them from public and ordinary administrative lists.

### 2.5 Completion remains fail-closed and replay-safe

- No validation, decoding, encoding, provider, cleanup, locking, audit, read-URL
  signing, or database failure may leave an unsafe image active.
- Completion may activate the row only after a sanitized publication candidate
  has been written successfully. Staging remains private, and one deletion
  attempt occurs after the activation commit establishes that the raw bytes are
  no longer needed; cleanup failure cannot expose staging or invalidate the
  committed sanitized result.
- A provider mutation with an unknown outcome must leave the row pending. A
  deliberate later completion retry must use a new candidate key and must be
  safe whether the prior candidate write happened or did not happen.
- Once `commit()` has been invoked, failure of subsequent session invalidation
  or closure cannot downgrade commit uncertainty, authorize object cleanup,
  mask the original interruption, or cause reuse of the affected request's
  session. The original unknown-commit result and object-preservation rule
  remain authoritative even if recovery bookkeeping also fails.
- Concurrent completion requests may do redundant bounded work in different API
  processes, but at most one may commit the active transition and completion
  audit. A loser may clean up only a candidate whose successful conditional
  creation by that request was confirmed; a collided or uncertain key is never
  eligible for request-time deletion.
- Completion must recheck the pending, unconsumed, unexpired intent under the
  existing row lock immediately before local activation. A concurrent change
  that makes the row non-completable is rejected; metadata changes that leave
  the row pending are deliberately adopted from the freshly locked row rather
  than compared with an earlier snapshot.

### 2.6 Existing security and response boundaries remain intact

- Only the existing active-admin routes may initiate, complete, or manage a
  venue image.
- Object keys, raw bytes, extracted metadata, presigned URLs, signatures,
  credentials, and provider-private responses must not enter audit metadata,
  public errors, or ordinary logs.
- The optional ETag sent by the browser remains accepted for request
  compatibility but is not trusted as validation evidence and must not override
  the ETag returned by the server-side R2 operation.
- The successful completion response remains compatible with the current
  frontend and contains a read URL for the sanitized publication object.

### 2.7 Persisted storage identity controls every object operation

- The canonical storage target for a venue-image row is the immutable tuple
  `(storage_provider="r2", storage_account_id, storage_bucket)` persisted when
  WS06-01 creates the upload intent. Configuration changes must never
  reinterpret an existing row as belonging to a different account or bucket.
- Completion download, publication, request-time deletion, read-URL signing,
  and every public, game, and administrative image reader must supply that
  persisted target to the R2 adapter. The adapter must validate the configured
  account, bucket, and endpoint/target relationship before creating a client or
  issuing an operation.
- A provider, account, bucket, or endpoint/target mismatch is a fail-closed
  configuration error. It must perform no provider call, issue no capability,
  mutate no row, write no success audit, and never fall back to the currently
  configured target.

### 2.8 Public failures have exact outcomes

- Every newly introduced validation, admission, readiness, storage-target,
  download, publication, and cleanup condition must use the exact exception,
  HTTP status, stable public code, public outcome token, transaction effect,
  storage effect, audit/event behavior, retry/reconciliation rule, and bounded
  metric result defined in Sections 3.3, 3.6, and 3.10, including their
  explicit status/error-code precedence and ambiguous-response outcomes.
- The current normalized public error envelope remains authoritative. A new
  venue-image error must provide its stable code, message, and outcome through
  the implementation contract in Section 3.10 rather than relying on a bare
  status code to synthesize an outcome.
- The accepted download-timeout behavior remains
  `DependencyReadTimeoutError` with HTTP `503`, code
  `API.DEPENDENCY_READ_TIMEOUT`, and outcome `retry_later`. It must not be
  collapsed into a generic provider `502` or generic `503`.

### 2.9 Upload initiation enforces processor readiness

- The upload-initiation service must call the same canonical processor
  readiness validator used by the administrative readiness endpoint after
  authorization and request-shape/content-policy validation, but before
  signing, durable intent persistence, or success auditing.
- Missing Pillow support for any configured approved format fails closed with
  the exact processor-not-ready response in Section 3.10. Frontend sequencing
  and a prior readiness request are advisory only and cannot replace this
  server-side initiation check.
- Readiness rejection creates no upload capability, venue-image row, storage
  mutation, or successful administrative audit.

## 3. Design

The design keeps image processing request-local and synchronous, but admits only
one processing request per API process and moves ordinary multi-image browser
uploads through completion sequentially. It adds no durable worker or processing
state. Every admitted completion writes an immutable, attempt-specific
publication candidate; the database winner selects one candidate, so neither a
still-valid browser upload capability nor a losing completion can overwrite
bytes used by application readers.

### 3.1 Fixed image policy and processing dependency

Use Pillow `12.3.0` as the pinned decoder and encoder dependency.
Upload-readiness validation must confirm that the installed build can decode
and encode JPEG, PNG, and WebP; a missing codec is a configuration/readiness
failure rather than a per-image client rejection.

One side-effect-free `validate_image_processor_readiness()` function owns that
codec check. The existing administrative readiness service calls it in addition
to its R2-configuration and database-schema checks. The upload-initiation
service calls the same function after `require_active_admin`, venue/request
validation, and declared type/size policy validation, but before it acquires the
venue capacity lock, creates an R2 client, signs the staging upload `PUT`,
constructs a `VenueImage`, or records the create audit. Successful initiation
never invokes the read signer: the nested pending response is constructed with
`image_url: null`, so no staging `GET` capability is created. The check uses the
configured allowed format subset; it does not require a codec that configuration
has deliberately disabled. Its result may be cached only for the immutable
installed Pillow build plus normalized allowed-format set, never from a prior
HTTP readiness response.

Completion calls that same validator after admission and before target/client
resolution or staging download. This second check covers an installed-build or
allowed-format change after an intent was created; it does not replace the
required initiation check.

The application's approved format set is exactly:

| MIME type | Pillow format | Object extension |
|---|---|---|
| `image/jpeg` | `JPEG` | `jpg` |
| `image/png` | `PNG` | `png` |
| `image/webp` | `WEBP` | `webp` |

`R2_ALLOWED_IMAGE_TYPES` may select a non-empty subset of that set. Settings
loading must reject any other MIME type instead of allowing an arbitrary
`image/*` value. `R2_MAX_IMAGE_BYTES` remains the per-image configured byte
limit, defaults to 8 MiB, and must be in the inclusive range from 1 byte through
8 MiB.

Upload initiation rejects a declaration outside the configured subset before it
creates an intent or signs a capability. Completion normally receives that same
persisted approved declaration. If configuration is narrowed after initiation
so the persisted declaration is no longer enabled, completion rejects the
staged content as `unsupported_content` before format probing or decoding; it
does not relabel deployment policy drift as decoder unavailability or a corrupt
image. A later upload must use a currently enabled declared type.

The 8,192-per-axis and 20,000,000-total-pixel ceilings are application safety
constants. They are not provider capacity values and cannot be expanded by an
environment variable. Processing keeps the original dimensions after EXIF
orientation; an image outside the bounds is rejected rather than resized.

### 3.2 Object namespaces and persistent publication state

New upload intents use a deterministic staging key derived from server-owned
venue and image IDs. Each admitted completion generates a fresh UUID and uses it
to create an attempt-specific publication candidate key:

```text
venues/{venue_id}/staging/{venue_image_id}.{ext}
venues/{venue_id}/published/{venue_image_id}/{publication_attempt_id}.{ext}
```

The existing `storage_object_key` continues to store the staging key and stays
immutable after initiation. The venue-image row gains nullable publication
fields for the publication object key, content type, size, and ETag. The
publication attempt ID and key are generated only by the backend and are never
accepted from a request. A successful completion persists the exact candidate
key it wrote; that key is immutable afterward. A retry uses a new attempt ID
rather than overwriting an earlier candidate whose provider outcome or database
ownership is uncertain. A publication write is an atomic conditional create
(`If-None-Match: *`) on the exact candidate key, never ordinary overwriting
`PutObject`. A confirmed `412 PreconditionFailed` means the proposed key already
exists: the request did not create or acquire that key, must not sign or delete
it, and fails without automatically regenerating/retrying in the same request.
A concurrent conditional-write `409` or any ambiguous result leaves key
ownership uncertain and likewise forbids request-time deletion. No database
uniqueness check performed after the `PUT` substitutes for conditional creation.
A deliberate later completion generates a new attempt ID and key.

The row's immutable `storage_provider`, `storage_account_id`, and
`storage_bucket` remain the canonical target identity for both its staging and
publication objects. No endpoint value is persisted: for Cloudflare R2 the
endpoint is transport configuration that must be validated against the
persisted account identity on every operation. Introduce a value object carrying
the normalized provider/account/bucket tuple, and require all venue-image R2
adapter entry points to receive it. The adapter resolves credentials and the
configured endpoint, then requires:

- provider exactly `r2`;
- configured account ID exactly equal to the persisted account ID;
- configured bucket exactly equal to the persisted bucket; and
- the normalized endpoint authority to identify the configured/persisted R2
  account, with no alternate host, path, query, fragment, embedded credentials,
  or caller-supplied endpoint.

Any mismatch raises `R2StorageTargetMismatchError` before client construction.
Changing deployment configuration may make an existing row temporarily
unavailable, but it may never redirect that row to a new account, bucket, or
endpoint. Moving an object between targets requires a separately authorized
lifecycle/migration operation; ordinary completion, reading, signing, and
cleanup never perform that move.

Initiation has no pre-existing row, so it resolves and validates one target
value after processor readiness succeeds, passes that same value to staging
upload signing, and persists its account/bucket members on the new row. It must
not resolve configuration independently for signing and persistence. Initiation
does not call read signing at all; the pending response is built directly with
`image_url: null`. Once flushed, all retry, completion, read, and cleanup paths
use the persisted tuple rather than selecting a target again.

The table enforces one complete publication-state invariant. Publication key,
content type, size, and ETag are either all absent or all present, and
`upload_completed_at` is present if and only if that complete publication tuple
is present. The four statuses then have these allowed forms:

| Row form | Publication tuple | `upload_completed_at` | Visibility and response behavior |
|---|---|---|---|
| `pending_upload` | absent | null | Excluded from public reads. Upload-ticket/admin responses keep staging metadata but return `image_url: null`; no staging read signing occurs. |
| `active` | present | present | Eligible for public/admin reads; response storage fields and signed URL use only the committed publication object. |
| `hidden` | present | present | Excluded from public reads; administrative responses use only the committed publication object. |
| `removed` before publication | absent | null | Excluded from public and ordinary administrative lists. A direct removal response, when returned by the existing PATCH flow, may retain staging metadata but must return `image_url: null` and must not sign staging. |
| `removed` after publication | present | present | Excluded from public and ordinary administrative lists. A direct removal response, when returned by the existing PATCH flow, uses the retained publication metadata and may sign only the committed publication key. |

Publication content type is one of JPEG, PNG, or WebP; published size is between
1 byte and 8 MiB; publication key and ETag are non-blank; and publication keys
are unique when present. No status may contain a partial publication tuple or a
publication/completion-timestamp mismatch.

The model and the canonical `venue_images` migration must contain matching
columns, constraints, and indexes implementing this complete matrix. The
repository's clean-rebuild policy applies; no patch migration or historical-data
backfill is introduced.

API responses retain their current field names. Storage fields describe staging
only for unpublished forms and publication only for published forms. No response
ever signs a staging key, and no new provider fields are exposed to the public
response.

### 3.3 Bounded byte retrieval

The R2 adapter replaces the metadata-only `HEAD` operation with a bounded object
download that returns one value containing the body bytes and the matching
content length, content type, and ETag from that `GET` response. It accepts the
persisted target identity and declared byte count from the staging intent.
Completion does not perform a separate `HEAD` followed by `GET`, because the
object could change between those calls.

The adapter must:

1. validate the persisted target against configuration as defined in Section
   3.2, then request exactly that bucket and the persisted staging key;
2. require a normal full-object `GetObject` return to have validated HTTP
   `200` response status; missing, non-integer (including boolean), or other
   success status is a malformed provider response, not successful download;
   treat a missing, non-integer (including boolean), negative, or otherwise
   unusable `ContentLength`, malformed response structure, a non-streaming body,
   or non-byte body chunks as the same provider failure before comparing sizes;
3. reject a well-formed `ContentLength` outside `1..max_bytes` as an upload
   mismatch before reading; a present provider content type is separately
   checked against the persisted declaration;
4. read at most `max_bytes + 1` bytes from the streaming body;
5. reject bodies whose actual length differs from the provider length and,
   when an expected staging size was supplied, from that expected size;
6. close the streaming body on success, rejection, cancellation, and error;
7. return only normalized metadata and bytes, never the raw SDK response; and
8. use the object-operation R2 connection and socket-read timeouts defined in
   Section 3.6.

Malformed provider metadata produces `r2.object.download/failed`, the shared
`storage.operation_failed` diagnostic, and the `502` provider-read contract;
close any obtained body and preserve staging without cleanup so a subsequent
read may recover. A well-formed length outside policy or inconsistent with
consumed/declared bytes, or a present string provider content type inconsistent
with the persisted declaration, produces `r2.object.download/failed` and one safe
`venue_image.validation_rejected` event with canonical `resource_kind`
`venue_image` and `result` `metadata_mismatch`, but
not a storage-provider failure event; make one staging-delete attempt and require
a corrected upload before deliberate retry. The adapter records one result for
the failed read, never `succeeded` before provider metadata and body validation
complete.
Download error classification uses this ordered rule, independently of upload
metadata checks:

1. Target/configuration validation that prevents `GetObject` is
   `configuration_error`; an actual connection/socket read timeout is
   `timed_out` because `GetObject` is a safe read.
2. An SDK `ClientError` must have a usable non-boolean integer HTTP error
   status in `400..599`. A status that is missing, malformed, or inconsistent
   with a special-purpose error code is `failed`, never `not_found` or
   `rate_limited` by code alone.
3. `not_found` requires HTTP `404` with an absent error code or a recognized
   missing-object code (`404`, `NoSuchKey`, or `NotFound`). HTTP `404` paired
   with an unrelated error code is `failed`; HTTP `503` paired with
   `NoSuchKey` is also `failed`, not proof of a missing staging object.
4. HTTP `429` with absent or recognized throttling code, or HTTP `503` with
   an explicit recognized throttling code, is `rate_limited`. HTTP `429` with
   an incompatible missing-object or other non-throttling code is `failed`,
   not `not_found` or `rate_limited`. Other provider
   rejections and non-timeout transport errors are `failed`. Neither
   `rate_limited` nor `failed` deletes staging or claims an upload mismatch.

The adapter records one result per invoked download and closes any acquired
body on all paths. A normal `GetObject` return missing its HTTP `200` success
status, or a structured error missing its valid error status, is a provider
failure even if any error code says `NoSuchKey` or `SlowDown`; a non-byte
streaming body has the
same provider-failure behavior as malformed response metadata. No application
retry occurs inside the adapter, and a missing staging object is not recovered
from an uncommitted publication candidate.

### 3.4 Processing admission and isolation

Image processing remains in the API process rather than introducing a durable
job. Its resource boundary is explicit:

- one process-local `BoundedSemaphore` with capacity one guards the entire
  staging-download, decode, encode, candidate-write, database-finalization, and
  request-time cleanup sequence;
- acquisition is non-blocking; a request that cannot acquire the slot raises
  `ImageProcessingBusyError` and returns the exact
  `503`/`STORAGE.IMAGE_PROCESSOR_BUSY`/`retry_later` response from Section 3.10
  before R2 or Pillow work, records the bounded local rejection event but no
  provider result, and performs no database mutation;
- the slot is released in `finally` after every success, rejection, conflict,
  cancellation, or exception;
- byte, axis, pixel, frame, and output limits remain the in-process memory and
  work bounds for the one admitted image; and
- the browser submits its maximum three selected venue images sequentially so
  the supported product flow does not create avoidable admission failures.

This is request-process isolation, not a claim of a separate sandbox or a
deployment-wide concurrency value. Multiple API processes may each admit one
image, and final process/instance topology and capacity proof remain outside the
source contract. Decoder exceptions are contained as request failures; a native
library process crash remains an API-process failure rather than recoverable
request state. The pinned processor dependency, strict format allowlist, byte
and pixel bounds, and single-slot admission are the selected source safeguards.

The semaphore is not a retry queue, distributed lock, or correctness lock for a
particular image. Cross-process correctness comes from attempt-specific
publication keys and the existing PostgreSQL row lock.

### 3.5 Verification, normalization, and re-encoding

A focused, side-effect-free venue-image processor owns all decoder and encoder
behavior. It accepts bytes, the persisted declared content type, the configured
byte limit, and the fixed dimension/pixel policy, and returns sanitized bytes
plus their content type and dimensions.

Processing follows this order:

1. Reject an empty or over-limit buffer as `resource_limit`.
2. Normalize the persisted declared MIME type. If it is not in the currently
   configured approved subset, reject `unsupported_content` without probing or
   decoding the source.
3. Classify the bounded source using only these approved signature rules:
   JPEG begins with `FF D8 FF`; PNG begins with its complete eight-byte
   signature; WebP has `RIFF` at bytes `0..3` and `WEBP` at bytes `8..11`.
   These checks do not invoke an unsupported decoder and do not establish
   validity. If none matches, reject `unsupported_content`. Valid GIF, BMP,
   TIFF, ICO, PPM, or any other non-approved image and arbitrary unrecognized
   bytes receive that same result because neither may enter an unsupported
   decoder path.
4. If the approved signature identifies a different MIME type from the
   persisted declaration, reject `type_mismatch` without decoding. This rule
   also applies when the differently signed approved format is not enabled in
   the current configured subset: declaration mismatch is already definite and
   takes precedence.
5. Open the buffer while restricting Pillow to the one signature-selected,
   declaration-matching JPEG, PNG, or WebP decoder. Treat
   `DecompressionBombWarning` and `DecompressionBombError` as
   `resource_limit`. If Pillow otherwise cannot open the source, if it reports
   a format inconsistent with the preliminary signature and declaration, or if
   verification/full decode later fails with an `UnidentifiedImageError`,
   syntax error, truncation, or decoder error, reject `corrupt_image`.
6. Check positive dimensions, both axis ceilings, and the total-pixel ceiling
   before pixel decoding. Reject a bound violation as `resource_limit` before
   classifying animation or frame count.
7. Run container/format verification, reopen under the same restricted decoder,
   repeat the reported-format and dimension/pixel checks, and force a complete
   first-frame pixel load with truncated-image support disabled. An ordinary
   verification or first-frame decode failure is `corrupt_image`; a
   decompression-bomb or dimension/pixel failure remains `resource_limit`.
8. Only after the bounded first frame has verified and fully decoded, inspect
   `n_frames` and the animation flag. Reject any `n_frames != 1` or animated
   source as `multi_frame`. Do not decode additional frames of a rejected
   multi-frame image: their validity cannot make it publishable. An ordinary
   first-frame failure takes precedence over frame-count rejection; a malformed
   later frame does not supersede an already established `multi_frame` result.
9. Apply EXIF orientation and repeat the dimension and pixel checks.
10. Normalize JPEG to RGB. Normalize PNG and WebP to RGBA when transparency is
   present and RGB otherwise. A fully decoded source mode that the selected
   normalization cannot convert safely is `unsupported_content`, not corrupt
   data.
11. Construct a fresh pixel-only image so source metadata dictionaries and
    profiles are not inherited.
12. Encode into a new buffer without supplying source metadata.
13. Enforce the output byte limit, reopen the output under the same restricted
    format set, fully decode it, and prove its format, frame count, dimensions,
    and metadata are acceptable. Empty or over-limit encoded output is
    `encoded_size_limit`; an encoder exception or output reopen, format,
    verification, full-decode, or prohibited-metadata failure is
    `corrupt_image`; an output dimension/pixel or decompression-bomb failure is
    `resource_limit`.

The resulting input-classification matrix is complete and ordered. The first
matching row owns the result:

| Persisted declaration and current policy | Approved source signature | Restricted decoder result | Required result |
|---|---|---|---|
| Any | Source buffer is empty or exceeds the configured byte limit | Signature and decoder are not invoked | `resource_limit` |
| Declaration is outside the currently configured approved subset | Any | Decoder is not invoked | `unsupported_content` |
| Declaration is currently allowed | None of JPEG, PNG, or WebP | Decoder is not invoked | `unsupported_content`; valid non-approved images and unrecognized bytes intentionally share this result |
| Declaration is currently allowed | A different approved format | Decoder is not invoked | `type_mismatch` |
| Declaration is currently allowed | Matching approved format | Open or first-frame decode reaches a decompression-bomb warning/error, or source/reopened dimensions/pixels violate their bounds before first-frame decode; post-orientation bounds also apply to otherwise eligible single-frame content | `resource_limit` |
| Declaration is currently allowed | Matching approved format | Open, reported format, container verification, or complete first-frame decode is otherwise inconsistent or fails | `corrupt_image` |
| Declaration is currently allowed | Matching approved format | Container verification and bounded first-frame decode succeed, but the image declares animation or multiple frames; later frames are not decoded | `multi_frame` |
| Declaration is currently allowed | Matching approved format | Verified, fully decoded single-frame source mode cannot be normalized safely | `unsupported_content` |
| Declaration is currently allowed | Matching approved format | Single-frame decode, bounds, normalization, re-encoding, and output verification all succeed | Continue with sanitized output in the same approved format |

After the source reaches the final row, output processing has the same explicit
classification: empty or over-limit encoded bytes are `encoded_size_limit`;
encoder or output reopen/format/verification/full-decode/prohibited-metadata
failure is `corrupt_image`; and an output dimension/pixel or
decompression-bomb failure is `resource_limit`. None of these output failures
creates a publication candidate.

Provider `ContentType` remains an earlier, separate staging-metadata check: a
present value that disagrees with the persisted declaration is
`metadata_mismatch`, while an absent value does not alter this byte-classification
matrix. Filename and extension never select a row. Every rejected processor row
leaves the database intent pending, creates no publication candidate or success
audit, attempts staging cleanup once, and emits
`venue_image.validation_rejected` with `resource_kind=venue_image` and the exact
result token. The preceding bounded download remains a successful provider read;
the processor rejection does not emit `storage.operation_failed` or rewrite its
provider metric. A corrected overwrite may be completed only while the original
intent remains live; otherwise the administrator must create a new intent.

The explicit encoder settings are:

| Format | Output mode | Encoder settings |
|---|---|---|
| JPEG | RGB | quality 85, 4:2:0 subsampling, non-progressive, no optimization |
| PNG | RGB or RGBA | compression level 6, no optimization, no palette conversion |
| WebP | RGB or RGBA | quality 85, method 4, single frame |

The encoder must supply empty EXIF where the format accepts it, omit `pnginfo`,
XMP, comments, and animation parameters, and omit or explicitly clear ICC
profiles. It must not copy arbitrary `Image.info` entries. The fixed Pillow
version and explicit options make retries over the same pixels deterministic
and prevent library defaults from silently changing the publication contract.

### 3.6 R2 publication, cleanup, and complete operation contract

The R2 adapter adds server-credential operations for bounded staging download,
publication-candidate creation, and object deletion. Publication makes exactly
one SDK `put_object` call with the complete sanitized buffer, its sanitized
content type, the attempt-specific key, and `IfNoneMatch="*"` (wire header
`If-None-Match: *`); it returns success only for a validated, non-empty ETag.
Use a publication-specific botocore client/configuration with
`retries={"total_max_attempts": 1}` so neither the application nor the SDK
silently resends a mutation under the same key. A `412` is a definite collision:
no publication ownership was acquired, even if an object is now present at that
key. A conditional-write `409` is treated conservatively as unknown, never as
permission to reuse or delete that key. Deletion accepts only an
application-selected staging key or this request's *confirmed successfully
created* uncommitted candidate and treats an already-absent object as success.

Every upload signing, download, publication, deletion, and read signing call
accepts either the initiation target that the same request will persist or an
existing row's persisted target value from Section 3.2, and validates it before
client construction. No operation accepts a client-provided account, bucket,
endpoint, or key. Publication does not set a public ACL, provider-specific
cache policy, or final delivery-topology setting.

Publication and deletion use one ordered mutation-classification rule owned
by the R2 adapter. A provider error code alone never proves rejection or
object absence after an SDK mutation invocation:

1. Target/configuration validation that prevents the SDK mutation method from
   being invoked is `configuration_error`. A proven failure before the SDK
   method is invoked makes no provider-mutation claim.
2. Once the SDK method has been invoked, any structured HTTP `408`,
   conditional-publication `409`, other ambiguous `409`, any HTTP `5xx`, or
   missing/unusable non-boolean integer error status outside `400..599` is
   `unknown_outcome` **before considering an
   error-code string**. For example, `503` + `SlowDown` and `503` + `NoSuchKey`
   are both unknown for publication and deletion; neither authorizes candidate
   cleanup or assumes deletion succeeded. Mutation connect/read timeouts,
   connection loss, and unstructured SDK/transport exceptions without a
   definite non-acceptance response are also `unknown_outcome`.
3. Only a coherent structured `412` + `PreconditionFailed` conditional-publication
   response is a definite `failed` key collision: this request did not create,
   acquire, or own the key. Conflicting/malformed `412` error details are
   `unknown_outcome`, not permission to delete a possibly existing object.
   A coherent HTTP `404` + absent or recognized missing-object code on deletion
   means the eligible object was already absent and is idempotent `succeeded`;
   an inconsistent `404` error code is `unknown_outcome`, not definite absence.
4. A structured HTTP `429` with absent or recognized throttling code, or
   an unambiguous `4xx` other than `404`, `408`, `409`, `412`, or `429` with an
   explicit recognized throttling code, is `rate_limited` only when the
   response establishes non-acceptance. A `429` paired with a contradictory
   missing-object or other non-throttling code, or a `404` with a non-missing
   code, is `unknown_outcome`. An ordinary
   non-throttling `4xx` is `failed` only when its status and code consistently
   establish definite non-acceptance; inconsistent or incomplete evidence is
   `unknown_outcome`.
5. Only a validated normal SDK success is `succeeded`: publication requires its
   validated non-empty ETag, while deletion requires a valid successful SDK
   response. A normal SDK return missing required success data is
   `unknown_outcome`, even if an accompanying status looks successful.

Do not apply this mutation-specific uncertainty to safe `GetObject` or local
URL signing: their operation-specific classification and existing public
contracts remain separate. Never convert a response with contradictory
status/code signals into an assumed successful read or a definite mutation
rejection.

Once the SDK mutation method has been invoked, an exception is never called a
definite pre-dispatch failure merely because the application cannot tell where
dispatch failed. Callers do not reinterpret adapter classifications.
A publication candidate whose outcome is unknown is preserved and never adopted
or reused; a later deliberate completion uses a new key. A collided key is not
owned by the current request, so a definite `412` rejection also forbids
request-time deletion, including in later error/rollback cleanup. Only a
validated successful conditional creation establishes candidate ownership;
local failure afterward may clean that owned candidate if non-commit is proven.
Deletion remains idempotent, but the application does not issue an automatic
second call after an unknown outcome.

The complete R2 operation vocabulary after this work is:

| Operation | Class | Outcomes |
|---|---|---|
| `r2.upload.validate` | local configuration/target validation | `configuration_error` |
| `r2.upload_url.create` | local signing | `succeeded`, `timed_out`, `rate_limited`, `failed`, `configuration_error` |
| `r2.read_url.create` | local signing | `succeeded`, `timed_out`, `rate_limited`, `failed`, `configuration_error` |
| `r2.object.download` | provider read | `succeeded`, `not_found`, `timed_out`, `rate_limited`, `failed`, `configuration_error` |
| `r2.object.publish` | attempt-scoped provider mutation with no application retry | `succeeded`, `unknown_outcome`, `rate_limited`, `failed`, `configuration_error` |
| `r2.object.delete` | idempotent provider mutation | `succeeded`, `unknown_outcome`, `rate_limited`, `failed`, `configuration_error` |
| `r2.readiness.check` | local readiness validation | `configuration_error` |

`r2.metadata.head` and its metadata-only adapter are removed because completion
is their only production caller and the bounded `GET` supersedes it. Tests and
inventories must not retain `HEAD` as a current runtime operation.

The metadata-specific timeout settings are replaced by
`R2_OBJECT_CONNECT_TIMEOUT_SECONDS` and `R2_OBJECT_READ_TIMEOUT_SECONDS`.
They remain positive-integer, portable SDK socket bounds with source defaults of
2 and 6 seconds respectively. The connect timeout applies to download,
publication, and deletion; the read timeout applies to response/body socket
inactivity for those calls. These settings do not claim a whole-request
deadline, final provider capacity, or final production tuning. Signing remains
local work even though it uses the same configured client object.

Download socket timeouts are `timed_out` because the operation is a safe
read. Publication and deletion apply the ordered mutation classification
above: a mutation prevented before SDK invocation has no provider effect;
coherent conditional-publication `412` is definite collision without ownership;
coherent already-absent deletion is idempotent success; `408`/`409`/`5xx`,
missing status, contradictory status/code responses, uncertain transport, and
malformed success data preserve `unknown_outcome`. A throttling code cannot
turn a `5xx` mutation response into definite `rate_limited` rejection. Target
mismatch is `configuration_error` for the operation that was prevented and
produces no SDK call.

Cancellation is classified without swallowing cancellation semantics. Before
mutation dispatch it produces no provider result. After dispatch but before a
validated success it records `unknown_outcome`, preserves the affected object
responsibility exactly as the corresponding unknown-outcome path requires, and
then re-raises the cancellation instead of translating it into an HTTP response.
After validated mutation success, the metric remains `succeeded`; any later
local non-commit cleanup rule applies before cancellation is re-raised when the
request still owns cleanup responsibility.

The application invokes each SDK operation once and adds no application or
background retry. For publication only, SDK retry attempts are explicitly
disabled as stated above: one SDK invocation means at most one conditional PUT
attempt. SDK-owned retries for other operations remain dependency-owned and
must not be represented as application retry counts. The adapter, as the single metric
owner, records exactly one final bounded result for each application invocation
that reaches a classifiable provider operation; callers must not duplicate that
observation, and the adapter never records success before response validation
completes.

The R2 adapter owns credential use; venue-image services own which persisted
target and namespace an operation may address. The backend credential contract
is the minimum operation set required by this workflow, limited to the
configured account and bucket: sign `PutObject` for staging keys, sign
`GetObject` for committed publication keys, call `GetObject` for staging keys,
call `PutObject` for attempt-specific publication keys, and call `DeleteObject`
for staging and the current request's uncommitted candidate. This pass does not
require bucket listing, arbitrary-prefix access, public ACL changes, lifecycle
administration, cross-account access, or browser write access to publication
keys. Source and deterministic local tests enforce target/key selection. A
separately runnable provider-contract suite verifies the required operation
semantics with isolated non-production R2 credentials and a dedicated test
bucket; final production token, bucket, and CORS/access proof remains outside
this pass.

The complete affected inventory family must describe the resulting operations
consistently: provider-result metrics, storage diagnostics, timeout settings and
environment documentation, provider-cost and outbound-operation inventories,
transaction boundaries, retry/unknown-outcome policy, architecture and trust
boundaries, credential-purpose records, and storage limit records. Download is
a bounded storage dependency read; publication is a
`NO_AUTOMATIC_RETRY_MUTATION` whose unknown candidate is never reused by a new
completion; deletion is an `IDEMPOTENT_PROVIDER_MUTATION`. No inventory may keep
the former metadata-only or no-R2-mutation description.

### 3.7 Completion workflow and transaction ordering

Completion preserves the prerequisite rule that database locks are not held
across provider I/O or image decoding. The workflow is:

1. Load the row and reject a missing, removed, non-pending, consumed, or expired
   intent before provider work.
2. Acquire the process-local processing slot without waiting; reject with safe
   retry-later semantics when the slot is occupied.
3. Validate processor readiness with the canonical check, then resolve and
   validate the row's persisted target once for this completion,
   retain that validated execution-target snapshot for every subsequent R2
   operation in the request, then generate a fresh publication attempt UUID and
   derive its candidate key from the persisted venue ID, image ID, declared
   approved type, and attempt UUID. Do not re-resolve ambient target selection
   between download, publication, signing, and cleanup.
4. Download only the persisted staging object with the configured byte and
   timeout bounds.
5. Validate provider metadata when present, then run the complete byte processor.
6. Conditionally create the sanitized candidate using the publication-specific
   no-retry client. On a `412` collision, do not acquire, reuse, sign, or delete
   the collided key; on `409`/unknown, preserve the key and staging without
   retry or cleanup. Continue only after validated conditional-write success.
7. Lock and freshly reload the venue-image row.
8. Capture a fresh UTC time and repeat the pending, unconsumed, unexpired
   validation. If a concurrent PATCH changed only metadata while leaving the row
   pending, deliberately adopt the freshly locked values for `image_role`,
   `is_primary`, `sort_order`, `alt_text`, and `caption`; do not compare them
   with the initial read or reject them as stale. A lifecycle/consumption change
   that makes completion invalid still fails here.
9. Store the candidate key, content type, byte count, and provider ETag;
   transition to `active`; set `upload_completed_at`; and apply the existing
   primary-image behavior from the freshly locked `is_primary` value.
10. Write the existing successful completion audit from the freshly locked
    row, using the existing bounded status/role/primary/order snapshot rather
    than an initial-read snapshot. Fresh `alt_text` and `caption` remain adopted
    on the row and response but stay outside that bounded audit snapshot, matching
    the current audit contract rather than expanding audit payloads in this pass.
11. Flush the local changes and sign the response read URL for the candidate key
    before committing.
12. Invoke `commit()` exactly once for the image, primary-image changes, and
    audit local transaction. A normal return proves commit success and makes the
    selected candidate the immutable publication object.
13. After a confirmed successful commit, make one best-effort idempotent
    deletion of the staging key. Cleanup failure or unknown outcome is recorded
    safely but does not turn the committed sanitized image into a failed
    completion.
14. If a failure occurs before `commit()` is invoked, or affirmative database
    evidence proves non-commit, roll back/reset local state as needed. Make one
    best-effort deletion only if this request received validated success for
    its own conditional candidate creation; never delete a collided or
    unknown-outcome key.
15. Mark `commit()` as invoked before entering its call. Treat every
    interruption before its successful return—including ordinary exceptions,
    Python cancellation, and other `BaseException`—as unknown unless the
    database affirmatively proves non-commit. Establish the unknown-commit
    preservation rule *before* recovery cleanup: preserve staging and the
    confirmed-created candidate, and prohibit any candidate/staging deletion,
    retry, second audit, or claim of rollback. Independently attempt session
    invalidation and closure as best-effort recovery steps; guard each step so
    its own `Exception` or `BaseException` cannot mask the original interruption,
    change the unknown classification, or fall through to a pre-commit cleanup
    handler. Attempt the one bounded
    `venue_image.completion_outcome_unknown` event with canonical
    `resource_kind` `venue_image` and `result` `database_commit_unknown`;
    diagnostic-emission failure likewise cannot authorize deletion or replace
    the original interruption. Never reuse this request's session, and do not
    claim it was successfully invalidated if either recovery step failed.
    For an original ordinary exception, return the exact non-timeout
    unknown-commit response from Section 3.10 even if a recovery step failed;
    for original cancellation or another `BaseException`, re-raise that
    original interruption with no synthesized HTTP response.
16. Release the processing slot in `finally` and return the already-built
    successful response only after a confirmed successful commit.

Pre-commit validation, locked-state, signing, and flush failures are definite
local non-commit paths. Because the explicit flush precedes `commit()`, a
connection or DBAPI exception—or `BaseException` interruption—from the
`commit()` call itself is treated as unknown unless SQLAlchemy/PostgreSQL
provides affirmative evidence that the transaction did not commit. A cleanup
`rollback()`, session invalidation, session close, or failure of any
of those operations is not affirmative evidence of non-commit and never
authorizes candidate deletion. Record whether commit invocation began before
entering the commit call so an interrupt after the server commits but before
Python regains control is not mistaken for a pre-commit cancellation. Once
commit uncertainty has been established, outer request/session cleanup must
not remap it to definite rollback or override the original exception; all
follow-on handling respects the already-selected preserve-both-objects rule.

The completion API has no client idempotency key and this pass does not invent
one. After an unknown commit response, the caller must refetch the venue-image
row. An active/hidden row whose publication metadata matches the attempt proves
success; a still-pending row permits a deliberate new completion with a new
candidate key. A replay never recommits the same attempt: normal locked
single-consumption returns the exact conflict response from Section 3.10 when
the prior commit won. If the prior transaction did not commit, the preserved
candidate is unreachable and remains owned by WS06-03's Pickup-Lane-namespace
orphan reconciliation and idempotent cleanup; it is never discovered or adopted
by request-time completion.

The optional browser ETag remains accepted solely for request compatibility. It
cannot select an object, skip byte validation, override the authoritative ETag
returned by publication, or enter diagnostics.

### 3.8 Partial failure, retry, and concurrency

Each completion attempt generates a new publication key but owns the candidate
only after its `If-None-Match: *` write returns validated success. A forced
UUID/key collision receives `412` without acquiring ownership; a concurrent
conditional-write `409` leaves ownership uncertain. Neither path may delete
that key, regardless of local rollback. Provider success followed by a definite
pre-commit local failure may delete only that request's confirmed-owned
candidate once. Provider success followed by an unknown database
commit outcome preserves the candidate because it may be the object referenced
by a committed active row, including when session invalidation, session closure,
or unknown-commit diagnostic emission also fails. If the database did not commit, that preserved
candidate is an unreachable orphan. A later pending completion reads the
still-private staging object and writes a new candidate; it does not discover,
trust, overwrite, or delete the earlier candidate.

Two completions in different API processes may both read, sanitize, and publish
different candidate keys in the ordinary case. The existing final row lock
and fresh state check allow only one request to commit activation and its audit.
A loser whose own conditional publication succeeded can delete that confirmed
owned candidate after a definite non-commit; a forced collision or uncertain
write instead preserves the key. No loser can alter the winner's object or
persisted metadata.

A concurrent administrative PATCH is a separate case. If it changes lifecycle
state so the row is no longer pending/completable, the final locked validation
rejects completion. If it changes only `image_role`, `is_primary`, `sort_order`,
`alt_text`, or `caption` and leaves the row pending, completion intentionally
uses those freshly locked values. Primary-image effects use the fresh
`is_primary`; the completion audit uses the fresh bounded
status/role/primary/order snapshot, while fresh `alt_text` and `caption` remain
outside that existing audit snapshot. No version column or stale-metadata
rejection mechanism is added by this pass.

The committed publication key is never rewritten by completion. Its stored
content type, byte count, and ETag therefore continue to describe the bytes at
that key even if a losing request finishes later.

The transaction-local successful completion audit has the same commit outcome
as activation. Unknown commit emits no separate failed administrative action:
the original success action either committed atomically with the image or did
not. The `venue_image.completion_outcome_unknown` operational event records
canonical `resource_kind` `venue_image`, `result` `database_commit_unknown`,
and request correlation. The general emitter deliberately excludes
high-cardinality venue-image and publication-attempt identifiers; the event also
omits the object key and storage identity values. The ordinary API request metric records the `503`,
while provider-operation metrics retain only the actual R2 results already
observed.

A commit-time cancellation or other `BaseException` without a confirmed
successful return follows the same unknown-commit preservation rule as a
post-commit connection loss, but propagates the original interruption rather
than synthesizing an HTTP envelope. A secondary failure of session invalidation,
closure, or event emission does not change that rule or permit an outer generic
handler to delete either object. The diagnostic event is attempted once with
the same bounded fields and `result` `database_commit_unknown`; an API request
metric must not claim a `503` when no HTTP response was sent.

An unexpired browser upload URL can recreate a staging object after request-time
cleanup. Because staging and committed publication keys differ, this cannot
change the active image. Completion performs the immediate cleanup it can
control; broader discovery of recreated, abandoned, or orphaned objects remains
outside request-time image processing.

### 3.9 Read paths and API compatibility

Every consumer that signs or carries a venue-image object must use the committed
publication key for a published image and the row's persisted
provider/account/bucket target. Queries and projections that currently carry
only `storage_object_key` must instead carry the persisted target fields and
publication key together. URL helpers accept that explicit value rather than
consulting ambient configuration alone. No caller may fall back to staging or a
different configured target.

The affected reader/signing population and failure behavior is explicit:

| Reader or response surface | Target mismatch or read-signing failure |
|---|---|
| Public venue-image list / `build_public_venue_image_read` | Fail the direct request with the exact `503` target-mismatch or `502` read-signing contract. Return no partial image payload and never substitute staging. |
| Administrative venue-image list / `build_admin_venue_image_read` | Fail the direct request with the same exact contract. Pending rows never invoke signing and expose `image_url: null`. |
| Administrative update/remove response | Build against the freshly updated row before commit. A required publication read-signing failure is a definite pre-commit failure and rolls back the metadata/status mutation. Removed-before-publication returns `image_url: null` without signing; removed-after-publication may sign only its committed publication key. |
| Completion response | Sign only the candidate selected for publication. Target/signing failure before commit is a definite non-commit path: roll back, make one best-effort deletion only of that request's confirmed-created candidate, keep staging pending, and return the exact error. |
| Browse/game-card venue-image fallback in `game_service` | Preserve the existing aggregate fallback: emit `storage.operation_failed`, return the game/card with the venue fallback image URL set to null, and do not fail the game record. |
| Official-game administrative card in `official_game_query_service` | Preserve the existing aggregate fallback: emit `storage.operation_failed`, return the card with `primary_venue_image_url` null, and do not fail the game record. |
| Upload-ticket pending image | Never calls the read signer. It returns `image_url: null`, so target/read-signing failure is not an initiation response path. |

Aggregate-card projections must carry the persisted target plus publication key
needed by their signer while preserving their null-image fallback. Direct
venue-image readers propagate the exact storage error instead of silently
omitting a row. The public response shape remains unchanged and continues to
include active images only.

The upload-ticket response keeps `image`, `upload_url`, `upload_headers`, and
`expires_at`. Its nested pending image keeps the existing identity and metadata
fields but returns `image_url: null`; the browser flow consumes the image ID and
upload capability, not a pending read URL. The administrative/read response
schema therefore makes `image_url` nullable for unpublished pending or removed
forms, while the public active-image response remains non-null. Completion
returns the same successful response shape with a non-null publication URL after
confirmed commit.

The create-game browser flow replaces its concurrent `Promise.all` image
submissions with a sequential loop, preserving one direct `PUT` followed by one
completion per image without adding frontend-managed processing state,
automatic retry, or polling.

### 3.10 Validation rejection and safe diagnostics

Every WS06-02 failure that returns an HTTP response has one exact envelope.
Non-timeout failures use the venue-image HTTPException helper with this normalized
shape:

```text
{
  "detail": {"code": <code>, "message": <message>, "outcome": <outcome>},
  "code": <code>,
  "message": <message>,
  "correlation_id": <request correlation ID>
}
```

Non-timeout errors do not add `details.timeout_class`. Timeout classes retain
their existing `PublicTimeoutError` envelope: scalar `detail`, top-level `code`,
`message`, `correlation_id`, and `details.outcome`/`details.timeout_class`.
Python cancellation is not converted into either envelope; after any required
provider classification/preservation/cleanup bookkeeping it is re-raised.
Gate B must implement the following complete mapping rather than infer a public
token from the status alone:

WS06-01's accepted upload-URL and ordinary read-URL signing failure contracts
remain unchanged except that processor-not-ready and target-mismatch failures
now precede signing where applicable. Those existing signing results must not be
collapsed into, or have their outcomes inferred from, the new rows below.

| Condition | Raised error | HTTP / public code / outcome | Local, storage, audit, recovery, and observation behavior |
|---|---|---|---|
| Persisted declaration is no longer enabled; source has no approved JPEG/PNG/WebP signature; or a successfully decoded source mode cannot be normalized safely | `ImageContentRejectedError` carrying `unsupported_content` | `400` / `STORAGE.IMAGE_INVALID` / `unsupported_content` | Row stays pending; no candidate, primary-image side effect, or success audit; make one staging-delete attempt; emit `venue_image.validation_rejected` with `result=unsupported_content`. The successful bounded download keeps its own provider result and no `storage.operation_failed` event is emitted. Retry requires bytes and a declaration accepted by current policy while the original capability remains live. |
| Approved JPEG/PNG/WebP source signature differs from the persisted currently allowed declaration | `ImageContentRejectedError` carrying `type_mismatch` | `400` / `STORAGE.IMAGE_INVALID` / `type_mismatch` | Row stays pending; do not invoke a decoder, create a candidate, change primary state, or write a success audit; make one staging-delete attempt and emit the bounded validation-rejection event with `result=type_mismatch`. Retry requires a corrected overwrite while the original capability remains live. |
| Source has the matching approved signature but restricted open, format consistency, container verification, or bounded complete first-frame decode otherwise fails (including a declared multi-frame source with an invalid first frame); or encoding/output reopen, format, verification, full decode, or prohibited-metadata validation fails | `ImageContentRejectedError` carrying `corrupt_image` | `400` / `STORAGE.IMAGE_INVALID` / `corrupt_image` | Row stays pending; no candidate, primary-image side effect, or success audit; close owned image resources, make one staging-delete attempt, and emit the bounded validation-rejection event with `result=corrupt_image`. Retry requires a corrected overwrite while the original capability remains live. |
| Matching approved content passes source dimension/pixel bounds, container verification, and complete first-frame decode, then declares animation or multiple frames | `ImageContentRejectedError` carrying `multi_frame` | `400` / `STORAGE.IMAGE_INVALID` / `multi_frame` | Row stays pending; no candidate or success audit; close owned image resources, make one staging-delete attempt, and emit the bounded validation-rejection event with `result=multi_frame`. Retry requires a single-frame overwrite while the original capability remains live. |
| Source buffer is empty/over-limit, or source/output dimension, pixel, or decompression limit is exceeded; recognized multi-frame content with excessive dimensions is classified here before frame-count rejection | `ImageContentRejectedError` carrying `resource_limit` | `400` / `STORAGE.IMAGE_INVALID` / `resource_limit` | Row stays pending; no candidate or success audit; close owned image resources, make one staging-delete attempt, and emit the bounded validation-rejection event with `result=resource_limit`. Do not disclose decoder diagnostics. |
| Sanitized output is empty or exceeds the byte limit | `ImageContentRejectedError` carrying `encoded_size_limit` | `400` / `STORAGE.IMAGE_INVALID` / `encoded_size_limit` | Row stays pending; no publication write or success audit; close owned image resources, make one staging-delete attempt, and emit the bounded validation-rejection event with `result=encoded_size_limit`. Retry requires a corrected overwrite while the original capability remains live. |
| Well-formed provider `ContentLength` outside `1..max_bytes` or different from consumed bytes or the persisted declared length; or a present string `ContentType` differs from the persisted declaration | `ImageUploadMismatchError` | `400` / `STORAGE.UPLOAD_MISMATCH` / `metadata_mismatch` | Close body; row stays pending; no publication/audit; record `r2.object.download/failed` and one `venue_image.validation_rejected` event with `resource_kind=venue_image` and `result=metadata_mismatch`, not `storage.operation_failed`; make one staging-delete attempt; corrected overwrite may retry while live. An absent `ContentType` proceeds to byte classification. |
| Staging object definitively absent: structured HTTP `404` with absent or recognized missing-object code | `R2ObjectNotFoundError` translated by the venue-image service | `400` / `STORAGE.OBJECT_NOT_FOUND` / `not_found` | Row/staging intent stays pending; no publication, cleanup, or success audit; deliberate retry only after an object is uploaded. Provider metric `r2.object.download/not_found`. A missing/unusable HTTP status, `503` + `NoSuchKey`, or contradictory `404` code is a provider failure instead, not proof of absence. |
| Download connect/read timeout | existing `DependencyReadTimeoutError` | `503` / `API.DEPENDENCY_READ_TIMEOUT` / `retry_later` | Close body, roll back/reset the read transaction, keep pending/staging, no cleanup or audit; deliberate completion retry is allowed while live. Provider metric `timed_out`; no duplicate generic storage-failure event. |
| Download coherent HTTP `429`, or HTTP `503` with an explicit recognized throttling code, without contradictory missing-object metadata | `R2StorageError` translated with the named result | `502` / `STORAGE.OBJECT_READ_FAILED` / `rate_limited` | Same no-mutation behavior; deliberate retry while live; provider metric `rate_limited` and one safe storage-failure event. A missing status or contradictory missing-object code is `failed` instead. |
| Download rejection, transport failure other than timeout, contradictory HTTP status/error code (`503` + `NoSuchKey`, `404` + unrelated code), missing/unusable HTTP status, or malformed provider response, including missing/invalid normal-download HTTP `200` status, invalid `ContentLength`, non-string `ContentType`, or non-byte streaming body/chunks | `R2StorageError` translated with the named result | `502` / `STORAGE.OBJECT_READ_FAILED` / `provider_error` | Close any body; row/staging stay pending; no publication, staging deletion, or success audit. Deliberate read retry is allowed while live. Metric `r2.object.download/failed` and one shared `storage.operation_failed` event; do not classify provider metadata or body corruption as a client upload mismatch or missing object. |
| Publication definite pre-SDK failure, coherent structured non-throttling `4xx` proven not accepted, or coherent conditional-create HTTP `412` + `PreconditionFailed` collision | `R2StorageError` translated with the named result | `502` / `STORAGE.PUBLICATION_FAILED` / `provider_error` | Row and staging stay pending; no success audit or automatic retry. Only a coherent `412` proves this request did not acquire the key: never sign, adopt, reuse, or delete it. Conflicting `412` details, missing status, or any `5xx` is unknown instead. A proven pre-SDK/no-write path has nothing to delete. Metric `r2.object.publish/failed`; emit shared `storage.operation_failed`. |
| Publication coherent structured HTTP `429`, or another unambiguous `4xx` excluding `404`, `408`, `409`, `412`, and `429` with recognized throttling code and proven non-acceptance | `R2StorageError` translated with the named result | `502` / `STORAGE.PUBLICATION_FAILED` / `rate_limited` | Same pending/no-success behavior; no automatic retry. Provider metric `r2.object.publish/rate_limited`; emit shared `storage.operation_failed`. A `5xx` carrying `SlowDown` or another throttling code remains unknown, not a definite rejection. |
| Publication mutation timeout | existing `DependencyMutationTimeoutUnknownError` | `503` / `API.DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN` / `unknown` using scalar `detail`, `details.outcome=unknown`, and `details.timeout_class=dependency_mutation_timeout` | Preserve staging and candidate, keep row pending, no success audit, cleanup, or automatic retry; deliberate replay uses a new candidate. Provider metric `r2.object.publish/unknown_outcome`; WS06-03 owns orphan reconciliation. |
| Publication non-timeout uncertainty: conditional-write/other `409`, `408`, any `5xx` including `503` + `SlowDown` or `503` + `NoSuchKey`, missing/unusable status, contradictory `412`/`429` details, connection loss, generic SDK/transport failure with uncertain dispatch, or malformed/missing success data | `R2MutationOutcomeUnknownError` translated by the venue-image helper | `503` / `STORAGE.MUTATION_OUTCOME_UNKNOWN` / `unknown`; message `Storage mutation outcome is unknown. Check current state before retrying.`; mapping `detail`; no `details` and no `timeout_class` | Preserve staging and candidate, keep row pending, no success audit, cleanup, or automatic retry; deliberate replay uses a new candidate. Provider metric `r2.object.publish/unknown_outcome`; emit shared `storage.operation_failed`; WS06-03 owns orphan reconciliation. |
| Publication cancellation after dispatch and before validated success | re-raise the original cancellation after recording uncertainty | no HTTP envelope is synthesized | Record `r2.object.publish/unknown_outcome`, preserve staging and candidate, write no success audit or cleanup, then re-raise cancellation. A later deliberate completion uses a new candidate. |
| Cleanup deletion definite pre-SDK failure or coherent structured rejection proven not accepted; coherent HTTP `404` plus absent/recognized missing-object code is already-absent idempotent success instead | `R2StorageError` carrying the adapter-owned `failed` result; cleanup catches it instead of translating it | no replacement public response | Preserve the already-established completion/rejection result, record `r2.object.delete/failed` only for a definite failure, emit one `venue_image.cleanup_incomplete` event, and do not retry automatically in request time. Contradictory/missing status is not definite non-acceptance. |
| Cleanup deletion coherent structured `429` or other unambiguous `4xx` excluding `404`, `408`, `409`, `412`, and `429` with recognized throttle code and proven non-acceptance | `R2StorageError` carrying the adapter-owned `rate_limited` result; cleanup catches it instead of translating it | no replacement public response | Preserve the already-established completion/rejection result, record `r2.object.delete/rate_limited`, emit one `venue_image.cleanup_incomplete` event, and do not retry automatically in request time. `5xx` + throttling code remains `unknown_outcome`. |
| Cleanup deletion mutation timeout | existing `DependencyMutationTimeoutUnknownError`; cleanup catches it instead of exposing the timeout envelope | no replacement public response | Preserve the already-established completion/rejection result, record `r2.object.delete/unknown_outcome`, emit one `venue_image.cleanup_incomplete` event, do not retry automatically, and leave later reconciliation/cleanup to WS06-03. |
| Cleanup deletion non-timeout uncertainty: `408`/`409`/any `5xx` including `503` + `SlowDown` or `NoSuchKey`, missing/unusable status, contradictory `404`/`429` details, connection loss, generic SDK/transport failure with uncertain dispatch, or malformed/missing success data | `R2MutationOutcomeUnknownError`; cleanup catches it instead of translating it | no replacement public response | Preserve the already-established completion/rejection result, record `r2.object.delete/unknown_outcome`, emit one `venue_image.cleanup_incomplete` event, do not retry automatically or claim the object is absent, and leave later reconciliation/cleanup to WS06-03. |
| Cleanup deletion cancellation after dispatch and before validated success | preserve the already-established completion/rejection result and propagate cancellation where control can still unwind | no synthesized replacement HTTP envelope | Record `r2.object.delete/unknown_outcome`; never claim deletion succeeded; do not issue a second delete. |
| Configured provider/account/bucket/endpoint does not match the persisted target | `R2StorageTargetMismatchError` | Direct/mutating paths use `503` / `STORAGE.TARGET_MISMATCH` / `configuration_error`; aggregate card readers preserve the null-image fallback defined in Section 3.9 | Fail before client/provider work. No capability, row change, cleanup, or success audit. Correct configuration; never retry against a different target. Metric result `configuration_error` for the prevented R2 operation. Direct/mutating paths emit the applicable safe storage event; aggregate readers emit `storage.operation_failed` and return their parent record without an image. |
| Other missing/invalid R2 configuration | `R2StorageConfigError` | Direct/mutating paths use `503` / `STORAGE.CONFIG_UNAVAILABLE` / `configuration_error`; aggregate card readers preserve the null-image fallback defined in Section 3.9 | Fail before provider work or local mutation. Correct configuration before retry. Record `configuration_error` for the attempted operation. Aggregate readers emit `storage.operation_failed`, omit only the venue-image URL, and preserve the parent game/card response. |
| Read-URL signing explicit failure or malformed output | `R2StorageError` | Direct/mutating paths use `502` / `STORAGE.READ_URL_FAILED` / `provider_error`; aggregate card readers preserve the null-image fallback defined in Section 3.9 | Before a mutation commit, roll back and apply the candidate rule appropriate to definite versus unknown local commit state. Direct readers return no row payload; aggregate readers emit `storage.operation_failed`, omit only the venue-image URL, and preserve the parent game/card response. Metric `r2.read_url.create/failed`; no staging fallback. |
| Processor slot occupied | `ImageProcessingBusyError` | `503` / `STORAGE.IMAGE_PROCESSOR_BUSY` / `retry_later` | After the initial eligibility read, reject before R2/Pillow work or any DB mutation; no success audit/provider metric. Emit one bounded `venue_image.processing_rejected` event with `resource_kind=venue_image` and `result=busy`; caller may retry. |
| Configured Pillow decoder/encoder unavailable | `ImageProcessorNotReadyError` | `503` / `STORAGE.IMAGE_PROCESSOR_UNAVAILABLE` / `not_ready` | Initiation and readiness endpoint fail before signing/persistence; completion fails after admission but before target/client resolution or download; no success audit/provider metric. Emit one bounded `venue_image.processor_not_ready` event; retry only after deployment/configuration repair. |
| Pending intent expired, consumed, or changed at the locked final check | existing lifecycle HTTP exception with explicit mapping | `409` / `STORAGE.UPLOAD_NOT_PENDING` / `conflict` | No activation or success audit; after a confirmed successful conditional candidate creation and definite non-commit, one owned-candidate cleanup attempt is allowed. Never delete a collided or uncertain key. No automatic completion retry. |
| Image is removed/deleted or not visible to the caller | existing not-found exception through the venue-image error helper | `404` / `API.NOT_FOUND` / `not_found` | Preserve accepted non-enumeration, perform no provider call or mutation when known before processing, and clean only this request's confirmed-created candidate if a later locked check proves a definite non-commit. |
| Database timeout before commit invocation or an authoritative non-commit | existing `DatabaseTimeoutError` | `503` / `API.DATABASE_TIMEOUT` / `retry_later` | Roll back, delete only a confirmed-created candidate from this attempt once if definite non-commit is established; preserve staging and write no success audit. A deliberate retry uses a new candidate. |
| Other pre-commit persistence/constraint failure after provider work | `VenueImagePersistenceError` after mapping known domain conflicts separately | `503` / `STORAGE.PERSISTENCE_FAILED` / `failed` | Roll back, delete only this attempt's confirmed-created candidate once, preserve staging, no success audit or raw database detail. Retry only after the cause is corrected. |
| An ordinary `Exception` escapes invoked `commit()` with no affirmative proof of non-commit, whether or not session invalidation/closure subsequently fails | `DatabaseCommitOutcomeUnknownError` translated by the venue-image helper | `503` / `API.DATABASE_COMMIT_OUTCOME_UNKNOWN` / `unknown`; message `Database commit outcome is unknown. Check current state before retrying.`; mapping `detail`; no `details` and no `timeout_class` | Establish preservation before best-effort, separately guarded invalidation and closure; never reuse this request session or claim invalidation succeeded if it failed. Preserve staging and confirmed-owned candidate; no cleanup, retry, second audit, or success claim. Attempt the bounded `venue_image.completion_outcome_unknown` event with `resource_kind=venue_image` and `result=database_commit_unknown`; secondary cleanup/event exceptions cannot change the public result or authorize object deletion. Caller refetches state and WS06-03 owns any orphan; rollback is not proof of non-commit. |
| Python cancellation or another `BaseException` interrupts invoked `commit()` before confirmed success with no proof of non-commit, even if session invalidation/closure raises afterward | Re-raise the original interruption after recording database outcome unknown | no synthesized HTTP envelope | Establish preservation first; separately attempt guarded session invalidation, closure, and one bounded unknown-commit event without masking the original `BaseException`; stop use of that request session. Preserve staging and candidate, never retry commit or delete either object, and never claim rollback. A later caller checks durable state before any deliberate replay. |
| Post-commit staging deletion is failed or unknown | no replacement public error | preserve the successful completion response | Active row/candidate remain authoritative. Record `r2.object.delete/failed`, `rate_limited`, `configuration_error`, or `unknown_outcome` plus one safe cleanup event; WS06-03 owns later cleanup. |
| Rejection/confirmed-owned-candidate cleanup deletion is failed or unknown | no replacement public error | preserve the original rejection/error | Only a validated-success candidate eligible after definite non-commit may be deleted. Preserve the truthful original result; never retry or delete a collided or uncertain key. Record a bounded delete result/event only for an actual cleanup attempt; WS06-03 owns later orphan cleanup. |

Shared storage dependency failures retain the accepted
`storage.operation_failed` event name used by current venue-image, browse-card,
and official-game paths. Its bounded fields are provider kind, operation, final
result, and stable error code. Venue-image-specific local events remain
`venue_image.validation_rejected`, `venue_image.processing_rejected`,
`venue_image.processor_not_ready`, `venue_image.completion_outcome_unknown`, and
`venue_image.cleanup_incomplete` where their local condition actually applies.
The first four use canonical `resource_kind=venue_image` and a bounded `result`.
Cleanup uses `resource_kind=staging` or `publication_candidate` plus the bounded
deletion `result`. These are the only payload fields added by this event family;
canonical request correlation is supplied by the emitter.
An adapter-owned provider metric is never duplicated by a caller. General
storage dependency failures use the shared `storage.operation_failed` event;
request-time cleanup deletion failures use the one local
`venue_image.cleanup_incomplete` event instead, so one failed operation does not
produce two service failure events. There is still only one provider metric
result.

Mutation timeout and non-timeout uncertainty are deliberately different public
contracts. `DependencyMutationTimeoutUnknownError` keeps the accepted timeout
code/message, scalar `detail`, `details.outcome=unknown`, and
`details.timeout_class=dependency_mutation_timeout`. `R2MutationOutcomeUnknownError`
is not a `PublicTimeoutError`; it uses the non-timeout mapping-detail envelope,
code `STORAGE.MUTATION_OUTCOME_UNKNOWN`, message `Storage mutation outcome is
unknown. Check current state before retrying.`, outcome `unknown`, and no timeout
classification. `DatabaseCommitOutcomeUnknownError` likewise uses the non-timeout
mapping-detail envelope with code `API.DATABASE_COMMIT_OUTCOME_UNKNOWN`, message
`Database commit outcome is unknown. Check current state before retrying.`,
outcome `unknown`, and no timeout classification. None of these unknown outcomes
is `retry_later`; reconciliation or a state read precedes any deliberate replay.

Events and metrics may contain provider kind, bounded operation/result, stable
error code, canonical resource kind, and request correlation. The venue-image
event family represents validation categories and local reasons in `result`;
cleanup uses `resource_kind` `staging` or `publication_candidate`. It does not
place internal row/attempt identifiers into the general emitter. Events must not
contain filenames, object keys, account/bucket/endpoint values, URLs,
signatures, credentials, image metadata, provider payloads, or image bytes.

## 4. Failures And Edge Cases

These cases cover the ways untrusted bytes, distributed storage effects, and
local state could otherwise disagree or expose an unsanitized image.

1. **Declared size or type is rejected before upload authorization**
   - **Condition:** The request is empty, over the configured byte bound, or
     declares a type outside the configured approved subset.
   - **Required behavior:** Preserve the existing `400` request-validation
     rejection before a row or upload capability is created. This is not a
     completion-time `ImageContentRejectedError`, emits no image-validation
     result, and does not inspect filename extension or source bytes.

2. **Well-formed download metadata or body violates the upload contract**
   - **Condition:** A well-formed nonnegative provider `ContentLength` is
     outside the configured positive byte bound, unequal to bytes consumed,
     or unequal to the persisted declared size; a bounded body is short,
     overlong, or exceeds the declared size; or a present string provider
     `ContentType` differs from the persisted declaration. An absent provider
     `ContentType` is allowed and leaves byte classification authoritative.
   - **Required behavior:** Close the stream, return
     `400`/`STORAGE.UPLOAD_MISMATCH`/`metadata_mismatch`, record
     `r2.object.download/failed` and one validation-rejection event, attempt
     staging deletion once, and leave the row pending without publication or
     completion audit. Malformed/missing provider metadata is case 8, not this
     upload mismatch.

3. **Content is unsupported, unrecognized, or differs from the declaration**
   - **Condition:** Completion sees one of the ordered Section 3.5 cases: the
     persisted declaration is no longer in the configured approved subset; the
     bounded source has no canonical JPEG, PNG, or WebP signature; or it has an
     approved signature different from the persisted currently allowed
     declaration. A misleading filename is irrelevant.
   - **Required behavior:** A disabled declaration or source without an
     approved signature returns
     `400`/`STORAGE.IMAGE_INVALID`/`unsupported_content`; this intentionally
     groups valid non-approved images and arbitrary unrecognized signatures
     because neither may invoke an unsupported decoder. A different approved
     signature returns
     `400`/`STORAGE.IMAGE_INVALID`/`type_mismatch` without decoding. In every
     case, leave the row pending, create no candidate or success audit, attempt
     staging cleanup once, emit the exact bounded validation-rejection result,
     and never publish the source bytes.

4. **Recognized approved image is corrupt, truncated, animated, or multi-frame**
   - **Condition:** The source has the signature matching its persisted approved
     declaration, but restricted open, format-consistency checking,
     container verification, or complete first-frame decode fails; or a
     dimension-bounded, verified, fully decoded first frame declares more than
     one frame or animation.
   - **Required behavior:** Return `corrupt_image` for ordinary open,
     verification, or first-frame decode failure before checking frame count;
     return `multi_frame` only after those stages pass. A malformed later frame
     cannot supersede `multi_frame` because it is not decoded. Return
     `400`/`STORAGE.IMAGE_INVALID` with the applicable outcome, attempt staging cleanup,
     close owned image resources, and keep the image unpublished. Do not use
     `corrupt_image` merely because bytes have no approved signature; that is
     the `unsupported_content` branch in case 3. Decompression-bomb and
     dimension/pixel failures are the `resource_limit` branch in case 5.

5. **Byte, dimension, pixel, or decompression limit is reached**
   - **Condition:** The processor receives an empty or over-limit buffer, an
     input/output axis or pixel total exceeds its ceiling, or Pillow emits a
     decompression-bomb warning/error.
   - **Required behavior:** Return
     `400`/`STORAGE.IMAGE_INVALID`/`resource_limit` before unrestricted pixel
     work, attempt staging cleanup, and disclose no decoder diagnostic. For a
     declared multi-frame image, known source dimension/pixel excess takes
     precedence over frame-count and ordinary verification/decode failures.

6. **Sanitized output violates its byte or verification contract**
   - **Condition:** A valid bounded input produces empty or over-limit encoded
     bytes, or encoding/output reopen, format, verification, full decode, or
     prohibited-metadata validation fails. Output resource-limit failures use
     case 5.
   - **Required behavior:** Empty or over-limit output returns
     `400`/`STORAGE.IMAGE_INVALID`/`encoded_size_limit`; the other output
     failures return `400`/`STORAGE.IMAGE_INVALID`/`corrupt_image`. Create no
     publication candidate, attempt staging cleanup, and leave the row pending.

7. **Staging download is missing**
   - **Condition:** R2 returns a coherent structured HTTP `404` with an absent
     or recognized missing-object code for the staging key. A contradictory
     status/code pair is not proof of absence.
   - **Required behavior:** Return
     `400`/`STORAGE.OBJECT_NOT_FOUND`/`not_found`, leave the row pending, and do
     not search for or trust an uncommitted publication candidate.

8. **Staging download times out or fails**
   - **Condition:** R2 is unavailable, coherently throttles, times out, or
     returns a contradictory or malformed download response. Examples include
     `503` + `NoSuchKey`, a missing status alongside a missing-object code, a normal SDK return
     without valid HTTP `200` success, `404` with an unrelated code,
     missing/non-integer/negative `ContentLength`,
     a non-string `ContentType`, or non-byte streaming body/chunks.
   - **Required behavior:** Apply Section 3.10: timeouts retain the accepted
     `503` read-timeout envelope; throttling and malformed/provider responses
     use their exact `502` outcomes, `r2.object.download/failed` for malformed
     metadata, and one shared storage-failure event. Close any body obtained;
     retain private staging without deletion and leave intent pending. Unlike
     case 2, this provider failure permits a deliberate read retry without
     requiring reupload.

9. **Publication has an unknown outcome**
   - **Condition:** The conditional sanitized `PUT` has a mutation timeout,
     concurrent conditional-write `409`, `408`, any provider `5xx` (including
     `503` carrying `SlowDown` or `NoSuchKey`), a missing/unusable status or
     contradictory structured error, connection loss, generic SDK/transport
     failure whose dispatch point cannot be proved, or malformed/missing
     success data.
     Cancellation after dispatch is the same storage-uncertainty class but keeps
     cancellation propagation semantics.
   - **Required behavior:** For an HTTP-returning path, use the exact timeout or
     non-timeout mutation-unknown contract from Section 3.10. Preserve both
     staging and candidate and leave the row pending. A cancellation records the
     unknown provider result and preservation responsibility, then re-raises
     rather than synthesizing an HTTP response. A later completion uses a new
     attempt key; it never overwrites, adopts, or request-time deletes the
     uncertain candidate.

10. **Publication is definitely rejected or configuration is invalid**
    - **Condition:** Local validation fails before the SDK mutation method
      is invoked, R2 returns an explicit rejection proven not accepted, R2
      unambiguously throttles the write with a coherent non-ambiguous `4xx`,
      or target/credential configuration is invalid before SDK invocation.
    - **Required behavior:** Do not delete staging or activate the row. Return
      the exact provider/configuration result from Section 3.10. A provider
      `5xx` (even with a throttling code), conflicting or missing response
      status, uncertain transport failure, or missing/malformed success data
      does not belong here; it is case 9. Only a coherent conditional-create
      `412` + `PreconditionFailed` is a definite collision, not candidate
      ownership: preserve staging, return
      `502`/`STORAGE.PUBLICATION_FAILED`/`provider_error`, emit one shared
      storage-failure event and `r2.object.publish/failed`, and never delete,
      adopt, sign, or reuse the collided key. No automatic application or SDK
      publication retry occurs.

11. **Processing admission is occupied**
    - **Condition:** Another completion in the same API process owns the single
      processing slot.
    - **Required behavior:** Return
      `503`/`STORAGE.IMAGE_PROCESSOR_BUSY`/`retry_later` without waiting,
      downloading an object, allocating an image, recording a provider result,
      or mutating database state.

12. **Intent expires during processing**
    - **Condition:** The initial check passes but the locked final check occurs
      at or after `upload_expires_at`.
    - **Required behavior:** Return
      `409`/`STORAGE.UPLOAD_NOT_PENDING`/`conflict`, write no completion audit,
      and do not activate. After definite non-commit, make one best-effort
      deletion only of this request's confirmed-created candidate; never delete
      staging or a collided/uncertain key.

13. **The pending row changes during processing**
    - **Condition:** An administrator PATCH commits after the completion's
      initial read and before its final row lock.
    - **Required behavior:** The final locked recheck rejects only a lifecycle or
      consumption change that makes the row non-completable, such as removal,
      non-pending/consumed state, or expiry. If the row is still pending and the
      PATCH changed `image_role`, `is_primary`, `sort_order`, `alt_text`, or
      `caption`, completion deliberately adopts those freshly locked values,
      applies primary-image behavior from the fresh `is_primary` value, and
      writes the completion audit from the fresh bounded snapshot. It does not
      claim stale rejection for metadata changes it does not version.

14. **Two completion requests race**
    - **Condition:** Both requests pass initial checks and perform processing.
    - **Required behavior:** At most one commits activation, primary-image
      effects, publication metadata, and the successful audit. The other returns
      a conflict after the fresh locked check and can delete only its own
      *confirmed-created* candidate. Publication uses `If-None-Match: *` with
      SDK retries disabled. Force both attempts to propose the same UUID/key:
      at most one may successfully create it; a `412` loser cannot delete or
      overwrite the winner's object, and an uncertain `409` loser preserves
      the key. A deterministic distinct-key race in which the loser finishes
      publication after the winner commits must also preserve the winner's
      bytes, ETag, size, URL, and key.

15. **Definite local non-commit after provider work**
    - **Condition:** This request's conditional publication returned validated
      success, but the locked check, response signing, flush, or another
      pre-commit step fails, or the database affirmatively proves non-commit.
    - **Required behavior:** Roll back local changes, keep staging available,
      make one best-effort deletion only of the confirmed-owned candidate, and
      return the original error. A collided or uncertain key is never a cleanup
      target; a later completion starts from staging with a new attempt key.

16. **Database commit result is unknown, including interruption**
    - **Condition:** `commit()` has been invoked but has not returned confirmed
      success when it raises an ordinary exception, Python cancellation, or
      another `BaseException`, including when the real commit succeeds before
      interruption reaches Python.
    - **Required behavior:** Establish unknown status and preserve staging and
      the confirmed-created candidate before cleanup. Attempt session
      invalidation and closure independently under guards that preserve the
      original exception or `BaseException` even if either recovery step raises;
      do not reuse the affected session or allow an outer generic handler to
      delete either object. Attempt the bounded unknown-commit event once;
      diagnostic failure cannot change the result. Do not claim rollback,
      retry commit, or write another audit. Ordinary exceptions produce the exact
      `503`/`API.DATABASE_COMMIT_OUTCOME_UNKNOWN`/`unknown` response;
      cancellation/other `BaseException` is re-raised without synthesizing an
      HTTP response. A caller refetches state before any deliberate replay;
      WS06-03 owns any orphan.

17. **The old upload URL is replayed after activation**
    - **Condition:** The browser writes the staging key again before its
      presigned URL expires.
    - **Required behavior:** The active image and all application read URLs
      continue to reference the unchanged publication key. No completion replay
      or staging write may alter published bytes or database state.

18. **Post-commit staging deletion fails or has an unknown outcome**
    - **Condition:** The sanitized publication and database activation committed,
      but the request-time staging delete did not produce confirmed success.
    - **Required behavior:** Preserve and return the truthful successful
      completion because every reader uses the sanitized committed key. Record
      the bounded deletion result safely; do not roll back or rewrite the active
      row and do not expose staging.

19. **Losing-candidate cleanup fails or has an unknown outcome**
    - **Condition:** A rejected, stale, or locally failed request cannot confirm
      deletion of its own uncommitted candidate.
    - **Required behavior:** Preserve the truthful rejection or original error,
      keep the database row unchanged, record the bounded deletion result, and
      never reuse or expose the candidate key.

20. **Processing support is unavailable**
    - **Condition:** The installed Pillow build lacks an approved decoder or
      encoder.
    - **Required behavior:** Both the readiness endpoint and a direct upload
      initiation return
      `503`/`STORAGE.IMAGE_PROCESSOR_UNAVAILABLE`/`not_ready`; initiation must
      create no capability, row, storage effect, or success audit.

21. **Persisted storage target and current configuration disagree**
    - **Condition:** Any initiation, download, publication, deletion, or signing
      path observes a provider/account/bucket/endpoint mismatch.
    - **Required behavior:** Fail before provider work, mutate nothing, emit no
      success audit, and never redirect the row to current configuration.
      Direct venue-image reads return the exact
      `503`/`STORAGE.TARGET_MISMATCH`/`configuration_error` response. Browse/game
      cards and official-game administrative cards instead preserve their
      accepted aggregate behavior: emit `storage.operation_failed`, omit only
      the venue-image URL, and still return the game/card. Pending initiation
      never invokes read signing. Operators must correct configuration or use
      separately authorized lifecycle work.

22. **Cancellation or interruption occurs before commit invocation**
    - **Condition:** A Python cancellation or interruption reaches the workflow
      during provider, processing, or another step before `commit()` is invoked.
      Interruption during an invoked but unconfirmed commit is case 16.
    - **Required behavior:** Close owned image and stream resources, release the
      admission slot, perform no local activation, and then re-raise the
      cancellation rather than translate it into a public HTTP error. Cancellation
      before mutation dispatch records no provider result. Cancellation after
      mutation dispatch but before validated success records `unknown_outcome`
      and preserves the candidate. Cancellation after validated publication
      success followed by a definite local non-commit may delete only that
      request's confirmed-owned candidate before propagation. Collided or
      unknown-outcome publication keys are never cleanup targets. Synchronous
      Pillow work is allowed to reach its bounded return point before control
      can unwind; the plan does
      not claim that a browser disconnect forcibly terminates native decoder
      work.

23. **Interruption occurs after confirmed activation commit**
    - **Condition:** The database commit has returned confirmed success, but the
      request or process is interrupted before staging cleanup or the response
      completes. An interruption before confirmed return remains case 16.
    - **Required behavior:** The committed active row and its immutable
      publication object remain authoritative and are not rolled back. Staging
      may remain private; a completion replay observes consumed state and cannot
      republish. If the process remains alive, `finally` releases its admission
      slot; process exit releases all process-local state.

## 5. Testing

Testing must prove both that accepted images are rebuilt from bounded decoded
pixels and that every abnormal path keeps staging bytes outside application
read paths. The ordinary deterministic suite uses synthetic image bytes and
mocked R2 boundaries, requires no provider credentials, makes no external
network calls, and retains all simulated failure coverage. A separately
runnable provider-contract suite uses only isolated non-production credentials
and a dedicated R2 test bucket to verify the real adapter/provider operation
semantics on which publication safety depends. Neither suite uses production
credentials, production data, or a production bucket.

### 5.1 Image processor tests

- Generate small valid JPEG, PNG, and WebP fixtures and prove the output fully
  decodes, retains intended dimensions and transparency behavior, uses the
  detected approved format, and stays within the output byte bound.
- Attach EXIF orientation, EXIF fields, ICC data, comments, XMP-like data, and
  PNG text where supported; prove orientation is applied and none of that
  caller-supplied metadata survives output encoding.
- Exercise the complete ordered Section 3.5 matrix rather than grouping all
  invalid bytes under one assertion. Prove that a declaration outside the
  current configured subset is `unsupported_content` before signature probing;
  each JPEG/PNG/WebP signature paired with a different currently allowed
  declaration is `type_mismatch` without a decoder call; valid GIF, BMP, TIFF,
  ICO, PPM, and representative arbitrary/unrecognized bytes are
  `unsupported_content` without invoking an unsupported decoder; and a source
  with the matching approved signature whose restricted open, reported format,
  verification, or full decode otherwise fails is `corrupt_image`. Cover
  truncated and otherwise corrupt data for each approved format, not only
  malformed headers, and prove decompression-bomb failures remain
  `resource_limit` rather than being absorbed into `corrupt_image`.
- Prove filename and extension have no authority: valid approved bytes with a
  misleading or absent extension succeed when the persisted declaration
  matches, while an approved-looking filename does not change the result for
  unsupported, mismatched, or corrupt content. Prove that source
  dimension/pixel limits are checked before frame count, that container
  verification and complete first-frame decode precede `multi_frame`, and
  that later frames of rejected multi-frame content are never decoded.
  Exercise intersecting conditions: oversized animated/multi-frame content is
  `resource_limit`; dimension-bounded multi-frame content whose first frame
  fails ordinary verification/decode is `corrupt_image`; a verified and fully
  decoded first frame with additional frames is `multi_frame` without
  attempting later-frame decoding. A successfully decoded single-frame mode
  that cannot be normalized safely remains `unsupported_content`.
- Exercise just-below, exact, and just-above byte, axis, and total-pixel
  boundaries with a smaller injected policy where needed so tests remain fast
  and memory-bounded.
- Prove decompression warnings/errors are rejected, truncated-image support is
  not enabled globally, resources close on every path, and output verification
  classifies empty/over-limit encoder output as `encoded_size_limit`, malformed
  or metadata-bearing output as `corrupt_image`, and output resource-bound
  failures as `resource_limit`.
- Run the same input through the processor repeatedly and assert byte-identical
  output under the pinned library and explicit encoder settings.

### 5.2 R2 adapter and observability tests

- For upload signing, staging download, candidate publication, deletion, and
  read signing, prove the adapter receives the persisted
  provider/account/bucket target and sends that exact bucket to the SDK. Cover
  wrong provider, wrong account, wrong bucket, an endpoint for another account,
  an alternate endpoint host/path, and configuration drift after intent
  creation; every mismatch must fail before client construction with
  `configuration_error`, no provider call, and no private target values in
  diagnostics. Direct/mutating paths must expose the exact `503` target-mismatch
  contract, while aggregate card readers must exercise the Section 3.9 null-image
  fallback instead of converting the parent response into a `503`.
- Prove download reads no more than `max_bytes + 1`, validates response shape
  and lengths, validates HTTP `200` on a normal full-object SDK return, and
  closes the streaming body. Inject absent/non-integer/boolean/incorrect
  success status and prove the adapter reports a malformed-provider failure
  without staging deletion or publication. Separately inject absent,
  non-integer, boolean, and negative `ContentLength` as malformed provider
  responses yielding `502`/`STORAGE.OBJECT_READ_FAILED`/`provider_error`,
  `r2.object.download/failed`, one shared storage-failure event, no staging
  deletion, and safe deliberate read retry; a present non-string `ContentType`
  has the same malformed-provider result; also inject a non-streaming body
  and non-byte body chunks and prove they never become client-side size or
  content mismatches. Prove an absent `ContentType` proceeds to byte
  classification and a matching present value does not change it.
  Inject a differing present string `ContentType`, well-formed zero or
  over-limit length, short/overlong consumed body, and declared-size mismatch;
  each yields `400`/`STORAGE.UPLOAD_MISMATCH`/`metadata_mismatch`, one
  validation-rejection event, `r2.object.download/failed`, and one
  staging-delete attempt. Test structured HTTP `404` plus absent or recognized
  missing-object code as the only definitive missing-object response;
  contradictory `404` + unrelated code, `429` + `NoSuchKey`, `503` +
  `NoSuchKey`, a missing status
  with `NoSuchKey`/`SlowDown`, coherent `429`, and coherent `503` + explicit
  throttling separately. Assert the exact not-found versus failed versus
  rate-limited metric, public code/outcome, storage event, staging preservation,
  and retry behavior for each case; retain timeout, configuration, and other
  failure coverage.
- Prove publication sends only the expected bucket, attempt-specific
  server-generated key, bytes, sanitized content type, and
  `IfNoneMatch="*"`; its publication-specific SDK client has
  `total_max_attempts=1`. Reject missing/malformed success ETags. Independent
  successful attempts produce different keys. Inject a pre-existing key and a
  forced duplicate UUID: the resulting `412` must not overwrite, delete, adopt,
  sign, or reuse that candidate; test the exact failed metric, event, and public
  error. Inject a competing conditional-write `409` and prove unknown outcome,
  preservation, and no automatic SDK/application mutation retry.
- Prove deletion accepts only the persisted staging key or this request's
  confirmed successfully created uncommitted candidate; it cannot target a
  collided, unknown-outcome, or another request's committed candidate. An
  already-absent eligible deletion is idempotent success.
- Cover every result token in the complete R2 operation table. For both
  publication and deletion, separately prove confirmed success, coherent
  definite `4xx` throttling, prevention before SDK invocation, coherent
  definite-rejection `4xx`, ambiguous `408`/`409`/`5xx`, mutation connect/read
  timeout, generic SDK/transport failure without a definite non-acceptance
  response, malformed/missing success data, target/configuration failure,
  coherent publication `412` collision, and cancellation before versus after
  dispatch. For **each** mutation inject contradictory status/code pairs:
  `503` + `SlowDown`, `503` + `NoSuchKey`, missing/unusable status with either
  code, `429` + missing-object code, and `404` + unrelated code. All must stay
  `unknown_outcome`, preserve possibly affected objects, emit the exact one
  bounded result, and forbid request-time retries or delete claims. Separately
  prove coherent `429` remains `rate_limited`, coherent `412` +
  `PreconditionFailed` is a non-owning publication collision, and coherent
  `404` + missing-object code is idempotent deletion success only for an eligible
  object. Prove upload/read signing keeps its separate accepted local-signing
  classification and cannot gain an object mutation outcome from these rules.
  Unknown mutation paths must record exactly one `unknown_outcome` provider
  metric, preserve a possibly written candidate without claiming ownership,
  and never be collapsed into definite failure. Cancellation after dispatch must re-raise after recording
  uncertainty rather than synthesize an HTTP response.
- Prove the metadata `HEAD` adapter and `r2.metadata.head` token are absent from
  the complete post-pass production operation, metric, transaction, timeout,
  cost, and retry inventories.
- Prove object connect/read settings use their canonical environment names,
  defaults, positive-integer validation, and SDK client fields, and that the
  old metadata-only settings are no longer accepted as the current contract.
- Prove provider permission errors for download, publication, and deletion map
  to safe provider failures without leaking bucket, prefix, credential, or key
  values. Source tests assert the exact operation/prefix contract without
  claiming provider-side token proof.
- Preserve `storage.operation_failed` as the shared storage-failure event for
  venue-image direct reads, browse/game-card fallback, official-game-card
  fallback, and ordinary provider/configuration failures introduced here. Assert
  the bounded operation/result/stable-code fields. Assert every venue-image
  local event through the real structured emitter, including its exact
  `resource_kind`/`result` shape and absence of `logging.event_rejected`.
  Cleanup deletion failures use the local `venue_image.cleanup_incomplete`
  event instead, with no duplicate service failure event for the same failed
  operation.
- Update the existing provider-boundary and retry-policy assertions so they
  recognize the intentional R2 download/publish/delete calls, continue to
  forbid a second network owner, classify publish as no-automatic-retry and
  delete as idempotent, preserve SDK-owned retry ownership for other
  operations, require publication-specific SDK retries disabled, and prove
  neither the application nor the SDK makes a second publication PUT.

### 5.3 Isolated R2 provider-contract test

Add a focused provider-contract suite under
`backend/tests/provider_contract/r2/` and a repository-owned runner mode that
selects only that suite and explicitly enables its R2 network access. It must be
separately runnable from ordinary and migration tests, and the ordinary/full
backend suite must continue to block provider network access. Run it with:

```text
backend/.venv/bin/python -m backend.test_runner test provider_contract backend/tests/provider_contract/r2 -q
```

The new `provider_contract` mode is database-free and allows network access
only to the validated configured R2 test endpoint. The provider run must refuse
to start unless
`R2_TEST_ACCOUNT_ID`, `R2_TEST_ACCESS_KEY_ID`,
`R2_TEST_SECRET_ACCESS_KEY`, `R2_TEST_BUCKET_NAME`, and
`R2_TEST_ENDPOINT_URL` are all present, the endpoint is a valid HTTPS R2
endpoint for that test account, and the test bucket differs from the
application's configured R2 bucket when both are present. Missing test
configuration is a reported provider-test prerequisite, not an ordinary-suite
skip that can be mistaken for proof.

Use a unique `provider-contract/r2-object-semantics/{run_id}/` key prefix for each run,
track every created key locally, and delete those exact keys in `finally`
cleanup without requiring bucket listing. The suite must never print or retain
credentials, endpoint/account/bucket values, signed URLs, object keys, or
provider-private response bodies in normal output or failure artifacts. Test
credentials and setup helpers may have the minimum Get/Put/Delete access needed
inside the dedicated test bucket; that test-only setup access does not expand
the production credential contract in Section 3.6.

Exercise the production R2 adapter against the real test bucket and prove all
of the following in one isolated operation family:

- Seed a staging object with known non-sensitive bytes and metadata, retrieve it
  through the production bounded staging `GetObject` path, and assert the bytes,
  length, content type, and ETag returned by the adapter match the object.
- Conditionally publish known sanitized bytes to an absent attempt key through
  the production publication path with `IfNoneMatch="*"`, assert validated
  success, and read the object back to prove the expected bytes were stored.
- Seed a second publication key with original bytes, attempt to publish distinct
  replacement bytes to that same key through the production conditional path,
  assert that R2 returns the adapter's definite `412` collision result, and
  independently read the key afterward to prove the original bytes remain
  unchanged. The collision path must not delete or otherwise mutate that key.
- Delete a test object through the production deletion path, verify it is
  absent, call the same deletion path again, and verify the already-absent case
  remains idempotent success.

Keep timeout, connection loss, ambiguous `409`, provider `5xx`, malformed
responses, missing success data, cancellation timing, and other simulated
failure classifications in the deterministic mocked suite; the provider test
must not attempt to induce nondeterministic network failures. This test-bucket
contract verifies the current GetObject/conditional-PutObject/DeleteObject
semantics only. It does not claim final production token permissions, browser
CORS behavior, delivery topology, lifecycle reconciliation, or cache/removal
proof.

### 5.4 Completion and persistence tests

- Prove successful completion downloads staging bytes, publishes a unique
  candidate using the persisted target, persists that candidate's authoritative
  metadata, activates and audits once, commits before staging cleanup, attempts
  staging deletion against the same target, and returns the already-signed
  publication URL.
- Prove the complete publication-state matrix at the database and model layers:
  pending requires no publication tuple and null `upload_completed_at`; active
  and hidden require the complete publication tuple and non-null
  `upload_completed_at`; removed-before-publication requires the unpublished
  form; removed-after-publication requires the published form. Reject every
  partial publication tuple, every publication/completion-timestamp mismatch,
  unsupported publication type, invalid published size, blank publication
  identity, and duplicate publication key.
- For every pre-commit validation or provider failure that prevents
  activation, assert the row remains pending, no completion audit or
  primary-image side effect is written, and no staging key becomes readable
  through an application response. Keep post-commit cleanup failures in their
  separate truthful-success contract below.
- Drive every Section 3.5 processor-rejection result through the production
  completion/API path. Assert the exact `400`/`STORAGE.IMAGE_INVALID` envelope
  and `unsupported_content`, `type_mismatch`, `corrupt_image`, `multi_frame`,
  `resource_limit`, or `encoded_size_limit` outcome; drive oversized multi-frame
  sources (`resource_limit`), bounded multi-frame sources with invalid first
  frames (`corrupt_image`), and fully decoded bounded first frames declaring
  additional frames (`multi_frame`) through the production service as well;
  assert no publication candidate, primary-image change, or success audit;
  one staging-cleanup attempt; and one
  bounded `venue_image.validation_rejected` event with the same result. Prove
  the successful bounded download retains its `r2.object.download/succeeded`
  metric and is not relabeled as a provider failure or accompanied by
  `storage.operation_failed`.
- Prove each partial boundary: publication unknown outcome leaves staging and
  pending state; signing, flush, and authoritative non-commit failure leave
  staging and clean only the request's confirmed-created candidate;
  candidate-cleanup failure
  preserves the original error; post-commit staging-cleanup failure preserves
  truthful success; and missing staging never falls back to an uncommitted
  candidate. Inject an interruption immediately after confirmed commit and
  prove the active row/publication remain authoritative, staging stays private,
  and replay cannot publish again.
- Separate definite pre-commit/non-commit proof from commit uncertainty. Inject
  a `commit()` implementation that performs the real PostgreSQL commit and then
  raises a connection/DBAPI error. Through the production completion entry
  path, assert the exact
  `503`/`API.DATABASE_COMMIT_OUTCOME_UNKNOWN`/`unknown` envelope, one commit
  invocation, session invalidation/closure, no candidate or staging deletion,
  no automatic retry, and no second audit. Independently fault session
  invalidation and session closure after that real commit succeeds and raises:
  each secondary exception must leave the original unknown-commit `503`, no
  cleanup of staging/candidate, no second audit or commit, one attempted bounded
  unknown-commit event, and no further use of the affected request session.
  Repeat with the real PostgreSQL commit succeeding and then
  `asyncio.CancelledError` (and a representative other `BaseException`)
  interrupting before the call returns: preserve both objects, attempt the
  bounded unknown-commit diagnostic, and propagate the **original** interruption
  even when invalidation or closure raises another exception. No synthesized
  HTTP `503`, object deletion, automatic retry, or second audit is allowed.
  Independently verify both session-cleanup failure sites for an ordinary
  exception and for at least one `BaseException`. In a fresh session, prove
  the active row, selected
  candidate metadata, primary effect, and one success audit committed atomically
  in each case; prove replay cannot republish. Also inject an authoritative
  non-commit before invocation and prove only a confirmed-owned candidate is
  eligible for cleanup.
- Preserve exact before/equal/after expiry coverage with an injected clock and
  repeat the locked expiry check after processing.
- Use independent PostgreSQL sessions and deterministic barriers to prove two
  completions with distinct candidate keys produce one activation/audit.
  Exercise the interleaving where the loser finishes its R2 publication after
  the winner commits, then prove the committed key's bytes, ETag, size, URL, and
  database metadata remain coherent and the loser deletes only its
  confirmed-owned candidate after definite non-commit. Force a second race in
  which both attempts propose the same UUID/key; enforce the conditional-write
  boundary so neither an existing winner nor another row's published object
  can be overwritten or deleted, including when one call receives `412` and
  another has an uncertain `409` result. Separately commit an administrative PATCH while completion is
  processing: prove a lifecycle change such as removal is rejected by the final
  locked check, while pending-preserving changes to role, primary selection,
  sort order, alt text, and caption are adopted from the freshly locked row and
  reflected in primary effects and the completion audit.
- Hold the process-local admission slot and prove a second in-process request
  receives `503` before provider work or image allocation, performs no database
  mutation, and does not queue. Prove release after success, every rejection,
  provider failure, database failure, and interruption so a later request can
  enter.
- Prove a staging-key write after activation cannot change the bytes, ETag, URL,
  or metadata returned for the active publication object.

### 5.5 Read-path and browser-contract regression tests

- Prove the complete affected reader population uses publication key plus
  persisted target and never falls back to staging or ambient account/bucket
  configuration. Direct public/admin venue-image responses must propagate the
  exact target-mismatch or read-signing error; browse/game-card and
  official-game-card aggregate readers must instead emit `storage.operation_failed`,
  keep the game/card, and return a null venue-image URL. Query/projection tests
  must fail if an aggregate reader drops the persisted target or publication
  key.
- Prove public lists still return only active images and preserve their current
  minimized response fields. Administrative list/update/remove behavior must
  match the state matrix, including null `image_url` for unpublished removed
  responses and publication-only signing for published removed responses.
- Prove successful upload initiation invokes only staging `PUT` signing, never
  the read signer, retains the fields consumed by the frontend, and returns a
  null nested `image_url`; completion alone returns a non-null sanitized
  publication URL after success.
- Preserve the current active-admin route matrix, upload intent expiry/replay
  contract, three-selected-image capacity behavior, primary-image transition,
  and browser `PUT` followed by completion flow.
- Prove the create-game frontend sends selected venue-image upload/completion
  workflows sequentially rather than through `Promise.all`, preserves order and
  primary selection, stops truthfully on the first failure, and does not add an
  automatic completion retry.
- Run the focused frontend API-client and create-game unit checks because the
  upload response nullability and submission scheduling change, but do not add
  browser/end-to-end testing solely for this processing contract.

### 5.6 Configuration and migration tests

- Prove settings accept each non-empty subset of JPEG, PNG, and WebP and reject
  unsupported types, an empty explicit set, and a byte limit outside `1..8 MiB`.
- Prove upload initiation rejects a declaration outside the configured subset
  through existing request validation before processor readiness, signing,
  persistence, or audit. Create an intent while a type is enabled, narrow the
  configured subset before completion, and prove completion returns
  `unsupported_content` before signature probing or decoder invocation rather
  than `type_mismatch`, `corrupt_image`, or processor-not-ready.
- Prove the object-operation timeout settings replace the metadata-only names,
  keep the defined portable defaults and positive-integer validation, and remain
  distinct from any claim about final provider or request deadlines.
- Prove the administrative readiness endpoint, upload initiation, and
  completion entry point call the same canonical processor validator. Send a
  direct upload-initiation request
  with one configured required decoder or encoder unavailable and assert the
  exact `503` processor-not-ready envelope, no upload/read signer or R2 client
  call, no `venue_images` row, no storage mutation, no create-success audit, and
  the bounded readiness event. Prove authorization and request validation still
  precede the initiation check, and prove that check precedes capacity locking,
  signing, and persistence. Separately prove completion checks after admission
  but before target/client resolution or download and always releases the slot
  on a not-ready result.
- Exercise every Section 3.10 row through the production service/API path where
  it is externally observable. Assert exact exception type, status, top-level
  code/message, correlation ID, mapping `detail.outcome` for non-timeout errors,
  scalar `detail` plus `details.outcome`/`details.timeout_class` only for timeout
  errors, transaction/persistence/storage effects, audit/event behavior, metric
  operation/result, and retry/reconciliation disposition. Prove specifically
  that `R2MutationOutcomeUnknownError` returns
  `STORAGE.MUTATION_OUTCOME_UNKNOWN`/`unknown` without timeout classification,
  `DatabaseCommitOutcomeUnknownError` returns
  `API.DATABASE_COMMIT_OUTCOME_UNKNOWN`/`unknown` without timeout
  classification, generic `503` does not synthesize `retry_later`, and the
  accepted `DependencyReadTimeoutError` and
  `DependencyMutationTimeoutUnknownError` envelopes remain unchanged. Include
  the conflicting R2 status/code and secondary uncertain-commit session-cleanup
  cases in this exact public-outcome and prohibited-side-effect check.
- Rebuild the guarded ordinary test database after editing the canonical venue
  image migration.
- Prove a clean migration build has the publication columns, constraints, and
  indexes; the SQLAlchemy model matches them; and downgrade/re-upgrade and drift
  checks remain valid under the migration test runner.
- Prove the affected architecture/trust, credential-purpose, storage-limit,
  timeout, provider-cost, transaction-boundary, retry, operation, metric, and
  diagnostic inventories all describe the same post-pass R2 surface and retain
  no metadata-only or no-object-mutation claim.
- Run focused venue-image, settings, R2 timeout/metrics, response-minimization,
  provider-boundary, transaction/retry/cost inventory, migration, and frontend
  coverage, followed by the full backend suite because the R2 adapter,
  cross-cutting policy registries, database schema, and shared game-image
  readers have cross-cutting consumers. Run the isolated R2 provider-contract
  suite separately with its dedicated non-production configuration; its result
  is required in addition to, not as part of or a replacement for, the ordinary
  deterministic regression suite.

## 6. Done When

This checklist is the engineering completion bar for WS06-02.

- [ ] Browser-uploaded bytes remain under a private staging key and no
      application reader exposes that key as an image URL.
- [ ] JPEG, PNG, and WebP inputs are validated from actual bytes under the byte,
      dimension, pixel, frame, and decompression bounds.
- [ ] Declared type, current configured policy, canonical JPEG/PNG/WebP
      signature, and restricted decode result follow the complete ordered
      Section 3.5 matrix: unsupported or unrecognized signatures are
      `unsupported_content`, a different approved signature is
      `type_mismatch`, matching approved content whose ordinary restricted
      decoding or verification fails is `corrupt_image`, and byte, dimension,
      pixel, or decompression bounds remain `resource_limit` before frame-count
      rejection; ordinary container-verification or first-frame decode failures
      precede `multi_frame`, which is returned only for a bounded, successfully
      verified/decoded first frame declaring animation/additional frames. No
      rejected later frames are decoded. Intersecting cases have explicit
      processor and production-completion tests. Encoder/output verification
      has the explicit Section 3.5 results. Filename and extension
      do not influence classification, and every rejection preserves the
      defined no-publication side effects and exact public/event outcome.
- [ ] Successful output is a fully verified fresh re-encoding with uploader
      metadata removed and deterministic format-specific settings.
- [ ] Pending, active, hidden, removed-before-publication, and
      removed-after-publication rows satisfy the complete publication tuple /
      completion-timestamp matrix, with matching model and canonical migration
      constraints and no staging read capability.
- [ ] Each completion uses a server-only conditional-create candidate with
      SDK retries disabled; a UUID collision cannot overwrite an existing
      object, and no collided or uncertain candidate can be deleted by a loser.
      One locked and audited transition selects the immutable winner. The
      separately run non-production R2 provider-contract test proves the real
      provider rejects an existing-key conditional publication and leaves the
      original bytes unchanged.
- [ ] An invoked commit whose outcome is unknown preserves candidate and staging
      even on cancellation/other `BaseException` or failed session
      invalidation/closure; ordinary exceptions produce the exact unknown
      response, while the original interruption propagates without an invented
      HTTP response. Secondary cleanup failure never authorizes object deletion
      or masks the original result; no affected session is reused. State
      read/replay cannot delete a possibly committed winner; definite non-commit
      cleanup remains separate.
- [ ] One processing admission slot per API process bounds concurrent image
      memory/work, the ordinary browser flow completes selected images
      sequentially, and overload fails before provider or decoder work.
- [ ] Upload initiation reuses the canonical processor-readiness check before
      capability signing or durable/audit effects and fails closed with the
      exact not-ready contract.
- [ ] Every R2 read and mutation outcome—including contradictory status/code
      responses, absent status, coherent absence/throttling/collision, and
      ambiguous `5xx` mutations—has one explicit result. Every
      processing/expiry/cancellation path, concurrent completion, concurrent
      pending-row PATCH, rollback, and partial-success path leaves unsafe bytes
      unpublished; cancellation propagation and deliberate retry/reconciliation
      behavior are defined rather than inferred.
- [ ] Successful activation is followed by one staging cleanup attempt, while
      cleanup failure cannot make staging public or turn a committed sanitized
      image into a misleading failed completion.
- [ ] Direct public/admin readers and aggregate browse/official-game card
      readers use publication keys plus persisted R2 target identity with their
      caller-specific failure behavior; no reader falls back to staging, and
      successful upload initiation never creates a staging read URL.
- [ ] R2 operation metrics, timeout/unknown-outcome behavior, safe diagnostics,
      minimum credential-purpose contract, and every affected cross-cutting
      inventory cover the exact download/publish/delete surface and remove the
      obsolete metadata-only `HEAD` contract.
- [ ] Every externally observable WS06-02 failure has the exact exception,
      status, code, envelope outcome, side effects, audit/event, metric, and
      retry/reconciliation behavior defined in Section 3.10.
- [ ] Focused processor, service, PostgreSQL, configuration, adapter, API, and
      frontend compatibility tests pass, followed by the affected full backend
      regression suite; the separately runnable isolated R2 provider-contract
      suite also passes for bounded staging `GetObject`, conditional
      publication `PutObject`, collision/no-overwrite, and idempotent
      `DeleteObject` behavior.
