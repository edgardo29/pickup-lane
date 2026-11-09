# F26 — Admin Sign In

## 1. Existing Route(s)

- `/admin/sign-in`

## 2. Purpose

Admin Sign In gives authorized Pickup Lane staff a dedicated entry into the admin workspace and explains when an account lacks staff access.

## 3. Main Functionality

### 3.1. Sign In and Check Access

Staff enter email and password. After authentication, the page checks current staff access and returns to the originally requested admin page when authorized, including a direct-link destination such as [Financial Outcome Detail](../admin/financial-outcome-detail.md). Otherwise it opens an appropriate permitted fallback without exposing restricted content. The form includes password visibility and the shared Forgot Password link.

### 3.2. Handle Access Denial

An access-denied redirect displays a staff-access message. A user already signed in with staff access can proceed after the page checks current permissions.

## 4. Important Behavior & Decisions

### 4.1. Separate Staff Authorization

A valid player login alone does not grant admin access. The backend verifies an active, verified staff identity and current permissions. Unauthorized sign-in is rejected from the workspace and the page shows a general staff-access error. The staff page does not offer Google sign-in or account creation.

### 4.2. Safe Admin Return

The saved destination is used only if it is a real admin page the account is
authorized to open. A page need not appear in admin navigation to be a valid
return destination. An inaccessible or unavailable destination uses an
appropriate permitted fallback or unavailable state without showing protected
content. Sign-in failures keep the form available for retry; authorization is
rechecked at the destination.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Sign in with valid authorized staff credentials after requesting an admin page. | Current access is checked and the user returns to that exact authorized destination, including its applicable page context. |
| 2 | ☐ | Open the page while already signed in as authorized staff. | The page verifies access and redirects to an allowed admin page. |
| 3 | ☐ | Arrive after an admin access denial. | A clear staff-access error is visible without exposing protected workspace content. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 4 | ☐ | Submit invalid email, empty password, or incorrect credentials. | The form shows validation or authentication feedback and does not open the workspace. |
| 5 | ☐ | Sign in with a valid nonstaff, inactive, or unverified account. | Staff access is denied and no admin page opens. |
| 6 | ☐ | Supply a non-admin, sign-in, or unauthorized admin return destination. | The destination is ignored; an authorized staff user goes only to a permitted fallback and protected content is not exposed. |
| 7 | ☐ | Fail the access check or connection after credential sign-in. | No admin page opens; the form reports the failure and remains recoverable. |
| 8 | ☐ | Sign in after directly requesting Financial Outcome Detail or another authorized admin detail page absent from navigation. | The originally requested detail page opens after authentication and its normal permission check. |
| 9 | ☐ | Sign in after requesting a now-unavailable admin record. | The user sees appropriate unavailable handling or a permitted fallback; no inaccessible record content appears. |

## 6. Open Items to Resolve

Administrator TOTP is required by System Architecture §2.3 but is not set up yet. Its setup is deferred for now. Before the Admin Sign In pass can be completed, define the TOTP sign-in step in this specification and verify that it works.
