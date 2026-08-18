# Pickup Lane Production Readiness Governance

Status: WS01 governance foundation, pre-production.

Accountable role: Production-readiness program owner, held by Project owner (interim) until reassigned under the approved ownership model.

## Purpose

This documentation set is the governance baseline for the Pickup Lane production-readiness remediation program. It records architecture evidence, interim ownership, approved foundation decisions, limit-decision structure, audit-process rules, and the empty risk/exception process required before later technical work can be closed.

These records support GOV-001, GOV-004, GOV-005, GOV-006, and GOV-007. They also preserve decisions needed by API-M08, API-M18, TST-011, TST-017, and OPS-010, but those downstream controls are not implemented or closed by this pass.

## Relationship To Finalized Audit And Remediation Plan

The authoritative audit baseline is the finalized Parts 1 through 6 static audit and the finalized production-readiness remediation plan. Those reports established that production-readiness sign-off is not supported and that every P0 control remains unresolved until the required repository, test, runtime, deployment, provider, operational, recovery, and owner-decision evidence exists.

These WS01 artifacts are governance records. They are not proof that application behavior changed, CI ran, providers were configured, deployments succeeded, backups exist, alerts work, or runtime behavior was verified.

## Artifact Map

| Artifact | Purpose | Primary controls |
|---|---|---|
| [Architecture and trust boundaries](architecture-and-trust-boundaries.md) | Repository-confirmed and evidence-required production topology inventory. | GOV-001 |
| [Production ownership register](production-ownership-register.md) | Interim role model, accountable owner hats, evidence duties, and unassigned backups. | GOV-004 |
| [Foundation decision register](foundation-decision-register.md) | Approved foundation decisions recorded without adding new outcomes or threshold values. | GOV-004, GOV-006, API-M08, API-M18, TST-011, TST-017, OPS-010 |
| [Limits and thresholds register](limits-and-thresholds-register.md) | Evidence-based method and open value register for limits, timeouts, retention, recovery, alerts, and capacity. | GOV-006 |
| [Production-readiness audit process](production-readiness-audit-process.md) | Repeatable audit workflow, evidence classes, approval gates, reassessment, result versioning, and unresolved-control handling. | GOV-005, GOV-007 |
| [Risk and exception register](risk-and-exception-register.md) | Empty governed exception register and required approval process. | GOV-007 |
| [Reusable templates](templates.md) | Decision, exception, and audit-run templates for future governed changes. | GOV-005, GOV-006, GOV-007 |
| [Provider control-plane register](provider-control-plane-register.md) | Sanitized register of provider/control-plane ownership, access, MFA, recovery, separation, and evidence gaps. | OPS-005, OPS-025 |
| [Secret lifecycle register](secret-lifecycle-register.md) | Secret-name and configuration lifecycle register without values. | OPS-006, OPS-007 |
| [Provider evidence handling standard](provider-evidence-handling-standard.md) | Rules for collecting, sanitizing, reviewing, storing, and replacing provider evidence. | OPS-025 |
| [Provider evidence checklist](provider-evidence-checklist.md) | Reusable provider evidence checklist with no real account information. | OPS-005, OPS-006, OPS-007, OPS-025 |
| [EN-03 secrets, control plane, and evidence foundation](../planning/passes/en/en-03-secrets-control-plane-evidence-foundation.md) | Pass-specific scope, topology, boundaries, control mapping, and deferred evidence. | OPS-005, OPS-006, OPS-007, OPS-025 |

## Record Types

Approved decisions are owner-approved governance choices recorded in the foundation decision register. They unlock downstream work but do not close controls by themselves.

Open decisions are unresolved value, policy, ownership, or applicability questions. They remain unresolved until a decision record is approved and the required downstream evidence exists.

Evidence records are preserved source, test, runtime, deployment, provider, operational, or recovery artifacts tied to a control and source revision or artifact identity. Evidence records support an audit finding but do not replace implementation.

Accepted exceptions are explicit risk records with owner approval, scope, compensating controls, evidence, verification plan, and expiry or review date. No unresolved finding is accepted unless a separate approved exception says so.

## Update And Review Rules

The production-readiness program owner keeps this index and linked artifacts current. Each artifact names the role that owns updates and evidence review.

Update these records when a source architecture component changes, a provider or deployment setting changes, a new production dependency is introduced, a control status is reassessed, a remediation workstream completes, a material incident or recovery exercise occurs, an exception expires, or an approved decision is superseded.

The periodic calendar review cadence is open until an owner-approved decision sets it. Do not invent a time-based interval.

No P0 gap is accepted without a separate approved exception. Expired exceptions return the affected control to unresolved status until new evidence or a renewed approval exists.

The current `docs/` directory is ignored by repository ignore rules. This pass does not change that configuration.
