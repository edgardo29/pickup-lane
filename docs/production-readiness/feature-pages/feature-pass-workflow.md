# Pickup Lane Feature Pass Workflow

Use this workflow to implement the product behavior defined by Pickup Lane's
54 Product & Functional Specifications. Each feature pass covers one page
specification and the shared behavior it requires. This workflow explains
how to assess, implement, verify, and complete that page.

The F01–F54 IDs in `docs/production-readiness/feature-pages/page-inventory.md`
give a preferred work order. An earlier ID is not automatically a prerequisite
for a later pass; complete actual dependencies before dependent work.

This document governs feature assessment, implementation, verification,
completed-work review, corrections, Git safety, publication authorization,
and manual merge. The finalized page specifications supply the requirements
and verification scenarios. Each page's Feature Pass Plan tracks what is in
the code, which tests exist, and what work remains, without changing those
requirements.

Product features do not use production-readiness pass numbers, pass records,
the verification map, or
`docs/production-readiness/production-launch/production-launch-pass-completion-log.md`.
When feature work also satisfies a production-readiness requirement, that
program still owns its separate evidence and completion decision.

## 1. Gate A — Read the documents

**Branch.** Before the pass's first file change, create its branch from
`develop`, named `feature/<page ID>-<page name>`: the page ID from
`page-inventory.md`, then the page specification's file name, for example
`feature/F15-browse-games`. Use one branch and one pull request per page pass.
The pull request targets `develop`; merging `develop` into `main` is a separate
step outside the pass.

Start with `docs/production-readiness/feature-pages/page-inventory.md` to find the
ID and Product & Functional Specification for the page being implemented.

Read the complete specification for the selected page under
`docs/production-readiness/feature-pages/pages/`:

- Section 1 identifies the page's routes.
- Section 2 explains why the page exists and who uses it.
- Section 3 defines its required functionality.
- Section 4 defines its established behavior and product decisions.
- Section 5 defines the scenarios and expected results that must be verified.
- Section 6 identifies unresolved decisions or missing content.

If the specification refers to behavior defined by another specification,
read that specification too. Use the document that defines the shared behavior
instead of copying or reinterpreting its requirements.

Read these supporting documents when they apply to the feature:

- `docs/production-readiness/system-architecture.md` for application
  structure and external services.
- `docs/production-readiness/database-architecture.md` for the intended database design.
- `docs/production-readiness/data-model-baseline.md` for the database structures currently
  represented in the repository.
- The applicable coding, database, and testing standards under
  `docs/coding-standards/`.

The specifications define the required product behavior. Existing code and
tests show what is currently implemented. They do not replace or override the
specifications.

If two authoritative documents conflict, identify the exact conflicting
requirements and stop the affected work until the conflict is resolved. Do not
invent a decision.

## 2. Gate B — Check current behavior against the specification

Before editing, compare the current application with Sections 3 (Main
Functionality) and 4 (Important Behavior & Decisions) of the selected Product
& Functional Specification under `docs/production-readiness/feature-pages/pages/`. Use its Section 5
(Tests & Edge Cases) scenarios and expected results to check what the existing
tests prove. When those sections rely on a rule defined in another
specification, check the code against that specification's rule too. Decide
what already works, what still needs verification, what is missing or
incomplete, and what is blocked by a decision or dependency.

Follow the page through the frontend, API, database, background work, and
external services it actually uses, including error and recovery behavior
required by those specifications. For access, money, capacity, privacy,
status, and data integrity rules, inspect backend or database enforcement
where appropriate; hiding a frontend control is insufficient.

Preserve behavior that already meets the specification. Identify work that
must be completed first. When shared code will change, add an item to
Feature Pass Plan, Section 3 (Work to do) to re-check each other page that
uses it. Use one
implementation when pages share the same rule, and keep different rules
separate. Complete prerequisites before dependent work.

Read `docs/production-readiness/feature-pages/feature-pass-planning-template.md` in full, then save the
selected page's Feature Pass Plan under `docs/production-readiness/feature-pages/feature-pass-plans/` using the naming
rule in that template. Use the exact rules in the page specification's
Sections 3 and 4 and its numbered Section 5 scenarios as the fixed
list. The Feature Pass Plan records, without copying the specification, Section 1 (Page
requirements: whether each requirement is in the code), Section 2 (Test
scenarios: whether each scenario has a backend test in Section 2.1 and a
frontend test in Section 2.2, as it requires), and Section 3 (Work to do).
Before implementation, have the complete Feature Pass Plan reviewed against the
specification and the inspected code and tests. Correct any defects, then
review the corrected Feature Pass Plan again.

## 3. Gate C — Implement and verify the page

**Before starting,** re-read these coding standards in full, in
`docs/coding-standards/`: `backend-standards.md`, `backend-structure.md`,
`frontend-standards.md`, `frontend-structure.md`, `css-standards.md`,
`database.md`, `backend-testing.md`, and `frontend-testing.md`. Do not work
from memory of earlier passes.

**Working through the Feature Pass Plan**

1. Work through Feature Pass Plan, Section 3 (Work to do) in order, one item at a time.
2. After finishing each item in Feature Pass Plan, Section 3 (Work to do),
   update the Feature Pass Plan:
   - Feature Pass Plan, Section 1 (Page requirements): set "In the code?" to **Yes** for each
     requirement fixed.
   - Feature Pass Plan, Section 2.1 (Backend tests) and Section 2.2 (Frontend
     tests): set "Test exists?" to **Yes** for each test added, and fill in
     "Result" with **Pass** or **Fail** for each test run.

   Always update before stopping or switching chats.
3. Before setting a test row to **Yes** or **Pass**, confirm:
   - the test exists and proves that exact scenario, not only that it
     carries the scenario's marker or name;
   - every faked API answer matches what the real server returns for that
     kind of user (for example signed out, unverified, or suspended),
     including its status code and message;
   - test data is built the way the real workflow creates it, for example a
     community game includes the host's own roster place;
   - the test follows `backend-testing.md` or `frontend-testing.md`: its
     folder, page marker or name, one file per topic, exact status codes, a
     database check after each successful change, a nothing-changed check
     after each rejected request, and every allowed value of a status or role
     the behavior depends on.
4. When the pass changes the database schema, update
   `docs/production-readiness/data-model-baseline.md` in the same pass.
5. If new work is found, add it to Feature Pass Plan, Section 3 (Work to do)
   before starting it.
6. Gate C is done when every "In the code?" is **Yes**, and every "Test
   exists?" is **Yes** and every "Result" is **Pass** in both Section 2.1 and
   Section 2.2.

Use the reviewed Feature Pass Plan to identify the remaining work. Resolve technical
choices using the specifications, current repository, approved architecture,
and applicable engineering standards. Use
`docs/production-readiness/database-architecture.md` for
approved database changes that have not yet been implemented. Stop affected
work if an unresolved product decision could change the required behavior.
If implementation reveals an incorrect Feature Pass Plan, update it and
review the correction before relying on it.

Follow Sections 3 and 4 of the selected page specification and the shared
rules it depends on. Verify the applicable Section 5 scenarios in that
specification and any required related specifications. For each scenario,
choose checks that can establish its expected result where the behavior is
enforced. Check the complete workflow when several parts of the application
must work together; a frontend check alone cannot prove a backend or database
safeguard.

Add checks when a requirement, realistic failure, existing behavior that must
continue working, or an applicable engineering standard calls for them,
including when a gap is found during review. Compare the observed result with
the expected result and check that prohibited effects did not occur. A check
that failed, did not run, or became invalid after a later change is incomplete.

When shared behavior changes, verify affected pages and other callers. A
check of the shared code alone does not prove that each caller uses it
correctly.

## 4. Gate D — Review corrections and completed work

**Before starting,** re-read these coding standards in full, in
`docs/coding-standards/`: `backend-standards.md`, `backend-structure.md`,
`frontend-standards.md`, `frontend-structure.md`, `css-standards.md`,
`database.md`, `backend-testing.md`, and `frontend-testing.md`. Do not work
from memory of earlier passes.

Conduct an independent, read-only review of the completed page pass against every item in its approved Feature Pass Plan, Sections 3–5 of the selected page specification, and the applicable coding standards.

Every Gate D round is a complete review from the start, including the round
after corrections. Do not review only the diff or only the corrected items.

- For each requirement, follow the whole path: every request the page makes,
  what the server allows for each kind of user, and how the stored data
  really looks.
- Read every section of another specification or architecture document that
  the page specification or Feature Pass Plan relies on, and check the code
  against that rule.
- Open each test listed in Feature Pass Plan, Section 2, and check it against
  the Gate C test checks above.

Report findings as a short, plain list of the issues. Give further detail
only when asked.

Examine the relevant implementation, directly affected dependencies, and verification results from Gate C. Confirm that the required behavior, failure handling, prohibited effects, and applicable test scenarios have been addressed.

**Limit the review to the selected page pass and its directly affected dependencies.** If shared code changed, review only the other pages named in the re-check items in Feature Pass Plan, Section 3 (Work to do). If a directly affected page or dependency was omitted, report the specific connection and return to Gate C to update the Feature Pass Plan. Review the updated Feature Pass Plan before continuing. Do not investigate unrelated features, files, or repository issues.

### Security and sensitive-information review

Identify the complete publication set:

- Every file this page pass intends to commit, whether staged, unstaged, or untracked.
- Every additional artifact this page pass intends to package, deploy, or publish.

Include relevant code, configuration, tests, scripts, documentation, generated files, and build artifacts. Exclude unrelated workspace files and local-only or ignored files that will not be published.

Run **Gitleaks** against the complete publication set and manually inspect that same set for secrets and prohibited sensitive information. Confirm which files Gitleaks examined. If Gitleaks cannot inspect a file or artifact, use an appropriate alternative inspection method and record the limitation. Do not scan unrelated files or expand the review beyond the publication set.

Check for:

- Passwords, database credentials, credential-bearing connection strings, API secrets, authentication tokens, private keys, service-account credentials, webhook secrets, recovery codes, and other access credentials.
- `.env` files, credential files, private-key certificates, and confidential configuration.
- Sensitive values embedded in URLs, logs, comments, test fixtures, documentation, generated output, or encoded content.
- Personal information, financial information, and private external-service identifiers that must not be disclosed.

Distinguish legitimate public configuration and synthetic test values from confidential information. Do not assume information is safe because it appears in a test, document, or generated file.

**Gate D cannot pass if Gitleaks fails, any publication item remains unchecked, or a confirmed or suspected sensitive-information exposure remains unresolved.**

Report findings by file, location, information category, and exposure risk without reproducing sensitive values. Redact secret values from scanner reports and review output.

If a real credential was exposed, determine whether it reached Git history, logs, published artifacts, or another accessible location. Approval remains blocked until the exposure is assessed and required revocation, replacement, and remediation are complete. Removing a credential from the current file alone does not resolve an earlier exposure.

### Corrections and re-review

Gate D is strictly read-only. Return identified problems to Gate C for correction.

After corrections, rerun the verification affected by those corrections. Repeat Gitleaks and manual sensitive-information inspection, then conduct a new independent Gate D review of the complete corrected work.

If corrections change the Feature Pass Plan or its re-check items in Section 3 (Work to do), update and review the Feature Pass Plan before proceeding.

Approve Gate D only when the selected page pass satisfies its assessed requirements, the required verification has passed, and no blocking findings remain.

When Gate D approves the page, replace the items in Feature Pass Plan, Section 3 (Work to do) with "None. All work is done."

## 5. Gate E — Finalize, publish when authorized, and record page completion

Begin Gate E only after Gate D approval.

Confirm the correct branch and identify the exact changes authorized for publication. Do not discard, overwrite, or include unrelated work.

If publication is authorized:

1. Read the complete `docs/production-readiness/pass-pr-description-template.md`. Follow its applicable PR-body instructions to describe the actual changes and verification. Use the selected feature pass's F ID in the pull-request title, following the template's feature-pass format.

2. Stage only the changes approved in Gate D. Inspect the exact staged files and diff. Confirm that every staged file was reviewed in Gate D and that its contents match the approved version. If unrelated or unreviewed changes are staged, stop without modifying or discarding them.

3. **Run Gitleaks against the exact staged contents and manually inspect them for secrets and prohibited sensitive information.** Also inspect any publication artifacts outside the staged files. Confirm that every item matches what was approved in Gate D, that inspection coverage is complete, and that no unresolved sensitive-information findings remain.

4. Confirm that every "Result" in Feature Pass Plan, Section 2.1 (Backend tests) and Section 2.2 (Frontend tests) is **Pass** and was reviewed in Gate D. Do not introduce additional tests or expand the verification scope during Gate E. If required verification is missing, failed, or invalidated by subsequent changes, stop and return to Gate C.

5. Record the page's completion date in `docs/production-readiness/feature-pages/feature-pass-completion-log.md` as part of the pass PR, following the completion rules below. Merging the PR records the completion; do not change the log after the merge.

6. Commit and push normally only after the preceding requirements pass. Create or update the pull request. Confirm its base branch, source branch, title, and description. Inspect the complete pull-request diff and verify that it contains only the exact changes approved in Gate D.

**Stop publication if any file or artifact is unrelated, unreviewed, or differs from its Gate D-approved contents; any sensitive-information finding remains unresolved; or any required verification or security inspection is missing or failed.**

Return changed or defective work to Gate C for correction and repeat Gate D before continuing. Do not silently modify or discard unrelated files.

Leave the pull request open for manual merge. All applicable reviews and any checks required by the repository's existing branch-protection settings must pass before merging. Do not assume unconfigured CI checks exist. Merge only when explicitly authorized.

After manual merge, confirm that the intended changes reached the base branch and that their verification remains valid. If the page required no pull request, confirm its accepted result directly.

`docs/production-readiness/feature-pages/feature-pass-completion-log.md` is the only feature completion record. Enter the completion date in the pass PR only when the selected page satisfies its specification's Sections 3 and 4 and applicable shared rules, and all applicable Section 5 scenarios have passed. If the pass is merged with only blocked work left, enter the merge date followed by "(items left)"; the pass plan's Blocked section lists what remains, and the PR that finishes that work replaces the entry with the completion date.

A connected page pass does not need to be complete first if every requirement
and scenario for the selected page passes, including its required interactions
with that page. If unfinished connected work prevents a required scenario from
passing, leave the selected page incomplete.

Leave the date blank if required work, failed verification, a missing dependency, or an unresolved decision remains.

Do not automatically begin another page pass.
