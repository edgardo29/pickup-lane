# [Feature pass ID] — [Page name] Feature Pass Plan

**Page specification:** [Exact path under `docs/production-readiness/feature-pages/pages/`]  
**Endpoints:** [Each backend endpoint the page calls, e.g. `GET /games/browse`. Use these to search the old tests in `backend/tests/`.]

[Use this template during Gate B of
`docs/production-readiness/feature-pages/feature-pass-workflow.md`. Use the
page's F01–F54 ID from `docs/production-readiness/feature-pages/page-inventory.md`
in the title. Save it under `docs/production-readiness/feature-pages/feature-pass-plans/`,
named `<page ID>-<page name>-plan.md`: the same ID and name as the pass's
branch, without the `feature/` prefix. For example, branch
`feature/F15-browse-games` saves its plan as `F15-browse-games-plan.md`.
Remove all bracketed instructions before saving.]

## 1. Page requirements

[One row for each required behavior in Sections 3 and 4 of the page
specification. Number the rows R1, R2, and so on. Use a short label; do not
copy the full wording.]

| # | Spec section | Requirement | In the code? | What's missing |
|---|---|---|---|---|
| [R1] | [3.1] | [Short label] | [Yes, Partly, or No] | [What's missing, or "—"] |

## 2. Test scenarios

[One row per specified case: each distinct expected result in Sections 3–5 of
the page specification, with the behavior and conditions it applies to. A
scenario with several expected results has several rows. Backend tests prove
what the API returns and saves; frontend tests prove what the page shows and
does. A case that needs both appears in both tables. Only tests in the current
test suite count; the old tests in `backend/tests_archive/` and
`frontend/tests_archive/` do not.

Fill in during Gate B:

- **#:** the Section 5 scenario number, or the specification section for a
  case from Sections 3–4.
- **Expected result:** the one case the row's test verifies, taken from the
  specification.
- **Requirements:** each Section 1 requirement the case proves, for example
  "R1, R4". Every requirement in Section 1 must appear in at least one row. A
  requirement no row names has no test proving it and cannot be marked done.

Fill in during Gate C, following "Test coverage" and "Test failure
verification" in `docs/production-readiness/feature-pages/feature-pass-workflow.md`:

- **Test:** the name of the one test that verifies the case. Blank means the
  test is not written yet.
- **What was broken:** one short phrase describing the temporary change that
  made the test fail, or "Failed before the change".
- **Where:** the file changed, without line numbers, or "—" for "Failed before
  the change".

A row is complete only when Test, What was broken, and Where are filled in.]

### 2.1 Backend tests

| # | Expected result | Requirements | Test | What was broken | Where |
|---|---|---|---|---|---|
| [9] | [A removed card cannot be chosen for a paid waitlist] | [R7] | [`test_a_removed_card_cannot_be_chosen_for_a_paid_waitlist`] | [Removed the "card must be active" check for waitlist joins] | [`game_waitlist_service.py`] |

### 2.2 Frontend tests

| # | Expected result | Requirements | Test | What was broken | Where |
|---|---|---|---|---|---|
| [1] | [Saved cards show one Default badge] | [R1, R9] | [`F13-1: %s shows the cards with one Default badge`] | [Every card showed the Default badge] | [`PaymentMethodsPage.jsx`] |

## 3. Work to do

1. [Each fix, missing piece, or test to add, in order.]

[If a decision or dependency blocks any work, add a "Blocked" section naming
what is blocked and what is needed. Otherwise leave it out.

When Gate D approves the page, replace this list with "None. All work is
done."]
