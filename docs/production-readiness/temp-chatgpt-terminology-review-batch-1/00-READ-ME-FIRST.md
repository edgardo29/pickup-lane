# Pickup Lane Production-Readiness Entry Point

This is the single entry point for Pickup Lane production-readiness work. It
defines startup, requirement-source priority, workflow selection, repository
safety, and publication boundaries.

The corrected master blueprint owns current production-readiness scope and
roadmap. This document does not maintain mutable branch, SHA, or current-pass
status.

## Accepted State And Current Change Set

Keep the accepted repository state separate from unmerged branch work:

1. **Accepted repository state** is the source, configuration, tests,
   migrations, and documentation in current accepted `origin/develop`.
2. **Current change set** is every change on the working branch relative to its
   accepted starting point, including branch commits, staged and unstaged
   changes, and applicable untracked files.
3. `planning/program/PASS-EXECUTION-REGISTER.md` records accepted execution
   state or the state a substantive PR intends to establish after merge.
4. The current run instruction defines the work presently authorized and its
   edit, validation, review, publication, and stop boundaries.

Do not rely on historical baseline SHAs, branch names, prior PRs, or chat
history as the current state. Do not describe an unmerged implementation or
planning change as accepted merely because it exists on the working branch.

## Initial Reading Order

Before production-readiness work:

1. Read this document.
2. Read `01-PROGRAM-CONTEXT.md`.
3. Read
   `planning/program/pickup-lane-master-production-readiness-blueprint.md`.
4. Check `planning/program/PASS-EXECUTION-REGISTER.md` for accepted or intended
   post-merge state, remaining work, and recorded deferred obligations. A normal
   pass does not use the register to track transient pre-publication progress.
5. Use the workflow-selection section below to enter the applicable workflow.
6. Follow that workflow's stage-specific routing to the reviewed plan or current
   planning record, technical standards, product documents, provider records,
   or historical material needed for the selected work.
7. Verify the current branch, its relationship to accepted `origin/develop`, the
   worktree, intended scope, and staged state before editing.

Historical plans, SHAs, audits, remediation documents, decisions, and local
session notes are optional context, not mandatory inputs, and cannot override
the corrected master. Current templates required by the applicable workflow are
used at the stage that workflow identifies.

## Workflow Selection

Use `planning/workflows/PASS-IMPLEMENTATION-WORKFLOW.md` when a pass is being
implemented for the first time from current requirements and accepted
`develop`.

Use `planning/workflows/PASS-RECHECK-WORKFLOW.md` when a pass already merged
into `develop`, or historical implementation that predates the current
workflow, is being revalidated against current requirements, accepted repository
state, and applicable verification standards.

When workflow selection is unclear, stop and report the ambiguity instead of
inventing a hybrid process.

## Workflow Roles And Progression

First-time implementation uses this execution sequence:

```text
SCOPE, RECONCILIATION, AND DECOMPOSITION DECISION / STAGE 0
-> ENGINEERING PLAN AND PLAN REVIEW / GATE A
-> IMPLEMENT AND TEST / GATE B
-> INDEPENDENT SEMANTIC REVIEW / GATE C
-> GIT AND PR FINALIZATION + EXECUTION-REGISTER UPDATE / GATE D
-> MANUAL MERGE
```

Stage 0 is required before first-time work begins for a selected corrected-master
unit. When a recorded Stage 0 result has already decomposed a parent, that result
also satisfies Stage 0 for its later children while current requirements,
dependencies, and accepted repository behavior still support it; each child
still performs Gate A. Return to Stage 0 only when those facts make the recorded
decomposition invalid. Stage 0 may decide that no decomposition is needed, and
Gate A may use a concise plan for straightforward work.

Durable intake or plan documents are required only when the current instruction
or the work itself requires them. When Gate A creates a durable plan, it must use
`planning/templates/PASS-PLANNING-TEMPLATE.md`. Gate D uses
`planning/templates/PASS-PR-DESCRIPTION-TEMPLATE.md` for the pull-request body.

The sequence does not create automatic orchestration. A user instruction
authorizes only the stage, work, and boundaries it actually states. The
corrected master defines production-readiness scope; the workflow does not.

Select work from the corrected master, accepted repository state, the current
change set when relevant, real prerequisites, late-bound triggers, the factual
execution register, and owner direction. Do not select work from old pass
ordering, filename order, stale branches, historical SHAs, or prior chat. When
several units are valid and no
real dependency selects one, ask the owner.

A deferred infrastructure/runtime obligation stays visible and incomplete but
blocks only work that genuinely depends on its missing facts.

## Final Infrastructure Timing Rule

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

When scoping, planning, or implementing work:

- separate work that is independent of final infrastructure selection from work
  that depends on the final hosting provider, topology, runtime, or
  configuration facts;
- complete coherent work that is independent of final infrastructure selection
  now when possible, including
  source interfaces, generic configuration interfaces, validation, portable
  behavior, formulas, synthetic test fixtures, and later-verification rules;
- do not invent, copy, or promote final production values from temporary
  providers, README examples, local or CI settings, free-tier defaults,
  framework defaults, or temporary deployments;
- defer work that requires the actual final infrastructure, including concrete
  provider plan/tier/region/capacity, provider-native deployment settings,
  project or account binding, DNS/TLS/proxy/edge settings, instance/process
  counts, autoscaling or rolling-overlap facts, provider-dependent pool or
  capacity values, concrete production roles or grants, final numeric values
  that depend on provider characteristics, and external provider/runtime
  verification;
- when one unit contains both kinds of work, separate the executable-now work
  from a deferred follow-up rather than forcing an early infrastructure choice
  or blocking unrelated work;
- every deferred follow-up must record its owning pass or unit, exact trigger,
  preserved obligations, dependencies, latest required completion boundary, and
  execution-register visibility;
- deferred work is not verification and does not complete the affected
  requirement. Run it as soon as its trigger is satisfied and no later than the
  earliest downstream pass that truly needs the deferred facts or `CLOSE-01`,
  whichever comes first;
- downstream work may continue only when its own prerequisites do not require
  the deferred infrastructure/runtime facts. If it does require them, stop on that
  specific prerequisite instead of inventing or substituting temporary values.

The master blueprint must make known final-infrastructure-dependent passes or
pass portions visible before normal progression reaches them, including the
required trigger or late-bound placement. The execution register records any
resulting decomposition, deferred units, and trigger state. Do not wait until
implementation to discover that a unit requires intentionally unselected
production infrastructure.

This rule does not prohibit an existing service-specific product integration,
such as Cloudflare R2, Stripe, or Firebase, when the corrected master or an
applicable current product requirement fixes that integration. It also does not
prohibit portable configuration interfaces. It governs final infrastructure
selection and concrete production configuration or external verification that
depends on that selection. If the corrected master or an explicit owner decision selects a
permanent infrastructure provider, follow that decision, but do not invent
concrete production values without verification of the relevant external facts.

## Requirement Sources And Existing Behavior

Use this distinction:

1. The corrected master blueprint defines current production-readiness scope,
   correction targets, remaining roadmap, boundaries, and completion criteria.
2. Applicable current product requirements and explicit owner decisions define
   product behavior where the corrected master delegates or does not decide it.
   A historical decision applies only when the corrected master, the current
   instruction, or a reviewed plan still adopts it.
3. Current accepted source, configuration, tests, migrations, and documentation
   establish existing repository behavior. They do not create a requirement
   merely because the behavior exists.
4. The execution register records accepted execution state or the intended
   post-merge state carried by the current substantive PR; it does not track a
   normal pass's transient progress through earlier gates.

Applicable engineering and testing standards constrain work within their
stated technical scope. They do not expand the selected pass or override a
product requirement.

Historical audits, the old remediation plan, governance records, decision
records, intakes, pass plans, SHAs, PR descriptions, and Git history are
provenance or supporting context. They may explain past decisions and useful
technical interfaces or invariants, but they may not override the corrected
master or restore scope it rejects.

When implementation conflicts with a current requirement source, identify the
specific sources in conflict and correct the mismatch within the selected
scope. Stop for a genuine unresolved product, security, policy, or operational
decision; do not guess.

## Existing Tests

Evaluate every existing test by usefulness, correctness, isolation, and the
behavior it proves. The former `backend/tests/legacy/` archive was assessed
file by file; useful missing coverage was migrated and the archive was retired.
Do not recreate it. Maintained tests belong in the active behavior-owned test
roots, but directory placement alone does not make a test a requirement source.

## Instruction Adherence

Before acting, resolve the binding requirements of the current instruction.

Treat explicit scope, editable files, requested validation, review or
publication boundaries, stop conditions, and `must` / `must not` instructions
as constraints. A path or specifically requested integrity check is binding
when the current owner instruction makes it so; neither is a universal workflow
requirement.

If an instruction conflicts with the corrected master, accepted repository
behavior that the selected work must preserve, or a required safety boundary,
identify the specific conflict and stop. Never silently substitute a broader,
narrower, or supposedly equivalent action.

Before reporting completion, compare the work actually performed with the
instruction. Correct an in-scope mismatch or report it honestly.

## Precise Terminology

Use precise, accurate terminology throughout the repository, including code,
tests, filenames, directories, configuration, logs, errors, and documentation.
Name a concrete service such as Cloudflare R2, Stripe, or Firebase when the
implementation or interface is service-specific. Retain generic terms such as
`provider` only for genuinely shared functionality, established external
interfaces, or service-independent abstractions. Production-readiness pass IDs
belong in historical artifacts and `pytest.mark.pass_provenance`; they must not
substitute for behavioral names in active source or tests.

Use these terms consistently:

- **Requirement source** means the corrected master, an applicable current
  product requirement, an explicit owner decision, or an applicable technical
  standard. Name the source instead of using an unexplained phrase such as
  `current authority` or `higher authority`.
- **Reviewed plan** means the Gate A plan or planning record approved for the
  current implementation. A draft or corrected plan awaiting review is not a
  reviewed plan.
- **Verification method** means a test, source inspection, migration check,
  build, provider exercise, or operational exercise used to establish a stated
  result. **Validation results** report only methods actually run and what was
  observed.
- **External evidence** means information about provider, deployment, runtime,
  or operational state that repository content cannot establish. Source code
  may define how to obtain or interpret it, but cannot prove the external state.
- **Review result** is the reviewer's source-backed conclusion for a specific
  requirement, behavior, or affected item. It is distinct from the files that
  define the requirement and from the verification method inspected or rerun.

## Planning Artifacts

Stage 0 scope/reconciliation/decomposition and Gate A engineering planning and
plan review are required first-time workflow responsibilities. Durable intake
and plan documents are optional unless the current instruction or the work
requires them. When Gate A creates a durable plan, use the current
`planning/templates/PASS-PLANNING-TEMPLATE.md` as its required structure. Keep
the plan current and route a material scope change back to Stage 0 or Gate A
before implementation continues.

Do not routinely calculate, freeze, compare, record, or verify SHAs or other
hashes for baselines, intakes, plans, or artifacts. Normal Git commit identity
continues to exist through ordinary repository work. Existing historical hashes
may remain as provenance, and a current instruction may require a specific
integrity check, but hash bookkeeping is not production-readiness workflow.

## Current Session Context

Determine current work from the accepted repository state, the complete current
change set, the corrected master, the execution register, and the current owner
instruction. Treat local notes or prior-session summaries as orientation only
and verify them before relying on them.

Do not require or maintain a custom handoff bundle. Never place secrets,
personal data, payment data, raw logs, or provider-private values in session
notes.

## Tracked-Documentation Safety

Tracked production-readiness documentation may contain:

- repository-relative paths;
- architecture and system descriptions;
- requirements and technical identifiers;
- sanitized verification and validation summaries;
- public provider names;
- normal Git branch or commit references when they are genuinely useful;
- historical artifact hashes already retained as provenance, without adding
  routine hash bookkeeping to new work.

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

## Documentation Areas

### Current Scope, Requirements, And Routing

- the corrected master blueprint;
- this read-first entry point and Program Context;
- the execution register;
- implementation and recheck workflow guidance;
- `planning/templates/PASS-PLANNING-TEMPLATE.md` when Gate A creates a durable
  plan;
- `planning/templates/PASS-PR-DESCRIPTION-TEMPLATE.md` when implementation Gate
  D publishes a production-readiness PR.

### Supporting Or Historical Context

- `governance/`, `audit-research/`, and `decisions/`;
- the old remediation plan;
- existing pass intakes and plans.

Supporting or historical material remains useful when relevant, but it is not a
second source of production-readiness scope.

## Excluded Intentionally

Current routing does not require superseded decision inventories, draft
remediation plans, correction prompts, Codex implementation prompts, temporary
input packages, ZIP archives from earlier planning work, or local
current-session handoff files.

## Execution And Publication Boundary

Reading these documents does not authorize implementation, provider mutation, or
publication. Follow the current owner instruction.

Implementation and review do not automatically authorize Git publication.
Stage, commit, push, and create or update a PR only when requested after the
change set is ready and independently reviewed. Inspect the exact diff and
staged files, protect sensitive information, avoid destructive history changes
and force-pushes, and leave the PR open.

PR merge remains a deliberate manual repository action.

After a manual merge, follow the implementation workflow's post-merge sequence:
verify the intended merge, return local `develop` to current `origin/develop`,
confirm that the Gate D execution-register update landed in its intended final
state, and then select the next eligible unit from current requirements,
dependencies, accepted repository state, and owner direction. Do not make a
second routine register update for the same pass; correct the register only as
exceptional cleanup if publication failed or accepted repository state differs
from the intended state. If the next unit is a later child of a recorded
decomposition that remains valid, it begins at Gate A rather than repeating
Stage 0.

Separate explicit authorization is required for destructive or irreversible
provider, runtime, database, deployment, credential, or real-data operations
unless the current instruction already and unambiguously authorizes that exact
action.

If the current instruction conflicts with the corrected master, accepted
repository behavior that must be preserved, or a required safety boundary,
identify the specific conflict and stop.
