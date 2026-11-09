# F03 — Privacy Policy

## 1. Existing Route(s)

- `/privacy`

## 2. Purpose

Privacy Policy explains the current description of information Pickup Lane collects, how it is used, and what happens to personal information after account deletion.

## 3. Main Functionality

### 3.1. Read the Policy

The page presents the Privacy Policy title and current sections in reading order. It is reachable from the footer; Create Account opens the same policy in a modal.

### 3.2. Leave the Page

The brand opens Landing. The Back control returns to a supplied origin when available, otherwise to Landing.

## 4. Important Behavior & Decisions

### 4.1. Public, Read-Only Policy

No account is required. Reading this page does not change privacy settings or account data. The policy content is shared with [Create Account](../authentication/create-account.md); account settings belong to [Profile](../player/profile.md).

### 4.2. Development Copy

The current text identifies itself as a working placeholder pending final legal review. It must not be described here as final launch language.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open Privacy directly while signed out or signed in. | Both viewers can read the title and all current sections without a sign-in gate. |
| 2 | ☐ | Open Privacy from the footer and the Create Account modal. | Both surfaces show the same policy content. |
| 3 | ☐ | Select the brand or Back control. | The brand opens Landing; Back returns to the supplied origin when present. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 4 | ☐ | Open the route without origin state. | Back opens Landing. |
| 5 | ☐ | Read through the current policy. | Its development placeholder notice remains visible with the current copy. |

## 6. Open Items to Resolve

- **Launch privacy policy — unresolved content:** Final legal language is explicitly pending review. Evidence: `frontend/src/features/legal/legalPolicies.js:52-53`; `docs/feature-notes/auth.md:128-131`.
