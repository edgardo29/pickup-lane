# Pickup Lane Production-Readiness Program Context

## 1. Purpose

This document is the stable program overview and routing index for Pickup Lane
production-readiness work. It explains the system shape, program structure,
document locations, evidence approach, work selection, and terminology.

Startup, authority order, conflict handling, repository safety, and publication
boundaries are owned by `docs/production-readiness/00-READ-ME-FIRST.md`.

Production-readiness assignments should identify the corrected-master unit and
any run-specific constraints. This document and the read-first entry point route
to the applicable workflow, technical standards, and current repository truth;
historical pass artifacts are read only when they are useful to the work.

## 2. Pickup Lane And Production-Readiness Overview

Pickup Lane is a web application for organizing and operating pickup basketball
games.
The production-readiness program spans code, configuration, tests, provider
settings, runtime proof, operational ownership, and recovery evidence.

System areas relevant to production-readiness planning include:

- Backend: FastAPI application code under `backend/`.
- Frontend: React/Vite browser application under `frontend/`.
- Database: PostgreSQL, SQLAlchemy models, and Alembic migrations.
- Authentication: Firebase-backed user identity and admin access behavior.
- Payments: Stripe-backed payment and checkout flows.
- External providers: hosting, database provider, Firebase/GCP, Stripe,
  Cloudflare/R2, DNS/TLS, repository/CI, monitoring, and backup providers.
- Product workflows: games, bookings, rosters, waitlists, Need-a-Sub, chats,
  notifications, venue images, credits, and payment-related state.
- Admin and operations: admin workflows, moderation, notices, deployment,
  health, evidence, ownership, incident, recovery, privacy, and provider
  control-plane behavior.

Production readiness requires these areas to satisfy the corrected master with
credible evidence, not merely to pass local tests.


## 3. Final Infrastructure Timing And Late-Bound Production Evidence

Temporary development/demo infrastructure must not become permanent production
architecture merely because it exists in the repository or is currently used for
a portfolio/demo deployment.

Current Vercel frontend hosting, Render API hosting, and Neon PostgreSQL hosting
are temporary development/demo infrastructure. They may be referenced when
describing current repository or demo behavior, but they are not the selected
final production hosting/database topology and must not supply permanent
provider-specific architecture, capacity assumptions, or final production
configuration values.

Final production hosting, database hosting, edge/ingress/proxy/TLS topology,
process and instance topology, autoscaling and rolling-deployment behavior,
provider plan/capacity/region, provider-native deployment settings, concrete
production roles/grants, and other infrastructure-dependent production facts
remain late-bound until the final infrastructure is selected and evidence exists.

Planning and implementation must preserve this boundary:

- Complete coherent provider-independent work when it can be implemented and
  proved without the final infrastructure. This may include portable source
  behavior, generic configuration interfaces, validation, formulas, synthetic
  fixtures, and later-verification contracts.
- A generic setting or configuration interface may be implemented before final
  infrastructure selection when its existence and validation are provider
  independent. Concrete production values that depend on the final provider or
  topology remain deferred.
- Do not promote values from temporary providers, README examples, local/CI
  configuration, free-tier defaults, framework defaults, or demo deployments
  into final production assumptions.
- If a unit contains both executable-now work and work requiring intentionally
  unselected final infrastructure, separate them rather than force an early
  provider choice or leave unrelated work blocked.
- Every mandatory deferred follow-up must identify its owner/pass, exact trigger,
  preserved obligations, dependencies, and latest required completion boundary.
  The execution register must keep that follow-up visible.
- A deferred follow-up is not evidence and does not complete its requirements.
  Run it as soon as its trigger is satisfied and no later than the first
  downstream pass that genuinely needs those facts or `CLOSE-01`, whichever
  comes first.
- Downstream work may continue only when its own prerequisites are satisfied
  without the deferred provider/runtime facts. If it needs one of those facts,
  stop on that specific missing prerequisite instead of guessing or substituting
  temporary values.

The master blueprint must identify known final-infrastructure-dependent passes or
unit portions before implementation reaches them, including the expected trigger
or late-bound placement. Scoping may refine that structure against current
repository truth, but it must not rediscover a known infrastructure dependency
only after implementation begins.

This rule does not reopen provider-specific product integrations that higher
authority has already fixed. It governs final infrastructure selection and the
concrete production configuration/evidence that depends on that selection.

## 4. Program Structure

Current production-readiness work follows this authority and execution chain:

```text
corrected master blueprint
-> current repository truth
-> selected roadmap unit and real prerequisites
-> focused planning when needed
-> implementation and risk-based testing
-> independent semantic review
-> normal Git/PR finalization and manual merge
```

The corrected master defines scope, the implemented-work correction program, the
27 remaining units, provider timing, testing philosophy, explicit do-not-build
boundaries, and completion criteria.

Earlier audits, the remediation plan, owner decisions, governance records,
intakes, plans, SHAs, and PRs remain useful provenance or technical context.
They do not override the corrected master or restore rejected scope.

The familiar Stage 0 and Gate A labels may still be used for decomposition and
planning when genuinely helpful. Gate B, Gate C, and Gate D continue to describe
implementation/testing, independent review, and Git/PR finalization. These roles
are not mandatory automatic orchestration.

## 5. Document Map And Routing Indexes

| Path | Purpose |
|---|---|
| `docs/production-readiness/00-READ-ME-FIRST.md` | Startup, authority, safety, and publication-boundary entry point. |
| `docs/production-readiness/01-PROGRAM-CONTEXT.md` | Program overview and routing index. |
| `docs/production-readiness/planning/program/pickup-lane-master-production-readiness-blueprint.md` | Authoritative production-readiness scope, correction program, remaining roadmap, and completion criteria. |
| `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md` | Factual accepted, unmerged, historical decomposition, and remaining-work state. |
| `docs/production-readiness/planning/workflows/PASS-IMPLEMENTATION-WORKFLOW.md` | First-time implementation guidance, including optional scoping/planning roles. |
| `docs/production-readiness/planning/workflows/PASS-RECHECK-WORKFLOW.md` | Recheck guidance for accepted or historical implementation. |
| `docs/production-readiness/planning/passes/` | Historical and current pass intakes/plans; consult when materially relevant, not as authority over the master. |
| `docs/production-readiness/audit-research/` | Historical audit and research provenance. |
| `docs/production-readiness/planning/program/pickup-lane-production-readiness-remediation-plan-final.md` | Historical remediation provenance; not current scope authority. |
| `docs/production-readiness/decisions/` | Historical owner decisions and supporting context; current product authority only where the corrected master or current task still adopts it. |
| `docs/production-readiness/governance/` | Supporting operational and ownership context; not authority for rejected scope. |
| `docs/production-readiness/planning/templates/` | Optional legacy drafting aids; no template is mandatory merely because it exists. |
| `docs/agent-notes/` | Repository engineering and testing guidance used when its technical scope applies. |
| `backend/tests/README.md` | Backend test organization, execution, and safety guidance. |
| `backend/tests/` | Current backend tests, evaluated by usefulness and correctness rather than trusted/legacy labels. |
| `backend/tests/support/requirements/`, `backend/tests/checker/`, `backend/tests/compliance/` | Existing old-framework infrastructure pending later cleanup under the corrected master; not required routing for current work. |

Read historical or supporting records only when needed to understand current
behavior, accepted technical contracts, ownership, or provenance. If they
conflict with the corrected master, the master controls production-readiness
scope.

## 6. Supporting Engineering And Testing Standards

Supporting standards guide implementation within their technical scope. They do
not override the corrected master or current repository truth.

| Document | Read when |
|---|---|
| `docs/agent-notes/app-testing-standards.md` | Application risks, safeguards, scenarios, or evidence adequacy are in scope. |
| `docs/agent-notes/backend-structure.md` | Backend source, ownership boundaries, imports, or file placement are in scope. |
| `docs/agent-notes/backend-testing.md` | Backend pytest organization, fixtures, isolation, proof quality, or execution is in scope. |
| `backend/tests/README.md` | Backend test placement, execution, or database safety is in scope. |
| `docs/agent-notes/database.md` | PostgreSQL, SQLAlchemy, Alembic, migrations, transactions, or test database work is in scope. |
| `docs/agent-notes/frontend-structure.md` | Frontend source, routing, configuration, interaction, or browser behavior is in scope. |
| `docs/agent-notes/playwright-structure.md` | Playwright or end-to-end work is explicitly requested or materially necessary. |

Use feature-specific agent notes and provider or operational records only when
the selected work actually touches them.

## 7. Workflow Selection

Use the implementation workflow for a corrected-master unit being implemented
for the first time from current accepted `develop`.

Use the recheck workflow when accepted or historical implementation is being
revalidated or repaired against the corrected master and current repository
truth.

Within either workflow:

- use Stage 0 only when scope or decomposition genuinely needs it;
- use Gate A only when complexity warrants a written, reviewed plan;
- implement and test as Gate B work;
- perform an independent read-only semantic review as Gate C work;
- perform Git/PR publication as Gate D work only when requested;
- keep PR merge manual.

No stage advances automatically. Do not select later work from filename order,
old pass order, or stale chat context. Use the corrected master, current
repository truth, real prerequisites, late-bound triggers, and owner direction.
If several units are valid and no dependency selects one, ask the owner.

## 8. Evidence Approach

Tests and evidence should prove real production risks without becoming a
separate compliance platform.

Use the lowest reliable proof layer and scale validation to risk. Depending on
the work, that can include unit, service, API, authorization, real PostgreSQL,
migration, deterministic concurrency, provider-boundary, frontend, browser,
configuration, build, lint, or operational evidence.

Passing tests alone do not prove production readiness. Review the behavior,
failure paths, security/privacy boundaries, compatibility, and any external facts
the repository cannot establish.

Stable requirement JSON, pytest requirement markers, checker/compliance
commands, trusted test roots, generated traceability, and
`TESTING_RECORD.md` are not mandatory. Existing useful tests and evidence
remain useful regardless of directory or old metadata. Historical testing
infrastructure remains in the repository until its corrected-master cleanup
work is performed.

## 9. Work Families And Ordering

The corrected master section 8 defines the 27 remaining units and the scope that
survives. The execution register records what is accepted, what is implemented
but unmerged, and what remains; it does not define or expand scope.

A selected unit may be kept whole or decomposed when that is genuinely needed.
Each child must own one coherent outcome, preserve all parent obligations, avoid
overlap, and leave a safe intermediate state. Historical decompositions remain
provenance unless current authority adopts them.

Deferred provider/runtime work must retain an owner, trigger, prerequisites, and
required completion boundary. It does not count as evidence while deferred and
blocks only work that actually depends on the missing fact.

After merge, choose subsequent work from the corrected master, current
repository truth, real prerequisites, deferred-trigger state, and owner
direction. Do not use automatic progression.

## 10. Essential Terminology

| Term | Meaning |
|---|---|
| Corrected master | The authoritative production-readiness scope, correction program, remaining roadmap, and completion criteria. |
| Repository truth | What current accepted source, configuration, tests, documentation, and migrations actually contain and do. |
| Provenance | Historical evidence of what happened, such as audits, plans, PRs, commits, and diffs; provenance does not define current requirements. |
| Selected unit | The corrected-master work currently authorized for implementation or recheck. |
| Executable child | A coherent subdivision created when a selected unit genuinely needs decomposition. |
| Stage 0 | Optional scope and decomposition work. |
| Gate A | Optional engineering planning and plan review. |
| Gate B | Implementation and risk-based testing. |
| Gate C | Independent, read-only semantic review. |
| Gate D | Normal Git and PR finalization; it does not include merge. |
| Accepted baseline | The current `develop` commit used as the understood starting point for a branch. |
| Provider-neutral work | Work whose correctness does not require unselected final-provider facts. |
| Deferred obligation | Required late-bound work with a known owner, trigger, prerequisites, and completion boundary; deferral is not proof. |
| External evidence | Sanitized provider, runtime, deployment, operational, or other evidence that cannot be proved from repository content alone. |

## 11. Minimum Routing For A Work Item

Before acting, identify:

- the corrected-master unit and intended outcome;
- current repository truth and accepted baseline;
- applicable prerequisites and ownership;
- relevant technical and testing guidance;
- provider-neutral versus late-bound facts;
- requested edit, validation, review, and publication boundaries.

Read an intake, plan, historical decision, remediation record, template, or
external evidence artifact only when it materially helps answer one of those
questions. No reusable artifact or document matrix is mandatory by default.
