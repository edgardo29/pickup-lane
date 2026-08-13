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

## 13. Permanent Four-Gate Workflow

Each gate does exactly its assigned job, stops at its approval boundary, and
does not begin the next gate. The four-gate model groups approvals for speed;
it does not remove audit depth, evidence design, independent review, security
review, or Git publication safeguards.

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
not automatic cleanup, rebase, reset, restore, stash, or deletion.

### Gate A - Reconciliation And Design

Gate A is one comprehensive reasoning run before implementation. It contains
the former zero-trust audit, canonical-plan reconciliation, and test/evidence
design responsibilities.

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
approved audit, current authority, and `PASS-PLANNING-TEMPLATE.md`.

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
- exact Gate B file set.

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
- the exact Gate B file set is feasible;
- no hidden prerequisite or owner decision remains.

This is analysis and validation only. Do not create the proposed implementation
artifacts during Gate A.

#### Gate A Human Approval

Gate A returns material findings, a requirement reconciliation matrix, the
updated canonical plan, exact correction design, exact evidence design, exact
Gate B file set, and blockers.

The canonical plan, requirements, correction design, evidence design, and Gate
B file set become frozen only after human approval.

#### Gate A Review Completion Rule

Before approving Gate A or issuing a Gate A correction instruction, the
reviewer must complete review of the full Gate A report and the complete
canonical plan, including authority alignment, numeric-value authority,
cross-pass ownership, current repository truth, requirements, correction
design, evidence design, completion criteria, and the exact Gate B editable
file set.

Return all material findings together. After corrections, review the complete
corrected Gate A state, not only the sections changed by the correction.

### Gate B - Approved Implementation

Gate B implements exactly the approved Gate A design. It contains the former
pass-owned correction and trusted test/evidence implementation
responsibilities.

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

If Gate B unexpectedly needs another production file, another requirement,
another proof layer, provider access, PostgreSQL, browser evidence, migration
evidence, concurrency evidence, controlled-time evidence, or broader scope,
stop and return to Gate A. Gate B must not silently expand or redesign the
pass. Tests must not redefine behavior or cause requirements to be weakened.

Validate focused tests, relevant prerequisite regressions, checker
file/domain/suite scopes as appropriate, generated traceability,
syntax/compile, environment/database/network/provider safety, and
`git diff --check`.

Gate B ends with an implementation and validation report. It does not commit or
push.

### Gate C - Independent Final Review

Gate C must be a new, independent, read-only run. It combines the former
evidence adequacy and whole-pass local review responsibilities without removing
either review obligation.

Gate C never modifies repository content. When Gate C finds a defect, it
returns `corrections required` and defines the exact authorized correction
scope. A separate scoped correction run performs only the approved changes.
After the correction, a new independent read-only Gate C re-review is required
before approval or Gate D. Gate C must not fix files during the review run,
silently transition from review into implementation, or review an agent's own
unapproved correction in the same run.

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
local change set, verify no unexpected files are present, and verify repository
contents remain unchanged by the read-only review. Gate C does not
automatically rerun already-current successful validation. Gate C may run only
the smallest relevant test or check when it has a concrete stated reason, and
the reason and exact rerun must be reported. Do not require unrelated
full-repository validation when the approved pass scope does not justify it.

Green commands alone are not sufficient for whole-pass approval. Gate C must
review semantic consistency and evidence adequacy, not merely test execution.

#### Post-Gate C Correction Routing

Gate C reports correction routing; it does not perform the correction.

The run that modifies files owns post-change validation. The independent
read-only reviewer owns semantic review.

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

The subsequent Gate C re-review remains independent, semantic, and read-only.
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
automatically run unrelated application suites. The correction is followed by
the required targeted independent read-only Gate C re-review.

An implementation mistake inside the already-approved frozen design may use a
separate scoped correction run only when the authoritative contract, canonical
plan, requirement set, proof layer, approved file set, and pass scope remain
unchanged. The correction run fixes only that approved mistake, runs affected
targeted validation, runs the full relevant regression, checker, and
traceability validation required for the corrected final pass state, corrects
any in-scope failures before handoff, and is followed by a new full independent
read-only Gate C review.

Return to Gate A when a finding requires a new requirement, changed
requirement, new owner decision, new proof layer, expanded file set, broader
pass scope, or material plan revision. No post-Gate C correction run may make
these changes under Gate C authorization.

Do not impose an artificial maximum number of correction rounds. Every
correction round must be followed by a new independent read-only Gate C review,
using either the targeted or full route authorized by the prior Gate C finding.
Approval requires a genuinely clean independent review.

End with exactly one semantic outcome:

- approved for Git finalization;
- corrections required.

When the outcome is `corrections required`, report the material finding, the
affected requirement or contract, the exact authorized correction scope, and
whether the next review is a targeted Gate C re-review, a full Gate C re-review,
or a return to Gate A. Gate C itself leaves repository contents unchanged.

Do not commit or push during Gate C.

### Gate D - Git And PR Finalization

Run only after Gate C approval. This gate is mechanical.

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

## 14. Additional Intermediate Gates

Do not create lanes or risk scores.

An additional intermediate gate is allowed only when a concrete discovered
blocker cannot safely fit within the four standard gates. Examples include:

- unresolved owner or policy decision;
- real provider-account mutation;
- destructive migration or real-data transformation;
- irreversible operational action;
- required external evidence that must be gathered before implementation;
- another concrete issue requiring independent approval before Gate B can
  continue.

The extra gate must address only the discovered blocker. Do not create
speculative process merely because a pass sounds high risk.

## 15. Freeze Rule

After Gate A approval, the canonical plan, requirements, correction design,
evidence design, and authorized Gate B file set are frozen unless concrete
contradictory evidence requires returning to Gate A.

After Gate C approval, no semantic changes are permitted in Gate D.

Do not rewrite a plan because a test name is inconvenient, change production
merely to satisfy a test, weaken a requirement to make evidence pass, redesign
scenarios while implementing them, reopen approved gates for cosmetic
preferences, or allow scope creep between gates.

## 16. Safe Efficiency Rules

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

## 17. Test And Evidence Principles

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

## 18. Security And Confidentiality

Throughout all gates, do not publish or echo real passwords, API keys, tokens,
private keys, database credentials, webhook secrets, signed or private URLs,
recovery codes, personal or private user data, payment data, raw provider
evidence, provider-private dashboard links, or local secrets.

Synthetic placeholders must be obviously synthetic. If sensitive material is
discovered, report location and category only, not the value.

## 19. Human Review And Stop Discipline

Each Codex prompt should explicitly state:

```text
Do only this gate. Do not begin the next gate.
```

This prevents mixed audit and implementation work, repeated redesign,
accidental scope expansion, production changes driven by tests, endless review
loops, and ambiguous approval state.
