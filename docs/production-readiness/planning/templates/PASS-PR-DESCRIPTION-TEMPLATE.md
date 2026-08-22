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

1. why the change was needed and its high-level result;
2. the material changes in the actual diff;
3. the meaningful behavior or system properties that were validated.

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
* other internal shorthand.

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

**Explain why the change exists and the high-level result.**

Keep it short.

A reviewer should understand the purpose without reading planning documents, testing records, execution records, requirement records, Gate reports, or other supporting material.

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

**Tell the reviewer what meaningful behavior or system property was checked and the result.**

Each bullet must make clear:

* what was checked;
* the type of test or verification when useful;
* the result.

Use the behavior or system property as the subject of the bullet.

Do not use internal test names, architecture labels, policy names, checker names, configuration terms, or abstract internal concepts when the verified behavior can be stated directly.

Test counts may be included when useful, but they are supporting information. The bullet must still explain what the tests established.

Regression validation is appropriate when it confirms that important existing behavior still works after the change.

Do not create separate bullets that substantially repeat the same validation. Combine overlapping results when they describe the same test set or the same behavior.

Do not include validation merely because a check ran.

Do not include validation whose real purpose is to report:

* test placement;
* test-to-requirement mapping;
* coverage or traceability mapping;
* requirement linkage;
* suite organization;
* policy or checker compliance;
* repository-process compliance;
* evidence completeness;
* execution-record consistency;
* routine Git or finalization state.

Rewording process bookkeeping does not make it reviewer-relevant.

State what the validation establishes. Do not add statements about what it does not prove merely for completeness.

Do not make claims stronger than the performed validation supports.

## Mandatory final rewrite pass

After drafting the PR description, review every sentence and bullet before producing the final output.

For each one:

1. **Translate terminology:** If an implementation, configuration, framework, architecture, planning, testing, or internal term can be replaced by a short description of what it actually does, replace it.
2. **Remove process language:** If the sentence mainly describes tracking, evidence, mapping, policy, approval, or production-readiness machinery rather than the reviewed change, remove it.
3. **Remove duplication:** If the same engineering fact or validation result appears elsewhere, keep the clearest version only.
4. **Preserve substance:** Do not remove meaningful behavior, boundaries, compatibility information, or engineering consequences merely to make the description shorter.

Do not produce the PR description until this rewrite pass is complete.

## Writing standard

* Explain the actual change, not the process used to produce it.
* Use normal product and engineering language.
* Prefer concrete behavior over names, labels, and shorthand.
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

1. Is it immediately clear why the PR exists and what materially changed?
2. Does every `Changes` bullet describe a real change in the diff in language that does not require translating internal terminology?
3. Does every `Validation` bullet state meaningful behavior that was checked and the result without duplication or process bookkeeping?
4. Is anything unnecessary, repetitive, vague, unsupported, process-heavy, needlessly technical, or sensitive?

If any answer reveals a problem, correct it before producing the final output.

## Copyable body

```markdown
## Summary

[Briefly explain why the change was needed and the high-level result.]

## Changes

- [Material change]
- [Material change]

## Validation

- [Behavior or system area]&#58; [test or verification and result].
- [Behavior or system area]&#58; [test or verification and result].
```
