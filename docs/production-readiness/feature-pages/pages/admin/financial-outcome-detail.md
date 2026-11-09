# F52 — Financial Outcome Detail

## 1. Existing Route(s)

- `/admin/money/financial-outcomes/:financialOutcomeId`

## 2. Purpose

Financial Outcome Detail shows staff the recorded decision about a community
host's publish fee after an admin cancelled the host's community game: refund,
credit for a future publish, forfeit, no fee charged, or manual review.
Authorized staff can record the investigation result for a manual-review
outcome here. The page is reached from [Review Case Detail](review-case-detail.md) and
related admin links. It is not part of the Money navigation.

## 3. Main Functionality

### 3.1. Outcome

Shows the decision, whether it has been applied, the amount and currency, the
reason and internal note, any failure, and when it was applied, created, and
updated, along with references to the publish fee, publish credit, admin action,
and review case.

### 3.2. Related Records

Links to the [Community Game Detail](community-game-detail.md), the
[Payment Detail](payment-detail.md) and [Refund Detail](refund-detail.md) when
present, and the host's [User Detail](user-detail.md).

### 3.3. Navigation

**Back** returns to [Review Cases](review-cases.md). **Refresh** reloads the
outcome. A staff member who opens this page's link while signed out returns to
the same outcome after signing in, even though the page is not in admin
navigation; the return rules are owned by
[Admin Sign In](../authentication/admin-sign-in.md#42-safe-admin-return).

### 3.4. Resolve Manual Review

An authorized administrator can select **Resolve** on a pending manual-review
outcome, record the decision and a required explanation, and confirm it. The
page shows who resolved it, when, and the recorded decision, while preserving
the original outcome and resolution history for auditing. Resolving records
the investigation result only; any refund, game credit, payment, or other
financial transaction requires a separately authorized action.

## 4. Important Behavior & Decisions

### 4.1. How Outcomes Are Created

Outcomes are recorded when staff cancel a community game, as described in
[Community Game Detail](community-game-detail.md#33-publish-fee-outcome-on-cancellation).
This page can resolve a pending manual-review outcome without changing an
already applied refund, credit, forfeit, or no-fee outcome.

### 4.2. Applied Status

- **Refund:** a refund of the publish fee is created; problems become
  [Money Issues](money-issues.md).
- **Credit future publish:** the host receives a free future publish.
- **Forfeit:** no refund or credit.
- **No fee charged:** nothing to apply.
- **Manual review:** left pending until an authorized administrator records
  the investigation result. Resolution alone does not issue or promise money.

### 4.3. Recorded Viewing

Opening an outcome is recorded as a sensitive admin view. See
[Admin Action Log](admin-action-log.md).

### 4.4. Resolution Authorization and Audit

Only an authorized administrator can resolve a pending manual-review outcome;
the backend must enforce this even if a UI control is bypassed. The reason,
decision, actor, and time remain available with the outcome history and
[Admin Action Log](admin-action-log.md). A failed or repeated resolution does
not create a second decision or any financial transaction.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open a refund outcome for a paid publish fee. | The decision, applied status, amount, and links to the game, payment, refund, and host appear. |
| 2 | ☐ | Open a credit outcome. | The decision is applied and references the host's publish credit. |
| 3 | ☐ | Open a manual review outcome. | The applied status shows pending and an authorized administrator can open Resolve. |
| 4 | ☐ | Open the outcome from its review case. | The outcome loads and Back returns to Review Cases. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 5 | ☐ | Open an outcome whose refund failed. | The failure appears and the refund's money issue is reachable from the refund. |
| 6 | ☐ | Open an already applied outcome. | Resolve is unavailable; the recorded financial result remains unchanged. |
| 7 | ☐ | Open an outcome that does not exist. | A not-found error appears. |
| 8 | ☐ | Open the page when the admin view cannot be recorded. | Outcome details are not shown and an error appears. |
| 9 | ☐ | Resolve a pending manual-review outcome with a decision and explanation. | The page records the decision, reason, actor, and time and preserves the earlier pending outcome in history; no refund, credit, payment, or other financial transaction is issued by resolution. |
| 10 | ☐ | Attempt resolution without authorization, a reason, or a pending manual review. | The action is unavailable or rejected by the backend, and no resolution or money movement is recorded. |
| 11 | ☐ | Retry a completed or failed resolution request. | A completed decision is not duplicated; a failed attempt leaves the outcome pending and does not initiate a financial transaction. |
| 12 | ☐ | Open an outcome's direct link while signed out, then sign in as authorized staff. | The same outcome opens after authentication and its normal permission check, not the default admin page. |

## 6. Open Items to Resolve

**None**.
