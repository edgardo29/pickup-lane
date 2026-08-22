# Production-Readiness Pass Intake Template

Use this template to decide what executable engineering work should happen next
for a production-readiness parent pass.

An intake has one job:

```text
Decide the correct executable engineering shape of the parent work.
```

The intake must determine whether the parent:

- should execute as one pass;
- should be split into multiple executable passes;
- is blocked by a technical prerequisite;
- is blocked by an owner or authority decision.

The intake is not an implementation plan.

It does not design the implementation, define detailed tests, prescribe exact
code changes, or narrate the production-readiness workflow.

Write the reader-facing parts for a competent developer who needs to understand:

- what parent engineering work is being evaluated;
- which facts affect how that work should be executed;
- what execution shape was chosen;
- why that shape is technically correct;
- where every major part of the parent scope belongs;
- what engineering work can proceed next.

Authority controls technical meaning, approved scope, dependencies, identifiers,
and accepted decisions. Authority wording does not need to be copied verbatim.
Preserve the meaning and express it in normal technical language.

Internal production-readiness bookkeeping belongs only in `Internal Record`
unless an exact process term is genuinely necessary to understand the
engineering decision.

Intake records are tracked production-readiness artifacts. Do not include
literal credentials, credential-bearing URLs, secrets, private keys or tokens,
private provider values, personal or payment data, raw sensitive logs, local
machine paths, session state, internal chat material, or other local-only
sensitive information.

Use environment-variable names or sanitized descriptions when configuration
must be referenced.

Store intake records at:

```text
docs/production-readiness/planning/passes/<family>/<parent-id>-intake.md
```

If a section is not applicable, write:

```text
Not applicable - [reason]
```

---

# Universal Intake Rules

## Orient The Reader Before Presenting Information

Every reader-facing section must begin with a short explanation of:

1. what the section tells the reader;
2. why that information matters to the execution decision;
3. how the information that follows should be interpreted.

Do not jump directly from a heading into a table, dependency list, split, or
technical fact without explaining why the reader is looking at it.

Write the explanation specifically for the parent work being evaluated.

Do not use generic filler merely to satisfy this rule.

Sections 1 through 5 are reader-facing engineering sections.

`Internal Record` is the only section intended primarily for workflow
bookkeeping.

---

## Keep Reader-Facing Sections About Engineering

Sections 1 through 5 should be understandable without knowledge of the
production-readiness framework.

Do not fill them with terminology such as:

- Gate A;
- Gate B;
- Stage 0 mechanics;
- execution-register transitions;
- evidence classifications;
- publication mechanics;
- approval workflow;
- trusted-evidence terminology;
- artifact-state terminology.

If the engineering decision can be explained without a framework term, use
normal engineering language.

Exact workflow terminology may remain in `Internal Record`.

---

## Do Not Design The Implementation Here

The intake decides **how the parent work should be divided for execution**.

It does not decide detailed implementation.

Do not define here:

- detailed APIs;
- exact implementation algorithms;
- exact configuration values unless already approved and necessary to the split;
- detailed formulas;
- detailed failure handling;
- detailed permission models;
- test cases;
- assertion inventories;
- file-by-file implementation instructions;
- migration steps;
- detailed validation strategy.

Those belong in the engineering plan for the selected executable pass.

Include a technical detail only when it materially affects the execution
decision.

---

## Create Only Real Executable Work

Do not create a child whose purpose is merely to:

- document rules;
- prepare another plan;
- restate requirements;
- collect information that belongs inside another executable pass;
- create a handoff;
- perform planning that the engineering-plan stage already exists to perform.

A child must represent either:

1. a meaningful executable engineering result; or
2. a genuinely independent verification result.

Each child must leave the system, repository, or verified production state in a
coherent condition that can be accepted independently.

If two pieces only become correct, safe, usable, or meaningful when completed
together, keep them together.

Do not split work merely because it can be described as separate tasks.

---

## Split For Engineering Reasons

A split should exist because the work has genuinely different:

- prerequisites;
- implementation boundaries;
- verification environments;
- technical ownership;
- dependency order;
- source-versus-external evidence needs;
- independently acceptable outcomes.

Do not split merely to make individual passes smaller.

Do not create artificial sequencing where one child is only preparation for the
next.

---

## Do Not Guess Missing Facts

Unknown information does not automatically block the parent.

For each material unknown, determine whether the current executable work
actually requires it.

If a child can be implemented correctly without the unknown fact, that fact
should not block the child.

If correct implementation or verification genuinely depends on the unknown
fact, treat it as a real prerequisite or blocker.

Do not replace unknown information with:

- guesses;
- placeholder decisions;
- development values;
- test values;
- examples;
- library defaults;
- assumed provider behavior.

---

## Preserve The Entire Parent Scope

The intake must account for the complete parent engineering scope.

Every parent-level work area must have exactly one clear destination unless an
intentional shared dependency is explicitly explained.

Do not:

- lose work during the split;
- assign the same implementation responsibility to multiple children;
- quietly move parent work into an unrelated future area;
- call blocked work complete.

The intake should prove that the parent has been divided without hidden gaps or
accidental overlap.

---

# 1. What Needs To Be Decided

Begin by explaining what decision this intake is making and why the parent work
requires that decision before implementation proceeds.

Then identify:

- the parent engineering work being evaluated;
- the reason its execution shape must be decided.

Keep this section short.

The reader should finish this section understanding:

```text
What are we deciding about this parent, and why does that decision matter?
```

Do not include:

- drafting history;
- previous rejected structures;
- correction history;
- workflow narration;
- implementation design.

---

# 2. What We Know

Begin by explaining that this section contains only the technical facts,
dependencies, decisions, and unknowns that materially affect whether the parent
should execute as one pass, be split, or be blocked.

Then include only information that changes the execution decision.

Relevant information may include:

- current system or source behavior;
- parent scope;
- approved technical decisions;
- completed prerequisites;
- technical dependencies;
- external dependencies;
- meaningful implementation boundaries;
- material unknowns;
- real blockers;
- facts that require a different verification environment.

Do not produce a general architecture summary.

Do not include information simply because it is related to the parent.

Every fact should answer:

```text
Why does this affect how the parent should be executed?
```

A compact table may be used when it improves clarity:

| Topic | Current fact or constraint | Why it affects execution |
|---|---|---|
| `[Relevant area]` | `[Current fact, decision, dependency, or unknown]` | `[Effect on whether/how the work can execute]` |

Do not claim external production, provider, runtime, account, deployment,
backup, access, or operational facts from repository source alone.

Exact authority citations and workflow references belong in `Internal Record`
unless the reader needs them to understand the engineering decision.

---

# 3. Execution Decision

Begin by explaining that this section states the chosen execution shape for the
parent and the technical reason that shape is appropriate.

Choose exactly one outcome:

- execute the parent as one pass;
- split the parent;
- blocked on a technical prerequisite;
- blocked on an owner or authority decision.

State the outcome directly.

Then explain the technical reason.

If the parent is split, provide only the executable order:

| Order | Work | Depends on |
|---|---|---|
| `1` | `[CHILD-ID - clear engineering title]` | `[Technical dependency or None]` |

The `Work` column must describe a coherent engineering or independent
verification result.

Do not turn this table into a miniature plan.

Do not include:

- implementation steps;
- detailed requirements;
- test plans;
- file lists;
- detailed settings;
- detailed failure behavior;
- evidence inventories.

After the table, explain only what is necessary to understand why the children
are separate and why the dependency order is correct.

For every proposed child, verify:

```text
Does this child leave behind a coherent result that can be accepted on its own?
```

If the answer is no, the split is probably artificial.

If two pieces must be completed together for either one to be correct, safe, or
useful, combine them.

---

# 4. Where The Parent Work Goes

Begin by explaining that this section accounts for the complete parent scope.

Its purpose is to show that every major parent responsibility has a destination
and that the split contains no hidden gaps or accidental overlap.

This is scope allocation, not implementation design.

Use:

| Parent work | Goes to | Remaining boundary |
|---|---|---|
| `[Parent-level engineering responsibility]` | `[Executable pass or named owner]` | `[What is fully covered here or intentionally outside this responsibility]` |

Keep rows at the parent-work level.

Do not decompose the parent into individual implementation details.

Good rows describe meaningful engineering responsibilities.

Avoid rows for individual:

- configuration values;
- functions;
- API fields;
- test cases;
- failure branches;
- formulas;
- implementation files.

Those belong in the executable pass plan.

`Remaining boundary` should explain only what is not included in that allocation
when clarification is necessary.

Do not use this column to narrate future implementation.

Blocked work remains blocked until its prerequisite is satisfied.

---

# 5. What Happens Next

Begin by explaining that this section identifies the next executable engineering
work and why it is ready to begin.

State:

- the exact next executable pass or parent work;
- why its technical prerequisites are satisfied;
- any real prerequisite or blocker that still prevents it from starting.

Keep this section about engineering readiness.

Do not describe the internal workflow sequence.

For example, prefer:

> `[PASS-ID] is the next executable work because its required source,
> decisions, and technical prerequisites are available.`

instead of:

> `[PASS-ID] can now proceed to Gate A.`

Exact workflow actions belong in `Internal Record`.

Do not include:

- preliminary requirement catalogs;
- test matrices;
- evidence matrices;
- artifact catalogs;
- detailed implementation design;
- repeated stop conditions already defined elsewhere.

The reader should finish this section knowing:

```text
What engineering work happens next, and is anything actually preventing it?
```

---

# 6. Internal Record

This section contains the production-readiness bookkeeping required to preserve
the intake decision and route the workflow correctly.

Unlike sections 1 through 5, exact framework terminology is allowed here.

Keep bookkeeping here rather than leaking it into the engineering narrative.

Include only metadata the workflow actually needs, such as:

- parent ID;
- intake outcome;
- accepted baseline;
- intake path;
- authority references;
- execution-register state;
- approved prerequisite or decision references;
- child IDs and order;
- proposed canonical plan path;
- proposed requirement artifact location;
- proposed test or verification location;
- blockers;
- exact next workflow action.

Use a table when exact values are easier to review:

| Detail | Value |
|---|---|
| Parent pass | `[PASS-ID - title]` |
| Intake outcome | `[execute parent / split / blocked on prerequisite / blocked on owner-authority decision]` |
| Accepted baseline | `[Accepted baseline SHA or equivalent]` |
| Intake path | `docs/production-readiness/planning/passes/<family>/<parent-id>-intake.md` |
| Authority sources | `[Relevant authoritative sources]` |
| Execution-register state | `[Current accepted state relevant to the parent]` |
| Approved decisions and prerequisites | `[Relevant decisions and completed prerequisites / None]` |
| Child order | `[PASS-A -> PASS-B -> PASS-C / Not applicable]` |
| Proposed canonical plan path | `[Path for next executable work / Not applicable]` |
| Proposed requirement declaration | `[Path / Not applicable]` |
| Proposed trusted test or verification location | `[Path / Not applicable]` |
| Blockers | `[Actual blockers / None]` |
| Exact next allowed action | `[Exact workflow action]` |

Do not duplicate the engineering explanation from sections 1 through 5 here.

This section records the decision; it does not redesign it.

---

# Final Author Check

This section is for the intake author.

Do not copy it into the completed intake.

Before reporting the intake ready, reread the entire document.

## Reader Understanding

Verify that:

- sections 1 through 5 are understandable without prior chat history;
- sections 1 through 5 are understandable without production-readiness
  framework knowledge;
- every reader-facing section explains what information it contains;
- every reader-facing section explains why that information matters;
- tables are introduced before the reader encounters them;
- the reader never has to infer why a section or table exists;
- internal workflow terminology is confined to `Internal Record` unless
  technically unavoidable.

## Execution Decision

Verify that:

- the intake clearly answers what executable engineering work should happen;
- the chosen outcome is one of the four allowed outcomes;
- the technical reason for the decision is explicit;
- a split exists only for genuine engineering reasons;
- dependency order is technically justified.

## Child Quality

For every child, verify that:

- it represents executable engineering or genuinely independent verification;
- it is not merely another planning layer;
- it is not merely preparatory documentation;
- it leaves behind a coherent independently acceptable result;
- work that must be correct together has not been split artificially.

## Parent Coverage

Verify that:

- every major parent responsibility has a destination;
- no parent responsibility disappeared during the split;
- implementation ownership does not accidentally overlap;
- intentional shared dependencies are clearly explained;
- blocked work is not represented as complete;
- allocation remains at parent-scope level rather than becoming implementation
  design.

## Relevance

Verify that every fact in sections 1 through 5 materially helps the reader
understand:

- the execution decision;
- the child boundaries;
- the dependency order;
- the parent allocation;
- the readiness or blocker for the next work.

Remove information that does not affect one of those things.

## Engineering Discipline

Verify that:

- unknown facts were not guessed;
- absent source behavior was not automatically converted into a separate child;
- detailed implementation design was not performed during intake;
- another planning-only child was not created;
- framework mechanics did not replace engineering reasoning.

## Safety And Sensitive Information

Verify that the intake contains no:

- credentials;
- credential-bearing URLs;
- secrets;
- private keys or tokens;
- prohibited private provider values;
- personal or payment data;
- raw sensitive logs;
- local machine paths;
- session-only state;
- internal chat material;
- other sensitive information that should not be committed.

After approval, freeze the intake according to the production-readiness
workflow.