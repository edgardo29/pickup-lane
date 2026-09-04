# Pickup Lane Production-Readiness Entry Point

This is the single entry point for Pickup Lane production-readiness work. It
owns startup, authority, workflow selection, repository safety, and publication
boundaries.

The corrected master blueprint owns current production-readiness scope and
roadmap. This document does not maintain mutable branch, SHA, or current-pass
status.

## Current Execution State

Determine current execution state from:

1. current accepted `origin/develop`;
2. current local repository state;
3. `planning/program/PASS-EXECUTION-REGISTER.md`;
4. the current production-readiness run instruction.

Do not rely on historical baseline SHAs, branch names, prior PRs, or chat
history as current execution state.

## Initial Reading Order

Before production-readiness work:

1. Read this document.
2. Read `01-PROGRAM-CONTEXT.md`.
3. Read
   `planning/program/pickup-lane-master-production-readiness-blueprint.md`.
4. Check `planning/program/PASS-EXECUTION-REGISTER.md` for factual accepted,
   unmerged, and remaining-work state.
5. Select the implementation or recheck workflow.
6. Inspect current repository truth and read only the plans, technical standards,
   product documents, provider records, or historical material relevant to the
   selected work.
7. Verify current Git state, baseline, branch, intended scope, and staged state
   before editing.

Historical plans, SHAs, audits, remediation documents, decisions, templates,
and local session notes are optional context, not mandatory inputs or authority
over the corrected master.

## Workflow Selection

Use `PASS-IMPLEMENTATION-WORKFLOW.md` when a pass is being implemented for the
first time from current authority and current accepted `develop`.

Use `PASS-RECHECK-WORKFLOW.md` when a pass already accepted into `develop`, or
historical implementation that predates the current workflow, is being
revalidated against current authority, source, and evidence standards.

When workflow selection is unclear, stop and report the ambiguity instead of
inventing a hybrid process.

## Workflow Roles And Progression

The familiar workflow roles remain available:

```text
SCOPE / STAGE 0 WHEN DECOMPOSITION IS NEEDED
-> PLAN / GATE A WHEN COMPLEXITY WARRANTS IT
-> IMPLEMENT AND TEST / GATE B
-> INDEPENDENT SEMANTIC REVIEW / GATE C
-> GIT AND PR FINALIZATION / GATE D
-> MANUAL MERGE
```

These labels do not create automatic orchestration. Stage 0 and Gate A are
optional. A user instruction authorizes only the work and boundaries it
actually states.

Select work from the corrected master, current repository truth, real
prerequisites, late-bound triggers, the factual execution register, and owner
direction. Do not select work from old pass ordering, filename order, stale
branches, historical SHAs, or prior chat. When several units are valid and no
real dependency selects one, ask the owner.

A deferred provider/runtime obligation stays visible and incomplete but blocks
only work that genuinely depends on its missing facts.

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

When scoping, planning, or implementing work:

- separate work that can be completed provider-independently from work that
  depends on final provider, topology, runtime, or configuration facts;
- complete coherent provider-independent work now when possible, including
  source interfaces, generic configuration contracts, validation, portable
  behavior, formulas, synthetic test fixtures, and later-verification rules;
- do not invent, copy, or promote final production values from temporary
  providers, README examples, local or CI settings, free-tier defaults,
  framework defaults, or temporary deployments;
- defer work that requires the actual final infrastructure, including concrete
  provider plan/tier/region/capacity, provider-native deployment settings,
  project or account binding, DNS/TLS/proxy/edge settings, instance/process
  counts, autoscaling or rolling-overlap facts, provider-dependent pool or
  capacity values, concrete production roles or grants, final numeric values
  that depend on provider characteristics, and provider/runtime proof;
- when one unit contains both kinds of work, separate the executable-now work
  from a deferred follow-up rather than forcing an early infrastructure choice
  or blocking unrelated work;
- every deferred follow-up must record its owning pass or unit, exact trigger,
  preserved obligations, dependencies, latest required completion boundary, and
  execution-register visibility;
- deferred work is not proof and does not complete the affected requirement.
  Run it as soon as its trigger is satisfied and no later than the earliest
  downstream pass that truly needs the deferred facts or `CLOSE-01`, whichever
  comes first;
- downstream work may continue only when its own prerequisites do not require
  the deferred provider/runtime facts. If it does require them, stop on that
  specific prerequisite instead of inventing or substituting temporary values.

The master blueprint must make known final-infrastructure-dependent passes or
pass portions visible before normal progression reaches them, including the
required trigger or late-bound placement. The execution register records later
accepted decomposition, deferred units, and trigger state. Do not wait until
implementation to discover that a unit requires intentionally unselected
production infrastructure.

This rule does not prohibit existing provider-specific product integrations that
are already fixed by higher authority, nor does it prohibit portable
provider-neutral configuration interfaces. It governs final infrastructure
selection and concrete production configuration or evidence that depends on
that selection. If higher authority explicitly locks a permanent provider,
follow that authority, but do not invent concrete production values without the
required evidence.

## Authority Order

Use this distinction:

1. The corrected master blueprint defines current production-readiness scope,
   correction targets, remaining roadmap, boundaries, and completion criteria.
2. Applicable current product requirements and explicit owner decisions define
   product behavior where the master delegates or does not decide it.
3. Current accepted source, configuration, tests, migrations, and documentation
   define what currently exists and behaves.
4. The execution register records factual implementation state.

Historical audits, the old remediation plan, governance records, decision
records, intakes, pass plans, SHAs, PR descriptions, and Git history are
provenance or supporting context. They may explain past decisions and useful
technical contracts, but they may not override the corrected master or restore
scope it rejects.

When implementation conflicts with current authority, report and correct the
mismatch within the selected scope. Stop for a genuine unresolved conflict or
owner decision; do not guess.

## Existing Tests

Evaluate every existing test by usefulness, correctness, isolation, and the
behavior it proves. A `legacy/` path does not make a test nonexistent, and a
preferred directory does not make a test authoritative.

## Instruction Adherence

Before acting, resolve the binding requirements of the current instruction.

Treat explicit scope, editable files, requested validation, review or
publication boundaries, stop conditions, and `must` / `must not` instructions
as constraints. A path or SHA is binding when the current owner instruction
specifically makes it so; neither is a universal workflow requirement.

If an instruction conflicts with the corrected master, repository truth, or a
required safety boundary, stop and report the issue. Never silently substitute
a broader, narrower, or supposedly equivalent action.

Before reporting completion, compare the work actually performed with the
instruction. Correct an in-scope mismatch or report it honestly.

## Planning Artifacts

Intakes and plans are optional tools for work that needs decomposition or a
durable engineering design. When used, keep them current and route a material
scope change back to scoping or planning before implementation continues.

Historical artifact SHAs may be retained as provenance or used when a specific
instruction requests an integrity check. They are not mandatory production-
readiness infrastructure.

## Current Session Context

Determine current work from Git, the corrected master, the execution register,
and the current owner instruction. Treat local notes or prior-session summaries
as orientation only and verify them before relying on them.

Do not require or maintain a custom handoff bundle. Never place secrets,
personal data, payment data, raw logs, or provider-private values in session
notes.

## Tracked-Documentation Safety

Tracked production-readiness documentation may contain:

- repository-relative paths;
- architecture and system descriptions;
- requirements and technical identifiers;
- sanitized evidence and validation summaries;
- public provider names;
- pass-specific branches, baselines, commits, or artifact hashes only when they
  are genuinely useful.

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

### Current Authority And Routing

- the corrected master blueprint;
- this read-first entry point and Program Context;
- the execution register;
- implementation and recheck workflow guidance.

### Supporting Or Historical Context

- `governance/`, `audit-research/`, and `decisions/`;
- the old remediation plan;
- existing pass intakes and plans;
- optional planning and PR templates.

Supporting or historical material remains useful when relevant, but it is not a
second production-readiness scope authority.

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

Separate explicit authorization is required for destructive or irreversible
provider, runtime, database, deployment, credential, or real-data operations
unless the current instruction already and unambiguously authorizes that exact
action.

If the current instruction conflicts with the corrected master, repository
truth, or a required safety boundary, stop and report the conflict.
