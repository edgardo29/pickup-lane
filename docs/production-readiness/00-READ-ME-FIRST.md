# Pickup Lane Production-Readiness Entry Point

This is the single entry point for starting Pickup Lane production-readiness
work. It owns startup, authority, workflow selection, frozen-artifact rules,
publication boundaries, local handoff usage, and tracked-documentation safety.

This document does not maintain mutable branch, SHA, or current-pass status.

## Current Execution State

Determine current execution state from:

1. current accepted `origin/develop`;
2. current local repository state;
3. `planning/program/PASS-EXECUTION-REGISTER.md`;
4. the currently approved pass-specific instruction.

Do not rely on historical baseline SHAs, branch names, prior PRs, or chat
history as current execution state.

## Initial Reading Order

Before any production-readiness pass work:

1. Read this document.
2. If `docs/agent/production-readiness/CURRENT-HANDOFF.md` is supplied, read it
   as optional local orientation and verify it against current Git state and
   tracked authority before acting.
3. Read `01-PROGRAM-CONTEXT.md` for stable program overview and routing.
4. Read `planning/program/PASS-EXECUTION-REGISTER.md`.
5. Select and read the applicable workflow:
   `planning/workflows/PASS-IMPLEMENTATION-WORKFLOW.md` for first-time pass
   implementation, or `planning/workflows/PASS-RECHECK-WORKFLOW.md` for
   revalidating an accepted pass or historical implementation.
6. Read the approved intake, frozen pass plan, gate templates,
   engineering/testing standards, governance records, owner decisions, current
   source, and evidence routed by the workflow, Program Context, and current
   pass instruction.
7. Verify current Git state, accepted baseline, branch, frozen artifact SHAs,
   changed-file scope, and staged-file state before acting.

## Workflow Selection

Use `PASS-IMPLEMENTATION-WORKFLOW.md` when a pass is being implemented for the
first time from current authority and current accepted `develop`.

Use `PASS-RECHECK-WORKFLOW.md` when a pass already accepted into `develop`, or
historical implementation that predates the current workflow, is being
revalidated against current authority, source, and evidence standards.

When workflow selection is unclear, stop and report the ambiguity instead of
inventing a hybrid process.

## Authority Order

1. Current repository tree at the trusted baseline and later accepted pass
   commits
2. The six locked audit reports and 163-control checklist
3. Final remediation plan
4. Approved decision records and final decision inventory
5. Master production-readiness blueprint
6. Approved pass-specific inspection and implementation instructions

Stop when two authoritative records conflict. Do not guess or silently
reconcile them.

`planning/program/PASS-EXECUTION-REGISTER.md` is accepted-state navigation, not
product authority. Approved intake constrains child structure and parent
obligation allocation, but it cannot override audits, decisions, the final
remediation plan, the master blueprint, or current repository truth.

Intake approval does not authorize implementation. The next pass requires
explicit owner direction.

## Frozen Intake And Frozen Plan Rules

Approved intake records and approved canonical plans are frozen gate artifacts.
Gate instructions identify their approved SHA-256 values. Gate B, Gate C, and
Gate D verify those values.

Intake content changes return to Stage 0. Canonical-plan content changes return
to Gate A. Gate B must not edit the frozen intake or frozen canonical plan.

## Local Current-State Handoff

`docs/agent/production-readiness/CURRENT-HANDOFF.md` is optional local
orientation. Verify it against current Git state and tracked authority before
acting.

Refresh the handoff when production-readiness workflow state materially
changes, including intake completion or decomposition changes, Gate A plan
freeze, Gate B completion, Gate C approval or required corrections, completion
of Gate C corrections, Gate D/PR creation, PR merge and accepted `develop`
advancement, selection or start of the next executable pass, or changes to the
current branch, accepted baseline, frozen artifacts, changed-file set, review
status, or exact next action.

Refresh it before moving production-readiness work to a new ChatGPT session.
Do not refresh it for routine commands, individual test runs, or small edits
that do not materially change workflow state. Replace stale current-state
information instead of accumulating a historical diary.

The ignored local handoff may contain the local repository path, branch,
baseline, frozen-artifact SHAs, current local changes, validation summary, and
exact next action. It must never contain secrets, personal data, payment data,
raw logs, or provider-private values.

## Tracked-Documentation Safety

Tracked production-readiness documentation may contain:

- repository-relative paths;
- architecture and system descriptions;
- requirements and control identifiers;
- sanitized evidence and validation summaries;
- public provider names;
- pass-specific branches, baselines, and artifact SHAs only where the pass
  workflow genuinely requires them.

Tracked production-readiness documentation excludes:

- credentials, tokens, passwords, secret values, private keys, or recovery
  material;
- provider-private account, project, tenant, customer, payment, webhook, or
  dashboard identifiers;
- private dashboard/account URLs;
- personal data, real emails, phone numbers, addresses, user identifiers, or
  payment data;
- raw production logs or unredacted errors;
- local absolute paths and workstation usernames;
- internal chat history;
- temporary ChatGPT/Codex prompts;
- user interaction preferences;
- transient Git status, temporary session notes, or mutable current-pass state
  in general durable documents.

## Bundle Contents

### `governance/`

The finalized WS01 governance package.

### `audit-research/`

The six audit reports, 163-control checklist, static inventory crosswalk, and
research consolidation/register.

### `decisions/`

Final approved decision records and the final decision inventory.

### `planning/`

The finalized remediation plan, master execution blueprint, execution register,
forward implementation workflow, historical recheck workflow, pass intake
template, pass planning template, testing-record template, and PR description
template.

## Excluded Intentionally

This bundle does not include superseded decision inventories, draft remediation
plans, correction prompts, Codex implementation prompts, temporary input
packages, ZIP archives from earlier planning work, or local current-session
handoff files.

## Execution And Publication Boundary

Reading this bundle does not authorize implementation. Gate C approval also
does not authorize staging, committing, pushing, PR creation, or PR updates.
Only an explicit Gate D instruction authorizes publication mechanics. Codex
must act only on the currently approved pass-specific prompt and stop at that
prompt's boundaries.
