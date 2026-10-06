# Production-Readiness Pass Implementation Workflow

This document defines the reusable process for implementing a Pickup Lane
production-readiness pass for the first time from current requirements and
accepted `develop`.

Use this workflow for forward implementation work and for correction rounds on
the same unmerged first-time executable pass. Use
`docs/production-readiness/planning/workflows/PASS-RECHECK-WORKFLOW.md` only
when a pass already merged into `develop`, or historical implementation that
predates the current workflow, is later revalidated or repaired against current
requirements and accepted repository state.

This workflow is process guidance only. It does not define product behavior and
does not override the requirement-source priority in
`docs/production-readiness/00-READ-ME-FIRST.md`.

The familiar workflow roles are:

```text
STAGE 0: SCOPE, RECONCILIATION, AND DECOMPOSITION DECISION
-> GATE A: ENGINEERING PLAN AND REVIEW
-> GATE B: IMPLEMENTATION AND RISK-BASED VERIFICATION
-> GATE C: INDEPENDENT SEMANTIC REVIEW
-> GATE D: GIT AND PR FINALIZATION + EXECUTION-REGISTER UPDATE
-> MANUAL MERGE
```

Every first-time corrected-master unit receives Stage 0 scope and decomposition
work before implementation begins. A recorded parent decomposition satisfies
Stage 0 for its later children while current requirements, dependencies, and
accepted repository behavior still support it; each child still performs Gate
A. Stage 0 may decide that no decomposition is required, and Gate A may use a
concise plan for straightforward work. A durable intake or plan artifact is
required only when the current instruction or the work itself needs one.

This sequence does not create automatic orchestration. Each stage begins only
under the current instruction and obeys its own edit, publication, and stop
boundaries. The corrected master defines production-readiness scope; this
workflow only organizes execution.

## 1. Purpose And Applicability

Use this workflow when a production-readiness pass is being implemented as a
new executable pass rather than rechecked after prior implementation.

The workflow applies when:

- the corrected master blueprint contains a selected roadmap unit;
- current accepted `develop` is the implementation starting point;
- no previously merged or currently selected executable child owns the specific
  scope;
- the task is to design, implement, verify, review, and publish the pass for the
  first time.

Do not use this workflow to:

- revalidate a pass already merged into `develop`, or historical
  implementation predating the current workflow;
- repair a pass already merged into `develop`;
- perform unrelated documentation or repository housekeeping;
- choose a next parent or child from filename order, stale chat context, or any
  source other than current requirement sources and recorded dependency state;
- mutate providers, databases, deployments, credentials, or runtime settings
  unless the current executable pass and a named requirement source explicitly
  authorize that action.

## 2. Requirement And Current-State Principle

Forward implementation follows this reasoning order:

```text
CORRECTED MASTER BLUEPRINT AND APPLICABLE CURRENT REQUIREMENTS
-> ACCEPTED REPOSITORY STATE AND CURRENT CHANGE SET
-> STAGE 0 SCOPE AND EXECUTABLE-BOUNDARY DECISION
-> GATE A ENGINEERING PLAN AND PLAN REVIEW
-> IMPLEMENTATION AND RISK-BASED VERIFICATION
-> VALIDATION AND INDEPENDENT REVIEW
```

The corrected master blueprint controls current production-readiness
scope and roadmap. Historical audits, remediation plans, decisions, pass plans,
and SHAs may explain earlier work but do not override it.

When a parent pass is too broad, Stage 0 decomposes it into one or more
bounded executable child passes. The child pass must preserve the parent pass
intent, surviving requirements, dependencies, and verification boundaries while
remaining small enough for meaningful implementation and review.

The **accepted repository state** is the source, configuration, tests,
migrations, and documentation in current accepted `develop`. The **current
change set** is every branch change relative to that accepted starting point,
including branch commits, staged and unstaged changes, and applicable untracked
files. Do not treat the current change set as accepted before merge. Existing
source and tests establish current behavior but do not define requirements by
themselves.

The corrected master, applicable current product requirements, explicit owner
decisions, and applicable technical standards state what must be true. Accepted
repository state establishes what already exists; the current change set shows
what this branch proposes to alter. Stage 0 defines the executable boundary,
including a decision to execute the selected unit whole, and Gate A records and
reviews the engineering approach, risks, and planned verification. Gate B
implements and tests the selected work; it does not create requirements.

## 3. Workflow Selection

Before starting pass work, determine the workflow.

| Situation | Workflow |
|---|---|
| The pass is already merged into `develop` and is being revalidated or repaired later. | `docs/production-readiness/planning/workflows/PASS-RECHECK-WORKFLOW.md` |
| The pass is being implemented for the first time from current requirements. | This document |
| A completed Gate C found a defect in the same unmerged first-time pass. | Scoped correction under this implementation workflow, followed by correction validation and a new full Gate C review |
| The task is global workflow maintenance, documentation navigation, or register maintenance. | The explicit task prompt, not a production-readiness implementation pass |

If the workflow is unclear, stop and report the ambiguity. Do not choose the
next pass or workflow from filename order. Select work from the corrected master,
real dependencies, accepted repository state, and owner direction.

## 4. Shared Rules For All Stages

Every stage must:

- start from a clean, understood Git state;
- apply the requirement-source priority from the read-first document;
- apply the instruction-adherence rule from the read-first document to the
  current run instruction before acting;
- read any applicable scoping or planning artifact when one exists;
- treat explicit scope, editable files, paths, validation requirements,
  stage or gate boundaries, and stop conditions from the current instruction as
  binding constraints;
- evaluate existing tests by usefulness and correctness rather than directory
  labels;
- distinguish accepted repository state, the current change set, requirement
  sources, provenance, inference, external evidence, and unknown facts;
- keep provider/runtime/control-plane facts unknown until the required external
  evidence is available and has been verified for the current work;
- apply the final-infrastructure timing rule from the
  read-first document: temporary Vercel, Render, and Neon demo infrastructure
  must not become permanent production architecture, and concrete production
  values that depend on final infrastructure remain late-bound until that
  infrastructure is selected;
- protect secrets, local paths, provider-private data, payment data, and
  personal data;
- stop rather than guess when requirement ownership, external facts, or scope is
  ambiguous, when the current instruction cannot be followed exactly, or when it
  conflicts with a named requirement source or accepted behavior that must be
  preserved.

A short assignment may identify only the selected work and its current stage or
gate. Start at `docs/production-readiness/00-READ-ME-FIRST.md`, use
`docs/production-readiness/01-PROGRAM-CONTEXT.md` as the navigation map, and use
the applicable section below to find the additional documents needed for that
stage. Individual prompts do not need to repeat this document stack.

When this workflow requires complete coverage, apply these terms concretely:

- An **affected closed set** is a bounded list obtained from an enum, database
  constraint, operation registry, configuration schema, state table, explicit
  requirement list, or another repository source that defines its members.
  Identify every member and its treatment. Do not sample it.
- For inputs without a bounded member list, identify every
  **behavior-changing condition**: a condition that changes the result, public
  response, persisted or external side effect, authorization decision, retry,
  cleanup, transaction handling, or recovery behavior. The workflow does not
  require arbitrary combinations that cannot change behavior.
- A **related path** is relevant when it shares the changed interface or
  invariant: it calls the changed function, produces or consumes the changed
  value, reads or writes the changed database field, applies the same policy or
  external-service outcome, or represents the same behavior through another
  API, worker, serializer, UI, or display path. Words such as `sibling`,
  `equivalent`, or `adjacent` do not expand review beyond that connection.
- A **verification method** is a test, source inspection, migration check,
  build, provider exercise, or operational exercise. A **validation result**
  states what was actually run and observed. A **review result** records the
  specific requirement or affected item, its implementation path, the
  verification inspected or rerun, and the reviewer's conclusion.

Do not routinely calculate, freeze, compare, record, or verify SHAs or other
hashes for Git baselines, intakes, plans, or artifacts. Normal branch, worktree,
index, HEAD, upstream, and merge-base safety checks remain required. Git commit
identity continues to exist through ordinary repository work, and a current
owner instruction may still require a specific integrity check, but artifact-
hash bookkeeping is not part of this workflow.

Before reporting completion, compare the actual work performed
against the binding current instruction. Correct any in-scope mismatch before
reporting, or report the mismatch and stop.

## 5. Forward-Pass Initialization

Before implementation work edits repository content, initialize from current
accepted `develop` unless the current instruction explicitly establishes a
different understood starting point.

Required initialization:

1. fetch remote metadata safely;
2. verify the worktree and index are clean or explicitly understood;
3. switch to local `develop`;
4. run a fast-forward-only update from `origin/develop`;
5. verify local `develop` equals `origin/develop`; this is the accepted starting
   state, without separately recording a baseline hash;
6. create or switch to the local working branch specified by the user or current
   task; when no different branch name is mandated, `pr/<EXECUTABLE-PASS-ID>`
   remains a useful convention;
7. use that branch through implementation, review, and publication unless an
   explicitly authorized change requires another branch;
8. do not push merely for branch creation.

Unexpected local work, divergence, worktree conflict, or branch ambiguity causes
a stop. Do not automatically reset, rebase, merge, stash, restore, clean, or
delete anything.

If preserved local work such as a stash is later restored or converted into
commit-eligible pass artifacts, recheck it for prohibited sensitive material
under the read-first document before continuing.

Stage 0 and Gate A edit only planning artifacts authorized by the current
instruction. They do not stage, commit, push, create a PR, or update a PR.
They also do not update the execution register merely to record the current
pass's transient progress. Publication and the normal execution-register update
remain Gate D work after independent review.

## 6. STAGE 0: Scope, Reconciliation, And Decomposition Decision

Perform Stage 0 before first executable work under a selected first-time
corrected-master unit. It reconciles scope with accepted repository state, then
decides whether the unit executes whole, decomposes into coherent children, or
needs a split between work independent of final infrastructure selection and
mandatory deferred work. Do not repeat Stage 0 for a later child when a recorded
parent decomposition still matches current requirements, dependencies, and
accepted repository behavior. Return to Stage 0 if those facts invalidate the
decomposition or executable boundary. A no-decomposition decision is a
valid Stage 0 result. Stage 0 does not edit production code, tests, provider
settings, migrations, or runtime configuration. A reusable intake document is
optional; use an existing intake template only when the current instruction or
the work requires a durable intake record.

### 6.1 Inputs

Read:

- the read-first document and program context;
- this workflow;
- `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md`;
- the relevant master blueprint parent pass entry;
- historical remediation, decision, and pass records only when useful as
  provenance or technical context;
- prerequisite behavior already merged into `develop` and its verification
  boundaries;
- accepted repository state for the area;
- applicable engineering and testing standards.

### 6.2 Parent-Pass Reconciliation

For the selected parent blueprint pass, answer:

- What surviving requirements, decisions, dependencies, and verification
  obligations does the parent pass cover?
- Which parts were implemented by earlier passes already merged into `develop`?
- Which parts require repository changes now; which require an external-service,
  deployed-runtime, migration, or operational action; and which have a named
  later pass or owner?
- Which parts need source implementation now?
- Which parts require facts from an external service or deployed runtime before
  source implementation can be specified honestly?
- Which parts depend specifically on final hosting, database hosting, edge,
  runtime, provider topology, provider plan/capacity, provider-native settings,
  concrete production roles/grants, or other intentionally late-bound
  infrastructure facts?
- Which parts are independent of final infrastructure selection and can be
  completed now through portable source behavior, generic configuration
  interfaces, validation, formulas, focused verification, or synthetic fixtures?
- Which parts are too broad to implement and review in one PR?
- Which prerequisite interfaces, behaviors, and invariants must be preserved?

Do not modify the master blueprint to make the decomposition easier. If the
blueprint already identifies a final-infrastructure dependency, Stage 0 must
apply it. If a current requirement source reveals an unrecorded material
infrastructure dependency, preserve it in the intake/register and route any
needed blueprint correction through the appropriate program-documentation
change rather than pretending the dependency does not exist.

### 6.3 Final-Infrastructure Timing Check

Before choosing an executable boundary, Stage 0 must classify every material
infrastructure/runtime/configuration requirement as one of:

- independent of final infrastructure selection and executable now;
- dependent on already selected infrastructure whose required facts have been
  verified;
- dependent on intentionally unselected final infrastructure and therefore
  mandatory deferred work.

Current Vercel frontend hosting, Render API hosting, and Neon PostgreSQL hosting
are temporary development/demo infrastructure. Their accepted repository
integration and observed demo behavior may be inspected when relevant, but
their provider-specific settings, limits, topology, plan characteristics, and
runtime observations must not be used as
final production assumptions unless the corrected master or an explicit owner
decision later selects them as permanent production providers and the required
external facts have been verified.

A generic setting or configuration interface may be implemented now when its
existence, validation, and semantics are independent of final infrastructure
selection. Concrete production values remain deferred when they depend on the
final infrastructure provider or topology. Never populate them from README
examples, local/CI configuration, free-tier defaults, framework defaults, or
temporary deployment values.

When one parent combines executable-now work with final-infrastructure-dependent
work, Stage 0 must separate them. Prefer a coherent current executable child or
children plus a mandatory deferred follow-up rather than forcing an early
infrastructure choice or blocking unrelated downstream engineering.

Every mandatory deferred follow-up must record:

- one owning pass or executable unit;
- the preserved parent requirements and verification obligations;
- the exact trigger that makes the work executable;
- prerequisites and downstream consumers;
- the latest required completion boundary;
- execution-register visibility;
- an explicit statement that deferred status is not verification or completion.

Run deferred work as soon as its trigger is satisfied and no later than the
earliest downstream pass that genuinely needs the deferred facts or `CLOSE-01`,
whichever comes first. Downstream work may proceed while the trigger is false
only when its own prerequisites do not depend on those deferred facts.

### 6.4 Decomposition Decision

Choose one of these outcomes:

| Outcome | Meaning |
|---|---|
| Implement parent as one executable pass | The parent pass is narrow enough to plan, implement, verify, review, and publish as one coherent PR. |
| Decompose into ordered child passes | The parent pass is too broad. Stage 0 defines child pass IDs, order, scope, dependencies, and non-overlap. |
| Decompose current work plus mandatory deferred follow-up | A coherent result independent of final infrastructure selection can be completed now, but another obligation requires intentionally unselected final infrastructure. Stage 0 defines the current executable unit plus the deferred owner, trigger, preserved obligations, dependencies, and latest completion boundary. |
| Stop for prerequisite | A prerequisite required by the current executable work is genuinely missing and cannot be deferred without making the current result false or unsafe. |
| Stop for owner decision | Existing requirement sources cannot decide a product, security, operational, or policy question. |

Child pass IDs must be stable and must preserve the parent ID prefix where
practical, for example `WS03-03A` and `WS03-03B`.

### 6.5 Executable-Pass Cohesion Test

Stage 0 must assess every proposed executable pass against this cohesion test.

| Cohesion question | Required record |
|---|---|
| One primary outcome | Verdict, supporting facts, and split implication. |
| One coherent requirement/invariant family | Verdict, supporting facts, and split implication. |
| One prerequisite state | Verdict, supporting facts, and split implication. |
| One safe merge/rollback or forward-fix unit | Verdict, supporting facts, and split implication. |
| One coherent set of verification methods | Verdict, supporting facts, and split implication. |
| One coherent semantic-review scope | Verdict, supporting facts, and split implication. |
| Safe and useful intermediate state | Verdict, supporting facts, and split implication. |

Split the parent or candidate child when either of these is false:

- one prerequisite state;
- one safe merge/rollback or forward-fix unit.

Normally recommend a split when two or more of the other cohesion questions
fail.

These are warning signals only, not automatic split rules:

- file count;
- changed-line count;
- requirement count;
- test count;
- frontend plus backend;
- prompt length.

### 6.6 Split Boundaries

Good split reasons include:

- separate production outcomes;
- sequential foundation and consumer work;
- separate schema/migration phases;
- external-service source support versus external-service activation;
- separate rollback units;
- independently blocked components;
- different named requirement or operational owners;
- distinct failure/recovery models.

Do not split one coherent feature into artificial backend, frontend, testing,
or documentation passes. Required frontend behavior, production behavior,
relevant tests, and compatibility verification travel with the interface or
invariant they establish.

Do not permit an unsafe partial merge merely to create smaller PRs.

### 6.7 Child-Pass Rules

When a parent is split:

- the parent is an umbrella and is not implemented directly;
- every child is an executable pass;
- every child is planned at a level appropriate to its complexity and receives
  the complete Gate C review required by Section 9;
- each later child starts from accepted `develop` after earlier required
  children merge;
- no later child blindly reuses a detailed plan designed against an older
  baseline;
- immediate child progression includes only children whose prerequisites and
  execution triggers are satisfied;
- a recorded mandatory deferred follow-up with an unmet
  final-infrastructure trigger remains visible but is not treated as the next
  executable child merely because earlier children completed;
- the work independent of final infrastructure selection may be complete for
  downstream engineering without treating deferred infrastructure/runtime
  verification as complete;
- the parent or affected requirements must not be represented as fully production
  verified while a mandatory deferred obligation remains outstanding;
- every parent obligation remains accounted for through children already merged
  into `develop`, the current selected child, or an explicitly recorded
  mandatory deferred owner.

If planning discovers that a child is still too broad, or that its
completion criteria require intentionally unselected final infrastructure not
properly separated by Stage 0, stop and return to Stage 0.

### 6.8 No-Gap / No-Overlap Rule

Stage 0 must enforce:

```text
UNION OF CHILD OWNERSHIP = COMPLETE PARENT OWNERSHIP
```

and:

```text
CHILD OWNERSHIP INTERSECTION = EMPTY
```

except for explicitly documented shared prerequisites, compatibility
regression responsibility, or verification that intentionally applies to more
than one child.

Every parent requirement must have one primary implementing child,
one clearly named verification or operational owner, or one mandatory deferred
follow-up with an exact trigger and latest completion boundary. No obligation
may disappear between children, be treated as complete because its trigger
is false, or be replaced with facts from temporary infrastructure.

### 6.9 Intake Record Storage And Publication

When a durable intake record is useful, use the existing pass-family structure:

```text
docs/production-readiness/planning/passes/<family>/<parent-id>-intake.md
```

Do not create retroactive intake documents for historical splits already merged
into `develop`, such as WS02-04, WS02-05, or WS03-03.

Stage 0 may create or update only the intake record authorized by its current
task. Record the selected structure, scope allocation, prerequisites, and
deferred obligations. Historical decompositions do not require retroactive
intake records. If an intake record is created, normally publish it with the
substantive work it supports rather than in a tracker-only PR.

### 6.10 Stage 0 Completion And Progression

Stage 0 returns:

- selected parent blueprint pass;
- selected executable pass ID and title;
- decomposition decision and rationale;
- parent-to-child scope map when applicable;
- cohesion-test verdicts and split implications;
- no-gap/no-overlap obligation allocation;
- dependencies and prerequisite state;
- expected verification methods and the results each must establish;
- expected non-goals and external boundaries;
- final-infrastructure dependency classification;
- mandatory deferred follow-up owner, trigger, preserved obligations,
  dependencies, and latest completion boundary when applicable;
- intake-record path when applicable;
- exact recorded executable structure, including parent/child allocation when
  decomposed;
- blockers.

Stage 0 does not automatically start later work. The next action follows the
corrected master, actual prerequisites, accepted repository state, and owner
direction. A later child whose recorded decomposition remains sound begins at
Gate A; do not rerun Stage 0 merely because an earlier child merged.

A mandatory deferred follow-up whose final-infrastructure trigger is false is
not a current executable child. Keep it visible in the intake and execution
register, preserve its obligations as open, and continue only to downstream work
whose own prerequisites do not require those deferred facts. When the trigger
becomes true, the deferred unit becomes eligible for planning and implementation
and must run no later than its recorded completion boundary.

When all currently executable child obligations are complete, determine
progression from the corrected master, execution register, real dependency
state, deferred-trigger state, accepted repository state, and owner direction.
Do not mark deferred infrastructure/runtime obligations as verified merely to
advance. If multiple units are valid and no real dependency selects one, stop
for owner selection instead of inventing priority.

## 7. GATE A: Engineering Plan And Review

Perform Gate A for every selected first-time executable unit. Create and review
an engineering plan before implementation; keep it concise when the work is
straightforward. A durable standalone plan document is required only when the
current instruction or the work itself requires one, not merely because the unit
has an old pass ID or historical plan.

Start from the recorded Stage 0 result or intake, the corrected-master scope,
the execution register, accepted repository state, prerequisite interfaces,
behaviors, and invariants already merged into `develop`, and the applicable
engineering and testing standards routed through Program Context. For a later
child of a still-valid recorded decomposition, Gate A is the starting stage and
must re-evaluate the child plan against accepted `develop` without repeating
Stage 0.

When Gate A creates a durable planning document, use
`docs/production-readiness/planning/templates/PASS-PLANNING-TEMPLATE.md` as the
required plan structure. Gate A may edit only the planning artifacts authorized
by the current instruction. It does not edit production code, tests, migrations,
configuration, or provider state.

### 7.1 Planning Responsibilities

The plan must:

- reconcile the selected unit with the corrected master, accepted repository
  state, and any existing current change set;
- define the intended behavior, important invariants, ownership, and non-goals;
- identify affected callers, interfaces, persistence, migrations, provider
  boundaries, and compatibility expectations;
- explain transaction, concurrency, retry, rollback, and failure behavior where
  relevant;
- identify security, privacy, authorization, payment, and sensitive-data risks;
- distinguish work independent of final infrastructure selection from facts that
  remain late-bound;
- choose realistic verification methods and focused validation;
- remain small enough for one coherent implementation and review.

For every affected closed set, and every requirement that applies across more
than one operation or representation, identify all applicable items and the
planned treatment of every member, including members intentionally unchanged or
inapplicable. Members with identical planned treatment may be grouped only when
every member is identified and its treatment is explicit. Include all affected
requirements, behaviors, and repository elements, not only those near the
expected edits.
This includes, when present:

- states, transitions, terminal conditions, and historical behavior;
- provider operations and their success, pending, rejection, transient,
  unknown, malformed, and configuration outcomes;
- identifiers, idempotency keys, uniqueness constraints, replay equivalence,
  and collision behavior;
- values or result tokens introduced or changed by the plan and every producer
  and consumer of each value;
- persisted representations, database tables and columns, constraints, schemas,
  migrations, transactions, locks, and rollback behavior;
- configuration settings and fields, defaults, feature flags, and the code that
  reads or writes them;
- affected interfaces, policy rules, registry entries, metrics, diagnostic
  fields, logs, and compatibility requirements; and
- the verification method and observable result that will establish each
  material behavior.

Record these affected sets and multi-path requirements in the relevant
requirements, design, failure, or testing section. No separate checklist or
process-administration artifact is required. Do not sample a closed set or leave
any member for Gate B to classify. Identify the actual operations and
external services involved; a shared helper or error handler does not establish
that every calling operation has the same required outcome. For each applicable
operation and outcome, specify the required effects, prohibited effects, error
handling, recovery, and relevant timing or competing-operation behavior.
Identify the planned verification and what it must establish, including
persisted or absent side effects when those determine correctness. State why a
member or category is intentionally unchanged or inapplicable; do not leave its
treatment implicit. For open-ended inputs, use the behavior-changing conditions
defined in Section 4; do not require arbitrary combinations of unrelated inputs.

Gate A must resolve contradictory plan statements and engineering choices by
checking the applicable requirements, current source, prerequisite behavior
already merged into `develop`, and engineering and testing standards. When
several implementation approaches satisfy them, select and document one
coherent technical design in Gate A;
ordinary engineering choices do not require an owner decision. If the conflict
instead exposes a genuinely missing product, security, policy, operational, or
other designated owner decision that the existing requirement sources cannot
resolve, stop and route that exact question to the responsible owner. Do not
pass an unresolved contradiction to Gate B, encode one interpretation in tests,
or let Gate C choose a preferred interpretation after implementation.

The planning template defines structure and authoring quality for a durable
plan; it does not define scope or override current requirement sources. Existing
plans and historical records remain supporting artifacts rather than a separate
source of production-readiness requirements.

### 7.2 Impact And Compatibility Review

Before the plan is ready for review, trace every proposed behavior and design
change through the current surrounding system. Inspect the actual producers,
callers, entry points, persisted representations, direct and downstream
consumers, state transitions, constraints, policies, registries, metrics,
diagnostics, external-service boundaries, failure paths, tests, and preserved
interfaces or invariants that the change affects. Include routes, schemas,
settings, middleware, migrations, frontend behavior, or other representations
when they participate in that chain.

For every state, result token, identity, operation, interface, or persisted
field that the plan introduces or changes, identify all current producers and
consumers and define their resulting behavior. Trace every affected operation,
related code path, configuration or database element, policy, diagnostic field,
and other relevant representation. Proximity to an expected edit location is
not a boundary. Complete each affected closed set rather than sampling it, and
cover every behavior-changing condition for open-ended inputs.

A Gate A correction run must perform the same trace for every design decision it
adds or changes. Check every affected requirement and every member of its
closed set or multi-path requirement, including operations, outcomes, consumers,
configurations, database elements, policies, diagnostics, compatibility, and
verification. Correct every member that needs a change rather than only the
cited sentence or example; explicitly preserve members that remain unchanged.
This impact trace is part of producing an executable plan; it does not authorize
the author or corrector to approve the plan.

Before any authored or corrected plan is submitted for independent review, the
planner must reread the entire reviewed-plan candidate, or the complete current
planning record when no standalone plan is required, and perform a full
self-audit against every applicable responsibility in Sections 7.1 and 7.2.
This self-audit is not limited to the latest edits or to defects already found.
It must confirm the complete requirement, design, failure, compatibility, and
verification scope, then perform a second omission-focused pass looking
specifically for:

- required interfaces or invariants that remain unstated;
- missing failure, recovery, concurrency, retry, reconciliation, or
  unknown-outcome behavior;
- unaccounted caller, external-service, persistence, schema, configuration,
  operational, verification, or compatibility paths;
- material implementation choices still left for Gate B to invent; and
- related paths, as defined in Section 4, where the same design obligation has
  not been applied.

Finding and correcting several defects does not permit the planner to stop this
self-audit early. The plan is ready for independent review only after every
applicable responsibility and the omission-focused pass are complete. Its
requirements, design, and testing sections must let the independent reviewer
locate the planned treatment of every member of an affected closed set and the
intended behavior and planned verification for every applicable requirement.
Members with identical treatment may be grouped if each is identified.
An unresolved requirement, unspecified outcome, or unexplained missing
verification prevents review readiness; keep any explicitly permitted external
or later-pass verification open, with its named owner and completion condition.

### 7.3 Plan Review And Corrections

Gate A plan authoring or correction and Gate A plan review are separate runs. A
run that creates or changes the plan must stop when the plan candidate is ready
for review and cannot approve it. Review begins only in a later Gate A review
run; it does not occur in the same run that authored or corrected the plan.

The review run must use fresh context separate from the authoring or correction
context. It must derive its conclusions from current requirement sources,
accepted repository state, and the current change set rather than an authoring
report, prior review verdict, or correction summary. It must reread and identify
the fixed review requirements in its report:

- the corrected-master obligation;
- the recorded Stage 0 result or intake and selected executable boundary;
- the accepted repository starting point, complete current change set
  (committed branch changes, staged and unstaged changes, and applicable
  untracked files), and source needed to check the plan's claims;
- the execution register;
- every prerequisite interface, behavior, or invariant identified by a current
  requirement source, Stage 0, or affected accepted repository behavior;
- every engineering and testing standard that Program Context routes to for the
  plan's actual technical scope and, for a durable plan, the current planning
  template; and
- explicit owner decisions that govern the selected work.

The Gate A review requirements become fixed when the first complete plan review
begins. They consist of the corrected-master obligation, recorded executable
boundary, applicable prerequisite interfaces and invariants, applicable
standards, explicit owner decisions, and accepted repository behavior relevant
to those items. Plan corrections may change the plan, but they do not change
those review requirements.

A later review may identify a previously missed violation or consequence within
the fixed review requirements, but it must not move the completion bar,
introduce a new requirement, or reinterpret a preference as an obligation. If a
requirement source, accepted repository behavior, or an owner decision genuinely
changes the fixed review requirements, the review must identify that change
explicitly and route any resulting scope, design, or ownership consequence
before continuing.

Before reaching a verdict, build a source-backed review inventory from those
requirements. This inventory defines the items to inspect and report; it is not
a new permanent artifact. It must contain:

- every in-scope requirement, prerequisite interface or invariant, boundary,
  non-goal, and deferred obligation;
- every behavior, invariant, mechanism, failure case, and completion claim in
  the plan;
- every affected closed set and every requirement that applies across multiple
  operations or representations under Section 7.1, including configurations,
  database elements, policies, and diagnostics where applicable; and
- every actual producer, representation, consumer, and compatibility interface
  or invariant needed to verify those items.

Trace each inventory item through the governing source, plan requirement,
design, current producer, persisted or transmitted representation, every
consumer, failure and replay behavior, and planned verification. For each item,
record one review result in the Gate A report:

- `covered`: the complete chain is defined and consistent;
- `material finding`: the item satisfies the materiality rule below; or
- `inapplicable`: the category was evaluated and the report gives the concrete
  reason it does not apply.

For every affected closed set, verify the planned treatment of every member,
including members intentionally unchanged or inapplicable. The report must
expose every member and its result, or provide an equivalent source-backed
representation that makes every member's treatment and review result
verifiable. Members with identical treatment and review results may be grouped
only when every member is identified. An umbrella entry such as
`status population -> covered` is insufficient when it hides individual members.
This applies to affected sets such as state transitions, external-service
operations and outcomes, configuration fields, database constraints, policy
entries, diagnostic fields, result tokens, and affected readers and consumers.
It does not create a universal checklist, ledger, or separate artifact.

The coverage record belongs in the review report and does not require another
repository artifact. A review cannot claim complete coverage while an inventory
item is omitted, unresolved, or supported only by the plan's assertion. The
reviewer must verify that every applicable operation and materially distinct
outcome has unambiguous planned behavior and adequate planned verification,
rather than accepting a generic operation-level claim or a test count. Where
shared code serves multiple operations, verify each operation's required
behavior separately.

Confirm from this trace that deferred or out-of-scope work has not been pulled
into the pass, repository claims and affected paths are accurate, Gate B would
not need to invent a material design choice, and the proposed validation can
establish every material completion claim.

The reviewer must complete this entire applicable review scope from scratch
before issuing a semantic verdict. The review is never limited to the latest
edits, the latest correction, or previously reported findings. When one defect
suggests the same defect class may exist elsewhere, inspect every applicable
related operation, code path, configuration, database element, policy,
diagnostic, and other affected implementation or verification location before
concluding the review.

After the normal consistency trace, perform a final omission-focused pass using
the concerns in Section 7.2's planner self-audit. Finding enough defects to know
that corrections are required does not permit the review to stop; return all
independently discoverable material findings together rather than distributing
them across avoidable review rounds.

If a real blocker, tool or context limitation, missing requirement source,
inaccessible review material, or another applicable stop condition prevents
completion of the full review, report that limitation and return `blocked`. Do
not issue a semantic approval or present a partial review as complete.

A plan-review finding is material only when the review demonstrates at least
one of these conditions:

- a conflict with a current requirement source, accepted repository behavior,
  or a prerequisite interface or invariant;
- behavior or design required to implement an existing in-scope obligation is
  missing;
- the plan contains a scope gap, scope overlap, or unauthorized expansion;
- Gate B would have to invent a material implementation choice;
- the planned behavior is incompatible with an existing affected workflow; or
- the proposed validation cannot establish a material completion claim.

Each material finding must identify the governing requirement source or
repository behavior, the affected plan section, the conflicting or missing
design, its concrete consequence, and the exact correction route. A preference,
speculative hardening proposal, unsupported hypothetical, harmless alternative,
optional refactoring, or request for additional verification that does not
expose one of the conditions above is not a Gate A blocker.

Complete the review of the entire plan after finding a defect and report all
qualifying material findings together. Do not drip-feed material findings that
the same complete review could reasonably have discovered. Route a plan defect
to a separate Gate A correction run, a wrong executable boundary to Stage 0,
and an unresolved product, policy, security, provider, or operational decision
to the owner.

Before modifying the plan, the correction run must independently confirm each
reported finding against the complete fixed Gate A review requirements, current
repository behavior, and the materiality conditions above.
Correct only findings that are supported by that basis and actually satisfy a
materiality condition. If a reported finding does not qualify, do not change the
plan for it; report the finding as rejected with the source-backed reason.

The validated findings are the minimum required correction set, not a ceiling
on the correction run. For every validated finding, identify the underlying
defect class, inspect every applicable related operation, code path,
configuration, database element, policy, diagnostic, and verification location
for the same omission or inconsistency, and correct every additional in-scope
defect found. Fully resolve the design defect and update all affected
requirements and behaviors, including failure handling, recovery,
concurrency, retry, reconciliation, unknown outcomes, compatibility, and
verification consequences. Do not opportunistically redesign, strengthen,
generalize, refactor, or rewrite unrelated plan behavior.
Broader changes are allowed when they are required to close the validated defect
class completely or are required by a current requirement source or accepted
repository behavior.

After those corrections, reread the entire corrected plan candidate rather than
only the modified sections. Repeat the complete Sections 7.1 and 7.2 self-audit
and its omission-focused second pass before reporting the plan ready for another
independent review. A correction run must not patch only the literal findings
and immediately resubmit the plan.

A correction run may change the plan but cannot approve it. Its report must name
every requirement or technical design rule added or materially changed by the
correction and provide a compact correction-impact account in this form:

```text
ADDED OR CHANGED REQUIREMENT OR DESIGN RULE
-> ALL AFFECTED OPERATIONS, OUTCOMES, CONFIGURATION, DATABASE,
   POLICY, DIAGNOSTIC, CODE, AND VERIFICATION ITEMS CHECKED
-> RESULT
```

This account must expose newly introduced requirements or technical rules as
well as changes to existing ones. A bare assertion that all affected items or
planned verification was checked is not a substitute for the account. Keep it
in the correction report; no separate checklist, ledger, or permanent artifact
is required.

Review a corrected plan in another fresh Gate A review run against the complete
fixed review requirements and the entire corrected plan, not only the reported
corrections. Use the prior coverage inventory as navigation, not as completed
verification: independently reverify every item and add every requirement or
technical rule introduced or changed by the correction. An additional inventory
item is valid only when
the review cites the requirement source or accepted repository behavior that
makes it applicable and explains why it was absent from the prior inventory. A
reviewer cannot add an item from
preference, speculative hardening, or a newly invented requirement.

When a later full review finds a material defect that already existed in the
immediately preceding reviewed plan, was reasonably discoverable during that
preceding full review, and was neither introduced nor newly exposed by the
intervening correction, classify it as a `prior-review miss`. This classification
exposes incomplete review behavior; it does not make the finding non-material,
suppress its correction, or change normal correction routing.

The first complete Gate A review with no material findings approves the plan and
ends Gate A; do not request another clean review. If required review material is
inaccessible or a routed decision remains unresolved, report Gate A as blocked.
Gate A does not automatically begin implementation. Do not impose an arbitrary
maximum number of review or correction rounds; Gate A ends through semantic
approval, an applicable stop or routing condition, or a genuine blocker.

## 8. GATE B: Implementation And Risk-Based Verification

Gate B implements the selected corrected-master work. When a reviewed plan
exists, follow it unless accepted repository behavior or the current change set
exposes a material design problem; in that case, return to planning rather than
silently redesigning the work.

Before editing, read the reviewed Gate A plan or current reviewed planning
record, any recorded intake that defines the executable boundary, and the
technical and testing standards Program Context routes to for the actual change.
Recheck relevant current source and prerequisites rather than relying on a plan's
predicted file list.

Develop implementation and verification together by coherent behavior or
invariant:

```text
BEHAVIOR / INVARIANT
-> IMPLEMENTATION
-> FOCUSED TEST OR OTHER APPROPRIATE VERIFICATION
-> AFFECTED COMPATIBILITY CHECK
```

### 8.1 Implementation Rules

Gate B must:

- verify the working branch, baseline, worktree, and staged state before editing;
- modify only files genuinely needed for the selected outcome;
- preserve prerequisite interfaces, invariants, and existing behavior outside
  the change;
- use the smallest mechanism that solves the actual production-readiness
  problem;
- avoid speculative product features, parallel architecture, and process
  infrastructure rejected by the corrected master;
- test realistic failure, authorization, persistence, concurrency, retry,
  rollback, provider, browser, or migration behavior at the correct layer when
  applicable;
- assess existing tests by usefulness and correctness regardless of directory;
- protect secrets, credentials, PII, payment data, and provider-private data;
- report validation that was actually run and any material gap that remains.

When Gate B introduces or materially changes a test as verification for the pass,
mark that test with `pytest.mark.pass_provenance` using the narrowest accurate
scope. Preserve genuine multi-pass ownership. Do not add provenance merely
because the pass reran an existing test, and do not require it for ordinary
tests with no production-readiness provenance. Provenance is source-local
context, not universal metadata or a completeness system.

### 8.2 Validation Selection

Use focused tests while developing, then run the affected compatibility checks
needed for confidence. Broader regression is appropriate when blast radius,
shared infrastructure, schema changes, concurrency behavior, or the current task
warrants it. Do not run expensive suites merely to satisfy an old Gate ritual,
and do not omit them when the actual risk calls for them.

Diagnose every validation failure. Fix and report genuine defects when the
current Gate B edit scope permits; after a focused correction, repeat broader
coverage only when the correction or remaining uncertainty warrants it.

Applicable validation may include:

- unit and service tests;
- API and authorization tests;
- real PostgreSQL and migration tests;
- deterministic independent-session concurrency tests;
- provider-boundary or sandbox checks;
- frontend static checks and focused component tests;
- browser tests when explicitly requested or materially necessary;
- lint, formatting, type, build, or configuration checks.

A green suite is one verification result, not semantic review. Gate B must also
inspect the diff for missing behavior, stale tests, unexplained files,
accidental expansion, and completion claims broader than the verification
performed.

### 8.3 Implementation Completion Check

Before reporting Gate B ready for Gate C, reread the complete reviewed Gate A
plan or planning record and independently compare every applicable requirement
and planned verification with the complete pass change set relative to its
accepted starting point: changes already committed on the working branch,
staged and unstaged changes, and applicable untracked files. Also inspect unchanged
surrounding implementation needed to verify the result. Verify that every
changed file is within the selected pass scope; classify unexpected untracked
files rather than silently ignoring them. Do not use
completed tasks, green test counts, or the list of files edited as a
substitute for this check. For each requirement:

- identify the actual implementation, including relevant entry points, shared
  helpers, callers, persisted or transmitted values, downstream consumers, and
  affected existing behavior;
- check each applicable operation, material outcome, failure path, retry,
  recovery path, and concurrency or timing case specified by the reviewed plan;
  where multiple operations use the same code, check their required results
  individually;
- identify the exact focused test, inspection, migration check, or other
  appropriate verification method and verify that its assertions or observed
  result establish the required result and any prohibited side effects, not
  merely that execution succeeds;
- verify the affected compatibility behavior, and distinguish completed
  repository verification from external evidence or explicitly permitted later
  work; and
- classify each item as `implemented and verified`,
  `defect or missing verification`, `inapplicable` with a reason for a genuinely
  inapplicable category, or
  `permitted open external or later verification` with the named owner and
  completion condition. A required item cannot be marked inapplicable because
  code or verification is missing. Do not present a planned test, unrun test,
  unavailable external fact, or assumption as completed verification.

Use every affected closed set and multi-path requirement identified in
Gate A, not selected examples. Verify the planned treatment of every member,
including members intentionally unchanged or inapplicable, against current
source and appropriate existing or new verification. If source inspection
exposes an additional implementation location or affected configuration,
database, policy, diagnostic, or related code path already governed by the reviewed requirements
and design, check it and identify it in the Gate B report. If the plan
instead omitted a material required operation, expected outcome, verification
approach, or design decision, stop and return to Gate A for a reviewed plan
correction; do not make that decision during implementation. A recorded
deferral stays visibly open with its named owner and trigger; it is not
counted as verified.

After the implementation and tests are aligned, perform a separate
omission-focused self-check of the entire affected change: look for missing
related operations, callers, readers, configuration fields, database objects,
policy rules, diagnostic outputs, error and cancellation paths, partial
results, retries, transaction or external-service uncertainty, cleanup,
competing operations, and assertions that fail to check actual effects.
Inspect all applicable related paths before handoff, even if the focused tests
pass. A discovered issue must be corrected within Gate B's approved edit scope
or routed to the earlier responsible stage before Gate B claims readiness.

The existing Gate B implementation and validation report must give a compact,
verifiable account of each requirement and every member of each affected closed
set or multi-path requirement: the actual implementation paths and relevant
configuration, database, policy, or diagnostic locations, applicable test names
or other verification locations, current validation
results, affected compatibility checks, and any expressly permitted open
external or later verification. The report may group items only when every
member is identified and its treatment and result are verifiable. A blanket
statement that all requirements or related paths were
checked is not sufficient. This account belongs in the existing report; no
separate checklist, permanent ledger, universal matrix, or new testing metadata
is required.

### 8.4 Gate B Correction Runs

A correction of an unmerged first-time pass follows the same implementation,
verification, and completion requirements as the initial Gate B run. Before
editing, confirm each reported finding against the current code and the fixed
Gate C review requirements. Identify the underlying defect, all in-scope requirements
it affects, and every applicable related operation, outcome, caller, consumer,
configuration, database object, policy, diagnostic, and verification case where
the same defect could occur. A reported example is the start of that
investigation, not a limit on the correction. Reject a finding that is
not supported by current requirement sources and repository behavior, with the
reason in the correction report; do not change unrelated behavior to satisfy a
preference.

Correct all confirmed findings and additional in-scope occurrences, including
their necessary tests and compatibility checks. Do not redesign a requirement,
add unrelated hardening, or silently enlarge the pass. Route any missing design,
new requirement, wrong executable boundary, or unresolved owner decision to
Gate A, Stage 0, or the owner as appropriate. Run focused and affected
validation under Section 8.2; a correction does not automatically invalidate
previously successful unrelated broad suites.

Before handoff, repeat the complete Section 8.3 check against the corrected
pass, not just the changed lines or previous findings. The correction report
must identify which other operations and paths were inspected, every material
additional issue found and resolved, the exact requirement source,
implementation path, and verification for affected requirements, and which
validation results still apply to the final state. A missing check or incomplete
required verification prevents a ready-for-review claim.

The editing run ends here; the next Gate C review remains fresh, independent,
and read-only.

Gate B ends with a validated local change set and a concise implementation and
validation report containing the Section 8.3 account, including after any
correction. It does not stage, commit, push, create a PR, or begin Gate C unless
the current owner instruction explicitly asks for the next step. It does not
update the execution register merely to record that the current pass has been
implemented locally.

## 9. GATE C: Independent Semantic Review

Gate C is a read-only, independent, systematic semantic review of the complete
change set against fixed review requirements. Review rigor does not scale down
because a change is small, appears simple, has green tests, passed Gate B
validation, or inspires reviewer confidence. Only the amount of material inside
the implementation scope changes.

Passing tests do not replace semantic review.

Read the reviewed Gate A plan or planning record, any recorded intake that
defines ownership, the applicable prerequisite interfaces, invariants, and
standards, and the actual Gate B diff and validation report. Use the corrected
master and accepted repository behavior to resolve conflicts; the plan does not
override them.

Use a fresh review context that is separate from the context used to implement
or correct the current change set. Reach conclusions from current requirement
sources, accepted repository state, the complete current change set, tests, and
validation results rather than relying on the implementer's conclusions or prior
review results.

The fixed review requirements consist of the corrected-master scope, the
recorded executable boundary, the reviewed requirements and design,
prerequisite behavior already merged into `develop`, and applicable engineering
standards. Gate C may expose a material defect within those requirements,
including one the plan failed to name explicitly, but it does not create new
product requirements or move the
completion bar during review. Route an actual requirement, design, or boundary
problem to the responsible earlier stage.

If any material required to complete the review cannot be inspected, Gate C
must return blocked rather than approve through inference or partial visibility.

### 9.1 Implementation And Review Scope

Review the complete implementation scope needed to determine whether the pass
is correct, complete, safe, compatible, and faithful to its selected scope.

Review:

- the corrected-master obligation being implemented;
- accepted repository state, the complete current change set, and applicable
  prerequisites;
- every requirement, invariant, acceptance criterion, failure case,
  compatibility obligation, and validation claim owned by the pass;
- the reviewed planning document or planning record used for the work;
- every actual pass change relative to its accepted starting point, including
  changes already committed on the working branch, staged changes, unstaged
  changes, and applicable untracked files, including tests and other artifacts
  not captured by a single Git diff; independently verify this complete file
  inventory and investigate unexpected files;
- every changed behavior in context, not only the edited lines;
- all surrounding implementation necessary to establish correctness, including
  relevant related paths as defined in Section 4, shared helpers and services,
  policies, registries, constants, schemas, serializers, display paths, models,
  migrations, constraints, indexes, defaults, transaction boundaries,
  authorization dependencies, asynchronous or external-service boundaries, and
  tests;
- implementation, schema and migration behavior, interfaces, failure paths, and
  security or privacy behavior;
- tests and validation claims;
- compatibility with prerequisite behavior already merged into `develop` and
  unaffected existing workflows;
- scope omissions, accidental expansion, and unexplained behavior changes.

Do not interpret relevant surrounding code as only immediately adjacent lines,
functions, or files; use the shared interface or invariant test in Section 4.

Do not approve while any material part of the required review scope remains
uninspected.

Gate C does not edit files, stage changes, commit, push, create or update a PR,
merge, rebase, reset, apply a stash, or self-fix.

Gate C does not require the current pass to appear in the execution register as
implemented but unmerged. The absence of a transient register update for the
current pass is not a finding; the normal register transition occurs once in
Gate D after Gate C approval.

### 9.2 Requirements-Based Semantic Review

Trace every pass-owned requirement and invariant through the implementation,
every affected representation and path, applicable failure and edge behavior,
and its appropriate verification.

Systematically evaluate every category below against the actual change. A
category may be determined inapplicable only after it has been considered
against the implementation.

Evaluate:

- wrong types, coercion, nulls, blanks, malformed values, unexpected fields,
  lengths, caps, empty collections, and multiplicity;
- identity, actor attribution, canonicalization, deduplication, replay,
  generated identifiers, and collision boundaries;
- state transitions, stale state, terminal and historical behavior, required
  effects, prohibited effects, and repeated operations;
- ordering, tie-breaking, timestamps, time zones, pagination, stale data, and
  deterministic behavior;
- SQL NULL semantics, constraints, foreign keys, indexes, defaults, and
  model, migration, and live-schema parity;
- transaction ownership, lock order, idempotency, retries, rollback, commit
  uncertainty, and competing transitions;
- exception handling, logs, SQL parameters, conflict and error responses,
  internal-detail leakage, and sensitive-data leakage;
- authorization, privilege boundaries, denied operations, actor identity, and
  bypass paths;
- cross-domain, cross-representation, related caller, API, UI, persistence,
  serialization, and display parity;
- external-service failures, asynchronous outcomes, unknown outcomes, recovery,
  and compatibility;
- no-op behavior, duplicate requests, partial progress, cleanup behavior, and
  repeated requests;
- tests, validation results, comments, documentation, or completion claims that
  exceed what the inspected verification establishes.

Inspect related paths proactively whenever they share an affected interface or
invariant under Section 4. Do not wait for a defect to be found first.

When a defect pattern is found, expand the review across every affected closed
set member, behavior-changing condition, and related path within the selected
implementation scope.

Finding one or several defects does not end the review. Complete the defined
review scope before reporting all qualifying material findings together.

Before a verdict, independently assemble and verify a source-backed account of
every applicable requirement, every member of affected closed sets, and every
requirement that applies across multiple operations or representations. Derive
it from the current requirement sources, the reviewed Gate A plan or planning
record, the actual implementation, and the applicable tests or other
verification. Do not copy Gate B's completion account or assume its claimed
coverage is true.

For each applicable item, identify the requirement and its source, actual
implementation path, affected operations, consumers, configuration, database,
policy, or diagnostic elements as applicable, and specific test or other
verification that establishes the required behavior, including any required
absent side effect. Distinguish verification inspected from commands
actually rerun; Gate C need not rerun already-current successful suites.

Record a verifiable result for each requirement and every member of an
affected closed set: `verified`, `material finding`,
`inapplicable` with a concrete reason for a genuinely inapplicable category,
or `permitted open external or later verification` with the named owner and
completion condition. A required item cannot be marked inapplicable because its
code or verification is missing. The last status applies only where the reviewed
plan explicitly permits the pass to finish without that external or later-pass
verification; do not mark open work verified. The existing Gate C review report
must expose this account directly or through a compact source-backed
representation that identifies every member and makes its result checkable.
Grouping is acceptable only when all grouped members share the same result and
each member is identified.

Compare it with Gate B's account, investigate missing or inconsistent items,
and check for omissions in both accounts. A generic claim that the full scope
was reviewed, a list of touched files, or a green validation summary cannot
replace these review results. This is a review-report requirement, not a request
for another repository artifact or a new universal test matrix.

Complete a final omission-focused review of the entire scope in Section
9.1, including affected operations, configurations, database elements, policies,
diagnostics, and related paths not mentioned in Gate B's report, before
issuing the verdict. If a required item was not inspected, obtain the missing
source and verification or return `blocked`; if inspection establishes a
material omission or defect, report `corrections required`. Do not infer
correctness from an uninspected path or suppress later findings after the first
defect.

### 9.3 Outcomes And Corrections

Gate C returns one of:

- approved for Git finalization;
- corrections required;
- blocked because the review cannot be completed safely or honestly.

Approval requires:

- completion of the entire defined Gate C review;
- every pass-owned requirement and invariant traced through implementation and
  verification;
- every applicable review category evaluated against the change;
- all affected related and cross-representation paths inspected under the
  Section 4 definition;
- no remaining material semantic defect;
- no material omission;
- no unexplained scope expansion;
- external-evidence and validation claims that match the verification inspected
  or rerun;
- no required review material remaining inaccessible or uninspected.

The required source-backed account stays in the existing Gate C report. It
does not require a separate permanent coverage ledger, appendix, universal
matrix, or parallel verification bookkeeping, and it does not expand the
selected pass or require automatic broad-suite reruns.

A material finding must identify:

- the governing requirement source, required invariant, prerequisite behavior
  or interface guarantee, applicable standard, or necessary consequence of them
  that is violated;
- a concrete reachable input, state, event, failure, concurrency, or execution
  path;
- the conflicting implementation behavior and its material consequence;
- the relevant files or paths and the source behavior or verification supporting
  the finding;
- the correct correction route.

Use a focused reproduction or test when source inspection alone cannot
establish the behavior confidently. A new failing test is not mandatory when
the reachable defect is already established directly from the source and
interfaces and invariants.

Speculative hardening, unreachable hypotheticals, cosmetic preferences,
harmless alternative designs, optional refactoring, and tests proposed only to
increase test volume are not material findings. If no finding satisfies the
standard above, Gate C must report no material findings and may approve when all
other approval conditions are met.

Corrections are separate editing work followed by focused and affected
validation and a new complete review of the corrected change set.

Before editing, the separate Gate B correction run must confirm each reported
finding against current source and the fixed review requirements, investigate
the complete affected requirements and related paths, and follow Section 8.4.
Correct the complete confirmed finding set and any additional in-scope
occurrences; run focused and affected validation warranted by those changes.

After corrections, Gate C must use fresh review context, independently rebuild
the Section 9.2 coverage account, and review the entire corrected pass. It must
not limit the next review to the changes or previously reported findings. When
it finds a material defect that existed in the immediately preceding reviewed
state, was reasonably discoverable then, and was neither introduced nor newly
exposed by the correction, identify it as a `prior-review miss`. The finding
still requires normal correction. Do not classify genuinely new behavior or a
newly exposed defect as a prior-review miss.

Stop after the first complete Gate C review with no material findings; do not
require additional clean reviews.

Stop and route the work instead of continuing the cycle when correct resolution
requires a changed design or executable boundary, an owner decision, or
inaccessible required verification.

Gate C does not automatically rerun successful broad suites. Run the smallest
focused reproduction only when a concrete semantic concern requires it.

Limiting test execution does not limit semantic review depth. Passing tests,
prior validation, implementation notes, or reviewer confidence never substitute
for complete inspection of the implementation, preserved interfaces and
invariants, and required verification.

## 10. GATE D: Git And PR Finalization And Execution-Register Update

Gate D performs the one normal execution-register update and mechanical Git and
PR work after the change set has passed independent review and the owner has
asked to publish it.

Before drafting or updating the pull request, read and follow the current
`docs/production-readiness/planning/templates/PASS-PR-DESCRIPTION-TEMPLATE.md`.
Individual Gate D prompts do not need to restate its PR-body format or writing
rules.

Gate D must:

- fetch remote metadata safely;
- verify the current branch, HEAD, baseline, merge-base, worktree, staged state,
  and intended changed-file set;
- stop if `origin/develop` advanced in a way that requires reconciliation;
- inspect the final diff for scope and sensitive material;
- update the execution register exactly once for the current pass, in the
  substantive PR, to the state intended to exist after that PR merges;
- stage only files authorized for publication and inspect the staged diff;
- create the intended commit or commit structure;
- push normally without force;
- create or update exactly the intended PR;
- verify PR base, head, commit count, changed-file list, title, body, and
  sensitive-content safety;
- leave the PR open and unmerged.

Use exactly the PR-body structure and authoring rules required by the current PR
guidance. Draft from the base, final diff, and validation that actually ran;
plans and Gate reports do not prove implementation behavior.

Gate D does not amend, squash, rebase, reset, cherry-pick, rewrite history,
force-push, merge, or enable auto-merge unless the owner explicitly authorizes
the particular action. PR merge remains manual. Gate D does not author semantic
product, implementation, or planning changes. The required execution-register
transition is the authorized application of the already-approved pass result,
not permission to redesign execution state. Route any discovered content defect
back to implementation or planning.

## 11. Correction Routing

| Discovery | Route |
|---|---|
| Selected unit contains multiple independent outcomes or has a wrong ownership/dependency boundary | Stage 0 |
| A written plan has a defect within a sound boundary | Gate A correction |
| Implementation has a defect within the selected scope | Gate B correction |
| Correct implementation requires a changed design, new product behavior, or unresolved owner decision | Gate A or owner decision, as appropriate |
| Final infrastructure is required but not selected or verified | Defer to the recorded owner and trigger, or stop if current work truly depends on it |
| Independent review finds a material implementation or verification defect | Follow Section 8.4 to correct all confirmed findings and other affected occurrences, complete Section 8.3 for the corrected pass, run warranted focused and affected validation, and perform a fresh full Gate C review with Section 9.2 accounting |
| Git finalization finds semantic or publication-integrity trouble | Stop and route to the responsible earlier work; Gate D does not fix content |

## 12. Register Updates

The execution register is a factual status record. It does not define scope or
select work automatically.

For a normal pass, update the register exactly once during Gate D. The update
travels in the substantive PR and describes the final execution state intended
to exist after that PR merges, including the pass or recorded decomposition,
remaining corrected-master scope, and any still-open late-bound obligations.
The register version carried by the open PR may therefore describe the current
pass as merged or complete before the PR has physically merged; that wording
represents the atomic intended post-merge state, not transient branch progress.

Do not update the register during Stage 0, Gate A, Gate B, or Gate C merely to
record the current pass's progress, and do not introduce an
implemented-but-unmerged entry for that purpose. Gate C must not treat the
absence of such an intermediate update as a defect.

After the PR merges, do not perform a second routine register update for the
same pass. If publication fails, the merged result differs from the intended
state, or the register is otherwise factually wrong, correct it as exceptional
cleanup. Never claim completion for a surviving obligation or deferred
verification that the pass did not actually complete.

## 13. Stop Conditions

Stop and report when:

- the worktree, branch, baseline, or intended publication state is unsafe or
  ambiguous;
- the selected scope conflicts with the corrected master;
- a required owner decision is missing;
- a real prerequisite is missing;
- current completion depends on unselected or unverified final infrastructure;
- a provider, deployment, migration, database, credential, or runtime action
  needs approval that has not been given;
- correct completion requires unrelated product expansion or files outside the
  selected outcome;
- a completion claim would overstate external facts;
- validation exposes a defect requiring broader design or an owner decision;
- sensitive material would enter Git or a PR.

Do not automatically reset, rebase, merge, stash, restore, clean, delete,
force-push, or mutate provider/runtime state to escape a stop condition.

## 14. Completion Meaning And Post-Merge Progression

A change is complete when its intended PR has been manually merged and current
accepted `develop` contains the result. A decomposed parent remains incomplete
while any surviving corrected-master child or late-bound obligation remains
open.

After manual merge:

1. verify the intended PR merged;
2. verify the worktree is safe, switch back to local `develop`, and fetch remote
   metadata;
3. fast-forward local `develop` to `origin/develop` using the normal safe path;
4. verify local and remote `develop` agree;
5. confirm that the Gate D execution-register update landed with the intended
   final state; do not make a second routine update for the same pass, and use
   exceptional cleanup only if publication failed or accepted repository state
   differs from that intended state.

Select later work from the corrected master, accepted repository state, real
prerequisites, deferred-trigger state, and owner direction. A later child of a
recorded decomposition that remains valid begins at Gate A; new first-time scope
without a recorded decomposition begins at Stage 0. Neither stage starts
automatically. If several units are valid and no real dependency selects one,
ask the owner rather than inventing priority.
