# Production-Readiness Pass Recheck Workflow

This document defines the reusable process for revalidating a Pickup Lane
production-readiness pass that is already accepted into `develop`, or historical
implementation that predates the current workflow and is being formally
revalidated. It is process guidance only. It does not define product behavior
and does not override the authority order in
`docs/production-readiness/00-READ-ME-FIRST.md`.

Use `docs/production-readiness/planning/workflows/PASS-IMPLEMENTATION-WORKFLOW.md`
for first-time executable pass implementation and for correction rounds on the
same unmerged first-time pass. Normal recheck does not run Stage 0. When
recheck discovers that an accepted parent/child decomposition is materially
wrong, route that structural problem to main-Codex-owned Stage 0 or program
structural correction outside this recheck. Stop only for a real unresolved
blocker or owner decision required by durable authority. Do not silently
restructure pass families inside recheck Gate A.

## 1. Purpose And Applicability

Use this workflow when rechecking a pass already accepted into `develop`, or
historical implementation that predates the current workflow and is being
formally revalidated against current repository truth, especially when the
trusted testing or evidence architecture has changed since the pass was first
implemented.

Distinguish three kinds of work:

- First-time implementation creates an approved executable pass from authority,
  approved intake when applicable, and current accepted `develop`.
- Pass recheck or revalidation verifies whether an already accepted pass or
  historical implementation still agrees with authority, current repository
  behavior, current ownership, and current evidence standards.
- Testing or evidence reconstruction creates fresh trusted proof under the
  accepted EN-01 architecture when old tests or evidence are no longer trusted.

The objective is not merely to prove that current code passes tests. The
objective is to establish that current repository truth is production-grade,
matches authoritative requirements, has honest ownership, and has adequate
evidence or explicit remaining gaps.

This workflow applies to already accepted work or historical implementation
being formally revalidated. It does not apply merely because source code has
been written locally. It preserves the existing zero-trust recheck depth, but it
does not select future passes, decompose new parent passes, or repair unmerged
first-time implementation branches.

## 2. Core Authority Principle

Every recheck follows this reasoning order:

```text
AUTHORITATIVE PRODUCT / PRODUCTION-READINESS SOURCES
-> APPROVED PASS PLAN
-> IMPLEMENTATION
-> REQUIREMENTS / RISKS / EVIDENCE
```

Authoritative sources define what must be true. A pass plan is verified against
authority before it is used. Production code does not define its own
requirements, and tests do not define production behavior. A historical
implementation does not become authority merely because it was merged.

The current accepted `develop` branch is the repository source of truth for
current implementation state. Historical branches, old prompts, past PR
descriptions, and other permitted historical implementation artifacts are
provenance unless a current authoritative source explicitly adopts them. The
excluded test tree defined below is never used for provenance or
production-readiness reasoning.

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

### Excluded Test Tree

For production-readiness work, `backend/tests/legacy/` is treated as
nonexistent.

Do not read, search, inspect, execute, inventory, count, cite, use for
provenance, include in original-PR changed-file summaries, use for requirement
discovery, use for scenario or assertion design, use for implementation
reasoning, use for evidence design, compare with current implementation, or use
to confirm current behavior.

Do not record files from this tree by path or changed-file presence for
provenance. Legitimate provenance outside the excluded tree remains allowed:
current authoritative documents, current accepted source/configuration and
governance files, production Git history outside the excluded tree, and fresh
trusted evidence created under EN-01 may still be used within the authority
rules above.

## 4. Requirement-By-Requirement Provenance Model

For every material authoritative obligation, Gate A zero-trust recheck must
answer:

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

A zero-trust recheck must actively search for absent obligations, not only
inspect files that already exist.

Ask:

- What authoritative requirement has no implementation?
- What requirement was omitted from the original plan?
- What planned requirement was never implemented?
- What required tracked artifact does not exist?
- What required configuration, documentation, or governance update is missing?
- What required behavior has no current owner?
- What pass handoff names a future owner that never actually accepted the
  obligation?

The audit must be able to discover an omission even when no suspicious file is
available to inspect.

## 6. Reverse-Direction Scope Audit

Gate A zero-trust recheck must also audit implementation back toward authority:

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
itself; the receiving owner must preserve the obligation in current authority or
accepted planning.

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
evidence, controls, and ownership boundaries only when they materially define,
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

## 13. Mandatory Gate Preflight

Before drafting, issuing, approving, correcting, or executing any gate instruction

1. reread this workflow;
2. verify current repository state, including branch, baseline, staged files,
   local changes, and current run instruction;
3. apply the instruction-adherence rule from
   `docs/production-readiness/00-READ-ME-FIRST.md` to the current approved
   instruction;
4. read the current or frozen pass plan for the gate;
5. identify and read all applicable repository templates and required
   engineering/testing standards for the gate;
6. verify material ownership across authority, current source, prerequisite
   passes, later-pass handoffs, and external/provider evidence boundaries;
7. self-review the gate instruction for scope, editable files, validation,
   stop boundary, security/confidentiality, and correction-routing clarity
   before issuing it.

A gate instruction is incomplete when an applicable repository template or
required standard was not reviewed before the instruction was drafted.

Explicit scope, editable files, paths, SHAs, validation requirements, gate
boundaries, and stop conditions from the current run instruction are
binding constraints. If the instruction cannot be followed exactly or conflicts
with authority, repository truth, or a frozen artifact, stop and report instead
of silently substituting another action.

## 14. Permanent Four-Gate Workflow

Each gate does exactly its assigned job and does not perform the next gate's
work itself. The main Codex session owns automatic transitions between
successfully completed gates. The four-gate model does not remove audit depth,
evidence design, semantic review, security review, or Git publication safeguards.

Before any gate reports completion, compare the actual work performed against
the binding current instruction. Correct any in-scope mismatch before handoff,
or report the mismatch and stop.

There is no Fast Lane, Full Lane, pre-pass risk score, or risk-classification
process. Additional gates are allowed only for concrete discovered blockers as
defined below.

### Pass Initialization

At the start of each pass recheck:

1. fetch remote metadata;
2. verify local safety;
3. fast-forward local `develop` to `origin/develop`;
4. record the exact accepted baseline;
5. create one remediation branch from that baseline;
6. use that branch for the whole pass;
7. do not push merely for branch creation.

Unexpected local work, divergence, or conflicting branch state causes a stop,
not automatic cleanup, rebase, reset, restore, stash, or deletion. If preserved
local work such as a stash is later restored or converted into commit-eligible
pass artifacts, recheck it for prohibited sensitive material under the
read-first document before continuing.

### Gate A - Reconciliation And Design

Gate A contains planning/reconciliation followed by a read-only review of the
complete current canonical plan before Gate B. Any plan correction is performed
by the main Codex session as separate Gate A correction work.

#### A1. Zero-Trust Recheck

Read-only after branch creation.

Reconcile:

```text
AUTHORITATIVE REQUIREMENTS
-> ORIGINAL PLAN
-> ORIGINAL IMPLEMENTATION / PR / ACTUAL DIFF
-> ORIGINAL OMISSIONS
-> IMPLEMENTATION-TO-AUTHORITY EXTRA SCOPE
-> MATERIAL LATER EVOLUTION
-> CURRENT FULL REPOSITORY STATE
-> NEGATIVE SPACE
-> BYPASS / SINGLE-OWNER STATE
-> DEPENDENCIES / CROSS-PASS HANDOFFS
-> TRACKED ARTIFACT STATE
-> REPOSITORY / EXTERNAL-EVIDENCE BOUNDARY
```

No plan edits, implementation edits, test design, tests, requirement JSON, or
`TESTING_RECORD.md` changes.

Classify findings precisely rather than forcing a binary result:

- production source correction required;
- tracked configuration correction required;
- governance or document artifact correction required;
- canonical plan reconciliation required;
- fresh trusted testing or evidence required;
- accepted external evidence required;
- later-pass work remains;
- no correction required.

If correct resolution requires a new product, policy, technical-policy,
security-policy, operational, or other owner decision that is not already
approved in authoritative records, stop. Report the unresolved question, why
existing authority does not resolve it, and which requirement is affected. Do
not invent policy, silently choose a value or behavior, or continue into later
gate work until the required decision exists.

#### A2. Finalize The Canonical Pass Plan

If A1 has no unresolved blocker, update only the canonical pass plan using the
approved audit, current authority, and
`docs/production-readiness/planning/templates/PASS-PLANNING-TEMPLATE.md`.

The plan must define:

- stable requirements;
- technical contracts;
- scope and non-goals;
- pass-owned outputs;
- handoffs;
- evidence categories;
- completion criteria.

The plan defines what must be true; it does not implement corrections. Do not
change production code, tracked configuration, governance artifacts,
requirement JSON, `TESTING_RECORD.md`, or tests in Gate A.

Gate A does not stage, commit, push, create a PR, or update a PR.

#### A3. Correction And Evidence Design

Using the reconciled plan, design:

- exact production or configuration corrections, if any;
- exact governance, document, or repository-owned operational artifacts, if
  any;
- exact testing-infrastructure compatibility corrections, if any;
- stable requirement IDs and declaration states;
- source controls, scopes, and required reasons for declarations;
- requirement-to-risk reasoning;
- meaningful scenarios, boundaries, and failure modes;
- safeguards;
- lowest reliable proof layer;
- executable versus non-executable evidence;
- covered-elsewhere evidence;
- external or later-pass gaps;
- implementation scope boundaries and changed-file justification rules.

When designing a `TESTING_RECORD.md`, use
`docs/production-readiness/planning/templates/TESTING-RECORD-TEMPLATE.md` and
keep the design consistent with its required structure and evidence-quality
rules.

Before designing evidence, read the accepted testing architecture and standards.
Testing standards define how proof is organized; they do not define product
behavior.

Design requirement-by-requirement:

```text
authoritative requirement
-> invariant
-> material risk
-> actor/state/action/input/time/dependency dimensions
-> equivalence classes / boundaries / failure modes
-> safeguard
-> lowest reliable proof layer
-> executable vs non-executable evidence
-> remaining external gap
```

Include deliberate negative cases, boundaries, failure transformations, and
concurrency, timing, provider, or database layers only where materially
required. Do not create blind Cartesian combinations. Historical tests remain
out of bounds.

For every requirement or meaningful requirement group, decide before Gate B:

- correct trusted owning test or evidence location;
- exact evidence artifact types needed;
- executable versus non-executable proof;
- whether PostgreSQL is required;
- whether external network or provider access is required;
- whether browser or Playwright evidence is required;
- whether migration or schema-history proof is required;
- whether genuine concurrency or race proof is required;
- whether controlled time is required;
- what repository-owned evidence is sufficient;
- what remains external or deliberately deferred.

#### Gate A Feasibility Check

Before Gate A may be approved, verify the proposed design against current
repository machinery. At minimum confirm:

- requirement IDs are accepted by the checker;
- declaration states, scopes, source controls, and reasons are
  schema-compatible;
- proposed trusted roots or subtrees are allowed by suite policy;
- proposed paths do not conflict with current files;
- required proof layers actually exist;
- PostgreSQL, provider/network, browser, migration, concurrency, and
  controlled-time needs are explicitly decided;
- the implementation scope and proof strategy are feasible;
- no hidden prerequisite or owner decision remains.

This is analysis and validation only. Do not create the proposed implementation
artifacts during Gate A.

#### Gate A Plan Completion

Gate A returns material findings, a requirement reconciliation matrix, the
updated canonical plan, exact correction design, exact evidence design,
implementation scope boundaries, changed-file justification rules, exact
validation strategy, and blockers.

When the main Codex session completes the corrected canonical plan, compute its
SHA-256 and report the exact plan path and SHA. Gate A review covers that exact
SHA. A clean review freezes that exact SHA for Gate B.
Do not embed a mutable SHA inside the canonical plan; the SHA belongs in Gate A
reports and run instructions.

Gate A freezes these as distinct artifacts:

- frozen canonical plan artifact;
- frozen requirements, correction design, evidence design, implementation scope
  boundaries, and changed-file justification rules;
- exact validation strategy.

The canonical plan, canonical-plan SHA, requirements, correction design,
evidence design, implementation scope boundaries, changed-file justification
rules, and validation strategy become frozen when a clean Gate A plan review
approves the exact current canonical-plan SHA.

#### Gate A Plan Review

Before Gate B, the complete current canonical plan must receive a read-only
review.

The review must inspect the complete Gate A state, including:

- the full Gate A report and complete canonical plan;
- canonical-plan SHA;
- authority alignment and numeric-value authority;
- original implementation provenance and current repository truth;
- negative-space, reverse-direction scope, bypass/single-owner, dependency, and
  handoff conclusions required by this recheck workflow;
- requirements and requirement ownership;
- technical contracts and invariants;
- correction design;
- evidence design and proof-layer choices;
- implementation scope boundaries and changed-file justification rules;
- exact validation strategy;
- completion criteria;
- external/later-pass gaps and blockers.

The review must be comprehensive and return all material findings together. Do
not drip-feed findings across rounds or require corrections for cosmetic
wording, stylistic preferences, harmless naming differences, formatting
preferences, or another reasonable design choice that still fully satisfies
authority and the executable-pass boundary. A correction-worthy finding must
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
- Stage 0/program structural correction when the accepted parent/child
  decomposition or executable-pass boundary is materially wrong;
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
that routes to Stage 0/program correction or a blocker/owner decision exits the
automatic plan-review cycle immediately and follows that routing instead.

When Review 2 or Review 3 discovers a material issue that was already present
and reasonably discoverable in the immediately preceding reviewed plan state,
and that issue was not introduced or newly exposed by the intervening
correction, identify it as a prior-review miss. The classification makes review
quality visible; it does not make the issue non-material.

When the main Codex session finishes the current Gate A plan draft or
correction, compute the canonical-plan SHA-256 and report the exact path and
SHA. Gate A review covers that exact current SHA. A clean review freezes that
exact reviewed SHA for Gate B. If plan content changes after the clean review,
the review is no longer current and the changed plan must receive a new full Gate
A review before it can govern Gate B.

`gate_a_plan_approved` freezes the exact reviewed canonical-plan SHA for the
current automated run. The main Codex session then advances automatically to
Gate B.

### Gate B - Frozen-Plan Implementation

Gate B implements exactly the frozen Gate A design that passed Gate A review. It
contains the former pass-owned correction and trusted test/evidence
implementation responsibilities.

Before editing, Gate B must verify branch, HEAD, accepted baseline, merge-base
with that baseline, frozen canonical-plan path and SHA, implementation scope
boundaries, changed-file justification rules, validation strategy, and
worktree/index state. Gate B must not edit the frozen canonical plan. Before
handoff, Gate B must reverify baseline and merge-base, frozen canonical-plan
SHA, that every actual changed file is justified by the frozen scope and
design, and nothing staged.

#### B1. Pass-Owned Corrections And Artifacts

As approved, this may include:

- production source;
- tracked configuration;
- governance or document artifacts;
- repository-owned operational artifacts;
- narrow testing-infrastructure compatibility corrections.

Do not modify production merely because testing is inconvenient. Do not add
unrelated refactors. If no implementation or artifact correction is approved,
explicitly skip that portion.

#### B2. Trusted Test And Evidence Implementation

As approved, create stable requirement declaration JSON, `TESTING_RECORD.md`,
fresh trusted executable tests, and legitimate non-executable repository
evidence under the accepted EN-01 architecture.

Use `docs/production-readiness/planning/templates/TESTING-RECORD-TEMPLATE.md`
for any created or reconciled `TESTING_RECORD.md`.

Tests are derived from authority and the approved pass plan, never from
historical tests.

#### Required Order

Use this implementation order:

```text
approved source/config/artifact corrections
-> approved supporting infrastructure corrections
-> requirement metadata
-> TESTING_RECORD
-> trusted executable/non-executable evidence
-> focused validation
-> checker and generated traceability
-> STOP
```

Implement the approved proof architecture rather than quietly redesigning it.
Do not change production code merely to make a test pass. If current production
contradicts the approved plan, stop and return to Gate A.

If Gate B needs another repository file for the same approved requirements,
engineering design, proof strategy, and pass scope, Gate B may modify it and
must justify it against the frozen design. If Gate B needs another requirement,
changed design, changed proof strategy, provider access, or a PostgreSQL,
browser, migration, concurrency, or controlled-time proof layer not already
approved by the frozen proof strategy, or broader pass scope, stop and return
to Gate A. If the executable-pass boundary itself is wrong, return to Stage 0. Gate B must not silently expand or
redesign the pass. Tests must not redefine behavior or cause requirements to be
weakened.

Validate focused tests, relevant prerequisite regressions, checker
file/domain/suite scopes as appropriate, generated traceability,
syntax/compile, environment/database/network/provider safety, and
`git diff --check`.

Gate B ends with an implementation and validation report. When Gate B is valid
and complete, the main Codex session advances automatically to Gate C. Gate B
itself does not commit, push, stage files, create a PR, update a PR, or perform
Gate C.

### Gate C - Independent Final Review

Gate C must be a new, independent, read-only run. It combines the former
evidence adequacy and whole-pass local review responsibilities without removing
either review obligation.

Gate C must verify and report branch, HEAD, accepted baseline, merge-base with
that baseline, frozen canonical-plan path and SHA, complete actual
changed-file set, file-by-file scope justification, staged-file state, current
run instruction, and authorized execution boundaries. Review inputs must
also include requirement declarations,
`TESTING_RECORD.md`, implemented evidence, and current validation. Use
`docs/production-readiness/planning/templates/TESTING-RECORD-TEMPLATE.md` when
reviewing testing-record compliance.

Gate C never modifies repository content. When Gate C finds a defect, it
returns `corrections required` and defines the exact authorized correction
scope. A separate scoped correction run performs only the approved changes.
After any correction that changes repository content, the corrected final pass
must receive a new full independent, semantic, read-only Gate C review of the
complete corrected pass before approval or Gate D. This full review is required
regardless of whether the correction was narrow evidence, testing-record,
requirement metadata, test, testing-infrastructure, approved
production/configuration, documentation-only, or another correction within the
already-frozen design. Gate C must not fix files during the review run,
silently transition from review into implementation, review an agent's own
unapproved correction in the same run, or grant final approval through a
narrowed post-correction review.

#### C1. Evidence Adequacy Review

Read-only review of the implemented proof. Evaluate whether the evidence
actually covers the approved risks and proves the intended safeguards. Do not
approve merely because commands are green.

Check for missing risks, weak assertions, tests passing for the wrong reason,
wrong proof layers, implementation-detail coupling, incorrect requirement
markers, over-tagging, under-tagging, static-test false confidence,
ambient-state or isolation defects, missing persisted-effect proof, missing
rejected-side-effect proof, missing idempotency, concurrency, or boundary proof
where applicable, dishonest `covered_elsewhere`, `TESTING_RECORD.md`
overclaims, unsupported adequacy claims, fake pytest used for documentary or
provider facts, generated traceability defects, and redundant evidence without
distinct risk value.

#### C2. Whole-Pass Consistency Review

Read-only review of the complete pass together:

```text
AUTHORITY
<-> CANONICAL PLAN
<-> IMPLEMENTATION / ARTIFACTS
<-> REQUIREMENT DECLARATIONS
<-> TESTING_RECORD
<-> EXECUTABLE / NON-EXECUTABLE EVIDENCE
<-> GENERATED TRACEABILITY
<-> EXTERNAL / LATER-PASS GAPS
```

Review all material issues in one pass. Do not drip-feed cosmetic findings.
Require correction only for issues affecting correctness, evidence
truthfulness, security, scope, maintainability, traceability, or production
readiness.

Review the current validation results from the final changed state, inspect the
complete local pass change set, review actual generated traceability, run
`git diff --check`, perform a secret/confidential-data review of the complete
local change set, verify the complete tracked pass state contains no prohibited
literal credentials or sensitive values under the read-first document, verify no
unexpected files are present, and verify repository contents remain unchanged by
the read-only review. Gate C approval confirms that the final pass state matches
both the frozen plan and the current run instruction's execution
boundaries. Gate C does not
automatically rerun already-current successful validation. Gate C may run only
the smallest relevant test or check when it has a concrete stated reason, and
the reason and exact rerun must be reported. Do not require unrelated
full-repository validation when the approved pass scope does not justify it.

Green commands alone are not sufficient for whole-pass approval. Gate C must
review semantic consistency and evidence adequacy, not merely test execution.

#### Post-Gate C Correction Routing

Gate C reports correction routing; it does not perform the correction.

The run that modifies files owns post-change validation. Gate C owns semantic
review.

When an approved correction changes an executable or shared artifact, including
production source, configuration, tests, requirement metadata, testing
infrastructure, or another executable/shared artifact, the correction run must
run affected targeted validation, run the full relevant regression, checker,
and traceability validation required for the corrected final pass state,
correct any in-scope failures before handing the work back, and report a fully
validated corrected repository state.

Documentation-only corrections do not automatically require unrelated
application test suites. They require only validation materially affected by the
documentation change.

After any correction run that changes repository content, the next semantic
review is always a new full, semantic, read-only Gate C review of the complete
corrected pass. There is no narrowed final Gate C approval path after a
correction.

Full Gate C review means the semantic review scope is the entire corrected
pass. It does not mean automatically rerunning every successful test suite.
Gate C must not automatically rerun already-current successful validation when
no relevant artifact changed after that validation. Gate C may run the smallest
relevant test or check only when there is a concrete reason, such as missing,
ambiguous, suspicious, or potentially misleading evidence, or a specific result
that needs reproduction.

A narrow evidence defect is limited to affected evidence files, such as a
missing test scenario, weak assertion, wrong marker, testing-record
overstatement, or narrow static-test defect. Gate C returns
`corrections required`, defines the affected evidence files and exact
correction scope, then stops. A separate scoped correction run modifies only
those files. If the correction changes executable or shared artifacts,
including tests, requirement metadata, testing infrastructure, or executable
evidence, the correction run must run affected targeted validation, run the full
relevant regression, checker, and traceability validation required for the
corrected final pass state, and correct in-scope failures before handoff. If
the correction is documentation-only, the correction run must run only
validation materially affected by the documentation change and must not
automatically run unrelated application suites. After validation, the corrected
final pass must receive a new full, semantic, read-only Gate C review of the
complete pass before approval or Gate D.

An implementation mistake inside the already-approved frozen design may use a
separate scoped correction run only when the authoritative contract, canonical
plan, requirement set, proof layer, implementation scope boundaries, and pass
scope remain unchanged. The correction run fixes only that approved mistake,
runs affected targeted validation, runs the full relevant regression, checker,
and traceability validation required for the corrected final pass state,
corrects any in-scope failures before handoff, and is followed by a new full,
semantic, read-only Gate C review of the complete corrected pass.

Return to Gate A when a finding requires a new requirement, changed
requirement, new owner decision, new proof layer, changed engineering design,
broader pass scope, or material plan revision. Return to Stage 0 when the
executable-pass boundary itself is wrong. No post-Gate C correction run may
make these changes under Gate C authorization.

Gate A plan-review findings follow the same ownership principle: correct plan
defects inside the existing executable boundary through a separate Gate A
correction by the main Codex session, route a materially wrong executable
boundary to Stage 0/program correction, and stop for owner direction when
existing authority cannot resolve the issue. Plan Review 3 never authorizes an
automatic Plan Correction Round 3.

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
   pass. If Review 3 still returns material corrections required, stop for owner
   direction. Do not perform an automatic Correction Round 3.

Every Gate C review in the cycle must review the complete current pass. The
review and correction counts are cumulative for that automatic cycle and do not
reset merely because work moves through a correction step. A finding that routes
to Gate A, Stage 0, an owner decision, or another approval boundary exits the
automatic correction cycle immediately and follows that routing instead.

Any owner-approved continuation after Review 3 must preserve the existing review
and correction history. It does not silently reset the completed automatic cycle
or retroactively authorize a third automatic correction round. Approval still
requires a genuinely clean full-pass review.

End with exactly one semantic outcome:

- approved for Git finalization;
- corrections required.

A clean `approved for Git finalization` result authorizes the main Codex session
to advance automatically to Gate D for the exact reviewed pass state.

When the outcome is `corrections required`, report the material finding, the
affected requirement or contract, the exact authorized correction scope, and the
durable route: separate scoped Gate B correction, return to Gate A, Stage
0/program structural correction, or blocked/owner stop.
After any scoped correction run that changes repository content, the next
semantic review is a new full Gate C review of the complete corrected pass. Gate
C itself leaves repository contents unchanged.

At review completion, confirm repository contents remain unchanged.

Do not commit or push during Gate C.

### Gate D - Git And PR Finalization

A clean Gate C review automatically authorizes Gate D for the current automated
recheck run. Gate D is mechanical.

Before staging, fetch remote metadata and verify branch, HEAD, accepted
baseline, merge-base with that baseline, frozen canonical-plan SHA, current
`origin/develop`, exact approved change set, no unexpected files, no staged
contamination, secret/confidential-data safety, and diff integrity. Run an
explicit final credential/secret scan, or equivalent repository-approved
verification, before staging or publication.

If `origin/develop` differs from the accepted baseline, stop, report the
divergence, do not automatically merge, rebase, reset, cherry-pick, or
force-push, and require explicit owner-approved reconciliation.

Before drafting, creating, updating, or reviewing a PR title or body, read and
follow
`docs/production-readiness/planning/templates/PASS-PR-DESCRIPTION-TEMPLATE.md`.

Then stage only approved files, inspect the exact staged diff, create one pass
commit unless the approved pass explicitly requires a different commit
structure, push the existing remediation branch normally, create or update
exactly the intended PR, review the remote changed-file list and PR
description, verify no unrelated or sensitive content, verify base/head/commit,
verify intended upstream tracking, verify local HEAD equals the pushed remote
branch HEAD, and verify no merge or auto-merge occurred.

Normal finalization must not amend, squash, rebase, reconstruct history through
cherry-pick, rewrite history, force-push, create an unintended second PR,
merge, or enable auto-merge. PR merge remains manual.

Commit messages and PR bodies must not expose secrets or credential values, raw
provider evidence, provider-private URLs, personal/private user data, payment
data, local filesystem paths or local usernames, internal conversation or chat
history, or temporary debugging information.

The user merges manually.

## 14.1 Post-Merge Recheck Completion

The recheck PR is merged manually by the user.

When the workflow resumes after merge:

1. verify the intended PR actually merged;
2. fetch remote metadata;
3. fast-forward local `develop` to `origin/develop`;
4. verify local `develop == origin/develop`;
5. record the new accepted baseline;
6. treat the rechecked executable pass as accepted in current repository truth;
7. return progression control to the main Codex session.

The main Codex session then determines the next first-time child/parent or
recheck work from the master blueprint, remediation plan, execution register,
accepted dependencies, and current repository truth. Recheck itself does not
invent a new parent/child decomposition.

## 15. Additional Intermediate Gates

Do not create lanes or risk scores.

An additional intermediate gate is allowed only when a concrete discovered
blocker cannot safely fit within the four standard gates. Examples include:

- unresolved owner or policy decision;
- real provider-account mutation;
- destructive migration or real-data transformation;
- irreversible operational action;
- required external evidence that must be gathered before implementation;
- another concrete issue requiring explicit approval before Gate B can
  continue.

The extra gate must address only the discovered blocker. Do not create
speculative process merely because a pass sounds high risk.

## 16. Freeze Rule

After a clean Gate A review, the canonical plan, canonical-plan SHA,
requirements, correction design, evidence design, implementation scope
boundaries, changed-file justification rules, and validation strategy are frozen
unless concrete contradictory evidence requires returning to Gate A. Any plan
content change returns to recheck Gate A, produces a new SHA, and requires a new
full Gate A plan review before Gate B can resume.

After Gate C approval, no semantic changes are permitted in Gate D.

Do not rewrite a plan because a test name is inconvenient, change production
merely to satisfy a test, weaken a requirement to make evidence pass, redesign
scenarios while implementing them, reopen approved gates for cosmetic
preferences, or allow scope creep between gates.

## 17. Safe Efficiency Rules

Efficiency comes from grouped approval points and targeted evidence, not from
skipping analysis.

### Targeted Authority Reading

For each pass, read fully:

- authority-order entry point;
- workflow;
- current pass plan;
- relevant blueprint entry;
- relevant control or decision sections;
- original implementation diff;
- relevant prerequisite and downstream plans;
- current implementation areas.

Large audit, checklist, and remediation records may be searched by pass or
control identifier and expanded where relevant instead of reread end to end
without purpose.

### Exception-Oriented Reporting

The analysis remains comprehensive. Reports should emphasize material findings,
corrections, unusual ownership or proof decisions, remaining gaps, and
blockers.

A mandatory requirement reconciliation or completion matrix prevents
requirements from disappearing despite shorter prose.

### Pass-Family Research Reuse

Related split passes may reuse already accepted common authority, history, and
repository reconnaissance.

Each pass or subpass still requires its own requirements, current-state
verdict, implementation or artifacts, evidence, traceability, remaining gaps,
and final approval. Shared research does not create family-wide automatic
approval.

## 18. Test And Evidence Principles

Use the accepted EN-01 architecture and current testing documents for detailed
mechanics. Permanent proof principles include:

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
- generated pytest-node traceability rather than manually maintained node IDs;
- passing tests alone are never sufficient evidence of production readiness.

## 19. Security And Confidentiality

Use `docs/production-readiness/00-READ-ME-FIRST.md` as the canonical global
sensitive-information policy. If sensitive material is discovered during recheck
work, report location and category only, not the value.

## 20. Automated Review And Stop Discipline

The main Codex session must preserve the one-stage/gate boundary clearly. It
owns automatic transitions between clean states and must stop only at durable
blockers, Gate A/Gate C hard review limits, unsafe state, or the manual
PR-merge boundary.

This prevents mixed audit and implementation work, repeated redesign,
accidental scope expansion, production changes driven by tests, endless Gate A
or Gate C review loops, and ambiguous workflow state.
