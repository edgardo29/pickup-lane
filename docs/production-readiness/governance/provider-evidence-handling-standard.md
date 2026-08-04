# Provider Evidence Handling Standard

Pass: EN-03.

Primary control: OPS-025.

Owner role: Secrets and provider access owner, held by Project owner (interim) until reassigned under the approved ownership model.

This standard defines how Pickup Lane collects, sanitizes, reviews, references, and stores provider evidence for production-readiness work. It is a process record only. It does not require provider access, create provider evidence, or close provider-dashboard controls.

## Allowed Evidence Types

Allowed evidence may include sanitized:

- provider screenshots
- exported role or member lists
- CI output
- deployment records
- terminal output
- configuration screenshots
- rotation and revocation evidence
- incident and recovery evidence
- audit or activity log summaries
- access-review summaries
- runtime verification summaries

Evidence is acceptable only after review confirms it contains no secrets, no unnecessary personal data, and no sensitive provider details beyond the approved purpose.

## Raw Versus Sanitized Evidence

Raw evidence is the original screenshot, export, log, terminal transcript, provider payload, or incident material before redaction. Raw evidence must not be committed to Git.

Sanitized evidence is a reduced record that preserves the fact being proven while removing secret values, credentials, personal data, unnecessary account details, sensitive topology, and unrelated provider content.

Repository records may contain sanitized summaries and references. Raw evidence must remain outside Git in an approved access-controlled evidence location selected by the production-readiness program owner. The specific retention period is unresolved until an owner-approved retention decision sets it.

## Redaction Requirements

Before evidence enters the repository, redact or remove:

- secret values
- tokens and keys
- authorization headers
- cookies
- QR codes
- recovery codes
- private keys
- database passwords and connection strings
- signed URLs
- personal email addresses
- personal names where unnecessary
- phone numbers
- billing information
- account or project identifiers where unnecessary
- private hostnames or IP addresses where sensitive
- provider payloads
- user or customer data

When provider identifiers, project identifiers, user names, or email addresses are necessary to prove a specific control, prefer stable aliases in the repository and keep the raw mapping outside Git.

## Evidence Metadata

Each sanitized evidence record must include at least:

- provider or control plane
- environment
- date collected
- reviewer
- purpose
- control or pass supported
- source type
- sanitized evidence reference
- raw evidence location reference, if one exists outside Git
- open gaps or follow-up actions

Do not include raw URLs to private dashboards, signed object URLs, invite links, recovery links, or downloadable exports when those links grant access or reveal private data.

## Repository Locations

Approved Git locations for EN-03 evidence handling are:

- `docs/production-readiness/governance/` for standards, registers, and reusable checklists
- `docs/production-readiness/planning/` for pass-specific sanitized findings and control mapping

Do not add raw screenshots, raw exports, provider ZIP files, billing files, credentials, local `.env` files, key files, recovery documents, or private provider payloads anywhere in the repository.

A future evidence directory may be created only after the production-readiness program owner approves naming, retention, access, and redaction rules for committed sanitized evidence.

## Naming Convention

Use concise, non-secret names for sanitized records:

```text
provider-environment-purpose-yyyy-mm-dd-sanitized.md
```

Examples should use provider and environment names only, not account names, project identifiers, tenant identifiers, private hostnames, or personal names unless those details are explicitly required and approved for repository exposure.

## Pre-Commit Review

Before staging any provider evidence or evidence summary:

1. Confirm the file is intentionally allowed in the repository.
2. Confirm all secret values, credentials, signed URLs, cookies, recovery codes, private keys, personal data, billing details, and unnecessary provider identifiers are removed.
3. Confirm the evidence includes the minimum metadata.
4. Confirm the evidence supports the stated control without exposing extra provider surface.
5. Run repository searches for private-key blocks, token-shaped values, connection strings with passwords, webhook secrets, recovery codes, signed URLs, raw exports, and ignored local env files.
6. Record unresolved gaps instead of guessing provider settings.

## Staleness And Replacement

Evidence becomes stale when provider settings change, users or roles change, credentials rotate, environments split or merge, deployments move, domains change, incidents occur, recovery methods change, or the approved review cadence expires.

Stale repository evidence must be replaced with a new sanitized record or marked superseded by a later approved record. Do not silently edit historical evidence in a way that hides the original review basis.

## Relationship To EN-02 Redaction Principles

EN-02 established redaction principles for logs and observable text. Apply those same principles to provider evidence: preserve operational meaning while removing secrets, unnecessary personal data, and sensitive payload details.

EN-03 does not require screenshots, exports, or provider evidence to be processed automatically by EN-02 code. Human review remains required before any evidence is committed.
