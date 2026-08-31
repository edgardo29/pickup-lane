# PR Description Template

Use this template to write the final pull-request description from the PR base, the completed branch, the final diff, and the validation that actually ran.

Write for a competent software engineer who has never worked in this repository.

When producing the PR-body artifact, include only the three required sections defined below. This restriction applies only to the PR body. It does not replace any surrounding Gate D or workflow report requested by the user, such as the commit SHA, PR URL, publication result, blockers, or next action.

## Required PR Body

Use exactly these sections:

```markdown
## Summary

...

## Changes

- ...

## Validation

- ...
```

Do not add another PR-body section unless explicitly requested for that PR.

Use only as much text as the change requires. Do not add bullets to meet a quota, and do not compress distinct ideas merely to keep the description short.

## Sources Of Truth

Use:

- the PR base to establish the previous behavior;
- the final diff and completed branch behavior to establish what changed and the final result;
- the actual tests, checks, testing record, and recorded execution results to establish what was validated.

Plans, pass titles, requirement names, test filenames, directory names, and workflow reports may help locate relevant work, but they do not prove what the final implementation changed or validated.

Do not make a claim unless the implementation or executed validation supports it.

When the available evidence does not support a claim, omit the claim.

## Drafting Process

Complete these steps before returning the PR body.

### 1. Identify The Primary Change Or Unifying Purpose

Privately identify either:

- the single primary change; or
- for an intentionally multi-part PR, the single engineering purpose that unifies the material changes.

Use this form:

```text
[Main component or area] now [does what] so [practical result].
```

Center the Summary on that result or purpose.

Put supporting mechanisms and secondary behavior in `Changes`.

Do not output this private sentence.

### 2. Establish The Concrete Facts

Privately identify:

```text
BEFORE
What did the PR base do, allow, prevent, omit, or represent?

CONSEQUENCE
What practical consequence existed, when one materially existed?

AFTER
What does the completed branch now do differently?

SUPPORTING CHANGES
Which material changes in the final diff produce that result?

VALIDATION
Which scenarios were actually exercised, and what observable result occurred?
```

A practical consequence is not mandatory when none materially exists.

Never invent or exaggerate impact merely to make the Summary sound more important.

For a small maintenance, documentation, configuration, or mechanical PR, the relevant fact may simply be that something was inaccurate, inconsistent, outdated, difficult to reproduce, or no longer aligned with repository behavior.

Do not output this private fact list.

### 3. Translate Technical Wording

Before drafting, translate repository-specific, implementation-specific, testing, infrastructure, or specialist terms into the behavior they represent.

Use this private form:

```text
candidate phrase
-> what it actually means in this PR
-> reviewer-facing wording
```

Do not output the translation list.

### 4. Draft The Three Sections

Draft `Summary`, `Changes`, and `Validation` from the primary change or unifying purpose and the concrete facts.

### 5. Run The Final Output Gate

Review every sentence and bullet against the checklist near the end of this template.

Do not return the first draft when any check fails. Rewrite it until the complete PR body passes.

## Writing Rules

### Use Actor, Action, And Result

Prefer sentences that identify:

1. who or what acts;
2. what it does;
3. what result that produces.

Weak:

```text
Adds durable-job lifecycle safeguards.
```

Clear:

```text
Pickup Lane stores background work in PostgreSQL, and workers temporarily claim each job so unfinished work can be recovered after a crash.
```

Weak:

```text
Improves authorization boundaries.
```

Clear:

```text
The API rejects the operation unless the current user is an active administrator.
```

Weak:

```text
Improves form resilience.
```

Clear:

```text
The form keeps the user's entered values after a failed submission so the user can correct the error without entering everything again.
```

For concurrency, retries, recovery, or state changes, describe the concrete event sequence.

Weak:

```text
Prevents a lease race.
```

Clear:

```text
When two workers try to claim the same job, PostgreSQL gives the job to one worker and prevents the other from claiming that same row.
```

### Describe Behavior, Not Labels

A technically correct term is not sufficient when it names a category but hides what the system actually does.

| Do not stop at | Explain the behavior |
|---|---|
| `job lifecycle` | Describe how a job moves from waiting, to being processed, to success, retry, cancellation, or permanent failure. |
| `authorization boundary` | State which user or role may perform the action and what happens when authorization fails. |
| `schema drift check` | State that migrations are checked to produce the tables, columns, indexes, and constraints expected by the application. |
| `request hardening` | State which invalid request, unsafe behavior, timeout, or failure is now rejected or handled. |
| `state reconciliation` | State which records are compared and how conflicting or incomplete state is corrected. |
| `configuration validation` | State which required value is checked and what happens when it is missing or unsafe. |
| `UI resilience` | State which user input or screen state is preserved after a failure. |
| `deployment safety` | State which build, startup, shutdown, or rollout behavior is now enforced. |
| `documentation alignment` | State which instructions, commands, paths, or examples now match the repository. |

These examples demonstrate the expected transformation. They are not an exhaustive prohibited-word list.

Standard technology and product names such as PostgreSQL, Alembic, FastAPI, React, Stripe, Firebase, or Cloudflare R2 may remain when their identity helps explain the change.

A technology name must not replace the explanation of what it does in this PR.

### Avoid Compressed Shorthand

Do not make the reviewer unpack dense noun phrases or slash-separated labels.

Avoid wording such as:

```text
value/default/SQL-safety behavior
provider/runtime proof
connection/session lifecycle
model/schema agreement
role/grant verification
retry/recovery contract
```

Write the concrete concepts in normal sentences.

Weak:

```text
Model/schema agreement was verified.
```

Clear:

```text
The database created by the migrations matched the tables, columns, indexes, and constraints defined by the application models.
```

Weak:

```text
Existing value/default/SQL-safety checks passed.
```

Clear:

```text
Existing checks for stored values, database-generated defaults, and parameterized SQL continued to pass.
```

### Use Exact Names Only When Helpful

An exact table, setting, command, endpoint, class, or configuration name may appear when its identity helps the reviewer understand or locate the change.

Explain its purpose in the same sentence when the purpose is not obvious.

Clear:

```text
Migration tests use `MIGRATION_DATABASE_URL` to connect to a separate PostgreSQL database instead of resetting the database used by ordinary backend tests.
```

Unclear:

```text
Adds `MIGRATION_DATABASE_URL` boundary validation.
```

### Do Not Overstate

Do not claim that the PR:

- fully solves a broader problem when it addresses only part of it;
- proves production behavior using only local or synthetic evidence;
- validates a scenario that was not actually exercised;
- changes behavior that appears only in a plan, requirement, or test name;
- preserves compatibility unless relevant compatibility checks actually ran;
- creates a practical benefit that is merely hypothetical.

### Protect Sensitive Information

Do not include:

- secrets or credentials;
- private provider values;
- personal or payment data;
- sensitive log content;
- local workstation paths;
- developer-specific environment details.

## Summary

The Summary explains the primary change or unifying purpose of the PR.

It should communicate:

- the relevant previous behavior or condition;
- the practical consequence, when one materially existed;
- the main result after the change.

Write one compact paragraph. Usually one or two clear sentences are enough, but clarity matters more than a fixed sentence count.

Do not summarize every Changes bullet.

A common structure is:

```text
[Concrete previous behavior and its material consequence, when applicable.]
[Main component now does what, producing which result.]
```

For maintenance, documentation, configuration, or mechanical work, do not invent a user-facing or production consequence. State the actual inconsistency or missing behavior and the resulting correction.

The Summary must be understandable without reading:

- the plan;
- the pass title;
- the testing record;
- requirement declarations;
- Gate reports;
- the execution register;
- internal documentation.

Do not include in the Summary:

- test counts or test-suite names;
- commands;
- CI or Git details;
- pass IDs, Gate names, or requirement IDs;
- planning, approval, evidence, or acceptance terminology;
- future or deferred work;
- rollout disclaimers;
- unnecessary configuration identifiers;
- a list of secondary implementation mechanisms.

Avoid vague statements such as:

```text
Improves reliability.
Adds safeguards.
Hardens the system.
Handles edge cases.
Improves production readiness.
```

Replace them with the actual behavior.

## Changes

The Changes section explains the material engineering behavior added, removed, or changed by the final diff.

Use one bullet for each distinct material change. Include only the bullets needed to explain the PR clearly.

Each bullet should:

- identify the relevant component or actor when useful;
- explain what it now does;
- state the practical result when it is not obvious;
- support the primary change or unifying purpose established in the Summary.

Changes may describe:

- application or API behavior;
- database behavior;
- background processing;
- authorization or security behavior;
- failure and recovery behavior;
- frontend or browser behavior;
- configuration and startup behavior;
- compatibility behavior;
- materially changed testing, build, or deployment infrastructure.

Do not merely inventory:

- files;
- functions;
- classes;
- migrations;
- tests;
- records;
- documentation artifacts.

Weak:

```text
Updates the worker service and job tests.
```

Clear:

```text
Workers renew ownership while a handler is running, preventing another worker from recovering the same job while the first worker remains healthy.
```

Do not create Changes bullets for:

- pass decomposition or acceptance;
- Gate state;
- requirement mapping;
- traceability or evidence bookkeeping;
- testing-record updates;
- execution-register state;
- artifact hashes;
- staging or Git state;
- future owners or deferred follow-ups;

unless the PR itself materially changes that workflow mechanism.

Tests do not belong in Changes merely because tests were added. Describe what they proved in `Validation`.

Testing, CI, build, or deployment infrastructure belongs in Changes only when changing that infrastructure is itself a material part of the PR.

### Scope Clarification

A concise scope clarification may appear in `Changes` only when a reviewer could otherwise reasonably misunderstand the current PR.

Example:

```text
- Creates the shared background-job engine but does not add payment, refund, or notification handlers in this PR.
```

A scope clarification must explain the present engineering boundary.

It must not become roadmap bookkeeping, pass ownership, deferred-work tracking, or a general list of things not changed.

## Validation

The Validation section explains what important behavior was actually exercised and what observable result occurred.

Use one bullet for each meaningful validation scenario. Include only the bullets needed to communicate the evidence clearly.

Each bullet should lead with the scenario or property, followed by what was exercised and what happened.

Use this form:

```text
[Scenario or property]: [what was exercised and what result was observed].
```

Examples:

```text
- Competing workers: two independent PostgreSQL sessions tried to claim the same job, and only one session obtained it.
```

```text
- Failed-job recovery: a worker stopped before recording completion, the lease expired, and another worker recovered the job without allowing the stale worker to update it.
```

```text
- Authorization failure: a non-admin user attempted the protected operation, and the API rejected it without changing the target record.
```

```text
- Form recovery: a failed submission displayed the server error while preserving the user's entered values.
```

Validation should cover the most important applicable areas, such as:

- the primary changed behavior;
- meaningful failure cases;
- retry or recovery;
- concurrency or ordering;
- invalid-state rejection;
- authorization failures;
- compatibility that could realistically regress;
- database, API, browser, provider, build, or integration behavior affected by the PR.

Do not infer validation from:

- the implementation;
- the plan;
- a requirement;
- a test filename;
- a related suite;
- intended behavior.

Only describe validation that actually ran and passed.

### Keep Changes And Validation Distinct

`Changes` explains what was implemented.

`Validation` explains which scenario was exercised and what happened.

Weak Validation:

```text
- Added lease renewal for active jobs.
```

Clear Validation:

```text
- Long-running work: a handler ran longer than its original lease while the worker renewed ownership, and another worker could not claim the job.
```

### Test Counts

Test counts are optional supporting information.

Lead with the proven behavior. Add a count afterward only when it helps communicate the breadth of the validation.

Preferred:

```text
- Fresh and older database states both reached the expected schema, interrupted runs recovered successfully, and overlapping runs remained isolated; 26 focused tests covered these scenarios.
```

Avoid:

```text
- 26 tests passed.
```

### Documentation, Configuration, And Mechanical Changes

Do not invent runtime validation for a PR that does not change runtime behavior.

For documentation-only work, describe the checks that actually ran, such as:

- links and referenced paths were verified;
- commands and examples were checked against current repository behavior;
- formatting or documentation-build checks passed.

A truthful validation bullet may state:

```text
- Documentation verification: referenced commands, paths, and examples were checked against the current repository; no runtime tests were applicable because runtime code did not change.
```

For configuration-only or mechanical work, describe the relevant checks that actually ran, such as:

- configuration parsing;
- startup rejection of missing or unsafe values;
- build output;
- generated-file consistency;
- repository-approved static checks.

### Exclude Process-Only Results

Do not use Validation bullets for:

- checker `PASS`;
- requirement mapping;
- traceability generation;
- testing-record completeness;
- `git diff --check`;
- Git status or staged state;
- Gate approval;
- artifact hashes;
- execution-register consistency;
- PR creation or finalization;

unless the PR materially changes the mechanism being checked.

## Final Output Gate

Do not return the PR body until every applicable answer is yes.

1. Is the single primary change or unifying engineering purpose obvious after reading the Summary?
2. Does the Summary accurately compare the PR base with the completed branch?
3. Does the Summary state a practical consequence only when one materially exists?
4. Does the Summary avoid listing secondary mechanisms?
5. Can an engineer unfamiliar with the repository understand every phrase without opening the plan?
6. Do sentences use concrete actors or components, actions, and results?
7. Does every Changes bullet describe material behavior rather than a file, test, or process artifact?
8. Are exact technical names explained when their purpose is not obvious?
9. Is any scope clarification necessary, concise, and limited to the current PR boundary?
10. Does every Validation bullet describe a scenario that actually ran and an observable result?
11. Does Validation lead with proven behavior rather than counts or commands?
12. Are Changes and Validation clearly different rather than repeated?
13. Are planning, Gate, requirement, evidence, Git, and acceptance bookkeeping excluded?
14. Are vague, duplicated, unsupported, exaggerated, or unnecessarily technical claims removed?
15. Is the amount of text appropriate for the actual change, without padding or excessive compression?
16. Does the PR body contain no sensitive information or local workstation details?

If any applicable answer is no, rewrite the PR body before returning it.

## Copyable Body

```markdown
## Summary

[Explain the relevant previous behavior and any material consequence, then state the primary result or unifying purpose of the PR.]

## Changes

- [Add one bullet for each distinct material change.]

## Validation

- [Add one bullet for each meaningful scenario or property that was actually checked.]
```