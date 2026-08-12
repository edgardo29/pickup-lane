# EN-03 - Secrets, Control Plane, And Evidence Foundation

## At A Glance

| Field | Value |
|---|---|
| Pass | `EN-03` |
| Track | WS10 early operational/provider foundation |
| Type | Operational / provider-control-plane / evidence foundation |
| Primary controls | `OPS-005`, `OPS-006`, `OPS-007`, `OPS-025` |
| Authority basis | Current accepted repository; locked OPS control findings; finalized remediation plan; FDN-01/FDN-07 and evidence decisions; master blueprint EN-03/WS10-02 |
| Depends on | GOV-01 / WS01 ownership and evidence rules |
| Trusted test/evidence scope | Mixed EN-03 repository proof: structural documentation review, source/configuration inspection, fresh trusted EN-03 tests where executable behavior requires proof, plus later external sanitized provider/runtime evidence |

## 1. Purpose

EN-03 establishes Pickup Lane's secrets, provider-control-plane, and safe-evidence foundation before later operational remediation mutates production providers or claims production readiness.

This pass reconciles the current repository with the authoritative OPS findings and the WS10 remediation blueprint. Its job is to make ownership, secret categories, provider control planes, evidence rules, and open unknowns explicit enough that later passes can verify or change real provider state without leaking secrets, personal data, private screenshots, recovery material, or unsupported claims into Git.

The accepted current implementation is already correct for EN-03's production/configuration surface. No production code or deployed-provider correction phase is required for this pass.

## 2. Why This Matters

Secrets and provider dashboards are among the highest-risk parts of production readiness. A repository can look complete while the actual production risk still lives outside the codebase: unmanaged secrets, shared admin accounts, missing MFA, unclear billing or recovery ownership, unsafe screenshots, stale access, or provider settings that nobody has verified.

EN-03 prevents that by separating three kinds of truth:

| Truth Type | EN-03 Treatment |
|---|---|
| Repository-confirmed truth | May be documented when proved by tracked source, current configuration contracts, or safe repository inspection. |
| Intended operational standard | May be documented as a required future state when authority documents require it. |
| External provider/runtime truth | Must remain explicitly unproven until supported by sanitized evidence from the provider/runtime environment. |

This distinction keeps the pass useful without overstating closure. EN-03 can establish the registers, rules, and evidence paths. It cannot prove that every provider account, role, secret store, MFA setting, recovery path, runtime injection setting, log sink, DNS zone, or backup configuration is production-ready.

## 3. Requirements

| Requirement ID | Requirement | What It Means | Why It Matters |
|---|---|---|---|
| `EN03-CTRL-001` | Provider/control-plane inventory and unresolved access gaps. | Maintain a sanitized register of known or expected production providers, ownership expectations, required evidence, and access or verification gaps. | Provider risk lives outside the repo; the team needs a visible map before mutating dashboards or claiming control closure. |
| `EN03-SECRET-001` | Secret lifecycle register without secret values. | Record secret/configuration names and categories only, with owner, consumer, storage/injection expectations, rotation, revocation, emergency response, and evidence status. | Secret values must stay out of Git while later operators still need enough structure to manage and review them safely. |
| `EN03-BOUNDARY-001` | Frontend-public configuration remains separate from backend-private credentials. | Keep browser-public values distinct from server-only credentials and preserve environment-specific handling for both. | Public client config is not automatically a breach, but private credentials in frontend bundles would be a high-impact exposure. |
| `EN03-INDEPENDENCE-001` | Inbox token signing secret is independent and does not fall back to or reuse other credentials. | Require `INBOX_TOKEN_SECRET` in production-like environments and reject reuse of database, Firebase, Stripe, R2, or placeholder values. | Token-signing compromise must not cascade from another credential or silently inherit a broader production secret. |
| `EN03-EVIDENCE-001` | Provider evidence is sanitized and metadata-bearing, and raw secrets/private evidence do not enter Git. | Define redaction, metadata, provenance, staleness, and raw-evidence handling rules before evidence is collected. | Evidence should prove controls without creating a new leak path for credentials, private provider data, personal data, or payment data. |
| `EN03-SCOPE-001` | External/provider facts remain unknown until proven and EN-03 does not falsely close later-evidence controls. | Keep provider/runtime facts open unless backed by sanitized evidence from the right source. | A local documentation pass cannot prove dashboard access, MFA, secret stores, runtime injection, DNS, monitoring, backups, or recovery posture. |

## 4. Technical Design / Contracts

### 4.1 Provider / Control-Plane Inventory

A control plane is any provider, dashboard, repository, runtime, account, console, billing surface, DNS surface, deployment system, monitoring surface, or backup surface that can affect production availability, data access, identity, payments, secrets, infrastructure, or evidence.

The EN-03 provider-control-plane register must track at least:

| Field Type | Contract |
|---|---|
| Provider/control plane | Name the provider or control surface without exposing account-private links or identifiers. |
| Purpose and environment usage | Describe why Pickup Lane uses or expects the provider, and whether the usage is repository-confirmed, intended, demo-only, unknown, not selected, or not applicable. |
| Ownership | Record the expected owner role, current interim owner where known, and backup/escalation gaps. |
| Access controls | Track evidence still needed for named accounts, admin access, billing access, least privilege, MFA, recovery, service identities, offboarding, and emergency access. |
| Production separation | Track evidence still needed for production versus non-production separation, deployment permissions, and provider-side environment boundaries. |
| Evidence status | Use explicit safe statuses such as `NOT YET EVIDENCED`, `UNKNOWN`, `NOT SELECTED`, `NOT APPLICABLE`, and `PARTIAL`. |
| Later verification | Record the pass, owner, or evidence path expected to close the gap later. |

The current provider/control-plane topology that EN-03 must account for is:

| Provider / Control Plane | EN-03 Treatment |
|---|---|
| GitHub / GitHub Actions | Repository and CI control plane; provider-side access, branch protection, secret storage, workflow permissions, and review evidence remain external until verified. |
| Vercel | Frontend hosting/deployment control plane currently documented as temporary demo infrastructure, not a permanent production-provider decision until later evidence. |
| Render | Backend hosting/deployment control plane currently documented as temporary demo infrastructure, not a permanent production-provider decision until later evidence. |
| PostgreSQL / Neon | Database/provider surface currently documented as temporary demo infrastructure, not a permanent production-provider decision until later evidence. |
| Firebase / GCP | Identity and service-account control plane; service-account evidence, IAM, MFA, recovery, key handling, and workload-identity posture remain external until verified. |
| Stripe | Payments provider control plane; dashboard access, webhook secret handling, key rotation, event retention, and role separation remain external until verified. |
| Cloudflare / R2 | Object-storage/provider control plane; access keys, bucket policy, CORS, signed URL posture, rotation, and provider access remain external until verified. |
| DNS / TLS | Domain and certificate control plane; registrar, DNS authority, TLS ownership, recovery, and emergency access remain external until verified. |
| Monitoring / logging provider | Not selected or not yet evidenced; later monitoring pass must prove selection and controls if a provider is adopted. |

The provider-control-plane register and provider-evidence checklist together serve as the EN-03 unresolved provider-access log. They must make gaps visible instead of converting unknowns into implicit acceptance.

### 4.2 Public Versus Private Configuration Boundary

EN-03 preserves a strict boundary between frontend-public configuration and backend-private credentials.

| Category | Examples | Contract |
|---|---|---|
| Browser-public configuration | Firebase web configuration, Stripe publishable key, public API base URL, frontend feature flags using `VITE_` names | May be delivered to the browser, but remains environment-bound configuration and must not be confused with proof of provider security. |
| Backend-private credentials | Database URL, Firebase Admin credentials, Stripe secret key, Stripe webhook secret, R2 access key ID, R2 secret access key, inbox token signing secret | Must remain server-side only and must not appear in frontend bundles, tracked secret files, documentation values, screenshots, logs, tickets, or shared files. |
| Sensitive non-secret configuration | CORS origins, bucket names, provider endpoint names, docs/health flags, signed URL expiration policy | May not be credential material by itself, but still needs controlled ownership, environment separation, and safe disclosure rules. |
| Local/test configuration | Local development examples, synthetic CI database settings, test-only placeholders | Must remain clearly non-production and must not become proof of production secret handling. |

Current repository safeguards that support this boundary include ignored local environment files, example placeholders, backend settings that centralize private runtime configuration, browser-facing `VITE_` configuration names, and EN-02 redaction principles. These safeguards are repository evidence only; deployed bundle and runtime-provider evidence remain later work.

### 4.3 Secret Lifecycle

The secret-lifecycle register records names and categories only. It must never record secret values, private keys, tokens, recovery codes, raw credential-bearing commands, or provider-private exports.

Each secret or sensitive configuration class should record:

| Lifecycle Field | Contract |
|---|---|
| Classification | Private credential, public configuration, sensitive configuration, or local/test configuration. |
| Owner / consumer | The role or subsystem responsible for the value and the application component that consumes it. |
| Storage / injection expectation | The intended controlled storage and runtime-injection model, such as managed provider secret storage or equivalent controlled deployment injection. |
| Environment separation | Whether production, preview, staging, local, and CI values must be distinct. |
| Rotation triggers | Events that require rotation, including suspected compromise, role change, employee/vendor offboarding, provider incident, accidental exposure, or scheduled review. |
| Revocation effects | What application capability is affected when the value is revoked. |
| Emergency response | The safe response path when compromise is suspected. |
| Evidence status | Whether current repository evidence, provider evidence, runtime evidence, and owner review are complete, partial, unknown, or pending. |

The authoritative future-state preference is managed secret storage, controlled runtime injection, and short-lived workload identity/OIDC where supported. EN-03 records that expectation but does not prove provider-side implementation.

### 4.4 Secret Independence

The inbox token signing secret is a distinct private credential. It must not be missing in production-like environments, must not fall back to another credential, and must not reuse high-risk credential values.

The accepted current backend settings contract enforces that production-like environments require `INBOX_TOKEN_SECRET` and reject equality with:

| Disallowed Reuse |
|---|
| `DATABASE_URL` |
| `FIREBASE_ADMIN_CREDENTIALS_JSON` |
| `FIREBASE_ADMIN_CREDENTIALS` |
| `STRIPE_SECRET_KEY` |
| `STRIPE_WEBHOOK_SECRET` |
| `R2_ACCESS_KEY_ID` |
| `R2_SECRET_ACCESS_KEY` |

Production-like settings also reject documented placeholder values for the inbox token signing secret.

This repository contract closes the obsolete secret-reuse design risk in accepted source. It does not prove deployed secret-store configuration, provider-side access controls, rotation, revocation, or emergency procedures.

### 4.5 Provider Evidence Handling

Provider evidence must be safe before it enters the repository.

| Evidence Rule | Contract |
|---|---|
| Raw evidence | Raw screenshots, exports, provider dashboard captures, account lists, billing pages, secret-store screens, logs, recovery material, and private support records do not belong in Git. |
| Sanitized evidence | Repository evidence must remove secret values, tokens, private keys, credentials, account-private URLs, personal data, customer data, payment data, provider identifiers that are not safe to disclose, and recovery material. |
| Required metadata | Sanitized evidence must identify provider/control plane, environment, evidence date, reviewer, purpose, mapped control, mapped pass, source type, evidence reference, and unresolved gaps. |
| Traceability | Evidence must map back to a requirement/control without turning the evidence file into an unsupported closure claim. |
| Staleness | Provider evidence expires or is replaced when the relevant provider, secret, role, account, deployment environment, or control process changes. |

EN-02 redaction and privacy principles inform EN-03's safe-evidence rules. They do not automatically sanitize external provider material; human/provider review remains required before any evidence artifact is added.

### 4.6 External Unknowns

EN-03 must keep the following categories open until separately proven:

| Unknown Category | Examples |
|---|---|
| Provider access | Actual admin users, MFA posture, role assignments, least privilege, billing access, emergency access, recovery ownership, offboarding status. |
| Secret storage / lifecycle | Provider-side secret-store configuration, runtime injection, production/preview separation, rotation cadence, revocation procedure, overlap strategy, incident response. |
| Environment and deployment | Production versus demo provider decisions, deploy permissions, CI/CD secret exposure, branch/deployment gating, runtime configuration drift. |
| Runtime/provider logs | Whether secrets or sensitive metadata appear in provider logs, webhooks, build logs, deploy output, function logs, observability sinks, or support exports. |
| DNS, TLS, monitoring, backups | Registrar ownership, DNS authority, certificate management, monitoring provider selection, alerting access, backup ownership, restore proof, and safe evidence. |

Unknown does not mean failed implementation inside this pass. It means EN-03 must leave a clear, auditable gap for the later owner to verify.

### 4.7 Ownership / Later Verification

FDN-01 currently assigns the project owner as the interim owner for production readiness and related evidence until roles are delegated. EN-03 uses that ownership model without pretending that permanent backup, escalation, or provider-specific ownership is complete.

Later passes consume EN-03 as follows:

| Later Area | Expected Use Of EN-03 |
|---|---|
| WS02 deployment/configuration | Uses secret names, public/private boundaries, and provider evidence rules when proving deployed runtime configuration. |
| WS03 identity/Firebase | Uses Firebase/GCP control-plane gaps and IAM-011 service-account evidence expectations. |
| WS04 database/provider operations | Uses database/provider ownership, access, backup, recovery, and secret lifecycle expectations. |
| WS05 payments/Stripe | Uses Stripe dashboard, key, webhook, evidence, and role-separation expectations. |
| WS06 storage/R2 | Uses R2 credential, bucket, CORS, signed URL, provider access, and rotation expectations. |
| WS08 CI/release | Uses repository, CI permissions, secret exposure, workflow evidence, and release-gating expectations. |
| WS09 observability | Uses monitoring/logging provider selection and safe log/evidence expectations. |
| WS10 provider verification | Completes provider-dashboard verification, access review, managed secret storage proof, rotation/revocation, recovery, offboarding, and break-glass evidence. |

## 5. Implementation Scope

EN-03 owns the canonical plan and foundational governance artifacts needed to support later secrets/control-plane work:

| Artifact | EN-03 Role |
|---|---|
| `docs/production-readiness/planning/en-03-secrets-control-plane-evidence-foundation.md` | Canonical EN-03 planning document and authority reconciliation. |
| `docs/production-readiness/governance/provider-control-plane-register.md` | Sanitized provider/control-plane inventory and unresolved provider-access log. |
| `docs/production-readiness/governance/secret-lifecycle-register.md` | Sanitized secret/configuration category and lifecycle register. |
| `docs/production-readiness/governance/provider-evidence-handling-standard.md` | Safe evidence handling, redaction, metadata, traceability, and staleness rules. |
| `docs/production-readiness/governance/provider-evidence-checklist.md` | Reusable provider-evidence checklist for later dashboard/runtime verification. |

The current repository already contains the required EN-03 foundational artifacts and accepted source-level secret-independence behavior. This canonical plan update aligns EN-03 with that current truth.

This pass may verify repository-owned facts such as ignored local secret files, placeholder-only examples, public/private configuration naming, backend settings validation, and sanitized documentation. It does not mutate provider dashboards, deploy configuration, secrets, roles, DNS, certificates, monitoring, backups, or payment settings.

## 6. Testing And Evidence

EN-03 evidence is intentionally mixed. Some requirements are proved by repository inspection or documentation review, executable behavior receives fresh trusted EN-03 tests where that is the correct proof layer, and external provider/runtime facts require later sanitized provider evidence that cannot be replaced by local tests.

| Requirement ID | Repository Evidence | Later External Evidence |
|---|---|---|
| `EN03-CTRL-001` | Review the provider-control-plane register and provider-evidence checklist for required providers, statuses, owners, evidence fields, and unresolved gaps. | Sanitized provider dashboard/access evidence for each selected production control plane. |
| `EN03-SECRET-001` | Review the secret-lifecycle register for name-only entries, classifications, lifecycle fields, and absence of secret values. | Sanitized provider/runtime evidence for managed storage, injection, owner review, rotation, revocation, and emergency handling. |
| `EN03-BOUNDARY-001` | Inspect source/configuration naming and imports to confirm public browser configuration remains separate from backend private credentials. Add fresh trusted EN-03 tests where executable settings/boundary behavior needs proof. | Bundle/runtime/deployment evidence that private backend credentials are not exposed to frontend artifacts or provider logs. |
| `EN03-INDEPENDENCE-001` | Inspect accepted backend settings behavior and, during the EN-03 testing/evidence phase, run trusted settings tests that prove production-like `INBOX_TOKEN_SECRET` independence and placeholder rejection where required. | Deployed secret-store and runtime evidence that the inbox token secret is independently configured and operationally rotated/revoked. |
| `EN03-EVIDENCE-001` | Review the evidence-handling standard/checklist and run repository safety checks against changed artifacts. | Sanitized provider evidence review with raw evidence retained only in approved access-controlled storage outside Git. |
| `EN03-SCOPE-001` | Review the canonical plan, registers, and diff to confirm unknown external facts are not falsely marked closed. | Later pass evidence packages that explicitly close the remaining provider/runtime gaps. |

Fresh trusted tests created during the EN-03 testing/evidence phase must follow the EN-01 architecture and test only current accepted application behavior. Historical or excluded test areas cannot be used as EN-03 authority.

EN-03 requirement declarations and testing/risk documentation must be created during the EN-03 testing/evidence phase where required by the EN-01 testing architecture and final evidence design. They should reflect the appropriate proof for each requirement rather than forcing every EN-03 requirement into pytest.

## 7. Integration / Operational Expectations

The EN-03 artifacts become operating inputs for later production-readiness work:

| Consumer | Expected Integration |
|---|---|
| Product/domain owners | Use owner fields and open gaps to decide who must approve provider evidence and secret lifecycle choices. |
| Engineering implementation passes | Use public/private boundaries and secret names when changing settings, tests, deployments, or runtime configuration. |
| Security/operations review | Use the provider register, secret register, and evidence standard to request and evaluate provider screenshots, exports, role reviews, and runtime proof safely. |
| PR/release review | Confirm diffs do not introduce secret values, raw evidence, private provider data, or unsupported production-readiness closure claims. |

Operationally, EN-03 keeps a conservative default: a provider fact is not accepted until it has current, sanitized, traceable evidence from the right source.

## 8. Not Part Of This Pass

EN-03 does not include:

| Area | Out Of Scope |
|---|---|
| Provider/account changes | Mutating provider dashboards, creating/removing accounts, changing roles, enabling MFA, changing DNS/TLS, selecting a monitoring provider, changing backups, or modifying billing/recovery access. |
| Secret operations | Rotating production secrets, revoking secrets, proving provider-side managed secret storage, configuring deployed injection, exercising offboarding, or establishing break-glass access. |
| Raw evidence collection | Committing raw screenshots, exports, account lists, recovery codes, provider-private links, real user data, payment data, secrets, or logs to Git. |
| Application behavior | Changing product behavior, broad logging, metrics, tracing, dashboards, provider observability, release gating, or user-facing flows. |
| Release enforcement / control closure | Adding CI secret-scanning enforcement owned by later passes or producing broad OPS control-closure reports. |

## 9. Related Controls And Remaining Evidence

| Control | EN-03 Contribution | Remaining Evidence / Later Work |
|---|---|---|
| `OPS-005` | Establishes a provider/control-plane register, expected ownership fields, and unresolved access/evidence gaps. | Provider dashboard evidence for named accounts, MFA, least privilege, billing/admin access, recovery ownership, emergency access, and offboarding. |
| `OPS-006` | Documents managed-secret-storage and runtime-injection expectations, repository hygiene boundaries, and accepted source-level settings safeguards. | Provider/runtime proof that production secrets are stored and injected safely, excluded from frontend bundles, build layers, logs, tickets, shared files, and screenshots. |
| `OPS-007` | Establishes a name-only secret lifecycle register with categories, owners, consumers, rotation/revocation expectations, emergency response, and evidence status. | Actual provider/runtime evidence for secret owners, storage location, rotation/revocation procedure, overlap handling, compromise response, offboarding, and short-lived identity/OIDC where supported. |
| `OPS-025` | Establishes a provider-evidence standard and checklist that define sanitized evidence, metadata, traceability, redaction, and open gaps. | Provider-dashboard verification across hosting, Firebase/GCP, Stripe, Cloudflare/R2, PostgreSQL, DNS, repository, monitoring, and backups. |

Supporting relationships:

| Related Authority | Relationship |
|---|---|
| GOV-004 / FDN-01 | EN-03 uses the interim ownership model and keeps backup/escalation gaps visible until delegated and evidenced. |
| IAM-011 | Firebase/GCP service-account and workload-identity evidence remains a later provider-evidence requirement. |
| EN-02 / FDN-07 | Redaction and privacy principles inform safe evidence handling and secret-safe documentation. |

EN-03 completion does not mean these controls are fully closed. It means the repository has the safe structure required for later verification and closure work.

## 10. Completion Criteria

EN-03 is complete when its repository-owned requirements, required fresh tests/evidence, and final whole-pass review are complete:

| Criterion | Required Outcome |
|---|---|
| Canonical plan | This planning document matches the current accepted repository and authoritative EN-03/WS10 scope. |
| Requirement coverage | All six EN-03 requirements are accounted for with clear repository and later-evidence expectations. |
| Governance artifacts | Required provider-control-plane, secret-lifecycle, provider-evidence-standard, and provider-evidence-checklist artifacts exist, remain complete for EN-03, and remain sanitized. |
| Secret independence | Accepted source-level `INBOX_TOKEN_SECRET` independence behavior is represented correctly. |
| Fresh trusted tests / evidence | Fresh trusted EN-03 tests pass where executable behavior needs test proof, and structural/document/evidence checks pass for non-executable requirements. |
| Traceability / testing records | Required EN-01 traceability, requirement declarations, and testing/risk documentation exist and pass where applicable. |
| Evidence safety | EN-03 artifacts contain no secret values, tokens, private keys, credential-bearing commands, private provider evidence, unnecessary personal data, payment data, or unsupported closure claims. |
| Fact separation | Repository-owned facts and external provider/runtime unknowns remain clearly separated. |
| Scope discipline | No provider dashboard, secret, deployment, CI, production config, unrelated application behavior, or later-pass work is claimed as completed by EN-03. |
| Final whole-pass review | Documentation, existing behavior, tests/evidence, and scope boundaries agree, and no unresolved EN-03 blocker remains. |

When these criteria are met, EN-03's repository-owned requirements and evidence are complete and reviewed. Later external provider/runtime verification remains separate, and broader `OPS-005`, `OPS-006`, `OPS-007`, and `OPS-025` control closure still depends on those external evidence passes.
