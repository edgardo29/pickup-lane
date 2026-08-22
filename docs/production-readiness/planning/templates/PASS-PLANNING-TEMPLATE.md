# [PASS ID] - [Official Title]

[One plain-English sentence stating exactly what this pass designs, implements,
changes, removes, or verifies.]

This document is the engineering blueprint for this pass.

A competent developer should be able to read it without prior chat history or
knowledge of the production-readiness process and understand:

- what the work is;
- why it matters;
- what the finished behavior must be;
- how it should be implemented;
- what important failures and boundaries apply;
- how it will be tested;
- when it is complete.

Use normal engineering language.

Use precise technical terminology when it is the correct terminology of the
system. Do not invent formal-sounding internal language when ordinary
engineering language is clearer.

Human-readable does not mean technically shallow. Include every technical detail
genuinely required to implement the work correctly.

The instructions in this template are for the plan author. Do not copy them into
the completed plan.

---

# Universal Authoring Rules

## Orient The Reader

Every major section must begin with a short explanation of:

1. what the section contains;
2. why it matters to this pass;
3. how the developer should interpret what follows.

Do the same for a technical subsection when its purpose is not immediately
obvious.

Do not drop the reader directly into requirements, formulas, failure cases,
tests, or dense technical mechanics without first establishing their purpose.

Keep these introductions short and specific to the actual pass.

---

## Keep The Document Easy To Scan

Main sections use numbered level-two headings:

```text
## 1. ...
## 2. ...
## 3. ...
```

Meaningful subsections use hierarchical numbering:

```text
### 2.1 ...
### 2.2 ...

### 3.1 ...
### 3.2 ...
```

Use deeper heading levels only when the engineering genuinely requires them.

A developer scanning only the headings should understand the structure of the
plan.

Keep paragraphs reasonably short and separate distinct concepts with
whitespace.

Use descriptive headings.

Do not create headings merely to make the document look more structured.

Do not use bold text as a substitute for proper headings.

Use code blocks only when literal formatting matters, such as code, commands,
formulas, schemas, or exact configuration structures.

Do not put ordinary explanatory prose inside code blocks.

---

## Focus On This Pass

Describe the engineering being performed now.

Do not narrate:

- planning history;
- workflow stages;
- approvals;
- handoffs;
- future passes;
- evidence administration;
- publication mechanics;
- tracking mechanics.

Do not justify current engineering by explaining what another pass will
eventually do with it.

Explain the current engineering reason.

Work outside the pass should be mentioned only when necessary to make the scope
boundary clear.

State that boundary concisely. Do not repeat it throughout the document.

---

## Describe The Resulting System

Write primarily in terms of what the system should do when this pass is
complete.

Do not organize the plan around statements such as:

- something is missing;
- something will be needed later;
- something prepares future work;
- something will eventually be verified.

A current deficiency may be mentioned briefly when it helps explain why the
work exists.

The plan should focus on the resulting behavior.

---

## Use Plain Engineering Language

Use established technical terminology when it carries real meaning.

Do not invent jargon merely to make the plan sound rigorous.

Avoid unnecessary internal wording such as:

- source-owned;
- repository-owned;
- non-closure;
- handoff;
- evidence boundary;
- provider-fact boundary;
- trusted evidence;

when ordinary engineering language says the same thing more clearly.

Do not make the reader translate process terminology into engineering meaning.

---

## Include Only Necessary Engineering

A missing feature, possible improvement, common best practice, framework
capability, or technically interesting safeguard does not automatically belong
in the pass.

Introduce a new mechanism only when it is:

1. required by the approved engineering scope; or
2. necessary to satisfy a requirement of this pass.

Every new setting, component, abstraction, dependency, validation rule,
permission boundary, state, retry, timeout, safeguard, or other mechanism must
have a concrete engineering reason.

Do not add something because it might be useful later or makes the design appear
more complete.

---

## Resolve Questions The Repository Can Answer

The plan must contain an executable design.

If current repository source can answer an important design question, inspect
the source and resolve it before finalizing the plan.

Do not leave implementation with unnecessary alternatives such as:

```text
If X is true, do this.
Otherwise, do that.
```

when current source can establish which case actually applies.

If correct implementation genuinely depends on information that is unavailable,
state the issue clearly instead of guessing.

---

## Do Not Guess

Do not invent unknown values, external facts, architecture, or requirements.

If an unknown fact is not needed for the current implementation, leave it
unknown.

If the system can correctly remain configurable, define the required behavior
without inventing the eventual value.

If correct implementation genuinely depends on unavailable information, treat
that as a blocker.

Do not substitute:

- guesses;
- example values;
- development values;
- test values;
- CI values;
- documentation examples;
- framework defaults;
- library defaults;

for facts that are not actually known.

---

## Preserve Necessary Technical Depth

Include whatever technical detail the current pass genuinely needs.

That may include, when relevant:

- architecture;
- invariants;
- lifecycle;
- configuration;
- validation;
- calculations;
- limits;
- data and state;
- permissions;
- security;
- transactions;
- rollback;
- concurrency;
- locking;
- ordering;
- idempotency;
- retries;
- timeouts;
- migrations;
- compatibility;
- failure handling;
- recovery;
- integrations;
- deployment behavior;
- observability;
- performance;
- testing.

Include only what actually applies.

Do not mechanically fill a generic engineering checklist.

---

## Do Not Repeat Yourself

Give each important fact one primary home:

- `What This Work Does` explains the work and its boundary.
- `What Must Be True` defines required outcomes.
- `Design` explains implementation.
- `Failures And Edge Cases` defines abnormal behavior.
- `Testing` explains verification.
- `Done When` defines completion.

Repeat information only when the new context adds something useful.

Remove repeated scope disclaimers, repeated test limitations, repeated future
work, and repeated explanations of the same requirement.

---

## Keep Process Administration Out

The completed engineering plan must not contain:

- requirement-ID tables;
- stable-ID sections;
- evidence classifications;
- evidence-management language;
- checker administration;
- staging mechanics;
- traceability-generation mechanics;
- approval mechanics;
- publication mechanics;
- execution-register mechanics;
- file allowlists;
- predicted file lists;
- implementation-area lists;
- final changed-file inventories;
- Git-boundary bookkeeping.

Those belong in supporting workflow artifacts when required.

The engineering plan contains only information that helps a developer
understand, implement, test, or complete the work.

---

## 1. What This Work Does

Begin by explaining what part of the system this pass addresses, why the work
matters, and what result it produces.

Then describe:

- the relevant existing behavior;
- what this pass establishes, changes, removes, or verifies;
- important behavior that remains unchanged;
- the major engineering boundary.

Keep this section concise.

If important related work is outside the pass, state that boundary once here in
plain language.

Do not describe how that other work will be performed later.

---

## 2. What Must Be True

Begin by explaining what these requirements represent and why they define
success for the pass.

Then state the required engineering outcomes.

Use meaningful numbered subsections when they improve readability:

```text
### 2.1 [Requirement Area]
### 2.2 [Requirement Area]
```

Use direct, readable, testable statements.

Describe what the system must do.

Do not include implementation procedure unless a particular mechanism is itself
a required technical constraint.

Do not include:

- requirement IDs;
- tracking matrices;
- workflow requirements;
- evidence requirements;
- publication requirements;
- responsibilities belonging to other work.

Machine-readable artifacts may assign identifiers separately. They must preserve
the engineering meaning defined here.

Every requirement must be necessary to this pass.

---

## 3. Design

Begin by explaining the design's overall approach and how it satisfies the
requirements above.

Then organize the design into meaningful numbered technical areas:

```text
### 3.1 [Design Area]
### 3.2 [Design Area]
### 3.3 [Design Area]
```

Choose the subsections based on the actual engineering work.

Do not mechanically create generic categories.

For each design area, explain only what the developer needs, such as:

- why it matters;
- how it works;
- components involved;
- configuration;
- validation;
- lifecycle;
- calculations;
- data or state;
- permissions;
- security boundaries;
- compatibility;
- important technical tradeoffs.

Every new mechanism must have a concrete reason tied to a requirement.

Do not introduce speculative engineering.

Do not leave repository-answerable questions unresolved.

Preserve existing behavior concisely where needed rather than creating a large
section that repeats the overview and requirements.

When a formula, state model, security boundary, integration contract,
transaction rule, or other technical structure matters, explain why it matters
before presenting its details.

---

## 4. Failures And Edge Cases

Begin by explaining which abnormal or boundary situations matter and what
correct handling protects against.

Present each case as a numbered item:

```markdown
1. **[Descriptive case name]**
   - **Condition:** [What triggers the case.]
   - **Required behavior:** [What the system must do.]
```

Each item must represent a real exceptional or boundary condition.

Do not add normal lifecycle events simply to make the section longer.

Do not include:

- workflow failures;
- documentation mistakes;
- evidence problems;
- approval states;
- publication states;
- status of other work.

Do not place the entire section inside a code block.

---

## 5. Testing

Begin by explaining what testing must prove about the engineering in this pass.

Use numbered subsections when materially different testing areas exist:

```text
### 5.1 [Test Area]
### 5.2 [Test Area]
```

Testing must follow directly from the requirements and design.

Cover only relevant behavior, such as:

- normal operation;
- validation;
- important boundaries;
- failure handling;
- lifecycle;
- integrations;
- security;
- concurrency;
- compatibility;
- regression protection.

Be precise about what tests can and cannot establish.

If an important limitation exists, state it briefly once.

Do not include:

- exact test-file inventories;
- requirement-ID administration;
- checker execution;
- staging mechanics;
- traceability generation;
- evidence publication;
- approval mechanics;
- workflow reporting.

Do not end the section with a generic paragraph that merely repeats what the
testing subsections already said.

---

## 6. Done When

Begin by explaining that this section defines the engineering completion bar for
the pass.

Then provide a concise Markdown checklist:

```markdown
- [ ] [Concrete engineering completion condition]
```

Every item must represent something that genuinely has to be true before this
pass is complete.

Prefer engineering outcomes over incidental implementation details.

Do not include:

- future work;
- another pass's completion;
- repeated scope disclaimers;
- evidence publication;
- tracking updates;
- approval mechanics;
- workflow bookkeeping.

Do not repeat every requirement word for word. Summarize the actual completion
conditions.

---

# Final Author Check

This section is for the plan author only. Do not copy it into the completed
plan.

Before declaring the plan ready, verify that:

- a competent developer can understand it without production-readiness process
  knowledge;
- every section explains its purpose;
- the heading hierarchy is easy to scan;
- technical detail has context before it;
- failures are individually numbered and organized;
- no unnecessary jargon remains;
- no future-pass narration remains;
- outside-scope material is not repeated;
- every requirement is necessary;
- every new mechanism has a concrete engineering reason;
- unknown facts were not guessed;
- repository-answerable design questions were resolved;
- requirements, design, testing, and completion criteria are not unnecessarily
  duplicating each other;
- no requirement-ID tables, workflow administration, file predictions, or Git
  inventories appear;
- no paragraph exists merely because the document would otherwise look less
  comprehensive;
- nothing has been retained merely because an earlier version contained it;
- no credentials, credential-bearing URLs, secrets, private keys, prohibited
  private provider values, personal/payment data, raw sensitive logs, or other
  protected information appear.

If correct implementation requires materially changing the approved
requirements or design, return to planning rather than silently changing the
engineering contract.