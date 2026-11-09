# [Page Name]

Use this template for one distinct page experience. Keep the six main sections;
remove all instructional text and sample rows when writing a page. Add only the
subsections the page needs, numbered within their main section (for example,
3.1, 3.2). See
[docs/production-readiness/feature-pages/pages/public/browse-games.md](pages/public/browse-games.md) for a
completed example of this format.

Before writing, review the relevant frontend and backend behavior, existing
documentation, feature notes, and tests. Verify established decisions before
calling something unresolved. Code shows what is implemented; it does not, by
itself, approve a product requirement. For every page, review related page
specifications and existing shared business rules. Identify which document owns
shared functionality. Describe this page's responsibilities and page-specific
test scenarios; reference the owning document instead of duplicating shared
rules, processes, or test scenarios. Check related specifications for
contradictions, and record genuine conflicts with supporting evidence under
Open Items to Resolve.

## 1. Existing Route(s)

- `[Route to this page]`

[List other routes for the same page experience. Note redirects or aliases
without giving them a separate page specification.]

## 2. Purpose

[Say who uses this page, why it exists, and what they accomplish here. Keep the
description in product terms.]

## 3. Main Functionality

[Describe the meaningful actions and information on this page. Group related
behavior under numbered subsections when that makes the page easier to read.]

### 3.1. [Main capability]

[Describe what users can do and the result. Add, rename, or remove subsections
as needed.]

## 4. Important Behavior & Decisions

[State consequential established product rules and decisions that shape this
page's behavior, including important limits or exceptions. Describe each rule
once; put verification scenarios and expected results in section 5. Avoid
technical implementation detail or repetition from section 3.]

### 4.1. [Important rule or behavior]

[State the intended behavior clearly. Add, rename, or remove subsections as
needed.]

## 5. Tests & Edge Cases

Derive scenarios from this page's actual functionality and established
requirements. Cover normal use, boundaries, failures, and recovery where they
matter. Each expected result must be specific and verifiable. Document these
scenarios for future verification. During this documentation phase, do not run
tests, claim scenarios have passed, or mark checkboxes complete. Keep only the
subsections and scenarios relevant to this page, and number the table rows
consecutively.

### 5.1. [Established Behavior]

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | [User action or relevant condition.] | [Observable result required by established behavior.] |

### 5.2. [Boundary and Recovery Cases]

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 2 | ☐ | [Boundary, invalid input, failure, or changing state.] | [Specific result or recovery behavior supported by the requirements.] |

## 6. Open Items to Resolve

Every item here must identify a genuine unresolved product decision, conflict
between established requirements, or implementation gap. Reference the
documentation or code supporting the finding. Do not invent speculative issues
or reopen established decisions without evidence. State what needs resolution
without inventing an expected result. If there are no open items, write
**None**.
