# Pickup Lane Production-Readiness Authoritative Documentation Bundle

## Execution status

This document does not maintain mutable branch, SHA, or current-pass status.

Determine current execution state from:

1. current accepted `origin/develop`;
2. current local repository state;
3. the currently approved pass-specific instruction.

Do not rely on historical baseline SHAs, branch names, or previously recorded
pass status as current execution state.

## New session bootstrap

Before any production-readiness pass work:

1. Read this document, `01-PROGRAM-CONTEXT.md`, and
   the applicable workflow:
   `planning/PASS-IMPLEMENTATION-WORKFLOW.md` for first-time pass
   implementation or `planning/PASS-RECHECK-WORKFLOW.md` for revalidating an
   already-implemented pass.
2. Verify current Git/repository state and determine the current pass and gate
   from current repository truth and the current approved instruction before
   relying on historical prompts, PRs, branches, SHAs, or prior chat context.
3. Load the current or frozen pass plan and every gate-specific repository
   template or required engineering/testing standard before drafting or
   executing that gate's instruction.

## Authority order

1. Current repository tree at the trusted baseline and later accepted pass commits
2. The six locked audit reports and 163-control checklist
3. Final remediation plan
4. Approved decision records and final decision inventory
5. Master production-readiness blueprint
6. Approved pass-specific inspection and implementation instructions

Stop when two authoritative records conflict. Do not guess or silently reconcile them.

## Bundle contents

### `governance/`
The finalized WS01 governance package.

### `audit-research/`
The six audit reports, 163-control checklist, static inventory crosswalk, and research consolidation/register.

### `decisions/`
Only the final approved decision records and the v4 inventory showing 27 approved decisions and 0 open decisions.

### `planning/`
The finalized remediation plan and master execution blueprint.
The forward implementation workflow for first-time executable passes lives at
[`PASS-IMPLEMENTATION-WORKFLOW.md`](planning/PASS-IMPLEMENTATION-WORKFLOW.md).
The pass intake template lives at
[`PASS-INTAKE-TEMPLATE.md`](planning/PASS-INTAKE-TEMPLATE.md).
The execution register that distinguishes original blueprint parent passes
from accepted executable passes lives at
[`PASS-EXECUTION-REGISTER.md`](planning/PASS-EXECUTION-REGISTER.md).
The historical pass recheck process for revalidating already-implemented
passes lives at
[`PASS-RECHECK-WORKFLOW.md`](planning/PASS-RECHECK-WORKFLOW.md).

## Excluded intentionally

This bundle does not include superseded decision inventories, draft remediation plans, correction prompts, Codex implementation prompts, temporary input packages, or ZIP archives from earlier planning work.

## Codex restriction

Reading this bundle does not authorize implementation. Codex must act only on the currently approved pass-specific prompt and stop at that prompt's boundaries.
