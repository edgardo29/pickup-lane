# [PASS ID] - [Plain-English Title]

## At A Glance

| Field | Value |
|---|---|
| Pass | `[PASS-ID]` |
| Blueprint parent pass | `[Parent PASS-ID and title]` |
| Execution mode | `[First-time implementation / Recheck / Closeout / other]` |
| Track | `[WSxx / PROGRAM / GOVERNANCE / other canonical track]` |
| Type | `[Domain implementation / API / Database / Migration / Provider / Frontend / CI / Operations / other pass type]` |
| Primary controls | `[CONTROL-ID, CONTROL-ID]` |
| Authority basis | `[Primary controls / decision records / blueprint entry / other authoritative sources]` |
| Depends on | `[PASS-ID / prerequisite / None]` |
| Intake record | `[path or Not applicable]` |
| Requirement declaration | `[path or Not applicable]` |
| Trusted test scope | `[path or Not applicable]` |

## How To Use This Template

This template is the reusable planning-document standard for Pickup Lane
production-readiness passes. It is meant to make pass documents readable,
understandable, well organized, and technically complete.

Do not make a pass easier to read by deleting technical detail that another
developer needs to understand, implement, or review the work correctly. Improve
readability through context, hierarchy, examples, clear labels, and plain
explanations before dense terminology.

Before creating or revising a pass planning document, reconcile the pass
against the current production-readiness authority order defined by the
canonical read-first documentation. Confirm the relevant sources agree,
including as applicable the current accepted repository tree, locked
audit/control sources, finalized remediation plan, approved decision records or
decision inventory, master production-readiness blueprint, and accepted
pass-specific planning or instructions. Lower-level planning cannot silently
override higher authority. If authoritative sources conflict, stop, document
and resolve the conflict before pass work continues, and do not guess or
silently choose one source.

For a first-time executable pass, use
`docs/production-readiness/planning/workflows/PASS-IMPLEMENTATION-WORKFLOW.md`
and an approved intake record. Owner direction selects the parent pass or
remaining parent scope to evaluate; it does not replace Stage 0 intake. If the
work starts from a parent blueprint pass, use
`docs/production-readiness/planning/templates/PASS-INTAKE-TEMPLATE.md` and
`docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md` before
Gate A to establish the parent pass, executable pass ID, decomposition
rationale, dependencies, and non-overlap. Historical accepted decompositions do
not require retroactive intake creation. `Not applicable` is allowed for intake
only for recheck, closeout, program, or other genuinely non-intake work. For a
pass already accepted into `develop`, or historical implementation predating
the current workflow, use
`docs/production-readiness/planning/workflows/PASS-RECHECK-WORKFLOW.md`.

Use progressive detail:

```text
WHY
-> WHAT
-> REQUIREMENTS
-> TECHNICAL DESIGN
-> IMPLEMENTATION SCOPE
-> TESTING / EVIDENCE
-> INTEGRATION
-> BOUNDARIES
-> CONTROLS / REMAINING EVIDENCE
-> COMPLETION
```

Write current truth, not implementation history. Prefer language such as:

- "The pass requires..."
- "The pass-owned output must..."
- "The contract guarantees..."

Avoid diary-style references to past fixes, discoveries, superseded text, or
replaced designs unless that history is genuinely necessary to understand an
authoritative constraint.

Use these rules throughout:

- Requirements describe what must be true.
- Technical Design / Contracts describes exact technical behavior, invariants,
  constraints, and design rules.
- Testing And Evidence explains how the requirements are proven.
- Detailed scenario inventories, edge cases, failure cases, and adequacy
  reasoning belong in the appropriate `TESTING_RECORD.md` when that testing
  architecture applies. Use
  `docs/production-readiness/planning/templates/TESTING-RECORD-TEMPLATE.md` when creating
  or reconciling those records. The planning document may summarize major
  risks, but it should not duplicate the entire testing record.
- Explain control IDs and relationships instead of listing identifiers without
  context.
- Separate what this pass establishes from what remains for later passes or
  evidence.
- Document non-goals explicitly to prevent scope creep.
- If a standard section does not apply, state `Not applicable - [reason]`
  instead of inventing filler.
- Do not invent requirements, values, thresholds, provider behavior, owner
  decisions, or evidence merely to fill the template.

A developer unfamiliar with Pickup Lane should be able to understand the
purpose, scope, risks, technical contract, evidence model, and completion
conditions without needing oral history from the original author.

## Executable Pass Identity And Intake

Every planning document must identify the pass it is actually designing.

For first-time implementation, state the parent blueprint pass and whether the
parent is implemented directly or decomposed into this executable child pass.
The plan must preserve the parent intent while defining a reviewable,
non-overlapping implementation scope.

When an intake exists, link it in the At A Glance table and carry forward its
approved parent/child boundary, dependencies, stop conditions, and non-goals.
When intake is not applicable, explain why in the relevant scope or authority
section.

For first-time implementation, an approved intake record is a frozen gate
artifact. Stage 0 reports its exact path and SHA-256 before human approval; Gate
instructions identify the approved intake-record SHA. Gate A and Gate B consume
that record read-only unless a Stage 0 revision with a new SHA and new human
approval changes it.

For every executable pass, explain:

- one primary outcome;
- coherent requirement family;
- why this is one safe merge/rollback or forward-fix unit;
- parent contribution;
- prerequisite state;
- child handoff;
- safe state after merge.

When the pass is a child, identify allocated parent obligations and state that
the plan does not reopen sibling-child scope.

This template does not select the next pass. Pass selection comes from explicit
owner direction and the current execution register.

## 1. Purpose

Explain the pass in normal engineering language before relying on dense
implementation terminology.

This section should cover:

- what the pass does
- what problem it solves
- where the resulting behavior, foundation, or evidence is used
- what broad area it intentionally does not try to complete

A developer should understand the basic point of the pass from this section
alone.

## 2. Why This Matters

Explain the actual product, security, reliability, operational, or compliance
failure modes the pass is intended to prevent.

Use concrete but generic examples where they help. Depending on the pass, the
risks might include:

- duplicate payments
- oversold game capacity
- stale authorization
- leaked sensitive data
- lost jobs
- unsafe migrations
- provider replay failures
- cross-user frontend state
- unrecoverable storage objects

Examples should illustrate risk. They should not introduce requirements,
thresholds, provider promises, or owner decisions that are not authoritative for
the pass.

## 3. Requirements

Use stable requirement IDs and describe what must be true.

| ID | Requirement | What it means | Why it matters |
|---|---|---|---|
| `[PASS-REQ-001]` | `[Requirement]` | `[Plain-English meaning]` | `[Risk/reason]` |

Requirement guidance:

- IDs must be stable across edits.
- Requirements state what must be true, not how tests are written.
- The table should stay readable for a developer who is new to the pass.
- Detailed test-case inventories do not belong in this table.
- Authoritative source controls should be identified and explained in plain
  language.
- Do not add requirements merely because the template has space.

## 4. Technical Design / Contracts

This section is pass-specific. It is where important technical detail belongs.
Do not force the same subsections into every pass.

Use subsections for the concepts, invariants, state models, integration
contracts, evidence standards, decision rules, failure behavior, and constraints
that define correct behavior for this pass.

### 4.1 [Technical concept / invariant]

**What this is**

Explain the concept in understandable engineering language before relying on
specialized terminology.

**Contract / required behavior**

State the exact technical rules that make the behavior correct. Depending on
the pass, this may include allowed behavior, prohibited behavior, limits, state
transitions, concurrency behavior, failure behavior, serialization behavior,
compatibility rules, recovery behavior, or security constraints.

**Why**

Explain why important restrictions exist where that is not obvious.

Example technical subsection topics by pass type:

Database:

- transaction boundaries
- invariants
- locking
- concurrency behavior
- rollback or failure behavior

Payments:

- state model
- webhook authority
- idempotency
- compensation or refunds
- reconciliation

Frontend:

- state ownership
- browser persistence
- API and error behavior
- routing
- accessibility and security behavior

Provider:

- provider contract
- timeout and retry behavior
- replay and idempotency behavior
- failure isolation
- sandbox or runtime verification

Governance and evidence:

- decision authority
- evidence source and artifact identity
- review and approval responsibilities
- exception handling
- reassessment triggers

Configuration, CI, and release:

- environment boundaries
- artifact identity
- release gates
- rollback or forward-fix behavior
- required verification evidence

Migration:

- compatibility
- upgrade path
- rollback or forward-fix behavior
- interrupted migration behavior
- rehearsal requirements

These are examples only. Remove irrelevant topics and add the pass-specific
technical subsections that another developer needs to implement or review the
work correctly.

## 5. Implementation Scope

Describe the systems, code, configuration, documents, evidence, provider
resources, operational procedures, or other artifacts owned by this pass.

This section should explain:

- which implementation, configuration, evidence, documentation, operational
  procedure, provider resource, or other artifact the pass owns
- what behavior, evidence, or invariants must be implemented or preserved
- what ownership boundaries or dependencies constrain the pass
- which systems, artifacts, resources, or code areas may be affected
- what behavior or evidence is already correct and should remain unchanged, if
  relevant

Use current-truth wording. Do not turn this section into a change log. Exact
filenames are helpful when they clarify ownership, but artifact-level,
resource-level, module-level, or concept-level ownership is often more stable
and useful.

Narrative ownership may use modules, resources, or artifact classes, but the
final frozen repository file lists must use exact repository-relative paths.
External/provider/runtime artifacts that are not repository files may be listed
separately using stable artifact descriptions, owners, or evidence identifiers.

The final Gate A plan must distinguish:

| Scope item | Exact value |
|---|---|
| Frozen Stage 0 intake artifact | `[exact repository-relative path or Not applicable]` |
| Frozen canonical plan artifact | `[exact repository-relative path]` |
| Exact Gate B editable file set | `[exact repository-relative paths only]` |
| Exact expected final pass changed-file set | `[exact repository-relative paths only]` |

For a first substantive child pass, the expected final changed-file set is:

- frozen Stage 0 intake record;
- frozen Gate A canonical plan;
- exact Gate B editable files, which include
  `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md`;
- no additional repository file.

The intake record and canonical plan are not Gate B-editable.

For later children, the accepted intake record already exists in `develop`; it
is read-only and normally does not appear in the new child diff. The expected
final changed-file set is:

- frozen Gate A canonical plan;
- exact Gate B editable files, which include the execution register;
- no additional repository file.

For a parent implemented whole, the expected final changed-file set is:

- frozen Stage 0 intake record;
- frozen Gate A canonical plan;
- exact Gate B editable files, which include the execution register;
- no additional repository file.

Every substantive first-time executable pass changes accepted execution state
when merged. Therefore, Gate A must include
`docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md` in the
exact Gate B editable file set and design the exact register change. By default,
the first child prepares the register update for accepted intake/decomposition,
accepted first-child state, remaining child state, and incomplete parent state;
later children prepare their own accepted state and remaining parent state; the
final child marks the parent complete; and a parent kept whole prepares the
direct parent completion update. Gate C reviews the proposed register state with
the complete pass. Gate D never authors or semantically edits register content,
and routine post-merge tracker-only PRs are not required.
Program/documentation maintenance and historical rechecks remain outside this
automatic first-time-pass rule unless their explicit scope says otherwise.

## 6. Implementation Impact And Compatibility Review

Document the Gate A repository-wide impact scan.

Identify:

- production callers;
- frontend callers;
- routes;
- settings/config inventories;
- CORS/header contracts;
- provider/timeout/retry/rate inventories;
- middleware assumptions;
- schema/migration/database expectations;
- trusted cross-pass tests;
- compatibility files expected to change;
- areas reviewed and found unaffected.

This section should make the final file set predictable before Gate B. Do not
wait for broad regression to discover obvious finite inventories, callers, or
accepted compatibility contracts.

## 7. Testing And Evidence

Explain how the requirements are proven. Tests prove behavior; they do not
define behavior. Authority and requirements define the behavior.

Document only evidence types that are relevant to the pass, such as:

- trusted test ownership and location
- requirement declaration location, when applicable
- human testing and risk record location, when applicable
- required unit, integration, API, frontend, migration, provider, or runtime
  test layers
- non-test evidence
- runtime evidence
- provider evidence
- migration evidence
- browser evidence
- concurrency evidence
- recovery evidence

Where the EN-01 testing architecture applies, use this relationship:

```text
Pass
-> Requirement
-> Risk / Scenario / Edge Case
-> Trusted Test
-> Generated Traceability
```

Under that architecture, exact pytest node references should be generated from
collection and requirement metadata rather than manually maintained in the
planning document.

Summarize major risks and evidence coverage here. Keep detailed scenario
inventories, edge cases, failure cases, and adequacy reasoning in the
appropriate `TESTING_RECORD.md` when that record applies.

## 8. Validation Strategy

Summarize the validation design. Do not require raw command dumps in the
reusable template.

Pass plans must never contain literal sensitive values, including usernames,
passwords, credential-bearing database or service URLs, API keys or tokens,
private keys, webhook/signing/encryption secrets, recovery credentials,
private provider/account/project/tenant/customer identifiers when the actual
value is not required to define the contract, or other secret or credential
material. Validation commands or examples must use environment-variable
references or sanitized placeholders, such as
`DATABASE_URL="$TEST_DATABASE_URL"`, instead of literal credential values.

Cover applicable:

- focused scope;
- compatibility scopes;
- prerequisite regressions;
- specialized frontend/browser/provider/migration/PostgreSQL/concurrency or
  runtime proof;
- checkers;
- traceability;
- broad regression;
- final semantic sanity sweep;
- diff/security/scope checks.

## 9. Integration / Operational Expectations

Explain what consumes, integrates with, or depends on this pass now or in later
work.

This section should cover:

- existing or later systems that consume the pass
- important integration contracts
- operational expectations
- boundaries future consumers must preserve

If there are no meaningful consumers or operational expectations for the pass,
write:

```text
Not applicable - [reason]
```

Do not invent integration content.

## 10. Not Part Of This Pass

List explicit non-goals. This section protects pass boundaries and prevents
scope creep.

Identify, where relevant:

- neighboring work intentionally deferred
- later passes
- provider or runtime work not yet authorized
- broader systems that may eventually consume the pass but are not completed
  here

Do not use this section as an excuse to omit something actually required by the
pass.

## 11. Related Controls And Remaining Evidence

Explain which controls or decisions the pass advances, what it establishes for
each, and what remains later.

| Control / Decision | What this pass establishes | What remains later |
|---|---|---|
| `[CONTROL-ID]` | `[Contribution of this pass]` | `[Remaining work/evidence for full closure]` |

This section must make it obvious:

- which controls or decisions the pass advances
- exactly what the pass establishes
- whether the control is fully closed or remains open
- what later implementation or evidence remains

Do not claim complete control closure unless authoritative evidence supports
that conclusion.

### Supporting relationships

Use this optional subsection for secondary controls or decisions that are
related to the pass but do not need a full table row.

## 12. Stop And Correction Boundaries

State what discoveries:

- remain Gate B implementation fixes;
- require Gate A correction;
- require Stage 0 revision;
- remain external/later evidence.

This section should prevent Gate B from silently expanding scope and should
prevent Stage 0 structural questions from being hidden inside implementation.

## 13. Completion Criteria

Answer: "When is this pass complete?"

Use a concise checklist. Include only criteria relevant to the actual pass.

- [ ] Every pass requirement is accounted for.
- [ ] Required behavior, configuration, evidence, documentation, or other
  pass-owned outputs match the requirements and contracts in this document.
- [ ] Trusted tests pass, where tests are required.
- [ ] Required checker or traceability passes are complete, where applicable.
- [ ] Required provider, runtime, browser, migration, concurrency, or recovery
  evidence exists, where applicable.
- [ ] The testing/risk record is complete, where required.
- [ ] Pass documentation matches the pass-owned outputs and authoritative scope.
- [ ] No unresolved blocker remains.
- [ ] Pass boundaries remain intact.

Pass completion and full audit-control closure are not automatically the same
thing. A pass may be complete while later implementation or evidence is still
required before a broader control can close.

## Flexibility Rule

The top-level structure is standardized; the technical content is not.

This template should not create bureaucracy where authors fill irrelevant
headings with filler. Use the shared sections for consistent navigation and
reasoning, then make the technical depth match what another developer needs to
complete and review the pass correctly.

In particular:

- Technical Design / Contracts subsections are pass-specific.
- Testing and evidence types are pass-specific.
- Integration content may be `Not applicable - [reason]`.
- Exact technical depth depends on the pass.

The goal is consistency of navigation and reasoning, not identical documents.

## Document Self-Review

Before marking a pass plan ready for review, confirm that a developer
unfamiliar with the pass can answer:

- What does this pass do?
- Why does it exist?
- What can go wrong if the pass is incorrect or incomplete?
- What requirements must be true?
- What technical contracts, invariants, evidence standards, or decision rules
  define correct behavior?
- What systems, code, configuration, evidence, documents, resources, or
  operational responsibilities does the pass own?
- What current callers, routes, inventories, compatibility files, and
  materially affected documents were reviewed?
- How is each requirement proven?
- What validation strategy proves the focused pass and affected compatibility
  scopes?
- Where do detailed testing risks and scenarios live, when required?
- What integrates with or consumes this work?
- What is deliberately outside the pass?
- Which discoveries stay in Gate B, require Gate A correction, require Stage 0
  revision, or remain external/later evidence?
- Which controls or decisions does the pass advance?
- What evidence or work still remains later?
- What makes the pass complete?

Also check that:

- important technical detail was not removed merely for brevity
- unexplained jargon was reduced or explained
- sections do not unnecessarily duplicate one another
- no implementation-history diary language was introduced
- no requirement, control, or evidence was invented
- current authoritative terminology is used
- the completed plan contains no literal credentials, secrets,
  credential-bearing URLs, or other prohibited sensitive values
