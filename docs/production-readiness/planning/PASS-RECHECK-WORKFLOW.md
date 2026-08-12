# Production-Readiness Pass Recheck Workflow

This document defines the reusable process for revalidating an already
implemented Pickup Lane production-readiness pass. It is process guidance only.
It does not define product behavior and does not override the authority order in
`docs/production-readiness/00-READ-ME-FIRST.md`.

## 1. Purpose And Applicability

Use this workflow when rechecking an already-implemented pass against current
repository truth, especially when the trusted testing or evidence architecture
has changed since the pass was first implemented.

Distinguish three kinds of work:

- Greenfield implementation creates an approved pass for the first time from
  authority and the current pass plan.
- Pass recheck or revalidation verifies whether an already-implemented pass
  still agrees with authority, current repository behavior, current ownership,
  and current evidence standards.
- Testing or evidence reconstruction creates fresh trusted proof under the
  accepted EN-01 architecture when old tests or evidence are no longer trusted.

The objective is not merely to prove that current code passes tests. The
objective is to establish that current repository truth is production-grade,
matches authoritative requirements, has honest ownership, and has adequate
evidence or explicit remaining gaps.

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
current implementation state. Historical branches, old prompts, old tests, and
past PR descriptions are provenance unless a current authoritative source
explicitly adopts them.

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

### Historical Test Restriction

Historical or pre-reset tests remain outside behavioral reasoning.

Do not read historical test contents, execute them, derive expected behavior or
scenarios from them, compare current behavior against them, or repair current
production code to satisfy them. If an original PR contains historical test
files, record their path and change presence for provenance only.

## 4. Requirement-By-Requirement Provenance Model

For every material authoritative obligation, Phase 1 must answer:

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

Phase 1 must also audit implementation back toward authority:

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

## 13. Permanent Phase Workflow

Each phase does exactly its assigned job, stops for human review, and does not
begin the next phase.

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
not automatic cleanup, rebase, reset, restore, stash, or deletion.

### Phase 1 - Zero-Trust Audit

Read-only after branch creation.

Reconcile:

```text
AUTHORITATIVE REQUIREMENTS
-> ORIGINAL PLAN
-> ORIGINAL IMPLEMENTATION / PR
-> ORIGINAL OMISSIONS
-> MATERIAL LATER EVOLUTION
-> CURRENT FULL REPOSITORY STATE
-> NEGATIVE SPACE
-> IMPLEMENTATION-TO-AUTHORITY EXTRA SCOPE
-> BYPASS / SINGLE-OWNER STATE
-> DEPENDENCIES / CROSS-PASS HANDOFFS
-> TRACKED ARTIFACT STATE
-> EXTERNAL-EVIDENCE BOUNDARY
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
phases until the required decision exists.

End with human review.

### Phase 2 - Finalize Canonical Pass Plan

Inputs are the approved Phase 1 audit, current authority, and
`PASS-PLANNING-TEMPLATE.md`.

Only reconcile and finalize the canonical pass plan. The plan defines what must
be true; it does not implement corrections. Do not design tests, create
requirement JSON, or create `TESTING_RECORD.md`.

Once approved, freeze the plan unless concrete contradictory evidence later
requires reopening it.

### Phase 3A - Pass-Owned Implementation Correction

Run only when the approved audit or plan proves a pass-owned implementation or
artifact correction is required. Depending on the pass, this may include
production source, tracked configuration, governance or document artifacts, or
repository-owned operational artifacts.

Do not modify production merely because testing is inconvenient. Do not add
unrelated refactors. Do not write full trusted evidence here; only run narrow
syntax, loadability, or safety validation when needed to establish that the
correction itself is coherent.

If no implementation or artifact correction is required, explicitly skip this
phase.

### Phase 3B - Read-Only Test / Evidence Design Gate

Before designing evidence, read the accepted testing architecture and
standards. Testing standards define how proof is organized; they do not define
product behavior.

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
out of bounds. No files are changed in this phase.

For every requirement or meaningful requirement group, decide before Phase 4:

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

### Phase 4 - Trusted Test / Evidence Implementation

Implement only the approved Phase 3B design.

As applicable, create stable requirement declaration JSON, `TESTING_RECORD.md`,
fresh trusted executable tests, and repository-owned non-executable evidence
under the accepted EN-01 architecture.

Tests are derived from authority and the approved pass plan, never from
historical tests. Validate focused tests, relevant prerequisite regressions,
checker file/domain/suite scopes as appropriate, generated traceability,
syntax/compile, environment/database/network/provider safety, and
`git diff --check`.

Implement the approved proof architecture rather than quietly redesigning it.
Do not change production code merely to make a test pass. If current production
contradicts the approved plan, stop and reopen the appropriate earlier phase.

### Phase 5 - Independent Test / Evidence Adequacy Review

Read-only review of the implemented proof. Evaluate whether the evidence
actually covers the approved risks and proves the intended safeguards. Do not
approve merely because commands are green.

Check for missing risks, weak assertions, tests passing for the wrong reason,
wrong proof layers, implementation-detail coupling, missing persisted-effect
proof, missing rejected-side-effect proof, missing idempotency, concurrency, or
boundary proof where applicable, unsupported adequacy claims, fake pytest used
for documentary or provider facts, and redundant evidence without distinct risk
value.

If a real deficiency exists, allow one tightly scoped correction round. Do not
casually reopen the whole pass.

### Phase 6 - Whole-Pass Local Review

Read-only review of the complete pass together:

```text
AUTHORITY
<-> CANONICAL PLAN
<-> IMPLEMENTATION / ARTIFACTS
<-> REQUIREMENT DECLARATIONS
<-> TESTING_RECORD
<-> EXECUTABLE / NON-EXECUTABLE EVIDENCE
<-> GENERATED TRACEABILITY
```

Review all material issues in one pass. Do not drip-feed cosmetic findings.
Require correction only for issues affecting correctness, evidence
truthfulness, security, scope, maintainability, traceability, or production
readiness.

As applicable, rerun the approved relevant validation, inspect the complete
local pass change set, review actual generated traceability, run
`git diff --check`, perform a secret/confidential-data review of the complete
local change set, verify no unexpected files are present, and verify repository
contents remain unchanged by the read-only review. Do not require unrelated
full-repository validation when the approved pass scope does not justify it.

Green commands alone are not sufficient for whole-pass approval. Phase 6 must
review semantic consistency and evidence adequacy, not merely test execution.

End with exactly one outcome:

- approved for Git finalization;
- corrections required.

Do not commit or push during this phase.

### Phase 7 - Git / PR Finalization

Run only after Phase 6 approval. This phase is mechanical.

Verify the accepted baseline, exact approved change set, no unexpected files,
no staged contamination, secret/confidential-data safety, and diff integrity.

Then stage only approved files, inspect the exact staged diff, create one pass
commit unless the approved pass explicitly requires a different commit
structure, push the existing remediation branch normally, create or update
exactly the intended PR, review the remote changed-file list and PR
description, verify no unrelated or sensitive content, verify base/head/commit,
verify intended upstream tracking, verify local HEAD equals the pushed remote
branch HEAD, and verify no merge or auto-merge occurred.

Normal finalization must not amend, squash, rebase, reconstruct history through
cherry-pick, rewrite history, force-push, create an unintended second PR,
merge, or enable auto-merge unless that operation was already approved for the
pass.

Commit messages and PR bodies must not expose secrets or credential values, raw
provider evidence, provider-private URLs, personal/private user data, payment
data, local filesystem paths or local usernames, internal conversation or chat
history, or temporary debugging information.

The user merges manually.

## 14. Freeze Rule

Once a phase receives human approval, its result is frozen. A later phase may
reopen it only when concrete evidence demonstrates a material contradiction.

Do not rewrite a plan because a test name is inconvenient, change production
merely to satisfy a test, weaken a requirement to make evidence pass, redesign
scenarios while implementing them, reopen approved phases for cosmetic
preferences, or allow scope creep between phases.

## 15. Test And Evidence Principles

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

## 16. Security And Confidentiality

Throughout all phases, do not publish or echo real passwords, API keys, tokens,
private keys, database credentials, webhook secrets, signed or private URLs,
recovery codes, personal or private user data, payment data, raw provider
evidence, provider-private dashboard links, or local secrets.

Synthetic placeholders must be obviously synthetic. If sensitive material is
discovered, report location and category only, not the value.

## 17. Human Review And Stop Discipline

Each Codex prompt should explicitly state:

```text
Do only this phase. Do not begin the next phase.
```

This prevents mixed audit and implementation work, repeated redesign,
accidental scope expansion, production changes driven by tests, endless review
loops, and ambiguous approval state.
