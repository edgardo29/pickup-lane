# [Feature pass ID] — [Page name] Feature Pass Plan

Use this template during Gate B of `docs/production-readiness/feature-pages/feature-pass-workflow.md`
for one complete page specification. The specification defines the required
behavior and expected results. This document records what is already verified
and what remains. Replace the bracketed instructions and sample rows in a
completed assessment. Use the page's F01–F54 ID from
`docs/production-readiness/feature-pages/page-inventory.md` in the title.

**Page specification:** [Exact path under `docs/production-readiness/feature-pages/pages/`]  
**Related specifications:** [Exact paths and sections that own shared rules,
or `None`]  
**Other pages to check after shared-code changes:** [Exact page specification
paths identified during assessment, or `None`]  
**Architecture and standards to check:** [Exact paths from the documents read
for this pass, limited to the parts being changed]

Save the completed assessment under `docs/production-readiness/feature-pages/feature-pass-plans/`. Name it from
the page specification's path below `pages/`, replacing `/` with `-`. For
example, `pages/public/need-a-sub-post-detail.md` becomes
`feature-pass-plans/public-need-a-sub-post-detail.md`.

## 1. Assessment against the page specification

[Use the selected page specification as the fixed list. Give one row to each
distinct required behavior in its Sections 3 and 4, including rules it
explicitly adopts from another specification. Identify each rule by exact
section and a short, unique label; do not copy its full wording.]

Use only these current-state labels: **Verified** (an observed check established
the required result), **Present but unverified**, **Missing or incorrect**, and
**Blocked**. A route, component, or test file merely existing is not proof of
correct behavior. Keep findings brief and explain remaining work only where
there is a gap.

| Required behavior and exact specification reference | Current state | Finding or remaining work |
|---|---|---|
| [Section and short rule label] | [One label above] | [What was observed and what remains] |

[List every applicable numbered scenario in Section 5 of the selected page
specification. Do not repeat its scenario or expected result. Mark **Verified**
only when a check actually produced that expected result; otherwise use
**Not yet verified**, **Failed**, or **Blocked**. Briefly state what was found,
including the existing check when one established the result.]

| Section 5 scenario | Current state | Finding |
|---|---|---|
| [Number] | [Verified, Not yet verified, Failed, or Blocked] | [What the existing check established, or why the scenario remains unverified] |

[Identify any decision or dependency that blocks work, its exact source, and
what is needed to proceed. A Section 5 scenario checks a requirement; it does
not add a new product requirement. Gate C of
`docs/production-readiness/feature-pages/feature-pass-workflow.md` governs implementation and
verification.]
