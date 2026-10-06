# Pickup Lane Production-Readiness Program Context

## 1. Purpose

This document is the stable program overview and routing index for Pickup Lane
production-readiness work. It explains the system shape, program structure,
document locations, verification approach, work selection, and terminology.

Startup, requirement-source priority, conflict handling, repository safety, and
publication boundaries are defined by
`docs/production-readiness/00-READ-ME-FIRST.md`.

Production-readiness assignments should identify the corrected-master unit and
any run-specific constraints. This document and the read-first entry point route
to the applicable workflow, technical standards, accepted repository state,
and current change set. Historical pass artifacts are read only when they are
useful to the work.

## 2. Pickup Lane And Production-Readiness Overview

Pickup Lane is a web application for organizing and operating pickup football
games. The production-readiness program spans code, configuration, tests, external
service settings, runtime verification, operational ownership, and recovery
verification.

System areas relevant to production-readiness planning include:

- Backend: FastAPI application code under `backend/`.
- Frontend: React/Vite browser application under `frontend/`.
- Database: PostgreSQL, SQLAlchemy models, and Alembic migrations.
- Authentication: Firebase-backed user identity and admin access behavior.
- Payments: Stripe-backed payment and checkout flows.
- External services and infrastructure providers: hosting, database hosting,
  Firebase/GCP, Stripe, Cloudflare R2, DNS/TLS, repository/CI, monitoring, and
  backup providers.
- Product workflows: games, bookings, rosters, waitlists, Need-a-Sub, chats,
  notifications, venue images, credits, and payment-related state.
- Admin and operations: admin workflows, moderation, notices, deployment,
  health, verification, ownership, incident, recovery, privacy, and external
  service control-plane behavior.

Production readiness requires these areas to satisfy the corrected master with
credible verification at the appropriate source, test, database, provider,
runtime, or operational boundary, not merely to pass local tests.

## 3. Final Infrastructure Timing And Late-Bound Verification

The read-first document defines the complete final-infrastructure timing rule.
For routing purposes, classify work in one of two ways:

- **Independent of final infrastructure selection:** correctness does not
  require facts about the eventual production hosting provider, topology,
  capacity, account binding, or provider-native settings. Portable source
  behavior, configuration interfaces, validation, formulas, and synthetic
  fixtures can belong here.
- **Requires selected final infrastructure:** correct implementation or
  verification needs facts about the eventual production hosting, database,
  edge/TLS topology, runtime shape, capacity, concrete roles or grants, or
  provider control plane. Keep this work deferred until those facts exist.

Vercel, Render, and Neon remain temporary development/demo infrastructure and
cannot supply final production assumptions. Do not copy final values from them,
README examples, local or CI settings, free-tier defaults, framework defaults,
or demo deployments.

When a unit contains both classifications, separate the executable work from a
mandatory deferred follow-up. Record the follow-up's owner, trigger, preserved
obligations, dependencies, latest completion boundary, and execution-register
visibility. Deferral is not verification or completion. Downstream work may
continue only when it does not need the deferred facts; otherwise stop on the
specific missing prerequisite.

This timing rule does not prohibit a service-specific product integration such
as Cloudflare R2, Stripe, or Firebase when a current requirement source fixes
that integration. It governs the still-unselected production infrastructure and
the concrete configuration or external verification that depends on it.

## 4. Program Structure

Current production-readiness work follows this requirement and execution chain:

```text
corrected master blueprint and applicable current requirements
-> accepted repository state and current change set
-> Stage 0 scope, reconciliation, and decomposition decision
-> Gate A engineering planning and plan review
-> implementation and risk-based testing
-> independent semantic review
-> normal Git/PR finalization with the intended post-merge execution-register update
-> manual merge
```

The corrected master defines scope, the implemented-work correction program, the
27 remaining units, provider timing, testing philosophy, explicit do-not-build
boundaries, and completion criteria.

Earlier audits, the remediation plan, owner decisions, governance records,
intakes, plans, SHAs, and PRs remain useful provenance or technical context.
They do not override the corrected master or restore rejected scope.

For first-time implementation, Stage 0 through Gate D are retained execution
responsibilities. Stage 0 may decide no decomposition is required, and Gate A's
plan may be concise for straightforward work. A recorded parent decomposition
does not rerun Stage 0 for each later child while current requirements,
dependencies, and accepted repository behavior still support it; those children
begin at Gate A. The sequence does not create automatic transitions, does not require elaborate
artifacts, and does not define production-readiness scope.

## 5. Document Map And Routing Indexes

| Path | Purpose |
|---|---|
| `docs/production-readiness/00-READ-ME-FIRST.md` | Startup, requirement-source priority, terminology, safety, and publication-boundary entry point. |
| `docs/production-readiness/01-PROGRAM-CONTEXT.md` | Program overview and routing index. |
| `docs/production-readiness/planning/program/pickup-lane-master-production-readiness-blueprint.md` | Controlling production-readiness scope, correction program, remaining roadmap, and completion criteria. |
| `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md` | Accepted or intended post-merge execution state, historical decomposition, deferred obligations, and remaining work. |
| `docs/production-readiness/planning/workflows/PASS-IMPLEMENTATION-WORKFLOW.md` | First-time Stage 0 through Gate D implementation workflow. |
| `docs/production-readiness/planning/workflows/PASS-RECHECK-WORKFLOW.md` | Recheck guidance for implementation already merged into `develop` or older historical implementation. |
| `docs/production-readiness/planning/passes/` | Historical and current pass intakes/plans; use the reviewed plan for the current branch and do not use other records to override corrected-master scope. |
| `docs/production-readiness/audit-research/` | Historical audit and research provenance. |
| `docs/production-readiness/planning/program/pickup-lane-production-readiness-remediation-plan-final.md` | Historical remediation provenance; it does not define current scope. |
| `docs/production-readiness/decisions/` | Historical owner decisions and supporting context; a decision is a current requirement source only where the corrected master or current task still adopts it. |
| `docs/production-readiness/governance/` | Historical supporting context only; active instructions must not rely on it to define current scope or requirements. |
| `docs/production-readiness/planning/templates/PASS-PLANNING-TEMPLATE.md` | Required plan structure whenever Gate A creates a durable implementation plan. |
| `docs/production-readiness/planning/templates/PASS-PR-DESCRIPTION-TEMPLATE.md` | Current PR-authoring guidance used by implementation Gate D. |
| `docs/production-readiness/planning/templates/` | Other templates are supporting aids unless the applicable workflow explicitly requires one. |
| `docs/agent-notes/README.md` | Routing index for tracked coding standards and optional local feature notes. |
| `docs/agent-notes/coding-standards/` | Tracked repository coding and testing guidance used when its technical scope applies. |
| `backend/tests/README.md` | Backend test organization, execution, and safety guidance. |
| `backend/tests/` | Current backend tests, organized by behavior ownership and evaluated by usefulness and correctness. |
| `backend/tests/platform/backend_test_runner/` | Direct tests for guarded execution, database and network safety, artifact sanitization, and pytest configuration. |

Read historical or supporting records only when needed to understand current
behavior, an explicitly preserved interface or invariant, ownership, or
provenance. If they conflict with the corrected master, the master controls
production-readiness scope.

## 6. Supporting Engineering And Testing Standards

Supporting standards constrain implementation within their technical scope.
They do not expand corrected-master scope, override current product
requirements, or erase accepted repository behavior that the selected work must
preserve.

| Document | Read when |
|---|---|
| `docs/agent-notes/coding-standards/app-testing-standards.md` | Application risks, safeguards, scenarios, or verification adequacy are in scope. |
| `docs/agent-notes/coding-standards/backend-structure.md` | Backend source, ownership boundaries, imports, or file placement are in scope. |
| `docs/agent-notes/coding-standards/backend-testing.md` | Backend pytest organization, fixtures, isolation, verification quality, or execution is in scope. |
| `backend/tests/README.md` | Backend test placement, execution, or database safety is in scope. |
| `docs/agent-notes/coding-standards/database.md` | PostgreSQL, SQLAlchemy, Alembic, migrations, transactions, or test database work is in scope. |
| `docs/agent-notes/coding-standards/frontend-structure.md` | Frontend source, routing, configuration, interaction, or browser behavior is in scope. |
| `docs/agent-notes/coding-standards/css-standards.md` | CSS ownership, cascade, accessibility, responsive behavior, or maintenance is in scope. |

Local feature notes may provide supporting context when present, but they are
not a current requirement source. Verify their claims against accepted
repository source and applicable tracked requirements. Use provider or
operational records only when the selected work actually touches them.

## 7. Workflow Selection

Use the implementation workflow for a corrected-master unit being implemented
for the first time from current accepted `develop`.

Use the recheck workflow when implementation already merged into `develop`, or
older historical implementation, is being revalidated or repaired against the
corrected master and accepted repository state.

For first-time implementation:

- perform Stage 0 scope reconciliation before first work under a selected unit
  and decide whether it executes whole, decomposes, or needs a mandatory
  deferred follow-up;
- when a recorded parent decomposition remains valid, start each later child at
  Gate A instead of repeating Stage 0;
- perform Gate A engineering planning and plan review, using a concise plan for
  straightforward work and the current `PASS-PLANNING-TEMPLATE.md` whenever the
  plan is a durable document;
- implement and test as Gate B work;
- perform an independent read-only semantic review as Gate C work;
- perform Git/PR publication as Gate D work only when requested, using the
  current `PASS-PR-DESCRIPTION-TEMPLATE.md` for the PR body, and update the
  execution register once to the final state intended after merge;
- keep PR merge manual.

For a recheck of a pass already merged into `develop`, normally perform Gate A
through Gate D. Return to Stage 0 only when the recorded executable boundary or
decomposition is materially wrong.

No stage advances automatically. Do not select later work from filename order,
old pass order, or stale chat context. Use the corrected master, accepted
repository state, the current change set when relevant, real prerequisites,
late-bound triggers, and owner direction.
If several units are valid and no dependency selects one, ask the owner.

## 8. Verification Approach

Verification should address real production risks without becoming a
separate compliance platform.

Use the lowest reliable verification method and scale validation to risk.
Depending on the work, that can include unit, service, API, authorization, real
PostgreSQL, migration, deterministic concurrency, external-service boundary,
frontend, browser, configuration, build, lint, or operational checks.

Passing tests alone do not establish production readiness. Inspect behavior,
failure paths, security/privacy boundaries, compatibility, and any external
facts the repository cannot establish.

Backend verification can use current source and tests, applicable pass artifacts,
and source-local `pytest.mark.pass_provenance` where a production-readiness pass
introduced or materially changed a test as verification for the pass.
Provenance may name more than one genuine owning pass, but it is not added
merely because a pass reran a test and is not required for ordinary tests
without production-readiness provenance. Search it directly in source, for
example with `rg 'WS06-01' backend/tests`.

Plans, intakes, and audit records from earlier merged work may describe earlier
testing mechanics. They remain provenance for what happened, but they do not
define current backend test execution or verification handling.

## 9. Work Families And Ordering

The corrected master section 8 defines the 27 remaining units and the scope that
survives. The execution register records accepted execution state or the
intended post-merge state carried by a substantive PR, plus remaining and
deferred work; it does not track normal transient gate progress or define or
expand scope.

A selected unit may be kept whole or decomposed when that is genuinely needed.
Each child must own one coherent outcome, preserve all parent obligations, avoid
overlap, and leave a safe intermediate state. Historical decompositions remain
provenance unless the corrected master or a current recorded Stage 0 decision
adopts them.

Deferred infrastructure/runtime work must retain an owner, trigger,
prerequisites, and required completion boundary. It does not count as
verification while deferred and blocks only work that actually depends on the
missing fact.

After merge, verify the intended merge, switch local `develop` back to the
current `origin/develop` state using the normal safe fast-forward path, and
confirm that the Gate D register update landed in its intended final state. Do
not make a second routine register update for the same pass; use exceptional
cleanup only when publication failed or accepted repository state differs from
that intended state. Then choose subsequent work from the corrected master,
accepted repository state, real prerequisites, deferred-trigger state, and
owner direction. Do not use automatic progression. If the next unit is a later
child of a recorded decomposition that remains valid, begin that child at Gate
A; otherwise perform Stage 0 for new first-time scope.

## 10. Essential Terminology

| Term | Meaning |
|---|---|
| Corrected master | The controlling production-readiness scope, correction program, remaining roadmap, and completion criteria. |
| Requirement source | The corrected master, an applicable current product requirement, an explicit owner decision, or a technical standard that applies to the work. Name the specific source when resolving a conflict. |
| Accepted repository state | The source, configuration, tests, documentation, and migrations in current accepted `develop`. |
| Current change set | Every branch change relative to its accepted starting point: committed branch changes, staged and unstaged changes, and applicable untracked files. It is not accepted until merged. |
| Provenance | Historical evidence of what happened, such as audits, plans, PRs, commits, and diffs; provenance does not define current requirements. |
| Selected unit | The corrected-master work currently authorized for implementation or recheck. |
| Executable child | A coherent subdivision created when a selected unit genuinely needs decomposition. |
| Stage 0 | Required first-time scope/reconciliation responsibility that decides whether the unit executes whole, decomposes, or needs a deferred follow-up. |
| Gate A | Required first-time engineering planning and plan review; the plan may be concise. |
| Gate B | Implementation and risk-based testing. |
| Gate C | Independent, read-only semantic review. |
| Gate D | Normal Git and PR finalization, including the pass's one execution-register update to its intended post-merge state; it does not include merge. |
| Accepted starting point | The accepted `develop` commit from which the current branch's change set is measured. |
| Reviewed plan | The Gate A plan or planning record approved for the current implementation; not a draft or a corrected plan awaiting review. |
| Independent of final infrastructure selection | Work whose correctness does not require facts about the still-unselected final production hosting, topology, capacity, account binding, or provider-native settings. |
| Deferred obligation | Required late-bound work with a known owner, trigger, prerequisites, and completion boundary; deferral is not verification or completion. |
| Verification method | A test, source inspection, migration check, build, provider exercise, or operational exercise used to establish a stated result. |
| Validation result | A report of a verification method actually run and the result observed. |
| External evidence | Sanitized information about provider, runtime, deployment, operational, or other state that repository content cannot establish. |
| Review result | A source-backed conclusion for a specific requirement, behavior, or affected item, distinct from both the requirement source and the verification method. |

## 11. Minimum Routing For A Work Item

Before acting, identify:

- the corrected-master unit and intended outcome;
- accepted repository state, the branch's accepted starting point, and the
  complete current change set;
- applicable prerequisites and ownership;
- relevant technical and testing guidance;
- facts independent of final infrastructure selection versus facts that require
  selected final infrastructure;
- requested edit, validation, review, and publication boundaries.

Read the recorded intake or reviewed plan when the selected work has one. When
authoring a durable Gate A plan, use `PASS-PLANNING-TEMPLATE.md`; when publishing
a first-time implementation at Gate D, use `PASS-PR-DESCRIPTION-TEMPLATE.md`.
Read other historical decisions, remediation records, templates, or external
evidence only when they materially help answer one of the questions above. Do
not routinely calculate, freeze, compare, record, or verify hashes for
baselines, intakes, plans, or artifacts; normal Git safety checks remain
required.
