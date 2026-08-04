# Production-Readiness Audit Process

Primary controls: GOV-005 and GOV-007.

Owner role: Production-readiness program owner, held by Project owner (interim).

## Authority

The authoritative control manifest is the finalized 163-control production-readiness checklist. Future audit runs must identify the manifest version, the assessed source revision, any deployment or artifact identities used as evidence, the evidence package location, the reviewer, the approver, and any superseded result.

Audit output is not proof of implementation. Configured CI is not proof that CI ran. Code is not complete without required tests and external evidence. No P0 gap is accepted without a separately approved exception. Expired exceptions return the affected control to unresolved status.

## Status Vocabulary

Use only the normalized control statuses from the finalized audit process:

| Status | Meaning |
|---|---|
| PASS | Required evidence exists for the assessed scope. |
| PARTIAL | Some repository-verifiable evidence exists, but required evidence remains incomplete. |
| FAIL | Required evidence is absent or a confirmed gap exists. |
| NEEDS DECISION | A control is blocked by an owner decision, policy, applicability, or threshold choice. |
| NOT APPLICABLE | A control is formally out of scope with documented rationale. |
| EXTERNAL EVIDENCE REQUIRED | Repository evidence cannot prove the control; provider, runtime, deployment, operational, or recovery evidence is controlling. |

## Evidence Classes

Audit rows must use normalized evidence classes and distinguish evidence from planned remediation. Supported classes include source code, database schema or migration, static configuration, CI configuration, deployment configuration, current non-legacy test source, runtime required, provider dashboard required, owner decision required, operational process required, and recovery or exercise evidence where the control requires it.

Legacy tests are historical context only and cannot be used as current-test evidence.

## Audit Run Workflow

1. Define scope from the authoritative manifest and name the source revision, artifact identity, environment, and files/packages to be assessed.
2. Collect evidence from current source, current non-legacy tests, static configuration, CI configuration, deployment records, provider evidence, runtime observations, operational records, and recovery exercises as applicable.
3. Preserve evidence in a durable audit package with redaction rules for secrets, tokens, private messages, payment data, personal data, signed URLs, and provider credentials.
4. Assign each control one normalized status, class, priority, evidence class set, current evidence, missing evidence or gap, and next verification.
5. Reconcile control counts, duplicate IDs, missing IDs, class/priority mismatches, invalid statuses, and evidence-class vocabulary.
6. Review unresolved P0 controls and owner-decision controls with the responsible owner hats.
7. Link any approved exception by exception ID. Do not treat unresolved audit findings as accepted risks without an approved exception.
8. Approver signs or rejects the audit package. Rejection must record required corrections.
9. Preserve the result with versioning, source revision or artifact linkage, reviewer, approver, date, supersession relationship, and unresolved-control register.

## Reviewers And Approvers

The production-readiness program owner coordinates the audit. Domain owner hats review evidence for their systems. The Project owner (interim) approves or rejects the result until a superseding ownership record delegates that authority.

Controls that depend on external provider settings require review by the owner of that provider or control plane. Controls that depend on payment, privacy, incident response, recovery, or data retention require the corresponding owner hat before sign-off.

## Reassessment Triggers

Run a reassessment when a remediation workstream completes, a production-readiness control changes, an architecture component is added or removed, a provider/deployment setting changes, a security or reliability incident occurs, a recovery exercise changes evidence, a P0 exception expires, a source artifact is superseded, or a release candidate seeks production sign-off.

The periodic calendar cadence is open until approved by owner decision. Do not invent a time-based interval.

## Pre-Production Sign-Off Gate

Production sign-off requires every P0 control to be PASS, formally not applicable, externally evidenced where applicable, or covered by a separately approved non-expired exception. The sign-off package must include the final manifest reconciliation, P0 index, owner decisions, runtime/failure verification, provider and operational evidence, test assessment, accepted exceptions, unresolved controls, and explicit approval.

Adding governance documentation does not close any control by itself.

## Supersession

A later audit run supersedes an earlier run only when it states the prior result, source/artifact identity, controls reassessed, finding changes, reviewer, approver, and reason for supersession. Prior results remain preserved.
