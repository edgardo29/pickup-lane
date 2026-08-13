# Frontend Structure

This document defines the authoritative rules for frontend file placement,
responsibility, dependency direction, and architectural ownership in Pickup
Lane.

Read it before creating, moving, splitting, renaming, or substantially changing
frontend files.

Also read:

* the relevant feature documentation before changing product behavior
* `universal-ui-style.md` before changing visual design or interaction patterns
* `global-rules.md` before running commands, tests, or broad repository changes

This document does not define detailed visual styling, feature behavior, test
commands, or temporary implementation plans.

When existing code conflicts with these rules, do not silently copy or expand
the conflict. Keep the requested change focused and identify the inconsistency
unless the task explicitly includes correcting it.

## Existing Structure

The frontend currently uses:

```text
frontend/
├── public/                 Static files served from fixed root URLs
├── src/
│   ├── assets/             Assets imported by source files
│   ├── components/         UI shared across unrelated features
│   │   ├── app/            Shared signed-in application shell
│   │   └── skeleton/       Shared loading primitives
│   ├── context/            Application-wide React providers
│   ├── data/               Shared static reference data
│   ├── features/           Domain UI and workflows shared by multiple pages
│   ├── hooks/              Hooks shared across unrelated features
│   ├── lib/                API, provider, and external-service infrastructure
│   ├── pages/              Route-level feature folders and page components
│   ├── routes/             Route registration, guards, and route utilities
│   ├── styles/             Global, shared, admin, and route-feature styles
│   ├── App.jsx             Application composition
│   └── main.jsx            React, router, and provider bootstrap
└── tests/
    └── e2e/                Playwright browser tests
```

Continue using these locations.

Do not create a new top-level frontend directory or architectural layer unless
none of the existing locations can clearly own the responsibility.

A new architectural layer requires an explicit project-level decision.

The following are generated or dependency folders, not source folders:

* `frontend/node_modules/`
* `frontend/dist/`
* `frontend/playwright-report/`
* `frontend/test-results/`

Do not edit or treat files inside those directories as application source.

## Placement Decision Order

Use the narrowest correct owner:

1. Route-level screens and route-specific behavior belong in `pages/`.
2. Code used only by one route feature stays beside that feature.
3. Cohesive domain UI or workflows shared by multiple pages may belong in
   `features/`.
4. UI shared across unrelated domains belongs in `components/`.
5. Hooks shared across unrelated domains belong in `hooks/`.
6. Application-wide state belongs in `context/`.
7. Shared API, provider, and external-service infrastructure belongs in `lib/`.
8. Route declarations and guards belong in `routes/`.
9. Shared static reference data belongs in `data/`.
10. Create a new file or directory only when no existing owner is appropriate.

Do not make code shared in anticipation of possible reuse.

Promote code when there is a real second caller or when one canonical owner is
needed to prevent behavior from drifting.

## Pages

`frontend/src/pages/` owns route-level screens and the code used only by those
screens.

A route feature may contain:

* page components
* feature-specific components
* page hooks
* API request functions
* form behavior
* payload construction
* selectors and derived state
* formatting and mapping
* validation
* loading, error, and empty-state UI
* feature-specific static data

Page components own route-level composition and orchestration, including:

* route parameters
* navigation
* page loading
* page-level errors
* feature hooks
* API calls
* page sections
* dialogs and panels
* route-specific skeletons

Supporting code used only by one route feature should remain beside that
feature.

Do not move feature-only code into a global folder merely to shorten a page
file.

A route feature may use subdirectories when it contains several substantial
workflows with distinct responsibilities.

Do not create nested folders while the feature remains easy to understand as
one directory.

A feature `index.js` may expose its intentional route-facing API. Do not use
barrel files to export every private module or conceal unclear dependencies.

## Features And Shared Components

`frontend/src/features/` owns cohesive domain UI or workflows reused by multiple
route pages.

Use `features/` when:

* multiple pages share the same domain workflow
* the shared code has one clear domain owner
* keeping separate copies would risk behavioral drift
* the code is more specific than generic presentation UI

Do not mirror every page folder under `features/`.

Do not split one domain between `pages/` and `features/` without a clear reuse
boundary.

`frontend/src/components/` owns:

* reusable presentation components
* application-shell components
* shared navigation and layout
* reusable loading primitives
* shared semantic UI
* cross-domain component systems

A file is not globally shared merely because it contains JSX.

A component used only by one route domain belongs in that domain's page or
feature folder.

Shared components must not import route page components or route-specific
workflow logic.

## Hooks And Context

Use the narrowest hook location:

* a hook used by one route feature belongs in that page feature
* a hook used by one shared domain workflow belongs in that feature
* a hook used across unrelated domains belongs in `src/hooks/`

Keep route-specific navigation, form state, and data orchestration local unless
there is real cross-feature reuse.

Shared hooks must not import route page components.

`frontend/src/context/` owns application-wide React context and provider
implementation.

Create context only for state or actions that must cross broad parts of the
application.

Do not use context:

* to avoid passing props through one small feature
* for route-local form state
* for one page's modal state
* as a general replacement for feature hooks
* as an unstructured global store

Keep each provider focused on one application-wide responsibility.

Split provider internals when they contain distinct cohesive responsibilities,
not merely because the provider file is long.

## API And External Infrastructure

`frontend/src/lib/` owns low-level, broadly reusable infrastructure such as:

* the shared API client
* provider initialization
* external SDK initialization
* shared transport behavior
* shared authentication transport
* broadly reused error normalization
* cross-domain API infrastructure

Feature-specific endpoint functions belong with the page or feature that owns
the workflow.

Keep API request functions separate from React rendering and display
formatting.

Use existing shared clients and provider initialization.

Do not create:

* duplicate API clients
* duplicate provider setup
* feature-specific fetch wrappers that bypass shared infrastructure
* wrappers that merely rename one existing call
* generic `services.js`, `utils.js`, or `helpers.js` dumping grounds

Infrastructure modules must not import route page components.

Domain decisions based on API responses belong in the owning page hook or
feature workflow, not in the low-level client.

## Routes

`frontend/src/routes/` owns:

* route path registration
* route-to-page mapping
* route guards
* route-level redirects
* route-wide navigation behavior

Route configuration should import page entry points and shared guards.

Keep product UI, form behavior, and substantial data workflows out of route
configuration.

Route guards may decide whether the frontend permits entry to a page. Backend
authorization remains authoritative.

Pages must not register themselves with the router.

## Data, Assets, And Public Files

`frontend/src/data/` owns static reference data reused across unrelated
features.

Feature-only options, labels, tabs, limits, and static configuration belong
inside the owning page or feature.

Do not move local constants into global data files merely because they do not
contain JSX.

Use `frontend/src/assets/` for assets imported by React or CSS.

Use `frontend/public/` only for files that require a stable root URL or must be
served without a source import.

Do not duplicate the same asset across both locations.

Do not edit generated build output.

## Styles

The frontend uses plain CSS imported by the source modules that own it.

Current style ownership:

* `styles/base.css`: root variables, reset behavior, document defaults, and
  genuinely global element rules
* `styles/app-shell.css`: shared application shell, navigation, page shell,
  footer, shared controls, and cross-page application material
* `styles/game-card.css`: shared compact game-card chrome used by Browse Games
  and My Games; feature CSS owns page layout and relationship/status variants
* `styles/<feature>/`: route-feature layout and component styles
* `styles/admin/`: shared admin shell and admin feature styles
* component-local CSS: portable shared components whose styles are part of the
  component's reusable contract

Global CSS is loaded from `main.jsx`.

Feature CSS should be imported by the page, feature entry point, or shared
component that owns it.

Do not place page-specific rules in `base.css` or `app-shell.css`.

Do not create a separate global stylesheet for behavior owned by one feature.

Keep responsive rules with the styles they modify.

Do not create one stylesheet per tiny component by default.

Split a stylesheet when it owns separate substantial surfaces or has become
difficult to navigate.

Detailed visual rules, spacing, colors, typography, controls, modals,
responsive behavior, and design-system requirements belong in
`universal-ui-style.md`.

## Files, Folders, And Naming

Every frontend file must have a purpose that can be described in one short
sentence.

Use:

* `PascalCase` for React components and component files
* a `use` prefix and camel case for hooks
* lower camel case for non-component JavaScript modules
* `.jsx` only for files containing JSX
* `.js` for files without JSX
* clear responsibility suffixes where useful
* `*.spec.js` for Playwright end-to-end test files

Useful responsibility suffixes include:

* `Api`
* `Data`
* `Formatters`
* `Mappers`
* `Payloads`
* `Selectors`
* `Validation`

Avoid vague names such as:

* `utils.js`
* `helpers.js`
* `common.js`
* `misc.js`
* `manager.js`
* `processor.js`
* `services.js`

Create or split a file when it establishes a meaningful responsibility or
separates behavior with different callers, dependencies, or reasons to change.

Do not split a file merely because it is long.

Do not create:

* speculative shared abstractions
* wrapper components that add no meaningful behavior
* one-function modules without a clear boundary
* files that only rename another function call
* tiny files that make one cohesive workflow harder to follow
* generic helper or constants dumping grounds

Create a subdirectory only when a domain contains several cohesive files and
the folder provides a clear ownership or navigation benefit.

Do not create a directory for one file or because a feature may grow later.

For a non-trivial new file or directory, identify:

1. its path
2. its responsibility
3. why an existing file is insufficient
4. which modules may import it
5. which modules it may import

## Imports And Dependency Direction

The project currently uses relative ES module imports with explicit `.js` or
`.jsx` extensions.

No frontend source alias is currently configured in Vite.

Follow the existing relative-import convention.

Do not introduce a source alias, omit required file extensions, or change module
resolution as an incidental part of a feature task.

Required dependency direction:

* `main.jsx` bootstraps React, routing, and global providers
* `App.jsx` composes application-wide pieces
* `routes/` imports page entry points and guards
* route pages import their local modules and shared frontend systems
* features import their local modules and lower-level shared systems
* shared components, hooks, context, data, and library modules do not import
  route page components

Keep same-feature imports local.

Use a feature export surface only when outside modules need its intentional
public API.

Avoid:

* wildcard imports
* circular dependencies
* hidden side-effect imports
* barrel files that export private implementation details
* reverse dependencies from shared code into page-owned code
* permanent import workarounds that conceal unclear ownership

When shared code needs behavior currently owned by a route page, identify the
actual shared owner instead of importing the page module.

## Tests

The current frontend test setup is Playwright.

Current locations:

* configuration: `frontend/playwright.config.js`
* browser tests: `frontend/tests/e2e/*.spec.js`
* generated reports: `frontend/playwright-report/`
* generated test output: `frontend/test-results/`

Browser-level tests should follow the user-visible workflow or feature being
tested.

Tests should verify behavior through stable user-facing outcomes rather than
depending unnecessarily on private component implementation.

There is currently no configured frontend unit or component test runner.

Until a unit or component test runner is explicitly introduced:

* do not add unexecuted `*.test.js` or `*.test.jsx` files
* do not invent a unit-test folder convention
* do not introduce a new test framework as part of an unrelated feature change

Do not place production modules in the test package.

Exact commands, environment requirements, and test-running rules belong in
`global-rules.md` or dedicated testing documentation.

## Scope Discipline

Keep each implementation limited to the approved task.

Do not mix unrelated:

* cleanup
* renaming
* file moves
* architecture changes
* styling changes
* feature work
* dependency changes
* test-tooling changes

Do not refactor nearby legacy structure merely because a file is being touched.

A structural correction is appropriate when it is necessary to implement the
requested behavior safely and clearly.

## Before Frontend Changes

Before editing frontend code:

1. Read this document.
2. Read the relevant feature documentation.
3. Read `universal-ui-style.md` when visual or interaction behavior may change.
4. Read `global-rules.md` for commands and testing requirements.
5. Identify the page, feature, or shared system that currently owns the
   behavior.
6. State which files will change.
7. Keep feature-specific code inside its owner by default.
8. Explain any non-trivial new shared file, directory, or moved responsibility.
9. Confirm the dependency direction.
10. Confirm the focused validation for the change.
11. Keep unrelated cleanup outside the task.

Before considering the structural portion complete, confirm:

* each changed file has one clear responsibility
* route pages retain route-level ownership
* feature-specific code remains local
* shared code has real reuse and one clear owner
* shared modules do not depend on page components
* API and provider infrastructure have not been duplicated
* global state has not absorbed feature-local behavior
* styles remain with the narrowest correct owner
* existing app shell, API client, style system, icons, and skeleton primitives
  are reused where applicable
* imports follow the configured relative path and extension convention
* imports do not form cycles
* tests and imports reflect any file movement
