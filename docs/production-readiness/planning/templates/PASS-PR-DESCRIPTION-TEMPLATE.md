# PR Description Template

Use this template to produce the final pull-request description from the completed diff and the validation that actually ran.

The description must let a software engineer who is unfamiliar with this repository understand:

- the concrete reason the PR was needed;
- what the system now does differently;
- which material behaviors changed;
- what important behavior was actually proven.

The PR description explains the engineering change. It does not reproduce planning, approval, tracking, or evidence-management processes.

## Required output

Every PR description must contain exactly these three sections:

1. `Summary`
2. `Changes`
3. `Validation`

Do not add another section unless the owner explicitly requests one for that PR.

The PR description is invalid and must not be returned until it passes every mandatory check in this template.

## Source of truth

Use the following sources:

- the final diff for `Summary` and `Changes`;
- the actual testing record, tests, and recorded execution results for `Validation`;
- current repository behavior when needed to understand the effect of the diff.

Do not derive claims from:

- the pass title;
- planning-document wording;
- requirement names;
- test-directory names;
- workflow reports;
- what the implementation merely appears intended to do.

A plan describes intended work. It is not proof that the final implementation or validation achieved it.

## Required authoring process

Complete these steps before returning the PR description.

### 1. Extract the engineering facts

Privately identify:

- **Before:** the concrete problem, risk, limitation, or missing behavior;
- **Consequence:** what could fail, become incorrect, remain unverified, or become difficult because of that problem;
- **After:** what the system now does differently;
- **Material changes:** the meaningful behaviors changed by the diff;
- **Validation results:** the scenarios actually exercised and the observable results.

Do not output this private fact list.

### 2. Translate terminology into behavior

Before drafting, privately create a translation for every candidate phrase that may require implementation, repository, testing, infrastructure, or specialist context.

Use:

```text
candidate term
-> what it actually means in this PR
-> plain wording for the reviewer
```

Do not output this translation list.

Use the plain wording in the final PR description.

### 3. Draft the three sections

Draft `Summary`, `Changes`, and `Validation` from the extracted facts and translated wording.

### 4. Run the mandatory rejection checks

Review every sentence and bullet against the rejection checks in this template.

Do not return the first draft when any check fails. Rewrite it until every check passes.

## Plain-language output gate

A phrase is not acceptable merely because it is technically correct, common in the codebase, or familiar to specialists.

For every technical noun or shorthand phrase, ask:

> Could a competent software engineer who has never worked in this repository explain the actual behavior from this sentence alone?

If the answer is no, replace the term with what it actually means.

A term that names a category but hides the relevant behavior must be translated.

### Translation examples

These examples establish the expected transformation. They are not an exhaustive prohibited-word list.

| Do not stop at | Explain the behavior |
|---|---|
| `drift check` | checks that migrations create the tables, columns, indexes, and constraints expected by the application models |
| `migration graph check` | checks that migration revisions have no missing, duplicate, or conflicting dependencies |
| `migration rehearsal` | runs the real migrations against a controlled PostgreSQL database |
| `schema-history reset` | returns the migration database to an empty state or an earlier migration version |
| `fail closed` | rejects an unrecognized risky operation instead of accepting it |
| `advisory-lock serialization` | prevents two migration runs from changing the migration database at the same time |
| `interruption recovery` | checks what remains when a migration stops partway through and whether a later run can safely complete |
| `provider-independent` | does not depend on a specific hosting or database provider |
| `connection budget` | how many database connections the deployed system can safely use |
| `role/grant verification` | checks that database accounts have only the permissions they need |
| `boundary` | state exactly what is allowed, required, separated, or prevented |
| `contract` | state the actual behavior or rule being enforced |
| `lifecycle` | describe the relevant states or operations |
| `hardening` | describe the specific failure or unsafe behavior now prevented |

Standard technology and product names such as PostgreSQL, Alembic, FastAPI, Stripe, or Firebase may remain when their identity helps explain the change.

An exact technical name must never substitute for explaining its behavior.

## Summary

The Summary has one job:

**Explain the concrete reason the PR was necessary and the practical high-level result.**

Use one compact paragraph of no more than two sentences.

The normal structure is:

1. what was missing, incorrect, unsafe, or unverified and what consequence that created;
2. what the system now does differently.

The Summary must be understandable without reading:

- the plan;
- the testing record;
- requirement declarations;
- Gate reports;
- the execution register;
- internal documentation.

### Summary rules

The Summary must:

- state a concrete previous problem or missing capability;
- state the meaningful consequence of that problem when one exists;
- state the practical result after the PR;
- use behavior rather than internal labels;
- remain understandable to an engineer outside the repository.

The Summary must not include:

- test counts;
- test-suite names;
- commands;
- CI bookkeeping;
- validation details;
- pass IDs;
- Gate names;
- requirement IDs;
- execution or acceptance state;
- future work;
- deferred work;
- rollout disclaimers;
- things not changed;
- things not proven;
- configuration identifiers unless the exact identifier is essential to understand the result.

Do not write:

- improves reliability;
- strengthens validation;
- adds safeguards;
- hardens migrations;
- makes behavior safer;
- handles edge cases;
- improves production readiness;

unless the same sentence states the concrete problem and resulting behavior.

### Summary acceptance test

Do not return the Summary unless a reviewer can answer all four questions after reading it once:

1. What concrete problem or missing behavior existed?
2. What could that problem cause or prevent?
3. What does the system now do differently?
4. Why does this PR matter?

If any answer requires interpreting jargon or opening another document, rewrite the Summary.

## Changes

The Changes section has one job:

**Describe the material engineering changes in the final diff.**

Use three to seven bullets unless the actual diff genuinely requires fewer or more.

Each bullet must:

- describe one distinct material change;
- begin with what the system now does, requires, prevents, separates, records, or verifies;
- explain the behavior or engineering consequence;
- use an exact identifier only when its identity helps the reviewer.

### Changes rules

Describe:

- behavior changes;
- configuration behavior;
- database or migration behavior;
- security behavior;
- API behavior;
- failure handling;
- compatibility behavior;
- architectural separation;
- materially changed test or CI infrastructure when that infrastructure is itself part of the engineering change.

Do not merely inventory:

- files;
- classes;
- functions;
- tests;
- records;
- documentation artifacts.

Bad:

```text
Updates migration_test_database.py and the CI workflow.
```

Better:

```text
Uses a separate PostgreSQL database for migration tests so they can rebuild schema history without modifying the database used by ordinary backend tests.
```

### Exact identifiers

An exact name may appear when it materially helps the reviewer, but explain its purpose in the same bullet.

Acceptable:

```text
Requires migration tests to use the separate `pickup_lane_migration_test_db` database through `MIGRATION_DATABASE_URL`, preventing them from falling back to the ordinary backend test database.
```

Not acceptable:

```text
Adds `MIGRATION_DATABASE_URL` boundary validation.
```

### Exclude process bookkeeping

Do not create Changes bullets for:

- pass decomposition;
- pass acceptance;
- execution-register state;
- Gate state;
- requirement mapping;
- traceability;
- checker compliance;
- evidence records;
- artifact hashes;
- staging or Git state;
- future owners;
- deferred follow-ups;

unless that process mechanism is itself the material subject of the PR.

Do not include tests as Changes bullets merely because tests were added. Describe the tested behavior in `Validation`.

A testing or CI mechanism belongs in Changes only when the mechanism itself materially changes how the system is verified or isolated.

## Validation

The Validation section has one job:

**Explain what important behavior, failure case, compatibility boundary, or system property was actually proven.**

Use two to five bullets unless the validation genuinely requires a different number.

Every bullet must identify:

1. the scenario or property checked;
2. the observable result;
3. that the verification passed.

Use this structure:

```text
[Scenario or system property]: [what was exercised and what the observed result proved].
```

### Validation source of truth

Before writing Validation, inspect:

- the current testing record;
- the actual tests when needed to understand the scenario;
- the recorded results from validation that actually ran.

Do not infer a validation claim from:

- the implementation;
- the plan;
- a test filename;
- a requirement;
- a related suite passing;
- the intended behavior.

When the evidence does not establish a claim, omit it.

### Validation rules

Validation should describe:

- direct changed behavior;
- meaningful failure cases;
- retry or recovery behavior;
- concurrency or ordering behavior;
- invalid-state rejection;
- compatibility behavior that could realistically regress;
- database, API, provider, browser, migration, or integration behavior materially affected by the PR.

Validation must not merely repeat Changes.

`Changes` explains what was implemented.

`Validation` explains what scenario was exercised and what result was observed.

Bad:

```text
Added a lock to serialize migration tests.
```

Better:

```text
Two overlapping migration test sessions were started, and the second could not change the migration database until the first released control.
```

### Counts and commands

Test counts are optional supporting details.

Never use a bare count as the validation result.

Bad:

```text
26 tests passed.
```

Acceptable:

```text
Twenty-six migration tests passed covering fresh-database upgrades, upgrades from an earlier version, interrupted-run recovery, unsafe SQL rejection, and overlapping migration execution.
```

Commands are normally unnecessary.

Include a command only when the exact command materially helps a reviewer reproduce a non-obvious validation scenario.

### Exclude process-only checks

Do not include:

- checker PASS;
- requirement mapping;
- generated traceability;
- testing-record completeness;
- `git diff --check`;
- Git status;
- staged-file state;
- Gate approval;
- artifact hashes;
- execution-register consistency;
- CI bookkeeping;
- PR finalization.

These are not reviewer-facing validation results unless the PR materially changes that mechanism.

## Hard rejection conditions

The PR description is invalid and must be rewritten when any of the following is true:

1. A technical phrase names a concept without explaining its concrete behavior.
2. The Summary contains terminology that requires the plan or implementation to decode.
3. The Summary contains tests, CI, future work, limitations, or deferred-work language.
4. A Changes bullet inventories a file or artifact instead of explaining behavior.
5. A Changes bullet describes pass, Gate, requirement, traceability, evidence, or execution bookkeeping.
6. A Validation bullet is only a test count, command, suite name, checker result, or Git check.
7. A Validation bullet merely repeats a Changes bullet.
8. A claim is stronger than the implementation or executed validation supports.
9. Two bullets substantially communicate the same fact.
10. A vague improvement word replaces the actual engineering behavior.
11. A local path, workstation detail, credential, secret, private provider value, personal data, payment data, or sensitive log content appears.
12. A reviewer would reasonably need to ask, “What does that term mean?” before understanding the sentence.

Do not return the PR description while any rejection condition remains.

## Mandatory final rewrite

Run this review after drafting and before returning the body.

### 1. Review every noun phrase

For every technical or abstract noun phrase, ask what it means in concrete behavior.

Replace the phrase when its behavior is not already clear.

### 2. Review the Summary independently

Read only the Summary.

Confirm that it communicates the problem, consequence, result, and importance without relying on the title, Changes, or internal documents.

### 3. Separate Changes from Validation

Confirm that:

- every Changes bullet states something materially changed;
- every Validation bullet states something actually exercised and observed;
- no bullet can move between the two sections without changing its meaning.

### 4. Remove process language

Remove planning, requirements, evidence, traceability, approval, Gate, acceptance, Git, and execution terminology unless that mechanism is itself the reviewed change.

### 5. Ground every validation claim

Confirm that every Validation bullet is supported by validation that actually ran.

### 6. Remove repetition

Keep one primary statement for each material change and validation result.

### 7. Run the unfamiliar-reviewer test

Read the complete body as an engineer who has never seen this repository.

Rewrite every sentence that requires repository-specific knowledge before its practical meaning becomes clear.

## Final author check

Do not return the body unless every answer is yes:

1. Does the Summary state a concrete previous problem?
2. Does it state the meaningful consequence of that problem?
3. Does it state what the system now does differently?
4. Can an engineer unfamiliar with the repository understand every phrase in the Summary?
5. Does every Changes bullet describe a material behavior rather than a file or process artifact?
6. Is every exact technical identifier accompanied by an explanation of what it does?
7. Does every Validation bullet describe an actually executed scenario and observable result?
8. Does Validation avoid repeating Changes?
9. Are bare counts, commands, checker results, Git checks, Gate state, and process bookkeeping excluded?
10. Are future work and deferred-work disclaimers excluded?
11. Are duplicate, vague, unsupported, or unnecessarily technical claims removed?
12. Does the body contain no sensitive information or local workstation details?

If any answer is no, rewrite the body before returning it.

## Copyable body

```markdown
## Summary

[One or two sentences explaining the concrete previous problem and consequence, followed by what the system now does differently.]

## Changes

- [Material behavior changed.]
- [Material behavior changed.]
- [Material behavior changed.]

## Validation

- [Scenario or system property]&#58; [what was exercised and what the result proved].
- [Scenario or system property]&#58; [what was exercised and what the result proved].
```