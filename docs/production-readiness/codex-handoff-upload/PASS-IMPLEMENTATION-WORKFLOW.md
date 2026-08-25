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

The permanent shape is:

```text
STAGE 0: PASS INTAKE AND DECOMPOSITION
-> GATE A: EXECUTABLE-PASS DESIGN
-> GATE B: IMPLEMENTATION AND TRUSTED EVIDENCE
-> GATE C: INDEPENDENT SEMANTIC REVIEW
-> GATE D: GIT AND PR FINALIZATION
```

## 1. Purpose And Applicability

Use this workflow when a production-readiness pass is being implemented as a
new executable pass rather than rechecked after prior implementation.

The workflow applies when:

- the original master blueprint contains a parent-level planned pass;
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
AUTHORITATIVE PRODUCT / PRODUCTION-READINESS SOURCES
-> PARENT BLUEPRINT PASS
-> PASS INTAKE AND DECOMPOSITION
-> EXECUTABLE PASS PLAN
-> STABLE REQUIREMENTS / RISKS / EVIDENCE DESIGN
-> IMPLEMENTATION AND TRUSTED EVIDENCE
-> VALIDATION AND INDEPENDENT REVIEW
```

The master blueprint remains authoritative for the original parent-level pass
register. It does not by itself authorize a too-large branch or force a parent
pass to be implemented as one executable unit.

When a parent pass is too broad, Stage 0 decomposes it into one or more
bounded executable child passes. The child pass must preserve the parent pass
intent, controls, dependencies, and evidence boundaries while remaining small
enough for meaningful implementation and review.

Current accepted `develop` is repository truth for current implementation
state. Source code does not define requirements by itself, and tests do not
define production behavior.

Authority defines what must be true. Stage 0 defines the executable boundary.
Gate A defines requirements, contracts, risks, proof layers, and exact scope.
Gate B implements the approved behavior and evidence together. Implementation
does not create its own requirements.

## 3. Workflow Selection

Before starting pass work, determine the workflow.

| Situation | Workflow |
|---|---|
| The pass has already been accepted or merged and is being revalidated or repaired later. | `docs/production-readiness/planning/workflows/PASS-RECHECK-WORKFLOW.md` |
| The pass is being implemented for the first time from current authority. | This document |
| A completed Gate C found a defect in the same unmerged first-time pass. | Scoped correction under this implementation workflow, followed by correction validation and a new full Gate C review |
| The task is global workflow maintenance, documentation navigation, or register maintenance. | The explicit task prompt, not a production-readiness implementation pass |

If the workflow is unclear, stop and report the ambiguity. Do not choose the
next pass or workflow from filename order. Automated progression may select the
next child or parent only when current durable authority, accepted dependencies,
the execution register, and current `develop` determine one unambiguous next
unit.

## 4. Shared Rules For All Stages

Every stage must:

- start from a clean, understood Git state;
- apply the authority order from the read-first document;
- apply the instruction-adherence rule from the read-first document to the
  current run instruction before acting;
- read the current pass intake, current or frozen pass plan, and applicable
  templates before acting;
- treat explicit scope, editable files, paths, SHAs, validation requirements,
  stage or gate boundaries, and stop conditions from the current instruction as
  binding constraints;
- follow the excluded legacy-test rule owned by the read-first document;
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
  conflicts with authority, repository truth, or a frozen artifact.

Before any stage or gate reports completion, compare the actual work performed
against the binding current instruction. Correct any in-scope mismatch before
handoff, or report the mismatch and stop.

## 5. Forward-Pass Initialization

Before Stage 0 or Gate A edits any repository content, initialize the pass from
current accepted `develop`.

Required initialization:

1. fetch remote metadata safely;
2. verify the worktree and index are clean or explicitly understood;
3. switch to local `develop`;
4. run a fast-forward-only update from `origin/develop`;
5. verify local `develop` equals `origin/develop`;
6. record the exact accepted baseline;
7. create or switch to the local working branch specified by current authority
   or the user; when automated progression selects a new executable pass and no
   different branch name is mandated, use `pr/<EXECUTABLE-PASS-ID>`;
8. use that branch through Stage 0, Gate A, Gate B, Gate C, and Gate D unless a
   structural Stage 0 revision requires a different executable-pass branch;
9. do not push merely for branch creation.

Unexpected local work, divergence, worktree conflict, or branch ambiguity causes
a stop. Do not automatically reset, rebase, merge, stash, restore, clean, or
delete anything.

If preserved local work such as a stash is later restored or converted into
commit-eligible pass artifacts, recheck it for prohibited sensitive material
under the read-first document before continuing.

Stage 0 and Gate A may create or edit only their explicitly authorized planning
artifacts. Stage 0 and Gate A must not stage, commit, push, create a PR, or
update a PR. Publication remains Gate D-only after a clean Gate C review.

## 6. STAGE 0: Pass Intake And Decomposition

Stage 0 is the parent-pass entry process before Gate A. It decides what
executable pass or ordered child structure should exist. It does not edit
production code, tests,
requirement declarations, testing records, provider settings, migrations, or
runtime configuration.

Use `docs/production-readiness/planning/templates/PASS-INTAKE-TEMPLATE.md` for
the intake record.

### 6.1 Inputs

Read:

- the read-first document and program context;
- this workflow;
- `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md`;
- the relevant master blueprint parent pass entry;
- the relevant final remediation-plan workstream sections;
- approved decisions and governance records that define the parent pass;
- accepted prerequisite pass plans and evidence boundaries;
- current accepted repository truth for the area;
- applicable engineering and testing standards.

### 6.2 Parent-Pass Reconciliation

For the selected parent blueprint pass, answer:

- What controls, decisions, dependencies, and evidence classes does the parent
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
  evidence contracts/checkers, synthetic fixtures, or handoff rules?
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
- the preserved parent controls/requirements and evidence obligations;
- the exact trigger that makes the work executable;
- prerequisites and downstream consumers;
- the latest required completion boundary;
- execution-register visibility;
- an explicit statement that deferred status is not proof or control closure.

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
requirement declaration, testing record, trusted tests, and compatibility
evidence travel with the contract they establish.

Do not permit an unsafe partial merge merely to create smaller PRs.

### 6.7 Child-Pass Rules

When a parent is split:

- the parent is an umbrella and is not implemented directly;
- every child is an executable pass;
- every child receives its own fresh Gate A;
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
- the parent or affected controls must not be represented as fully production
  verified while a mandatory deferred obligation remains outstanding;
- every parent obligation remains accounted for through accepted children or an
  explicitly recorded mandatory deferred owner.

If Gate A discovers before freeze that a child is still too broad, or that its
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

Every parent control or requirement must have one primary implementing child,
one clearly named evidence/governance owner, or one mandatory deferred follow-up
with an exact trigger and latest completion boundary. No obligation may disappear
between children, become implicitly accepted because its trigger is false, or be
replaced with temporary-provider evidence.

### 6.9 Intake Record Storage And Publication

For future intake records, use the existing pass-family structure:

```text
docs/production-readiness/planning/passes/<family>/<parent-id>-intake.md
```

Do not create retroactive intake documents for already accepted historical
splits such as WS02-04, WS02-05, or WS03-03.

Stage 0 may create or update only the intake record authorized by its current
run.

Complete the intake record, compute its SHA-256, and report the exact intake
path and SHA. A valid Stage 0 result freezes that exact intake artifact for the
current automated run and authorizes the first executable pass to begin Gate A.
It does not itself authorize Gate B. The frozen intake record is read-only
during Gate A and Gate B, and any content change produces a new SHA and
requires a Stage 0 revision. Do not embed a mutable SHA inside the intake
document; the SHA belongs in Stage 0 reports and run instructions.

When a new intake record is created, it is published with the first substantive
child pass, but it is not Gate B-editable. Later child passes consume the
already-accepted intake record from current `develop` and do not edit it unless
the parent structure itself requires a Stage 0 revision. If a parent is
implemented whole, treat its frozen intake record the same way as a
first-child intake artifact.

Historical decompositions do not require retroactive intake records.

By default, the Stage 0 intake record is published in the first substantive
child-pass PR, not in a separate intake-only PR. A separate intake-only PR is
exceptional and requires explicit owner direction because no safe child can
begin until the structure itself is versioned.

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
- intake-record SHA-256 reported for approval when an intake record exists;
- proposed Gate A planning file;
- exact approved parent/child structure;
- exact next executable child authorized for Gate A;
- blockers.

For new parent or remaining parent scope, a valid Stage 0 result automatically
selects the first executable pass and advances it to Gate A. An intake record
already accepted in current `develop` may be consumed without recreating Stage
0, and historical accepted decompositions remain exempt from retroactive intake
creation.

After a child PR is manually merged, do not rerun Stage 0 merely because the
next accepted child is beginning. Start that child from current accepted
`develop` with a fresh Gate A when its prerequisites and any execution trigger
are satisfied.

A mandatory deferred follow-up whose final-infrastructure trigger is false is
not a current executable child. Keep it visible in the intake and execution
register, preserve its obligations as open, and continue only to downstream work
whose own prerequisites do not require those deferred facts. When the trigger
becomes true, the deferred unit becomes eligible for fresh Gate A and must run no
later than its recorded completion boundary.

When all currently executable child obligations are complete, determine
progression from the master blueprint, remediation plan, execution register,
dependency state, deferred-trigger state, and current accepted repository truth.
Do not mark deferred provider/runtime obligations as proven merely to advance. If
exactly one next unit is determined, begin it at the applicable Stage 0 or fresh
Gate A boundary. If durable authority leaves multiple equally valid next units,
stop for owner selection instead of inventing priority.

## 7. GATE A: Executable-Pass Design

Gate A converts the accepted Stage 0 boundary into a frozen executable pass
plan. It includes planning followed by a read-only review of the complete plan.
A clean review freezes the exact reviewed canonical-plan SHA and advances
automatically to Gate B. Gate A is read-only with respect to production source, tests,
requirement declarations, testing records, provider settings, migrations, and
runtime configuration except for the canonical pass plan itself when the prompt
authorizes that edit. Any plan correction is performed by the main Codex session
as separate Gate A correction work.

### 7.1 Gate A Responsibilities

Gate A must:

- confirm branch, baseline, clean status, and current accepted `develop`;
- reread the accepted intake and verify its path and SHA-256 when one exists,
  then reread this workflow, planning template, testing-record template, and
  applicable standards;
- confirm one primary outcome, one coherent requirement family, one safe
  merge/rollback or forward-fix unit, accepted intake boundary, current
  accepted prerequisites, and exact child handoff;
- reconcile the executable pass against current authority and current source;
- define stable requirements and requirement states;
- define exact technical contracts and invariants;
- define pass-owned source, configuration, documentation, provider, runtime,
  migration, operational, and evidence boundaries;
- decide the lowest reliable proof layer for each requirement;
- design requirement declarations and testing records where applicable;
- design executable and non-executable evidence;
- define the Gate B implementation scope and changed-file justification rule;
- require Gate B to modify only files genuinely necessary to implement and
  prove the frozen engineering design;
- require every substantive first-time executable pass to update
  `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md`, and
  design the exact register change that will become true upon merge;
- identify all external, deferred, blocked, and covered-elsewhere facts;
- confirm that any final-infrastructure-dependent requirement belongs either to
  a triggered current pass with accepted evidence or to a Stage 0-recorded
  mandatory deferred follow-up;
- reject completion criteria that require temporary Vercel, Render, Neon, local,
  CI, README, free-tier, framework-default, or demo values to stand in for final
  production facts;
- stop on conflicts, missing owner decisions, missing proof layers, scope that
  cannot fit the current executable pass, or a late-bound infrastructure
  dependency that Stage 0 did not allocate correctly.

The final Gate A plan must distinguish:

| Scope item | Required meaning |
|---|---|
| Frozen Stage 0 intake artifact | Included when a new intake record was created; published with the pass when applicable; not Gate B-editable. |
| Frozen Gate A canonical plan | Published with the pass; not Gate B-editable. |
| Gate B implementation scope | Gate B may modify any repository file genuinely necessary to implement and prove the frozen engineering design. |
| Changed-file scope review | Gate C and Gate D review actual changed files for justification against the frozen scope and design rather than equality with a predicted filename list. |

For a first substantive child, the published change set includes the frozen
Stage 0 intake record, frozen Gate A canonical plan, every implementation and
evidence file genuinely needed by the frozen design, and
`docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md`.

For later children, the published change set includes the frozen Gate A
canonical plan, every implementation and evidence file genuinely needed by the
frozen design, and the execution register. The accepted intake record already
exists in `develop` and normally does not appear in the later-child diff.

For a parent kept whole, the published change set includes the frozen Stage 0
intake record, frozen Gate A canonical plan, every implementation and evidence
file genuinely needed by the frozen design, and the execution register.

This is not a predicted filename allowlist. Discovering another necessary file
for the same frozen engineering outcome does not itself require Gate A
correction, but every changed file must be justified by the frozen pass scope
and design.

### 7.2 Repository-Wide Impact And Compatibility Scan

Before freezing the engineering design and proof strategy, Gate A must inspect
every applicable:

- backend caller;
- frontend caller;
- route registration;
- dependency expectation;
- request/response/OpenAPI contract;
- settings/env inventory;
- CORS/header inventory;
- middleware-order assumption;
- provider/network boundary inventory;
- timeout operation inventory;
- retry/reconciliation registry;
- provider-cost/rate inventory;
- security negative-space inventory;
- exact finite set/allowlist;
- schema/migration expectation;
- database constraint;
- accepted prior-pass compatibility test;
- materially affected documentation statement.

Gate A must identify every trusted compatibility file expected to become stale
because of the frozen implementation. Do not wait for full regression to
discover an obvious finite inventory or caller expectation.

### 7.3 Gate A Outputs

Gate A returns:

- the frozen Gate A plan artifact;
- the exact canonical-plan path and SHA-256;
- requirement reconciliation;
- exact implementation and evidence design;
- implementation scope boundaries and changed-file justification rule;
- validation plan;
- explicit non-goals and external evidence boundaries;
- blockers.

The plan, canonical-plan SHA, requirements, correction/design decisions,
evidence design, implementation scope boundaries, and validation strategy become
frozen when a clean Gate A plan review approves the exact current canonical-plan
SHA.

Before Gate A begins plan review, it must reverify that the frozen
intake-record SHA remains unchanged when an intake record applies. If the intake
SHA changed, stop the current Gate A, return to Stage 0, and compute a new intake
SHA before restarting Gate A under the corrected Stage 0 boundary.

Gate A must also verify current branch, accepted baseline, merge-base with that
baseline, no staged content, and that only the explicitly authorized Gate A
planning artifact changed during Gate A.

When the main Codex session finishes the current Gate A plan draft or
correction, compute the canonical-plan SHA-256 and report it with the exact plan
path. Gate A review covers that exact current SHA. A clean review freezes that
exact SHA and automatically authorizes Gate B. If plan content changes after the
clean review, the review is no longer current and the changed plan must receive a
new full Gate A review before it can govern Gate B. Do not embed a mutable SHA in
the canonical planning document itself; the SHA belongs in gate reports and run
instructions.

Gate B must verify the frozen canonical-plan SHA before implementation and again
at completion. Gate C must verify it before semantic review. Gate D must verify
it before staging and committing. Gate B must not edit the frozen canonical
plan. Any required canonical-plan content change returns to Gate A, produces a
new SHA, and requires a new clean Gate A plan review before Gate B resumes.

### 7.4 Gate A Plan Review

Before Gate B, the complete current canonical plan must receive a read-only
review.

The review must inspect the complete plan against:

- current authority and accepted intake when applicable;
- current repository truth and accepted prerequisites;
- the complete executable-pass obligation;
- requirements and requirement ownership;
- technical contracts and invariants;
- repository-wide impact and compatibility analysis;
- implementation scope and changed-file justification rules;
- evidence design and proof-layer choices;
- validation strategy and proof feasibility;
- non-goals, handoffs, external/later-pass gaps, and completion criteria;
- final-infrastructure timing, provider-neutrality, deferred-owner/trigger
  correctness, and absence of temporary-provider substitution;
- applicable engineering/testing standards and templates.

For recheck-equivalent planning concerns that arise during a first-time pass,
review the current plan against repository truth and authority without importing
historical recheck mechanics that do not apply.

The review must be comprehensive and return all material findings together. Do
not drip-feed findings across rounds or require corrections for cosmetic
wording, stylistic preferences, harmless naming differences, formatting
preferences, or another reasonable design choice that still fully satisfies the
authority and approved executable boundary. A correction-worthy finding must
materially affect requirement correctness/completeness, technical-design
sufficiency, evidence/proof adequacy, validation adequacy, scope/ownership,
security/production-readiness behavior, traceability, or completion
truthfulness.

The review has these semantic outcomes:

- plan approved (`gate_a_plan_approved`);
- corrections required (`gate_a_corrections_required`).

A preflight condition that prevents the review is
`blocked_before_review`; it is not semantic approval or a correction finding.

When corrections are required, each finding must route to one of:

- Gate A correction when the executable boundary remains valid and the main
  Codex session can correct the plan within existing authority;
- Stage 0 when the executable-pass boundary, parent/child allocation,
  decomposition, separate outcome, or dependency allocation is wrong;
- blocker/owner direction when correct planning requires unresolved authority,
  a missing owner/product/security/policy/operational decision, unavailable
  required evidence/proof capability, unsafe Git state, sensitive-data handling,
  or another durable stop condition.

Eligible Gate A corrections are performed by the main Codex session as separate
correction work, after which the entire corrected plan receives a new full
review.

For automated execution, one Gate A plan-review cycle may contain at most three
full reviews and at most two automatic plan-correction rounds:

1. Plan Review 1 performs a full review. If it returns eligible Gate
   A corrections, Plan Correction Round 1 may run, produce a new plan SHA, and
   continue to the next full review.
2. Plan Review 2 performs another full review of the entire corrected
   plan. If it returns eligible Gate A corrections, Plan Correction Round 2 may
   run, produce a new plan SHA, and continue to the next full review.
3. Plan Review 3 performs a final full review of the entire corrected
   plan. If it still returns material corrections required, stop for owner
   direction. Do not perform an automatic Plan Correction Round 3.

Review count does not reset merely because a correction run starts. A finding
that routes to Stage 0 or a blocker/owner decision exits the automatic
plan-review cycle immediately and follows that routing instead.

When Review 2 or Review 3 discovers a material issue that was already present
and reasonably discoverable in the immediately preceding reviewed plan state,
and that issue was not introduced or newly exposed by the intervening
correction, identify it as a prior-review miss. The classification makes review
quality visible; it does not make the issue non-material.

`gate_a_plan_approved` freezes the exact reviewed canonical-plan SHA for the
current automated run. The main Codex session then begins Gate B subject to the
normal Gate B preflight.

## 8. GATE B: Implementation And Trusted Evidence

Gate B implements exactly the frozen Gate A design that passed Gate A review. It
must not redesign the pass while implementing it.

### 8.1 Requirement-Group Implementation Order

Develop implementation and evidence together by coherent requirement group:

```text
REQUIREMENT / INVARIANT
-> PRODUCTION OR ARTIFACT IMPLEMENTATION
-> FOCUSED TRUSTED EVIDENCE
-> COMPATIBILITY UPDATE
-> FOCUSED VALIDATION
```

Do not implement all source first and bolt evidence on afterward. Skip any
item that Gate A explicitly marked not applicable.

### 8.2 Gate B Rules

Gate B must:

- before editing, verify current branch, current HEAD, accepted baseline,
  merge-base with the accepted baseline, worktree status, staged-file status,
  frozen intake-record path and SHA when applicable, frozen canonical-plan
  path and SHA, frozen engineering design, implementation scope boundaries, and
  validation strategy;
- verify the frozen intake-record SHA when applicable and the frozen
  canonical-plan SHA before implementation;
- modify only files genuinely necessary to implement and prove the frozen
  engineering design;
- not edit the frozen intake record or frozen canonical plan;
- preserve pass boundaries and prerequisite contracts;
- use `docs/production-readiness/planning/templates/TESTING-RECORD-TEMPLATE.md`
  for any testing record;
- derive tests from authority and the frozen plan, not from current code shape
  alone;
- verify meaningful persisted effects, rejected side effects, concurrency,
  time, provider, browser, migration, or recovery behavior where the frozen
  plan requires it;
- run the frozen applicable validation layers and report commands not run;
- continue within Gate B when another file is genuinely necessary for the same
  frozen requirements, engineering design, proof strategy, and pass scope;
- stop and return to Gate A if correct completion needs a new requirement,
  changed engineering design, changed proof strategy, provider mutation,
  a migration not already approved by the frozen design, owner decision, or
  broader pass scope;
- stop and return to Stage 0 if the executable-pass boundary itself is wrong,
  including when implementation discovers that current completion actually
  requires intentionally unselected final infrastructure that should have been
  separated into a mandatory deferred follow-up.

The branch HEAD and merge-base must still reflect the approved baseline.
Unexpected commits, divergence, staged content, unrelated local changes, or
branch ambiguity cause a stop. Do not automatically merge, rebase, reset,
cherry-pick, stash, restore, clean, or delete.

Before handoff, Gate B must reverify current branch, accepted baseline,
merge-base with that baseline, frozen intake-record SHA when applicable,
frozen canonical-plan SHA, that every actual changed file is justified by the
frozen pass scope and design, and nothing staged.

Gate B ends with a validated local change set. It does not stage, commit, push,
create a PR, or begin Gate C.

After all requirement groups, run the validation layers frozen in Gate A, which
may include:

- complete focused pass scope;
- affected compatibility scopes;
- prerequisite regressions;
- frontend/browser/provider/migration/PostgreSQL/concurrency/runtime proof;
- domain checker;
- suite checker;
- generated traceability;
- broad regression selected in Gate A;
- final semantic sanity sweep;
- `git diff --check`;
- security/publication scan;
- exact scope/status verification.

## 9. GATE C: Semantic Review

Gate C is a read-only review of the entire final pass state. Green commands are
not semantic approval.

Gate C must inspect:

- branch, HEAD, accepted baseline, merge-base with that baseline, staged-file
  status, complete actual changed-file set, and file-by-file scope
  justification;
- current run instruction and authorized execution boundaries;
- authority and accepted intake;
- frozen intake-record path and SHA when applicable;
- frozen canonical-plan path and SHA;
- implementation;
- trusted evidence;
- requirement declaration;
- `TESTING_RECORD.md`;
- generated traceability;
- scope;
- security and publication safety;
- validation results;
- proposed execution-register update;
- actual changed-file scope justification;
- external and later-pass gaps;
- final-infrastructure timing and provider-neutrality, including whether any
  temporary Vercel, Render, Neon, local, CI, README, free-tier, or demo value was
  improperly promoted into final production evidence;
- the complete local change set and secret/confidentiality safety.

Gate C must verify that the complete tracked pass state contains no prohibited
literal credentials or sensitive values under the read-first document.
Gate C approval confirms that the final pass state matches both the frozen
design and the current run instruction's execution boundaries.

Gate C must not edit files, stage files, commit, push, create or update a PR,
merge, rebase, reset, apply a stash, or self-fix. Gate C must review the complete
diff from the accepted baseline, not merely inspect currently modified files
without confirming the baseline.

Gate C has exactly two outcomes:

- approved for Git finalization;
- corrections required.

Every Gate C review must be comprehensive across the complete current pass
state and return all material findings together. Do not drip-feed findings
across review rounds or create correction churn for cosmetic wording, stylistic
preferences, or other non-material issues. Require correction only for issues
affecting correctness, evidence truthfulness, security, scope, maintainability,
traceability, or production readiness.

When a later Gate C review discovers a material issue that was already present
and reasonably discoverable in the immediately preceding reviewed state, and
that issue was not introduced or newly exposed by the intervening correction,
identify it as a prior-review miss. The classification does not make the issue
non-material or remove the need for correct routing.

For automated execution, one Gate C review/correction cycle may contain at most
three full Gate C reviews and at most two automatic correction rounds:

1. Review 1 performs a full review. If it returns corrections
   required and the findings are eligible for scoped correction under the frozen
   design, Correction Round 1 may run, validate the corrected state, and continue
   to the next full review.
2. Review 2 performs another full review of the entire corrected
   pass. If it returns corrections required and the findings are still eligible
   for scoped correction under the frozen design, Correction Round 2 may run,
   validate the corrected state, and continue to the next full review.
3. Review 3 performs a final full review of the entire corrected
   pass. If Review 3 returns corrections required, stop for owner direction. Do
   not perform an automatic Correction Round 3. If any review is clean,
   automatically proceed to Gate D.

The review count is cumulative for the automatic cycle and does not reset merely
because a correction step starts. A finding that routes to Gate A, Stage 0, an
owner decision, or another approval boundary exits the automatic correction cycle
immediately and follows that routing instead. Gate C itself still stops after
each review and never performs corrections.

Gate C does not automatically rerun already-current successful suites. When a
concrete concern exists, run only the smallest focused reproduction needed and
report the exact reason and reproduction.

If a correction changes repository content, the corrected final pass must
receive correction validation and a new full Gate C review of the entire
corrected pass before Gate D. Targeted-only final approval is forbidden. The
automatic correction/review cycle remains subject to the three-review,
two-correction-round limit above.

At the end of Gate C, verify repository contents and staged state remained
unchanged by the review.

## 10. GATE D: Git And PR Finalization

A clean Gate C review automatically authorizes Gate D for the current automated
pass run.

Gate D is mechanical and begins immediately after Gate C approval.

Gate D must:

- before staging, fetch remote metadata safely;
- verify current branch, current HEAD, accepted baseline, merge-base with that
  baseline, local/remote branch state, frozen intake SHA when applicable,
  frozen canonical-plan SHA, Gate C-approved changed-file set, and nothing
  unexpectedly staged;
- verify whether current `origin/develop` still equals the accepted baseline;
- read
  `docs/production-readiness/planning/templates/PASS-PR-DESCRIPTION-TEMPLATE.md`;
- inspect the diff for scope and sensitive material;
- run an explicit final credential/secret scan, or equivalent
  repository-approved verification, before staging or publication;
- stage only approved files;
- inspect the staged diff;
- create the approved commit or commit structure;
- push normally without force;
- create or update exactly the intended PR;
- verify PR base, head, commit count, changed-file list, title, body, and
  sensitive-content safety;
- leave the PR open and unmerged.

Gate D must not amend, squash, rebase, reset, cherry-pick, rewrite history,
force-push, merge, or enable auto-merge. PR merge remains manual.

If `origin/develop` has advanced beyond the accepted baseline, stop, report the
old accepted baseline, current `origin/develop`, and the divergence. Do not
automatically merge, rebase, reset, cherry-pick, or force-push. Reconciliation
and any materially required revalidation must occur before Gate D can resume.
Do not publish stale-baseline work silently.

## 11. Correction Routing

| Discovery | Route |
|---|---|
| Parent contains multiple independent outcomes | Stage 0 |
| Proposed child remains too broad before Gate A freeze | Stage 0 revision |
| Gate A identifies another file for same coherent outcome | Include before Gate A freeze |
| Gate A identifies a separate outcome | Stage 0 revision |
| Gate A review finds a plan defect inside the approved executable boundary and existing authority | Separate Gate A correction by the main Codex session, then new full Gate A review |
| Gate A review finds the executable-pass boundary, parent/child allocation, or final-infrastructure deferral allocation wrong | Stage 0 revision |
| Gate A or Gate B discovers intentionally unselected final infrastructure is required by the current pass but no valid deferred owner/trigger exists | Stage 0 revision |
| Gate A Review 3 still finds material plan corrections | Stop for owner direction; no automatic Plan Correction Round 3 |
| Gate B finds an implementation defect inside frozen scope | Fix and validate in Gate B |
| Gate B needs another file for the same frozen outcome | Continue Gate B and justify the file against the frozen design |
| Gate B needs changed requirements, engineering design, proof strategy, or pass scope | Gate A correction |
| Gate B discovers a separate feature or child dependency | Stage 0 revision |
| Gate C finds implementation/evidence defect inside approved scope | Separate Gate B correction, validation, new full Gate C |
| Gate C finds pass-design defect without changing child structure | Gate A correction |
| Gate C finds parent/child allocation wrong | Stage 0 revision |
| Gate D finds semantic/content problem | Return to Gate B/Gate A; Gate D never fixes content |

## 12. Register Updates

Register updates normally travel with the substantive pass PR that makes the
new state true.

Every substantive first-time executable pass changes accepted execution state
when merged, so Gate A must design and Gate B must implement the exact
`docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md` update
that will become true upon merge. Program or documentation maintenance and
historical rechecks remain outside this automatic first-time-pass rule unless
their explicit scope says otherwise.

Default behavior:

- the first child substantive PR includes the frozen Stage 0 intake record and
  the register update describing the accepted intake/decomposition reference,
  accepted first-child state, remaining immediate-child state, and any mandatory
  deferred follow-up that remains open;
- later child PRs update the register for that child's accepted state, the
  remaining immediate-child state, and the current deferred-obligation state;
- the final immediate-child PR records that child's acceptance and may mark the
  current executable child set complete, but it must not mark the parent complete
  while a mandatory deferred follow-up or other parent obligation remains open;
- a decomposed parent is marked complete only when every accepted immediate child
  and every mandatory deferred follow-up or other parent obligation has been
  accepted, closed by authoritative evidence, or explicitly reallocated by higher
  authority;
- when a parent is kept whole, the substantive PR includes the direct parent
  completion update only when no separately recorded mandatory deferred obligation
  remains;
- register entries in a PR describe the accepted state that becomes true
  atomically upon merge;
- Gate C reviews the proposed register state with the complete pass;
- Gate D never authors or semantically edits register content;
- do not create routine tracker-only PRs after every pass.

Separate documentation-only register PRs require a genuine program-level
correction or explicit human instruction.

The register must distinguish:

- original parent-level blueprint passes;
- accepted executable child passes;
- parent passes that were decomposed;
- parent passes not yet selected;
- source-owned closeout documents;
- mandatory deferred follow-ups, their triggers, preserved obligations, and
  latest completion boundaries;
- external/provider/runtime evidence still required.

The register alone does not select the next executable unit. Automated
progression determines the next immediate child, triggered deferred follow-up, or
parent only from the register together with the master blueprint, remediation
plan, accepted intake/dependencies, prerequisites, deferred-trigger state, and
current accepted repository truth.

## 13. Stop Conditions

Stop and report instead of continuing when:

- current repository state is dirty or ambiguous;
- local `develop` cannot fast-forward to `origin/develop`;
- the intended workflow is unclear;
- parent-pass scope cannot be decomposed honestly;
- a required owner decision is missing;
- current completion depends on intentionally unselected final infrastructure
  and Stage 0 has not provided a valid provider-independent/deferred split;
- a pass attempts to use temporary Vercel, Render, Neon, local, CI, README,
  free-tier, framework-default, or demo values as final production evidence;
- a provider, runtime, migration, deployment, or operational action is needed
  but not explicitly approved;
- the pass needs files outside the approved scope;
- evidence would overclaim external facts;
- validation exposes a defect requiring broader authority or proof-layer
  changes;
- the third automatic Gate C review still returns corrections required;
- a child allocation creates a gap, unapproved overlap, or unsafe partial
  state;
- Gate A Plan Review 3 still requires material plan correction;
- sensitive material would enter Git or a PR.

## 14. Completion Meaning And Post-Merge Progression

An executable pass is complete when its Gate D PR has been manually merged and
current accepted `develop` contains the pass output. Executable-pass completion
is distinct from parent completion: a decomposed parent remains incomplete while
any mandatory deferred follow-up or other parent obligation is still open. That
also does not necessarily mean the broader audit controls are closed. Controls
close only through the final evidence and reassessment process defined by the
remediation plan and master blueprint.

When the workflow resumes after manual merge:

1. verify the intended PR actually merged;
2. fetch remote metadata;
3. fast-forward local `develop` to `origin/develop`;
4. verify local `develop` equals `origin/develop`;
5. record the new accepted baseline;
6. verify the execution-register state that became true with the merge.

Then determine progression from current durable authority:

- if another accepted immediate child remains for the current parent and its
  prerequisites and execution trigger are satisfied, create/switch to that
  child's pass branch from current `develop` and begin a fresh Gate A without
  rerunning Stage 0;
- if a mandatory deferred follow-up exists but its final-infrastructure trigger
  is false, keep it open in the execution register and do not select it merely
  because earlier children completed;
- continue to downstream work only when its own prerequisites do not require the
  deferred facts. If a downstream pass needs them, stop on that specific
  prerequisite until the deferred follow-up is completed;
- when a deferred follow-up's trigger becomes true, it becomes eligible for a
  fresh Gate A and must execute no later than its recorded completion boundary;
- if all current child obligations are accepted and no triggered deferred unit
  blocks progression, determine the next parent from the master blueprint,
  remediation plan, execution register, dependencies, deferred-trigger state,
  and current repository truth without treating deferred evidence as closed;
- before `CLOSE-01`, require every mandatory deferred follow-up that remains
  necessary for production readiness to be accepted;
- if exactly one next unit is determined, begin it at the applicable Stage 0 or
  fresh Gate A boundary;
- if durable authority leaves multiple equally valid next units, stop for owner
  selection instead of inventing priority.
