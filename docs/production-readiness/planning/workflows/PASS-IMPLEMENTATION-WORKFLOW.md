# Production-Readiness Pass Implementation Workflow

This document defines the reusable process for implementing a Pickup Lane
production-readiness pass for the first time from current authority and current
accepted `develop`.

Use this workflow for forward implementation work and for correction rounds on
the same unmerged first-time executable pass. Use
`docs/production-readiness/planning/workflows/PASS-RECHECK-WORKFLOW.md` only
when a pass already accepted into `develop`, or historical implementation that
predates the current workflow, is later revalidated or repaired against current
repository truth.

This workflow is process guidance only. It does not define product behavior and
does not override the authority order in
`docs/production-readiness/00-READ-ME-FIRST.md`.

The familiar workflow roles are:

```text
STAGE 0: SCOPE AND DECOMPOSITION, WHEN NEEDED
-> GATE A: ENGINEERING PLAN AND REVIEW, WHEN NEEDED
-> GATE B: IMPLEMENTATION AND RISK-BASED EVIDENCE
-> GATE C: INDEPENDENT SEMANTIC REVIEW
-> GATE D: GIT AND PR FINALIZATION
```

Stage 0 and Gate A are optional tools for work that needs decomposition or a
durable reviewed plan. This naming does not create mandatory orchestration; a
straightforward unit may proceed through normal implementation, review, and PR
finalization.

## 1. Purpose And Applicability

Use this workflow when a production-readiness pass is being implemented as a
new executable pass rather than rechecked after prior implementation.

The workflow applies when:

- the corrected master blueprint contains a selected roadmap unit;
- current accepted `develop` is the implementation baseline;
- no accepted executable child pass exists for the specific scope;
- the task is to design, implement, prove, review, and publish the pass for the
  first time.

Do not use this workflow to:

- revalidate a pass already accepted into `develop`, or historical
  implementation predating the current workflow;
- repair a pass already accepted into `develop`;
- perform unrelated documentation or repository housekeeping;
- choose a next parent or child from filename order, stale chat context, or any
  source other than current durable authority and accepted dependency state;
- mutate providers, databases, deployments, credentials, or runtime settings
  unless the current executable pass and durable authority explicitly own that
  action.

## 2. Authority Principle

Forward implementation follows this reasoning order:

```text
CORRECTED MASTER BLUEPRINT
-> CURRENT REPOSITORY TRUTH
-> OPTIONAL SCOPE DECOMPOSITION OR ENGINEERING PLAN
-> IMPLEMENTATION AND RISK-BASED EVIDENCE
-> VALIDATION AND INDEPENDENT REVIEW
```

The corrected master blueprint is authoritative for current production-readiness
scope and roadmap. Historical audits, remediation plans, decisions, pass plans,
and SHAs may explain earlier work but do not override it.

When a parent pass is too broad, Stage 0 decomposes it into one or more
bounded executable child passes. The child pass must preserve the parent pass
intent, surviving requirements, dependencies, and evidence boundaries while
remaining small enough for meaningful implementation and review.

Current accepted `develop` is repository truth for current implementation
state. Source code does not define requirements by itself, and tests do not
define production behavior.

Authority defines what must be true, and current repository truth defines what
currently exists and behaves. When used, Stage 0 defines the executable boundary
and Gate A records the engineering approach, risks, and proof strategy. Gate B
implements and tests the selected work; it does not create its own requirements.

## 3. Workflow Selection

Before starting pass work, determine the workflow.

| Situation | Workflow |
|---|---|
| The pass has already been accepted or merged and is being revalidated or repaired later. | `docs/production-readiness/planning/workflows/PASS-RECHECK-WORKFLOW.md` |
| The pass is being implemented for the first time from current authority. | This document |
| A completed Gate C found a defect in the same unmerged first-time pass. | Scoped correction under this implementation workflow, followed by correction validation and a new full Gate C review |
| The task is global workflow maintenance, documentation navigation, or register maintenance. | The explicit task prompt, not a production-readiness implementation pass |

If the workflow is unclear, stop and report the ambiguity. Do not choose the
next pass or workflow from filename order. Select work from the corrected master,
real dependencies, current repository truth, and owner direction.

## 4. Shared Rules For All Stages

Every stage must:

- start from a clean, understood Git state;
- apply the authority order from the read-first document;
- apply the instruction-adherence rule from the read-first document to the
  current run instruction before acting;
- read any applicable scoping or planning artifact when one exists;
- treat explicit scope, editable files, paths, validation requirements,
  stage or gate boundaries, and stop conditions from the current instruction as
  binding constraints;
- evaluate existing tests by usefulness and correctness rather than directory
  labels;
- distinguish repository truth, authority, provenance, inference, external
  evidence, and unknown facts;
- keep provider/runtime/control-plane facts unknown until accepted evidence
  exists;
- apply the final-infrastructure timing and provider-neutrality rule from the
  read-first document: temporary Vercel, Render, and Neon demo infrastructure
  must not become permanent production architecture, and concrete production
  values that depend on final infrastructure remain late-bound until that
  infrastructure is selected;
- protect secrets, local paths, provider-private evidence, payment data, and
  personal data;
- stop rather than guess when authority, ownership, evidence layer, or scope is
  ambiguous, when the current instruction cannot be followed exactly, or when it
  conflicts with authority or repository truth.

Before reporting completion, compare the actual work performed
against the binding current instruction. Correct any in-scope mismatch before
reporting, or report the mismatch and stop.

## 5. Forward-Pass Initialization

Before implementation work edits repository content, initialize from current
accepted `develop` unless the current instruction explicitly establishes a
different understood baseline.

Required initialization:

1. fetch remote metadata safely;
2. verify the worktree and index are clean or explicitly understood;
3. switch to local `develop`;
4. run a fast-forward-only update from `origin/develop`;
5. verify local `develop` equals `origin/develop`;
6. record the exact accepted baseline;
7. create or switch to the local working branch specified by the user or current
   task; when no different branch name is mandated, `pr/<EXECUTABLE-PASS-ID>`
   remains a useful convention;
8. use that branch through implementation, review, and publication unless an
   explicitly authorized change requires another branch;
9. do not push merely for branch creation.

Unexpected local work, divergence, worktree conflict, or branch ambiguity causes
a stop. Do not automatically reset, rebase, merge, stash, restore, clean, or
delete anything.

If preserved local work such as a stash is later restored or converted into
commit-eligible pass artifacts, recheck it for prohibited sensitive material
under the read-first document before continuing.

Stage 0 and Gate A, when used, edit only their authorized planning artifacts.
They do not stage, commit, push, create a PR, or update a PR. Publication remains
Gate D work after independent review.

## 6. STAGE 0: Pass Intake And Decomposition

Use Stage 0 when a selected corrected-master unit is too broad, mixes genuinely
different outcomes, or needs a provider-independent/deferred split. It decides
the executable boundary without editing production code, tests, provider
settings, migrations, or runtime configuration. A reusable intake document is
optional; use the existing template only when a durable intake record is useful.

### 6.1 Inputs

Read:

- the read-first document and program context;
- this workflow;
- `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md`;
- the relevant master blueprint parent pass entry;
- historical remediation, decision, and pass records only when useful as
  provenance or technical context;
- accepted prerequisite behavior and evidence boundaries;
- current accepted repository truth for the area;
- applicable engineering and testing standards.

### 6.2 Parent-Pass Reconciliation

For the selected parent blueprint pass, answer:

- What surviving requirements, decisions, dependencies, and evidence classes does the parent
  pass cover?
- Which parts are already accepted by earlier executable passes?
- Which parts are repository-owned, provider-owned, runtime-owned, governance
  owned, migration-owned, or later-owned?
- Which parts need source implementation now?
- Which parts require external evidence before source implementation can be
  honest?
- Which parts depend specifically on final hosting, database hosting, edge,
  runtime, provider topology, provider plan/capacity, provider-native settings,
  concrete production roles/grants, or other intentionally late-bound
  infrastructure facts?
- Which parts can be completed provider-independently now through portable
  source behavior, generic configuration interfaces, validation, formulas,
  focused evidence, or synthetic fixtures?
- Which parts are too broad to implement and review in one PR?
- Which prerequisite contracts must be preserved?

Do not modify the master blueprint to make the decomposition easier. If the
blueprint already identifies a final-infrastructure dependency, Stage 0 must
apply it. If current authority reveals an unrecorded material infrastructure
dependency, preserve it in the intake/register and route any needed blueprint
correction through the appropriate program-documentation change rather than
pretending the dependency does not exist.

### 6.3 Final-Infrastructure Timing Check

Before choosing an executable boundary, Stage 0 must classify every material
provider/runtime/configuration requirement as one of:

- provider-independent and executable now;
- dependent on already selected and evidenced infrastructure;
- dependent on intentionally unselected final infrastructure and therefore
  mandatory deferred work.

Current Vercel frontend hosting, Render API hosting, and Neon PostgreSQL hosting
are temporary development/demo infrastructure. They may be inspected as current
repository/demo truth when relevant, but their provider-specific settings,
limits, topology, plan characteristics, and runtime evidence must not be used as
final production assumptions unless higher authority later selects them as the
permanent production providers and the required evidence exists.

A generic setting or configuration interface may be implemented now when its
existence, validation, and semantics are provider-independent. Concrete
production values remain deferred when they depend on the final provider or
topology. Never populate them from README examples, local/CI configuration,
free-tier defaults, framework defaults, or temporary deployment values.

When one parent combines executable-now work with final-infrastructure-dependent
work, Stage 0 must separate them. Prefer a coherent current executable child or
children plus a mandatory deferred follow-up rather than forcing an early
infrastructure choice or blocking unrelated downstream engineering.

Every mandatory deferred follow-up must record:

- one owning pass or executable unit;
- the preserved parent requirements and evidence obligations;
- the exact trigger that makes the work executable;
- prerequisites and downstream consumers;
- the latest required completion boundary;
- execution-register visibility;
- an explicit statement that deferred status is not proof of completion.

Run deferred work as soon as its trigger is satisfied and no later than the
earliest downstream pass that genuinely needs the deferred facts or `CLOSE-01`,
whichever comes first. Downstream work may proceed while the trigger is false
only when its own prerequisites do not depend on those deferred facts.

### 6.4 Decomposition Decision

Choose one of these outcomes:

| Outcome | Meaning |
|---|---|
| Implement parent as one executable pass | The parent pass is narrow enough to plan, implement, prove, review, and publish as one coherent PR. |
| Decompose into ordered child passes | The parent pass is too broad. Stage 0 defines child pass IDs, order, scope, dependencies, and non-overlap. |
| Decompose current work plus mandatory deferred follow-up | A coherent provider-independent result can be completed now, but another obligation requires intentionally unselected final infrastructure. Stage 0 defines the current executable unit plus the deferred owner, trigger, preserved obligations, dependencies, and latest completion boundary. |
| Stop for prerequisite | A prerequisite required by the current executable work is genuinely missing and cannot be deferred without making the current result false or unsafe. |
| Stop for owner decision | Existing authority cannot decide a product, security, operational, or policy question. |

Child pass IDs must be stable and must preserve the parent ID prefix where
practical, for example `WS03-03A` and `WS03-03B`.

### 6.5 Executable-Pass Cohesion Test

Stage 0 must assess every proposed executable pass against this cohesion test.

| Cohesion question | Required record |
|---|---|
| One primary outcome | Verdict, reasoning/evidence, and split implication. |
| One coherent requirement/invariant family | Verdict, reasoning/evidence, and split implication. |
| One prerequisite state | Verdict, reasoning/evidence, and split implication. |
| One safe merge/rollback or forward-fix unit | Verdict, reasoning/evidence, and split implication. |
| One coherent evidence model | Verdict, reasoning/evidence, and split implication. |
| One semantic review model | Verdict, reasoning/evidence, and split implication. |
| Safe and useful intermediate state | Verdict, reasoning/evidence, and split implication. |

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
- provider source support versus provider activation;
- separate rollback units;
- independently blocked components;
- different authoritative owners;
- distinct failure/recovery models.

Do not split one coherent feature into artificial backend, frontend, testing,
or documentation passes. Required frontend behavior, production behavior,
relevant tests, and compatibility evidence travel with the contract they
establish.

Do not permit an unsafe partial merge merely to create smaller PRs.

### 6.7 Child-Pass Rules

When a parent is split:

- the parent is an umbrella and is not implemented directly;
- every child is an executable pass;
- every child is planned and reviewed at a level appropriate to its complexity;
- each later child starts from current `develop` after earlier required
  children merge;
- no later child blindly reuses a detailed plan designed against an older
  baseline;
- immediate child progression includes only children whose prerequisites and
  execution triggers are satisfied;
- a structurally approved mandatory deferred follow-up with an unmet
  final-infrastructure trigger remains visible but is not treated as the next
  executable child merely because earlier children completed;
- the provider-independent foundation may be complete for downstream engineering
  without treating deferred provider/runtime evidence as accepted proof;
- the parent or affected requirements must not be represented as fully production
  verified while a mandatory deferred obligation remains outstanding;
- every parent obligation remains accounted for through accepted children or an
  explicitly recorded mandatory deferred owner.

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
regression responsibility, or cross-cutting evidence.

Every parent requirement must have one primary implementing child,
one clearly named evidence/governance owner, or one mandatory deferred follow-up
with an exact trigger and latest completion boundary. No obligation may disappear
between children, become implicitly accepted because its trigger is false, or be
replaced with temporary-provider evidence.

### 6.9 Intake Record Storage And Publication

When a durable intake record is useful, use the existing pass-family structure:

```text
docs/production-readiness/planning/passes/<family>/<parent-id>-intake.md
```

Do not create retroactive intake documents for already accepted historical
splits such as WS02-04, WS02-05, or WS03-03.

Stage 0 may create or update only the intake record authorized by its current
task. Record the selected structure, scope allocation, prerequisites, and
deferred obligations. Historical decompositions do not require retroactive
intake records. If an intake record is created, normally publish it with the
substantive work it supports rather than in a tracker-only PR.

### 6.10 Stage 0 Completion And Progression

Stage 0 returns:

- selected parent blueprint pass;
- proposed executable pass ID and title;
- decomposition rationale;
- parent-to-child scope map when applicable;
- cohesion-test verdicts and split implications;
- no-gap/no-overlap obligation allocation;
- dependencies and prerequisite state;
- expected evidence layers;
- expected non-goals and external boundaries;
- final-infrastructure dependency classification;
- mandatory deferred follow-up owner, trigger, preserved obligations,
  dependencies, and latest completion boundary when applicable;
- intake-record path when applicable;
- exact approved parent/child structure;
- blockers.

Stage 0 does not automatically start later work. The next action follows the
corrected master, actual prerequisites, current repository truth, and owner
direction. Do not rerun Stage 0 merely because a child merged when the accepted
structure remains sound.

A mandatory deferred follow-up whose final-infrastructure trigger is false is
not a current executable child. Keep it visible in the intake and execution
register, preserve its obligations as open, and continue only to downstream work
whose own prerequisites do not require those deferred facts. When the trigger
becomes true, the deferred unit becomes eligible for planning and implementation
and must run no
later than its recorded completion boundary.

When all currently executable child obligations are complete, determine
progression from the corrected master, execution register, real dependency
state, deferred-trigger state, current repository truth, and owner direction.
Do not mark deferred provider/runtime obligations as proven merely to advance. If
multiple units are valid and no real dependency selects one, stop for owner
selection instead of inventing priority.

## 7. GATE A: Engineering Plan And Review

Use Gate A only when the selected work is complex enough to benefit from a
written engineering plan. A plan is not required merely because the unit has an
old pass ID or historical plan.

Gate A may edit the authorized planning document, but it does not edit
production code, tests, migrations, configuration, or provider state.

### 7.1 Planning Responsibilities

A useful plan should:

- reconcile the selected unit with the corrected master and current repository
  truth;
- define the intended behavior, important invariants, ownership, and non-goals;
- identify affected callers, interfaces, persistence, migrations, provider
  boundaries, and compatibility expectations;
- explain transaction, concurrency, retry, rollback, and failure behavior where
  relevant;
- identify security, privacy, authorization, payment, and sensitive-data risks;
- distinguish provider-neutral work from facts that remain late-bound;
- choose realistic proof layers and focused validation;
- remain small enough for one coherent implementation and review.

For finite or cross-cutting contracts, use a matrix or inventory when it
materially reduces omission risk. Do not create one as process bookkeeping when
the contract is already clear.

A planning template may be used as a convenience. Plans and historical SHAs are
supporting artifacts, not a separate source of production-readiness authority.

### 7.2 Impact And Compatibility Review

Before implementation, inspect the relevant surrounding system rather than only
the expected edit locations. Depending on the change, this can include callers,
routes, request and response contracts, settings, middleware, provider
boundaries, state values, schema and migration expectations, constraints,
existing regression tests, frontend behavior, and technical documentation.

The depth of this review should scale with risk. Complete finite populations
such as state transitions, actor classes, event types, or equivalent adapters
when sampling could hide a material omission.

### 7.3 Plan Review And Corrections

When a written plan is used, review it before implementation. Verify that it is
consistent with the corrected master, current repository truth, real
prerequisites, and the selected scope; that it leaves no material design choice
for implementation to invent; and that its validation can prove the behavior it
claims.

Report material findings together. Route a plan defect back to Gate A, a wrong
executable boundary back to Stage 0, and an unresolved product, policy,
security, provider, or operational decision to the owner. After a correction,
review the corrected plan again. There is no fixed number of automatic review or
correction rounds.

Gate A ends with either a usable current plan or a clearly reported blocker. It
does not automatically begin implementation.

## 8. GATE B: Implementation And Risk-Based Evidence

Gate B implements the selected corrected-master work. When a reviewed plan
exists, follow it unless repository truth exposes a material design problem; in
that case, return to planning rather than silently redesigning the work.

Develop implementation and evidence together by coherent behavior or invariant:

```text
BEHAVIOR / INVARIANT
-> IMPLEMENTATION
-> FOCUSED TEST OR OTHER APPROPRIATE PROOF
-> AFFECTED COMPATIBILITY CHECK
```

### 8.1 Implementation Rules

Gate B must:

- verify the working branch, baseline, worktree, and staged state before editing;
- modify only files genuinely needed for the selected outcome;
- preserve prerequisite contracts and accepted behavior outside the change;
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

Requirement JSON, pytest requirement markers, checker/compliance commands,
trusted test roots, and a `TESTING_RECORD.md` are not required. Existing useful
tests and technical safeguards remain valid; their location or old metadata does
not determine whether they count.

### 8.2 Validation Selection

Use focused tests while developing, then run the affected compatibility checks
needed for confidence. Broader regression is appropriate when blast radius,
shared infrastructure, schema changes, concurrency behavior, or the current task
warrants it. Do not run expensive suites merely to satisfy an old Gate ritual,
and do not omit them when the actual risk calls for them.

Applicable validation may include:

- unit and service tests;
- API and authorization tests;
- real PostgreSQL and migration tests;
- deterministic independent-session concurrency tests;
- provider-boundary or sandbox checks;
- frontend static checks and focused component tests;
- browser tests when explicitly requested or materially necessary;
- lint, formatting, type, build, or configuration checks.

A green suite is evidence, not semantic proof. Gate B should also inspect the
diff for missing behavior, stale tests, unexplained files, accidental expansion,
and evidence claims broader than the proof.

Gate B ends with a validated local change set and a concise implementation and
validation report. It does not stage, commit, push, create a PR, or begin Gate C
unless the current owner instruction explicitly asks for the next step.

## 9. GATE C: Independent Semantic Review

Gate C is a read-only independent review of the complete change set. Passing
tests do not replace semantic review.

### 9.1 Review Boundary

Review:

- the corrected-master obligation being implemented;
- current repository truth and applicable prerequisites;
- any current planning document used for the work;
- every actual changed file and relevant surrounding code;
- implementation, schema/migrations, interfaces, failure paths, and security or
  privacy behavior;
- tests and validation claims;
- compatibility and scope.

Gate C does not edit files, stage changes, commit, push, create or update a PR,
merge, rebase, reset, apply a stash, or self-fix.

### 9.2 Semantic And Adversarial Sweep

Trace each material requirement and invariant through the implementation and its
appropriate proof. Scale the review to the change, deliberately considering
applicable risks such as:

- wrong types, coercion, nulls, blanks, malformed values, unexpected fields,
  lengths, caps, empty collections, and multiplicity;
- identity, canonicalization, deduplication, replay, generated identifiers, and
  collision boundaries;
- state transitions, stale state, terminal and historical behavior, required
  effects, and prohibited effects;
- ordering, tie-breaking, timestamps, time zones, pagination, and stale data;
- SQL NULL semantics, constraints, foreign keys, indexes, defaults, and
  model/migration/live-schema parity;
- lock order, idempotency, retries, rollback, and competing transitions;
- exception handling, logs, SQL parameters, conflict/error responses, and
  sensitive-data leakage;
- cross-domain, cross-representation, sibling-path, caller, API/UI, and
  serialization parity;
- provider failures, unknown outcomes, recovery, and compatibility;
- evidence or documentation claims that exceed what was proved.

When a defect pattern is found, inspect equivalent paths within the relevant
change boundary before concluding the review. Continue far enough to report all
reasonably discoverable material findings together rather than stopping after
the first few.

### 9.3 Outcomes And Corrections

Gate C returns one of:

- approved for Git finalization;
- corrections required;
- blocked because the review cannot be completed safely or honestly.

Approval requires a complete review at the level warranted by the change, no
remaining material semantic defect, no unexplained scope expansion, and evidence
claims that match actual proof. It does not require a permanent coverage ledger,
visible appendix, universal matrix, requirement declaration, or testing record.

A material finding identifies the affected requirement or invariant, the
conflicting behavior, its consequence, relevant files or paths, and the correct
route. Cosmetic preferences and harmless alternative designs are not material
findings.

Corrections are separate editing work followed by focused and affected
validation and a new complete review of the corrected change set. Inspect the
adjacent invariant family so a narrow fix does not leave sibling defects. There
is no fixed automatic correction-cycle count; owner direction and the current
task determine whether another correction or review occurs. Gate C itself
remains read-only.

Gate C does not automatically rerun successful broad suites. Run the smallest
focused reproduction only when a concrete semantic concern requires it.

## 10. GATE D: Git And PR Finalization

Gate D is mechanical Git and PR work after the change set has passed independent
review and the owner has asked to publish it.

Gate D must:

- fetch remote metadata safely;
- verify the current branch, HEAD, baseline, merge-base, worktree, staged state,
  and intended changed-file set;
- stop if `origin/develop` advanced in a way that requires reconciliation;
- inspect the final diff for scope and sensitive material;
- stage only approved files and inspect the staged diff;
- create the intended commit or commit structure;
- push normally without force;
- create or update exactly the intended PR;
- verify PR base, head, commit count, changed-file list, title, body, and
  sensitive-content safety;
- leave the PR open and unmerged.

Use the normal PR structure:

- Summary
- Changes
- Validation

A reusable PR template is optional guidance, not a mandatory framework.

Gate D does not amend, squash, rebase, reset, cherry-pick, rewrite history,
force-push, merge, or enable auto-merge unless the owner explicitly authorizes
the particular action. PR merge remains manual. Gate D does not author semantic
content changes; route any discovered content defect back to implementation or
planning.

## 11. Correction Routing

| Discovery | Route |
|---|---|
| Selected unit contains multiple independent outcomes or has a wrong ownership/dependency boundary | Stage 0 |
| A written plan has a defect within a sound boundary | Gate A correction |
| Implementation has a defect within the selected scope | Gate B correction |
| Correct implementation requires a changed design, new product behavior, or unresolved owner decision | Gate A or owner decision, as appropriate |
| Final infrastructure is required but not selected or evidenced | Defer to the corrected-master owner/trigger, or stop if current work truly depends on it |
| Independent review finds a material implementation or evidence defect | Separate correction, validation, and new independent review |
| Git finalization finds semantic or publication-integrity trouble | Stop and route to the responsible earlier work; Gate D does not fix content |

## 12. Register Updates

The execution register is a factual status record, not scope authority or an
automatic work selector. Update it when a substantive change alters accepted
execution state, a decomposition is genuinely created, or recorded history is
found inaccurate.

Register updates normally travel with the substantive PR. They must distinguish
merged/accepted work, implemented but unmerged work, remaining corrected-master
scope, and late-bound obligations. Do not mark work accepted before merge or
claim deferred evidence is complete.

## 13. Stop Conditions

Stop and report when:

- the worktree, branch, baseline, or intended publication state is unsafe or
  ambiguous;
- the selected scope conflicts with the corrected master;
- a required owner decision is missing;
- a real prerequisite is missing;
- current completion depends on unselected or unevidenced final infrastructure;
- a provider, deployment, migration, database, credential, or runtime action
  needs approval that has not been given;
- correct completion requires unrelated product expansion or files outside the
  selected outcome;
- evidence would overclaim external facts;
- validation exposes a defect requiring broader design or authority;
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
2. fetch remote metadata;
3. fast-forward local `develop` to `origin/develop`;
4. verify local and remote `develop` agree;
5. update factual execution state when needed.

Select later work from the corrected master, current repository truth, real
prerequisites, deferred-trigger state, and owner direction. Stage 0 and Gate A
remain available when the next unit genuinely needs decomposition or planning;
they are not automatic prerequisites. If several units are valid and no real
dependency selects one, ask the owner rather than inventing priority.
