# Pickup Lane Production-Readiness Entry Point

This is the single entry point for starting Pickup Lane production-readiness
work. It owns startup, authority, workflow selection, frozen-artifact rules,
automation boundaries, publication boundaries, local handoff usage, and
tracked-documentation safety.

This document does not maintain mutable branch, SHA, or current-pass status.

## Current Execution State

Determine current execution state from:

1. current accepted `origin/develop`;
2. current local repository state;
3. `planning/program/PASS-EXECUTION-REGISTER.md`;
4. the current production-readiness run instruction.

Do not rely on historical baseline SHAs, branch names, prior PRs, or chat
history as current execution state.

## Initial Reading Order

Before any production-readiness pass work:

1. Read this document.
2. If `docs/local/CURRENT-HANDOFF.md` is supplied, read it as optional local
   orientation and verify it against current Git state and tracked authority
   before acting.
3. Read `01-PROGRAM-CONTEXT.md` for stable program overview and routing.
4. Read `planning/program/PASS-EXECUTION-REGISTER.md`.
5. Select and read the applicable workflow:
   `planning/workflows/PASS-IMPLEMENTATION-WORKFLOW.md` for first-time pass
   implementation, or `planning/workflows/PASS-RECHECK-WORKFLOW.md` for
   revalidating an accepted pass or historical implementation.
6. Read the accepted intake when applicable, current or frozen pass plan, gate
   templates, engineering/testing standards, governance records, owner
   decisions, current source, and evidence routed by the workflow, Program
   Context, and current run instruction.
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

## Automated Program Progression

A user instruction to start, run, continue, or resume Pickup Lane
production-readiness work authorizes the normal automated workflow for the
selected work:

```text
STAGE 0
-> GATE A PLANNING
-> INDEPENDENT GATE A REVIEW / CORRECTION CYCLE
-> GATE B IMPLEMENTATION AND VALIDATION
-> INDEPENDENT GATE C REVIEW / CORRECTION CYCLE
-> GATE D GIT AND PR FINALIZATION
-> OPEN PR FOR MANUAL MERGE
```

Routine successful transitions between those states do not require separate
human approval prompts.

For first-time parent work:

- Stage 0 determines whether the parent remains one executable pass, is
  decomposed into ordered executable children, or contains a current executable
  unit plus a mandatory deferred follow-up.
- A valid Stage 0 result is accepted for the current automated run and the first
  executable pass proceeds to Gate A.
- Every executable child receives a fresh Gate A against current accepted
  `develop` after required earlier children merge and any execution trigger is
  satisfied.
- After a child PR is manually merged, resume from current repository truth. If
  another accepted current child remains and its prerequisites and execution
  trigger are satisfied, continue with that child at Gate A without rerunning
  Stage 0.
- When all current executable child obligations are accepted, reconcile any
  mandatory deferred follow-up before deciding parent completion or subsequent
  work. An unmet deferred trigger keeps that obligation and its controls open but
  does not block unrelated downstream work whose own prerequisites are already
  satisfied.
- Determine the next executable unit from the master blueprint, remediation plan,
  execution register, dependency state, deferred-trigger state, and current
  accepted source. If exactly one next unit is determined, begin it at the stage
  required by the applicable workflow.
- If durable authority leaves multiple equally valid next units or otherwise
  cannot determine progression safely, stop for owner selection instead of
  inventing priority.

Automated progression never authorizes guessing through an unresolved product,
security, policy, operational, provider, evidence, dependency, or structural
decision.

## Final Infrastructure Timing And Provider-Neutrality Rule

Temporary development/demo infrastructure must not become permanent production
architecture by accident.

Current Vercel frontend hosting, Render API hosting, and Neon PostgreSQL hosting
are temporary development/demo infrastructure. They may be described as current
demo integrations where relevant, but they are not evidence of the final
production hosting or database topology and must not be used as permanent
implementation targets, default capacity assumptions, or final configuration
values.

Final production hosting, database hosting, edge/ingress/proxy/TLS topology,
process and instance topology, autoscaling and rolling-deployment behavior,
provider plan or capacity, provider-specific hardening, and other
deployment-specific settings remain intentionally late-bound until final
infrastructure is selected.

Before Stage 0 accepts an executable boundary, and before Gate A freezes a plan:

- separate work that can be completed provider-independently from work that
  depends on final provider, topology, runtime, or configuration facts;
- complete coherent provider-independent work now when possible, including
  source interfaces, generic configuration contracts, validation, portable
  behavior, formulas, evidence schemas or checkers, synthetic test fixtures, and
  ownership or handoff rules;
- do not invent, copy, or promote final production values from temporary
  providers, README examples, local or CI settings, free-tier defaults,
  framework defaults, or temporary deployments;
- defer work that requires the actual final infrastructure, including concrete
  provider plan/tier/region/capacity, provider-native deployment settings,
  project or account binding, DNS/TLS/proxy/edge settings, instance/process
  counts, autoscaling or rolling-overlap facts, provider-dependent pool or
  capacity values, concrete production roles or grants, final numeric values
  that depend on provider characteristics, and provider/runtime proof;
- when one parent contains both kinds of work, Stage 0 must split the
  executable-now work from a mandatory deferred follow-up rather than forcing an
  early infrastructure choice or blocking unrelated work;
- every deferred follow-up must record its owning pass or unit, exact trigger,
  preserved obligations, dependencies, latest required completion boundary, and
  execution-register visibility;
- deferred work is not proof and does not close the affected control. Run it as
  soon as its trigger is satisfied and no later than the earliest downstream
  pass that truly needs the deferred facts or `CLOSE-01`, whichever comes first;
- downstream work may continue only when its own prerequisites do not require
  the deferred provider/runtime facts. If it does require them, stop on that
  specific prerequisite instead of inventing or substituting temporary values.

The master blueprint must make known final-infrastructure-dependent passes or
pass portions visible before normal progression reaches them, including the
required trigger or late-bound placement. The execution register records later
accepted decomposition, deferred units, and trigger state. Do not wait until
Gate B to discover that a pass requires intentionally unselected production
infrastructure.

This rule does not prohibit existing provider-specific product integrations that
are already fixed by higher authority, nor does it prohibit portable
provider-neutral configuration interfaces. It governs final infrastructure
selection and concrete production configuration or evidence that depends on
that selection. If higher authority explicitly locks a permanent provider,
follow that authority, but do not invent concrete production values without the
required evidence.

## Authority Order

Current accepted repository source, configuration, tests, and artifacts are
authoritative for what currently exists and how the implementation currently
behaves. They are repository truth. Current implementation does not define
product or production-readiness requirements merely because it exists in the
repository.

Requirement authority is, in order:

1. The six locked audit reports and 163-control checklist
2. Final remediation plan
3. Approved decision records and final decision inventory
4. Master production-readiness blueprint
5. Current pass-specific inspection and implementation instructions

When current implementation conflicts with authoritative requirements, treat
that as an implementation mismatch to reconcile, not as authority for changing
the requirement.

Stop when two authoritative records conflict. Do not guess or silently
reconcile them.

`planning/program/PASS-EXECUTION-REGISTER.md` is accepted-state navigation, not
product authority. Accepted intake and frozen plans constrain gate work, child
structure, and parent obligation allocation, but they cannot override audits,
decisions, the final remediation plan, the master blueprint, or repository truth
about current implementation behavior.

A valid Stage 0 result defines the executable structure for the current
automated run. A clean independent Gate A review freezes the exact reviewed
canonical-plan SHA for Gate B. Neither transition overrides higher authority.

## Excluded Legacy Tests

For production-readiness work, `backend/tests/legacy/` is treated as
nonexistent. Do not read, search, list, execute, cite, derive from, or use that
tree for provenance, requirement discovery, scenario or assertion design,
implementation reasoning, evidence, or behavioral confirmation.

## Instruction Adherence

Reading an instruction is not sufficient compliance. Before acting, resolve the
binding requirements of the current run instruction.

Treat explicit scope, artifact paths, SHAs, stage or gate boundaries, validation
requirements, stop conditions, and `must` / `must not` instructions as
constraints, not suggestions.

If a binding instruction conflicts with authority, a frozen artifact, repository
truth, or cannot be followed exactly, stop and report the issue. Never silently
substitute an approximate, broader, narrower, or supposedly equivalent action
for an explicit instruction.

Before reporting completion, compare the actual work performed against the
binding instruction. Correct any mismatch that is still in scope; otherwise
report the mismatch and stop.

## Frozen Intake And Frozen Plan Rules

An accepted Stage 0 intake and a canonical plan that has passed independent
Gate A review are frozen gate artifacts for the current automated run. Gate
instructions identify their SHA-256 values. Gate B, Gate C, and Gate D verify
the applicable frozen values.

For a later child, an intake already accepted in current `develop` remains the
frozen parent decomposition unless a structural Stage 0 revision is required.

Intake content changes return to Stage 0. Canonical-plan content changes return
to Gate A and require a new full independent Gate A review before the changed
plan can govern Gate B. Gate B must not edit the frozen intake or frozen
canonical plan.

## Local Current-State Handoff

`docs/local/CURRENT-HANDOFF.md` is optional local orientation. Verify it against
current Git state and tracked authority before acting.

Refresh the handoff when production-readiness workflow state materially
changes, including intake completion or decomposition changes, Gate A planning
or review changes, Gate A plan freeze, Gate B completion, Gate C approval or
required corrections, completion of Gate C corrections, Gate D/PR creation, PR
merge and accepted `develop` advancement, selection or start of the next
executable pass, or changes to the current branch, accepted baseline, frozen
artifacts, changed-file set, review status, or exact next action.

Refresh it before moving production-readiness work to a new ChatGPT/Codex
session. Do not refresh it for routine commands, individual test runs, or small
edits that do not materially change workflow state. Replace stale current-state
information instead of accumulating a historical diary.

The ignored local handoff may contain the local repository path, branch,
baseline, frozen-artifact SHAs, current local changes, validation summary,
review counters/history, PR state, and exact next action. It must never contain
secrets, personal data, payment data, raw logs, or provider-private values.

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

Reading this bundle by itself does not authorize implementation or publication.

A user instruction to start, run, continue, or resume production-readiness work
authorizes the coordinator to execute the normal automated Stage 0 through Gate
D workflow for the selected/deterministically progressing work, subject to the
durable stop conditions and review limits.

Within that authorized run:

- a valid Stage 0 result may advance automatically to Gate A;
- a clean independent Gate A review may freeze the exact reviewed plan SHA and
  advance automatically to Gate B;
- a completed/validated Gate B may advance automatically to Gate C;
- a clean independent Gate C review may advance automatically to Gate D;
- Gate D may stage, commit, push, and create or update the intended PR.

Gate D does not merge the PR. PR merge remains manual.

Separate explicit authorization is still required for destructive or
irreversible provider/runtime/database/deployment/credential operations when the
approved pass does not already and unambiguously authorize that exact action.

If the current run instruction conflicts with durable authority, repository
truth, a frozen artifact, or a required safety boundary, stop and report instead
of proceeding.
