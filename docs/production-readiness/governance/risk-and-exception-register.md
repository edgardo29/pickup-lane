# Risk And Exception Register

Primary control: GOV-007.

Owner role: Incident response and recovery owner with production-readiness program owner oversight. Both roles are held by Project owner (interim) until reassigned.

No production-readiness exception is approved unless an explicit record in this register says otherwise. This initial register contains no approved exceptions. Unresolved audit findings are not automatically accepted risks.

## Approved Exceptions

| Exception ID | Related control IDs | Risk statement | Owner | Rationale | Scope | Compensating controls | Evidence | Approval | Start date | Expiry or review date | Verification plan | Status | Closure or supersession record |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Required Fields

| Field | Requirement |
|---|---|
| Exception ID | Stable identifier for the exception record. |
| Related control IDs | All affected checklist controls. |
| Risk statement | Clear description of the accepted risk and potential impact. |
| Owner | Accountable owner hat and named accountable owner. |
| Rationale | Why the exception is requested instead of immediate remediation. |
| Scope | Exact environment, feature, provider, control, user population, and time scope. |
| Compensating controls | Temporary safeguards, monitoring, manual process, or restriction used while the gap remains. |
| Evidence | Static, runtime, provider, operational, or recovery evidence supporting the exception request and compensating controls. |
| Approval | Approver, approval date, and decision record. |
| Start date | Date the exception becomes effective. |
| Expiry or review date | Date or event when the exception must be revalidated, renewed, closed, or allowed to expire. |
| Verification plan | How compensating controls and closure/remediation will be verified. |
| Status | Proposed, approved, rejected, expired, closed, or superseded. |
| Closure or supersession record | Closure evidence, superseding exception, or return-to-unresolved note. |

## Process

An exception request starts as proposed. It becomes approved only after the accountable owner and approver accept the risk statement, scope, compensating controls, evidence, and expiry or review condition.

No exception may silently cover a P0 gap. Each P0 exception must identify the control IDs, compensating controls, verification plan, and expiry or review condition.

When an exception expires or its scope is no longer true, affected controls return to unresolved status until new evidence, remediation, or renewed approval exists.

Rejected, closed, expired, and superseded exceptions remain preserved for audit history.
