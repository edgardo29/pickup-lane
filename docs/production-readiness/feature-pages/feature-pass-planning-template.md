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

- **Test #:** the row's number in its table, counting from 1 in each table.
- **Scenario:** the Section 5 scenario as the tests tag it, the page ID and
  scenario number (`F13-9`). When the case also comes from a rule in Sections
  3–4, add that section after it (`F13-9, Section 4.1`).
- **Expected result:** the one case the row's test verifies, in the
  specification's own words for that part of the scenario or rule. Reword only
  where the test needs more detail than the specification gives.
- **Requirements:** each Section 1 requirement the case proves, for example
  "R1, R4". Every requirement in Section 1 must appear in at least one row. A
  requirement no row names has no test proving it and cannot be marked done.

Fill in during Gate C, following "Test coverage" and "Test failure
verification" in `docs/production-readiness/feature-pages/feature-pass-workflow.md`:

- **Test:** the name of the one test that verifies the case. Blank means the
  test is not written yet.
- **Failure check:** one short phrase describing the temporary change that
  made the test fail, or "Failed before the change".
- **File broken:** the file changed, without line numbers, or "—" for "Failed
  before the change".

A row is complete only when Test, Failure check, and File broken are filled
in.

Put this key above the two tables in the plan:]

One row per specified case from Sections 3–5 of the page specification.

- **Test #**: the row's number in its table.
- **Scenario**: the page's Section 5 scenario, written as the tests tag it (`F13-9` is scenario 9); "Section 4.1" names a spec rule the result also comes from.
- **Expected result**: the spec's own words for the part this test proves.
- **Requirements**: the Section 1 requirements the test proves.
- **Failure check** and **File broken**: the temporary break that made the test fail, and the file it was made in.

### 2.1 Backend tests

| Test # | Scenario | Expected result | Requirements | Test | Failure check | File broken |
|---|---|---|---|---|---|---|
| [1] | [F13-9, Section 4.1] | [A removed card is not usable for a paid waitlist] | [R7] | [`test_a_removed_card_cannot_be_chosen_for_a_paid_waitlist`] | [Removed the "card must be active" check for waitlist joins] | [`game_waitlist_service.py`] |

### 2.2 Frontend tests

| Test # | Scenario | Expected result | Requirements | Test | Failure check | File broken |
|---|---|---|---|---|---|---|
| [1] | [F13-1] | [The page shows one default marker] | [R1, R9] | [`F13-1: %s shows the cards with one Default badge`] | [Every card showed the Default badge] | [`PaymentMethodsPage.jsx`] |

## 3. Work to do

1. [Each fix, missing piece, or test to add, in order.]

[If a decision or dependency blocks any work, add a "Blocked" section naming
what is blocked and what is needed. Otherwise leave it out.

When Gate D approves the page, replace this list with "None. All work is
done."]
