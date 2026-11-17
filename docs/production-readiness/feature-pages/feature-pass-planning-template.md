# [Feature pass ID] — [Page name] Feature Pass Plan

**Page specification:** [Exact path under `docs/production-readiness/feature-pages/pages/`]  
**Endpoints:** [Each backend endpoint the page calls, e.g. `GET /games/browse`. Use these to search the old tests in `backend/tests/`.]

[Use this template during Gate B of
`docs/production-readiness/feature-pages/feature-pass-workflow.md`. Use the
page's F01–F54 ID from `docs/production-readiness/feature-pages/page-inventory.md`
in the title. Save it under `docs/production-readiness/feature-pages/feature-pass-plans/`,
named from the specification's path below `pages/` with `/` replaced by `-`.
For example, `pages/public/browse-games.md` becomes `public-browse-games.md`.
Remove all bracketed instructions before saving.]

## 1. Page requirements

[One row for each required behavior in Sections 3 and 4 of the page
specification. Use a short label; do not copy the full wording.]

| Spec section | Requirement | In the code? | What's missing |
|---|---|---|---|
| [3.1] | [Short label] | [Yes, Partly, or No] | [What's missing, or "—"] |

## 2. Test scenarios

[List every numbered scenario in Section 5 of the page specification in the
table or tables that prove it. Backend tests prove what the API returns and
saves. Frontend tests prove what the page shows and does. A scenario that needs
both appears in both tables. Only tests in the current test suite count; the
old tests in `backend/tests_archive/` and `frontend/tests_archive/` do not. Leave Result blank until the tests are
run in Gate C.]

### 2.1 Backend tests

| # | Scenario | Test exists? | Result |
|---|---|---|---|
| [1] | [Short label] | [Yes or No] | [Pass or Fail] |

### 2.2 Frontend tests

| # | Scenario | Test exists? | Result |
|---|---|---|---|
| [2] | [Short label] | [Yes or No] | [Pass or Fail] |

## 3. Work to do

1. [Each fix, missing piece, or test to add, in order.]

[If a decision or dependency blocks any work, add a "Blocked" section naming
what is blocked and what is needed. Otherwise leave it out.

When Gate D approves the page, replace this list with "None. All work is
done."]
