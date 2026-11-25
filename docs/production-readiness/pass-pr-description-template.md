# PR Description Template

Use this template to write the final pull-request description from the PR base, the completed branch, and the final diff.

Write for a competent software engineer who has never worked in this repository.

## 1. PR Title

The title matches the pass's branch name: the same pass ID, a colon, and the
same page or pass name, written as a title instead of in lowercase with dashes.

```text
<pass ID>: <page or pass name>
```

| Pass type | Branch | PR title |
|---|---|---|
| Feature pass | `feature/F15-browse-games` | `F15: Browse Games` |
| Production launch pass | `production-launch/PL06-backend-api-and-http-foundations` | `PL06: Backend API and HTTP Foundations` |
| Production launch minor pass | `production-launch/PL06a-request-limits` | `PL06a: Request Limits` |

Do not use other forms such as `<pass ID> - ...`, `Implement <pass ID> ...`, or `Add <pass ID> ...`.

Non-pass repository-maintenance work may use an appropriate descriptive convention such as `Docs:` or `Program:`.

When producing the PR-body artifact, include only the two required sections defined below. This restriction applies only to the PR body. It does not replace any surrounding Gate D or workflow report requested by the user, such as the commit SHA, PR URL, publication result, blockers, or next action.

## 2. Required PR Body

Use exactly these sections:

```markdown
## Summary

...

## Changes

- ...
```

Do not add another PR-body section unless explicitly requested for that PR.

Use only as much text as the change requires. Do not add bullets to meet a quota, and do not compress distinct ideas merely to keep the description short.

## 3. Drafting Sources

Use:

- the PR base to establish the previous behavior;
- the final diff and completed branch behavior to establish what changed and the final result.

Plans, pass titles, requirement names, test filenames, directory names, and workflow reports may help locate relevant work, but they do not prove what the final implementation changed.

Do not make a claim unless the implementation supports it.

When the final implementation does not support a claim, omit the claim.

## 4. Drafting Process

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

### 4. Draft The Two Sections

Draft `Summary` and `Changes` from the primary change or unifying purpose and the concrete facts.

### 5. Review The Final Output

Review every sentence and bullet against the checklist near the end of this template.

Do not return the first draft when any check fails. Rewrite it until the complete PR body satisfies the checks.

## 5. Writing Rules

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

### Describe Things Instead Of Naming Code

Do not include API endpoint paths, table names, or column names. Describe what the endpoint, table, or column does.

Weak:

```text
Adds `GET /checkout/games/{game_id}/quote` and `game_participants.hold_expires_at`.
```

Clear:

```text
A new read-only price check shows the amount due before the player confirms, and added guests hold their spots for two minutes while their payment is pending.
```

A setting, command, or class name may appear only when its identity helps the reviewer locate the change. Explain its purpose in the same sentence when the purpose is not obvious.

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

## 6. Summary

The Summary explains the primary change or unifying purpose of the PR.

A pass PR contains everything its page or pass needed. Its Summary describes what the PR did overall, in general terms. Do not single out one change or list the changes.

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
- Gate reports;
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

## 7. Changes

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
- artifact hashes;
- staging or Git state;
- future owners or deferred follow-ups;

unless the PR itself materially changes that workflow mechanism.

Tests do not belong in Changes merely because tests were added.

Testing, CI, build, or deployment infrastructure belongs in Changes only when changing that infrastructure is itself a material part of the PR.

### Scope Clarification

A concise scope clarification may appear in `Changes` only when a reviewer could otherwise reasonably misunderstand the current PR.

Example:

```text
- Creates the shared background-job engine but does not add payment, refund, or notification handlers in this PR.
```

A scope clarification must explain the present engineering boundary.

It must not become roadmap bookkeeping, pass ownership, deferred-work tracking, or a general list of things not changed.

## 8. Final Review

Do not return the PR body until every applicable answer is yes.

1. Is the single primary change or unifying engineering purpose obvious after reading the Summary?
2. Does the Summary accurately compare the PR base with the completed branch?
3. Does the Summary state a practical consequence only when one materially exists?
4. Does the Summary avoid listing secondary mechanisms?
5. Can an engineer unfamiliar with the repository understand every phrase without opening the plan?
6. Do sentences use concrete actors or components, actions, and results?
7. Does every Changes bullet describe material behavior rather than a file, test, or process artifact?
8. Is the PR body free of endpoint paths, table names, and column names, and is any other exact name explained when its purpose is not obvious?
9. Is any scope clarification necessary, concise, and limited to the current PR boundary?
10. Are planning, Gate, requirement, evidence, Git, and acceptance bookkeeping excluded?
11. Are vague, duplicated, unsupported, exaggerated, or unnecessarily technical claims removed?
12. Is the amount of text appropriate for the actual change, without padding or excessive compression?
13. Does the PR body contain no sensitive information or local workstation details?
14. Does the Summary describe the whole PR without singling out one change?

If any applicable answer is no, rewrite the PR body before returning it.

## 9. Copyable Body

```markdown
## Summary

[Explain the relevant previous behavior and any material consequence, then state the primary result or unifying purpose of the PR.]

## Changes

- [Add one bullet for each distinct material change.]
```
