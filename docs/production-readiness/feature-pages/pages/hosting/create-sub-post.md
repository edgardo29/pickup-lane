# F21 — Create Sub Post

## 1. Existing Route(s)

- `/need-a-sub` (create panel)

This panel shares its URL with [Need a Sub browse](../public/need-a-sub.md); it has no separate route.

## 2. Purpose

Create Sub Post lets a signed-in player ask for substitute players for an outside soccer game. The post is published for others to find through Need a Sub. [Need a Sub Post Detail](../public/need-a-sub-post-detail.md) owns requests, owner responses, and chat after publication.

## 3. Main Functionality

### 3.1. Describe the Outside Game

- A five-step form collects Game, Subs, Location, Notes, and Review information while showing a preview.
- Game details include a future date no more than 14 days ahead, start/end time, format, skill level, player group, and indoor or outdoor setting. The date control and form validation explain and enforce this limit before publication.
- The host defines one or more field-player or goalkeeper needs, with compatible player groups and a spot count for each need. The form shows the total subs needed.
- Location requires venue name, street, city, state, and ZIP. Neighborhood, price due at the venue, and notes are optional.

### 3.2. Review and Publish

- The host can move back through steps and review the full post before publishing. The first step checks whether the host already has an active post on that game date.
- Successful publication opens [Sub Post Published](sub-post-published.md). Cancel returns to Need a Sub browse; changed entries require a keep-editing or discard choice.

## 4. Important Behavior & Decisions

### 4.1. Eligibility and Posting Limits

Creating a post requires a signed-in active user with verified account email. An unverified owner sees a clear requirement and **Verify Email** action before publishing. Verification through Create Game or this entry point unlocks both; entered form information is preserved through verification where applicable. [Email Verification](../authentication/email-verification.md) owns the shared flow. Suspension blocks new posts but does not cancel the owner's existing posts; see [User Detail](../admin/user-detail.md#410-suspended-player-experience). Posts are published directly; the flow does not save drafts. An owner can have only one active Need a Sub post per local game date. The start must be in the future, no more than 14 days ahead, and the end later than the start. Formats are 3v3 through 11v11.

### 4.2. Sub Requirements

The post can request at most 11 substitutes across at most six requirement rows. Each position/player-group combination is unique. An Any Player row cannot coexist with Men or Women rows for the same position, and every row must be compatible with the game's player group. The total needed equals the sum of the rows. Request and waitlist behavior belongs to [Need a Sub Post Detail](../public/need-a-sub-post-detail.md).

### 4.3. Outside-Game Payment and Visibility

Any stated price is due at the venue; Need a Sub does not collect it in-app. Exact street and owner-only information are withheld from public browse cards according to [Need a Sub browse](../public/need-a-sub.md). Publication creates the post and its sub needs together.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open the create panel from Need a Sub while signed in. | The five-step form and preview appear at the shared URL; browsing remains a separate view of that URL. |
| 2 | ☐ | Enter a valid outside game with several compatible sub needs. | Review shows the game, venue, each position/group and count, total subs, and optional price or notes. |
| 3 | ☐ | Publish a complete post. | One active post with its requested sub needs is created; the owner reaches its publication success page. |
| 4 | ☐ | Cancel before or after changing fields. | The panel returns to browse directly when unchanged, or offers keep editing/discard when changed; no draft post is created. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 5 | ☐ | Attempt creation signed out or with unverified email. | Sign-in is required; an unverified owner sees the verification requirement and Verify Email action before publishing, and no post is created. |
| 6 | ☐ | Choose a past start, a start more than 14 days ahead, end before start, missing required location, or unsupported game choice. | The affected step identifies the invalid value before publication; the date control and validation enforce and explain the 14-day maximum, and the backend rejects a bypassed limit. |
| 7 | ☐ | Add too many subs or requirement rows, duplicate a position/group, or combine Any with Men/Women for one position. | Invalid sub needs are rejected; the published total cannot exceed 11 or six rows. |
| 8 | ☐ | Choose a sub group incompatible with the game's player group. | The combination is blocked and no inconsistent post is published. |
| 9 | ☐ | Try to publish another active post for the same local date. | The date check or final save rejects it; the original post remains unchanged. |
| 10 | ☐ | Have the date precheck or publication request fail. | The form retains entered values and shows the failure; it does not claim the post was published. |
| 11 | ☐ | Try to create a new post while suspended, with an existing post still active. | Creation is blocked without changing the existing post or its requests. |
| 12 | ☐ | Enter post details while unverified, verify the account, and return. | Entered information remains available where applicable; the verified account can publish without a second feature-specific verification. |

## 6. Open Items to Resolve

**None**.
