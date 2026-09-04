# Production-Readiness Pass Recheck Workflow

This document defines the reusable process for revalidating a Pickup Lane
production-readiness pass that is already accepted into `develop`, or historical
implementation that predates the current workflow and is being formally
revalidated. It is process guidance only. It does not define product behavior
and does not override the authority order in
`docs/production-readiness/00-READ-ME-FIRST.md`.

Use `docs/production-readiness/planning/workflows/PASS-IMPLEMENTATION-WORKFLOW.md`
for first-time executable pass implementation and for correction rounds on the
same unmerged first-time pass. A normal recheck does not need Stage 0. When
recheck discovers that an accepted parent/child decomposition is materially
wrong, route that structural problem to Stage 0 or program
structural correction outside this recheck. Stop only for a real unresolved
blocker or owner decision required by durable authority. Do not silently
restructure pass families during recheck planning.

## 1. Purpose And Applicability

Use this workflow when rechecking a pass already accepted into `develop`, or
historical implementation that predates the current workflow and is being
formally revalidated against current repository truth, especially when its
implementation, test coverage, ownership, or surrounding contracts have changed.

Distinguish three kinds of work:

- First-time implementation creates an executable change from the corrected
  master and current accepted `develop`.
- Pass recheck or revalidation verifies whether an already accepted pass or
  historical implementation still agrees with authority, current repository
  behavior, current ownership, and current evidence standards.
- Testing or evidence reconstruction creates current, reliable proof when older
  tests or evidence are stale or inadequate.

The objective is not merely to prove that current code passes tests. The
objective is to establish that current repository truth is production-grade,
matches authoritative requirements, has honest ownership, and has adequate
evidence or explicit remaining gaps.

This workflow applies to already accepted work or historical implementation
being formally revalidated. It does not apply merely because source code has
been written locally. It preserves independent, evidence-seeking review depth,
but it
does not select future passes, decompose new parent passes, or repair unmerged
first-time implementation branches.

## 2. Core Authority Principle

Every recheck follows this reasoning order:

```text
CORRECTED MASTER BLUEPRINT
-> CURRENT REPOSITORY TRUTH
-> CURRENT PLAN, WHEN ONE IS USEFUL
-> IMPLEMENTATION
-> REQUIREMENTS / RISKS / EVIDENCE
```

The corrected master and applicable product authority define what must be true.
A pass plan is verified against them before it is used. Production code does not
define its own requirements, and tests do not define production behavior. A
historical implementation does not become authority merely because it was
merged.

The current accepted `develop` branch is the repository source of truth for
current implementation state. Historical branches, old prompts, past PR
descriptions, and other permitted historical implementation artifacts are
provenance unless a current authoritative source explicitly adopts them.

## 3. Original Implementation As Provenance

Every recheck reconstructs the original pass implementation to answer what
happened, not what should be true.

Identify, where available:

- original pass PR;
- original branch;
- original commit or commits;
- exact changed-file list;
- production, configuration, documentation, governance, and evidence files
  changed;
- original scope actually implemented;
- required areas the original change set did not touch.

Historical implementation evidence helps explain provenance, omissions, and
later evolution. It never overrides higher authority.

PR title, description, summary, and validation claims may help locate and
understand the original pass. They are provenance. When available, inspect the
actual original commit diff and changed-file set before concluding what the
original pass implemented. The diff establishes what changed, not what should
be true.

### Existing Tests

Evaluate existing tests by current usefulness, correctness, isolation, and the
behavior they prove. A directory label, including `legacy/`, neither validates
nor disqualifies a test. Stale tests may be corrected or removed only when the
current task owns that work.

## 4. Obligation-Oriented Provenance Review

For material obligations under review, answer the applicable questions:

```text
What does authority require?
Was it represented in the original pass plan?
Was it implemented by the original pass?
What exact artifact/source implemented it?
Was it materially changed after that pass?
What owns it today?
What does current develop do?
Is the current state correct?
What proof exists?
What remains unproven?
Did the original or current implementation introduce material behavior,
restrictions, defaults, configuration, ownership, or artifacts that authority
did not require or justify?
```

Useful provenance outcomes include:

- originally implemented and unchanged;
- originally implemented and later legitimately evolved;
- originally implemented and later weakened or regressed;
- not originally implemented but implemented later;
- still missing today;
- moved or superseded by another accepted owner;
- external evidence still required.

## 5. Negative-Space Audit

A recheck must actively search for absent obligations, not only
inspect files that already exist.

Ask:

- What authoritative requirement has no implementation?
- What requirement was omitted from the original plan?
- What planned requirement was never implemented?
- What required artifact does not exist?
- What required configuration, documentation, or governance update is missing?
- What required behavior has no current owner?
- What pass handoff names a future owner that never actually accepted the
  obligation?

The audit must be able to discover an omission even when no suspicious file is
available to inspect.

## 6. Reverse-Direction Scope Audit

Also audit implementation back toward authority:

```text
AUTHORITY -> IMPLEMENTATION
What required behavior is missing?

IMPLEMENTATION -> AUTHORITY
What implemented behavior lacks authoritative justification?
```

Apply this to the original implementation and, where material, current
repository behavior. Do not treat harmless implementation detail as
unauthorized scope. Focus on material behavior, restrictions, defaults,
configuration, ownership, and production-readiness consequences.

## 7. Current Repository Search

The original pass file list is not sufficient for current validation. After
reconstructing provenance, independently search current accepted source,
configuration, documentation, and evidence artifacts for every authoritative
concept.

This is required because behavior may have moved, been duplicated, been
replaced, been bypassed, been split across modules, or been modified by later
passes. Do not infer current ownership only from files originally touched.

## 8. Material Later-Evolution Review

For files or areas implementing a pass requirement, inspect material later
changes where necessary. Do not review every later commit indiscriminately.
Follow only history relevant to the authoritative requirement.

Classify later evolution as:

- preserved;
- legitimately strengthened;
- moved or refactored without behavioral change;
- superseded by an accepted later owner;
- weakened;
- bypassed;
- regressed.

Git history is provenance evidence, not behavioral authority. Do not claim
causation unless history proves it.

## 9. Ownership, Dependencies, And Handoffs

For each material obligation, determine whether it is:

- owned by the rechecked pass;
- inherited from a prerequisite pass;
- prepared by this pass but completed later;
- fully owned by a later pass;
- dependent on external, provider, or runtime evidence.

Detect ownership gaps, where a pass defers an obligation but the receiving pass
never actually preserves it, and ownership overlap, where multiple passes claim
completion without a clear relationship. A written deferral is not enough by
itself; the receiving owner must preserve the obligation in the corrected
master or current accepted implementation scope.

Dependencies must be checked as real contracts. For every prerequisite, state
what this pass relies on, whether that contract still exists, whether current
implementation honors it, and whether the rechecked pass duplicates or
contradicts it. Also identify downstream contracts this pass establishes for
later passes.

## 10. Bypass And Single-Source-Of-Truth Audit

For every pass-owned mechanism, inspect whether another path can avoid or
contradict it. Examples include duplicate configuration parsing, direct
environment access outside the authoritative settings owner, fallback paths,
alternate construction paths, old compatibility mechanisms, import-time
behavior, legacy-but-reachable routes or helpers, duplicated validation,
provider clients sourcing configuration differently, and secondary mutation
paths bypassing central safeguards.

A requirement is not correctly implemented merely because one happy path
enforces it. Where the architecture requires a single authoritative owner,
verify that competing owners do not remain reachable.

When an accepted implementation replaces an older mechanism, verify whether the
older mechanism is removed, unreachable, intentionally retained, or still able
to bypass the new contract.

## 11. Tracked Artifact Consistency

Inspect artifacts actually owned by the pass or necessary to verify its
contract. Depending on scope, this may include application source,
configuration, example environment files, deployment configuration, README or
deployment documentation, governance registers, schemas, migrations, workflows,
frontend-public configuration, backend-private configuration, and
repository-owned evidence.

Do not expand pass scope merely because an adjacent artifact exists.

### Pass Plan Scope Rule

A pass plan must remain within the material scope of that pass.

A pass plan may contain artifacts, requirements, dependencies, integrations,
evidence, constraints, and ownership boundaries only when they materially define,
implement, govern, constrain, or prove that pass.

Do not include unrelated repository housekeeping in a pass plan merely because
it may be completed on the same branch or included in the same PR. Examples of
unrelated material that must remain outside a feature or pass plan include
global workflow maintenance, program-context or onboarding documentation,
unrelated documentation cleanup, branch or PR housekeeping, and unrelated
process changes.

## 12. Repository, External Evidence, And Fact Classification

Every conclusion must distinguish:

```text
PROVEN FROM REPOSITORY
PROVEN FROM ACCEPTED EXTERNAL EVIDENCE
EXTERNAL EVIDENCE STILL REQUIRED
LATER-PASS RESPONSIBILITY
UNKNOWN
```

Do not claim deployed, provider, runtime, dashboard, account, secret-store,
network, DNS, TLS, monitoring, backup, or branch-protection facts from
repository source alone. Unknown external facts remain unknown until accepted
evidence exists.

Important conclusions should be identifiable as one of:

- authoritative fact;
- repository fact;
- historical/provenance fact;
- accepted external fact;
- inference;
- unknown.

Label inferences and support them. Do not silently convert unknowns into
assumptions.

## 13. Recheck Preflight

Before editing:

1. verify the current branch, accepted baseline, worktree, staged state, and
   current instruction;
2. read the corrected master and inspect current repository truth;
3. read any current plan and relevant standards that materially apply;
4. identify ownership, prerequisites, later responsibility, and external or
   provider evidence boundaries;
5. confirm the requested scope, validation, publication boundary, and any action
   requiring approval.

A historical SHA, template, testing record, or requirement declaration is not a
mandatory preflight input. If the instruction conflicts with the corrected
master, current repository truth, or safe Git/provider operation, stop and
report the conflict.

## 14. Recheck Workflow

The familiar Gate labels may be used to keep responsibilities clear, but they do
not create mandatory orchestration.

### Pass Initialization

For a recheck that will edit files:

1. fetch remote metadata safely;
2. verify the worktree and index are clean or explicitly understood;
3. switch to local `develop`;
4. fast-forward only from `origin/develop`;
5. verify local and remote `develop` agree;
6. record the accepted baseline;
7. create or switch to the owner-approved working branch;
8. do not push merely for branch creation.

Unexpected local work or divergence causes a stop, not automatic cleanup,
rebase, reset, restore, stash, or deletion.

### Gate A - Reconciliation And Planning When Needed

Reconstruct what the accepted pass originally changed, then assess its current
state against the corrected master and current repository truth. Use the
provenance, negative-space, reverse-direction, current-search, later-evolution,
ownership, bypass, artifact, and fact-classification methods in sections 3-12.

Write or update a concise plan only when the recheck is complex enough to need
one. A useful plan records:

- actual remaining defects or unproven risks;
- intended corrections and non-goals;
- important behavior, invariants, ownership, and compatibility;
- affected source, tests, schema, configuration, documentation, or provider
  boundaries;
- realistic proof layers and validation;
- external facts and later obligations that remain open.

Do not create a plan, intake, SHA, requirement declaration, testing record, or
mapping artifact merely because an older workflow expected it. Historical plans
remain provenance and may not resurrect scope rejected by the corrected master.

When a plan is used, review it before implementation and correct material
problems. Route a wrong executable boundary to Stage 0 or program correction and
an unresolved product, policy, security, provider, or operational choice to the
owner. There is no fixed review or correction count.

### Gate B - Correction And Risk-Based Evidence

Implement only the selected correction. Do not change production behavior merely
to satisfy a stale test, and do not silently expand the recheck into unrelated
cleanup.

Develop corrections and proof together:

```text
CURRENT DEFECT OR RISK
-> CORRECTION
-> FOCUSED TEST OR APPROPRIATE EVIDENCE
-> AFFECTED COMPATIBILITY VALIDATION
```

Validation depth follows actual risk and blast radius. Use real PostgreSQL,
independent sessions, controlled time, provider boundaries, authorization
matrices, persisted effects, rejected side effects, rollback, idempotency,
browser checks, migration checks, or broader regression where they are
materially appropriate.

Existing tests are judged by usefulness and correctness regardless of directory
or old metadata. Requirement JSON, pytest requirement markers, trusted roots,
checker/compliance commands, generated traceability, and
`TESTING_RECORD.md` are not required.

Before reporting completion, inspect the complete diff, confirm every changed
file belongs to the correction, and state the commands actually run, results,
and remaining material gaps. Gate B does not stage, commit, push, create a PR,
or perform independent review.

### Gate C - Independent Final Review

Gate C is an independent, read-only semantic review of the complete corrected
recheck change set. It examines the corrected-master obligation, repository
truth, relevant provenance, any current plan, all changed files, affected
surrounding code, and actual validation evidence.

Review both directions:

```text
CURRENT REQUIREMENT / RISK -> IMPLEMENTATION AND PROOF
CHANGED BEHAVIOR / FILE -> JUSTIFIED RECHECK SCOPE
```

Depending on the change, deliberately inspect applicable identity, type,
boundary, state, ordering, timestamp, database, concurrency, retry, rollback,
authorization, provider, logging, privacy, serialization, historical-state,
negative-path, and sibling-domain risks. Check that evidence claims do not
exceed what was proved. Green tests alone are not semantic approval.

When a defect pattern is found, inspect equivalent paths in the relevant
boundary and report all reasonably discoverable material findings together.
Gate C remains read-only and does not self-fix.

Gate C returns approved, corrections required, or blocked. A correction is
separate work, receives risk-appropriate validation, and then receives a new
complete independent review. Documentation-only corrections do not trigger
unrelated application suites. There is no fixed automatic review/correction
cycle, and no automatic transition to publication.

Gate C does not automatically rerun current successful suites. Run only the
smallest focused reproduction needed for a concrete semantic concern.

### Gate D - Git And PR Finalization

After independent approval and an owner instruction to publish:

- fetch remote metadata and verify branch, HEAD, accepted baseline, merge-base,
  worktree, staged state, and intended changed-file set;
- stop for reconciliation if `origin/develop` advanced materially;
- inspect the final diff and scan for secrets or confidential material;
- stage only approved files and inspect the staged diff;
- commit using the intended structure;
- push normally without force;
- create or update exactly the intended PR;
- verify base, head, commit count, changed files, title, body, and sensitive-data
  safety;
- leave the PR open and unmerged.

Use the normal PR headings `Summary`, `Changes`, and `Validation`. A reusable
PR template is optional guidance, not required infrastructure.

Do not amend, squash, rebase, reset, cherry-pick, rewrite history, force-push,
merge, or enable auto-merge unless the owner explicitly authorizes the
particular action. PR merge remains manual.

### Post-Merge Recheck Completion

After the user merges the recheck PR:

1. verify the intended PR merged;
2. fetch remote metadata;
3. fast-forward local `develop` to `origin/develop`;
4. verify local and remote `develop` agree;
5. update factual execution state when necessary.

Future work is selected from the corrected master, current repository truth,
real prerequisites, deferred-trigger state, and owner direction. Recheck does
not invent new parent/child decomposition or automatic progression.

## 15. Additional Approval Boundaries

Do not create lanes or risk scores. Pause for an additional approval only when a
concrete blocker requires it, such as:

- an unresolved owner or policy decision;
- real provider-account mutation;
- destructive migration or real-data transformation;
- irreversible operational action;
- external evidence that must be gathered before correction;
- another specific safety issue that cannot fit normal planning and review.

Address only the discovered blocker; do not create speculative process because a
recheck sounds high risk.

## 16. Plan Stability

When a current plan is used, implement the reviewed design. Return to planning
when repository truth requires a material change in behavior, proof strategy, or
scope. Historical SHAs are optional integrity aids, not mandatory workflow
artifacts.

After independent approval, do not make semantic changes during Git
finalization. Do not weaken requirements to make evidence pass, change
production merely to satisfy a test, or reopen planning for cosmetic
preferences.

## 17. Safe Efficiency Rules

Efficiency comes from targeted reading and evidence, not skipped reasoning.

### Targeted Authority Reading

Read the corrected-master requirement, current plan when one exists, relevant
implementation, original implementation diff when useful, material
prerequisites, downstream contracts, and current evidence. Search large
historical records by relevant concept rather than rereading them without
purpose.

### Exception-Oriented Reporting

Keep the analysis comprehensive but emphasize material findings, corrections,
unusual ownership or proof decisions, remaining gaps, and blockers. Do not
create a permanent reconciliation matrix when concise reporting is sufficient.

### Pass-Family Research Reuse

Related work may reuse accepted common authority, history, and repository
reconnaissance. Each recheck still evaluates its own current behavior, risks,
evidence, scope, and remaining gaps.

## 18. Test And Evidence Principles

Use the current testing documents for detailed mechanics. Important principles
include:

- requirement-driven rather than implementation-driven tests;
- behavior and invariant testing over implementation shape;
- safeguard first, test second;
- lowest reliable owning proof layer;
- real PostgreSQL for PostgreSQL-specific behavior;
- independent sessions or connections for genuine races;
- controlled time for exact time boundaries;
- external-boundary mocking rather than business-rule mocking;
- no uncontrolled live provider calls in ordinary tests;
- provider-contract proof separated from ordinary tests;
- synthetic data only;
- successful mutation proves intended persisted effects;
- rejected mutation proves prohibited side effects;
- idempotency proves no duplicated persisted or external effects;
- explicit remaining gaps;
- passing tests alone are never sufficient evidence of production readiness.

## 19. Security And Confidentiality

Use `docs/production-readiness/00-READ-ME-FIRST.md` as the global
sensitive-information policy. If sensitive material is discovered during recheck
work, report location and category only, not the value.

## 20. Review And Stop Discipline

Keep planning, editing, independent review, and Git publication responsibilities
clear. Stop at real blockers, unsafe repository state, missing owner decisions,
unapproved provider or destructive actions, sensitive-data risk, or the manual
PR-merge boundary.

This prevents mixed review and implementation, accidental scope expansion,
production changes driven by stale tests, and ambiguous workflow state without
turning the recheck into automatic multi-gate orchestration.
