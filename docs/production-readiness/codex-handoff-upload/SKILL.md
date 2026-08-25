---
name: pickup-lane-production-readiness
description: Orchestrate Pickup Lane production-readiness work from Stage 0 through Gate D, including independent Gate A and Gate C review cycles, automatic correction routing, PR publication, and post-merge progression through child and parent passes. Use when the user asks to start, run, continue, or resume Pickup Lane production-readiness work.
---

# Pickup Lane Production-Readiness Coordinator

## Role

The active main Codex session is the production-readiness coordinator and owns
all mutable workflow work.

Durable repository documents define the engineering process. This Skill defines
how the main Codex session operates that process automatically across stages,
gates, independent review cycles, publication, and post-merge progression.

The main Codex session does not replace the durable workflows and must not
perform the independent reviews itself. Only independent review is delegated.

## Durable Entry Points

At every start, resume, and material transition, begin with:

- `docs/production-readiness/00-READ-ME-FIRST.md`
- `docs/production-readiness/01-PROGRAM-CONTEXT.md`
- `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md`

Then use exactly one applicable workflow:

- first-time implementation:
  `docs/production-readiness/planning/workflows/PASS-IMPLEMENTATION-WORKFLOW.md`
- accepted/historical recheck:
  `docs/production-readiness/planning/workflows/PASS-RECHECK-WORKFLOW.md`

Follow the templates, authority, engineering/testing standards, pass artifacts,
source, evidence, decisions, governance, and prerequisite records routed by
those documents.

## Execution Architecture

The main Codex session directly owns:

- workflow coordination;
- startup and resume reconstruction;
- post-merge progression;
- Stage 0 and Stage 0 corrections;
- Gate A plan creation and Gate A plan corrections;
- Gate B implementation, debugging, validation, and post-Gate-C corrections;
- review-attempt counters and correction-round counters;
- deferred-follow-up tracking;
- Gate D staging, commit, push, PR creation/update, and PR verification;
- final workflow-state reporting.

Do not delegate mutable workflow work to custom worker agents. The main Codex
session retains the workflow state throughout the pass and performs corrections
and routing after review findings return.

Use exactly one project-scoped production-readiness custom subagent
configuration:

- `production_readiness_reviewer`
  - read-only;
  - supports `review_type = gate_a` and `review_type = gate_c`;
  - performs exactly one independent review attempt per invocation;
  - returns all material findings together;
  - never edits, fixes, stages, commits, pushes, publishes, merges, or advances
    workflow state;
  - never spawns other agents;
  - never invokes this Skill recursively.

If the required reviewer configuration is missing, cannot be loaded, cannot use
a read-only sandbox, or cannot honor its review boundary, stop and report the
configuration problem. Do not substitute the main Codex session or a generic
agent for independent review.

## Automation Authority

A user instruction to run, start, continue, or resume production-readiness work
authorizes the main Codex session to operate the selected production-readiness
workflow through Stage 0, Gate A, Gate B, Gate C, and Gate D without routine
human approval between those stages.

That authorization includes, when the durable workflow reaches Gate D:

- staging the approved pass files;
- committing;
- pushing the pass branch;
- creating or updating the intended PR;
- verifying the PR.

It does **not** authorize merging the PR. PR merge remains manual.

Do not stop merely to ask the user to approve:

- a successful Stage 0 intake/decomposition;
- a Gate A plan that passed independent Gate A review;
- progression from Gate B to Gate C;
- progression from clean Gate C to Gate D;
- ordinary in-scope Gate B implementation/debugging.

Stop only when a durable blocker, review-limit stop, unsafe state, unresolved
decision, or manual PR merge boundary requires it.

## Main Codex Must Not

The main Codex session must not:

- invent product, security, policy, operational, provider, or ownership
  decisions that authority does not resolve;
- perform independent Gate A or Gate C review itself;
- let a reviewing agent fix its own findings;
- merge a PR;
- silently repair dirty/divergent Git state with reset, rebase, stash, force,
  history rewriting, or destructive cleanup;
- silently change a frozen intake or frozen Gate A plan;
- hide a Stage 0/Gate A routing problem inside Gate B;
- continue after a hard review-limit stop without new owner direction;
- overclaim provider/runtime/external facts that are not actually proven.

## Start And Resume

### Start A Requested Pass

When the user explicitly identifies a parent pass, executable child, or recheck
target:

1. Read the durable entry points.
2. Inspect the execution register and relevant pass artifacts.
3. Determine first-time implementation versus recheck.
4. Verify the working branch and accepted baseline.
5. Reconstruct whether Stage 0 is required or whether an already accepted intake
   authorizes the requested child to begin at Gate A.
6. Begin the correct state automatically.

For first-time implementation:

- if the parent has no accepted current intake/decomposition, begin Stage 0;
- if the selected executable child is already defined by the current accepted
  intake, begin Gate A;
- do not recreate Stage 0 merely because a later approved child is starting.

For recheck, begin at recheck Gate A unless the durable recheck workflow requires
a structural stop outside normal recheck.

### Branch Naming

Use a pass-specific branch name already supplied by current authority or the
user when one exists.

When automatic progression selects a new first-time executable pass and no
different branch name is already mandated, use:

`pr/<EXECUTABLE-PASS-ID>`

For a recheck with no different mandated branch name, use:

`pr/<PASS-ID>-recheck`

Before creating or reusing a branch, verify it does not conflict with unrelated
local/remote state. Stop rather than overwrite or repurpose an ambiguous branch.

### Resume

On resume:

1. Reread the durable entry points.
2. Read `docs/local/CURRENT-HANDOFF.md` if present.
3. Verify every material handoff claim against Git, tracked authority, current
   pass artifacts, frozen SHAs, validation state, PR state when applicable, and
   current `origin/develop`.
4. Reconstruct the true workflow state.
5. Continue from that state automatically unless a real stop condition applies.

Chat history is never authoritative workflow state.

## Local State

Use ignored `docs/local/CURRENT-HANDOFF.md` as a resumable state checkpoint, not
as authority.

Track only what materially helps resumption:

- parent pass ID;
- current executable pass ID;
- workflow type;
- accepted baseline SHA;
- working branch;
- intake path/SHA when applicable;
- current canonical-plan path/SHA;
- mandatory deferred follow-ups, including owner/pass, preserved obligations,
  trigger, prerequisites/downstream consumers, latest completion boundary, and
  current trigger state;
- current stage/gate;
- Gate A review attempt and plan-correction round;
- prior Gate A findings and routing;
- Gate C review attempt and correction round;
- prior Gate C findings and routing;
- latest Gate B validation state;
- current PR identity/state when published;
- current blocker, if any;
- exact next action.

Do not maintain Gate B retry counters. Gate B is implementation/validation, not
a bounded independent-review loop.

Never store secrets, private provider values, personal/payment data, raw
sensitive logs, or other prohibited material in the handoff.

## Reviewer Assignment Contract

Every independent review invocation uses the reusable
`production_readiness_reviewer` configuration and performs exactly one review
attempt in a fresh reviewer thread/context.

The main Codex session must provide:

- `review_type`: exactly `gate_a` or `gate_c`;
- pass ID;
- parent pass when applicable;
- workflow type;
- branch;
- accepted baseline;
- review attempt number;
- frozen/accepted intake path and SHA when applicable;
- canonical plan path and SHA;
- prior findings and correction history when applicable;
- current validation state when applicable;
- exact review boundary;
- exact stop boundary.

The reviewer must reject unknown review types instead of guessing.

Use a brand-new reviewer thread/context for:

- Gate A Review 1;
- Gate A Review 2;
- Gate A Review 3;
- Gate C Review 1;
- Gate C Review 2;
- Gate C Review 3;
- any newly authorized post-limit independent review.

Never reuse a reviewer conversation between attempts.

After every reviewer return, the main Codex session verifies that the outcome
matches the assigned review type, review attempt, and repository state before
routing the next workflow action.

## Machine Outcome Dispatch

Machine tokens control transitions. Do not infer a transition from vague prose.

### Gate A Review Outcomes

Expected outcomes for `review_type = gate_a`:

- `gate_a_plan_approved`
- `gate_a_corrections_required`
- `blocked_before_review`

#### `gate_a_plan_approved`

1. Verify this was a fresh full-plan read-only review.
2. Verify the reviewer reviewed the exact current canonical-plan SHA.
3. Treat that exact reviewed SHA as the frozen Gate A plan.
4. Record the clean Gate A review.
5. Update the handoff.
6. Automatically begin Gate B.
7. Do not stop for routine human Gate A approval.

#### `gate_a_corrections_required`

Apply the Gate A review-cycle rules below.

#### `blocked_before_review`

Do not count semantic approval or a correction round. Stop on the reported
preflight blocker. Resume the same review attempt only after the blocker is
resolved and state is reverified.

### Gate C Review Outcomes

Expected outcomes for `review_type = gate_c`:

- `approved_for_git_finalization`
- `corrections_required`
- `blocked_before_review`

#### `approved_for_git_finalization`

1. Verify this was the required fresh full-pass read-only review.
2. Record Gate C approval for the exact current pass state.
3. Update the handoff.
4. Automatically begin Gate D.
5. Do not stop for separate publication authorization.

#### `corrections_required`

Apply the Gate C review-cycle rules below.

#### `blocked_before_review`

Do not count semantic approval or a correction round. Stop on the reported
preflight blocker. Resume the same Gate C attempt only after the blocker is
resolved and state is reverified.

### Gate D Outcomes

Gate D is performed by the main Codex session. Report exactly one of:

- `pr_ready_for_owner_merge`
- `baseline_advanced`
- `semantic_problem_found`
- `publication_blocked`

#### `pr_ready_for_owner_merge`

1. Verify the intended PR is open and unmerged.
2. Verify base/head/commit/changed-file state required by Gate D.
3. Update the handoff with PR identity and merge-pending state.
4. Stop for the user to merge the PR manually.

#### `baseline_advanced`

Stop. Report accepted baseline, current `origin/develop`, and required
reconciliation. Do not automatically rewrite history or publish stale-baseline
work.

#### `semantic_problem_found`

Gate D never fixes semantic content.

Route exactly as reported:

- in-scope implementation/evidence defect -> Gate B correction -> validation ->
  new full Gate C cycle;
- Gate A design/requirement/proof defect -> Gate A correction -> new Gate A
  review cycle -> Gate B -> Gate C;
- executable-boundary defect -> Stage 0;
- unresolved owner/external blocker -> stop.

#### `publication_blocked`

Stop and report the exact failed publication step and blocker.

Unknown tokens or tokens returned from the wrong review type/state are workflow
errors. Stop instead of guessing.

## Stage 0

Stage 0 runs at the parent-pass boundary and is performed directly by the main
Codex session.

It determines whether the parent:

- remains one executable pass; or
- is decomposed into ordered executable children; or
- separates executable-now work from a mandatory deferred follow-up whose
  external or final-infrastructure trigger is currently false.

It must preserve complete parent ownership, no-gap/no-overlap allocation,
dependencies, safe intermediate states, and evidence boundaries according to the
durable implementation workflow.

Every mandatory deferred follow-up must preserve:

- owner/pass;
- obligations;
- exact trigger;
- prerequisites and downstream consumers;
- latest completion boundary;
- execution-register visibility;
- an explicit statement that deferred status is not proof or control closure.

When Stage 0 produces a valid structure:

- record/freeze the exact intake artifact/SHA when applicable;
- select the first executable child, or the parent itself when kept whole;
- keep any mandatory deferred follow-up visible without treating it as proven or
  current-executable while its trigger is false;
- automatically proceed to Gate A.

There is no numeric Stage 0 retry limit. Stage 0 stops only for a real
structural, authority, prerequisite, evidence, owner-decision, or safety blocker.

## Gate A Planning And Independent Review

The main Codex session authors and corrects the Gate A plan. The main Codex
session never independently approves its own plan.

Every independent Gate A review attempt uses a fresh
`production_readiness_reviewer` thread with `review_type = gate_a` and reviews
the complete current plan.

The automatic Gate A cycle is exactly:

```text
Gate A plan
-> Review 1
   -> clean: freeze reviewed plan and begin Gate B
   -> material findings: Plan Correction 1
-> Review 2
   -> clean: freeze reviewed plan and begin Gate B
   -> material findings: Plan Correction 2
-> Review 3
   -> clean: freeze reviewed plan and begin Gate B
   -> material findings: HARD STOP
```

Rules:

- maximum 3 full independent reviews;
- maximum 2 automatic plan-correction rounds;
- no automatic Plan Correction Round 3;
- every review returns all material findings together;
- no cosmetic/style/preference-only correction churn;
- Review 2 and Review 3 verify prior findings while still reviewing the complete
  current plan;
- prior-review misses are identified according to the reviewer contract.

After Review 1 or Review 2 returns `gate_a_corrections_required`:

- if every material finding routes to `gate_a_correction`, the main Codex
  session applies the complete finding set in one Gate A correction step and
  then launches the next fresh full review;
- if any finding routes to Stage 0, exit the cycle and route to Stage 0;
- if any finding routes to a real blocker, stop;
- if routing is internally incompatible or ambiguous, stop rather than silently
  choosing a path.

If Review 3 still returns material findings, stop and report the complete
three-review history. A new owner instruction is required before any further
plan correction/review.

### Gate A Re-entry

Any route back to Gate A from Gate B, Gate C, or Gate D starts a **new Gate A
review cycle at Review 1** after the main Codex session corrects the plan.

The prior plan is no longer the current frozen design once a material Gate A
change is required.

If the new Gate A cycle becomes clean, automatically continue to Gate B. Do not
insert a routine human approval stop.

## Gate B

Gate B implements and validates the exact current frozen Gate A design. The main
Codex session owns ordinary in-scope implementation/debugging iterations needed
to reach the frozen completion and validation criteria.

Gate B has **no arbitrary numeric retry limit**.

Gate B continues while the work remains ordinary implementation or validation
inside the frozen design.

Route out of Gate B when:

- a new/changed requirement, engineering design, proof strategy, broader pass
  scope, or material plan revision is required -> Gate A;
- the executable-pass boundary/decomposition is wrong -> Stage 0;
- a genuine unresolved owner/product/security/policy/provider/runtime/safety
  decision or unavailable required evidence prevents completion -> stop.

When Gate B is valid and complete, automatically begin Gate C.

## Gate C Independent Review

Every Gate C attempt uses a fresh `production_readiness_reviewer` thread with
`review_type = gate_c` and reviews the complete current pass.

The automatic Gate C cycle is exactly:

```text
Review 1
-> clean: begin Gate D
-> material findings: Correction 1 + validation
-> Review 2
-> clean: begin Gate D
-> material findings: Correction 2 + validation
-> Review 3
-> clean: begin Gate D
-> material findings: HARD STOP
```

Rules:

- maximum 3 full independent reviews;
- maximum 2 automatic correction rounds;
- no automatic Correction Round 3;
- every review returns all material findings together;
- no cosmetic/style/preference-only correction churn;
- every content-changing correction receives required validation and then a new
  full independent Gate C review;
- Review 2 and Review 3 verify prior findings while independently reviewing the
  complete corrected pass;
- prior-review misses are identified according to the reviewer contract.

After Review 1 or Review 2 returns `corrections_required`:

- if every material finding routes to `gate_b_correction`, the main Codex
  session applies the complete finding set in one Gate B correction step,
  validates the corrected state, and then launches the next fresh full Gate C
  review;
- if any finding routes to Gate A, exit the Gate C cycle and run the Gate A
  re-entry path;
- if any finding routes to Stage 0, exit the cycle and route to Stage 0;
- if any finding is a real blocker, stop;
- if routing is internally incompatible or ambiguous, stop.

If Review 3 still returns material findings, stop and report the complete
three-review history. A new owner instruction is required before any further
correction/review.

## Gate D

A clean Gate C automatically authorizes Gate D for the current automated pass
run.

The main Codex session performs Gate D immediately after
`approved_for_git_finalization`.

Gate D:

- verifies baseline, branch, frozen artifacts, Gate C-approved state, changed
  files, and sensitive-content safety;
- stages the approved pass files;
- inspects the staged diff;
- commits;
- pushes normally without force;
- creates or updates the intended PR;
- verifies the remote PR;
- leaves the PR open and unmerged.

Gate D does not make semantic corrections.

The user manually merges the PR.

## After Manual PR Merge

When the workflow is resumed after the user merges:

1. Verify the intended PR actually merged.
2. Fetch remote metadata.
3. Switch to local `develop`.
4. Fast-forward-only to `origin/develop`.
5. Verify local `develop == origin/develop`.
6. Record the new accepted baseline.
7. Verify the execution-register state that became true with the merge.
8. Determine parent/child/deferred progression from current accepted intake,
   execution register, master blueprint, remediation plan, prerequisites,
   deferred-trigger state, and current accepted source.

Then:

### Another Child Remains

If the current parent has another current executable child whose prerequisites
and execution trigger are now satisfied:

- select that next child according to the accepted child order/dependencies;
- create/switch to its pass branch from the new accepted `develop`;
- do **not** rerun Stage 0;
- begin a fresh Gate A for that child.

### Deferred Follow-Up Triggered

If a mandatory deferred follow-up's trigger is now true and durable authority
makes it the deterministic next required unit:

- select that deferred unit according to its recorded owner/pass, obligations,
  prerequisites, downstream consumers, and latest completion boundary;
- create/switch to its pass branch from the new accepted `develop`;
- begin a fresh Gate A for the deferred unit.

### Deferred Follow-Up Still Waiting

If a mandatory deferred follow-up exists but its trigger remains false:

- keep it open and visible in the intake, execution register, and handoff;
- do not count it as proof or control closure;
- continue only to downstream work whose prerequisites do not require its facts;
- stop if the next candidate work requires the deferred facts.

### Parent Complete

If all executable obligations and mandatory deferred obligations for the parent
are actually resolved:

1. Mark/reconstruct the parent as complete from accepted repository state.
2. Determine the next parent pass from the durable blueprint/program order and
   prerequisite state.
3. If exactly one next parent is determined by durable authority, create its
   branch from current accepted `develop` and begin Stage 0.
4. If durable authority leaves multiple equally valid next parents with no
   deterministic order, stop for owner selection instead of inventing priority.

Do not infer the next parent from alphabetical filenames or stale chat history.

## Recheck Flow

For a selected recheck:

```text
preflight
-> recheck Gate A planning
-> independent Gate A review cycle
-> Gate B
-> independent Gate C review cycle
-> Gate D
-> PR open/unmerged
-> manual merge
```

Normal recheck does not run Stage 0 unless a structural problem is discovered
that the durable workflow routes outside recheck.

## Hard Stops

Numeric review limits apply only to independent review loops:

### Gate A

- Review 1
- optional Correction 1
- Review 2
- optional Correction 2
- Review 3
- still material findings -> stop

### Gate C

- Review 1
- optional Correction 1
- Review 2
- optional Correction 2
- Review 3
- still material findings -> stop

There is no numeric retry limit for ordinary Gate B implementation/debugging.

Also stop for real durable blockers such as:

- unsafe or ambiguous Git state;
- authority conflict;
- missing required owner/product/security/policy/operational decision;
- unavailable required evidence/proof capability;
- unauthorized destructive/provider/runtime action;
- sensitive-data risk;
- irreconcilable scope/decomposition ambiguity;
- baseline drift at publication;
- missing/broken required reviewer configuration;
- unreconstructable resume state.

## Reporting

Do not make the user relay routine reviewer outputs.

The main Codex session should report only when:

- a hard review-limit stop is reached;
- a real blocker requires owner/external action;
- Gate D has produced an open PR ready for manual merge;
- post-merge progression cannot be determined safely.

At an owner stop, report:

- current parent/executable pass;
- current stage/gate;
- material blocker/findings;
- relevant Gate A or Gate C review history;
- exact routing;
- exact action required.

## Invariants

- Durable authority and current repository truth outrank remembered chat state.
- The main Codex session owns all mutable workflow work and state.
- Stage 0 determines parent/child executable structure and any mandatory
  deferred follow-up.
- Every executable child receives a fresh Gate A from current accepted
  `develop` after required prior children merge.
- Gate A plan review is fresh, independent, full-plan, and read-only.
- Gate B implements/validates; it has no arbitrary numeric retry cap.
- Gate C review is fresh, independent, whole-pass, and read-only.
- Gate A and Gate C each allow at most 3 reviews and 2 automatic correction
  rounds.
- Reviewers never fix their own findings.
- The same reviewer configuration is reused, but every review attempt gets a
  fresh thread/context.
- Clean Gate A automatically advances to Gate B.
- Clean Gate C automatically advances to Gate D.
- Gate D automatically creates/verifies the PR.
- PR merge remains manual.
- After merge, another child advances directly to fresh Gate A.
- After merge, a triggered mandatory deferred follow-up may advance to fresh
  Gate A when it is the deterministic next required unit.
- A deferred follow-up whose trigger remains false stays open and visible while
  unrelated downstream work may continue only if it does not require that
  follow-up's facts.
- Never mark a parent/control complete merely because the current executable
  child set is finished; every mandatory deferred obligation must be actually
  resolved or truthfully reallocated by durable authority.
- After all executable and mandatory deferred obligations complete, the next
  deterministically ordered parent begins at Stage 0.
