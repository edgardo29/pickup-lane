# Provider Evidence Checklist

Pass: EN-03.

Primary controls: OPS-005, OPS-006, OPS-007, OPS-025.

Owner role: Secrets and provider access owner, held by Project owner (interim) until reassigned under the approved ownership model.

This checklist is reusable for future provider verification. It contains no real account information and is not proof that provider evidence has been collected.

## Checklist Fields

Each provider evidence record must complete these fields with sanitized values only:

| Field | Required content |
|---|---|
| Provider | Provider or control-plane name. |
| Environment | Production, preview, development, CI, test, or shared, as applicable. |
| Accountable owner | Role hat or approved owner, not a personal account unless approved for repository exposure. |
| Administrator | Sanitized administrator role or external evidence reference. |
| Billing owner | Sanitized billing-owner status or external evidence reference. |
| MFA | Evidence status and sanitized reference. |
| Recovery method | Evidence status and sanitized reference. |
| Backup owner | Evidence status and sanitized reference. |
| Least-privilege roles | Sanitized role summary and open gaps. |
| Service identities | Sanitized service-account, token, key, OIDC, or integration summary. |
| Secret storage location | Sanitized location class, not secret values. |
| Environment separation | Production/development/test separation evidence status. |
| Last credential rotation | Date or sanitized evidence reference, if approved for repository exposure. |
| Revocation procedure | Sanitized procedure or open gap. |
| Offboarding procedure | Sanitized procedure or open gap. |
| Emergency access | Sanitized emergency access status and recovery owner. |
| Audit/activity logs | Sanitized evidence that activity logs exist and are reviewable. |
| Sanitized evidence reference | Repository-safe summary or pointer to approved external evidence. |
| Evidence date | Date evidence was collected or reviewed. |
| Reviewer | Role or approved reviewer alias. |
| Open gaps | Remaining unknowns or missing proof. |
| Later action | Pass or owner responsible for closure. |

## Provider Records To Complete

| Provider | Environment | Accountable owner | Administrator | Billing owner | MFA | Recovery method | Backup owner | Least-privilege roles | Service identities | Secret storage location | Environment separation | Last credential rotation | Revocation procedure | Offboarding procedure | Emergency access | Audit/activity logs | Sanitized evidence reference | Evidence date | Reviewer | Open gaps | Later action |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GitHub and GitHub Actions | Development, CI, release governance | Project owner (interim) | NOT YET EVIDENCED | UNKNOWN | NOT YET EVIDENCED | NOT YET EVIDENCED | UNASSIGNED | PARTIAL; workflow permissions visible, repository roles not evidenced | PARTIAL; Actions identity exists, OIDC/secrets not evidenced | NOT YET EVIDENCED | PARTIAL; branch and workflow policy require provider evidence | NOT YET EVIDENCED | NOT YET EVIDENCED | NOT YET EVIDENCED | UNKNOWN | NOT YET EVIDENCED | None yet | NOT YET EVIDENCED | Project owner role | Branch protection, required checks, admin list, secrets, MFA, recovery, logs | WS10 provider verification |
| Vercel | Frontend deployments | Project owner (interim) | NOT YET EVIDENCED | UNKNOWN | NOT YET EVIDENCED | NOT YET EVIDENCED | UNASSIGNED | NOT YET EVIDENCED | UNKNOWN | NOT YET EVIDENCED | NOT YET EVIDENCED | NOT YET EVIDENCED | NOT YET EVIDENCED | NOT YET EVIDENCED | UNKNOWN | NOT YET EVIDENCED | None yet | NOT YET EVIDENCED | Project owner role | Project access, env scopes, domain/TLS, deploy history, preview policy | WS02 and WS10 |
| Render | Backend API deployments | Project owner (interim) | NOT YET EVIDENCED | UNKNOWN | NOT YET EVIDENCED | NOT YET EVIDENCED | UNASSIGNED | NOT YET EVIDENCED | UNKNOWN | NOT YET EVIDENCED | NOT YET EVIDENCED | NOT YET EVIDENCED | NOT YET EVIDENCED | NOT YET EVIDENCED | UNKNOWN | NOT YET EVIDENCED | None yet | NOT YET EVIDENCED | Project owner role | Service settings, runtime env, deploy roles, logs, health checks | WS02 and WS10 |
| PostgreSQL/Neon | Database | Project owner (interim) | NOT YET EVIDENCED | UNKNOWN | NOT YET EVIDENCED | NOT YET EVIDENCED | UNASSIGNED | NOT YET EVIDENCED | UNKNOWN | NOT YET EVIDENCED | PARTIAL; EN-01 test DB guard exists, deployed separation missing | NOT YET EVIDENCED | NOT YET EVIDENCED | NOT YET EVIDENCED | UNKNOWN | NOT YET EVIDENCED | None yet | NOT YET EVIDENCED | Project owner role | Roles, grants, backups, PITR, app/migration credentials, activity logs | WS04 and WS10 |
| Firebase/GCP | Authentication and Admin SDK | Project owner (interim) | NOT YET EVIDENCED | UNKNOWN | NOT YET EVIDENCED | NOT YET EVIDENCED | UNASSIGNED | NOT YET EVIDENCED | PARTIAL; Admin SDK credentials referenced, scope not evidenced | NOT YET EVIDENCED | NOT YET EVIDENCED | NOT YET EVIDENCED | NOT YET EVIDENCED | NOT YET EVIDENCED | UNKNOWN | NOT YET EVIDENCED | None yet | NOT YET EVIDENCED | Project owner role | Project binding, IAM, service-account keys, auth settings, App Check decision | WS03 and WS10 |
| Stripe | Payments and webhooks | Project owner (interim) | NOT YET EVIDENCED | UNKNOWN | NOT YET EVIDENCED | NOT YET EVIDENCED | UNASSIGNED | NOT YET EVIDENCED | PARTIAL; key names referenced, scope not evidenced | NOT YET EVIDENCED | NOT YET EVIDENCED | NOT YET EVIDENCED | NOT YET EVIDENCED | NOT YET EVIDENCED | UNKNOWN | NOT YET EVIDENCED | None yet | NOT YET EVIDENCED | Project owner role | Test/live mode, dashboard roles, webhook endpoint, alerts, event delivery | WS05 and WS10 |
| Cloudflare/R2 | Object storage | Project owner (interim) | NOT YET EVIDENCED | UNKNOWN | NOT YET EVIDENCED | NOT YET EVIDENCED | UNASSIGNED | NOT YET EVIDENCED | PARTIAL; access key names referenced, token scope not evidenced | NOT YET EVIDENCED | NOT YET EVIDENCED | NOT YET EVIDENCED | NOT YET EVIDENCED | NOT YET EVIDENCED | UNKNOWN | NOT YET EVIDENCED | None yet | NOT YET EVIDENCED | Project owner role | Bucket privacy, token scope, CORS, lifecycle, logging, recovery | WS06 and WS10 |
| DNS and TLS | Domains, records, certificates, canonical host | Project owner (interim) | NOT YET EVIDENCED | UNKNOWN | NOT YET EVIDENCED | NOT YET EVIDENCED | UNASSIGNED | NOT YET EVIDENCED | UNKNOWN | NOT APPLICABLE | NOT YET EVIDENCED | NOT APPLICABLE | NOT YET EVIDENCED | NOT YET EVIDENCED | UNKNOWN | NOT YET EVIDENCED | None yet | NOT YET EVIDENCED | Project owner role | Registrar, DNS records, TLS renewal, domain lock, CDN/edge ownership | WS02 and WS10 |
| Monitoring/logging provider | Logs, metrics, dashboards, alerts | Project owner (interim) | NOT SELECTED | NOT SELECTED | NOT SELECTED | NOT SELECTED | UNASSIGNED | NOT SELECTED | NOT SELECTED | NOT SELECTED | NOT SELECTED | NOT SELECTED | NOT SELECTED | NOT SELECTED | NOT SELECTED | NOT SELECTED | None yet | NOT SELECTED | Project owner role | Provider selection, access model, retention, alert routing, redaction controls | WS09 and WS10 |

## Completion Rule

A row is not complete until sanitized evidence supports every required field or an approved exception records the remaining gap. Unknowns must remain visible until a later verification pass closes them.
