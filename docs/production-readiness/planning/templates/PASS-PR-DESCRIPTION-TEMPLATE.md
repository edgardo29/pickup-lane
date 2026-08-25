# PR Description Template

Use this template to write a PR description that lets a reviewer quickly understand:

* why the PR exists;
* what materially changed;
* what meaningful behavior was validated.

The PR description must explain the change itself, not the process used to plan, track, document, verify, or approve it.

Preserve important engineering information. Remove process noise, repetition, unnecessary completeness language, and terminology that makes the reviewer translate the description before understanding it.

## Default structure

Use only these three sections by default:

1. `Summary`
2. `Changes`
3. `Validation`

Add another section only when the specific PR genuinely requires it to understand or evaluate the change.

Do not add sections merely for completeness.

## Content selection

Before writing, identify only:

1. the concrete problem, risk, limitation, or missing behavior that made the change necessary, and the practical result after the change;
2. the material changes in the actual diff;
3. the meaningful behavior, failure cases, compatibility boundaries, or system properties that were actually validated.

Exclude supporting process information unless that process document, template, or mechanism is itself a material change being reviewed.

A file, test, record, artifact, requirement, checker result, or process document does not deserve a PR bullet merely because it changed.

## Plain-language rule

Write for a software engineer who understands normal engineering concepts but does not know the internal terminology of this work.

**Prefer what something does over what it is called.**

Do not make the reviewer decode:

* configuration names;
* framework-specific labels;
* internal architecture names;
* abbreviations;
* planning terminology;
* testing terminology;
* production-readiness terminology;
* infrastructure shorthand;
* other internal terminology.

If a term can be replaced with a short, accurate description of the behavior without losing important meaning, replace it.

Do not keep terminology merely because it:

* appears in the code;
* appears in supporting documents;
* is technically correct;
* is commonly used by engineers.

Use an exact technical name only when its exact identity materially helps the reviewer understand the change. When an exact name is necessary, make what it does clear from the same sentence.

Do not simplify precise engineering facts into vague phrases. Simplify the wording, not the substance.

## Summary

Summary has one job:

**Explain the concrete reason the change was needed and the practical high-level result.**

Keep it short. Usually one compact paragraph is enough.

A reviewer should understand the purpose without reading planning documents, testing records, execution records, requirement records, Gate reports, or other supporting material.

The Summary must be understandable without knowing the repository's internal architecture, infrastructure terminology, or production-readiness terminology.

The Summary must communicate both sides of the change:

1. **Before:** what concrete problem, risk, limitation, missing capability, or incorrect behavior existed.
2. **After:** what the system now does differently at a high level.

When the old behavior could cause a meaningful incorrect state or failure, say what that consequence was. Do not make the reviewer infer why the change mattered.

### Summary Acceptance Test

A Summary is acceptable only if a reviewer can answer these after reading it once:

1. What changed?
2. What problem, risk, limitation, or missing behavior made the change necessary?
3. What does the system do differently after this PR?
4. Why does the change matter in this PR's own context?

If any answer is unclear, rewrite the Summary before continuing.

Do not use broad labels as the main explanation. Phrases such as `adds safeguards`, `handles concurrency`, `improves reliability`, `strengthens validation`, `database-backed`, `production-readiness`, or `race conditions` are not enough unless the same sentence explains the concrete problem and practical result.

For example, do not stop at:

`This adds database safeguards for concurrency issues.`

Prefer the actual engineering meaning:

`Concurrent requests could make decisions from the same stale database state and consume the same limited capacity more than once. The change serializes conflicting database operations so each request makes its decision against the state left by the request that won first.`

The example illustrates the required level of concreteness, not a required sentence structure. For an additive capability, refactor, configuration change, migration, or other kind of PR, describe its real motivation and result naturally.

**Describe the practical engineering result, not merely the category of work.**

A Summary is too vague if it mainly says the PR:

* adds safeguards;
* improves reliability;
* handles concurrency;
* strengthens validation;
* hardens behavior;
* improves safety;
* makes something more robust;
* improves production readiness;

without explaining what could actually go wrong, what was missing, or what the system now does differently.

Do not use an internal, infrastructure, or process term in the Summary when a short description of what it actually means would be clearer.

In particular, avoid terms such as these unless the exact term is genuinely necessary to understand the change:

* provider-independent;
* topology;
* connection budget;
* role/grant;
* evidence contract;
* verification framework;
* production-readiness;
* control;
* deferred verification;
* provider/runtime evidence;
* infrastructure timing;
* execution boundary;
* traceability;
* requirement mapping.

Translate them into what they mean.

Examples:

* Instead of `provider-independent`, say `without depending on a specific hosting provider`.
* Instead of `database topology`, say `how the application and database are deployed and connected`.
* Instead of `connection budget`, say `how many database connections the production system can safely use`.
* Instead of `role/grant verification`, say `checking that database accounts have only the permissions they need`.
* Instead of `verification framework`, describe the checks or rules that were added.
* Instead of `deferred production evidence`, explain that the actual production values will be checked after the final hosting setup is selected.

The Summary should answer these questions directly:

1. What concrete problem, limitation, risk, or missing capability made this PR necessary?
2. What did that mean for the system before this change?
3. What does the system now do differently?

If a sentence sounds like the title of an internal design document, a feature label, or a generic statement that something was improved instead of an explanation to another engineer, rewrite it.

Do not use the Summary for:

* process or review benefits;
* testing or evidence details;
* internal planning language;
* unrelated background;
* unchanged behavior included only for completeness;
* future work;
* limitations or disclaimers;
* things not changed or not proven.

## Changes

Changes has one job:

**Describe the material changes in the actual diff.**

Each bullet must describe a meaningful reviewer-facing change.

Describe what the system now does, requires, allows, prevents, limits, separates, configures, or handles differently.

Preserve important:

* behavior changes;
* configuration differences;
* environment differences;
* compatibility boundaries;
* architectural consequences;
* security behavior;
* API behavior;
* data or migration behavior;
* infrastructure or operational behavior;
* material documentation or template changes.

Describe the behavior or engineering result rather than inventorying files.

Tests normally belong in `Validation`.

Do not create `Changes` bullets merely for:

* tests;
* evidence;
* requirements or controls;
* testing records;
* execution records;
* coverage or traceability records;
* approval or Gate records;
* supporting process files.

A documentation or template change may receive a bullet when that change itself is material and part of the diff being reviewed. Describe what the document now communicates, requires, or enables in clear language rather than repeating internal process terminology.

Do not include preserved or unchanged behavior merely to demonstrate completeness. If preserving an existing behavior was meaningfully verified after the change, describe that result in `Validation`.

## Validation

Validation has one job:

**Explain what important behavior, failure mode, compatibility boundary, or system property was actually proven after the change.**

Write validation for the reviewer, not as a log of commands that ran.

Each bullet should describe one distinct validation result and make clear:

* what behavior, risk, failure case, or regression boundary was checked;
* the scenario or type of verification when that helps explain the proof;
* what the system did correctly;
* whether the verification passed.

Use the behavior or system property as the subject of the bullet.

Prefer:

`Overlapping roster requests were tested against PostgreSQL and could not commit more players than the game had available spots.`

Instead of:

`17 tests passed.`

Prefer:

`Existing booking, roster, and account-deletion behavior continued to pass after the locking changes.`

Instead of:

`Compatibility suite: 54 passed.`

### Validation source of truth

Do not derive Validation claims from `Changes`, from the implementation alone, or from what the code appears intended to do.

Before writing `Validation`, inspect the actual validation evidence for the PR.

Use, as applicable:

1. the current testing record or equivalent validation/evidence record, especially its scenario, proof-layer, and validation-result sections;
2. the actual tests or verification artifacts when needed to understand exactly what scenario was exercised;
3. the recorded results from validation that actually ran;
4. the approved validation plan only to understand intended scope, never as proof that validation passed.

Every Validation bullet must be supported by validation that actually ran or by another explicitly identified proof layer.

Do not claim that behavior was tested merely because:

* the implementation appears to provide it;
* the plan required it;
* a test file exists;
* a related suite passed;
* a requirement says the behavior should exist.

If the available evidence does not establish a claimed behavior, omit the claim rather than infer it.

When a broader regression or compatibility suite is used, identify the behavior or system area that made that suite relevant instead of reporting only its name or test count.

### Relevant validation only

Include validation that helps establish that the change works correctly, such as:

* direct behavior changed by the PR;
* meaningful edge and failure cases;
* concurrency or ordering behavior;
* rollback, retry, duplicate, or invalid-state handling;
* security or authorization behavior;
* database, API, provider, migration, browser, or integration behavior when materially affected;
* existing behavior that could realistically regress because of the change.

The relevant validation scope should come from:

* the actual behavior changed;
* the risks introduced or addressed by that change;
* affected callers and integrations;
* compatibility boundaries identified for the change;
* the actual validation evidence that was executed.

Do not add unrelated validation merely to increase the amount of reported testing.

### Test counts and commands

Test counts are optional supporting information.

If a count is included, identify what those tests covered and why that scope was relevant.

Do not use a bare count as a validation result.

Bad:

* `17 passed`
* `69 tests passed`

Acceptable:

* `Seventeen PostgreSQL concurrency tests passed covering contested roster capacity, waitlist promotion, account-deletion cleanup, and game-credit operations.`

Commands are normally unnecessary.

Include a command only when the exact command materially helps a reviewer reproduce or understand the verification.

Do not turn Validation into a transcript of the validation run.

### Avoid repeating Changes

Validation may cover the same system areas described in `Changes`, but it must not merely restate the implementation.

A `Changes` bullet explains what the PR changed.

A `Validation` bullet explains what behavior, failure case, compatibility boundary, or system property was exercised and what the result proved.

Do not repeat implementation details in `Validation` unless they are necessary to explain the scenario being verified.

If a Validation bullet could be moved into `Changes` without changing its meaning, rewrite or remove it.

Example:

`Changes`

- Serializes roster capacity decisions so competing requests cannot decide from the same stale capacity state.

`Validation`

- Concurrent join and guest-add scenarios confirmed that overlapping requests cannot commit more players than the game has available spots.

### Regression validation

Regression validation belongs in the PR description when the change could realistically affect existing behavior and that behavior was actually rechecked.

Describe the affected behavior, not merely the suite that ran.

Prefer:

`Existing transaction handling, account deletion, roster operations, and credit behavior continued to pass after the database-locking changes.`

Instead of:

`Regression tests: 124 passed.`

If a regression suite covers many unrelated areas, report only the relevant validated behavior rather than advertising the total suite size.

### Exclude process-only checks

Do not include validation merely because a check ran.

Unless that mechanism is itself materially changed by the PR, omit validation whose only purpose is:

* test placement;
* test-to-requirement mapping;
* requirement traceability;
* checker compliance;
* suite organization;
* testing-record completeness;
* execution-register consistency;
* `git diff --check`;
* Git status or staged-file state;
* PR or Git finalization;
* CI bookkeeping;
* artifact hashes;
* approval or Gate state;
* other workflow or evidence bookkeeping.

Rewording process bookkeeping does not make it reviewer-relevant.

Do not create multiple bullets that substantially prove the same thing. Combine overlapping results or keep the strongest, clearest statement.

Do not make claims stronger than the performed validation supports.

## Mandatory final rewrite pass

After drafting the PR description, review every sentence and bullet before producing the final output.

For each one:

1. **Strengthen the Summary:** Verify that it passes the Summary Acceptance Test, explains a concrete reason the change was needed, and states what the system now does differently. If a reviewer could reasonably ask "what does that mean?", or if it only names a category of work or says something was improved, strengthened, hardened, safeguarded, or made more reliable, rewrite it.
2. **Translate terminology:** If an implementation, configuration, framework, architecture, infrastructure, planning, testing, or internal term can be replaced by a short description of what it actually does, replace it.
3. **Remove process language:** If the sentence mainly describes tracking, evidence, mapping, policy, approval, or production-readiness machinery rather than the reviewed change, remove it.
4. **Remove duplication:** If the same engineering fact or validation result appears elsewhere, keep the clearest version only.
5. **Preserve substance:** Do not remove meaningful behavior, failure consequences, boundaries, compatibility information, or engineering consequences merely to make the description shorter.
6. **Check Summary comprehension:** Read the Summary as if the reviewer has never seen the project's production-readiness documents. The reviewer should understand why the change was necessary and what practical result it produced without having to infer either one.
7. **Ground Validation:** Confirm every Validation claim is supported by validation that actually ran or another explicit proof layer. Do not infer Validation from the implementation or plan.
8. **Check Validation relevance:** Every Validation bullet must prove a distinct behavior, failure case, regression boundary, or system property that matters to the PR. Remove command-log entries, bare test counts, and process checks.
9. **Check Changes/Validation separation:** If a Validation bullet merely repeats what was implemented, rewrite it around the scenario exercised and result proved, or remove it.

Do not produce the PR description until this rewrite pass is complete.

## Writing standard

* Explain the actual change, not the process used to produce it.
* Use normal product and engineering language.
* Prefer concrete behavior over names, labels, and shorthand.
* Explain the real problem or missing behavior instead of merely naming the category of work.
* Explain the resulting system behavior instead of merely saying something was improved, hardened, safeguarded, or made more reliable.
* Preserve important engineering detail.
* Use exact technical names only when their exact identity helps the reviewer understand the diff.
* Do not copy wording from planning, testing, requirement, Gate, traceability, or other process documents when the underlying engineering fact can be stated directly.
* Include only information that helps the reviewer understand or evaluate the diff.
* Do not repeat the same fact in multiple sections.
* Do not add background, future work, limitations, disclaimers, unchanged behavior, or things not proven merely for completeness.
* Do not include process history, approval state, requirement or control bookkeeping, execution state, evidence bookkeeping, artifact hashes, Git bookkeeping, or similar information unless it is itself the material change being reviewed.
* Do not make claims stronger than the implementation or validation supports.
* Do not include secrets, credentials, private identifiers, personal or payment data, local paths, workstation details, or internal chat history.

## Final author check

Before producing the final PR description, confirm:

1. Does the Summary clearly state the concrete reason the PR was needed?
2. Does the Summary clearly state what the system does differently after the change?
3. Would a reviewer understand why the change matters rather than only knowing what technical category it belongs to?
4. Does every `Changes` bullet describe a real change in the diff in language that does not require translating internal terminology?
5. Does every `Validation` bullet come from validation that actually ran or another explicit proof layer?
6. Does every `Validation` bullet explain a distinct behavior, failure case, regression boundary, or system property that was actually proven?
7. Are test counts and commands used only as supporting detail rather than as the validation result itself?
8. Does `Validation` avoid repeating implementation details already explained in `Changes`?
9. Is process-only validation such as requirement mapping, checker compliance, Git checks, and workflow bookkeeping omitted unless it is itself part of the PR's material change?
10. Is anything unnecessary, repetitive, vague, unsupported, process-heavy, needlessly technical, or sensitive?
11. Could an engineer unfamiliar with this project explain both the problem and the result after reading the Summary once?

If any answer reveals a problem, correct it before producing the final output.

## Copyable body

```markdown
## Summary

[Briefly explain the concrete problem, risk, limitation, or missing behavior that made the change necessary, followed by what the system now does differently at a high level.]

## Changes

- [Material change]
- [Material change]

## Validation

- [Distinct behavior, failure case, regression boundary, or system property]&#58; [what was actually exercised and what the result proved].
- [Distinct behavior, failure case, regression boundary, or system property]&#58; [what was actually exercised and what the result proved].
```