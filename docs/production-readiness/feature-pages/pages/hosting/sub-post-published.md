# F23 — Sub Post Published

## 1. Existing Route(s)

- `/need-a-sub/posts/:postId/published`

## 2. Purpose

Sub Post Published confirms that the owner created an outside-game substitute post and gives a quick route to the new post or back to Need a Sub. Creation rules belong to [Create Sub Post](create-sub-post.md); subsequent requests and management belong to [Need a Sub Post Detail](../public/need-a-sub-post-detail.md).

## 3. Main Functionality

### 3.1. Confirm and Navigate

- After publication, show a success heading and a compact summary of the post's game date, time, location, and filled/needed spots.
- **View Post** opens that post's detail page. **Back to Need a Sub** opens the browse page.
- A direct visit or refresh without a confirmed successful publication does not show publication success. If the post is available, the visitor goes to its normal detail page; otherwise the page shows an unavailable or load-error state.

## 4. Important Behavior & Decisions

### 4.1. Publication Outcome

The create flow opens this page only after the signed-in owner successfully publishes the post. The success message requires that publication context; the route and a readable post alone do not prove publication by this visitor. This page is informational; it does not create another post, accept requests, or change availability.

### 4.2. Access and Load Failure

The route requires a signed-in account. Post data must be available to show a truthful summary. Without confirmed publication context, an available post opens in Post Detail; an unavailable post shows an unavailable state, and a failed load shows a load error. Neither state claims publication success.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Publish a valid Need a Sub post. | The success page opens for the created post and shows its date, time, location, and filled/needed count. |
| 2 | ☐ | Use View Post or Back to Need a Sub. | The first link opens that post's detail; the second returns to browse without creating another post. |
| 3 | ☐ | Refresh or directly open the new post's success URL without confirmed publication context. | An available post redirects to Post Detail; no new publication success is claimed. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 4 | ☐ | Open the success URL while signed out. | The route requires sign-in before private success content is shown. |
| 5 | ☐ | Fail to load a post on a direct visit. | A load error appears without publication success or an invented post summary. |
| 6 | ☐ | Open a success URL for another owner's available post, or an inactive or missing post. | An available post opens in Post Detail; an unavailable post shows its unavailable state; neither claims that this visitor published it. |

## 6. Open Items to Resolve

**None**.
