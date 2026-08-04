# Pickup Lane Approved Foundation Decisions

## Decision record metadata

| Field | Value |
|---|---|
| Status | APPROVED AND LOCKED |
| Approval date | August 3, 2026 |
| Approved by | Project owner |
| Applies to | WS01 governance foundation, WS02 production foundation, early WS08 test-harness work, and early WS09 telemetry-contract work |
| Implementation performed | None |
| Change rule | A later change requires a new superseding decision record. The original decision remains preserved. |

## Approved decisions

### FDN-01: Interim production ownership

**Related control:** GOV-004  
**Decision:** The project owner serves as the interim accountable owner for all distinct production role hats until responsibilities are reassigned.

The ownership register must keep these roles separate even when one person holds them:

- production-readiness program
- platform and deployment
- API
- identity and application security
- database
- payments and finance operations
- durable jobs
- storage and R2
- frontend platform
- quality and release assurance
- observability and reliability
- secrets and provider access
- incident response and recovery
- privacy and retention

**Constraint:** Backup and escalation coverage may remain unassigned during development, but it must be explicitly recorded and cannot be represented as complete production coverage.

### FDN-02: Security-header ownership

**Related control:** API-M08  
**Decision:** Use split ownership by response class with a documented source of truth.

| Surface | Primary ownership |
|---|---|
| Frontend HTML and static assets | Frontend hosting edge and frontend configuration |
| API JSON responses | FastAPI application, with hosting-edge enforcement where appropriate |
| HTTPS redirect, TLS, and HSTS | Public edge or hosting provider |
| Interactive API documentation | API application plus hosting access policy |
| Header conflicts and precedence | Platform and deployment owner |

**Constraint:** This decision does not approve exact header values. Values require response-class analysis and staging verification.

### FDN-03: OpenAPI, documentation, compatibility, and deprecation

**Related control:** API-M18  
**Decision:**

1. Interactive documentation is enabled in local development and controlled test environments.
2. Production interactive documentation and raw schema exposure are disabled or access-restricted by default.
3. The generated OpenAPI schema remains part of CI validation and endpoint inventory.
4. Authorization protects every endpoint regardless of documentation exposure.
5. Pickup Lane remains an internal web-application API at the current product stage.
6. Frontend and backend changes preserve rolling-deployment compatibility.
7. Breaking contract changes require a compatibility plan, deprecation record, and coordinated deployment.
8. Explicit public API versioning is introduced before independent external clients are supported.

### FDN-04: Basis for limits and thresholds

**Related control:** GOV-006  
**Decision:** Approve an evidence-based selection method now. Do not invent numeric values.

Every limit decision must record:

- protected resource or failure mode
- all enforcing layers
- accountable owner
- provider and platform constraints
- expected workload and abuse risk
- failure cost and recovery behavior
- whether the value is configurable
- boundary and multi-instance tests
- telemetry and alerts
- rollback or safe-adjustment behavior
- reassessment triggers

This applies to request size, headers, URLs, pagination, timeouts, connection pools, rate limits, retries, worker concurrency, retention, RPO/RTO, alert thresholds, and capacity budgets.

### FDN-05: Test retries, flaky tests, artifacts, and coverage

**Related control:** TST-011  
**Decision:**

- Retries are diagnostic aids and cannot silently hide a recurring failure.
- Deterministic unit, service, API, database, and concurrency tests do not depend on retries for success.
- A diagnostic retry is allowed only when the first failure remains visible and gate behavior is explicit.
- A flaky test requires an owner, defect reference, reason, containment, and expiry or review condition.
- Quarantine cannot remove critical-workflow coverage without an approved replacement.
- Failure artifacts must be useful, sanitized, access-controlled, and free of secrets or sensitive user, message, and payment data.
- Coverage is risk-based, not governed by one universal percentage.
- Recurring failures require root-cause work.

Artifact retention duration remains a later value selected under FDN-04.

### FDN-06: Release artifact identity and provenance

**Related control:** TST-017  
**Decision:** Use immutable source and actual deployment or artifact identities, preserving the release evidence chain.

Required release evidence includes:

- immutable source revision
- frontend deployment or artifact identifier
- backend deployment, image, or artifact identifier
- dependency lockfile identity
- migration head or schema compatibility reference
- environment
- release timestamp
- CI result set
- approval record
- provider deployment linkage
- prior rollback artifact identity

**Direction:**

- Generate an SBOM for release artifacts.
- Preserve provenance metadata where the selected build platform supports it.
- Adopt signing when the chosen artifact distribution model can verify signatures meaningfully.
- Do not claim a signing or provenance level before it is actually verifiable.

### FDN-07: Correlation, telemetry labels, privacy, and tracing

**Related control:** OPS-010  
**Decision:** Structured correlation is mandatory now. Full distributed tracing remains a later risk-based decision.

| Activity | Required correlation |
|---|---|
| HTTP request | Request identifier propagated through API logs and safe error responses |
| Durable job | Stable job ID, attempt ID, and originating request or event reference where applicable |
| Payment workflow | Internal payment, booking, refund, credit, or money-issue IDs plus redacted provider identifiers |
| Storage workflow | Internal image/object record ID, job ID, and non-sensitive object reference |
| Admin action | Admin action or audit record ID plus request correlation |
| Release context | Environment and immutable release identity |

Privacy and cardinality rules:

- Never place raw tokens, passwords, private keys, full signed URLs, private-message bodies, card data, or unnecessary personal data in logs, metrics, traces, or labels.
- Email addresses, names, phone numbers, and free text are not metric labels.
- Metric labels use bounded values such as route template, outcome class, provider, job type, and stable error code.
- Provider identifiers appear only where operationally necessary and remain access-controlled and appropriately redacted.
- Full distributed tracing may be adopted later if structured correlation is insufficient.

## Approval effect

These decisions unlock:

1. WS01 governance-document implementation.
2. WS02 production configuration and deployment design.
3. Early WS08 test taxonomy and harness decisions.
4. Early WS09 correlation and telemetry contract design.

They do not close any audit control by themselves. Closure still requires the repository, test, runtime, provider, deployment, and operational evidence listed in the finalized remediation plan.
