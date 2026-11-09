# Frontend Engineering Standards

## Purpose and scope

This document defines general engineering standards for browser-delivered React
applications written in modern JavaScript and built with Vite. It covers code
behavior and maintainability, not a universal folder structure, product design,
test runner, routing library, state library, deployment model, or rendering mode.

An adopting project's repository guide defines its actual paths, configured
tools, browser baseline, and local conventions. Product requirements define
behavior. CSS standards own detailed styling rules; testing documentation owns
test organization and commands. Apply this document together with those sources.

The requirement words have these meanings:

- **MUST**: required for correct or safe implementation.
- **MUST NOT**: prohibited.
- **SHOULD**: preferred; a justified exception may be appropriate.
- **SHOULD NOT**: normally avoid.
- **MAY**: optional when the stated conditions apply.

Do not turn an optional library or React feature into a requirement merely
because it is available. Evaluate version-dependent APIs against the adopting
project's installed versions.

## 1. Ownership, reuse, and modules

Keep each UI behavior, state transition, side effect, request operation, and
style responsibility with the narrowest owner that can explain it. Route-level
composition needs a clear owner; code used by one feature SHOULD stay with that
feature. Move code to a shared owner when there is real reuse or a stable shared
contract, not in anticipation of possible callers.

Use cohesive components and modules with clear inputs, outputs, and reasons to
change. Extract code when doing so clarifies ownership, reuse, or testing. Do
not split a cohesive workflow solely because a file is long. Avoid wrappers
that merely rename a framework or platform call, generic dumping-ground modules,
and highly configurable components whose unrelated options conceal different
responsibilities.

Use ECMAScript modules with intentional public exports. A module SHOULD expose
only what its consumers need. Named and default exports are both acceptable
when their use is clear. Dependencies SHOULD point from feature-specific code
to stable shared code. Shared code SHOULD NOT depend on private feature modules.
Avoid circular dependencies, hidden import side effects, and barrels that expose
private implementation details. The adopting project defines import paths,
extensions, aliases, and naming conventions.

## 2. Components, props, and identity

React components and Hooks **MUST** remain pure during render. Rendering must
not cause externally visible side effects or mutate values outside the render's
local scope. Props, state snapshots, Hook arguments and return values, and
values already passed to JSX **MUST NOT** be mutated directly. Local mutation
of a value created and contained within one calculation MAY be used when it is
clear and does not violate these boundaries.

Components SHOULD have explicit, small interfaces. Prefer composition when
variations represent meaningfully different structures or behavior. A compact
set of props is appropriate when the variations form one stable component
contract. Do not create a universal component whose many flags make supported
combinations unclear.

React associates component state with rendered identity. List keys **SHOULD**
represent stable semantic identity when items can be inserted, removed, or
reordered. Do not use array positions as keys for identity-bearing, reorderable
items. Change a key deliberately when resetting a subtree is intended. Avoid
defining a stateful component type inside another component's render, where its
identity can change unexpectedly.

## 3. State, Context, and reducers

Store the smallest complete state representation. Values derivable from props
or existing state **SHOULD** be calculated during render rather than copied
into another state variable and synchronized with an Effect. Avoid duplicated,
contradictory, or unnecessarily deep state.

Keep state local to its owner. Lift state to the closest common owner when
multiple components must coordinate it. Context **MAY** carry values or actions
shared across a meaningful subtree, including a feature subtree; it should not
become the default destination for local form, modal, or transient state.
Reducers **MAY** clarify numerous or interdependent transitions. Simple,
independent state does not require a reducer. An external state library needs a
demonstrated requirement beyond the project's existing state mechanisms.

State updates **MUST** produce new values where React needs to observe a
change. Prefer named transitions and one source of truth for related state.

## 4. Hooks and Effects

Hooks **MUST** follow React's Rules of Hooks. Ordinary Hooks must be called at
the top level of React components or custom Hooks, never conditionally or in
loops. React's special `use()` API is an exception and may be called
conditionally or in loops, subject to its documented restrictions. Custom
Hooks SHOULD encapsulate a coherent reusable behavior, not simply hide a line
of code.

Use Effects to synchronize with systems outside React, such as subscriptions,
timers, browser APIs, or network activity. Derivations belong in render and
interaction-triggered work generally belongs in the event handler. Effect
dependencies are determined by the reactive values the Effect reads; they are
not a scheduling preference. **MUST NOT** suppress required dependencies merely
to make an Effect run less often. Restructure the Effect instead.

An Effect that establishes a subscription, timer, connection, or pending work
**SHOULD** provide corresponding cleanup. If a request can become obsolete,
abort it or ignore its result so an old response cannot replace current state.
Do not require an `AbortController` for every request when a different
stale-result guard is the correct boundary.

Version-specific tools such as `useEffectEvent` **MAY** be used when supported
and when they solve their intended narrow problem. They must not hide missing
Effect dependencies.

## 5. JavaScript and asynchronous work

Functions SHOULD have descriptive names and visible dependencies. Prefer
straightforward control flow and transformations over hidden mutation of
shared data. Contained local mutation is acceptable when it improves clarity;
a blanket rule that all JavaScript values must be immutable is unnecessary.

Handle errors where code can recover, add useful context, or present a user
outcome. Do not catch and rethrow the same error at every layer without adding
meaning. Async work SHOULD have an explicit rejection path; avoid unhandled
fire-and-forget Promises. Run independent tasks concurrently when all results
are needed and doing so is safe; use sequential work when order or a dependency
requires it.

Error Boundaries **SHOULD** protect product regions where an unexpected render
failure would otherwise remove an unacceptable amount of UI. They catch React
rendering failures in descendant trees, not ordinary event-handler or most
asynchronous errors. Place them around meaningful recovery regions rather than
mechanically around every component.

## 6. API communication and UI reliability

Keep transport mechanics, domain request operations, and user-visible state
conceptually distinct; they do not require separate files in every case.
Transport code handles shared HTTP policy, credentials, serialization, status,
and cancellation. Domain operations describe the action being requested.
Components and Hooks translate results into interface state. Avoid bypassing a
project's established client or duplicating its policy in feature code.

When using `fetch`, HTTP failure statuses **MUST** be checked explicitly:
`fetch` can resolve with a response for an HTTP error. Handle network failures,
protocol failures, and application failures at the appropriate boundary. A
request whose parameters or owner can change **SHOULD** guard against stale
results. User-visible operations **SHOULD** communicate the relevant loading,
error, empty, and success states and offer recovery where the product requires
it. Preserve entered data on recoverable failures when practical.

A data-fetching or caching library **MAY** be adopted when its deduplication,
cache invalidation, retry, mutation, or rendering support solves a demonstrated
problem. Do not add one for a few simple independent requests solely to follow
a preferred architecture pattern.

## 7. Routing, navigation, and forms

Route-level code SHOULD own route parameter interpretation, route-specific
loading and errors, and page composition. Domain UI SHOULD not depend on
browser location details without a navigation responsibility. Supported routes
SHOULD work as direct entry points; history entries SHOULD represent meaningful
navigation. Client-side navigation SHOULD manage focus when the normal browser
page-load behavior is absent and users would otherwise lose context.

Choose controlled inputs when rendering or validation needs each change;
uncontrolled inputs MAY be used when values are mainly consumed at submission.
Both can coexist when ownership is clear. Use native form semantics and
constraints where they express the requirement. Client validation **MUST NOT**
be treated as server enforcement. Prevent harmful duplicate submissions when
the operation cannot safely accept them, and communicate pending and failure
states.

## 8. Security

Untrusted content **MUST** be rendered as text by default. Do not insert it
into HTML, script, URL, or other executable contexts without protection
appropriate to that context. An intentional HTML feature requires a maintained
sanitization boundary; `dangerouslySetInnerHTML` is not a shortcut for normal
text rendering.

All client code and client-exposed configuration must be treated as public.
Secrets **MUST NOT** be placed in Vite variables exposed to the client or in
other client bundles. Browser storage **MUST NOT** be treated as secret storage
for credentials or session tokens. A frontend route guard or hidden control
**MUST NOT** be treated as authorization; protected operations require backend
authorization.

Third-party scripts and dependencies SHOULD have a concrete benefit and a
maintenance and security review proportionate to their authority and impact.
Do not invent a new authentication scheme as part of ordinary frontend work.

## 9. Accessibility and interaction semantics

Prefer semantic HTML and native controls. Interactive functionality **MUST**
have accurate accessible names and states, appropriate keyboard operation, and
visible keyboard focus. Custom widgets must implement their declared semantics
and expected keyboard behavior; ARIA alone does not add native interaction.

When WCAG 2.2 Level AA applies, a keyboard-focused component **MUST NOT** be
entirely hidden by author-created content, subject to that criterion's defined
notes and exceptions. Dialogs, menus, navigation, and removal of focused
elements SHOULD move or restore focus deliberately when needed to preserve
context. Programmatically associate form errors and instructions with their
controls. When WCAG 4.1.3 applies, status messages **MUST** be programmatically
determinable without receiving focus. Other important status changes SHOULD
also be exposed to assistive technology without forcing focus unnecessarily.

The applicable CSS standard owns focus-indicator styling, contrast, sizing,
reflow, motion, and other visual requirements. The frontend must supply the DOM
semantics and state that make those styles meaningful.

## 10. Performance, Vite, and assets

Measure the affected rendering, network, JavaScript, or bundle cost before
adding optimization complexity. **SHOULD NOT** add `useMemo`, `useCallback`,
`React.memo`, virtualization, or manual chunks mechanically. Use them when
profiling or a clear identity-sensitive boundary shows a benefit. Code splitting
**MAY** defer expensive or infrequently used UI when it materially reduces
initial work and preserves a useful loading experience.

Vite configuration and plugins SHOULD remain limited to concrete requirements
or measured needs. Do not add build overrides merely because a feature exists.
Import assets through the source module graph by default; use Vite's `public`
directory when an asset needs a stable root URL, unchanged filename, or
untransformed copying. Client-exposed environment values arrive as strings and
SHOULD be parsed when another type is intended. Their public nature still
applies regardless of which environment file supplies them.

Rendering mode, production source-map publication, HTML and hashed-asset cache
policy, and deployment strategy require project-level decisions. This standard
does not mandate client-side rendering, server-side rendering, or React Compiler.

## 11. Testability

Code SHOULD make behavior observable through clear inputs, outputs, DOM
semantics, and user-facing outcomes. Keep side effects and network boundaries
explicit so tests can substitute them without mocking every internal module.
Tests SHOULD verify behavior or contracts at the narrowest layer that gives
reasonable confidence, rather than depending unnecessarily on private
component structure. Browser-level tests SHOULD follow the user-visible
workflow or feature they cover. Detailed suites, commands, execution policy,
and coverage belong to the adopting project's testing documentation.

## 12. Decision rule

When several implementations are valid, prefer the one with clear ownership,
correct React behavior, explicit failure paths, accessible interaction,
appropriate project conventions, and the least unnecessary complexity.

## Technical references

- [React: Rules of React](https://react.dev/reference/rules)
- [React: `use` API](https://react.dev/reference/react/use)
- [React: Choosing the State Structure](https://react.dev/learn/choosing-the-state-structure)
- [React: Synchronizing with Effects](https://react.dev/learn/synchronizing-with-effects)
- [MDN: Using the Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch)
- [Vite: Environment Variables and Modes](https://vite.dev/guide/env-and-mode.html)
- [Vite: Static Asset Handling](https://vite.dev/guide/assets)
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/)
- [OWASP: DOM based XSS Prevention](https://cheatsheetseries.owasp.org/cheatsheets/DOM_based_XSS_Prevention_Cheat_Sheet.html)
