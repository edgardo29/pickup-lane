# Production-Readiness PR Description Template

## Purpose

This is the standard reviewer-facing PR description template for Pickup Lane
production-readiness passes. It helps each pass PR communicate the outcome,
material changes, validation, remaining boundaries, and reviewer focus without
turning the PR body into a Gate report, command log, testing record, branch
status report, pass plan, artifact inventory, or implementation diary.

PR descriptions must be concise and technically complete. Concise does not mean
omitting important technical information that a reviewer needs in order to
understand what changed and what was not claimed.

## Central Rule

Write the PR description from the actual diff and reviewer-facing outcome
outward, not from the pass plan, intake, Gate reports, testing record, execution
register, or approval workflow inward.

Reviewer-ready language is a correctness requirement. A PR description that is
technically accurate but requires production-readiness program knowledge to
understand is not acceptable and must be rewritten before publication.
Being understandable after interpretation is not enough. If the underlying
behavior can be stated directly and clearly, state the behavior directly
instead of naming the internal label for it.
Across the PR body, internal labels must not carry meaning that can be stated
as concrete application behavior. Before publication, rewrite any sentence or
bullet where the main label is an internal category instead of the
reviewer-facing fact. Internal labels may remain only when the same sentence
explains the concrete behavior and the label adds useful reviewer context.

Reviewer-ready sentences normally identify the actual actor, resource, action,
authorization condition, state, failure, safeguard, system behavior, or test
behavior. Standard engineering and product terms such as PostgreSQL, FastAPI,
authorization, API, database, transaction, middleware, cache, migration,
concurrency, Stripe, Firebase, and HTTP are fine when accurate. The problem is
internal shorthand that merely sounds technical while forcing the reviewer to
decode what actually happened.

Internal workflow-state terms such as accepted, approved, frozen, current pass
state, later-owner ownership, and closure state are usually not reviewer
information for implementation or test PRs. Translate or remove them unless the
workflow itself is the change. For example, prefer "repairs existing
chat-rate-limit tests" over "repairs accepted chat-rate-limit tests".

The PR body must be reviewer-complete, not process-complete. A true internal
fact does not belong in the PR body unless it helps a reviewer understand the
actual change, risk, validation, or material boundary. Internal planning
artifacts may be read to verify accuracy, but they are not PR-description
content unless changing those artifacts is itself the purpose of the PR.

Wording copied or closely paraphrased from pass plans, requirement
declarations, testing records, execution-register entries, Gate reports, or
internal validation summaries is not reviewer-ready by default. Extract the
underlying engineering fact and rewrite it in product, API, database,
authorization, test, or system language.

A fact being accurate does not automatically make it useful in a
reviewer-facing PR description.

Every section must be understandable to an engineer who has not read the
production-readiness documents. Internal terms may appear only when they are
genuinely necessary to review the change and are explained in ordinary
engineering language. An internal term is necessary only when it materially
helps the reviewer understand the actual diff and cannot be replaced by clearer
concrete engineering language without losing important meaning.

For example, prefer "users can retrieve only their own bookings and roster
entries" over "current-user booking and roster reads", "actions that hosts and
players are allowed to perform" over "host/player mutations", and
"unauthorized requests do not change bookings, roster membership, chat state,
or request state" over "rejected side effects". These are examples of the
decision rule, not a fixed glossary. The same rule applies to compressed
phrases such as "provider-payment input" when the actual protection is that
client-supplied provider or payment values cannot improperly affect protected
state.

## Evidence Language

Evidence language must match the proof that was actually collected.

When validation imports or inspects the application in local repository tests,
describe that as the current application, current source, or the route table
generated from the current FastAPI application. Do not describe local repository
inspection as live, deployed, production-verified, runtime-verified, or
real-world proof.

Use words such as live, deployed, production-verified, runtime-verified, or
real-world only when the PR actually includes the corresponding deployed,
production, runtime, provider, or external evidence. A local test importing the
application is not deployed proof.

## PR Title

Use this format:

```text
[PASS-ID]: [Plain-English outcome]
```

Examples:

```text
WS02-02: Revalidate runtime lifecycle and health contracts
WS02-03: Harden backend CORS and HTTP security boundaries
```

## Size And Shape

Use only as much space as the PR needs to communicate the change clearly and
completely to a reviewer. Keep the description concise, group related
information, avoid filler and repetition, and let the size of each section
follow the complexity of the actual change.

Completeness comes from grouping meaningful facts, not listing every artifact,
field, route category, requirement, downstream owner, or test mechanic.

## PR Body Sections

### Summary

Keep the Summary short enough to read quickly and complete enough to orient a
reviewer.

Start by explaining the real engineering problem or risk in ordinary language.
Write for a reviewer who has not read the pass plan or internal
production-readiness documents. The reader should understand what part of the
product or system is affected, what can go wrong, and why this work exists
before encountering internal terminology.

Then explain the high-level result and whether application, configuration,
data, provider, frontend, or runtime behavior changed. Technical terminology is
fine after its meaning is clear.

Do not:

- begin with a pass ID;
- begin with `This PR` unless it is genuinely the clearest sentence;
- start every Summary with the same product-name formula;
- lead with internal artifact names or production-readiness terminology;
- introduce pass IDs, requirement IDs, control IDs, Gate terms, child names,
  file paths, evidence states, or planning artifacts before the reader
  understands the underlying problem;
- turn the Summary into a compressed Changes list.

For example, prefer explaining that a change prevents client-supplied payment
information from being treated as proof of a real payment before describing the
change as "payment input ownership."

### Changes

Use grouped bullets sized to the actual change. Each bullet must describe a
meaningful reviewer-facing outcome, such as:

- a behavior change;
- an implementation outcome;
- a configuration change;
- a safeguard;
- an evidence result;
- a documentation outcome.

Describe every material behavior, configuration, test, evidence, or governance
change a reviewer needs to understand. Mention deliberately preserved behavior
when it matters.

Do not make individual files or internal artifacts the subject of bullets unless
the reviewer genuinely needs the location. When planning, requirement, testing,
or evidence artifacts need to be mentioned, group them concisely in
reviewer-facing language instead of enumerating them.

Do not enumerate schema fields, route-owner totals, requirement states, internal
pass structure, or internal ownership bookkeeping.

### Validation

Use grouped bullets sized to the validation story. Include only validation that
helps a reviewer judge confidence.

Every Validation statement must identify what kind of proof actually ran and
what scope it covered. Clearly distinguish focused pytest tests, affected
regression tests, full regression suites, static checks, compliance or policy
checkers, checks that map tests to the rules they verify, and specialized
database, browser, provider, migration, concurrency, or runtime evidence.

Describe validation by the application behavior or system area the reviewer
cares about before using internal pass, suite, matrix, checker, or test-system
terminology. Internal labels are supplemental, not substitutes for saying what
was tested. A bullet such as "Existing authorization-matrix tests: 11 passed"
normally fails because the reviewer still has to know what the matrix covers;
state the authorization behavior covered by those tests. A bullet such as
"WS03-04C authorization tests: 17 passed" normally fails when the same result
can be described through the game, booking, roster, chat, or Need-a-Sub
behavior tested. Keep an internal label only when it materially helps the
reviewer, and put it after the behavior instead of making it carry the meaning.

Validation follows the same reviewer-language rule as the rest of the PR body:
state the behavior or subsystem actually tested before introducing internal
suite, pass, checker, or mapping terminology. Internal checker or mapping terms
belong only when they give the reviewer useful confidence that cannot be stated
more clearly as the concrete verification performed. A checker name may remain
when its identity matters, but the bullet must still say what the checker
verified.

Every Validation bullet must answer: what concrete behavior or system property
does this result give the reviewer confidence in? If the bullet only identifies
a suite, matrix, checker, pass, mapping mechanism, or evidence category, it is
not reviewer-ready.

Validation bullets must report completed proof and its result. Do not add
bullets about tests that were not run, claims the PR is not making, compliance
with this template, or the absence of broader validation.

When a broader test suite was not run, omit the regression bullet. Explain the
omission only when it is materially important for the reviewer, using concrete
engineering language rather than a defensive disclaimer.

Useful validation includes:

- focused tests described by the product or system behavior they exercise;
- materially affected regression tests described by the behavior or subsystem;
- specialized PostgreSQL, browser, migration, provider-contract, concurrency,
  or runtime proof when applicable;
- checks that verify tests are linked to the rules they prove, when that
  materially helps the reviewer understand confidence in the change.

Compliance or policy checkers are not regression test suites. Do not describe a
checker as a regression result unless it actually executes regression tests.

Avoid vague phrases such as "broader validation passed", "backend test-standard
validation passed", "all checks passed", or "comprehensive validation passed"
unless the same statement immediately explains the actual proof and scope. Do
not imply that broad or full regression testing occurred unless it actually ran.
Do not use vague scope references such as "this workflow", "this scope",
"relevant tests", "applicable checks", or "broader validation". Name the actual
behavior, test area, checker, or evidence scope in ordinary engineering
language. Translate phrases such as "requirement mapping and traceability" or
"test-to-rule mapping checks" into what was verified, such as "the tests are
mapped to the authorization rules they verify."

Do not include compilation checks, Git checks, raw commands, checker node
counts, requirement-link counts, working-tree checks, publication mechanics, or
routine finalization checks.

Examples of routine internal checks that do not belong in normal PR
descriptions:

- `git diff --check`;
- `py_compile`;
- publication-safety review;
- local working-tree status;
- branch, baseline, artifact, or commit SHAs;
- no second PR created;
- auto-merge disabled;
- every checker scope as a separate bullet;
- exact pytest node lists;
- every command executed.

### Scope Boundaries

Use grouped bullets sized to the actual boundaries. State only the most
important behavior not changed, implemented, or proven. Identify material
external, deferred, or later-owned evidence in normal engineering language. Do
not falsely imply full control closure.

Describe remaining work in concrete product or system language. Avoid
process-oriented phrases such as "follow-up work", "follow-up review",
"evidence scope", "later-owned", "final closure", or "downstream proof" unless
their real engineering meaning is explained.

Do not reproduce pass decomposition, enumerate every later pass, enumerate every
external owner, copy the complete Not Part Of This Pass section from the plan,
or dump internal ownership bookkeeping. Do not list unrelated future domains
merely because they appear in the pass plan.

Translate specialized phrases such as export, unmask, read-audit, concealment,
or negative proof into concrete behavior a new developer can understand, or
omit them when they are not material to reviewing the diff.

Scope Boundaries must describe missing behavior, not internal closure state. Do
not rely on phrases such as "authorization behavior is not established here",
"owned later", "closed elsewhere", or "deferred" when the concrete system
boundary can be named. Prefer stating the product or system areas not covered,
such as administrator-only actions, sensitive data access, moderation behavior,
audit behavior, provider reconciliation, deployed-provider behavior, or
concurrent database race behavior.

### Reviewer Focus

This section is optional. Keep it brief and include it only when it helps review.

Use Reviewer Focus only for subtle implementation, compatibility, or review
points a reviewer could reasonably misunderstand while reviewing the diff.

Examples include:

- framework behavior that differs from application configuration;
- response classes intentionally excluded from generic middleware behavior;
- compatibility behavior that must remain unchanged;
- a narrow production change surrounded by broad evidence additions.

Do not use Reviewer Focus to explain pass structure, evidence architecture,
approval mechanics, downstream ownership, or information already stated
elsewhere. Remove this section when there is no meaningful reviewer focus.

## Unfamiliar Developer Standard

Every section, not only the Summary, must be understandable to an engineer who
has not read the production-readiness documents.

Unexplained phrases such as "route family", "behavioral proof",
"authorization dimensions", "concealment posture", "negative-proof owner",
"evidence scope", or "parent-gap disposition" must trigger a rewrite. An
internal term may appear only when it is genuinely necessary to review the
change and is explained in ordinary engineering language.

### Required Final Rewrite Pass

Before the final rejection check, perform a required rewrite pass:

1. Draft the PR body from the actual diff and validation.
2. Reread the complete draft specifically for internal, process, or abstract
   language.
3. Rewrite each sentence or bullet that can be stated as concrete product,
   API, database, authorization, test, or system behavior.
4. Only then apply the final publication/rejection check.

A useful sentence shape is:

```text
actual system noun + actual action + allowed/rejected/changed/preserved effect + why it matters to review
```

The PR body is a translation of the engineering work for a reviewer, not a
summary of the pass plan's vocabulary. Keep technical precision, but prefer the
product or system behavior over the internal label.

For each material sentence or bullet, ask:

- Does this identify a real product or system concept, actor, resource, action,
  or effect?
- Can an engineer who knows the application but not the production-readiness
  program understand it immediately?
- Am I naming the behavior, or am I naming our internal label for the behavior?
- Could this sentence be made clearer by replacing an abstract noun phrase with
  who does what to which resource and what happens?
- Does this primarily describe production-readiness process, test architecture,
  evidence bookkeeping, or internal state when the reviewer needs the
  underlying engineering behavior?
- Is an internal noun phrase being used where the actual behavior could be said
  directly?
- Is a pass ID, requirement ID, testing-system term, or planning term carrying
  meaning that should instead be expressed in normal engineering language?
- If an internal label remains, would removing it make the reviewer lose
  important technical information?

If the answer exposes avoidable internal language, rewrite before publication.
Prefer behavior such as:

- Instead of "source-derived lifecycle and state drift protection", prefer
  "tests fail when a new status is added without an explicit authorization
  rule".
- Instead of "default-deny lifecycle behavior", prefer "stale, invalid, and
  unauthorized states are rejected".
- Instead of "requirement traceability", prefer "the tests are mapped to the
  authorization rules they verify".
- Instead of "payment-input ownership", prefer "users cannot supply payment
  information that belongs to another user".
- Instead of "response-minimization", prefer "API responses do not expose
  protected fields".
- Instead of "test-to-rule mapping checks", prefer "checks confirm each test is
  linked to the authorization rule it verifies".
- Instead of "relationship-sensitive APIs", prefer "APIs where access depends
  on whether the user owns, hosts, has joined, or has requested access to the
  resource".
- Instead of "current-user relationship scoping", prefer "users cannot retrieve
  another user's bookings, roster entries, waitlist entries, or requests".

## Prohibited Content

Unless the PR specifically changes the workflow, planning, or governance system
itself, do not include:

- Stage or Gate narration;
- intake, frozen-plan, approval, or publication mechanics;
- execution-register acceptance mechanics;
- branch names;
- baseline SHAs;
- artifact SHAs;
- commit SHAs;
- exact changed-file inventories;
- file-by-file narration of planning and evidence artifacts;
- child-pass graphs;
- full downstream ownership maps;
- internal gap IDs;
- requirement-state inventories;
- control-ID inventories;
- matrix schema-field inventories;
- raw command logs;
- `git diff --check`;
- `py_compile`;
- checker node counts;
- requirement-link counts;
- Git status;
- staged-file status;
- PR-finalization checks;
- merge mechanics;
- local paths;
- usernames;
- workstation details;
- internal terminology such as `covered_elsewhere`, `negative proof`,
  `repository truth`, or `canonical plan` when normal engineering language
  communicates the meaning more clearly.

The narrow exception is when one of these subjects is itself the actual
reviewer-facing change, such as a workflow-documentation or governance PR. Even
then, describe the change in reviewer-facing language instead of dumping process
state.

## Writing Rules

PR descriptions must:

- use plain engineering language;
- make the Summary understandable without requiring the reviewer to read the
  pass plan first;
- explain the product or system meaning before introducing internal terminology,
  requirement IDs, or control IDs;
- vary sentence shape naturally instead of reusing stock openings across PRs;
- prefer concrete descriptions of behavior, risk, and outcome over abstract
  production-readiness language;
- preserve technical precision;
- explain uncommon internal terminology when it must be used;
- distinguish production changes from test, evidence, and documentation
  changes;
- distinguish current repository or application proof from live, deployed,
  provider, runtime, production, or other external evidence;
- label validation by the kind of proof that actually ran and the scope it
  covered;
- state important non-closure boundaries;
- group related facts instead of producing long repetitive lists;
- stay complete by grouping important information, not by hiding it;
- use requirement IDs only when they genuinely help the reviewer;
- translate internal states such as `covered_elsewhere` or `deferred` into
  understandable reviewer-facing language when those states must be mentioned;
- avoid Gate narration, implementation diary language, and internal agent
  workflow details;
- avoid unsupported claims, including claims that imply stronger evidence or
  broader validation than the PR actually collected;
- avoid secrets, credentials, private URLs, provider-private identifiers,
  personal data, payment data, local paths/usernames, workstation details, and
  internal chat history.

## Final Rejection Check

Before publication, reject and rewrite the PR description unless every answer
below is YES:

1. Can an engineer unfamiliar with the production-readiness program understand
   the Summary?
2. Does every Changes bullet describe a meaningful reviewer-facing outcome
   rather than merely naming a file or artifact?
3. Is Validation a confidence summary rather than a command log?
4. Are Scope Boundaries grouped by real system behavior rather than internal
   pass ownership?
5. Are Gate details, SHAs, file inventories, internal state dumps, and Git
   mechanics absent?
6. Is uncommon internal terminology translated into normal engineering language
   or removed?
7. Does the body use only as much space as needed, without filler, repetition,
   or avoidable internal detail?
8. Does the description distinguish current repository/application evidence
   from live, deployed, provider, runtime, production, or other external
   evidence?
9. Does Validation accurately distinguish tests, regressions, checkers,
   traceability, and specialized proof?
10. Does any wording avoid implying broader validation than actually ran?
11. Does every Validation bullet report proof that actually ran and a concrete
    result, rather than explaining what was not run or what the PR does not
    claim?
12. Are remaining boundaries concrete, relevant to the diff, and understandable
    without knowing the pass structure?
13. Can a developer unfamiliar with the production-readiness program understand
    every uncommon term in the complete PR body?
14. Does the body contain no secrets, credentials, private URLs or identifiers,
    personal or payment data, local paths or usernames, raw sensitive material,
    internal chat history, or local session information?
15. Does every material sentence or bullet identify a concrete product or system
    concept, actor, resource, action, or effect?
16. Have internal pass IDs, requirement IDs, or production-readiness terms been
    removed or translated wherever they are not needed to preserve technical
    meaning?
17. Does every Validation bullet identify the behavior or subsystem tested
    before any internal suite, pass, matrix, checker, or requirement-mapping
    label?
18. Has every abstract noun phrase carrying behavior been replaced with the
    actor, resource, action, condition, or effect when that would be clearer?
19. Can the reviewer understand each protection or change without mentally
    translating an internal label into the underlying behavior?
20. Have pass IDs and internal test-system labels been removed wherever they
    can be removed without losing useful reviewer information?
21. Has every sentence that primarily described production-readiness process,
    test architecture, evidence bookkeeping, or internal state been rewritten
    when the reviewer actually needs the underlying engineering behavior?
22. For every internal label that remains, would removing that label make the
    reviewer lose important technical information?
23. Does every internal label that remains appear with concrete behavior that
    makes its reviewer value clear?

Do not publish a description that fails this check.

## Copyable Markdown Template

The placeholders below are examples, not fixed wording. Add, remove, or group
bullets as needed to describe every material reviewer-relevant fact. Remove
`Specialized proof` when it does not apply, and remove `Reviewer Focus`
entirely when there is no meaningful reviewer focus.

```markdown
## Summary

[Explain the real engineering problem or risk in ordinary language so a
reviewer can understand the context without reading the pass plan.]

[Explain the high-level result and whether application or runtime behavior
changed.]

## Changes

- [Grouped material behavior, implementation, configuration, safeguard,
  evidence, or documentation outcome]
- [Grouped material reviewer-facing outcome]
- [Important behavior deliberately preserved, when relevant]

## Validation

- [Concrete behavior or system property verified, before any internal suite
  label]:
  [result]
- [Affected existing behavior or subsystem tested]: [result]
- [Compliance or static check and what it verified, when reviewer-relevant]:
  [result]
- [What the mapping check verified, when reviewer-relevant]:
  [result]
- [Specialized database, browser, provider, concurrency, migration, or runtime
  proof, when applicable]: [result]

## Scope Boundaries

- [Concrete product or system behavior not changed, implemented, or proven]
- [Live, deployed, provider, production, or runtime evidence not collected,
  stated in ordinary engineering language]
- [Material future behavior still needing proof, without relying on pass
  structure or unexplained internal terms]

## Reviewer Focus

- [Optional subtle implementation or compatibility contract]
```
