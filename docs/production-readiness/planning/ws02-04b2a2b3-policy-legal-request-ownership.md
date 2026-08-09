# WS02-04B2A2B3 Policy And Legal Request Ownership

Pass: WS02-04B2A2B3

Scope: policy/legal content ownership, generic policy-document write
retirement, and generic policy-acceptance mutation retirement.

## Split

- B1 retired obsolete body-bearing lifecycle and generic CRUD scaffolds.
- B2 owned opaque provider/payment inputs, checkout return URLs, inbox seen
  tokens, raw provider metadata, generic payment mutation retirement, and
  source-derived game-credit behavior.
- B3 owns the policy, legal, and acceptance request surfaces that previously
  blocked broader ordinary body-limit work.
- A2C remains responsible for activating the general ordinary JSON request-body
  limit.

## Current Legal Architecture

Current legal pages and agreement presentation are source/content-managed by
the application. The frontend uses static/source-owned legal content for Terms,
Privacy, cancellation/refund policy presentation, and existing signup/checkout
agreement display. There is no active policy-authoring UI, no current frontend
caller for generic policy-document writes, and no current frontend caller for
generic policy-acceptance writes.

B3 does not add a policy editor, move legal text into API-managed content, or
create a new acceptance product workflow.

## Policy Document Writes

The generic public/admin policy-document authoring routes are retired as stable
bodyless tombstones:

- `POST /policy-documents`
- `PATCH /policy-documents/{policy_document_id}`

The routes no longer accept arbitrary client/admin `content_text` or
`content_url` request bodies. They preserve authentication, correlation,
response-security headers, CORS behavior, and stable error shape, but do not
parse JSON request bodies and do not mutate policy-document rows.

Policy-document read behavior remains available for managed records:

- `GET /policy-documents`
- `GET /policy-documents/{policy_document_id}`

## Policy Content And content_url Ownership

Policy content remains source/content-managed. The retained internal model and
service primitives can still support controlled setup, seed, or bootstrap
records, but generic public/admin callers cannot author legal content through
the API.

If `content_url` is present on an internal policy record, it is managed
reference metadata. B3 does not allow ordinary clients or generic admin bodies
to supply arbitrary external policy URLs, does not fetch arbitrary URLs, and
does not add origin or hosting assumptions.

No policy-specific large-body request class is introduced, and no arbitrary
policy-text maximum is selected.

## Policy Acceptance Mutations

The generic policy-acceptance mutation routes are retired as stable bodyless
tombstones:

- `POST /policy-acceptances`
- `PATCH /policy-acceptances/{policy_acceptance_id}`

Generic callers can no longer fabricate or rewrite acceptance evidence,
including user identity, acceptance time, policy identity/version, IP metadata,
or user-agent metadata.

Existing acceptance records remain readable for admin workflows:

- `GET /policy-acceptances`
- `GET /policy-acceptances/{policy_acceptance_id}`

A future acceptance workflow, if required, must derive identity, time, request
metadata, and policy reference from server-owned context and the authoritative
policy record. B3 does not design that future workflow.

## Schemas, Services, And Internal Setup

Read schemas remain active. Existing write schemas and service primitives are
retained only because internal setup, seed, bootstrap, and tests can still use
them without preserving a public/admin write API contract.

Seed scenario scripts no longer print generic write-route request bodies. Test
helpers create policy documents and acceptances through internal service-owned
setup instead of the retired API paths.

No database models or migrations are changed.

## Frontend Compatibility

Current static/source-owned legal behavior is preserved. B3 does not change
frontend legal routes, legal text rendering, agreement presentation, or add a
policy authoring or acceptance integration.

## A2C Compatibility

B3 removes the policy/legal reason for a separate large policy-body request
class. No retained public/admin policy/legal write route accepts policy text,
arbitrary policy URLs, or fabricated acceptance evidence.

Policy/legal request surfaces therefore do not require special handling beyond
the future ordinary JSON request-body limit owned by A2C.

## API-M09 Status And Remaining Work

API-M09 remains partial. B3 closes the policy/legal request-ownership blocker,
but it does not activate the ordinary JSON body limit and does not complete
provider infrastructure, timeout, retry, rate, streaming, multipart,
header/cookie, or broader B2B/B2C request-boundary work.
