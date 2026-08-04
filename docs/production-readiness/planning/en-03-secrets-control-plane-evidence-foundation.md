# EN-03 Secrets, Control Plane, And Evidence Foundation

Pass: EN-03.

Track: WS10 early operational/provider foundation.

Primary controls: OPS-005, OPS-006, OPS-007, OPS-025.

Baseline: `122dedc435021b9946e8a181dd58a82ed916e925`.

Branch: `pr/EN-03`.

## Purpose And Scope

EN-03 creates sanitized documentation and registers for provider control planes, secret lifecycle expectations, and provider-evidence handling. It records what the repository proves, what remains unknown, and which later passes must collect provider evidence.

EN-03 does not mutate provider accounts, rotate secrets, configure MFA, change application behavior, add a secret scanner, alter CI, inspect ignored local env files, or prove provider-dashboard configuration.

## Documents Added

- [Provider control-plane register](../governance/provider-control-plane-register.md)
- [Secret lifecycle register](../governance/secret-lifecycle-register.md)
- [Provider evidence handling standard](../governance/provider-evidence-handling-standard.md)
- [Provider evidence checklist](../governance/provider-evidence-checklist.md)

## Inspected Provider Topology

Repository evidence identifies these providers or control planes:

- GitHub and GitHub Actions for source control, pull requests, CI, and repository governance.
- Vercel as the intended frontend hosting provider.
- Render as the intended backend API hosting provider.
- PostgreSQL/Neon as the intended durable database provider.
- Firebase/GCP for browser Firebase configuration and backend Firebase Admin operations.
- Stripe for payments, saved cards, webhooks, refunds, and financial provider events.
- Cloudflare/R2 for private object storage and signed URL workflows.
- DNS and TLS as external public-entry-point controls.
- Monitoring/logging provider as not yet selected in repository evidence.

No external email or SMS provider was found in repository-owned provider configuration. Application inbox and notification behavior remains application-owned until a later pass selects an external delivery provider.

## Frontend-Public Versus Backend-Private Boundary

Frontend-public configuration may enter browser bundles only when it is intentionally public and environment-specific. Browser-public Firebase configuration, Stripe publishable keys, frontend payment feature flags, and the frontend API base URL remain distinct from backend private credentials.

Backend-private credentials include database credentials, Firebase Admin credentials, Stripe secret keys, Stripe webhook signing secrets, R2 access credentials, and the inbox token signing secret. These values must remain server-side or provider-side only.

Public URLs are not signed/private URLs. Configuration values are not automatically credentials, but sensitive configuration such as CORS origins, provider bucket names, endpoint names, API docs exposure, health exposure, and signed URL lifetimes still requires review.

## Current Repository Safeguards

Repository-visible safeguards include:

- ignored local env files and Firebase Admin JSON key patterns
- environment examples instead of committed local env files
- frontend use of `VITE_` names for browser configuration
- backend environment loading for private provider credentials
- EN-01 test database and network isolation controls
- EN-02 redaction principles and tests for sensitive observable text
- GitHub Actions configured with read-only repository content permission for CI

These safeguards are partial. They do not prove managed production secret storage, provider-side access control, MFA, recovery, rotation, revocation, offboarding, provider dashboard state, or deployment environment separation.

## Current Unknown Provider Facts

The following facts remain unknown until later owner-supplied provider evidence exists:

- named provider users and administrators
- billing owners where applicable
- MFA status
- recovery methods and backup owners
- emergency access
- least-privilege role assignments
- service-account, token, key, OIDC, or integration scope
- production/development/test separation
- deployed secret-storage and runtime-injection method
- credential rotation and revocation history
- offboarding process and evidence
- provider audit/activity logs
- DNS, TLS, domain-lock, certificate-renewal, and CDN ownership
- monitoring/logging provider selection, retention, alert routing, and access control

Unknowns are recorded as unknowns. EN-03 does not guess or close them.

## Provider Ownership Model

The approved GOV-01 ownership model remains in force: the project owner is the interim accountable owner for all separate production role hats until reassigned. Provider control-plane evidence is owned by the secrets and provider access role, with domain-specific collaboration from platform/deployment, database, identity/security, payments, storage, frontend platform, quality/release assurance, observability/reliability, and incident response roles.

Backup and escalation coverage remains unassigned until a later approved record changes it. Solo interim ownership is not complete production resilience.

## Secret Lifecycle Expectations

Secret categories must have:

- canonical environment-variable names
- provider/system ownership
- consumer classification
- public/private/sensitive classification
- expected storage or injection location
- environment-separation requirements
- rotation triggers
- revocation effects
- suspected-compromise responses
- offboarding dependencies
- evidence status
- later verification ownership

The EN-03 [secret lifecycle register](../governance/secret-lifecycle-register.md) records names and lifecycle expectations only. It contains no values.

## Evidence-Handling Rules

Provider evidence must be sanitized before repository use. Raw screenshots, raw exports, provider payloads, key files, billing pages, local env files, private dashboard links, recovery codes, signed URLs, credentials, and private user/customer data must not be committed.

Sanitized evidence records must include provider, environment, collection date, reviewer, purpose, supported control or pass, source type, evidence reference, and open gaps. Raw evidence storage and retention remain unresolved until a later owner-approved decision selects an access-controlled location and retention period.

The EN-03 [provider evidence handling standard](../governance/provider-evidence-handling-standard.md) references EN-02 redaction principles, but EN-03 does not require screenshots or exports to be processed automatically by EN-02 code.

## INBOX_TOKEN_SECRET Fallback Risk

Repository source references `INBOX_TOKEN_SECRET` for inbox token signing. If that variable is unset, the current implementation falls back to `DATABASE_URL`.

EN-03 records this as a risk because the inbox token signing secret must be independent from database credentials and any other provider credential. EN-03 does not modify the fallback behavior. Correction belongs to WS02-01 typed settings and environment isolation, followed by WS10 rotation and revocation verification.

## Control Mapping After EN-03

| Control | EN-03 result | Status after EN-03 | Remaining evidence required |
|---|---|---|---|
| OPS-005 | Provider/control-plane register and reusable checklist created. | PARTIAL. Account, MFA, recovery, least privilege, emergency access, and offboarding evidence remain external. | Sanitized provider access review evidence for GitHub, Vercel, Render, PostgreSQL/Neon, Firebase/GCP, Stripe, Cloudflare/R2, DNS/TLS, monitoring/logging, and backups. |
| OPS-006 | Secret storage and injection expectations documented by category. | PARTIAL. Repository hygiene and env loading exist, but managed production secret storage and runtime injection are not evidenced. | Provider/runtime secret-store evidence, production env separation proof, access controls, and image/bundle/log checks in later passes. |
| OPS-007 | Secret-name and lifecycle register created without values. | PARTIAL. EN-03 creates the first lifecycle register, but actual owners, storage, rotation, revocation, emergency response, and short-lived identity decisions need provider/process proof. | Rotation/revocation procedures, key inventory, offboarding evidence, emergency response evidence, and workload identity decisions. |
| OPS-025 | Evidence handling standard and checklist created. | EXTERNAL EVIDENCE REQUIRED. EN-03 defines safe evidence handling but does not verify provider dashboards. | Sanitized dashboard/configuration evidence across hosting, Firebase/GCP, Stripe, Cloudflare/R2, PostgreSQL, DNS, repository, monitoring, and backups. |

No externally evidenced control is closed by EN-03.

## Deferred Work

Later WS10 provider verification and mutation work must collect provider account evidence, configure or verify MFA, confirm least privilege, review service identities, test recovery access, rotate and revoke credentials, validate offboarding, exercise emergency procedures, and preserve dated sanitized evidence.

Later WS08 work may add secret scanning, CI enforcement, frontend bundle checks, artifact handling enforcement, and checker integration if those controls are approved for that pass.

Later WS02 typed-settings work must correct the `INBOX_TOKEN_SECRET` fallback, enforce environment-specific settings, reject unsafe production defaults, and prove runtime environment separation.

## Non-Closure Statement

EN-03 is a foundation pass. It organizes provider, secret, and evidence expectations so later passes can collect evidence safely. It does not prove production provider-dashboard configuration, production secret storage, deployed runtime behavior, account access, MFA, recovery, rotation, revocation, offboarding, monitoring, backups, DNS, or TLS readiness.
