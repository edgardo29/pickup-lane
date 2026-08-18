# Production-Readiness Pass Implementation Workflow

This document defines the reusable process for implementing a Pickup Lane
production-readiness pass for the first time from current authority and current
accepted `develop`.

Use this workflow for forward implementation work. Use
`PASS-RECHECK-WORKFLOW.md` only when the task is to revalidate an already
implemented pass against current repository truth.

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

- revalidate an already implemented pass;
- repair a previously approved pass after Gate C findings;
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
-> IMPLEMENTATION
-> REQUIREMENTS / RISKS / EVIDENCE
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

## 3. Workflow Selection

Before starting pass work, determine the workflow.

| Situation | Workflow |
|---|---|
| The pass has already been implemented and is being revalidated. | `PASS-RECHECK-WORKFLOW.md` |
| The pass is being implemented for the first time from current authority. | This document |
| A completed Gate C found a defect in an approved pass change set. | Scoped correction under the owning workflow, followed by a new full Gate C review |
| The task is global workflow maintenance, documentation navigation, or register maintenance. | The explicit task prompt, not a production-readiness implementation pass |

If the workflow is unclear, stop and ask for owner direction. Do not choose the
next pass or workflow from filename order.

## 4. Shared Rules For All Stages

Every stage must:

- start from a clean, understood Git state;
- apply the authority order from the read-first document;
- read the current pass intake, current or frozen pass plan, and applicable
  templates before acting;
- preserve the excluded-test rule from the program context and workflow docs;
- distinguish repository truth, authority, provenance, inference, external
  evidence, and unknown facts;
- keep provider/runtime/control-plane facts unknown until accepted evidence
  exists;
- protect secrets, local paths, provider-private evidence, payment data, and
  personal data;
- stop rather than guess when authority, ownership, evidence layer, or scope is
  ambiguous.

## 5. STAGE 0: Pass Intake And Decomposition

Stage 0 is the owner-approved entry process before Gate A. It decides what
executable pass should exist. It does not edit production code, tests,
requirement declarations, testing records, provider settings, migrations, or
runtime configuration.

Use `PASS-INTAKE-TEMPLATE.md` for the intake record.

### 5.1 Inputs

Read:

- the read-first document and program context;
- this workflow;
- `PASS-EXECUTION-REGISTER.md`;
- the relevant master blueprint parent pass entry;
- the relevant final remediation-plan workstream sections;
- approved decisions and governance records that define the parent pass;
- accepted prerequisite pass plans and evidence boundaries;
- current accepted repository truth for the area;
- applicable engineering and testing standards.

### 5.2 Parent-Pass Reconciliation

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

### 5.3 Decomposition Decision

Choose one of these outcomes:

| Outcome | Meaning |
|---|---|
| Implement parent as one executable pass | The parent pass is narrow enough to plan, implement, prove, review, and publish as one coherent PR. |
| Decompose into ordered child passes | The parent pass is too broad. Stage 0 defines child pass IDs, order, scope, dependencies, and non-overlap. |
| Stop for prerequisite | Current authority, dependency, provider access, owner decision, or evidence is missing. |
| Stop for owner decision | Existing authority cannot decide a product, security, operational, or policy question. |

Child pass IDs must be stable and must preserve the parent ID prefix where
practical, for example `WS03-03A` and `WS03-03B`.

### 5.4 Intake Approval

Stage 0 returns:

- selected parent blueprint pass;
- proposed executable pass ID and title;
- decomposition rationale;
- parent-to-child scope map when applicable;
- dependencies and prerequisite state;
- expected evidence layers;
- expected non-goals and external boundaries;
- proposed Gate A planning file;
- blockers.

No Gate A design begins until the owner approves the intake or gives an
equivalent explicit pass instruction.

## 6. GATE A: Executable-Pass Design

Gate A converts approved intake into a frozen executable pass plan. It is
read-only with respect to production source, tests, requirement declarations,
testing records, provider settings, migrations, and runtime configuration
except for the canonical pass plan itself when the prompt authorizes that edit.

### 6.1 Gate A Responsibilities

Gate A must:

- confirm branch, baseline, clean status, and current accepted `develop`;
- reread the approved intake, this workflow, planning template, testing-record
  template, and applicable standards;
- reconcile the executable pass against current authority and current source;
- define stable requirements and requirement states;
- define exact technical contracts and invariants;
- define pass-owned source, configuration, documentation, provider, runtime,
  migration, operational, and evidence boundaries;
- decide the lowest reliable proof layer for each requirement;
- design requirement declarations and testing records where applicable;
- design executable and non-executable evidence;
- define exact Gate B editable files;
- identify all external, deferred, blocked, and covered-elsewhere facts;
- stop on conflicts, missing owner decisions, missing proof layers, or scope
  that cannot fit the approved executable pass.

### 6.2 Gate A Outputs

Gate A returns:

- the canonical executable pass plan;
- requirement reconciliation;
- exact implementation and evidence design;
- exact Gate B editable file set;
- validation plan;
- explicit non-goals and external evidence boundaries;
- blockers.

The plan, requirements, correction/design decisions, evidence design, and Gate
B file set become frozen only after human approval.

## 7. GATE B: Implementation And Trusted Evidence

Gate B implements exactly the human-approved Gate A design. It must not
redesign the pass while implementing it.

### 7.1 Required Order

Use this order:

```text
approved source/config/artifact implementation
-> approved supporting infrastructure changes
-> requirement metadata
-> TESTING_RECORD
-> trusted executable/non-executable evidence
-> focused validation
-> checker and generated traceability
-> STOP
```

Skip any item that Gate A explicitly marked not applicable.

### 7.2 Gate B Rules

Gate B must:

- edit only the approved Gate B file set;
- preserve pass boundaries and prerequisite contracts;
- use `TESTING-RECORD-TEMPLATE.md` for any testing record;
- derive tests from authority and the frozen plan, not from current code shape
  alone;
- verify meaningful persisted effects, rejected side effects, concurrency,
  time, provider, browser, migration, or recovery behavior where the frozen
  plan requires it;
- run materially required validation and report commands not run;
- stop and return to Gate A if correct completion needs a new requirement,
  new proof layer, broader file set, provider mutation, migration, owner
  decision, or broader scope.

Gate B ends with a validated local change set. It does not commit, push, create
a PR, or begin Gate C.

## 8. GATE C: Independent Semantic Review

Gate C is a new independent read-only review of the complete pass state.

Gate C must inspect:

- authority and approved intake;
- frozen plan;
- requirement declaration;
- `TESTING_RECORD.md`;
- implementation and artifacts;
- executable and non-executable evidence;
- generated traceability;
- validation results;
- external and later-pass gaps;
- the complete local change set and secret/confidentiality safety.

Gate C must not edit files, stage files, commit, push, or create a PR.

Gate C has exactly two outcomes:

- approved for Git finalization;
- corrections required.

If a correction changes repository content, the corrected final pass must
receive a new full independent Gate C review of the complete corrected pass
before Gate D.

## 9. GATE D: Git And PR Finalization

Gate D is mechanical and runs only after Gate C approval.

Gate D must:

- verify current branch, baseline, clean index, and exact approved change set;
- read `PASS-PR-DESCRIPTION-TEMPLATE.md`;
- inspect the diff for scope and sensitive material;
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

## 10. Register Updates

After an executable pass is accepted and merged, update
`PASS-EXECUTION-REGISTER.md` in a separate documentation change or in the
approved pass scope when explicitly authorized.

The register must distinguish:

- original parent-level blueprint passes;
- accepted executable child passes;
- parent passes that were decomposed;
- parent passes not yet selected;
- source-owned closeout documents;
- external/provider/runtime evidence still required.

Updating the register does not select the next pass.

## 11. Stop Conditions

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
- sensitive material would enter Git or a PR.

## 12. Completion Meaning

An executable pass is complete when its approved Gate D PR has been merged and
current accepted `develop` contains the pass output. That does not necessarily
mean the broader audit controls are closed. Controls close only through the
final evidence and reassessment process defined by the remediation plan and
master blueprint.
