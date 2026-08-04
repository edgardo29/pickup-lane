# Pickup Lane Master Decision Inventory

## Purpose

This is the first organization artifact for the complete production-readiness blueprint. It inventories every owner decision before implementation planning begins.

No application code, Git branch, worktree, provider, deployment, or runtime action is authorized by this document.

## Reconciliation

- Total decision-register entries: **27**
- Approved and locked: **27**
- Still open: **0**
- Source: finalized production-readiness remediation plan owner-decision execution register

## Current sequence rule

1. Inventory all decisions.
2. Confirm their dependencies and earliest blocking workstream.
3. Group related decisions into plain-language approval packets.
4. Approve the complete blueprint and Git workflow.
5. Begin implementation only after the relevant entry gate passes.

## Decision register

| ID | Status | Decision | Earliest affected workstream | Decision timing |
|---|---|---|---|---|
| API-M18 | APPROVED (FDN-03) | Decide OpenAPI/docs exposure, inventory, versioning, compatibility, and deprecation policy. | WS01 | Approved foundation decision |
| GOV-004 | APPROVED (FDN-01) | Assign named production owners across core systems and provider accounts. | WS01 | Approved foundation decision |
| GOV-006 | APPROVED (FDN-04) | Decide documented bases for limits, thresholds, pools, retries, retention, RPO, RTO, and alerts. | WS01 | Approved foundation decision |
| TST-011 | APPROVED (FDN-05) | Decide retry, flake, artifact retention, and risk-based coverage policy. | WS01 | Approved foundation decision |
| API-M08 | APPROVED (FDN-02) | Assign security-header ownership between app and edge. | WS02 | Approved foundation decision |
| TST-017 | APPROVED (FDN-06) | Decide artifact identity, SBOM, provenance, signing, and release-evidence policy. | WS02 | Approved foundation decision |
| OPS-010 | APPROVED (FDN-07) | Decide telemetry label bounds, privacy review, and correlation/tracing posture. | WS08 | Approved foundation decision |
| DB-002 | APPROVED (DBP-01) | Decide deployment-wide DB connection budget. | WS02 | Approved in Decision Packet 3 |
| FE-M09 | APPROVED (IDB-05) | Decide third-party browser-code inventory, data-sharing, CSP/SRI, and provider-failure posture. | WS02 | Approved in Decision Packet 2 |
| FE-M12 | APPROVED (OPP-01) | Decide WCAG target and accessibility verification scope. | WS02 | Approved in Decision Packet 4 |
| FE-M13 | APPROVED (OPP-02) | Decide browser support, performance budgets, source-map policy, and telemetry/performance measurement. | WS02 | Approved in Decision Packet 4 |
| IAM-003 | APPROVED (IDB-01) | Decide Firebase browser persistence and retry/replay behavior. | WS02 | Approved in Decision Packet 2 |
| IAM-010 | APPROVED (IDB-04) | Decide whether Firebase App Check applies. | WS02 | Approved in Decision Packet 2 |
| STO-009 | APPROVED (DBP-04) | Decide deletion, lifecycle, retention, recovery, monitoring, and R2 controls. | WS02 | Approved in Decision Packet 3 |
| ADM-014 | APPROVED (OPP-03) | Decide enforcement notice timing, suppression, appeal, and safe-content rules. | WS03 | Approved in Decision Packet 4 |
| IAM-006 | APPROVED (IDB-02) | Decide source-of-truth matrix for identity, profile, role, account state, ownership, and permissions. | WS03 | Approved in Decision Packet 2 |
| IAM-007 | APPROVED (IDB-03) | Decide verified-email policy and administrator verified-identifier requirement. | WS03 | Approved in Decision Packet 2 |
| PAY-007 | APPROVED (DBP-02) | Decide canonical financial state mapping. | WS03 | Approved in Decision Packet 3 |
| OPS-018 | APPROVED (OPP-04) | Decide RPO, RTO, PITR, backup/WAL window, and restore dependencies. | WS04 | Approved in Decision Packet 4 |
| OPS-020 | APPROVED (OPP-05) | Decide R2 loss tolerance and recovery protection. | WS04 | Approved in Decision Packet 4 |
| OPS-021 | APPROVED (OPP-06) | Decide tabletop and technical recovery exercise cadence and scope. | WS04 | Approved in Decision Packet 4 |
| OPS-022 | APPROVED (OPP-07) | Decide data-purpose and retention schedules. | WS04 | Approved in Decision Packet 4 |
| STO-006 | APPROVED (DBP-03) | Decide image sanitization, re-encoding, derivative, metadata, and processing requirements. | WS05 | Approved in Decision Packet 3 |
| OPS-012 | APPROVED (OPP-09) | Decide service indicators, objectives, launch thresholds, and error-budget posture. | WS08 | Approved in Decision Packet 4 |
| OPS-016 | APPROVED (OPP-10) | Decide capacity and cost model across API, DB, workers, providers, logs, CI, and backups. | WS08 | Approved in Decision Packet 4 |
| ADM-008 | APPROVED (OPP-11) | Decide audit review, alerting, retention, archive, deletion, legal hold, and export handling. | WS10 | Approved in Decision Packet 4 |
| DB-011 | APPROVED (OPP-08) | Decide per-table lifecycle, deletion, anonymization, retention, restoration, and backup-retention policy. | WS10 | Approved in Decision Packet 4 |

## Next blueprint task

All owner decisions are now approved. The next artifact will convert them into the complete implementation blueprint:

- plain-language question
- realistic options
- recommendation
- consequences of each option
- information or provider evidence needed
- exact workstreams and implementation passes blocked
- approval deadline in the sequence

No open decision will be silently delegated to Codex.