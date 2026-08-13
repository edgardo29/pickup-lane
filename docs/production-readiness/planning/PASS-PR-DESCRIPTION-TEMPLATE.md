# Production-Readiness PR Description Template

## Purpose

This is the standard reviewer-facing PR description template for Pickup Lane
production-readiness passes. It helps each pass PR communicate the outcome,
material changes, validation, remaining boundaries, and reviewer focus without
turning the PR body into a Gate report, command log, testing record, branch
status report, pass plan, or implementation diary.

PR descriptions should be concise and technically complete. Concise does not
mean omitting important technical information that a reviewer needs in order to
understand what changed and what was not claimed.

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

## PR Body Sections

### Summary

Use a brief summary sized to the PR.

Explain why the PR exists, the production-readiness outcome it establishes, and
whether production behavior changed. Include the context needed for a reviewer
to understand the work, but do not repeat the entire Changes section.

### Changes

Describe every material behavior, configuration, test, evidence, or governance
change a reviewer needs to understand. Group related facts so the list stays
readable, but do not omit important changes to satisfy a preferred length.
Mention deliberately preserved behavior when it matters. Avoid listing every
file unless filenames clarify ownership.

### Validation

Include only validation that helps a reviewer judge confidence. Use grouped
reviewer-useful categories instead of raw command logs.

Useful validation includes:

- focused pass test result;
- relevant broad regression result;
- specialized PostgreSQL, browser, migration, provider-contract, concurrency,
  or runtime proof when applicable;
- consolidated requirement-checker and traceability result.

Do not include routine internal finalization checks such as:

- `git diff --check`;
- publication-safety review;
- local working-tree status;
- branch or baseline SHA;
- no second PR created;
- auto-merge disabled;
- every checker scope as a separate bullet;
- exact pytest node lists;
- every command executed.

### Scope Boundaries

State important systems or behavior not changed. Identify material external,
deferred, or later-owned evidence. Group closely related boundaries. Do not copy
the entire Not Part Of This Pass section from the plan, and do not falsely imply
full control closure.

### Reviewer Focus

This section is optional. Use it only when the PR contains subtle contracts or
review points a reviewer could easily misunderstand.

Examples include:

- framework behavior that differs from application configuration;
- response classes intentionally excluded from generic middleware behavior;
- compatibility behavior that must remain unchanged;
- a narrow production change surrounded by broad evidence additions.

Do not include this section when there is no meaningful reviewer focus.

## Writing Rules

PR descriptions must:

- use plain engineering language;
- preserve technical precision;
- explain uncommon internal terminology;
- distinguish production changes from test, evidence, and documentation
  changes;
- distinguish repository proof from external evidence;
- state important non-closure boundaries;
- group related facts instead of producing long repetitive lists;
- stay complete by grouping important information, not by hiding it;
- use requirement IDs only when they genuinely help the reviewer;
- translate internal states such as `covered_elsewhere` or `deferred` into
  understandable reviewer-facing language;
- avoid Gate narration, implementation diary language, and internal agent
  workflow details;
- avoid unsupported claims;
- avoid secrets, credentials, private URLs, provider-private identifiers,
  personal data, payment data, local paths/usernames, and internal chat history.

## Copyable Markdown Template

The placeholders below are examples, not fixed counts. Add, remove, or group
bullets as needed to describe every material reviewer-relevant fact. Remove
`Specialized proof` when it does not apply, and remove `Reviewer Focus`
entirely when there is no meaningful reviewer focus.

```markdown
## Summary

[Explain why this PR exists, the outcome it establishes, and whether production
behavior changes.]

## Changes

- [Material behavior or configuration change]
- [Important tests, evidence, or governance artifacts added]
- [Important behavior deliberately preserved]

## Validation

- Focused: [suite/proof] - [result]
- Regression: [relevant suite] - [result]
- Specialized proof: [when applicable] - [result]
- Requirement checker and traceability: PASS

## Scope Boundaries

- [Important behavior or system not changed]
- [External or deferred evidence not claimed]
- [Later owner or follow-up when material]

## Reviewer Focus

- [Optional subtle contract]
```
