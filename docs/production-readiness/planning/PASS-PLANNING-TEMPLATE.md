# [PASS ID] - [Plain-English Title]

## At A Glance

| Field | Value |
|---|---|
| Pass | `[PASS-ID]` |
| Track | `[WSxx / PROGRAM / GOVERNANCE / other canonical track]` |
| Type | `[Domain implementation / API / Database / Migration / Provider / Frontend / CI / Operations / other pass type]` |
| Primary controls | `[CONTROL-ID, CONTROL-ID]` |
| Authority basis | `[Primary controls / decision records / blueprint entry / other authoritative sources]` |
| Depends on | `[PASS-ID / prerequisite / None]` |
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
  `docs/production-readiness/planning/TESTING-RECORD-TEMPLATE.md` when creating
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

## 6. Testing And Evidence

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

## 7. Integration / Operational Expectations

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

## 8. Not Part Of This Pass

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

## 9. Related Controls And Remaining Evidence

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

## 10. Completion Criteria

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
- How is each requirement proven?
- Where do detailed testing risks and scenarios live, when required?
- What integrates with or consumes this work?
- What is deliberately outside the pass?
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
