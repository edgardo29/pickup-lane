# F09 — Check Email

## 1. Existing Route(s)

- `/check-email`

## 2. Purpose

Check Email confirms a password reset request and tells the visitor how to continue or request another email.

## 3. Main Functionality

### 3.1. Follow Reset Instructions

The page displays a non-disclosing confirmation, the submitted email when available, and steps to check inbox/spam, open the link, and reset the password. The page states that the link expires in 60 minutes. It links back to Sign In and Forgot Password.

### 3.2. Resend

When the submitted email is available, **Resend email** requests another reset link and reports success or a recoverable error.

## 4. Important Behavior & Decisions

### 4.1. Missing Page Context

A direct visit without a submitted email still shows general guidance. Resend is disabled until an email is supplied through the Forgot Password flow; the visitor can return there.

### 4.2. Account Privacy

Known and unknown emails receive the same non-disclosing confirmation. An unknown-email response during resend is treated like successful dispatch rather than exposing account existence. The actual link handling belongs to [Reset Password](reset-password.md).

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Arrive after a reset request. | The page identifies the submitted email and gives the reset instructions without asserting that an account exists. |
| 2 | ☐ | Resend using the retained email. | Another request is made and a success message appears; the action is disabled while sending. |
| 3 | ☐ | Follow Forgot Password or Back to Sign In. | The selected authentication page opens. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 4 | ☐ | Open Check Email directly without retained email. | General guidance appears; Resend is disabled and the visitor can return to Forgot Password. |
| 5 | ☐ | Resend for an unknown account. | The same success message appears as for a known account. |
| 6 | ☐ | Fail a resend for another provider or network reason. | A recoverable error appears without a false success message. |

## 6. Open Items to Resolve

**None**.
