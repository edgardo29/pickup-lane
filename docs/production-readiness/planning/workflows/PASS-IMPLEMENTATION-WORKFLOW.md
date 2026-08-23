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
- select the next pass without explicit owner instruction;
- mutate providers, databases, deployments, credentials, or runtime settings
  unless the approved executable pass explicitly owns that action.

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

If the workflow is unclear, stop and ask for owner direction. Do not choose the
next pass or workflow from filename order.

## 4. Shared Rules For All Stages

Every stage must:

- start from a clean, understood Git state;
- apply the authority order from the read-first document;
- apply the instruction-adherence rule from the read-first document to the
  current approved instruction before acting;
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
7. create the local working branch specified by the approved instruction;
8. use that branch through Stage 0, Gate A, Gate B, Gate C, and Gate D unless a
   structural Stage 0 revision explicitly requires a local branch rename;
9. do not push merely for branch creation.

Pass-specific approved instructions control branch names. This workflow does not
prescribe a universal branch-name format.

Unexpected local work, divergence, worktree conflict, or branch ambiguity causes
a stop. Do not automatically reset, rebase, merge, stash, restore, clean, or
delete anything.

If preserved local work such as a stash is later restored or converted into
commit-eligible pass artifacts, recheck it for prohibited sensitive material
under the read-first document before continuing.

Stage 0 and Gate A may create or edit only their explicitly authorized planning
artifacts. Stage 0 and Gate A must not stage, commit, push, create a PR, or
update a PR. Publication remains Gate D-only after explicit owner authorization.

## 6. STAGE 0: Pass Intake And Decomposition

Stage 0 is the owner-approved entry process before Gate A. It decides what
executable pass should exist. It does not edit production code, tests,
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
- Which parts are too broad to implement and review in one PR?
- Which prerequisite contracts must be preserved?

Do not modify the master blueprint to make the decomposition easier.

### 6.3 Decomposition Decision

Choose one of these outcomes:

| Outcome | Meaning |
|---|---|
| Implement parent as one executable pass | The parent pass is narrow enough to plan, implement, prove, review, and publish as one coherent PR. |
| Decompose into ordered child passes | The parent pass is too broad. Stage 0 defines child pass IDs, order, scope, dependencies, and non-overlap. |
| Stop for prerequisite | Current authority, dependency, provider access, owner decision, or evidence is missing. |
| Stop for owner decision | Existing authority cannot decide a product, security, operational, or policy question. |

Child pass IDs must be stable and must preserve the parent ID prefix where
practical, for example `WS03-03A` and `WS03-03B`.

### 6.4 Executable-Pass Cohesion Test

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

### 6.5 Split Boundaries

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

### 6.6 Child-Pass Rules

When a parent is split:

- the parent is an umbrella and is not implemented directly;
- every child is an executable pass;
- every child receives its own fresh Gate A;
- each later child starts from current `develop` after earlier required
  children merge;
- no later child blindly reuses a detailed plan designed against an older
  baseline;
- the parent is complete only after every approved child is complete and every
  parent obligation is accounted for.

If Gate A discovers before freeze that a child is still too broad, stop and
return to Stage 0.

### 6.7 No-Gap / No-Overlap Rule

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

Every parent control or requirement must have one primary implementing child
or one clearly named evidence/governance owner. No obligation may disappear
between children.

### 6.8 Intake Record Storage And Publication

For future intake records, use the existing pass-family structure:

```text
docs/production-readiness/planning/passes/<family>/<parent-id>-intake.md
```

Do not create retroactive intake documents for already accepted historical
splits such as WS02-04, WS02-05, or WS03-03.

Stage 0 may create or update only the intake record authorized by its
instruction.

Intake approval authorizes the accepted parent/child structure and the next
executable child's Gate A. It does not authorize Gate B.

Complete the intake record, compute its SHA-256, and report the exact intake
path and SHA before human approval. Human intake approval applies to that exact
reported path and SHA. After approval, the intake record is frozen. The frozen
intake record is read-only during Gate A and Gate B, and any content change
produces a new SHA and requires a Stage 0 revision plus new human approval. Do
not embed a mutable SHA inside the intake document; the SHA belongs in Stage 0
reports and approved instructions.

When a new intake record is created, it is published with the first substantive
child pass, but it is not Gate B-editable. Later child passes consume the
already-accepted intake record from current `develop` and do not edit it unless
the parent structure itself requires a Stage 0 revision. If a parent is
implemented whole, treat its approved intake record the same way as a
first-child intake artifact.

Historical decompositions do not require retroactive intake records.

By default, the approved intake record is published in the first substantive
child-pass PR, not in a separate intake-only PR. A separate intake-only PR is
exceptional and requires explicit human approval because no safe child can
begin until the structure itself is versioned.

### 6.9 Intake Approval

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
- intake-record path when applicable;
- intake-record SHA-256 reported for approval when an intake record exists;
- proposed Gate A planning file;
- exact approved parent/child structure;
- exact next executable child authorized for Gate A;
- blockers.

For new parent or remaining parent scope, no Gate A design begins until the
owner approves the exact intake path and SHA for the next executable pass.
Explicit owner direction selects the parent pass or remaining parent scope to
evaluate; it does not bypass Stage 0. An already accepted intake record from
current `develop` may be consumed without recreating Stage 0, and historical
accepted decompositions remain exempt from retroactive intake creation.

## 7. GATE A: Executable-Pass Design

Gate A converts approved intake into a frozen executable pass plan. It is
read-only with respect to production source, tests, requirement declarations,
testing records, provider settings, migrations, and runtime configuration
except for the canonical pass plan itself when the prompt authorizes that edit.

### 7.1 Gate A Responsibilities

Gate A must:

- confirm branch, baseline, clean status, and current accepted `develop`;
- reread the approved intake and verify its path and SHA-256 when one exists,
  then reread this workflow, planning template, testing-record template, and
  applicable standards;
- confirm one primary outcome, one coherent requirement family, one safe
  merge/rollback or forward-fix unit, approved intake boundary, current
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
- stop on conflicts, missing owner decisions, missing proof layers, or scope
  that cannot fit the approved executable pass.

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
for the same approved engineering outcome does not itself require Gate A
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
because of the approved implementation. Do not wait for full regression to
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
frozen only after human approval.

Before Gate A reports the canonical plan ready for human approval, it must
reverify that the approved intake-record SHA remains unchanged when an intake
record applies. If the intake SHA changed, stop, do not approve Gate A, return
to Stage 0, compute a new intake SHA, and require new human Stage 0 approval.

Gate A must also verify current branch, accepted baseline, merge-base with that
baseline, no staged content, and that only the explicitly authorized Gate A
planning artifact changed during Gate A.

At the end of Gate A, compute the canonical-plan SHA-256 and report it with the
exact plan path. Human Gate A approval freezes that exact SHA. Do not embed a
mutable SHA in the canonical planning document itself; the SHA belongs in gate
reports and approved instructions.

Gate B must verify the frozen canonical-plan SHA before implementation and again
at completion. Gate C must verify it before semantic review. Gate D must verify
it before staging and committing. Gate B must not edit the frozen canonical
plan. Any required canonical-plan content change returns to Gate A and produces
a new SHA plus new human approval.

## 8. GATE B: Implementation And Trusted Evidence

Gate B implements exactly the human-approved Gate A design. It must not
redesign the pass while implementing it.

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
  approved intake-record path and SHA when applicable, frozen canonical-plan
  path and SHA, frozen engineering design, implementation scope boundaries, and
  validation strategy;
- verify the approved intake-record SHA when applicable and the frozen
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
  approved requirements, engineering design, proof strategy, and pass scope;
- stop and return to Gate A if correct completion needs a new requirement,
  changed engineering design, changed proof strategy, provider mutation,
  a migration not already approved by the frozen design, owner decision, or
  broader pass scope;
- stop and return to Stage 0 if the executable-pass boundary itself is wrong.

The branch HEAD and merge-base must still reflect the approved baseline.
Unexpected commits, divergence, staged content, unrelated local changes, or
branch ambiguity cause a stop. Do not automatically merge, rebase, reset,
cherry-pick, stash, restore, clean, or delete.

Before handoff, Gate B must reverify current branch, accepted baseline,
merge-base with that baseline, approved intake-record SHA when applicable,
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

## 9. GATE C: Independent Semantic Review

Gate C is a new independent read-only review of the entire final pass state.
Green commands are not semantic approval.

Gate C must inspect:

- branch, HEAD, accepted baseline, merge-base with that baseline, staged-file
  status, complete actual changed-file set, and file-by-file scope
  justification;
- current approved instruction and authorized execution boundaries;
- authority and approved intake;
- approved intake-record path and SHA when applicable;
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
- the complete local change set and secret/confidentiality safety.

Gate C must verify that the complete tracked pass state contains no prohibited
literal credentials or sensitive values under the read-first document.
Gate C approval confirms that the final pass state matches both the frozen
design and the current approved instruction's execution boundaries.

Gate C must use a new independent read-only reviewer. It must not edit files,
stage files, commit, push, create or update a PR, merge, rebase, reset, apply a
stash, or self-fix. Gate C must review the complete diff from the accepted
baseline, not merely inspect currently modified files without confirming the
baseline.

Gate C has exactly two outcomes:

- approved for Git finalization;
- corrections required.

Gate C returns all material findings together. It does not automatically rerun
already-current successful suites. When a concrete concern exists, run only the
smallest focused reproduction needed and report the exact reason and
reproduction.

If a correction changes repository content, the corrected final pass must
receive correction validation and a new full independent Gate C review of the
entire corrected pass before Gate D. Targeted-only final approval is forbidden.

At the end of Gate C, verify repository contents and staged state remained
unchanged by the review.

## 10. GATE D: Git And PR Finalization

Gate C approval makes a pass eligible for Gate D. It does not automatically
authorize staging, committing, pushing, or PR creation. Codex must not stage,
commit, push, create a PR, or update a PR until the owner explicitly gives a
Gate D publication instruction.

Gate D is mechanical and runs only after Gate C approval and explicit owner
Gate D authorization.

Gate D must:

- before staging, fetch remote metadata safely;
- verify current branch, current HEAD, accepted baseline, merge-base with that
  baseline, local/remote branch state, approved intake SHA when applicable,
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
force-push, merge, or enable auto-merge unless the pass-specific instruction
explicitly authorizes that operation.

If `origin/develop` has advanced beyond the accepted baseline, stop, report the
old accepted baseline, current `origin/develop`, and the divergence. Do not
automatically merge, rebase, reset, cherry-pick, or force-push. Require explicit
owner-approved reconciliation and any materially required revalidation before
Gate D can resume. Do not publish stale-baseline work silently.

## 11. Correction Routing

| Discovery | Route |
|---|---|
| Parent contains multiple independent outcomes | Stage 0 |
| Proposed child remains too broad before Gate A freeze | Stage 0 revision |
| Gate A identifies another file for same coherent outcome | Include before Gate A freeze |
| Gate A identifies a separate outcome | Stage 0 revision |
| Gate B finds an implementation defect inside frozen scope | Fix and validate in Gate B |
| Gate B needs another file for the same approved outcome | Continue Gate B and justify the file against the frozen design |
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

- the first child substantive PR includes the frozen approved intake record and
  the register update describing the accepted intake/decomposition reference,
  accepted first-child state, remaining child state, and incomplete parent state
  unless all children are complete;
- later child PRs update the register for that child's accepted state and the
  remaining parent state;
- the final child PR records final-child acceptance and marks the parent
  complete;
- when a parent is kept whole, the substantive PR includes the direct parent
  completion update;
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
- external/provider/runtime evidence still required.

Updating the register does not select the next pass.

## 13. Stop Conditions

Stop and report instead of continuing when:

- current repository state is dirty or ambiguous;
- local `develop` cannot fast-forward to `origin/develop`;
- the intended workflow is unclear;
- parent-pass scope cannot be decomposed honestly;
- a required owner decision is missing;
- a provider, runtime, migration, deployment, or operational action is needed
  but not explicitly approved;
- the pass needs files outside the approved scope;
- evidence would overclaim external facts;
- validation exposes a defect requiring broader authority or proof-layer
  changes;
- a child allocation creates a gap, unapproved overlap, or unsafe partial
  state;
- sensitive material would enter Git or a PR.

## 14. Completion Meaning

An executable pass is complete when its approved Gate D PR has been merged and
current accepted `develop` contains the pass output. That does not necessarily
mean the broader audit controls are closed. Controls close only through the
final evidence and reassessment process defined by the remediation plan and
master blueprint.
