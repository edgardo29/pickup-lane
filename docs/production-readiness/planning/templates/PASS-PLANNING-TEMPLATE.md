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
When an applicable requirement or required external evidence must remain open beyond this
pass, preserve the specific outstanding work and completion conditions as
explained in Section 1. This narrow exception does not authorize a history of
future passes or general project tracking.

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

The plan should focus on the resulting behavior. Do not omit recorded
outstanding requirements or external evidence that determine which parts of
that result can honestly be called complete.

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
- test-certification language;

when ordinary engineering language says the same thing more clearly.

Do not make the reader translate process terminology into engineering meaning.

---

## Include Only Necessary Engineering

A missing feature, possible improvement, common best practice, framework
capability, or technically interesting safeguard does not automatically belong
in the pass.

Introduce a new mechanism only when it is:

1. required by the selected engineering scope; or
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
the source and resolve it before finalizing the plan. Resolve conflicts about
what is required through the applicable requirement sources. Inspect accepted
repository behavior and the current branch change set to understand existing
implementation, compatibility, consequences, and mismatches. Existing behavior
does not create a requirement merely because it exists, and current branch
changes are unaccepted proposals that do not create requirements. Choose one
coherent approach when the remaining choice is ordinary engineering. If the
resolution genuinely requires an unavailable product, security, policy, or
operational decision, stop and identify the exact decision rather than leaving
it for implementation.

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

Do not mechanically fill a generic engineering checklist. For every affected
set of operations, outcomes, states, configuration fields, database elements,
policy rules, diagnostics, or other applicable items, account for every member
in the appropriate requirements, design, failure, or testing section. Include
members intentionally unchanged or inapplicable, with their actual treatment
and reason. Group identical treatments only when every member is identified;
do not add unrelated input combinations merely to increase the number of cases.

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
- staging mechanics;
- approval mechanics;
- publication mechanics;
- execution-register mechanics;
- file allowlists;
- predicted file lists;
- implementation-area lists;
- final changed-file inventories;
- Git-boundary bookkeeping.

Those belong in supporting workflow artifacts when required.

An outstanding requirement or required external evidence is not
unnecessary administration when it limits what this pass can complete. Retain
its necessary engineering consequences and the recorded responsibility and
completion conditions without adding requirement-ID tables or copying the
execution register into the plan.

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

If the selected scope leaves mandatory work or external evidence outstanding,
identify the exact unfinished requirement or external fact, its recorded responsible
pass or owner, the prerequisite or trigger, and the latest required completion
point. State why the current pass can finish safely while it remains open; if
current correctness depends on that missing work, treat it as a blocker instead.
Keep this account brief and do not present outstanding work as completed or
verified.

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

For each affected operation and each materially distinct outcome, state the
required result and any result or side effect that must not occur. Account for
every member of each affected set, including unchanged or genuinely
inapplicable members, with an explicit treatment and reason. Include affected
configurations, database elements, policies, diagnostic outputs, states, and
interfaces when they are part of the selected scope. Shared implementation does
not imply identical required behavior for every operation that uses it. Group
members only if each is named and the shared treatment is unambiguous. Put
implementation details in Design and verification details in Testing.

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

For each applicable requirement, explain how the design treats every affected
operation and its related callers, consumers, configuration, persisted data,
policy rules, and diagnostics. Define relevant state changes, required and
prohibited effects, failure handling, retries, recovery, concurrency, and
timing where they affect correctness. When operations share a helper or service,
check and describe the required result for each operation rather than assuming
the helper makes their behavior identical. Every applicable requirement must have
an executable design; do not leave implementation to decide an unspecified outcome or
invent a necessary technical rule.

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

Cover every applicable, materially distinct failure or boundary outcome for
the affected operations, including malformed or incomplete external responses,
unknown outcomes, partial progress, cancellation, recovery, retries,
transaction uncertainty, concurrent operations, and time boundaries when
relevant. Specify the required behavior and prohibited side effects of each
case. Do not treat a shared error handler as verification that every calling operation
has the correct response. Do not require arbitrary combinations of unrelated
conditions; record normal behavior in the requirements or design sections.

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

Testing must follow directly from the requirements and design. For every
applicable requirement and each affected member, explain which appropriate
test, inspection, migration check, or other verification method will establish
its required behavior. Specify what the verification must establish, including
persisted effects and the absence of prohibited effects when those determine correctness.
Existing tests may supply the verification when adequate; do not require duplicate
tests or list predicted test filenames.

If necessary verification genuinely depends on recorded later work or external
facts, distinguish it from verification this pass can execute and preserve the
recorded owner, trigger, and completion condition in Section 1. Do not claim a
planned, unrun, unavailable, or deferred verification method is complete.

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
- staging mechanics;
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
pass is complete. Include the required behavior and verification outcomes of
the current pass without copying every requirement verbatim. If recorded
obligations or external evidence remain open, keep them visibly outstanding
under the boundary recorded in Section 1. A checklist item must not imply the
current pass proved them or require another pass to finish before this pass can
reach its separately recorded completion point.

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

Before declaring the plan ready, reread the entire current plan and complete
the Gate A self-review required by Sections 7.1 and 7.2 of the implementation
workflow. Check every applicable requirement and every member of each affected
set, with its expected behavior, design, failures, compatibility, and planned
verification. Then perform a **separate omission-focused pass** over the entire plan:
look for missing related operations or consumers, configuration or database
elements, policy or diagnostic behavior, failure and recovery cases, retries,
concurrency, unknown outcomes, unresolved engineering choices, and verification that
would not actually establish a required effect or prohibited side effect. Do
not stop this check after fixing the first few problems.

Before declaring the plan ready, verify that:

- a competent developer can understand it without production-readiness process
  knowledge;
- every section explains its purpose;
- the heading hierarchy is easy to scan;
- technical detail has context before it;
- failures are individually numbered and organized;
- no unnecessary jargon remains;
- no unnecessary future-pass narration remains beyond the concise, recorded
  outstanding obligations needed to state the current pass's honest scope;
- outside-scope material is not repeated;
- every requirement is necessary;
- every applicable requirement and every affected member, including intentionally
  unchanged or genuinely inapplicable members, has explicit planned treatment;
- required behavior is consistent across requirements, design, failure cases,
  testing, and completion criteria, including related operations and outcomes;
- planned verification establishes every required result and prohibited side
  effect at an appropriate layer, with no necessary verification method left undefined;
- any recorded outstanding work or external evidence has its recorded owner,
  prerequisite or trigger, and latest completion point, and is not called proven;
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

Resolve every applicable omission found by these two checks before submitting
the complete plan for its separate, fresh independent Gate A review. The plan
author or correction run must not approve its own plan. If correct implementation
requires materially changing the applicable requirements, technical design, or
executable scope, route the issue through the appropriate Gate A planning or
Stage 0 decision instead of silently redesigning work during implementation.
